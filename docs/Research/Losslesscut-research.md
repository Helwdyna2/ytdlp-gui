## Executive Summary

LosslessCut is a GPL-2.0-only Electron desktop app built around an Electron main process, a React renderer, and FFmpeg/FFprobe-backed media operations rather than a reusable embeddable SDK.[^1] Its product model is segment-first: users create ordered segments and markers, optionally invert them, manage tracks independently of segments, and then export with a large set of container, metadata, and timestamp options plus warning-driven troubleshooting guidance.[^4][^5][^7][^8][^11] Your app has already implemented the right architectural direction for a LosslessCut-style experience: a dedicated Trim page, an in-memory segment model with labels/tags and enable/disable state, libmpv render-based preview, ffprobe-backed keyframe analysis, project persistence, quick-session autosave, and conservative lossless export warnings.[^12][^13][^14][^16][^17][^18][^20] 

The best integration path is therefore **not** embedding or automating LosslessCut itself, but continuing the current in-app reimplementation and selectively importing its **product behaviors**: markers and invert/skip mode, per-track export control, output-container/remux controls, advanced export options (`avoid_negative_ts`, metadata, chapters, MOV faststart), and only then an opt-in experimental smart-cut path.[^10][^11][^18][^19][^20]

## Architecture / System Overview

### Upstream LosslessCut

```text
┌───────────────────────────────┐
│ Electron main process         │
│ - config store                │
│ - ffmpeg/ffprobe orchestration│
│ - compat preview process      │
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│ React renderer                │
│ - timeline / segments UI      │
│ - tracks / export options UI  │
│ - warnings & smart-cut UI     │
└──────────────┬────────────────┘
               │
       primary │ Chromium playback
      fallback │ FFmpeg→MSE fragmented MP4
               ▼
┌───────────────────────────────┐
│ FFmpeg / FFprobe              │
│ - probing                     │
│ - cutting / concat            │
│ - preview transcoding         │
│ - waveform / scene detect     │
└───────────────────────────────┘
```

LosslessCut’s codebase is explicitly an Electron application: `package.json` declares Electron as the desktop runtime, React as the renderer stack, and platform-specific FFmpeg/FFprobe download/build scripts for macOS, Linux, and Windows.[^1] Preview is fundamentally Chromium-based; when Chromium cannot decode a file, LosslessCut offers “FFmpeg-assisted software decoding playback,” and the implementation streams fragmented MP4 chunks from an FFmpeg child process into a `MediaSource`-backed HTML video element, with a retry path for unsupported colorspaces.[^2][^3] That architecture matters because it means LosslessCut is optimized as a standalone Electron product, not as a native media widget you can drop into a PyQt app.[^1][^3]

### Current app

```text
┌────────────────────────────────────┐
│ PyQt Trim page                     │
│ - load/save project                │
│ - segment list + timeline          │
│ - export warnings + diagnostics    │
└───────────────┬────────────────────┘
                │
      preview   ▼
┌────────────────────────────────────┐
│ libmpv render path                 │
│ - PlaybackController               │
│ - QOpenGLWidget render surface     │
│ - scrub controller                 │
└───────────────┬────────────────────┘
                │
      analysis  ▼
┌────────────────────────────────────┐
│ ffprobe-backed analysis            │
│ - source metadata probe            │
│ - keyframe scan worker             │
└───────────────┬────────────────────┘
                │
      export    ▼
┌────────────────────────────────────┐
│ local export planner / manager     │
│ - separate or merged outputs       │
│ - copy/re-encode choice            │
│ - temp segments + concat for merge │
└────────────────────────────────────┘
```

Your app already chose the correct native equivalent: `PlaybackController` owns a libmpv client/render context, exposes exact vs keyframe seeks, and renders into a `QOpenGLWidget`-backed preview surface instead of relying on Chromium or MediaSource Extensions.[^13][^14] The Trim page wires that preview to an `EditorSession`, ffprobe metadata probing, a background keyframe scan, project load/save, quick-session restore, warning presentation, and an export manager.[^16][^17][^20] The current internal docs accurately describe the feature as “implemented and ready for live validation,” not finished product parity, because desktop runtime validation and packaging confidence are still incomplete.[^12][^21]

