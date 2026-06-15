# Generated Composition Sketches

This directory contains deterministic composition artifacts rendered from:

- `compositions/down-tempo-punk-bluegrass-set.json`
- `compositions/composition-mutation-blueprints.json`
- `automation/live12-session-template.json`

The `.mid` files are generated note/control sketches for Ableton Live import. The JSON build plan also carries per-track composition mutation blueprints: full bluegrass-role jobs, alien-electronic role jobs, punk constraints, source-deck approval state, and Max for Live mutation lanes.

These generated files do not contain sampled audio, Ableton Live Sets, Max for Live devices, Arturia presets, commercial pack content, private recordings, credentials, cookies, or license files.

The approval-gated Ableton/Max for Live action queue that consumes these sketches lives at `automation/generated/live12-daw-action-plan.json`.

Regenerate and verify with:

```bash
python3 scripts/render_composition_sketches.py --stable
python3 scripts/render_live12_daw_action_plan.py --stable
python3 scripts/validate_repo.py
```
