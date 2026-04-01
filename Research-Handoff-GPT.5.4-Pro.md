PHASE 1 — Executive implementation brief

Recommended v1 architecture

Build a PyQt6 QWidget application with a single custom QOpenGLWidget player pane that uses libmpv render API (render.h, OpenGL path) for playback and preview, while FFmpeg/ffprobe run as external authoritative tools for probe/export through QProcess. Do not start with mpv’s native-window embedding (wid) and do not start with a QWindow/createWindowContainer player inside a widget UI. mpv’s own examples recommend the render API over window embedding because of platform-specific issues, especially on OSX/Qt; Qt’s window-container path has known stacking, focus, rendering-integration, and performance limitations, and many native child windows hurt performance. QOpenGLWindow is faster than QOpenGLWidget in isolation, but once embedded into a QWidget app you inherit the native-window/container tradeoffs you want to avoid. QOpenGLWidget also fits the product shape better because the player sits inside a classic desktop layout with timeline, segment lane, file bin, overlays, and inspector panels.  ￼  ￼  ￼

Key v1 decisions
	•	Playback backend: libmpv render API with OpenGL into a custom QOpenGLWidget. Use the official Qt-style callback pattern: mpv wakeup callback posts to Qt to drain events; render update callback posts update()/repaint; paintGL() calls mpv_render_context_render() into the widget FBO. QOpenGLWidget renders into an FBO, so use defaultFramebufferObject() and never assume framebuffer 0.  ￼  ￼  ￼
	•	Seek/scrub behavior: implement a two-phase seek model: fast approximate seek while dragging, then exact settle seek on pause/idle/release. mpv documents that precise seeks decode from the previous keyframe and can be slow; use that cost only for settle behavior, not for continuous scrub.  ￼
	•	Timeline truth: treat ffprobe probe data + mpv reported play position as v1 source of truth. Use time-based math, not frame-count math, for segment boundaries. mpv’s time-pos is the practical play position property; audio-pts updates more often but can be negative and mpv itself advises generally preferring time-pos. mpv also warns container FPS can be bogus and filter-estimated FPS can be unstable after precise seeks or on imperfect timestamps.  ￼  ￼
	•	Canonical edit model: store edits as an ordered range list of segments per source, not as a graph. Editing modes are UI affordances that all reduce to the same primitives: split, trim, enable/disable, label/tag, select, group-for-export.
	•	Export model: use an Export Planner + Policy Engine. The planner computes whether stream copy is safe, risky, or impossible. The policy engine decides whether to block, warn-and-ask, or allow an alternate plan. Default policy: warn and ask.
	•	Lossless default: stream copy is default, but never silently promise frame-exactness when the source is inter-frame and boundaries are off-keyframe. FFmpeg documents that input -ss seeks to the closest seek point before the request, and with stream copy the extra segment is preserved. LosslessCut’s own docs say lossless cutting is “not an exact science” and users may need to try both modes.  ￼  ￼
	•	Multi-file merge: represent cross-file assembly as a separate export/assembly sequence abstraction, not as the same object as a source timeline.
	•	Background analysis: immediate fast probe on open; lazy jobs for keyframes, waveform, thumbnails, compatibility, and diagnostics. Use async QProcess for FFmpeg/ffprobe and QThreadPool only for lightweight CPU post-processing. Qt’s threading docs say GUI classes stay on the main thread; QProcess is reentrant but event-driven objects should live and be used from one thread with an event loop.  ￼  ￼
	•	Persistence: JSON project file for saved projects; lightweight autosaved quick-session JSON in cache for ad hoc editing.

Biggest technical risks
	1.	Playback smoothness in embedded Qt player under 4K / HEVC / 10-bit / VFR / hidden-window states.
	2.	Off-keyframe lossless cuts causing unexpected start/end positions or stitch artifacts.
	3.	Timestamp weirdness: negative starts, discontinuities, edit-list behavior, VFR, B-frames.
	4.	Cross-file concat compatibility beyond superficial codec-name matching.
	5.	Linux hardware decode interop under X11 vs Wayland with libmpv render API.
	6.	Licensing/distribution: PyQt6 is GPL/commercial, not LGPL; mpv and FFmpeg build choices can also move you into GPL territory.  ￼  ￼  ￼  ￼
	7.	macOS signing/notarization with bundled dylibs + CLI tools.
	8.	Source relink drift when users relink to a “similar but not identical” file.
	9.	Background analysis contention with playback on slower machines.
	10.	Policy UX: warning too little is dangerous; warning too much makes the app feel broken.

Recommended boundaries
	•	UI layer: widgets, dialogs, timeline view, segment lane, source bin, assembly bin, export dialog.
	•	Domain layer: sources, segments, selection, tags, export groups, edit commands, undo/redo, policy decisions.
	•	Playback layer: libmpv wrapper, player controller, render widget, scrub controller.
	•	Analysis layer: ffprobe parser, keyframe map, thumbnails, waveform, diagnostics.
	•	Export layer: export assessment, compatibility analyzer, command planning, ffmpeg executor.
	•	Persistence layer: project I/O, autosave, migrations, relink state, cache index.
	•	Infrastructure layer: toolchain locator, logging, process runner, app paths, version manifest.

What should be built first
	1.	A minimal libmpv + QOpenGLWidget prototype with load/play/pause/seek and property observation.
	2.	A scrub controller with approximate-drag + exact-settle behavior.
	3.	A probe pipeline (ffprobe basic JSON + parse).
	4.	A canonical segment domain model and edit-command stack.
	5.	A first export planner for single-file separate segment exports via stream copy.
	6.	A warning model for off-keyframe boundaries and unsafe merges.
	7.	A concat-based merged-export path using temp segments + concat demuxer.
	8.	Quick-session autosave/reopen.
	9.	A relink flow.
	10.	Packaging smoke builds on all three platforms.

⸻

PHASE 2 — Deep technical handoff

A. Playback / seeking / preview

A1. Best libmpv integration strategy for PyQt6

Recommendation

Use libmpv render API with a custom QOpenGLWidget subclass in a QWidget app.

Why this is the best v1 choice
	•	mpv’s own docs/examples say there are two embedding methods: native window embedding and render API; they explicitly recommend render API over window embedding because of platform-specific behavior and issues, especially on OSX. They also mark the old opengl-cb API deprecated and say to use render.h instead.  ￼
	•	Qt’s createWindowContainer path makes the embedded window a native child with known limitations: it stacks as an opaque box over widgets, overlapping container order is undefined, focus return is platform-dependent, rendering integration is limited, and many such windows hurt performance. That is exactly the wrong tradeoff for a media editor with timeline + overlays + inspectors.  ￼
	•	QOpenGLWidget is designed for OpenGL content integrated into a QWidget hierarchy, and it guarantees a current GL context in initializeGL/paintGL, rendering into a Qt-managed FBO.  ￼
	•	The official mpv Qt OpenGL example already demonstrates the exact shape you need: create mpv with vo=libmpv, observe properties, create render context in initializeGL, render into the widget FBO in paintGL, and bridge callbacks into Qt with queued invocations.  ￼  ￼  ￼

Explicit non-recommendations
	•	Do not use wid / native child window embedding as the primary v1 path. mpv says it is OS-dependent, and on X11/win32 mpv creates its own child window and fills the parent window; mpv’s example notes X11 focus mismatch and OSX/Qt stability problems. This clashes with overlays and polished editor UI behavior.  ￼  ￼
	•	Do not use QOpenGLWindow inside createWindowContainer for v1. QOpenGLWindow itself is faster than QOpenGLWidget, but once embedded into a QWidget app the container limitations dominate. Use it only as an escalation path if benchmarking proves QOpenGLWidget is insufficient.  ￼  ￼
	•	Do not use deprecated opengl-cb. mpv says it is deprecated and deactivated.  ￼

Binding recommendation

Use a small internal binding layer over libmpv (client.h + render.h) with either:
	•	ctypes, or
	•	cffi

Prefer an internal wrapper over a high-level third-party mpv Python wrapper because you need:
	•	render-context creation,
	•	callback lifetime control,
	•	explicit struct layout,
	•	strict threading/GL-context rules,
	•	typed error mapping,
	•	stable integration with Qt’s event loop.

Required widget behavior

