# Live 12 DAW Mutation Queue Runbook

Generated operator handoff for local-only Ableton Live 12 / Max for Live DAW mutation queues.

Status: `queued_not_launched`.

Do not commit Ableton sets, Max devices, rendered audio, raw source audio, credentials, cookies, or license files.

## Queue Preparation

```bash
python3 scripts/prepare_live12_daw_mutation_queue.py --stable
```

Queue manifest: `output/daw-mutation-queue/queue-manifest.json`

## Track Commands

### Good Vibrations in a Burned Barn

- Track slug: `good-vibrations-in-a-burned-barn`
- Planned action count: `19`
- Request: `output/daw-mutations/good-vibrations-in-a-burned-barn/mutation-request.json`
- Bundle manifest: `output/daw-import-bundles/good-vibrations-in-a-burned-barn/bundle-manifest.json`
- Launch plan: `output/daw-import-bundles/good-vibrations-in-a-burned-barn/launch-plan.json`
- Max for Live devices: `m4l.aeroband_banjo_mapper`, `m4l.roll_probability_engine`, `m4l.call_response_router`, `m4l.chop_clock_guard`, `m4l.slide_phrase_sampler`, `m4l.root_motion_limiter`, `m4l.fill_trigger`, `m4l.house_grid_conductor`, `m4l.provenance_sampler`, `m4l.spatial_harmonic_field`

Stage bundle:

```bash
python3 scripts/stage_live12_daw_import_bundle.py --request output/daw-mutations/good-vibrations-in-a-burned-barn/mutation-request.json --stable
```

Gated Ableton launch:

```bash
python3 scripts/stage_live12_daw_import_bundle.py --request output/daw-mutations/good-vibrations-in-a-burned-barn/mutation-request.json --launch-ableton --confirm-live-mutation --operator-approval-reference <approval-ref> --rollback-copy-reference <rollback-copy-ref>
```

Record receipt:

```bash
python3 scripts/record_live12_daw_mutation_receipt.py --request output/daw-import-bundles/good-vibrations-in-a-burned-barn/mutation-request.json --evidence output/daw-mutations/good-vibrations-in-a-burned-barn/operator-evidence.json --output output/daw-import-bundles/good-vibrations-in-a-burned-barn/applied-receipt.json
```

### A.P. Carter in the Warehouse

- Track slug: `a-p-carter-in-the-warehouse`
- Planned action count: `18`
- Request: `output/daw-mutations/a-p-carter-in-the-warehouse/mutation-request.json`
- Bundle manifest: `output/daw-import-bundles/a-p-carter-in-the-warehouse/bundle-manifest.json`
- Launch plan: `output/daw-import-bundles/a-p-carter-in-the-warehouse/launch-plan.json`
- Max for Live devices: `m4l.aeroband_banjo_mapper`, `m4l.roll_probability_engine`, `m4l.call_response_router`, `m4l.chop_clock_guard`, `m4l.slide_phrase_sampler`, `m4l.root_motion_limiter`, `m4l.fill_trigger`, `m4l.house_grid_conductor`, `m4l.provenance_sampler`, `m4l.spatial_harmonic_field`

Stage bundle:

```bash
python3 scripts/stage_live12_daw_import_bundle.py --request output/daw-mutations/a-p-carter-in-the-warehouse/mutation-request.json --stable
```

Gated Ableton launch:

```bash
python3 scripts/stage_live12_daw_import_bundle.py --request output/daw-mutations/a-p-carter-in-the-warehouse/mutation-request.json --launch-ableton --confirm-live-mutation --operator-approval-reference <approval-ref> --rollback-copy-reference <rollback-copy-ref>
```

Record receipt:

```bash
python3 scripts/record_live12_daw_mutation_receipt.py --request output/daw-import-bundles/a-p-carter-in-the-warehouse/mutation-request.json --evidence output/daw-mutations/a-p-carter-in-the-warehouse/operator-evidence.json --output output/daw-import-bundles/a-p-carter-in-the-warehouse/applied-receipt.json
```

### No Gods, No Masters, No Quantize

- Track slug: `no-gods-no-masters-no-quantize`
- Planned action count: `18`
- Request: `output/daw-mutations/no-gods-no-masters-no-quantize/mutation-request.json`
- Bundle manifest: `output/daw-import-bundles/no-gods-no-masters-no-quantize/bundle-manifest.json`
- Launch plan: `output/daw-import-bundles/no-gods-no-masters-no-quantize/launch-plan.json`
- Max for Live devices: `m4l.aeroband_banjo_mapper`, `m4l.roll_probability_engine`, `m4l.call_response_router`, `m4l.chop_clock_guard`, `m4l.slide_phrase_sampler`, `m4l.root_motion_limiter`, `m4l.fill_trigger`, `m4l.house_grid_conductor`, `m4l.provenance_sampler`, `m4l.spatial_harmonic_field`

Stage bundle:

```bash
python3 scripts/stage_live12_daw_import_bundle.py --request output/daw-mutations/no-gods-no-masters-no-quantize/mutation-request.json --stable
```

Gated Ableton launch:

```bash
python3 scripts/stage_live12_daw_import_bundle.py --request output/daw-mutations/no-gods-no-masters-no-quantize/mutation-request.json --launch-ableton --confirm-live-mutation --operator-approval-reference <approval-ref> --rollback-copy-reference <rollback-copy-ref>
```

Record receipt:

