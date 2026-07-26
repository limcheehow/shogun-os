# Staff Directory v2 Implementation Plan

**Goal:** Expand the staff management module with comms platform IDs, CSV import, HR provider abstraction with BrioHR reference, and auto-generated brain pages.

**Architecture:** User model expands with staff profile fields. Brain sync auto-writes `shared/staff/{slug}.md` on every staff change. CSV import parses → validates → bulk creates users with temp passwords. BrioHR sync follows the HR provider abstraction pattern under `recipes/hr/staff-directory/`.

**Tech Stack:** FastAPI (Python), React/Vite (TypeScript), gbrain MCP, BrioHR API

---

### Task 1: Expand User Model with Staff Profile Fields

**Objective:** Add phone, slack_user_id, telegram_user_id, employee_id, manager_id, avatar_url, source, last_synced_at to User model.

**Files:**
- Modify: `shogun-web/server/models.py`

**Implementation:**

```python
# New fields on User model, after invited_by_id:
phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
slack_user_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
telegram_user_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
employee_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
manager_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
avatar_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

# New relationships
manager: Mapped[Optional["User"]] = relationship(
    remote_side="User.id", back_populates="direct_reports"
)
direct_reports: Mapped[List["User"]] = relationship(
    back_populates="manager", cascade="all, delete-orphan"
)
```

Also update `to_dict()` to include the new fields.

**Verify:**
```bash
python3 -c "import ast; ast.parse(open('shogun-web/server/models.py').read()); print('OK')"
```

---

### Task 2: Create brain_sync.py Utility

**Objective:** Create shared utility that writes/updates `shared/staff/{slug}.md` brain pages from User data.

**Files:**
- Create: `shogun-web/server/brain_sync.py`

**Implementation:**

```python
"""Auto-generate staff brain pages on every staff create/update."""
import logging
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
from models import User, UserDepartment

logger = logging.getLogger(__name__)

STAFF_BRAIN_DIR = Path.home() / "brain" / "shared" / "staff"


def _user_slug(user: User) -> str:
    """Generate a brain-page slug from user name."""
    name = user.name or user.email.split("@")[0]
    slug = name.lower().replace(" ", "-")
    # Remove non-alphanumeric except hyphens
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    return slug.strip("-") or f"user-{user.id}"


def sync_staff_to_brain(user: User, db: Session) -> Optional[Path]:
    """Write a staff brain page for the given user. Returns the path written."""
    from models import UserDepartment

    assignments = (
        db.query(UserDepartment).filter(UserDepartment.user_id == user.id).all()
    )
    dept_names = ", ".join(a.department.name for a in assignments if a.department)
    titles = ", ".join(a.title for a in assignments if a.title)

    manager_name = ""
    if user.manager_id:
        mgr = db.get(User, user.manager_id)
        if mgr:
            manager_name = mgr.name

    slug = _user_slug(user)
    content = f"""---
type: staff
title: {user.name}
email: {user.email}
department: {dept_names}
role: {titles or user.role}
slack_user_id: {user.slack_user_id or ''}
telegram_user_id: {user.telegram_user_id or ''}
employee_id: {user.employee_id or ''}
phone: {user.phone or ''}
manager: {manager_name}
source: {user.source}
---

# {user.name}

**Role:** {titles or user.role}
**Department:** {dept_names}
**Email:** {user.email}
{f'**Phone:** {user.phone}' if user.phone else ''}
{f'**Slack:** {user.slack_user_id}' if user.slack_user_id else ''}
{f'**Telegram:** {user.telegram_user_id}' if user.telegram_user_id else ''}
{f'**Employee ID:** {user.employee_id}' if user.employee_id else ''}
{f'**Manager:** {manager_name}' if manager_name else ''}
"""

    brain_path = STAFF_BRAIN_DIR / f"{slug}.md"
    brain_path.parent.mkdir(parents=True, exist_ok=True)
    brain_path.write_text(content, encoding="utf-8")
    logger.info("Wrote staff brain page: %s", brain_path)
    return brain_path
```

**Verify:**
```bash
python3 -c "import ast; ast.parse(open('shogun-web/server/brain_sync.py').read()); print('OK')"
```

---

### Task 3: Expand Staff API with New Fields + CSV Import + Directory + BrioHR Sync

**Objective:** Update staff.py CRUD with all new fields, add POST /import-csv, GET /directory, POST /sync-briohr.

**Files:**
- Modify: `shogun-web/server/staff.py`

**Step 1: Update CreateStaffPayload and UpdateStaffPayload**

Add new fields:
```python
class CreateStaffPayload(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    name: str = Field(min_length=1, max_length=256)
    role: str = Field(default="user", pattern=r"^(admin|hr_manager|user)$")
    assignments: List[AssignmentPayload] = Field(default_factory=list)
    phone: str | None = None
    slack_user_id: str | None = None
    telegram_user_id: str | None = None
    employee_id: str | None = None
    manager_email: str | None = None  # resolved to manager_id on backend
```