Your MpvRenderWidget should:
	•	create mpv handle early, but create render context only in initializeGL;
	•	use defaultFramebufferObject() in paintGL;
	•	pass MPV_RENDER_PARAM_FLIP_Y=1 for default framebuffer rendering;
	•	destroy render context before destroying mpv core;
	•	account for device pixel ratio when computing FBO width/height (prototype this on macOS Retina and Windows HiDPI);
	•	explicitly handle hidden/minimized states because the mpv Qt example warns that when Qt skips update() on an invisible window, mpv render timing can get confused and cause occasional freezes.  ￼  ￼  ￼

macOS note

If you request a specific OpenGL profile via QSurfaceFormat, set the default format before QApplication construction; Qt notes this is mandatory on some platforms, including macOS, to keep context sharing functional.  ￼

Render-thread decision

render.h recommends rendering on a separate thread and warns that deadlocks can happen if render-thread rules are broken, but the official Qt example demonstrates a viable Qt-main-thread render path. For Python v1, start with single-thread Qt render:
	•	all mpv API calls serialized through a PlaybackController,
	•	no locks held in callbacks or paintGL,
	•	render only in paintGL,
	•	all callbacks do minimal work and post to Qt.

Only move to a dedicated render thread if a prototype proves you need it. The dedicated-thread path is harder in Python because GL-context migration + callback affinity + GIL + Qt event loops increase risk.  ￼  ￼

A2. Best strategy for smooth scrubbing and responsive seeking

Implement three playback interaction modes:
	1.	Playback mode
	•	normal play/pause
	•	periodic UI position updates from mpv observed properties
	2.	Scrub mode
	•	entered when user drags timeline/thumbstrip/waveform
	•	pause playback immediately (remember whether playback was active)
	•	coalesce seek requests aggressively
	•	throttle actual seek commands to ~16–33 ms cadence
	•	during drag, use approximate/keyframe-biased seek
	•	mute audio during drag by default
	3.	Settle mode
	•	when drag pauses for ~100–150 ms or ends, issue exact settle seek
	•	wait until seek is done and position stabilizes
	•	if user was playing before scrub and setting allows, resume playback after settle

Concrete scrub algorithm

Maintain:
	•	requested_preview_time_us
	•	last_sent_seek_us
	•	settled_time_us
	•	seek_generation
	•	drag_active
	•	resume_after_scrub

Behavior:
	•	On every drag event:
	•	update UI thumb immediately;
	•	overwrite requested_preview_time_us;
	•	if no seek in flight and send interval expired, send approximate seek.
	•	Approximate seek command:
	•	absolute seek to requested time
	•	keyframe/fast preference
	•	no frame-accurate promise
	•	On drag idle or release:
	•	send exact seek to latest requested time
	•	mark generation
	•	when seek completion observed, update settled_time_us
	•	If more drag events arrive while exact seek in flight:
	•	do not queue many exact seeks; overwrite pending request and send a new one only after the current one completes or after a short cancellation window.

Why this aligns with mpv behavior

mpv documents that precise seeks decode from the previous keyframe up to target, so they are slower; this is exactly why precise seek should be used for settle, not for continuous drag.  ￼

A3. Balancing approximate seeks vs exact settle

Recommended default:
	•	Global mpv default: normal/precise-capable
	•	During scrub drag: approximate
	•	During settle: exact
	•	During frame-step or boundary-inspection mode: exact + more conservative framedrop behavior

More concrete policy:
	•	Drag: use “fast enough” absolute seek with keyframe bias
	•	Pause settle: use precise absolute seek
	•	Frame stepping: if paused and user explicitly invoked frame step, use frame-step commands rather than normal seek
	•	Boundary inspection: if user is parked and nudging around an edit boundary, temporarily favor accuracy over responsiveness

mpv also notes hr-seek-framedrop=yes speeds precise seeking but can skip the target frame in some cases; when you care about paused-frame inspection or backstep accuracy, prototype a temporary stricter mode for those actions only.  ￼

A4. How mpv reports playback position and caveats

Use these properties:
	•	time-pos/full or time-pos as the main playhead position
	•	duration as a provisional player duration only until ffprobe arrives
	•	audio-pts for diagnostics only, not as the main playhead

Why:
	•	mpv says time-pos is the position in current file in seconds, with a time-pos/full millisecond sub-property.
	•	mpv says audio-pts updates more often than once per frame and includes audio driver delay, but can become negative; it explicitly says in general you probably want time-pos.  ￼

Implications:
	•	UI playhead: time-pos/full
	•	segment math: project microseconds derived from ffprobe-normalized timeline
	•	diagnostics: compare audio-pts vs time-pos only for playback-health hints
	•	do not use container FPS as authoritative: mpv says container FPS can easily be bogus; estimated-vf-fps can be unstable after precise seeking or with imprecise timestamps.  ￼

A5. Frame stepping, keyframe stepping, pause-after-seek behavior

Use two distinct concepts:

Frame stepping
Use mpv commands:
	•	forward: frame-step 1 play or frame-step 1 seek
	•	backward: frame-back-step

mpv says:
	•	frame-step play is accurate but can be slow for many frames,
	•	backward stepping is seek-based,
	•	seek-based frame stepping can misbehave with timing-altering filters,
	•	for VFR, seek-based frame stepping is probably not correct except -1 case.  ￼

Recommendation:
	•	Expose single-frame forward/back only when paused.
	•	Do not build timeline math on frame stepping.
	•	Show a subtle diagnostic badge on VFR files: “frame stepping may be approximate”.

Keyframe stepping
Do not ask mpv to “discover” keyframes for editor semantics.
Instead:
	•	generate a keyframe map with ffprobe,
	•	seek to previous/next keyframe timestamps from that map.

This keeps preview and export aligned to the same authoritative keyframe knowledge.

Pause-after-seek
	•	If the app was paused before seek: stay paused.
	•	If the seek came from scrub drag: pause during drag; resume only if user setting says so.
	•	After an exact settle on paused boundary inspection: stay paused.

Also set mpv keep-open=yes so EOF parks instead of exiting and seeking past EOF snaps to last frame; that is editor-friendly.  ￼

A6. Known issues with 4K / high-bitrate / VFR / H.264 / H.265 / 10-bit in embedded mpv

Practical expectations for v1:
	•	4K/high-bitrate: decode/upload path matters; keep the player path minimal, avoid mpv filters, prefer DR/hwdec when stable.
	•	VFR: do not quantize edits to nominal frame count; stay time-based.
	•	H.264/H.265 with long GOP + B-frames: exact settle seeks will be slower.
	•	10-bit/HDR: cross-platform GPU-driver behavior must be prototype-validated early.
	•	Embedded Qt rendering: hidden/minimized-widget behavior can cause stale timing/freezes if not handled.

mpv says direct rendering can help large resolutions or slow hardware, but image-writing video filters silently disable that path. mpv’s Qt example also explicitly warns of occasional freezes when Qt skips updates on invisible windows.  ￼  ￼

A7. Hardware decoding considerations and cross-platform caveats

Recommended default setting:
	•	hwdec=auto

Why:
	•	mpv recommends starting with hwdec=auto because it limits itself to actively supported hardware decoders.
	•	It warns that forcing specific choices or broad enablement can cause problems.
	•	hwdec-current exists to inspect what is actually active.  ￼  ￼

Recommended user-visible setting:
	•	Auto
	•	Off
	•	Debug / specific API (advanced page only)

Platform notes:
	•	Windows: validate desktop OpenGL vs ANGLE-backed behavior if you encounter driver issues.
	•	macOS: validate Apple Silicon + Intel separately; HiDPI and color path matter.
	•	Linux: prototype on both X11 and Wayland. render.h exposes MPV_RENDER_PARAM_X11_DISPLAY and MPV_RENDER_PARAM_WL_DISPLAY, which are sometimes used for hwdec interop.  ￼

Do not overcomplicate v1 with API-specific knobs in normal settings. Keep:
	•	one safe default (auto)
	•	one reliable fallback (off)
	•	diagnostics panel showing hwdec-current, GPU renderer string, and whether software fallback occurred

A8. Should waveform/thumbnails be generated independently of libmpv playback?

Yes. Absolutely.

Reasons:
	•	ffprobe/ffmpeg are the authoritative export/probe toolchain.
	•	libmpv render API is for playback/rendering, not offline extraction.
	•	mpv’s software render API is explicitly described as slow and “not really suitable” for extracting frames/non-playback use.  ￼
	•	ffprobe supports frame-level inspection (-show_frames) and interval-limited reads (-read_intervals), which are ideal for progressive keyframe analysis and viewport-priority scans.  ￼  ￼

