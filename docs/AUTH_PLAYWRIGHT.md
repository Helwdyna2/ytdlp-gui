# Authentication (Playwright)

This application uses Playwright to manage a persistent browser profile and exports cookies in Netscape format for use with yt-dlp.

## Source of Truth

- **Login/export/install logic:** [`src/core/auth_worker.py`](../src/core/auth_worker.py)
- **Auth orchestration:** [`src/core/auth_manager.py`](../src/core/auth_manager.py)
- **Result enumerations:** [`src/core/auth_types.py`](../src/core/auth_types.py)
- **Cookie parsing/writing:** [`src/core/netscape_cookies.py`](../src/core/netscape_cookies.py)
- **Site registry:** [`src/core/site_auth.py`](../src/core/site_auth.py)
- **Download page gating:** [`src/ui/main_window.py`](../src/ui/main_window.py)
- **Status panel UI:** [`src/ui/widgets/auth_status_widget.py`](../src/ui/widgets/auth_status_widget.py)

## Storage Model (Non-Negotiable)

The application maintains:
- **Single persistent Playwright profile:** stored in `auth.profile_dir`
- **Single Netscape cookies file:** at `auth.cookies_file_path`
- **No per-site cookie files or storage_state.json files**

This unified approach simplifies cookie management and ensures consistent authentication across download sessions.

## User Experience Flow

### Initial URL Setup
As users enter or paste URLs in the Download page:
1. The application extracts hostnames from all URLs
2. For known auth-required domains (Instagram, Redgifs), the auth status panel displays:
   - **✓ Authenticated** — cookies for this domain exist in the file
   - **✗ Not Authenticated** — domain requires login but no cookies found
   - **? Unknown** — domain not in known registry; users may skip or proceed
3. Users can click **Authenticate** to open a visible Playwright browser window for manual login

### Download Gating
Before starting downloads:
- If any required-auth domain is not authenticated, the application prompts users to authenticate first
- Unknown domains are allowed by default (with a warning)
- After authentication or user dismissal, downloads proceed

## Authentication Success

Authentication succeeds when:
- User closes the Playwright login window AND
- The application can export cookies to the file AND
- The exported cookies file contains cookies for the target domain suffix(es)

If the browser closes without cookies for the target domain:
- This is not an error—it is expected when login fails or cookies are cleared
- The UI displays a warning: "Please try again"

## Handling TargetClosedError

When users close the Playwright window, various Playwright API calls may raise errors like:
- `TargetClosedError`
- `"Target page, context or browser has been closed"`

The QThread worker treats this as expected user behavior and proceeds to the post-close cookie export and validation step.

## Authentication Result States

The `AuthWorker` emits `login_finished(result, message, cookies_path)` where `result` is one of:

| State | Meaning |
|-------|---------|
| `success` | Login successful and domain cookies exported |
| `cancelled_no_cookies` | Browser closed without domain cookies (expected, shows warning) |
| `cancelled_user` | User cancelled via UI button |
| `error_playwright_setup` | Browsers not installed or setup failed |
| `error_fatal` | Unexpected error during login |

Refer to [`src/core/auth_types.py`](../src/core/auth_types.py) for the full enum definition.

## Cookie Validation and Parsing

**Export step:**
After login closes, `AuthWorker` exports cookies from the persistent profile to `auth.cookies_file_path` in Netscape format.

**Validation step:**
For known sites, the application verifies that the exported cookies file contains cookies matching the site's registered `cookie_domain_suffixes`.

**Parsing utilities** in [`src/core/netscape_cookies.py`](../src/core/netscape_cookies.py):
- `parse_netscape_cookiefile(path)` — reads and parses the cookies file
- `cookiefile_has_domain_suffix(path, domain_suffix)` — checks for domain-specific cookies

## Site Authentication Registry

[`src/core/site_auth.py`](../src/core/site_auth.py) defines handlers for authentication-required domains.

Each handler provides:
- `match(hostname: str) -> bool` — matches domain and subdomains
- `display_name` — friendly name for UI display
- `start_url` — page to navigate to for login
- `cookie_domain_suffixes` — tuple of domain suffixes used for cookie validation
- `logged_in_heuristic(page) -> Optional[bool]` — (optional) lightweight status check

**Currently registered handlers:**
- Instagram (`instagram.com`)
- Redgifs (`redgifs.com`)

**Adding a new site:**
1. Create a handler class in [`src/core/site_auth.py`](../src/core/site_auth.py)
2. Add it to the `KNOWN_AUTH_HANDLERS` list
3. Ensure `cookie_domain_suffixes` matches the domain where login sets cookies
4. Keep `logged_in_heuristic()` lightweight to avoid repeated page navigation

## Playwright Engine Selection

The application allows users to choose the Playwright browser engine via configuration:
```
playwright.browser: "chromium" | "firefox" | "webkit"
```

Workers select the engine dynamically:
```python
engine = getattr(playwright, config.get("playwright.browser", "chromium"))
context = await engine.launch_persistent_context(...)
```

## Installing Playwright Browsers

### Standard Installation
Install default browsers (Chromium, Firefox, WebKit):
```bash
python -m playwright install
```

### Install Specific Browsers
```bash
python -m playwright install chromium firefox webkit
```

### Reinstall with --force
```bash
python -m playwright install --force
```

### Linux Container Environments
In containerized Linux (Docker, etc.), install system dependencies:
```bash
python -m playwright install --with-deps
```

## Important Edge Cases

- **Instagram and similar sites:** These platforms rarely reach the `networkidle` event reliably during login. Use `domcontentloaded` for initial navigation.
- **Stale cookies:** If the cookies file becomes outdated, export cookies again. Automatic export occurs before every download; manual re-authentication is also available.
- **Heuristic overhead:** Lightweight status checks (`logged_in_heuristic`) must not run repeatedly in tight loops. Keep checks best-effort and cache results where possible.
