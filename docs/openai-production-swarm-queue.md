# OpenAI Production Swarm Queue

Generated metadata-only queue for role-scoped OpenAI production workers.

Status: `planned_not_executed`.

No OpenAI API call is made by this renderer or CI check.

This queue is designed for future Agents SDK handoffs and Responses API structured outputs while keeping DAW, account, source-download, private-audio, and export actions behind explicit approval gates.

## Official Surfaces

- Responses API structured outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- Agents SDK handoffs: https://openai.github.io/openai-agents-python/handoffs/
- Agents SDK tracing: https://openai.github.io/openai-agents-python/tracing/
- Apps SDK MCP: https://developers.openai.com/apps-sdk/build/mcp-server

## Queue Summary

- Tracks: `6`
- Roles per track: `6`
- Total tasks: `36`
- Local output root: `output/openai-swarm`

## Tracks

### Good Vibrations in a Burned Barn

- Track slug: `good-vibrations-in-a-burned-barn`
- Tempo/key: `96 BPM`, `D mixolydian`
- Source deck state: `muted_until_human_provenance_review`
- Planned DAW actions: `19`
- DAW request: `output/daw-mutations/good-vibrations-in-a-burned-barn/mutation-request.json`

- `good-vibrations-in-a-burned-barn.archivist.01` - Music Library Scientist via `responses_api`
  Tools: `validate_source_rights`, `render_worker_brief`. Approval gates: `source_download`.
- `good-vibrations-in-a-burned-barn.controller_engineer.02` - AeroBand Banjo Controller Engineer via `agents_sdk`
  Tools: `read_inventory`, `propose_session_change`, `automate_daw_session`. Approval gates: `live_set_mutation`.
- `good-vibrations-in-a-burned-barn.max_device_builder.03` - Max for Live Device Builder via `agents_sdk`
  Tools: `read_inventory`, `propose_session_change`, `automate_daw_session`. Approval gates: `live_set_mutation`.
- `good-vibrations-in-a-burned-barn.arrangement_producer.04` - Arrangement Producer via `responses_api`
  Tools: `render_worker_brief`, `propose_session_change`. Approval gates: `live_set_mutation`, `private_audio_upload`.
- `good-vibrations-in-a-burned-barn.mix_engineer.05` - Masterclass Audio Technician via `agents_sdk`
  Tools: `read_inventory`, `automate_daw_session`, `render_release_checklist`. Approval gates: `private_audio_upload`, `live_set_mutation`, `export_or_release`.
- `good-vibrations-in-a-burned-barn.release_qa.06` - Release and Provenance QA via `responses_api`
  Tools: `validate_source_rights`, `read_inventory`, `render_release_checklist`. Approval gates: `source_download`, `vendor_account_action`, `purchase_or_license_change`, `export_or_release`.

### A.P. Carter in the Warehouse

- Track slug: `a-p-carter-in-the-warehouse`
- Tempo/key: `88 BPM`, `A minor / dorian interchange`
- Source deck state: `muted_until_human_provenance_review`
- Planned DAW actions: `18`
- DAW request: `output/daw-mutations/a-p-carter-in-the-warehouse/mutation-request.json`

- `a-p-carter-in-the-warehouse.archivist.01` - Music Library Scientist via `responses_api`
  Tools: `validate_source_rights`, `render_worker_brief`. Approval gates: `source_download`.
- `a-p-carter-in-the-warehouse.controller_engineer.02` - AeroBand Banjo Controller Engineer via `agents_sdk`
  Tools: `read_inventory`, `propose_session_change`, `automate_daw_session`. Approval gates: `live_set_mutation`.
- `a-p-carter-in-the-warehouse.max_device_builder.03` - Max for Live Device Builder via `agents_sdk`
  Tools: `read_inventory`, `propose_session_change`, `automate_daw_session`. Approval gates: `live_set_mutation`.
- `a-p-carter-in-the-warehouse.arrangement_producer.04` - Arrangement Producer via `responses_api`
  Tools: `render_worker_brief`, `propose_session_change`. Approval gates: `live_set_mutation`, `private_audio_upload`.
