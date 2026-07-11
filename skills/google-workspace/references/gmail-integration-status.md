# Gmail Integration Status & Brain Integration Options

## Current Status (2026-05-02)

### ✅ Working Features
- **Gmail Search**: `is:unread`, `from:`, `newer_than:`, `has:attachment` queries
- **Email Reading**: Full email content retrieval via `gmail get`
- **Calendar Access**: Basic event listing (work calendar accessible via `--calendar` flag)
- **Authentication**: Partial OAuth with token refresh

### ❌ Missing Scopes
- `https://www.googleapis.com/auth/contacts.readonly` - Contact management
- `https://www.googleapis.com/auth/documents.readonly` - Document access
- `https://www.googleapis.com/auth/gmail.modify` - Label modification, archive, mark as read
- `https://www.googleapis.com/auth/gmail.send` - Email sending capability

### 🔧 Quick Fixes Available
```bash
# Re-authenticate with full scopes
python /home/user/.hermes/skills/productivity/google-workspace/scripts/setup.py --revoke
python /home/user/.hermes/skills/productivity/google-workspace/scripts/setup.py --auth-url
# Complete OAuth flow, then verify:
python /home/user/.hermes/skills/productivity/google-workspace/scripts/setup.py --check
```

## Brain Integration Options

### Option 1: Manual Email-to-Brain (Current)
**Status**: Ready to implement
**Requirements**: Current Gmail access + brain structure
**Workflow**:
1. `gmail search "is:unread"` to find new emails
2. `gmail get MESSAGE_ID` to read full content
3. Detect entities (people, companies)
4. Update brain pages with timeline entries
5. Extract action items

**Implementation**:
- Create script to process emails on demand
- Set up cron jobs for regular checks
- Implement noise filtering (noreply@, notifications@)
- Generate Gmail links with correct `authuser` parameter

### Option 2: Full GBrain Integration (Recommended)
**Status**: Requires GBrain installation
**Requirements**: 
- GBrain repo: `git clone https://github.com/garrytan/gbrain ~/gbrain`
- Email collector with Node.js
- Credential gateway (ClawVisor or Google OAuth)
- Automated enrichment pipeline

**Setup Flow**:
1. Install GBrain: `bun install && gbrain init`
2. Set up email collector with noise filtering
3. Configure credential gateway
4. Implement automated brain enrichment
5. Set up cron jobs for continuous operation

### Option 3: Hybrid Approach (Short-term)
**Status**: Quick implementation
**Requirements**: Current Gmail access + basic scripting
**Features**:
- Manual email processing via current setup
- Simple brain page updates
- Action item extraction
- Scheduled digest generation

## Current Email Examples (2026-05-02)
- Franco Fernando (The Polymathic Engineer) - Tech content
- Skechers - Promotional content
- AliExpress - Order updates
- Ryt Bank - Transaction alerts
- Google Wallet - Card additions

## Integration Recommendations

### For Immediate Use (1-2 days)
1. **Enable full Gmail access** - Complete OAuth setup
2. **Create manual email digest** - Process emails on demand
3. **Set up basic brain enrichment** - Update contacts, companies

### For Long-term (1 week)
1. **Set up GBrain integration** - Full email-to-brain automation
2. **Implement noise filtering** - Automatic categorization
3. **Create action tracking** - Extract and prioritize tasks

## Next Steps
1. Complete OAuth setup for full Gmail access
2. Choose integration approach (manual vs. automated)
3. Implement selected workflow
4. Test with current email examples