# Profile Dashboards Implementation Plan

> **For Hermes:** Use subagent-driven-development to implement this plan task-by-task.

**Goal:** Add profile-specific operational dashboards as a new tab in the Shogun OS web portal department view, starting with CRM.

**Architecture:** FastAPI backend proxies to gbrain MCP (local Postgres) for page data, aggregates stats server-side, and returns JSON to React. The new "Dashboard" tab replaces the "Reports" placeholder. Recharts is the standard charting library. A `DashboardViewer` generic wrapper resolves dept-specific dashboard components.

**Tech Stack:** FastAPI (Python), React/Vite (TypeScript), Recharts, Tailwind CSS, gbrain MCP HTTP

---

## Task 1: Install Recharts + Create Palette Utility

**Objective:** Add Recharts to Shogun web dependencies and create a utility for auto-generating chart color palettes from a base hue.

**Files:**
- Modify: `shogun-web/ui/package.json` (add recharts)
- Create: `shogun-web/ui/src/lib/palette.ts`

**Step 1: Install Recharts**

```bash
cd ~/shogun-os/shogun-web/ui && npm install recharts
```

Expected: Recharts appear in `package.json` dependencies.

**Step 2: Create palette utility**

```typescript
// shogun-web/ui/src/lib/palette.ts

/** Parse hex color to HSL. Returns [hue, saturation, lightness]. */
export function hexToHsl(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;

  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const l = (max + min) / 2;

  if (max === min) return [0, 0, Math.round(l * 100)];

  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);

  let h = 0;
  switch (max) {
    case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
    case g: h = ((b - r) / d + 2) / 6; break;
    case b: h = ((r - g) / d + 4) / 6; break;
  }

  return [Math.round(h * 360), Math.round(s * 100), Math.round(l * 100)];
}

/** Generate N visually distinct colors by stepping hue around the base. */
export function generatePalette(baseColor: string, count: number): string[] {
  if (count <= 1) return [baseColor];

  const [h, s, l] = hexToHsl(baseColor);
  const step = 360 / count;
  const palette: string[] = [];

  for (let i = 0; i < count; i++) {
    const hue = (h + i * step) % 360;
    palette.push(`hsl(${Math.round(hue)}, ${Math.max(40, s)}%, ${Math.max(45, Math.min(65, l))}%)`);
  }

  return palette;
}

/** Return a single chart color (base) or palette (multi). */
export function chartColors(baseColor: string, count: number): string[] {
  return count > 1 ? generatePalette(baseColor, count) : [baseColor];
}
```

**Step 3: Verify**

```bash
cd ~/shogun-os/shogun-web/ui && npx tsc --noEmit --strict src/lib/palette.ts 2>&1
```

Expected: No type errors.

**Step 4: Commit**

```bash
cd ~/shogun-os && git add shogun-web/ui/package.json shogun-web/ui/package-lock.json shogun-web/ui/src/lib/palette.ts
git commit -m "feat: add recharts + palette utility for profile dashboards"
```

---

## Task 2: Create Shared gbrain HTTP Client

**Objective:** Extract gbrain MCP HTTP proxy logic into a reusable utility that both brain viewer and dashboard endpoints can use.

**Files:**
- Create: `shogun-web/server/gbrain_client.py`

**Step 1: Write gbrain_client.py**

```python
"""Shared HTTP client for gbrain MCP. Used by brain, docs, and dashboard endpoints."""
from __future__ import annotations

import logging
from typing import Any, List, Optional

import httpx
from config import get_config

logger = logging.getLogger(__name__)


async def gbrain_fetch_pages(
    source: str,
    *,
    limit: int = 200,
    slug_prefix: Optional[str] = None,
) -> List[dict[str, Any]]:
    """Fetch pages from gbrain for a given source, optionally filtered by slug prefix."""
    cfg = get_config()
    base = cfg.gbrain_base_url.rstrip("/")
    params = {"source_id": source, "limit": str(min(limit, 500))}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{base}/api/pages", params=params)
            if resp.status_code >= 400:
                logger.warning("gbrain /api/pages returned %s: %s", resp.status_code, resp.text[:300])
                return []
            payload = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("gbrain fetch pages error for %s: %s", source, exc)
        return []

    # gbrain may wrap pages in a nested key
    raw_pages: List[dict] = []
    if isinstance(payload, list):
        raw_pages = payload
    elif isinstance(payload, dict):
        raw_pages = payload.get("pages") or payload.get("data") or payload.get("results") or []

    if slug_prefix:
        raw_pages = [p for p in raw_pages if str(p.get("slug", "")).startswith(slug_prefix)]

    return raw_pages


async def gbrain_fetch_page(source: str, slug: str) -> Optional[dict[str, Any]]:
    """Fetch a single page from gbrain."""
    cfg = get_config()
    base = cfg.gbrain_base_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base}/api/pages/{slug}", params={"source_id": source})
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                return None
            logger.warning("gbrain /api/pages/%s returned %s", slug, resp.status_code)
            return None
    except httpx.HTTPError as exc:
        logger.warning("gbrain fetch page error %s/%s: %s", source, slug, exc)
        return None


async def gbrain_search(
    source: str,
    query: str,
    limit: int = 20,
) -> List[dict[str, Any]]:
    """Search gbrain pages for a source."""
    cfg = get_config()
    base = cfg.gbrain_base_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{base}/api/search",
                json={"query": query, "source_id": source, "limit": limit},
            )
            if resp.status_code >= 400:
                return []
            payload = resp.json()
            if isinstance(payload, list):
                return payload
            return payload.get("results") or payload.get("pages") or []
    except httpx.HTTPError as exc:
        logger.warning("gbrain search error for %s: %s", source, exc)
        return []
```