**Step 2: Update create_staff to handle new fields**

After setting `invited_by_id` and before creating assignments:

```python
new_user.phone = body.phone or None
new_user.slack_user_id = body.slack_user_id or None
new_user.telegram_user_id = body.telegram_user_id or None
new_user.employee_id = body.employee_id or None
new_user.source = body.source or "manual"
if body.manager_email:
    mgr = db.execute(
        select(User).where(User.tenant_id == tenant.id, User.email == body.manager_email.lower().strip())
    ).scalar_one_or_none()
    if mgr:
        new_user.manager_id = mgr.id
```

After commit, call brain sync:
```python
from brain_sync import sync_staff_to_brain
sync_staff_to_brain(new_user, db)
```

**Step 3: Add CSV import endpoint**

```python
@router.post("/import-csv")
async def import_staff_csv(
    user: User = Depends(_require_admin_or_hr),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
) -> dict:
    """Import staff from CSV. Creates portal accounts with temp passwords."""
    import csv, io
    
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    
    created = 0
    updated = 0
    skipped = 0
    errors = []
    temp_passwords = {}
    tenant = get_primary_tenant(db)
    
    for row_num, row in enumerate(reader, start=2):  # header = row 1
        email = (row.get("email") or "").strip().lower()
        name = (row.get("name") or "").strip()
        dept_name = (row.get("department") or "").strip()
        
        if not email or not name:
            errors.append(f"Row {row_num}: missing email or name")
            skipped += 1
            continue
        
        # Find department
        dept = None
        if dept_name:
            dept = db.execute(
                select(Department).where(Department.tenant_id == tenant.id, Department.name == dept_name)
            ).scalar_one_or_none()
            if not dept:
                errors.append(f"Row {row_num}: unknown department '{dept_name}'")
        
        # Upsert user
        existing = db.execute(
            select(User).where(User.tenant_id == tenant.id, User.email == email)
        ).scalar_one_or_none()
        
        if existing:
            # Update
            existing.name = name
            existing.phone = row.get("phone") or existing.phone
            existing.slack_user_id = row.get("slack_id") or existing.slack_user_id
            existing.telegram_user_id = row.get("telegram_id") or existing.telegram_user_id
            existing.employee_id = row.get("employee_id") or existing.employee_id
            existing.source = "csv"
            db.add(existing)
            db.flush()
            updated += 1
        else:
            # Create
            temp_pw = _generate_temp_password()
            new_user = User(
                tenant_id=tenant.id,
                email=email,
                name=name,
                role=row.get("role", "user").strip() or "user",
                password_hash=hash_password(temp_pw),
                first_login=True,
                is_temporary_password=True,
                phone=row.get("phone") or None,
                slack_user_id=row.get("slack_id") or None,
                telegram_user_id=row.get("telegram_id") or None,
                employee_id=row.get("employee_id") or None,
                source="csv",
                invited_by_id=user.id,
            )
            db.add(new_user)
            db.flush()
            temp_passwords[email] = temp_pw
            created += 1
        
        # Create/update department assignment
        user_obj = existing or new_user
        if dept:
            existing_ud = db.execute(
                select(UserDepartment).where(
                    UserDepartment.user_id == user_obj.id,
                    UserDepartment.department_id == dept.id,
                )
            ).scalar_one_or_none()
            if not existing_ud:
                ud = UserDepartment(
                    user_id=user_obj.id,
                    department_id=dept.id,
                    title=row.get("title", "").strip() or "",
                )
                db.add(ud)
        
        # Brain sync
        sync_staff_to_brain(user_obj, db)
    
    db.commit()
    return {
        "ok": True,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "temporary_passwords": temp_passwords,
    }
```

**Step 4: Add directory endpoint**

```python
@router.get("/directory")
async def staff_directory(
    q: str | None = None,
    department: str | None = None,
    role: str | None = None,
    source: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(_require_admin_or_hr),
    db: Session = Depends(get_db),
) -> dict:
    """Searchable, filterable staff directory."""
    tenant = get_primary_tenant(db)
    query = select(User).where(User.tenant_id == tenant.id)
    
    if q:
        like = f"%{q}%"
        query = query.where(
            User.name.ilike(like) | User.email.ilike(like)
        )
    if role:
        query = query.where(User.role == role)
    if source:
        query = query.where(User.source == source)
    
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    users = db.execute(query.order_by(User.name).offset(offset).limit(limit)).scalars().all()
    
    return {
        "staff": [_staff_response(u, db) for u in users],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
```

Need to add `from sqlalchemy import func` to staff.py imports.

**Step 5: Add BrioHR sync endpoint**

```python
@router.post("/sync-briohr")
async def sync_briohr(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Trigger BrioHR employee sync. Uses the hr-provider abstraction."""
    from briohr_sync import sync_employees
    
    try:
        result = await sync_employees(db)
        return {"ok": True, **result}
    except Exception as exc:
        logger.exception("BrioHR sync failed")
        raise HTTPException(status_code=502, detail=str(exc))
```

