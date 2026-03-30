"""
Core Context Engine — read/write operations for the unified context store.

This is the single source of truth for all IDE adapters and the MCP server.
Every IDE adapter calls these functions; no adapter writes files directly.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import portalocker
import yaml

from .schema import (
    INDEX_FILE,
    MANIFEST_FILE,
    SUBDIRS,
    UCTX_DIR,
    ConversationSummary,
    Learning,
    Priority,
    ProjectManifest,
    Solution,
    Task,
    TaskStatus,
    _from_frontmatter,
    _to_frontmatter,
    slugify,
)


class UnifiedContextEngine:
    """Manages the .uctx/ store for a single project."""

    def __init__(self, project_root: str | Path):
        self.root = Path(project_root).resolve()
        self.uctx_dir = self.root / UCTX_DIR
        self.manifest_path = self.uctx_dir / MANIFEST_FILE

    def _safe_write(self, path: Path, content: str):
        """Write file with portalocker for concurrent-safe access (Windows-compatible)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with portalocker.Lock(str(path), mode="w", timeout=5) as fh:
            fh.write(content)

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------
    def init(
        self,
        name: str = "",
        description: str = "",
        tech_stack: list[str] | None = None,
        git_remote: str = "",
    ) -> ProjectManifest:
        """Initialize a .uctx/ store in the project root."""
        self.uctx_dir.mkdir(parents=True, exist_ok=True)

        for subdir in SUBDIRS:
            (self.uctx_dir / subdir).mkdir(parents=True, exist_ok=True)

        # Create .gitignore for ephemeral files only
        gitignore = self.uctx_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(
                "# Ignore lock files and local-only caches\n*.lock\n.sync-state\n"
            )

        manifest = ProjectManifest(
            name=name or self.root.name,
            description=description,
            tech_stack=tech_stack or [],
            git_remote=git_remote,
        )

        if not self.manifest_path.exists():
            self.manifest_path.write_text(
                yaml.dump(
                    {k: v for k, v in manifest.__dict__.items()},
                    default_flow_style=False,
                    sort_keys=False,
                )
            )

        self.rebuild_index()
        return manifest

    def is_initialized(self) -> bool:
        return self.manifest_path.exists()

    def get_manifest(self) -> dict:
        if not self.manifest_path.exists():
            return {}
        return yaml.safe_load(self.manifest_path.read_text()) or {}

    # ------------------------------------------------------------------
    # Conversations
    # ------------------------------------------------------------------
    def save_conversation(self, conv: ConversationSummary) -> Path:
        """Save a conversation summary to .uctx/conversations/."""
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filename = f"{date}_{conv.ide}_{conv.id}.md"
        path = self.uctx_dir / "conversations" / filename
        self._safe_write(path, _to_frontmatter(conv))
        self.rebuild_index()
        return path

    def list_conversations(self, limit: int = 20) -> list[dict]:
        conv_dir = self.uctx_dir / "conversations"
        if not conv_dir.exists():
            return []
        files = sorted(conv_dir.glob("*.md"), reverse=True)[:limit]
        results = []
        for f in files:
            data = _from_frontmatter(f.read_text())
            data["_file"] = f.name
            results.append(data)
        return results

    def get_conversation(self, filename: str) -> dict:
        path = self.uctx_dir / "conversations" / filename
        if not path.exists():
            return {}
        return _from_frontmatter(path.read_text())

    # ------------------------------------------------------------------
    # Solutions
    # ------------------------------------------------------------------
    def save_solution(self, sol: Solution) -> Path:
        filename = f"{slugify(sol.title)}.md"
        path = self.uctx_dir / "solutions" / filename
        self._safe_write(path, _to_frontmatter(sol))
        self.rebuild_index()
        return path

    def list_solutions(self) -> list[dict]:
        sol_dir = self.uctx_dir / "solutions"
        if not sol_dir.exists():
            return []
        results = []
        for f in sorted(sol_dir.glob("*.md")):
            data = _from_frontmatter(f.read_text())
            data["_file"] = f.name
            results.append(data)
        return results

    def get_solution(self, filename: str) -> dict:
        path = self.uctx_dir / "solutions" / filename
        if not path.exists():
            return {}
        return _from_frontmatter(path.read_text())

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------
    def save_task(self, task: Task) -> Path:
        subdir = "completed" if task.status == TaskStatus.COMPLETED else "pending"
        filename = f"{slugify(task.title)}.md"
        path = self.uctx_dir / "tasks" / subdir / filename
        task.updated = datetime.now(timezone.utc).isoformat()
        path.write_text(_to_frontmatter(task))

        # If completed, remove from pending
        if task.status == TaskStatus.COMPLETED:
            pending = self.uctx_dir / "tasks" / "pending" / filename
            if pending.exists():
                pending.unlink()
        self.rebuild_index()
        return path

    def list_tasks(self, status: str = "all") -> list[dict]:
        results = []
        if status in ("all", "pending", "in_progress", "blocked"):
            pending_dir = self.uctx_dir / "tasks" / "pending"
            if pending_dir.exists():
                for f in sorted(pending_dir.glob("*.md")):
                    data = _from_frontmatter(f.read_text())
                    data["_file"] = f"pending/{f.name}"
                    data["_slug"] = f.stem
                    # Filter by specific status stored in frontmatter
                    if status not in ("all", "pending") and data.get("status") != status:
                        continue
                    results.append(data)
        if status in ("all", "completed"):
            comp_dir = self.uctx_dir / "tasks" / "completed"
            if comp_dir.exists():
                for f in sorted(comp_dir.glob("*.md")):
                    data = _from_frontmatter(f.read_text())
                    data["_file"] = f"completed/{f.name}"
                    data["_slug"] = f.stem
                    results.append(data)
        return results

    def complete_task(self, slug: str) -> bool:
        pending = self.uctx_dir / "tasks" / "pending" / f"{slug}.md"
        if not pending.exists():
            return False
        text = pending.read_text()
        data = _from_frontmatter(text)
        # Reconstruct as Task with completed status
        task = Task(
            id=data.get("id", ""),
            title=data.get("title", ""),
            status=TaskStatus.COMPLETED,
            priority=Priority(data.get("priority", "medium")),
            created=data.get("created", ""),
            updated=datetime.now(timezone.utc).isoformat(),
            description=data.get("description", ""),
            acceptance_criteria=data.get("acceptance_criteria", []),
            related_solutions=data.get("related_solutions", []),
            assigned_ide=data.get("assigned_ide", ""),
            tags=data.get("tags", []),
        )
        completed = self.uctx_dir / "tasks" / "completed" / f"{slug}.md"
        completed.write_text(_to_frontmatter(task))
        pending.unlink()
        self.rebuild_index()
        return True

    # ------------------------------------------------------------------
    # Learnings
    # ------------------------------------------------------------------
    def save_learning(self, learning: Learning) -> Path:
        filename = f"{slugify(learning.title)}.md"
        path = self.uctx_dir / "learnings" / filename
        self._safe_write(path, _to_frontmatter(learning))
        self.rebuild_index()
        return path

    def list_learnings(self) -> list[dict]:
        learn_dir = self.uctx_dir / "learnings"
        if not learn_dir.exists():
            return []
        results = []
        for f in sorted(learn_dir.glob("*.md")):
            data = _from_frontmatter(f.read_text())
            data["_file"] = f.name
            results.append(data)
        return results

    # ------------------------------------------------------------------
    # Daily Log
    # ------------------------------------------------------------------
    def append_daily_log(self, entry: str, ide: str = "unknown") -> Path:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self.uctx_dir / "daily" / f"{today}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC")
        line = f"\n- **[{timestamp}] [{ide}]** {entry}\n"
        if path.exists():
            with portalocker.Lock(str(path), mode="a", timeout=5) as fh:
                fh.write(line)
        else:
            self._safe_write(path, f"# Daily Log — {today}\n{line}")
        return path

    def get_daily_log(self, date: str = "") -> str:
        if not date:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self.uctx_dir / "daily" / f"{date}.md"
        if path.exists():
            return path.read_text()
        return f"No log for {date}."

    # ------------------------------------------------------------------
    # Search (simple keyword across all markdown)
    # ------------------------------------------------------------------
    def search(self, query: str, max_results: int = 20) -> list[dict]:
        query_lower = query.lower()
        results = []
        for md_file in self.uctx_dir.rglob("*.md"):
            if md_file.name == INDEX_FILE:
                continue
            content = md_file.read_text()
            if query_lower in content.lower():
                rel = md_file.relative_to(self.uctx_dir)
                # Extract first non-empty, non-frontmatter line as preview
                lines = [
                    l
                    for l in content.split("\n")
                    if l.strip() and not l.startswith("---")
                ]
                preview = lines[0][:200] if lines else ""
                results.append(
                    {
                        "file": str(rel),
                        "preview": preview,
                    }
                )
                if len(results) >= max_results:
                    break
        return results

    # ------------------------------------------------------------------
    # Index Rebuild
    # ------------------------------------------------------------------
    def rebuild_index(self):
        """Regenerate INDEX.md — a flat routing file for LLMs to scan."""
        if not self.uctx_dir.exists():
            return

        manifest = self.get_manifest()
        lines = [
            f"# {manifest.get('name', 'Project')} — Unified Context Index",
            "",
            f"> Auto-generated by uctx. Last updated: "
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
        ]

        sections = {
            "Architecture": "architecture",
            "Solutions": "solutions",
            "Learnings": "learnings",
            "Pending Tasks": "tasks/pending",
            "Completed Tasks": "tasks/completed",
            "Recent Conversations": "conversations",
            "Daily Logs": "daily",
        }

        for heading, subdir in sections.items():
            dir_path = self.uctx_dir / subdir
            if not dir_path.exists():
                continue
            files = sorted(dir_path.glob("*.md"), reverse=True)
            if not files:
                continue
            lines.append(f"## {heading}")
            for f in files[:15]:  # cap for context window
                rel = f.relative_to(self.uctx_dir)
                # Try to extract title from frontmatter
                try:
                    data = _from_frontmatter(f.read_text())
                    title = data.get("title", f.stem.replace("-", " ").title())
                except Exception:
                    title = f.stem.replace("-", " ").title()
                lines.append(f"- [{rel}] — {title}")
            lines.append("")

        index_path = self.uctx_dir / INDEX_FILE
        self._safe_write(index_path, "\n".join(lines))

    # ------------------------------------------------------------------
    # Architecture / freeform notes
    # ------------------------------------------------------------------
    def save_note(self, filename: str, content: str, subdir: str = "architecture") -> Path:
        """Write a freeform markdown note to .uctx/<subdir>/."""
        if not filename.endswith(".md"):
            filename = f"{slugify(filename)}.md"
        path = self.uctx_dir / subdir / filename
        self._safe_write(path, content)
        self.rebuild_index()
        return path

    # ------------------------------------------------------------------
    # Pruning
    # ------------------------------------------------------------------
    def prune_old_conversations(self, days: int = 30) -> int:
        """Remove conversation summaries older than N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        conv_dir = self.uctx_dir / "conversations"
        removed = 0
        if not conv_dir.exists():
            return 0
        for f in conv_dir.glob("*.md"):
            try:
                date_str = f.name[:10]  # YYYY-MM-DD prefix
                file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
                if file_date < cutoff:
                    f.unlink()
                    removed += 1
            except (ValueError, IndexError):
                continue
        if removed:
            self.rebuild_index()
        return removed

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def stats(self) -> dict:
        """Return a summary of the context store."""

        def count_md(subdir: str) -> int:
            d = self.uctx_dir / subdir
            return len(list(d.glob("*.md"))) if d.exists() else 0

        return {
            "conversations": count_md("conversations"),
            "solutions": count_md("solutions"),
            "pending_tasks": count_md("tasks/pending"),
            "completed_tasks": count_md("tasks/completed"),
            "learnings": count_md("learnings"),
            "daily_logs": count_md("daily"),
            "total_size_kb": sum(
                f.stat().st_size for f in self.uctx_dir.rglob("*") if f.is_file()
            )
            // 1024,
        }
