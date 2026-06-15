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
python3 scripts/render_production_appeal_scorecards.py --stable
python3 scripts/render_library_installation_queue.py --stable
python3 scripts/render_openai_worker_briefs.py --stable
python3 scripts/render_openai_production_swarm_queue.py --stable
python3 scripts/render_max_for_live_device_contracts.py --stable
python3 scripts/render_live12_daw_action_plan.py --stable
python3 scripts/render_public_domain_source_deck.py --stable
python3 scripts/render_live12_daw_mutation_package.py --stable
python3 scripts/render_live12_daw_mutation_runbook.py --stable
python3 scripts/render_live12_daw_mutation_queue_runbook.py --stable
python3 scripts/validate_repo.py
python3 scripts/test_production_appeal_scorecards.py
python3 scripts/test_library_installation_queue.py
python3 scripts/test_library_installation_preflight.py
python3 scripts/test_openai_production_swarm_queue.py
python3 scripts/test_max_for_live_device_contracts.py
python3 scripts/test_composition_mutation_blueprints.py
python3 scripts/test_live12_daw_mutation_preflight.py
python3 scripts/test_live12_daw_mutation_runbook.py
python3 scripts/test_live12_daw_mutation_queue_runbook.py
python3 scripts/test_public_domain_source_deck.py
python3 scripts/prepare_library_installation_queue.py --stable
python3 scripts/inventory_live_suite.py
```

Generated local inventory lands in `inventory/live12-local-inventory.json` and `inventory/live12-local-inventory.md`. Paths are home-relative and do not copy licensed content into Git.

## Core Artifacts

- `docs/production-system.md` - project architecture and operating model.
- `docs/production-appeal-scorecards.md` - generated non-overclaiming production appeal hypotheses and listener-study gates.
- `docs/library-installation-queue.md` - generated approval-gated Ableton/Arturia library installation queue.
- `docs/live12-m4l-ci-cd.md` - CI/CD contract for Ableton Live 12 and Max for Live work.
- `docs/openai-orchestration.md` - OpenAI-enabled agent and worker-chain design.
- `docs/openai-production-swarm-queue.md` - generated track-by-track OpenAI worker handoff queue for role-scoped production tasks.
- `docs/source-acquisition-policy.md` - public-domain source and sampling rules.
- `docs/public-domain-source-deck.md` - generated metadata-only source deck handoff for Ableton/Max sampling.
- `docs/playwright-source-capture.md` - browser capture and trace runbook for source research.
- `docs/recommended-packs.md` - Ableton and Arturia recommendations.
- `docs/live12-daw-mutation-runbook.md` - generated operator checklist for approval-gated local DAW mutations.
- `docs/live12-daw-mutation-queue-runbook.md` - generated full-set queue handoff for local-only DAW mutation staging, gated launch, and receipts.
- `automation/openai-production-orchestration.json` - OpenAI, account automation, DAW automation, and approval-gate contract.
- `automation/live12-session-template.json` - repeatable Live set structure.
- `automation/worker-chain.json` - division-of-labor chain for production automation.
- `automation/max-for-live-device-contracts.json` - source definitions for reviewable Max for Live device blueprints.
- `automation/generated/openai-worker-briefs.json` - generated role briefs for OpenAI-assisted production workers.
- `automation/generated/openai-production-swarm-queue.json` - generated metadata-only per-track swarm queue linking worker roles to DAW mutation and source-deck handoffs.
- `automation/generated/production-appeal-scorecards.json` - generated per-track affect/listening hypotheses, Max for Live levers, and evidence gates before stronger claims.
- `automation/generated/library-installation-queue.json` - generated metadata-only queue for supervised official Ableton/Arturia account and library actions.
- `scripts/prepare_library_installation_queue.py` - local-only request, launch-plan, evidence, and receipt scaffold generator for the library queue.
- `scripts/record_library_installation_receipt.py` - local-only receipt recorder for approved vendor/account action evidence.
- `automation/generated/max-for-live-device-contracts.json` - generated source-only Max for Live contract bundle with `.maxpat` patch hashes.
- `automation/generated/live12-daw-action-plan.json` - generated approval-gated Ableton Live 12 / Max for Live action queue for local session building.
- `automation/generated/public-domain-source-deck.json` - generated source deck manifest with approved source metadata, per-track assignments, and muted-by-default policy.
- `automation/generated/live12-daw-mutation-package.json` - generated local-only preflight package for approved Live 12 / Max for Live session mutations and receipts.
- `automation/generated/live12-daw-mutation-runbook.json` - generated DAW mutation operator contract with commands, approval gates, Max for Live device assignments, and postflight checks.
- `automation/generated/live12-daw-mutation-queue-runbook.json` - generated full-set queue command manifest for staging ignored local DAW mutation artifacts without launching Ableton automatically.
- `max-for-live/patches/*.maxpat` - reviewable Max patch source blueprints, not compiled `.amxd` devices.
- `compositions/down-tempo-punk-bluegrass-set.json` - initial standalone track briefs.
- `compositions/composition-mutation-blueprints.json` - machine-checkable per-track composition DNA: full bluegrass role jobs, alien-electronic role jobs, punk constraints, source-deck approval state, and Max for Live mutation lanes.
- `compositions/generated/live12-track-build-plans.json` - generated Live-import plan with MIDI hashes, device targets, and mirrored composition mutation blueprints.
- `compositions/generated/midi/*.mid` - deterministic MIDI sketches for importing each standalone track into Live.
- `catalogs/public-domain-bluegrass-sources.json` - rights-aware source catalog.
- `catalogs/recommended-packs.json` - license-aware library and pack catalog.

## Safety Boundary

Commercial packs must be installed through official Ableton, Arturia, or vendor account flows. DAW/account automation is allowed when it uses official authenticated surfaces, avoids credential capture, records redacted receipts, and requires explicit approval for purchases, installs, Live-set mutation, exports, and release. Public-domain audio must have provenance before use. Automation may collect metadata and approved downloads, but it must not bypass terms, scrape copyrighted catalogs, commit licensed assets, or make unverified rights assumptions.