- `a-p-carter-in-the-warehouse.mix_engineer.05` - Masterclass Audio Technician via `agents_sdk`
  Tools: `read_inventory`, `automate_daw_session`, `render_release_checklist`. Approval gates: `private_audio_upload`, `live_set_mutation`, `export_or_release`.
- `a-p-carter-in-the-warehouse.release_qa.06` - Release and Provenance QA via `responses_api`
  Tools: `validate_source_rights`, `read_inventory`, `render_release_checklist`. Approval gates: `source_download`, `vendor_account_action`, `purchase_or_license_change`, `export_or_release`.

### No Gods, No Masters, No Quantize

- Track slug: `no-gods-no-masters-no-quantize`
- Tempo/key: `104 BPM`, `G major with flat-7 pressure`
- Source deck state: `muted_until_human_provenance_review`
- Planned DAW actions: `18`
- DAW request: `output/daw-mutations/no-gods-no-masters-no-quantize/mutation-request.json`

- `no-gods-no-masters-no-quantize.archivist.01` - Music Library Scientist via `responses_api`
  Tools: `validate_source_rights`, `render_worker_brief`. Approval gates: `source_download`.
- `no-gods-no-masters-no-quantize.controller_engineer.02` - AeroBand Banjo Controller Engineer via `agents_sdk`
  Tools: `read_inventory`, `propose_session_change`, `automate_daw_session`. Approval gates: `live_set_mutation`.
- `no-gods-no-masters-no-quantize.max_device_builder.03` - Max for Live Device Builder via `agents_sdk`
  Tools: `read_inventory`, `propose_session_change`, `automate_daw_session`. Approval gates: `live_set_mutation`.
- `no-gods-no-masters-no-quantize.arrangement_producer.04` - Arrangement Producer via `responses_api`
  Tools: `render_worker_brief`, `propose_session_change`. Approval gates: `live_set_mutation`, `private_audio_upload`.
- `no-gods-no-masters-no-quantize.mix_engineer.05` - Masterclass Audio Technician via `agents_sdk`
  Tools: `read_inventory`, `automate_daw_session`, `render_release_checklist`. Approval gates: `private_audio_upload`, `live_set_mutation`, `export_or_release`.
- `no-gods-no-masters-no-quantize.release_qa.06` - Release and Provenance QA via `responses_api`
  Tools: `validate_source_rights`, `read_inventory`, `render_release_checklist`. Approval gates: `source_download`, `vendor_account_action`, `purchase_or_license_change`, `export_or_release`.

### Possum Kingdom Afterhours

- Track slug: `possum-kingdom-afterhours`
- Tempo/key: `82 BPM`, `E minor pentatonic`
- Source deck state: `muted_until_human_provenance_review`
- Planned DAW actions: `18`
- DAW request: `output/daw-mutations/possum-kingdom-afterhours/mutation-request.json`

- `possum-kingdom-afterhours.archivist.01` - Music Library Scientist via `responses_api`
  Tools: `validate_source_rights`, `render_worker_brief`. Approval gates: `source_download`.
- `possum-kingdom-afterhours.controller_engineer.02` - AeroBand Banjo Controller Engineer via `agents_sdk`
  Tools: `read_inventory`, `propose_session_change`, `automate_daw_session`. Approval gates: `live_set_mutation`.
- `possum-kingdom-afterhours.max_device_builder.03` - Max for Live Device Builder via `agents_sdk`
  Tools: `read_inventory`, `propose_session_change`, `automate_daw_session`. Approval gates: `live_set_mutation`.
- `possum-kingdom-afterhours.arrangement_producer.04` - Arrangement Producer via `responses_api`
  Tools: `render_worker_brief`, `propose_session_change`. Approval gates: `live_set_mutation`, `private_audio_upload`.
- `possum-kingdom-afterhours.mix_engineer.05` - Masterclass Audio Technician via `agents_sdk`
  Tools: `read_inventory`, `automate_daw_session`, `render_release_checklist`. Approval gates: `private_audio_upload`, `live_set_mutation`, `export_or_release`.