## What LosslessCut actually contributes conceptually

### 1. Segment-first editing, not clip-first editing

LosslessCut treats segments as the primary domain object: the documentation calls them “first class citizens,” allows markers by omitting the end time, and uses segment order as export order.[^4] The renderer utilities support creating segments, combining selected or overlapping segments, inverting them into “keep the gaps” mode, converting them into chapter-compatible contiguous ranges, and driving playback behavior such as loop-current-segment or play-selected-segments.[^5] The user-facing contract also includes segment labels, tags, numbering, and file-name-template variables exposed through typed interfaces.[^6]

Your app already mirrors the segment-first part well: `EditorSession` holds ordered `EditorSegment` objects, supports split/delete/select/enable-disable, and persists labels and tags.[^14] The main structural gap is that your `EditorSegment` requires an `end_time: float`, so there is no current marker abstraction and therefore no direct equivalent to LosslessCut’s “marker” or Yin-Yang invert workflow.[^4][^14] If you want closer product parity, **markers + invert mode** are the highest-value model additions because they unlock skip-the-middle editing, marker workflows, and future chapter generation without replacing the rest of your editor architecture.[^4][^5][^14]

### 2. Tracks are a first-class export concern

LosslessCut’s documentation is unusually explicit that tracks are separate from segments, are cut in parallel, and often determine whether an export succeeds; its export dialog warns that some track types are problematic and encourages disabling tracks to isolate failures.[^4][^8][^11] That advice is not theoretical: the troubleshooting guide repeatedly says to disable all nonessential tracks first, because FFmpeg sometimes cannot correctly cut specific tracks, causing wrong durations, black sections, or broken merges.[^11]

The Trim page you have now does **not** expose LosslessCut-style track selection or per-stream export controls in the UI I inspected; its export panel only exposes lossless on/off, export mode, output target, warnings, and the action buttons.[^20] The local exporter likewise does not build explicit `-map` choices or per-track policies; it either copies or re-encodes the whole input for the requested time range and, for merges, concatenates temporary files.[^19] If you want the next biggest parity jump after markers, it is **a tracks panel plus explicit stream mapping**, because upstream troubleshooting shows that track control is one of the main levers users need when lossless cutting misbehaves.[^4][^8][^11][^19]

### 3. Export is mostly a warning-driven decision surface

LosslessCut’s default config enables keyframe cutting, preserves chapters and metadata by default, keeps export confirmation enabled, turns on MOV faststart, and exposes `avoid_negative_ts`, smart cut, keyframe visualization, and many other advanced toggles.[^7] The export-confirm UI turns that state into warnings and recommendations: it warns about problematic thumbnail tracks, smart cut being experimental, output-length drift when no nearby keyframe exists, container-specific advice, and the recommended `avoid_negative_ts` mode for merge vs cut workflows.[^8] The troubleshooting guide then reinforces the same heuristics: try keyframe cut on/off, adjust `avoid_negative_ts`, shift starts a few frames, change container, disable tracks, remux before merge, and treat smart cut as experimental.[^11]

Your app already implements the beginnings of the same pattern. `ExportPlanner` computes warnings for unknown keyframe safety, off-keyframe copy boundaries, and merged-copy drift, and the Trim page presents those warnings before export and optionally requires confirmation.[^18][^20] That is a solid foundation, but it is still much narrower than upstream LosslessCut because the current export panel does not expose container remuxing, metadata/chapters preservation, MOV faststart, track-specific warnings, or different `avoid_negative_ts` strategies; the local lossless exporter always uses `-avoid_negative_ts make_zero`.[^18][^19][^20]

**Recommendation:** treat the current warning system as the anchor and expand outward. The most useful advanced options to add next are:

1. `avoid_negative_ts` modes (`make_zero`, `auto`, `make_non_negative`, `disabled`), because both LosslessCut’s warning UI and troubleshooting docs rely on them heavily.[^8][^11]
2. Container selection/remuxing, because upstream docs repeatedly recommend switching to MOV/MKV/MP4/TS to work around codec/timebase issues.[^4][^11]
3. Metadata/chapter/MOV-faststart toggles, because upstream exposes them by default and documents real tradeoffs in compatibility and runtime cost.[^7][^8][^11]
4. Track-selection warnings, because that is the upstream escape hatch for many “export succeeded but output is wrong” cases.[^8][^11]

