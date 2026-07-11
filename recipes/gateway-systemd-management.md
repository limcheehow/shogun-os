---
name: gateway-systemd-management
id: gateway-systemd-management
category: infra
setup_time: 15 min
cost: $0
depends_on: []
---

# Gateway Systemd Management

Systemd template units for per-profile gateway management. Provides automatic restart, watchdog with exponential backoff, dead-PTY detection, and orphaned process cleanup for all Hermes profile gateways.

## Architecture

```
systemd --user
  ├── hermes-gateway.service              (default profile)
  └── hermes-gateway@.service template    (per-profile)
        ├── hermes-gateway@crm-manager.service
        ├── hermes-gateway@hr-manager.service
        └── ...

restart-profile-gateway.sh (script)
  └── systemctl --user restart hermes-gateway@<profile>.service

gateway-signal-monitor.sh (cron every 2 min)
  └── Monitors PID changes, detects death/restart events
```

## Setup

### Step 1: Create the systemd template unit

Write to `~/.config/systemd/user/hermes-gateway@.service`:

```ini
[Unit]
Description=Hermes Gateway (%I)
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/hermes gateway run --profile %i
Restart=on-failure
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=3
Environment=HERMES_HOME=%h/.hermes
Environment=HOME=%h
WorkingDirectory=%h/.hermes/profiles/%i

# Watchdog with exponential backoff
Restart=on-failure
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=10

# Dead PTY detection — kill if no I/O for 5 minutes
TimeoutStopSec=30
WatchdogSec=300

# Orphan cleanup
KillMode=control-group
KillSignal=SIGTERM
SendSIGKILL=yes

# Resource limits
MemoryMax=2G
CPUQuota=80%

[Install]
WantedBy=default.target
```

For the **default** profile (no `%i`), create a separate unit at `~/.config/systemd/user/hermes-gateway.service`:

```ini
[Unit]
Description=Hermes Gateway (default)
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/hermes gateway run
Restart=on-failure
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=10
TimeoutStopSec=30
KillMode=control-group
KillSignal=SIGTERM
SendSIGKILL=yes
MemoryMax=2G
CPUQuota=80%

[Install]
WantedBy=default.target
```

### Step 2: Enable and start for each profile

```bash
# Reload systemd
systemctl --user daemon-reload

# Enable and start per profile
for profile in crm-manager hr-manager marketing-manager product-manager project-manager; do
    systemctl --user enable hermes-gateway@$profile.service
    systemctl --user start hermes-gateway@$profile.service
done

# Default gateway
systemctl --user enable hermes-gateway.service
systemctl --user start hermes-gateway.service
```

### Step 3: Create the restart script

Copy `scripts/restart-profile-gateway.sh` from this repo to `~/.hermes/scripts/`:

```bash
cp scripts/restart-profile-gateway.sh ~/.hermes/scripts/
chmod +x ~/.hermes/scripts/restart-profile-gateway.sh
```

Edit the `PROFILES` array at the top to match your profile names.

### Step 4: Create the signal monitor cron

```bash
hermes cron create \
  --name "Gateway Signal Monitor" \
  --schedule "*/2 * * * *" \
  --script gateway-signal-monitor.sh \
  --no-agent \
  --deliver local
```

### Step 5: API key corruption check

Add a quick health check script `~/.hermes/scripts/check-api-keys.sh`:

```bash
#!/bin/bash
# API key corruption check — ensures config.yaml has valid-looking keys
set -euo pipefail

check_config() {
    local file="$1"
    local name="$2"
    if [ ! -f "$file" ]; then
        echo "❌ $name: config not found"
        return 1
    fi
    local key=$(grep -A5 "^model:" "$file" | grep "api_key:" | head -1 | sed 's/.*api_key: *//')
    if [ -z "$key" ] || [ "$key" = "''" ] || [ "$key" = '""' ]; then
        echo "❌ $name: api_key is empty or missing"
        return 1
    fi
    echo "✅ $name: api_key present"
}

check_config "$HOME/.hermes/config.yaml" "main"
for p in "$HOME/.hermes/profiles/"*/config.yaml; do
    profile=$(basename "$(dirname "$p")")
    check_config "$p" "$profile"
done
```

## Cron Jobs

| Name | Schedule | Script | Agent | Delivery |
|------|----------|--------|-------|----------|
| Gateway Signal Monitor | `*/2 * * * *` | `gateway-signal-monitor.sh` | No | `local` |
| Gateway Scheduled Restart | `0 4 * * 0` | `gateway-scheduled-restart.sh` | No | `local` |

## Config

No additional config needed beyond the systemd unit files above. Edit the `PROFILES` array in `restart-profile-gateway.sh` to match your setup.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Gateway won't start | Check journal: `journalctl --user -u hermes-gateway@profile.service --no-pager -n 50` |
| Restart loop | Check `StartLimitBurst` — increase if fragile |
| Orphaned processes | `systemctl --user kill hermes-gateway@profile.service -s SIGKILL` then restart |
| Dead PTY | Set `WatchdogSec` lower (e.g., 120s) for faster detection |
| API key corruption | Run `check-api-keys.sh` — keys can get truncated during crash writes |