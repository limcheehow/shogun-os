# Creating a Google Sheet via Direct API

`google_api.py` only supports `get`, `update`, and `append` on existing
spreadsheets. To **create** a new spreadsheet, use the Google Sheets API
directly with the same OAuth token.

## Recipe

```python
import os
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
token_path = os.path.expanduser("~/.hermes/google_token.json")

creds = Credentials.from_authorized_user_file(token_path, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(token_path, "w") as f:
        f.write(creds.to_json())

service = build("sheets", "v4", credentials=creds)

spreadsheet = {
    "properties": {"title": "My Spreadsheet Name"},
    "sheets": [
        {"properties": {"title": "Sheet1", "gridProperties": {"frozenRowCount": 1}}},
    ]
}

result = service.spreadsheets().create(body=spreadsheet, fields="spreadsheetId").execute()
sheet_id = result["spreadsheetId"]
print(f"https://docs.google.com/spreadsheets/d/{sheet_id}")
```

## Add headers immediately

```python
svc = service.spreadsheets().values()
svc.update(
    spreadsheetId=sheet_id, range="Sheet1!A1:G1",
    valueInputOption="USER_ENTERED",
    body={"values": [["Date", "Description", "Category", "Amount", "Type", "Source", "Notes"]]}
).execute()
```

## Add initial rows

```python
svc.append(
    spreadsheetId=sheet_id, range="Sheet1!A:G",
    valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
    body={"values": [["2026-05-01", "Opening Balance", "Cash", 50000.00, "balance", "Manual", "Estimate"]]}
).execute()
```

## Create multiple tabs

Pass a `sheets` list with multiple entries:
```python
spreadsheet = {
    "properties": {"title": "Title"},
    "sheets": [
        {"properties": {"title": "Transactions"}},
        {"properties": {"title": "Monthly Summary", "gridProperties": {"frozenRowCount": 1}}},
        {"properties": {"title": "Categories"}},
    ]
}
```

## Pitfalls

### 1. Sheet names with dots/spaces — single-quote A1 notation

If a sheet (tab) name contains dots, spaces, or special characters like `1.0 Preliminary`, the Sheets API **requires** single-quoting in the A1 range string. Without them you get `400: Requested writing within range [...], but tried writing to row [N]` because the parser splits on the dot.

**WRONG** (400 error):
```python
range_str = "1.0 Preliminary!A1:G10"
```

**RIGHT**:
```python
range_str = "'1.0 Preliminary'!A1:G10"
```

Use this helper to always quote sheet names defensively, even when the name seems safe:
```python
def a1_range(sheet_name: str, range_str: str) -> str:
    """Build a safely-quoted A1 range string."""
    return f"'{sheet_name}'!{range_str}"
```

**Always quote sheet names unconditionally** — it's harmless on clean names but catches dot-bearing names like `"3.0 Flooring"`, `"v2.1 Data"`, `"My.Sheet.Name"`.

### 2. Range must exactly cover the rows you write — off-by-one trap

When using `svc_values.update()` (not `append`), the range must **exactly match** the number of rows and columns you're writing. If your data has 14 rows but the range specifies 13, you get a 400 error.

The common bug: using `last_row = len(data)` when the data starts at row `N` instead of row 1.

**WRONG**:
```python
last_row = len(data)  # Only correct if start_row == 1
range_str = f"A{start_row}:G{last_row}"  # Off by N-1 if start_row > 1
```

**RIGHT**:
```python
start_row = int(re.search(r'\d+', start_cell).group())
last_row = start_row + len(data) - 1
```

### 3. Prefer `append()` over `update()` for new rows

When adding data to the end of a sheet (you don't know the exact next row number), use `append()` instead of `update()`:

```python
svc_values.append(
    spreadsheetId=sheet_id,
    range=f"'{sheet_name}'!A:G",  # Sheets API reads the last row from this
    valueInputOption="USER_ENTERED",
    insertDataOption="INSERT_ROWS",
    body={"values": rows}
).execute()
```

`append()` auto-detects the next empty row and avoids off-by-one range errors entirely.

### 4. Column letter arithmetic breaks past Z

`chr(ord('A') + N)` only works for columns A–Z (max 26 columns). For wider sheets, use a proper column-letter converter:

```python
def col_letter(n: int) -> str:
    """0-indexed column number → A1 notation letter(s)."""
    result = ""
    while n >= 0:
        result = chr(n % 26 + 65) + result
        n = n // 26 - 1
    return result

# Usage: col_letter(0) → 'A', col_letter(25) → 'Z', col_letter(26) → 'AA'
```

### 5. Frozen row count doesn't survive `create` in all cases

Setting `frozenRowCount: 2` in the `create` body works, but some tab names cause the property to be silently dropped. Verify after creation:

```python
props = service.spreadsheets().get(
    spreadsheetId=sheet_id,
    fields="sheets(properties(sheetId,title),gridProperties(frozenRowCount))"
).execute()
for sheet in props['sheets']:
    fp = sheet.get('gridProperties', {})
    print(f"{sheet['properties']['title']}: frozen={fp.get('frozenRowCount', 'MISSING!')}")
```

If a tab's frozenRowCount shows as MISSING, re-apply it with a separate request:

```python
requests = [{
    "updateSheetProperties": {
        "properties": {
            "sheetId": sheet_id_int,
            "gridProperties": {"frozenRowCount": 2}
        },
        "fields": "gridProperties.frozenRowCount"
    }
}]
service.spreadsheets().batchUpdate(
    spreadsheetId=sheet_id, body={"requests": requests}
).execute()
```
