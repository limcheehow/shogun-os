#!/usr/bin/env python3
"""
Accounting MCP Bridge — Unified
─────────────────────────────────
Loads a provider plugin based on the ACCT_PROVIDER env var.
Supports: bukku, quickbooks, xero

Configure in config.yaml:
  mcp_servers:
    accounting:
      command: python3
      args: [~/.hermes/scripts/acct-bridge.py]
      env:
        ACCT_PROVIDER: "${ACCT_PROVIDER}"
        ACCT_API_KEY: "${ACCT_API_KEY}"
        ACCT_SUBDOMAIN: "${ACCT_SUBDOMAIN}"

Environment variables (per profile .env):
  ACCT_PROVIDER   — Provider name: bukku, quickbooks, xero
  ACCT_API_KEY    — API key or OAuth token
  ACCT_SUBDOMAIN  — Bukku subdomain (bukku only)
  ACCT_REFRESH_TOKEN — OAuth refresh token (quickbooks/xero)
  ACCT_CLIENT_ID     — OAuth client ID (quickbooks/xero)
  ACCT_CLIENT_SECRET — OAuth client secret (quickbooks/xero)
  ACCT_TENANT_ID     — Xero tenant ID (xero only)
  ACCT_COMPANY_ID    — QuickBooks company/realm ID (quickbooks only)
"""

import json
import os
import sys
import traceback
import importlib.util
from pathlib import Path

# ── Resolve provider plugin ──────────────────────────────────────────────

PROVIDER = os.environ.get("ACCT_PROVIDER", "bukku")
PLUGIN_DIR = Path(__file__).resolve().parent.parent / "plugins"


def load_provider(name):
    """Dynamically load a provider plugin from the plugins/ directory."""
    plugin_path = PLUGIN_DIR / f"{name}.py"
    if not plugin_path.exists():
        # Also try ~/.hermes/scripts/accounting/plugins/ as fallback
        fallback = Path.home() / ".hermes" / "scripts" / "accounting" / "plugins" / f"{name}.py"
        if fallback.exists():
            plugin_path = fallback
        else:
            sys.stderr.write(f"[acct-bridge] Provider plugin not found: {plugin_path}\n")
            sys.exit(1)

    # Add parent dir to sys.path so plugins can import oauth_helper
    sys.path.insert(0, str(PLUGIN_DIR.parent))

    spec = importlib.util.spec_from_file_location(name, plugin_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Validate the plugin has the required interface
    if not hasattr(module, "get_tool_schemas"):
        sys.stderr.write(f"[acct-bridge] Plugin {name} missing get_tool_schemas()\n")
        sys.exit(1)
    if not hasattr(module, "handle_tool"):
        sys.stderr.write(f"[acct-bridge] Plugin {name} missing handle_tool()\n")
        sys.exit(1)

    return module


# ── Load the provider ────────────────────────────────────────────────────

sys.stderr.write(f"[acct-bridge] Loading provider: {PROVIDER}\n")
provider = load_provider(PROVIDER)

# ── MCP stdio handler ────────────────────────────────────────────────────


def handle_request(req):
    """Handle a single MCP JSON-RPC request."""
    method = req.get("method")
    params = req.get("params", {})

    if method == "tools/list":
        return {"tools": provider.get_tool_schemas()}

    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        try:
            result = provider.handle_tool(tool_name, tool_args)
            return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
        except Exception as e:
            return {
                "isError": True,
                "content": [{"type": "text", "text": json.dumps({
                    "error": str(e),
                    "code": "PROVIDER_ERROR"
                })}]
            }

    return {
        "isError": True,
        "content": [{"type": "text", "text": json.dumps({
            "error": f"Unknown method: {method}",
            "code": "NOT_FOUND"
        })}]
    }


# ── Main loop ────────────────────────────────────────────────────────────

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        request = json.loads(line)
        response = handle_request(request)
        response["jsonrpc"] = "2.0"
        response["id"] = request.get("id")
        print(json.dumps(response), flush=True)
    except json.JSONDecodeError:
        continue
    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "isError": True,
            "content": [{"type": "text", "text": json.dumps({
                "error": f"Bridge error: {str(e)}",
                "code": "PROVIDER_ERROR"
            })}]
        }
        print(json.dumps(error_response), flush=True)
        traceback.print_exc(file=sys.stderr)