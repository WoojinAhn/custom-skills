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
CONTEXT_ROOT_MARKERS = ("SKILL.md", "CLAUDE.md", "AGENTS.md", ".claude", ".mcp.json")

IMPORT_RE = re.compile(
    r"""^\s*(?:[-*+]\s*)?@(?P<path>(?:~|/|\.{1,2}/)?[A-Za-z0-9_.\-/]+)"""
)
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

PLUGIN_MAPPINGS = {
    "frontend-design@claude-plugins-official": [
        {
            "candidate": "build-web-apps@openai-curated",
            "confidence": "mapped",
            "note": "Prefer Codex official web-app workflow before retaining Claude frontend-design.",
        }
    ],
    "superpowers@claude-plugins-official": [
        {
            "candidate": "superpowers@openai-curated",
            "confidence": "same-name",
            "note": "Same name still requires behavior and trigger comparison.",
        }
    ],
    "playwright@claude-plugins-official": [
        {
            "candidate": "browser@openai-bundled",
            "confidence": "mapped",
            "note": "Pair with Codex MCP Playwright review when browser automation is needed.",
        },
        {
            "candidate": "mcp-playwright@codex-mcp",
            "confidence": "research",
            "note": "Check Codex MCP registration; not a plugin marketplace entry.",
        },
    ],
    "mcp-server-dev@claude-plugins-official": [
        {
            "candidate": "openai-developers@openai-curated",
            "confidence": "research",
            "note": "No guaranteed one-to-one equivalent; inspect available OpenAI developer tooling.",
        },
        {
            "candidate": "plugin-eval@openai-curated",
            "confidence": "research",
            "note": "Evaluate only if the task is plugin/server evaluation rather than MCP server authoring.",
        },
    ],
    "cc@sendbird": [
        {
            "candidate": "",
            "confidence": "third-party-exception",
            "note": "Reverse bridge candidate; retain only with explicit user reason.",
        }
    ],
}


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
        "--guided-auto-plan",
        action="store_true",
        help="Emit a conservative guided-auto migration plan draft from inventory signals.",
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


def import_stats(repo: Path) -> dict[str, object]:
    total = 0
    home = 0
    external = 0
    unsafe_external = 0
    unresolved = 0
    unreadable_paths: list[str] = []
    for source in iter_claude_markdown_sources(repo):
        try:
            lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            unreadable_paths.append(str(source))
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
            total += 1
            if import_path.startswith("~/"):
                home += 1
            if resolved.kind in {"absolute", "external"}:
                unsafe_external += 1
            if resolved.kind == "external":
                external += 1
            if resolved.safe_to_stat and not resolved.path.exists():
                unresolved += 1
    return {
        "total": total,
        "home": home,
        "external": external,
        "unsafe_external": unsafe_external,
        "unresolved": unresolved,
        "unreadable": len(unreadable_paths),
        "unreadable_paths": unreadable_paths,
    }


def read_json_file(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


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


def detected_plugin_refs(repo: Path) -> list[str]:
    refs: set[str] = set()

    for settings_file in iter_claude_settings_sources(repo):
        data = read_json_file(settings_file)
        if data is not None:
            refs.update(collect_plugin_refs_from_json(data))

    for source in iter_claude_markdown_sources(repo):
        try:
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


def ecosystem_from_signals(signals: Iterable[str], provider: str) -> str:
    signal_set = set(signals)
    if "has-codex-manifest" in signal_set and "has-claude-manifest" in signal_set:
        return "mixed"
    if provider.startswith("openai-") or "has-codex-manifest" in signal_set:
        return "codex"
    if provider.startswith("claude-") or "has-claude-manifest" in signal_set:
        return "claude"
    return "unknown"


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
    refs: Iterable[str], available_plugins: dict[str, list[str]]
) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for ref in sorted(refs):
        mappings = PLUGIN_MAPPINGS.get(ref)
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


