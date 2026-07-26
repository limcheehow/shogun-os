# Staff Management & Access Control — Design Spec

> Author: Hermes Agent
> Date: 2026-07-26
> Status: Draft

## 1. Problem

Currently, every authenticated user in the Shogun OS web portal sees **all** department profiles and has access to **all** department chats, brain viewers, docs, and dashboards. There is no way for an admin to:

- Control which users can see which departments
- Assign a person-in-charge (PIC) per department during onboarding
- Generate temporary passwords for new users
- Prevent OAuth self-registrants from accessing anything until assigned

## 2. Goals

1. **Admin assigns PIC per department** — during onboarding or via Staff Management page
2. **Department-scoped access** — non-admin users see only their assigned departments in sidebar + tabs
3. **Staff Management page** — full CRUD for users and their department assignments
4. **Temp password flow** — admin creates users with temp passwords, shares them manually
5. **OAuth access gate** — self-registrants get a "No access" wall until assigned by admin
6. **Role system** — `admin`, `hr_manager`, `user` roles control what each user can do
7. **Settings tab** — admin-only

## 3. Non-Goals

- Email delivery of passwords (admin shows temp password on screen for now)
- Self-service password reset (admin does it)
- Granular permissions beyond role-based (no per-endpoint ACLs)
- SSO/SAML beyond existing OAuth (Google/Microsoft)

## 4. DB Model Changes

### 4.1 New Table: `user_departments`

```python
class UserDepartment(Base):
    __tablename__ = "user_departments"
    __table_args__ = (UniqueConstraint("user_id", "department_id", name="uq_user_dept"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    user: Mapped["User"] = relationship(back_populates="department_assignments")
    department: Mapped["Department"] = relationship()
```

### 4.2 Modified: `User` model

Add fields:

```python
class User(Base):
    # ... existing fields ...
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="user")
    #                     ^^ existing, but values expand to: "admin" | "hr_manager" | "user"
    is_temporary_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    invited_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    # New relationship
    department_assignments: Mapped[List["UserDepartment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
```

**Role values:**
| Role | Access |
|---|---|
| `admin` | Everything — all depts, Staff Management, Settings, default dashboard |
| `hr_manager` | Staff Management page + own assigned departments |
| `user` | Only own assigned departments (sidebar + tabs) — no Settings, no Staff Mgmt |

## 5. API Endpoints

### 5.1 Staff Management

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/api/staff` | admin, hr_manager | List all staff with department assignments |
| `POST` | `/api/staff` | admin, hr_manager | Create user + assign departments |
| `PUT` | `/api/staff/{id}` | admin, hr_manager | Update name, departments, titles, role |
| `DELETE` | `/api/staff/{id}` | admin, hr_manager | Remove user from all depts (cascade UserDepartment) |
| `POST` | `/api/staff/{id}/reset-password` | admin, hr_manager | Generate new temp password, returns once |

**POST /api/staff** request body:

```json
{
  "email": "ahmad@company.com",
  "name": "Ahmad",
  "assignments": [
    { "department": "crm", "title": "Sales Manager" }
  ],
  "role": "user"
}
```

Response:

```json
{
  "ok": true,
  "user": { "id": 42, "email": "...", "name": "...", "role": "user" },
  "temporary_password": "A8xK9m2p",
  "assignments": [
    { "department": "crm", "title": "Sales Manager", "department_name": "CRM" }
  ]
}
```

**POST /api/staff/{id}/reset-password** response:

```json
{
  "ok": true,
  "temporary_password": "zQ4wR7nL",
  "message": "Show this password to the user once."
}
```

### 5.2 Access Control

**GET /api/departments** — modified to filter:

```python
def list_departments(user, db):
    if user.role in {"admin", "owner"}:
        return ALL departments
    else:
        # Return only departments assigned to the user
        rows = db.query(UserDepartment).filter(UserDepartment.user_id == user.id).all()
        dept_ids = [r.department_id for r in rows]
        depts = db.query(Department).filter(Department.id.in_(dept_ids)).all()
        return depts
```

**GET /api/auth/me/access** — new endpoint:

```python
@router.get("/me/access")
def my_access(user, db):
    assigned = db.query(UserDepartment).filter(UserDepartment.user_id == user.id).all()
    return {
        "role": user.role,
        "assigned_departments": [
            {
                "department": a.department.name,
                "title": a.title,
                "department_name": a.department.name.capitalize(),
            }
            for a in assigned
        ],
        "has_access": len(assigned) > 0 or user.role in {"admin", "owner"},
    }
```

## 6. Frontend

### 6.1 New Routes

| Route | Access | Component |
|---|---|---|
| `/staff` | admin, hr_manager | StaffManagement page |
| `/no-access` | any (non-admin, no depts) | NoAccessWall page |

### 6.2 Sidebar Changes

In `Layout.tsx`, the sidebar nav is filtered:

```typescript
// After fetching departments and user access:
const canManageStaff = user.role === 'admin' || user.role === 'hr_manager';
const visibleDepts = user.role === 'admin' || user.role === 'hr_manager'
  ? allDepts  // admin/HR see all, but HR only sees Staff Mgmt + own depts
  : assignedDepts;

// Staff Management link — shown only to admin/hr_manager
{canManageStaff && (
  <NavLink to="/staff">
    <Users className="h-4 w-4" />
    Staff
  </NavLink>
)}
```

### 6.3 Staff Management Page

File: `ui/src/pages/StaffManagement.tsx`

Route: `/staff`

Components:
- `StaffTable.tsx` — card/table pattern with rows for each staff member
- `StaffFormModal.tsx` — add/edit modal with email, name, role select, department multi-select
- `ResetPasswordModal.tsx` — shows temp password once with copy button

Data fetching:

```typescript
const staffQuery = useQuery({
  queryKey: ['staff'],
  queryFn: () => staffApi.list(),
});