### 4. Smart cut is useful, but only after the basics

LosslessCut does have smart cut, but both the code and docs frame it as experimental. The smart-cut helper first checks whether the desired start is already on an exact keyframe; if not, it finds the next keyframe and flags that only the range from the desired start until that keyframe needs smart-cut handling.[^9] It also limits support to inputs with exactly one real video stream and derives codec/timebase/bitrate parameters before attempting the operation, padding bitrate upward to hedge quality loss.[^9] The UI help text and troubleshooting docs are blunt that smart cut may not work on many files, works better on some H.264 than H.265 content, and may require extra frame shifting or pre-remuxing to MP4.[^8][^11]

Your app currently does **not** implement smart cut; instead, it uses ffprobe-discovered keyframes to warn when lossless copy is likely risky.[^17][^18] That is the right place to stop for now. Upstream evidence suggests smart cut is best treated as a **phase-2/phase-3 feature behind an “experimental” gate**, not as a prerequisite for a good LosslessCut-style editor.[^8][^9][^11] In other words: finish track control, remux/output settings, and marker/invert workflows first; only then add a narrowly scoped smart-cut path for single-video-stream cases.[^8][^9]

### 5. Preview behavior is a major architectural divergence

LosslessCut’s preview path is Chromium first, FFmpeg-assisted fallback second.[^2][^3] The app explicitly tells users that some files will not preview correctly in Chromium and that the remedy is conversion to a supported format or FFmpeg-assisted playback, sometimes with HEVC hardware-decoding toggles.[^2][^11] Its actual implementation spawns an FFmpeg process that produces fragmented MP4 for MSE consumption and keeps a master/slave playback model synchronized in React.[^3]

Your app has taken a cleaner native-desktop route: preview uses libmpv render API inside `QOpenGLWidget`, and when libmpv is unavailable the UI remains usable for loading files, splitting segments, and exporting enabled ranges.[^12][^13][^14] That is a better fit for PyQt than trying to reproduce LosslessCut’s Chromium+MSE path inside a Qt app. The main **feature** gap, not architectural gap, is that LosslessCut gives users an upstream-supported fallback path for preview issues, whereas your app currently degrades to “no preview” plus ffprobe duration / export-only behavior.[^2][^14][^20] If preview resilience is a priority, add a **one-click preview fallback** such as “Create temporary preview/remux copy” or an FFmpeg-assisted secondary preview path; keep libmpv as the primary renderer.[^2][^3][^14]

### 6. Projects and persistence are already aligned in spirit

LosslessCut persists segment state to `.llc` project files and also documents CSV/TSV import/export for segment lists.[^4] Your app already persists editor sessions to project JSON via `ProjectStore` and to a quick-session JSON under app data via `QuickSessionStore`, and the Trim page restores both export state and analysis state when reopening a saved session.[^15][^16][^20] The current project format is your own `*.cutproj.json` schema, not LosslessCut-compatible `.llc`/CSV/TSV.[^12][^15]

That means you do **not** need a new persistence architecture. If interoperability matters, the practical next step is to add **import/export adapters** for `.llc` and possibly CSV/TSV, not to replace the local project store.[^4][^15]

### 7. Diagnostics and runtime validation matter more than feature count now

LosslessCut’s documentation is basically a productized troubleshooting playbook: it encodes real-world advice for wrong keyframes, merge corruption, playback codec incompatibility, metadata issues, single-instance behavior, and very large file progress behavior.[^11] Your app already has the beginnings of a comparable support surface: an in-page diagnostics/activity feed, warning counting, persisted analysis snapshots, and export-plan warnings.[^12][^17][^18][^20][^21] However, your own implementation-status doc is clear that live desktop verification, cross-platform confidence, and packaging/signing behavior are still open items before the editor should be called complete.[^12][^21]

So the near-term quality plan should be: **widen the troubleshooting UX before widening the algorithmic surface area**. In practice that means surfacing more actionable recovery suggestions around keyframes, track problems, remuxing, and preview fallback using the LosslessCut docs as your product reference.[^8][^11][^21]