**Step 2: Commit**

```bash
cd ~/shogun-os && git add shogun-web/server/gbrain_client.py
git commit -m "feat: add shared gbrain HTTP client for dashboard/brain endpoints"
```

---

## Task 3: Create Dashboard Router (Backend)

**Objective:** Create FastAPI dashboard endpoint with CEO stats aggregation for CRM.

**Files:**
- Create: `shogun-web/server/dashboard.py`

**Step 1: Write dashboard.py**

```python
"""Department dashboard endpoints — aggregates data via gbrain MCP."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db, get_primary_tenant
from gbrain_client import gbrain_fetch_pages
from models import Department, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/departments/{name}/dashboard", tags=["dashboard"])

# ─── Canonicalization helpers ───

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
    # Fuzzy match
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
        import re
        if re.search(pattern, text):
            return product
    return "Uncategorised"


def _month_key(iso_str: str) -> str:
    return iso_str[:7] if len(iso_str) >= 7 else iso_str


# ─── Aggregation types ───

class OwnerAccum:
    __slots__ = ("salesMTD", "salesQTD", "salesYTD", "deals", "wonDeals",
                 "pipelineValue", "weightedPipeline", "closeThisMonth", "closeThisQ",
                 "closeNextQ", "closeThisYear", "winNum", "winDen")
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

    # CRM gets the CEO dashboard; other departments can be added later
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
    """Aggregated CEO dashboard stats for CRM — port of crm-dashboard/app/api/deals/ceo-stats/route.ts."""
    pages = await gbrain_fetch_pages("crm", limit=200)

    # Filter to deal pages
    deals = [p for p in pages if p.get("slug", "").startswith("deals/")]
    deals = [p for p in deals if not any(
        x in p["slug"] for x in ["templates/", "readme", "_schema", "activity-log", "risk-register"]
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
        if d.year != cy: return d.year == cy + 1 and cq == 3
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
        owner = _canonical_owner(fm.get("owner", ""))
        partner = str(fm.get("partner", "")).strip() if fm.get("partner") else None
        priority = str(fm.get("priority", "Medium"))
        close_date = str(fm.get("close_date", ""))
        hot = fm.get("hot") in ("Yes", True)

        won = stage in WON_STAGES
        lost = stage in LOST_STAGES
        active = stage in ACTIVE_STAGES

        # Owner accum init
        if owner not in owner_map:
            owner_map[owner] = OwnerAccum()
        om = owner_map[owner]

        # Revenue (won)
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

        # Active deals
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
                if _is_this_month(close_date): om.closeThisMonth += amount
                if _is_this_quarter(close_date): om.closeThisQ += amount
                if _is_next_quarter(close_date): om.closeNextQ += amount
                if _is_this_year(close_date): om.closeThisYear += amount

            if hot:
                hotDeals += 1
            elif priority == "High":
                warmDeals += 1
            else:
                coldDeals += 1

            # At-risk
            days_in_stage = _days_since(fm.get("created") or close_date or now.isoformat())
            if days_in_stage > 30:
                ar = at_risk_by_owner.setdefault(owner, {"count": 0, "value": 0})
                ar["count"] += 1
                ar["value"] += amount
                if partner:
                    arp = at_risk_by_partner.setdefault(partner, {"count": 0, "value": 0})
                    arp["count"] += 1
                    arp["value"] += amount

        # Win rate
        if won or lost:
            om.winDen += 1
            if won: om.winNum += 1

        # Partner
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
                if won: pm.winNum += 1

            mk = f"{owner}|{partner}"
            mm = matrix_map.setdefault(mk, {"owner": owner, "partner": partner, "deals": 0})
            mm["deals"] += 1

            # Partner-owner cross counts
            poc = partner_owner_counts.setdefault(partner, {})
            poc[owner] = poc.get(owner, 0) + 1

        # Product
        product = fm.get("product") or _infer_product(title, slug)
        pe = product_map.setdefault(product, {"value": 0.0, "count": 0})
        pe["count"] += 1
        if amount > 0:
            pe["value"] += amount

        # Stage
        se = stage_map.setdefault(stage, {"count": 0.0, "value": 0.0})
        se["count"] += 1
        if amount > 0:
            se["value"] += amount

        # Monthly
        if close_date:
            mk = _month_key(close_date)
            if won and amount > 0:
                won_month_map[mk] = won_month_map.get(mk, 0) + amount
            if won or active:
                month_map[mk] = month_map.get(mk, 0) + amount

        # Priority
        priority_map[priority] = priority_map.get(priority, 0) + 1

        # Top deals
        is_early = stage in ("Lead", "Prospecting", "Qualified")
        if amount > 0 and active and stage != "Unqualified" and stage != "On Hold" and (not is_early or amount > 0):
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

    # ── Assemble response ──

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
        [{"owner": o, "atRiskDeals": v["count"], "atRiskValue": v["value"]} for o, v in at_risk_by_owner.items()],
        key=lambda x: -x["atRiskValue"],
    )

    at_risk_by_partner_result = sorted(
        [
            {
                "partner": p, "atRiskDeals": v["count"], "atRiskValue": v["value"],
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
        "salesMTD": salesMTD, "salesQTD": salesQTD, "salesYTD": salesYTD,
        "totalPipelineValue": totalPipelineValue,
        "weightedPipelineValue": weightedPipelineValue,
        "pipelineCoverage": pipeline_coverage,
        "winRate": round(total_win_num / total_win_den * 100) if total_win_den > 0 else 0,
        "avgDealSize": avg_deal_size,
        "salesCycleDays": 47,
        "totalActiveDeals": totalActiveDeals,
        "hotDeals": hotDeals, "warmDeals": warmDeals, "coldDeals": coldDeals,
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
```

