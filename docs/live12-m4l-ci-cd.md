# Live 12 and Max for Live CI/CD Contract

GitHub-hosted runners do not include Ableton Live, Max for Live, Arturia Software Center, licensed packs, or a user account. CI therefore validates the production contract instead of pretending it can render or open `.als` files.

## CI Gates

- Validate JSON manifests.
- Confirm required repo files exist.
- Block secrets and unreviewed commercial/binary assets.
- Exercise local inventory code in dry-run mode.
- Ensure public-domain source entries include rights metadata.
- Regenerate OpenAI worker briefs and composition MIDI sketches in stable mode, then diff them against committed generated artifacts.
- Regenerate the Live 12 / Max for Live DAW action plan in stable mode, then diff it against the committed generated artifact.

## Local Gates

Run before committing production changes:

```bash
python3 scripts/validate_repo.py
python3 scripts/render_live12_daw_action_plan.py --stable
python3 scripts/inventory_live_suite.py
```

For future Max device work:

- Store source patches as reviewable `.maxpat` JSON where possible.
- Treat `.amxd`, `.als`, `.alp`, and rendered audio as release artifacts, not ordinary source.
- Treat generated `.mid` files as importable note/control sketches only; the reviewable source of truth is `compositions/generated/live12-track-build-plans.json`.
- If binary artifacts must be versioned, add a pull request that documents Git LFS policy, provenance, and rollback.

## Ableton Workflow Mapping

| Repo artifact | Live 12 / Max for Live responsibility |
| --- | --- |
| `automation/live12-session-template.json` | Canonical track layout, routing, devices, sends, and performance controls. |
| `automation/worker-chain.json` | Agent/worker responsibilities for arrangement, sound design, source research, mix review, and release QA. |
| `automation/generated/live12-daw-action-plan.json` | Approval-gated action queue for building generated tracks locally in Live 12 without committing `.als`, `.amxd`, samples, renders, credentials, or account artifacts. |
| `compositions/generated/live12-track-build-plans.json` | Human-readable import map, device targets, MIDI hashes, and safety constraints for each standalone track. |
| `compositions/generated/midi/*.mid` | Deterministic placeholder MIDI sketches for Live import and replacement with verified Ableton/Arturia instruments. |
| `inventory/live12-local-inventory.*` | Non-sensitive local host state for pack and plugin availability. |
| `catalogs/recommended-packs.json` | License-aware install planning for Ableton and Arturia content. |
| `catalogs/public-domain-bluegrass-sources.json` | Rights-aware source pool for sampling and reference study. |

## Deployment Model

1. Merge text contracts and scripts through PR.
2. Install packs locally through official vendor account flows.
3. Refresh inventory.
4. Build or update Live set locally.
5. Export stems/renders to an artifact store or release process with provenance, not directly into the source repo.
