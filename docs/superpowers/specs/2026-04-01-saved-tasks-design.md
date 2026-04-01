# Saved Tasks Design

Date: 2026-04-01
Status: Approved for planning

## Summary

Introduce a shared Saved Tasks system that lets users pause, park, restore, and delete unfinished work across the app. The initial implementation should provide a unified product experience for Convert, Trim, Match, Rename, Download, and similar batch-oriented tools, while allowing each tool to keep its own runtime engine and persistence details.

The highest-priority workflow is Convert. If the app closes unexpectedly or the user chooses to put a running conversion batch aside, reopening the task should preserve completed files, remember queue order and settings, and restart the interrupted file from the beginning. The system should also provide a fallback "skip already processed files" option that detects expected outputs and marks those items as already done.

## Goals

- Preserve meaningful progress when the app closes unexpectedly.
- Let users intentionally pause or put a task aside, do something else, and resume later.
- Provide one Saved Tasks surface for multiple tools instead of separate recovery experiences.
- Give clear per-item visual feedback for pending, running, completed, skipped, failed, and incomplete items.
- Support editable queues for batch-oriented tools, starting with Convert.

## Non-Goals

- True mid-file FFmpeg resume. Interrupted conversions restart the current file from the beginning.
- Rewriting every tool to share a single runtime engine.
- Automatic validation based on source and output file size equality.
- Full cross-tool parity in the first implementation. Convert is the first complete adapter.

## Current Context

The current codebase already contains useful building blocks:

- Downloads have crash recovery via `SessionService`, `SessionRepository`, and `CrashRecoveryService`.
- Convert has persisted `ConversionJob` records and a `ConversionManager`, but no recoverable task/session model.
- Trim already persists user work through `QuickSessionStore` and `ProjectStore`.

These existing patterns suggest a shared Saved Tasks shell with per-tool adapters, rather than a full rewrite into one universal queue engine.

## User Experience

### Saved Tasks Entry Points

The app should expose Saved Tasks in two places:

- Startup recovery prompt: when the app launches and an unfinished task exists, prompt the user to restore the most recent unfinished task.
- Saved Tasks list: a persistent list where users can manually open, inspect, pause, resume, or delete parked tasks at any time.

The startup prompt and Saved Tasks list both point to the same underlying records. The prompt is a convenience, not a separate recovery system.

### Task Lifecycle

Each task has a lifecycle status:

- `active`
- `paused`
- `completed`
- `failed`
- `cancelled` or `deleted` as terminal states if needed by the UI model

For a running batch, `Pause / Put Aside` should:

- cancel the active worker immediately
- mark the currently processing item as `incomplete`
- persist the remaining queue and per-item state
- move the task back to the Saved Tasks list

On resume, the task continues with:

- all `completed` items preserved
- all `skipped` items preserved
- the interrupted `incomplete` item restarted from the beginning
- remaining `pending` items processed in saved queue order

### Convert Queue UX

Convert should move from a plain file list plus transient job list to a queue model with visible per-item state. Each file row should support:

- pending
- processing
- completed
- skipped
- failed
- incomplete

Completed items should use strong visual confirmation such as green styling and/or a check icon. Failed and incomplete items should remain visible for review instead of disappearing into logs.

Queue controls for Convert v1:

- reorder items
- skip a selected item without deleting task history
- force-start a selected item next
- pause the whole task
- resume a saved task
- delete the saved task record

## Architecture

### Shared Saved Task Record

Add a new persistence layer for user-facing saved work. Each record should include:

- task id
- task type, for example `convert`, `trim`, `match`, `rename`, `download`
- display title
- lifecycle status
- created and updated timestamps
- summary counts for UI display
- tool-specific payload blob

The shared record is responsible for discovery, listing, filtering, and lifecycle management. It should not force all tools to share the same detailed schema internally.

### Per-Tool Adapter Boundary

Each tool integrates through a small adapter contract:

- serialize the current task state into a payload
- restore a task payload back into UI state and runtime state
- provide a short summary for the Saved Tasks list
- update persisted task state as runtime progress changes

