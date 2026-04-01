# yt-dlp technical deep-dive

## Executive Summary

[yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) is a Python 3.10+ command-line downloader that forks the original youtube-dl lineage, keeps its public surface area broad, and layers a richer architecture on top: a central `YoutubeDL` controller, a large extractor framework, a pluggable networking stack, downloader and post-processing chains, a plugin loader, and a self-update/release system tied to multiple channels.[^1][^2][^3]

The runtime path is straightforward but extensible: `python -m yt_dlp` or the `yt-dlp` console script enters `yt_dlp.main()`, parses options and config files, optionally loads plugins, constructs `YoutubeDL`, then either updates itself, lists capabilities, or downloads URLs.[^2][^3][^21] Once running, `YoutubeDL` chooses the first suitable extractor, resolves intermediary URL/playlist results into concrete video results, normalizes metadata, selects formats, downloads media, and finally runs post-processors such as FFmpeg-based steps.[^4][^5][^6][^7][^8][^9]

Two design choices stand out. First, networking is abstracted behind `RequestDirector` and `RequestHandler`, so yt-dlp can swap or prefer different HTTP stacks and special capabilities like impersonation without changing extractor code.[^13][^14][^15][^16] Second, the project treats distribution as part of the product: it publishes stable, nightly, and master channels, enforces update lockfiles and checksum verification, and uses GitHub Actions workflows to build binaries, wheels, and releases across several platforms.[^22][^23][^24][^25][^26][^27][^28][^29][^30]

## Architecture / System Overview

```text
CLI / console_script / python -m yt_dlp
                |
                v
        parseOpts + config loading
                |
                v
           YoutubeDL controller
      /            |            \
     v             v             v
Extractors    RequestDirector   Postprocessors
 (site logic)  -> handlers       (ffmpeg, metadata,
      |          (urllib,         thumbnails, etc.)
      |           requests,
      |           curl_cffi,
      |           websockets...)
      v
  info_dict / playlist / URL refs
      |
      v
 format selection -> downloader -> files -> post-process chain
      |
      v
 archive / metadata / final outputs / optional self-update
```

The entrypoint is intentionally thin. `yt_dlp/__main__.py` just dispatches to `yt_dlp.main()`, while `_real_main()` handles parsing, plugin directory setup, `YoutubeDL` construction, update checks, impersonation target listing, and the final call to `download()` or `download_with_info_file()`.[^2] Packaging exposes the same flow through the `yt-dlp` console script in `pyproject.toml`.[^21]

## 1. Entry point and option ingestion

`parseOpts()` builds a custom `optparse` parser, layers command-line arguments with portable, home, user, and system config files, then returns parser/options/args; the parser also supports preset aliases such as `mp3`, `aac`, `mp4`, `mkv`, and `sleep`.[^3] `_real_main()` applies a few early side effects before `YoutubeDL` exists, most notably setting the FFmpeg location and loading plugins into the global lookup if plugin directories were configured.[^2]

That makes yt-dlp’s effective configuration model: **command line + multiple config scopes + preset aliases + plugin directories**, all resolved before the main controller is instantiated.[^2][^3]

## 2. Core controller: `YoutubeDL`

`YoutubeDL` is the orchestration layer. Its constructor allocates extractor and post-processor registries, cache, output streams, hooks, archive handling, header/cookie state, JS runtime selection, remote component selection, format selector compilation, and post-processor instantiation from config.[^4] It also loads plugins automatically for API users if they have not already been loaded, then installs the default extractors unless `auto_init` is disabled.[^4]

The main download path is:

1. `download(url_list)` iterates URLs and wraps each call through `extract_info()`.[^9]
2. `extract_info()` walks registered extractors in order, picks the first suitable one, skips archived IDs when possible, and calls the internal extraction wrapper.[^6]
3. `__extract_info()` invokes `ie.extract(url)`, injects default metadata like `webpage_url`, `extractor`, and `extractor_key`, optionally waits for scheduled content, then hands results to `process_ie_result()`.[^6]
4. `process_ie_result()` resolves `_type` values such as `url`, `url_transparent`, and `video`; `video` results flow into `process_video_result()` for normalization, common field filling, subtitle URL sanitization, format handling, and eventual download/post-processing.[^7][^8]
5. After download, `post_process()` runs configured post-processors and a final move stage.[^9]

