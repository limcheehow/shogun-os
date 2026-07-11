#!/usr/bin/env python3
"""
One-shot LinkedIn profile lookup via CDP.
Usage: python linkedin-profile.py "Full Name"

Strategy:
1. Try direct URL: linkedin.com/in/[firstnamelastname] (fast, ~10s)
2. Fall back to LinkedIn search if 404
3. Scroll page, dump profile text to stdout
"""
import asyncio, json, urllib.request, websockets, sys
import sys

CDP_HTTP = "http://172.31.176.1:9222"

async def eval_js(ws, expr):
    cmd = json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True}})
    await ws.send(cmd)
    resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
    try:
        return resp["result"]["result"]["value"]
    except:
        return str(resp)

async def navigate(ws, url):
    cmd = json.dumps({"id": 1, "method": "Page.navigate", "params": {"url": url}})
    await ws.send(cmd)
    return await asyncio.wait_for(ws.recv(), timeout=15)

async def main():
    if len(sys.argv) < 2:
        print("Usage: python linkedin-profile.py \"Full Name\"")
        sys.exit(1)

    name = " ".join(sys.argv[1:])
    slug = name.lower().replace(" ", "").replace("-", "").replace("'", "")
    direct_url = f"https://www.linkedin.com/in/{slug}/"
    search_url = f"https://www.linkedin.com/search/results/people/?keywords={name.replace(' ', '%20')}"

    # Find a LinkedIn tab in Chrome
    resp = urllib.request.urlopen(CDP_HTTP + "/json", timeout=5)
    pages = json.loads(resp.read())
    target = None
    for p in pages:
        if "linkedin.com/feed" in p.get("url", ""):
            target = p
            break
    if not target:
        for p in pages:
            if "linkedin.com" in p.get("url", ""):
                target = p
                break
    if not target:
        print("ERROR: No LinkedIn tab open in Chrome. Open LinkedIn first.")
        sys.exit(1)

    ws_url = target["webSocketDebuggerUrl"]
    async with asyncio.timeout(25):
        async with websockets.connect(ws_url, max_size=2**20, ping_interval=None) as ws:
            # Step 1: Try direct URL
            await navigate(ws, direct_url)
            await asyncio.sleep(2)
            curr_url = await eval_js(ws, "window.location.href")

            if "/in/" not in curr_url or "404" in curr_url:
                # Step 2: Fall back to search
                search_url_encoded = f"https://www.linkedin.com/search/results/people/?keywords={name.replace(' ', '%20')}"
                await navigate(ws, search_url_encoded)
                await asyncio.sleep(3)
                text = await eval_js(ws, "document.body.innerText")
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                for l in lines:
                    print(l)
                    # Orphan prevention: link to category index hub
                    try:
                        sys.path.insert(0, os.path.expanduser("~/.hermes/scripts"))
                        from brain_compliance_helper import link_to_index
                        link_to_index(f"people/{slug}", "person")
                    except Exception:
                        pass

                return

            # Step 3: Scroll to load content
            await eval_js(ws, "window.scrollTo(0, 800)")
            await asyncio.sleep(1)
            await eval_js(ws, "window.scrollTo(0, 1600)")
            await asyncio.sleep(1)
            await eval_js(ws, "window.scrollTo(0, 2400)")
            await asyncio.sleep(1)

            text = await eval_js(ws, "document.body.innerText")
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            for l in lines:
                print(l)

if __name__ == "__main__":
    asyncio.run(main())
