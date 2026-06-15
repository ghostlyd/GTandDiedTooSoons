# Playwright Source Capture Runbook

Browser automation is used for source metadata review, not for unsafe downloading.

## Current Tool State

- `npx` is available.
- The user-scoped `playwright_cli.sh` wrapper currently resolves to a stale `playwright-cli` binary path with the installed `@playwright/mcp` package.
- `npx --yes playwright --version` reported Playwright 1.60.0 on 2026-06-15.
- Direct `npx --package playwright` module resolution was unreliable with the local Node/npm runtime on 2026-06-14.
- A temporary runtime under `/tmp/gt-playwright-runtime` successfully ran Playwright 1.60.0 against the installed Chrome channel without adding Node dependencies to this repository.

## Verified Commands

```bash
tmpdir=/tmp/gt-playwright-runtime
rm -rf "$tmpdir"
mkdir -p "$tmpdir"
cd "$tmpdir"
npm init -y
npm install playwright@1.60.0
node -e "const { chromium } = require('playwright'); console.log(typeof chromium.launch)"
```

The Copyright Office, UCSB, and LOC Citizen DJ screenshots rendered real rights/source pages and are intentionally ignored under `output/playwright/`.

The expanded 2026-06-14 LOC Citizen DJ capture used `/tmp/gt-playwright-runtime/node_modules/playwright` to write:

- `output/playwright/loc-citizen-dj-folk-20260614-expanded.png`
- `output/playwright/loc-citizen-dj-folk-20260614-trace.zip`

The 2026-06-15 LOC Citizen DJ capture used the same temporary runtime and wrote:

- `output/playwright/loc-citizen-dj-folk-20260615.png`
- `output/playwright/loc-citizen-dj-folk-20260615-rendered.json`
- `output/playwright/loc-citizen-dj-folk-20260615-trace.zip`

The trace was inspected with:

```bash
npx --yes playwright trace open output/playwright/loc-citizen-dj-folk-20260615-trace.zip
npx --yes playwright trace actions
npx --yes playwright trace requests
npx --yes playwright trace console
npx --yes playwright trace close
```

Trace metadata: Chromium, 1440x1200 viewport, 4 actions, 18 network requests, 0 Playwright errors. Browser console output contained Adobe analytics DNS lookup failures only; the LOC page, screenshot, and rendered link extraction completed.

## Source Notes

The LOC Citizen DJ Folk Music collection page is approved as browser evidence for item-level downloads in `catalogs/public-domain-bluegrass-sources.json`. Because `output/playwright/` is ignored, the catalog also stores concise rights evidence from the page: public-domain status, commercial reuse scope, credit recommendation, and cultural-respect notes. Its WAV/MP3 pack links are still fetched through `scripts/fetch_public_domain_audio.py` so exact host checks, path-prefix allow-lists, size limits, SHA-256 ledger entries, and local provenance sidecars are enforced consistently.

Target a subset of approved entries with repeated `--source-id` flags:

```bash
python3 scripts/fetch_public_domain_audio.py \
  --execute \
  --source-id loc-citizen-dj-turkey-in-the-straw-medley-247928-001 \
  --source-id loc-citizen-dj-carnival-of-venice-260123-001 \
  --source-id loc-citizen-dj-medley-old-time-reels-248482-001 \
  --source-id loc-citizen-dj-medley-favorite-reels-422524-001 \
  --source-id loc-citizen-dj-hornpipe-13796-001 \
  --source-id loc-citizen-dj-lamplighters-hornpipe-28465-001
```

The LOC Henry Reed collection page rendered a Cloudflare security-verification interstitial in headless Chromium on 2026-06-14. Do not treat that screenshot as source metadata evidence.

## Trace Workflow

When future Playwright captures produce `trace.zip`, inspect them with the installed Playwright tooling available in that runtime. On 2026-06-14, `show-trace` was available and the newer `playwright trace open` subcommand was not:

```bash
/tmp/gt-playwright-runtime/node_modules/.bin/playwright show-trace output/playwright/loc-citizen-dj-folk-20260614-trace.zip
```

For non-UI inspection, unzip the trace and inspect `trace.trace`, `trace.network`, and resource files. The 2026-06-14 trace contains a `goto` action for `https://citizen-dj.labs.loc.gov/loc-jukebox-folk-songs/use/` plus DOM snapshots and screenshots.

Do not commit traces by default; store only concise notes or screenshots needed for review.
