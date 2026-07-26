# Profile Dashboards — Design Spec

> Author: Hermes Agent
> Date: 2026-07-26
> Status: Draft

## 1. Problem

Shogun OS web portal (`/department/:name`) shows 5 tabs per department profile: Chat, Brain, Docs, Reports (placeholder), and Settings. There is no way to view **profile-specific operational dashboards** — structured, visual views of data relevant to each department.

Separate standalone dashboards exist (CRM at port 8770, marketing at a separate port) but:

- Each has its own auth, its own design system, its own data source (Supabase)
- They cannot be embedded into the unified Shogun portal
- No shared patterns exist for departments that want dashboards
- Data sources bypass gbrain (local Postgres), defeating the knowledge-layer unification

## 2. Goals

1. **Unified single backend** — all dashboard data flows through FastAPI → gbrain MCP → local Postgres
2. **Profile-specific dashboards** — each department declares its own dashboard tabs and sub-sections
3. **Unified design** — Recharts standard, Shogun design tokens, shared chart wrappers
4. **Extensible** — any profile can opt in (CRM first, marketing next, project/product after)
5. **Zero auth duplication** — reuses Shogun portal auth (session cookie / JWT)

## 3. Non-Goals

- Not replacing the standalone Next.js CRM dashboards *in place* — they remain until the Shogun versions are fully feature-matched
- Not building dashboards for all 10 departments in one pass — CRM is the first
- Not building a drag-and-drop dashboard builder
- Not adding real-time streaming beyond existing WebSocket infrastructure

