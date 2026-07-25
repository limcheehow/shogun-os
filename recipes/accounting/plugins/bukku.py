#!/usr/bin/env python3
"""
Bukku Accounting Provider Plugin
─────────────────────────────────
Implements the accounting CONTRACT.md for Bukku (api.bukku.my).

Environment:
  ACCT_API_KEY     — Bukku API bearer token
  ACCT_SUBDOMAIN   — Bukku company subdomain (e.g. raubensdnbhd)
"""

import json
import os
import urllib.request
import urllib.error
import urllib.parse

API_KEY = os.environ.get("ACCT_API_KEY", "")
SUBDOMAIN = os.environ.get("ACCT_SUBDOMAIN", "")
BASE_URL = f"https://api.bukku.my"


def _headers():
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Company-Subdomain": SUBDOMAIN,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _api(method: str, path: str, data: dict = None, params: dict = None):
    """Call Bukku REST API."""
    url = f"{BASE_URL}{path}"
    if params:
        qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items() if v is not None)
        url = f"{url}?{qs}"

    req = urllib.request.Request(url, method=method, headers=_headers())
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
        {"name": "acct_list_sales_invoices", "description": "List sales invoices with filters",
         "inputSchema": {"type": "object", "properties": {
             "search": {"type": "string"}, "contact_id": {"type": "integer"},
             "date_from": {"type": "string"}, "date_to": {"type": "string"},
             "status": {"type": "string"}, "limit": {"type": "integer"}, "offset": {"type": "integer"}}}},
        {"name": "acct_create_sales_invoice", "description": "Create a sales invoice",
         "inputSchema": {"type": "object", "properties": {
             "contact_id": {"type": "integer"}, "date": {"type": "string"},
             "currency_code": {"type": "string"}, "exchange_rate": {"type": "number"},
             "number2": {"type": "string"}, "payment_mode": {"type": "string"},
             "status": {"type": "string"}, "tax_mode": {"type": "string"},
             "description": {"type": "string"}, "remarks": {"type": "string"},
             "billing_party": {"type": "string"}, "shipping_party": {"type": "string"},
             "term_items": {"type": "array"}, "deposit_items": {"type": "array"},
             "form_items": {"type": "array"}},
         "required": ["contact_id", "date", "payment_mode", "status", "tax_mode"]}},
        {"name": "acct_list_purchase_bills", "description": "List purchase bills with filters",
         "inputSchema": {"type": "object", "properties": {
             "search": {"type": "string"}, "contact_id": {"type": "integer"},
             "date_from": {"type": "string"}, "date_to": {"type": "string"},
             "status": {"type": "string"}, "limit": {"type": "integer"}, "offset": {"type": "integer"}}}},
        {"name": "acct_create_purchase_bill", "description": "Create a purchase bill",
         "inputSchema": {"type": "object", "properties": {
             "contact_id": {"type": "integer"}, "date": {"type": "string"},
             "currency_code": {"type": "string"}, "exchange_rate": {"type": "number"},
             "number2": {"type": "string"}, "payment_mode": {"type": "string"},
             "status": {"type": "string"}, "tax_mode": {"type": "string"},
             "description": {"type": "string"}, "billing_party": {"type": "string"},
             "form_items": {"type": "array"}},
         "required": ["contact_id", "date", "payment_mode", "status", "tax_mode"]}},
        {"name": "acct_list_contacts", "description": "List customers/suppliers",
         "inputSchema": {"type": "object", "properties": {
             "type": {"type": "string"}, "search": {"type": "string"},
             "limit": {"type": "integer"}, "offset": {"type": "integer"}}}},
        {"name": "acct_create_contact", "description": "Create a customer or supplier",
         "inputSchema": {"type": "object", "properties": {
             "name": {"type": "string"}, "email": {"type": "string"},
             "phone": {"type": "string"}, "type": {"type": "string"},
             "entity_type": {"type": "string"}, "reg_no": {"type": "string"},
             "billing_party": {"type": "string"}, "shipping_party": {"type": "string"}},
         "required": ["name", "type"]}},
        {"name": "acct_list_products", "description": "List products/services",
         "inputSchema": {"type": "object", "properties": {
             "search": {"type": "string"}, "limit": {"type": "integer"}, "offset": {"type": "integer"}}}},
        {"name": "acct_get_profit_loss", "description": "Get P&L for a date range",
         "inputSchema": {"type": "object", "properties": {
             "date_from": {"type": "string"}, "date_to": {"type": "string"}},
         "required": ["date_from", "date_to"]}},
        {"name": "acct_get_balance_sheet", "description": "Get balance sheet",
         "inputSchema": {"type": "object", "properties": {
             "as_of_date": {"type": "string"}}}},
        {"name": "acct_get_aging_report", "description": "Get AR/AP aging report",
         "inputSchema": {"type": "object", "properties": {
             "type": {"type": "string"}, "as_of_date": {"type": "string"}},
         "required": ["type"]}},
        {"name": "acct_update_invoice_status", "description": "Update invoice/bill status",
         "inputSchema": {"type": "object", "properties": {
             "id": {"type": "integer"}, "type": {"type": "string"}, "status": {"type": "string"}},
         "required": ["id", "type", "status"]}},
    ]


