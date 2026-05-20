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
import re
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

DEFAULT_CODEX_DOC_MAX_BYTES = 32768

IMPORT_RE = re.compile(
    r"""^\s*(?:[-*+]\s*)?@(?P<path>(?:~|/|\.{1,2}/)?[A-Za-z0-9_.\-/]+)"""
)


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


def file_size(path: Path) -> int | None:
    try:
        return path.stat().st_size if path.is_file() else None
    except OSError:
        return None


def count_files(path: Path, pattern: str) -> int:
    if not path.is_dir():
        return 0
    return sum(1 for candidate in path.rglob(pattern) if candidate.is_file())


def iter_claude_markdown_sources(repo: Path) -> Iterable[Path]:
    candidates = [
        repo / "CLAUDE.md",
        repo / "CLAUDE.local.md",
        repo / ".claude" / "CLAUDE.md",
    ]
    rules_dir = repo / ".claude" / "rules"
    if rules_dir.is_dir():
        candidates.extend(path for path in rules_dir.rglob("*.md") if path.is_file())

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen or not candidate.is_file():
            continue
        seen.add(candidate)
        yield candidate


def resolve_import(repo: Path, source: Path, import_path: str) -> Path:
    if import_path.startswith("~/"):
        return Path(import_path).expanduser()
    candidate = Path(import_path)
    if candidate.is_absolute():
        return candidate
    return (source.parent / candidate).resolve()


def import_stats(repo: Path) -> dict[str, int]:
    stats = {
        "total": 0,
        "home": 0,
        "external": 0,
        "unresolved": 0,
    }
    for source in iter_claude_markdown_sources(repo):
        try:
            lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        in_fence = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            match = IMPORT_RE.match(line)
            if not match:
                continue
            import_path = match.group("path").rstrip(".,);]")
            resolved = resolve_import(repo, source, import_path)
            stats["total"] += 1
            if import_path.startswith("~/"):
                stats["home"] += 1
            try:
                resolved.relative_to(repo)
            except ValueError:
                stats["external"] += 1
            if not resolved.exists():
                stats["unresolved"] += 1
    return stats