```bash
python3 scripts/record_live12_daw_mutation_receipt.py --request output/daw-import-bundles/no-gods-no-masters-no-quantize/mutation-request.json --evidence output/daw-mutations/no-gods-no-masters-no-quantize/operator-evidence.json --output output/daw-import-bundles/no-gods-no-masters-no-quantize/applied-receipt.json
```

### Possum Kingdom Afterhours

- Track slug: `possum-kingdom-afterhours`
- Planned action count: `18`
- Request: `output/daw-mutations/possum-kingdom-afterhours/mutation-request.json`
- Bundle manifest: `output/daw-import-bundles/possum-kingdom-afterhours/bundle-manifest.json`
- Launch plan: `output/daw-import-bundles/possum-kingdom-afterhours/launch-plan.json`
- Max for Live devices: `m4l.aeroband_banjo_mapper`, `m4l.roll_probability_engine`, `m4l.call_response_router`, `m4l.chop_clock_guard`, `m4l.slide_phrase_sampler`, `m4l.root_motion_limiter`, `m4l.fill_trigger`, `m4l.house_grid_conductor`, `m4l.provenance_sampler`, `m4l.spatial_harmonic_field`

Stage bundle:

```bash
python3 scripts/stage_live12_daw_import_bundle.py --request output/daw-mutations/possum-kingdom-afterhours/mutation-request.json --stable
```

Gated Ableton launch:

```bash
python3 scripts/stage_live12_daw_import_bundle.py --request output/daw-mutations/possum-kingdom-afterhours/mutation-request.json --launch-ableton --confirm-live-mutation --operator-approval-reference <approval-ref> --rollback-copy-reference <rollback-copy-ref>
```

Record receipt:

```bash
python3 scripts/record_live12_daw_mutation_receipt.py --request output/daw-import-bundles/possum-kingdom-afterhours/mutation-request.json --evidence output/daw-mutations/possum-kingdom-afterhours/operator-evidence.json --output output/daw-import-bundles/possum-kingdom-afterhours/applied-receipt.json
```

### The Ballad of the Broken Controller

- Track slug: `the-ballad-of-the-broken-controller`
- Planned action count: `18`
- Request: `output/daw-mutations/the-ballad-of-the-broken-controller/mutation-request.json`
- Bundle manifest: `output/daw-import-bundles/the-ballad-of-the-broken-controller/bundle-manifest.json`
- Launch plan: `output/daw-import-bundles/the-ballad-of-the-broken-controller/launch-plan.json`
- Max for Live devices: `m4l.aeroband_banjo_mapper`, `m4l.roll_probability_engine`, `m4l.call_response_router`, `m4l.chop_clock_guard`, `m4l.slide_phrase_sampler`, `m4l.root_motion_limiter`, `m4l.fill_trigger`, `m4l.house_grid_conductor`, `m4l.provenance_sampler`, `m4l.spatial_harmonic_field`

Stage bundle:

```bash
python3 scripts/stage_live12_daw_import_bundle.py --request output/daw-mutations/the-ballad-of-the-broken-controller/mutation-request.json --stable
```

Gated Ableton launch:

```bash
python3 scripts/stage_live12_daw_import_bundle.py --request output/daw-mutations/the-ballad-of-the-broken-controller/mutation-request.json --launch-ableton --confirm-live-mutation --operator-approval-reference <approval-ref> --rollback-copy-reference <rollback-copy-ref>
```

Record receipt:

```bash
python3 scripts/record_live12_daw_mutation_receipt.py --request output/daw-import-bundles/the-ballad-of-the-broken-controller/mutation-request.json --evidence output/daw-mutations/the-ballad-of-the-broken-controller/operator-evidence.json --output output/daw-import-bundles/the-ballad-of-the-broken-controller/applied-receipt.json
```

### Rail Yard Ghost in the Control Room

- Track slug: `rail-yard-ghost-in-the-control-room`
- Planned action count: `21`
- Request: `output/daw-mutations/rail-yard-ghost-in-the-control-room/mutation-request.json`
- Bundle manifest: `output/daw-import-bundles/rail-yard-ghost-in-the-control-room/bundle-manifest.json`
- Launch plan: `output/daw-import-bundles/rail-yard-ghost-in-the-control-room/launch-plan.json`
- Max for Live devices: `m4l.aeroband_banjo_mapper`, `m4l.roll_probability_engine`, `m4l.call_response_router`, `m4l.chop_clock_guard`, `m4l.slide_phrase_sampler`, `m4l.root_motion_limiter`, `m4l.fill_trigger`, `m4l.house_grid_conductor`, `m4l.provenance_sampler`, `m4l.spatial_harmonic_field`

Stage bundle:

```bash
python3 scripts/stage_live12_daw_import_bundle.py --request output/daw-mutations/rail-yard-ghost-in-the-control-room/mutation-request.json --stable
```

Gated Ableton launch:

```bash
python3 scripts/stage_live12_daw_import_bundle.py --request output/daw-mutations/rail-yard-ghost-in-the-control-room/mutation-request.json --launch-ableton --confirm-live-mutation --operator-approval-reference <approval-ref> --rollback-copy-reference <rollback-copy-ref>
```

Record receipt:

```bash
python3 scripts/record_live12_daw_mutation_receipt.py --request output/daw-import-bundles/rail-yard-ghost-in-the-control-room/mutation-request.json --evidence output/daw-mutations/rail-yard-ghost-in-the-control-room/operator-evidence.json --output output/daw-import-bundles/rail-yard-ghost-in-the-control-room/applied-receipt.json
```
