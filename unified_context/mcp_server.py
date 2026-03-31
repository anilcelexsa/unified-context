"""
Unified Context MCP Server — Model Context Protocol server exposing
the context engine as tools for any MCP-compatible IDE.

This is the UNIVERSAL integration layer. Any IDE that speaks MCP
(VS Code, Claude Desktop, Antigravity, Cursor, Windsurf, etc.)
can connect to this server and read/write the shared context.

Run:
    uctx-mcp                           # stdio mode (default)
    python -m unified_context.mcp_server
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("uctx-mcp")


def _find_project_root(hint: str = "") -> Path:
    """Find project root from hint path, cwd, or UCTX_PROJECT_ROOT env var.

    Tries in order:
    1. Explicit hint path
    2. Current working directory and parents
    3. UCTX_PROJECT_ROOT environment variable (for multi-project IDEs like Zed)
    """
    # Start from hint or cwd
    start = Path(hint) if hint else Path.cwd()
    if start.is_file():
        start = start.parent

    # Check start path and all parents for .uctx or .git
    for parent in [start, *start.parents]:
        if (parent / ".uctx").exists():
            return parent
        if (parent / ".git").exists():
            return parent

    # Fallback: check UCTX_PROJECT_ROOT env var (set by IDE for user-level config)
    env_root = os.environ.get("UCTX_PROJECT_ROOT", "")
    if env_root and Path(env_root).exists():
        return Path(env_root).resolve()

    return start


# project_path description reused across all tools
_PATH_DESC = "Path to project root (optional — auto-detected from cwd if omitted)"
_PATH_PROP = {"type": "string", "description": _PATH_DESC}


def create_server():
    """Create and configure the MCP server with all context tools."""
    from mcp.server import Server
    from mcp.types import TextContent, Tool

    server = Server("unified-context")

    # ── Tool definitions ──────────────────────────────────────────────

    TOOLS = [
        Tool(
            name="uctx_init",
            description=(
                "Initialize a .uctx/ context store in the project. "
                "Call this first if .uctx/ doesn't exist yet."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": _PATH_PROP,
                    "name": {"type": "string", "description": "Project name"},
                    "description": {
                        "type": "string",
                        "description": "Project description",
                    },
                    "tech_stack": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Technologies used",
                    },
                },
            },
        ),
        Tool(
            name="uctx_read_index",
            description=(
                "Read the INDEX.md routing file. This is the recommended "
                "FIRST call at session start — returns a compact summary of "
                "all context sections without loading full content."
            ),
            inputSchema={
                "type": "object",
                "properties": {"project_path": _PATH_PROP},
            },
        ),
        Tool(
            name="uctx_save_conversation",
            description=(
                "Save a conversation summary after a productive session. "
                "Include key decisions, files modified, and follow-up tasks."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": _PATH_PROP,
                    "ide": {
                        "type": "string",
                        "description": "IDE identifier (e.g., vscode, claude-code, cursor)",
                    },
                    "model": {"type": "string", "description": "AI model used"},
                    "title": {
                        "type": "string",
                        "description": "Short conversation title",
                    },
                    "summary": {
                        "type": "string",
                        "description": "What was discussed and accomplished",
                    },
                    "key_decisions": {"type": "array", "items": {"type": "string"}},
                    "files_modified": {"type": "array", "items": {"type": "string"}},
                    "follow_up_tasks": {"type": "array", "items": {"type": "string"}},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["ide", "title", "summary"],
            },
        ),
        Tool(
            name="uctx_list_conversations",
            description="List recent conversation summaries across all IDEs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": _PATH_PROP,
                    "limit": {"type": "integer", "default": 10},
                },
            },
        ),
        Tool(
            name="uctx_save_solution",
            description=(
                "Record an implemented solution — what the problem was, "
                "the approach taken, and the implementation details."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": _PATH_PROP,
                    "title": {"type": "string"},
                    "problem": {"type": "string"},
                    "approach": {"type": "string"},
                    "implementation": {"type": "string"},
                    "ide_origin": {"type": "string"},
                    "files_involved": {"type": "array", "items": {"type": "string"}},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "problem", "approach"],
            },
        ),
        Tool(
            name="uctx_list_solutions",
            description="List all recorded solutions and their summaries.",
            inputSchema={
                "type": "object",
                "properties": {"project_path": _PATH_PROP},
            },
        ),
        Tool(
            name="uctx_save_task",
            description=(
                "Create or update a task (pending, in_progress, completed, blocked). "
                "To update an existing task, call with the same title — it will overwrite."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": _PATH_PROP,
                    "title": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed", "blocked"],
                        "default": "pending",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "default": "medium",
                    },
                    "description": {"type": "string"},
                    "acceptance_criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="uctx_list_tasks",
            description=(
                "List tasks filtered by status. Each result includes a '_slug' field "
                "you can pass directly to uctx_complete_task."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": _PATH_PROP,
                    "status": {
                        "type": "string",
                        "enum": [
                            "all",
                            "pending",
                            "completed",
                            "in_progress",
                            "blocked",
                        ],
                        "default": "pending",
                    },
                },
            },
        ),
        Tool(
            name="uctx_complete_task",
            description=(
                "Mark a pending task as completed. "
                "Pass either 'slug' (filename stem from uctx_list_tasks '_slug' field) "
                "or 'title' (exact task title) — whichever is more convenient."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": _PATH_PROP,
                    "slug": {
                        "type": "string",
                        "description": "Task slug (the '_slug' field from uctx_list_tasks)",
                    },
                    "title": {
                        "type": "string",
                        "description": "Exact task title (alternative to slug)",
                    },
                },
            },
        ),
        Tool(
            name="uctx_save_learning",
            description=(
                "Record a hard-won learning, gotcha, or pattern discovered "
                "during development."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": _PATH_PROP,
                    "title": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["bug", "pattern", "gotcha", "performance", "security"],
                    },
                    "description": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "category", "description"],
            },
        ),
        Tool(
            name="uctx_list_learnings",
            description="List all recorded learnings and gotchas.",
            inputSchema={
                "type": "object",
                "properties": {"project_path": _PATH_PROP},
            },
        ),
        Tool(
            name="uctx_daily_log",
            description="Append an entry to today's daily log.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": _PATH_PROP,
                    "entry": {"type": "string", "description": "Log entry text"},
                    "ide": {"type": "string", "description": "Source IDE"},
                },
                "required": ["entry", "ide"],
            },
        ),
        Tool(
            name="uctx_get_daily_log",
            description="Read today's (or a specific date's) daily log.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": _PATH_PROP,
                    "date": {
                        "type": "string",
                        "description": "YYYY-MM-DD (default: today)",
                    },
                },
            },
        ),
        Tool(
            name="uctx_search",
            description=(
                "Search all context files with ranking by recency, relevance, and type. "
                "Returns top results scored by title match, tags, body, and freshness."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": _PATH_PROP,
                    "query": {"type": "string", "description": "Search term(s)"},
                    "max_results": {
                        "type": "integer",
                        "default": 5,
                        "description": "Number of top-ranked results to return",
                    },
                    "type_filter": {
                        "type": "string",
                        "description": "Filter by type: 'solutions', 'learnings', 'conversations', 'tasks', or empty for all",
                        "default": "",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="uctx_stats",
            description="Get a summary of the context store (counts, sizes).",
            inputSchema={
                "type": "object",
                "properties": {"project_path": _PATH_PROP},
            },
        ),
        Tool(
            name="uctx_read_file",
            description=(
                "Read a specific context file by its relative path within .uctx/. "
                "Use after uctx_read_index to drill into a specific section."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": _PATH_PROP,
                    "file_path": {
                        "type": "string",
                        "description": "Relative path within .uctx/ (e.g., 'solutions/auth-refactor.md')",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="uctx_save_note",
            description=(
                "Write a freeform markdown note to .uctx/architecture/ (or another subdir). "
                "Use this to store implementation plans, PRDs, design decisions, or any "
                "working document that should be visible to all IDEs sharing this context store."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": _PATH_PROP,
                    "filename": {
                        "type": "string",
                        "description": "Filename (with or without .md extension)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full markdown content of the note",
                    },
                    "subdir": {
                        "type": "string",
                        "description": "Subdirectory within .uctx/ (default: 'architecture')",
                        "default": "architecture",
                    },
                },
                "required": ["filename", "content"],
            },
        ),
        Tool(
            name="uctx_save_global_learning",
            description=(
                "Record a cross-project learning, gotcha, or pattern to the global context store. "
                "This makes the knowledge available across all projects."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["bug", "pattern", "gotcha", "performance", "security"],
                    },
                    "description": {"type": "string"},
                    "context": {"type": "string", "description": "Context or example"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "category", "description"],
            },
        ),
        Tool(
            name="uctx_checkpoint",
            description=(
                "Save a checkpoint entry at a natural event boundary (after fix, after plan, etc). "
                "Automatically records git context and routes to the appropriate storage type."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": _PATH_PROP,
                    "trigger": {
                        "type": "string",
                        "enum": ["after_fix", "after_plan", "after_bug_found", "after_confirmed"],
                        "description": "What event triggered this checkpoint",
                    },
                    "entry_type": {
                        "type": "string",
                        "enum": ["solution", "learning", "task"],
                        "description": "Type of entry to save",
                    },
                    "title": {"type": "string", "description": "Title of the entry"},
                    "content": {
                        "type": "string",
                        "description": "Main content/description of the entry",
                    },
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["trigger", "entry_type", "title", "content"],
            },
        ),
    ]

    @server.list_tools()
    async def list_tools():
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        from .engine import UnifiedContextEngine

        project_path = arguments.get("project_path", "")
        root = _find_project_root(project_path)
        engine = UnifiedContextEngine(root)

        try:
            result = _dispatch(engine, name, arguments)
            return [
                TextContent(type="text", text=json.dumps(result, indent=2, default=str))
            ]
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    return server


def _dispatch(engine, name: str, args: dict) -> dict:
    """Route tool calls to engine methods."""
    from .schema import (
        ConversationSummary,
        Learning,
        Priority,
        Solution,
        Task,
        TaskStatus,
        slugify,
    )

    if name == "uctx_init":
        manifest = engine.init(
            name=args.get("name", ""),
            description=args.get("description", ""),
            tech_stack=args.get("tech_stack", []),
        )
        return {
            "status": "initialized",
            "project": manifest.name,
            "path": str(engine.uctx_dir),
        }

    elif name == "uctx_read_index":
        index_path = engine.uctx_dir / "INDEX.md"
        if not index_path.exists():
            engine.rebuild_index()

        index_content = ""
        if index_path.exists():
            index_content = index_path.read_text()
        else:
            index_content = "No context store found. Run uctx_init first."

        # Auto-inject relevant global learnings
        global_learnings = engine._get_relevant_global_learnings(limit=5)

        return {
            "index": index_content,
            "global_learnings": global_learnings if global_learnings else None,
            "note": "Global learnings auto-loaded based on your project's tech stack and tags"
        }

    elif name == "uctx_save_conversation":
        conv = ConversationSummary(
            ide=args.get("ide", "unknown"),
            model=args.get("model", ""),
            title=args["title"],
            summary=args["summary"],
            key_decisions=args.get("key_decisions", []),
            files_modified=args.get("files_modified", []),
            follow_up_tasks=args.get("follow_up_tasks", []),
            tags=args.get("tags", []),
        )
        path = engine.save_conversation(conv)
        return {"status": "saved", "file": str(path.relative_to(engine.root))}

    elif name == "uctx_list_conversations":
        return {"conversations": engine.list_conversations(limit=args.get("limit", 10))}

    elif name == "uctx_save_solution":
        git_ctx = engine._get_git_context()
        sol = Solution(
            title=args["title"],
            problem=args["problem"],
            approach=args["approach"],
            implementation=args.get("implementation", ""),
            ide_origin=args.get("ide_origin", ""),
            files_involved=args.get("files_involved", []),
            tags=args.get("tags", []),
            git_commit=git_ctx.get("commit", ""),
            git_files=git_ctx.get("files", []),
        )
        path = engine.save_solution(sol)
        return {"status": "saved", "file": str(path.relative_to(engine.root))}

    elif name == "uctx_list_solutions":
        return {"solutions": engine.list_solutions()}

    elif name == "uctx_save_task":
        task = Task(
            title=args["title"],
            status=TaskStatus(args.get("status", "pending")),
            priority=Priority(args.get("priority", "medium")),
            description=args.get("description", ""),
            acceptance_criteria=args.get("acceptance_criteria", []),
            tags=args.get("tags", []),
        )
        path = engine.save_task(task)
        return {"status": "saved", "file": str(path.relative_to(engine.root))}

    elif name == "uctx_list_tasks":
        return {"tasks": engine.list_tasks(status=args.get("status", "pending"))}

    elif name == "uctx_complete_task":
        # Accept either slug or title
        slug = args.get("slug", "")
        if not slug and args.get("title"):
            slug = slugify(args["title"])
        if not slug:
            return {"error": "Provide either 'slug' or 'title'"}
        ok = engine.complete_task(slug)
        return {"status": "completed" if ok else "not_found", "slug": slug}

    elif name == "uctx_save_learning":
        git_ctx = engine._get_git_context()
        learn = Learning(
            title=args["title"],
            category=args["category"],
            description=args["description"],
            tags=args.get("tags", []),
            git_commit=git_ctx.get("commit", ""),
            git_files=git_ctx.get("files", []),
        )
        path = engine.save_learning(learn)
        return {"status": "saved", "file": str(path.relative_to(engine.root))}

    elif name == "uctx_list_learnings":
        return {"learnings": engine.list_learnings()}

    elif name == "uctx_daily_log":
        path = engine.append_daily_log(args["entry"], ide=args.get("ide", "unknown"))
        return {"status": "logged", "file": str(path.relative_to(engine.root))}

    elif name == "uctx_get_daily_log":
        return {"log": engine.get_daily_log(date=args.get("date", ""))}

    elif name == "uctx_search":
        return {
            "results": engine.search(
                args["query"],
                max_results=args.get("max_results", 5),
                type_filter=args.get("type_filter", ""),
            )
        }

    elif name == "uctx_stats":
        return engine.stats()

    elif name == "uctx_read_file":
        fp = engine.uctx_dir / args["file_path"]
        if fp.exists():
            return {"content": fp.read_text(), "file": args["file_path"]}
        return {"error": f"File not found: {args['file_path']}"}

    elif name == "uctx_save_note":
        path = engine.save_note(
            filename=args["filename"],
            content=args["content"],
            subdir=args.get("subdir", "architecture"),
        )
        return {"status": "saved", "file": str(path.relative_to(engine.root))}

    elif name == "uctx_save_global_learning":
        from .engine import GlobalContextEngine

        git_ctx = engine._get_git_context()
        learn = Learning(
            title=args["title"],
            category=args["category"],
            description=args["description"],
            context=args.get("context", ""),
            tags=args.get("tags", []),
            git_commit=git_ctx.get("commit", ""),
            git_files=git_ctx.get("files", []),
            scope="global",
        )
        global_engine = GlobalContextEngine()
        path = global_engine.save_learning(learn)
        return {"status": "saved", "file": str(path.name), "scope": "global"}

    elif name == "uctx_checkpoint":
        return engine.checkpoint(
            trigger=args["trigger"],
            entry_type=args["entry_type"],
            title=args["title"],
            content=args["content"],
            tags=args.get("tags", []),
        )

    else:
        return {"error": f"Unknown tool: {name}"}


def main():
    """Entry point — run the MCP server in stdio mode."""
    import asyncio

    from mcp.server.stdio import stdio_server

    server = create_server()

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, None)

    asyncio.run(run())


if __name__ == "__main__":
    main()
