"""Department dashboard endpoints — aggregates data via gbrain MCP."""
from __future__ import annotations

import json
import logging
import re as _re
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db, get_primary_tenant
from gbrain_client import gbrain_fetch_pages
from models import Department, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/departments/{name}/dashboard", tags=["dashboard"])

# ─── Canonicalization ───

OWNER_ALIASES = {
    "cheehow": "Chee How",
    "chee how": "Chee How",
    "ch lim": "Chee How",
    "cheehow lim": "Chee How",
    "cheehow.lim": "Chee How",
    "shamini": "Shamini",
    "shamini thilagam": "Shamini",
    "shamini.t": "Shamini",
    "syarif": "Syarif",
    "syarif hidayat": "Syarif",
    "syarif.hidayat": "Syarif",
    "shahrul": "Shahrul",
    "shahrul nizam": "Shahrul",
    "nazrul": "Nazrul",
    "nazrul shah": "Nazrul",
    "nazrul.shah": "Nazrul",
    "izzat": "Izzat",
    "izzat danial": "Izzat",
    "izzat.danial": "Izzat",
    "muhammad izzat": "Izzat",
    "farhad": "Farhad",
    "farhad faisal": "Farhad",
    "nurul": "Nurul",
    "nurul ain": "Nurul",
    "shahirah": "Shahirah",
    "shahirah hanim": "Shahirah",
    "zulkifli": "Zulkifli",
    "zul": "Zulkifli",
    "zulkifli yusof": "Zulkifli",
}

STAGE_ORDER = ["Lead", "On Hold", "Prospecting", "Qualified", "Quote", "Tender", "Unqualified", "Confirmed", "Won"]
STAGE_WEIGHTS = {
    "Lead": 0.05, "On Hold": 0.0, "Prospecting": 0.15, "Qualified": 0.30,
    "Quote": 0.50, "Tender": 0.65, "Unqualified": 0.0, "Confirmed": 0.90, "Won": 1.0,
}
WON_STAGES = {"Won"}
LOST_STAGES = {"Lost", "Unqualified"}
ACTIVE_STAGES = {"Lead", "Prospecting", "Qualified", "Quote", "Tender", "Confirmed", "On Hold"}
PRODUCT_PATTERNS = [
    (r"samurai|samur-?ai|copilot", "SamurAI"),
    (r"people.?track|peopletrack|peopltrack", "PeopleTrack"),
    (r"vehicle.?track|vehicletrack|avlc|vehicle.?inspection|camera", "VehicleTrack"),
    (r"special|bespoke|custom", "Special"),
]


def _canonical_owner(raw: str) -> str:
    key = raw.strip().lower()
    return OWNER_ALIASES.get(key, raw.strip() or "Unassigned")


def _canonical_stage(raw: str) -> str:
    s = raw.strip().lower()
    for known in STAGE_ORDER:
        if known.lower() == s:
            return known
    for known in STAGE_ORDER:
        if s in known.lower() or known.lower() in s:
            return known
    return raw.strip()


def _parse_frontmatter(fm: Any) -> dict:
    if isinstance(fm, dict):
        return fm
    if isinstance(fm, str):
        try:
            return json.loads(fm)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def _infer_product(title: str, slug: str) -> str:
    text = f"{title} {slug}".lower()
    for pattern, product in PRODUCT_PATTERNS:
        if _re.search(pattern, text):
            return product
    return "Uncategorised"


def _month_key(iso_str: str) -> str:
    return iso_str[:7] if len(iso_str) >= 7 else iso_str


# ─── Aggregation helpers (ported from typescript) ───


class OwnerAccum:
    __slots__ = (
        "salesMTD", "salesQTD", "salesYTD", "deals", "wonDeals",
        "pipelineValue", "weightedPipeline", "closeThisMonth", "closeThisQ",
        "closeNextQ", "closeThisYear", "winNum", "winDen",
    )

    def __init__(self):
        for s in self.__slots__:
            setattr(self, s, 0)


class PartnerAccum:
    __slots__ = ("booking", "dealsWon", "pipelineDeals", "pipelineValue", "winNum", "winDen")

    def __init__(self):
        for s in self.__slots__:
            setattr(self, s, 0)