**Step 2: Verify Python syntax**

```bash
cd ~/shogun-os && python3 -c "import ast; ast.parse(open('shogun-web/server/dashboard.py').read()); print('OK')"
```

Expected: "OK"

**Step 3: Commit**

```bash
cd ~/shogun-os && git add shogun-web/server/dashboard.py
git commit -m "feat: add dashboard router with CRM CEO stats aggregation"
```

---

## Task 4: Register Dashboard Router in main.py

**Objective:** Wire the new dashboard router into the FastAPI app.

**Files:**
- Modify: `shogun-web/server/main.py`

**Step 1: Add import and router registration**

In `main.py`, add import alongside existing domain imports:

```python
import dashboard  # NEW
```

After `app.include_router(registry.router)`, add:

```python
app.include_router(dashboard.router)
```

**Step 2: Verify syntax**

```bash
cd ~/shogun-os && python3 -m py_compile shogun-web/server/main.py
```

Expected: No errors.

**Step 3: Commit**

```bash
cd ~/shogun-os && git add shogun-web/server/main.py
git commit -m "feat: register dashboard router in FastAPI app"
```

---

## Task 5: Add Frontend Types and API Methods

**Objective:** Add `DashboardConfig`, `CeoDashboardStats`, and related types to the frontend, plus API methods.

**Files:**
- Modify: `shogun-web/ui/src/lib/types.ts`
- Modify: `shogun-web/ui/src/lib/api.ts`

**Step 1: Add types to types.ts**

Append before the final `TIMEZONES` export:

```typescript
// ─── Dashboard Types ───

export interface DashboardTab {
  id: string;
  label: string;
  icon: string;
}

export interface DashboardConfig {
  enabled: boolean;
  tabs: DashboardTab[];
}

export interface ManagerEntry {
  owner: string;
  salesMTD: number;
  salesQTD: number;
  salesYTD: number;
  deals: number;
  wonDeals: number;
  pipelineValue: number;
  weightedPipeline: number;
  closeThisMonth: number;
  closeThisQ: number;
  closeNextQ: number;
  closeThisYear: number;
  winRate: number;
}

export interface PartnerStatsEntry {
  partner: string;
  booking: number;
  dealsWon: number;
  pipelineDeals: number;
  pipelineValue: number;
  winRate: number;
  avgDealSize: number;
  primaryOwner: string;
}

export interface FunnelEntry {
  stage: string;
  count: number;
  value: number;
}

export interface MonthEntry {
  month: string;
  value: number;
}

export interface PriorityEntry {
  priority: string;
  count: number;
}

export interface ProductEntry {
  product: string;
  value: number;
  count: number;
}

export interface ManagerRiskEntry {
  owner: string;
  atRiskDeals: number;
  atRiskValue: number;
}

export interface PartnerRiskEntry {
  partner: string;
  atRiskDeals: number;
  atRiskValue: number;
  primaryOwner: string;
}

export interface DealRow {
  slug: string;
  title: string;
  customer: string;
  amount: number;
  stage: string;
  priority: string;
  owner: string;
  partner: string | null;
  closeDate: string;
  winProbability: number;
  daysInStage: number;
  hot: boolean;
}

export interface CeoDashboardStats {
  salesMTD: number;
  salesQTD: number;
  salesYTD: number;
  totalPipelineValue: number;
  weightedPipelineValue: number;
  pipelineCoverage: number;
  winRate: number;
  avgDealSize: number;
  salesCycleDays: number;
  totalActiveDeals: number;
  hotDeals: number;
  warmDeals: number;
  coldDeals: number;
  wonDeals: number;
  byManager: ManagerEntry[];
  byPartner: PartnerStatsEntry[];
  byStage: FunnelEntry[];
  byMonth: MonthEntry[];
  byPriority: PriorityEntry[];
  wonByMonth: MonthEntry[];
  byProduct: ProductEntry[];
  atRiskByManager: ManagerRiskEntry[];
  atRiskByPartner: PartnerRiskEntry[];
  byManagerByPartner: { owner: string; partner: string; deals: number }[];
  topDeals: DealRow[];
}
```

