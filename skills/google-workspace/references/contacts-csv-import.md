# Contacts CSV Import — Secondary Google Account

## Use Case

You need to import contacts from a **secondary Google account** (e.g. work Gmail `your-user@your-domain.com`) into `~/brain/people/` as person files. The current OAuth token is for a different account.

## Workflow: CSV Export → Parse → Person Files

### Step 1: Export Contacts CSV from the source account

1. Sign into the source Google account (e.g. `your-user@your-domain.com`)
2. Go to https://contacts.google.com
3. Left sidebar → **Export**
4. Select **All contacts**
5. Export format: **Google CSV** (not Outlook CSV)
6. Download the CSV file

### Step 2: Upload the CSV

The user provides the CSV file path. Read it and parse:

```python
import csv
import re
from pathlib import Path

BRAIN_PEOPLE = Path.home() / "brain" / "people"

with open("path/to/contacts.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row.get("Name", "").strip()
        email = row.get("E-mail 1 - Value", "").strip()
        phone = row.get("Phone 1 - Value", "").strip()
        # Google CSV columns: Name, Given Name, Additional Name, Family Name,
        # E-mail 1 - Value, Phone 1 - Value, Organization 1 - Name, etc.
        
        if not name or not email:
            continue
        
        # Generate slug from name
        slug = re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-"))
        slug = re.sub(r"-+", "-", slug).strip("-")
        
        # Create person file
        person_file = BRAIN_PEOPLE / f"{slug}.md"
        if person_file.exists():
            continue  # Skip existing
        
        person_file.write_text(f"""# {name}

**Source:** Google Contacts CSV import

## Contact
- Email: {email}
- Phone: {phone or "N/A"}

## Organization
{row.get("Organization 1 - Name", "") or "N/A"}

## Notes
Imported from Google Contacts CSV export.
""")
```

### Step 3: Stats & Summary

After processing, report:
- Total contacts in CSV
- New person files created
- Existing person files skipped (matches by slug)
- Contacts without names/emails (skipped)

### Google CSV Column Reference

Google CSV exports use these common columns:
| Column | Content |
|--------|---------|
| Name | Full display name |
| Given Name | First name |
| Family Name | Last name |
| E-mail 1 - Value | Primary email |
| E-mail 2 - Value | Secondary email |
| Phone 1 - Value | Primary phone |
| Phone 2 - Value | Secondary phone |
| Organization 1 - Name | Company name |
| Organization 1 - Title | Job title |
| Address 1 - Formatted | Street address |
| Notes | Free-text notes |
| Group Membership | Contact group labels |
