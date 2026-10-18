# Dispatch and evidence packet

Use only fields needed for the task. Keep the packet in the existing task record
or ignored evidence area; no new tracking service is required. Record participants
for this run rather than saving subscription state as global policy.

## Before dispatch

- Role and decision: implementation, spec compliance, quality, design or final
  review; the concrete question the result must resolve.
- User outcome, accepted constraints, relevant issue/spec and current instruction
  sources. Follow the repository's declared authority, not a hard-coded filename.
- Exact repository/worktree and base/head or patch identity; include the relevant
  plan task text for an SDD implementer rather than sending it to discover the plan.
- Owned and forbidden files, dependencies, permitted actions and delivery boundary.
  Shared README, instructions, API docs and registries stay coordinator-owned.
- Needed capability: source reads, execution, network or native/browser input.
  Discover what the selected route actually supports; review/read-only mode is not
  a portable guarantee of shell/network access or OS isolation.
- Small raw evidence set: exact diff, relevant source, command output, build
  identity and synthetic UI examples. Place the packet inside the authorized
  workspace when outside reads are unavailable. A missing read must be reported;
  neither a bare "hello" nor a model self-report proves repository access.

Do not feed independent reviewers the author's preferred verdict, prior reviews
or implementation-session history. Include known requirements and factual test
limits without claiming a blind human study. A correction re-review may include
the prior findings and their dispositions.

## Result to collect

```text
Role / route / native-agent or external-job ID:
Requested model / reported model (unknown if unavailable):
Terminal state and reviewed revision or patch:
Files and evidence inspected; failed or omitted reads:
Findings: trigger -> mechanism -> impact -> evidence -> proposed correction
Checks personally run, with results:
Supplied results or source-only inferences, clearly separated:
Remaining uncertainty and next decision:
```

Inspect the result and relevant raw receipts before counting coverage. An exit
code or provider's completed status does not prove that source was read or a
requested test was run. Do not infer an actual model solely from generated prose.

## Coordinator disposition

Keep one compact record per finding: source reviewer, claimed severity,
confirmed/inferred/unreproduced/refuted status, evidence, action and correction
revision. A rejected suggestion needs a reason; unrelated findings follow the
project's out-of-scope policy rather than expanding the implementation.

For each final review, connect the covered revision with any subsequent delta
review. New source changes reopen the affected coverage; unchanged, already
validated scope does not need ritual full replays. Keep public summaries concise
and sanitized. Raw local paths, access tokens and personal content stay private.

Use the repository's normal GitHub/API/CLI route to post authorized review records.
Attribute agent-produced comments honestly and retain their verification limits;
do not impersonate a human reviewer or bypass host self-review restrictions.