## Key Repositories / Areas Summary

| Repository / Area | Purpose | Key Files |
|---|---|---|
| [mifi/lossless-cut](https://github.com/mifi/lossless-cut) | Upstream product behavior, UI policies, smart-cut and preview fallback reference | `docs/index.md`, `docs/troubleshooting.md`, `src/renderer/src/segments.ts`, `src/renderer/src/smartcut.ts`, `src/renderer/src/MediaSourcePlayer.tsx`, `src/main/configStore.ts`, `src/main/compatPlayer.ts`, `src/main/ffmpeg.ts`[^1][^3][^4][^5][^7][^8][^9][^11] |
| `/Users/pb/Documents/GitHub/ytdlp-gui` | Current native PyQt implementation of a LosslessCut-style trim editor | `src/ui/pages/trim_page.py`, `src/core/editor/models.py`, `src/core/editor/playback_controller.py`, `src/ui/widgets/video_preview_widget.py`, `src/core/editor/keyframe_probe_worker.py`, `src/core/editor/export_planner.py`, `src/core/editor/export_manager.py`, `src/core/editor/project_store.py`, `src/core/editor/quick_session_store.py`[^12][^13][^14][^15][^16][^17][^18][^19][^20] |

## Gap Analysis

| Capability | Upstream LosslessCut | Current app | Recommendation |
|---|---|---|---|
| Markers / invert keep-vs-skip mode | Supported and central to workflow.[^4][^5] | No marker type; no invert workflow in current Trim page.[^14][^20] | Add optional `end_time` markers and a keep/skip export mode before deeper algorithm work. |
| Track selection / per-stream control | Tracks panel and track-specific troubleshooting are first-class.[^4][^8][^11] | No Track UI in Trim page; exporter has no explicit per-stream mapping controls.[^19][^20] | Add track panel + stream mapping next. |
| Output container / remux choice | Supported and often used as a fix strategy.[^4][^11] | Output naming preserves source suffix or merged suffix; no output-format selector exposed.[^18][^19][^20] | Add container selector early. |
| Advanced timestamp / metadata controls | `avoid_negative_ts`, MOV faststart, chapters, metadata toggles all exist upstream.[^7][^8][^11] | Lossless path hard-codes `make_zero`; no equivalent advanced controls exposed.[^19][^20] | Expose advanced export drawer/options. |
| Smart cut | Experimental, single-stream constrained, codec-sensitive.[^8][^9][^11] | Not implemented; keyframe probe is used only for warnings.[^17][^18] | Add only after tracks + remux + advanced export options. |
| Preview fallback | Chromium primary, FFmpeg-assisted fallback path exists.[^2][^3][^11] | libmpv primary; preview absence degrades to non-preview editing/export.[^13][^14][^20] | Keep libmpv primary, add explicit preview fallback/remux option. |
| Project interoperability | `.llc` plus CSV/TSV segment import/export.[^4] | Local `*.cutproj.json` + quick-session JSON.[^12][^15][^20] | Keep local schema, add adapters if interoperability is desired. |
| Troubleshooting UX | Rich, documented, action-oriented.[^8][^11] | Good start via warnings/diagnostics, but still lightweight.[^18][^20][^21] | Port upstream heuristics into local warnings/help text. |

## Recommended Integration Strategy

### What to keep doing

1. **Keep the implementation inside the current Trim tool.** Your repo already codified that “LosslessCut-style editor work” belongs in `src/core/editor/` and `src/ui/pages/trim_page.py`, and the codebase already follows that structure.[^12]
2. **Keep libmpv as the primary preview backend.** It is more native to PyQt than LosslessCut’s Chromium/MSE approach and is already integrated with exact/keyframe seeking semantics.[^3][^13][^14]
3. **Keep the current export planner / warning-first UX.** It is the right local equivalent to LosslessCut’s export-confirm surface.[^8][^18][^20]

### What to build next, in order

1. **Markers + invert/skip mode.** This closes one of the biggest model-level gaps with minimal architectural churn.[^4][^5][^14]
2. **Tracks panel and explicit stream mapping.** This will unlock a large fraction of LosslessCut’s real-world reliability story.[^4][^8][^11][^19]
3. **Output container selector and advanced export options.** Start with remux target, `avoid_negative_ts`, MOV faststart, metadata, and chapters.[^7][^8][^11][^19]
4. **Preview fallback/remux-for-preview.** This is the most practical way to borrow LosslessCut’s “convert to supported format” idea without importing its Chromium architecture.[^2][^3][^11][^14]
5. **Optional smart cut behind an experimental flag.** Reuse the current keyframe-analysis foundation, but keep the feature narrow and opt-in.[^8][^9][^17][^18]
6. **Optional compatibility import/export for `.llc` / CSV / TSV.** Only if users need interop with upstream projects.[^4][^15]

### What not to do

1. **Do not make LosslessCut’s CLI/API the core integration mechanism.** Upstream docs explicitly say the CLI/API are basic and the app was never designed for advanced batching/automation.[^10]
2. **Do not try to embed the Electron/React UI inside the PyQt app.** The runtime and playback stacks are fundamentally different: Electron/Chromium/MSE upstream versus PyQt/libmpv/OpenGL locally.[^1][^3][^13][^14]
3. **Do not prioritize smart cut ahead of track/export controls.** Upstream itself documents smart cut as experimental and unreliable on many files.[^8][^9][^11]
4. **Do not claim complete parity yet.** The current local status document is explicit that live desktop validation and packaging confidence are still outstanding.[^12][^21]

## Licensing / Reuse Consideration

LosslessCut is GPL-2.0-only.[^1] That makes **direct code copying** a licensing decision, not just a technical decision. I did not inspect the current app’s license in this research pass, so the safest recommendation is to treat LosslessCut primarily as a **behavior and architecture reference**, not a code donor, unless you intentionally want GPL-compatible reuse and have reviewed the licensing implications.[^1]

## Bottom Line

You do **not** need to “integrate LosslessCut” as an external subsystem. You already implemented the correct native analogue of its core architecture: segment-first editing, persistent projects, keyframe-aware warnings, and lossless-by-default export inside the existing Trim tool.[^12][^14][^15][^17][^18][^19][^20] The right move now is to continue along that path and add the parts of LosslessCut that most strongly affect user outcomes: markers/invert mode, track control, container/export options, and a better troubleshooting/fallback surface.[^4][^8][^11][^20][^21]

## Confidence Assessment

**High confidence:** the architectural comparison, the current-state summary of your app, the recommendation to continue the in-process PyQt implementation, and the prioritization of markers/tracks/export options ahead of smart cut are all directly supported by inspected source and docs.[^1][^3][^8][^12][^18][^19][^20]

**Medium confidence / inference:** the recommendation *against* embedding Electron UI is an engineering judgment derived from the evident runtime mismatch rather than a statement explicitly made by either codebase.[^1][^3][^13][^14] The licensing caution is certain on the LosslessCut side, but whether it becomes a practical blocker depends on your app’s own license, which I did not inspect.[^1]

**Lower confidence / unverified here:** I did not test runtime behavior, media edge cases, or packaging in this environment; the report relies on source, docs, and your repo’s existing implementation-status notes rather than live execution.[^12][^21]

## Footnotes

[^1]: `[mifi/lossless-cut](https://github.com/mifi/lossless-cut)` `package.json:2-23,42-46,92-119` (commit `5e1bb1fd002a10dc1e91caa3f440fb801fffb8b3`)
[^2]: `[mifi/lossless-cut](https://github.com/mifi/lossless-cut)` `docs/troubleshooting.md:67-86` (commit `5e1bb1fd002a10dc1e91caa3f440fb801fffb8b3`)
[^3]: `[mifi/lossless-cut](https://github.com/mifi/lossless-cut)` `src/main/compatPlayer.ts:8-24,27-55,97-124`; `src/renderer/src/MediaSourcePlayer.tsx:13-30,74-114,196-259`; `src/main/ffmpeg.ts:674-722` (commit `5e1bb1fd002a10dc1e91caa3f440fb801fffb8b3`)
[^4]: `[mifi/lossless-cut](https://github.com/mifi/lossless-cut)` `docs/index.md:51-108,110-126,137-138` (commit `5e1bb1fd002a10dc1e91caa3f440fb801fffb8b3`)
[^5]: `[mifi/lossless-cut](https://github.com/mifi/lossless-cut)` `src/renderer/src/segments.ts:12-49,90-149,159-221,224-297` (commit `5e1bb1fd002a10dc1e91caa3f440fb801fffb8b3`)
[^6]: `[mifi/lossless-cut](https://github.com/mifi/lossless-cut)` `src/common/userTypes.ts:1-69` (commit `5e1bb1fd002a10dc1e91caa3f440fb801fffb8b3`)
[^7]: `[mifi/lossless-cut](https://github.com/mifi/lossless-cut)` `src/main/configStore.ts:16-96,98-175` (commit `5e1bb1fd002a10dc1e91caa3f440fb801fffb8b3`)
[^8]: `[mifi/lossless-cut](https://github.com/mifi/lossless-cut)` `src/renderer/src/components/ExportConfirm.tsx:156-230,241-310` (commit `5e1bb1fd002a10dc1e91caa3f440fb801fffb8b3`)
[^9]: `[mifi/lossless-cut](https://github.com/mifi/lossless-cut)` `src/renderer/src/smartcut.ts:13-46,50-93` (commit `5e1bb1fd002a10dc1e91caa3f440fb801fffb8b3`)
[^10]: `[mifi/lossless-cut](https://github.com/mifi/lossless-cut)` `docs/index.md:9-10,42-43,137-138` (commit `5e1bb1fd002a10dc1e91caa3f440fb801fffb8b3`)
[^11]: `[mifi/lossless-cut](https://github.com/mifi/lossless-cut)` `docs/troubleshooting.md:7-23,25-56,118-156,138-140` (commit `5e1bb1fd002a10dc1e91caa3f440fb801fffb8b3`)
[^12]: `/Users/pb/Documents/GitHub/ytdlp-gui/docs/Trim-Editor.md:1-57`; `/Users/pb/Documents/GitHub/ytdlp-gui/docs/Implementation plans/Lossless cut/implementation-status.md:1-95`
[^13]: `/Users/pb/Documents/GitHub/ytdlp-gui/src/core/editor/playback_controller.py:34-137,192-215`
[^14]: `/Users/pb/Documents/GitHub/ytdlp-gui/src/ui/widgets/video_preview_widget.py:25-55,77-90,206-227,255-320`; `/Users/pb/Documents/GitHub/ytdlp-gui/src/core/editor/models.py:10-24,54-99,141-241`
[^15]: `/Users/pb/Documents/GitHub/ytdlp-gui/src/core/editor/project_store.py:12-47`; `/Users/pb/Documents/GitHub/ytdlp-gui/src/core/editor/quick_session_store.py:13-55`; `/Users/pb/Documents/GitHub/ytdlp-gui/tests/test_project_store.py:15-47`
[^16]: `/Users/pb/Documents/GitHub/ytdlp-gui/src/core/editor/keyframe_probe_worker.py:14-74`; `/Users/pb/Documents/GitHub/ytdlp-gui/src/ui/pages/trim_page.py:583-648`
[^17]: `/Users/pb/Documents/GitHub/ytdlp-gui/src/core/editor/export_planner.py:59-129,164-243`; `/Users/pb/Documents/GitHub/ytdlp-gui/tests/test_export_planner.py:27-47`
[^18]: `/Users/pb/Documents/GitHub/ytdlp-gui/src/core/editor/export_manager.py:17-266`
[^19]: `/Users/pb/Documents/GitHub/ytdlp-gui/src/ui/pages/trim_page.py:258-326,489-548,550-581,823-869,920-939,1214-1289`
[^20]: `/Users/pb/Documents/GitHub/ytdlp-gui/src/core/editor/diagnostics.py:13-51`; `/Users/pb/Documents/GitHub/ytdlp-gui/docs/Implementation plans/Lossless cut/implementation-status.md:43-94`
[^21]: `/Users/pb/Documents/GitHub/ytdlp-gui/src/main.py:25-68`