def read_json_file(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def settings_keys(repo: Path) -> set[str]:
    keys: set[str] = set()
    for settings_file in (repo / ".claude").glob("settings*.json"):
        data = read_json_file(settings_file)
        if not isinstance(data, dict):
            keys.add("unreadable")
            continue
        keys.update(str(key) for key in data)
        hooks = data.get("hooks")
        if isinstance(hooks, dict):
            keys.update(f"hook:{key}" for key in hooks)
        if "SessionStart" in json.dumps(data):
            keys.add("SessionStart")
    return keys


def list_signals(repo: Path, rel_path: str, destination_repo: Path | None) -> list[str]:
    signals: list[str] = []
    claude_dir = repo / ".claude"
    agents_size = file_size(repo / "AGENTS.md")
    agents_override_size = file_size(repo / "AGENTS.override.md")
    imports = import_stats(repo)
    claude_settings_keys = settings_keys(repo)

    if exists(repo / "CLAUDE.md"):
        signals.append("claude-md")
    if exists(repo / "CLAUDE.local.md"):
        signals.append("claude-local-md")
    if exists(repo / ".claude" / "CLAUDE.md"):
        signals.append("claude-project-md")
    if count_files(repo / ".claude" / "rules", "*.md"):
        signals.append("claude-rules")
    if imports["total"]:
        signals.append("claude-imports")
    if imports["home"]:
        signals.append("claude-home-imports")
    if imports["external"]:
        signals.append("claude-external-imports")
    if imports["unresolved"]:
        signals.append("claude-unresolved-imports")
    if exists(repo / "AGENTS.md"):
        signals.append("agents-md")
    if exists(repo / "AGENTS.override.md"):
        signals.append("agents-override-md")
    if (agents_size and agents_size > DEFAULT_CODEX_DOC_MAX_BYTES) or (
        agents_override_size and agents_override_size > DEFAULT_CODEX_DOC_MAX_BYTES
    ):
        signals.append("codex-doc-size-risk")
    if exists(repo / ".mcp.json"):
        signals.append("mcp-config")
    if claude_dir.is_dir():
        signals.append("claude-dir")
    if (claude_dir / "commands").is_dir():
        signals.append("claude-commands")
    if (claude_dir / "hooks").is_dir():
        signals.append("claude-hooks")
    if (claude_dir / "skills").is_dir():
        signals.append("claude-skills")
    if any(claude_dir.glob("settings*.json")):
        signals.append("claude-settings")
    if "permissions" in claude_settings_keys:
        signals.append("claude-permissions")
    if "mcpServers" in claude_settings_keys:
        signals.append("claude-settings-mcp")
    if "SessionStart" in claude_settings_keys:
        signals.append("claude-sessionstart")
    if "unreadable" in claude_settings_keys:
        signals.append("claude-settings-unreadable")

    path_parts = {part.lower() for part in Path(rel_path).parts}
    if path_parts & WEAK_EXCLUSION_NAMES:
        signals.append("weak-exclusion-name")

    if destination_repo is not None:
        if destination_repo.exists():
            signals.append("destination-present")
            if exists(destination_repo / "AGENTS.md"):
                signals.append("destination-agents-md")
            if exists(destination_repo / "AGENTS.override.md"):
                signals.append("destination-agents-override-md")
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
        "claude-skills",
        "claude-settings",
    }

    if "weak-exclusion-name" in signal_set and not (
        {"claude-md", "agents-md", "mcp-config"} & signal_set
    ):
        return "exclude-candidate"
    if "codex-doc-size-risk" in signal_set:
        return "review-size-risk"
    if {"claude-local-md", "claude-home-imports", "claude-external-imports"} & signal_set:
        return "review-private-context"
    if claude_specific & signal_set and "agents-md" not in signal_set:
        return "review-claude-specific"
    if {
        "claude-md",
        "claude-project-md",
        "claude-local-md",
        "claude-rules",
        "claude-imports",
        "agents-md",
        "agents-override-md",
        "mcp-config",
    } & signal_set:
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
        agents_size = file_size(repo / "AGENTS.md")
        agents_override_size = file_size(repo / "AGENTS.override.md")
        imports = import_stats(repo)
        claude_settings_keys = settings_keys(repo)
        rows.append(
            {
                "path": rel,
                "source": str(repo),
                "destination": str(destination_repo) if destination_repo else None,
                "has_git": True,
                "has_CLAUDE": exists(repo / "CLAUDE.md"),
                "has_claude_project_md": exists(repo / ".claude" / "CLAUDE.md"),
                "has_CLAUDE_local": exists(repo / "CLAUDE.local.md"),
                "has_AGENTS": exists(repo / "AGENTS.md"),
                "has_AGENTS_override": exists(repo / "AGENTS.override.md"),
                "has_mcp": exists(repo / ".mcp.json"),
                "has_claude_dir": (repo / ".claude").is_dir(),
                "claude_rules_count": count_files(repo / ".claude" / "rules", "*.md"),
                "claude_imports_count": imports["total"],
                "claude_home_imports_count": imports["home"],
                "claude_external_imports_count": imports["external"],
                "claude_unresolved_imports_count": imports["unresolved"],
                "claude_settings_keys": sorted(claude_settings_keys),
                "agents_size_bytes": agents_size,
                "agents_override_size_bytes": agents_override_size,
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
        "has_claude_project_md",
        "has_CLAUDE_local",
        "has_AGENTS",
        "has_AGENTS_override",
        "has_mcp",
        "has_claude_dir",
        "claude_rules_count",
        "claude_imports_count",
        "claude_unresolved_imports_count",
        "agents_size_bytes",
        "agents_override_size_bytes",
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
