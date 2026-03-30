"""
uctx CLI — Command-line interface for the Unified Context system.

Usage:
    uctx init [--name NAME] [--stack STACK]
    uctx log "message" --ide vscode
    uctx task add "title" --priority high --description "..."
    uctx task list [--status pending]
    uctx task complete <slug>
    uctx conv list
    uctx conv add --ide claude-code --title "Auth refactor" --summary "..."
    uctx solution add --title "..." --problem "..." --approach "..."
    uctx learn add --title "..." --category gotcha --description "..."
    uctx search "query"
    uctx stats
    uctx index
    uctx prune [--days 30]
    uctx setup <ide>          # Generate IDE-specific config files
    uctx today                # Show today's daily log
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .engine import UnifiedContextEngine
from .schema import (
    ConversationSummary,
    Learning,
    Priority,
    Solution,
    Task,
    TaskStatus,
)

console = Console()


def _find_project_root() -> Path:
    """Walk up from cwd to find a .uctx/ directory or git root."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".uctx").exists():
            return parent
        if (parent / ".git").exists():
            return parent
    return cwd


def _engine() -> UnifiedContextEngine:
    return UnifiedContextEngine(_find_project_root())


@click.group()
def main():
    """uctx — Unified Cross-IDE Context System"""
    pass


# ── init ──────────────────────────────────────────────────────────────
@main.command()
@click.option("--name", default="", help="Project name")
@click.option("--description", default="", help="Project description")
@click.option("--stack", default="", help="Comma-separated tech stack")
@click.option("--remote", default="", help="Git remote URL")
def init(name, description, stack, remote):
    """Initialize a .uctx/ context store in the current project."""
    engine = _engine()
    tech = [s.strip() for s in stack.split(",") if s.strip()] if stack else []
    manifest = engine.init(
        name=name, description=description, tech_stack=tech, git_remote=remote
    )
    console.print(
        Panel(
            f"[bold green]✓ Initialized .uctx/ in {engine.root}[/]\n\n"
            f"  Project: {manifest.name}\n"
            f"  Subdirs: {', '.join(['conversations', 'solutions', 'tasks', 'learnings', 'architecture', 'daily'])}",
            title="Unified Context",
        )
    )


# ── log ───────────────────────────────────────────────────────────────
@main.command()
@click.argument("message")
@click.option("--ide", default="cli", help="Source IDE identifier")
def log(message, ide):
    """Append an entry to today's daily log."""
    engine = _engine()
    path = engine.append_daily_log(message, ide=ide)
    console.print(f"[green]✓[/] Logged to {path.relative_to(engine.root)}")


# ── task ──────────────────────────────────────────────────────────────
@main.group()
def task():
    """Manage pending and completed tasks."""
    pass


@task.command("add")
@click.argument("title")
@click.option(
    "--priority",
    type=click.Choice(["low", "medium", "high", "critical"]),
    default="medium",
)
@click.option("--description", default="")
@click.option("--tags", default="")
def task_add(title, priority, description, tags):
    """Add a new pending task."""
    engine = _engine()
    t = Task(
        title=title,
        priority=Priority(priority),
        description=description,
        tags=[s.strip() for s in tags.split(",") if s.strip()] if tags else [],
    )
    path = engine.save_task(t)
    console.print(f"[green]✓[/] Task created: {path.relative_to(engine.root)}")


@task.command("list")
@click.option(
    "--status",
    default="pending",
    type=click.Choice(["all", "pending", "completed", "in_progress", "blocked"]),
)
def task_list(status):
    """List tasks by status."""
    engine = _engine()
    tasks = engine.list_tasks(status=status)
    if not tasks:
        console.print("[dim]No tasks found.[/]")
        return
    table = Table(title=f"Tasks ({status})")
    table.add_column("Title", style="bold")
    table.add_column("Priority")
    table.add_column("Status")
    table.add_column("File")
    for t in tasks:
        pcolor = {
            "critical": "red",
            "high": "yellow",
            "medium": "white",
            "low": "dim",
        }.get(t.get("priority", "medium"), "white")
        table.add_row(
            t.get("title", ""),
            f"[{pcolor}]{t.get('priority', '')}[/]",
            t.get("status", ""),
            t.get("_file", ""),
        )
    console.print(table)


@task.command("complete")
@click.argument("slug")
def task_complete(slug):
    """Mark a task as completed by its slug."""
    engine = _engine()
    if engine.complete_task(slug):
        console.print(f"[green]✓[/] Task '{slug}' marked completed.")
    else:
        console.print(f"[red]✗[/] Task '{slug}' not found in pending.")


# ── conv ──────────────────────────────────────────────────────────────
@main.group()
def conv():
    """Manage conversation summaries."""
    pass


@conv.command("list")
@click.option("--limit", default=10, help="Max results")
def conv_list(limit):
    """List recent conversation summaries."""
    engine = _engine()
    convs = engine.list_conversations(limit=limit)
    if not convs:
        console.print("[dim]No conversations recorded.[/]")
        return
    table = Table(title="Recent Conversations")
    table.add_column("Date/IDE", style="bold")
    table.add_column("Title")
    table.add_column("Tags")
    table.add_column("File")
    for c in convs:
        table.add_row(
            f"{c.get('ide', '')}",
            c.get("title", ""),
            ", ".join(c.get("tags", [])),
            c.get("_file", ""),
        )
    console.print(table)