- `possum-kingdom-afterhours.release_qa.06` - Release and Provenance QA via `responses_api`
  Tools: `validate_source_rights`, `read_inventory`, `render_release_checklist`. Approval gates: `source_download`, `vendor_account_action`, `purchase_or_license_change`, `export_or_release`.

### The Ballad of the Broken Controller

- Track slug: `the-ballad-of-the-broken-controller`
- Tempo/key: `100 BPM`, `B flat major with punk chromatic passing tones`
- Source deck state: `muted_until_human_provenance_review`
- Planned DAW actions: `18`
- DAW request: `output/daw-mutations/the-ballad-of-the-broken-controller/mutation-request.json`

- `the-ballad-of-the-broken-controller.archivist.01` - Music Library Scientist via `responses_api`
  Tools: `validate_source_rights`, `render_worker_brief`. Approval gates: `source_download`.
- `the-ballad-of-the-broken-controller.controller_engineer.02` - AeroBand Banjo Controller Engineer via `agents_sdk`
  Tools: `read_inventory`, `propose_session_change`, `automate_daw_session`. Approval gates: `live_set_mutation`.
- `the-ballad-of-the-broken-controller.max_device_builder.03` - Max for Live Device Builder via `agents_sdk`
  Tools: `read_inventory`, `propose_session_change`, `automate_daw_session`. Approval gates: `live_set_mutation`.
- `the-ballad-of-the-broken-controller.arrangement_producer.04` - Arrangement Producer via `responses_api`
  Tools: `render_worker_brief`, `propose_session_change`. Approval gates: `live_set_mutation`, `private_audio_upload`.
- `the-ballad-of-the-broken-controller.mix_engineer.05` - Masterclass Audio Technician via `agents_sdk`
  Tools: `read_inventory`, `automate_daw_session`, `render_release_checklist`. Approval gates: `private_audio_upload`, `live_set_mutation`, `export_or_release`.
- `the-ballad-of-the-broken-controller.release_qa.06` - Release and Provenance QA via `responses_api`
  Tools: `validate_source_rights`, `read_inventory`, `render_release_checklist`. Approval gates: `source_download`, `vendor_account_action`, `purchase_or_license_change`, `export_or_release`.

### Rail Yard Ghost in the Control Room

- Track slug: `rail-yard-ghost-in-the-control-room`
- Tempo/key: `94 BPM`, `C dorian`
- Source deck state: `muted_until_human_provenance_review`
- Planned DAW actions: `21`
- DAW request: `output/daw-mutations/rail-yard-ghost-in-the-control-room/mutation-request.json`

- `rail-yard-ghost-in-the-control-room.archivist.01` - Music Library Scientist via `responses_api`
  Tools: `validate_source_rights`, `render_worker_brief`. Approval gates: `source_download`.
- `rail-yard-ghost-in-the-control-room.controller_engineer.02` - AeroBand Banjo Controller Engineer via `agents_sdk`
  Tools: `read_inventory`, `propose_session_change`, `automate_daw_session`. Approval gates: `live_set_mutation`.
- `rail-yard-ghost-in-the-control-room.max_device_builder.03` - Max for Live Device Builder via `agents_sdk`
  Tools: `read_inventory`, `propose_session_change`, `automate_daw_session`. Approval gates: `live_set_mutation`.
- `rail-yard-ghost-in-the-control-room.arrangement_producer.04` - Arrangement Producer via `responses_api`
  Tools: `render_worker_brief`, `propose_session_change`. Approval gates: `live_set_mutation`, `private_audio_upload`.
- `rail-yard-ghost-in-the-control-room.mix_engineer.05` - Masterclass Audio Technician via `agents_sdk`
  Tools: `read_inventory`, `automate_daw_session`, `render_release_checklist`. Approval gates: `private_audio_upload`, `live_set_mutation`, `export_or_release`.
- `rail-yard-ghost-in-the-control-room.release_qa.06` - Release and Provenance QA via `responses_api`
  Tools: `validate_source_rights`, `read_inventory`, `render_release_checklist`. Approval gates: `source_download`, `vendor_account_action`, `purchase_or_license_change`, `export_or_release`.
