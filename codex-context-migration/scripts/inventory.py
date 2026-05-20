#!/usr/bin/env python3
"""Read-only inventory helper for Codex context migration.

The script finds Git repositories under a user-provided source root and reports
common Claude/Codex context files. It intentionally emits weak review signals
instead of final migration decisions.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable


PRUNE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".playwright-mcp",
    ".next",
    ".cache",
    "build",
    "dist",
    "target",
}

WEAK_EXCLUSION_NAMES = {
    "archive",
    "archived",
    "deprecated",
    "generated",
    "sample",
    "samples",
    "scratch",
    "tmp",
    "vendor",
    "vendored",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory child Git repositories and migration context files. "
            "This command is read-only."
        )
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Source workspace or repository root to scan.",
    )
    parser.add_argument(
        "--destination",
        help="Optional destination root used to compare repo/context presence.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=5,
        help="Maximum directory depth below --source to scan for Git repos. Default: 5.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format. Default: markdown.",
    )
    return parser.parse_args()


def resolve_dir(raw_path: str, label: str, *, must_exist: bool) -> Path:
    path = Path(raw_path).expanduser().resolve()
    if must_exist and not path.exists():
        raise SystemExit(f"{label} does not exist: {path}")
    if path.exists() and not path.is_dir():
        raise SystemExit(f"{label} is not a directory: {path}")
    return path


def depth_from(base: Path, path: Path) -> int:
    rel = path.relative_to(base)
    if rel == Path("."):
        return 0
    return len(rel.parts)


def has_git_marker(path: Path) -> bool:
    return (path / ".git").exists()


def iter_git_roots(source: Path, max_depth: int) -> Iterable[Path]:
    for root, dirs, files in os.walk(source):
        root_path = Path(root)
        current_depth = depth_from(source, root_path)

        dirs[:] = sorted(
            d
            for d in dirs
            if d not in PRUNE_DIRS and current_depth < max_depth
        )

        if ".git" in dirs or ".git" in files or has_git_marker(root_path):
            yield root_path


def exists(path: Path) -> bool:
    return path.exists()


def list_signals(repo: Path, rel_path: str, destination_repo: Path | None) -> list[str]:
    signals: list[str] = []
    claude_dir = repo / ".claude"

    if exists(repo / "CLAUDE.md"):
        signals.append("claude-md")
    if exists(repo / "AGENTS.md"):
        signals.append("agents-md")
    if exists(repo / ".mcp.json"):
        signals.append("mcp-config")
    if claude_dir.is_dir():
        signals.append("claude-dir")
    if (claude_dir / "commands").is_dir():
        signals.append("claude-commands")
    if (claude_dir / "hooks").is_dir():
        signals.append("claude-hooks")
    if any(claude_dir.glob("settings*.json")):
        signals.append("claude-settings")

    path_parts = {part.lower() for part in Path(rel_path).parts}
    if path_parts & WEAK_EXCLUSION_NAMES:
        signals.append("weak-exclusion-name")

    if destination_repo is not None:
        if destination_repo.exists():
            signals.append("destination-present")
            if exists(destination_repo / "AGENTS.md"):
                signals.append("destination-agents-md")
            if exists(destination_repo / "CLAUDE.md"):
                signals.append("destination-claude-md")
        else:
            signals.append("destination-missing")

    return signals


def suggest_action(signals: list[str]) -> str:
    signal_set = set(signals)
    claude_specific = {
        "claude-commands",
        "claude-hooks",
        "claude-settings",
    }

    if "weak-exclusion-name" in signal_set and not (
        {"claude-md", "agents-md", "mcp-config"} & signal_set
    ):
        return "exclude-candidate"
    if claude_specific & signal_set and "agents-md" not in signal_set:
        return "review-claude-specific"
    if {"claude-md", "agents-md", "mcp-config"} & signal_set:
        return "include-candidate"
    if "weak-exclusion-name" in signal_set:
        return "defer-candidate"
    return "review-needed"


def inventory(source: Path, destination: Path | None, max_depth: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen: set[Path] = set()

    for repo in iter_git_roots(source, max_depth):
        if repo in seen:
            continue
        seen.add(repo)

        rel = "." if repo == source else repo.relative_to(source).as_posix()
        destination_repo = None
        if destination is not None:
            destination_repo = destination if rel == "." else destination / rel

        signals = list_signals(repo, rel, destination_repo)
        rows.append(
            {
                "path": rel,
                "source": str(repo),
                "destination": str(destination_repo) if destination_repo else None,
                "has_git": True,
                "has_CLAUDE": exists(repo / "CLAUDE.md"),
                "has_AGENTS": exists(repo / "AGENTS.md"),
                "has_mcp": exists(repo / ".mcp.json"),
                "has_claude_dir": (repo / ".claude").is_dir(),
                "signals": signals,
                "suggested_action": suggest_action(signals),
            }
        )

    return sorted(rows, key=lambda row: str(row["path"]))


def markdown_escape(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def print_markdown(rows: list[dict[str, object]]) -> None:
    headers = [
        "path",
        "has_CLAUDE",
        "has_AGENTS",
        "has_mcp",
        "has_claude_dir",
        "signals",
        "suggested_action",
    ]
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        values = []
        for header in headers:
            value = row[header]
            if isinstance(value, list):
                value = ", ".join(value)
            values.append(markdown_escape(value))
        print("| " + " | ".join(values) + " |")


def main() -> None:
    args = parse_args()
    source = resolve_dir(args.source, "--source", must_exist=True)
    destination = (
        resolve_dir(args.destination, "--destination", must_exist=False)
        if args.destination
        else None
    )

    rows = inventory(source, destination, args.max_depth)
    if args.format == "json":
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        print_markdown(rows)


if __name__ == "__main__":
    main()
