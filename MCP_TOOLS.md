# MCP Tools Reference

Complete guide to all 17 tools exposed by the unified-context MCP server.

## Quick Start for Users

Most users don't need to call these tools directly—the AI agent in your IDE handles it automatically. The agent follows this **session protocol**:

1. **Session start** → reads the INDEX to understand context
2. **During work** → logs actions and records decisions
3. **Session end** → saves a summary automatically

However, if you want to manually invoke tools or understand what's happening, read on.

---

## Tool Categories

### 📖 Reading Context (Auto-approved in most IDEs)

These tools are read-only and typically don't require confirmation.

#### `uctx_read_index`
**Purpose:** Load the context overview at session start.

**Who calls it:** The AI agent, automatically at session start.

**Parameters:**
- `project_path` (optional) — defaults to current directory

**Returns:** The full INDEX.md file with a routing table of all context sections.

**Example use:**
```
Claude Code starts → calls uctx_read_index → sees:
  - 3 pending tasks
  - 2 active solutions in progress
  - 5 past conversations
  - Recent learnings about async patterns
```

---

#### `uctx_list_conversations`
**Purpose:** See recent session summaries across all IDEs.

**Who calls it:** You, to review what happened in past sessions; or the AI agent to find relevant context.

**Parameters:**
- `project_path` (optional)
- `limit` (default: 10) — how many recent conversations to return

**Returns:** List of conversation metadata (title, IDE used, timestamp, tags).

**Example:**
```json
{
  "conversations": [
    {
      "title": "Add OAuth to login flow",
      "ide": "cursor",
      "model": "claude-sonnet",
      "timestamp": "2026-03-28T14:32:00Z",
      "files_modified": ["auth.py", "config.yaml"],
      "tags": ["auth", "backend"]
    }
  ]
}
```

---

#### `uctx_list_tasks`
**Purpose:** See what work is pending, in progress, or done.

**Who calls it:** The AI agent at session start; you, to track work.

**Parameters:**
- `project_path` (optional)
- `status` (default: `"pending"`) — one of: `"all"`, `"pending"`, `"in_progress"`, `"completed"`, `"blocked"`

**Returns:** List of tasks with title, status, priority, acceptance criteria.

---

#### `uctx_list_solutions`
**Purpose:** Browse implemented solutions and decisions.

**Who calls it:** You, to understand what's been solved; the AI agent, to avoid re-solving the same problem.

**Returns:** List of past solutions with problem statement, approach, implementation details, and files involved.

---

#### `uctx_list_learnings`
**Purpose:** Review gotchas, patterns, and hard-won knowledge.

**Who calls it:** You, when you hit a new problem; the AI agent, to avoid pitfalls.

**Returns:** List of learnings categorized as: `"bug"`, `"pattern"`, `"gotcha"`, `"performance"`, `"security"`.

---

#### `uctx_get_daily_log`
**Purpose:** Review what happened across all IDEs today (or on a past date).

**Who calls it:** You, to see activity; the AI agent, to understand what's been done.

**Parameters:**
- `project_path` (optional)
- `date` (optional, default: today) — format: `"YYYY-MM-DD"`

**Returns:** Chronological log of entries from all IDEs that worked on this project today.

---

#### `uctx_read_file`
**Purpose:** Read any specific file within `.uctx/` (e.g., a specific solution, architecture note, or decision).

**Who calls it:** The AI agent, to drill into a specific context file.

**Parameters:**
- `project_path` (optional)
- `file_path` (required) — relative path within `.uctx/`, e.g., `"solutions/auth-refactor.md"` or `"architecture/api-design.md"`

**Returns:** Full markdown content of that file.

---

#### `uctx_search`
**Purpose:** Full-text search across all context files.

**Who calls it:** You or the AI agent, when you need to find something specific.

**Parameters:**
- `project_path` (optional)
- `query` (required) — search term or phrase
- `max_results` (default: 20)

**Returns:** List of matching files with snippets.

---

#### `uctx_stats`
**Purpose:** Get a summary of your context store—how many conversations, solutions, tasks, etc.

**Who calls it:** You, to see what you've accumulated.

**Returns:** Counts and sizes for all context categories.

---

### ✍️ Writing/Recording Context

#### `uctx_save_conversation` ⭐ IMPORTANT

**Purpose:** Save a session summary when you're done with productive work.

**Who calls it:** Should be called by the AI agent automatically at session end. Can also be called manually.

**When to use manually:**
- After a long brainstorming session
- After completing a feature or fixing a bug
- When handing off to a teammate
- End of day, before pushing changes