Also extend the `Department` interface (optional — for future use):

```typescript
export interface Department {
  // ... existing fields unchanged ...
  dashboard?: DashboardConfig;
}
```

**Step 2: Add API methods to api.ts**

Add to `departmentsApi`:

```typescript
export const departmentsApi = {
  // ... existing methods unchanged ...

  dashboardConfig: (name: string) =>
    apiFetch<DashboardConfig>(`/api/departments/${name}/dashboard`),

  dashboardCeoStats: (dept: string) =>
    apiFetch<CeoDashboardStats>(`/api/departments/${dept}/dashboard/ceo-stats`),
};
```

**Step 3: Verify TypeScript**

```bash
cd ~/shogun-os/shogun-web/ui && npx tsc --noEmit 2>&1 | head -30
```

Expected: No type errors.

**Step 4: Commit**

```bash
cd ~/shogun-os && git add shogun-web/ui/src/lib/types.ts shogun-web/ui/src/lib/api.ts
git commit -m "feat: add dashboard types and API methods"
```

---

## Task 6: Create Shared Chart Wrappers (Recharts)

**Objective:** Build thin Recharts wrappers that enforce Shogun design tokens.

**Files:**
- Create: `shogun-web/ui/src/components/dashboards/charts/BarChart.tsx`
- Create: `shogun-web/ui/src/components/dashboards/charts/LineChart.tsx`
- Create: `shogun-web/ui/src/components/dashboards/charts/PieChart.tsx`
- Create: `shogun-web/ui/src/components/dashboards/charts/FunnelChart.tsx`
- Create: `shogun-web/ui/src/components/dashboards/charts/index.ts`

**Step 1: Create index (barrel export)**

```typescript
// shogun-web/ui/src/components/dashboards/charts/index.ts
export { BarChart } from './BarChart';
export { LineChart } from './LineChart';
export { PieChart } from './PieChart';
export { FunnelChart } from './FunnelChart';
```

**Step 2: Create BarChart wrapper**

```typescript
// shogun-web/ui/src/components/dashboards/charts/BarChart.tsx
import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { chartColors } from '../../../lib/palette';

interface BarChartProps {
  data: Record<string, unknown>[];
  xKey: string;
  yKey: string;
  color?: string;
  colors?: string[];
  unit?: string;
  height?: number;
  stacked?: boolean;
  onClick?: (entry: Record<string, unknown>) => void;
  dataKeys?: string[]; // for stacked/multi-series
}

export function BarChart({
  data, xKey, yKey, color = '#6366f1', colors, unit = '',
  height = 250, stacked = false, onClick, dataKeys,
}: BarChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-full min-h-[200px] items-center justify-center rounded-xl border border-dashed border-slate-200 text-sm text-slate-400">
        No data
      </div>
    );
  }

  const palette = colors || chartColors(color, dataKeys?.length || 1);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsBarChart data={data as Record<string, number>[]}
        margin={{ top: 5, right: 5, left: -10, bottom: 5 }}
        onClick={(e) => { if (e?.activePayload?.[0]?.payload) onClick?.(e.activePayload[0].payload); }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false}
          tickFormatter={(v: number) => unit ? `${unit}${v.toLocaleString()}` : v.toLocaleString()}
        />
        <Tooltip
          contentStyle={{
            background: '#fff', border: '1px solid #e2e8f0',
            borderRadius: '8px', fontSize: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          }}
          formatter={(value: number) => [unit ? `${unit}${value.toLocaleString()}` : value.toLocaleString()]}
        />
        {dataKeys && dataKeys.length > 0
          ? dataKeys.map((k, i) => (
              <Bar key={k} dataKey={k} fill={palette[i % palette.length]}
                stackId={stacked ? 'stack' : undefined}
                radius={[3, 3, 0, 0]}
              />
            ))
          : <Bar dataKey={yKey} fill={palette[0]} radius={[3, 3, 0, 0]} />
        }
      </RechartsBarChart>
    </ResponsiveContainer>
  );
}
```

**Step 3: Create LineChart wrapper**

```typescript
// shogun-web/ui/src/components/dashboards/charts/LineChart.tsx
import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { chartColors } from '../../../lib/palette';

interface LineChartProps {
  data: Record<string, unknown>[];
  xKey: string;
  yKey: string;
  color?: string;
  colors?: string[];
  unit?: string;
  height?: number;
  dataKeys?: string[];
}

export function LineChart({
  data, xKey, yKey, color = '#6366f1', colors, unit = '', height = 250, dataKeys,
}: LineChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-full min-h-[200px] items-center justify-center rounded-xl border border-dashed border-slate-200 text-sm text-slate-400">
        No data
      </div>
    );
  }

  const palette = colors || chartColors(color, dataKeys?.length || 1);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsLineChart data={data as Record<string, number>[]}
        margin={{ top: 5, right: 5, left: -10, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false}
          tickFormatter={(v: number) => unit ? `${unit}${v.toLocaleString()}` : v.toLocaleString()}
        />
        <Tooltip
          contentStyle={{
            background: '#fff', border: '1px solid #e2e8f0',
            borderRadius: '8px', fontSize: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          }}
          formatter={(value: number) => [unit ? `${unit}${value.toLocaleString()}` : value.toLocaleString()]}
        />
        {dataKeys && dataKeys.length > 0
          ? dataKeys.map((k, i) => (
              <Line key={k} type="monotone" dataKey={k} stroke={palette[i % palette.length]}
                strokeWidth={2} dot={{ r: 3 }} connectNulls
              />
            ))
          : <Line type="monotone" dataKey={yKey} stroke={palette[0]} strokeWidth={2} dot={{ r: 3 }} />
        }
      </RechartsLineChart>
    </ResponsiveContainer>
  );
}
```

