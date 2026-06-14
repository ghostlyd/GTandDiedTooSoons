# GTandDiedTooSoons

Experimental electronic, punk, and bluegrass out of Santa Cruz, California.

This repository is the living production system for a Live 12 Suite / Max for Live project built around:

- bluegrass instrumentation and historical source literacy
- deep-house pulse, spatial movement, and alien electronic processing
- independent punk energy, constraint, and directness
- auditable automation for composition, sampling, orchestration, and release work

The repo intentionally tracks process, manifests, device contracts, session templates, and provenance. It does not track commercial Ableton/Arturia content, private recordings, secrets, installers, or bulky audio binaries.

## Quick Start

```bash
python3 scripts/validate_repo.py
python3 scripts/inventory_live_suite.py
```

Generated local inventory lands in `inventory/live12-local-inventory.json` and `inventory/live12-local-inventory.md`. Paths are home-relative and do not copy licensed content into Git.

## Core Artifacts

- `docs/production-system.md` - project architecture and operating model.
- `docs/live12-m4l-ci-cd.md` - CI/CD contract for Ableton Live 12 and Max for Live work.
- `docs/openai-orchestration.md` - OpenAI-enabled agent and worker-chain design.
- `docs/source-acquisition-policy.md` - public-domain source and sampling rules.
- `docs/playwright-source-capture.md` - browser capture and trace runbook for source research.
- `docs/recommended-packs.md` - Ableton and Arturia recommendations.
- `automation/live12-session-template.json` - repeatable Live set structure.
- `automation/worker-chain.json` - division-of-labor chain for production automation.
- `compositions/down-tempo-punk-bluegrass-set.json` - initial standalone track briefs.
- `catalogs/public-domain-bluegrass-sources.json` - rights-aware source catalog.
- `catalogs/recommended-packs.json` - license-aware library and pack catalog.

## Safety Boundary

Commercial packs must be installed through official Ableton or Arturia account flows. Public-domain audio must have provenance before use. Automation may collect metadata and approved downloads, but it must not bypass terms, scrape copyrighted catalogs, or make unverified rights assumptions.
