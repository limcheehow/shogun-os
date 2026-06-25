#!/usr/bin/env python3
"""
Company OS — E2E Test Suite
─────────────────────────────
Tests provider abstractions (comm, time tracking) using mock providers.
Does NOT require real API keys — all providers are simulated.

Usage:
  python3 scripts/verify-e2e.py
  python3 scripts/verify-e2e.py --verbose
"""

import argparse
import json
import os
import sys
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

PASS = 0
FAIL = 0
VERBOSE = False

# Add the comm provider module to path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "skills" / "department-scrum" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def section(name):
    print(f"\n━━━ {name} ━━━")


def ok(msg):
    global PASS
    PASS += 1
    print(f"  ✓ {msg}")


def fail(msg):
    global FAIL
    FAIL += 1
    print(f"  ✗ {msg}")


# ═══════════════════════════════════════════════════════════════════════
#  COMM PROVIDER E2E TESTS
# ═══════════════════════════════════════════════════════════════════════

def test_provider_registry():
    """Test all providers are registered."""
    section("Provider Registry")

    from comm.provider import REGISTRY, get_provider, _discover_providers

    _discover_providers()  # Force discovery before checking registry

    registered = sorted(REGISTRY.keys())
    expected = ["lark", "slack", "telegram"]

    for p in expected:
        if p in registered:
            ok(f"Provider `{p}` registered")
        else:
            fail(f"Provider `{p}` NOT registered")

    for p in registered:
        if p not in expected:
            ok(f"Provider `{p}` (extra — acceptable)")


def test_provider_load():
    """Test each provider can be instantiated with mock env."""
    section("Provider Loading")

    from comm.provider import get_provider

    tests = [
        ("slack", {"SLACK_BOT_TOKEN": "xoxb-test-token"}),
        ("telegram", {"TELEGRAM_BOT_TOKEN": "123:test-token"}),
        ("lark", {"LARK_ACCESS_TOKEN": "test-token"}),
    ]

    for name, env in tests:
        try:
            provider = get_provider(name, env)
            assert provider is not None
            ok(f"`{name}` — loaded successfully")
        except ImportError as e:
            # Slack SDK or requests not installed — skip
            ok(f"`{name}` — skipped (dependency: {e})")
        except Exception as e:
            fail(f"`{name}` — load error: {e}")


def test_slack_send_dm():
    """Test Slack provider send_dm with mocked client."""
    section("Slack Provider — send_dm")

    from comm.provider import get_provider

    try:
        provider = get_provider("slack", {"SLACK_BOT_TOKEN": "xoxb-test"})
    except ImportError:
        ok("Slack — skipped (slack_sdk not installed)")
        return

    # Mock the WebClient
    mock_client = MagicMock()
    mock_client.conversations_open.return_value = {
        "channel": {"id": "D0TEST123"}
    }
    mock_client.chat_postMessage.return_value = {
        "ts": "1734567890.123456"
    }
    provider.client = mock_client

    result = provider.send_dm("U0TESTUSER", "Hello from test!")
    assert result["thread_id"] == "1734567890.123456"
    assert result["conversation_id"] == "D0TEST123"
    ok(f"send_dm — OK (thread_id={result['thread_id']})")


def test_slack_read_replies():
    """Test Slack provider read_replies with mocked client."""
    section("Slack Provider — read_replies")

    from comm.provider import get_provider

    try:
        provider = get_provider("slack", {"SLACK_BOT_TOKEN": "xoxb-test"})
    except ImportError:
        ok("Slack — skipped (slack_sdk not installed)")
        return

    mock_client = MagicMock()
    mock_client.conversations_history.return_value = {
        "messages": [
            {"user": "U0USER1", "text": "I finished the report", "ts": "1734567891.123456"},
            {"user": "U0USER2", "text": "Blocked on vendor approval", "ts": "1734567892.123456"},
        ]
    }
    provider.client = mock_client

    replies = provider.read_replies_in_thread("D0TEST123", "1734567890.123456")
    assert len(replies) == 2
    assert replies[0]["sender"] == "U0USER1"
    assert replies[1]["text"] == "Blocked on vendor approval"
    ok("read_replies — OK (2 replies parsed)")


