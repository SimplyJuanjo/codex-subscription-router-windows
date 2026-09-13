# Windows update qualification: 26.908.4834.0

Checked on 2026-09-13. The installed Store package is `26.908.4834.0`, inner
desktop `26.908.40834`, build `8881`, bundled CLI `0.154.0-alpha.6.2`.
The production update manifest advertised `26.908.4561.0`; the stable MSIX
download metadata advertised `26.903.8094.0`. Neither is newer than the locally
installed, signature-verified package. Do not downgrade to either download.

Update feed used by the official app:
<https://persistent.oaistatic.com/codex-app-prod/windows-store-update.json>
Official Windows deployment guidance:
<https://learn.chatgpt.com/docs/enterprise/windows-deployment>

## Changes and validation

- Exact source version, build and payload hashes registered in the patcher.
- Native runtime/cache, Chrome native-host isolation and verifier profiles adapted.
- Profile menu, reset sheet, profile query and thread-summary bindings adapted.
  The old usage SVG now needs explicit lazy initialization. The native menu
  still supports the old `LeftIcon` API despite using assets in its own rows.
- Appshots stays opt-in, and does not override upstream feature availability.
- Original signed desktop, CLI and native components remain byte-for-byte intact.
- Go tests and vet, 34 UI tests, packed-menu rendering with a negative control,
  seven patched-bundle syntax checks and auxiliary app-server initialize passed.
- Full Windows build verifier passed all 53 checks after adding the exact 26.908
  native-host isolation profile. No validation gate was disabled.
- Real voice audio/sideband and interactive Computer Use on this version have
  not been qualified. Offline checks do not certify those end-to-end workflows.

## Deployment state

At preparation time the running router was `26.903.9818.0`. The previous
activation log confirms that the September 11 upgrade completed successfully.

New build prepared under
`%LOCALAPPDATA%/Programs/Codex Subscription Router Update 26908`.
Existing accounts, state root and control port are preserved.

Local activation helper: `artifacts/Apply-Pending-26908.ps1` (ignored, not part of
the public source distribution). `-ValidateOnly` validates paths, version,
account-state location, private ACLs and hashes without activation. Normal mode
waits at most 30 minutes for all router processes to exit; never kills processes.
It uses the installer mutex, revalidates the build, updates destination metadata,
moves the previous installation to a recoverable backup and reopens the launcher.
Directory-swap failure restores the previous installation and staged manifest.

Activation log: `%LOCALAPPDATA%/Programs/Codex Subscription Router Data/logs/activate-26908.log`.
Check that log, the final build manifest and running process paths before saying
the new desktop is active. A prepared build or a queued task is not activation.

Final prepared mux SHA-256:
`9fa8b772a0da4fb5ed68c675fe11063a9358d431c37e8db843c3bca4586f2376`.
Final patched ASAR SHA-256:
`c7992d3695afb141f41cdb06aa1568ada3798d3660d9aecdd914920114a16487`.

One-shot local Task Scheduler action `CodexRouter-Activate-26908-20260913` was
started after validation, as the current interactive user with limited privilege
and no recurring trigger. It waits for voluntary router shutdown for 30 minutes.
Do not start a duplicate helper. The full 100-test Windows suite and all seven
26.908-specific tests passed (three were added after the full-suite run).

Activation confirmed on 2026-09-13 at 16:31 (local time): the task returned 0,
the log recorded the successful swap, and the running launcher/desktop processes
started from the final installation. The installed manifest declares
`26.908.4834.0`; both mux and ASAR hashes match the qualified build above.