Recommendation:
	•	Keyframe map: ffprobe job
	•	Thumbnails: ffmpeg job(s), cached
	•	Waveform: ffmpeg audio-decode job + peak-envelope build, cached
	•	Playback: libmpv only

⸻

B. Timeline / segment model

B1. Best internal data model

Use these core domain entities:

MediaSource
Represents one source file.
Fields:
	•	source_id: UUID
	•	primary_path
	•	alternate_paths[]
	•	missing: bool
	•	changed_since_saved: bool
	•	fingerprint
	•	probe_summary
	•	stream_signature
	•	duration_us
	•	diagnostic_flags[]
	•	cache_keys for waveform/thumbnails/keyframes

SourceFingerprint
For relink/change detection:
	•	file size
	•	mtime ns
	•	basename
	•	optional inode/file ID where available
	•	quick hash of first/last N bytes
	•	optional full hash (lazy)
	•	primary stream signature snapshot

Segment
Canonical edit unit.
Fields:
	•	segment_id: UUID
	•	source_id
	•	start_us
	•	end_us
	•	state: active | disabled | soft_deleted
	•	selected: bool
	•	label: str | null
	•	tag_ids[]
	•	notes
	•	created_by_operation
	•	created_at
	•	modified_at

AssemblyGroup
Ordered list of segment references for export/merge.
Fields:
	•	group_id
	•	name
	•	items[] where each item is {segment_id, ordinal}
	•	mode_hint: separate | merge | ask
	•	diagnostics[]

TagCatalog
Project-level tag definitions:
	•	tag_id
	•	name
	•	color
	•	description

Project
Contains:
	•	sources
	•	segments by source
	•	groups
	•	settings snapshot refs
	•	export history
	•	UI state snapshot
	•	schema version

B2. Should segments be intervals, graph/nodes, or ordered range list?

Use an ordered range list of intervals as the canonical model.

Why:
	•	Your edits are linear and source-relative.
	•	Segments need ordering, enable/disable state, selection, labels, and export grouping.
	•	A graph is only justified if v1 supports alternate branches, overlaps, compositing, or general NLE semantics. It does not.
	•	A plain interval list is easy to test, serialize, diff, undo, relink-check, and export-plan.

Recommended structure:
	•	per source: List[Segment] sorted by start_us
	•	invariant: no overlaps within a single source timeline unless later feature work explicitly introduces them
	•	multi-file assembly: separate AssemblyGroup references, not a graph over segments

B3. Supporting all three editing modes without duplicated logic

Treat the three editing modes as UI/command generators over the same canonical segment operations.

Canonical operations:
	•	split_segment(segment_id, at_us)
	•	trim_segment_start(segment_id, new_start_us)
	•	trim_segment_end(segment_id, new_end_us)
	•	insert_segment(source_id, start_us, end_us)
	•	toggle_segment_state(segment_id, state)
	•	set_segment_label/tags
	•	reorder_group_item

Map UI modes to canonical operations:

split-at-playhead
	•	find active segment containing playhead
	•	split_segment(active_segment, playhead_us)

mark in/out
Two flavors:
	•	create new keep segment from marks
	•	trim selected segment to marks

Both are commands over interval objects.

cut-point slicing
	•	maintain temporary cut-point list in UI
	•	when committed, slice the relevant source span into ordered intervals
	•	persist only resulting segments, not the transient cut-point model

This avoids storing multiple competing edit representations.

B4. Undo/redo model recommendation

Use a domain-command + inverse patch model.

Recommended behavior:
	•	domain state is independent of Qt
	•	every edit command returns:
	•	before_patch
	•	after_patch
	•	undo_patch
	•	redo_patch
	•	coalesce drag-resize trim events into one undo step
	•	playback actions are not part of undo
	•	selection changes may be undoable only if they are part of an editing workflow, otherwise keep them UI-local

Commands that should be undoable:
	•	split
	•	trim
	•	create segment
	•	slice by cut points
	•	enable/disable/soft delete/restore
	•	label/tag changes
	•	export-group reorder/add/remove

B5. Keeping timeline state robust when files are relinked or slightly changed

Store segments in time units (us), not frame numbers.

Relink/change workflow:
	1.	On project load, compare saved fingerprint against current file.
	2.	If exact match: relink silently.
	3.	If path missing: search known locations + project dir + user-selected folder.
	4.	If candidate differs but looks similar:
	•	compare duration
	•	compare primary stream signature
	•	compare quick hashes
	•	compare stream count/types
	5.	If compatible-ish but not exact:
	•	allow relink with warning
	•	mark source as changed_since_saved
	•	re-run diagnostics
	•	mark any segments beyond new duration as invalid
	6.	If incompatible:
	•	do not silently relink

Suggested thresholds:
	•	duration delta < 100 ms and same primary stream signature = “probable same media, changed container/path”
	•	duration delta >= 100 ms or stream signature mismatch = explicit review required

⸻

C. Lossless cutting / merging

C1. Real-world limitations of “lossless cut” with FFmpeg

This is the core truth the app must surface clearly:
	•	FFmpeg says input -ss seeks to the closest seek point before the target, not exactly to the target, and with stream copy the extra segment is preserved.  ￼
	•	LosslessCut’s own troubleshooting says lossless cutting is not exact science and users may need to try both modes.  ￼

So v1 must distinguish:
	1.	Container/packet-exact stream copy
	•	no re-encode
	•	boundaries may not be frame-exact on inter-frame video
	2.	Frame-exact cut
	•	generally requires re-encode or smart edge re-encode
	•	not allowed unless user explicitly approves

C2. Keyframe boundary issues and how to communicate them

User-facing rule:
	•	If a video segment start is not on a keyframe, exact lossless start cannot be promised.
	•	End boundaries can also be imperfect because packet/timestamp behavior can extend or truncate around the marked out point.

Recommended UX:
	•	Show per-segment status in export assessment:
	•	Green: start/end keyframe-safe
	•	Yellow: best-effort copy only
	•	Red: re-encode required for exact result
	•	For each risky segment show:
	•	requested in/out
	•	nearest previous/next keyframes
	•	policy consequence:
	•	copy with warning
	•	snap to safe boundaries
	•	require re-encode for exact

C3. Best FFmpeg strategies

Single segment extraction
Use one FFmpeg process per output segment.

Support two copy strategies internally:
	•	Fast keyframe-biased copy
	•	Best-effort copy

The app can expose these as policy presets or advanced modes, but default behavior should remain “warn and ask” rather than pretending one mode is universally correct. LosslessCut explicitly notes users may need to try both modes; it maps “keyframe cut” to -ss before -i.  ￼

Multi-segment separate export
	•	one FFmpeg job per active segment
	•	explicit stream mapping each time
	•	serialize by default; limited parallelism only after benchmark

Multi-segment merged export (same file or multi-file)
Preferred v1 plan:
	1.	export each segment to a temp file using the chosen copy policy
	2.	concat temp files with concat demuxer
	3.	remove temp files on success (or keep for debug when export fails)

Why:
	•	FFmpeg concat demuxer supports stream-copy-style concatenation, but all files must have the same streams, codecs, time base, etc.  ￼
	•	FFmpeg concat filter is not a lossless stream-copy path; the FFmpeg wiki says filters are incompatible with stream copy, and filter docs require all segments to start at timestamp 0 and have matching parameters, with VFR possible at output.  ￼  ￼

Do not use concat-demuxer inpoint/outpoint as the primary authoritative lossless-cut engine
FFmpeg documents that concat demuxer inpoint/outpoint selection may still output packets not entirely contained in the selected interval; concatdec_select is then used on decoded frames. That is fine for filter/re-encode paths, but not the cleanest base for a lossless editor.  ￼

C4. When stream copy is safe vs unsafe

Safe enough for default lossless path
	•	single source, or temp outputs from one compatible source
	•	same stream topology
	•	same codec parameters
	•	chosen output container supports selected streams
	•	boundaries are keyframe-safe, or user explicitly accepts best-effort copy

Unsafe / warn
	•	off-keyframe video boundaries
	•	VFR + weird timestamps
	•	mismatched stream layouts across files
	•	mismatched time bases
	•	negative timestamps / discontinuities
	•	container mismatch with selected subtitles/attachments/data
	•	merged sources with inconsistent metadata/chapters

C5. Detecting when re-encode is required or recommended

