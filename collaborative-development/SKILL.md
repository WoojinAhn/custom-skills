---
name: collaborative-development
description: Coordinate non-trivial development when the user requests subagent-driven, multi-model, or rescue-assisted work. Adapt implementers and independent reviewers to current access and task needs, and own verification through the authorized delivery boundary.
---

# Collaborative Development

Keep responsibilities and evidence stable; choose participants for this run.
The coordinator owns the outcome, including reconciling reviews and finishing
the authorized work. Model agreement alone is not acceptance.

## Compose existing workflows

Follow the current user's scope and the repository's active instruction chain.
Register an issue when its workflow requires one. Reuse available Superpowers
skills for planning, subagent-driven implementation, spec/quality review, and
verification. Load the relevant skill at its phase; do not copy or modify its
implementation here. If unavailable, use the host's supported equivalents and
state the substitution. This skill is coordination policy, not an agent runtime.

For interaction changes, use the applicable task walkthrough/platform review
and complementary visual or accessibility review. Follow project guides for
CLI/API parity, packaging, installation and cleanup. Scale review depth to risk;
trivial edits and standalone review requests do not need this whole workflow.

## Choose the participants

Start from the user's current provider constraints, available tools and task
needs. Subscription/access changes affect this run, not permanent skill policy.
Use actual installed provider skills and verified CLI help; do not invent
commands or map a named rescue route to a different backend silently.

Check roster/authentication without inference first. When access is uncertain,
use a bounded minimal invocation to confirm it. A listed model is not proof of
quota, file access, execution tools or review completion. An unknown job state
requires status/result inspection before another launch. Diagnose repeated
failure rather than multiplying jobs or relaxing permissions.

Assign coordinator, implementation, spec/quality and independent-review roles
according to capability. No provider, model or reviewer count is fixed. Prefer
complementary perspectives when useful and available; a previously used pair
is not a quorum. If an optional provider fails, use an authorized available
alternative, retain independent context, and disclose the changed coverage.
Do not substitute when the user explicitly requires that provider. A coordinator's
own reread is not an independent review; report that gap if no reviewer can run.

## Execute and review

Use the [dispatch and evidence packet](references/review-packet.md) when handing
off work. Keep native agent IDs and external rescue job IDs distinct in the
task record. Track role, owned scope, state and result. Reuse a worker for its
bounded correction, but use fresh context for an independent final assessment.

Follow the chosen implementation workflow's concurrency rules. Under Superpowers
SDD, implement one task at a time. Parallelize independent investigations/reviews;
other execution workflows may parallelize implementation only with explicit
dependency and file ownership boundaries. Shared registries, docs and integration
belong to the coordinator. Independent worktrees do not remove logical dependencies.
Fit active jobs to available capacity and collect terminal results before cleanup.

| Checkpoint | Decision it supports |
|---|---|
| Design/spec | Are the outcome, boundaries, acceptance evidence and affected interfaces sufficient? |
| Material implementation decision | Are changed contracts, state transitions or integration assumptions sound before dependents continue? |
| Final candidate | Does the complete implementation satisfy the accepted contract at the recorded revision? |

Keep spec compliance and code quality review distinct when using SDD. Intermediate
reviews need a decision to resolve, not a call per commit. Final reviewers get
the requirements and raw source/evidence before author conclusions or other
reviewers' verdicts. Start the final assessment fresh; after correction, resuming
that reviewer is useful but is labeled a re-review, not another independent vote.

## Resolve findings and cover the delivered revision

For each actionable finding, establish its trigger, source mechanism, user impact
and supporting evidence. Reproduce runtime claims where feasible. If reproduction
fails, distinguish a demonstrated source/state-machine gap from an unobserved
environmental trigger. Adjust the severity or reject the claim with reasons.
Multiple agreeing models still need evidence. Do not change an accepted user
requirement merely to obtain reviewer agreement; raise a concrete conflict when
it cannot be resolved within scope.

Record the reviewed base/head (or exact patch identity). After a correction,
compare the delivered candidate against that coverage: behavior changes need
focused re-review and relevant validation; broad changes need a fresh wider pass.
Explain any comment/docs-only coverage decision. Passing CI does not extend an
old review to new code. Publish actual review identities and limits, not an
invented human approval or claims of tests a reviewer did not execute.

## Accept and finish

The coordinator verifies requirements and the relevant integrated tests/build,
plus actual UI or installed-artifact behavior where the claim depends on it.
Separate reviewer analysis, observed command output, browser replay and native
validation. A blocked observation is not a passed check or automatically a product
defect. Follow the current authorization through PR, merge, release or local
installation as applicable: neither this skill nor `/goal` grants those actions.
Honor a PR-only stopping point; do not force a PR where the project does not need
one. Create a persistent goal only when requested and supported by the host.

Do not ask again for already-authorized routine continuation. When a required
gate cannot be completed, report the exact missing evidence or decision. Finish
with the delivered revision, validation scope, remaining limits and disposition
of task-owned jobs, fixtures and worktrees. Preserve unrelated work and restore
user state according to project guidance; report teardown that remains unverified.

## Basis and boundaries

Harvest gate: existing skills covered component workflows but not interchangeable
participant selection and cross-stage review coverage. The owner requested reuse
after [Wunderkammer #163](https://github.com/WoojinAhn/wunderkammer/pull/163), where
independent review led to reproduced corrections and a final re-review. This
companion preserves that coordination gap; product-specific QA stays in project
guides. It does not rank models, manage subscriptions or replace Superpowers.

Avoid fixed model rosters, forced parallelism, consensus-as-proof, successful-job
status as proof of complete coverage, and automatic delivery beyond authorization.
