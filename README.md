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
python3 scripts/render_composition_sketches.py --stable
python3 scripts/render_openai_worker_briefs.py --stable
python3 scripts/render_live12_daw_action_plan.py --stable
python3 scripts/render_live12_daw_mutation_package.py --stable
python3 scripts/validate_repo.py
python3 scripts/test_live12_daw_mutation_preflight.py
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
- `automation/openai-production-orchestration.json` - OpenAI, account automation, DAW automation, and approval-gate contract.
- `automation/live12-session-template.json` - repeatable Live set structure.
- `automation/worker-chain.json` - division-of-labor chain for production automation.
- `automation/generated/openai-worker-briefs.json` - generated role briefs for OpenAI-assisted production workers.
- `automation/generated/live12-daw-action-plan.json` - generated approval-gated Ableton Live 12 / Max for Live action queue for local session building.
- `automation/generated/live12-daw-mutation-package.json` - generated local-only preflight package for approved Live 12 / Max for Live session mutations and receipts.
- `compositions/down-tempo-punk-bluegrass-set.json` - initial standalone track briefs.
- `compositions/generated/live12-track-build-plans.json` - generated Live-import plan with MIDI hashes and device targets.
- `compositions/generated/midi/*.mid` - deterministic MIDI sketches for importing each standalone track into Live.
- `catalogs/public-domain-bluegrass-sources.json` - rights-aware source catalog.
- `catalogs/recommended-packs.json` - license-aware library and pack catalog.

## Safety Boundary

Commercial packs must be installed through official Ableton, Arturia, or vendor account flows. DAW/account automation is allowed when it uses official authenticated surfaces, avoids credential capture, records redacted receipts, and requires explicit approval for purchases, installs, Live-set mutation, exports, and release. Public-domain audio must have provenance before use. Automation may collect metadata and approved downloads, but it must not bypass terms, scrape copyrighted catalogs, commit licensed assets, or make unverified rights assumptions.