Define export outcomes:
	•	COPY_SAFE
	•	COPY_RISKY_WARN
	•	COPY_UNSAFE_BLOCK
	•	REENCODE_OPTIONAL_FOR_EXACTNESS
	•	REENCODE_REQUIRED

Typical triggers:
	•	exact user boundary is off-keyframe and user demands frame-exactness
	•	merge files differ in hard stream-copy compatibility fields
	•	target container cannot accept selected streams
	•	timestamps are structurally broken enough that copy plan is likely invalid

C6. Rules engine / preset policy

Implement a dedicated ExportPolicyEngine.

Input:
	•	selected segments / group
	•	source probe summaries
	•	keyframe alignment
	•	stream compatibility
	•	user-chosen output mode
	•	container choice
	•	stream preset
	•	naming preset
	•	policy preset

Output:
	•	ExportAssessment
	•	allowed_plans[]
	•	warnings[]
	•	requires_explicit_approval[]

Recommended policy presets:

strict_lossless
	•	block off-keyframe exactness
	•	block incompatible merges
	•	no stream drops unless explicitly approved
	•	no re-encode offered by default

warn_and_ask (default)
	•	warn on off-keyframe boundaries
	•	warn on stream drops, metadata/chapter drops, timestamp normalization
	•	allow best-effort copy if user confirms
	•	allow re-encode only if user explicitly opts in

auto_adjust_safe_boundaries
	•	explicit opt-in preset only
	•	snap/expand/trim to safe boundaries according to preset semantics
	•	never default

Important nuance:
There are two kinds of auto-adjust:
	•	expand to include requested content
start -> previous keyframe
end -> next safe boundary
	•	trim to remain inside requested content
start -> next safe boundary
end -> previous safe boundary

Do not choose one silently unless the user explicitly selected that preset.

C7. Recommended handling of timestamps, time bases, VFR, B-frames, edit lists, discontinuities

Rules:
	1.	Store project times in integer microseconds.
	2.	Never derive authoritative edit positions from nominal FPS.
	3.	Use ffprobe stream + frame analysis to classify VFR risk.
	4.	Do not blanket-enable copyts by default.

Why not blanket copyts:
	•	FFmpeg says -copyts keeps input timestamps without sanitizing them, but output timestamps may still differ because of muxer processing or avoid_negative_ts.  ￼
	•	FFmpeg says copytb 1 can be required to avoid non-monotonic timestamps when copying VFR video streams.  ￼
	•	FFmpeg notes timestamp discontinuity correction is disabled with -copyts on discontinuity-accepting formats unless wrapping is detected.  ￼

Recommended default timestamp policy for v1:
	•	standalone outputs: normalize starts for usability (avoid_negative_ts make_zero is a sensible default candidate)
	•	preserve-source-timestamps: advanced preset only
	•	merged outputs: normalize rather than preserve strange source starts unless workflow explicitly demands preservation

FFmpeg says avoid_negative_ts can:
	•	make non-negative,
	•	make zero,
	•	auto,
	•	disable shifting.  ￼

VFR / B-frame implications:
	•	Use time-based boundaries.
	•	Use ffprobe keyframe/frame data for diagnostics.
	•	Do not market paused frame-step as fully authoritative on VFR.
	•	Keep preview filters off; mpv warns timing-modifying filters can break precise stepping semantics.  ￼

C8. Safe handling of subtitle, audio, attachments, chapters, metadata

Streams
Always build explicit -map plans. Never rely on implicit stream selection for an editor.

Metadata
FFmpeg says by default global metadata is copied from the first input file, and per-stream/per-chapter metadata is copied along with streams/chapters unless explicit mapping disables it. For merged outputs this default is dangerous. Default v1 behavior should be:
	•	-map_metadata -1
	•	then explicitly add sanitized metadata you want to preserve or generate
	•	allow preset override for “preserve metadata from first source” only with warning.  ￼

Chapters
FFmpeg says if no chapter mapping is specified, chapters are copied from the first input with chapters. For partial cuts and merges this is usually misleading. Default v1 behavior:
	•	-map_chapters -1
	•	future option: generate synthetic chapters from segment labels on merged export
	•	explicit override: preserve chapters only for remux/full-file workflows.  ￼

Attachments
FFmpeg documents attachments as a specific type of stream. Default v1 behavior:
	•	preserve only in single-source same-container remux/copy when the stream preset explicitly says so
	•	otherwise drop with warning
	•	never silently preserve from multiple incompatible sources.  ￼

Audio/subtitles
Use stream presets:
	•	preserve_all_streams
	•	preserve_common_compatible_streams
	•	selected_streams_only
	•	video_plus_default_audio
	•	audio_only

⸻

D. Multi-file merge workflows

D1. Compatibility checks required before stream-copy merge

At minimum compare, per stream position/type:

Video
	•	codec name
	•	codec tag / bitstream form when available
	•	profile
	•	level
	•	width / height
	•	sample aspect ratio
	•	pixel format
	•	field order
	•	color range / primaries / transfer / colorspace
	•	time base
	•	extradata fingerprint if available
	•	avg_frame_rate / r_frame_rate for risk classification
	•	HDR side-data presence if available

Audio
	•	codec
	•	sample format
	•	sample rate
	•	channels
	•	channel layout
	•	bits per sample / raw sample size when relevant
	•	time base

Subtitle / data / attachment
	•	stream type
	•	codec
	•	container acceptability for target output
	•	disposition/language only as warning-level differences unless workflow demands matching

Container / mux behavior
	•	same output container target
	•	same stream ordering after mapping
	•	same chapter/metadata policy

D2. What should be compared, explicitly

FFmpeg concat demuxer says all files must have the same streams, same codecs, same time base, etc. LosslessCut markets lossless merge only for arbitrary files with identical codec parameters. Treat that as the minimum public promise.  ￼  ￼

So implement compatibility in three levels:

Hard blockers
	•	stream count/type/order mismatch
	•	codec mismatch
	•	time base mismatch
	•	resolution/pix_fmt/SAR mismatch
	•	sample rate/channel layout mismatch
	•	incompatible container target

Warn-only risks
	•	avg_frame_rate mismatch / VFR suspicion
	•	metadata mismatch
	•	chapter mismatch
	•	language/title/disposition mismatch
	•	duration inconsistencies

Deep-compare optional
	•	codec extradata hash mismatch
	•	HDR/mastering metadata mismatch

D3. Recommended user-facing behavior when files are incompatible

If incompatible:
	•	show a merge-assessment dialog
	•	group issues by stream and severity
	•	offer:
	•	Cancel
	•	Export separately
	•	Proceed with copy merge on common compatible streams only (warning)
	•	Re-encode merged output (explicit approval only)

Never silently:
	•	drop streams,
	•	reorder streams,
	•	re-encode,
	•	or switch containers.

D4. Does previewing merge order require a separate abstraction from timeline editing?

Yes.

Use:
	•	SourceTimeline for per-file editing
	•	AssemblyGroup for cross-file export/merge ordering

Do not turn v1 into a full multi-file continuous timeline editor.
That adds huge complexity around:
	•	cross-file preview continuity,
	•	timescale normalization,
	•	transport semantics,
	•	per-source relink and diagnostics,
	•	merged waveform/thumb generation

Recommended v1 preview behavior:
	•	user edits one source timeline at a time
	•	assembly list shows ordered segment refs across files
	•	clicking an assembly item loads its source and seeks to that segment
	•	optional “play selected assembly from here” can be app-driven later, but not required for first stable v1

⸻

E. File naming / tags / presets

E1. Best template system for output names

Use a small custom token engine, not Jinja2 and not Python eval.

Recommended syntax:
	•	${token}
	•	${token:format} for numeric/time formatting

Examples:
	•	${source_base}_${segment_index:03d}
	•	${project_name}_${group_name}_${date}
	•	${source_base}_${label}_${in_tc}_${out_tc}

Why:
	•	deterministic
	•	safe
	•	easy to validate
	•	easy to document
	•	no sandbox/security problem

E2. Recommended variable tokens

Core tokens:
	•	project_name
	•	session_mode
	•	source_base
	•	source_ext
	•	source_index
	•	segment_index
	•	segment_count
	•	segment_label
	•	segment_tags
	•	segment_state
	•	in_s
	•	out_s
	•	duration_s
	•	in_tc
	•	out_tc
	•	group_name
	•	group_index
	•	export_mode
	•	preset_name
	•	date
	•	time

Optional later:
	•	video_codec
	•	audio_codec
	•	resolution
	•	stream_preset