# ── Tool Handlers ────────────────────────────────────────────────────────

def handle_tool(name: str, args: dict) -> dict:
    """Dispatch tool call to the appropriate handler."""

    handlers = {
        "acct_list_sales_invoices": _list_sales_invoices,
        "acct_create_sales_invoice": _create_sales_invoice,
        "acct_list_purchase_bills": _list_purchase_bills,
        "acct_create_purchase_bill": _create_purchase_bill,
        "acct_list_contacts": _list_contacts,
        "acct_create_contact": _create_contact,
        "acct_list_products": _list_products,
        "acct_get_profit_loss": _get_profit_loss,
        "acct_get_balance_sheet": _get_balance_sheet,
        "acct_get_aging_report": _get_aging_report,
        "acct_update_invoice_status": _update_invoice_status,
    }

    handler = handlers.get(name)
    if not handler:
        return {"error": f"Not implemented: {name}", "code": "NOT_IMPLEMENTED"}
    return handler(args)


def _list_sales_invoices(args: dict) -> dict:
    params = {}
    if args.get("search"): params["search"] = args["search"]
    if args.get("contact_id"): params["contact_id"] = args["contact_id"]
    if args.get("date_from"): params["date_from"] = args["date_from"]
    if args.get("date_to"): params["date_to"] = args["date_to"]
    if args.get("status"): params["status"] = args["status"]
    if args.get("limit"): params["per_page"] = args["limit"]
    if args.get("offset"): params["page"] = args["offset"]

    data = _api("GET", "/sales/invoices", params=params)
    if "error" in data:
        return data

    invoices = []
    for inv in data.get("data", []):
        invoices.append({
            "id": inv.get("id"),
            "number": inv.get("number", ""),
            "number2": inv.get("number2", ""),
            "date": inv.get("date", ""),
            "contact_id": inv.get("contact_id"),
            "contact_name": inv.get("contact", {}).get("name", "") if isinstance(inv.get("contact"), dict) else "",
            "currency_code": inv.get("currency_code", "MYR"),
            "total": float(inv.get("total", 0)),
            "balance_due": float(inv.get("balance_due", 0)),
            "status": inv.get("status", ""),
            "payment_mode": inv.get("payment_mode", "credit"),
        })

    return {"invoices": invoices, "total": len(invoices)}


def _create_sales_invoice(args: dict) -> dict:
    payload = {
        "contact_id": args["contact_id"],
        "date": args["date"],
        "currency_code": args.get("currency_code", "MYR"),
        "exchange_rate": args.get("exchange_rate", 1),
        "payment_mode": args["payment_mode"],
        "status": args["status"],
        "tax_mode": args["tax_mode"],
    }
    for opt in ["number2", "description", "remarks", "billing_party", "shipping_party"]:
        if args.get(opt):
            payload[opt] = args[opt]
    if args.get("term_items"):
        payload["term_items"] = args["term_items"]
    if args.get("deposit_items"):
        payload["deposit_items"] = args["deposit_items"]
    if args.get("form_items"):
        payload["form_items"] = args["form_items"]

    data = _api("POST", "/sales/invoices", data=payload)
    if "error" in data:
        return data

    return {
        "id": data.get("id"),
        "number": data.get("number", ""),
        "status": data.get("status", ""),
        "total": float(data.get("total", 0)),
    }


