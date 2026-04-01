# mpv Research Report

## Executive Summary

mpv is best understood as **both** a command-line media player and a reusable playback engine whose public control surfaces all converge on the same underlying command/property model.[^1][^2] Internally, the `player/*.c` "frontend" owns initialization, playlist traversal, and the playback loop, while streams, demuxers, filters, decoders, subtitle rendering, audio output, and video output are split into dedicated subsystems beneath it.[^3][^4][^5] The project is intentionally CLI-first: it exposes a configurable command-driven input layer, has **no official full GUI** beyond the OSC, and expects third-party frontends or embedders to use either JSON IPC or, more commonly, `libmpv`.[^6][^7][^8]

Technically, mpv’s identity is strongly tied to a **shader-based rendering pipeline**: the README explicitly says the main video output uses shaders instead of fixed-function GPU video hardware, and the source tree centers that work in `video/out/gpu/*` plus `libmpv` render adapters.[^9][^10][^11] Embedding-wise, both the client API and render API docs recommend the render API over native window embedding, largely because embedding native windows causes cross-toolkit and cross-platform issues.[^12][^13] Extensibility is a first-class design goal: built-in Lua scripts provide core UX features like OSC, console, stats, select, and `ytdl_hook`, while user-extensible Lua, JavaScript, C plugins, shaders, and community scripts sit on top of the same control plane.[^14][^15][^16][^17]

## Architecture/System Overview

```text
                    ┌────────────────────────────────────┐
                    │           mpv frontend             │
                    │ player/main.c, playloop, command   │
                    └────────────────────────────────────┘
                                │
                ┌───────────────┼────────────────┬───────────────────┐
                │               │                │                   │
                ▼               ▼                ▼                   ▼
      ┌────────────────┐ ┌──────────────┐ ┌───────────────┐ ┌────────────────┐
      │ stream/*       │ │ demux/*      │ │ input/*       │ │ player/client  │
      │ file/network   │ │ packets, PTS │ │ keybindings,  │ │ libmpv handles │
      │ sources        │ │ cache, tracks│ │ commands, IPC │ │ + event queues │
      └────────────────┘ └──────────────┘ └───────────────┘ └────────────────┘
                │               │                │                   │
                └───────┬───────┴────────┬───────┴───────────────────┘
                        ▼                ▼
                 ┌──────────────┐ ┌──────────────────────┐
                 │ filters/*    │ │ scripting backends   │
                 │ decode/output│ │ Lua / JS / C / run   │
                 │ conversions  │ │ + built-in scripts   │
                 └──────────────┘ └──────────────────────┘
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
   ┌────────────────┐      ┌───────────────────────┐
   │ audio/*        │      │ video/out/*           │
   │ decode/output  │      │ GPU VOs, libmpv       │
   │ video sync base│      │ render adapters, OSD  │
   └────────────────┘      └───────────────────────┘
```

At a high level, mpv’s own technical overview says `player/*.c` initializes subsystems and pushes data between them during playback, while `main()` creates the context, initializes it, and then calls `mp_play_files()` to work through the playlist.[^3][^18] The same overview describes `input/input.c` as translating keyboard, remote, and client-API-originated actions into `mp_cmd` commands, `demux/*` as splitting streams into timestamped packets, `filters/*` as the generic transformation framework, and `video/out/*` as the output layer that also owns windows and input integration.[^5][^19][^20]

## Core Playback Architecture

The core runtime is intentionally centralized. The mpv technical overview calls `player/*.c` the "frontend," says most state lives in `MPContext`, and notes that `run_playloop()` is the function that does the ongoing playback work: decoding audio/video, waiting for input, and advancing playback state.[^3][^4] The actual CLI entry point in `player/main.c` is correspondingly small: `mpv_main()` creates an `MPContext`, runs `mp_initialize()`, and then, if initialization succeeds, calls `mp_play_files()`.[^18]

