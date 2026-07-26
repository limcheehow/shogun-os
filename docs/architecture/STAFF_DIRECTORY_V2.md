# Staff Directory v2 — Design Spec

> Author: Hermes Agent
> Date: 2026-07-26
> Status: Draft

## 1. Problem

The current Staff Management module creates portal users with basic fields (email, name, role, department assignments). Several gaps remain:

- Staff data is scattered across `brain/hr/profiles/`, `brain/people/`, and `brain/shared/staff/` (empty)
- No comms platform IDs (Slack, Telegram) stored on staff profiles
- No CSV import for bulk staff creation
- No HRMS integration beyond BrioHR leave balance sync
- No automatic brain page generation for staff directory
- No staff directory view showing all staff in one place
- Manager hierarchy not tracked

## 2. Goals

1. **Unified staff profile** — `User` model is the single source of truth for all staff data
2. **Comms IDs** — Slack user ID, Telegram user ID, phone per staff member
3. **CSV import** — bulk create/update staff from CSV with temp password generation
4. **BrioHR integration** — sync employee data from BrioHR (optional, portal + cron)
5. **Brain sync** — auto-generate `shared/staff/{slug}.md` pages on every staff change
6. **Staff directory view** — enhanced web portal page with search, filter, comms badges
7. **Migration** — move existing `brain/hr/profiles/` → `brain/shared/staff/`

## 3. Non-Goals

- Real-time presence/status (online/offline)
- Department hierarchy visualization
- Multiple HRMS providers beyond the first reference (BrioHR) — the provider abstraction is defined; adding providers is a separate task
- Staff-to-staff messaging
- Payroll or compensation data
- Migration of existing brain staff pages — this is a local Hermes task, not part of Shogun OS

## 4. DB Model Changes

### 4.1 Expanded `User` model

```python
class User(Base):
    # ... existing fields ...
    email: str
    name: str
    role: str              # "admin" | "hr_manager" | "user"
    password_hash: str | None
    is_temporary_password: bool = False
    first_login: bool = True
    invited_by_id: int | None (FK → users.id)

    # NEW: Staff directory fields
    phone: str | None = None
    slack_user_id: str | None = None
    telegram_user_id: str | None = None
    employee_id: str | None = None          # BrioHR / HRMS employee number
    manager_id: int | None (FK → users.id)  # self-referential manager
    avatar_url: str | None = None
    source: str = "manual"                  # "manual" | "csv" | "briohr" | "api"
    last_synced_at: datetime | None = None  # last BrioHR sync timestamp

    # Relationships
    manager: Mapped[Optional["User"]] = relationship(
        remote_side="User.id", back_populates="direct_reports"
    )
    direct_reports: Mapped[List["User"]] = relationship(
        back_populates="manager", cascade="all, delete-orphan"
    )
```

### 4.2 Migration: Create new columns

```sql
ALTER TABLE users ADD COLUMN phone VARCHAR(64);
ALTER TABLE users ADD COLUMN slack_user_id VARCHAR(128);
ALTER TABLE users ADD COLUMN telegram_user_id VARCHAR(128);
ALTER TABLE users ADD COLUMN employee_id VARCHAR(128);
ALTER TABLE users ADD COLUMN manager_id INTEGER REFERENCES users(id);
ALTER TABLE users ADD COLUMN avatar_url VARCHAR(1024);
ALTER TABLE users ADD COLUMN source VARCHAR(32) DEFAULT 'manual';
ALTER TABLE users ADD COLUMN last_synced_at TIMESTAMP;
```

SQLite auto-creates columns via `Base.metadata.create_all` for new non-nullable-with-default fields. For nullable fields, SQLite handles them natively.

## 5. Backend API

### 5.1 Enhanced Staff Endpoints

| Method | Path | Change |
|---|---|---|
| `POST` | `/api/staff` | Accept `phone`, `slack_user_id`, `telegram_user_id`, `employee_id`, `manager_email` |
| `PUT` | `/api/staff/{id}` | Accept same fields |
| `GET` | `/api/staff/{id}` | Return all profile fields |
| `GET` | `/api/staff/directory` | **New** — searchable, filterable staff list |

**GET /api/staff/directory** query params:
- `q` — search by name, email
- `department` — filter by department name
- `role` — filter by role
- `source` — filter by source ("manual", "csv", "briohr")
- `limit` (default 50)
- `offset` (default 0)

Returns:
```json
{
  "staff": [...],
  "total": 142,
  "limit": 50,
  "offset": 0
}
```

### 5.2 CSV Import

**POST /api/staff/import-csv** — multipart form with CSV file.

