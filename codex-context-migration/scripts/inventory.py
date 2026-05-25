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
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal


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

CLAUDE_NATIVE_KEYWORDS = {"claude", "cc"}
CLAUDE_NATIVE_QUALIFIERS = {
    "agent",
    "agents",
    "code",
    "command",
    "commands",
    "config",
    "hook",
    "hooks",
    "mcp",
    "plugin",
    "plugins",
    "setting",
    "settings",
    "setup",
    "skill",
    "skills",
    "sync",
    "tool",
    "tools",
}

DEFAULT_CODEX_DOC_MAX_BYTES = 32768
DEFAULT_MAX_SOURCE_BYTES = 1024 * 1024
CONTEXT_ROOT_MARKERS = ("SKILL.md", "CLAUDE.md", "AGENTS.md", ".claude", ".mcp.json")

DIRECTIVE_IMPORT_RE = re.compile(
    r"""^\s*(?:[-*+]\s*)?@(?P<path>(?:~|/|\.{1,2}/)?[A-Za-z0-9_.\-/]+)"""
)
IMPORT_RE = DIRECTIVE_IMPORT_RE
INLINE_REF_RE = re.compile(r"""(?:^|\s)@(?P<path>[A-Za-z0-9_.\-/]+)""")
PLUGIN_REF_RE = re.compile(r"(?P<name>[a-z0-9][a-z0-9-]*)@(?P<source>[a-z0-9][a-z0-9-]*)")
ALLOWED_PLUGIN_REF_SOURCES = {
    "claude-plugins-official",
    "openai-curated",
    "openai-bundled",
    "openai-primary-runtime",
    "openai-codex",
    "sendbird",
    "codex-mcp",
}
JSON_PLUGIN_CONTEXT_KEYS = (
    "plugins",
    "enabledplugins",
    "disabledplugins",
    "marketplace",
    "marketplaces",
    "source",
    "provider",
)
PLUGIN_MAPPINGS_PATH = Path(__file__).resolve().parents[1] / "references" / "plugin-mappings.json"
CODEX_RUNTIME_MCP_NAMES = {"node_repl"}


@dataclass(frozen=True)
class ResolvedImport:
    path: Path
    kind: Literal["repo", "home", "absolute", "external"]
    safe_to_stat: bool


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
    parser.add_argument(
        "--codex-home",
        default="~/.codex",
        help="Codex home used for read-only plugin marketplace/cache discovery. Default: ~/.codex.",
    )
    parser.add_argument(
        "--include-artifacts",
        action="store_true",
        help="Also inventory Codex/Claude plugin, skill, command, hook, agent, and marketplace artifacts.",
    )
    parser.add_argument(
        "--artifact-output",
        choices=("summary", "detail"),
        help="Artifact markdown output mode. Default: summary for markdown, detail for JSON.",
    )
    parser.add_argument(
        "--audit-detail",
        action="store_true",
        help="Include per-import audit detail in JSON rows.",
    )
    parser.add_argument(
        "--max-source-bytes",
        type=int,
        default=DEFAULT_MAX_SOURCE_BYTES,
        help="Maximum markdown source size to parse for import/plugin signals. Default: 1048576.",
    )
    parser.add_argument(
        "--guided-auto-plan",
        action="store_true",
        help="Emit a conservative guided-auto migration plan draft from inventory signals.",
    )
    parser.add_argument(
        "--emit-manifest",
        action="store_true",
        help="Emit a draft migration manifest that binds inventory classifications to copy decisions.",
    )
    parser.add_argument(
        "--operation-mode",
        choices=("setup-in-place", "migrate-full-workspace", "context-only"),
        help="Operation mode to record in the emitted manifest. Defaults from destination presence.",
    )
    parser.add_argument(
        "--target-posture",
        choices=("codex-native", "dual-run-current-workspace"),
        help="Target posture to record in the emitted manifest. Defaults from destination presence.",
    )
    parser.add_argument(
        "--include-global-claude-runtime",
        action="store_true",
        help="Also classify global ~/.claude runtime settings, commands, plugins, and skills.",
    )
    parser.add_argument(
        "--include-mcp-audit",
        action="store_true",
        help="Also classify source MCP configs and target Codex MCP baseline as capability decisions.",
    )
    parser.add_argument(
        "--claude-home",
        default="~/.claude",
        help="Claude home used for global runtime classification. Default: ~/.claude.",
    )
    parser.add_argument(
        "--forbidden-scan-root",
        help="Destination root to scan for codex-native forbidden paths after copy.",
    )
    parser.add_argument(
        "--artifact-scope",
        choices=("active", "all"),
        default="active",
        help="Artifact scan scope. active scans installed/cache roots; all also scans marketplace staging/data. Default: active.",
    )
    parser.add_argument(
        "--artifact-root",
        action="append",
        default=[],
        help="Additional artifact root to scan. May be passed more than once.",
    )
    return parser.parse_args()


def resolve_dir(raw_path: str, label: str, *, must_exist: bool) -> Path:
    try:
        path = Path(raw_path).expanduser().resolve()
    except RuntimeError as exc:
        raise SystemExit(f"{label} cannot be resolved safely: {raw_path}") from exc
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


def git_marker_kind(path: Path) -> str:
    marker = path / ".git"
    if marker.is_dir():
        return "dir"
    if marker.is_file():
        try:
            text = marker.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        if "modules" in text:
            return "file-submodule"
        return "file-worktree"
    return "none"


