# Sessions

## 2026-03-25 — codex:2026-03-25:agents-consolidation

- Reviewed repository markdown guidance, excluding the requested audit and redesign docs.
- Rewrote `AGENTS.md` as the complete agent-facing source of truth for setup, commands, architecture, invariants, troubleshooting, and shared-state maintenance.
- Reduced `CLAUDE.md` and `.github/copilot-instructions.md` to pointer documents so agent guidance is no longer duplicated across files.

## 2026-03-17 — auth-cookie retry

- Investigated the Playwright auth flow where logging in and closing the browser still left the Download tab blocked on "needs auth".
- Confirmed the persistent Chromium profile contained Instagram cookies in `data/browser_profiles/global/Default/Cookies` even when `data/cookies/playwright_cookies.txt` was missing.
- Added retry-based cookie export validation in `src/core/auth_worker.py` so login finalization tolerates short delays between browser shutdown and cookie persistence/export visibility.
- Added `tests/test_auth_worker.py` to cover the delayed-cookie-success case and kept the existing Netscape/domain tests passing.
- Verification: `pytest -q tests/test_auth_worker.py tests/test_auth_domain_suffix.py tests/test_netscape_cookies.py` and `pytest -q` both passed.
- Remaining: user should retry the auth flow in the app to confirm the blocker clears after login on a live site.

## 2026-03-17 — branch-history update

- Replaced `main` with the former `pyqt6` history after confirming the branches had unrelated roots.
- Preserved the previous `main` tip on backup branch `codex/main-backup-2026-03-17` and pushed it to origin.
- Force-pushed `main` to commit `1dd6af7` (`pyqt6` / `codex/claude-ui-refactor-signal-plan` tip).
- Verified `origin/codex/claude-ui-refactor-signal-plan` is now identical to `origin/main`, so no PR is needed for that branch.
- Opened draft PR #1 for `codex/Fix-playwright-auth` into `main`: https://github.com/Helwdyna/ytdlp-gui/pull/1
- Remaining work: clean up the `codex/Fix-playwright-auth` branch before merge, especially stray artifacts like `pytest-of-pb/`, `urls.txt`, and generated metadata files if they are not intended.

## 2026-03-18 — PR 4 review fixes

- Reviewed PR #4 with `gh` and verified each requested finding against the current code before changing anything.
- Updated Playwright CLI docs to remove unsupported `--debug=cli` / `playwright-cli attach` guidance and to use the supported `--debug` Inspector flow or `PWDEBUG=console` with `await page.pause()`.
- Normalized Playwright video docs to the positional `playwright-cli video-stop <filename>` form based on the local skill reference, and kept the recordings examples consistent.
- Confirmed the runtime shell code already preserves the stable public stage keys `ingest`, `prepare`, `organize`, and `export`; updated the UI redesign plan doc so it no longer proposes deleting that contract.
- Aligned the accessibility audit with its stated WCAG 2.1 AA scope by reclassifying the trim target-size item as AAA/advisory, and fixed `GUI_FIX_PROMPT.md` wording/code fences for markdownlint and explicit LIGHT_TOKENS AA contrast verification.
- Fixed `EmptyStateWidget` so the icon label hides when no icon text is present.
- Fixed stale UI state when folders change in Match, Rename, and Sort by clearing old results/previews/scan-derived state instead of leaving the previous folder's data active.
- Follow-up PR #4 fixes: `RenamePreviewTable` now clears its cached checked/conflict state when the preview is invalidated, `RenameTabWidget.set_enabled()` now disables the source path edit along with browse/scan controls, `SortTabWidget.set_enabled()` now disables scanning through `SourceFolderBar`, and Task 18 in the redesign plan now explicitly preserves `stage_definitions.py`.
- Moved raw ffprobe JSON delivery onto the existing background worker path by extending `FFprobeWorker` with a `raw_metadata_ready` signal and wiring `MetadataViewerTabWidget` to consume it, removing the blocking GUI-thread subprocess loop.
- Polished the repetitive directory bullets in `.github/copilot-instructions.md`.
- Verification: `python3 -m compileall` passed for the touched Python files; `pytest -q tests/test_shell.py` passed; `pytest -q tests/test_theme_tokens.py tests/test_qss_builder.py tests/test_icons.py` passed.
- Remaining: `tests/test_main_window_workbench.py` crashes with a PyQt/Python 3.14 bus error during teardown in this environment, so that full UI verification still needs follow-up.
