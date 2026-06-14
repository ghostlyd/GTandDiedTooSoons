# OpenAI Orchestration Design

This project should use OpenAI APIs as production tooling, not as an unreviewed replacement for authorship or licensing judgment.

Official docs consulted:

- Responses API and tool use: https://developers.openai.com/api/docs
- Agents SDK orchestration: https://developers.openai.com/api/docs/guides/agents
- Agents SDK handoffs and tracing: https://openai.github.io/openai-agents-python/
- Realtime and audio: https://developers.openai.com/api/docs/guides/realtime
- OpenAI SDKs and CLI: https://developers.openai.com/api/docs/libraries
- Codex MCP workflows: https://developers.openai.com/codex/mcp

## Versioned Contract

The executable orchestration contract lives in `automation/openai-production-orchestration.json`.

It defines:

- official OpenAI API surfaces used by the project
- data classes and privacy boundaries
- narrow tool contracts for inventory, rights checks, worker briefs, session proposals, account/vendor automation, DAW automation, and release checklists
- approval gates for source downloads, private audio upload, vendor account actions, purchases/license changes, Live-set mutation, and export/release
- Max for Live rollback and artifact boundaries

Generated worker briefs are rendered to `automation/generated/openai-worker-briefs.json`:

```bash
python3 scripts/render_openai_worker_briefs.py --stable
python3 scripts/validate_repo.py
```

CI diffs the generated file against a stable render on both Ubuntu and macOS, so edits to the worker chain, Live template, DAW mutation package, installation plan, inventory, source catalog, or composition set must be reflected in the generated briefs.

Generated DAW mutation packages are rendered to `automation/generated/live12-daw-mutation-package.json`:

```bash
python3 scripts/render_max_for_live_device_contracts.py --stable
python3 scripts/render_live12_daw_mutation_package.py --stable
python3 scripts/prepare_live12_daw_mutation_queue.py --stable
python3 scripts/prepare_live12_daw_mutation.py --track good-vibrations-in-a-burned-barn
python3 scripts/stage_live12_daw_import_bundle.py --request output/daw-mutations/good-vibrations-in-a-burned-barn/mutation-request.json
python3 scripts/record_live12_daw_mutation_receipt.py --request output/daw-mutations/good-vibrations-in-a-burned-barn/mutation-request.json --evidence output/daw-mutations/good-vibrations-in-a-burned-barn/operator-evidence.json
python3 scripts/test_live12_daw_mutation_preflight.py
```

They translate the source-only Max for Live device contracts and approval-gated DAW action plan into a full-set local queue, per-track Max patch references, per-track preflight jobs, ignored Ableton import bundles, and receipt templates under `output/`. This is the bridge for Ableton/Max work: render `.maxpat` source blueprints, prepare the queue, stage import bundles, approve each Live mutation, launch Live locally, then record operator evidence without committing DAW binaries or audio artifacts.

## API Fit

| Need | OpenAI surface | Guardrail |
| --- | --- | --- |
| Prompted arrangement, lyric alternatives, source summaries | Responses API | Use structured outputs and store prompts/results only when useful. |
| Multi-role production chain | Agents SDK | Handoffs require explicit role boundaries and trace review. |
| Live performance co-pilot or talkback | Realtime API | Do not stream private rehearsal audio without explicit opt-in. |
| Transcribing field notes or rehearsal takes | Audio / transcription APIs | Keep raw audio local unless a reviewed workflow permits upload. |
| Codex-driven repo automation | Codex CLI / MCP | Run in branch/worktree, require tests, PR review, and no secret exposure. |
| ChatGPT-facing control surface | Apps SDK / MCP | Expose narrow tools; never expose arbitrary filesystem or DAW control. |
| Account-authorized library installs | Official vendor UI/app automation | Use authenticated user sessions only; do not capture credentials, bypass terms, or commit installers/assets. |
| Ableton Live / Max for Live session actions | Reviewed local DAW automation | Require rollback copy, affected-track scope, action receipt, and post-action validation. |

## Worker Chain

The canonical worker chain is versioned in `automation/worker-chain.json`.

High-value divisions of labor:

- **Archivist**: rights metadata, source lineage, historical notes.
- **Banjo Controller Engineer**: AeroBand MIDI mapping, velocity curves, articulations.
- **Max Device Builder**: clock, probability, modulation, and provenance sampler devices.
- **Arrangement Producer**: song form, hooks, contrast, and track-specific constraints.
- **Mix Engineer**: gain staging, masking, space, loudness, and translation checks.
- **Release QA**: provenance, credits, export manifest, and CI status.

## Safe Tool Design

Tools exposed to agents should be narrow and auditable:

- `read_inventory`: reads generated inventory only.
- `propose_session_change`: writes a patch proposal, not a Live set directly.
- `validate_source_rights`: checks catalog metadata before download.
- `summarize_take`: processes local transcript text, not raw audio by default.
- `automate_vendor_install`: uses official Ableton, Arturia, or vendor account surfaces after approval and writes a redacted receipt plus refreshed inventory delta.
- `automate_daw_session`: applies approved local Ableton/Max for Live actions from the DAW mutation package and records a local-only receipt from operator evidence.
- `render_checklist`: emits required human checks before export.

No agent gets unrestricted shell, filesystem, browser, account, or DAW control in production without a branch, log, approval boundary, and rollback path.

## Automation Boundary

DAW and account automation are in scope for this project. The secure default is not "no automation"; it is official-surface automation with explicit gates.

Allowed:

- navigate official Ableton, Arturia, or vendor pages/apps in an authenticated user session
- trigger already-entitled installs through official account, Live Browser, or Arturia Software Center flows
- refresh local inventory after install
- apply approved Live/Max for Live changes to a local session after a rollback copy exists
- record redacted receipts with product/action/result metadata

Blocked:

- capturing passwords, API keys, cookies, serials, license files, or payment data
- bypassing paywalls, DRM, terms, or entitlement checks
- purchasing or changing license state without explicit confirmation
- committing installers, packs, presets, samples, `.als`, `.amxd`, plugin binaries, or raw/private audio
- streaming private rehearsal audio to OpenAI without session-specific opt-in
