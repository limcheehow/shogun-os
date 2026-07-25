#!/usr/bin/env python3
"""
QuickBooks Online Accounting Provider Plugin
─────────────────────────────────────────────
Implements the accounting CONTRACT.md for QuickBooks Online API.

Environment:
  ACCT_API_KEY     — OAuth access token (auto-refreshed via oauth-helper)
  ACCT_CLIENT_ID   — QuickBooks OAuth client ID
  ACCT_CLIENT_SECRET — QuickBooks OAuth client secret
  ACCT_REFRESH_TOKEN — OAuth refresh token
  ACCT_COMPANY_ID  — QuickBooks company/realm ID
"""

import json
import os
import urllib.request
import urllib.error
import urllib.parse

from oauth_helper import get_quickbooks_session, QB_TOKEN_URL, QB_SCOPES

COMPANY_ID = os.environ.get("ACCT_COMPANY_ID", "")
BASE_URL = f"https://quickbooks.api.intuit.com/v3/company/{COMPANY_ID}"
SANDBOX_URL = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{COMPANY_ID}"


def _get_access_token() -> str | None:
    """Get a valid access token, refreshing if necessary."""
    session = get_quickbooks_session()
    if session:
        return session.get("access_token")
    # Fallback to env var
    return os.environ.get("ACCT_API_KEY") or None


def _headers():
    token = _get_access_token()
    if not token:
        return {}
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _api(method: str, path: str, data: dict = None, params: dict = None):
    """Call QuickBooks Online API."""
    use_sandbox = os.environ.get("ACCT_SANDBOX", "false").lower() == "true"
    base = SANDBOX_URL if use_sandbox else BASE_URL
    url = f"{base}{path}"
    if params:
        qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items() if v is not None)
        url = f"{url}?{qs}"

    headers = _headers()
    if not headers.get("Authorization"):
        return {"error": "No valid access token", "code": "AUTH_FAILED"}

    req = urllib.request.Request(url, method=method, headers=headers)
    if data:
        req.data = json.dumps(data).encode()

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"error": f"HTTP {e.code}: {body}", "code": "PROVIDER_ERROR"}
    except Exception as e:
        return {"error": str(e), "code": "PROVIDER_ERROR"}


# ── Tool Schemas ─────────────────────────────────────────────────────────

def get_tool_schemas():
    return [
        {"name": "acct_list_sales_invoices", "description": "List sales invoices (QuickBooks: invoices)",
         "inputSchema": {"type": "object", "properties": {
             "search": {"type": "string"}, "contact_id": {"type": "string"},
             "date_from": {"type": "string"}, "date_to": {"type": "string"},
             "status": {"type": "string"}, "limit": {"type": "integer"}, "offset": {"type": "integer"}}}},
        {"name": "acct_create_sales_invoice", "description": "Create a sales invoice",
         "inputSchema": {"type": "object", "properties": {
             "contact_id": {"type": "string"}, "date": {"type": "string"},
             "currency_code": {"type": "string"}, "number2": {"type": "string"},
             "payment_mode": {"type": "string"}, "status": {"type": "string"},
             "description": {"type": "string"}, "form_items": {"type": "array"}},
         "required": ["contact_id", "date"]}},
        {"name": "acct_list_purchase_bills", "description": "List purchase bills (QuickBooks: bills)",
         "inputSchema": {"type": "object", "properties": {
             "search": {"type": "string"}, "contact_id": {"type": "string"},
             "date_from": {"type": "string"}, "date_to": {"type": "string"},
             "status": {"type": "string"}, "limit": {"type": "integer"}, "offset": {"type": "integer"}}}},
        {"name": "acct_create_purchase_bill", "description": "Create a purchase bill",
         "inputSchema": {"type": "object", "properties": {
             "contact_id": {"type": "string"}, "date": {"type": "string"},
             "currency_code": {"type": "string"}, "number2": {"type": "string"},
             "payment_mode": {"type": "string"}, "status": {"type": "string"},
             "description": {"type": "string"}, "form_items": {"type": "array"}},
         "required": ["contact_id", "date"]}},
        {"name": "acct_list_contacts", "description": "List customers/vendors",
         "inputSchema": {"type": "object", "properties": {
             "type": {"type": "string"}, "search": {"type": "string"},
             "limit": {"type": "integer"}, "offset": {"type": "integer"}}}},
        {"name": "acct_create_contact", "description": "Create a customer or vendor",
         "inputSchema": {"type": "object", "properties": {
             "name": {"type": "string"}, "email": {"type": "string"},
             "phone": {"type": "string"}, "type": {"type": "string"},
             "billing_party": {"type": "string"}},
         "required": ["name", "type"]}},
        {"name": "acct_list_products", "description": "List products/services (QBO: items)",
         "inputSchema": {"type": "object", "properties": {
             "search": {"type": "string"}, "limit": {"type": "integer"}, "offset": {"type": "integer"}}}},
        {"name": "acct_get_profit_loss", "description": "Get P&L for a date range",
         "inputSchema": {"type": "object", "properties": {
             "date_from": {"type": "string"}, "date_to": {"type": "string"}},
         "required": ["date_from", "date_to"]}},
        {"name": "acct_get_balance_sheet", "description": "Get balance sheet",
         "inputSchema": {"type": "object", "properties": {"as_of_date": {"type": "string"}}}},
        {"name": "acct_get_aging_report", "description": "Get AR/AP aging report",
         "inputSchema": {"type": "object", "properties": {
             "type": {"type": "string"}, "as_of_date": {"type": "string"}},
         "required": ["type"]}},
        {"name": "acct_update_invoice_status", "description": "Update invoice status",
         "inputSchema": {"type": "object", "properties": {
             "id": {"type": "string"}, "type": {"type": "string"}, "status": {"type": "string"}},
         "required": ["id", "type", "status"]}},
    ]


