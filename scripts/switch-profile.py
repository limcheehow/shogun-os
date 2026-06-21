#!/usr/bin/env python3
"""
Profile Model & MCP Manager
Switch models and manage MCP servers across profiles from one command.

Usage:
  # List all profiles with current model
  python3 switch-profile.py list

  # Switch one profile to a model preset
  python3 switch-profile.py hr-manager --model coding

  # Switch multiple profiles to a model preset
  python3 switch-profile.py hr-manager finance-manager --model standard

  # Set a custom model (ad-hoc, not a preset)
  python3 switch-profile.py coding-agent --model-custom "anthropic/claude-sonnet-4" --provider openrouter

  # Add shared MCP servers to all profiles
  python3 switch-profile.py mcp-sync

  # Add profile-specific MCP server
  python3 switch-profile.py hr-manager --mcp-add jibble --command "npx" --args mcp-jibble
"""
import os, sys, json, yaml, shutil
from pathlib import Path

HERMES_HOME = Path(os.path.expanduser("~/.hermes"))
PROFILES_DIR = HERMES_HOME / "profiles"
TEMPLATES_DIR = HERMES_HOME / "profile-templates"

# ── Model Presets ──
# These match profile-templates/*-config.yaml
PRESETS = {
    "standard": {
        "model": {
            "default": "deepseek-v4-flash",
            "provider": "custom",
            "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            "api_key": "${DASHSCOPE_API_KEY}",
            "api_mode": "chat_completions",
        },
        "fallback_providers": [
            {"provider": "openrouter", "model": "deepseek/deepseek-v4-flash"}
        ],
        "auxiliary": "google/gemma-4-31b-it:free",
    },
    "coding": {
        "model": {
            "default": "~anthropic/claude-sonnet-4-20250514",
            "provider": "openrouter",
        },
        "fallback_providers": [
            {
                "provider": "custom",
                "model": "deepseek-v4-flash",
                "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
                "api_key": "${DASHSCOPE_API_KEY}",
                "api_mode": "chat_completions",
            }
        ],
    },
    "lightweight": {
        "model": {
            "default": "google/gemini-2.0-flash-exp:free",
            "provider": "openrouter",
        },
        "fallback_providers": [
            {"provider": "openrouter", "model": "deepseek/deepseek-v4-flash"}
        ],
    },
}

# ── Shared MCP Servers ──
# These get merged into EVERY profile's config.yaml
SHARED_MCP_SERVERS = {
    "gbrain": {
        "command": "gbrain",
        "args": ["mcp"],
        "env": {
            "GBRAIN_SOURCE": "${GBRAIN_SOURCE}",
            "GBRAIN_FEDERATED_READ": "${GBRAIN_FEDERATED_READ:-}",
        },
    },
    "stock-scanner": {
        "command": "npx",
        "args": ["-y", "stock-scanner-mcp"],
    },
}

# ── Profile-Specific MCP Servers ──
# These only get added to specific profiles
PROFILE_MCP_SERVERS = {
    "hr-manager": {
        "jibble": {
            "command": "npx",
            "args": ["-y", "mcp-jibble"],
        },
    },
    "crm-manager": {
        "hubspot": {
            "command": "npx",
            "args": ["-y", "@hubspot/mcp-server"],
        },
    },
}


def get_all_profiles():
    """Return list of profile names with config.yaml."""
    profiles = []
    for d in PROFILES_DIR.iterdir():
        config_file = d / "config.yaml"
        if config_file.exists():
            profiles.append(d.name)
    return sorted(profiles)


def read_config(profile_name):
    config_file = PROFILES_DIR / profile_name / "config.yaml"
    if not config_file.exists():
        return {}
    with open(config_file) as f:
        return yaml.safe_load(f) or {}


def write_config(profile_name, config):
    config_file = PROFILES_DIR / profile_name / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    print(f"  ✓ {profile_name}/config.yaml updated")


def list_profiles():
    """Show all profiles with their current model."""
    print(f"{'Profile':<25} {'Model':<40} {'Provider'}")
    print(f"{'─'*25} {'─'*40} {'─'*15}")
    for name in get_all_profiles():
        config = read_config(name)
        model_block = config.get("model", {})
        default = model_block.get("default", "(not set)")
        provider = model_block.get("provider", "(not set)")
        print(f"{name:<25} {str(default):<40} {provider}")


def switch_model(profile_names, preset_name, custom_model=None):
    """Switch one or more profiles to a model preset or custom config."""
    if custom_model:
        model_config = {
            "model": {
                "default": custom_model.get("model"),
                "provider": custom_model.get("provider", "openrouter"),
            }
        }
        if custom_model.get("base_url"):
            model_config["model"]["base_url"] = custom_model["base_url"]
        if custom_model.get("api_key"):
            model_config["model"]["api_key"] = custom_model["api_key"]
    elif preset_name in PRESETS:
        model_config = PRESETS[preset_name]
    else:
        print(f"❌ Unknown preset '{preset_name}'. Available: {', '.join(PRESETS.keys())}")
        sys.exit(1)

    for name in profile_names:
        config = read_config(name)
        # Merge model config (replace model block, keep everything else)
        config["model"] = model_config["model"]
        if "fallback_providers" in model_config:
            config["fallback_providers"] = model_config["fallback_providers"]
        if "auxiliary" in model_config:
            config["auxiliary"] = model_config["auxiliary"]
        write_config(name, config)
        preset_label = custom_model.get("model") if custom_model else preset_name
        print(f"  → {name} now uses: {preset_label}")


def sync_mcp():
    """Sync shared MCP servers into all profiles, plus profile-specific ones."""
    for name in get_all_profiles():
        config = read_config(name)
        if "mcp_servers" not in config:
            config["mcp_servers"] = {}

        # Merge shared MCP servers (don't overwrite profile-specific overrides)
        for server_name, server_config in SHARED_MCP_SERVERS.items():
            if server_name not in config["mcp_servers"]:
                config["mcp_servers"][server_name] = server_config

        # Merge profile-specific MCP servers
        for pname, servers in PROFILE_MCP_SERVERS.items():
            if name == pname:
                for sname, sconfig in servers.items():
                    if sname not in config["mcp_servers"]:
                        config["mcp_servers"][sname] = sconfig

        write_config(name, config)

    print(f"\nSynced shared MCP servers across {len(get_all_profiles())} profiles")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "list":
        list_profiles()

    elif command == "mcp-sync":
        sync_mcp()

    elif command == "switch":
        profiles = []
        preset = None
        custom = None
        i = 2
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg == "--model" and i + 1 < len(sys.argv):
                preset = sys.argv[i + 1]
                i += 2
            elif arg == "--model-custom" and i + 3 < len(sys.argv):
                custom = {
                    "model": sys.argv[i + 1],
                    "provider": sys.argv[i + 2],
                }
                i += 3
            else:
                profiles.append(arg)
                i += 1

        if not profiles:
            print("❌ Specify at least one profile name")
            sys.exit(1)
        if not preset and not custom:
            print("❌ Specify --model <preset> or --model-custom <model> <provider>")
            sys.exit(1)

        switch_model(profiles, preset, custom)

    else:
        print(f"❌ Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()