def guided_auto_plan(
    source: Path,
    destination: Path | None,
    rows: list[dict[str, object]],
) -> dict[str, object]:
    root_row = next((row for row in rows if row.get("path") == "."), None)
    child_rows = [row for row in rows if row.get("path") != "."]
    operation_mode = "migrate-full-workspace" if destination else "setup-in-place"
    target_posture = "codex-native" if destination else "dual-run-current-workspace"

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
    if imports["unsafe_external"]:
        signals.append("claude-unsafe-external-imports")
    if imports["unresolved"]:
        signals.append("claude-unresolved-imports")
    if imports["unreadable"]:
        signals.append("unreadable-markdown-source")
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
    if looks_claude_native(rel_path, repo):
        signals.append("claude-native-repo")
    path_tokens = name_tokens(rel_path)
    if {"config", "settings", "sync"} & path_tokens and "claude" in path_tokens:
        signals.append("claude-config-repo")
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
    if {"claude-native-repo", "claude-config-repo"} & signal_set:
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


def has_context_root_markers(path: Path) -> bool:
    return any((path / marker).exists() for marker in CONTEXT_ROOT_MARKERS)


def inventory_row(
    repo: Path,
    rel: str,
    destination_repo: Path | None,
    available_plugins: dict[str, list[str]],
    *,
    has_git: bool,
    extra_signals: Iterable[str] = (),
) -> dict[str, object]:
    signals = list_signals(repo, rel, destination_repo)
    for signal in extra_signals:
        if signal not in signals:
            signals.append(signal)
    agents_size = file_size(repo / "AGENTS.md")
    agents_override_size = file_size(repo / "AGENTS.override.md")
    imports = import_stats(repo)
    claude_settings_keys = settings_keys(repo)
    plugin_refs = detected_plugin_refs(repo)
    candidates = plugin_candidates(plugin_refs, available_plugins)
    return {
        "path": rel,
        "source": str(repo),
        "destination": str(destination_repo) if destination_repo else None,
        "has_git": has_git,
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
        "unsafe_external_imports_count": imports["unsafe_external"],
        "claude_unresolved_imports_count": imports["unresolved"],
        "unreadable_markdown_sources_count": imports["unreadable"],
        "unreadable_markdown_source_paths": imports["unreadable_paths"],
        "claude_settings_keys": sorted(claude_settings_keys),
        "is_claude_native_repo": (
            "claude-native-repo" in signals or "claude-config-repo" in signals
        ),
        "agents_size_bytes": agents_size,
        "agents_override_size_bytes": agents_override_size,
        "detected_plugin_refs": plugin_refs,
        "codex_plugin_candidates": candidates,
        "plugin_decisions_required": plugin_decision_flags(plugin_refs, candidates),
        "signals": signals,
        "suggested_action": suggest_action(signals),
    }


def inventory(
    source: Path,
    destination: Path | None,
    max_depth: int,
    available_plugins: dict[str, list[str]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen: set[Path] = set()

    if not has_git_marker(source) and has_context_root_markers(source):
        destination_repo = destination if destination is not None else None
        rows.append(
            inventory_row(
                source,
                ".",
                destination_repo,
                available_plugins,
                has_git=False,
                extra_signals=("non-git-context-root",),
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
                has_git=True,
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
        "has_CLAUDE",
        "has_claude_project_md",
        "has_CLAUDE_local",
        "has_AGENTS",
        "has_AGENTS_override",
        "has_mcp",
        "has_claude_dir",
        "claude_rules_count",
        "claude_imports_count",
        "unsafe_external_imports_count",
        "claude_unresolved_imports_count",
        "unreadable_markdown_sources_count",
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


def print_artifact_markdown(rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    headers = [
        "artifact_type",
        "scanned_manifest_type",
        "effective_ecosystem",
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

    available_plugins = discover_codex_plugins(codex_home)
    rows = inventory(source, destination, args.max_depth, available_plugins)
    artifacts = (
        inventory_artifacts(artifact_roots(codex_home, args.artifact_scope, args.artifact_root))
        if args.include_artifacts
        else []
    )
    plan = guided_auto_plan(source, destination, rows) if args.guided_auto_plan else {}
    if args.format == "json":
        if args.include_artifacts or args.guided_auto_plan:
            print(
                json.dumps(
                    {
                        "guided_auto_plan": plan,
                        "repos": rows,
                        "artifacts": artifacts,
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
        print_artifact_markdown(artifacts)


if __name__ == "__main__":
    main()