# ── Tool Handlers ────────────────────────────────────────────────────────

def handle_tool(name: str, args: dict) -> dict:
    handlers = {
        "acct_list_sales_invoices": _list_invoices,
        "acct_create_sales_invoice": _create_invoice,
        "acct_list_purchase_bills": _list_bills,
        "acct_create_purchase_bill": _create_bill,
        "acct_list_contacts": _list_contacts,
        "acct_create_contact": _create_contact,
        "acct_list_products": _list_products,
        "acct_get_profit_loss": _get_profit_loss,
        "acct_get_balance_sheet": _get_balance_sheet,
        "acct_get_aging_report": _get_aging_report,
        "acct_update_invoice_status": _update_status,
    }
    handler = handlers.get(name)
    if not handler:
        return {"error": f"Not implemented: {name}", "code": "NOT_IMPLEMENTED"}
    return handler(args)


def _query_qbo(endpoint: str, query: str = None, limit: int = 50) -> dict:
    """Query QBO using the query endpoint or direct read."""
    if query:
        return _api("GET", f"/query", params={"query": query, "minorversion": "65"})
    return _api("GET", f"/{endpoint}", params={"minorversion": "65"})


def _list_invoices(args: dict) -> dict:
    # QBO uses a query language
    conditions = []
    if args.get("date_from"):
        conditions.append(f"TxnDate >= '{args['date_from']}'")
    if args.get("date_to"):
        conditions.append(f"TxnDate <= '{args['date_to']}'")
    if args.get("status") and args["status"] == "ready":
        conditions.append("Balance > 0")

    where = " AND ".join(conditions) if conditions else ""
    query = f"SELECT * FROM Invoice WHERE {where} MAXRESULTS {args.get('limit', 50)}" if where else \
            f"SELECT * FROM Invoice MAXRESULTS {args.get('limit', 50)}"

    data = _api("GET", "/query", params={"query": query, "minorversion": "65"})
    if "error" in data:
        return data

    invoices = []
    for inv in data.get("QueryResponse", {}).get("Invoice", []):
        invoices.append({
            "id": inv.get("Id"),
            "number": inv.get("DocNumber", ""),
            "number2": inv.get("DocNumber", ""),
            "date": inv.get("TxnDate", ""),
            "contact_id": inv.get("CustomerRef", {}).get("value", ""),
            "contact_name": inv.get("CustomerRef", {}).get("name", ""),
            "currency_code": inv.get("CurrencyRef", {}).get("value", "USD"),
            "total": float(inv.get("TotalAmt", 0)),
            "balance_due": float(inv.get("Balance", 0)),
            "status": "ready" if float(inv.get("Balance", 0)) > 0 else "paid",
        })

    return {"invoices": invoices, "total": len(invoices)}