That separation is the project’s key architectural seam: extractors produce structured metadata; `YoutubeDL` decides how aggressively to resolve, sanitize, select, download, archive, and post-process it.[^4][^6][^7][^8][^9]

## 3. Extractor framework

The extractor subsystem is both large and disciplined. `yt_dlp/extractor/__init__.py` registers extractor plugins, exposes helper functions for loading and enumerating extractors, and ensures `GenericIE` is yielded last when listing extractors, which preserves more specific extractors’ precedence.[^5]

The base `InfoExtractor` contract is explicit: extractor output is a dictionary whose default `_type` is `video`, and a valid video result must contain `id`, `title`, and either a direct `url` or a `formats` list. The base class also documents the structure of format entries in considerable detail, including protocol, codecs, bitrate, fragments, DRM flags, subtitles, and manifest-related fields.[^10]

`InfoExtractor.extract()` wraps the site-specific `_real_extract()` implementation with initialization, user-visible logging, geo-restriction retry logic using fake `X-Forwarded-For` IPs, and error normalization into `ExtractorError`.[^11] The helper constructors `url_result()` and `playlist_result()` standardize how one extractor hands control to another extractor or returns a playlist container.[^12]

### Example: extractor handoff objects

```python
return {
    **kwargs,
    '_type': 'url_transparent' if url_transparent else 'url',
    'url': url,
}
```

That is the core mechanism that lets one extractor defer to another or construct playlist entries without downloading anything itself.[^12]

## 4. Networking stack

yt-dlp’s newer networking design is more modular than the original youtube-dl model. `RequestDirector` owns a set of registered handlers, scores them with preference functions, validates which handlers support a given request, and sends the request through the highest-preference compatible handler; if every handler rejects or fails, it raises `NoSupportingHandlers` with both unsupported and unexpected errors preserved.[^13]

`RequestHandler` is the base transport contract. It validates URL schemes, proxy schemes, optional request extensions such as `cookiejar`, `timeout`, `legacy_ssl`, and `keep_header_casing`, and requires subclasses to implement `_send()`.[^14] Its class naming convention also drives stable handler keys: any concrete handler must end in `RH`, and the key is derived from the class name minus that suffix.[^14]

`YoutubeDL.build_request_director()` wires user params into handlers: default headers, proxies, cookiejar, source address, socket timeout, legacy SSL, `--enable-file-urls`, impersonation, and client certificate options all flow into the director at build time; the compatibility option `prefer-legacy-http-handler` adds a synthetic preference for the urllib-based handler.[^15] `urlopen()` then sanitizes URLs, promotes `user:pass@host` URLs into `Authorization` headers, cleans proxy/header shims, and translates some missing-capability cases into higher-level guidance, including disabled `file://` support, missing HTTPS proxy dependencies, and missing WebSocket support.[^15]

The tests make this design concrete. `test_networking.py` verifies handler overwrite behavior, preference-based routing, proxy cleaning, custom handler parameter injection, file URL blocking, WebSocket error translation, impersonation target validation, and the `prefer-legacy-http-handler` compatibility preference.[^16]

## 5. Download and post-processing pipeline

`FileDownloader` is the abstract download engine. It owns retryable file operations, progress rendering, speed/ETA formatting, rate limiting, resume/no-overwrite checks, optional sleep intervals, and a template-driven progress hook interface. The actual transfer is delegated to `real_download()` in subclasses.[^17]

`PostProcessor` mirrors that shape on the back end. A post-processor receives an info dict containing `filepath`, may mutate metadata, returns a pair of `(files_to_delete, updated_info)`, emits progress hooks, and can fetch auxiliary JSON with extractor-style retry behavior.[^18] `YoutubeDL.run_pp()`, `run_all_pps()`, `pre_process()`, and `post_process()` connect those post-processors into ordered chains keyed by lifecycle stage such as `pre_process`, `post_process`, and `after_move`.[^9][^18]

This is why FFmpeg is so central to real-world yt-dlp usage: the README marks `ffmpeg` and `ffprobe` as strongly recommended for merging, remuxing, and post-processing, and the runtime architecture gives those steps first-class lifecycle slots rather than treating them as ad hoc extras.[^22]

## 6. Plugins and extensibility

The plugin system is a real subsystem, not a convenience import hook. `plugins.py` defines a `PluginSpec`, a namespace-package `PluginFinder`, search path discovery, module iteration, and the `load_plugins()` / `load_all_plugins()` entrypoints.[^19] By default it searches:

1. yt-dlp config directories under `plugins/`
2. `yt-dlp-plugins` directories alongside executable and user/system config roots
3. the Python import path (`sys.path`)[^19]

It also understands directory-based plugins and zipped/egg/wheel packages, skips hidden modules and classes, supports a backward-compatible older plugin layout, and prepends loaded plugin classes into the main extractor or post-processor lookup so plugins can extend or override built-ins.[^19] The file explicitly warns that no backward compatibility is guaranteed for the plugin API because of the complexity of the mechanism.[^19]

The tests validate exactly the interesting cases: zipped plugin packages, extractor override plugins, selective loading, global plugin registration, and custom plugin directories.[^20]

## 7. Packaging, dependencies, release channels, and self-update

`pyproject.toml` makes the packaging stance clear: yt-dlp requires Python `>=3.10`, exposes `yt-dlp` as a console script, ships with **no mandatory runtime dependencies**, and places most functionality behind optional extras such as `default`, `curl-cffi`, `secretstorage`, and `deno`.[^21] The same file also registers PyInstaller hook directories and defines Hatch test/lint environments, including `python -m devscripts.run_tests` as the hatch test entrypoint.[^21]

The README documents three binary channels: `stable`, `nightly`, and `master`. `stable` is the default; `nightly` is built daily and is explicitly recommended for regular users; `master` is built after each push to the master branch and trades freshness for higher regression risk.[^22] The README also describes release artifacts, GPG-verifiable checksum files, and the fact that some bundled executables carry third-party licenses distinct from the source tree’s Unlicense.[^30]

The updater implementation matches that documentation closely. `update.py` maps those channels to repositories, detects whether the current runtime is a zipapp, PyInstaller binary, source checkout, or another unsupported packaging mode, fetches GitHub release metadata, processes an `_update_spec` lockfile to block incompatible upgrades, downloads checksum files for verification, blocks automatic restart into unofficial or unverified builds, and restarts the executable only when safe to do so.[^23] The update tests cover lockfile behavior across Python versions, OS variants, channel repositories, and forked repositories, which is a strong signal that the update path is treated as compatibility-critical infrastructure.[^24]

## 8. Build, test, and publish flow

The project’s CI/CD is substantial:

- `core.yml` runs the core test suite across CPython 3.10-3.14 and PyPy 3.11 on Linux and Windows, with special flaky handling when networking-related files change.[^25]
- `release-nightly.yml` is scheduled daily, checks whether relevant files changed since the last nightly, and then calls the shared release workflow; it can also publish to PyPI when configured.[^26]
- `release-master.yml` triggers on pushes to `master` that touch relevant code or workflow paths and routes them through the same shared release workflow, optionally followed by PyPI publication.[^27]
- `release.yml` prepares release variables, updates version/changelog/docs, optionally pushes a release commit, builds artifacts via `build.yml`, builds PyPI packages, and publishes GitHub releases.[^28]
- `build.yml` generates version/changelog/lazy extractor artifacts and builds a wide artifact matrix including Unix zipimport, Linux, musllinux, macOS, Windows, and architecture-specific variants.[^29]

Taken together, yt-dlp treats “release engineering” as part of the user experience: the runtime updater, channel semantics, artifact naming, checksum signing, and GitHub Actions workflows are all aligned around a predictable self-update story.[^22][^23][^26][^27][^28][^29][^30]

## Key repositories summary