E3. Filename sanitization strategy across macOS/Linux/Windows

Apply a centralized FilenameSanitizer:
	•	normalize Unicode (NFKC or NFC)
	•	replace control chars
	•	replace path separators
	•	Windows: strip <>:"/\|?*
	•	strip trailing spaces and dots
	•	guard reserved DOS names (CON, PRN, AUX, NUL, COM1…)
	•	collapse repeated separators/whitespace
	•	enforce per-component max length
	•	preserve extension
	•	collision resolution:
	•	name.ext
	•	name (1).ext
	•	name (2).ext

E4. How segment tags should be represented internally

Use:
	•	one free-text label
	•	zero or more tag IDs from a project-level tag catalog

Why:
	•	renaming a tag should update all segments without rewriting raw tag text
	•	tags can carry color and description
	•	label remains human-facing and naming-template friendly

E5. Preset storage and override model

Use layered presets:
	1.	Built-in presets
	2.	User presets
	3.	Project-local snapshots/references
	4.	Export-dialog transient overrides

Persist both:
	•	the preset reference used
	•	the resolved snapshot in export history

That makes old exports reproducible even if the preset changes later.

⸻

F. Background analysis / diagnostics

F1. What should be probed immediately vs lazily

Immediate on open
	•	file exists
	•	file stat / fingerprint start
	•	ffprobe basic format/streams/chapters
	•	duration
	•	stream list
	•	initial diagnostics from stream topology
	•	open mpv immediately in parallel

Lazy / background
	•	keyframe map
	•	waveform peaks
	•	thumbnails
	•	deeper timestamp diagnostics
	•	merge compatibility scans
	•	optional full-file frame scan for difficult media

F2. Background jobs that should exist

BasicProbeJob
	•	fast ffprobe JSON
	•	highest priority

KeyframeMapJob
	•	ffprobe frame scan on primary video
	•	progressive: viewport-first using -read_intervals, then full scan
	•	cache result by source fingerprint

ThumbnailJob
	•	ffmpeg frame extraction
	•	priority near visible viewport / playhead first
	•	cached

WaveformJob
	•	ffmpeg audio decode to downmixed PCM
	•	compute peak envelope pyramid
	•	cached

DiagnosticsJob
	•	inspect timestamps, start offsets, VFR suspicion, missing/odd durations, stream anomalies

MergeCompatibilityJob
	•	compare selected sources / assembly group and compute copy-safe matrix

F3. How to structure worker processes/threads safely in PyQt6

Recommended split:

QProcess for FFmpeg/ffprobe
Create and use them in one thread with an event loop, ideally the main thread job manager, because Qt warns event-driven objects should be used in a single thread and QProcess is one of those reentrant-but-thread-affine classes. Always launch with absolute executable paths.  ￼  ￼

QThreadPool for lightweight CPU work
Use for:
	•	parsing large probe outputs
	•	peak-envelope building
	•	hashing
	•	thumbnail image post-processing

Qt says QThreadPool recycles threads, is thread-safe, and is appropriate for QRunnable tasks.  ￼

Main thread only
	•	all QWidget work
	•	mpv render widget
	•	most playback control calls
	•	job orchestration
	•	dialog/UI state updates

F4. Logging and diagnostic surfaces needed

Implement all of these:

Structured app log
JSON lines:
	•	timestamp
	•	level
	•	subsystem
	•	event
	•	session/project/source/segment IDs
	•	job ID
	•	command line array
	•	exit code
	•	elapsed ms
	•	warning codes
	•	exception info

mpv log capture
	•	selected mpv log levels
	•	important observed properties
	•	playback backend info (hwdec-current, renderer, etc.)

ffmpeg/ffprobe command history
	•	exact arg arrays
	•	stdout/stderr capture
	•	parsed summary
	•	retained per export/probe job

In-app diagnostics surfaces
	•	source diagnostics panel
	•	export assessment panel
	•	last command / raw log drawer
	•	“copy for support” button
	•	export history inspector

F5. What A/V sync and drift risks are practical to detect in v1

Detectable in v1:
	•	large audio/video stream start-time delta
	•	negative or non-zero starts that imply timestamp normalization risk
	•	VFR suspicion from rate fields / frame scan variance
	•	discontinuity/non-monotonic timestamp hints
	•	concat duration/gap risk
	•	sparse subtitle risk for shortest/buffering behavior
	•	source changed since saved project

Not realistically guaranteed in v1:
	•	perceptual lip-sync judgment
	•	perfect detection of every muxer/player-specific artifact before export

So diagnostics should be framed as:
	•	structural risk detection, not oracle-level prediction

⸻

G. Cross-platform packaging / deployment

G1. How to package PyQt6 + libmpv + FFmpeg

Recommended v1 bundler

Use PyInstaller onedir first.
PyInstaller documents standalone freezing for Windows, macOS, and GNU/Linux, and its build system supports adding extra binaries/data. That fits a PyQt6 app with bundled libmpv and ffmpeg/ffprobe binaries.  ￼  ￼

Windows

Bundle:
	•	app exe
	•	Qt DLLs/plugins
	•	mpv-*.dll
	•	ffmpeg.exe
	•	ffprobe.exe
	•	dependent DLLs for libmpv/ffmpeg

Implementation notes:
	•	always resolve absolute tool paths from app dir
	•	load libmpv by absolute path
	•	sign EXE + DLLs
	•	keep DLL names recognizable for LGPL compliance if using LGPL FFmpeg builds; FFmpeg legal says do not obfuscate dll names.  ￼  ￼

macOS

Bundle inside .app:
	•	Python runtime
	•	Qt frameworks/plugins
	•	libmpv.dylib and deps
	•	ffmpeg / ffprobe binaries
	•	license/compliance manifest

Must validate:
	•	codesigning every nested dylib and executable
	•	notarization
	•	Apple Silicon + Intel builds (separate or universal2)
	•	Retina/HiDPI FBO sizing

Linux

Recommended official distribution first:
	•	AppImage or onedir tarball
	•	optional distro-native packages later

Bundle:
	•	app
	•	Qt libs/plugins as needed
	•	vetted libmpv
	•	ffmpeg / ffprobe
	•	rely on system GPU/driver stacks, not bundled GPU drivers

Also support advanced override:
	•	user-configurable external ffmpeg/ffprobe/mpv paths
	•	useful for distro quirks and support cases

G2. Distribution/licensing concerns

This is the biggest non-technical blocker.

PyQt6
Riverbank says:
	•	free PyQt versions are GPLv3,
	•	if your use is not GPL-compatible, you need a commercial license,
	•	PyQt itself is not LGPL, even though GPL wheels include LGPL Qt libraries.  ￼  ￼

Implication:
	•	if the product is not GPL, commercial PyQt licensing is required

FFmpeg
FFmpeg’s legal page says FFmpeg is LGPL by default, but optional parts can change obligations; it also lists concrete LGPL distribution requirements, including source-availability/documentation obligations, and warns commercial products may face patent/licensing exposure around patented codecs.  ￼  ￼  ￼

Implication:
	•	keep a build manifest with FFmpeg version + configure line
	•	prefer LGPL-only FFmpeg builds unless product/legal explicitly approves GPL implications
	•	do not casually ship GPL encoders like libx264 if your distribution plan assumes LGPL-only

mpv
mpv’s copyright file says:
	•	mpv as a whole is GPL by default
	•	it can be LGPL if built without GPL-only files
	•	-Dgpl=false is only a convenience for excluding GPL-only files and is not by itself a license grant.  ￼

Implication:
	•	use a vetted LGPL-eligible libmpv build if the app is not GPL
	•	keep provenance/build flags documented

G3. Native dependency bundling strategy

Recommended:
	•	bundle your own known-good toolchain on Windows/macOS
	•	on Linux, bundle too, but allow external override for support
	•	keep a third_party_manifest.json or similar with:
	•	component name
	•	version
	•	build source/provenance
	•	configure flags
	•	license summary
	•	source-code location

G4. Update strategy considerations

Recommended v1:
	•	no auto-updater in first stable milestone
	•	manual update notification only
	•	versioned toolchain manifest in diagnostics
	•	signed installers/bundles per platform

Reason:
	•	packaging/signing/licensing is already a large surface
	•	auto-updaters add more platform-specific risk than value for first delivery

G5. Platform-specific blockers / pain points
	•	Windows: DLL search/path correctness, signing, GPU-driver variance
	•	macOS: bundle signing/notarization, Apple Silicon vs Intel, OpenGL path validation
	•	Linux: Wayland/X11 variance, libmpv hwdec interop, distro/libc fragmentation