def _create_invoice(args: dict) -> dict:
    payload = {
        "Line": [],
        "CustomerRef": {"value": args["contact_id"]},
        "TxnDate": args["date"],
    }
    if args.get("currency_code"):
        payload["CurrencyRef"] = {"value": args["currency_code"]}
    if args.get("number2"):
        payload["DocNumber"] = args["number2"]

    for item in args.get("form_items", []):
        line = {
            "DetailType": "SalesItemLineDetail",
            "Amount": float(item.get("quantity", 1)) * float(item.get("unit_price", 0)),
            "SalesItemLineDetail": {
                "ItemRef": {"value": str(item.get("product_id", "1"))},
                "Qty": float(item.get("quantity", 1)),
                "UnitPrice": float(item.get("unit_price", 0)),
            },
            "Description": item.get("description", ""),
        }
        payload["Line"].append(line)

    data = _api("POST", "/invoice", data=payload)
    if "error" in data:
        return data

    inv = data.get("Invoice", {})
    return {
        "id": inv.get("Id"),
        "number": inv.get("DocNumber", ""),
        "status": "ready",
        "total": float(inv.get("TotalAmt", 0)),
    }


def _list_bills(args: dict) -> dict:
    conditions = []
    if args.get("date_from"):
        conditions.append(f"TxnDate >= '{args['date_from']}'")
    if args.get("date_to"):
        conditions.append(f"TxnDate <= '{args['date_to']}'")

    where = " AND ".join(conditions) if conditions else ""
    query = f"SELECT * FROM Bill WHERE {where} MAXRESULTS {args.get('limit', 50)}" if where else \
            f"SELECT * FROM Bill MAXRESULTS {args.get('limit', 50)}"

    data = _api("GET", "/query", params={"query": query, "minorversion": "65"})
    if "error" in data:
        return data

    bills = []
    for bill in data.get("QueryResponse", {}).get("Bill", []):
        bills.append({
            "id": bill.get("Id"),
            "number": bill.get("DocNumber", ""),
            "number2": bill.get("DocNumber", ""),
            "date": bill.get("TxnDate", ""),
            "contact_id": bill.get("VendorRef", {}).get("value", ""),
            "contact_name": bill.get("VendorRef", {}).get("name", ""),
            "currency_code": bill.get("CurrencyRef", {}).get("value", "USD"),
            "total": float(bill.get("TotalAmt", 0)),
            "balance_due": float(bill.get("Balance", 0)),
            "status": "ready",
        })

    return {"bills": bills, "total": len(bills)}


def _create_bill(args: dict) -> dict:
    payload = {
        "Line": [],
        "VendorRef": {"value": args["contact_id"]},
        "TxnDate": args["date"],
    }
    if args.get("currency_code"):
        payload["CurrencyRef"] = {"value": args["currency_code"]}
    if args.get("number2"):
        payload["DocNumber"] = args["number2"]

    for item in args.get("form_items", []):
        line = {
            "DetailType": "AccountBasedExpenseLineDetail",
            "Amount": float(item.get("quantity", 1)) * float(item.get("unit_price", 0)),
            "AccountBasedExpenseLineDetail": {
                "AccountRef": {"value": str(item.get("account_id", "1"))},
                "BillableStatus": "Billable",
            },
            "Description": item.get("description", ""),
        }
        payload["Line"].append(line)

    data = _api("POST", "/bill", data=payload)
    if "error" in data:
        return data

    bill = data.get("Bill", {})
    return {
        "id": bill.get("Id"),
        "number": bill.get("DocNumber", ""),
        "status": "ready",
        "total": float(bill.get("TotalAmt", 0)),
    }


