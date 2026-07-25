#!/usr/bin/env python3
"""
Xero Accounting Provider Plugin
────────────────────────────────
Implements the accounting CONTRACT.md for Xero API.

Environment:
  ACCT_API_KEY     — OAuth access token (auto-refreshed via oauth-helper)
  ACCT_CLIENT_ID   — Xero OAuth client ID
  ACCT_CLIENT_SECRET — Xero OAuth client secret
  ACCT_REFRESH_TOKEN — OAuth refresh token
  ACCT_TENANT_ID   — Xero organisation/tenant ID
"""

import json
import os
import urllib.request
import urllib.error
import urllib.parse

from oauth_helper import get_xero_session, XERO_TOKEN_URL, XERO_SCOPES

TENANT_ID = os.environ.get("ACCT_TENANT_ID", "")
BASE_URL = "https://api.xero.com/api.xro/2.0"


def _get_access_token() -> str | None:
    """Get a valid access token, refreshing if necessary."""
    session = get_xero_session()
    if session:
        return session.get("access_token")
    return os.environ.get("ACCT_API_KEY") or None


def _headers():
    token = _get_access_token()
    if not token:
        return {}
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Xero-tenant-id": TENANT_ID,
        "Content-Type": "application/json",
    }


def _api(method: str, path: str, data: dict = None, params: dict = None):
    """Call Xero API."""
    url = f"{BASE_URL}{path}"
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
        {"name": "acct_list_sales_invoices", "description": "List sales invoices",
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
        {"name": "acct_list_purchase_bills", "description": "List purchase bills",
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
        {"name": "acct_list_contacts", "description": "List contacts",
         "inputSchema": {"type": "object", "properties": {
             "type": {"type": "string"}, "search": {"type": "string"},
             "limit": {"type": "integer"}, "offset": {"type": "integer"}}}},
        {"name": "acct_create_contact", "description": "Create a contact",
         "inputSchema": {"type": "object", "properties": {
             "name": {"type": "string"}, "email": {"type": "string"},
             "phone": {"type": "string"}, "type": {"type": "string"},
             "billing_party": {"type": "string"}},
         "required": ["name", "type"]}},
        {"name": "acct_list_products", "description": "List products/services (Xero: items)",
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


def _list_invoices(args: dict) -> dict:
    params = {}
    if args.get("date_from"): params["DateFrom"] = args["date_from"]
    if args.get("date_to"): params["DateTo"] = args["date_to"]
    if args.get("status"): params["Status"] = args["status"].upper()
    if args.get("limit"): params["pageSize"] = args["limit"]

    data = _api("GET", "/Invoices", params=params)
    if "error" in data:
        return data

    invoices = []
    for inv in data.get("Invoices", []):
        invoices.append({
            "id": inv.get("InvoiceID"),
            "number": inv.get("InvoiceNumber", ""),
            "number2": inv.get("Reference", ""),
            "date": inv.get("Date", ""),
            "contact_id": inv.get("Contact", {}).get("ContactID", ""),
            "contact_name": inv.get("Contact", {}).get("Name", ""),
            "currency_code": inv.get("CurrencyCode", "USD"),
            "total": float(inv.get("Total", 0)),
            "balance_due": float(inv.get("AmountDue", 0)),
            "status": inv.get("Status", ""),
        })

    return {"invoices": invoices, "total": len(invoices)}


def _create_invoice(args: dict) -> dict:
    line_items = []
    for item in args.get("form_items", []):
        line_items.append({
            "Description": item.get("description", ""),
            "Quantity": float(item.get("quantity", 1)),
            "UnitAmount": float(item.get("unit_price", 0)),
            "AccountCode": str(item.get("account_id", "200")),
        })

    payload = {
        "Type": "ACCREC",
        "Contact": {"ContactID": args["contact_id"]},
        "Date": args["date"],
        "LineItems": line_items,
        "Status": "AUTHORISED" if args.get("status") == "ready" else "DRAFT",
    }
    if args.get("number2"):
        payload["Reference"] = args["number2"]
    if args.get("currency_code"):
        payload["CurrencyCode"] = args["currency_code"]

    data = _api("POST", "/Invoices", data=payload)
    if "error" in data:
        return data

    inv = data.get("Invoices", [{}])[0]
    return {
        "id": inv.get("InvoiceID"),
        "number": inv.get("InvoiceNumber", ""),
        "status": inv.get("Status", ""),
        "total": float(inv.get("Total", 0)),
    }


def _list_bills(args: dict) -> dict:
    params = {"Type": "ACCPAY"}
    if args.get("date_from"): params["DateFrom"] = args["date_from"]
    if args.get("date_to"): params["DateTo"] = args["date_to"]
    if args.get("status"): params["Status"] = args["status"].upper()
    if args.get("limit"): params["pageSize"] = args["limit"]

    data = _api("GET", "/Invoices", params=params)
    if "error" in data:
        return data

    bills = []
    for bill in data.get("Invoices", []):
        bills.append({
            "id": bill.get("InvoiceID"),
            "number": bill.get("InvoiceNumber", ""),
            "number2": bill.get("Reference", ""),
            "date": bill.get("Date", ""),
            "contact_id": bill.get("Contact", {}).get("ContactID", ""),
            "contact_name": bill.get("Contact", {}).get("Name", ""),
            "currency_code": bill.get("CurrencyCode", "USD"),
            "total": float(bill.get("Total", 0)),
            "balance_due": float(bill.get("AmountDue", 0)),
            "status": bill.get("Status", ""),
        })

    return {"bills": bills, "total": len(bills)}


def _create_bill(args: dict) -> dict:
    line_items = []
    for item in args.get("form_items", []):
        line_items.append({
            "Description": item.get("description", ""),
            "Quantity": float(item.get("quantity", 1)),
            "UnitAmount": float(item.get("unit_price", 0)),
            "AccountCode": str(item.get("account_id", "200")),
        })

    payload = {
        "Type": "ACCPAY",
        "Contact": {"ContactID": args["contact_id"]},
        "Date": args["date"],
        "LineItems": line_items,
        "Status": "AUTHORISED" if args.get("status") == "ready" else "DRAFT",
    }
    if args.get("number2"):
        payload["Reference"] = args["number2"]
    if args.get("currency_code"):
        payload["CurrencyCode"] = args["currency_code"]

    data = _api("POST", "/Invoices", data=payload)
    if "error" in data:
        return data

    bill = data.get("Invoices", [{}])[0]
    return {
        "id": bill.get("InvoiceID"),
        "number": bill.get("InvoiceNumber", ""),
        "status": bill.get("Status", ""),
        "total": float(bill.get("Total", 0)),
    }


def _list_contacts(args: dict) -> dict:
    params = {}
    if args.get("search"): params["where"] = f'Name.Contains("{args["search"]}")'
    if args.get("limit"): params["pageSize"] = args["limit"]

    data = _api("GET", "/Contacts", params=params)
    if "error" in data:
        return data

    contacts = []
    for c in data.get("Contacts", []):
        contacts.append({
            "id": c.get("ContactID"),
            "name": c.get("Name", ""),
            "email": c.get("EmailAddress", ""),
            "phone": c.get("Phones", [{}])[0].get("PhoneNumber", "") if c.get("Phones") else "",
            "type": "supplier" if c.get("IsSupplier") else "customer",
            "billing_party": c.get("Addresses", [{}])[0].get("AddressLine1", "") if c.get("Addresses") else "",
        })

    return {"contacts": contacts, "total": len(contacts)}


def _create_contact(args: dict) -> dict:
    payload = {
        "Name": args["name"],
        "IsCustomer": args["type"] in ("customer", "both"),
        "IsSupplier": args["type"] in ("supplier", "both"),
    }
    if args.get("email"):
        payload["EmailAddress"] = args["email"]

    data = _api("POST", "/Contacts", data=payload)
    if "error" in data:
        return data

    c = data.get("Contacts", [{}])[0]
    return {"id": c.get("ContactID"), "name": c.get("Name", ""), "type": args["type"]}


def _list_products(args: dict) -> dict:
    params = {}
    if args.get("limit"): params["pageSize"] = args["limit"]

    data = _api("GET", "/Items", params=params)
    if "error" in data:
        return data

    products = []
    for p in data.get("Items", []):
        products.append({
            "id": p.get("ItemID"),
            "name": p.get("Name", ""),
            "unit_label": p.get("Unit", "Each"),
            "unit_price": float(p.get("SalesDetails", {}).get("UnitPrice", 0)),
            "account_id": p.get("SalesDetails", {}).get("AccountCode", ""),
            "account_name": "",
        })

    return {"products": products, "total": len(products)}


def _get_profit_loss(args: dict) -> dict:
    data = _api("GET", "/Reports/ProfitAndLoss",
                params={"fromDate": args["date_from"], "toDate": args["date_to"]})
    if "error" in data:
        return data

    # Parse Xero report structure
    rows = data.get("Rows", [])
    revenue_accounts = []
    expense_accounts = []
    total_revenue = 0
    total_expenses = 0

    for section in rows:
        section_name = section.get("Title", "")
        section_rows = section.get("Rows", [])
        for row in section_rows:
            cells = row.get("Cells", [])
            if len(cells) >= 2:
                account_name = cells[0].get("Value", "")
                amount = float(cells[1].get("Value", 0) or 0)
                if "Revenue" in section_name or "Income" in section_name:
                    if account_name != "Total Revenue" and account_name != "Total Income":
                        revenue_accounts.append({"account_id": "", "account_name": account_name, "amount": amount})
                    else:
                        total_revenue = amount
                elif "Expense" in section_name:
                    if account_name != "Total Expenses":
                        expense_accounts.append({"account_id": "", "account_name": account_name, "amount": amount})
                    else:
                        total_expenses = amount

    return {
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "net_profit": total_revenue - total_expenses,
        "revenue_accounts": revenue_accounts,
        "expense_accounts": expense_accounts,
    }


def _get_balance_sheet(args: dict) -> dict:
    params = {"date": args.get("as_of_date", "")} if args.get("as_of_date") else {}
    data = _api("GET", "/Reports/BalanceSheet", params=params)
    if "error" in data:
        return data

    # Parse Xero balance sheet report structure
    rows = data.get("Rows", [])
    asset_accounts = []
    liability_accounts = []
    equity_accounts = []
    total_assets = 0
    total_liabilities = 0
    total_equity = 0

    for section in rows:
        section_name = section.get("Title", "")
        section_rows = section.get("Rows", [])
        for row in section_rows:
            cells = row.get("Cells", [])
            if len(cells) >= 2:
                account_name = cells[0].get("Value", "")
                amount = float(cells[1].get("Value", 0) or 0)
                if "Asset" in section_name:
                    if account_name != "Total Assets":
                        asset_accounts.append({"account_id": "", "account_name": account_name, "amount": amount})
                    else:
                        total_assets = amount
                elif "Liability" in section_name:
                    if account_name != "Total Liabilities":
                        liability_accounts.append({"account_id": "", "account_name": account_name, "amount": amount})
                    else:
                        total_liabilities = amount
                elif "Equity" in section_name:
                    if account_name != "Total Equity":
                        equity_accounts.append({"account_id": "", "account_name": account_name, "amount": amount})
                    else:
                        total_equity = amount

    return {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "total_equity": total_equity,
        "asset_accounts": asset_accounts,
        "liability_accounts": liability_accounts,
        "equity_accounts": equity_accounts,
    }


def _get_aging_report(args: dict) -> dict:
    report = "AgedReceivablesByContact" if args["type"] == "receivable" else "AgedPayablesByContact"
    data = _api("GET", f"/Reports/{report}")
    if "error" in data:
        return data

    return {
        "type": args["type"],
        "as_of_date": args.get("as_of_date", ""),
        "total": 0,
        "buckets": [],
        "items": [],
    }


def _update_status(args: dict) -> dict:
    entity_type = "Invoices"
    status = "VOIDED" if args["status"] == "void" else "DELETED" if args["status"] == "draft" else "AUTHORISED"

    payload = {
        "Invoices": [{"InvoiceID": args["id"], "Status": status}]
    }

    data = _api("POST", f"/{entity_type}", data=payload)
    if "error" in data:
        return data
    return {"id": args["id"], "number": "", "status": status.lower()}