def git_output(repo: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return completed.stdout.strip()


def git_remote_freshness(repo: Path) -> dict[str, object]:
    """Fetch and summarize whether a repo is stale relative to its upstream."""
    remotes = git_output(repo, "remote")
    if not remotes:
        return {
            "has_remote": False,
            "branch": git_output(repo, "branch", "--show-current"),
            "upstream": "",
            "head": git_output(repo, "rev-parse", "HEAD"),
            "upstream_head": "",
            "ahead": 0,
            "behind": 0,
            "decision_required": False,
            "signals": ["remote-not-configured"],
        }

    subprocess.run(
        ["git", "fetch", "--quiet"],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    branch = git_output(repo, "branch", "--show-current")
    upstream = git_output(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if not upstream:
        upstream = f"origin/{branch}" if branch else ""
    head = git_output(repo, "rev-parse", "HEAD")
    upstream_head = git_output(repo, "rev-parse", upstream) if upstream else ""
    ahead = 0
    behind = 0
    if upstream_head:
        counts = git_output(repo, "rev-list", "--left-right", "--count", f"HEAD...{upstream}")
        parts = counts.split()
        if len(parts) == 2 and all(part.isdigit() for part in parts):
            ahead = int(parts[0])
            behind = int(parts[1])

    signals: list[str] = []
    if behind:
        signals.append("remote-behind")
    if ahead:
        signals.append("remote-ahead")
    if not signals:
        signals.append("remote-current")
    return {
        "has_remote": True,
        "branch": branch,
        "upstream": upstream,
        "head": head,
        "upstream_head": upstream_head,
        "ahead": ahead,
        "behind": behind,
        "decision_required": bool(behind),
        "signals": signals,
    }


def count_git_markers(path: Path) -> int:
    if has_git_marker(path):
        return 1
    if not path.is_dir():
        return 0
    total = 0
    for root, dirs, _files in os.walk(path, followlinks=False):
        root_path = Path(root)
        if has_git_marker(root_path):
            total += 1
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in PRUNE_DIRS]
    return total


def iter_git_roots(source: Path, max_depth: int) -> Iterable[Path]:
    for root, dirs, files in os.walk(source, followlinks=False):
        root_path = Path(root)
        current_depth = depth_from(source, root_path)

        dirs[:] = sorted(
            d
            for d in dirs
            if d not in PRUNE_DIRS and current_depth < max_depth
        )

        if has_git_marker(root_path):
            yield root_path


def depth_limit_skipped_git_count(source: Path, max_depth: int) -> int:
    skipped = 0
    for root, dirs, _files in os.walk(source, followlinks=False):
        root_path = Path(root)
        current_depth = depth_from(source, root_path)
        dirs[:] = sorted(d for d in dirs if d not in PRUNE_DIRS)
        if current_depth >= max_depth:
            for dirname in dirs:
                skipped += count_git_markers(root_path / dirname)
            dirs[:] = []
    return skipped


def depth_limit_pruned_dir_count(source: Path, max_depth: int) -> int:
    pruned = 0
    for root, dirs, _files in os.walk(source, followlinks=False):
        root_path = Path(root)
        current_depth = depth_from(source, root_path)
        dirs[:] = sorted(d for d in dirs if d not in PRUNE_DIRS)
        if current_depth >= max_depth:
            pruned += len(dirs)
            dirs[:] = []
    return pruned


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


def resolve_import(repo: Path, source: Path, import_path: str) -> ResolvedImport:
    if import_path.startswith("~/"):
        return ResolvedImport(Path(import_path).expanduser(), "home", safe_to_stat=False)
    candidate = Path(import_path)
    if candidate.is_absolute():
        return ResolvedImport(candidate, "absolute", safe_to_stat=False)
    try:
        repo_root = repo.resolve()
        source_dir = source.parent.resolve()
    except RuntimeError:
        return ResolvedImport(source.parent / candidate, "external", safe_to_stat=False)
    normalized = Path(os.path.normpath(source_dir / candidate))
    try:
        relative = normalized.relative_to(repo_root)
    except ValueError:
        return ResolvedImport(normalized, "external", safe_to_stat=False)

    current = repo_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return ResolvedImport(normalized, "external", safe_to_stat=False)
    return ResolvedImport(normalized, "repo", safe_to_stat=True)


def import_stats(
    repo: Path,
    audit_detail: bool = False,
    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
) -> dict[str, object]:
    total = 0
    inline_refs = 0
    home = 0
    external = 0
    unsafe_external = 0
    unresolved = 0
    unreadable_paths: list[str] = []
    skipped_oversized_paths: list[str] = []
    import_details: list[dict[str, object]] = []
    for source in iter_claude_markdown_sources(repo):
        try:
            source_size = source.stat().st_size
        except OSError:
            unreadable_paths.append(str(source))
            continue
        if source_size > max_source_bytes:
            skipped_oversized_paths.append(str(source))
            continue
        try:
            lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            unreadable_paths.append(str(source))
            continue
        in_fence = False
        fence_marker = ""
        for line in lines:
            stripped = line.strip()
            fence_match = re.match(r"^\s*(```+|~~~+)", line)
            if fence_match:
                marker = fence_match.group(1)
                if not in_fence:
                    in_fence = True
                    fence_marker = marker[:3]
                    remainder = line[fence_match.end() :]
                    if fence_marker in remainder:
                        in_fence = False
                        fence_marker = ""
                elif marker.startswith(fence_marker):
                    in_fence = False
                    fence_marker = ""
                continue
            if in_fence:
                continue
            match = DIRECTIVE_IMPORT_RE.match(line)
            if not match:
                if INLINE_REF_RE.search(line):
                    inline_refs += 1
                continue
            import_path = match.group("path").rstrip(".,);]")
            resolved = resolve_import(repo, source, import_path)
            total += 1
            if import_path.startswith("~/"):
                home += 1
            if resolved.kind in {"absolute", "external"}:
                unsafe_external += 1
            if resolved.kind == "external":
                external += 1
            resolved_exists = resolved.path.exists() if resolved.safe_to_stat else None
            if resolved.safe_to_stat and not resolved_exists:
                unresolved += 1
            if audit_detail:
                if resolved.safe_to_stat:
                    detail_exists = resolved_exists
                elif resolved.kind == "home":
                    detail_exists = False
                else:
                    detail_exists = None
                import_details.append(
                    {
                        "source_file": source.relative_to(repo).as_posix(),
                        "raw": stripped,
                        "resolved": str(resolved.path),
                        "kind": resolved.kind,
                        "exists": detail_exists,
                    }
                )
    stats = {
        "total": total,
        "inline_refs": inline_refs,
        "home": home,
        "external": external,
        "unsafe_external": unsafe_external,
        "unresolved": unresolved,
        "unreadable": len(unreadable_paths),
        "skipped_oversized_count": len(skipped_oversized_paths),
        "unreadable_paths": unreadable_paths,
        "skipped_oversized_paths": skipped_oversized_paths,
    }
    if audit_detail:
        stats["imports"] = import_details
    return stats


def read_json_file(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def read_toml_file(path: Path) -> object | None:
    try:
        with path.open("rb") as file:
            return tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError):
        return None


def load_plugin_mappings(path: Path = PLUGIN_MAPPINGS_PATH) -> dict[str, list[dict[str, str]]]:
    data = read_json_file(path)
    if not isinstance(data, dict):
        return {}
    mappings: dict[str, list[dict[str, str]]] = {}
    for ref, entries in data.items():
        if ref == "_schema" or not isinstance(ref, str) or not isinstance(entries, list):
            continue
        normalized_entries: list[dict[str, str]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            normalized_entries.append(
                {
                    "candidate": str(entry.get("candidate") or ""),
                    "confidence": str(entry.get("confidence") or "unknown"),
                    "note": str(entry.get("note") or ""),
                }
            )
        if normalized_entries:
            mappings[ref] = normalized_entries
    return mappings


def settings_keys(repo: Path) -> set[str]:
    keys: set[str] = set()
    for settings_file in iter_claude_settings_sources(repo):
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


def repo_name_looks_claude_native(repo: Path) -> bool:
    tokens = name_tokens(repo.name)
    return "claude" in tokens or (
        bool(tokens & CLAUDE_NATIVE_KEYWORDS) and bool(tokens & CLAUDE_NATIVE_QUALIFIERS)
    )


def iter_claude_settings_sources(repo: Path) -> Iterable[Path]:
    yield from (repo / ".claude").glob("settings*.json")

    if not repo_name_looks_claude_native(repo):
        return

    for candidate in sorted(repo.glob("settings*.json")):
        if candidate.is_file():
            yield candidate
    home_dir = repo / "home"
    if home_dir.is_dir():
        for candidate in sorted(home_dir.glob("settings*.json")):
            if candidate.is_file():
                yield candidate


def is_plugin_json_context_key(key: str) -> bool:
    normalized = key.lower()
    return any(token in normalized for token in JSON_PLUGIN_CONTEXT_KEYS)


def collect_plugin_refs_from_json(value: object, in_plugin_context: bool = False) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            key_in_plugin_context = in_plugin_context or (
                isinstance(key, str) and is_plugin_json_context_key(key)
            )
            if key_in_plugin_context and isinstance(key, str):
                refs.update(plugin_refs_from_text(key))
            refs.update(collect_plugin_refs_from_json(item, key_in_plugin_context))
    elif isinstance(value, list):
        for item in value:
            refs.update(collect_plugin_refs_from_json(item, in_plugin_context))
    elif in_plugin_context and isinstance(value, str):
        refs.update(plugin_refs_from_text(value))
    return refs


def plugin_refs_from_text(text: str) -> set[str]:
    refs: set[str] = set()
    for match in PLUGIN_REF_RE.finditer(text):
        name = match.group("name")
        source = match.group("source")
        if source not in ALLOWED_PLUGIN_REF_SOURCES:
            continue
        refs.add(f"{name}@{source}")
    return refs


def detected_plugin_refs(
    repo: Path,
    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
) -> list[str]:
    refs: set[str] = set()

    for settings_file in iter_claude_settings_sources(repo):
        data = read_json_file(settings_file)
        if data is not None:
            refs.update(collect_plugin_refs_from_json(data))

    for source in iter_claude_markdown_sources(repo):
        try:
            if source.stat().st_size > max_source_bytes:
                continue
            refs.update(plugin_refs_from_text(source.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue

    return sorted(refs)


def split_plugin_ref(ref: str) -> tuple[str, str]:
    if "@" not in ref:
        return ref, ""
    name, source = ref.rsplit("@", 1)
    return name, source


def discover_codex_plugins(codex_home: Path) -> dict[str, list[str]]:
    available: dict[str, set[str]] = {}

    def add(name: str, source: str) -> None:
        if not name:
            return
        available.setdefault(name, set()).add(source)

    marketplace = codex_home / ".tmp" / "plugins" / ".agents" / "plugins" / "marketplace.json"
    data = read_json_file(marketplace)
    if isinstance(data, dict):
        marketplace_name = str(data.get("name") or "openai-curated")
        for plugin in data.get("plugins", []):
            if isinstance(plugin, dict):
                add(str(plugin.get("name") or ""), marketplace_name)

    cache_root = codex_home / "plugins" / "cache"
    if cache_root.is_dir():
        for family in sorted(path for path in cache_root.iterdir() if path.is_dir()):
            for plugin_dir in sorted(path for path in family.iterdir() if path.is_dir()):
                add(plugin_dir.name, family.name)

    return {name: sorted(sources) for name, sources in sorted(available.items())}


def artifact_roots(codex_home: Path, scope: str, extra_roots: Iterable[str]) -> list[Path]:
    roots = [
        codex_home / "plugins" / "cache",
        codex_home / "skills",
        codex_home / "vendor_imports" / "skills",
        Path("~/.claude/plugins/cache").expanduser(),
        Path("~/.claude/commands").expanduser(),
        Path("~/.claude/skills").expanduser(),
        Path("~/.claude/agents").expanduser(),
        Path("~/.claude/hooks").expanduser(),
    ]
    if scope == "all":
        roots.extend(
            [
                codex_home / ".tmp" / "plugins",
                codex_home / ".tmp" / "marketplaces",
                Path("~/.claude/plugins/marketplaces").expanduser(),
                Path("~/.claude/plugins/data").expanduser(),
            ]
        )
    roots.extend(Path(raw).expanduser() for raw in extra_roots)

    seen: set[Path] = set()
    existing: list[Path] = []
    for root in roots:
        resolved = root.resolve()
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        if resolved.is_dir():
            existing.append(resolved)
    return existing


def provider_from_path(path: Path) -> str:
    parts = path.parts
    for marker in ("cache", "marketplaces"):
        if marker in parts:
            index = parts.index(marker)
            if index + 1 < len(parts):
                return parts[index + 1]
    known = {
        "openai-bundled",
        "openai-codex",
        "openai-curated",
        "openai-primary-runtime",
        "claude-plugins-official",
        "sendbird",
    }
    for part in parts:
        if part in known:
            return part
    return ""


def version_from_path(path: Path, name: str) -> str:
    parts = list(path.parts)
    if name in parts:
        index = parts.index(name)
        if index + 1 < len(parts):
            return parts[index + 1]
    return ""


def source_class_from_path(path: Path) -> str:
    parts = path.parts
    if "vendor_imports" in parts or "vendored" in parts:
        return "vendor"
    if "cache" in parts:
        return "cache"
    if "skills" in parts:
        index = len(parts) - 1 - list(reversed(parts)).index("skills")
        if index + 1 < len(parts):
            if parts[index + 1] == ".system":
                return "system"
            return "user"
    return "unknown"


def ecosystem_from_signals(signals: Iterable[str], provider: str) -> str:
    signal_set = set(signals)
    if "has-codex-manifest" in signal_set and "has-claude-manifest" in signal_set:
        return "mixed"
    if provider.startswith("openai-") or "has-codex-manifest" in signal_set:
        return "codex"
    if provider.startswith("claude-") or "has-claude-manifest" in signal_set:
        return "claude"
    return "unknown"


def agents_md_appears_generated(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[:200]
    except OSError:
        return False
    joined = "\n".join(lines).lower()
    if any(marker in joined for marker in ("generated by", "do not edit", "auto-generated", "<!-- generated")):
        return True
    heading_run = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            heading_run += 1
            if heading_run >= 3:
                return True
        elif stripped:
            heading_run = 0
    return False


def artifact_row(
    artifact_type: str,
    name: str,
    source_path: Path,
    manifest_path: Path | None,
    signals: list[str],
    scanned_manifest_type: str = "",
) -> dict[str, object]:
    provider = provider_from_path(source_path)
    effective_ecosystem = ecosystem_from_signals(signals, provider)
    return {
        "artifact_type": artifact_type,
        "ecosystem": effective_ecosystem,
        "scanned_manifest_type": scanned_manifest_type,
        "effective_ecosystem": effective_ecosystem,
        "source_class": source_class_from_path(source_path),
        "provider": provider,
        "name": name,
        "version": version_from_path(source_path, name) or "unknown",
        "source_path": str(source_path),
        "manifest_path": str(manifest_path) if manifest_path else "",
        "signals": sorted(set(signals)),
    }


def manifest_name(manifest_path: Path) -> str:
    data = read_json_file(manifest_path)
    if isinstance(data, dict) and data.get("name"):
        return str(data["name"])
    return manifest_path.parent.parent.name


def inventory_artifacts(roots: list[Path]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()

    for root in roots:
        for manifest in sorted(root.rglob("plugin.json")):
            if ".git" in manifest.parts:
                continue
            marker = manifest.parent.name
            if marker not in {".codex-plugin", ".claude-plugin"}:
                continue
            plugin_root = manifest.parent.parent
            signals = [
                "has-codex-manifest" if marker == ".codex-plugin" else "has-claude-manifest"
            ]
            if (plugin_root / ".codex-plugin" / "plugin.json").is_file() and marker != ".codex-plugin":
                signals.append("has-codex-manifest")
            if (plugin_root / ".claude-plugin" / "plugin.json").is_file() and marker != ".claude-plugin":
                signals.append("has-claude-manifest")
            if any(plugin_root.glob("skills/*/SKILL.md")) or any(
                plugin_root.glob(".claude/skills/*/SKILL.md")
            ):
                signals.append("has-skills")
            if (plugin_root / "commands").is_dir() or (plugin_root / ".claude" / "commands").is_dir():
                signals.append("has-commands")
            if (plugin_root / "hooks").is_dir() or (plugin_root / ".claude" / "hooks").is_dir():
                signals.append("has-hooks")
            if (plugin_root / "agents").is_dir() or (plugin_root / ".claude" / "agents").is_dir():
                signals.append("has-agents")

            key = ("plugin", str(plugin_root))
            if key in seen:
                continue
            seen.add(key)
            scanned_manifest_type = "codex-plugin" if marker == ".codex-plugin" else "claude-plugin"
            if "has-codex-manifest" in signals and "has-claude-manifest" in signals:
                signals.append("mixed-plugin-manifests")
            rows.append(
                artifact_row(
                    "plugin",
                    manifest_name(manifest),
                    plugin_root,
                    manifest,
                    signals,
                    scanned_manifest_type,
                )
            )

        for marketplace in sorted(root.rglob("marketplace.json")):
            if ".git" in marketplace.parts:
                continue
            signals = ["marketplace-only"]
            if ".codex-plugin" in marketplace.parts or ".agents" in marketplace.parts:
                signals.append("has-codex-marketplace")
            if ".claude-plugin" in marketplace.parts:
                signals.append("has-claude-marketplace")
            data = read_json_file(marketplace)
            name = ""
            if isinstance(data, dict):
                name = str(data.get("name") or data.get("displayName") or marketplace.parent.name)
            else:
                name = marketplace.parent.name
                signals.append("unreadable")
            key = ("marketplace", str(marketplace))
            if key in seen:
                continue
            seen.add(key)
            rows.append(artifact_row("marketplace", name, marketplace.parent, marketplace, signals))

        for skill in sorted(root.rglob("SKILL.md")):
            if ".git" in skill.parts:
                continue
            skill_root = skill.parent
            signals = ["skill-md"]
            if ".claude" in skill.parts:
                signals.append("claude-embedded-skill")
            if (skill_root.parent.parent / ".codex-plugin" / "plugin.json").is_file():
                signals.append("has-codex-manifest")
            if (skill_root.parent.parent / ".claude-plugin" / "plugin.json").is_file():
                signals.append("has-claude-manifest")
            key = ("skill", str(skill_root))
            if key in seen:
                continue
            seen.add(key)
            rows.append(artifact_row("skill", skill_root.name, skill_root, skill, signals))

        for artifact_type, pattern in (
            ("command", "*.md"),
            ("agent", "*.md"),
            ("hook", "*"),
        ):
            if root.name != artifact_type + "s":
                continue
            for path in sorted(root.glob(pattern)):
                if not path.is_file():
                    continue
                signals = [f"{artifact_type}-file"]
                if artifact_type == "hook" and os.access(path, os.X_OK):
                    signals.append("executable")
                key = (artifact_type, str(path))
                if key in seen:
                    continue
                seen.add(key)
                rows.append(artifact_row(artifact_type, path.stem, path.parent, path, signals))

    return sorted(
        rows,
        key=lambda row: (
            str(row["artifact_type"]),
            str(row["ecosystem"]),
            str(row["provider"]),
            str(row["name"]),
            str(row["source_path"]),
        ),
    )


def candidate_status(candidate_ref: str, available_plugins: dict[str, list[str]]) -> str:
    if not candidate_ref:
        return "not-applicable"
    name, source = split_plugin_ref(candidate_ref)
    if source == "codex-mcp":
        return "manual-review"
    sources = available_plugins.get(name, [])
    if not sources:
        return "not-found"
    if source in sources:
        return "available"
    return "available-via-other-source"


def plugin_candidates(
    refs: Iterable[str],
    available_plugins: dict[str, list[str]],
    plugin_mappings: dict[str, list[dict[str, str]]] | None = None,
) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    mappings_by_ref = plugin_mappings if plugin_mappings is not None else load_plugin_mappings()
    for ref in sorted(refs):
        mappings = mappings_by_ref.get(ref)
        if not mappings and ref.endswith("@claude-plugins-official"):
            mappings = [
                {
                    "candidate": "",
                    "confidence": "unknown",
                    "note": "Claude official plugin detected; check Codex official/curated alternatives before retaining.",
                }
            ]
        if not mappings:
            continue
        for mapping in mappings:
            candidate = str(mapping.get("candidate") or "")
            candidates.append(
                {
                    "source": ref,
                    "candidate": candidate,
                    "candidate_status": candidate_status(candidate, available_plugins),
                    "confidence": mapping.get("confidence", "unknown"),
                    "decision_required": True,
                    "note": mapping.get("note", ""),
                }
            )
    return candidates


def plugin_decision_flags(
    refs: Iterable[str], candidates: list[dict[str, object]]
) -> list[str]:
    flags: set[str] = set()
    for ref in refs:
        if ref.endswith("@claude-plugins-official"):
            flags.add("claude-plugin-retained-requires-user-confirmation")
        if ref == "cc@sendbird":
            flags.add("third-party-exception-requires-reason")
    for candidate in candidates:
        if candidate.get("candidate_status") in {"not-found", "manual-review", "not-applicable"}:
            flags.add("manual-plugin-review-required")
        elif candidate.get("candidate_status") == "available":
            flags.add("codex-native-candidate-available")
    return sorted(flags)


def plugin_migration_decisions(candidates: list[dict[str, object]]) -> list[dict[str, str]]:
    decisions: list[dict[str, str]] = []
    for candidate in candidates:
        source = str(candidate.get("source") or "")
        target = str(candidate.get("candidate") or "")
        status = str(candidate.get("candidate_status") or "")
        if status == "available":
            decision = "already-present"
            reason = "Codex candidate is available"
        elif status in {"not-found", "manual-review", "not-applicable"}:
            decision = "defer"
            reason = "Codex candidate needs manual review"
        else:
            decision = "defer"
            reason = f"candidate status is {status or 'unknown'}"
        decisions.append(
            {
                "source": source,
                "candidate": target,
                "decision": decision,
                "reason": reason,
            }
        )
    return decisions


def global_claude_runtime_snapshot(claude_home: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not claude_home.exists():
        return rows

    for name in ("settings.json", "settings.local.json"):
        path = claude_home / name
        if not path.is_file():
            continue
        data = read_json_file(path)
        signals: list[str] = []
        if isinstance(data, dict):
            if "hooks" in data:
                signals.append("hooks")
            if "permissions" in data:
                signals.append("permissions")
            if "env" in data:
                signals.append("env")
            if "enabledPlugins" in data:
                signals.append("enabled-plugins")
            if "statusLine" in data:
                signals.append("status-line")
        else:
            signals.append("unreadable")
        rows.append(
            {
                "path": name,
                "kind": "runtime-config",
                "decision": "defer",
                "reason": "global Claude runtime config requires Codex-specific design",
                "signals": signals,
            }
        )

    commands = claude_home / "commands"
    if commands.is_dir():
        for path in sorted(commands.glob("*.md")):
            rows.append(
                {
                    "path": f"commands/{path.name}",
                    "kind": "claude-command",
                    "decision": "defer",
                    "reason": "Claude slash command requires Codex-native redesign",
                    "signals": ["command-file"],
                }
            )

    plugins = claude_home / "plugins"
    if plugins.is_dir():
        for path in sorted(plugins.glob("*.json")):
            rows.append(
                {
                    "path": f"plugins/{path.name}",
                    "kind": "plugin-runtime-state",
                    "decision": "defer",
                    "reason": "plugin runtime registry/config must not be copied as workspace source",
                    "signals": ["plugin-runtime-json"],
                }
            )

    skills = claude_home / "skills"
    if skills.is_dir():
        for path in sorted(skills.glob("*/SKILL.md")):
            rows.append(
                {
                    "path": f"skills/{path.parent.name}/SKILL.md",
                    "kind": "skill-source",
                    "decision": "defer",
                    "reason": "loose Claude skill requires portability review",
                    "signals": ["skill-md"],
                }
            )

    return rows


def mcp_transport(config: dict[str, object]) -> str:
    if config.get("url"):
        return "remote-url"
    if config.get("command"):
        return "stdio-command"
    return "unknown"


def mcp_risk_signals(name: str, config: dict[str, object]) -> list[str]:
    signals: list[str] = []
    lower_name = name.lower()
    url = str(config.get("url") or "")
    command = str(config.get("command") or "")
    if name in CODEX_RUNTIME_MCP_NAMES or "node_repl" in command:
        return ["codex-runtime"]
    if url:
        signals.append("remote-access")
    if isinstance(config.get("env"), dict) and config.get("env"):
        signals.append("credentials")
    if any(token in lower_name for token in ("prod", "write", "admin")):
        signals.append("write-or-production-risk")
    if any(token in url.lower() for token in ("prod", "admin", "write")):
        signals.append("write-or-production-risk")
    return sorted(set(signals))


def mcp_row(
    *,
    name: str,
    origin: str,
    source_path: Path,
    config: dict[str, object],
) -> dict[str, object]:
    return {
        "name": name,
        "origin": origin,
        "managed_by": "codex-mcp" if origin == "target" else "source-config",
        "source_path": str(source_path),
        "transport": mcp_transport(config),
        "command": str(config.get("command") or ""),
        "url": str(config.get("url") or ""),
        "risk_signals": mcp_risk_signals(name, config),
    }


def source_mcp_capabilities(source: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(source.rglob(".mcp.json")):
        if ".git" in path.parts:
            continue
        data = read_json_file(path)
        if not isinstance(data, dict):
            rows.append(
                {
                    "name": path.name,
                    "origin": "source",
                    "source_path": str(path),
                    "transport": "unknown",
                    "command": "",
                    "url": "",
                    "risk_signals": ["unreadable"],
                }
            )
            continue
        servers = data.get("mcpServers") or data.get("servers") or {}
        if not isinstance(servers, dict):
            continue
        for name, config in sorted(servers.items()):
            if not isinstance(name, str) or not isinstance(config, dict):
                continue
            rows.append(
                mcp_row(name=name, origin="source", source_path=path, config=config)
            )
    return rows


def target_mcp_baseline(codex_home: Path) -> list[dict[str, object]]:
    config_path = codex_home / "config.toml"
    data = read_toml_file(config_path)
    if not isinstance(data, dict):
        return []
    servers = data.get("mcp_servers") or {}
    if not isinstance(servers, dict):
        return []
    rows: list[dict[str, object]] = []
    for name, config in sorted(servers.items()):
        if not isinstance(name, str) or not isinstance(config, dict):
            continue
        rows.append(
            mcp_row(name=name, origin="target", source_path=config_path, config=config)
        )
    return rows


def mcp_decision(row: dict[str, object], target_names: set[str]) -> tuple[str, str]:
    name = str(row.get("name") or "")
    origin = str(row.get("origin") or "")
    risk_signals = set(row.get("risk_signals") or [])
    transport = str(row.get("transport") or "")
    if name in CODEX_RUNTIME_MCP_NAMES or "codex-runtime" in risk_signals:
        return "already-present", "Codex target runtime baseline"
    if origin == "target" and transport == "remote-url":
        return "defer", "remote MCP requires auth and data-scope review before keeping"
    if origin == "target":
        return "already-present", "Codex-managed MCP registration already present"
    if "credentials" in risk_signals or "write-or-production-risk" in risk_signals:
        return "defer", "MCP uses credentials or remote access requiring review"
    if origin == "source" and name in target_names:
        return "already-present", "Target already has an MCP with the same capability name"
    if transport == "remote-url":
        return "defer", "remote MCP requires auth and data-scope review"
    return "manual-review", "MCP capability requires explicit target decision"


def mcp_capability_decisions(
    source_rows: list[dict[str, object]],
    target_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    target_names = {str(row.get("name") or "") for row in target_rows}
    decisions: list[dict[str, object]] = []
    for row in [*target_rows, *source_rows]:
        decision, reason = mcp_decision(row, target_names)
        updated = dict(row)
        updated["decision"] = decision
        updated["reason"] = reason
        decisions.append(updated)
    return decisions


def destination_path_relation(source: Path, destination: Path | None) -> str:
    if destination is None:
        return ""
    try:
        source_resolved = source.resolve()
        destination_resolved = destination.resolve()
    except RuntimeError:
        return "symlink-related"
    if source_resolved == destination_resolved:
        return "identical"
    try:
        source_resolved.relative_to(destination_resolved)
        return "source-inside-destination"
    except ValueError:
        pass
    try:
        destination_resolved.relative_to(source_resolved)
        return "destination-inside-source"
    except ValueError:
        pass
    if source.absolute() == destination.absolute():
        return "symlink-related"
    return "disjoint"


def guided_auto_plan(
    source: Path,
    destination: Path | None,
    rows: list[dict[str, object]],
) -> dict[str, object]:
    root_row = next((row for row in rows if row.get("path") == "."), None)
    child_rows = [row for row in rows if row.get("path") != "."]
    operation_mode = "migrate-full-workspace" if destination else "setup-in-place"
    target_posture = "codex-native" if destination else "dual-run-current-workspace"
    destination_relation = destination_path_relation(source, destination) if destination else ""

    root_has_policy = bool(
        root_row
        and (
            root_row.get("has_AGENTS")
            or root_row.get("has_CLAUDE")
            or root_row.get("has_claude_project_md")
        )
    )
    confirmations: set[str] = {
        "confirm-target-posture",
        "confirm-child-repo-plan",
    }
    if root_row and root_row.get("has_AGENTS"):
        confirmations.add("confirm-agents-trust-mode")
    if destination_relation and destination_relation != "disjoint":
        confirmations.add("destination-overlap")
    blocked_auto_actions = {
        "private-or-local-memory",
        "runtime-permissions",
        "hooks",
        "mcp-write-or-production-access",
        "third-party-bridges",
        "claude-plugin-retention",
    }
    recommended_root_actions: dict[str, int] = {}
    recommended_child_actions: dict[str, int] = {}

    if root_row:
        root_action = str(root_row.get("suggested_action") or "review-needed")
        recommended_root_actions[root_action] = 1

    for row in child_rows:
        action = str(row.get("suggested_action") or "review-needed")
        recommended_child_actions[action] = recommended_child_actions.get(action, 0) + 1

    for row in rows:
        signals = set(row.get("signals") or [])
        if {"claude-local-md", "claude-home-imports", "claude-external-imports"} & signals:
            confirmations.add("confirm-private-context-disposition")
        if {
            "claude-permissions",
            "claude-hooks",
            "claude-sessionstart",
            "claude-settings-mcp",
            "mcp-config",
        } & signals:
            confirmations.add("confirm-runtime-config-disposition")
        if row.get("plugin_decisions_required"):
            confirmations.add("confirm-plugin-ecosystem-decisions")
        if "destination-present" in signals:
            confirmations.add("confirm-destination-overwrite-or-merge")

    return {
        "mode": "guided-auto",
        "source": str(source),
        "destination": str(destination) if destination else "",
        "operation_mode_default": operation_mode,
        "target_posture_default": target_posture,
        "agents_trust_mode_default": "unknown" if root_row and root_row.get("has_AGENTS") else "not-present",
        "parent_policy_mode_default": "inherit-parent" if root_has_policy and child_rows else "isolated",
        "child_repo_selection_default": "selected" if child_rows else "all",
        "child_repo_count": len(child_rows),
        "destination_path_relation": destination_relation,
        "recommended_root_actions": recommended_root_actions,
        "recommended_action_counts": recommended_child_actions,
        "user_confirmations_required": sorted(confirmations),
        "blocked_auto_actions": sorted(blocked_auto_actions),
        "notes": [
            "Defaults are plan suggestions, not approval to edit files.",
            "Risky runtime, private, MCP write/prod, third-party bridge, and Claude plugin retention decisions require user confirmation.",
        ],
    }


def name_tokens(path_text: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", path_text.lower()) if token}


def looks_claude_native(rel_path: str, repo: Path) -> bool:
    tokens = name_tokens(rel_path)
    repo_tokens = name_tokens(repo.name)
    keyword_hit = bool(tokens & CLAUDE_NATIVE_KEYWORDS)
    qualifier_hit = bool(tokens & CLAUDE_NATIVE_QUALIFIERS)

    if "claude" in repo_tokens:
        return True
    if keyword_hit and qualifier_hit:
        return True
    return False


def has_runtime_config_structure(repo: Path) -> bool:
    runtime_files = ("settings.json", "settings.local.json", "hooks.json", "config.toml")
    if any((repo / name).is_file() for name in runtime_files):
        text = read_first_existing_text(
            repo,
            ("README.md", "README.ko.md", "package.json", "pyproject.toml"),
        ).lower()
        if any(token in text for token in ("hook", "hooks", "permission", "settings", "runtime")):
            return True
    for path in repo.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        if path.suffix not in {".sh", ".js", ".mjs", ".ts", ".py", ".json", ".toml"}:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            continue
        if any(
            marker in content
            for marker in (
                ".claude/settings",
                ".codex/config.toml",
                ".codex/hooks.json",
                "mcp_servers",
            )
        ):
            return True
    return False


def list_signals(
    repo: Path,
    rel_path: str,
    destination_repo: Path | None,
    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
) -> list[str]:
    signals: list[str] = []
    claude_dir = repo / ".claude"
    agents_size = file_size(repo / "AGENTS.md")
    agents_override_size = file_size(repo / "AGENTS.override.md")
    imports = import_stats(repo, max_source_bytes=max_source_bytes)
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
    if imports["inline_refs"]:
        signals.append("claude-inline-refs")
    if imports["home"]:
        signals.append("claude-home-imports")
    if imports["external"]:
        signals.append("claude-external-imports")
    if imports["unsafe_external"]:
        signals.append("claude-unsafe-external-imports")
    if imports["unresolved"]:
        signals.append("claude-unresolved-imports")
    if imports["unreadable"]:
        signals.append("unreadable-markdown-source")
    if imports["skipped_oversized_count"]:
        signals.append("skipped-oversized-source")
    if exists(repo / "AGENTS.md"):
        signals.append("agents-md")
        if agents_md_appears_generated(repo / "AGENTS.md"):
            signals.append("agents-md-appears-generated")
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
    if any(repo.rglob("SKILL.md")):
        signals.append("skill-source-structure")
    if has_runtime_config_structure(repo):
        signals.append("agent-runtime-config-structure")
    if "permissions" in claude_settings_keys:
        signals.append("claude-permissions")
    if "mcpServers" in claude_settings_keys:
        signals.append("claude-settings-mcp")
    if "SessionStart" in claude_settings_keys:
        signals.append("claude-sessionstart")
    if "unreadable" in claude_settings_keys:
        signals.append("claude-settings-unreadable")

    path_parts = {part.lower() for part in Path(rel_path).parts}
    if looks_claude_native(rel_path, repo):
        signals.append("claude-native-repo")
    path_tokens = name_tokens(rel_path)
    if {"config", "settings", "sync"} & path_tokens and "claude" in path_tokens:
        signals.append("claude-config-repo")
    elif {"config", "settings", "sync"} & path_tokens and {
        "agent",
        "agents",
    } & path_tokens:
        signals.append("agent-config-repo")
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
    if "git-marker-file-submodule" in signal_set:
        return "include-copy-only"
    if {
        "claude-native-repo",
        "claude-config-repo",
        "agent-config-repo",
        "agent-runtime-config-structure",
    } & signal_set:
        return "defer-claude-native"
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


def read_first_existing_text(repo: Path, names: Iterable[str]) -> str:
    for name in names:
        path = repo / name
        if not path.is_file():
            continue
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    return ""


def classify_repo_kind(row: dict[str, object]) -> str:
    path = str(row.get("path") or "")
    source = Path(str(row.get("source") or "."))
    signals = set(row.get("signals") or [])
    purpose_text = read_first_existing_text(
        source,
        ("README.md", "README.ko.md", "package.json", "pyproject.toml"),
    ).lower()

    if {
        "claude-native-repo",
        "claude-config-repo",
        "agent-config-repo",
        "agent-runtime-config-structure",
    } & signals:
        if "claude --print" in purpose_text and "app" in purpose_text:
            return "product-using-claude-cli"
        if "skill-source-structure" in signals or "skill source" in purpose_text:
            return "skill-source"
        return "claude-runtime-tool"
    if "claude --print" in purpose_text:
        return "product-using-claude-cli"
    if "skill-source-structure" in signals or "skill source" in purpose_text:
        return "skill-source"
    if row.get("plugin_decisions_required"):
        return "ecosystem-tool"
    return "workspace-repo"


def manifest_decision(row: dict[str, object], *, target_posture: str) -> tuple[str, str]:
    kind = classify_repo_kind(row)
    signals = set(row.get("signals") or [])
    action = str(row.get("suggested_action") or "")
    if kind == "claude-runtime-tool":
        return "exclude", "claude-native runtime/config/tooling repository"
    if target_posture == "codex-native" and "claude-local-md" in signals:
        return "defer", "private/local Claude context requires separate decision"
    if action in {"exclude-candidate", "defer-candidate", "review-private-context"}:
        return "defer", f"inventory suggested {action}"
    return "migrate", f"inventory suggested {action or 'review-needed'}"


def build_migration_manifest(
    source: Path,
    destination: Path | None,
    rows: list[dict[str, object]],
    *,
    operation_mode: str,
    target_posture: str,
) -> list[dict[str, object]]:
    manifest: list[dict[str, object]] = []
    for row in rows:
        rel = str(row.get("path") or ".")
        source_path = Path(str(row.get("source") or source))
        destination_path = ""
        if destination is not None:
            destination_path = str(destination if rel == "." else destination / rel)
        decision, reason = manifest_decision(row, target_posture=target_posture)
        manifest.append(
            {
                "path": rel,
                "purpose": repo_purpose_summary(source_path),
                "kind": classify_repo_kind(row),
                "decision": decision,
                "reason": reason,
                "destination": destination_path,
                "evidence_source": "inventory-signals",
                "operation_mode": operation_mode,
                "target_posture": target_posture,
                "signals": row.get("signals") or [],
                "remote_freshness": git_remote_freshness(source_path)
                if bool(row.get("has_git"))
                else {},
            }
        )
    return manifest


def repo_purpose_summary(repo: Path) -> str:
    text = read_first_existing_text(repo, ("README.md", "README.ko.md", "package.json"))
    for line in text.splitlines():
        stripped = line.strip(" #\t")
        if stripped:
            return stripped[:160]
    return repo.name


def forbidden_path_scan(destination: Path, *, target_posture: str) -> list[dict[str, str]]:
    if target_posture != "codex-native" or not destination.exists():
        return []
    hits: list[dict[str, str]] = []
    for path in sorted(destination.rglob("CLAUDE.md")):
        if ".git" not in path.parts:
            hits.append({"kind": "claude-md", "path": str(path), "severity": "fail"})
    for path in sorted(destination.rglob(".claude")):
        if path.is_dir() and ".git" not in path.parts:
            hits.append({"kind": "claude-runtime-dir", "path": str(path), "severity": "fail"})
    for path in sorted(destination.rglob(".mcp.json")):
        if ".git" not in path.parts:
            hits.append({"kind": "mcp-config", "path": str(path), "severity": "fail"})
    return hits


def has_context_root_markers(path: Path) -> bool:
    return any((path / marker).exists() for marker in CONTEXT_ROOT_MARKERS)


def inventory_row(
    repo: Path,
    rel: str,
    destination_repo: Path | None,
    available_plugins: dict[str, list[str]],
    plugin_mappings: dict[str, list[dict[str, str]]],
    *,
    has_git: bool,
    audit_detail: bool = False,
    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
    depth_limit_skipped: int = 0,
    depth_limit_pruned: int = 0,
    extra_signals: Iterable[str] = (),
) -> dict[str, object]:
    signals = list_signals(
        repo,
        rel,
        destination_repo,
        max_source_bytes=max_source_bytes,
    )
    marker_kind = git_marker_kind(repo) if has_git else "none"
    if marker_kind != "none":
        signals.append(f"git-marker-{marker_kind}")
    if depth_limit_skipped:
        signals.append("depth-limit-reached")
    if depth_limit_pruned:
        signals.append("depth-limit-pruned-dirs")
    for signal in extra_signals:
        if signal not in signals:
            signals.append(signal)
    agents_size = file_size(repo / "AGENTS.md")
    agents_override_size = file_size(repo / "AGENTS.override.md")
    imports = import_stats(
        repo,
        audit_detail=audit_detail,
        max_source_bytes=max_source_bytes,
    )
    claude_settings_keys = settings_keys(repo)
    plugin_refs = detected_plugin_refs(repo, max_source_bytes=max_source_bytes)
    candidates = plugin_candidates(plugin_refs, available_plugins, plugin_mappings)
    row = {
        "path": rel,
        "source": str(repo),
        "destination": str(destination_repo) if destination_repo else None,
        "has_git": has_git,
        "git_marker_kind": marker_kind,
        "has_CLAUDE": exists(repo / "CLAUDE.md"),
        "has_claude_project_md": exists(repo / ".claude" / "CLAUDE.md"),
        "has_CLAUDE_local": exists(repo / "CLAUDE.local.md"),
        "has_AGENTS": exists(repo / "AGENTS.md"),
        "has_AGENTS_override": exists(repo / "AGENTS.override.md"),
        "has_mcp": exists(repo / ".mcp.json"),
        "has_claude_dir": (repo / ".claude").is_dir(),
        "claude_rules_count": count_files(repo / ".claude" / "rules", "*.md"),
        "claude_imports_count": imports["total"],
        "claude_inline_refs_count": imports["inline_refs"],
        "claude_home_imports_count": imports["home"],
        "claude_external_imports_count": imports["external"],
        "unsafe_external_imports_count": imports["unsafe_external"],
        "claude_unresolved_imports_count": imports["unresolved"],
        "unreadable_markdown_sources_count": imports["unreadable"],
        "skipped_oversized_count": imports["skipped_oversized_count"],
        "depth_limit_skipped_git_count": depth_limit_skipped,
        "depth_limit_pruned_dir_count": depth_limit_pruned,
        "unreadable_markdown_source_paths": imports["unreadable_paths"],
        "skipped_oversized_source_paths": imports["skipped_oversized_paths"],
        "claude_settings_keys": sorted(claude_settings_keys),
        "is_claude_native_repo": (
            "claude-native-repo" in signals
            or "claude-config-repo" in signals
            or "agent-config-repo" in signals
            or "agent-runtime-config-structure" in signals
        ),
        "agents_size_bytes": agents_size,
        "agents_override_size_bytes": agents_override_size,
        "detected_plugin_refs": plugin_refs,
        "codex_plugin_candidates": candidates,
        "plugin_decisions_required": plugin_decision_flags(plugin_refs, candidates),
        "signals": signals,
        "suggested_action": suggest_action(signals),
    }
    if audit_detail:
        row["claude_imports_detail"] = imports.get("imports", [])
    return row


def inventory(
    source: Path,
    destination: Path | None,
    max_depth: int,
    available_plugins: dict[str, list[str]],
    plugin_mappings: dict[str, list[dict[str, str]]] | None = None,
    audit_detail: bool = False,
    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen: set[Path] = set()
    mappings = plugin_mappings if plugin_mappings is not None else load_plugin_mappings()
    skipped_by_depth = depth_limit_skipped_git_count(source, max_depth)
    pruned_by_depth = depth_limit_pruned_dir_count(source, max_depth)

    if not has_git_marker(source) and has_context_root_markers(source):
        destination_repo = destination if destination is not None else None
        rows.append(
            inventory_row(
                source,
                ".",
                destination_repo,
                available_plugins,
                mappings,
                has_git=False,
                audit_detail=audit_detail,
                max_source_bytes=max_source_bytes,
                depth_limit_skipped=skipped_by_depth,
                depth_limit_pruned=pruned_by_depth,
                extra_signals=("non-git-context-root",),
            )
        )
        seen.add(source)
    elif not has_git_marker(source) and (skipped_by_depth or pruned_by_depth):
        rows.append(
            inventory_row(
                source,
                ".",
                destination if destination is not None else None,
                available_plugins,
                mappings,
                has_git=False,
                audit_detail=audit_detail,
                max_source_bytes=max_source_bytes,
                depth_limit_skipped=skipped_by_depth,
                depth_limit_pruned=pruned_by_depth,
                extra_signals=("depth-limit-root",),
            )
        )
        seen.add(source)

    for repo in iter_git_roots(source, max_depth):
        if repo in seen:
            continue
        seen.add(repo)

        rel = "." if repo == source else repo.relative_to(source).as_posix()
        destination_repo = None
        if destination is not None:
            destination_repo = destination if rel == "." else destination / rel

        rows.append(
            inventory_row(
                repo,
                rel,
                destination_repo,
                available_plugins,
                mappings,
                has_git=True,
                audit_detail=audit_detail,
                max_source_bytes=max_source_bytes,
                depth_limit_skipped=skipped_by_depth if repo == source else 0,
                depth_limit_pruned=pruned_by_depth if repo == source else 0,
            )
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
        "has_git",
        "git_marker_kind",
        "has_CLAUDE",
        "has_claude_project_md",
        "has_CLAUDE_local",
        "has_AGENTS",
        "has_AGENTS_override",
        "has_mcp",
        "has_claude_dir",
        "claude_rules_count",
        "claude_imports_count",
        "claude_inline_refs_count",
        "unsafe_external_imports_count",
        "claude_unresolved_imports_count",
        "unreadable_markdown_sources_count",
        "skipped_oversized_count",
        "depth_limit_skipped_git_count",
        "depth_limit_pruned_dir_count",
        "is_claude_native_repo",
        "agents_size_bytes",
        "agents_override_size_bytes",
        "detected_plugin_refs",
        "codex_plugin_candidate_summary",
        "plugin_decisions_required",
        "signals",
        "suggested_action",
    ]
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        values = []
        for header in headers:
            if header == "codex_plugin_candidate_summary":
                value = summarize_plugin_candidates(row["codex_plugin_candidates"])
            else:
                value = row[header]
            if isinstance(value, list):
                value = ", ".join(value)
            values.append(markdown_escape(value))
        print("| " + " | ".join(values) + " |")
    total_unreadable = sum(int(row.get("unreadable_markdown_sources_count") or 0) for row in rows)
    total_oversized = sum(int(row.get("skipped_oversized_count") or 0) for row in rows)
    total_depth_skipped = sum(int(row.get("depth_limit_skipped_git_count") or 0) for row in rows)
    print()
    print(f"Total unreadable markdown sources: {total_unreadable}")
    print(f"Total skipped oversized markdown sources: {total_oversized}")
    print(f"Total skipped git candidates at depth limit: {total_depth_skipped}")


def artifact_summary_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    counts: dict[tuple[str, str, str], int] = {}
    for row in rows:
        key = (
            str(row.get("artifact_type") or ""),
            str(row.get("effective_ecosystem") or row.get("ecosystem") or ""),
            str(row.get("provider") or ""),
        )
        counts[key] = counts.get(key, 0) + 1
    return [
        {
            "artifact_type": artifact_type,
            "effective_ecosystem": ecosystem,
            "provider": provider,
            "count": count,
        }
        for (artifact_type, ecosystem, provider), count in sorted(counts.items())
    ]


def print_artifact_markdown(rows: list[dict[str, object]], output: str = "detail") -> None:
    if not rows:
        return
    if output == "summary":
        headers = [
            "artifact_type",
            "effective_ecosystem",
            "provider",
            "count",
        ]
        summary_rows = artifact_summary_rows(rows)
        print()
        print("## Ecosystem Artifacts Summary")
        print()
        print("| " + " | ".join(headers) + " |")
        print("| " + " | ".join("---" for _ in headers) + " |")
        for row in summary_rows:
            values = [markdown_escape(row[header]) for header in headers]
            print("| " + " | ".join(values) + " |")
        return

    headers = [
        "artifact_type",
        "scanned_manifest_type",
        "effective_ecosystem",
        "source_class",
        "provider",
        "name",
        "version",
        "source_path",
        "manifest_path",
        "signals",
    ]
    print()
    print("## Ecosystem Artifacts")
    print()
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


def print_guided_auto_plan(plan: dict[str, object]) -> None:
    if not plan:
        return
    print()
    print("## Guided Auto Plan")
    print()
    fields = [
        "mode",
        "operation_mode_default",
        "target_posture_default",
        "agents_trust_mode_default",
        "parent_policy_mode_default",
        "child_repo_selection_default",
        "child_repo_count",
        "destination_path_relation",
        "recommended_root_actions",
        "recommended_action_counts",
        "user_confirmations_required",
        "blocked_auto_actions",
        "notes",
    ]
    for field in fields:
        value = plan.get(field, "")
        if isinstance(value, list):
            value = ", ".join(value)
        elif isinstance(value, dict):
            value = ", ".join(f"{key}:{count}" for key, count in sorted(value.items()))
        print(f"- {field}: {markdown_escape(value)}")


def print_manifest_markdown(manifest: list[dict[str, object]]) -> None:
    if not manifest:
        return
    headers = [
        "path",
        "kind",
        "decision",
        "reason",
        "destination",
        "remote",
    ]
    print()
    print("## Migration Manifest Draft")
    print()
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join("---" for _ in headers) + " |")
    for row in manifest:
        freshness = row.get("remote_freshness") or {}
        remote = ""
        if isinstance(freshness, dict):
            signals = freshness.get("signals") or []
            if isinstance(signals, list):
                remote = ", ".join(str(signal) for signal in signals)
        values = [
            row.get("path", ""),
            row.get("kind", ""),
            row.get("decision", ""),
            row.get("reason", ""),
            row.get("destination", ""),
            remote,
        ]
        print("| " + " | ".join(markdown_escape(value) for value in values) + " |")


def print_global_runtime_markdown(rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    headers = ["path", "kind", "decision", "reason", "signals"]
    print()
    print("## Global Claude Runtime Snapshot")
    print()
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        values = []
        for header in headers:
            value = row.get(header, "")
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value)
            values.append(markdown_escape(value))
        print("| " + " | ".join(values) + " |")


def print_forbidden_scan_markdown(hits: list[dict[str, str]]) -> None:
    print()
    print("## Forbidden Path Scan")
    print()
    if not hits:
        print("No forbidden active-path artifacts found.")
        return
    headers = ["kind", "severity", "path"]
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join("---" for _ in headers) + " |")
    for hit in hits:
        print("| " + " | ".join(markdown_escape(hit.get(header, "")) for header in headers) + " |")


def print_mcp_audit_markdown(rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    headers = [
        "name",
        "origin",
        "managed_by",
        "transport",
        "decision",
        "reason",
        "risk_signals",
    ]
    print()
    print("## MCP Capability Audit")
    print()
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        values = []
        for header in headers:
            value = row.get(header, "")
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value)
            values.append(markdown_escape(value))
        print("| " + " | ".join(values) + " |")


def summarize_plugin_candidates(candidates: object) -> str:
    if not isinstance(candidates, list):
        return ""
    parts = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        source = candidate.get("source", "")
        target = candidate.get("candidate") or "<none>"
        status = candidate.get("candidate_status", "unknown")
        confidence = candidate.get("confidence", "unknown")
        parts.append(f"{source}->{target} [{status}/{confidence}]")
    return "; ".join(parts)


def main() -> None:
    args = parse_args()
    source = resolve_dir(args.source, "--source", must_exist=True)
    destination = (
        resolve_dir(args.destination, "--destination", must_exist=False)
        if args.destination
        else None
    )
    codex_home = resolve_dir(args.codex_home, "--codex-home", must_exist=False)
    claude_home = resolve_dir(args.claude_home, "--claude-home", must_exist=False)
    operation_mode = args.operation_mode or (
        "migrate-full-workspace" if destination else "setup-in-place"
    )
    target_posture = args.target_posture or (
        "codex-native" if destination else "dual-run-current-workspace"
    )

    available_plugins = discover_codex_plugins(codex_home)
    plugin_mappings = load_plugin_mappings()
    rows = inventory(
        source,
        destination,
        args.max_depth,
        available_plugins,
        plugin_mappings,
        audit_detail=args.audit_detail,
        max_source_bytes=args.max_source_bytes,
    )
    artifacts = (
        inventory_artifacts(artifact_roots(codex_home, args.artifact_scope, args.artifact_root))
        if args.include_artifacts
        else []
    )
    artifact_output = args.artifact_output or ("detail" if args.format == "json" else "summary")
    artifact_payload = artifact_summary_rows(artifacts) if artifact_output == "summary" else artifacts
    plan = guided_auto_plan(source, destination, rows) if args.guided_auto_plan else {}
    manifest = (
        build_migration_manifest(
            source,
            destination,
            rows,
            operation_mode=operation_mode,
            target_posture=target_posture,
        )
        if args.emit_manifest
        else []
    )
    global_runtime = (
        global_claude_runtime_snapshot(claude_home)
        if args.include_global_claude_runtime
        else []
    )
    forbidden_root = (
        resolve_dir(args.forbidden_scan_root, "--forbidden-scan-root", must_exist=False)
        if args.forbidden_scan_root
        else None
    )
    forbidden_hits = (
        forbidden_path_scan(forbidden_root, target_posture=target_posture)
        if forbidden_root is not None
        else []
    )
    mcp_audit = (
        mcp_capability_decisions(
            source_mcp_capabilities(source),
            target_mcp_baseline(codex_home),
        )
        if args.include_mcp_audit
        else []
    )
    if args.format == "json":
        if (
            args.include_artifacts
            or args.guided_auto_plan
            or args.emit_manifest
            or args.include_global_claude_runtime
            or args.forbidden_scan_root
            or args.include_mcp_audit
        ):
            print(
                json.dumps(
                    {
                        "guided_auto_plan": plan,
                        "repos": rows,
                        "artifacts": artifact_payload,
                        "migration_manifest": manifest,
                        "global_claude_runtime": global_runtime,
                        "forbidden_path_scan": forbidden_hits,
                        "mcp_capability_audit": mcp_audit,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        print_guided_auto_plan(plan)
        print_markdown(rows)
        print_manifest_markdown(manifest)
        print_global_runtime_markdown(global_runtime)
        if args.forbidden_scan_root:
            print_forbidden_scan_markdown(forbidden_hits)
        print_mcp_audit_markdown(mcp_audit)
        print_artifact_markdown(artifacts, output=artifact_output)


if __name__ == "__main__":
    main()