The project’s architectural split is practical rather than purely academic. Commands and properties live in `player/command.c`, which the overview describes as the implementation point for user commands such as seeking and track switching; `player/client.c` implements the client API and manages the event ringbuffer between the player and clients.[^21] That explains why the CLI, scripts, JSON IPC, and `libmpv` feel so similar in practice: they are distinct front doors into the same command/property machinery, not four unrelated APIs.[^2][^6][^21]

Data flow is similarly explicit. Streams provide byte-oriented access to files, HTTP sources, and special prefixed inputs; demuxers turn those streams into audio/video/subtitle packet streams tagged with PTS; filters convert and adapt frames; then audio and video output layers consume the filtered results.[^19][^20] The overview also calls out an operational consequence that many embedders overlook: mpv synchronizes **video to audio**, so buggy audio drivers can materially degrade playback quality.[^22]

## Control, Embedding, and External Integration

mpv’s public control model is command-centric from top to bottom. The manpage says mpv has a "fully configurable, command-driven control layer," and the libmpv client header says nearly all real interaction happens through **options, commands, and properties**, including file loading and progress queries.[^6][^2] That shared model is the conceptual key to understanding mpv: the CLI, scripting APIs, `libmpv`, and JSON IPC are different transport layers over a largely common semantic surface.[^2][^6][^8]

### `libmpv`

`libmpv` is the recommended embedding surface when mpv is a backend inside a larger application.[^8][^23] The `client.h` header defines it as a general playback-control API that can be used internally by mpv or externally via `mpv_create()` to embed the player, and it documents the event loop model centered on `mpv_wait_event()` and `mpv_set_wakeup_callback()`.[^2][^24] Each client handle has its **own** event queue, observed-property state, logging state, and async-operation state, even though all handles share the same underlying player core.[^25]

There are two major caveats for embedders. First, the API is thread-safe, but `client.h` explicitly says there is "no real advantage" in using multiple threads against it because everything is serialized through a single lock in the playback core.[^26] Second, event draining is not optional operationally: if you do not empty a handle’s event queue quickly enough with `mpv_wait_event()`, the queue can overflow and asynchronous requests can fail with `MPV_ERROR_EVENT_QUEUE_FULL`.[^24][^27]

The build system reflects how central `libmpv` is. `meson.build` builds a `library('mpv', ...)`, generates pkg-config metadata, installs `client.h`, `render.h`, `render_gl.h`, and `stream_cb.h`, and even exposes an override dependency so other Meson projects can depend on a checkout under `subprojects/mpv`.[^28]

### Render API vs native window embedding

mpv strongly prefers the render API over attaching a native mpv window to your application. The client header says render API embedding is recommended, while the render header states more directly that using the render API is recommended because window embedding can cause issues with GUI toolkits and some platforms.[^12][^13] The render API is built around `mpv_render_context_create()`, explicit frame rendering, and update callbacks, and the docs recommend rendering on a separate thread.[^13]

That recommendation matters on macOS and GUI-toolkit integrations in particular. mpv does still support older `wid`-style embedding, but both headers frame it as the compatibility path rather than the preferred design.[^12][^13] For low-performance or non-GPU scenarios there is also a software render API, but `render.h` is blunt that it is extremely simple **and slow**, with color conversion, scaling, OSD, and subtitle rendering done on the CPU in a single thread.[^29]

### JSON IPC

JSON IPC is mpv’s process-external remote-control interface. The IPC manual says mpv can be controlled by external programs over a JSON-based protocol enabled with `--input-ipc-server` or `--input-ipc-client`, using a Unix socket or named pipe.[^30] The main manpage positions this as the recommended way to do interactive control or remote control from outside the terminal, while also warning that the protocol is **not secure** and is intended for local control.[^7][^31]

The implementation matches the docs closely. `input/ipc.c` parses JSON requests, recognizes async mode and request IDs, writes JSON replies, and falls back to plain text command execution when the incoming line does not start with `{`.[^32][^33] In other words, JSON IPC is not a separate execution engine; it is a socket/pipe adapter over the same command API and event model that powers the rest of mpv.[^21][^32]

## Scripting and Extensibility

