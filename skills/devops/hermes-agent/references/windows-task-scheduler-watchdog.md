# Windows Task Scheduler — Hermes Gateway Watchdog

## When to use this

The user's WSL VM was restarting for unknown reasons (WSL restart, Windows reboot, power cycle, etc.). The existing `~/.bashrc` auto-start only fires when a terminal is opened — if the VM restarts and no one opens a terminal, the gateway stays down. This doc covers registering a Windows scheduled task that runs `wsl.exe` to launch the watchdog on logon.

## Context (this session)

- **Distro**: Ubuntu (verified `Ubuntu-22.04` running, `Ubuntu` stopped)
- **User**: Company (same WSL and Windows username)
- **WSL config**: `/etc/wsl.conf` has `systemd=true` and `default=tapway`
- **Watchdog**: already installed at `~/.local/bin/hermes-gateway-watchdog`, uses `hermes gateway run` in a `while true` loop
- **`~/.bashrc`**: already has the auto-start snippet with tmux session guard

## Commands executed

### 1. Check WSL distro name

```bash
wsl.exe -l -v 2>/dev/null | cat -v
```

WSL outputs UTF-16; piping through `cat -v` reveals the actual chars. The clean distro name is `Ubuntu`.

### 2. Get Windows username

```bash
cmd.exe /c "echo %USERNAME%"
# → company
```

### 3. Create the scheduled task (from WSL, elevated)

`schtasks.exe /Create` requires Administrator. From WSL, use `Start-Process -Verb RunAs` to prompt UAC:

```powershell
powershell.exe -Command "Start-Process schtasks.exe -ArgumentList '/Create /SC ONLOGON /TN \"Hermes Gateway\" /TR \"wsl.exe -d Ubuntu bash -l -c ''~/.local/bin/hermes-gateway-watchdog &''\" /DELAY 0000:01 /F' -Verb RunAs -Wait"
```

Note the double single quotes `''...''` inside the PowerShell argument string — these escape literal single quotes for the WSL command.

### 4. Verify the task

```bash
schtasks.exe /Query /TN "Hermes Gateway" /FO LIST
```

Output:
```
Folder: \
HostName:      companyPowerBI
TaskName:      \Hermes Gateway
Next Run Time: N/A
Status:        Ready
Logon Mode:    Interactive only
```

### 5. Check the XML definition

```bash
schtasks.exe /Query /TN "Hermes Gateway" /XML
```

Relevant snippet:
```xml
<Command>wsl.exe</Command>
<Arguments>-d Ubuntu bash -l -c "~/.local/bin/hermes-gateway-watchdog &amp;"</Arguments>
```

### 6. Test-run the task immediately

```bash
schtasks.exe /Run /TN "Hermes Gateway"
```

## Pitfalls

1. **`schtasks /Create` fails with "Access is denied"** when run from a non-elevated WSL process. The fix: use `Start-Process -Verb RunAs` in PowerShell, or create a `.bat` on the Desktop and tell the user to right-click → Run as Administrator.

2. **`wsl.exe -l -q` produces UTF-16 binary output** — piping to `grep` gives "binary file matches". Use `cat -v` or `strings` to see clean text.

3. **Distro name matters** — the `-d Ubuntu` flag must match the installed distro. If wrong, `wsl.exe` silently uses the default, which may be a different distro. Always verify with `wsl.exe -l -v`.

4. **`&amp;` in the XML** — `schtasks /Create` with the `&` character in the TR argument encodes it as `&amp;` in the XML. This is correct WSL behavior; the bash command still runs in background.

5. **`ONLOGON` vs `ONSTART`** — `ONSTART` requires SYSTEM or admin privileges. `ONLOGON` runs as the current user and is easier to set up without elevation. Downside: it only fires on interactive logon, so if the user has no auto-login and the machine boots but nobody logs in, the task won't fire.

6. **`wsl.exe` delay** — WSL may not be ready immediately at boot/logon. The `/DELAY 0000:01` (1 second) is usually enough for WSL with `systemd=true`, but if the gateway fails to start, increase the delay to `0000:10` (10 seconds) or `0001:00` (1 minute).

7. **Duplicate gateways** — Running the task when a gateway is already active (e.g., from `~/.bashrc`) causes Telegram to reject the token ("already in use"). The watchdog doesn't check for existing sessions — it just runs `hermes gateway run`. This is fine for boot scenarios but would fail if triggered manually while the gateway is already running.