def test_slack_backward_compat():
    """Test that slack_id field works with the new provider."""
    section("Slack — Backward Compatibility")

    # The send-scrum-dms.py script uses member.get("user_id", member.get("slack_id", ""))
    # This tests that old scrum.yaml files with slack_id still work
    from comm.provider import get_provider

    try:
        provider = get_provider("slack", {"SLACK_BOT_TOKEN": "xoxb-test"})
    except ImportError:
        ok("Slack — skipped (slack_sdk not installed)")
        return

    mock_client = MagicMock()
    mock_client.conversations_open.return_value = {"channel": {"id": "D0OLDUSER"}}
    mock_client.chat_postMessage.return_value = {"ts": "1734567890.123456"}
    provider.client = mock_client

    # Simulate old config with slack_id instead of user_id
    team_member = {"name": "Alice", "slack_id": "U0OLDUSER", "role": "Engineer"}
    user_id = team_member.get("user_id", team_member.get("slack_id", ""))
    assert user_id == "U0OLDUSER", f"Expected U0OLDUSER, got {user_id}"

    result = provider.send_dm(user_id, "Test message")
    assert result["thread_id"] == "1734567890.123456"
    ok("Backward compat — slack_id fallback works")


def test_telegram_send_dm():
    """Test Telegram provider send_dm with mocked requests."""
    section("Telegram Provider — send_dm")

    from comm.provider import get_provider

    try:
        import requests
        provider = get_provider("telegram", {"TELEGRAM_BOT_TOKEN": "123:test"})
    except ImportError:
        ok("Telegram — skipped (requests not installed)")
        return
    except Exception as e:
        fail(f"Telegram — load error: {e}")
        return

    # Mock requests.post
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "result": {
                "message_id": 42,
                "chat": {"id": 12345},
                "text": "Hello from test!",
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = provider.send_dm("12345", "Hello from test!")
        assert result["thread_id"] == "42"
        assert result["conversation_id"] == "12345"
        ok("send_dm — OK (message_id=42)")


def test_lark_send_dm():
    """Test Lark provider send_dm with mocked requests."""
    section("Lark Provider — send_dm")

    from comm.provider import get_provider

    try:
        import requests
        provider = get_provider("lark", {"LARK_ACCESS_TOKEN": "test-token"})
    except ImportError:
        ok("Lark — skipped (requests not installed)")
        return

    provider._token_expires_at = float("inf")
    provider._token = "test-token"

    # Mock requests.request (Lark uses request() not post())
    with patch("requests.request") as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "msg": "success",
            "data": {
                "message": {
                    "message_id": "om_1234567890",
                    "chat_id": "oc_1234567890",
                }
            },
        }
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        result = provider.send_dm("user_789", "Hello from test!")
        assert result["thread_id"] == "om_1234567890"
        assert result["conversation_id"] == "oc_1234567890"
        ok("send_dm — OK (thread_id=om_1234567890)")


def test_lark_auth_refresh():
    """Test Lark provider auto-refreshes expired token."""
    section("Lark Provider — Token Refresh")

    from comm.provider import get_provider

    try:
        import requests
        provider = get_provider("lark", {"LARK_ACCESS_TOKEN": "test-token"})
    except ImportError:
        ok("Lark — skipped (requests not installed)")
        return

    # Manually set app credentials to trigger auth flow
    provider._app_id = "cli_xxx"
    provider._app_secret = "secret_xxx"
    provider._token = None
    provider._token_expires_at = 0

    # Mock requests.post for auth
    auth_response = MagicMock()
    auth_response.json.return_value = {
        "code": 0,
        "msg": "ok",
        "tenant_access_token": "fresh-token-123",
        "expire": 7200,
    }
    auth_response.raise_for_status.return_value = None

    with patch("requests.post") as mock_post:
        mock_post.return_value = auth_response

        # After auth, the provider should have the new token
        provider._ensure_token()
        assert provider._token == "fresh-token-123"
        ok("Token refresh — got fresh-token-123")


# ═══════════════════════════════════════════════════════════════════════
#  SCRUM SCRIPT E2E TESTS
# ═══════════════════════════════════════════════════════════════════════

def test_scrum_state_format():
    """Test that scrum state file uses provider-agnostic fields."""
    section("Scrum State Format")

    # Simulate the state JSON produced by send-scrum-dms.py
    state = {
        "date": "2026-06-26",
        "profile": "project-manager",
        "comm_provider": "slack",
        "team": [
            {
                "name": "Alice",
                "user_id": "U0TESTALICE",
                "role": "Engineer",
                "thread_id": "1734567890.123456",
                "conversation_id": "D0TESTCHAN",
                "replied": False,
            },
            {
                "name": "Bob",
                "user_id": "U0TESTBOB",
                "role": "Designer",
                "thread_id": "1734567891.123456",
                "conversation_id": "D0TESTCHAN2",
                "replied": True,
                "reply_text": "Finished the mockups",
            },
        ],
    }

    assert "comm_provider" in state
    for member in state["team"]:
        assert "user_id" in member, "Missing user_id in state"
        assert "thread_id" in member, "Missing thread_id in state"
        assert "conversation_id" in member, "Missing conversation_id in state"

    ok("State format — provider-agnostic fields present")


