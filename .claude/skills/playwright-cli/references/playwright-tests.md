# Running Playwright Tests

> **Prerequisite:** Run `npx playwright install` to install browser binaries before running tests.

To run Playwright tests, use the `npx playwright test` command, or a package manager script. To avoid opening the interactive html report, use `PLAYWRIGHT_HTML_OPEN=never` environment variable.

```bash
# Run all tests
PLAYWRIGHT_HTML_OPEN=never npx playwright test

# Run all tests through a custom npm script
PLAYWRIGHT_HTML_OPEN=never npm run special-test-command
```

# Debugging Playwright Tests

To debug a failing Playwright test with the Playwright Inspector, run it with the boolean `--debug` flag. This pauses the test and opens the Inspector UI.

For CLI-style debugging in the terminal, set `PWDEBUG=console` and add an explicit `await page.pause()` where you want execution to stop.

```bash
# Open the Playwright Inspector
PLAYWRIGHT_HTML_OPEN=never npx playwright test --debug

# Or debug in the terminal after adding `await page.pause()` in the test
PWDEBUG=console PLAYWRIGHT_HTML_OPEN=never npx playwright test
```

Keep the test running while you inspect the page and look for a fix. With `--debug`, you can step through the test in the Inspector. With `PWDEBUG=console`, execution pauses at `await page.pause()` so you can inspect and experiment from the terminal.

Every action you perform with `playwright-cli` generates corresponding Playwright TypeScript code.
This code appears in the output and can be copied directly into the test. Most of the time, a specific locator or an expectation should be updated, but it could also be a bug in the app. Use your judgement.

After fixing the test, stop the background test run. Rerun to check that test passes.
