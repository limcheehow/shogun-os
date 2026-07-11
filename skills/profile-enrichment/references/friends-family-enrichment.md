# Friends & Family Enrichment — Facebook Export Session

This reference captures the approach used for enriching user's Facebook friends export (1,507 friends).

## Export Structure

Facebook data exports store friends in:
`connections/friends/your_friends.html`

Each friend is in a `<section>` block:
```html
<section><h2>Name</h2><footer><div>Date</div></footer></section>
```

Extract with Python regex:
```python
sections = re.findall(
    r'<section[^>]*>.*?<h2[^>]*>(.*?)</h2>.*?<footer[^>]*>.*?<div[^>]*>(.*?)</div>.*?</footer>.*?</section>',
    html, re.DOTALL
)
```

## Date Parsing

Dates are in format: `"%b %d, %Y %I:%M:%S %p"` (e.g. "Apr 20, 2026 12:30:36 pm")

**String-based sorting is WRONG** — dates like "Sep 30, 2025" sort *before* "Apr 20, 2026" alphabetically. Always:
```python
from datetime import datetime
dt = datetime.strptime(date_str, "%b %d, %Y %I:%M:%S %p")
```

## Year Distribution (1,507 friends)

| Year | Count | Notes |
|------|-------|-------|
| 2007 | 232 | Oldest batch |
| 2008 | 160 | |
| 2009 | 152 | |
| 2010 | 97 | |
| 2011 | 72 | |
| 2012 | 45 | |
| 2013 | 82 | |
| 2014 | 104 | |
| 2015 | 144 | |
| 2016 | 68 | |
| 2017 | 144 | |
| 2018 | 56 | |
| 2019 | 49 | |
| 2020 | 41 | |
| 2021 | 9 | |
| 2022 | 5 | |
| 2023 | 5 | |
| 2024 | 6 | |
| 2025 | 24 | Priority batch |
| 2026 | 12 | Most recent |

## Output Path

`~/brain/friends-and-family/<slug>.md` — NOT `~/brain/persons/` (isolated from CRM)

## Query Patterns for Web-Search-Only Enrichment

These query patterns worked well for Malaysian/SE Asian names:

| Pattern | When | Example |
|---------|------|---------|
| `"Full Name" Malaysia` | General search | `"Kai Yong Kang" Malaysia` |
| `Name Malaysia LinkedIn` | Find LinkedIn | `Kenneth Boo Malaysia LinkedIn` |
| `"Name" Company` | If company known | `"Mu Pathma" Cre8IOT` |
| `Name Embry-Riddle` | For likely ERAU alumni | `"Nick Candrella" Embry-Riddle` |

## Common-Name Disambiguation Notes

These surnames are very common in Malaysia and will yield multiple LinkedIn results:
- **Tan** (Tan Dennis, Hong Tan, Be Chu Tan)
- **Lim** (Winnie Lim, HJ Lim, YaoVoon Lim, Chong Li Ken)
- **Goh** (Johnson Goh, John Goh, Alex Goh, Petrina Goh)
- **Lee** (Derrick Lee, Toby Lee, Mark Leow)
- **Chew** (Ryan Chew, Terrence Chew)
- **Chua** (Kahhoe Chua, Keljin Chua, Mj Chua)

When multiple profiles match, note all possibilities in the file and flag with `"verify with CH"`.

## Known LinkedIn Profiles Found

### AWS/Cloud Cluster
- Kai Yong Kang — Startup Ecosystem Evangelist at AWS, also GenAI Fund Partner
- Sandy YW Woo — Country Director at eCloudvalley (AWS Premier Partner)
- YaoVoon Lim — Partner Development Manager at AWS
- Arren Tan — AVP Enterprise Sales at Exabytes Group

### Notable Entrepreneurs
- Nadhir Ashafiq — Co-Founder TheLorry.com (Forbes 30 Under 30, acquired by Kargo)
- Petrina Goh — Founder & Group CEO Nuren Group (5M+ users, VC-backed)
- Johnson Goh — CEO at MindHive (AI/GenAI for Zus Coffee)
- Mark Leow — Group MD of Verity Intelligence (EY Entrepreneur of Year nominee)
- George Gan — Founder CEO at Silicon & Sand, EO Trainer

### Tech/Engineering
- Ryan Chew — Building Clawbber.ai, CTO at RxTxt
- Low Yin Yin — Senior Software Developer at MYEG
- Mu Pathma — Founder & CEO Cre8IOT (IoT sensors pioneer)
- Kenneth Boo — Sales Director at iDimension Systems
- Alex Goh — Group Manager at Kenanga Group

### Embry-Riddle Era Connections (identified)
- Jeswin Joseph — Research Manager at NIAR/Wichita State (aviation)
- Nick Candrella — Contributed photos to ERAU aircraft design textbook
- Amy Hor — Optical Microscopist at Evident/Keysight (Santa Clara)
- Eugene Mark — Fellow at ISEAS Singapore (Ph.D., NTU)
- Lim Chee Han — Senior Researcher at Third World Network (Ph.D., Imperial)
- Keljin Chua — Director at Shopee Singapore
- Kyle Bembnister, Manish Shinde, Dhawal Patel, James Leoputra — likely ERAU classmates

### Hospitality/Service
- Teoh Kok Seng — Regional Director at Plaza Premium Group
- Kevin Leow — MD at Heezy (M) Sdn Bhd
- Fred Toh — CEO at EPI Everlast (paint manufacturing)

### Professional Services
- Derrick Lee — Principal / Lawyer at Messrs Derrick Lee (Penang)
- JiunYan Kee — Manager - Business Consulting at EY
- Chong Li Ken — Managing Partner at Collexe Consulting (sustainability)

## Batch Processing Script

The companion script `scripts/batch-enrich-exa.py` automates bulk enrichment:

- Reads friends list from `/tmp/friends_list.json`
- Calls Exa API for web search
- Extracts company/role/location/LinkedIn from snippets
- Writes enriched .md files

Key: EXA_API_KEY is in `~/.hermes/.env` under the main profile, NOT in bashrc.
Launch: `export EXA_API_KEY=<key> && python3 scripts/batch-enrich-exa.py`