**Parameters:**
- `project_path` (optional)
- `ide` (required) — identifier like `"claude-code"`, `"cursor"`, `"vscode"`, `"antigravity"`, etc.
- `title` (required) — short session title, e.g., `"Implement payment webhook"`, `"Debug async race condition"`
- `summary` (required) — what was discussed and accomplished (2-3 sentences)
- `model` (optional) — AI model used, e.g., `"claude-opus"`, `"gpt-4"`
- `key_decisions` (optional) — list of major decisions made
- `files_modified` (optional) — list of files changed
- `follow_up_tasks` (optional) — list of next steps
- `tags` (optional) — tags like `["backend", "auth"]`, `["performance"]`, etc.

**Example call (from AI agent):**
```json
{
  "ide": "claude-code",
  "model": "claude-opus-4-6",
  "title": "Implement OAuth2 password grant flow",
  "summary": "Added support for password grant type in auth service. Integrated with existing token endpoints and added rate limiting.",
  "key_decisions": [
    "Use existing token endpoint instead of creating new one",
    "Implement rate limiting per user IP, not global"
  ],
  "files_modified": [
    "auth/handlers.py",
    "auth/models.py",
    "config/oauth.yaml"
  ],
  "follow_up_tasks": [
    "Add client rotation for service accounts",
    "Test with production OAuth clients"
  ],
  "tags": ["auth", "oauth", "backend"]
}
```

**Returns:** Path to the saved conversation file.

**Saved location:** `.uctx/conversations/YYYY-MM-DD_HH-MM-SS_<title-slug>.md`

**Why it matters:** Without this, each IDE loses the context of what happened in previous sessions. The next time you start coding, the AI agent has no idea what decisions were made, what files were edited, or what's left to do.

---

#### `uctx_save_solution`
**Purpose:** Record an implemented solution—the problem, the approach, the code, and why.

**Who calls it:** The AI agent, after solving a non-trivial problem; you, if you want to document a manual fix.

**Parameters:**
- `project_path` (optional)
- `title` (required) — e.g., `"Race condition in database writes"`
- `problem` (required) — what was wrong
- `approach` (required) — how you fixed it
- `implementation` (optional) — code details, architecture changes, etc.
- `ide_origin` (optional) — which IDE solved this
- `files_involved` (optional) — affected files
- `tags` (optional) — category tags

**Saved location:** `.uctx/solutions/`

---

#### `uctx_save_task`
**Purpose:** Create, update, or track a work item.

**Who calls it:** You (via CLI or manually) or the AI agent (when creating tasks from a conversation).

**Parameters:**
- `project_path` (optional)
- `title` (required)
- `status` (default: `"pending"`) — `"pending"` | `"in_progress"` | `"completed"` | `"blocked"`
- `priority` (default: `"medium"`) — `"low"` | `"medium"` | `"high"` | `"critical"`
- `description` (optional)
- `acceptance_criteria` (optional) — list of requirements
- `tags` (optional)

**Note:** Calling with the same `title` updates the existing task (overwrites).

**Saved location:** `.uctx/tasks/pending/` or `.uctx/tasks/completed/`

---

#### `uctx_complete_task`
**Purpose:** Mark a task as done.

**Who calls it:** You or the AI agent.

**Parameters:**
- `project_path` (optional)
- `slug` (optional) — task filename stem from `uctx_list_tasks` output
- `title` (optional) — exact task title (alternative to slug)

**Returns:** `{"status": "completed", "slug": "..."}` or `{"status": "not_found"}`

---

#### `uctx_save_learning`
**Purpose:** Record a gotcha, pattern, or hard-won insight.

**Who calls it:** You or the AI agent, when you discover something worth remembering.

**Parameters:**
- `project_path` (optional)
- `title` (required) — e.g., `"Async/await patterns in FastAPI"`
- `category` (required) — `"bug"` | `"pattern"` | `"gotcha"` | `"performance"` | `"security"`
- `description` (required) — the learning
- `tags` (optional)

**Saved location:** `.uctx/learnings/`

---

#### `uctx_daily_log`
**Purpose:** Append an activity entry to today's cross-IDE log.

**Who calls it:** The AI agent, at the end of the session or during work.

**Parameters:**
- `project_path` (optional)
- `entry` (required) — what you did, e.g., `"Debugged memory leak in WebSocket handler, narrowed to connection pool"`
- `ide` (required) — which IDE, e.g., `"claude-code"`

**Saved location:** `.uctx/daily/YYYY-MM-DD.md`

**Format:** Timestamped entries from all IDEs, so you see a single timeline.

---

#### `uctx_save_note`
**Purpose:** Write a freeform markdown note—architecture decisions, design docs, PRDs, implementation plans, etc.