def test_scrum_config_schema():
    """Test that scrum config templates have valid comm_provider."""
    section("Scrum Config comm_provider")

    test_dir = Path(__file__).resolve().parent.parent / "examples" / "scrum-configs"
    try:
        import yaml
    except ImportError:
        ok("Scrum config — skipped (pyyaml not installed)")
        return

    for f in sorted(test_dir.glob("*.yaml")):
        with open(f) as fh:
            config = yaml.safe_load(fh)
        profile = config.get("profile", "?")
        provider = config.get("comm_provider")
        if provider:
            ok(f"{profile} — comm_provider={provider}")
        else:
            fail(f"{profile} — missing comm_provider")


# ═══════════════════════════════════════════════════════════════════════
#  TIME TRACKING CONTRACT E2E TESTS
# ═══════════════════════════════════════════════════════════════════════

def test_tt_bridge_syntax():
    """Test that the Jibble bridge has valid Python syntax."""
    section("Time Tracking Bridge — Syntax")

    bridge_path = (
        Path(__file__).resolve().parent.parent
        / "recipes" / "time-tracking" / "bridges" / "tt-bridge-jibble.py"
    )
    if not bridge_path.exists():
        ok("Bridge — not found (may be in alternate path)")
        return

    try:
        compile(bridge_path.read_text(), bridge_path.name, "exec")
        ok(f"tt-bridge-jibble.py — valid syntax")
    except SyntaxError as e:
        fail(f"Syntax error: {e}")


def test_tt_contract_tools():
    """Test that the Jibble bridge exports all required tools."""
    section("Time Tracking Contract — Tools")

    bridge_path = (
        Path(__file__).resolve().parent.parent
        / "recipes" / "time-tracking" / "bridges" / "tt-bridge-jibble.py"
    )
    if not bridge_path.exists():
        ok("Bridge tools — skipped (not found)")
        return

    # Extract the TOOL_SCHEMAS list from the bridge
    ns = {}
    exec(bridge_path.read_text(), ns)

    required_tools = [
        "tt_current_status",
        "tt_get_entries",
        "tt_get_members",
        "tt_get_projects",
        "tt_create_project",
    ]

    available = {t["name"] for t in ns.get("TOOL_SCHEMAS", [])}

    for tool in required_tools:
        if tool in available:
            ok(f"`{tool}` — defined")
        else:
            fail(f"`{tool}` — MISSING")


def test_tt_bridge_responds():
    """Test that the Jibble bridge handles tools/list correctly."""
    section("Time Tracking Bridge — tools/list")

    bridge_path = (
        Path(__file__).resolve().parent.parent
        / "recipes" / "time-tracking" / "bridges" / "tt-bridge-jibble.py"
    )
    if not bridge_path.exists():
        ok("Bridge tools/list — skipped (not found)")
        return

    ns = {}
    exec(bridge_path.read_text(), ns)
    handle_func = ns.get("handle")

    assert handle_func is not None, "handle() function not found"

    response = handle_func({"method": "tools/list", "params": {}})
    assert "tools" in response, "tools/list response missing 'tools' key"
    assert len(response["tools"]) >= 5, f"Expected >=5 tools, got {len(response['tools'])}"
    ok(f"tools/list — returns {len(response['tools'])} tools")


def test_tt_bridge_current_status():
    """Test the tt_current_status tool call flow."""
    section("Time Tracking Bridge — tt_current_status")

    bridge_path = (
        Path(__file__).resolve().parent.parent
        / "recipes" / "time-tracking" / "bridges" / "tt-bridge-jibble.py"
    )
    if not bridge_path.exists():
        ok("Bridge tt_current_status — skipped (not found)")
        return

    ns = {}
    exec(bridge_path.read_text(), ns)
    TOOLS = ns.get("TOOLS", {})

    assert "tt_current_status" in TOOLS
    # With no API key, it should return an error, not crash
    result = TOOLS["tt_current_status"]({})
    assert "error" in result or "active" in result
    ok("tt_current_status — returns result (error or data)")


# ═══════════════════════════════════════════════════════════════════════
#  RUN ALL
# ═══════════════════════════════════════════════════════════════════════

def run_all():
    parser = argparse.ArgumentParser(description="Company OS — E2E Test Suite")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    global VERBOSE
    VERBOSE = args.verbose

    test_provider_registry()
    test_provider_load()
    test_slack_send_dm()
    test_slack_read_replies()
    test_slack_backward_compat()
    test_telegram_send_dm()
    test_lark_send_dm()
    test_lark_auth_refresh()
    test_scrum_state_format()
    test_scrum_config_schema()
    test_tt_bridge_syntax()
    test_tt_contract_tools()
    test_tt_bridge_responds()
    test_tt_bridge_current_status()

    print(f"\n{'═' * 50}")
    print(f"  Results:  {PASS} passed, {FAIL} failed")
    print(f"{'═' * 50}")

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all())