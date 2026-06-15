# Production System

## Intent

GTandDiedTooSoons is a repeatable production framework for composing spatially aware downtempo punk-bluegrass tracks in Ableton Live 12 Suite with Max for Live. The project should behave like a living lab: every source, device contract, session shape, and automation decision is inspectable in Git.

## Assumptions

- Target DAW: Ableton Live 12 Suite with Max for Live.
- Lead controller: AeroBand MIDI guitar/controller mapped to a banjo-like performance layer.
- Local commercial libraries may be installed, but they are never copied into this repository.
- OpenAI-backed tools can assist ideation, analysis, arrangement, transcription, and orchestration, but human review owns musical and rights decisions.

## Architecture

1. **Source layer**: public-domain or rights-cleared audio references documented in `catalogs/public-domain-bluegrass-sources.json`, download evidence in `sources/public-domain/download-ledger.json`, and generated source-deck handoff artifacts in `automation/generated/public-domain-source-deck.json` plus `docs/public-domain-source-deck.md`.
2. **Library layer**: Ableton/Arturia packs and instruments documented in `catalogs/recommended-packs.json` and local inventory snapshots.
   Installation readiness and account-gated pack backlog live in `catalogs/library-installation-plan.json`.
3. **Session layer**: track/routing/device contracts in `automation/live12-session-template.json`.
4. **Max for Live source layer**: device definitions in `automation/max-for-live-device-contracts.json`, generated source bundle in `automation/generated/max-for-live-device-contracts.json`, and reviewable `.maxpat` blueprints in `max-for-live/patches/`.
5. **Agent layer**: production worker roles in `automation/worker-chain.json`, role briefs in `automation/generated/openai-worker-briefs.json`, and per-track swarm queue handoffs in `automation/generated/openai-production-swarm-queue.json` plus `docs/openai-production-swarm-queue.md`.
6. **Composition layer**: standalone track briefs in `compositions/down-tempo-punk-bluegrass-set.json`.
7. **Generated sketch layer**: deterministic Live-import build plans and MIDI sketches in `compositions/generated/`, rendered by `scripts/render_composition_sketches.py`.
8. **Production appeal layer**: generated non-overclaiming listening hypotheses in `automation/generated/production-appeal-scorecards.json` and `docs/production-appeal-scorecards.md`, rendered by `scripts/render_production_appeal_scorecards.py`.
9. **DAW action layer**: approval-gated local Ableton/Max for Live action queues in `automation/generated/live12-daw-action-plan.json`, rendered by `scripts/render_live12_daw_action_plan.py`.
10. **DAW mutation layer**: local-only preflight jobs and receipt templates in `automation/generated/live12-daw-mutation-package.json`, batch-staged by `scripts/prepare_live12_daw_mutation_queue.py` under ignored `output/` folders with per-track Max for Live source patch references. The generated operator runbooks in `automation/generated/live12-daw-mutation-runbook.json`, `automation/generated/live12-daw-mutation-queue-runbook.json`, `docs/live12-daw-mutation-runbook.md`, and `docs/live12-daw-mutation-queue-runbook.md` turn that queue into auditable per-track commands.
11. **CI layer**: repository checks in `.github/workflows/live12-foundation-ci.yml`.

## Security and Operational Controls

- Secrets live in `.env` only and are ignored by Git.
- CI blocks common audio, installer, plugin, and Ableton binary artifacts unless a future reviewed Git LFS policy explicitly allows them.
- Generated `.mid` sketches are permitted only under `compositions/generated/midi/`; they contain note/control data and are validated against the JSON build plan.
- Generated Max for Live patches are permitted only as reviewable `.maxpat` JSON source under `max-for-live/patches/`; compiled `.amxd` devices remain blocked release artifacts.
- Generated DAW action plans are proposal-only text. They may describe Live/Max for Live actions, but they must not mutate `.als`, `.amxd`, account state, exports, or local devices without approval and rollback evidence.
- Generated DAW mutation packages are execution preflight text. They may prepare local ignored mutation requests and receipt templates, but they must not claim a Live-set mutation was applied before Ableton/Max confirms the change and a rollback reference exists.
- Generated DAW mutation runbooks and queue runbooks are operator checklists. They may include local command paths under ignored `output/` roots, but they must keep Ableton launches approval-gated and must not contain absolute user paths, raw source audio paths, secrets, or committed DAW binary references.
- Generated production appeal scorecards are hypotheses and listening-test gates. They may guide arrangement, Max for Live macro choices, and mix review, but they must not claim scientifically proven psychological effects without approved protocol and results.
- Inventory scripts record names, versions, and home-relative paths only.
- Audio acquisition requires explicit rights metadata and `approved_for_download: true`.
- Generated public-domain source decks are metadata-only handoffs. They may include source IDs, rights evidence, credit summaries, SHA-256 values, and per-track source candidates, but they must not expose raw local audio paths or download URLs in tracked generated artifacts.
- Logs should not contain vocals, private lyrics, account IDs, license keys, or raw prompt data that is not needed for review.

## Scientific Claims Boundary

The project can use evidence-informed production tactics: repetition, call-and-response, spectral contrast, entrainment-friendly tempo ranges, tension/release, dynamic surprise, and spatial motion. It must not claim tracks are scientifically proven to affect the human psyche unless the repo includes an approved study protocol, consent model, data handling plan, and results.

## Rollback

All foundational changes are text manifests and scripts. Rollback is a normal Git revert. Local Ableton/Arturia installs and fetched public-domain audio are not modified by CI.
