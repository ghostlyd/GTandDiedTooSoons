#!/usr/bin/env python3
"""Render a deterministic local Ableton Live 12 DAW mutation package."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "automation" / "generated" / "live12-daw-mutation-package.json"
STABLE_GENERATED_AT = "1970-01-01T00:00:00Z"

SOURCE_FILES = [
    "automation/generated/live12-daw-action-plan.json",
    "automation/live12-session-template.json",
    "compositions/generated/live12-track-build-plans.json",
]

EXECUTABLE_ACTION_GROUPS = [
    "session_actions",
    "scene_actions",
    "layer_actions",
]
BLOCKED_ACTION_GROUPS = ["mix_and_release_gates"]
EXECUTION_MODE = "local_preflight_then_human_approved_daw_mutation"
RECEIPT_ROOT = "output/daw-mutations"
REQUIRED_RECEIPT_FIELDS = [
    "run_id",
    "track_slug",
    "track_title",
    "execution_status",
    "operator_approval_reference",
    "rollback_copy_reference",
    "mutation_package_sha256",
    "plan_track_sha256",
    "midi_verification",
    "affected_tracks",
    "affected_returns",
    "applied_action_ids",
    "skipped_action_ids",
    "required_postflight_checks",
    "created_artifacts",
    "redactions",
]
REQUIRED_POSTFLIGHT_CHECKS = [
    "rollback copy exists outside Git before mutation",
    "generated MIDI hash matched before import",
    "affected tracks match mutation package scope",
    "Public Domain Source Deck remains muted until provenance review",
    "no export, render, .als, .amxd, sample, preset, credential, cookie, or license artifact is committed",
    "python3 scripts/validate_repo.py passes after metadata updates",
]
PROHIBITED_ARTIFACTS = [
    ".als",
    ".amxd",
    ".alp",
    "plugins",
    "presets",
    "samples",
    "renders",
    "credentials",
    "cookies",
    "license files",
    "private audio",
]


def read_json(relative_path: str) -> dict[str, Any]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def unique_ordered(values: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def action_ids(track: dict[str, Any], groups: list[str]) -> list[str]:
    return [
        action["id"]
        for group in groups
        for action in track.get(group, [])
        if action.get("id")
    ]


def build_job(track: dict[str, Any]) -> dict[str, Any]:
    slug = track["slug"]
    source_deck = track.get("source_deck", {})
    layer_tracks = [
        action.get("session_track")
        for action in track.get("layer_actions", [])
        if action.get("session_track")
    ]
    affected_tracks = unique_ordered(layer_tracks + [source_deck.get("session_track", "")])
    configure_return_actions = [
        action
        for action in track.get("session_actions", [])
        if action.get("type") == "create_or_verify_return_tracks"
    ]
    affected_returns = [
        item.get("name")
        for item in (configure_return_actions[0].get("returns", []) if configure_return_actions else [])
        if item.get("name")
    ]
    executable_action_ids = action_ids(track, EXECUTABLE_ACTION_GROUPS)
    source_deck_action_id = f"{slug}.source-deck.keep-muted-for-provenance-review"
    executable_action_ids.append(source_deck_action_id)

    return {
        "id": f"daw-mutation.{slug}",
        "track_slug": slug,
        "track_title": track["title"],
        "execution_mode": EXECUTION_MODE,
        "approval_gates_required": track.get("approval_gates_required", []),
        "approval_required_before_execution": [
            "live_set_mutation",
            "private_audio_upload",
        ],
        "blocked_action_groups": BLOCKED_ACTION_GROUPS,
        "executable_action_groups": EXECUTABLE_ACTION_GROUPS + ["source_deck"],
        "preflight_action_ids": action_ids(track, ["preflight_actions"]),
        "executable_action_ids": executable_action_ids,
        "mutation_action_count": len(executable_action_ids),
        "plan_track_sha256": sha256_json(track),
        "midi_artifact": {
            "path": track["midi_file"],
            "sha256": track["midi_sha256"],
            "verification_action_id": f"{slug}.preflight.verify-midi-hash",
        },
        "affected_tracks": affected_tracks,
        "affected_returns": affected_returns,
        "source_deck_policy": {
            "session_track": source_deck.get("session_track"),
            "default_state": "muted_until_human_provenance_review",
            "action_id": source_deck_action_id,
            "candidate_source_count": len(source_deck.get("candidate_sources", [])),
            "requires_provenance_review": True,
        },
        "rollback": {
            "required": True,
            "instruction": "Save a timestamped local rollback copy outside Git before applying any Ableton Live or Max for Live mutation.",
        },
        "local_output_policy": {
            "receipt_root": RECEIPT_ROOT,
            "git_policy": "ignored_local_only",
        },
    }


def render(stable: bool = False) -> dict[str, Any]:
    daw_plan = read_json("automation/generated/live12-daw-action-plan.json")
    session_template = read_json("automation/live12-session-template.json")
    build_plans = read_json("compositions/generated/live12-track-build-plans.json")
    return {
        "schema_version": 1,
        "generated_at": STABLE_GENERATED_AT if stable else utc_now(),
        "generator": "scripts/render_live12_daw_mutation_package.py",
        "source_files": SOURCE_FILES,
        "source_file_sha256": {relative_path: sha256_file(ROOT / relative_path) for relative_path in SOURCE_FILES},
        "purpose": "Local-only preflight package for applying reviewed Ableton Live 12 / Max for Live mutation jobs without committing DAW binaries or audio artifacts.",
        "safety": {
            "local_only": True,
            "requires_operator_approval_before_execution": [
                "Live-set mutation",
                "Max for Live device mutation",
                "private audio upload",
                "export or release",
            ],
            "must_not": [
                "commit .als, .amxd, .alp, plugins, presets, samples, renders, credentials, cookies, or license files",
                "mark a mutation applied before Ableton Live or Max for Live confirms the change",
                "load unapproved source audio into the Public Domain Source Deck",
                "export or publish from a mutation preflight run",
            ],
        },
        "receipt_contract": {
            "output_root": RECEIPT_ROOT,
            "git_policy": "ignored_local_only",
            "required_fields": REQUIRED_RECEIPT_FIELDS,
            "required_postflight_checks": REQUIRED_POSTFLIGHT_CHECKS,
            "prohibited_artifacts": PROHIBITED_ARTIFACTS,
        },
        "live_template": daw_plan.get("live_template", {}),
        "composition_set": daw_plan.get("composition_set"),
        "source_plan": {
            "path": "automation/generated/live12-daw-action-plan.json",
            "sha256": sha256_file(ROOT / "automation/generated/live12-daw-action-plan.json"),
            "track_count": len(daw_plan.get("tracks", [])),
            "build_plan_track_count": len(build_plans.get("tracks", [])),
            "session_track_count": len(session_template.get("tracks", [])),
        },
        "jobs": [build_job(track) for track in daw_plan.get("tracks", [])],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON path.")
    parser.add_argument("--stable", action="store_true", help="Use deterministic generated_at value.")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = render(stable=args.stable)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "schema_version": data["schema_version"],
                    "job_count": len(data["jobs"]),
                    "generated_at": data["generated_at"],
                    "receipt_root": data["receipt_contract"]["output_root"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        display_path = args.output.relative_to(ROOT)
    except ValueError:
        display_path = args.output
    print(f"Wrote {display_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
