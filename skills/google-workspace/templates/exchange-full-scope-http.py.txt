"""
Direct HTTP exchange for full-scope Google OAuth token.

USAGE:
  1. python3 exchange-full-scope-http.py --auth-url
     → prints URL, send to user
  2. user authorizes, pastes back redirect URL
  3. python3 exchange-full-scope-http.py 'http://localhost/?code=...'

Bypasses ALL oauthlib issues:
  - No "Warning: Scope has changed" rejection
  - No PKCE state management needed
  - No monkey-patching required
  - Accepts whatever scopes Google returns
"""
import json, os, sys, time, urllib.request, urllib.parse
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone

CLIENT_PATH=os.pat...).hermes/google_client_secret.json")
TOKEN_PATH=os.pat...).hermes/google_token.json")

ALL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/fitness.activity.read",
    "https://www.googleapis.com/auth/fitness.body.read",
    "https://www.googleapis.com/auth/fitness.sleep.read",
    "https://www.googleapis.com/auth/fitness.location.read",
    "https://www.googleapis.com/auth/fitness.blood_glucose.read",
    "https://www.googleapis.com/auth/fitness.blood_pressure.read",
    "https://www.googleapis.com/auth/fitness.heart_rate.read",
    "https://www.googleapis.com/auth/fitness.nutrition.read",
    "https://www.googleapis.com/auth/fitness.oxygen_saturation.read",
    "https://www.googleapis.com/auth/fitness.reproductive_health.read",
]

def gen_auth_url():
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_secrets_file(CLIENT_PATH, scopes=ALL_SCOPES, redirect_uri="http://localhost")
    url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true", prompt="consent")
    print(url)

def exchange(redirect_url):
    parsed = urlparse(redirect_url)
    params = parse_qs(parsed.query)
    code = params.get("code", [None])[0]
    if not code:
        print("NO_CODE")
        sys.exit(1)

    with open(CLIENT_PATH) as f:
        client = json.load(f)
    cfg = client["installed"]

    body = urllib.parse.urlencode({
        "code": code,
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "redirect_uri": "http://localhost",
        "grant_type": "authorization_code",
    }).encode()

    req = urllib.request.Request(cfg["token_uri"], data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    resp_data = json.loads(urllib.request.urlopen(req).read())

    token = {
        "token": resp_data["access_token"],
        "refresh_token": resp_data.get("refresh_token", ""),
        "token_uri": cfg["token_uri"],
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "scopes": resp_data.get("scope", "").split(),
        "universe_domain": "googleapis.com",
        "account": "",
        "expiry": datetime.fromtimestamp(
            time.time() + resp_data.get("expires_in", 3599), tz=timezone.utc
        ).isoformat(),
    }

    with open(TOKEN_PATH, "w") as f:
        json.dump(token, f, indent=2)

    scopes = token["scopes"]
    print(f"OK:{len(scopes)}:{bool(token.get('refresh_token'))}")
    for s in sorted(scopes):
        print(f"SCOPE:{s}")
    print(f"EXPIRES:{token.get('expiry')}")

    # Verify fitness
    try:
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, scopes)
        if creds.expired:
            creds.refresh(Request())
        fit = build("fitness", "v1", credentials=creds)
        sources = fit.users().dataSources().list(userId="me").execute()
        print(f"FITNESS_TEST:{len(sources.get('dataSource', []))}")
    except Exception as e:
        print(f"FITNESS_ERROR:{e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--auth-url":
            gen_auth_url()
        else:
            exchange(sys.argv[1])
    else:
        print("Usage:")
        print("  exchange-full-scope-http.py --auth-url    # generate auth URL")
        print("  exchange-full-scope-http.py 'http://...'  # exchange code")