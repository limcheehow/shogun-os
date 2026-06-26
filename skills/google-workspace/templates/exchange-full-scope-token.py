#!/usr/bin/env python3
"""
Exchange a Google OAuth code for a token with workspace + fitness scopes.
Run this when the user authorizes a URL generated from full-scope-auth.md.

Usage:
    python3 exchange-full-scope-token.py 'http://localhost/?code=4/0A...&scope=...'

Pass the full redirect URL as a single argument.
"""
import json, sys, os
from urllib.parse import urlparse, parse_qs
from google_auth_oauthlib.flow import Flow

CLIENT_PATH=os.pat...TOKEN_PATH=*** = [
    # Workspace
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
    # Fitness
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

# 🚨 Monkey-patch: oauthlib rejects Google's scope expansion by default.
# This must run BEFORE flow instantiation.
from oauthlib.oauth2.rfc6749 import tokens as oauth_tokens
_orig = oauth_tokens.parse_token_response
oauth_tokens.parse_token_response = lambda body, scope=None: _orig(body, scope=None)

redirect = sys.argv[1]
params = parse_qs(urlparse(redirect).query)
code = params.get("code", [None])[0]
if not code:
    print("❌ No authorization code found in URL")
    print(f"   Parsed query params: {list(params.keys())}")
    sys.exit(1)

print(f"✅ Code extracted ({code[:30]}...)")

flow = Flow.from_client_secrets_file(CLIENT_PATH, scopes=ALL_SCOPES, redirect_uri="http://localhost")
flow.fetch_token(code=code)
creds = flow.credentials

token_data = json.loads(creds.to_json())
with open(TOKEN_PATH, "w") as f:
    json.dump(token_data, f, indent=2)

print()
print(f"✅ Token saved to {TOKEN_PATH}")
print(f"   Scopes: {len(creds.scopes)}")
for s in sorted(creds.scopes):
    print(f"     - {s}")
print(f"   Refresh token: {'✅' if creds.refresh_token else '❌ MISSING'}")
print(f"   Expires: {creds.expiry}")

# Verify fitness API works
try:
    from googleapiclient.discovery import build
    fit = build("fitness", "v1", credentials=creds)
    sources = fit.users().dataSources().list(userId="me").execute()
    n = len(sources.get("dataSource", []))
    print(f"\n✅ Fitness API test: {n} data source(s) found")
except Exception as e:
    print(f"\n⚠️ Fitness API test failed: {e}")
    print("   (This may be fine if no fitness data exists)")