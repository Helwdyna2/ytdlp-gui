# Memory

- 2026-03-17: The workbench uses one shared `window.splitter_sizes` config value across the stage splitter layouts.
- 2026-03-17: Runtime and generated artifacts such as `data/config.json` and `ytdlp_gui.egg-info/` should stay out of git tracking.
- 2026-03-17: Settings navigation is part of the `Export` stage, not a separate top-level destination.
- 2026-03-17: Playwright auth can persist cookies in the Chromium profile before the exported Netscape cookie file is immediately available, so auth validation needs a short retry window after browser close.
- codex:2026-03-25:agents-ssot: `AGENTS.md` is the canonical agent instruction file; `CLAUDE.md` and `.github/copilot-instructions.md` should remain thin pointers instead of duplicated guidance.
## Working Memory

- On 2026-03-17, `main` was force-updated to the former `pyqt6` history. The old `main` was preserved on `codex/main-backup-2026-03-17`.
- `codex/claude-ui-refactor-signal-plan` points at the same commit as the new `main`, so it does not need a PR unless it diverges again.
- Draft PR #1 targets `codex/Fix-playwright-auth` into `main` and still appears to include cleanup artifacts that should be reviewed before merge.
