"""
Unified Context Schema — canonical data structures for cross-IDE context.

Storage layout per project:
    .uctx/
    ├── uctx.yaml              # Project manifest & config
    ├── INDEX.md               # Auto-generated routing file for LLMs
    ├── conversations/         # Session summaries (one per session)
    │   ├── 2026-03-29_vscode_abc123.md
    │   └── 2026-03-29_claude-code_def456.md
    ├── solutions/             # Implemented solutions & decisions
    │   ├── auth-refactor.md
    │   └── db-migration-v3.md
    ├── tasks/                 # Pending & completed tasks
    │   ├── pending/
    │   │   └── fix-auth-timeout.md
    │   └── completed/
    │       └── setup-ci-pipeline.md
    ├── learnings/             # Hard-won knowledge & gotchas
    │   └── tailwind-v4-migration.md
    ├── architecture/          # System design & decisions log
    │   └── decisions-log.md
    └── daily/                 # Cross-IDE daily logs
        └── 2026-03-29.md
"""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
UCTX_DIR = ".uctx"
MANIFEST_FILE = "uctx.yaml"
INDEX_FILE = "INDEX.md"

SUBDIRS = [
    "conversations",
    "solutions",
    "tasks/pending",
    "tasks/completed",
    "learnings",
    "architecture",
    "daily",
]


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class ConversationSummary:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    ide: str = ""
    model: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    title: str = ""
    summary: str = ""
    key_decisions: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    follow_up_tasks: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class Solution:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    title: str = ""
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ide_origin: str = ""
    problem: str = ""
    approach: str = ""
    implementation: str = ""
    files_involved: list[str] = field(default_factory=list)
    related_conversations: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class Task:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    title: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: Priority = Priority.MEDIUM
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated: str = ""
    description: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    related_solutions: list[str] = field(default_factory=list)
    assigned_ide: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class Learning:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    title: str = ""
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    category: str = ""  # bug, pattern, gotcha, performance, security
    description: str = ""
    context: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class ProjectManifest:
    name: str = ""
    description: str = ""
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    git_remote: str = ""
    tech_stack: list[str] = field(default_factory=list)
    active_ides: list[str] = field(default_factory=list)
    sync_mode: str = "git"  # git | file | none
    auto_index: bool = True
    max_conversation_age_days: int = 30


# ---------------------------------------------------------------------------
# Markdown serialization helpers
# ---------------------------------------------------------------------------
def _to_frontmatter(obj) -> str:
    """Serialize a dataclass to YAML frontmatter + markdown body."""
    from enum import Enum
    d = asdict(obj) if hasattr(obj, "__dataclass_fields__") else dict(obj)
    # Separate body fields from metadata
    body_fields = {
        "summary",
        "description",
        "problem",
        "approach",
        "implementation",
        "context",
    }
    meta = {k: v for k, v in d.items() if k not in body_fields}
    # Convert enum instances to plain string values so yaml.dump emits clean YAML
    meta = {k: (v.value if isinstance(v, Enum) else v) for k, v in meta.items()}
    body_parts = []
    for bf in body_fields:
        if bf in d and d[bf]:
            body_parts.append(f"## {bf.replace('_', ' ').title()}\n\n{d[bf]}")

    lines = ["---"]
    lines.append(yaml.dump(meta, default_flow_style=False, sort_keys=False).strip())
    lines.append("---")
    if body_parts:
        lines.append("")
        lines.append("\n\n".join(body_parts))
    return "\n".join(lines) + "\n"


def _from_frontmatter(text: str) -> dict:
    """Parse YAML frontmatter + markdown body from a file."""
    pattern = r"^---\s*\n(.*?)\n---\s*\n?(.*)"
    match = re.match(pattern, text, re.DOTALL)
    if not match:
        return {"_body": text}
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        # Fallback for files written with !!python/object/apply: enum tags
        meta = yaml.load(match.group(1), Loader=yaml.FullLoader) or {}  # noqa: S506
    meta["_body"] = match.group(2).strip()
    return meta


def slugify(text: str) -> str:
    """Create a filesystem-safe slug from text."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_]+", "-", slug).strip("-")[:80]