def _list_purchase_bills(args: dict) -> dict:
    params = {}
    if args.get("search"): params["search"] = args["search"]
    if args.get("contact_id"): params["contact_id"] = args["contact_id"]
    if args.get("date_from"): params["date_from"] = args["date_from"]
    if args.get("date_to"): params["date_to"] = args["date_to"]
    if args.get("status"): params["status"] = args["status"]
    if args.get("limit"): params["per_page"] = args["limit"]
    if args.get("offset"): params["page"] = args["offset"]

    data = _api("GET", "/purchases/bills", params=params)
    if "error" in data:
        return data

    bills = []
    for bill in data.get("data", []):
        bills.append({
            "id": bill.get("id"),
            "number": bill.get("number", ""),
            "number2": bill.get("number2", ""),
            "date": bill.get("date", ""),
            "contact_id": bill.get("contact_id"),
            "contact_name": bill.get("contact", {}).get("name", "") if isinstance(bill.get("contact"), dict) else "",
            "currency_code": bill.get("currency_code", "MYR"),
            "total": float(bill.get("total", 0)),
            "balance_due": float(bill.get("balance_due", 0)),
            "status": bill.get("status", ""),
        })

    return {"bills": bills, "total": len(bills)}


def _create_purchase_bill(args: dict) -> dict:
    payload = {
        "contact_id": args["contact_id"],
        "date": args["date"],
        "currency_code": args.get("currency_code", "MYR"),
        "exchange_rate": args.get("exchange_rate", 1),
        "payment_mode": args["payment_mode"],
        "status": args["status"],
        "tax_mode": args["tax_mode"],
    }
    for opt in ["number2", "description", "billing_party"]:
        if args.get(opt):
            payload[opt] = args[opt]
    if args.get("form_items"):
        payload["form_items"] = args["form_items"]

    data = _api("POST", "/purchases/bills", data=payload)
    if "error" in data:
        return data

    return {
        "id": data.get("id"),
        "number": data.get("number", ""),
        "status": data.get("status", ""),
        "total": float(data.get("total", 0)),
    }


def _list_contacts(args: dict) -> dict:
    params = {"per_page": args.get("limit", 50)}
    if args.get("search"): params["search"] = args["search"]
    if args.get("type") and args["type"] != "all":
        params["type"] = args["type"]

    data = _api("GET", "/contacts", params=params)
    if "error" in data:
        return data

    contacts = []
    for c in data.get("data", []):
        contacts.append({
            "id": c.get("id"),
            "name": c.get("name", c.get("legal_name", "")),
            "email": c.get("email", ""),
            "phone": c.get("phone", ""),
            "type": "customer" if "customer" in c.get("types", []) else "supplier",
            "billing_party": c.get("billing_party", ""),
            "reg_no": c.get("reg_no", ""),
        })

    return {"contacts": contacts, "total": len(contacts)}


def _create_contact(args: dict) -> dict:
    payload = {
        "legal_name": args["name"],
        "other_name": args["name"],
        "types": [args["type"]] if args["type"] != "both" else ["customer", "supplier"],
        "entity_type": args.get("entity_type", "GENERAL_PUBLIC"),
    }
    for opt in ["email", "reg_no", "billing_party"]:
        if args.get(opt):
            payload[opt] = args[opt]
    if args.get("phone"):
        payload["phone_no"] = [{"number": args["phone"], "label": "main"}]

    data = _api("POST", "/contacts", data=payload)
    if "error" in data:
        return data

    return {"id": data.get("id"), "name": data.get("legal_name", ""), "type": args["type"]}


