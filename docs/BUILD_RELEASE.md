# Build And Release

## Build

```bash
source .venv/bin/activate
pyinstaller ytdlp_gui.spec
```

## Before A Release

- confirm `pyproject.toml` version matches `src/utils/constants.py`
- run `pytest -q`
- smoke test with `python run.py`
- confirm `ffmpeg` and Playwright flows still work on the target machine

## Version Source Of Truth

Use these files together:

- `pyproject.toml`
- `src/utils/constants.py`

The current app version is `1.0.0`.