def _list_contacts(args: dict) -> dict:
    entity_type = "Customer" if args.get("type") == "customer" else \
                  "Vendor" if args.get("type") == "supplier" else "Customer"
    query = f"SELECT * FROM {entity_type} MAXRESULTS {args.get('limit', 50)}"
    if args.get("search"):
        query = f"SELECT * FROM {entity_type} WHERE DisplayName LIKE '%{args['search']}%' MAXRESULTS {args.get('limit', 50)}"

    data = _api("GET", "/query", params={"query": query, "minorversion": "65"})
    if "error" in data:
        return data

    key = "Customer" if entity_type == "Customer" else "Vendor"
    contacts = []
    for c in data.get("QueryResponse", {}).get(key, []):
        contacts.append({
            "id": c.get("Id"),
            "name": c.get("DisplayName", ""),
            "email": c.get("PrimaryEmailAddr", {}).get("Address", "") if c.get("PrimaryEmailAddr") else "",
            "phone": c.get("PrimaryPhone", {}).get("FreeFormNumber", "") if c.get("PrimaryPhone") else "",
            "type": "customer" if entity_type == "Customer" else "supplier",
            "billing_party": "",
        })

    return {"contacts": contacts, "total": len(contacts)}


def _create_contact(args: dict) -> dict:
    if args["type"] in ("customer", "both"):
        payload = {
            "DisplayName": args["name"],
            "GivenName": args["name"].split()[0] if args["name"].split() else args["name"],
            "FamilyName": " ".join(args["name"].split()[1:]) if len(args["name"].split()) > 1 else "",
        }
        if args.get("email"):
            payload["PrimaryEmailAddr"] = {"Address": args["email"]}
        if args.get("phone"):
            payload["PrimaryPhone"] = {"FreeFormNumber": args["phone"]}
        cust_data = _api("POST", "/customer", data=payload)
        if "error" in cust_data:
            return cust_data
        customer_id = cust_data.get("Customer", {}).get("Id")

    if args["type"] in ("supplier", "both"):
        payload = {"DisplayName": args["name"]}
        if args.get("email"):
            payload["PrimaryEmailAddr"] = {"Address": args["email"]}
        if args.get("phone"):
            payload["PrimaryPhone"] = {"FreeFormNumber": args["phone"]}
        vend_data = _api("POST", "/vendor", data=payload)
        if "error" in vend_data:
            return vend_data
        supplier_id = vend_data.get("Vendor", {}).get("Id")

    if args["type"] == "both":
        return {"id": customer_id, "name": args["name"], "type": "both"}
    elif args["type"] == "customer":
        return {"id": customer_id, "name": args["name"], "type": "customer"}
    elif args["type"] == "supplier":
        return {"id": supplier_id, "name": args["name"], "type": "supplier"}

    return {"error": "Unknown contact type", "code": "MISSING_FIELD"}


def _list_products(args: dict) -> dict:
    query = f"SELECT * FROM Item MAXRESULTS {args.get('limit', 50)}"
    if args.get("search"):
        query = f"SELECT * FROM Item WHERE Name LIKE '%{args['search']}%' MAXRESULTS {args.get('limit', 50)}"

    data = _api("GET", "/query", params={"query": query, "minorversion": "65"})
    if "error" in data:
        return data

    products = []
    for p in data.get("QueryResponse", {}).get("Item", []):
        products.append({
            "id": p.get("Id"),
            "name": p.get("Name", ""),
            "unit_label": p.get("QtyOnHand", "") if p.get("Type") == "Inventory" else "Unit",
            "unit_price": float(p.get("UnitPrice", 0)),
            "account_id": p.get("IncomeAccountRef", {}).get("value", "") if p.get("IncomeAccountRef") else "",
            "account_name": "",
        })

    return {"products": products, "total": len(products)}