## 4. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser (SPA)                              │
│  /department/crm?tab=dashboard                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ <DashboardViewer department={key}>                        │ │
│  │  └─ resolves dept-specific dashboard component            │ │
│  │       └─ <CrmDashboard />                                 │ │
│  │            ├─ <DashboardSubNav tabs={...} />               │ │
│  │            └─ active sub-tab content (Recharts)           │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────┬────────────────────────────────────────┘
                       │ GET /api/departments/crm/dashboard/*
┌──────────────────────▼────────────────────────────────────────┐
│  FastAPI Backend (port 8787)                                   │
│                                                                 │
│  departments.py (existing)                                      │
│    └─ GET /{name} → department detail                           │
│    └─ GET /{name}/brain → gbrain proxy                          │
│    └─ GET /{name}/docs → doc listing                            │
│                                                                 │
│  dashboard.py (NEW)                                             │
│    └─ GET /{name}/dashboard → dashboard config (tabs, meta)     │
│    └─ GET /{name}/dashboard/ceo-stats → CRM aggregated stats    │
│    └─ GET /{name}/dashboard/manager/{owner} → drill-down        │
│                                                                 │
│  gbrain_client.py (NEW — shared utility)                        │
│    └─ fetch_pages(source, slug_prefix, limit)                   │
│    └─ fetch_page(source, slug)                                  │
│    └─ search_pages(source, query)                               │
└──────────────┬──────────────────────────────────────────────────┘
               │ HTTP proxy to gbrain HTTP MCP
┌──────────────▼──────────────────────────────────────────────────┐
│  gbrain HTTP MCP (port 7432)                                    │
│    └─ GET /api/pages?source=crm&limit=200                       │
│    └─ GET /api/pages/crm/{slug}                                 │
│    └─ POST /api/search → {query, source_id, limit}             │
└──────────────┬──────────────────────────────────────────────────┘
               │ SQL
     ┌─────────▼──────────┐
     │  Local Postgres 16  │
     │  pages table        │
     │  content_chunks     │
     └────────────────────┘
```

### Data Flow (CRM CEO Stats — the critical path)

```
1. React calls GET /api/departments/crm/dashboard/ceo-stats
2. FastAPI calls gbrain MCP: GET http://127.0.0.1:7432/api/pages?source=crm&limit=200
3. gbrain returns pages array (including deals/* entries with frontmatter)
4. FastAPI filters to slug ~ 'deals/%'
5. FastAPI aggregates: ownerMap, stageMap, monthMap, partnerMap, productMap, etc.
   (1:1 port of the current CRM Next.js route logic)
6. FastAPI returns CeoDashboardStats JSON
7. React renders KPI cards + sub-tab charts
```

## 5. Backend Design

### 5.1 New File: `shogun-web/server/dashboard.py`

```python
router = APIRouter(prefix="/departments/{name}/dashboard", tags=["dashboard"])

@router.get("")
async def get_dashboard_config(name, user, db):
    """Return dashboard config for this department."""
    # Checks department exists
    # Returns {enabled, tabs, meta} from a per-dept config
    # or 404 if department has no dashboard

@router.get("/ceo-stats")
async def get_crm_ceo_stats(name, user, db):
    """Aggregated CEO dashboard stats for CRM."""
    pages = await gbrain_fetch_pages("crm", limit=200)
    deals = filter_deals(pages)  # slug starts with deals/
    # Port of the aggregation logic from crm-dashboard/app/api/deals/ceo-stats/route.ts
    return CeoDashboardStats(...)

@router.get("/manager/{owner}")
async def get_crm_manager_drilldown(name, owner, user, db):
    """Per-manager drill-down stats."""
    # Similar aggregation filtered by owner
```

### 5.2 New File: `shogun-web/server/gbrain_client.py`

Shared HTTP client for gbrain MCP. Extracted from the ad-hoc proxying currently in `departments.py`:

```python
async def gbrain_fetch_pages(source: str, limit: int = 100, prefix: str = None) -> list[dict]:
    """Fetch pages from gbrain via HTTP MCP."""
    cfg = get_config()
    base = cfg.gbrain_base_url.rstrip("/")
    params = {"source_id": source, "limit": min(limit, 500)}
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(f"{base}/api/pages", params=params)
        resp.raise_for_status()
        pages = resp.json()
    if prefix:
        pages = [p for p in pages if p.get("slug", "").startswith(prefix)]
    return pages

async def gbrain_fetch_page(source: str, slug: str) -> dict | None:
    """Fetch a single page from gbrain."""
    # ...

async def gbrain_search(source: str, query: str, limit: int = 20) -> list[dict]:
    """Search gbrain pages."""
    # POST /api/search with {query, source_id, limit}
```

### 5.3 Aggregation Logic Port

The aggregation math currently in `crm-dashboard/app/api/deals/ceo-stats/route.ts` (348 lines) ports to `Python` in `dashboard.py`. Key port mapping:

| JavaScript | Python |
|---|---|
| `canonicalOwner`, `canonicalStage` | `canonicalize.owner()`, `canonicalize.stage()` |
| `stageWeight()` | `STAGE_WEIGHTS` dict |
| `ownerMap` (Map) | `dict[str, OwnerAccum]` |
| `partnerMap` (Map) | `dict[str, PartnerAccum]` |
| `monthMap` (Map) | `dict[str, float]` |
| `isThisMonth()`, `isThisQuarter()` | `datetime` comparisons |
| `parseFrontmatter()` | `json.loads()` |
| `inferProduct()` | Same regex logic |

The Python port returns the identical `CeoDashboardStats` JSON shape so the React frontend contract is unchanged.

## 6. Frontend Design

### 6.1 Department Tab Registration

Replace the "Reports" placeholder tab with "Dashboard" in `Department.tsx`:

```typescript
const TABS = [
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'brain', label: 'Brain', icon: Brain },
  { id: 'docs', label: 'Docs', icon: FileText },
  { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },  // was 'reports'
  { id: 'settings', label: 'Settings', icon: Settings },
];
```

The dashboard tab render section:

```typescript
{!deptQuery.isLoading && tab === 'dashboard' && (
  <DashboardViewer department={key} color={color} />
)}
```

### 6.2 DashboardViewer (generic wrapper)

File: `ui/src/components/dashboards/DashboardViewer.tsx`

Responsibilities:
1. Fetch dashboard config via `departmentsApi.dashboardConfig(key)`
2. If config is `{enabled: false}`, render "No dashboard configured" placeholder
3. If enabled, resolve the department-specific dashboard component
4. Pass through the department color for visual theming

Component resolution map:

```typescript
const DASHBOARD_COMPONENTS: Record<string, React.ComponentType<DashboardProps>> = {
  crm: CrmDashboard,
  marketing: MarketingDashboard,
  // future: projects, product, etc.
};

function DashboardViewer({ department, color }: DashboardProps) {
  const config = useQuery(['dashboard-config', department], () =>
    departmentsApi.dashboardConfig(department)
  );
  const DashboardComponent = DASHBOARD_COMPONENTS[department];

  if (!config.data?.enabled || !DashboardComponent) {
    return <DashboardPlaceholder />;
  }

  return <DashboardComponent department={department} color={color} />;
}
```

### 6.3 DashboardSubNav (sub-tab bar)

File: `ui/src/components/dashboards/DashboardSubNav.tsx`

A scrollable chip navigation bar for dashboard sub-sections. Uses the same visual pattern as the current CRM dashboard's tab bar, but styled with Shogun design tokens:

```typescript
interface DashboardSubNavProps {
  tabs: { id: string; label: string; icon: LucideIcon }[];
  active: string;
  onChange: (id: string) => void;
  color?: string; // department accent color
}
```

Active tab gets the department accent color as background; inactive tabs are white with border. The bar scrolls horizontally on mobile.

### 6.4 Shared Chart Wrappers

File: `ui/src/components/dashboards/charts/`

Standardize Recharts via thin wrappers that enforce Shogun design tokens, reduce boilerplate, and handle empty-data states:

```typescript
// BarChart.tsx
export function BarChart({
  data, xKey, yKey, color, unit, stacked, onClick
}: BarChartProps) {
  // Returns <ResponsiveContainer> → <BarChart> with:
  // - Default margins (top=5, right=5, left=0, bottom=5)
  // - Tooltip styled with Shogun tokens (bg-white, border, shadow)
  // - X axis: rotated labels, no gridlines
  // - Y axis: formatted with unit prefix (RM, %, count)
  // - Empty state: centered "No data" message
  return (...);
}

// LineChart.tsx — time-series trend lines
// PieChart.tsx — donut segments
// FunnelChart.tsx — sales funnel bars
```

Each wrapper:
- Is a thin composition around Recharts primitives
- Accepts `color` prop for the department accent
- Handles empty data without crashing
- Includes `displayName` for React DevTools
- Exports named exports for tree-shaking

### 6.5 CRM Dashboard Components

File: `ui/src/components/dashboards/crm/`

Each sub-tab is a self-contained component receiving the `CeoDashboardStats` as a prop:

```
CrmDashboard.tsx              ← fetches stats, manages active sub-tab
├── SalesPulseTab.tsx         ← KPI cards, MTD/QTD/YTD, win rate, avg deal
├── PipelineForecastTab.tsx   ← funnel, monthly trend, weighted pipeline
├── PartnerPerformanceTab.tsx ← partner leaderboard, cross-tab matrix
├── ManagerPerformanceTab.tsx ← manager rankings, at-risk alerts
└── DealsDeepDiveTab.tsx      ← top deals table, hot deals, stage breakdown
```

The stats fetch lives in `CrmDashboard.tsx` (the parent) and is shared via props — exactly the same pattern as the current CRM Next.js app where `DashboardPage` fetches once and passes to all 5 children.

### 6.6 Type Definitions

New types in `ui/src/lib/types.ts`:

```typescript
export interface DashboardConfig {
  enabled: boolean;
  tabs: DashboardTab[];
  meta?: Record<string, unknown>;
}

export interface DashboardTab {
  id: string;
  label: string;
  icon: string; // lucide icon name
}
```

Extended `DEPARTMENT_CATALOG` entries:

```typescript
crm: {
  ...existing,
  dashboard: {
    enabled: true,
    tabs: [
      { id: 'revenue', label: 'Sales Booking', icon: 'LayoutDashboard' },
      { id: 'pipeline', label: 'Pipeline & Forecast', icon: 'TrendingUp' },
      { id: 'partner', label: 'Partner Performance', icon: 'Handshake' },
      { id: 'managers', label: 'Manager Performance', icon: 'Users' },
      { id: 'deals', label: 'Deals Deep-Dive', icon: 'Target' },
    ],
  },
},
```

New API methods in `ui/src/lib/api.ts`:

```typescript
export const departmentsApi = {
  // ... existing
  dashboardConfig: (name: string) =>
    apiFetch<DashboardConfig>(`/api/departments/${name}/dashboard`),
  dashboardStats: (name: string, query: string) =>
    apiFetch<CeoDashboardStats>(`/api/departments/${name}/dashboard/${query}`),
};
```

## 7. Recharts Standardization

Recharts is added to Shogun web's dependencies (`npm install recharts`). All future dashboard visuals SHALL use the shared chart wrappers rather than raw Recharts imports, to enforce:

1. Consistent sizing and responsiveness
2. Shogun color token usage
3. Proper empty-state handling
4. Accessibility basics (role="img", aria-label)

The wrappers live at `components/dashboards/charts/` and are importable as:

```typescript
import { BarChart, LineChart, PieChart, FunnelChart } from '../dashboards/charts';
```

## 8. Migration Plan for CRM Dashboard

### Phase 1: Infrastructure (this round)

| Step | File(s) | Description |
|---|---|---|
| 1 | `package.json` | Add `recharts` dependency |
| 2 | `server/gbrain_client.py` | Shared gbrain HTTP client utility |
| 3 | `server/dashboard.py` | Dashboard router + CEO stats endpoint |
| 4 | `server/main.py` | Register dashboard router |
| 5 | `ui/src/lib/api.ts` | Add `dashboardConfig`, `dashboardStats` methods |
| 6 | `ui/src/lib/types.ts` | Add `DashboardConfig`, `CeoDashboardStats` types, extend catalog |
| 7 | `ui/src/components/dashboards/charts/*.tsx` | Shared chart wrappers |
| 8 | `ui/src/components/dashboards/DashboardViewer.tsx` | Generic wrapper |
| 9 | `ui/src/components/dashboards/DashboardSubNav.tsx` | Sub-tab nav |
| 10 | `ui/src/components/dashboards/crm/CrmDashboard.tsx` | CRM parent (+ 5 sub-tabs) |
| 11 | `ui/src/pages/Department.tsx` | Wire "Dashboard" tab |

### Phase 2: Feature parity (separate round)

- Manager drill-down page (`/department/crm/dashboard/manager/{owner}`)
- Deals list view (filtered/sortable table)
- Companies view
- Tasks view

### Phase 3: More profiles (separate rounds)

- Marketing dashboard sub-tabs
- Projects dashboard (scrum stats, milestone tracking)
- Product dashboard (roadmap, feature usage)

## 9. Design Token Usage

All dashboard components use existing Shogun design tokens from `ui/src/index.css`:

| Token | Usage | CSS Class |
|---|---|---|
| Brand | Active tab, primary chart color | `var(--brand)`, `bg-brand` |
| Surface | Card backgrounds | `card`, `bg-white` |
| Surface muted | Section backgrounds | `bg-surface-muted` |
| Text body | Labels, descriptions | `text-slate-700` |
| Text primary | Headings, KPI values | `text-slate-900` |
| Text muted | Secondary info | `text-slate-500` |

No new design tokens are introduced. The department accent color (`color` prop from `DEPARTMENT_CATALOG`) is used for chart fills, active tab indicators, and KPI accent borders.

## 10. Verification

1. `npm run build` — TypeScript compilation + Vite build passes
2. SPA serves without errors on page load
3. Navigate to `/department/crm?tab=dashboard` — dashboard loads with 5 sub-tabs
4. Each sub-tab renders correct charts with data
5. Switching departments shows correct (or placeholder) dashboard
6. No new browser console errors
7. Recharts components render without hydration/SSR mismatches (SPA-only — Vite, no SSR)

## 11. Resolved Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Manager drill-down | Modal overlay within dashboard tab | Simpler UX, no route duplication, user stays in context |
| Chart colors | Auto-generated palette from dept accent | Single-series uses accent; multi-series generates a harmonious palette via `chroma-js` or manual HSL stepping |

A lightweight palette utility (`utils/palette.ts`) generates N distinct colors from a base hue:

```typescript
export function generatePalette(baseColor: string, count: number): string[] {
  // Parse base hex → HSL
  // Step saturation and lightness around the base hue
  // Return N visually distinct colors
}
```