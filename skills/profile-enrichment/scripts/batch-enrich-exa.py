#!/usr/bin/env python3
"""
Batch-enrich Facebook friends with Exa web search.
Writes ~/brain/friends-and-family/<slug>.md for each person.

Usage:
  export EXA_API_KEY=your_key_here
  python3 batch-enrich-exa.py

The script processes a list from /tmp/friends_list.json (generated from
FB export HTML). It only enriches files that haven't been enriched yet.
Rate-limits to 3 requests/second to stay within Exa API quota.

Output: enriched markdown files in ~/brain/friends-and-family/
"""
import json, re, os, urllib.request, sys, time
from datetime import datetime

FRIENDS_DIR = os.path.expanduser("~/brain/friends-and-family")
EXA_API_KEY = os.environ.get("EXA_API_KEY", "")
if not EXA_API_KEY:
    print("ERROR: EXA_API_KEY not set.")
    sys.exit(1)

def slugify(name):
    s = name.lower().replace("'", "").replace(".", "").replace(",", "")
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'\s+', '-', s.strip())
    return s

def parse_dt(f):
    try:
        return datetime.strptime(f["date"], "%b %d, %Y %I:%M:%S %p")
    except:
        return datetime.min

def exa_search(name):
    """Search Exa for a person's professional info."""
    for query in [f'"{name}" Malaysia', f"{name} Malaysia"]:
        data = json.dumps({"query": query, "type": "auto", "numResults": 2}).encode()
        req = urllib.request.Request(
            "https://api.exa.ai/search",
            data=data,
            headers={"x-api-key": EXA_API_KEY, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            results = json.loads(resp.read()).get("results", [])
            if results:
                return results
        except:
            continue
    return []

def extract_info(results):
    """Extract company, role, location, LinkedIn from search results."""
    info = {"company": "", "role": "", "location": "", "linkedin": ""}
    text = "\n".join(
        r.get("title", "") + "\n" + (r.get("text", "") or "")[:1000]
        for r in results
    )[:3000]

    for r in results:
        url = r.get("url", "")
        if "linkedin.com/in/" in url:
            info["linkedin"] = url.split("?")[0]
            break

    pat = (
        r"(CEO|Director|Manager|Engineer|Founder|Head|Lead|Partner|President|"
        r"VP|Consultant|Analyst|Specialist|Coordinator|Officer|Assistant|"
        r"Executive|Developer|Architect|Designer|Lecturer|Professor|Researcher|"
        r"Advisor|Chairman|Owner|Principal)\s+(?:at|with|–|-|—|·|@|[|])"
        r"\s+([A-Z][A-Za-z0-9. &/\-–—,()]+?)(?=\s*[|,\n]|\s*$|\.)"
    )
    m = re.search(pat, text)
    if m:
        info["role"] = m.group(1).strip()
        info["company"] = re.sub(
            r"\s*\(.*?\)\s*$", "", m.group(2).strip()
        )[:80]

    for loc in [
        "Kuala Lumpur", "Selangor", "Penang", "Singapore", "Johor",
        "Ipoh", "Sabah", "Sarawak", "Malacca", "Perak", "Pahang",
        "Kedah", "Kelantan", "Terengganu", "Negeri Sembilan",
        "Jakarta", "Bangkok", "Ho Chi Minh", "Vietnam", "Indonesia",
        "United States", "US", "UK", "Australia", "China",
    ]:
        if loc in text[:2000]:
            info["location"] = loc
            break

    if not info["company"] and results:
        t = results[0].get("text", "")[:500]
        m2 = re.search(
            r"(?:at|–|—|·)\s*([A-Z][A-Za-z0-9. &/\-–—,]+"
            r"(?:Sdn\.?\s*Bhd\.?|Berhad|Inc|Ltd|LLC|Pte|Limited|Corp))",
            t,
        )
        if m2:
            info["company"] = m2.group(1).strip()[:80]

    return info


def build_file(name, date, info):
    profile_parts = [p for p in [info["role"], info["company"]] if p]
    profile_line = " · ".join(profile_parts) if profile_parts else "Facebook friend since 2007"

    contact_lines = []
    if info["company"]:
        contact_lines.append(f"- **Company:** {info['company']}")
    if info["role"]:
        contact_lines.append(f"- **Role:** {info['role']}")
    if info["linkedin"]:
        contact_lines.append(f"- **LinkedIn:** {info['linkedin']}")
    if info["location"]:
        contact_lines.append(f"- **Location:** {info['location']}")
    if not contact_lines:
        contact_lines.append("- _(Not found via web search)_")

    return f"""---
tags: [friend, facebook]
facebook_friend_since: {date}
source: facebook_export
enriched: 2026-05-30
---

# {name}

> {profile_line}

## Facebook Friendship
- **Friend Since:** {date}
- **Source:** Facebook data export

## Contact Information
{chr(10).join(contact_lines)}

## Relationship
- **Connection:** Old Facebook friend

## Timeline
- {date} | Added as Facebook friend.
- May 30, 2026 | Enriched via web search.

---
*Enriched: 2026-05-30 · Source: web_search*
"""


def main():
    with open("/tmp/friends_list.json") as f:
        friends = json.load(f)

    friends.sort(key=parse_dt)
    batch = [f for f in friends if parse_dt(f).year == 2007]

    pending = []
    for f in batch:
        slug = slugify(f["name"])
        fp = os.path.join(FRIENDS_DIR, f"{slug}.md")
        if not os.path.exists(fp):
            pending.append(f)
            continue
        with open(fp) as fh:
            content = fh.read()
        if "Not enriched" in content or "enriched" not in content:
            pending.append(f)

    total = len(pending)
    print(f"2007 batch: {len(batch)} total, {total} to enrich")

    success = 0
    errors = []
    for idx, f in enumerate(pending):
        name, date = f["name"], f["date"]
        slug = slugify(name)
        fp = os.path.join(FRIENDS_DIR, f"{slug}.md")

        sys.stdout.write(f"\r  [{idx+1}/{total}] {name[:35]:35s}")
        sys.stdout.flush()

        try:
            results = exa_search(name)
            info = extract_info(results)
            content = build_file(name, date, info)
            with open(fp, "w") as fout:
                fout.write(content)
            success += 1
        except Exception as e:
            errors.append((name, str(e)))

        time.sleep(0.35)

    print()
    print(f"Done. {success}/{total} enriched, {len(errors)} errors.")
    if errors:
        for n, e in errors[:10]:
            print(f"  ! {n}: {e}")


if __name__ == "__main__":
    main()