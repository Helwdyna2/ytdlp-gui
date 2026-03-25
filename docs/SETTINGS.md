# Settings

The settings UI is available inside the `Export` stage.

## Sections

### Appearance

- theme toggle for Signal Deck dark and light modes
- updates are applied immediately through `ThemeEngine`
- selection is persisted in `appearance.theme`

### Playwright

- choose browser engine
- install or reinstall Playwright browsers
- inspect the profile directory and cookie file location

### Download Defaults

- force overwrite
- video-only downloads

### Polite Mode

- request sleep
- min/max pre-download sleep
- rate limiting
- retry count
- HTTP retry sleep strategy
- fragment retry sleep strategy

## Storage

Settings are stored in `data/config.json` through `ConfigService`.
