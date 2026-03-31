# unified-context

Cross-IDE shared context for AI coding tools. One `.uctx/` directory, every IDE, zero duplication.

When you work across VS Code, Cursor, Windsurf, and Claude Code on the same project, each AI agent starts from scratch every session. **unified-context** fixes that — it gives every IDE a shared memory backed by plain Markdown files in your repo.

**✨ Now with:** 3-layer memory hierarchy (session/project/global), event-based checkpoints, ranked search, and git integration.

---

## How it works

- A `.uctx/` directory in your project root stores conversations, tasks, solutions, learnings, and daily logs as human-readable Markdown + YAML
- Global learnings stored at `~/.uctx/global/` — knowledge reused across all projects
- An MCP server (`uctx-mcp`) exposes that store to any MCP-compatible IDE as **22 tools** (17 core + 5 new)
- Commit `.uctx/` to git and push — teammates and other IDEs stay in sync
- The AI agent handles reading and writing context; you just work normally
- Git context (commit hash, changed files) auto-captured and linked to all solutions and learnings
- **Global learnings auto-injected** into every session based on project tech stack and tags

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

| IDE | Auto-setup command | Config path |
|-----|--------------------|-------------|
| VS Code | `uctx setup vscode` | `.vscode/mcp.json` |
| Cursor | `uctx setup cursor` | `.cursor/mcp.json` + `.cursorrules` |
| Windsurf | `uctx setup windsurf` | `.windsurf/mcp.json` + `.windsurf/rules.md` |
| Claude Code | `uctx setup claude-code` | `.claude/mcp.json` + `.claude/CLAUDE.md` |
| Kiro (AWS) | `uctx setup kiro` | `.kiro/settings/mcp.json` |
| Trae (ByteDance) | `uctx setup trae` | `.trae/mcp.json` |
| Zed | `uctx setup zed` | snippet — see [Zed setup](#zed-setup) |
| Antigravity (Google) | `uctx setup antigravity` | `.vscode/mcp.json` |

---

## Install

```bash
uv tool install git+https://github.com/anilcelexsa/unified-context.git
```

This installs `uctx` and `uctx-mcp` as isolated CLI tools on your PATH — no virtual environment setup needed.

After install, make sure the shims are on your PATH:

```bash
uv tool update-shell   # adds uv's tool bin dir to PATH
# then restart your terminal and IDE
```

Alternatively with pip:

```bash
pip install git+https://github.com/anilcelexsa/unified-context.git
```

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/) (recommended) or pip.

> **Note:** `uctx setup <ide>` resolves the full path to `uctx-mcp` at setup time and writes it into the MCP config. If you reinstall or move the binary, re-run `uctx setup <ide>` to update the path.

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
git push
```

The AI agent will now call `uctx_read_index` at session start and keep the store updated automatically.

---

## Git sync

Context is synced via plain git — there is no background daemon or auto-push.

**Recommended workflow:**

```bash
# Pull latest context before starting a session
git pull

