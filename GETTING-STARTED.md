# Getting Started with unified-context

New to unified-context? Start here.

---

## What is it?

When you work on the same project across different IDEs (VS Code, Cursor, Claude Code, etc.), each AI agent starts fresh every session. **unified-context** fixes that by creating a shared memory in `.uctx/` that all IDEs can read and update.

---

## Install (One Time)

```bash
# Using uv (recommended)
uv tool install git+https://github.com/anilcelexsa/unified-context.git
uv tool update-shell    # add to PATH

# Or using pip
pip install git+https://github.com/anilcelexsa/unified-context.git
```

Verify:
```bash
uctx --version
uctx-mcp --version
```

---

## Setup (Per Project)

In your project directory:

```bash
# 1. Initialize the context store
uctx init

# 2. Generate MCP config for your IDEs
uctx setup claude-code
uctx setup cursor
uctx setup vscode
# ... add any other IDEs you use

# 3. Commit and push
git add .uctx/
git commit -m "add unified context"
git push

# 4. Restart your IDEs
# They'll now connect to the MCP server automatically
```

---

## How It Works

### The `.uctx/` Directory

Stores your project's shared context as plain Markdown files:

```
.uctx/
├── INDEX.md                ← AI reads this first
├── uctx.yaml              ← project metadata
├── conversations/         ← session summaries
├── solutions/             ← implemented solutions
├── tasks/                 ← pending and completed tasks
├── learnings/             ← gotchas and patterns
├── architecture/          ← design docs and plans
└── daily/                 ← activity log
```

### The Session Protocol

The AI agent in your IDE automatically:

1. **At start:** Reads the index and pending tasks
2. **During work:** Logs progress and saves decisions
3. **At end:** Saves a conversation summary

**The magic:** When you switch to a different IDE next session, the AI there sees everything that happened before.

---

## Common Tasks

### "I want to save this session's work"

The AI automatically saves at session end. You don't need to do anything.

If you want to manually trigger it in your IDE's MCP tool UI:
- Call `uctx_save_conversation` with:
  - `ide` = your IDE name (e.g., "claude-code")
  - `title` = what you did (e.g., "Implement payment webhook")
  - `summary` = 2-3 sentences

### "I discovered a gotcha I don't want to repeat"

Call `uctx_save_learning`:
```json
{
  "title": "FastAPI async context managers",
  "category": "gotcha",
  "description": "__aexit__ can run after response is sent..."
}
```

### "I solved a hard problem and want to document it"

Call `uctx_save_solution`:
```json
{
  "title": "JWT refresh token rotation",
  "problem": "Refresh tokens were reused indefinitely",
  "approach": "Implement one-time-use tokens with rotation counter"
}
```

### "I want to create a task for the next IDE"

Call `uctx_save_task`:
```json
{
  "title": "Add rate limiting to auth endpoint",
  "priority": "high",
  "acceptance_criteria": ["Limit 5 req/min per IP", "Return 429 on limit"]
}
```

### "I want to create a design document or implementation plan"

Call `uctx_save_note`:
```json
{
  "filename": "api-design",
  "subdir": "architecture",
  "content": "# API Design\n\n... [your markdown] ..."
}
```

### "I want to see what happened in past sessions"

```bash
# List recent conversations
uctx list conversations

# See today's activity across all IDEs
uctx today

# Search all context
uctx search "oauth"

# View store summary
uctx stats
```

---

## Update the Package

When new features are added to unified-context:

```bash
uv tool upgrade unified-context
```

Then update your IDE configs:
```bash
uctx setup claude-code
uctx setup cursor
# etc.
```

See [UPDATING.md](./UPDATING.md) for detailed instructions.

---

## Documentation

- **[MCP_TOOLS.md](./MCP_TOOLS.md)** — Complete reference for all 17 tools with examples
- **[.claude/UNIFIED-CONTEXT-INSTRUCTIONS.md](./.claude/UNIFIED-CONTEXT-INSTRUCTIONS.md)** — How AI agents should use the tools
- **[UPDATING.md](./UPDATING.md)** — How to update the package
- **[README.md](./README.md)** — Full feature overview and IDE setup

---

## Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| IDE can't find MCP server | Run `uctx setup <ide>` to regenerate config |
| `.uctx/` directory doesn't exist | Run `uctx init` in project root |
| Conversations aren't saving | Make sure the tool call is approved; check `.uctx/conversations/` exists |
| Want to sync with teammates | Commit and push `.uctx/` to git |

---

## Next Steps

1. Run `uctx setup <your-ide>` for each IDE you use
2. Restart your IDEs
3. Open a file in your project — the AI should read the context automatically
4. Work normally — the AI handles logging and saving
5. At end of day, commit `.uctx/` changes: `git add .uctx/ && git commit -m "uctx: update context" && git push`

---

## Questions?

- **For tool details:** See [MCP_TOOLS.md](./MCP_TOOLS.md)
- **For AI agent behavior:** See [.claude/UNIFIED-CONTEXT-INSTRUCTIONS.md](./.claude/UNIFIED-CONTEXT-INSTRUCTIONS.md)
- **For installation/updates:** See [UPDATING.md](./UPDATING.md)
- **For IDE-specific config:** See [README.md](./README.md#per-ide-manual-configuration)
