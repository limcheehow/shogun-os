#!/usr/bin/env python3
"""
Time Tracking Bridge — Jibble Provider
───────────────────────────────────────
Maps standard tt_* tools to Jibble REST API v1.
Configure as an MCP server in config.yaml:

    mcp_servers:
      time-tracking:
        command: python3
        args: [~/.hermes/scripts/tt-bridge-jibble.py]
        env:
          TT_API_KEY: "${TT_API_KEY}"

Requires: TT_API_KEY env var (from Jibble Integrations → API Keys)
"""

import json, os, sys, urllib.request, urllib.error
from datetime import date, datetime

API_KEY = os.environ.get("TT_API_KEY", "") or os.environ.get("JIBBLE_API_KEY", "")
BASE_URL = os.environ.get("TT_BASE_URL", "https://api.jibble.io/v1")


def api(path, params=None, method="GET", data=None):
    """Call Jibble REST API."""
    url = f"{BASE_URL}{path}"
    if params:
        qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items() if v)
        url = f"{url}?{qs}"
    
    req = urllib.request.Request(url, method=method)
    req.add_header("X-Api-Key", API_KEY)
    req.add_header("Content-Type", "application/json")
    
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


# ── Tool implementations ──

def tool_current_status(args):
    """Who's clocked in right now."""
    data = api("/entries", {"status": "active"})
    if "error" in data:
        return data
    members = {m["id"]: m for m in api("/members", {"status": "active"}).get("data", [])}
    active = []
    for entry in data.get("data", []):
        if entry.get("isActive"):
            m = members.get(entry.get("memberId"), {})
            now = datetime.utcnow()
            clock_in = entry.get("clockIn", "")
            elapsed = 0
            if clock_in:
                try:
                    start = datetime.fromisoformat(clock_in.replace("Z", "+00:00"))
                    elapsed = int((now - start).total_seconds() / 60)
                except: pass
            active.append({
                "memberId": entry["memberId"],
                "name": m.get("displayName", "Unknown"),
                "clockIn": clock_in,
                "elapsedMinutes": elapsed,
            })
    return {"active": active}


def tool_get_entries(args):
    """Get time entries for date range."""
    params = {
        "from": args.get("from"),
        "to": args.get("to", args.get("from")),
        "memberId": args.get("memberId"),
        "projectId": args.get("projectId"),
        "limit": args.get("limit", 100),
    }
    data = api("/entries", params)
    if "error" in data:
        return data
    
    members = {m["id"]: m for m in api("/members").get("data", [])}
    projects = {p["id"]: p for p in api("/projects").get("data", [])}
    
    entries = []
    for entry in data.get("data", []):
        m = members.get(entry.get("memberId"), {})
        p = projects.get(entry.get("projectId"), {})
        total_min = 0
        if entry.get("clockIn") and entry.get("clockOut"):
            try:
                ci = datetime.fromisoformat(entry["clockIn"].replace("Z", "+00:00"))
                co = datetime.fromisoformat(entry["clockOut"].replace("Z", "+00:00"))
                total_min = int((co - ci).total_seconds() / 60)
            except: pass
        
        entries.append({
            "entryId": entry.get("id"),
            "memberId": entry.get("memberId"),
            "memberName": m.get("displayName", "Unknown"),
            "projectId": entry.get("projectId"),
            "projectName": p.get("name", ""),
            "clockIn": entry.get("clockIn"),
            "clockOut": entry.get("clockOut"),
            "totalMinutes": total_min,
            "status": "completed" if entry.get("clockOut") else "active",
            "gpsLatitude": entry.get("latitude"),
            "gpsLongitude": entry.get("longitude"),
        })
    
    return {"entries": entries, "total": len(entries)}


def tool_get_members(args):
    """List team members."""
    data = api("/members", {"status": args.get("status", "active")})
    if "error" in data:
        return data
    return {
        "members": [
            {
                "memberId": m.get("id"),
                "name": m.get("displayName"),
                "email": m.get("email", ""),
                "role": m.get("role", ""),
                "status": m.get("status", "active"),
                "hourlyRate": m.get("hourlyRate", 0),
            }
            for m in data.get("data", [])
        ]
    }


def tool_get_projects(args):
    """List projects."""
    data = api("/projects", {"status": args.get("status", "active")})
    if "error" in data:
        return data
    return {
        "projects": [
            {
                "projectId": p.get("id"),
                "name": p.get("name"),
                "description": p.get("description", ""),
                "status": p.get("status", "active"),
                "budget": p.get("budgetMinutes", 0),
                "billable": p.get("billable", True),
            }
            for p in data.get("data", [])
        ]
    }


def tool_create_project(args):
    """Create a new project."""
    data = api("/projects", method="POST", data={
        "name": args["name"],
        "description": args.get("description", ""),
        "budgetMinutes": args.get("budget", 0),
        "billable": args.get("billable", True),
    })
    if "error" in data:
        return data
    return {
        "projectId": data.get("id"),
        "name": data.get("name"),
        "status": data.get("status", "active"),
    }


TOOLS = {
    "tt_current_status": tool_current_status,
    "tt_get_entries": tool_get_entries,
    "tt_get_members": tool_get_members,
    "tt_get_projects": tool_get_projects,
    "tt_create_project": tool_create_project,
}

TOOL_SCHEMAS = [
    {"name": "tt_current_status", "description": "Who's currently clocked in", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "tt_get_entries", "description": "Time entries for a date range", "inputSchema": {"type": "object", "properties": {
        "from": {"type": "string"}, "to": {"type": "string"}, "memberId": {"type": "string"}, "projectId": {"type": "string"}, "limit": {"type": "number"}
    }}},
    {"name": "tt_get_members", "description": "List team members", "inputSchema": {"type": "object", "properties": {
        "status": {"type": "string"}
    }}},
    {"name": "tt_get_projects", "description": "List projects", "inputSchema": {"type": "object", "properties": {
        "status": {"type": "string"}
    }}},
    {"name": "tt_create_project", "description": "Create a new project", "inputSchema": {"type": "object", "properties": {
        "name": {"type": "string"}, "description": {"type": "string"}, "budget": {"type": "number"}, "billable": {"type": "boolean"}
    }, "required": ["name"]}},
]


# ── MCP stdio handler ──

def handle(req):
    method = req.get("method")
    params = req.get("params", {})
    
    if method == "tools/list":
        return {"tools": TOOL_SCHEMAS}
    
    if method == "tools/call":
        tool = params.get("name")
        args = params.get("arguments", {})
        if tool in TOOLS:
            return {"content": [{"type": "text", "text": json.dumps(TOOLS[tool](args), indent=2)}]}
        return {"isError": True, "content": [{"type": "text", "text": json.dumps({"error": f"Unknown tool: {tool}", "code": "NOT_FOUND"})}]}
    
    return {"isError": True, "content": [{"type": "text", "text": json.dumps({"error": f"Unknown method: {method}"})}]}


for line in sys.stdin:
    try:
        request = json.loads(line.strip())
        response = handle(request)
        response["jsonrpc"] = "2.0"
        response["id"] = request.get("id")
        print(json.dumps(response), flush=True)
    except json.JSONDecodeError:
        continue