# After a session (or at end of day), commit and push
git add .uctx/
git commit -m "uctx: update context"
git push
```

The `.uctx/` directory only excludes lock files and `.sync-state` — everything else (conversations, tasks, solutions, learnings, daily logs) is committed and shared.

If two IDEs write simultaneously and git reports a conflict in `.uctx/`, the files are plain Markdown — open them, keep both entries, and commit the merge.

---

## Per-IDE manual configuration

If `uctx setup` doesn't work for your environment, configure the MCP server manually. Replace `FULL_PATH_TO_UCTX_MCP` with the output of `which uctx-mcp` (Mac/Linux) or `where uctx-mcp` (Windows), and set `UCTX_PROJECT_ROOT` to your project path.

### VS Code

File: `.vscode/mcp.json` — note the root key is `"servers"`, not `"mcpServers"`.

```json
{
  "servers": {
    "unified-context": {
      "type": "stdio",
      "command": "FULL_PATH_TO_UCTX_MCP",
      "args": [],
      "env": {
        "UCTX_PROJECT_ROOT": "C:/Projects/my-app"
      }
    }
  }
}
```

Requires Copilot Agent mode. Verify: open Copilot chat → Agent mode → type "Read the project context index".

### Antigravity (Google)

Same config and path as VS Code (it is a VS Code fork):

```json
{
  "servers": {
    "unified-context": {
      "type": "stdio",
      "command": "FULL_PATH_TO_UCTX_MCP",
      "args": [],
      "env": {
        "UCTX_PROJECT_ROOT": "C:/Projects/my-app"
      }
    }
  }
}
```

### Cursor

File: `.cursor/mcp.json` — no `"type"` field (Cursor infers stdio from the command).

```json
{
  "mcpServers": {
    "unified-context": {
      "command": "FULL_PATH_TO_UCTX_MCP",
      "args": [],
      "env": {
        "UCTX_PROJECT_ROOT": "C:/Projects/my-app"
      }
    }
  }
}
```

### Windsurf

File: `.windsurf/mcp.json` — same format as Cursor.

```json
{
  "mcpServers": {
    "unified-context": {
      "command": "FULL_PATH_TO_UCTX_MCP",
      "args": [],
      "env": {
        "UCTX_PROJECT_ROOT": "C:/Projects/my-app"
      }
    }
  }
}
```

### Trae (ByteDance)

File: `.trae/mcp.json` — **`"mcpServers"` is an array**, not an object. Command is also an array.

```json
{
  "mcpServers": [
    {
      "name": "unified-context",
      "command": ["FULL_PATH_TO_UCTX_MCP"],
      "env": {
        "UCTX_PROJECT_ROOT": "C:/Projects/my-app"
      }
    }
  ]
}
```

> Wrong format (object instead of array) causes silent failure — no error shown.

### Kiro (AWS)

File: `.kiro/settings/mcp.json` — supports `autoApprove` for read-only tools so they run without confirmation prompts.

```json
{
  "mcpServers": {
    "unified-context": {
      "command": "FULL_PATH_TO_UCTX_MCP",
      "args": [],
      "env": {
        "UCTX_PROJECT_ROOT": "C:/Projects/my-app"
      },
      "disabled": false,
      "autoApprove": [
        "uctx_read_index",
        "uctx_list_conversations",
        "uctx_list_solutions",
        "uctx_list_tasks",
        "uctx_list_learnings",
        "uctx_get_daily_log",
        "uctx_search",
        "uctx_stats",
        "uctx_read_file"
      ]
    }
  }
}
```

### Claude Code

File: `.claude/mcp.json`

```json
{
  "mcpServers": {
    "unified-context": {
      "type": "stdio",
      "command": "FULL_PATH_TO_UCTX_MCP",
      "args": [],
      "env": {
        "UCTX_PROJECT_ROOT": "C:/Projects/my-app"
      }
    }
  }
}
```

### Other VS Code forks

- If the fork reads `.vscode/mcp.json` with `"servers"` key → use the VS Code config above
- If it has its own config dir with `"mcpServers"` → use the Cursor pattern
- Run `uctx setup vscode` as a first try and check if the IDE picks it up

---

## Zed setup

Zed is the exception — it uses a **user-level** config file, not a project-level one, and uses `"context_servers"` instead of `"mcpServers"`.

`uctx setup zed` generates a snippet file at `.zed/settings-uctx-snippet.json`. You must merge it manually:

**Windows:**
```powershell
notepad "$env:APPDATA\Zed\settings.json"
```

**Mac/Linux:**
```bash
nano ~/.config/zed/settings.json
```

Merge this block into your settings:

```json
{
  "context_servers": {
    "unified-context": {
      "command": {
        "path": "FULL_PATH_TO_UCTX_MCP",
        "args": [],
        "env": {
          "UCTX_PROJECT_ROOT": "C:/Projects/my-app"
        }
      }
    }
  }
}
```

> When switching projects in Zed, update `UCTX_PROJECT_ROOT` in your user settings, or omit it and let the server auto-detect from the working directory.

See `.zed/ZED-SETUP.md` in your project for the pre-filled snippet.

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

---

## MCP tools

The MCP server exposes **22 tools** (17 core + 5 new). All `project_path` parameters are optional — the server auto-detects the project root from the working directory.

### Core Tools (17)

| Tool | Description |
|------|-------------|
| `uctx_read_index` | Read INDEX.md + auto-injected relevant global learnings — call this first at session start |
| `uctx_save_conversation` | Save a session summary |
| `uctx_list_conversations` | List recent sessions across all IDEs |
| `uctx_save_task` | Create or update a task |
| `uctx_list_tasks` | List tasks by status |
| `uctx_complete_task` | Mark a task done (by title or slug) |
| `uctx_save_solution` | Record an implemented solution (auto-captures git context) |
| `uctx_list_solutions` | List all solutions |
| `uctx_save_learning` | Record a gotcha, pattern, or bug (auto-captures git context) |
| `uctx_list_learnings` | List all learnings |
| `uctx_daily_log` | Append to today's log |
| `uctx_get_daily_log` | Read today's (or a past) log |
| `uctx_save_note` | Write a freeform note to `.uctx/architecture/` |
| `uctx_read_file` | Read any file within `.uctx/` |
| `uctx_search` | Full-text search with ranking by relevance/recency |
| `uctx_stats` | Store summary (counts, size) |
| `uctx_init` | Initialize the store |

### New Tools (5)

| Tool | Description |
|------|-------------|
| `uctx_checkpoint` | Save at event boundaries (after_fix, after_plan, after_bug_found, after_confirmed) |
| `uctx_save_global_learning` | Save cross-project learning to `~/.uctx/global/` |
| `uctx_search` (enhanced) | Ranks by title/tags/body match + type + recency; supports `type_filter` |
| `uctx_read_index` (enhanced) | Auto-returns relevant global learnings based on tech stack/tags |

### Session protocol

The generated IDE config files include instructions for the AI agent to follow this pattern automatically:

1. **Session start** — call `uctx_read_index`, `uctx_list_tasks`, `uctx_get_daily_log`
2. **During work** — log actions with `uctx_daily_log`, record solutions and learnings
3. **Session end** — save a summary with `uctx_save_conversation`

**Detailed guide:** See [UNIFIED-CONTEXT-INSTRUCTIONS.md](./.claude/UNIFIED-CONTEXT-INSTRUCTIONS.md) for how AI agents should use these tools.

---

## Architecture Improvements

### 1. Three-Layer Memory Hierarchy
- **Session Memory** — ephemeral, in the AI's context window
- **Project Memory** — persistent in `.uctx/`, shared across IDEs
- **Global Memory** — persistent in `~/.uctx/global/`, automatically reused across all projects

**How it works:**
1. Save discoveries with `uctx_save_global_learning` (e.g., "Stripe webhook integration pattern", "FastAPI async pitfalls")
2. When you start a new project, call `uctx_read_index`
3. Relevant global learnings are **automatically injected** based on your project's tech stack and tags
4. No manual search needed — the AI sees them immediately

**Example:**
```
Project A (tech: stripe, fastapi):
  → uctx_read_index returns:
    - Project context
    - Relevant global learnings: "Stripe webhook pattern", "FastAPI async pitfalls"

