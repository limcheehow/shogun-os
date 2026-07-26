---
name: add-profile-dashboard
description: "Step-by-step guide for AI agents to add a profile-specific operational dashboard to the Shogun OS web portal, following the CRM dashboard pattern."
---

# Add a Profile Dashboard

Use this skill when a user asks to add a new dashboard for a department profile (marketing, projects, product, etc.) in the Shogun OS web portal.

## Architecture Overview

```
SPA → /api/departments/{name}/dashboard/{query_type}
    → FastAPI backend → gbrain MCP HTTP (port 7432) → local Postgres
    → Aggregated JSON → React sub-tab components (Recharts via shared wrappers)
```

## Workflow

### Step 1: Load reference files

Load the CRM dashboard implementation as a reference pattern:

- `shogun-web/server/dashboard.py` — backend endpoint
- `shogun-web/ui/src/components/dashboards/crm/CrmDashboard.tsx` — parent component
- `shogun-web/ui/src/components/dashboards/crm/SalesPulseTab.tsx` — example sub-tab
- `shogun-web/ui/src/lib/types.ts` — CeoDashboardStats and related types
- `shogun-web/ui/src/lib/api.ts` — departmentsApi methods

### Step 2: Backend — Add aggregation endpoint

In `shogun-web/server/dashboard.py`, add a new entry to the `dashboard_meta` dict:

```python
# Inside get_dashboard_config(), add to dashboard_meta:
"marketing": {
    "enabled": True,
    "tabs": [
        {"id": "overview", "label": "Overview", "icon": "LayoutDashboard"},
        {"id": "leads", "label": "Leads", "icon": "Users"},
        {"id": "analytics", "label": "Analytics", "icon": "TrendingUp"},
    ],
},
```

Then add a new `@router.get(...)` method for the aggregation:

```python
@router.get("/summary")
async def get_marketing_summary(
    name: str = Path(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Aggregated marketing dashboard stats."""
    pages = await gbrain_fetch_pages("marketing", limit=200, slug_prefix="marketing/")
    return _aggregate_marketing(pages)
```

The aggregation function reads pages from gbrain, filters by the department's slug prefix, and computes the stat shapes the frontend expects.

**Rule of thumb:** The aggregation logic lives in Python on the server. The React frontend is a "dumb" renderer — it fetches stats and displays them. This keeps the frontend fast and avoids duplicating business logic.

### Step 3: Frontend — Add types

In `shogun-web/ui/src/lib/types.ts`, add dashboard-specific types:

```typescript
export interface MarketingDashboardStats {
  totalLeads: number;
  pipelineValue: number;
  // ... other fields the backend returns
}
```

### Step 4: Frontend — Add API method

In `shogun-web/ui/src/lib/api.ts`, add to `departmentsApi`:

```typescript
dashboardMarketingStats: (dept: string) =>
  apiFetch<MarketingDashboardStats>(`/api/departments/${dept}/dashboard/summary`),
```

### Step 5: Frontend — Create sub-tab components

Create `shogun-web/ui/src/components/dashboards/marketing/` directory and component files.

**Parent component** (`MarketingDashboard.tsx`):

```typescript
interface Props { department: string; color: string }

export function MarketingDashboard({ department, color }: Props) {
  const [activeTab, setActiveTab] = useState('overview');
  const statsQuery = useQuery(['dashboard-marketing', department], () =>
    departmentsApi.dashboardMarketingStats(department)
  );
  // ... same pattern as CrmDashboard.tsx
}
```

**Sub-tab components** follow this pattern:

```typescript
interface SubTabProps { stats: MarketingDashboardStats; color: string }

export function OverviewTab({ stats, color }: SubTabProps) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {/* KPI cards using className="card p-4" */}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {/* Charts using shared wrappers */}
      </div>
    </div>
  );
}
```

### Step 6: Register in DashboardViewer

In `shogun-web/ui/src/components/dashboards/DashboardViewer.tsx`, add to the component map:

```typescript
import { MarketingDashboard } from './marketing/MarketingDashboard';

const DASHBOARD_COMPONENTS: Record<string, React.ComponentType<...>> = {
  crm: CrmDashboard,
  marketing: MarketingDashboard,  // NEW
};
```

## Design Conventions

