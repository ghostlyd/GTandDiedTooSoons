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

npm exec --yes --package=playwright -- playwright screenshot \
  --browser chromium \
  --viewport-size 1280,900 \
  --wait-for-timeout 3000 \
  https://citizen-dj.labs.loc.gov/loc-jukebox-folk-songs/use/ \
  output/playwright/loc-citizen-dj-folk-20260614.png
```

The Copyright Office, UCSB, and LOC Citizen DJ screenshots rendered real rights/source pages and are intentionally ignored under `output/playwright/`.

## Source Notes

The LOC Citizen DJ Folk Music collection page is approved as browser evidence for item-level downloads in `catalogs/public-domain-bluegrass-sources.json`. Because `output/playwright/` is ignored, the catalog also stores concise rights evidence from the page: public-domain status, commercial reuse scope, credit recommendation, and cultural-respect notes. Its WAV/MP3 pack links are still fetched through `scripts/fetch_public_domain_audio.py` so exact host checks, path-prefix allow-lists, size limits, SHA-256 ledger entries, and local provenance sidecars are enforced consistently.

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
