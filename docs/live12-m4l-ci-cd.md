# Live 12 and Max for Live CI/CD Contract

GitHub-hosted runners do not include Ableton Live, Max for Live, Arturia Software Center, licensed packs, or a user account. CI therefore validates the production contract instead of pretending it can render or open `.als` files.

## CI Gates

- Validate JSON manifests.
- Confirm required repo files exist.
- Block secrets and unreviewed commercial/binary assets.
- Exercise local inventory code in dry-run mode.
- Ensure public-domain source entries include rights metadata.
- Regenerate OpenAI worker briefs and composition MIDI sketches in stable mode, then diff them against committed generated artifacts.
- Regenerate production appeal scorecards in stable mode, then diff JSON and Markdown outputs against committed artifacts.
- Regenerate the library installation queue in stable mode, then diff JSON and Markdown outputs against committed artifacts.
- Regenerate the OpenAI production swarm queue in stable mode, then diff JSON and Markdown outputs against committed artifacts.
- Regenerate Max for Live device contracts and `.maxpat` source blueprints in stable mode, then diff them against committed generated artifacts.
- Regenerate the Live 12 / Max for Live DAW action plan in stable mode, then diff it against the committed generated artifact.
- Regenerate the public-domain source deck in stable mode, then diff JSON and Markdown outputs against committed artifacts.
- Regenerate the Live 12 / Max for Live DAW mutation package in stable mode, then diff it against the committed generated artifact.
- Regenerate the Live 12 / Max for Live DAW mutation operator runbook and queue runbook in stable mode, then diff JSON and Markdown outputs against committed artifacts.
- Run Max for Live source contract probes without compiling `.amxd` devices.
- Run production appeal scorecard probes to verify hypothesis language, listener-study gates, Max for Live levers, and sensitive-path hygiene.
- Run library installation queue probes to verify official vendor hosts, approval gates, sanitized inventory summaries, and no CI vendor actions.
- Run OpenAI production swarm queue probes to verify role/task handoffs, approval gates, and sensitive-path hygiene.
- Run local DAW mutation preflight probes without opening Ableton or writing `.als`/`.amxd` files.
- Run DAW mutation runbook and queue runbook probes to verify command contracts, approval gates, Max for Live assignments, and sensitive-path hygiene.

## Local Gates

Run before committing production changes:

```bash
python3 scripts/validate_repo.py
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
python3 scripts/test_production_appeal_scorecards.py
python3 scripts/test_library_installation_queue.py
python3 scripts/test_openai_production_swarm_queue.py
python3 scripts/test_max_for_live_device_contracts.py
python3 scripts/test_live12_daw_mutation_preflight.py
python3 scripts/test_live12_daw_mutation_runbook.py
python3 scripts/test_live12_daw_mutation_queue_runbook.py
python3 scripts/test_public_domain_source_deck.py
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
| `automation/generated/production-appeal-scorecards.json` | Non-overclaiming per-track listening hypotheses, Max for Live levers, and evidence gates before stronger psychological claims. |
| `docs/production-appeal-scorecards.md` | Generated operator-facing scorecard summary for arrangement, spatial, mix, and listening-test decisions. |
| `automation/generated/library-installation-queue.json` | Metadata-only Ableton/Arturia queue for supervised official-surface account and library actions; never runs vendor actions in CI. |
| `docs/library-installation-queue.md` | Generated operator-facing library queue with approval gates, receipt root, official routes, and sanitized inventory summary. |
| `automation/generated/openai-production-swarm-queue.json` | Metadata-only per-track worker task queue for future OpenAI Agents/Responses execution without CI API calls or private audio. |
| `docs/openai-production-swarm-queue.md` | Generated human-readable swarm queue with track-by-track role handoffs, approval gates, and DAW/source references. |
| `automation/generated/max-for-live-device-contracts.json` | Source-only Max for Live contract bundle and `.maxpat` patch hashes for every session device contract. |
| `max-for-live/patches/*.maxpat` | Reviewable Max patch source blueprints; compile locally only after approval and rollback evidence. |
| `automation/generated/live12-daw-action-plan.json` | Approval-gated action queue for building generated tracks locally in Live 12 without committing `.als`, `.amxd`, samples, renders, credentials, or account artifacts. |
| `automation/generated/public-domain-source-deck.json` | Metadata-only approved source-deck handoff with rights evidence and muted-by-default per-track source assignments. |
| `docs/public-domain-source-deck.md` | Generated operator-facing source-deck summary that omits raw local paths and direct download URLs. |
| `automation/generated/live12-daw-mutation-package.json` | Local-only preflight jobs, affected-track scope, blocked export/release groups, and receipt contract for approved Live 12 / Max for Live mutations. |
| `automation/generated/live12-daw-mutation-runbook.json` | Generated operator contract for queue order, per-track commands, approval gates, Max for Live device assignments, and postflight checks. |
| `docs/live12-daw-mutation-runbook.md` | Generated human-readable checklist for applying local Ableton/Max mutations with rollback and receipt evidence. |
| `automation/generated/live12-daw-mutation-queue-runbook.json` | Generated full-set queue command manifest for staging ignored local DAW mutation artifacts without launching Ableton automatically. |
| `docs/live12-daw-mutation-queue-runbook.md` | Generated full-set queue handoff for queue preparation, gated per-track launch commands, and receipt capture. |
| `compositions/generated/live12-track-build-plans.json` | Human-readable import map, device targets, MIDI hashes, and safety constraints for each standalone track. |
| `compositions/generated/midi/*.mid` | Deterministic placeholder MIDI sketches for Live import and replacement with verified Ableton/Arturia instruments. |
| `inventory/live12-local-inventory.*` | Non-sensitive local host state for pack and plugin availability. |
| `catalogs/recommended-packs.json` | License-aware planning for Ableton and Arturia content. |
| `catalogs/library-installation-plan.json` | Account-gated Ableton/Arturia backlog consumed by the generated installation queue. |
| `catalogs/public-domain-bluegrass-sources.json` | Rights-aware source pool for sampling and reference study. |

## Deployment Model

1. Merge text contracts and scripts through PR.
2. Render the library installation queue and perform approved pack actions locally through official vendor account flows:

```bash
python3 scripts/render_library_installation_queue.py --stable
```

Use `docs/library-installation-queue.md` as the operator handoff. It is generated from tracked catalogs and local inventory, performs no vendor login, purchase, install, DAW launch, or OpenAI API call, and records any local evidence under ignored `output/library-installation/`.

3. Refresh inventory.
4. Build or update Live set locally.
5. Prepare and stage the full six-track DAW mutation queue under ignored `output/` folders:

```bash
python3 scripts/prepare_live12_daw_mutation_queue.py
```

This writes `output/daw-mutation-queue/queue-manifest.json` plus per-track mutation requests, receipt templates, editable `operator-evidence.json` drafts, Ableton import bundles, launch plans, and bundle evidence templates. The queue manifest paths are relative to its `artifact_base`, normally `output/`.
The queue also references `automation/generated/max-for-live-device-contracts.json` and lists the committed `.maxpat` source patches required for each queued track.

The generated runbook provides the same queue as an operator checklist:

```bash
python3 scripts/render_live12_daw_mutation_runbook.py --stable
```

Use `docs/live12-daw-mutation-runbook.md` as the local DAW mutation checklist. It is generated from committed contracts and remains non-authoritative if edited by hand; regenerate it instead.

The generated queue runbook provides the full-set queue handoff with gated launch and receipt commands for every track:

```bash
python3 scripts/render_live12_daw_mutation_queue_runbook.py --stable
```

Use `docs/live12-daw-mutation-queue-runbook.md` when preparing the whole set. It is generated from committed contracts and remains non-authoritative if edited by hand; regenerate it instead.

6. For targeted single-track work, write local mutation requests, receipt templates, and editable operator evidence drafts under `output/daw-mutations/`:

```bash
python3 scripts/prepare_live12_daw_mutation.py --track good-vibrations-in-a-burned-barn
```

7. Stage a local Ableton import bundle with the generated MIDI and launch plan:

```bash
python3 scripts/stage_live12_daw_import_bundle.py \
  --request output/daw-mutations/good-vibrations-in-a-burned-barn/mutation-request.json
```

To send the staged MIDI to Ableton Live, the launcher requires explicit mutation approval and rollback evidence:

```bash
python3 scripts/stage_live12_daw_import_bundle.py \
  --request output/daw-mutations/good-vibrations-in-a-burned-barn/mutation-request.json \
  --launch-ableton \
  --confirm-live-mutation \
  --operator-approval-reference <approval-id> \
  --rollback-copy-reference <rollback-note>
```

8. After an approved local Ableton/Max mutation attempt, fill the generated `operator-evidence.json` draft with approval and rollback references, then record evidence against the prepared request:

```bash
python3 scripts/record_live12_daw_mutation_receipt.py \
  --request output/daw-mutations/good-vibrations-in-a-burned-barn/mutation-request.json \
  --evidence output/daw-mutations/good-vibrations-in-a-burned-barn/operator-evidence.json
```

9. Export stems/renders to an artifact store or release process with provenance, not directly into the source repo.
