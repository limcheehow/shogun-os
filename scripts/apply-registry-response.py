#!/usr/bin/env python3
"""Apply central registry /api/register JSON onto local web.json + credentials.

Usage:
  apply-registry-response.py BODY.json WEB.json CRED.txt SHOGUN_HOME DOMAIN REGISTRY_URL
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 7:
        print(
            "usage: apply-registry-response.py BODY WEB CRED HOME DOMAIN REGISTRY_URL",
            file=sys.stderr,
        )
        return 2

    body_path, web_json, cred_file, shogun_home, domain_suffix, registry_url = sys.argv[1:7]
    try:
        body = json.loads(Path(body_path).read_text() or "{}")
    except Exception:
        body = {}

    sub = body.get("subdomain") or ""
    public = body.get("public_url") or (f"https://{sub}.{domain_suffix}" if sub else "")
    tid = body.get("tenant_id")
    tunnel = body.get("tunnel") or {}
    if not isinstance(tunnel, dict):
        try:
            tunnel = dict(tunnel)
        except Exception:
            tunnel = {}

    p = Path(web_json)
    data = json.loads(p.read_text()) if p.exists() else {}
    if sub:
        data["subdomain"] = sub
    if tid:
        data["tenant_id"] = tid
    data.setdefault("server", {})
    if public:
        data["server"]["public_url"] = public
    data.setdefault("registry", {})
    data["registry"]["registered"] = True
    data["registry"]["registered_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["registry"]["url"] = registry_url
    if tunnel:
        data["registry"]["tunnel"] = {
            k: tunnel.get(k)
            for k in ("id", "cloudflare_tunnel_id", "status", "name", "dns_record_id")
            if tunnel.get(k) is not None
        }
        token = tunnel.get("tunnel_token") or tunnel.get("token")
        if token:
            tp = Path(shogun_home) / "tunnel.token"
            tp.parent.mkdir(parents=True, exist_ok=True)
            tp.write_text(str(token) + "\n")
            tp.chmod(0o600)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n")

    cred = Path(cred_file)
    if cred.exists() and (sub or public):
        lines = []
        for line in cred.read_text().splitlines():
            if line.startswith("subdomain="):
                lines.append(f"subdomain={sub or data.get('subdomain', '')}")
            elif line.startswith("public_url="):
                lines.append(f"public_url={public}")
            elif line.startswith("tenant_id=") and tid:
                lines.append(f"tenant_id={tid}")
            else:
                lines.append(line)
        if public and not any(l.startswith("public_url=") for l in lines):
            lines.append(f"public_url={public}")
        cred.write_text("\n".join(lines) + "\n")

    print(sub)
    print(public)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
