# Playwright Source Capture Runbook

Browser automation is used for source metadata review, not for unsafe downloading.

## Current Tool State

- `npx` is available.
- The user-scoped `playwright_cli.sh` wrapper currently resolves to a stale `playwright-cli` binary path with the installed `@playwright/mcp` package.
- The Playwright package CLI is available through `npm exec --package=playwright -- playwright`.
- Chromium was installed into the local Playwright cache on 2026-06-14.

## Verified Commands

```bash
npm exec --yes --package=playwright -- playwright --version
npm exec --yes --package=playwright -- playwright trace --help
npm exec --yes --package=playwright -- playwright screenshot \
  --browser chromium \
  --viewport-size 1280,720 \
  --wait-for-timeout 1500 \
  https://www.copyright.gov/music-modernization/pre1972-soundrecordings/ \
  output/playwright/copyright-pre1972.png

npm exec --yes --package=playwright -- playwright screenshot \
  --browser chromium \
  --viewport-size 1280,720 \
  --wait-for-timeout 1500 \
  https://cylinders.library.ucsb.edu/hillbilly.php \
  output/playwright/ucsb-hillbilly.png
```

The Copyright Office and UCSB screenshots rendered real rights/source pages and are intentionally ignored under `output/playwright/`.

## Known Failure

This command failed from Chromium with `net::ERR_NAME_NOT_RESOLVED`:

```bash
npm exec --yes --package=playwright -- playwright screenshot \
  https://citizen-dj.labs.loc.gov/loc-jukebox-folk-songs/use/ \
  output/playwright/loc-citizen-dj-folk.png
```

The source remains in the catalog because it was reachable through web search metadata and should be manually checked in a normal browser/network path before any download entry is approved.

The LOC Henry Reed collection page rendered a Cloudflare security-verification interstitial in headless Chromium on 2026-06-14. Do not treat that screenshot as source metadata evidence.

## Trace Workflow

When future Playwright tests produce `trace.zip`, inspect them with:

```bash
npm exec --yes --package=playwright -- playwright trace open path/to/trace.zip
npm exec --yes --package=playwright -- playwright trace actions
npm exec --yes --package=playwright -- playwright trace requests --failed
npm exec --yes --package=playwright -- playwright trace console --errors-only
npm exec --yes --package=playwright -- playwright trace close
```

Do not commit traces by default; store only concise notes or screenshots needed for review.
