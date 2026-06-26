# Google Workspace Scope Testing Guide

## How to Test Missing Scopes

When `setup.py --check` shows partial authentication, test each functionality:

### 1. Test Gmail Read/Write
```bash
# This should work (readonly access)
python scripts/google_api.py gmail search "is:unread" --max 5

# These will fail with "Insufficient Permission" if scopes missing
python scripts/google_api.py gmail send --to test@example.com --subject "Test" --body "test"
python scripts/google_api.py gmail modify MESSAGE_ID --add-labels LABEL_ID
```

### 2. Test Contacts Access
```bash
# This will fail if contacts.readonly missing
python scripts/google_api.py contacts list --max 5
```

### 3. Test Docs Access
```bash
# This will fail if documents.readonly missing  
python scripts/google_api.py docs get DOC_ID
```

### 4. Check Current Scopes
```bash
python -c "import json; token = json.load(open('~/.hermes/google_token.json')); print('Scopes:', token.get('scope', '').split())"
```

## Common Error Messages

- **"Request had insufficient authentication scopes"**: Missing gmail.send or gmail.modify
- **"ACCESS_TOKEN_SCOPE_INSUFFICIENT"**: Missing contacts.readonly  
- **"Requested entity was not found"**: May indicate missing documents.readonly (or invalid doc ID)

## Fix: Re-authenticate with Full Scopes

1. Revoke current token: `setup.py --revoke`
2. Get new auth URL: `setup.py --auth-url` 
3. Complete OAuth flow - includes all scopes by default
4. Verify: `setup.py --check`