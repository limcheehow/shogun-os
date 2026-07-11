# Reading Google Sheets — Sheet Discovery & Read Patterns

## Problem

Calling `$GAPI sheets get SHEET_ID "Sheet1!A1:Z100"` fails with `400 Unable to parse range: Sheet1!A1:Z100` when the actual tab (sheet) has a different name — e.g. "Overview", "1_Tiles", "Transactions".

## 1. Discover Sheet Names First

Before any read/write, always resolve sheet names:

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_authorized_user_file('/home/user/.hermes/google_token.json')
service = build('sheets', 'v4', credentials=creds)

sheet_meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
for s in sheet_meta.get('sheets', []):
    props = s['properties']
    print(f"Sheet: {props['title']}, rows={props['gridProperties'].get('rowCount')}, cols={props['gridProperties'].get('columnCount')}")
```

## 2. Read with Correct Range

Once you have the correct sheet name:

```python
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID,
    range=f"{sheet_name}!A1:Z50"
).execute()
values = result.get('values', [])
```

### Pitfall: sheet names with dots/spaces

Tabs named like `"1.0 Preliminary"` or `"v2.1 Data"` need single-quoting:

```python
range_str = f"'{sheet_name}'!A1:Z50"  # Single-quote wraps the name
```

## 3. Sheets API falls back to first sheet on ambiguous ranges

If you pass just a range like `"A1:Z100"` without a sheet name prefix, the API defaults to the **first sheet** in the spreadsheet. This can silently give you the wrong tab. Always prefix with the explicit sheet name.

## 4. Read raw vs. formatted

By default the API returns the displayed value. For date/number/currency columns, use `valueRenderOption='FORMATTED_VALUE'` (default) to get what the user sees. For raw underlying values:

```python
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID,
    range=f"'{sheet_name}'!A1:Z50",
    valueRenderOption='UNFORMATTED_VALUE'  # Returns raw number/dates
).execute()
```

## 5. Verify with a metadata-only call first

```python
info = service.spreadsheets().get(
    spreadsheetId=SHEET_ID,
    fields="sheets(properties(sheetId,title,index),gridProperties(rowCount,columnCount,frozenRowCount))"
).execute()
```

This costs 1 API call and avoids downloading thousands of cells if the range is wrong.

## 7. Sheets API may reject native Google Sheets with "not supported for this document"

Sometimes the Sheets API returns `400 "This operation is not supported for this document"` even for a valid native Google Sheet ID. This appears to be a Drive permission/metadata quirk. Fix: export as .xlsx and read with openpyxl:

```python
import requests, openpyxl
from io import BytesIO

FILE_ID = "your_sheet_id"
headers = {"Authorization": f"Bearer {token}"}
resp = requests.get(
    f"https://docs.google.com/spreadsheets/d/{FILE_ID}/export?format=xlsx",
    headers=headers
)
resp.raise_for_status()
wb = openpyxl.load_workbook(BytesIO(resp.content))
for name in wb.sheetnames:
    ws = wb[name]
    print(f"Sheet: {name} (rows: {ws.max_row}, cols: {ws.max_column})")
    # Read all rows
    for row in ws.iter_rows(values_only=True):
        print([str(c) if c is not None else "" for c in row])
```

This bypasses the Sheets API entirely and works even when the API returns errors for that specific sheet. Limitations: no cell-level metadata (formatting, formulas, data validation) — use this for data extraction only.

## 6. Multi-tab Spreadsheets

When a spreadsheet has many tabs (e.g. shopping list with Overview, 1_Tiles, 2_Sanitary, ...), list them all and pick the right one by title or index:

```python
sheets = sheet_meta.get('sheets', [])
for s in sheets:
    print(f"  [{s['properties']['index']}] {s['properties']['title']}")
```

Then target by title:
```python
result = service.spreadsheets().values().get(
    spreadsheetId=SHEET_ID,
    range=f"'{sheets[target_idx]['properties']['title']}'!A1:Z50"
).execute()
```