**Step 4: Create PieChart wrapper**

```typescript
// shogun-web/ui/src/components/dashboards/charts/PieChart.tsx
import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { chartColors } from '../../../lib/palette';

interface PieChartProps {
  data: { name: string; value: number }[];
  color?: string;
  colors?: string[];
  unit?: string;
  height?: number;
  innerRadius?: number;
  showLegend?: boolean;
}

export function PieChart({
  data, color = '#6366f1', colors, unit = '', height = 250,
  innerRadius = 50, showLegend = true,
}: PieChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-full min-h-[200px] items-center justify-center rounded-xl border border-dashed border-slate-200 text-sm text-slate-400">
        No data
      </div>
    );
  }

  const palette = colors || chartColors(color, data.length);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsPieChart>
        <Pie data={data} cx="50%" cy="50%" innerRadius={innerRadius} outerRadius={80}
          dataKey="value" paddingAngle={2}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={palette[i % palette.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            background: '#fff', border: '1px solid #e2e8f0',
            borderRadius: '8px', fontSize: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          }}
          formatter={(value: number) => [unit ? `${unit}${value.toLocaleString()}` : value.toLocaleString()]}
        />
        {showLegend && <Legend />}
      </RechartsPieChart>
    </ResponsiveContainer>
  );
}
```

**Step 5: Create FunnelChart wrapper**

```typescript
// shogun-web/ui/src/components/dashboards/charts/FunnelChart.tsx
import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from 'recharts';
import { chartColors } from '../../../lib/palette';
import type { FunnelEntry } from '../../../lib/types';

interface FunnelChartProps {
  data: FunnelEntry[];
  color?: string;
  colors?: string[];
  unit?: string;
  height?: number;
  valueKey?: 'value' | 'count';
}

export function FunnelChart({
  data, color = '#6366f1', colors, unit = '', height = 280, valueKey = 'value',
}: FunnelChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-full min-h-[200px] items-center justify-center rounded-xl border border-dashed border-slate-200 text-sm text-slate-400">
        No data
      </div>
    );
  }

  const palette = colors || chartColors(color, Math.max(3, data.length));
  // Make funnel progressively lighter
  const funnelColors = palette.map((_, i) => {
    const base = palette[i % palette.length];
    // Lighten: adjust lightness by position
    return base;
  });

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsBarChart data={data as Record<string, number>[]}
        layout="vertical"
        margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false}
          tickFormatter={(v: number) => unit ? `${unit}${v.toLocaleString()}` : v.toLocaleString()}
        />
        <YAxis type="category" dataKey="stage" tick={{ fontSize: 11, fill: '#64748b' }}
          axisLine={false} tickLine={false} width={100}
        />
        <Tooltip
          contentStyle={{
            background: '#fff', border: '1px solid #e2e8f0',
            borderRadius: '8px', fontSize: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          }}
          formatter={(value: number) => [unit ? `${unit}${value.toLocaleString()}` : value.toLocaleString()]}
        />
        <Bar dataKey={valueKey} radius={[0, 4, 4, 0]} maxBarSize={36}>
          {data.map((_, i) => (
            <Cell key={i} fill={funnelColors[i % funnelColors.length]}
              fillOpacity={1 - (i * 0.08)}
            />
          ))}
        </Bar>
      </RechartsBarChart>
    </ResponsiveContainer>
  );
}
```

**Step 6: Verify TypeScript**

```bash
cd ~/shogun-os/shogun-web/ui && npx tsc --noEmit 2>&1 | head -30
```

Expected: No type errors.

**Step 7: Commit**

```bash
cd ~/shogun-os && git add shogun-web/ui/src/components/dashboards/charts/
git commit -m "feat: add shared Recharts chart wrappers with Shogun design tokens"
```

---

## Task 7: Create DashboardViewer + DashboardSubNav

**Objective:** Build the generic dashboard viewer wrapper and sub-tab navigation component.

**Files:**
- Create: `shogun-web/ui/src/components/dashboards/DashboardViewer.tsx`
- Create: `shogun-web/ui/src/components/dashboards/DashboardSubNav.tsx`

**Step 1: Create DashboardSubNav**

```typescript
// shogun-web/ui/src/components/dashboards/DashboardSubNav.tsx
import { type LucideIcon } from 'lucide-react';
import clsx from 'clsx';
import type { DashboardTab } from '../../lib/types';

const iconMap: Record<string, LucideIcon | null> = {};
// Dynamic import won't work — lazy import icons at usage site; for now pass icon as string

interface DashboardSubNavProps {
  tabs: DashboardTab[];
  active: string;
  onChange: (id: string) => void;
}

export function DashboardSubNav({ tabs, active, onChange }: DashboardSubNavProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={clsx(
            'shrink-0 flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-medium transition-all whitespace-nowrap',
            active === tab.id
              ? 'bg-brand text-white shadow-sm'
              : 'bg-white text-slate-500 border border-surface-border hover:border-slate-300',
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
```