| Repository | Purpose | Key evidence |
|---|---|---|
| [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) | Core CLI, extractor framework, networking, downloader, post-processing, updater, packaging | Runtime and packaging files analyzed throughout this report.[^2][^4][^5][^13][^21][^23] |
| [yt-dlp/yt-dlp-nightly-builds](https://github.com/yt-dlp/yt-dlp-nightly-builds) | Daily prerelease channel used by `--update-to nightly` | README channel docs and nightly workflow.[^22][^26] |
| [yt-dlp/yt-dlp-master-builds](https://github.com/yt-dlp/yt-dlp-master-builds) | On-push prerelease channel for the latest master branch state | README channel docs and master workflow.[^22][^27] |
| [yt-dlp/ejs](https://github.com/yt-dlp/ejs) | JavaScript package required for full YouTube support, together with a JS runtime such as Deno/Node/Bun/QuickJS | README dependency guidance.[^22] |
| [yt-dlp/FFmpeg-Builds](https://github.com/yt-dlp/FFmpeg-Builds) | Patched FFmpeg builds recommended by the project for known integration issues | README dependency guidance.[^22] |

## Practical takeaways

For someone integrating or wrapping yt-dlp, the stable abstraction boundary is the `YoutubeDL` API plus the extractor result contract: if you can construct valid `YoutubeDL` params and valid extractor-style info dicts, the rest of the pipeline—format sorting, downloading, archive handling, hooks, post-processing, sanitization—comes along automatically.[^4][^7][^8][^9][^10]

For someone modifying yt-dlp itself, the safest mental model is to treat extractors, request handlers, downloaders, post-processors, and plugins as separate extension points under a single orchestrator. The codebase is not a monolith so much as a controller with several registries and pipelines.[^4][^5][^13][^17][^18][^19]

For end users, the operationally important detail is that the project expects release freshness. The README recommends nightly for regular users, the runtime warns about versions older than 90 days, and the release/update stack is built to support frequent movement between channels and tags.[^22][^23]

## Confidence Assessment

**High confidence:** core architecture, request/handler model, extractor contract, plugin loading behavior, packaging metadata, release channels, and updater behavior. These are all directly verified from implementation files and corresponding tests/workflows.[^2][^4][^5][^13][^16][^19][^20][^21][^23][^24][^25][^26][^27][^28][^29]

**Medium confidence / bounded inference:** some runtime behavior of specific handler backends or site-specific extractors outside the files sampled here. The architectural conclusions are strong, but I did not enumerate every extractor or every concrete downloader/request-handler subclass in the repository.[^5][^13][^17]

**Assumption made:** this report is anchored to the repository state fetched on 2026-04-01, whose checked-out HEAD was commit `2d7b278666bfbf12cf287072498dd275c946b968`.[^31]

## Footnotes

[^1]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/README.md:19-20` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^2]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/__main__.py:1-17` and `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/__init__.py:963-1113` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^3]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/options.py:43-131` and `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/options.py:153-259` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^4]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/YoutubeDL.py:629-851` and `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/YoutubeDL.py:898-960` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^5]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/extractor/__init__.py:1-55` and `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/YoutubeDL.py:918-934` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^6]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/YoutubeDL.py:1643-1875` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^7]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/YoutubeDL.py:1876-1928` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^8]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/YoutubeDL.py:2799-2875` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^9]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/YoutubeDL.py:3659-3811` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^10]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/extractor/common.py:107-260` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^11]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/extractor/common.py:757-804` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^12]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/extractor/common.py:1281-1312` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^13]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/networking/common.py:37-141` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^14]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/networking/common.py:149-390` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^15]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/YoutubeDL.py:4239-4285` and `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/YoutubeDL.py:4303-4340` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^16]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/test/test_networking.py:1565-1931` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^17]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/downloader/common.py:37-79` and `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/downloader/common.py:430-500` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^18]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/postprocessor/common.py:16-52`, `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/postprocessor/common.py:135-212`, and `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/YoutubeDL.py:3763-3811` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^19]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/plugins.py:33-48`, `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/plugins.py:81-107`, `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/plugins.py:116-179`, and `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/plugins.py:194-247` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^20]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/test/test_plugins.py:63-220` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^21]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/pyproject.toml:1-190` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^22]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/README.md:159-256` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^23]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/update.py:38-45`, `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/update.py:115-160`, and `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/yt_dlp/update.py:249-587` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^24]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/test/test_update.py:16-20`, `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/test/test_update.py:79-125`, and `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/test/test_update.py:129-241` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^25]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/.github/workflows/core.yml:1-94` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^26]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/.github/workflows/release-nightly.yml:1-105` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^27]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/.github/workflows/release-master.yml:1-52` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^28]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/.github/workflows/release.yml:67-259` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^29]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/.github/workflows/build.yml:1-259` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^30]: `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/README.md:94-156` and `/Users/pb/.copilot/session-state/10a0e512-82bd-4467-9404-c89fb19d6195/files/yt-dlp/README.md:168-196` (commit `2d7b278666bfbf12cf287072498dd275c946b968`)
[^31]: Repository checkout of [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) at commit `2d7b278666bfbf12cf287072498dd275c946b968`, obtained via `git rev-parse HEAD` in the local research clone on 2026-04-01.
