# Lark (Feishu) — Communication Provider Setup

> **Enterprise messaging platform by ByteDance.** Used by many companies in APAC.
> Implements the [COMMS_ABSTRACTION.md](../../docs/architecture/COMMS_ABSTRACTION.md) interface.

## Setup

### 1. Create a Lark Custom App

1. Go to [Lark Developer Console](https://open.larksuite.com/app)
2. Click **Create App** → **Custom App**
3. Give it a name (e.g. "HR Manager Bot")
4. Go to **App Basic Information** → note your `App ID` and `App Secret`

### 2. Configure Permissions

Add these permission scopes in **Permissions → API Permissions**:

| Scope | Purpose |
|-------|---------|
| `im:message` | Send and read messages |
| `im:message:send_as_bot` | Send messages as bot |
| `im:chat` | Access chat information |
| `im:chat:readonly` | Read chat history |

### 3. Publish the App

Lark custom apps need to be **enabled and versioned** before they can send messages:

1. Go to **Version Management & Release**
2. Create a new version
3. Add permission scopes to the version
4. Submit for review and publish
5. Add the bot to your chats: `/add <bot-name>`

### 4. Get Bot Token

Two options:

**Option A: App ID + App Secret (auto-refresh, recommended):**
```bash
echo 'LARK_APP_ID=cli_xxx' >> ~/.hermes/.env
echo 'LARK_APP_SECRET=*** >> ~/.hermes/.env
```

The provider handles token refresh automatically (tokens expire every 2 hours).

**Option B: Pre-authenticated Tenant Access Token:**
```bash
echo 'LARK_ACCESS_TOKEN=*** >> ~/.hermes/.env
```

### 5. Configure the Profile

In `~/.hermes/profiles/<profile>/scrum.yaml`:

```yaml
profile: hr-manager
app_name: Jinzai
comm_provider: lark

team:
  - name: "Alice"
    user_id: "ou_xxxx"        # Lark user_id (from Contacts API)
    role: "HR Manager"
```

### 6. Verify

```bash
# Test DM sending
echo '{"id":1,"method":"tools/call","params":{"name":"comm_send_dm","arguments":{"userId":"ou_xxx","text":"Hello from Company OS!"}}}' \
  | python3 -c "from comm.lark import LarkProvider; p = LarkProvider({'LARK_APP_ID': '...', 'LARK_APP_SECRET': '...'}); print(p.send_dm('ou_xxx', 'Hello!'))"

# Expected: {"thread_id": "om_xxx", "conversation_id": "oc_xxx"}
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Lark auth failed` | Check App ID and Secret in `.env`. App must be published. |
| `Permission denied` | Add required API scopes and create a new version. |
| Bot doesn't receive events | Configure event subscriptions in Developer Console → Events. |
| Token expired | The provider auto-refreshes. If it fails, check `LARK_APP_SECRET` hasn't been rotated. |
| `User not found` | Verify the user_id format (`ou_xxx` for open_id, `user_xxx` for user_id). Lark has multiple ID types. |