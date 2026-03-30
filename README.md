# unified-context

Cross-IDE shared context for AI coding tools. One `.uctx/` directory, every IDE, zero duplication.

When you work across VS Code, Cursor, Windsurf, and Claude Code on the same project, each AI agent starts from scratch every session. **unified-context** fixes that — it gives every IDE a shared memory backed by plain Markdown files in your repo.

---

## How it works

- A `.uctx/` directory in your project root stores conversations, tasks, solutions, learnings, and daily logs as human-readable Markdown + YAML
- An MCP server (`uctx-mcp`) exposes that store to any MCP-compatible IDE as 17 tools
- Commit `.uctx/` to git — teammates and other IDEs stay in sync automatically
- The AI agent handles reading and writing context; you just work normally

```
.uctx/
├── INDEX.md               ← AI reads this first: compact overview of all context
├── uctx.yaml              ← project manifest
├── conversations/         ← session summaries (one per session, per IDE)
├── solutions/             ← implemented solutions & decisions
├── tasks/
│   ├── pending/           ← active work items
│   └── completed/
├── learnings/             ← gotchas, patterns, hard-won knowledge
├── architecture/          ← design decisions, plans, PRDs
└── daily/                 ← cross-IDE daily activity log
```

---

## Supported IDEs

| IDE | Config generated |
|-----|-----------------|
| VS Code | `.vscode/mcp.json` |
| Cursor | `.cursor/mcp.json` + `.cursorrules` |
| Windsurf | `.windsurf/mcp.json` + `.windsurf/rules.md` |
| Claude Code | `.claude/mcp.json` + `.claude/CLAUDE.md` |
| Kiro (AWS) | `.kiro/settings/mcp.json` |
| Trae (ByteDance) | `.trae/mcp.json` |
| Zed | `.zed/settings-uctx-snippet.json` |
| Antigravity (Google) | `.vscode/mcp.json` |

---

## Install

```bash
uv tool install git+https://github.com/anilcelexsa/unified-context.git
```

This installs `uctx` and `uctx-mcp` as isolated CLI tools on your PATH — no virtual environment setup needed.

Alternatively with pip:

```bash
pip install git+https://github.com/anilcelexsa/unified-context.git
```

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/) (recommended) or pip.

---

## Quick start

```bash
# 1. Initialize the context store in your project
cd my-project
uctx init

# 2. Generate the MCP config for your IDE(s)
uctx setup claude-code
uctx setup cursor
uctx setup vscode

# 3. Restart your IDE — the MCP server connects automatically

# 4. Commit .uctx/ so other IDEs and teammates share the same context
git add .uctx/
git commit -m "add unified context store"
```

That's it. The AI agent will now call `uctx_read_index` at session start and keep the store updated automatically.

---

## CLI reference

```bash
uctx init                          # initialize .uctx/ store
uctx setup <ide>                   # generate IDE MCP config
uctx today                         # show today's cross-IDE activity log
uctx task list                     # list pending tasks
uctx task list --status all        # list all tasks
uctx stats                         # show store summary
uctx search <query>                # search all context files
uctx index                         # rebuild INDEX.md
uctx prune                         # remove conversations older than 30 days
```

Supported `<ide>` values: `vscode`, `cursor`, `windsurf`, `claude-code`, `kiro`, `trae`, `zed`, `antigravity`

---

## MCP tools

The MCP server exposes 17 tools. All `project_path` parameters are optional — the server auto-detects the project root from the working directory.

| Tool | Description |
|------|-------------|
| `uctx_read_index` | Read INDEX.md — call this first at session start |
| `uctx_save_conversation` | Save a session summary |
| `uctx_list_conversations` | List recent sessions across all IDEs |
| `uctx_save_task` | Create or update a task |
| `uctx_list_tasks` | List tasks by status |
| `uctx_complete_task` | Mark a task done (by title or slug) |
| `uctx_save_solution` | Record an implemented solution |
| `uctx_list_solutions` | List all solutions |
| `uctx_save_learning` | Record a gotcha, pattern, or bug |
| `uctx_list_learnings` | List all learnings |
| `uctx_daily_log` | Append to today's log |
| `uctx_get_daily_log` | Read today's (or a past) log |
| `uctx_save_note` | Write a freeform note to `.uctx/architecture/` |
| `uctx_read_file` | Read any file within `.uctx/` |
| `uctx_search` | Full-text search across all context |
| `uctx_stats` | Store summary (counts, size) |
| `uctx_init` | Initialize the store |

### Session protocol

The generated IDE config files include instructions for the AI agent to follow this pattern automatically:

1. **Session start** — call `uctx_read_index`, `uctx_list_tasks`, `uctx_get_daily_log`
2. **During work** — log actions with `uctx_daily_log`, record solutions and learnings
3. **Session end** — save a summary with `uctx_save_conversation`

---

## Multi-IDE example

You start a feature in Cursor in the morning, hand off to a teammate using VS Code in the afternoon, and review with Claude Code in the evening. Each agent sees:

- What was decided and why (conversations + solutions)
- What's still pending (tasks)
- What gotchas to watch out for (learnings)
- What happened today across all sessions (daily log)

No manual copy-paste. No lost context. Just commit `.uctx/` to git.

---

## Zed setup

Zed uses user-level MCP config. After running `uctx setup zed`, merge the generated snippet into `~/.config/zed/settings.json`:

```bash
cat .zed/settings-uctx-snippet.json
```

See `.zed/ZED-SETUP.md` in your project for full instructions.

---

## Requirements

- Python 3.10+
- Any MCP-compatible IDE (see table above)
- Git (recommended, for cross-IDE sync)

---

## License

MIT — Edward Anil Joseph