**Step 2: Create DashboardViewer**

```typescript
// shogun-web/ui/src/components/dashboards/DashboardViewer.tsx
import { useQuery } from '@tanstack/react-query';
import { BarChart3 } from 'lucide-react';
import { departmentsApi } from '../../lib/api';
import type { DashboardConfig, DepartmentKey } from '../../lib/types';
import { CrmDashboard } from './crm/CrmDashboard';

const DASHBOARD_COMPONENTS: Record<string, React.ComponentType<{ department: string; color: string }>> = {
  crm: CrmDashboard,
  // future: marketing: MarketingDashboard, etc.
};

interface DashboardViewerProps {
  department: string;
  color: string;
}

export function DashboardViewer({ department, color }: DashboardViewerProps) {
  const configQuery = useQuery({
    queryKey: ['dashboard-config', department],
    queryFn: () => departmentsApi.dashboardConfig(department),
  });

  if (configQuery.isLoading) {
    return (
      <div className="flex justify-center py-16 text-slate-400">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  const config: DashboardConfig | undefined = configQuery.data;
  const DashboardComponent = DASHBOARD_COMPONENTS[department];

  if (!config?.enabled || !DashboardComponent) {
    return (
      <div className="flex min-h-[28rem] flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white text-center">
        <BarChart3 className="mb-3 h-10 w-10 text-slate-300" />
        <h2 className="text-lg font-semibold text-slate-800">Dashboard</h2>
        <p className="mt-1 max-w-sm text-sm text-slate-500">
          No dashboard configured for this department yet.
        </p>
      </div>
    );
  }

  return <DashboardComponent department={department} color={color} />;
}
```

**Step 3: Verify TypeScript**

```bash
cd ~/shogun-os/shogun-web/ui && npx tsc --noEmit 2>&1 | head -30
```

Expected: No type errors.

**Step 4: Commit**

```bash
cd ~/shogun-os && git add shogun-web/ui/src/components/dashboards/DashboardViewer.tsx shogun-web/ui/src/components/dashboards/DashboardSubNav.tsx
git commit -m "feat: add DashboardViewer generic wrapper and sub-tab nav"
```

---

## Task 8: Create CRM Dashboard Sub-Tabs

**Objective:** Build the 5 CRM dashboard sub-tabs that render CEO stats.

**Files:**
- Create: `shogun-web/ui/src/components/dashboards/crm/CrmDashboard.tsx`
- Create: `shogun-web/ui/src/components/dashboards/crm/SalesPulseTab.tsx`
- Create: `shogun-web/ui/src/components/dashboards/crm/PipelineForecastTab.tsx`
- Create: `shogun-web/ui/src/components/dashboards/crm/PartnerPerformanceTab.tsx`
- Create: `shogun-web/ui/src/components/dashboards/crm/ManagerPerformanceTab.tsx`
- Create: `shogun-web/ui/src/components/dashboards/crm/DealsDeepDiveTab.tsx`
- Create: `shogun-web/ui/src/components/dashboards/crm/ManagerDrillDownModal.tsx`

**Step 1: Create CrmDashboard (parent)**

```typescript
// shogun-web/ui/src/components/dashboards/crm/CrmDashboard.tsx
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { departmentsApi } from '../../../lib/api';
import { DashboardSubNav } from '../DashboardSubNav';
import type { CeoDashboardStats, DashboardTab } from '../../../lib/types';
import { SalesPulseTab } from './SalesPulseTab';
import { PipelineForecastTab } from './PipelineForecastTab';
import { PartnerPerformanceTab } from './PartnerPerformanceTab';
import { ManagerPerformanceTab } from './ManagerPerformanceTab';
import { DealsDeepDiveTab } from './DealsDeepDiveTab';

const TABS: DashboardTab[] = [
  { id: 'revenue', label: 'Sales Booking', icon: 'LayoutDashboard' },
  { id: 'pipeline', label: 'Pipeline & Forecast', icon: 'TrendingUp' },
  { id: 'partner', label: 'Partner Performance', icon: 'Handshake' },
  { id: 'managers', label: 'Manager Performance', icon: 'Users' },
  { id: 'deals', label: 'Deals Deep-Dive', icon: 'Target' },
];

interface CrmDashboardProps {
  department: string;
  color: string;
}

export function CrmDashboard({ department, color }: CrmDashboardProps) {
  const [activeTab, setActiveTab] = useState('revenue');
  const [drillDownOwner, setDrillDownOwner] = useState<string | null>(null);

  const statsQuery = useQuery({
    queryKey: ['dashboard-ceo-stats', department],
    queryFn: () => departmentsApi.dashboardCeoStats(department),
    refetchInterval: 120_000, // refresh every 2 min
  });

  if (statsQuery.isLoading) {
    return (
      <div className="flex justify-center py-16 text-slate-400">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  const stats: CeoDashboardStats | undefined = statsQuery.data;

  if (!stats) {
    return (
      <div className="flex min-h-[20rem] flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white text-center">
        <p className="text-sm text-slate-500">Unable to load dashboard data.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <DashboardSubNav tabs={TABS} active={activeTab} onChange={setActiveTab} />

      {drillDownOwner && (
        <ManagerDrillDownModal
          owner={drillDownOwner}
          onClose={() => setDrillDownOwner(null)}
          department={department}
          color={color}
        />
      )}

      {activeTab === 'revenue' && <SalesPulseTab stats={stats} color={color} />}
      {activeTab === 'pipeline' && <PipelineForecastTab stats={stats} color={color} />}
      {activeTab === 'partner' && <PartnerPerformanceTab stats={stats} color={color} />}
      {activeTab === 'managers' && (
        <ManagerPerformanceTab stats={stats} color={color} onDrillDown={setDrillDownOwner} />
      )}
      {activeTab === 'deals' && <DealsDeepDiveTab stats={stats} color={color} />}
    </div>
  );
}
```

