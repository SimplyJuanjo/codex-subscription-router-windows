# Profile-menu actions, 2026-09-14

## Root causes

`Rename subscription` called `window.prompt`, unsupported by the Electron
renderer. It now opens an inline labelled input with Save and Cancel; Enter
submits and Escape cancels without menu typeahead intercepting text. The
authenticated PATCH stays account-scoped, including Primary. Failure preserves
the draft, and a synchronous guard prevents duplicate submissions.

`Usage remaining` mapped the historical opener to `Dp` in desktop
`26.908.40834`. That import now resolves to the native product-event logger
(`Vy`), which does not open a dialog. The real native profile action uses `ud`
(export `Pmt`, implementation `sL`), updating the modal store. The patcher now
derives this binding from the native usage action and rejects absent/ambiguous
matches. The native reset module is initialized explicitly.

The native usage/reset panel and its confirmation behavior remain intact.
Credit reads and redemption are scoped to the selected account; successful
redemption refreshes both the native query and the subscription selector counts.
No real reset credits were consumed during validation.

## Validation

- UI interaction tests click Rename and Usage, type/save/cancel, check Primary
  and secondary isolation, duplicate submission, API failure and keyboard events.
- The packed-ASAR test executes the real native modal-store opener, checks that
  the old analytics binding opens nothing, invokes the lazy modal wrapper and
  exercises renamed-account and reset requests with a synthetic HTTP boundary.
- The patched native reset query/mutation are executed to verify that an
  in-flight redemption keeps its captured account even if the selection changes.
- Control tests exercise authenticated renaming and reset reads/redemption with
  explicit previews for both accounts. No live credentials or billing are used.

## Deployment caution

The earlier latest-request update was prepared but did not activate: the
2026-09-14 13:53 activation log reports a Windows sharing violation while moving
the installation. The current package still had the previous mux/ASAR hashes.
This menu correction includes that latest-request feature as well.

Do not report activation merely from a successful build or queued helper.
Check the installed manifest and process paths after voluntary shutdown. The
local menu-fix helper rechecks processes immediately before swapping and retries
sharing violations only after preserving/restoring both installations. It never
kills a process. Keep the old build as a recoverable backup.

Final validation passed: 45 UI tests, 104 Windows Python tests, Go suite and vet,
packed native click/reset contracts and all 53 staged-build verifier checks.
Two timing-sensitive Go tests initially exceeded their deadlines; both passed
an isolated rerun and the subsequent full serial suite. No timeouts were relaxed.

Prepared build: `%LOCALAPPDATA%/Programs/Codex Subscription Router Update MenuFix`.
Mux SHA-256: `8325629f5540425c4c8f95c481c5cec750ee9fd3a0e6b17305d24d1e63ead0db`.
ASAR SHA-256: `f2b637cf8227ad6686ea96a086263cd03c753194178a3632cb1ec08ec7d5eb27`.
Local ignored helper: `artifacts/Apply-Pending-MenuFix.ps1`; `-ValidateOnly`
checks identity/hashes/paths/ACLs without activation. It uses same-volume
`Directory.Move`, avoiding PowerShell's potential child-by-child move fallback.
Injected sharing failures in each move position were tested for complete
rollback, manifest restoration, and successful retry with the previous build
preserved. These are deployment-fixture tests, not a forced production failure.

One-shot task: `CodexRouter-Activate-MenuFix-20260914`, with no recurring trigger
and a 30-minute voluntary-exit wait. Log:
`%LOCALAPPDATA%/Programs/Codex Subscription Router Data/logs/activate-menu-fix.log`.
The old LastRequest helper is superseded and must not be restarted.
