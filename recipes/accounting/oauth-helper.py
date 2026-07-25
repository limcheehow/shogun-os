#!/usr/bin/env python3
"""
Shared OAuth Helper for Accounting MCP Bridges
───────────────────────────────────────────────
Manages OAuth2 tokens for QuickBooks and Xero providers.
Follows the same token caching pattern as Hermes' own OAuth MCP servers:
tokens stored at ~/.hermes/mcp-tokens/accounting-<provider>.json

Usage:
  from oauth_helper import get_oauth_session, refresh_if_needed, load_token

Environment variables:
  ACCT_CLIENT_ID     — OAuth client ID
  ACCT_CLIENT_SECRET — OAuth client secret
  ACCT_REFRESH_TOKEN — Refresh token (persisted after first auth)
"""

import json
import os
import sys
import time
from pathlib import Path

TOKEN_DIR = Path.home() / ".hermes" / "mcp-tokens"
TOKEN_PERMS = 0o600


def _token_path(provider_name: str) -> Path:
    """Get cached token file path, following Hermes convention."""
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    return TOKEN_DIR / f"accounting-{provider_name}.json"


def load_token(provider_name: str) -> dict | None:
    """Load cached OAuth token from disk."""
    path = _token_path(provider_name)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None


def save_token(provider_name: str, token_data: dict):
    """Save OAuth token to disk with secure permissions."""
    path = _token_path(provider_name)
    path.write_text(json.dumps(token_data, indent=2))
    path.chmod(TOKEN_PERMS)


def is_expired(token_data: dict) -> bool:
    """Check if the token is expired or about to expire (within 5 min)."""
    expires_at = token_data.get("expires_at", 0)
    if not expires_at:
        return True
    # Allow 5-minute buffer
    return time.time() >= (expires_at - 300)


def refresh_if_needed(provider_name: str, client_id: str, client_secret: str,
                      token_url: str, scopes: list[str]) -> dict | None:
    """
    Refresh the OAuth token if it's expired or about to expire.
    Returns the token dict, or None if refresh failed.

    Follows standard OAuth2 refresh token grant.
    """
    token = load_token(provider_name)
    if not token:
        return None

    refresh_token = token.get("refresh_token")
    if not refresh_token:
        return None

    if not is_expired(token):
        return token

    # Attempt refresh
    import urllib.request
    import urllib.parse

    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": " ".join(scopes),
    }).encode()

    req = urllib.request.Request(
        token_url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            new_token = json.loads(resp.read().decode())

        # Merge with existing token data
        token["access_token"] = new_token.get("access_token", token["access_token"])
        if "refresh_token" in new_token and new_token["refresh_token"]:
            token["refresh_token"] = new_token["refresh_token"]
        # Calculate new expiry
        expires_in = new_token.get("expires_in", 3600)
        token["expires_at"] = time.time() + expires_in

        save_token(provider_name, token)
        sys.stderr.write(f"[oauth-helper] Refreshed token for {provider_name}\n")
        return token

    except Exception as e:
        sys.stderr.write(f"[oauth-helper] Token refresh failed for {provider_name}: {e}\n")
        return None


# QuickBooks OAuth endpoints
QB_OAUTH_URL = "https://appcenter.intuit.com/connect/oauth2"
QB_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
QB_SCOPES = ["com.intuit.quickbooks.accounting", "openid", "profile", "email"]

# Xero OAuth endpoints
XERO_OAUTH_URL = "https://login.xero.com/identity/connect/authorize"
XERO_TOKEN_URL = "https://identity.xero.com/connect/token"
XERO_SCOPES = ["openid", "profile", "email", "accounting.transactions",
               "accounting.settings", "accounting.reports.read",
               "accounting.contacts", "offline_access"]


def get_quickbooks_session() -> dict | None:
    """Get a valid QuickBooks OAuth session, refreshing if needed."""
    client_id = os.environ.get("ACCT_CLIENT_ID", "")
    client_secret = os.environ.get("ACCT_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        return None

    return refresh_if_needed("quickbooks", client_id, client_secret,
                             QB_TOKEN_URL, QB_SCOPES)


def get_xero_session() -> dict | None:
    """Get a valid Xero OAuth session, refreshing if needed."""
    client_id = os.environ.get("ACCT_CLIENT_ID", "")
    client_secret = os.environ.get("ACCT_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        return None

    return refresh_if_needed("xero", client_id, client_secret,
                             XERO_TOKEN_URL, XERO_SCOPES)