@conv.command("add")
@click.option("--ide", required=True, help="Source IDE")
@click.option("--title", required=True, help="Conversation title")
@click.option("--summary", required=True, help="Summary text")
@click.option("--model", default="", help="Model used")
@click.option("--tags", default="")
@click.option("--files", default="", help="Comma-separated modified files")
@click.option("--decisions", default="", help="Comma-separated decisions")
def conv_add(ide, title, summary, model, tags, files, decisions):
    """Record a conversation summary."""
    engine = _engine()
    c = ConversationSummary(
        ide=ide,
        title=title,
        summary=summary,
        model=model,
        tags=[s.strip() for s in tags.split(",") if s.strip()] if tags else [],
        files_modified=[s.strip() for s in files.split(",") if s.strip()]
        if files
        else [],
        key_decisions=[s.strip() for s in decisions.split(",") if s.strip()]
        if decisions
        else [],
    )
    path = engine.save_conversation(c)
    console.print(f"[green]✓[/] Conversation saved: {path.relative_to(engine.root)}")


# ── solution ──────────────────────────────────────────────────────────
@main.group()
def solution():
    """Manage implemented solutions."""
    pass


@solution.command("add")
@click.option("--title", required=True)
@click.option("--problem", required=True)
@click.option("--approach", required=True)
@click.option("--implementation", default="")
@click.option("--ide", default="cli")
@click.option("--tags", default="")
def solution_add(title, problem, approach, implementation, ide, tags):
    """Record an implemented solution."""
    engine = _engine()
    s = Solution(
        title=title,
        problem=problem,
        approach=approach,
        implementation=implementation,
        ide_origin=ide,
        tags=[s.strip() for s in tags.split(",") if s.strip()] if tags else [],
    )
    path = engine.save_solution(s)
    console.print(f"[green]✓[/] Solution saved: {path.relative_to(engine.root)}")


@solution.command("list")
def solution_list():
    """List all recorded solutions."""
    engine = _engine()
    sols = engine.list_solutions()
    if not sols:
        console.print("[dim]No solutions recorded.[/]")
        return
    table = Table(title="Solutions")
    table.add_column("Title", style="bold")
    table.add_column("IDE")
    table.add_column("Tags")
    for s in sols:
        table.add_row(
            s.get("title", ""),
            s.get("ide_origin", ""),
            ", ".join(s.get("tags", [])),
        )
    console.print(table)


# ── learn ─────────────────────────────────────────────────────────────
@main.group()
def learn():
    """Manage learnings and gotchas."""
    pass


@learn.command("add")
@click.option("--title", required=True)
@click.option(
    "--category",
    default="gotcha",
    type=click.Choice(["bug", "pattern", "gotcha", "performance", "security"]),
)
@click.option("--description", required=True)
@click.option("--tags", default="")
def learn_add(title, category, description, tags):
    """Record a new learning."""
    engine = _engine()
    l = Learning(
        title=title,
        category=category,
        description=description,
        tags=[s.strip() for s in tags.split(",") if s.strip()] if tags else [],
    )
    path = engine.save_learning(l)
    console.print(f"[green]✓[/] Learning saved: {path.relative_to(engine.root)}")


# ── search ────────────────────────────────────────────────────────────
@main.command()
@click.argument("query")
@click.option("--limit", default=20)
def search(query, limit):
    """Search all context files for a keyword."""
    engine = _engine()
    results = engine.search(query, max_results=limit)
    if not results:
        console.print(f"[dim]No results for '{query}'.[/]")
        return
    for r in results:
        console.print(f"  [bold]{r['file']}[/]: {r['preview'][:120]}")


# ── stats ─────────────────────────────────────────────────────────────
@main.command()
def stats():
    """Show context store statistics."""
    engine = _engine()
    if not engine.is_initialized():
        console.print("[red]No .uctx/ found. Run 'uctx init' first.[/]")
        return
    s = engine.stats()
    table = Table(title="Context Store Stats")
    table.add_column("Section", style="bold")
    table.add_column("Count", justify="right")
    for key, val in s.items():
        if key != "total_size_kb":
            table.add_row(key.replace("_", " ").title(), str(val))
    table.add_row("Total Size", f"{s['total_size_kb']} KB")
    console.print(table)


# ── index ─────────────────────────────────────────────────────────────
@main.command()
def index():
    """Rebuild the INDEX.md routing file."""
    engine = _engine()
    engine.rebuild_index()
    console.print("[green]✓[/] INDEX.md rebuilt.")


# ── prune ─────────────────────────────────────────────────────────────
@main.command()
@click.option("--days", default=30, help="Remove conversations older than N days")
def prune(days):
    """Remove old conversation summaries."""
    engine = _engine()
    removed = engine.prune_old_conversations(days=days)
    console.print(f"[green]✓[/] Pruned {removed} conversations older than {days} days.")


# ── today ─────────────────────────────────────────────────────────────
@main.command()
def today():
    """Show today's daily log."""
    engine = _engine()
    log_text = engine.get_daily_log()
    console.print(Markdown(log_text))


# ── setup ─────────────────────────────────────────────────────────────
@main.command()
@click.argument(
    "ide",
    type=click.Choice(
        [
            "vscode",
            "claude-code",
            "antigravity",
            "cursor",
            "windsurf",
            "trae",
            "kiro",
            "zed",
            "all",
        ]
    ),
)
def setup(ide):
    """Generate IDE-specific integration config files."""
    from .adapters import generate_adapter_config

    engine = _engine()
    if not engine.is_initialized():
        console.print("[red]No .uctx/ found. Run 'uctx init' first.[/]")
        return
    all_ides = [
        "vscode",
        "claude-code",
        "antigravity",
        "cursor",
        "windsurf",
        "trae",
        "kiro",
        "zed",
    ]
    ides = all_ides if ide == "all" else [ide]
    for target_ide in ides:
        files_created = generate_adapter_config(engine, target_ide)
        for f in files_created:
            console.print(f"[green]✓[/] [{target_ide}] Created {f}")


if __name__ == "__main__":
    main()
