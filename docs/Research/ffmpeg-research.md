# FFmpeg research report

## Executive Summary

FFmpeg is best understood as a modular multimedia platform rather than only a command-line transcoder: the project ships a set of reusable libraries (`libavcodec`, `libavformat`, `libavfilter`, `libavutil`, `libavdevice`, `libswresample`, `libswscale`) plus end-user tools such as `ffmpeg`, `ffplay`, and `ffprobe`.[^1] Its core processing model is explicit and stable: data flows through demuxers, decoders, filtergraphs, encoders, and muxers, while "streamcopy" skips decode/filter/encode entirely and moves encoded packets directly from demuxer to muxer.[^2]

The public C APIs mirror that architecture closely. `libavformat` opens inputs, discovers streams, and owns mux/demux state; `libavcodec` exposes the modern send/receive API for encode/decode; `libavfilter` models processing as filter graphs; and `libavutil` now uses `AVChannelLayout` to represent native, custom, and ambisonic audio layouts.[^3][^4][^5][^6]

FFmpeg is also intentionally build-time configurable. External codec or acceleration libraries are not enabled by default, are generally turned on via `./configure` flags, and can materially change the resulting binary's license and redistributability through `--enable-gpl`, `--enable-version3`, and `--enable-nonfree`.[^7][^8][^9]

Operationally, current `ffmpeg` is no longer just a single-threaded wrapper over library calls. The CLI has a scheduler with pthread-backed tasks, queues, dedicated demux/mux worker threads, and release notes that describe major pipeline components running in parallel for better throughput and latency.[^10][^11]

## Architecture/System Overview

At a high level, FFmpeg's documented and implemented processing pipeline looks like this:[^2][^10]

```text
Input URL / device / stream
          |
          v
     ┌─────────┐      encoded packets
     │ Demuxer │------------------------------┐
     └─────────┘                              |
          |                                   |
          v                                   v
     ┌─────────┐                        ┌─────────┐
     │ Decoder │   raw frames           │  Muxer  │  (streamcopy path)
     └─────────┘----------┐             └─────────┘
                          v
                   ┌──────────────┐
                   │ Filtergraph  │
                   └──────────────┘
                          |
                          v
                     ┌─────────┐   encoded packets
                     │ Encoder │--------------------> Muxer -> output URL
                     └─────────┘
```

That model matters because most of FFmpeg's user-facing behavior follows from it: option ordering is file-scoped, `-map` controls stream routing, filtering only operates on decoded frames, and `-c copy` works because muxers can consume packets directly without transcoding.[^2]

## Project surfaces