Scripting is not a bolt-on feature in mpv; it is part of the default product surface. The scripting dispatcher registers Lua, C plugins, JavaScript, and a process-oriented `run` backend in `scripting_backends[]`.[^14] The built-in script loader then brings in core UX scripts such as `@osc.lua`, `@ytdl_hook.lua`, `@stats.lua`, `@console.lua`, `@auto_profiles.lua`, `@select.lua`, `@positioning.lua`, `@commands.lua`, and `@context_menu.lua`.[^15] Separately, `mp_load_scripts()` loads explicit `--script` entries and, if auto-loading is enabled, scans the configured `scripts` directories and loads everything it finds there.[^16]

That split explains an important practical point: some things users think of as “mpv features” are actually shipped as built-in scripts, especially UI-oriented behaviors like OSC, console, stats, and selection menus.[^15] The README reinforces that dependence by listing Lua as an optional dependency that is nevertheless required for the OSC pseudo-GUI and youtube-dl integration.[^34]

### Lua

Lua remains mpv’s most mature scripting environment. The Lua manual says the default prelude defines the script event loop, and the built-in `mp.options` module lets scripts declare defaults, read config files, and accept command-line `--script-opts` overrides.[^35][^36] Script configuration is namespaced by identifier and stored under `script-opts/<identifier>.conf`, while command-line overrides use `identifier-` prefixes inside `--script-opts=...` to avoid collisions.[^36]

### JavaScript

mpv also ships a JavaScript backend based on **MuJS**, which the JS manual describes as a minimal ES5 interpreter.[^17] The environment intentionally stays narrow: there is no full standard library, interaction outside mpv is mostly via provided APIs such as `mp.utils`, and CommonJS `require()` is available for modularity.[^17] This makes JavaScript support useful for extension authors, but it is not intended to be a Node.js-like general runtime.[^17]

### C plugins and ecosystem scripts

For lower-level native extensions, mpv supports C plugins that use the libmpv API without linking against the `libmpv` shared library itself; the docs say they live in the scripts directory, use `.so`/`.dll`, and are enabled by default where `-rdynamic` support exists (or always on Windows).[^37][^38] Beyond official built-ins, the wiki’s User Scripts page documents a large community ecosystem and explicitly frames most of it as **unofficial third-party scripts** placed under standard per-user `scripts/` directories.[^39] The wiki home page summarizes that extension space as Lua, JavaScript, VapourSynth, and GLSL shaders, and separately points to third-party applications and GUI frontends built on mpv.[^40]

## Rendering and Media Pipeline Characteristics

mpv’s rendering posture is opinionated. The README states that the main video output uses **shaders for rendering and scaling** rather than fixed-function GPU video hardware, and advises enabling hardware decoding explicitly with `--hwdec` rather than assuming it is on by default.[^9] The technical overview further says `video/out/*` is the layer responsible for video output, window creation, and input handling, and that `vo_gpu` should be treated as the reference implementation.[^10][^11]

The source tree confirms that this is not documentation rhetoric. `meson.build` includes `video/out/gpu/libmpv_gpu.c`, `video/out/vo_libmpv.c`, and OpenGL-specific support files such as `video/out/opengl/libmpv_gl.c`, reinforcing that libmpv-facing GPU rendering is a first-class build target.[^41] This is why mpv is frequently chosen for high-quality playback and GPU-driven post-processing, but also why weak GPUs and bad drivers show up so visibly in user experience.[^9]

On the ingest side, streams, demuxers, and filters are deliberately modular. The technical overview says stream handlers choose source-specific code paths (for example HTTP or DVD-like sources), demuxers split data into timestamped packets with caching that supports seeking/prefetching, and filters provide generic frame-to-frame conversion with auto-conversion and decoder-wrapper stages between the frontend and actual decoders.[^19][^20]

## Build, Dependencies, Release, and Operational Reality

