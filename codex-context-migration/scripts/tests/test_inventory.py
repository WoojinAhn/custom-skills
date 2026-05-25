import importlib.util
import json
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "inventory.py"
SPEC = importlib.util.spec_from_file_location("inventory", SCRIPT_PATH)
inventory = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = inventory
SPEC.loader.exec_module(inventory)


def run_git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def commit_file(repo: Path, name: str, content: str) -> None:
    (repo / name).write_text(content, encoding="utf-8")
    run_git(repo, "add", name)
    run_git(
        repo,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        f"add {name}",
    )


def test_inventory_non_git_root_creates_pseudo_row(tmp_path):
    source = tmp_path / "skill"
    source.mkdir()
    (source / "SKILL.md").write_text("---\nname: test\n---\n", encoding="utf-8")

    rows = inventory.inventory(source, None, 5, {})

    assert len(rows) == 1
    assert rows[0]["path"] == "."
    assert rows[0]["has_git"] is False
    assert "non-git-context-root" in rows[0]["signals"]


def test_plugin_ref_rejects_github_actions_ref(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "CLAUDE.md").write_text(
        "Use actions/github-script@v7 in GitHub Actions.\n",
        encoding="utf-8",
    )

    rows = inventory.inventory(repo, None, 5, {})

    assert rows[0]["detected_plugin_refs"] == []