| Surface | Role | What it is best for |
|---|---|---|
| [FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg) | Source repository | Headers, CLI implementation, build system, docs sources, examples[^1] |
| [ffmpeg.org](https://www.ffmpeg.org/) | Project website | Release notes, project news, canonical user-facing entry point[^11] |
| [documentation.html](https://ffmpeg.org/documentation.html) | Published API docs index | Versioned and nightly Doxygen/API browsing[^12] |
| [trac.ffmpeg.org/wiki/CompilationGuide](https://trac.ffmpeg.org/wiki/CompilationGuide) | Wiki/runbook-style docs | Platform-specific compilation guidance and build tips[^13] |

## Core components

### Libraries and tools

The repository README is the clearest compact inventory of FFmpeg's shipped surfaces. It describes the core libraries as codec implementation (`libavcodec`), container/protocol/basic I/O (`libavformat`), utility functionality (`libavutil`), graph-based audio/video processing (`libavfilter`), device abstraction (`libavdevice`), resampling/mixing (`libswresample`), and color conversion/scaling (`libswscale`). The same README identifies the primary tools: `ffmpeg` for manipulation/conversion/streaming, `ffplay` as a minimal player, and `ffprobe` as an inspection tool.[^1]

Practically, this means "FFmpeg" can refer to three different things depending on context: the project, the libraries, or the `ffmpeg` executable. That distinction matters for architecture discussions, because the CLI is a consumer of the libraries rather than the entirety of the platform.[^1][^2]

### Command-line pipeline semantics

The `doc/ffmpeg.texi` manual defines `ffmpeg` as a "universal media converter" that reads arbitrary inputs and writes arbitrary outputs, with command-line options applying to the next input or output file unless the option is global.[^2] The same source walks through the pipeline components in order: demuxers split inputs into encoded packets; decoders turn packets into raw frames; filtergraphs transform frames; encoders convert frames back into encoded packets; and muxers interleave/write output streams.[^2]

The manual also draws a sharp line between streamcopy and transcoding. Streamcopy is the packet-preserving fast path invoked by `-c copy`; it avoids decoding, filtering, and encoding. Transcoding is necessary when codecs, bitrates, formats, timestamps, or filters need to change, but it is computationally more expensive and often lossy.[^2]

Two design details are especially important in practice:

1. **Simple vs. complex filtergraphs**: simple graphs are attached to one output stream, while `-filter_complex` defines standalone graphs with multiple inputs/outputs.[^2]
2. **Option ordering and routing**: because options are file-scoped and reset between files, input/output order and `-map` placement are core semantics, not incidental syntax.[^2]

## Public API deep dive

### `libavformat`: opening, probing, and I/O ownership

`libavformat` documents its basic demuxing sequence as `avformat_open_input()` to open an input, `av_read_frame()` to read encoded packets, and `avformat_close_input()` for cleanup.[^3] The header explicitly recommends calling `avformat_find_stream_info()` after opening because some formats do not expose enough stream metadata in headers alone.[^3]

`AVFormatContext` is the central mux/demux object. Its documentation says it owns or references the chosen input/output format, private format data, I/O context, stream lists, and file-level flags and metadata; it also records demuxer-populated state such as streams/groups that may appear either during open or later during packet reads for no-header formats.[^3] The API also exposes knobs for advanced callers, including custom `AVIOContext` wiring, nonblocking packet reads via `AVFMT_FLAG_NONBLOCK`, analysis sizing via `probesize` and `max_analyze_duration`, and interrupt callbacks for the I/O layer.[^3]

The key architectural takeaway is that `libavformat` does not only "parse containers"; it is the ownership boundary for stream discovery, probing heuristics, container metadata, and I/O policy.[^3]

### `libavcodec`: the send/receive state machine

`libavcodec`'s header explicitly describes the modern encode/decode API as the `avcodec_send_packet() / avcodec_receive_frame()` and `avcodec_send_frame() / avcodec_receive_packet()` pairs.[^4] The design goal is decoupling input from output, so callers submit compressed packets for decoding or raw frames for encoding, then drain outputs in a loop until they see `AVERROR(EAGAIN)` or EOF conditions.[^4]

The important detail is that the API is intentionally state-machine-like. The documentation says the codec may buffer internally, draining is triggered by sending `NULL`, and the implementation is not allowed to return `EAGAIN` on both send and receive in a way that would create deadlock or time-dependent ambiguity.[^4] That is one of the most consequential FFmpeg API design choices of the last several years: callers are expected to write explicit pump/drain loops rather than assume one-input/one-output behavior.[^4]

### `libavfilter`: graph-first processing

`libavfilter` models processing around `AVFilterContext` and `AVFilterGraph`.[^5] The public API exposes allocation (`avfilter_graph_alloc()`), per-filter allocation (`avfilter_graph_alloc_filter()`), parsing (`avfilter_graph_parse()`, `avfilter_graph_parse_ptr()`, `avfilter_graph_parse2()`), and final graph validation/configuration (`avfilter_graph_config()`).[^5]

This is consistent with the CLI manual's description of filtergraphs as either simple linear chains or multi-input/multi-output complex graphs.[^2][^5] The library API makes the graph a first-class runtime object, which is why advanced uses such as overlays, splits, fan-out, and cross-stream audio/video composition can be represented without special-purpose transcoding code for each case.[^2][^5]

### `libavutil`: `AVChannelLayout` and modern audio layout handling

The current audio channel layout API in `libavutil/channel_layout.h` supports multiple ordering modes: unspecified, native, custom, and ambisonic.[^6] `AVChannelLayout` stores both `nb_channels` and per-order details, including a native bitmask representation, custom channel maps, and ambisonic layout helpers/macros.[^6]

The header also provides constructors and converters such as `av_channel_layout_custom_init()`, `av_channel_layout_from_mask()`, `av_channel_layout_default()`, and `av_channel_layout_ambisonic_order()`.[^6] This matters because modern FFmpeg audio APIs no longer assume that every layout can be faithfully represented by a single legacy speaker-mask bitfield; the data model explicitly accommodates custom ordering and ambisonic representations.[^6]

## CLI internals and performance characteristics

The `fftools/ffmpeg_sched.c` implementation shows that the current CLI uses a dedicated scheduler object with arrays of demuxers, muxers, decoders, encoders, sync queues, and filter graphs, plus mutexes/condition variables for readiness, completion, and scheduling state.[^10] Queue allocation is explicit for both frame and packet queues, and task startup uses `pthread_create()` to spawn worker threads.[^10]

The same scheduler file exposes `sch_add_mux()` and `sch_add_demux()` registration functions, making muxers and demuxers first-class scheduled tasks rather than incidental library calls from a single loop.[^10] That architecture is visible in the worker implementations:

- `fftools/ffmpeg_demux.c` runs `input_thread()`, which repeatedly calls `av_read_frame()`, handles `EAGAIN`/EOF/error paths, applies packet processing, and forwards packets downstream.[^10]
- `fftools/ffmpeg_mux.c` runs `muxer_thread()`, which receives scheduled packets, remaps stream indices, applies mux packet filtering, and signals stream completion/EOF handling.[^10]

This source-level design lines up with the project's own release communication. The FFmpeg website states that major components of the CLI pipeline now run in parallel, with improvements aimed at throughput, CPU utilization, and latency, and later release notes continue to emphasize threaded CLI and hardware-accelerated pipeline work.[^11]

The practical implication is that performance discussions about `ffmpeg` need two layers of thinking:

1. **Library-level codec performance**: codec/filter/container cost still dominates many workloads.[^4][^5]
2. **CLI orchestration performance**: packet/frame movement, queueing, and per-stage threading now matter more than they did in older single-loop versions of the tool.[^10][^11]

## Build, external integrations, and platform support

FFmpeg's build system is `./configure`-driven. The top-level configure help lists license switches (`--enable-gpl`, `--enable-version3`, `--enable-nonfree`) and major build-shaping options such as `--enable-shared`, `--disable-all`, and `--disable-autodetect`.[^7] That last flag is particularly important for reproducible/minimal builds because FFmpeg can otherwise auto-detect some external libraries on the build machine.[^7]

The external library guide is explicit that these integrations are opt-in, not default. Examples called out in the docs include `--enable-libaom`, `--enable-amf`, `--enable-libdav1d`, `--enable-libjxl`, `--enable-libvpx`, and `--enable-libx264`.[^8] In other words, FFmpeg's shipped source tree is intentionally designed to be a framework that can wrap native implementations, external software codecs, and hardware/vendor SDKs depending on how it is configured.[^7][^8]

For building from source, the Trac wiki acts as the practical runbook. It points readers first to a generic compilation guide, then to platform-specific guides for Linux, macOS, and Windows, and also includes performance notes such as `-march=native`, `--arch`/`--cpu`, and the trade-offs of `--enable-hardcoded-tables`.[^13]

## Licensing and redistribution

Licensing is one of FFmpeg's most operationally significant design constraints. `LICENSE.md` says the codebase is primarily LGPL v2.1+ with some MIT/X11/BSD-style files, while optional GPL components remain disabled unless `--enable-gpl` is passed.[^9] The same file states that `--enable-version3` upgrades the applicable LGPL/GPL license family to v3, and `--enable-nonfree` allows otherwise incompatible combinations at the cost of producing unredistributable binaries.[^9]

The license matrix becomes concrete when external libraries are added. `LICENSE.md` names `libx264`, `libx265`, and several others as GPL-triggering integrations; it also calls out Apache-2.0 libraries that require version-3 upgrading and explicitly notes that nonfree combinations include things like Fraunhofer FDK AAC and OpenSSL in certain scenarios.[^9] This is why "How was FFmpeg built?" is often as important as "What version of FFmpeg is this?" when diagnosing packaging or redistribution issues.[^7][^9]

## `ffprobe`, documentation, and usage in practice

`ffprobe` exists specifically for inspection rather than transformation. Its manual says it gathers information from multimedia streams and prints it in human- and machine-readable form, organizing output into named sections such as `FORMAT`, `STREAM`, `PROGRAM_STREAM`, and others.[^14] The same manual documents structured output modes through writers, including JSON via `-output_format json`.[^14]

That makes `ffprobe` the stable companion tool for automation, metadata extraction, and programmatic media introspection, while `ffmpeg` remains the transform/streaming tool.[^1][^14]

Documentation is split across several layers:

- the repository's `doc/` directory contains offline/manpage sources and coding examples;[^1]
- the published documentation index states that API docs are regenerated nightly and versioned Doxygen references are kept online;[^12]
- the wiki adds practical build and troubleshooting guidance that is complementary to the manpages and headers.[^13]

## Governance and contribution workflow

FFmpeg's contribution workflow is not GitHub-PR-centric. The README says patches should go to the `ffmpeg-devel` mailing list via `git format-patch` or `git send-email`, and warns that GitHub pull requests are not part of the core review process.[^15] The developer documentation refines that: code changes are reviewed on Forgejo or the mailing list, contributors are expected to subscribe to `ffmpeg-devel`, patch submission should use `git format-patch`/`git send-email`, and Patchwork is the place to verify mailing-list patch ingestion.[^15]

For teams consuming FFmpeg, this matters because the best design rationale often lives in commit messages, mailing-list reviews, and release notes rather than in GitHub PR discussions.[^11][^15]

## Key conclusions

FFmpeg's enduring strength is the consistency between its documentation model, public APIs, and CLI implementation: the same demux/decode/filter/encode/mux abstraction appears in the manuals, headers, and scheduler code.[^2][^3][^4][^5][^10] Its flexibility comes from build-time composition, not from a single monolithic binary image: codecs, accelerators, and even license posture are partially determined by how `./configure` is invoked.[^7][^8][^9]

If you are integrating FFmpeg into an application, the most important practical distinctions are:

1. **Library vs. CLI**: use the libraries when you need embedded media pipelines; use `ffmpeg`/`ffprobe` when a process boundary is acceptable.[^1][^3][^4][^14]
2. **Streamcopy vs. transcode**: choose packet-preserving copy when possible, and only pay decode/filter/encode costs when output semantics actually require it.[^2]
3. **Build provenance**: external-library enablement and license flags are part of the product definition, not incidental packaging metadata.[^7][^8][^9]
4. **Performance model**: current CLI behavior includes real internal scheduling/threading, but end-to-end speed is still dominated by codec/filter choices and hardware acceleration support.[^8][^10][^11]

## Confidence Assessment

**High confidence:** the library/tool decomposition, command-line pipeline semantics, API contracts (`avformat_*`, `avcodec_send/receive`, `avfilter_graph_*`, `AVChannelLayout`), configure flags, license behavior, and contribution workflow are all directly documented in upstream source files or official project pages.[^1][^2][^3][^4][^5][^6][^7][^8][^9][^10][^12][^13][^15]

**Moderate confidence:** statements about performance direction and "modern FFmpeg" pipeline threading are well-supported by current scheduler code and official release notes, but exact performance outcomes remain workload-dependent and are not guaranteed by architecture alone.[^10][^11]

**Inferred but reasonable:** where this report talks about operational implications (for example, that build provenance is often decisive in support/debugging, or that mailing-list discussion is where design rationale often lives), that is synthesis based on the documented license/build matrix and official contribution model rather than a single source line spelling it out verbatim.[^7][^9][^15]

## Footnotes

[^1]: `README.md:4-35` in [FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg) at branch-tip commit `e64a1d29532d89f0dc515da55343d3a3caa78ead`.
[^2]: `doc/ffmpeg.texi:20-52,90-109,142-162,212-234,265-315,433-480` in [FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg) at branch-tip commit `e64a1d29532d89f0dc515da55343d3a3caa78ead`.
[^3]: `libavformat/avformat.h:51-130,1265-1300,1413-1457,1513-1532` in [FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg) at branch-tip commit `e64a1d29532d89f0dc515da55343d3a3caa78ead`.
[^4]: `libavcodec/avcodec.h:92-177,2364-2444` in [FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg) at branch-tip commit `e64a1d29532d89f0dc515da55343d3a3caa78ead`.
[^5]: `libavfilter/avfilter.h:271-281,589-654,729-840` in [FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg) at branch-tip commit `e64a1d29532d89f0dc515da55343d3a3caa78ead`.
[^6]: `libavutil/channel_layout.h:119-155,292-352,384-441,508-552,702-709,736-740` in [FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg) at branch-tip commit `e64a1d29532d89f0dc515da55343d3a3caa78ead`.
[^7]: `configure:97-113,217,301,304` in [FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg) at branch-tip commit `e64a1d29532d89f0dc515da55343d3a3caa78ead`.
[^8]: `doc/general_contents.texi:3-14,24-29,105-106,190-200,338-340` in [FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg) at branch-tip commit `e64a1d29532d89f0dc515da55343d3a3caa78ead`.
[^9]: `LICENSE.md:3-11,61-64,79-123,125-127` in [FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg) at branch-tip commit `e64a1d29532d89f0dc515da55343d3a3caa78ead`.
[^10]: `fftools/ffmpeg_sched.c:273-312,320-423,620-742`, `fftools/ffmpeg_demux.c:730-833`, and `fftools/ffmpeg_mux.c:407-455` in [FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg) at branch-tip commit `e64a1d29532d89f0dc515da55343d3a3caa78ead`.
[^11]: [FFmpeg home page](https://www.ffmpeg.org/), especially the news entries dated 2023-12-12, 2024-04-05, 2025-08-22, and 2026-03-16.
[^12]: [FFmpeg documentation index](https://ffmpeg.org/documentation.html), which states that API documentation is regenerated nightly and publishes versioned Doxygen references.
[^13]: [FFmpeg Compilation Guide](https://trac.ffmpeg.org/wiki/CompilationGuide), including the generic guide, platform-specific compilation pages, and performance tips.
[^14]: `doc/ffprobe.texi:20-52,92-101,143-152,203-248` in [FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg) at branch-tip commit `e64a1d29532d89f0dc515da55343d3a3caa78ead`.
[^15]: `README.md:42-45` and `doc/developer.texi:47-50,664-667,711-743,767-769` in [FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg) at branch-tip commit `e64a1d29532d89f0dc515da55343d3a3caa78ead`.
