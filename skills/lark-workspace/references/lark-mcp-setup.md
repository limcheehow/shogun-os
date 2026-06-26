# Lark MCP Server Setup

Uses [YSzEthan/lark-office-mcp](https://github.com/YSzEthan/lark-office-mcp) — a Bun-based MCP server for Lark (Feishu) docs, wiki, drive, tasks, and search.

## Prerequisites

- **Bun** runtime: `curl -fsSL https://bun.sh/install | bash`
- **Lark App** created at https://open.feishu.cn/app
- **Permissions granted** in the app (see setup.md)

## Installation

```bash
# Clone into the target Hermes profile
mkdir -p ~/.hermes/profiles/executive-assistant/mcp-servers
cd ~/.hermes/profiles/executive-assistant/mcp-servers
git clone https://github.com/YSzEthan/lark-office-mcp.git
cd lark-office-mcp
bun install
```

## MCP Server Config

Add to the profile's `config.yaml`:

```yaml
mcp_servers:
  lark:
    command: bun
    args: [run, /path/to/lark-office-mcp/src/index.ts]
    env:
      LARK_APP_ID: ${LARK_APP_ID}
      LARK_APP_SECRET: ${LARK_APP_SECRET}
      LARK_CALLBACK_PORT: "9876"
```

## Environment Variables

```bash
# In ~/.hermes/profiles/<profile>/.env
LARK_APP_ID=cli_xxxxxxxxxxxxxxxxxxx
LARK_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Get these from https://open.feishu.cn/app → your app → Credentials.

## OAuth Flow

1. First call to any MCP tool opens a browser for Lark OAuth
2. After authorizing, the token is saved to `~/.lark-token.json`
3. Token auto-refreshes on expiry
4. Works without user intervention after first auth

## MCP Tools

| Category | Tools | What they do |
|----------|-------|-------------|
| Auth | `lark_auth_url`, `lark_auth` | OAuth flow |
| Users | `user_me`, `user_get`, `user_list` | Identity & directory |
| Documents | `doc_create`, `doc_read`, `doc_update`, `doc_delete`, `doc_append`, `doc_prepend`, `doc_insert_blocks`, `doc_delete_blocks`, `doc_move_blocks`, `doc_search_blocks`, `doc_indent_block`, `doc_batch_update_blocks`, `doc_move` | Full doc lifecycle |
| Wiki | `wiki_spaces`, `wiki_list_nodes`, `wiki_read`, `wiki_update`, `wiki_create_node`, `wiki_move_node`, `wiki_prepend`, `wiki_append`, `wiki_insert_blocks`, `wiki_delete_blocks` | Wiki management |
| Drive | `drive_list`, `drive_recent` | List cloud files |
| Search | `lark_search` | Global doc search |
| Tasks | `todo_list`, `todo_create`, `todo_search`, `todo_update`, `todo_add_members`, `todo_remove_members` | Task management |
| Task Lists | `tasklist_list`, `tasklist_create`, `tasklist_get`, `tasklist_update`, `tasklist_delete`, `tasklist_add_task`, `tasklist_remove_task`, `tasklist_tasks` | Task list management |
| Subtasks | `subtask_create`, `subtask_list`, `subtask_update` | Subtask management |
| Task Sections | `section_list`, `section_tasks`, `section_create`, `section_delete` | Task grouping |
| Completion | `task_complete`, `task_delete` | Complete/delete tasks |