**Step 2-6: Create each sub-tab**

Each sub-tab follows this pattern — receives `stats: CeoDashboardStats` and `color: string`, renders KPI cards and charts using the shared chart wrappers.

```typescript
// shogun-web/ui/src/components/dashboards/crm/SalesPulseTab.tsx
import { BarChart, LineChart } from '../charts';
import type { CeoDashboardStats } from '../../../lib/types';

interface Props { stats: CeoDashboardStats; color: string }

export function SalesPulseTab({ stats, color }: Props) {
  const KPIs = [
    { label: 'Sales MTD', value: `RM ${(stats.salesMTD / 1000).toFixed(0)}K` },
    { label: 'Sales QTD', value: `RM ${(stats.salesQTD / 1000).toFixed(0)}K` },
    { label: 'Sales YTD', value: `RM ${(stats.salesYTD / 1000).toFixed(0)}K` },
    { label: 'Win Rate', value: `${stats.winRate}%` },
    { label: 'Avg Deal', value: `RM ${(stats.avgDealSize / 1000).toFixed(0)}K` },
    { label: 'Active Deals', value: stats.totalActiveDeals.toString() },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {KPIs.map((kpi) => (
          <div key={kpi.label} className="card p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{kpi.label}</div>
            <div className="mt-1 text-xl font-bold text-slate-900">{kpi.value}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Sales by Manager (YTD)</h3>
          <BarChart
            data={stats.byManager}
            xKey="owner"
            yKey="salesYTD"
            color={color}
            unit="RM "
            height={220}
          />
        </div>
        <div className="card p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Monthly Sales Trend</h3>
          <LineChart
            data={stats.wonByMonth}
            xKey="month"
            yKey="value"
            color={color}
            unit="RM "
            height={220}
          />
        </div>
      </div>
    </div>
  );
}
```

Similar patterns for:

- **PipelineForecastTab** — funnel chart, monthly pipeline trend, weighted pipeline, pipeline coverage
- **PartnerPerformanceTab** — partner leaderboard (bar chart), partner x manager matrix
- **ManagerPerformanceTab** — manager comparison bars, at-risk deals table, manager list with drill-down via `onDrillDown`
- **DealsDeepDiveTab** — top deals table, priority distribution (pie), product breakdown, hot/warm/cold chips

**Step 7: Create ManagerDrillDownModal**

```typescript
// Modal overlay showing per-manager detailed stats using the shared chart wrappers
// Triggered by clicking a manager row in ManagerPerformanceTab
// Closes via backdrop click or X button
```

The modal should fetch manager-specific data when opened (for future: `GET /api/departments/crm/dashboard/manager/{owner}`) or just display the top deals / at-risk data for that owner filtered from the existing stats.

For Phase 1, the modal can show filtered data from `stats.atRiskByManager` and `stats.topDeals` filtered by owner. Phase 2 adds the dedicated backend endpoint.

**Step 8: Verify TypeScript**

```bash
cd ~/shogun-os/shogun-web/ui && npx tsc --noEmit 2>&1 | head -60
```

Expected: No type errors.

**Step 9: Commit**

```bash
cd ~/shogun-os && git add shogun-web/ui/src/components/dashboards/crm/
git commit -m "feat: add CRM dashboard with 5 sub-tabs"
```

---

## Task 9: Wire Dashboard Tab in Department.tsx

**Objective:** Replace the "Reports" placeholder tab with the "Dashboard" tab in the department view.

**Files:**
- Modify: `shogun-web/ui/src/pages/Department.tsx`

**Step 1: Update imports**

```typescript
// Replace BarChart3 import with:
import { BarChart3 } from 'lucide-react';
// Add DashboardViewer import
import { DashboardViewer } from '../components/dashboards/DashboardViewer';
```

**Step 2: Update TABS array**

```typescript
const TABS = [
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'brain', label: 'Brain', icon: Brain },
  { id: 'docs', label: 'Docs', icon: FileText },
  { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },  // was 'reports'
  { id: 'settings', label: 'Settings', icon: Settings },
] as const;
```