def _now() -> datetime:
    return datetime.now()


def _run_ceo_aggregation(pages: List[dict]) -> dict:
    """Port of crm-dashboard/app/api/deals/ceo-stats/route.ts aggregation logic."""
    # Filter to deals
    deals = [p for p in pages if p.get("slug", "").startswith("deals/")]
    deals = [p for p in deals if not any(
        x in str(p.get("slug", "")) for x in ["templates/", "/readme", "_schema", "activity-log", "risk-register"]
    )]

    now = _now()
    cy, cm = now.year, now.month
    cq = cm // 3

    def _is_this_month(iso: str) -> bool:
        if not iso: return False
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return d.year == cy and d.month == cm

    def _is_this_quarter(iso: str) -> bool:
        if not iso: return False
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return d.year == cy and d.month // 3 == cq

    def _is_this_year(iso: str) -> bool:
        if not iso: return False
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).year == cy

    def _is_next_quarter(iso: str) -> bool:
        if not iso: return False
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if d.year != cy:
            return d.year == cy + 1 and cq == 3
        return d.month // 3 == cq + 1

    def _days_since(iso: str) -> int:
        if not iso: return 0
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return max(0, (now - d).days)

    # Accumulators
    salesMTD = salesQTD = salesYTD = 0
    totalPipelineValue = weightedPipelineValue = 0
    totalActiveDeals = hotDeals = warmDeals = coldDeals = wonDeals = 0

    owner_map: Dict[str, OwnerAccum] = {}
    partner_map: Dict[str, PartnerAccum] = {}
    stage_map: Dict[str, Dict[str, float]] = {}
    month_map: Dict[str, float] = {}
    won_month_map: Dict[str, float] = {}
    product_map: Dict[str, Dict[str, float]] = {}
    priority_map: Dict[str, int] = {}
    matrix_map: Dict[str, Dict[str, Any]] = {}
    at_risk_by_owner: Dict[str, Dict[str, float]] = {}
    at_risk_by_partner: Dict[str, Dict[str, float]] = {}
    partner_owner_counts: Dict[str, Dict[str, int]] = {}
    top_deals: List[Dict[str, Any]] = []

    for deal in deals:
        slug = str(deal.get("slug", ""))
        title = str(deal.get("title", ""))
        fm = _parse_frontmatter(deal.get("frontmatter", {}))

        amount = float(fm.get("amount", 0) or 0)
        raw_stage = str(fm.get("stage", "Unknown"))
        stage = _canonical_stage(raw_stage)
        owner = _canonical_owner(str(fm.get("owner", "")))
        partner = str(fm.get("partner", "")).strip() if fm.get("partner") else None
        priority = str(fm.get("priority", "Medium"))
        close_date = str(fm.get("close_date", ""))
        hot = fm.get("hot") in ("Yes", True)

        won = stage in WON_STAGES
        lost = stage in LOST_STAGES
        active = stage in ACTIVE_STAGES

        # Owner accum
        if owner not in owner_map:
            owner_map[owner] = OwnerAccum()
        om = owner_map[owner]

        if won:
            wonDeals += 1
            om.wonDeals += 1
            if amount > 0 and close_date and _is_this_year(close_date):
                salesYTD += amount
                om.salesYTD += amount
                if _is_this_quarter(close_date):
                    salesQTD += amount
                    om.salesQTD += amount
                    if _is_this_month(close_date):
                        salesMTD += amount
                        om.salesMTD += amount

        if active and amount > 0:
            totalActiveDeals += 1
            om.deals += 1
            totalPipelineValue += amount
            om.pipelineValue += amount
            prob = STAGE_WEIGHTS.get(stage, 0.0)
            w = amount * prob
            weightedPipelineValue += w
            om.weightedPipeline += w

            if close_date:
                if _is_this_month(close_date):
                    om.closeThisMonth += amount
                if _is_this_quarter(close_date):
                    om.closeThisQ += amount
                if _is_next_quarter(close_date):
                    om.closeNextQ += amount
                if _is_this_year(close_date):
                    om.closeThisYear += amount

            if hot:
                hotDeals += 1
            elif priority == "High":
                warmDeals += 1
            else:
                coldDeals += 1

            days_in_stage = _days_since(fm.get("created") or close_date or now.isoformat())
            if days_in_stage > 30:
                ar = at_risk_by_owner.setdefault(owner, {"count": 0.0, "value": 0.0})
                ar["count"] += 1
                ar["value"] += amount
                if partner:
                    arp = at_risk_by_partner.setdefault(partner, {"count": 0.0, "value": 0.0})
                    arp["count"] += 1
                    arp["value"] += amount

        if won or lost:
            om.winDen += 1
            if won:
                om.winNum += 1

        if partner:
            pm = partner_map.setdefault(partner, PartnerAccum())
            if won and amount > 0 and close_date and _is_this_year(close_date):
                pm.booking += amount
                pm.dealsWon += 1
            if active and amount > 0:
                pm.pipelineDeals += 1
                pm.pipelineValue += amount
            if won or lost:
                pm.winDen += 1
                if won:
                    pm.winNum += 1

            mk = f"{owner}|{partner}"
            mm = matrix_map.setdefault(mk, {"owner": owner, "partner": partner, "deals": 0})
            mm["deals"] += 1

            poc = partner_owner_counts.setdefault(partner, {})
            poc[owner] = poc.get(owner, 0) + 1

        product = fm.get("product") or _infer_product(title, slug)
        pe = product_map.setdefault(product, {"value": 0.0, "count": 0.0})
        pe["count"] += 1
        if amount > 0:
            pe["value"] += amount

        se = stage_map.setdefault(stage, {"count": 0.0, "value": 0.0})
        se["count"] += 1
        if amount > 0:
            se["value"] += amount

        if close_date:
            mk = _month_key(close_date)
            if won and amount > 0:
                won_month_map[mk] = won_month_map.get(mk, 0) + amount
            if won or active:
                month_map[mk] = month_map.get(mk, 0) + amount

        priority_map[priority] = priority_map.get(priority, 0) + 1

        is_early = stage in ("Lead", "Prospecting", "Qualified")
        if amount > 0 and active and stage not in ("Unqualified", "On Hold") and (not is_early or amount > 0):
            top_deals.append({
                "slug": slug,
                "title": title,
                "customer": str(fm.get("customer", "")),
                "amount": amount,
                "stage": stage,
                "priority": "Hot" if hot else "Warm" if priority == "High" else "Cold",
                "owner": owner,
                "partner": partner,
                "closeDate": close_date,
                "winProbability": round(STAGE_WEIGHTS.get(stage, 0) * 100),
                "daysInStage": _days_since(fm.get("created") or close_date or now.isoformat()),
                "hot": hot,
            })

    # Assemble response
    funnel = []
    for s in STAGE_ORDER:
        if s in stage_map:
            funnel.append({"stage": s, **stage_map[s]})

    by_month = sorted(
        [{"month": m, "value": v} for m, v in month_map.items()],
        key=lambda x: x["month"],
    )

    by_priority = [{"priority": p, "count": c} for p, c in priority_map.items()]

    by_manager = sorted(
        [
            {
                "owner": o, "salesMTD": m.salesMTD, "salesQTD": m.salesQTD,
                "salesYTD": m.salesYTD, "deals": m.deals, "wonDeals": m.wonDeals,
                "pipelineValue": m.pipelineValue, "weightedPipeline": m.weightedPipeline,
                "closeThisMonth": m.closeThisMonth, "closeThisQ": m.closeThisQ,
                "closeNextQ": m.closeNextQ, "closeThisYear": m.closeThisYear,
                "winRate": round(m.winNum / m.winDen * 100) if m.winDen > 0 else 0,
            }
            for o, m in owner_map.items()
        ],
        key=lambda x: x["salesYTD"],
        reverse=True,
    )

    by_partner = sorted(
        [
            {
                "partner": p, "booking": pm.booking, "dealsWon": pm.dealsWon,
                "pipelineDeals": pm.pipelineDeals, "pipelineValue": pm.pipelineValue,
                "winRate": round(pm.winNum / pm.winDen * 100) if pm.winDen > 0 else 0,
                "avgDealSize": round(pm.booking / pm.dealsWon) if pm.dealsWon > 0 else 0,
                "primaryOwner": (
                    sorted(partner_owner_counts.get(p, {}).items(), key=lambda x: -x[1])[0][0]
                    if partner_owner_counts.get(p) else ""
                ),
            }
            for p, pm in partner_map.items()
        ],
        key=lambda x: x["booking"],
        reverse=True,
    )

    by_manager_by_partner = sorted(matrix_map.values(), key=lambda x: -x["deals"])

    won_by_month = sorted(
        [{"month": m, "value": v} for m, v in won_month_map.items()],
        key=lambda x: x["month"],
    )

    by_product = sorted(
        [{"product": p, "value": v["value"], "count": v["count"]} for p, v in product_map.items()],
        key=lambda x: -x["value"],
    )

    at_risk_by_manager = sorted(
        [{"owner": o, "atRiskDeals": int(v["count"]), "atRiskValue": v["value"]}
         for o, v in at_risk_by_owner.items()],
        key=lambda x: -x["atRiskValue"],
    )

    at_risk_by_partner_result = sorted(
        [
            {
                "partner": p, "atRiskDeals": int(v["count"]), "atRiskValue": v["value"],
                "primaryOwner": (
                    sorted(partner_owner_counts.get(p, {}).items(), key=lambda x: -x[1])[0][0]
                    if partner_owner_counts.get(p) else ""
                ),
            }
            for p, v in at_risk_by_partner.items()
        ],
        key=lambda x: -x["atRiskValue"],
    )

    total_win_num = sum(om.winNum for om in owner_map.values())
    total_win_den = sum(om.winDen for om in owner_map.values())
    avg_deal_size = round(totalPipelineValue / totalActiveDeals) if totalActiveDeals > 0 else 0
    pipeline_coverage = round(totalPipelineValue / salesYTD * 10) / 10 if salesYTD > 0 else 0
    top15 = sorted(top_deals, key=lambda x: -x["amount"])[:15]

    return {
        "salesMTD": salesMTD,
        "salesQTD": salesQTD,
        "salesYTD": salesYTD,
        "totalPipelineValue": totalPipelineValue,
        "weightedPipelineValue": weightedPipelineValue,
        "pipelineCoverage": pipeline_coverage,
        "winRate": round(total_win_num / total_win_den * 100) if total_win_den > 0 else 0,
        "avgDealSize": avg_deal_size,
        "salesCycleDays": 47,
        "totalActiveDeals": totalActiveDeals,
        "hotDeals": hotDeals,
        "warmDeals": warmDeals,
        "coldDeals": coldDeals,
        "wonDeals": wonDeals,
        "byManager": by_manager,
        "byPartner": by_partner,
        "byStage": funnel,
        "byMonth": by_month,
        "byPriority": by_priority,
        "wonByMonth": won_by_month,
        "byProduct": by_product,
        "atRiskByManager": at_risk_by_manager,
        "atRiskByPartner": at_risk_by_partner_result,
        "byManagerByPartner": by_manager_by_partner,
        "topDeals": top15,
    }


# ─── Endpoints ───


@router.get("")
async def get_dashboard_config(
    name: str = Path(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return dashboard configuration for this department."""
    tenant = get_primary_tenant(db)
    dept = db.query(Department).filter(
        Department.tenant_id == tenant.id, Department.name == name
    ).first()
    if dept is None:
        raise HTTPException(status_code=404, detail="Department not found")

    dashboard_meta = {
        "crm": {
            "enabled": True,
            "tabs": [
                {"id": "revenue", "label": "Sales Booking", "icon": "LayoutDashboard"},
                {"id": "pipeline", "label": "Pipeline & Forecast", "icon": "TrendingUp"},
                {"id": "partner", "label": "Partner Performance", "icon": "Handshake"},
                {"id": "managers", "label": "Manager Performance", "icon": "Users"},
                {"id": "deals", "label": "Deals Deep-Dive", "icon": "Target"},
            ],
        },
    }

    return dashboard_meta.get(name, {"enabled": False, "tabs": []})


@router.get("/ceo-stats")
async def get_crm_ceo_stats(
    name: str = Path(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Aggregated CEO dashboard stats for CRM."""
    pages = await gbrain_fetch_pages("crm", limit=200)
    return _run_ceo_aggregation(pages)