Request: `multipart/form-data` with `file` field containing CSV.

CSV columns:

| Column | Required | Maps to |
|---|---|---|
| `email` | ✅ | User.email |
| `name` | ✅ | User.name |
| `department` | ✅ | UserDepartment (matched by name) |
| `title` | | UserDepartment.title |
| `role` | | User.role (default: "user") |
| `phone` | | User.phone |
| `slack_id` | | User.slack_user_id |
| `telegram_id` | | User.telegram_user_id |
| `employee_id` | | User.employee_id |
| `manager_email` | | User.manager_id (resolved via email lookup) |

Response:
```json
{
  "ok": true,
  "created": 14,
  "updated": 2,
  "skipped": 1,
  "errors": ["Row 5: Unknown department 'eng'"],
  "staff": [ ... ],
  "temporary_passwords": {
    "ahmad@company.com": "A8xK9m2p",
    "siti@company.com": "zQ4wR7nL"
  }
}
```

When creating new users, temp passwords are generated. When updating existing users, password is not changed.

### 5.3 HR Provider Abstraction (recipe)

The BrioHR sync follows the **provider abstraction pattern** defined in `docs/architecture/PROVIDER_ABSTRACTION.md`. This allows multiple HRMS backends (BrioHR, BambooHR, Personio, etc.) to implement the same contract.

**Abstraction structure:**

```
recipes/hr/staff-directory/
├── CONTRACT.md              # API contract: sync employees, sync leave, lookup
├── GENERIC_SKILL.md         # Generic Hermes skill using hr tool names
└── providers/
    ├── briohr.md            # Reference implementation — BrioHR
    └── ...                  # Future: bamboohr, personio, etc.
```

**Contract (CONTRACT.md) defines these operations:**

| Operation | Returns | Description |
|---|---|---|
| `hr_sync_employees()` | `Employee[]` | Fetch all employees with name, email, dept, role, manager |
| `hr_sync_leave_balances()` | `LeaveBalance[]` | Fetch annual leave, sick leave, carry-over |
| `hr_lookup_employee(email)` | `Employee\|null` | Single employee lookup |

The portal's **POST /api/staff/sync-briohr** endpoint calls the BrioHR provider implementation. When a new provider is added, a new endpoint or a provider-selectable endpoint serves the same purpose.

**BrioHR reference implementation** (file: `recipes/hr/staff-directory/providers/briohr.md`):

Documents:
- API endpoints used: employee list download, leave summaries download
- Authentication: Basic Auth via stored credentials
- Rate limiting: retry logic, backoff on 403
- Field mapping: BrioHR CSV columns → User model fields

### 5.4 Brain Sync — Auto-generate staff pages

Whenever a staff member is created or updated via ANY path (portal form, CSV, BrioHR sync), the backend writes/updates a brain page at `shared/staff/{slug}.md`:

```python
def _sync_staff_to_brain(user: User, db: Session) -> None:
    """Write a staff brain page for the given user."""
    slug = _user_slug(user)  # e.g. "ahmad-bin-ali"
    assignments = db.query(UserDepartment).filter(...).all()
    depts = ", ".join(a.department.name for a in assignments)
    titles = ", ".join(a.title for a in assignments if a.title)

    content = f"""---
type: staff
title: {user.name}
email: {user.email}
department: {depts}
role: {titles or user.role}
slack_user_id: {user.slack_user_id or ''}
telegram_user_id: {user.telegram_user_id or ''}
employee_id: {user.employee_id or ''}
phone: {user.phone or ''}
source: {user.source}
---

# {user.name}

**Role:** {titles or user.role}
**Department:** {depts}
**Email:** {user.email}
{f'**Phone:** {user.phone}' if user.phone else ''}
{f'**Slack:** {user.slack_user_id}' if user.slack_user_id else ''}
{f'**Telegram:** {user.telegram_user_id}' if user.telegram_user_id else ''}
{f'**Employee ID:** {user.employee_id}' if user.employee_id else ''}
"""
    # Write via gbrain MCP or direct file write
    brain_path = Path.home() / "brain" / "shared" / "staff" / f"{slug}.md"
    brain_path.parent.mkdir(parents=True, exist_ok=True)
    brain_path.write_text(content)
```

Called from:
- `POST /api/staff` — after creation
- `PUT /api/staff/{id}` — after update
- `POST /api/staff/import-csv` — after each row
- `POST /api/staff/sync-briohr` — after each employee upsert

## 6. Frontend

### 6.1 Staff Management page — expanded

