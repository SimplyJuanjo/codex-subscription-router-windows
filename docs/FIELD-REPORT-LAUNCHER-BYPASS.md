# Field report: long staging paths and launcher bypass

Observed on a second Windows 11 x64 machine (not the maintainer's) between
2026-09-13 and 2026-09-17. Store package `26.908.4834.0`, router installed from
`7eaf2e9` with the default destination and state root, control port `61289`,
`LongPathsEnabled = 0`. Nothing here was reproduced on a clean VM.

This file records one fix included in the same change and two open issues that
still need a maintainer decision.

## 1. Fixed here: staging copy exceeds `MAX_PATH`

`patch_windows_app.py` created its staging directory as
`codex-subscription-router-staging-XXXXXXXX` next to the destination. With the
default destination under `%LOCALAPPDATA%\Programs`, the 26.908 payload has
relative paths of up to 168 characters, all under
`resources\cua_node\...\classic-level\deps\leveldb\...`.

| Location | Longest resulting path |
| --- | --- |
| Final destination | 231 |
| Staging with the old prefix | 274 |
| Staging with `csr-stg-` | 250 |

Figures are for a five-character Windows user name. With the old prefix,
`shutil.copytree` failed for 111 files with `[WinError 3] The system cannot
find the path specified`, in both `--dry-run` and a real install, so the router
could not be installed at all. The final destination was never the problem.

The prefix is now `csr-stg-`. It still does not start with a dot, which the
existing comment requires for `@electron/asar` unpack matching. A user name
longer than roughly 14 characters would still overflow; a preflight check of the
longest projected staging path, or a documented `LongPathsEnabled` requirement,
would close that gap properly.

## 2. Open: Windows relaunches `ChatGPT.real.exe` without the launcher

Symptom: the profile menu shows `Failed to fetch (127.0.0.1:61289)` and
`0 connected subscriptions`. Chats still work, through the primary account only.

Evidence from the affected session:

- Two top-level `ChatGPT.real.exe` processes, parent `explorer.exe`, started
  about two minutes after sign-in. No `ChatGPT.exe` launcher process existed.
- Both command lines ended with `--restore-last-session --restart`. One carried
  `--user-data-dir=<state root>\Profile`; the other had no user data directory.
- Each spawned its own `resources\codex.exe`, but nothing listened on the
  control port, because the launcher never supplied `CODEX_MUX_CONTROL_PORT`
  and the control token.
- No `Run` key, Startup folder item or scheduled task referenced the router.

This matches Chromium registering the process for application restart, and
Windows reopening registered apps at sign-in using the process's own image
path. That path is `ChatGPT.real.exe`, so the launcher is bypassed after every
reboot or sign-out while the router was open.

Closing the window does not end the session: the app stays alive in the
background, so reopening it through the correct shortcut only focuses the broken
instance. All router processes had to be stopped before starting `ChatGPT.exe`.

Possible directions, not evaluated:

- Have `ChatGPT.real.exe` detect a missing launcher environment at startup and
  re-execute `ChatGPT.exe` instead of continuing.
- Unregister application restart for the patched copy, or register the launcher
  path as the restart command.
- Have the doctor script flag "router processes present, launcher absent,
  control port closed" as a named condition.

## 3. Open: the Start Menu shortcut is retargeted to `ChatGPT.real.exe`

The installer wrote `Codex Subscription Router.lnk` with the launcher as target
and the router AppUserModelID. On 2026-09-14 and again on 2026-09-15, after
being repaired by hand, the shortcut's target had become `ChatGPT.real.exe`.
The modification times fall a few minutes after a router instance started.

- Desktop and taskbar-pinned shortcuts with the same target and AppUserModelID
  were not modified.
- The patched `app.asar` contains no `writeShortcutLink`,
  `setLoginItemSettings` or `openAtLogin` call, and its only `Start Menu`
  references are read-only application detection. The rewrite most likely comes
  from native Chromium shortcut maintenance keyed on the AppUserModelID. This
  was not confirmed.

Launching from the rewritten shortcut produces the same symptom as issue 2.

## 4. Open: ACL hardening fails under Windows PowerShell 5.1 on long paths

Seen on 2026-09-23 while updating the same machine from the 26.908 build to
26.917 with `install_windows.ps1 -Force`. The build, patch and verification
steps succeeded; the step `Hardening private router payload and state ACLs`
then failed twice with `Could not find a part of the path`, and the automatic
rollback restored the previous build each time.

`Set-CsrPrivateDirectoryAcl` and `Assert-CsrPrivateDirectoryAcl` enumerate the
whole state root and backup root with `Get-ChildItem -Recurse`. Windows
PowerShell 5.1 cannot open paths longer than 260 characters even with
`LongPathsEnabled`, and two trees under those roots exceed it:

| Tree | Longest path | Count over 260 |
| --- | --- | --- |
| `Data\accounts\<id>\codex-home\.tmp\plugins` (Codex bundled-plugin cache, one per account) | 289 | 101 per account |
| `.codex-subscription-router-backups\<stamp>\Codex Subscription Router\resources\cua_node\...` | about 290 | 111 |

The first tree is regenerated by Codex; the second is created by the installer
itself when it moves the previous build aside, so on this machine every update
fails while a backup is retained. A failed attempt also leaves the new build
under `Data\failed-installations\<stamp>`, which contains the same long paths
and makes the next attempt fail the same way until it is deleted with
long-path-aware tooling.

Running the same command under PowerShell 7.6.6 (portable, unsigned MSI not
needed) completed the update and all 53 verifier checks. PowerShell 7 supports
long paths in `Get-ChildItem`, `Get-Acl` and
`[IO.FileSystemAclExtensions]::SetAccessControl`. Options: require PowerShell 7
in the installer's prerequisite check instead of allowing 5.1, or enumerate
with `\\?\`-prefixed paths and skip `.tmp` caches and the backup root during
hardening.

## Workaround used on the affected machine

A local script, not part of this repository, stops every process whose image
path is under the router destination and then starts `ChatGPT.exe`. It asks for
confirmation first, since it interrupts running work.
