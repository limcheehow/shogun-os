"""Configuration loader for the Shogun OS web portal backend.

Loads settings from ``~/.shogun-os/web.json`` and overlays environment variables.
"""

from __future__ import annotations

import json
import os
import secrets
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

SHOGUN_HOME = Path(os.environ.get("SHOGUN_HOME", Path.home() / ".shogun-os")).expanduser()
CONFIG_PATH = SHOGUN_HOME / "web.json"
DB_PATH = SHOGUN_HOME / "web.db"


@dataclass
class OAuthProviderConfig:
    """OAuth client credentials for a single IdP."""

    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = ""


@dataclass
class WebConfig:
    """Typed configuration for the per-tenant web portal."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8787
    debug: bool = False
    secret_key: str = ""
    session_max_age_seconds: int = 60 * 60 * 24 * 7  # 7 days

    # Tenant identity
    subdomain: str = "local"
    company_name: str = "Shogun OS"
    logo_url: str = ""
    timezone: str = "UTC"
    tenant_status: str = "active"

    # Paths
    db_path: str = str(DB_PATH)
    static_dir: str = ""
    gbrain_base_url: str = "http://127.0.0.1:7432"
    brain_root: str = str(Path.home() / "brain")

    # CORS
    cors_origins: List[str] = field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8787",
            "http://127.0.0.1:8787",
        ]
    )

    # Central registry (defaults = seamless public cloud)
    registry_url: str = "https://registry.shogun-os.ai"
    registry_api_key: str = ""
    auto_register: bool = False  # claim URL via onboarding Go Live, not silently on boot
    tenant_id: str = ""

    # OAuth
    public_base_url: str = "http://localhost:8787"
    google_oauth: OAuthProviderConfig = field(default_factory=OAuthProviderConfig)
    microsoft_oauth: OAuthProviderConfig = field(default_factory=OAuthProviderConfig)

    # Default department gateway port base (profile N uses base + N)
    gateway_port_base: int = 18789

    def ensure_secret(self) -> None:
        """Generate a durable secret key if missing."""
        if not self.secret_key:
            self.secret_key = secrets.token_urlsafe(48)


_config: Optional[WebConfig] = None


def _as_dict(obj: Any) -> Dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    return {}


def _oauth_from_dict(data: Dict[str, Any]) -> OAuthProviderConfig:
    return OAuthProviderConfig(
        client_id=str(data.get("client_id", "") or ""),
        client_secret=str(data.get("client_secret", "") or ""),
        redirect_uri=str(data.get("redirect_uri", "") or ""),
    )


def _load_json_file(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _apply_env(cfg: WebConfig) -> WebConfig:
    """Overlay environment variables on top of file config."""
    env = os.environ

    if env.get("SHOGUN_WEB_HOST"):
        cfg.host = env["SHOGUN_WEB_HOST"]
    if env.get("SHOGUN_WEB_PORT"):
        cfg.port = int(env["SHOGUN_WEB_PORT"])
    if env.get("SHOGUN_WEB_DEBUG"):
        cfg.debug = env["SHOGUN_WEB_DEBUG"].lower() in {"1", "true", "yes", "on"}
    if env.get("SHOGUN_WEB_SECRET_KEY"):
        cfg.secret_key = env["SHOGUN_WEB_SECRET_KEY"]
    if env.get("SHOGUN_WEB_SUBDOMAIN"):
        cfg.subdomain = env["SHOGUN_WEB_SUBDOMAIN"]
    if env.get("SHOGUN_WEB_COMPANY_NAME"):
        cfg.company_name = env["SHOGUN_WEB_COMPANY_NAME"]
    if env.get("SHOGUN_WEB_TIMEZONE"):
        cfg.timezone = env["SHOGUN_WEB_TIMEZONE"]
    if env.get("SHOGUN_WEB_DB_PATH"):
        cfg.db_path = env["SHOGUN_WEB_DB_PATH"]
    if env.get("SHOGUN_WEB_STATIC_DIR"):
        cfg.static_dir = env["SHOGUN_WEB_STATIC_DIR"]
    if env.get("SHOGUN_GBRAIN_URL"):
        cfg.gbrain_base_url = env["SHOGUN_GBRAIN_URL"]
    if env.get("SHOGUN_BRAIN_ROOT"):
        cfg.brain_root = env["SHOGUN_BRAIN_ROOT"]
    if env.get("SHOGUN_REGISTRY_URL"):
        cfg.registry_url = env["SHOGUN_REGISTRY_URL"]
    if env.get("SHOGUN_REGISTRY_API_KEY"):
        cfg.registry_api_key = env["SHOGUN_REGISTRY_API_KEY"]
    if env.get("SHOGUN_PUBLIC_BASE_URL"):
        cfg.public_base_url = env["SHOGUN_PUBLIC_BASE_URL"]
    if env.get("SHOGUN_CORS_ORIGINS"):
        cfg.cors_origins = [o.strip() for o in env["SHOGUN_CORS_ORIGINS"].split(",") if o.strip()]

    # Google OAuth
    if env.get("GOOGLE_OAUTH_CLIENT_ID"):
        cfg.google_oauth.client_id = env["GOOGLE_OAUTH_CLIENT_ID"]
    if env.get("GOOGLE_OAUTH_CLIENT_SECRET"):
        cfg.google_oauth.client_secret = env["GOOGLE_OAUTH_CLIENT_SECRET"]
    if env.get("GOOGLE_OAUTH_REDIRECT_URI"):
        cfg.google_oauth.redirect_uri = env["GOOGLE_OAUTH_REDIRECT_URI"]

    # Microsoft OAuth
    if env.get("MICROSOFT_OAUTH_CLIENT_ID"):
        cfg.microsoft_oauth.client_id = env["MICROSOFT_OAUTH_CLIENT_ID"]
    if env.get("MICROSOFT_OAUTH_CLIENT_SECRET"):
        cfg.microsoft_oauth.client_secret = env["MICROSOFT_OAUTH_CLIENT_SECRET"]
    if env.get("MICROSOFT_OAUTH_REDIRECT_URI"):
        cfg.microsoft_oauth.redirect_uri = env["MICROSOFT_OAUTH_REDIRECT_URI"]

    return cfg


def load_config(force_reload: bool = False) -> WebConfig:
    """Load configuration from disk + environment."""
    global _config
    if _config is not None and not force_reload:
        return _config

    SHOGUN_HOME.mkdir(parents=True, exist_ok=True)
    data = _load_json_file(CONFIG_PATH)

    google = _oauth_from_dict(_as_dict(data.get("google_oauth")))
    microsoft = _oauth_from_dict(_as_dict(data.get("microsoft_oauth")))

    default_static = str(
        Path(__file__).resolve().parent.parent / "ui" / "dist"
    )

    cfg = WebConfig(
        host=str(data.get("host", "0.0.0.0")),
        port=int(data.get("port", 8787)),
        debug=bool(data.get("debug", False)),
        secret_key=str(data.get("secret_key", "") or ""),
        session_max_age_seconds=int(data.get("session_max_age_seconds", 60 * 60 * 24 * 7)),
        subdomain=str(data.get("subdomain", "local")),
        company_name=str(data.get("company_name", "Shogun OS")),
        logo_url=str(data.get("logo_url", "") or ""),
        timezone=str(data.get("timezone", "UTC")),
        tenant_status=str(data.get("tenant_status", "active")),
        db_path=str(data.get("db_path", str(DB_PATH))),
        static_dir=str(data.get("static_dir", default_static) or default_static),
        gbrain_base_url=str(data.get("gbrain_base_url", "http://127.0.0.1:7432")),
        brain_root=str(data.get("brain_root", str(Path.home() / "brain"))),
        cors_origins=list(data.get("cors_origins") or WebConfig().cors_origins),
        registry_url=str(data.get("registry_url", "https://registry.shogun-os.ai") or "https://registry.shogun-os.ai"),
        registry_api_key=str(data.get("registry_api_key", "") or ""),
        auto_register=bool(data.get("auto_register", False)),
        tenant_id=str(data.get("tenant_id", "") or ""),
        public_base_url=str(data.get("public_base_url", "http://localhost:8787")),
        google_oauth=google,
        microsoft_oauth=microsoft,
        gateway_port_base=int(data.get("gateway_port_base", 18789)),
    )

    cfg = _apply_env(cfg)
    cfg.ensure_secret()

    # Fill default OAuth redirect URIs if unset
    if not cfg.google_oauth.redirect_uri:
        cfg.google_oauth.redirect_uri = f"{cfg.public_base_url.rstrip('/')}/auth/google/callback"
    if not cfg.microsoft_oauth.redirect_uri:
        cfg.microsoft_oauth.redirect_uri = (
            f"{cfg.public_base_url.rstrip('/')}/auth/microsoft/callback"
        )

    _config = cfg
    return cfg


def get_config() -> WebConfig:
    """Return the cached config, loading it on first call."""
    return load_config()


def save_config(cfg: Optional[WebConfig] = None) -> None:
    """Persist the current (or provided) config to ``web.json``."""
    global _config
    cfg = cfg or get_config()
    SHOGUN_HOME.mkdir(parents=True, exist_ok=True)

    payload = asdict(cfg)
    with CONFIG_PATH.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")
    _config = cfg


# Known shared department profiles (name -> Hermes profile_name suffix / gbrain source)
DEFAULT_DEPARTMENTS: List[Dict[str, Any]] = [
    {"name": "hr", "profile_name": "hr-manager", "label": "HR", "port_offset": 1},
    {"name": "finance", "profile_name": "finance-manager", "label": "Finance", "port_offset": 2},
    {
        "name": "procurement",
        "profile_name": "procurement-manager",
        "label": "Procurement",
        "port_offset": 3,
    },
    {"name": "crm", "profile_name": "crm-manager", "label": "CRM", "port_offset": 4},
    {
        "name": "marketing",
        "profile_name": "marketing-manager",
        "label": "Marketing",
        "port_offset": 5,
    },
    {
        "name": "compliance",
        "profile_name": "compliance-manager",
        "label": "Compliance",
        "port_offset": 6,
    },
    {
        "name": "customer-support",
        "profile_name": "customer-support-manager",
        "label": "Customer Support",
        "port_offset": 7,
    },
    {
        "name": "coding",
        "profile_name": "coding-manager",
        "label": "Coding",
        "port_offset": 8,
    },
    {
        "name": "executive",
        "profile_name": "executive-manager",
        "label": "Executive",
        "port_offset": 9,
    },
    {
        "name": "projects",
        "profile_name": "projects-manager",
        "label": "Projects",
        "port_offset": 10,
    },
]