**Who calls it:** You (manually) or the AI agent (e.g., when creating an implementation plan).

**Parameters:**
- `project_path` (optional)
- `filename` (required) — e.g., `"api-design.md"`, `"implementation-plan.md"`
- `content` (required) — full markdown body
- `subdir` (default: `"architecture"`) — subdirectory within `.uctx/` where it's saved

**Saved location:** `.uctx/{subdir}/{filename}.md` (or just `.uctx/{subdir}/{filename}` if .md is already in filename)

**Example:** When you create an implementation plan in a session, call this to save it so the next IDE can see it:

```json
{
  "filename": "auth-refactor-plan",
  "subdir": "architecture",
  "content": "# OAuth2 Password Grant Implementation Plan\n\n... [full markdown plan] ..."
}
```

---

#### `uctx_init`
**Purpose:** Initialize the `.uctx/` context store in a new project.

**Who calls it:** You, once, at project setup (via `uctx init` CLI).

**Parameters:**
- `project_path` (optional)
- `name` (optional) — project name
- `description` (optional) — what the project does
- `tech_stack` (optional) — list of technologies

---

## How to Invoke Tools

### Option 1: AI Agent (Automatic)
The AI agent in your IDE should call these automatically. If it doesn't, add instructions.

### Option 2: CLI
Some tools have CLI wrappers:
```bash
uctx task list
uctx task create "Fix bug in auth"
uctx today                 # shows daily log
uctx search "async"        # searches context
uctx stats
```

### Option 3: Manual MCP Call
In IDEs that support MCP tool UI (VS Code with Copilot, Cursor, etc.), you can invoke tools directly from the UI.

### Option 4: Your Custom Code
Build a script that calls the MCP server stdin/stdout and invokes tools programmatically.

---

## Session Protocol (Recommended)

This is what your IDE's AI agent should do:

**Session Start:**
1. Call `uctx_read_index` — see what's already known
2. Call `uctx_list_tasks --status pending` — see pending work
3. Call `uctx_get_daily_log` — see today's activity

**During Work:**
- Call `uctx_daily_log` every time you make meaningful progress
- Call `uctx_save_task` to create or update work items
- Call `uctx_save_learning` when you discover a gotcha
- Call `uctx_save_solution` when you fix a non-trivial problem

**Session End:**
- Call `uctx_save_conversation` with session summary, decisions, files modified, and follow-up tasks

---

## Common Patterns

### "I want to save my implementation plan so the next IDE sees it"
Use `uctx_save_note`:
```json
{
  "filename": "my-feature-plan",
  "subdir": "architecture",
  "content": "# My Feature Implementation Plan\n\n..."
}
```

### "I want to document a decision for future reference"
Use `uctx_save_solution`:
```json
{
  "title": "Why we cache user roles in Redis",
  "problem": "User permission checks were causing database overload",
  "approach": "Cache roles in Redis with 5-min TTL, invalidate on role change"
}
```

### "I discovered a gotcha I don't want to repeat"
Use `uctx_save_learning`:
```json
{
  "title": "FastAPI + async/await pitfalls",
  "category": "gotcha",
  "description": "Never call blocking I/O inside an async route without wrapping in run_in_threadpool. It locks the event loop."
}
```

### "I want to ensure the next IDE knows what to do"
Use `uctx_save_task` with acceptance criteria:
```json
{
  "title": "Test OAuth2 integration with real clients",
  "priority": "high",
  "acceptance_criteria": [
    "Test with Postman desktop client",
    "Test with third-party web app",
    "Verify token refresh works",
    "Document flow in ARCHITECTURE.md"
  ]
}
```

---

## Troubleshooting

**"I saved a conversation but it's not showing up"**
- Check that `.uctx/` exists: `uctx stats`
- Check that the conversation file was created: `ls .uctx/conversations/`
- Commit and push: `git add .uctx/ && git commit -m "uctx: save conversation" && git push`

**"The IDE can't find the MCP server"**
- Verify the MCP config has the correct path to `uctx-mcp`: `which uctx-mcp` (Mac/Linux) or `where uctx-mcp` (Windows)
- Re-run: `uctx setup <ide-name>` to regenerate the config with the correct path
- Restart the IDE

**"I want to use a different project directory"**
- Set `UCTX_PROJECT_ROOT` in your MCP config (see README.md for IDE-specific steps)
- Or pass `project_path` to any tool call

---

## Auto-Approval Configuration

Some IDEs (Kiro) support auto-approval for read-only tools. Here's what should be auto-approved:

```json
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
```

These tools don't modify state, so approval isn't necessary.