⸻

H. Project/session persistence

H1. Recommended project file format

Use JSON for v1.

Why JSON over SQLite for v1:
	•	easy to inspect
	•	easy to diff
	•	easy to migrate with explicit schema version
	•	session sizes remain manageable if thumbnails/waveforms stay in cache, not in project

Recommended extension:
	•	.cutproj.json or similar

H2. What to persist

Persist all of these:

Source references
	•	primary path
	•	alternate known paths
	•	fingerprint snapshot
	•	probe summary snapshot
	•	missing/changed flags

Segment model
	•	per-source ordered segments
	•	start/end in microseconds
	•	lifecycle state
	•	creation metadata

UI-related persistent editing state
	•	selected state
	•	active source
	•	active group
	•	zoom level
	•	optional in/out mark state if you want project reopen continuity

Labels/tags
	•	tag catalog
	•	segment label + tag IDs

Presets used
	•	preset refs
	•	resolved export-preset snapshots in export history

Export history
	•	timestamp
	•	outputs
	•	selected segments/group
	•	policy snapshot
	•	warnings
	•	command summary hash / full command log pointer

H3. Relink workflow design

On project load:
	1.	validate all sources
	2.	if missing, search:
	•	original path
	•	project dir
	•	recent relink roots
	•	same basename nearby
	3.	show candidate list with:
	•	path
	•	size
	•	mtime
	•	duration
	•	stream signature summary
	4.	allow:
	•	relink single file
	•	relink by root-folder substitution
	•	skip for now
	5.	after relink:
	•	rerun probe
	•	rerun diagnostics
	•	mark affected segments if source changed

H4. Versioning strategy for project files

Use:
	•	top-level schema_version
	•	monotonic migration functions
	•	preserve unknown fields when possible
	•	store app_version separately from schema_version

Recommended rule:
	•	project load always migrates to latest in memory
	•	save always writes latest schema

⸻

I. Testing strategy

I1. Unit-testable core logic boundaries

Unit-test these without Qt or media playback:
	•	interval math
	•	split/trim/slice command logic
	•	undo/redo
	•	selection rules
	•	disabled/soft-delete rules
	•	export policy engine
	•	compatibility analyzer
	•	filename template rendering + sanitization
	•	relink candidate scoring
	•	ffprobe JSON parsing
	•	project migrations
	•	export-plan construction
	•	warning generation

I2. Media fixture categories needed

You need fixtures for:
	•	H.264 MP4, dense keyframes
	•	H.264 MP4, sparse keyframes / long GOP
	•	HEVC 10-bit
	•	VFR smartphone MP4
	•	ProRes / intra-only
	•	MKV with multiple audio/subtitle streams
	•	MKV with attachments
	•	MPEG-TS with discontinuities
	•	audio-only AAC/MP3/FLAC
	•	files with negative/non-zero starts
	•	truncated/corrupt file
	•	long-duration file
	•	4K high-bitrate file
	•	multi-file compatible merge set
	•	multi-file incompatible merge sets:
	•	resolution mismatch
	•	pix_fmt mismatch
	•	sample-rate mismatch
	•	channel-layout mismatch
	•	subtitle mismatch
	•	time-base mismatch

I3. Edge-case files to test

Prioritize:
	•	long-GOP H.264 with off-keyframe cuts
	•	HEVC 10-bit with hwdec on/off
	•	VFR file with frame stepping
	•	MP4 with edit-list/timestamp oddities
	•	TS broadcast capture with discontinuity
	•	MKV with fonts/attachments/subtitles
	•	file with no audio
	•	file with no video
	•	multi-audio language tracks
	•	sparse subtitles

I4. Playback integration tests vs export pipeline tests

Playback integration tests
	•	mpv loads file
	•	widget renders first frame
	•	play/pause works
	•	approximate seek updates quickly
	•	exact settle lands near target time
	•	hidden/minimized behavior does not freeze next visible update
	•	EOF keep-open behavior works

Export pipeline tests
	•	command plans generated correctly
	•	outputs created
	•	no implicit re-encode when copy was expected
	•	output probe matches expected streams
	•	temp cleanup works
	•	concat path works for compatible temp segments
	•	warnings appear for risky inputs

I5. Regression tests for cut accuracy and merge safety

For each fixture:
	•	requested segment in/out
	•	expected policy classification
	•	actual output probe
	•	actual start/end timestamps
	•	actual stream copy vs re-encode detection
	•	compare merged output stream topology against expected

Also add “never regress” assertions:
	•	no silent re-encode
	•	no silent stream drop
	•	no silent metadata/chapter carryover on merge
	•	no project corruption on relink failure

⸻

PHASE 3 — Implementation-ready spec

Concrete module/package structure

src/
  app/
    main.py
    bootstrap.py
    version.py

  ui/
    main_window.py
    dialogs/
      export_dialog.py
      relink_dialog.py
      settings_dialog.py
      diagnostics_dialog.py
    player/
      mpv_render_widget.py
      transport_bar.py
      player_status_bar.py
    timeline/
      timeline_view.py
      ruler_view.py
      segment_lane_view.py
      thumbnail_strip_view.py
      waveform_view.py
    panels/
      source_bin_panel.py
      assembly_panel.py
      inspector_panel.py
      diagnostics_panel.py

  domain/
    models/
      source.py
      segment.py
      assembly.py
      tag.py
      project.py
      presets.py
      diagnostics.py
    commands/
      base.py
      split_at_playhead.py
      apply_in_out.py
      slice_by_cutpoints.py
      toggle_segment_state.py
      restore_segment.py
      set_label.py
      set_tags.py
      selection.py
      assembly_ops.py
    services/
      edit_service.py
      undo_service.py
      selection_service.py
      compatibility_service.py
      export_policy_service.py
      naming_service.py
      relink_service.py

  playback/
    mpv/
      lib.py
      types.py
      errors.py
      player_core.py
      player_controller.py
      scrub_controller.py
      property_bridge.py
      render_bridge.py

  analysis/
    probe/
      ffprobe_runner.py
      probe_models.py
      probe_parser.py
    jobs/
      job_manager.py
      basic_probe_job.py
      keyframe_job.py
      waveform_job.py
      thumbnail_job.py
      diagnostics_job.py
      compatibility_job.py
    cache/
      cache_index.py
      thumbnail_cache.py
      waveform_cache.py
      keyframe_cache.py

  export/
    models/
      export_request.py
      export_assessment.py
      export_plan.py
      export_result.py
    ffmpeg/
      ffmpeg_runner.py
      command_builder.py
      concat_builder.py
      stream_map_builder.py
      temp_manager.py
      stderr_parser.py

  persistence/
    project_store.py
    project_serializer.py
    migrations.py
    autosave.py
    quick_session_store.py

  infra/
    tool_locator.py
    process_runner.py
    logging.py
    paths.py
    platform_info.py
    app_settings.py
    version_manifest.py

tests/
  unit/
  integration/
  fixtures/

Interfaces / classes / services to create

Playback

ToolLocator
Responsibilities:
	•	resolve absolute paths for ffmpeg, ffprobe, libmpv
	•	prefer bundled tools, allow override
	•	expose version manifest

MpvPlayerCore
Responsibilities:
	•	own mpv_handle
	•	set options
	•	observe properties
	•	drain event queue
	•	load/unload sources
	•	send commands/properties

MpvRenderWidget(QOpenGLWidget)
Responsibilities:
	•	create render context in initializeGL
	•	issue render calls in paintGL
	•	handle hidden/minimized behavior
	•	emit Qt signals for exposed/render state

PlaybackController
Responsibilities:
	•	facade used by UI
	•	play/pause/toggle
	•	load source
	•	seek exact/approx
	•	frame step
	•	keyframe step
	•	resume-after-scrub logic

ScrubController
Responsibilities:
	•	coalesce drag events
	•	track seek generations
	•	run approximate then exact settle
	•	expose preview vs settled playhead

Domain / editing

ProjectStore
Responsibilities:
	•	hold current in-memory project state
	•	dispatch domain commands
	•	emit change notifications
	•	dirty-state tracking

EditService
Responsibilities:
	•	source-aware segment operations
	•	validation of overlaps/order
	•	cut-point slicing
	•	mark in/out application

UndoService
Responsibilities:
	•	command history
	•	coalescing drag operations
	•	redo stack

