# Latest-request subscription display

The Environment panel previously read `/v1/thread-account`, which correctly
returns history ownership but is not evidence of inference spending. Ownership
continues to route histories, filesystem state and account-specific integrations.
Do not repurpose it or modify the spend policy to fix a display problem.

The panel now reads authenticated `GET /v1/thread-spending?threadId=...`.
Its `request` is the newest dispatch accepted by the upstream HTTP service for
that exact task. `account` provides that subscription's current label, profile
and quota. The endpoint returns null evidence rather than guessing an owner or
the next Auto candidate. An account removed after use retains its recorded ID
and label, without inventing quota.

## Observation and ordering

- The gateway's `Accepted` hook runs after 2xx headers, before streaming or
  compaction-body processing. Voice setup also records its explicit `Thread-Id`;
  session and parent IDs are not treated as task IDs. Established voice calls
  are not rerouted by this change.
- Acceptance identifies the subscription used for the request. It is not a
  billing receipt or an assertion that a later stream/voice call succeeded.
  Not-sent, rejected and delivery-unknown attempts never replace this evidence.
- Dispatch sequence prevents older requests that receive headers or finish late
  from overwriting newer observations. Each subagent's task is independent.
- `thread-spending-updated` immediately updates the visible identity. A fresh
  authenticated fetch enriches quota/profile; terminal `inference-spent` events
  refresh quota. A 30-second refresh recovers missed events.
- Request cancellation, effect cleanup and refresh generations prevent stale
  responses and task navigation from displaying another task/account's data.
  Fetch failures retain known evidence with an unavailable-updates notice.

## Persistence and rollback

Private `thread-spending/<sha256-of-thread-id>.json` sidecars hold one bounded
record per task, separate from `state.json`, routing preferences and the global
100-record diagnostics ring. Reads validate version, identity, size, JSON fields
and duplicate keys. Reparse/symlink paths are rejected; writes use the existing
private atomic writer. Disk failure does not reject/retry accepted inference:
memory retains the observation and the API reports `persisted: false`.

Only live observations participate in sequence comparisons, since sequences
restart with the gateway. Persisted observations do not prevent a new process's
first request from updating the task. Older versions ignore these sidecars.
No accounts, ownership mappings, routing settings or signed native files change.

## Regression coverage

Go tests cover owner/spender differences, mode changes, Auto updates, late and
concurrent requests, subagent/task isolation, ring-buffer eviction, restart
sequence reset, removed accounts, persistence failures and malformed sidecars.
Gateway tests cover immediate acceptance versus terminal outcomes and rejected,
unsent or uncertain requests. Control tests cover authentication and validation.
UI tests cover live attribution, wrong-account quotas, missed/failed fetches,
navigation and stale responses; the packed-ASAR check renders the actual
26.908-injected component with its native bindings.

## Local qualification, 2026-09-14

Passed: Go suite and vet; race-enabled tests for spend/state/mux/control;
38 UI tests; 103 Windows Python tests; nine release tests; release metadata
check; packed renderer contract; full staged-build verifier (53 checks).
The original signed desktop, CLI and native components remain unchanged.
This validates the implementation and package, not live billing or voice audio.

Prepared for the existing `26.908.4834.0` installation under
`%LOCALAPPDATA%/Programs/Codex Subscription Router Update LastRequest`.
Mux SHA-256: `8325629f5540425c4c8f95c481c5cec750ee9fd3a0e6b17305d24d1e63ead0db`.
ASAR SHA-256: `b7a3c9be86039117f9a65255f75c08374eab77246f49d3878305b158ddc4827f`.

The local ignored helper `artifacts/Apply-Pending-LastRequest.ps1` validates
the exact old/new builds, preserves the old installation, and waits up to
30 minutes for voluntary shutdown. It never stops any process. One-shot task
name: `CodexRouter-Activate-LastRequest-20260914`; no recurring trigger.
Log: `%LOCALAPPDATA%/Programs/Codex Subscription Router Data/logs/activate-last-request.log`.
Verify that log, the installed hashes and `/v1/thread-spending` before claiming
activation. No historical observations are invented or backfilled: tasks with
no accepted request recorded by the updated router show an explicit empty state.

Later check: that activation failed with a Windows sharing violation; the
previous running installation remained active. The feature is now included in
the combined [menu-actions correction](MENU-ACTIONS-FIX.md), which supersedes
the LastRequest helper and has a new qualified ASAR hash and activation task.
