# Troubleshooting

## Tests Fail Immediately

- activate the virtual environment first
- install dev dependencies with `pip install -e ".[dev]"`

## App Starts But Auth Fails

- install Playwright browsers with `python -m playwright install`
- confirm the selected browser exists in Settings
- verify the profile and cookie paths in the Settings stage

## Download Tools Work But Convert/Trim Do Not

- confirm `ffmpeg` is installed and available on `PATH`

## Theme Or Layout State Looks Wrong

- inspect `data/config.json`
- remove the local config file if you need to reset UI state

## Build Issues

- rebuild from a clean virtual environment
- re-run `pyinstaller ytdlp_gui.spec`