def _list_products(args: dict) -> dict:
    params = {"per_page": args.get("limit", 50)}
    if args.get("search"): params["search"] = args["search"]

    data = _api("GET", "/products", params=params)
    if "error" in data:
        return data

    products = []
    for p in data.get("data", []):
        products.append({
            "id": p.get("id"),
            "name": p.get("name", ""),
            "unit_label": p.get("unit_label", ""),
            "unit_price": float(p.get("unit_price", 0)),
            "account_id": p.get("account_id"),
            "account_name": p.get("account", {}).get("name", "") if isinstance(p.get("account"), dict) else "",
        })

    return {"products": products, "total": len(products)}


def _get_profit_loss(args: dict) -> dict:
    # Bukku doesn't have a native P&L endpoint; use the report endpoint
    params = {
        "date_from": args["date_from"],
        "date_to": args["date_to"],
        "type": "profit_loss",
    }
    data = _api("GET", "/reports", params=params)
    if "error" in data:
        return data

    return {
        "total_revenue": float(data.get("total_revenue", 0)),
        "total_expenses": float(data.get("total_expenses", 0)),
        "net_profit": float(data.get("net_profit", 0)),
        "revenue_accounts": [
            {"account_id": a.get("account_id"), "account_name": a.get("account_name"), "amount": float(a.get("amount", 0))}
            for a in data.get("revenue_accounts", [])
        ],
        "expense_accounts": [
            {"account_id": a.get("account_id"), "account_name": a.get("account_name"), "amount": float(a.get("amount", 0))}
            for a in data.get("expense_accounts", [])
        ],
    }


def _get_balance_sheet(args: dict) -> dict:
    params = {"type": "balance_sheet"}
    if args.get("as_of_date"): params["as_of_date"] = args["as_of_date"]

    data = _api("GET", "/reports", params=params)
    if "error" in data:
        return data

    return {
        "total_assets": float(data.get("total_assets", 0)),
        "total_liabilities": float(data.get("total_liabilities", 0)),
        "total_equity": float(data.get("total_equity", 0)),
        "asset_accounts": [
            {"account_id": a.get("account_id"), "account_name": a.get("account_name"), "amount": float(a.get("amount", 0))}
            for a in data.get("asset_accounts", [])
        ],
        "liability_accounts": [
            {"account_id": a.get("account_id"), "account_name": a.get("account_name"), "amount": float(a.get("amount", 0))}
            for a in data.get("liability_accounts", [])
        ],
        "equity_accounts": [
            {"account_id": a.get("account_id"), "account_name": a.get("account_name"), "amount": float(a.get("amount", 0))}
            for a in data.get("equity_accounts", [])
        ],
    }


def _get_aging_report(args: dict) -> dict:
    params = {"type": args["type"]}
    if args.get("as_of_date"): params["as_of_date"] = args["as_of_date"]

    data = _api("GET", "/reports/aging", params=params)
    if "error" in data:
        return data

    return {
        "type": args["type"],
        "as_of_date": args.get("as_of_date", ""),
        "total": float(data.get("total", 0)),
        "buckets": [
            {"range": b.get("range"), "total": float(b.get("total", 0))}
            for b in data.get("buckets", [])
        ],
        "items": [
            {
                "contact_id": i.get("contact_id"),
                "contact_name": i.get("contact_name", ""),
                "invoice_number": i.get("invoice_number", ""),
                "date": i.get("date", ""),
                "due_date": i.get("due_date", ""),
                "amount": float(i.get("amount", 0)),
                "days_overdue": i.get("days_overdue", 0),
            }
            for i in data.get("items", [])
        ],
    }


def _update_invoice_status(args: dict) -> dict:
    entity_type = args["type"]
    entity_id = args["id"]
    status = args["status"]

    if entity_type == "invoice":
        data = _api("PATCH", f"/sales/invoices/{entity_id}", data={"status": status})
    elif entity_type == "bill":
        data = _api("PATCH", f"/purchases/bills/{entity_id}", data={"status": status})
    else:
        return {"error": f"Unknown type: {entity_type}", "code": "MISSING_FIELD"}

    if "error" in data:
        return data

    return {
        "id": entity_id,
        "number": data.get("number", ""),
        "status": data.get("status", status),
    }