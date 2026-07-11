# Remote Chrome Launch from WSL

When Chrome_Debug.bat fails (profile copy too slow, Chrome doesn't relaunch, or you're remote), launch Chrome directly from WSL:

## One-shot Launch

```bash
powershell.exe -Command "Start-Process -FilePath 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList '--remote-debugging-port=9223', '--user-data-dir=C:\Users\your-company\chrome-debug-profile'" -PassThru
```

Wait 3 seconds, then verify:
```bash
curl -s http://$(ip route show default | awk '{print $3}'):9222/json/version
```

## Troubleshooting CDP Connection Resets

If `curl` to 172.31.176.1:9222 returns **"Connection reset by peer"**:

1. **Verify Chrome debug launched** — check if Chrome is listening on 9223:
   ```bash
   powershell.exe -Command "netstat -ano | findstr ':9223'"
   ```
   If nothing shows, Chrome didn't launch with `--remote-debugging-port=9223`.

2. **Check portproxy** — WSL:9222 → Win:9223 should exist:
   ```bash
   powershell.exe -Command "netsh interface portproxy show v4tov4"
   ```
   If missing, recreate: `netsh interface portproxy add v4tov4 listenport=9222 listenaddress=0.0.0.0 connectport=9223 connectaddress=127.0.0.1`

3. **Check firewall** — inbound rule `Chrome_Debug_9222` must allow TCP/9222:
   ```bash
   powershell.exe -Command "netsh advfirewall firewall show rule name='Chrome_Debug_9222' verbose"
   ```

4. **Verify debug Chrome is freshly launched** — not just a regular Chrome. Debug Chrome must have `--remote-debugging-port=9223` in its command line. Regular Chrome processes are renderers/utilities and don't serve CDP. Check with:
   ```bash
   powershell.exe -Command 'Get-CimInstance Win32_Process -Filter "Name = ''chrome.exe''" | Select-Object CommandLine | Where-Object { $_.CommandLine -match "remote-debugging" }'
   ```

## Key Points

- Chrome 148+ CDP HTTP endpoint (`/json/version`, `/json`) may reset connections on the first hit but works fine with the WebSocket URL
- The `webSocketDebuggerUrl` from `/json/version` is the most reliable entry point
- The portproxy maps WSL port 9222 → Windows port 9223
- "Connection reset by peer" on port 9222 means Chrome is **not running** with debug flags — not a Chrome 148+ bug
- After launching successfully, CDP WebSocket connections work for `Runtime.evaluate` on already-loaded pages
- The debug Chrome opens a new window on your desktop; it does NOT share your regular Chrome session automatically unless the profile was pre-copied to `chrome-debug-profile`