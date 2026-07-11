#!/usr/bin/env python3
"""Configure rclone with Google Drive using existing Hermes OAuth credentials.

Reads google_token.json and google_client_secret.json from ~/.hermes/,
refreshes the access token, and writes a valid rclone config.

Usage: python3 rclone_configure.py [remote_name] [--scopes scope1,scope2]
Default remote_name: gdrive
Default scopes: drive
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install with: pip install requests")
    sys.exit(1)

HERMES_HOME = Path.home() / ".hermes"
TOKEN_PATH = HERMES_HOME / "google_token.json"
SECRET_PATH = HERMES_HOME / "google_client_secret.json"
RCLONE_CONFIG = Path.home() / ".config" / "rclone" / "rclone.conf"


def refresh_token(secret, refresh_token):
    """Exchange a refresh token for a new access token."""
    resp = requests.post(
        secret["token_uri"],
        data={
            "client_id": secret["client_id"],
            "client_secret": secret["client_secret"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    remote_name = sys.argv[1] if len(sys.argv) > 1 else "gdrive"

    # Read credentials
    if not SECRET_PATH.exists():
        print(f"Error: {SECRET_PATH} not found. Run google-workspace setup first.")
        sys.exit(1)
    if not TOKEN_PATH.exists():
        print(f"Error: {TOKEN_PATH} not found. Run google-workspace setup first.")
        sys.exit(1)

    with open(SECRET_PATH) as f:
        secret = json.load(f)["installed"]

    with open(TOKEN_PATH) as f:
        token = json.load(f)

    refresh_token = token.get("refresh_token")
    if not refresh_token:
        print("Error: No refresh_token in google_token.json")
        sys.exit(1)

    # Refresh
    new_token = refresh_token(secret, refresh_token)
    expires_in = new_token.get("expires_in", 3600)
    expiry_dt = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    expiry_str = expiry_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    # Build rclone token (expiry MUST be ISO 8601 string, not numeric)
    rclone_token = {
        "access_token": new_token["access_token"],
        "token_type": "Bearer",
        "refresh_token": refresh_token,
        "expiry": expiry_str,
    }

    # Write config
    RCLONE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    config = f"""[{remote_name}]
type = drive
client_id = {secret['client_id']}
client_secret = {secret['client_secret']}
scope = drive
token = {json.dumps(rclone_token)}
team_drive = 
"""

    with open(RCLONE_CONFIG, "w") as f:
        f.write(config)

    print(f"rclone config written to {RCLONE_CONFIG}")
    print(f"Remote: {remote_name}")
    print(f"Token expires: {expiry_str}")
    print(f"Test with: rclone lsf {remote_name}: --max-depth 1")


if __name__ == "__main__":
    main()
