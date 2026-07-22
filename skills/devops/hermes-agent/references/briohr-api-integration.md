# BrioHR API — Integration Notes

## Endpoint

```python
BASE = "https://static.api.briohr.com"
EMPLOYEES = "/v2/api/external/reports/employees-main-information/download?format=csv"
```

## Auth

Basic auth with company ID + password + context headers:

```python
headers = {
    "Authorization": f"Basic {base64.b64encode(f'{USERNAME}:{PASSWORD}'.encode()).decode()}",
    "x-api-context-company": COMPANY_ID,
    "x-resource-type": "employees-main-information",
}
```

## IP Whitelisting

BrioHR's API is **IP-whitelisted**. Even with correct credentials, the response is:

```
HTTP 403: {"type":"unhandled","message":"Forbidden","isBrioError":true}
```

**Auth validity check**: deliberately omit `x-api-context-company` or `x-resource-type` headers. A 400 "header required" response means authentication passed — the 403 is purely IP-based.

## Diagnostic Script

```python
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import base64

U, P, C = "USERNAME", "PASSWORD", "COMPANY_ID"

# Test 1: header required error = auth works
req = Request(url, headers={"Authorization": f"Basic {ENC}"})
# Expect: HTTP 400 "x-api-context-company header required"

# Test 2: full headers = if 403, IP blocked
req = Request(url, headers={
    "Authorization": f"Basic {ENC}",
    "x-api-context-company": C,
    "x-resource-type": "employees-main-information",
})
# Expect: HTTP 200 with CSV, or HTTP 403 if IP blocked
```

## Deployment Context

- Script: `~/brain/scripts/briohr-sync.py`
- Cron: 70887a2fe6cc (Mon 8am MYT)
- Data: `~/brain/data/briohr/`
- VPS outbound IP: 52.187.147.28