mpv builds with **Meson** and depends heavily on FFmpeg, libplacebo, libass, and platform graphics/audio stacks.[^43] The README explicitly documents a `libplacebo` subproject path for Meson and says it will be statically linked when used that way; it also lists Lua, libass, and hardware-decoding libraries as optional-but-important dependencies depending on desired features.[^43]

Feature surfaces are reflected directly in the build graph. `meson.build` conditionally enables C plugins, JavaScript via `mujs`, and Lua via supported Lua/LuaJIT package names, and pulls in the corresponding source files only when those features are found/enabled.[^44][^45][^46] That makes mpv feature-complete builds somewhat distribution-sensitive: packaging choices affect not just optional extras but visible behaviors such as OSC, scripting, and embedding support.[^34][^44][^45]

Release policy is intentionally lightweight. The README says releases are cut once or twice a year, are meant primarily to satisfy distribution packaging, and that releases older than the latest are unsupported and unmaintained.[^47] Licensing is similarly configurable: the project is GPLv2-or-later by default, but can be built as LGPLv2.1-or-later with `-Dgpl=false`, which matters for embedders evaluating legal integration models.[^48]

## Practical Conclusions

1. **For embedding in an application, use `libmpv` plus the render API unless you have a very strong reason not to.** That is the path most aligned with mpv’s own docs and architecture.[^8][^12][^13]
2. **Treat commands/properties as the real contract.** CLI usage, Lua, JavaScript, JSON IPC, and `libmpv` are mostly wrappers around that shared semantic layer.[^2][^6][^21]
3. **Expect scripting to be part of the product, not just user customization.** OSC, console, stats, select, and `ytdl_hook` are loaded as built-in scripts.[^15]
4. **Assume GPU quality depends on real graphics capability and drivers.** mpv’s default rendering path is shader-heavy and intentionally quality-oriented rather than “works everywhere by default.”[^9][^10]
5. **Do not expose JSON IPC beyond trusted local contexts.** The official IPC docs explicitly call it insecure and capable of arbitrary command execution through exposed commands like `run`.[^31]

## Key Repositories Summary