**Staff table** gains new columns:
- Comms IDs (Slack icon + ID, Telegram icon + ID)
- Phone
- Employee ID
- Source badge (blue "BrioHR", green "CSV", grey "Manual")

**Add/Edit form** gains fields:
- Phone (input)
- Slack User ID (input with Slack icon)
- Telegram User ID (input with Telegram icon)
- Employee ID (input)
- Manager (select dropdown of existing staff)

**Import CSV button** → opens modal:
```
┌──────────────────────────────────────────────┐
│ Import Staff from CSV                         │
│                                              │
│  [Drop CSV file here or click to browse]     │
│                                              │
│  Preview:                                     │
│  ┌────────┬────────┬────────┬────────┐       │
│  │ Email  │ Name   │ Dept   │ Status │       │
│  ├────────┼────────┼────────┼────────┤       │
│  │ a@c..  │ Ahmad  │ CRM    │ ✅ New │       │
│  │ b@c..  │ Siti   │ HR     │ 🔄 Upd │       │
│  └────────┴────────┴────────┴────────┘       │
│                                              │
│  [Cancel]                    [Import 12 Staff]│
└──────────────────────────────────────────────┘
```

**BrioHR sync panel** in the sidebar or top bar:
```
┌──────────────────────────────────┐
│ BrioHR Integration                │
│ Last sync: 2 hours ago           │
│ 45 staff synced, 0 errors        │
│                                   │
│ [Sync Now]                        │
└──────────────────────────────────┘
```

### 6.2 Staff Directory page (`/staff`)

The page is already `StaffManagement.tsx`. Enhanced with:

1. **Search bar** — filters by name/email as you type (client-side or debounced API)
2. **Department filter** — dropdown to filter by department
3. **Source filter** — "All", "Manual", "CSV", "BrioHR"
4. **Comms ID badges** — clickable Slack/Telegram icons with tooltip showing the ID
5. **Manager column** — shows manager name, clickable to filter

## 7. BrioHR Sync Cron

New file: `shogun-web/server/briohr_sync.py`

Shared module used by both the API endpoint and the cron job:

```python
async def sync_briohr_employees(db: Session) -> dict:
    """Fetch employee list from BrioHR, upsert Users, create brain pages."""

async def sync_briohr_leave_balances(db: Session) -> dict:
    """Existing leave balance sync, refactored to use shared/brain path."""
```

Cron job (via Hermes cron or systemd timer):

```bash
# Daily at 3am
hermes cron create --name sync-briohr-staff \
  --schedule "0 3 * * *" \
  --prompt "Run the BrioHR employee sync via POST /api/staff/sync-briohr"
```

## 8. File Inventory

| Action | File | Description |
|---|---|---|
| Modify | `shogun-web/server/models.py` | Add phone, slack_user_id, telegram_user_id, employee_id, manager_id, avatar_url, source, last_synced_at to User |
| Modify | `shogun-web/server/staff.py` | Expand CRUD with new fields, add import-csv, directory, sync-briohr endpoints |
| Create | `shogun-web/server/brain_sync.py` | Staff → brain page sync utility |
| Create | `recipes/hr/staff-directory/CONTRACT.md` | HR provider abstraction contract |
| Create | `recipes/hr/staff-directory/GENERIC_SKILL.md` | Generic Hermes skill for staff sync |
| Create | `recipes/hr/staff-directory/providers/briohr.md` | BrioHR reference implementation docs |
| Modify | `shogun-web/server/main.py` | Register any new routers |
| Modify | `shogun-web/ui/src/lib/types.ts` | Add new fields to StaffMember, CreateStaffPayload |
| Modify | `shogun-web/ui/src/lib/api.ts` | Add importCsv, syncBriohr, directory endpoints |
| Modify | `shogun-web/ui/src/pages/StaffManagement.tsx` | Expanded form, CSV import modal, BrioHR sync panel |
| Create | `docs/architecture/STAFF_DIRECTORY_V2.md` | This document |

## 10. Verification

1. Create staff via portal with Slack ID + Telegram ID → profile shows IDs → brain page created at `shared/staff/{slug}.md`
2. CSV import with 10 staff → 10 users created → 10 brain pages → temp passwords returned
3. BrioHR sync → employees fetched → users upserted by email → brain pages created/updated
4. Search `/api/staff/directory?q=ahmad&department=crm` → filtered results
5. Manager field: create user with `manager_email` → manager_id resolves → brain page shows manager name
6. Migration script: `brain/hr/profiles/*.md` → `brain/shared/staff/` with correct frontmatter
7. Old BrioHR leave sync still works with new `shared/staff/` path