**Step 3: Replace the Reports render block**

Replace this:

```typescript
{!deptQuery.isLoading && tab === 'reports' && (
  <div className="flex min-h-[28rem] flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white text-center">
    <BarChart3 className="mb-3 h-10 w-10 text-slate-300" />
    <h2 className="text-lg font-semibold text-slate-800">Reports</h2>
    <p className="mt-1 max-w-sm text-sm text-slate-500">Coming soon</p>
  </div>
)}
```

With:

```typescript
{!deptQuery.isLoading && tab === 'dashboard' && (
  <DashboardViewer department={key} color={color} />
)}
```

**Step 4: Verify TypeScript**

```bash
cd ~/shogun-os/shogun-web/ui && npx tsc --noEmit 2>&1 | head -20
```

Expected: No type errors.

**Step 5: Commit**

```bash
cd ~/shogun-os && git add shogun-web/ui/src/pages/Department.tsx
git commit -m "feat: wire Dashboard tab replacing Reports placeholder"
```

---

## Task 10: End-to-End Verification

**Objective:** Verify the entire feature works end-to-end.

**Step 1: Build the SPA**

```bash
cd ~/shogun-os/shogun-web/ui && npm run build
```

Expected: Vite build succeeds without errors.

**Step 2: Check backend syntax**

```bash
cd ~/shogun-os && python3 -c "
import ast
for f in ['shogun-web/server/dashboard.py', 'shogun-web/server/gbrain_client.py', 'shogun-web/server/main.py']:
    ast.parse(open(f).read())
    print(f'{f}: OK')
"
```

Expected: All 3 files parse.

**Step 3: Start the backend + verify health**

```bash
cd ~/shogun-os/shogun-web/server && python3 -m main &
sleep 2
curl -s http://localhost:8787/api/health | python3 -m json.tool
```

Expected: `{"ok": true, "service": "shogun-web", ...}`

**Step 4: Test dashboard config endpoint**

```bash
curl -s http://localhost:8787/api/departments/crm/dashboard \
  -H "Authorization: Bearer $(curl -s http://localhost:8787/api/auth/login -X POST -H 'Content-Type: application/json' -d '{"email":"admin","password":"admin"}' | python3 -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))")" \
  | python3 -m json.tool
```

Expected: `{"enabled": true, "tabs": [...]}`

**Step 5: Test CEO stats endpoint**

```bash
curl -s http://localhost:8787/api/departments/crm/dashboard/ceo-stats \
  -H "Authorization: Bearer <token>" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'Active deals: {d.get(\"totalActiveDeals\",0)}, Managers: {len(d.get(\"byManager\",[]))}')"
```

Expected: Shows active deal count and manager count.

**Step 6: Frontend visual check**

Open browser to `http://localhost:8787/department/crm?tab=dashboard`. Expected:
- Sidebar shows CRM department
- Dashboard tab is active
- Sub-tab pills show: Sales Booking, Pipeline & Forecast, etc.
- Clicking each tab switches content
- KPI cards and charts render with data

**Step 7: Stop background server**

```bash
kill %1 2>/dev/null; pkill -f "uvicorn" 2>/dev/null; true
```

---

## Summary of Files

| # | Action | File | Description |
|---|---|---|---|
| 1 | Install | `package.json` | Add `recharts` |
| 2 | Create | `ui/src/lib/palette.ts` | Color palette utility |
| 3 | Create | `server/gbrain_client.py` | Shared gbrain HTTP client |
| 4 | Create | `server/dashboard.py` | Dashboard router + CRM CEO stats |
| 5 | Modify | `server/main.py` | Register dashboard router |
| 6 | Modify | `ui/src/lib/types.ts` | Add `CeoDashboardStats` and related types |
| 7 | Modify | `ui/src/lib/api.ts` | Add `dashboardConfig`, `dashboardCeoStats` |
| 8 | Create | `ui/src/components/dashboards/charts/*.tsx` | 4 chart wrappers + barrel export |
| 9 | Create | `ui/src/components/dashboards/DashboardViewer.tsx` | Generic wrapper |
| 10 | Create | `ui/src/components/dashboards/DashboardSubNav.tsx` | Sub-tab navigation |
| 11 | Create | `ui/src/components/dashboards/crm/CrmDashboard.tsx` | CRM parent |
| 12 | Create | `ui/src/components/dashboards/crm/SalesPulseTab.tsx` | Sub-tab |
| 13 | Create | `ui/src/components/dashboards/crm/PipelineForecastTab.tsx` | Sub-tab |
| 14 | Create | `ui/src/components/dashboards/crm/PartnerPerformanceTab.tsx` | Sub-tab |
| 15 | Create | `ui/src/components/dashboards/crm/ManagerPerformanceTab.tsx` | Sub-tab |
| 16 | Create | `ui/src/components/dashboards/crm/DealsDeepDiveTab.tsx` | Sub-tab |
| 17 | Create | `ui/src/components/dashboards/crm/ManagerDrillDownModal.tsx` | Drill-down modal |
| 18 | Modify | `ui/src/pages/Department.tsx` | Replace Reports with Dashboard tab |

Total: 3 backend files, ~15 frontend files, 1 dependency install.