SelectionService
Responsibilities:
	•	current selected segments
	•	range selection
	•	source/group scoped selection behavior

Analysis

BasicProbeRunner
Responsibilities:
	•	run ffprobe basic JSON
	•	parse to ProbeSummary

KeyframeAnalyzer
Responsibilities:
	•	progressive keyframe scan
	•	cache keyframe times
	•	expose nearest previous/next keyframe API

WaveformAnalyzer
Responsibilities:
	•	decode audio
	•	compute peak pyramid
	•	cache

ThumbnailAnalyzer
Responsibilities:
	•	viewport-priority frame extraction
	•	cache

DiagnosticsService
Responsibilities:
	•	compute structural warnings from probe/analysis
	•	update source diagnostic badges

Export

CompatibilityAnalyzer
Responsibilities:
	•	compare segment/group sources
	•	produce hard blockers and warnings

ExportPolicyEngine
Responsibilities:
	•	map assessment to allowed plans and approval requirements

ExportPlanner
Responsibilities:
	•	build ExportPlan from request + assessment + policy

FfmpegExecutor
Responsibilities:
	•	execute plan steps
	•	manage temp files
	•	stream progress/logs
	•	produce ExportResult

Persistence

ProjectSerializer
Responsibilities:
	•	read/write JSON
	•	schema migration
	•	validation

AutosaveService
Responsibilities:
	•	periodic autosave
	•	quick session persistence
	•	restore last quick session by source fingerprint

RelinkService
Responsibilities:
	•	detect missing/changed sources
	•	search candidates
	•	apply relink updates

Key state models

AppState
	•	current project ID
	•	active source ID
	•	active assembly group ID
	•	active segment ID
	•	preview playhead us
	•	settled playhead us
	•	drag state
	•	in/out marks
	•	playback state
	•	visible diagnostics
	•	background job states
	•	export job states

ProjectState
	•	sources: dict[source_id, MediaSource]
	•	segments_by_source: dict[source_id, list[Segment]]
	•	assembly_groups: dict[group_id, AssemblyGroup]
	•	tag_catalog
	•	export_history
	•	project_settings_snapshot
	•	ui_state_snapshot

Core command names
	•	OpenSource
	•	LoadProject
	•	SaveProject
	•	RestoreQuickSession
	•	SetActiveSource
	•	SeekApprox
	•	SeekExact
	•	Play
	•	Pause
	•	FrameStepForward
	•	FrameStepBackward
	•	JumpNextKeyframe
	•	JumpPrevKeyframe
	•	SetInMark
	•	SetOutMark
	•	ApplyInOutToSelection
	•	SplitAtPlayhead
	•	AddCutPoint
	•	SliceByCutPoints
	•	ToggleSegmentDisabled
	•	SoftDeleteSegment
	•	RestoreSegment
	•	SelectSegments
	•	SetSegmentLabel
	•	SetSegmentTags
	•	CreateAssemblyGroup
	•	AddSegmentToAssembly
	•	RemoveSegmentFromAssembly
	•	MoveAssemblyItem
	•	RequestExport
	•	ApproveRiskyCopyExport
	•	ApproveReencodeExport
	•	RelinkSource
	•	RunDiagnostics

Core event names
	•	SourceLoaded
	•	SourceMissing
	•	SourceChanged
	•	ProbeReady
	•	KeyframeMapReady
	•	WaveformReady
	•	ThumbnailsReady
	•	DiagnosticsReady
	•	MpvTimePosChanged
	•	MpvPauseChanged
	•	MpvSeekingChanged
	•	MpvEofReached
	•	MpvRenderUpdate
	•	ExportAssessmentReady
	•	ExportStarted
	•	ExportProgress
	•	ExportWarning
	•	ExportFinished
	•	ExportFailed

Recommended settings schema

playback
	•	hwdec_mode: auto|off|debug_specific
	•	mute_during_scrub: bool = true
	•	resume_after_scrub: bool = false
	•	scrub_send_interval_ms: int = 24
	•	scrub_exact_settle_delay_ms: int = 120
	•	boundary_inspect_exact_mode: bool = true
	•	keep_open: bool = true
	•	show_subtitles_in_preview: bool = true
	•	volume: int
	•	remember_volume: bool

analysis
	•	auto_probe_on_open: bool = true
	•	auto_keyframe_scan: bool = true
	•	auto_waveform: bool = true
	•	auto_thumbnails: bool = true
	•	viewport_priority_analysis: bool = true
	•	max_cpu_postprocess_workers: int
	•	max_parallel_external_jobs: int
	•	deep_diagnostics_on_open: bool = false

export
	•	default_policy_preset_id
	•	default_stream_preset_id
	•	default_naming_preset_id
	•	default_output_mode: separate|merge|ask
	•	default_container
	•	default_overwrite_mode: ask|unique_name
	•	default_timestamp_policy: normalize|preserve_advanced
	•	default_metadata_policy: drop|preserve_first_source
	•	default_chapter_policy: drop|preserve_first_source|generate_from_segments
	•	keep_temp_files_on_failure: bool = true

ui
	•	show_disabled_segments: bool = true
	•	timeline_zoom
	•	time_display_mode: seconds|timecode
	•	theme
	•	remember_layout: bool

paths
	•	ffmpeg_path
	•	ffprobe_path
	•	mpv_library_path
	•	cache_dir_override
	•	temp_dir_override

advanced
	•	extra_mpv_options[]
	•	extra_ffmpeg_args[]
	•	log_level

Recommended project-file schema

Top-level:
	•	schema_version
	•	app_version
	•	project_id
	•	project_name
	•	mode: saved|quick
	•	created_at
	•	updated_at

sources[]

Each:
	•	source_id
	•	primary_path
	•	alternate_paths[]
	•	fingerprint
	•	probe_snapshot
	•	duration_us
	•	missing
	•	changed_since_saved

segments[]

Each:
	•	segment_id
	•	source_id
	•	start_us
	•	end_us
	•	state
	•	selected
	•	label
	•	tag_ids[]
	•	notes
	•	created_by_operation
	•	created_at
	•	modified_at

assembly_groups[]

Each:
	•	group_id
	•	name
	•	items[]: {segment_id, ordinal}
	•	mode_hint

tags[]

Each:
	•	tag_id
	•	name
	•	color
	•	description

preset_refs
	•	policy_preset_id
	•	stream_preset_id
	•	naming_preset_id

export_history[]

Each:
	•	export_id
	•	timestamp
	•	request_snapshot
	•	assessment_snapshot
	•	plan_snapshot
	•	result_snapshot
	•	output_paths[]

ui_state
	•	active_source_id
	•	active_group_id
	•	timeline_zoom
	•	selected_segment_ids[]

Recommended preset schema

Policy preset
	•	preset_id
	•	name
	•	description
	•	off_keyframe_action: block|warn|allow_best_effort|auto_adjust
	•	incompatible_merge_action: block|warn|allow_common_streams|require_reencode
	•	reencode_allowed: bool
	•	timestamp_policy
	•	metadata_policy
	•	chapter_policy
	•	attachment_policy
	•	default_output_mode
	•	default_container

Stream preset
	•	preset_id
	•	name
	•	video_mode: all|primary|selected|none
	•	audio_mode: all|default|selected|none
	•	subtitle_mode: all|selected|none
	•	data_mode: all|selected|none
	•	attachment_mode: preserve_single_source_only|drop
	•	common_streams_only_on_merge: bool

Naming preset
	•	preset_id
	•	name
	•	template
	•	sanitize: strict
	•	collision_policy: unique_suffix|overwrite_never

Suggested logging schema

Each log record:
	•	ts
	•	level
	•	subsystem
	•	event
	•	session_id
	•	project_id
	•	source_id
	•	segment_id
	•	group_id
	•	job_id
	•	tool
	•	program
	•	args[]
	•	cwd
	•	exit_code
	•	elapsed_ms
	•	warning_codes[]
	•	error_code
	•	message
	•	exception
	•	os
	•	app_version
	•	tool_versions

Staged build order
	1.	infra/tool locator + logging
	2.	ffprobe basic probe parser
	3.	libmpv render widget prototype
	4.	playback controller + scrub controller
	5.	project/domain models
	6.	split / mark in-out / slice commands + undo
	7.	minimal timeline + segment lane UI
	8.	single-segment export planner + executor
	9.	multi-segment separate export
	10.	temp-segment + concat merge export
	11.	compatibility analyzer + warnings
	12.	quick session autosave
	13.	relink flow
	14.	waveform/thumbnails
	15.	packaging
	16.	deep diagnostics polish

