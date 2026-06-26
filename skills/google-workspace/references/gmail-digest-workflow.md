# Gmail Email Digest Workflow

Pattern for "check my emails and give me a digest" requests.

## Steps

1. **Search with `newer_than:7d`** — covers "past week." Use `--max 20` to catch everything:
   ```bash
   $GAPI gmail search "newer_than:7d" --max 20
   ```

2. **Identify important emails** — signals:
   - Financial alerts (bank fraud, transfers, card locks)
   - Security notifications (new device login, password changes)
   - Receipts and payments
   - Replies the user sent (label `SENT`)
   - Newsletters (CATEGORY_UPDATES)

3. **Fetch full body for important ones** using:
   ```bash
   $GAPI gmail get MESSAGE_ID
   ```

4. **Ask for confirmation before acting** on any email (replying, sending, modifying).

## Categorization Structure

Use these groups for the digest:

- 🔴 **Important — Action Required** (security alerts, fraud warnings, account issues)
- 📋 **New Accounts & Payments** (receipts, signups, bills)
- 📰 **Newsletters & Subscriptions** (promotional emails, news digests)
- 🛒 **Promotions & Deals** (shopping, travel deals, coupons)
- 💬 **Community** (Reddit, forums, social)

## HTML Email Handling

Bank and security emails often arrive as rich HTML. The `body` field in `gmail get`
output contains the raw HTML. For text-only content:
- Plaintext-only emails have a clean `body` string
- HTML emails embed readable text inside the HTML tags — scan for `<p>` or `<div>` content
- Strip tracking pixels (1x1 images) and `mj-raw` tags when summarizing

## Common Search Patterns

| Request | Query |
|---------|-------|
| Last week | `newer_than:7d` |
| Last 24h | `newer_than:1d` |
| Unread | `is:unread` |
| From someone | `from:boss@co.com` |
| Attachments | `has:attachment newer_than:7d` |
| Only personal | `category:personal newer_than:7d` |