---

### Task 4: Create HR Provider Abstraction (recipe)

**Objective:** Create the CONTRACT.md, GENERIC_SKILL.md, and briohr.md provider docs following the provider pattern.

**Files:**
- Create: `recipes/hr/staff-directory/CONTRACT.md`
- Create: `recipes/hr/staff-directory/GENERIC_SKILL.md`
- Create: `recipes/hr/staff-directory/providers/briohr.md`

---

### Task 5: Update Frontend Types

**Objective:** Add new fields to StaffMember and CreateStaffPayload types.

**Files:**
- Modify: `shogun-web/ui/src/lib/types.ts`

**Changes:**

```typescript
export interface StaffMember {
  id: number;
  email: string;
  name: string;
  role: 'admin' | 'hr_manager' | 'user';
  first_login: boolean;
  is_temporary_password: boolean;
  created_at?: string;
  assignments: StaffAssignment[];
  // NEW:
  phone?: string;
  slack_user_id?: string;
  telegram_user_id?: string;
  employee_id?: string;
  manager_name?: string;
  source?: string;
  last_synced_at?: string;
}

export interface CreateStaffPayload {
  email: string;
  name: string;
  role: string;
  assignments: { department: string; title: string }[];
  // NEW:
  phone?: string;
  slack_user_id?: string;
  telegram_user_id?: string;
  employee_id?: string;
  manager_email?: string;
}
```

---

### Task 6: Update Frontend API Methods

**Objective:** Add importCsv, syncBriohr, directory endpoints to staffApi.

**Files:**
- Modify: `shogun-web/ui/src/lib/api.ts`

**Changes:**

```typescript
export const staffApi = {
  list: () => apiFetch<{ staff: StaffMember[] }>('/api/staff'),
  get: (id: number) => apiFetch<{ user: StaffMember }>(`/api/staff/${id}`),
  create: (payload: CreateStaffPayload) =>
    apiFetch<{ ok: boolean; user: StaffMember; temporary_password?: string }>('/api/staff', { ... }),
  update: (id: number, payload: Partial<CreateStaffPayload>) =>
    apiFetch<{ ok: boolean; user: StaffMember }>(`/api/staff/${id}`, { ... }),
  remove: (id: number) => apiFetch<{ ok: boolean }>(`/api/staff/${id}`, { method: 'DELETE' }),
  resetPassword: (id: number) =>
    apiFetch<{ ok: boolean; temporary_password: string }>(`/api/staff/${id}/reset-password`, { ... }),
  // NEW:
  importCsv: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return apiFetch<{ ok: boolean; created: number; updated: number; skipped: number; errors: string[]; temporary_passwords: Record<string, string> }>('/api/staff/import-csv', {
      method: 'POST',
      body: fd,
    });
  },
  directory: (params?: { q?: string; department?: string; role?: string; source?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.q) sp.set('q', params.q);
    if (params?.department) sp.set('department', params.department);
    if (params?.role) sp.set('role', params.role);
    if (params?.source) sp.set('source', params.source);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return apiFetch<{ staff: StaffMember[]; total: number; limit: number; offset: number }>(`/api/staff/directory?${sp.toString()}`);
  },
  syncBriohr: () =>
    apiFetch<{ ok: boolean; created: number; updated: number; errors: string[]; synced_at?: string }>('/api/staff/sync-briohr', { method: 'POST' }),
};
```

---

### Task 7: Expand Staff Management Page

**Objective:** Update StaffManagement.tsx with new form fields, CSV import modal, BrioHR sync panel.

**Files:**
- Modify: `shogun-web/ui/src/pages/StaffManagement.tsx`

Changes:
1. **Staff table** — add columns: Phone, Slack ID, Telegram ID, Employee ID, Manager, Source
2. **Add/Edit form** — add fields for phone, slack_user_id, telegram_user_id, employee_id, manager_email
3. **CSV Import button** → modal with file drag-and-drop + preview table + confirm
4. **BrioHR Sync** → panel showing last sync time and "Sync Now" button

---

### Task 8: Update HUB.md with new recipe

**Objective:** Register the staff-directory recipe in the HUB.md manifest.

**File:**
- Modify: `shogun-os/HUB.md`

**Change:**
Add to the skill table:
```
| `hr-staff-directory` | HR staff directory — sync employees from BrioHR (or any HRMS), auto-generate brain pages | <-- needs to be added to the table|
```

---

### Task 9: End-to-End Verification

**Step 1: TypeScript compile**
```bash
cd shogun-web/ui && npx tsc --noEmit
```

**Step 2: Vite build**
```bash
npm run build
```

**Step 3: Python syntax**
```bash
python3 -c "import ast; [ast.parse(open(f'shogun-web/server/{f}').read()) for f in ['models.py','staff.py','brain_sync.py']]; print('OK')"
```

**Step 4: Backend start**
```bash
cd shogun-web/server && python3 -m main &
sleep 3
curl -s http://localhost:8787/api/health
```