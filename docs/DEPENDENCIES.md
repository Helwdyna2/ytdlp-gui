# Dependencies

## Python Packages

Runtime dependencies are declared in `pyproject.toml`. Key packages:

- `PyQt6`
- `yt-dlp`
- `playwright`
- `python-mpv`
- `superqt`
- `qtawesome`
- `send2trash`

Dev dependencies:

- `pytest`
- `pytest-qt`
- `pyinstaller`

## External Tools

### Required

- `ffmpeg`

### Installed Separately

- Playwright browser binaries via:

```bash
source .venv/bin/activate
python -m playwright install
```

## Packaging

- `ytdlp_gui.spec` is the PyInstaller spec file