### Chart wrappers (shared, in `components/dashboards/charts/`)

Always import from the shared wrappers — do NOT import Recharts directly:

```typescript
// ✅ Correct
import { BarChart, LineChart, PieChart, FunnelChart } from '../charts';

// ❌ Wrong — don't import Recharts primitives directly
import { BarChart as RechartsBarChart, Bar, ... } from 'recharts';
```

### Shared wrapper props

| Prop | Type | Description |
|---|---|---|
| `data` | `any[]` | Array of data objects |
| `xKey` | string | Key for X axis / category |
| `yKey` / `valueKey` | string | Key for Y axis / value |
| `color` | string | Department accent color (hex, e.g. `#3b82f6`) |
| `colors` | string[] (optional) | Explicit palette override |
| `unit` | string | Prefix for values: `"RM "`, `"%"`, `""` |
| `height` | number | Chart height in px (default 250) |

### Color palette

Use the shared palette utility for multi-series charts:

```typescript
import { chartColors } from '../../../lib/palette';
const multiColors = chartColors(departmentColor, 3); // 3 distinct hues
```

### Styling

All new components must use Shogun design tokens from `ui/src/index.css`:

| Token | CSS Class | When to use |
|---|---|---|
| Brand | `bg-brand`, `text-brand` | Active tab, primary accent |
| Card | `card` | Section containers |
| Surface | `bg-surface-muted` | KPI card backgrounds, section headers |
| Text body | `text-slate-700` | Labels, descriptions |
| Text primary | `text-slate-900` | KPI values, headings |
| Text muted | `text-slate-500` | Secondary info, tab labels (inactive) |
| Border | `border-surface-border` | Card borders, dividers |
| Danger | `text-rose-600`, `bg-rose-50` | At-risk alerts, negative metrics |

### Tables

Use the existing card + table pattern:

```tsx
<div className="card overflow-hidden">
  <div className="border-b border-surface-border px-4 py-3">
    <h3 className="text-sm font-semibold text-slate-700">Title</h3>
  </div>
  <div className="overflow-x-auto">
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-surface-border text-xs font-medium uppercase tracking-wide text-slate-500">
          <th className="px-4 py-2">Header</th>
        </tr>
      </thead>
      <tbody>
        {data.map(row => (
          <tr className="border-b border-surface-border last:border-0 hover:bg-slate-50">
            <td className="px-4 py-2">Value</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
</div>
```

### Sub-tab navigation

Use `<DashboardSubNav>` for the pill-tab bar. Define tabs as `DashboardTab[]`:

```typescript
const TABS: DashboardTab[] = [
  { id: 'overview', label: 'Overview', icon: 'LayoutDashboard' },
  { id: 'leads', label: 'Leads', icon: 'Users' },
];
```

### Empty state

When a data array is empty, show the placeholder:

```tsx
<div className="flex h-full min-h-[200px] items-center justify-center rounded-xl border border-dashed border-slate-200 text-sm text-slate-400">
  No data
</div>
```

(The shared chart wrappers handle this automatically.)

## Verification Checklist

After implementing, verify:

1. `cd ~/shogun-os/shogun-web/ui && npx tsc --noEmit` — zero TypeScript errors
2. `cd ~/shogun-os/shogun-web/ui && npm run build` — Vite build succeeds
3. Navigate to `/department/{key}?tab=dashboard` — dashboard loads with correct sub-tabs
4. Data renders in charts (not empty)
5. "No dashboard configured" placeholder shows for departments without a dashboard
6. `cd ~/shogun-os && python3 -c "import ast; ast.parse(open('shogun-web/server/dashboard.py').read())"` — Python syntax valid
7. Commits follow the pattern: `feat: add {department} dashboard with {N} sub-tabs`

## Reference Files

- `docs/architecture/PROFILE_DASHBOARDS.md` — full design spec
- `shogun-web/server/dashboard.py` — reference backend implementation
- `shogun-web/ui/src/components/dashboards/crm/` — reference frontend implementation
- `shogun-web/ui/src/components/dashboards/charts/` — shared chart wrappers
- `shogun-web/ui/src/lib/palette.ts` — palette utility (hexToHsl, chartColors)
- `shogun-web/ui/src/index.css` — design tokens (card, btn, etc.)