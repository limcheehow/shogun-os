# Gmail Attachment Download

Pattern for downloading attachments (PDFs, images, etc.) from Gmail messages using the Gmail API directly.

## Common Use Case: Password-Protected PDF Statements

Banks and financial services often email password-protected PDF statements as attachments.

**Password source:** The password is typically mentioned in the email body text or snippet (e.g. "your registered mobile number", "your IC number", "your date of birth").

## Technique

The `google_api.py` wrapper doesn't have a built-in "download attachment" command. Use a direct Python script:

```python
import json, base64, os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Load token
token_path = os.path.expanduser("~/.hermes/google_token.json")
with open(token_path) as f:
    creds_data = json.load(f)
creds = Credentials.from_authorized_user_info(creds_data)

# Build Gmail service
service = build("gmail", "v1", credentials=creds)

# Get message
msg_id = "MESSAGE_ID_HERE"
msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()

# Recurse through MIME parts to find attachments
def find_attachment_parts(parts):
    results = []
    for part in parts:
        filename = part.get("filename", "")
        if filename and part.get("body", {}).get("attachmentId"):
            results.append(part)
        if "parts" in part:
            results.extend(find_attachment_parts(part["parts"]))
    return results

payload = msg.get("payload", {})
parts = payload.get("parts", [])
# Handle case where payload itself is the attachment
if payload.get("filename", ""):
    parts = [payload]

attachments = find_attachment_parts(parts or [payload])

for att in attachments:
    att_id = att["body"]["attachmentId"]
    filename = att["filename"]
    
    attachment = service.users().messages().attachments().get(
        userId="me", messageId=msg_id, id=att_id
    ).execute()
    
    file_data = base64.urlsafe_b64decode(attachment["data"])
    out_path = f"/tmp/{filename}"
    with open(out_path, "wb") as f:
        f.write(file_data)
    
    print(f"Saved: {out_path} ({len(file_data)} bytes)")
```

## Extracting Password-Protected PDFs

Use Python's `pypdf` library to unlock and extract text:

```python
from pypdf import PdfReader

reader = PdfReader("/tmp/statement.pdf")
reader.decrypt("PASSWORD_HERE")  # Password from the email body

text = ""
for page in reader.pages:
    text += page.extract_text()

print(text)
```

## Pitfalls

- Gmail API attachment size limit: base64-encoded data may be chunked (use `attachment.size` for verification)
- If the email body is empty in `get()` output, the body is likely HTML-only — check the snippet field for the password hint
- OAuth token must have `gmail.readonly` or `gmail.modify` scope
- Gateway restart NOT needed for this — it's a standalone script