This keeps tool-specific logic near the existing page/manager code and avoids over-generalizing runtime behavior.

### Convert Adapter

The Convert adapter payload should include:

- source file entries, including nullable source-root metadata for folder-based imports
- saved queue order
- output settings and destination folder
- per-item state
- derived output path per item
- active item identity, if any
- summary counts

The runtime conversion flow remains in `ConversionManager` and `FFmpegWorker`, but it should write state transitions into the saved-task store so crash recovery, manual pause, and manual resume all use the same persisted source of truth.

### Trim Adapter

Trim should integrate by wrapping the existing quick-session and project/session concepts instead of replacing them. The first Saved Tasks integration for Trim can store references to the existing persisted trim session/project data and use that to reopen the page in the correct state.

### Download Adapter

Download recovery already exists. The shared Saved Tasks system should eventually become the user-facing shell around this functionality, but the initial migration can defer deeper internal refactoring.

## Data Model

### Shared Task Fields

Proposed shared fields:

- `id`
- `task_type`
- `title`
- `status`
- `summary_json`
- `payload_json`
- `created_at`
- `updated_at`

### Convert Queue Item Fields

Each persisted Convert queue item should include:

- stable item id
- input path
- display name
- source root, if present
- output path
- item status
- last known progress percent
- error message, if any
- ordering key or position
- timestamps for completion or last update when useful

The Convert item model should be durable enough to survive crashes and restarts without relying on transient list-widget state.

## Processed-File Detection

The fallback "Skip already processed files?" option should work even without an existing saved task.

For v1, the detection strategy should be:

1. Compute the expected output path using the app's existing conversion naming logic.
2. If the expected output file exists and is non-zero size, treat it as an already processed candidate.
3. When metadata is already available, optionally verify that output duration is close enough to the source duration before auto-marking it complete.

Do not compare source and output file size as a primary signal. Conversion and trimming often change output size legitimately.

Detected matches should be marked in the queue UI as already processed and skipped automatically during execution.

## Error Handling

- If persisted state is partial or stale, restore the task in a safe state instead of blocking restore entirely.
- Unknown or unverifiable items should fall back to `pending` or `incomplete`, not `completed`.
- Missing input files should remain in the queue with a clear failure or missing-source status.
- If the active item was interrupted by crash or pause, it must never be assumed complete.
- Restore logic should be resilient to config drift or moved output folders and should surface a clear message when user action is required.

## Testing Strategy

Add focused tests for:

- pause/put-aside marking the current Convert item incomplete
- resume preserving completed Convert items and restarting the interrupted item
- crash recovery restoring unfinished Convert tasks from persisted state
- processed-file detection marking expected outputs as already processed
- queue reorder, skip, and force-start persistence
- startup prompt and manual restore from the Saved Tasks list
- Trim adapter reopening an existing saved trim session through the shared task layer

UI tests should focus on visible state transitions and recovery actions. Persistence tests should verify durable queue reconstruction independent of widget state.

## Rollout Plan

### Phase 1

Create the shared Saved Tasks persistence model and Saved Tasks list UI.

### Phase 2

Integrate Convert fully:

- persisted queue model
- pause and put-aside
- crash recovery
- per-item visual statuses
- processed-file detection
- editable queue actions

### Phase 3

Integrate Trim using the existing project and quick-session persistence.

### Phase 4

Extend the shared shell to Match, Rename, Download, and other batch workflows.

## Open Decisions Resolved In This Design

- Primary direction: one unified Saved Tasks system from the start.
- Startup behavior: both a restore prompt and a manual Saved Tasks list.
- Pause behavior: immediate stop, with the active file restarted from the beginning on resume.
- Recommended architecture: shared task shell plus per-tool adapters, not a universal runtime engine.

## Implementation Notes For Planning

- Prefer reusing existing repositories and session patterns where possible.
- Do not store queue state only in widgets.
- Keep runtime execution and persisted task metadata separate, with explicit synchronization points.
- Convert is the first complete implementation and should define reusable patterns for later adapters.
