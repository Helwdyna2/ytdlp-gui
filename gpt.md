# Codex Instructions

## Documentation Lookup

Use the "Find Docs" skill to utilize Context7 (Ctx7) when searching for documentation about ANY library. Always perform this search when relevant to verify assumptions before implementation.

When working with any external library (PyQt6, yt-dlp, FFmpeg, mpv, etc.), **search for current documentation before implementing**. Do not rely on training data for API signatures, config options, or version-specific behavior — verify against the latest docs. If a lookup produces important findings (breaking changes, undocumented quirks, correct API patterns), record them in `MEMORY.md` under a dated heading.

## Session Tracking

Maintain two files at the repo root throughout every session:

### `SESSION.md` — Append-only session log

Add a dated entry at the end of each session summarizing what was done, what changed, and any decisions made. Format:

```markdown
## YYYY-MM-DD — Brief title

- What was accomplished
- Key files touched
- Open questions or known issues left behind
```

Do not overwrite previous entries. This is a growing history.

### `MEMORY.md` — Persistent knowledge base

Record durable findings that future sessions should know about: API quirks, architecture decisions, gotchas, workarounds, things that didn't work and why. Organize by topic, not by date. Update existing sections rather than appending duplicates.

`MEMORY.md` is the scratch pad; `AGENTS.md` is the canonical, structured output. Anything in MEMORY.md that is generally useful should eventually graduate into AGENTS.md (see next section).

## Updating AGENTS.md

`AGENTS.md` is the single source of truth that all coding agents read when they enter this repo. It must stay accurate as the project evolves. Treat `MEMORY.md` as the staging area and `AGENTS.md` as the published reference.

### When to update

Regenerate or revise `AGENTS.md` when any of the following happen during a session:

- A new module, directory, or entry point is added or removed.
- Build, test, or dev commands change (new scripts, renamed targets, added flags).
- A dependency is added or removed from `requirements*.txt`.
- An architectural decision changes module boundaries, signal flow, or data paths.
- A recurring gotcha or workaround is recorded in `MEMORY.md` that other agents would hit.
- Coding conventions are established or changed (new linter, formatter, naming rule).
- You notice `AGENTS.md` contradicts the current state of the codebase.

If none of these triggers fired, do not touch `AGENTS.md` — avoid churn.

### How to update

1. **Audit the current file.** Read `AGENTS.md` top to bottom. Identify sections that are stale, missing, or contradicted by changes made this session.

2. **Harvest from `MEMORY.md`.** Review every entry in `MEMORY.md`. Anything that is:
   - **Project-wide** (not session-specific or one-off debugging)
   - **Durable** (will still matter next month)
   - **Actionable** (tells an agent what to do or avoid)

   …should be incorporated into the appropriate `AGENTS.md` section. After promoting an item, leave it in `MEMORY.md` but mark it `(promoted to AGENTS.md)` so it is not re-promoted.

3. **Rewrite, don't append.** `AGENTS.md` is not a log. Merge new information into existing sections. Remove content that is no longer true. Keep it concise — every sentence should earn its place.

4. **Follow the structure.** Maintain these sections (add new ones only when clearly needed):
   - Project overview & module organization
   - Environment setup & dev commands
   - Build, test, and validation commands
   - Coding style & naming conventions
   - Architecture constraints & gotchas
   - Testing guidelines
   - Commit & PR guidelines

5. **Validate.** After editing, verify that every command in `AGENTS.md` still works:
   ```bash
   # Spot-check: do the documented commands parse and run?
   python -m py_compile src/main.py
   pytest --co -q  # collect tests without running, confirms test infra is sane
   ```

6. **Commit separately.** AGENTS.md changes go in their own commit:
   ```
   docs: update AGENTS.md — <what changed>
   ```

### What not to put in AGENTS.md

- Session-specific notes (those belong in `SESSION.md`).
- Temporary workarounds with a known fix date (keep in `MEMORY.md` until resolved).
- Prose explanations of how code works — link to the source file and line instead.
- Anything already enforced by tooling config (e.g., linter rules that are in a config file).

## Git Workflow

1. **Branch first.** Before making any changes, create and checkout a new branch:
   ```bash
   git checkout -b codex/<short-description>
   ```
   Never commit directly to `main`.

2. **Commit messages.** Use conventional format:
   ```
   feat(area): add new capability
   fix(area): correct specific bug
   refactor(area): restructure without behavior change
   test(area): add or update tests
   docs: update documentation
   ```
   Keep the summary line under 72 characters. Add a body if the "why" isn't obvious.

3. **Commit often.** Make small, logical commits as you complete units of work — not one giant commit at the end.

4. **Push when done.** At the end of a session, push your branch:
   ```bash
   git push -u origin HEAD
   ```

5. **Update session files last.** After all code changes are committed, update `SESSION.md`, `MEMORY.md`, and `AGENTS.md` (if triggered), then make a final commit:
   ```
   docs: update session log, memory, and AGENTS.md
   ```

