# CLAUDE.md

All project guidance for AI agents lives in **[`AGENTS.md`](AGENTS.md)** (single source of truth).

For detailed documentation, see [`docs/INDEX.md`](docs/INDEX.md).

## Environment Setup

Always use the virtual environment. Activate the existing one, or create it if missing:

```bash
# Activate existing venv (from project root)
source .venv/bin/activate

# Or create + install if it doesn't exist
python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
```

## Quick Commands

```bash
python run.py                  # Run from source
pip install -e ".[dev]"        # Install dev dependencies
pytest                         # Run tests
pyinstaller ytdlp_gui.spec    # Build executable
```
