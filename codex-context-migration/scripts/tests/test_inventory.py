import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "inventory.py"
SPEC = importlib.util.spec_from_file_location("inventory", SCRIPT_PATH)
inventory = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = inventory
SPEC.loader.exec_module(inventory)


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