const deptsQuery = useQuery({
  queryKey: ['departments'],
  queryFn: () => departmentsApi.list(),
});
```

### 6.4 Onboarding Integration

In `Onboarding.tsx` (Step 0), each selected department card gains extra fields:

```tsx
// Inside the department card for each selected dept
{selected.includes(key) && (
  <div className="mt-3 space-y-2 border-t border-surface-border pt-3">
    <div>
      <label className="label text-xs">Person in charge (email)</label>
      <input
        className="input"
        placeholder="ahmad@company.com"
        value={picEmails[key] || ''}
        onChange={(e) => setPicEmails(prev => ({ ...prev, [key]: e.target.value }))}
      />
    </div>
    <div>
      <label className="label text-xs">Title</label>
      <input
        className="input"
        placeholder="Sales Manager"
        value={picTitles[key] || ''}
        onChange={(e) => setPicTitles(prev => ({ ...prev, [key]: e.target.value }))}
      />
    </div>
  </div>
)}
```

On "Next" click, the SPA calls `POST /api/staff` for each PIC-email pair, collects temp passwords, and shows them on the Review step.

### 6.5 "No Access" Wall

File: `ui/src/pages/NoAccess.tsx`

Shown when:
- User is authenticated
- `user.role` is not `admin`
- `assigned_departments` array is empty

Route: Renders in place of the normal layout, no sidebar.

```tsx
export default function NoAccess() {
  const { logout } = useAuth();
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface-muted px-4">
      <div className="card max-w-md p-8 text-center">
        <Shield className="mx-auto mb-4 h-12 w-12 text-slate-300" />
        <h1 className="text-lg font-semibold text-slate-900">Access Restricted</h1>
        <p className="mt-2 text-sm text-slate-500">
          Your Shogun OS account hasn't been assigned to any department yet.
        </p>
        <p className="text-sm text-slate-500">
          Please contact your company admin to get access.
        </p>
        <button type="button" className="btn-secondary mt-6" onClick={() => logout()}>
          Sign Out
        </button>
      </div>
    </div>
  );
}
```

### 6.6 Settings Tab

The existing Settings tab in Department.tsx is hidden for non-admin users:

```typescript
const TABS = user.role === 'admin'
  ? ALL_TABS  // includes settings
  : ALL_TABS.filter(t => t.id !== 'settings');
```

Or simply: the Settings render block is wrapped in admin check (the backend endpoint already has `require_admin` via the existing `updateConfig` route).

### 6.7 Default Dashboard Redirect

In `Dashboard.tsx`, add a useEffect that checks user access and redirects non-admin users to their first assigned department:

```typescript
const { user } = useAuth();
const accessQuery = useQuery({
  queryKey: ['my-access'],
  queryFn: () => authApi.myAccess(),
});

// Redirect non-admin with no access
if (!accessQuery.isLoading && !accessQuery.data?.has_access && user.role !== 'admin') {
  return <Navigate to="/no-access" replace />;
}

// Redirect non-admin with assignments to first department
if (user.role !== 'admin' && accessQuery.data?.assigned_departments?.length) {
  return <Navigate to={`/department/${accessQuery.data.assigned_departments[0].department}`} replace />;
}
```

## 7. OAuth Flow Diagram

```
User visits /login
  → Clicks "Sign in with Google"
  → OAuth callback
  → _upsert_oauth_user()

  BACKEND LOGIC:
  → Is there an existing user with this email where is_temporary_password=True?
    → YES: Link OAuth identity, clear temp password, keep UserDepartment assignments
    → NO:
      → Is this the first user ever on this tenant?
        → YES: role = "admin" (current behavior)
        → NO: role = "user", create with zero UserDepartment rows

  SPA BEHAVIOR:
  → GET /api/auth/me/access
  → If has_access = False:
    → Show NoAccess wall
  → Else if role = "admin":
    → Show full Dashboard with all departments
  → Else:
    → Redirect to first assigned department
```

## 8. Access Check Matrix

| User Role | `/dashboard` | `/department/{x}` | `/staff` | Settings tab |
|---|---|---|---|---|
| `admin` | ✅ All depts | ✅ Any dept | ✅ Full CRUD | ✅ |
| `hr_manager` | ❌ Redirect | ✅ Only assigned | ✅ Read + add (no role change) | ❌ |
| `user` (has depts) | ❌ Redirect | ✅ Only assigned | ❌ | ❌ |
| `user` (no depts) | ❌ → NoAccess | ❌→ NoAccess | ❌ | ❌ |

## 9. Verification

1. Admin creates user via Staff Management → temp password shown → user logs in with it → forced password change → sees only assigned departments
2. OAuth self-registration with unlisted email → sees "No Access" wall
3. Admin assigns user to a department → on next page load, user sees that department
4. HR manager accesses Staff Management page → sees all staff, can add/edit but cannot change someone's role to admin
5. Non-admin user navigates to `/staff` → redirected to dashboard or shows 403
6. Settings tab hidden for non-admin users (frontend + backend gated)
7. Default dashboard redirects non-admin users to their first assigned department
8. Existing admin users unaffected — still see everything

## 10. Future Considerations

- Email delivery of temporary passwords via SMTP/API
- "Request access" button on NoAccess wall that sends a notification to admins
- Granular permissions system beyond 3 roles
- Audit log for staff changes
- Department head auto-promotion (assigning HR department → grants hr_manager role automatically)