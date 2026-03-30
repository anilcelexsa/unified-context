"""
Per-IDE Adapter Configs — generates MCP integration files for each IDE/tool.

Every adapter creates the MCP config file in the IDE's native format so
the AI agent can read from and write to the shared .uctx/ context store.

MCP Config Differences (the #1 gotcha):
  ┌──────────────┬──────────────────────────────┬───────────────┐
  │ IDE          │ Config Path                  │ Root Key      │
  ├──────────────┼──────────────────────────────┼───────────────┤
  │ VS Code      │ .vscode/mcp.json             │ "servers"     │
  │ Antigravity  │ .vscode/mcp.json             │ "servers"     │
  │ Cursor       │ .cursor/mcp.json             │ "mcpServers"  │
  │ Windsurf     │ .windsurf/mcp.json           │ "mcpServers"  │
  │ Trae         │ .trae/mcp.json               │ "mcpServers"  │
  │ Kiro         │ .kiro/settings/mcp.json      │ "mcpServers"  │
  │ Zed          │ settings.json context_servers│ (unique)      │
  │ Claude Code  │ .claude/mcp.json             │ "mcpServers"  │
  └──────────────┴──────────────────────────────┴───────────────┘

Windows notes:
  - `_uctx_mcp_cmd()` resolves the full path via shutil.which at setup time,
    avoiding PATH lookup failures when the IDE launches with a minimal environment
  - Paths use os.sep but JSON configs use forward slashes per JSON convention
  - PowerShell is assumed as the default shell for hook scripts
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from textwrap import dedent

from .engine import UnifiedContextEngine

IS_WINDOWS = sys.platform == "win32"


def _uctx_mcp_cmd() -> str:
    """Return the full path to uctx-mcp, falling back to bare name if not on PATH.

    IDEs launch with a minimal environment that may not include the user's shell
    PATH. Using the full path avoids 'command not found' errors at MCP startup.
    """
    full = shutil.which("uctx-mcp")
    return full if full else "uctx-mcp"


def generate_adapter_config(engine: UnifiedContextEngine, ide: str) -> list[str]:
    """Generate IDE-specific MCP config files. Returns list of created file paths."""
    generators = {
        "vscode": _gen_vscode,
        "claude-code": _gen_claude_code,
        "antigravity": _gen_antigravity,
        "cursor": _gen_cursor,
        "windsurf": _gen_windsurf,
        "trae": _gen_trae,
        "kiro": _gen_kiro,
        "zed": _gen_zed,
    }
    gen = generators.get(ide)
    if not gen:
        return [f"[SKIP] Unknown IDE: {ide}"]
    return gen(engine)


def _project_path_posix(engine: UnifiedContextEngine) -> str:
    """Return project root as a forward-slash path (safe for JSON on all OS)."""
    return str(engine.root).replace("\\", "/")


def _session_protocol_text(ide_name: str) -> str:
    """Return the standard session protocol instructions for any IDE."""
    return dedent(f"""\
        ## Session Protocol
        1. **Session START**: Call `uctx_read_index` to load the cross-IDE context overview
        2. Check `uctx_list_tasks` for pending work items from any IDE
        3. Read today's daily log via `uctx_get_daily_log`
        4. **During work**: Log significant actions with `uctx_daily_log` (ide="{ide_name}")
        5. When solving a non-trivial problem: record it with `uctx_save_solution`
        6. When discovering a gotcha or pattern: save it with `uctx_save_learning`
        7. When identifying follow-up work: create a task with `uctx_save_task`
        8. **Session END**: Save a conversation summary with `uctx_save_conversation`

        ## Cross-IDE Awareness
        Multiple IDEs share this .uctx/ context store. Always check the daily log
        and recent conversations before making architectural decisions. If another
        IDE session recently modified the same area, coordinate carefully.
    """)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VS CODE — root key: "servers" (unique among all IDEs!)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _gen_vscode(engine: UnifiedContextEngine) -> list[str]:
    created = []
    vscode_dir = engine.root / ".vscode"
    vscode_dir.mkdir(exist_ok=True)

    # 1. MCP server configuration — VS Code uses "servers" NOT "mcpServers"
    mcp_config = {
        "servers": {
            "unified-context": {
                "type": "stdio",
                "command": _uctx_mcp_cmd(),
                "args": [],
                "env": {"UCTX_PROJECT_ROOT": _project_path_posix(engine)},
            }
        }
    }
    mcp_path = vscode_dir / "mcp.json"
    mcp_path.write_text(json.dumps(mcp_config, indent=2))
    created.append(str(mcp_path.relative_to(engine.root)))

    # 2. VS Code tasks for quick operations
    tasks_config = {
        "version": "2.0.0",
        "tasks": [
            {
                "label": "uctx: Show Today's Log",
                "type": "shell",
                "command": "uctx today",
                "group": "none",
                "presentation": {"reveal": "always", "panel": "shared"},
            },
            {
                "label": "uctx: List Pending Tasks",
                "type": "shell",
                "command": "uctx task list --status pending",
                "group": "none",
                "presentation": {"reveal": "always", "panel": "shared"},
            },
            {
                "label": "uctx: Show Stats",
                "type": "shell",
                "command": "uctx stats",
                "group": "none",
                "presentation": {"reveal": "always", "panel": "shared"},
            },
            {
                "label": "uctx: Rebuild Index",
                "type": "shell",
                "command": "uctx index",
                "group": "none",
                "presentation": {"reveal": "silent", "panel": "shared"},
            },
        ],
    }
    tasks_path = vscode_dir / "tasks.json"
    if not tasks_path.exists():
        tasks_path.write_text(json.dumps(tasks_config, indent=2))
        created.append(str(tasks_path.relative_to(engine.root)))

    # 3. Recommended settings
    settings_snippet = {
        "files.associations": {".uctx/**/*.md": "markdown"},
        "files.exclude": {
            "**/.uctx/.sync-state": True,
            "**/.uctx/*.lock": True,
        },
    }
    settings_path = vscode_dir / "settings.uctx-recommended.json"
    settings_path.write_text(json.dumps(settings_snippet, indent=2))
    created.append(str(settings_path.relative_to(engine.root)))

    return created


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLAUDE CODE — root key: "mcpServers"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _gen_claude_code(engine: UnifiedContextEngine) -> list[str]:
    created = []
    claude_dir = engine.root / ".claude"
    claude_dir.mkdir(exist_ok=True)

    # 1. MCP server config
    mcp_config = {
        "mcpServers": {
            "unified-context": {
                "type": "stdio",
                "command": _uctx_mcp_cmd(),
                "args": [],
                "env": {"UCTX_PROJECT_ROOT": _project_path_posix(engine)},
            }
        }
    }
    mcp_path = claude_dir / "mcp.json"
    mcp_path.write_text(json.dumps(mcp_config, indent=2))
    created.append(str(mcp_path.relative_to(engine.root)))

    # 2. CLAUDE.md with session protocol
    claude_md = claude_dir / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.write_text(
            dedent(f"""\
                # Unified Context — Claude Code

                This project uses **uctx** (unified-context) to share context across IDEs.
                The MCP server `unified-context` is configured in `.claude/mcp.json`.

                {_session_protocol_text("claude-code")}
            """)
        )
        created.append(str(claude_md.relative_to(engine.root)))

    return created


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ANTIGRAVITY (Google) — same config format as VS Code
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _gen_antigravity(engine: UnifiedContextEngine) -> list[str]:
    created = []
    vscode_dir = engine.root / ".vscode"
    vscode_dir.mkdir(exist_ok=True)

    mcp_config = {
        "servers": {
            "unified-context": {
                "type": "stdio",
                "command": _uctx_mcp_cmd(),
                "args": [],
                "env": {"UCTX_PROJECT_ROOT": _project_path_posix(engine)},
            }
        }
    }
    mcp_path = vscode_dir / "mcp.json"
    mcp_path.write_text(json.dumps(mcp_config, indent=2))
    created.append(str(mcp_path.relative_to(engine.root)))

    return created


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CURSOR — root key: "mcpServers", no "type" field
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _gen_cursor(engine: UnifiedContextEngine) -> list[str]:
    created = []
    cursor_dir = engine.root / ".cursor"
    cursor_dir.mkdir(exist_ok=True)

    # Cursor does NOT use a "type" field
    mcp_config = {
        "mcpServers": {
            "unified-context": {
                "command": _uctx_mcp_cmd(),
                "args": [],
                "env": {"UCTX_PROJECT_ROOT": _project_path_posix(engine)},
            }
        }
    }
    mcp_path = cursor_dir / "mcp.json"
    mcp_path.write_text(json.dumps(mcp_config, indent=2))
    created.append(str(mcp_path.relative_to(engine.root)))

    # .cursorrules with session protocol
    cursorrules = engine.root / ".cursorrules"
    if not cursorrules.exists():
        cursorrules.write_text(
            dedent(f"""\
                # Unified Context — Cursor

                This project uses **uctx** to share context across IDEs.
                The MCP server `unified-context` is configured in `.cursor/mcp.json`.

                {_session_protocol_text("cursor")}
            """)
        )
        created.append(str(cursorrules.relative_to(engine.root)))

    return created


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WINDSURF — root key: "mcpServers"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _gen_windsurf(engine: UnifiedContextEngine) -> list[str]:
    created = []
    windsurf_dir = engine.root / ".windsurf"
    windsurf_dir.mkdir(exist_ok=True)

    mcp_config = {
        "mcpServers": {
            "unified-context": {
                "type": "stdio",
                "command": _uctx_mcp_cmd(),
                "args": [],
                "env": {"UCTX_PROJECT_ROOT": _project_path_posix(engine)},
            }
        }
    }
    mcp_path = windsurf_dir / "mcp.json"
    mcp_path.write_text(json.dumps(mcp_config, indent=2))
    created.append(str(mcp_path.relative_to(engine.root)))

    # Windsurf rules file
    rules_path = windsurf_dir / "rules.md"
    if not rules_path.exists():
        rules_path.write_text(
            dedent(f"""\
                # Unified Context — Windsurf

                This project uses **uctx** to share context across IDEs.
                The MCP server `unified-context` is configured in `.windsurf/mcp.json`.

                {_session_protocol_text("windsurf")}
            """)
        )
        created.append(str(rules_path.relative_to(engine.root)))

    return created


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRAE (ByteDance) — array format under "mcpServers"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _gen_trae(engine: UnifiedContextEngine) -> list[str]:
    created = []
    trae_dir = engine.root / ".trae"
    trae_dir.mkdir(exist_ok=True)

    # Trae uses an array of server objects, not a named object map
    mcp_config = {
        "mcpServers": [
            {
                "name": "unified-context",
                "type": "stdio",
                "command": _uctx_mcp_cmd(),
                "args": [],
                "env": {"UCTX_PROJECT_ROOT": _project_path_posix(engine)},
            }
        ]
    }
    mcp_path = trae_dir / "mcp.json"
    mcp_path.write_text(json.dumps(mcp_config, indent=2))
    created.append(str(mcp_path.relative_to(engine.root)))

    return created


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KIRO (AWS) — nested path: .kiro/settings/mcp.json
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _gen_kiro(engine: UnifiedContextEngine) -> list[str]:
    created = []
    kiro_settings = engine.root / ".kiro" / "settings"
    kiro_settings.mkdir(parents=True, exist_ok=True)

    mcp_config = {
        "mcpServers": {
            "unified-context": {
                "type": "stdio",
                "command": _uctx_mcp_cmd(),
                "args": [],
                "env": {"UCTX_PROJECT_ROOT": _project_path_posix(engine)},
            }
        }
    }
    mcp_path = kiro_settings / "mcp.json"
    mcp_path.write_text(json.dumps(mcp_config, indent=2))
    created.append(str(mcp_path.relative_to(engine.root)))

    return created


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ZED — user-level settings.json, "context_servers" key, env var for root
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _gen_zed(engine: UnifiedContextEngine) -> list[str]:
    """Zed uses user-level settings — writes a snippet file, not the actual settings.json."""
    created = []

    # Zed config lives at user level, not project level.
    # We write a snippet the user can merge into ~/.config/zed/settings.json
    snippet_dir = engine.root / ".zed"
    snippet_dir.mkdir(exist_ok=True)

    # Zed context_servers format
    snippet = {
        "context_servers": {
            "unified-context": {
                "command": {
                    "path": _uctx_mcp_cmd(),
                    "args": [],
                    "env": {"UCTX_PROJECT_ROOT": _project_path_posix(engine)},
                }
            }
        }
    }
    snippet_path = snippet_dir / "settings-uctx-snippet.json"
    snippet_path.write_text(
        "// Merge this snippet into your ~/.config/zed/settings.json\n"
        + json.dumps(snippet, indent=2)
    )
    created.append(str(snippet_path.relative_to(engine.root)))

    readme = snippet_dir / "ZED-SETUP.md"
    readme.write_text(
        dedent(f"""\
            # Zed Setup for unified-context

            Zed uses user-level MCP config. Merge `.zed/settings-uctx-snippet.json`
            into `~/.config/zed/settings.json` under the `"context_servers"` key.

            Set `UCTX_PROJECT_ROOT` to `{_project_path_posix(engine)}` so Zed
            knows which project to load context from when you open this folder.

            {_session_protocol_text("zed")}
        """)
    )
    created.append(str(readme.relative_to(engine.root)))

    return created
