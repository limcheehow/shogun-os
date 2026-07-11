---
name: gateway-systemd-management
category: infra
setup_time: 15
cost: $0
depends_on: []
---

# Gateway Systemd Management

Per-profile gateway lifecycle management via systemd template units. Replaces ad-hoc tmux watchdogs with proper service supervision.

## Setup

1. Copy the template unit to `~/.config/systemd/user/hermes-gateway@.service`:

```ini
[Unit]
Description=Hermes Agent Gateway - %i Profile
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
ExecStart=/path/to/hermes-venv/bin/python -m hermes_cli.main --profile %i gateway run
WorkingDirectory=/path/to/.hermes
Environment="PATH=/path/to/hermes-venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="VIRTUAL_ENV=/path/to/hermes-venv"
Environment="HERMES_HOME=/path/to/.hermes"
Restart=always
RestartSec=5
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=210
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
```

2. Enable lingering (required for user services to survive logout):
```bash
sudo loginctl enable-linger $USER
```

3. Enable + start each profile gateway:
```bash
systemctl --user enable --now hermes-gateway@product-manager
systemctl --user enable --now hermes-gateway@hr-manager
# ... etc for each profile
```

4. Deploy the unified restart script:
```bash
cp scripts/restart-profile-gateway.sh ~/.hermes/scripts/
chmod +x ~/.hermes/scripts/restart-profile-gateway.sh

# Symlink to each profile for per-profile access
for profile in product-manager hr-manager crm-manager; do
  ln -sf ../../../scripts/restart-profile-gateway.sh \
    ~/.hermes/profiles/$profile/scripts/restart-gateway.sh
done
```

## Cron Jobs

| Job | Schedule | Script | Purpose |
|-----|----------|--------|---------|
| Gateway Signal Monitor | `*/2 * * * *` | `gateway-signal-monitor.sh` | Monitor PID changes + SIGTERM events |
| Model Health Check | `*/5 * * * *` | `model-health-check.sh` | Provider health + auto-failover |

## Config

```yaml
# scripts/config.yaml.example
hermes_home: "~/.hermes"
hermes_venv: "~/.hermes/hermes-agent/venv"
profiles:
  - product-manager
  - hr-manager
  - crm-manager
  - marketing-manager
  - project-manager
```

## Key Pitfalls

- **Duplicate services**: Never have both system-level (`/etc/systemd/system/hermes-gateway-<profile>.service`) and user-level (`hermes-gateway@<profile>.service`) units for the same profile. This causes an infinite crash loop.
- **Dead PTY**: If the tmux session dies but the watchdog survives (orphaned, PPID=1), child processes inherit broken FDs. Kill with `kill -9` and restart fresh.
- **SIGTERM/SIGHUP trapped**: The watchdog traps both. Use `kill -9` or `tmux kill-session` to stop it.
- **PID file cleanup**: `kill -9` does NOT clean `/tmp/hermes-gateway.pid`. Always `rm -f` after kill.
