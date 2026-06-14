# Production System

## Intent

GTandDiedTooSoons is a repeatable production framework for composing spatially aware downtempo punk-bluegrass tracks in Ableton Live 12 Suite with Max for Live. The project should behave like a living lab: every source, device contract, session shape, and automation decision is inspectable in Git.

## Assumptions

- Target DAW: Ableton Live 12 Suite with Max for Live.
- Lead controller: AeroBand MIDI guitar/controller mapped to a banjo-like performance layer.
- Local commercial libraries may be installed, but they are never copied into this repository.
- OpenAI-backed tools can assist ideation, analysis, arrangement, transcription, and orchestration, but human review owns musical and rights decisions.

## Architecture

1. **Source layer**: public-domain or rights-cleared audio references documented in `catalogs/public-domain-bluegrass-sources.json`.
2. **Library layer**: Ableton/Arturia packs and instruments documented in `catalogs/recommended-packs.json` and local inventory snapshots.
   Installation readiness and account-gated pack backlog live in `catalogs/library-installation-plan.json`.
3. **Session layer**: track/routing/device contracts in `automation/live12-session-template.json`.
4. **Agent layer**: production worker roles in `automation/worker-chain.json`.
5. **Composition layer**: standalone track briefs in `compositions/down-tempo-punk-bluegrass-set.json`.
6. **Generated sketch layer**: deterministic Live-import build plans and MIDI sketches in `compositions/generated/`, rendered by `scripts/render_composition_sketches.py`.
7. **CI layer**: repository checks in `.github/workflows/live12-foundation-ci.yml`.

## Security and Operational Controls

- Secrets live in `.env` only and are ignored by Git.
- CI blocks common audio, installer, plugin, and Ableton binary artifacts unless a future reviewed Git LFS policy explicitly allows them.
- Generated `.mid` sketches are permitted only under `compositions/generated/midi/`; they contain note/control data and are validated against the JSON build plan.
- Inventory scripts record names, versions, and home-relative paths only.
- Audio acquisition requires explicit rights metadata and `approved_for_download: true`.
- Logs should not contain vocals, private lyrics, account IDs, license keys, or raw prompt data that is not needed for review.

## Scientific Claims Boundary

The project can use evidence-informed production tactics: repetition, call-and-response, spectral contrast, entrainment-friendly tempo ranges, tension/release, dynamic surprise, and spatial motion. It must not claim tracks are scientifically proven to affect the human psyche unless the repo includes an approved study protocol, consent model, data handling plan, and results.

## Rollback

All foundational changes are text manifests and scripts. Rollback is a normal Git revert. Local Ableton/Arturia installs and fetched public-domain audio are not modified by CI.
