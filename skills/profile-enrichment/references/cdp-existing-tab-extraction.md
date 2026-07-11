# CDP Existing-Tab Extraction (Chrome 148 Workaround)

When both CDP approaches time out (Playwright `connect_over_cdp` hangs, raw CDP websocket navigation never fires `frameStoppedLoading`), use **existing-tab extraction**.

## The Problem

Chrome 148+ appears to hang on CDP navigation commands — `Page.navigate` returns a `frameId`/`loaderId` but the `Page.frameStoppedLoading` event never fires, and `Runtime.evaluate` calls after navigation fail with `KeyError: 'result'`.

The script `scripts/linkedin-profile.py` and the raw CDP approach in the SKILL.md Option B both assume navigation will complete. They don't.

## The Workaround: Skip Navigation, Use Existing Tab

If the user already has a LinkedIn tab open (e.g., they searched for the person during an earlier conversation), the profile content is **already loaded** in Chrome. You can connect to that tab and extract directly — zero navigation needed.

### Step 1: Find an Existing Tab with the Target Profile

```python
import asyncio, json, urllib.request

CDP_HTTP = "http://172.31.176.1:9222"
resp = urllib.request.urlopen(CDP_HTTP + "/json")
pages = json.loads(resp.read())

target = None
for p in pages:
    url = p.get("url", "").lower()
    title = p.get("title", "").lower()
    # Match on name in URL or title
    if "melvin-ong" in url or "melvin ong" in title:
        target = p
        break
```

### Step 2: Connect and Extract Directly

```python
import websockets

async with websockets.connect(target["webSocketDebuggerUrl"],
                              max_size=2**20, ping_interval=None) as ws:
    await asyncio.sleep(2)  # Let the page settle
    
    cmd = json.dumps({"id": 1, "method": "Runtime.evaluate",
                      "params": {"expression": "document.body?.innerText || ''",
                                 "returnByValue": True}})
    await ws.send(cmd)
    
    while True:
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=8)
            data = json.loads(msg)
            if "result" in data:
                text = data["result"]["result"]["value"]
                print(text)  # Full page content
                break
        except asyncio.TimeoutError:
            print("Timed out")
            break
```

### Step 3: If No Existing Tab Found

If no existing tab has the target profile, fall back to `web_search`:

```bash
web_search "First Last Company linkedin"
web_search "site:linkedin.com/in First Last Company"
```

Do NOT attempt to navigate via CDP — it will hang on Chrome 148+.

## Why This Works

- The page is **already loaded** — no navigation needed, no timeout risk
- Chrome's CDP WebSocket responds fine for `Runtime.evaluate` on already-loaded pages
- LinkedIn profile pages contain 5K-15K chars of innerText with full career history, education, activity feed
- The `websockets` library's `recv()` call works reliably once connected

## Extracting Additional Detail (About Section, etc.)

For structured sections (About, Experience, Education), use DOM selectors via `Runtime.evaluate`:

```javascript
(function() {
    var sections = document.querySelectorAll('section');
    var result = {};
    sections.forEach(function(s) {
        var h2 = s.querySelector('h2');
        var title = h2 ? h2.innerText.trim() : s.id || 'unnamed';
        result[title] = s.innerText.substring(0, 2000);
    });
    return JSON.stringify(result, null, 2).substring(0, 6000);
})()
```

This returns section-by-section content that's easier to process than `document.body.innerText`.