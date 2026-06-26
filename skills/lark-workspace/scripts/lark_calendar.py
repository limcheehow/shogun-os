#!/usr/bin/env python3
"""
Lark Calendar CLI — mirrors Google Calendar API for Benkei.
Uses Lark tenant access token (server-to-server, no user OAuth).
"""
import json, os, sys, time, urllib.request, urllib.error

LARK_BASE = "https://open.feishu.cn/open-apis"

def get_tenant_token():
    app_id = os.environ.get("LARK_APP_ID", "")
    app_secret = os.environ.get("LARK_APP_SECRET", "")
    if not app_id or not app_secret:
        return {"error": "LARK_APP_ID and LARK_APP_SECRET not set"}
    data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = urllib.request.Request(
        f"{LARK_BASE}/auth/v3/tenant_access_token/internal",
        data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    if "tenant_access_token" not in resp:
        return {"error": resp.get("msg", "auth failed")}
    return resp["tenant_access_token"]

def api(path, method="GET", body=None):
    token = get_tenant_token()
    if isinstance(token, dict) and "error" in token:
        return token
    url = f"{LARK_BASE}{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = json.loads(urllib.request.urlopen(req).read())
        return resp
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "body": e.read().decode()}

def handle(args):
    cmd = args.get("_cmd", "")
    if cmd == "list":
        return api("/calendar/v4/calendars/primary/events?page_size=50")
    elif cmd == "create":
        body = {
            "summary": args.get("summary", "Meeting"),
            "start_time": {"timestamp": args.get("start", str(int(time.time()))), "timezone": "Asia/Kuala_Lumpur"},
            "end_time": {"timestamp": args.get("end", str(int(time.time()) + 3600)), "timezone": "Asia/Kuala_Lumpur"},
        }
        if args.get("desc"):
            body["description"] = args["desc"]
        return api("/calendar/v4/calendars/primary/events", method="POST", body=body)
    elif cmd == "get":
        eid = args.get("event_id", "")
        return api(f"/calendar/v4/calendars/primary/events/{eid}")
    elif cmd == "delete":
        eid = args.get("event_id", "")
        return api(f"/calendar/v4/calendars/primary/events/{eid}", method="DELETE")
    return {"error": f"Unknown: {cmd}"}

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["list", "create", "get", "delete"])
    p.add_argument("--summary")
    p.add_argument("--start")
    p.add_argument("--end")
    p.add_argument("--desc")
    p.add_argument("--event-id")
    a = p.parse_args()
    result = handle(vars(a))
    print(json.dumps(result, indent=2))