def test_plugin_refs_from_settings_require_plugin_context(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    claude_dir = repo / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text(
        """
        {
          "hooks": {"foo": "actions/checkout@v3"},
          "enabledPlugins": ["frontend-design@claude-plugins-official"]
        }
        """,
        encoding="utf-8",
    )

    rows = inventory.inventory(repo, None, 5, {})

    assert rows[0]["detected_plugin_refs"] == [
        "frontend-design@claude-plugins-official"
    ]


def test_guided_auto_separates_root_and_child_action_counts(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "CLAUDE.md").write_text("Project guidance.\n", encoding="utf-8")
    rows = inventory.inventory(repo, None, 5, {})

    plan = inventory.guided_auto_plan(repo, None, rows)

    assert plan["child_repo_count"] == 0
    assert plan["recommended_action_counts"] == {}
    assert plan["recommended_root_actions"] == {"include-candidate": 1}


def test_mixed_manifest_reports_mixed_schema(tmp_path):
    mixed = tmp_path / "mixed"
    mixed.mkdir()
    (mixed / ".codex-plugin").mkdir()
    (mixed / ".claude-plugin").mkdir()
    (mixed / ".codex-plugin" / "plugin.json").write_text(
        '{"name":"mixed"}\n',
        encoding="utf-8",
    )
    (mixed / ".claude-plugin" / "plugin.json").write_text(
        '{"name":"mixed"}\n',
        encoding="utf-8",
    )
    codex_only = tmp_path / "codex-only"
    codex_only.mkdir()
    (codex_only / ".codex-plugin").mkdir()
    (codex_only / ".codex-plugin" / "plugin.json").write_text(
        '{"name":"codex-only"}\n',
        encoding="utf-8",
    )

    artifacts = inventory.inventory_artifacts([tmp_path])
    mixed_row = next(row for row in artifacts if row["name"] == "mixed")
    codex_row = next(row for row in artifacts if row["name"] == "codex-only")

    assert mixed_row["artifact_type"] == "plugin"
    assert mixed_row["effective_ecosystem"] == "mixed"
    assert "mixed-plugin-manifests" in mixed_row["signals"]
    assert codex_row["effective_ecosystem"] == "codex"


def test_iter_git_roots_detects_repo_after_pruning_git_dir(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    roots = list(inventory.iter_git_roots(tmp_path, max_depth=5))

    assert roots == [repo]


def test_import_re_preserves_line_start_import_behavior(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    docs = repo / "docs"
    docs.mkdir()
    (docs / "foo.md").write_text("foo\n", encoding="utf-8")
    (docs / "bar.md").write_text("bar\n", encoding="utf-8")
    (repo / "CLAUDE.md").write_text(
        "Inline import is not in scope: see @docs/foo.md\n"
        "- @docs/bar.md\n",
        encoding="utf-8",
    )

    stats = inventory.import_stats(repo)

    assert stats["total"] == 1
    assert stats["inline_refs"] == 1
    assert stats["unresolved"] == 0


def test_iter_git_roots_detects_git_file_marker(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").write_text("gitdir: ../.git/modules/repo\n", encoding="utf-8")

    roots = list(inventory.iter_git_roots(tmp_path, max_depth=5))
    rows = inventory.inventory(tmp_path, None, 5, {})

    assert inventory.has_git_marker(repo) is True
    assert roots == [repo]
    assert rows[0]["path"] == "repo"
    assert rows[0]["has_git"] is True
    assert rows[0]["git_marker_kind"] == "file-submodule"
    assert rows[0]["suggested_action"] == "include-copy-only"


def test_guided_auto_confirms_agents_trust_mode_only_when_agents_exists(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    rows = inventory.inventory(repo, None, 5, {})
    without_agents = inventory.guided_auto_plan(repo, None, rows)
    assert "confirm-agents-trust-mode" not in without_agents["user_confirmations_required"]

    (repo / "AGENTS.md").write_text("Project policy.\n", encoding="utf-8")
    rows = inventory.inventory(repo, None, 5, {})
    with_agents = inventory.guided_auto_plan(repo, None, rows)
    assert "confirm-agents-trust-mode" in with_agents["user_confirmations_required"]


def test_indented_code_fence_does_not_hide_following_import(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    docs = repo / "docs"
    docs.mkdir()
    (docs / "bar.md").write_text("bar\n", encoding="utf-8")
    (repo / "CLAUDE.md").write_text(
        "    ```python\n"
        "    @docs/ignored.md\n"
        "    ```\n"
        "@docs/bar.md\n",
        encoding="utf-8",
    )

    stats = inventory.import_stats(repo)

    assert stats["total"] == 1
    assert stats["unresolved"] == 0


def test_destination_relation_identical_requires_confirmation(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    rows = inventory.inventory(repo, repo, 5, {})

    plan = inventory.guided_auto_plan(repo, repo, rows)

    assert plan["destination_path_relation"] == "identical"
    assert "destination-overlap" in plan["user_confirmations_required"]


def test_agents_md_generated_heuristic_adds_signal(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "AGENTS.md").write_text("<!-- Generated by foo -->\n", encoding="utf-8")

    rows = inventory.inventory(repo, None, 5, {})

    assert "agents-md-appears-generated" in rows[0]["signals"]


def test_depth_limit_reports_skipped_git_candidates(tmp_path):
    root = tmp_path / "workspace"
    deep = root / "level1" / "level2"
    deep.mkdir(parents=True)
    (deep / ".git").mkdir()

    rows = inventory.inventory(root, None, max_depth=1, available_plugins={})

    assert rows[0]["depth_limit_skipped_git_count"] == 1
    assert rows[0]["depth_limit_pruned_dir_count"] == 1
    assert "depth-limit-reached" in rows[0]["signals"]
    assert "depth-limit-pruned-dirs" in rows[0]["signals"]


def test_depth_limit_pruned_dirs_signal_does_not_claim_skipped_repo(tmp_path):
    root = tmp_path / "workspace"
    child = root / "level1" / "level2"
    child.mkdir(parents=True)
    (root / "AGENTS.md").write_text("Workspace policy.\n", encoding="utf-8")

    rows = inventory.inventory(root, None, max_depth=1, available_plugins={})

    assert rows[0]["depth_limit_skipped_git_count"] == 0
    assert rows[0]["depth_limit_pruned_dir_count"] == 1
    assert "depth-limit-pruned-dirs" in rows[0]["signals"]
    assert "depth-limit-reached" not in rows[0]["signals"]


def test_resolve_import_unsafe_external_signal(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (tmp_path / "outside.md").write_text("outside\n", encoding="utf-8")
    (repo / "CLAUDE.md").write_text("@../outside.md\n", encoding="utf-8")

    rows = inventory.inventory(repo, None, 5, {})

    assert rows[0]["unsafe_external_imports_count"] == 1
    assert "claude-unsafe-external-imports" in rows[0]["signals"]


def test_symlink_loop_does_not_recurse(tmp_path):
    root = tmp_path / "workspace"
    repo = root / "repo"
    repo.mkdir(parents=True)
    (repo / ".git").mkdir()
    (root / "loop").symlink_to(root, target_is_directory=True)

    rows = inventory.inventory(root, None, max_depth=5, available_plugins={})

    assert [row["path"] for row in rows] == ["repo"]


def test_oversized_markdown_skipped(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "CLAUDE.md").write_bytes(b"@docs/foo.md\n" + b"x" * (2 * 1024 * 1024))

    rows = inventory.inventory(repo, None, 5, {})
    stats = inventory.import_stats(repo)

    assert stats["skipped_oversized_count"] == 1
    assert rows[0]["skipped_oversized_count"] == 1
    assert rows[0]["claude_imports_count"] == 0
    assert "skipped-oversized-source" in rows[0]["signals"]


def test_smaller_markdown_under_oom_guard_parses_normally(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    docs = repo / "docs"
    docs.mkdir()
    (docs / "foo.md").write_text("foo\n", encoding="utf-8")
    padding = "x" * (100 * 1024)
    (repo / "CLAUDE.md").write_text(f"@docs/foo.md\n{padding}\n", encoding="utf-8")

    rows = inventory.inventory(repo, None, 5, {})

    assert rows[0]["skipped_oversized_count"] == 0
    assert rows[0]["claude_imports_count"] == 1
    assert "skipped-oversized-source" not in rows[0]["signals"]


def test_unreadable_markdown_signal(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    source = repo / "CLAUDE.md"
    source.write_text("@./note.md\n", encoding="utf-8")
    source.chmod(0)
    try:
        rows = inventory.inventory(repo, None, 5, {})
    finally:
        source.chmod(0o600)

    assert rows[0]["unreadable_markdown_sources_count"] == 1
    assert "unreadable-markdown-source" in rows[0]["signals"]


def test_plugin_mappings_load_from_json_without_code_change(tmp_path):
    mappings = tmp_path / "plugin-mappings.json"
    mappings.write_text(
        json.dumps(
            {
                "_schema": {"description": "test schema"},
                "custom@claude-plugins-official": [
                    {
                        "candidate": "custom@openai-curated",
                        "confidence": "mapped",
                        "note": "Loaded from fixture JSON.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    loaded = inventory.load_plugin_mappings(mappings)
    candidates = inventory.plugin_candidates(
        ["custom@claude-plugins-official"],
        {"custom": ["openai-curated"]},
        loaded,
    )

    assert candidates[0]["candidate"] == "custom@openai-curated"
    assert candidates[0]["candidate_status"] == "available"


def test_artifact_source_class_distinguishes_system_and_user_skills(tmp_path):
    codex_home = tmp_path / ".codex"
    system_skill = codex_home / "skills" / ".system" / "imagegen"
    user_skill = codex_home / "skills" / "custom-skill"
    system_skill.mkdir(parents=True)
    user_skill.mkdir(parents=True)
    (system_skill / "SKILL.md").write_text("---\nname: imagegen\n---\n", encoding="utf-8")
    (user_skill / "SKILL.md").write_text("---\nname: custom-skill\n---\n", encoding="utf-8")

    rows = inventory.inventory_artifacts([codex_home / "skills"])
    by_name = {row["name"]: row for row in rows}

    assert by_name["imagegen"]["source_class"] == "system"
    assert by_name["custom-skill"]["source_class"] == "user"


def test_markdown_report_summarizes_unreadable_sources(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "CLAUDE.md").write_text("@./note.md\n", encoding="utf-8")
    (repo / "CLAUDE.md").chmod(0)
    try:
        rows = inventory.inventory(repo, None, 5, {})
    finally:
        (repo / "CLAUDE.md").chmod(0o600)

    inventory.print_markdown(rows)

    assert "Total unreadable markdown sources: 1" in capsys.readouterr().out


def test_inventory_audit_detail_includes_per_import_rows(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    docs = repo / "docs"
    docs.mkdir()
    (docs / "foo.md").write_text("foo\n", encoding="utf-8")
    (repo / "CLAUDE.md").write_text(
        "@docs/foo.md\n@~/notes.md\n@../../../../etc/passwd\n",
        encoding="utf-8",
    )

    rows = inventory.inventory(repo, None, 5, {}, audit_detail=True)
    detail = rows[0]["claude_imports_detail"]

    assert [item["kind"] for item in detail] == ["repo", "home", "external"]
    assert detail[0]["exists"] is True
    assert detail[1]["exists"] is False
    assert detail[2]["exists"] is None


def test_artifact_summary_counts_by_type_ecosystem_provider(tmp_path, capsys):
    codex_plugin = tmp_path / "plugins" / "cache" / "openai-bundled" / "browser" / "1.0.0"
    codex_plugin.mkdir(parents=True)
    (codex_plugin / ".codex-plugin").mkdir()
    (codex_plugin / ".codex-plugin" / "plugin.json").write_text(
        '{"name":"browser"}\n',
        encoding="utf-8",
    )
    user_skill = tmp_path / "skills" / "custom"
    user_skill.mkdir(parents=True)
    (user_skill / "SKILL.md").write_text("---\nname: custom\n---\n", encoding="utf-8")
    rows = inventory.inventory_artifacts([tmp_path])

    inventory.print_artifact_markdown(rows, output="summary")

    output = capsys.readouterr().out
    assert "| plugin | codex | openai-bundled | 1 |" in output
    assert "| skill | unknown |  | 1 |" in output


def test_git_remote_freshness_detects_behind_after_fetch(tmp_path):
    remote = tmp_path / "remote.git"
    run_git(tmp_path, "init", "--bare", str(remote))

    repo = tmp_path / "repo"
    run_git(tmp_path, "clone", str(remote), str(repo))
    commit_file(repo, "README.md", "initial\n")
    run_git(repo, "push", "-u", "origin", "HEAD:master")

    other = tmp_path / "other"
    run_git(tmp_path, "clone", str(remote), str(other))
    commit_file(other, "CHANGE.md", "remote change\n")
    run_git(other, "push")

    freshness = inventory.git_remote_freshness(repo)

    assert freshness["has_remote"] is True
    assert freshness["branch"] in {"master", "main"}
    assert freshness["upstream"] == "origin/master"
    assert freshness["behind"] == 1
    assert freshness["ahead"] == 0
    assert freshness["decision_required"] is True
    assert "remote-behind" in freshness["signals"]


def test_git_remote_freshness_no_remote_is_not_blocking(tmp_path):
    repo = tmp_path / "repo"
    run_git(tmp_path, "init", str(repo))
    commit_file(repo, "README.md", "initial\n")

    freshness = inventory.git_remote_freshness(repo)

    assert freshness["has_remote"] is False
    assert freshness["decision_required"] is False
    assert freshness["signals"] == ["remote-not-configured"]


def test_manifest_excludes_claude_native_and_migrates_product_repo(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "dest"
    source.mkdir()
    destination.mkdir()

    claude_config = source / "claude-config"
    claude_config.mkdir()
    (claude_config / ".git").mkdir()
    (claude_config / "settings.json").write_text("{}", encoding="utf-8")

    app = source / "backlog-idea-app"
    app.mkdir()
    (app / ".git").mkdir()
    (app / "README.md").write_text(
        "Local web app that calls claude --print as an implementation detail.\n",
        encoding="utf-8",
    )
    (app / "CLAUDE.md").write_text("Project guidance.\n", encoding="utf-8")

    rows = inventory.inventory(source, destination, 5, {})
    manifest = inventory.build_migration_manifest(
        source,
        destination,
        rows,
        operation_mode="migrate-full-workspace",
        target_posture="codex-native",
    )
    by_path = {row["path"]: row for row in manifest}

    assert by_path["claude-config"]["decision"] == "exclude"
    assert by_path["claude-config"]["kind"] == "claude-runtime-tool"
    assert "claude-native" in by_path["claude-config"]["reason"]

    assert by_path["backlog-idea-app"]["decision"] == "migrate"
    assert by_path["backlog-idea-app"]["kind"] == "product-using-claude-cli"
    assert by_path["backlog-idea-app"]["destination"] == str(
        destination / "backlog-idea-app"
    )


def test_forbidden_path_scan_fails_codex_native_active_paths(tmp_path):
    dest = tmp_path / "dest"
    repo = dest / "repo"
    claude_dir = repo / ".claude"
    claude_dir.mkdir(parents=True)
    (repo / "CLAUDE.md").write_text("legacy\n", encoding="utf-8")
    (claude_dir / "settings.json").write_text("{}", encoding="utf-8")
    (repo / ".mcp.json").write_text("{}", encoding="utf-8")

    hits = inventory.forbidden_path_scan(dest, target_posture="codex-native")

    assert [hit["kind"] for hit in hits] == [
        "claude-md",
        "claude-runtime-dir",
        "mcp-config",
    ]
    assert all(hit["severity"] == "fail" for hit in hits)


def test_forbidden_path_scan_allows_claude_md_for_dual_run(tmp_path):
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "CLAUDE.md").write_text("legacy\n", encoding="utf-8")

    hits = inventory.forbidden_path_scan(dest, target_posture="dual-run-current-workspace")

    assert hits == []


def test_global_claude_runtime_snapshot_classifies_hooks_commands_plugins_and_skills(tmp_path):
    claude_home = tmp_path / ".claude"
    commands = claude_home / "commands"
    plugins = claude_home / "plugins"
    skills = claude_home / "skills"
    commands.mkdir(parents=True)
    plugins.mkdir()
    skills.mkdir()
    (claude_home / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {"SessionStart": [{"hooks": [{"type": "command"}]}]},
                "enabledPlugins": {"superpowers@claude-plugins-official": True},
            }
        ),
        encoding="utf-8",
    )
    (claude_home / "settings.local.json").write_text(
        json.dumps({"permissions": {"allow": ["Bash(git status:*)"]}}),
        encoding="utf-8",
    )
    (commands / "lanes.md").write_text("/lanes\n", encoding="utf-8")
    (plugins / "installed_plugins.json").write_text("{}", encoding="utf-8")
    (skills / "custom").mkdir()
    (skills / "custom" / "SKILL.md").write_text(
        "---\nname: custom\n---\n", encoding="utf-8"
    )

    rows = inventory.global_claude_runtime_snapshot(claude_home)
    by_path = {row["path"]: row for row in rows}

    assert by_path["settings.json"]["kind"] == "runtime-config"
    assert by_path["settings.json"]["decision"] == "defer"
    assert "hooks" in by_path["settings.json"]["signals"]
    assert "enabled-plugins" in by_path["settings.json"]["signals"]
    assert by_path["commands/lanes.md"]["kind"] == "claude-command"
    assert by_path["plugins/installed_plugins.json"]["kind"] == "plugin-runtime-state"
    assert by_path["skills/custom/SKILL.md"]["kind"] == "skill-source"


def test_plugin_decisions_mark_already_present_candidates():
    candidates = [
        {
            "source": "superpowers@claude-plugins-official",
            "candidate": "superpowers@openai-curated",
            "candidate_status": "available",
            "confidence": "same-name",
        },
        {
            "source": "mcp-server-dev@claude-plugins-official",
            "candidate": "openai-developers@openai-curated",
            "candidate_status": "not-found",
            "confidence": "research",
        },
    ]

    decisions = inventory.plugin_migration_decisions(candidates)
    by_source = {row["source"]: row for row in decisions}

    assert (
        by_source["superpowers@claude-plugins-official"]["decision"]
        == "already-present"
    )
    assert (
        by_source["superpowers@claude-plugins-official"]["reason"]
        == "Codex candidate is available"
    )
    assert by_source["mcp-server-dev@claude-plugins-official"]["decision"] == "defer"


def test_mcp_target_baseline_marks_codex_runtime_and_unauthenticated_cleanup(tmp_path):
    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    (codex_home / "config.toml").write_text(
        """
        [mcp_servers.node_repl]
        command = "/Applications/Codex.app/Contents/Resources/node_repl"

        [mcp_servers.notion]
        url = "https://mcp.notion.com/mcp"

        [mcp_servers.notebooklm-mcp]
        command = "notebooklm-mcp"
        """,
        encoding="utf-8",
    )

    rows = inventory.target_mcp_baseline(codex_home)
    decisions = inventory.mcp_capability_decisions([], rows)
    by_name = {row["name"]: row for row in decisions}

    assert by_name["node_repl"]["decision"] == "already-present"
    assert by_name["node_repl"]["reason"] == "Codex target runtime baseline"
    assert by_name["notion"]["decision"] == "cleanup-candidate"
    assert "auth review" in by_name["notion"]["reason"]
    assert by_name["notebooklm-mcp"]["decision"] == "already-present"
    assert by_name["notebooklm-mcp"]["managed_by"] == "codex-mcp"


def test_source_only_context7_is_candidate_not_already_present(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "context7": {
                        "command": "npx",
                        "args": ["-y", "@upstash/context7-mcp"],
                    },
                    "prod-writer": {
                        "url": "https://prod.example.com/mcp",
                        "env": {"API_TOKEN": "secret"},
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    rows = inventory.source_mcp_capabilities(source)
    decisions = inventory.mcp_capability_decisions(rows, [])
    by_name = {row["name"]: row for row in decisions}

    assert by_name["context7"]["decision"] == "manual-review"
    assert "requires explicit target decision" in by_name["context7"]["reason"]
    assert by_name["prod-writer"]["decision"] == "defer"
    assert "credentials or remote access" in by_name["prod-writer"]["reason"]
    assert by_name["prod-writer"]["origin"] == "source"


def test_context7_codex_mcp_is_not_reclassified_by_claude_marketplace_entry(tmp_path):
    codex_home = tmp_path / ".codex"
    marketplace_plugin = (
        codex_home
        / ".tmp"
        / "marketplaces"
        / "claude-plugins-official"
        / "external_plugins"
        / "context7"
        / ".claude-plugin"
    )
    marketplace_plugin.mkdir(parents=True)
    (marketplace_plugin / "plugin.json").write_text(
        json.dumps({"name": "context7"}), encoding="utf-8"
    )
    codex_home.mkdir(exist_ok=True)
    (codex_home / "config.toml").write_text(
        """
        [mcp_servers.context7]
        command = "npx"
        args = ["-y", "@upstash/context7-mcp"]
        """,
        encoding="utf-8",
    )

    artifacts = inventory.inventory_artifacts(
        [codex_home / ".tmp" / "marketplaces"]
    )
    mcp_rows = inventory.target_mcp_baseline(codex_home)
    decisions = inventory.mcp_capability_decisions([], mcp_rows)
    by_name = {row["name"]: row for row in decisions}

    assert any(
        row["name"] == "context7" and row["provider"] == "claude-plugins-official"
        for row in artifacts
    )
    assert by_name["context7"]["origin"] == "target"
    assert by_name["context7"]["managed_by"] == "codex-mcp"
    assert by_name["context7"]["decision"] == "already-present"
    assert "Claude" not in by_name["context7"]["reason"]


def test_matching_target_baseline_makes_source_mcp_already_present(tmp_path):
    source = tmp_path / "source"
    codex_home = tmp_path / ".codex"
    source.mkdir()
    codex_home.mkdir()
    (source / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "context7": {
                        "command": "npx",
                        "args": ["-y", "@upstash/context7-mcp"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (codex_home / "config.toml").write_text(
        """
        [mcp_servers.context7]
        command = "npx"
        args = ["-y", "@upstash/context7-mcp"]
        """,
        encoding="utf-8",
    )

    source_rows = inventory.source_mcp_capabilities(source)
    target_rows = inventory.target_mcp_baseline(codex_home)
    decisions = inventory.mcp_capability_decisions(source_rows, target_rows)
    context7_decisions = [row for row in decisions if row["name"] == "context7"]

    assert {row["origin"] for row in context7_decisions} == {"source", "target"}
    assert all(row["decision"] == "already-present" for row in context7_decisions)
