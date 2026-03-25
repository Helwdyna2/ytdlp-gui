# Testing

## Baseline

Run the full suite from the repo root with the virtual environment active:

```bash
source .venv/bin/activate
pytest -q
```

## Useful Focused Commands

```bash
source .venv/bin/activate
pytest tests/test_main_window_workbench.py -v
pytest tests/test_ingest_stage_widget.py tests/test_prepare_stage_widget.py tests/test_organize_stage_widget.py tests/test_export_stage_widget.py -v
pytest tests/test_theme_tokens.py tests/test_qss_builder.py tests/test_icons.py -v
```

## Manual Smoke Pass

```bash
source .venv/bin/activate
python run.py
```

Check:

- workbench minimum size and stage switching
- stage context updates
- shared splitter behavior
- settings navigation into `Export`
- activity drawer behavior
- Signal Deck dark/light theme switching
