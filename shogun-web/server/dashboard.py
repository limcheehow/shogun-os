"""Department dashboard endpoints — aggregates data via gbrain MCP."""
from __future__ import annotations

import json
import logging
import pathlib
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
        next_q = (cq + 1) % 4
        next_q_year = cy + (1 if cq == 3 else 0)
        return d.year == next_q_year and d.month // 3 == next_q

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

    # Omnichannel accumulators (spec §2.3)
    channel_volume = {"shopee": 0, "lazada": 0, "fbMessenger": 0, "whatsapp": 0}
    _CHANNEL_MAP = {
        "Shopee": "shopee", "Lazada": "lazada",
        "Facebook Messenger": "fbMessenger", "FB Messenger": "fbMessenger",
        "WhatsApp": "whatsapp",
    }
    response_minutes: List[float] = []
    sla_compliant = 0
    ai_resolved = 0
    chat_inbox_rows: List[Dict[str, Any]] = []

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

        # Omnichannel: accumulate per-deal channel_origin + sla_response_minutes (spec §3)
        raw_channel = str(fm.get("channel_origin", "")).strip()
        chan_key = _CHANNEL_MAP.get(raw_channel)
        if chan_key:
            channel_volume[chan_key] = channel_volume.get(chan_key, 0) + 1
        raw_sla = fm.get("sla_response_minutes")
        if raw_sla not in (None, ""):
            try:
                sla_val = float(raw_sla)
                response_minutes.append(sla_val)
                if sla_val <= 15:
                    sla_compliant += 1
            except (TypeError, ValueError):
                pass

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

    # ── Omnichannel: derive from deals where possible, fall back to examples/crm-mock.json ──
    # Inbox + weekly trend are net-new data with no deal source (Concern 2); always load from mock.
    crm_mock: Dict[str, Any] = {}
    mock_json_path = pathlib.Path(__file__).resolve().parents[2] / "examples" / "crm-mock.json"
    if mock_json_path.exists():
        try:
            with open(mock_json_path, "r", encoding="utf-8") as f:
                crm_mock = json.load(f).get("dashboard_mock", {})
        except Exception as e:
            logger.warning("Failed to load mock data from %s: %s", mock_json_path, e)

    if totalActiveDeals == 0 and not wonDeals:
        # No real deals at all — return the full CRM mock wholesale (spec §1 Phase 1:
        # "realistic mock data engine, zero code modification required for preview").
        # Mirrors the finance/procurement fallback: every field below has a mock value
        # so all 6 sub-tabs render populated. The aggregated accumulators above are
        # discarded in this branch.
        return {
            "salesMTD": _safe_int(crm_mock.get("salesMTD")),
            "salesQTD": _safe_int(crm_mock.get("salesQTD")),
            "salesYTD": _safe_int(crm_mock.get("salesYTD")),
            "totalPipelineValue": _safe_int(crm_mock.get("totalPipelineValue")),
            "weightedPipelineValue": _safe_int(crm_mock.get("weightedPipelineValue")),
            "pipelineCoverage": _safe_float(crm_mock.get("pipelineCoverage")),
            "winRate": _safe_int(crm_mock.get("winRate")),
            "avgDealSize": _safe_int(crm_mock.get("avgDealSize")),
            "salesCycleDays": _safe_int(crm_mock.get("salesCycleDays"), 47),
            "totalActiveDeals": _safe_int(crm_mock.get("totalActiveDeals")),
            "hotDeals": _safe_int(crm_mock.get("hotDeals")),
            "warmDeals": _safe_int(crm_mock.get("warmDeals")),
            "coldDeals": _safe_int(crm_mock.get("coldDeals")),
            "wonDeals": _safe_int(crm_mock.get("wonDeals")),
            "byManager": crm_mock.get("byManager", []),
            "byPartner": crm_mock.get("byPartner", []),
            "byStage": crm_mock.get("byStage", []),
            "byMonth": crm_mock.get("byMonth", []),
            "byPriority": crm_mock.get("byPriority", []),
            "wonByMonth": crm_mock.get("wonByMonth", []),
            "byProduct": crm_mock.get("byProduct", []),
            "atRiskByManager": crm_mock.get("atRiskByManager", []),
            "atRiskByPartner": crm_mock.get("atRiskByPartner", []),
            "byManagerByPartner": crm_mock.get("byManagerByPartner", []),
            "topDeals": crm_mock.get("topDeals", []),
            "channelVolume": crm_mock.get("channelVolume", {"shopee": 0, "lazada": 0, "fbMessenger": 0, "whatsapp": 0}),
            "avgResponseMinutes": _safe_float(crm_mock.get("avgResponseMinutes")),
            "slaCompliancePct": _safe_float(crm_mock.get("slaCompliancePct")),
            "aiResolutionPct": _safe_float(crm_mock.get("aiResolutionPct")),
            "chatToOrderPct": _safe_float(crm_mock.get("chatToOrderPct")),
            "chatToOrderTrend": crm_mock.get("chatToOrderTrend", []),
            "chatInbox": crm_mock.get("chatInbox", []),
        }

    # Real deals exist — derive channel volume + SLA from frontmatter; inbox + trend still mock
    channel_volume_out = channel_volume
    if response_minutes:
        avg_response = round(sum(response_minutes) / len(response_minutes), 1)
        sla_pct = round(sla_compliant / len(response_minutes) * 100, 1)
    else:
        avg_response = _safe_float(crm_mock.get("avgResponseMinutes"))
        sla_pct = _safe_float(crm_mock.get("slaCompliancePct"))
    ai_pct = _safe_float(crm_mock.get("aiResolutionPct"))
    c2o_pct = _safe_float(crm_mock.get("chatToOrderPct"))
    c2o_trend = crm_mock.get("chatToOrderTrend", [])
    chat_inbox_out = crm_mock.get("chatInbox", [])

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
        "channelVolume": channel_volume_out,
        "avgResponseMinutes": avg_response,
        "slaCompliancePct": sla_pct,
        "aiResolutionPct": ai_pct,
        "chatToOrderPct": c2o_pct,
        "chatToOrderTrend": c2o_trend,
        "chatInbox": chat_inbox_out,
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
                {"id": "omnichannel", "label": "Omnichannel Chat", "icon": "MessageCircle"},
                {"id": "partner", "label": "Partner Performance", "icon": "Handshake"},
                {"id": "managers", "label": "Manager Performance", "icon": "Users"},
                {"id": "deals", "label": "Deals Deep-Dive", "icon": "Target"},
            ],
        },
        "finance": {
            "enabled": True,
            "tabs": [
                {"id": "pulse", "label": "Executive Pulse", "icon": "LayoutDashboard"},
                {"id": "runway", "label": "Cash & Runway", "icon": "TrendingUp"},
                {"id": "ops", "label": "AR & AP Ops", "icon": "Receipt"},
                {"id": "bva", "label": "Budget vs Actuals", "icon": "BarChart3"},
                {"id": "compliance", "label": "Close & Tax", "icon": "ShieldCheck"},
            ],
        },
        "procurement": {
            "enabled": True,
            "tabs": [
                {"id": "pulse", "label": "Procurement & Reorder Pulse", "icon": "LayoutDashboard"},
                {"id": "inventory", "label": "Inventory & Dead Stock", "icon": "Package"},
                {"id": "movements", "label": "Stock Movement Audit", "icon": "ArrowLeftRight"},
                {"id": "po", "label": "POs & Vendor Scorecard", "icon": "ClipboardList"},
                {"id": "bridge", "label": "Accounting Bridge", "icon": "Scale"},
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


# ─── Finance aggregation helpers ───

def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val or 0)
    except (TypeError, ValueError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(float(val or 0))
    except (TypeError, ValueError):
        return default


def _run_finance_aggregation(pages: List[dict]) -> dict:
    """Aggregate gbrain finance pages into structured dashboard stats.
    Supplies rich demo mock data when gbrain snapshots are empty so users can view all 5 tabs immediately.
    """
    now = _now()
    cy, cm = now.year, now.month

    # ── Pull snapshot pages (finance agent writes these) ──
    snapshot_map: Dict[str, dict] = {}
    for p in pages:
        slug = str(p.get("slug", ""))
        fm = _parse_frontmatter(p.get("frontmatter", {}))
        if not fm:
            try:
                body = p.get("content") or p.get("body") or ""
                fm = json.loads(body) if body else {}
            except (json.JSONDecodeError, TypeError):
                fm = {}
        if fm:
            snapshot_map[slug] = fm

    # Check if we have real snapshot data
    cash_snap = snapshot_map.get("snapshots/cash", snapshot_map.get("finance/snapshots/cash", {}))
    pl_snap = snapshot_map.get("snapshots/pl", snapshot_map.get("finance/snapshots/pl", {}))
    has_real_data = bool(cash_snap or pl_snap)

    if has_real_data:
        total_liquid_cash = _safe_float(cash_snap.get("total_liquid_cash"))
        net_monthly_burn = _safe_float(cash_snap.get("net_monthly_burn"))
        cash_runway_months = _safe_float(cash_snap.get("cash_runway_months", 0))
        revenue_mtd = _safe_float(pl_snap.get("revenue_mtd"))
        revenue_ytd = _safe_float(pl_snap.get("revenue_ytd"))
        gross_margin = _safe_float(pl_snap.get("gross_margin_pct"))
        ebitda_margin = _safe_float(pl_snap.get("ebitda_margin_pct"))
        unpaid_statutory = _safe_float(pl_snap.get("unpaid_statutory"))

        revenue_opex_trend: List[dict] = pl_snap.get("revenue_opex_trend", [])
        cash_flow_trend: List[dict] = cash_snap.get("cash_flow_trend", [])

        risk_alerts: List[dict] = []
        concentration_snap = snapshot_map.get("snapshots/concentration", snapshot_map.get("finance/snapshots/concentration", {}))
        for client in concentration_snap.get("clients", []):
            pct = _safe_float(client.get("revenue_pct"))
            if pct > 20:
                risk_alerts.append({
                    "type": "concentration",
                    "level": "warning",
                    "message": f"{client.get('name', 'Unknown')} represents {pct:.1f}% of YTD revenue",
                })

        bva_snap = snapshot_map.get("snapshots/bva", snapshot_map.get("finance/snapshots/bva", {}))
        for dept_line in bva_snap.get("departments", []):
            var_pct = _safe_float(dept_line.get("variance_pct"))
            if var_pct > 10:
                risk_alerts.append({
                    "type": "overrun",
                    "level": "warning",
                    "message": f"{dept_line.get('department', 'Unknown')} is {var_pct:.1f}% over OPEX budget",
                })

        ar_snap = snapshot_map.get("snapshots/ar", snapshot_map.get("finance/snapshots/ar", {}))
        overdue_90 = _safe_float(ar_snap.get("bucket_90_plus"))
        if overdue_90 > 0:
            risk_alerts.append({
                "type": "ar_overdue",
                "level": "critical" if overdue_90 > 50000 else "warning",
                "message": f"RM {overdue_90:,.0f} in receivables overdue >90 days",
            })

        if cash_runway_months == 0:
            runway_status = "unknown"
        elif cash_runway_months < 3:
            runway_status = "critical"
        elif cash_runway_months < 6:
            runway_status = "caution"
        else:
            runway_status = "healthy"

        bank_accounts: List[dict] = cash_snap.get("bank_accounts", [])
        fx_positions: List[dict] = cash_snap.get("fx_positions", [])
        forecast_13w: dict = cash_snap.get("forecast_13w", {"conservative": [], "expected": [], "optimistic": []})
        fixed_opex = _safe_float(cash_snap.get("fixed_opex"))
        variable_opex = _safe_float(cash_snap.get("variable_opex"))

        total_ar = _safe_float(ar_snap.get("total_ar"))
        ar_overdue_30 = _safe_float(ar_snap.get("bucket_31_60")) + _safe_float(ar_snap.get("bucket_61_90")) + _safe_float(ar_snap.get("bucket_90_plus"))
        dso = _safe_float(ar_snap.get("dso"))
        ar_aging = {
            "bucket_0_30": _safe_float(ar_snap.get("bucket_0_30")),
            "bucket_31_60": _safe_float(ar_snap.get("bucket_31_60")),
            "bucket_61_90": _safe_float(ar_snap.get("bucket_61_90")),
            "bucket_90_plus": _safe_float(ar_snap.get("bucket_90_plus")),
        }
        dunning_queue: List[dict] = ar_snap.get("dunning_queue", [])

        ap_snap = snapshot_map.get("snapshots/ap", snapshot_map.get("finance/snapshots/ap", {}))
        total_ap = _safe_float(ap_snap.get("total_ap"))
        ap_overdue = _safe_float(ap_snap.get("ap_overdue"))
        dpo = _safe_float(ap_snap.get("dpo"))
        ap_bills: List[dict] = ap_snap.get("bills", [])

        bva_departments: List[dict] = bva_snap.get("departments", [])
        unit_economics: dict = bva_snap.get("unit_economics", {"gross_margin_pct": gross_margin, "contribution_margin_pct": 0, "cac": 0, "ltv": 0, "ltv_cac_ratio": 0})
        client_concentration: List[dict] = concentration_snap.get("clients", [])

        compliance_snap = snapshot_map.get("snapshots/compliance", snapshot_map.get("finance/snapshots/compliance", {}))
        close_checklist: List[dict] = compliance_snap.get("close_checklist", [])
        statutory_schedule: List[dict] = compliance_snap.get("statutory_schedule", [])
        sst_readiness: dict = compliance_snap.get("sst_readiness", {"draft_status": "Not Started", "taxable_sales": 0, "sst_liability": 0})
        cp58_register: List[dict] = compliance_snap.get("cp58_register", [])
        wht_queue: List[dict] = compliance_snap.get("wht_queue", [])
        expense_claim_audit: List[dict] = compliance_snap.get("expense_claim_audit", [])
    else:
        # ── LOAD FROM EXAMPLES/FINANCE-BUDGET.JSON ──
        json_path = pathlib.Path(__file__).resolve().parents[2] / "examples" / "finance-budget.json"
        mock_data = {}
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    file_content = json.load(f)
                    mock_data = file_content.get("dashboard_mock", {})
            except Exception as e:
                logger.warning("Failed to load mock data from %s: %s", json_path, e)

        total_liquid_cash = _safe_float(mock_data.get("totalLiquidCash", 1450000.0))
        net_monthly_burn = _safe_float(mock_data.get("netMonthlyBurn", 120000.0))
        cash_runway_months = _safe_float(mock_data.get("cashRunwayMonths", 12.1))
        runway_status = str(mock_data.get("runwayStatus", "healthy"))
        revenue_mtd = _safe_float(mock_data.get("revenueMTD", 340000.0))
        revenue_ytd = _safe_float(mock_data.get("revenueYTD", 3850000.0))
        gross_margin = _safe_float(mock_data.get("grossMargin", 64.2))
        ebitda_margin = _safe_float(mock_data.get("ebitdaMargin", 22.1))
        unpaid_statutory = _safe_float(mock_data.get("unpaidStatutory", 42500.0))

        risk_alerts = mock_data.get("riskAlerts", [])
        revenue_opex_trend = mock_data.get("revenueOpexTrend", [])
        cash_flow_trend = mock_data.get("cashFlowTrend", [])

        bank_accounts = mock_data.get("bankAccounts", [])
        fx_positions = mock_data.get("fxPositions", [])
        fixed_opex = _safe_float(mock_data.get("fixedOpex", 85000.0))
        variable_opex = _safe_float(mock_data.get("variableOpex", 35000.0))
        forecast_13w = mock_data.get("forecast13w", {"expected": [], "conservative": [], "optimistic": []})

        total_ar = _safe_float(mock_data.get("totalAR", 485000.0))
        ar_overdue_30 = _safe_float(mock_data.get("arOverdue30", 145000.0))
        dso = _safe_float(mock_data.get("dso", 38.0))
        total_ap = _safe_float(mock_data.get("totalAP", 210000.0))
        ap_overdue = _safe_float(mock_data.get("apOverdue", 32000.0))
        dpo = _safe_float(mock_data.get("dpo", 28.0))

        ar_aging = mock_data.get("arAging", {"bucket_0_30": 340000.0, "bucket_31_60": 65000.0, "bucket_61_90": 40000.0, "bucket_90_plus": 40000.0})
        dunning_queue = mock_data.get("dunningQueue", [])
        ap_bills = mock_data.get("apBills", [])

        bva_departments = mock_data.get("bvaDepartments", [])
        unit_economics = mock_data.get("unitEconomics", {"gross_margin_pct": 64.2, "contribution_margin_pct": 48.5, "cac": 4200.0, "ltv": 24000.0, "ltv_cac_ratio": 5.7})
        client_concentration = mock_data.get("clientConcentration", [])

        close_checklist = mock_data.get("closeChecklist", [])
        statutory_schedule = mock_data.get("statutorySchedule", [])
        sst_readiness = mock_data.get("sstReadiness", {"draft_status": "Draft In Progress", "taxable_sales": 520000.0, "sst_liability": 31200.0})
        cp58_register = mock_data.get("cp58Register", [])
        wht_queue = mock_data.get("whtQueue", [])
        expense_claim_audit = mock_data.get("expenseClaimAudit", [])

    return {
        # Tab 1 — Executive Pulse
        "totalLiquidCash": total_liquid_cash,
        "netMonthlyBurn": net_monthly_burn,
        "cashRunwayMonths": cash_runway_months,
        "runwayStatus": runway_status,
        "revenueMTD": revenue_mtd,
        "revenueYTD": revenue_ytd,
        "grossMargin": gross_margin,
        "ebitdaMargin": ebitda_margin,
        "unpaidStatutory": unpaid_statutory,
        "riskAlerts": risk_alerts,
        "revenueOpexTrend": revenue_opex_trend,
        "cashFlowTrend": cash_flow_trend,
        # Tab 2 — Cash & Runway
        "bankAccounts": bank_accounts,
        "fxPositions": fx_positions,
        "forecast13w": forecast_13w,
        "fixedOpex": fixed_opex,
        "variableOpex": variable_opex,
        # Tab 3 — AR & AP
        "totalAR": total_ar,
        "arOverdue30": ar_overdue_30,
        "dso": dso,
        "totalAP": total_ap,
        "apOverdue": ap_overdue,
        "dpo": dpo,
        "arAging": ar_aging,
        "dunningQueue": dunning_queue,
        "apBills": ap_bills,
        # Tab 4 — BvA & Unit Economics
        "bvaDepartments": bva_departments,
        "unitEconomics": unit_economics,
        "clientConcentration": client_concentration,
        # Tab 5 — Close & Tax
        "closeChecklist": close_checklist,
        "statutorySchedule": statutory_schedule,
        "sstReadiness": sst_readiness,
        "cp58Register": cp58_register,
        "whtQueue": wht_queue,
        "expenseClaimAudit": expense_claim_audit,
    }


@router.get("/finance-stats")
async def get_finance_stats(
    name: str = Path(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Aggregated Finance dashboard stats — all 5 tabs."""
    pages = await gbrain_fetch_pages("finance", limit=300)
    return _run_finance_aggregation(pages)


# ─── Procurement aggregation helpers ───


def _run_procurement_aggregation(pages: List[dict]) -> dict:
    """Aggregate gbrain procurement pages into structured dashboard stats.
    Supplies rich demo mock data when gbrain snapshots are empty so users can view all 5 tabs immediately.
    """
    # ── Pull snapshot pages (procurement agent writes these) ──
    snapshot_map: Dict[str, dict] = {}
    for p in pages:
        slug = str(p.get("slug", ""))
        fm = _parse_frontmatter(p.get("frontmatter", {}))
        if not fm:
            try:
                body = p.get("content") or p.get("body") or ""
                fm = json.loads(body) if body else {}
            except (json.JSONDecodeError, TypeError):
                fm = {}
        if fm:
            snapshot_map[slug] = fm

    inventory_snap = snapshot_map.get("snapshots/inventory", snapshot_map.get("procurement/snapshots/inventory", {}))
    po_snap = snapshot_map.get("snapshots/purchase-orders", snapshot_map.get("procurement/snapshots/purchase-orders", {}))
    vendor_snap = snapshot_map.get("snapshots/vendors", snapshot_map.get("procurement/snapshots/vendors", {}))
    movement_snap = snapshot_map.get("snapshots/stock-movements", snapshot_map.get("procurement/snapshots/stock-movements", {}))
    bridge_snap = snapshot_map.get("snapshots/accounting-bridge", snapshot_map.get("procurement/snapshots/accounting-bridge", {}))
    has_real_data = bool(inventory_snap or po_snap)

    if has_real_data:
        total_inventory_valuation = _safe_float(inventory_snap.get("total_inventory_valuation"))
        total_active_skus = _safe_float(inventory_snap.get("total_active_skus"))
        low_stock_alerts = _safe_float(inventory_snap.get("low_stock_alerts"))
        dead_slow_stock_capital = _safe_float(inventory_snap.get("dead_slow_stock_capital"))
        valuation_by_category: List[dict] = inventory_snap.get("valuation_by_category", [])
        sku_catalog: List[dict] = inventory_snap.get("sku_catalog", [])
        dead_slow_stock: List[dict] = inventory_snap.get("dead_slow_stock", [])
        warehouse_bin_capacity: List[dict] = inventory_snap.get("warehouse_bin_capacity", [])
        spend_vs_budget_trend: List[dict] = inventory_snap.get("spend_vs_budget_trend", [])
        procurement_spend_mtd = _safe_float(inventory_snap.get("procurement_spend_mtd"))
        procurement_spend_budget_mtd = _safe_float(inventory_snap.get("procurement_spend_budget_mtd"))

        open_po_count = _safe_float(po_snap.get("open_po_count"))
        open_po_value = _safe_float(po_snap.get("open_po_value"))
        po_pipeline: List[dict] = po_snap.get("po_pipeline", [])
        active_purchase_orders: List[dict] = po_snap.get("active_purchase_orders", [])
        executive_approval_queue: List[dict] = po_snap.get("executive_approval_queue", [])

        vendor_scorecard: List[dict] = vendor_snap.get("vendor_scorecard", [])
        vendor_spend_concentration: List[dict] = vendor_snap.get("vendor_spend_concentration", [])

        stock_movements: List[dict] = movement_snap.get("stock_movements", [])
        movement_type_distribution: List[dict] = movement_snap.get("movement_type_distribution", [])
        shrinkage_flag_items: List[dict] = movement_snap.get("shrinkage_flag_items", [])

        bridge_status: dict = bridge_snap.get("bridge_status", {"enabled": False, "provider": "None", "connected": False})
        po_bill_conversion_queue: List[dict] = bridge_snap.get("po_bill_conversion_queue", [])
        gl_valuation_reconciliation: List[dict] = bridge_snap.get("gl_valuation_reconciliation", [])

        risk_alerts: List[dict] = inventory_snap.get("risk_alerts", [])
    else:
        # ── LOAD FROM EXAMPLES/PROCUREMENT-MOCK.JSON ──
        json_path = pathlib.Path(__file__).resolve().parents[2] / "examples" / "procurement-mock.json"
        mock_data = {}
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    file_content = json.load(f)
                    mock_data = file_content.get("dashboard_mock", {})
            except Exception as e:
                logger.warning("Failed to load mock data from %s: %s", json_path, e)

        total_inventory_valuation = _safe_float(mock_data.get("totalInventoryValuation", 1850000.0))
        total_active_skus = _safe_float(mock_data.get("totalActiveSkus", 1248.0))
        low_stock_alerts = _safe_float(mock_data.get("lowStockAlerts", 7.0))
        dead_slow_stock_capital = _safe_float(mock_data.get("deadSlowStockCapital", 285000.0))
        open_po_count = _safe_float(mock_data.get("openPoCount", 14.0))
        open_po_value = _safe_float(mock_data.get("openPoValue", 412000.0))
        procurement_spend_mtd = _safe_float(mock_data.get("procurementSpendMtd", 348000.0))
        procurement_spend_budget_mtd = _safe_float(mock_data.get("procurementSpendBudgetMtd", 380000.0))

        risk_alerts = mock_data.get("riskAlerts", [])
        valuation_by_category = mock_data.get("valuationByCategory", [])
        spend_vs_budget_trend = mock_data.get("spendVsBudgetTrend", [])

        sku_catalog = mock_data.get("skuCatalog", [])
        dead_slow_stock = mock_data.get("deadSlowStock", [])
        warehouse_bin_capacity = mock_data.get("warehouseBinCapacity", [])

        stock_movements = mock_data.get("stockMovements", [])
        movement_type_distribution = mock_data.get("movementTypeDistribution", [])
        shrinkage_flag_items = mock_data.get("shrinkageFlagItems", [])

        po_pipeline = mock_data.get("poPipeline", [])
        active_purchase_orders = mock_data.get("activePurchaseOrders", [])
        executive_approval_queue = mock_data.get("executiveApprovalQueue", [])
        vendor_scorecard = mock_data.get("vendorScorecard", [])
        vendor_spend_concentration = mock_data.get("vendorSpendConcentration", [])

        bridge_status = mock_data.get("accountingBridge", {"enabled": False, "provider": "None", "connected": False})
        po_bill_conversion_queue = mock_data.get("poBillConversionQueue", [])
        gl_valuation_reconciliation = mock_data.get("glValuationReconciliation", [])

    return {
        # Tab 1 — Executive Procurement & Reorder Pulse
        "totalInventoryValuation": total_inventory_valuation,
        "totalActiveSkus": total_active_skus,
        "lowStockAlerts": low_stock_alerts,
        "deadSlowStockCapital": dead_slow_stock_capital,
        "openPoCount": open_po_count,
        "openPoValue": open_po_value,
        "procurementSpendMtd": procurement_spend_mtd,
        "procurementSpendBudgetMtd": procurement_spend_budget_mtd,
        "riskAlerts": risk_alerts,
        "valuationByCategory": valuation_by_category,
        "spendVsBudgetTrend": spend_vs_budget_trend,
        # Tab 2 — Inventory Catalog & Dead/Slow Stock
        "skuCatalog": sku_catalog,
        "deadSlowStock": dead_slow_stock,
        "warehouseBinCapacity": warehouse_bin_capacity,
        # Tab 3 — Stock Movement Audit Log
        "stockMovements": stock_movements,
        "movementTypeDistribution": movement_type_distribution,
        "shrinkageFlagItems": shrinkage_flag_items,
        # Tab 4 — Purchase Orders & Vendor Scorecard
        "poPipeline": po_pipeline,
        "activePurchaseOrders": active_purchase_orders,
        "executiveApprovalQueue": executive_approval_queue,
        "vendorScorecard": vendor_scorecard,
        "vendorSpendConcentration": vendor_spend_concentration,
        # Tab 5 — Accounting Bridge & Valuation Reconciliation
        "accountingBridge": bridge_status,
        "poBillConversionQueue": po_bill_conversion_queue,
        "glValuationReconciliation": gl_valuation_reconciliation,
    }


@router.get("/procurement-stats")
async def get_procurement_stats(
    name: str = Path(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Aggregated Procurement dashboard stats — all 5 tabs."""
    pages = await gbrain_fetch_pages("procurement", limit=300)
    return _run_procurement_aggregation(pages)