Project B (tech: fastapi, postgres):
  → uctx_read_index returns:
    - Different project context
    - Different relevant global learnings: "FastAPI async pitfalls", "PostgreSQL connection pooling"
```

### 2. Event-Based Checkpoints
Instead of always calling individual save tools, use `uctx_checkpoint` to save at natural boundaries:

```json
uctx_checkpoint(
  trigger="after_fix",
  entry_type="solution",
  title="Fixed race condition in database writes",
  content="Added optimistic locking with version field...",
  tags=["database", "concurrency"]
)
```

Checkpoints automatically capture git context (commit hash, changed files) and trigger metadata.

### 3. Ranked Search
`uctx_search` now ranks results by relevance:
- Title matches score higher (+3) than tag matches (+2) or body matches (+1)
- Recent entries ranked higher than old ones
- Type priority: solutions > tasks > learnings > conversations
- Default returns top 5 results with scores

Use `type_filter` to search only solutions, learnings, etc.

### 4. Git Integration
All solutions and learnings automatically capture:
- **git_commit** — short commit hash (e.g., `a1b2c3d`)
- **git_files** — list of changed files in that commit
- Displayed inline in INDEX.md for easy navigation

This links all knowledge to actual code changes and helps trace decisions back to commits.

---

## Tool Reference

All 17 MCP tools are documented in **[MCP_TOOLS.md](./MCP_TOOLS.md)** with examples, parameters, and use cases.

Key tools:
- `uctx_read_index` — load context overview at session start
- `uctx_save_conversation` ⭐ — **save session summary at end** (most important)
- `uctx_daily_log` — log progress during work
- `uctx_save_solution`, `uctx_save_learning`, `uctx_save_note` — record knowledge and decisions
- `uctx_list_tasks`, `uctx_complete_task` — track work items

---

## Updating

The MCP server is installed from GitHub. To update when new features are added:

```bash
uv tool upgrade unified-context    # if using uv
# or
pip install --upgrade git+https://github.com/anilcelexsa/unified-context.git
```

Then re-run IDE setup to update binary paths (if needed):
```bash
uctx setup claude-code
uctx setup cursor
uctx setup vscode
```

See **[UPDATING.md](./UPDATING.md)** for full instructions.

---

## Multi-IDE example

You start a feature in Cursor in the morning, hand off to a teammate using VS Code in the afternoon, and review with Claude Code in the evening. Each agent sees:

- What was decided and why (conversations + solutions)
- What's still pending (tasks)
- What gotchas to watch out for (learnings)
- What happened today across all sessions (daily log)

No manual copy-paste. No lost context. Commit `.uctx/` to git and push.

---

## Known limitations

- **Git sync is manual** — there is no auto-push. You must commit and push `.uctx/` changes yourself.
- **Zed requires manual config merge** — `uctx setup zed` generates a snippet; you merge it into your user-level settings file.
- **Task title collisions** — two tasks whose titles produce the same slug (e.g. `"Fix bug"` and `"Fix bug!"`) share one file; the second save overwrites the first silently.
- **Monorepo root detection** — in a monorepo, `UCTX_PROJECT_ROOT` must be set explicitly in the MCP config to point to the correct sub-project; the auto-detect may latch onto the git root instead.

---

## Requirements

- Python 3.10+
- Any MCP-compatible IDE (see table above)
- Git (recommended, for cross-IDE sync)
- [uv](https://docs.astral.sh/uv/) (recommended for install)

---

## License

MIT — Edward Anil Joseph
