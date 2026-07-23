#!/usr/bin/env python3
"""Microsoft 365 Graph API client for Hermes Agent.

OAuth 2.0 client credentials against Azure AD, exposed via a simple
GraphClient class and a CLI dispatch for mail, calendar, drive, and
directory operations.

Usage:
  python msft_api.py --user user@example.com mail search "query" [--max N]
  python msft_api.py --user user@example.com mail get MESSAGE_ID
  python msft_api.py --user user@example.com mail send --to x@y.com --subject "S" --body "B"
  python msft_api.py --user user@example.com calendar list [--days N]
  python msft_api.py --user user@example.com drive list
  python msft_api.py --user user@example.com drive search "query"
  python msft_api.py --user user@example.com directory get-user
  python msft_api.py --user user@example.com directory list-users

Env vars:
  MSFT_TENANT_ID     — Azure AD tenant ID (required)
  MSFT_CLIENT_ID     — OAuth client ID (required)
  MSFT_CLIENT_SECRET — OAuth client secret (required)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from urllib.parse import quote

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_BASE = "https://graph.microsoft.com/v1.0"
TOKEN_URL_TPL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
TOKEN_SAFETY_MARGIN = 60  # seconds before actual expiry to consider token stale

# ---------------------------------------------------------------------------
# GraphClient
# ---------------------------------------------------------------------------


class GraphClient:
    """Client for Microsoft Graph API using OAuth 2.0 client credentials."""

    def __init__(self):
        """Read credentials from environment variables."""
        self._tenant_id = os.environ.get("MSFT_TENANT_ID", "")
        self._client_id = os.environ.get("MSFT_CLIENT_ID", "")
        self._client_secret = os.environ.get("MSFT_CLIENT_SECRET", "")
        self._token = None
        self._token_expiry = 0.0

        missing = []
        if not self._tenant_id:
            missing.append("MSFT_TENANT_ID")
        if not self._client_id:
            missing.append("MSFT_CLIENT_ID")
        if not self._client_secret:
            missing.append("MSFT_CLIENT_SECRET")
        if missing:
            print(
                f"ERROR: Missing required env var(s): {', '.join(missing)}",
                file=sys.stderr,
            )
            sys.exit(1)

    def _ensure_token(self):
        """Obtain or refresh the OAuth access token.

        Token is cached with a 60-second safety margin before expiry.
        Returns the current access token string.
        """
        now = time.time()
        if self._token and self._token_expiry > (now + TOKEN_SAFETY_MARGIN):
            return self._token

        token_url = TOKEN_URL_TPL.format(tenant=self._tenant_id)
        data = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }

        resp = requests.post(token_url, data=data)
        resp.raise_for_status()
        body = resp.json()

        self._token = body["access_token"]
        self._token_expiry = now + body.get("expires_in", 3600)
        return self._token

    def _headers(self):
        """Return HTTP headers with the current bearer token."""
        return {
            "Authorization": f"Bearer {self._ensure_token()}",
            "Content-Type": "application/json",
        }

    def _user_path(self, user, path):
        """Build a path under /users/{user}."""
        return f"/users/{user}{path}"

    def get(self, path):
        """Perform a GET request to the Graph API.

        Args:
            path: API path, e.g. /users/{user}/messages?$top=10

        Returns:
            Parsed JSON response body as a dict.
        """
        url = f"{API_BASE}{path}"
        resp = requests.get(url, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def post(self, path, data):
        """Perform a POST request to the Graph API.

        Args:
            path: API path, e.g. /users/{user}/sendMail
            data: JSON-serializable payload dict.

        Returns:
            Parsed JSON response body as a dict.
        """
        url = f"{API_BASE}{path}"
        resp = requests.post(url, headers=self._headers(), json=data)
        resp.raise_for_status()
        # 202 Accepted may return empty body
        if resp.content:
            return resp.json()
        return {}


# ---------------------------------------------------------------------------
# Command: mail search
# ---------------------------------------------------------------------------

def cmd_mail_search(client, user, args):
    """Search the user's mailbox.

    Usage: mail search QUERY [--max N]
    """
    parser = argparse.ArgumentParser(prog="mail search")
    parser.add_argument("query", nargs="*", default=[])
    parser.add_argument("--max", type=int, default=10)
    parsed, _ = parser.parse_known_args(args)

    query = " ".join(parsed.query)
    # Graph API search requires double-quoted query string
    search_expr = f'"{query}"' if query else ""
    params = f"?$top={parsed.max}&$orderby=receivedDateTime desc"
    if search_expr:
        params += f'&$search={quote(search_expr)}'

    path = client._user_path(user, f"/messages{params}")
    result = client.get(path)
    print(json.dumps(result, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Command: mail get
# ---------------------------------------------------------------------------

def cmd_mail_get(client, user, args):
    """Get a single message by ID.

    Usage: mail get MESSAGE_ID
    """
    if not args:
        print("ERROR: Missing MESSAGE_ID argument", file=sys.stderr)
        sys.exit(1)
    message_id = args[0]
    path = client._user_path(user, f"/messages/{message_id}")
    result = client.get(path)
    print(json.dumps(result, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Command: mail send
# ---------------------------------------------------------------------------

def cmd_mail_send(client, user, args):
    """Send an email on behalf of the user.

    Usage: mail send --to RECIPIENT --subject SUBJECT --body BODY
    """
    parser = argparse.ArgumentParser(prog="mail send")
    parser.add_argument("--to", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body", required=True)
    parsed, _ = parser.parse_known_args(args)

    payload = {
        "message": {
            "subject": parsed.subject,
            "body": {
                "contentType": "Text",
                "content": parsed.body,
            },
            "toRecipients": [
                {"emailAddress": {"address": parsed.to}},
            ],
        },
    }
    path = client._user_path(user, "/sendMail")
    result = client.post(path, payload)
    print(json.dumps({"status": "sent", **result}, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Command: calendar list
# ---------------------------------------------------------------------------

def cmd_calendar_list(client, user, args):
    """List calendar events.

    Usage: calendar list [--days N]
    """
    parser = argparse.ArgumentParser(prog="calendar list")
    parser.add_argument("--days", type=int, default=7)
    parsed, _ = parser.parse_known_args(args)

    now = datetime.utcnow()
    end = now + timedelta(days=parsed.days)
    start_str = now.isoformat() + "Z"
    end_str = end.isoformat() + "Z"

    path = client._user_path(
        user,
        f"/calendar/events?"
        f"$filter=start/dateTime ge '{start_str}' and end/dateTime le '{end_str}'"
        f"&$top=50&$orderby=start/dateTime",
    )
    result = client.get(path)
    print(json.dumps(result, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Command: drive list
# ---------------------------------------------------------------------------

def cmd_drive_list(client, user, args):
    """List the user's OneDrive root children.

    Usage: drive list
    """
    path = client._user_path(user, "/drive/root/children?$top=20")
    result = client.get(path)
    print(json.dumps(result, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Command: drive search
# ---------------------------------------------------------------------------

def cmd_drive_search(client, user, args):
    """Search the user's OneDrive.

    Usage: drive search QUERY
    """
    query = " ".join(args) if args else ""
    if not query:
        print("ERROR: Missing search query", file=sys.stderr)
        sys.exit(1)
    path = client._user_path(
        user,
        f"/drive/root/search(q='{quote(query)}')?$top=20",
    )
    result = client.get(path)
    print(json.dumps(result, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Command: directory get-user
# ---------------------------------------------------------------------------

def cmd_directory_get_user(client, user, args):
    """Get directory info for the specified user.

    Usage: directory get-user
    """
    path = client._user_path(user, "")
    result = client.get(path)
    print(json.dumps(result, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Command: directory list-users
# ---------------------------------------------------------------------------

def cmd_directory_list_users(client, user, args):
    """List users in the directory.

    Usage: directory list-users
    """
    path = "/users?$top=50&$select=id,displayName,mail,jobTitle,department"
    result = client.get(path)
    print(json.dumps(result, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Command dispatch table
# ---------------------------------------------------------------------------

COMMANDS = {
    "mail": {
        "search": cmd_mail_search,
        "get": cmd_mail_get,
        "send": cmd_mail_send,
    },
    "calendar": {
        "list": cmd_calendar_list,
    },
    "drive": {
        "list": cmd_drive_list,
        "search": cmd_drive_search,
    },
    "directory": {
        "get-user": cmd_directory_get_user,
        "list-users": cmd_directory_list_users,
    },
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Parse CLI args and dispatch to the appropriate command."""

    parser = argparse.ArgumentParser(
        description="Microsoft 365 Graph API client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--user", required=True, help="User email (UPN)")
    parser.add_argument("service", choices=list(COMMANDS.keys()), help="Service to use")
    parser.add_argument("action", help="Action to perform")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Action arguments")

    parsed = parser.parse_args()

    # Validate action
    service_actions = COMMANDS[parsed.service]
    if parsed.action not in service_actions:
        print(
            f"ERROR: Unknown action '{parsed.action}' for service '{parsed.service}'. "
            f"Available: {', '.join(service_actions.keys())}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Create client
    client = GraphClient()

    # Test connection before dispatching
    try:
        test_path = f"/users/{parsed.user}"
        client.get(test_path)
    except Exception as e:
        print(
            f"ERROR: Connection test failed for user '{parsed.user}': {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Dispatch
    cmd_func = service_actions[parsed.action]
    cmd_func(client, parsed.user, parsed.args)


if __name__ == "__main__":
    main()