id: hr-staff-directory-contract
name: HR Staff Directory — Provider Contract
version: 1.0.0
description: "Standard API contract for HRMS staff directory sync providers."

# HR Staff Directory Contract

Any HRMS provider (BrioHR, BambooHR, Personio, etc.) implementing this contract must support the following operations. The provider maps these to its own API endpoints and returns the standard response shapes.

## Operations

### `hr_sync_employees()`

Fetch all active employees from the HRMS.

**Returns:** `List[Employee]`

```json
[
  {
    "email": "ahmad@company.com",
    "name": "Ahmad Bin Ali",
    "department": "CRM",
    "title": "Sales Manager",
    "phone": "+60123456789",
    "employee_id": "EMP-042",
    "manager_email": "cheehow@company.com",
    "role": "user",
    "status": "active"
  }
]
```

### `hr_sync_leave_balances()`

Fetch leave balances for all employees.

**Returns:** `List[LeaveBalance]`

```json
[
  {
    "email": "ahmad@company.com",
    "leave_type": "annual",
    "total_days": 14,
    "taken_days": 5,
    "remaining_days": 9,
    "carry_over": 2
  }
]
```

### `hr_lookup_employee(email: str) -> Employee | None`

Single employee lookup by email.

## Provider File Structure

```
providers/
├── briohr.md       # Reference implementation
├── bamboohr.md     # (future)
└── personio.md     # (future)
```

Each provider doc documents:
- API endpoints and authentication
- Field mapping to contract shapes
- Rate limiting considerations
- Sync frequency recommendations