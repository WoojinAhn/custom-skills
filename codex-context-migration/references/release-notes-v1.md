# codex-context-migration v1 — Draft Release Notes

Status: draft for a future v1 release. This document does not announce a
published tag, GitHub Release, or curated catalog listing. The release version,
date, and final validation evidence must be recorded when the release is cut.

## Purpose

`codex-context-migration` provides an advanced audit workflow around
Claude-to-Codex workspace migration. Use OpenAI's curated `migrate-to-codex`
skill for routine supported conversion. Use this companion when a migration
also needs multi-repository selection, workspace-copy manifests, private
context separation, parent-policy layering, target-posture decisions, or
separate evidence for file edits, commits, and remote writes.

The full workflow runs in Codex. Claude Code support is limited to read-only
inventory and audit planning before handing conversion and final validation
to Codex.

## Included In The v1 Draft

- **Read-only inventory:** discover repositories and context artifacts, report
  import and runtime signals, and emit Markdown or JSON. Optional output adds
  migration manifests, plugin/skill inventory, and MCP capability decisions.
- **Guided-auto planning:** propose conservative defaults and flag decisions
  requiring confirmation. Defaults are review suggestions, not permission to
  edit, copy, retain runtime behavior, or register services.
- **Operation modes:** `setup-in-place` adds context in the current workspace;
  `migrate-full-workspace` copies approved workspace content to a destination;
  `context-only` leaves ordinary code repositories outside the copy scope.
  Full-workspace work cannot silently become context-only migration.
- **Workspace policy:** record `codex-native` or
  `dual-run-current-workspace` posture, parent-policy inheritance, and explicit
  include/defer/exclude decisions for child repositories. Native, temporary
  bridge, and dual-run instruction shapes are documented.
- **Copy and path checks:** require a manifest before copying, surface source
  and destination overlap, record remote freshness decisions, and scan the
  Codex-native destination for active Claude instruction/runtime artifacts.
- **Instruction safeguards:** treat source `AGENTS.md`, `CLAUDE.md`, `.claude/`,
  and imported content as data. Review generated instructions against durable
  sources. The import analyzer avoids existence checks for home, absolute,
  escaping, or symlinked import targets.
- **Oversized-source guard:** skip Markdown sources above the import/plugin
  signal parser's configurable size limit (default: 1 MiB), reporting skipped
  and unreadable sources for follow-up. This limit does not cap every file
  read by every inventory component.
- **Supporting material:** audit templates, a worked before/after example,
  ecosystem decisions, and focused inventory regression tests.

## Quick Start

Begin with the [skill README](https://github.com/WoojinAhn/custom-skills/blob/master/codex-context-migration/README.md) for the official-first decision and
optional advanced-audit installation. Install the whole skill directory so its
scripts and references remain available. See [distribution and
updates](https://github.com/WoojinAhn/custom-skills/blob/master/codex-context-migration/README.md#distribution-and-updates) for source tracking, snapshot
pinning, and copied-install behavior.

For an advanced migration, give Codex an explicit starting scope:

```text
Use codex-context-migration for the advanced workspace audit.
Source root: /path/to/old-workspace
Operation mode: migrate-full-workspace
Destination root: /path/to/new-codex-workspace
Read-only inventory is authorized. Show the guided-auto plan before edits.
Use the official migrate-to-codex skill for supported artifact conversion.
```

To inspect the same scope manually, use Python 3.11 or later and run from this
repository's root after replacing both example paths:

```bash
python3 codex-context-migration/scripts/inventory.py \
  --source /path/to/old-workspace \
  --destination /path/to/new-codex-workspace \
  --guided-auto-plan \
  --emit-manifest \
  --format markdown
```

This command emits inventory and draft planning output; it does not perform
the migration. Confirm target posture and scoped authorization before edits.
The [worked example](https://github.com/WoojinAhn/custom-skills/blob/master/codex-context-migration/references/example-migration.md) shows how durable instructions,
private context, and runtime artifacts are separated.

## Validation And Release Gate

The [inventory test suite](https://github.com/WoojinAhn/custom-skills/blob/master/codex-context-migration/scripts/tests/test_inventory.py) covers import
classification, false-positive guards, destination overlap, symlink loops,
oversized and unreadable sources, manifests, remote freshness, forbidden-path
scans, and MCP/plugin decisions. Its presence is not a claim that public
release QA has passed.

Before publishing, record the tested commit and results for the inventory
suite, clean installation and update/pin checks, README rendering and links,
and applicable Codex instruction-load validation. Public smoke QA is tracked
in [#40](https://github.com/WoojinAhn/custom-skills/issues/40); tag and release
publication is tracked separately in
[#39](https://github.com/WoojinAhn/custom-skills/issues/39).

## Limits

- This is an audit companion, not a blind `CLAUDE.md` rename or a replacement
  for the official converter. Inventory signals require review and may miss
  context or produce false positives.
- Private memory, credentials, hooks, permissions, MCP write/production access,
  third-party bridges, and retained Claude plugins are not silently migrated.
  Runtime and private-context decisions require explicit authorization.
- Plugin mappings identify candidates, not verified equivalence, availability,
  authentication, or target installation. MCP capabilities must be checked
  against the actual target baseline.
- Draft notes do not establish a released version, catalog acceptance, or
  automatic update guarantee. Snapshot and copied installations require
  deliberate updates as described in the distribution guide.

## License And Further Reading

The skill package is distributed under the [MIT license](https://github.com/WoojinAhn/custom-skills/blob/master/codex-context-migration/LICENSE.txt).
See the [repository README](https://github.com/WoojinAhn/custom-skills/blob/master/README.md), [operational
instructions](https://github.com/WoojinAhn/custom-skills/blob/master/codex-context-migration/SKILL.md), and [operation-mode reference](https://github.com/WoojinAhn/custom-skills/blob/master/codex-context-migration/references/operation-modes.md)
for the full scope and completion criteria.