def _get_profit_loss(args: dict) -> dict:
    data = _api("GET", "/reports/ProfitAndLoss",
                params={"start_date": args["date_from"], "end_date": args["date_to"], "minorversion": "65"})
    if "error" in data:
        return data

    # Parse QBO report structure
    rows = data.get("Rows", {}).get("Row", [])
    revenue_accounts = []
    expense_accounts = []
    total_revenue = 0
    total_expenses = 0

    for section in rows:
        section_name = (section.get("Header", {}).get("ColData", [{}])[0].get("value", "") if
                        section.get("Header", {}).get("ColData") else "")
        section_rows = section.get("Rows", {}).get("Row", []) if section.get("Rows") else []
        summary = section.get("Summary", {}).get("ColData", [{}])[0].get("value", "0") if section.get("Summary", {}).get("ColData") else "0"

        if "Income" in section_name:
            total_revenue = float(summary.replace(",", ""))
            for row in section_rows:
                cols = row.get("ColData", [])
                if len(cols) >= 2:
                    revenue_accounts.append({
                        "account_id": "",
                        "account_name": cols[0].get("value", ""),
                        "amount": float(cols[1].get("value", "0").replace(",", "")) if cols[1].get("value") else 0,
                    })
        elif "Expense" in section_name:
            total_expenses = float(summary.replace(",", ""))
            for row in section_rows:
                cols = row.get("ColData", [])
                if len(cols) >= 2:
                    expense_accounts.append({
                        "account_id": "",
                        "account_name": cols[0].get("value", ""),
                        "amount": float(cols[1].get("value", "0").replace(",", "")) if cols[1].get("value") else 0,
                    })

    return {
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "net_profit": total_revenue - total_expenses,
        "revenue_accounts": revenue_accounts,
        "expense_accounts": expense_accounts,
    }


def _get_balance_sheet(args: dict) -> dict:
    params = {"minorversion": "65"}
    if args.get("as_of_date"):
        params["end_date"] = args["as_of_date"]

    data = _api("GET", "/reports/BalanceSheet", params=params)
    if "error" in data:
        return data

    # Parse QBO balance sheet report structure
    rows = data.get("Rows", {}).get("Row", [])
    asset_accounts = []
    liability_accounts = []
    equity_accounts = []
    total_assets = 0
    total_liabilities = 0
    total_equity = 0

    for section in rows:
        section_name = (section.get("Header", {}).get("ColData", [{}])[0].get("value", "") if
                        section.get("Header", {}).get("ColData") else "")
        section_rows = section.get("Rows", {}).get("Row", []) if section.get("Rows") else []
        summary = section.get("Summary", {}).get("ColData", [{}])[0].get("value", "0") if section.get("Summary", {}).get("ColData") else "0"

        if "Asset" in section_name:
            total_assets = float(summary.replace(",", ""))
            for row in section_rows:
                cols = row.get("ColData", [])
                if len(cols) >= 2:
                    asset_accounts.append({
                        "account_id": "",
                        "account_name": cols[0].get("value", ""),
                        "amount": float(cols[1].get("value", "0").replace(",", "")) if cols[1].get("value") else 0,
                    })
        elif "Liability" in section_name:
            total_liabilities = float(summary.replace(",", ""))
            for row in section_rows:
                cols = row.get("ColData", [])
                if len(cols) >= 2:
                    liability_accounts.append({
                        "account_id": "",
                        "account_name": cols[0].get("value", ""),
                        "amount": float(cols[1].get("value", "0").replace(",", "")) if cols[1].get("value") else 0,
                    })
        elif "Equity" in section_name:
            total_equity = float(summary.replace(",", ""))
            for row in section_rows:
                cols = row.get("ColData", [])
                if len(cols) >= 2:
                    equity_accounts.append({
                        "account_id": "",
                        "account_name": cols[0].get("value", ""),
                        "amount": float(cols[1].get("value", "0").replace(",", "")) if cols[1].get("value") else 0,
                    })

    return {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "total_equity": total_equity,
        "asset_accounts": asset_accounts,
        "liability_accounts": liability_accounts,
        "equity_accounts": equity_accounts,
    }


def _get_aging_report(args: dict) -> dict:
    report_type = "AgedReceivables" if args["type"] == "receivable" else "AgedPayables"
    data = _api("GET", f"/reports/{report_type}", params={"minorversion": "65"})
    if "error" in data:
        return data

    return {
        "type": args["type"],
        "as_of_date": args.get("as_of_date", ""),
        "total": float(data.get("Header", {}).get("Total", 0)),
        "buckets": [],
        "items": [],
    }


def _update_status(args: dict) -> dict:
    # QBO uses void operation
    entity_type = "invoice" if args["type"] == "invoice" else "bill"
    if args["status"] == "void":
        data = _api("POST", f"/{entity_type}/{args['id']}/void", params={"minorversion": "65"})
    else:
        return {"error": "QBO only supports void via this endpoint", "code": "NOT_IMPLEMENTED"}

    if "error" in data:
        return data
    return {"id": args["id"], "number": "", "status": "void"}