⸻

PHASE 4 — Approval-gated work separation

A. Safe to scaffold immediately
	•	PyQt6 app skeleton
	•	QWidget UI shell
	•	QOpenGLWidget mpv render wrapper
	•	internal libmpv binding layer
	•	tool locator and version manifest
	•	ffprobe runner + parser
	•	project/domain models
	•	segment/assembly/tag models
	•	undo/redo framework
	•	timeline/segment-lane/source-bin UI
	•	quick-session/autosave infrastructure
	•	relink infrastructure
	•	logging and diagnostics plumbing
	•	export assessment data structures
	•	stream preset / policy preset / naming preset models

B. Safe to implement without further approval
	•	single-source playback, seek, scrub, pause, frame-step
	•	split-at-playhead
	•	mark in/out
	•	cut-point slicing
	•	soft-disable / soft-delete / restore
	•	labels/tags
	•	selected segments export separately
	•	selected segments merge into one output when copy-compatible
	•	same-file multi-segment temp-export + concat demuxer workflow
	•	multi-file compatibility analysis and warnings
	•	default export policy = warn and ask
	•	metadata/chapter default drop on merge
	•	background keyframe/thumbnails/waveform analysis
	•	quick session restore
	•	saved project open/save/migrate
	•	moved-file relink flow
	•	packaging/build scripts without final distribution-license decision baked in

C. Requires explicit approval before implementing

Call these out clearly in product review before coding them:

Output-fidelity / re-encode sensitive
	•	any automatic re-encode behavior
	•	any silent auto-adjust of segment boundaries
	•	any “smart cut” / edge re-encode
	•	any fallback that changes codecs without an explicit user confirmation
	•	any silent stream dropping on merge/export

Destructive actions
	•	overwriting existing outputs by default
	•	permanent delete of project/session/source files
	•	auto-pruning temp files in ways that can destroy debug evidence without user control

Packaging / licensing sensitive
	•	final distribution model if app is not GPL
	•	commercial PyQt licensing purchase/use
	•	bundling GPL-enabled FFmpeg or mpv builds
	•	bundling patented encoders/decoders with commercial distribution assumptions
	•	final license notices / compliance flow / source-offer packaging

Heavy optional features outside v1
	•	continuous multi-file assembly playback timeline
	•	proxy media
	•	automatic scene detection
	•	smart edge re-encode
	•	full sequence timeline editor
	•	in-app auto-updater
	•	remote telemetry / crash upload

⸻

PHASE 5 — Test and validation matrix

Feature test matrix

Playback
	•	open file
	•	first frame render
	•	play / pause
	•	drag scrub
	•	exact settle after scrub
	•	seek by click
	•	jump prev/next keyframe
	•	frame step forward/back
	•	EOF park / keep-open
	•	hidden/minimized/restore behavior
	•	source switch while background jobs running

Editing
	•	split at playhead
	•	mark in/out create segment
	•	mark in/out trim existing segment
	•	cut-point slicing
	•	multi-select segments
	•	enable/disable segment
	•	soft-delete/restore segment
	•	label/tag edit
	•	undo/redo for all edit actions

Export
	•	separate export, one segment
	•	separate export, many segments
	•	merged export, same file
	•	merged export, multi-file compatible
	•	warning on off-keyframe
	•	warning on incompatible merge
	•	no silent re-encode
	•	no silent stream drop
	•	metadata/chapter policies applied correctly
	•	naming preset output names correct

Persistence
	•	quick session autosave/load
	•	save/open project
	•	project migration
	•	source relink
	•	changed-source warning after reopen

File-type / media-fixture matrix

For each OS, validate at least:
	•	H.264 1080p CFR MP4
	•	H.264 long-GOP MP4
	•	HEVC 10-bit MP4/MKV
	•	VFR phone video
	•	MKV multi-audio multi-subtitle
	•	MKV with attachments/fonts
	•	MPEG-TS / M2TS
	•	AAC audio-only
	•	FLAC audio-only
	•	no-audio video
	•	no-video audio
	•	truncated/corrupt file
	•	very long file (>2h)
	•	4K60 high-bitrate sample
	•	multi-file compatible merge set
	•	multi-file incompatible merge sets

Cross-platform validation checklist

Windows
	•	bundled app launch
	•	Unicode paths
	•	spaces in paths
	•	absolute tool invocation
	•	hardware decode auto/off
	•	resize/HiDPI
	•	signed build launch
	•	export with bundled ffmpeg

macOS
	•	.app launch
	•	signed/notarized bundle
	•	Retina sizing
	•	Apple Silicon + Intel
	•	sandbox-ish path quirks if any
	•	libmpv and ffmpeg load from bundle
	•	export with bundled tools

Linux
	•	AppImage/tarball launch
	•	X11 playback
	•	Wayland playback
	•	system fallback paths
	•	hardware decode auto/off
	•	export with bundled or overridden tools

Playback quality validation checklist
	•	scrub feels responsive on 1080p H.264
	•	scrub remains usable on 4K HEVC
	•	settle behavior lands consistently after drag release
	•	no obvious UI starvation while scrubbing
	•	no stale frame after exact settle
	•	frame step works on CFR samples
	•	VFR files show appropriate warning/diagnostic
	•	hidden/minimize/restore does not produce frozen player
	•	hardware decode fallback is visible in diagnostics

Export correctness checklist
	•	output files created where expected
	•	output names follow template
	•	separate outputs start/end within policy expectations
	•	merged output ordering matches selected segments/groups
	•	output stream list matches requested stream preset
	•	no re-encode when copy plan chosen
	•	warning shown when exact lossless impossible
	•	metadata/chapter policy respected
	•	temp cleanup behavior correct on success/failure

Merge compatibility checklist
	•	hard blocker on stream-count/type mismatch
	•	hard blocker on codec/time-base mismatch
	•	warning on VFR-rate mismatch
	•	warning on stream metadata mismatch
	•	correct concat path for compatible temp segments
	•	no silent container change
	•	no silent stream drop

Performance validation checklist
	•	player open latency acceptable with large files
	•	background analysis does not break basic playback
	•	keyframe scan scalable on large files
	•	waveform build memory bounded
	•	thumbnail generation cancellable/prioritized
	•	many segments in UI remain interactive
	•	export logs do not block UI
	•	relink scan remains responsive with many sources

⸻

Recommended v1 architecture in one paragraph

A stable v1 should be a PyQt6 QWidget desktop app with a single QOpenGLWidget-based libmpv render surface for preview, a time-based domain model of ordered source-relative segments, a separate assembly/export-group abstraction for merges, ffprobe-driven analysis for authoritative metadata/keyframes, and FFmpeg CLI plans for all exports/remux/concat operations. Playback should prioritize approximate scrub responsiveness first and exact settle second, while export should prioritize lossless stream copy by default with explicit warnings whenever exact lossless output is not possible. Keep UI, domain, playback, analysis, export, and persistence as separate layers so the app stays debuggable, testable, and later-extendable.  ￼  ￼  ￼

Top 10 technical risks
	1.	QOpenGLWidget + libmpv render smoothness on 4K/10-bit hardware
	2.	Hidden/minimized player timing/freeze behavior
	3.	Off-keyframe copy exports being perceived as “wrong”
	4.	Timestamp normalization across weird MP4/TS/VFR files
	5.	Cross-file concat compatibility false positives
	6.	Linux X11/Wayland hwdec interop differences
	7.	Project relink to near-but-not-identical sources
	8.	Over-warning vs under-warning in export UX
	9.	PyQt6/mpv/FFmpeg licensing/compliance decisions
	10.	macOS bundle signing/notarization with bundled CLI/media libs

Top 10 prototype tasks to validate first
	1.	QOpenGLWidget + libmpv render prototype on Windows/macOS/Linux
	2.	Approximate drag scrub + exact settle controller
	3.	ffprobe basic probe + keyframe scan parser
	4.	Single-source stream-copy export with warning assessment
	5.	Off-keyframe UX: warn / cancel / proceed best-effort
	6.	Temp-segment + concat-demuxer merged export
	7.	Cross-file compatibility analyzer with hard-block vs warn
	8.	Quick-session autosave + reopen + relink
	9.	Background waveform/thumbnails while playback stays responsive
	10.	First packaged build with bundled libmpv + ffmpeg/ffprobe + compliance manifest