| Repository | Purpose | Key files used here |
|---|---|---|
| [mpv-player/mpv](https://github.com/mpv-player/mpv) | Core player, `libmpv`, scripting backends, build system, manual sources, wiki-linked docs | `README.md`, `DOCS/tech-overview.txt`, `include/mpv/client.h`, `include/mpv/render.h`, `player/main.c`, `player/scripting.c`, `input/ipc.c`, `DOCS/man/*.rst`, `meson.build` |

## Confidence Assessment

**High confidence:** mpv’s architectural split, control model, embedding guidance, scripting backends, render API recommendation, JSON IPC shape, build/dependency story, and release posture are directly documented in the upstream source tree and manpage sources used here.[^3][^12][^15][^28][^30][^43][^47]

**Moderate confidence:** statements about how these pieces are used “in practice” are based on the project’s own docs plus the structure of the codebase, rather than on telemetry or maintainer interviews. They are strong inferences, but still inferences.[^21][^40]

**Known limitation:** the wiki is community-edited, so it is best treated as ecosystem context rather than normative implementation truth. I used it mainly for extension/front-end landscape, not for internal architecture claims.[^39][^40]

## Footnotes

[^1]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/README.md:31-32`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/README.md#L31-L32) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^2]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/include/mpv/client.h:54-76`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/include/mpv/client.h#L54-L76) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^3]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/DOCS/tech-overview.txt:3-8`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/tech-overview.txt#L3-L8) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^4]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/DOCS/tech-overview.txt:18-28`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/tech-overview.txt#L18-L28) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^5]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/DOCS/tech-overview.txt:146-197,213-223`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/tech-overview.txt#L146-L197) and [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/tech-overview.txt#L213-L223) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^6]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/DOCS/man/mpv.rst:36-40`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/man/mpv.rst#L36-L40) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^7]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/DOCS/man/mpv.rst:1496-1499`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/man/mpv.rst#L1496-L1499) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^8]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/DOCS/man/mpv.rst:1114-1122`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/man/mpv.rst#L1114-L1122) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^9]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/README.md:42-53`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/README.md#L42-L53) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^10]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/DOCS/tech-overview.txt:213-223`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/tech-overview.txt#L213-L223) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^11]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/meson.build:233-247,1297-1301`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/meson.build#L233-L247) and [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/meson.build#L1297-L1301) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^12]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/include/mpv/client.h:190-205`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/include/mpv/client.h#L190-L205) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^13]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/include/mpv/render.h:29-47`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/include/mpv/render.h#L29-L47) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^14]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/player/scripting.c:42-58`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/player/scripting.c#L42-L58) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^15]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/player/scripting.c:262-274`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/player/scripting.c#L262-L274) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^16]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/player/scripting.c:276-299`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/player/scripting.c#L276-L299) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^17]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/DOCS/man/javascript.rst:51-62`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/man/javascript.rst#L51-L62) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^18]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/player/main.c:447-458`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/player/main.c#L447-L458) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^19]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/DOCS/tech-overview.txt:160-189`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/tech-overview.txt#L160-L189) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^20]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/DOCS/tech-overview.txt:191-197`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/tech-overview.txt#L191-L197) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^21]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/DOCS/tech-overview.txt:84-99`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/tech-overview.txt#L84-L99) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^22]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/DOCS/tech-overview.txt:238-249`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/tech-overview.txt#L238-L249) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^23]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/DOCS/man/libmpv.rst:1-7`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/man/libmpv.rst#L1-L7) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^24]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/include/mpv/client.h:85-97`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/include/mpv/client.h#L85-L97) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^25]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/include/mpv/client.h:544-548`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/include/mpv/client.h#L544-L548) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^26]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/include/mpv/client.h:136-139`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/include/mpv/client.h#L136-L139) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^27]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/include/mpv/client.h:1690-1693`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/include/mpv/client.h#L1690-L1693) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^28]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/meson.build:1802-1820`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/meson.build#L1802-L1820) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^29]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/include/mpv/render.h:125-145`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/include/mpv/render.h#L125-L145) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^30]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/DOCS/man/ipc.rst:1-9`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/man/ipc.rst#L1-L9) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^31]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/DOCS/man/ipc.rst:11-17`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/man/ipc.rst#L11-L17) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^32]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/input/ipc.c:116-180`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/input/ipc.c#L116-L180) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^33]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/input/ipc.c:372-410`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/input/ipc.c#L372-L410) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^34]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/README.md:108-123`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/README.md#L108-L123) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^35]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/DOCS/man/lua.rst:95-99`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/man/lua.rst#L95-L99) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^36]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/DOCS/man/lua.rst:698-758`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/man/lua.rst#L698-L758) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^37]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/DOCS/man/libmpv.rst:18-32`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/DOCS/man/libmpv.rst#L18-L32) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^38]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/meson.build:370-376`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/meson.build#L370-L376) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^39]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-web/User-Scripts.md:1-10`; upstream wiki [`mpv-player/mpv`](https://github.com/mpv-player/mpv/wiki/User-Scripts).
[^40]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-web/Wiki-Home.md:21-31`; upstream wiki [`mpv-player/mpv`](https://github.com/mpv-player/mpv/wiki).
[^41]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/meson.build:233-247`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/meson.build#L233-L247) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^43]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/README.md:86-149`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/README.md#L86-L149) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^44]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/meson.build:662-667`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/meson.build#L662-L667) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^45]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/meson.build:707-739`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/meson.build#L707-L739) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^46]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/README.md:120-123`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/README.md#L120-L123) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^47]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/README.md:154-163`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/README.md#L154-L163) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
[^48]: `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/README.md:190-193` and `/Users/pb/.copilot/session-state/06807d95-999b-461d-a857-b045a4537b83/files/mpv-src/include/mpv/client.h:16-20`; upstream [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/README.md#L190-L193) and [`mpv-player/mpv`](https://github.com/mpv-player/mpv/blob/d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9/include/mpv/client.h#L16-L20) at commit `d79c4ad1e33301552e23c9bb98ec3c6c9a4324b9`.
