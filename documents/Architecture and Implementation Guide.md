# Unified Cross-IDE Context System (uctx)

*Architecture & Implementation Guide — Windows Edition*

**Version 1.0 — March 2026**

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Storage Schema](#storage-schema)
4. [MCP Server — Tool Reference](#mcp-server--tool-reference)
5. [Installation (Windows)](#installation-windows)
6. [Per-IDE Setup Guides](#per-ide-setup-guides)
7. [Git Sync Strategy](#git-sync-strategy)
8. [CLI Reference](#cli-reference)
9. [Quick Start Walkthrough](#quick-start-walkthrough)
10. [Troubleshooting](#troubleshooting)
11. [Appendix A: Source File Listing](#appendix-a-source-file-listing)
12. [Appendix B: Adding Support for a New IDE](#appendix-b-adding-support-for-a-new-ide)

---

## Executive Summary

The **Unified Cross-IDE Context System (uctx)** lets every AI-powered coding IDE share the same project memory. It stores conversation summaries, implemented solutions, pending tasks, and hard-won learnings in one `.uctx/` directory per project.

Modern development workflows increasingly span multiple AI-powered IDEs:
- VS Code with Copilot for routine work
- Cursor for complex refactors
- Claude Code for CLI-driven automation

Each tool maintains isolated conversation history, leading to repeated explanations and lost decisions. **uctx eliminates this fragmentation.**

### Key Design Principles

- **MCP-only integration** — no IDE-specific plugins needed
- **Markdown + YAML** — human-readable, git-friendly storage
- **Git-backed sync** — no external infrastructure required
- **Zero config overhead** — automatic setup for all IDEs

### Supported IDEs

| IDE | Vendor | Config Path | Root Key |
|-----|--------|-------------|----------|
| VS Code | Microsoft | `.vscode/mcp.json` | `"servers"` |
| Antigravity | Google | `.vscode/mcp.json` | `"servers"` |
| Cursor | Anysphere | `.cursor/mcp.json` | `"mcpServers"` |
| Windsurf | Codeium | `.windsurf/mcp.json` | `"mcpServers"` |
| Trae | ByteDance | `.trae/mcp.json` | `"mcpServers"` (array) |
| Kiro | AWS | `.kiro/settings/mcp.json` | `"mcpServers"` |
| Zed | Zed Industries | User `settings.json` | `"context_servers"` |
| Claude Code | Anthropic | `.claude/mcp.json` | `"mcpServers"` |

> **⚠️ CRITICAL: Root Key Differences**
>
> VS Code and Antigravity use `"servers"`. All others use `"mcpServers"` except Zed which uses `"context_servers"`. Trae uses **array format**, not object. Wrong root key = silent failure.

---

## Architecture Overview

The uctx system has three layers:

### System Architecture

```
IDE Layer (VS Code, Cursor, Kiro, Claude Code)
         ↓
MCP Protocol (stdio)
         ↓
uctx-mcp Server (Python)
         ↓
.uctx/ Store (Markdown + YAML)
         ↓
Git (push/pull)
```

### The Three Layers

**1. IDE Layer**
AI agents call MCP tools as part of normal conversation flow.

**2. MCP Server Layer**
Translates MCP tool calls into file system operations.
Runs as subprocess of each IDE (stdio transport).

**3. Storage Layer**
`.uctx/` directory with Markdown files organized by type.
All state lives on disk; server is stateless between calls.

---

## Storage Schema

### Directory Structure

```
.uctx/
├── uctx.yaml              # Project manifest
├── INDEX.md               # Auto-generated routing file
├── conversations/         # Session summaries
├── solutions/             # Implemented solutions
├── tasks/
│   ├── pending/
│   └── completed/
├── learnings/             # Gotchas & patterns
├── architecture/          # Design decisions
└── daily/                 # Activity logs
```

### Project Manifest (uctx.yaml)

```yaml
name: my-saas-app
description: Next.js SaaS with Stripe billing
created: 2026-03-29T10:00:00+00:00
tech_stack: [nextjs, typescript, postgres, stripe]
active_ides: [vscode, cursor, claude-code]
sync_mode: git
auto_index: true
max_conversation_age_days: 30
```

### Conversation Example

```yaml
---
id: a1b2c3d4
ide: cursor
model: claude-3.5-sonnet
timestamp: 2026-03-29T14:30:00+00:00
title: Implemented Stripe webhook handler
key_decisions:
  - Used idempotency keys for retry safety
  - Chose synchronous verification over async queue
files_modified:
  - src/api/webhooks/stripe.ts
  - src/lib/billing.ts
follow_up_tasks:
  - Add webhook signature verification tests
tags: [billing, stripe, webhooks]
---

## Summary

Implemented the Stripe webhook handler for subscription lifecycle events.
```

### Solution Example

```yaml
---
id: e5f6g7h8
title: Stripe Webhook Idempotency
created: 2026-03-29T14:45:00+00:00
ide_origin: cursor
files_involved: [src/api/webhooks/stripe.ts]
tags: [stripe, webhooks, idempotency]
---

## Problem
Duplicate webhook deliveries causing double-charges.

## Approach
Store processed event IDs with unique constraint on stripe_event_id.

## Implementation
Created webhook_events table. Handler checks for existing record before processing.
```

### Task Example

```yaml
---
id: i9j0k1l2
title: Add webhook signature verification tests
status: pending
priority: high
created: 2026-03-29T14:50:00+00:00
acceptance_criteria:
  - Test valid signature passes
  - Test expired timestamp rejected
  - Test tampered payload rejected
tags: [testing, stripe, security]
---

## Description
Write unit tests for Stripe webhook signature verification.
```

### Learning Example

```yaml
---
id: l0m1n2o3
title: Tailwind v4 Migration Gotcha
created: 2026-03-29T15:00:00+00:00
category: gotcha
tags: [tailwind, css, migration]
---

## Description
When migrating to Tailwind v4, the old `@apply` directive no longer works.
Use the new `@layer utilities { ... }` syntax instead.
```

### INDEX.md

> INDEX.md is auto-generated. LLMs read this at session start to understand what context exists without loading everything. This keeps token usage low.

---

## MCP Server — Tool Reference

### All 16 Tools

| Tool | Purpose | Key Parameters |
|------|---------|---|
| `uctx_init` | Initialize `.uctx/` | name, description, tech_stack |
| `uctx_read_index` | Read INDEX.md | — |
| `uctx_save_conversation` | Save session | ide, title, summary |
| `uctx_list_conversations` | List sessions | limit |
| `uctx_save_solution` | Record solution | title, problem, approach |
| `uctx_list_solutions` | List solutions | — |
| `uctx_save_task` | Create task | title, status, priority |
| `uctx_list_tasks` | List tasks | status |
| `uctx_complete_task` | Mark done | slug |
| `uctx_save_learning` | Record learning | title, category |
| `uctx_list_learnings` | List learnings | — |
| `uctx_daily_log` | Append to log | entry, ide |
| `uctx_get_daily_log` | Read log | date |
| `uctx_search` | Search context | query |
| `uctx_stats` | Store stats | — |
| `uctx_read_file` | Read file | file_path |

### Session Protocol

**Session START (3 calls)**

1. `uctx_read_index` — Load context overview
2. `uctx_list_tasks` — Check pending work
3. `uctx_get_daily_log` — See today's activity

**During Work (as needed)**

1. `uctx_daily_log` — Log significant actions
2. `uctx_save_solution` — When solving problems
3. `uctx_save_learning` — When discovering gotchas
4. `uctx_save_task` — When identifying follow-up work

**Session END (1 call)**

1. `uctx_save_conversation` — Save comprehensive summary

---

## Installation (Windows)

### Prerequisites

- Python 3.11+ (verify: `python --version`)
- pip or uv package manager
- Git (verify: `git --version`)

### Step 1: Install uctx

Using pip:

```powershell
pip install -e C:\Tools\unified-context
```

Using uv:

```powershell
uv pip install -e C:\Tools\unified-context
```

### Step 2: Verify Installation

```powershell
uctx --help
uctx-mcp --help
```

You should see help output from both commands.

### Step 3: Initialize a Project

```powershell
cd C:\Projects\my-app
uctx init --name "My SaaS App" --tech nextjs typescript postgres stripe
```

### Step 4: Set Up IDEs

Setup all IDEs at once:

```powershell
uctx setup all
```

Or setup individually:

```powershell
uctx setup vscode
uctx setup cursor
uctx setup claude-code
```

### pyproject.toml Reference

```toml
[project]
name = "unified-context"
version = "1.0.0"
requires-python = ">=3.10"
license = "MIT"
dependencies = [
    "pyyaml>=6.0",
    "click>=8.1",
    "rich>=13.0",
    "watchdog>=4.0",
    "portalocker>=2.7",
    "mcp>=1.0",
    "gitpython>=3.1",
]

[project.scripts]
uctx = "unified_context.cli:main"
uctx-mcp = "unified_context.mcp_server:main"

[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"
```

---

## Per-IDE Setup Guides

### 6.1 VS Code (Microsoft)

**Config Details:**
- File: `.vscode/mcp.json`
- Root key: `"servers"` (UNIQUE — not `"mcpServers"`)
- Requires: Copilot Agent mode
- Generated by: `uctx setup vscode`

**Configuration:**

```json
{
  "servers": {
    "unified-context": {
      "type": "stdio",
      "command": "uctx-mcp",
      "args": [],
      "env": {
        "UCTX_PROJECT_ROOT": "C:/Projects/my-app"
      }
    }
  }
}
```

**Verification:**

Open Copilot chat in Agent mode → type "Read the project context index" → agent calls `uctx_read_index` and displays contents.

---

### 6.2 Antigravity (Google)

**Config Details:**
- File: `.vscode/mcp.json` (same as VS Code — it is a fork)
- Root key: `"servers"` (same as VS Code)
- Additional: `.antigravity/uctx-integration.md` knowledge base file
- Generated by: `uctx setup antigravity`

**Configuration:**

```json
{
  "servers": {
    "unified-context": {
      "type": "stdio",
      "command": "uctx-mcp",
      "args": [],
      "env": {
        "UCTX_PROJECT_ROOT": "C:/Projects/my-app"
      }
    }
  }
}
```

Running `uctx setup antigravity` also creates the additional `.antigravity/uctx-integration.md` knowledge base file.

---

### 6.3 Cursor (Anysphere)

**Config Details:**
- File: `.cursor/mcp.json`
- Root key: `"mcpServers"`
- Additional: `.cursorrules` with session protocol
- Generated by: `uctx setup cursor`

**Configuration:**

```json
{
  "mcpServers": {
    "unified-context": {
      "command": "uctx-mcp",
      "args": [],
      "env": {
        "UCTX_PROJECT_ROOT": "C:/Projects/my-app"
      }
    }
  }
}
```

> **Note:** Cursor does NOT use `"type": "stdio"` — it infers stdio from the command.

---

### 6.4 Windsurf (Codeium)

**Config Details:**
- File: `.windsurf/mcp.json`
- Root key: `"mcpServers"`
- Additional: `.windsurf/rules.md` with session protocol
- Generated by: `uctx setup windsurf`

**Configuration:**

```json
{
  "mcpServers": {
    "unified-context": {
      "command": "uctx-mcp",
      "args": [],
      "env": {
        "UCTX_PROJECT_ROOT": "C:/Projects/my-app"
      }
    }
  }
}
```

> **Note:** Same format as Cursor — no `"type": "stdio"` — placed in `.windsurf/` directory.

---

### 6.5 Trae (ByteDance)

**Config Details:**
- File: `.trae/mcp.json`
- Root key: `"mcpServers"` — **ARRAY FORMAT** (unique!)
- Additional: `.trae/project_rules.md`
- Generated by: `uctx setup trae`
- MCP support since: v1.3.0 (April 2025)

**Configuration:**

```json
{
  "mcpServers": [
    {
      "name": "unified-context",
      "command": ["uctx-mcp"],
      "env": {
        "UCTX_PROJECT_ROOT": "C:/Projects/my-app"
      }
    }
  ]
}
```

> **CRITICAL:** `"mcpServers"` is an **array** with a `"name"` field. Command is also an **array** `["uctx-mcp"]`. Wrong format = silent failure.

---

### 6.6 Kiro (AWS)

**Config Details:**
- File: `.kiro/settings/mcp.json` (note `settings/` subdirectory)
- User-level: `%USERPROFILE%\.kiro\settings\mcp.json`
- Root key: `"mcpServers"`
- Additional: `.kiro/steering/uctx-integration.md`
- Generated by: `uctx setup kiro`
- Special: Supports `autoApprove` for read-only tools

**Configuration:**

```json
{
  "mcpServers": {
    "unified-context": {
      "command": "uctx-mcp",
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

Read-only tools run without confirmation. Write tools still prompt.

---

### 6.7 Zed (Zed Industries)

**Config Details:**
- Architecture: NOT a VS Code fork — built in Rust
- Config location: User-level `settings.json` only
- Windows path: `%APPDATA%\Zed\settings.json`
- Root key: `"context_servers"` (unique to Zed)
- Generated by: `uctx setup zed`

**Configuration:**

```json
{
  "context_servers": {
    "unified-context": {
      "command": "uctx-mcp",
      "args": [],
      "env": {
        "UCTX_PROJECT_ROOT": "C:/Projects/my-app"
      }
    }
  }
}
```

> **Important:** Zed's config is user-level only. Update `UCTX_PROJECT_ROOT` when switching projects, OR the server auto-detects from working directory.

**Manual Setup:**

```powershell
notepad "$env:APPDATA\Zed\settings.json"
```

Merge the `context_servers` block from `.uctx/zed-settings-snippet.json`.

---

### 6.8 Claude Code (Anthropic)

**Config Details:**
- File: `.claude/mcp.json`
- Root key: `"mcpServers"`
- Additional: `CLAUDE.md`, `.claude/commands/*.md`
- Generated by: `uctx setup claude-code`

**Configuration:**

```json
{
  "mcpServers": {
    "unified-context": {
      "type": "stdio",
      "command": "uctx-mcp",
      "args": [],
      "env": {
        "UCTX_PROJECT_ROOT": "C:/Projects/my-app"
      }
    }
  }
}
```

Additional files created:
- `CLAUDE.md` — Project instructions with `@.uctx/INDEX.md` import
- `/uctx-status` — Slash command for quick status report
- `/uctx-handoff` — Slash command for session handoff

---

### 6.9 Other VS Code Forks

For other VS Code forks:

1. If it reads `.vscode/mcp.json` with `"servers"` key → use VS Code config
2. If it has own config (`.ide-name/mcp.json`) with `"mcpServers"` → use Cursor pattern
3. Check IDE docs for specific MCP format

Test: Run `uctx setup vscode` and check if IDE picks it up.

---

## Git Sync Strategy

The `.uctx/` directory is designed to be committed to git.

### Why Git Works

- All files are Markdown — diffs are readable
- Each file is independent — conversations don't conflict
- No binary blobs — all plain text
- No external infrastructure — no database or APIs

### Sync Workflow

```powershell
git add .uctx/
git commit -m "uctx: session summary from cursor"
git push

# On another machine:
git pull
# Context now available to all IDEs
```

### Gitignore

The `uctx init` creates `.uctx/.gitignore` for ephemeral files:

```gitignore
*.lock
.sync-state
```

### Conflict Resolution

Conflicts are rare because files have unique names (date + IDE + hash).

If INDEX.md conflicts, regenerate it:

```powershell
uctx index
```

---

## CLI Reference

```
uctx init                              Initialize .uctx/ store
uctx setup vscode|cursor|all           Generate IDE configs
uctx log "text"                        Append to daily log
uctx task add "title" --priority high  Create task
uctx task list --status all            List tasks
uctx task complete slug                Mark task done
uctx conv list                         List conversations
uctx solution list                     List solutions
uctx learn add --title "..." --category gotcha  Record learning
uctx search "query"                    Search all context
uctx stats                             Show store statistics
uctx index                             Rebuild INDEX.md
uctx prune --days 30                   Remove old conversations
uctx today                             Show today's log
```

---

## Quick Start Walkthrough

### Complete Setup

```powershell
# 1. Install uctx
git clone https://github.com/youruser/unified-context.git C:\Tools\unified-context
cd C:\Tools\unified-context
pip install -e .

# 2. Navigate to your project
cd C:\Projects\my-saas-app

# 3. Initialize the context store
uctx init --name "My SaaS App" --tech nextjs typescript postgres stripe

# 4. Set up your IDEs
uctx setup vscode
uctx setup cursor
uctx setup claude-code

# 5. Verify the setup
uctx stats

# 6. Commit to git
git add .uctx/ .vscode/mcp.json .cursor/mcp.json .claude/mcp.json
git commit -m "Initialize uctx cross-IDE context"
git push
```

### Verify in Your IDE

Open VS Code and ask the AI agent:

**"Read the project context index and list pending tasks"**

The agent should call `uctx_read_index` and `uctx_list_tasks`.

### Switching IDEs Mid-Session

| Step | Action |
|------|--------|
| 1 | In current IDE: "Save a conversation summary and create tasks for unfinished work" |
| 2 | Open the new IDE |
| 3 | Ask: "Read the context index and check for pending tasks from the last session" |

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| MCP server not found | `uctx-mcp` not on PATH | Run `pip install -e .` and restart terminal |
| "Unknown tool" error | Wrong root key in config | Check IDE comparison table |
| Trae ignores config | Object instead of array format | Use array format with `"name"` field |
| Zed tools not showing | Config not in user `settings.json` | Merge snippet into `%APPDATA%\Zed\settings.json` |
| Kiro not connecting | Wrong config path | Must be `.kiro/settings/mcp.json` |
| INDEX.md outdated | Not rebuilt after manual edits | Run `uctx index` |
| Python not found | Wrong command | Windows uses `python`, not `python3` |
| Permission denied | No write access | Use `pip install --user -e .` |
| Config not detected | IDE not restarted | Close and reopen IDE completely |

---

## Appendix A: Source File Listing

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package config, dependencies, CLI entry points |
| `unified_context/__init__.py` | Package marker |
| `unified_context/schema.py` | Data classes, YAML serialization |
| `unified_context/engine.py` | Core CRUD engine for file operations |
| `unified_context/cli.py` | Click-based CLI with 14 commands |
| `unified_context/mcp_server.py` | MCP server with 16 tools |
| `unified_context/adapters.py` | Per-IDE config generators |

---

## Appendix B: Adding Support for a New IDE

### Step-by-Step

**1. Research the IDE's MCP format:**
- What is the config path? (e.g., `.newide/mcp.json`)
- What is the root key? (`"servers"`, `"mcpServers"`, etc.)
- Object or array format?
- Does it support `"type": "stdio"`?

**2. Implement the adapter:**

Create a `_gen_newide()` function in `adapters.py`:

```python
def _gen_newide(project_root: str) -> dict:
    return {
        "mcpServers": {
            "unified-context": {
                "command": "uctx-mcp",
                "env": {"UCTX_PROJECT_ROOT": project_root}
            }
        }
    }
```

**3. Register the IDE:**

Add to generators dict in `generate_adapter_config()`.

**4. Update the CLI:**

Add IDE name to Click choices in `cli.py`.

**5. Test:**

```powershell
uctx setup newide
# Verify config created at correct path
# Open IDE and check MCP tools appear
```

---

**Unified Cross-IDE Context System (uctx)**
**Version 1.0 — March 2026**
**Windows Edition**
