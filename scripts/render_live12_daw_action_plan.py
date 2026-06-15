#!/usr/bin/env python3
"""Render a deterministic Ableton Live 12 / Max for Live action plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "automation" / "generated" / "live12-daw-action-plan.json"
STABLE_GENERATED_AT = "1970-01-01T00:00:00Z"

SOURCE_FILES = [
    "automation/openai-production-orchestration.json",
    "automation/live12-session-template.json",
    "compositions/down-tempo-punk-bluegrass-set.json",
    "compositions/generated/live12-track-build-plans.json",
    "catalogs/public-domain-bluegrass-sources.json",
    "sources/public-domain/download-ledger.json",
    "inventory/live12-local-inventory.json",
]

APPROVAL_GATE_ORDER = [
    "source_download",
    "private_audio_upload",
    "vendor_account_action",
    "purchase_or_license_change",
    "live_set_mutation",
    "export_or_release",
]
SOURCE_MATCH_STOP_WORDS = {
    "001",
    "ableton",
    "and",
    "audio",
    "citizen",
    "congress",
    "deck",
    "domain",
    "excerpt",
    "fetched",
    "for",
    "from",
    "jukebox",
    "loc",
    "local",
    "national",
    "none",
    "project",
    "public",
    "raw",
    "sampler",
    "source",
    "the",
    "use",
    "with",
}


def read_json(relative_path: str) -> dict[str, Any]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def approved_source_pool(catalog: dict[str, Any], ledger: dict[str, Any]) -> list[dict[str, Any]]:
    sources_by_id = {
        source.get("id"): source
        for source in catalog.get("sources", [])
        if source.get("id") and source.get("approved_for_download")
    }
    pool = []
    for record in ledger.get("downloads", []):
        source = sources_by_id.get(record.get("source_id"))
        if not source:
            continue
        pool.append(
            {
                "source_id": record.get("source_id"),
                "name": record.get("name"),
                "rights_status": record.get("rights_status"),
                "credit_line": record.get("credit_line"),
                "sha256": record.get("sha256"),
                "byte_size": record.get("byte_size"),
                "project_use": source.get("project_use"),
                "transformation": record.get("transformation"),
            }
        )
    return sorted(pool, key=lambda item: item["source_id"])


def match_tokens(*values: Any) -> set[str]:
    text = " ".join(str(value) for value in values if value)
    return {
        token
        for token in re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", text.lower())
        if len(token) > 2 and token not in SOURCE_MATCH_STOP_WORDS
    }


def track_source_match_score(
    track_plan: dict[str, Any],
    composition_track: dict[str, Any],
    source: dict[str, Any],
) -> tuple[int, str]:
    title_tokens = match_tokens(track_plan.get("title"))
    key_tokens = match_tokens(track_plan.get("key_center"))
    scene_tokens = match_tokens(
        *(
            f"{scene.get('name', '')} {scene.get('arrangement_note', '')}"
            for scene in track_plan.get("scenes", [])
        )
    )
    composition_tokens = match_tokens(
        *composition_track.get("bluegrass_core", []),
        *composition_track.get("electronic_dna", []),
        *composition_track.get("punk_spirit", []),
        *composition_track.get("max_for_live_focus", []),
    )
    source_tokens = match_tokens(
        source.get("source_id"),
        source.get("name"),
        source.get("project_use"),
        source.get("transformation"),
    )

    title_overlap = title_tokens & source_tokens
    key_overlap = key_tokens & source_tokens
    scene_overlap = scene_tokens & source_tokens
    composition_overlap = composition_tokens & source_tokens
    score = (
        10 * len(title_overlap)
        + 3 * len(key_overlap)
        + 2 * len(scene_overlap)
        + len(composition_overlap)
    )
    rationale_tokens = sorted(title_overlap | key_overlap | scene_overlap | composition_overlap)
    return score, ", ".join(rationale_tokens)


def source_candidates_for_track(
    track_plan: dict[str, Any],
    composition_track: dict[str, Any],
    source_pool: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not source_pool:
        return []

    ranked = []
    for source in source_pool:
        score, rationale = track_source_match_score(track_plan, composition_track, source)
        ranked.append((score, rationale, source))
    ranked.sort(key=lambda item: (-item[0], item[2]["source_id"]))
    return [source for _, _, source in ranked[:3]]


def approval_gates_from_actions(*action_groups: Any) -> list[str]:
    gates = set()
    for action_group in action_groups:
        if isinstance(action_group, dict):
            action_group = [action_group]
        for action in action_group:
            approval_gate = action.get("approval_gate")
            if approval_gate:
                gates.add(approval_gate)
    return [gate for gate in APPROVAL_GATE_ORDER if gate in gates]


def build_preflight_actions(track_plan: dict[str, Any]) -> list[dict[str, Any]]:
    slug = track_plan["slug"]
    return [
        {
            "id": f"{slug}.preflight.verify-midi-hash",
            "type": "verify_artifact",
            "input": track_plan["midi_file"],
            "expected_sha256": track_plan["midi_sha256"],
            "approval_gate": None,
        },
        {
            "id": f"{slug}.preflight.create-local-rollback-copy",
            "type": "operator_check",
            "instruction": "Before any Live-set mutation, save a timestamped local rollback copy outside Git.",
            "approval_gate": "live_set_mutation",
        },
        {
            "id": f"{slug}.preflight.confirm-no-private-audio-upload",
            "type": "operator_check",
            "instruction": "Do not upload private rehearsal audio, unreleased lyrics, or controller recordings without session-specific consent.",
            "approval_gate": "private_audio_upload",
        },
    ]


def build_scene_actions(track_plan: dict[str, Any]) -> list[dict[str, Any]]:
    slug = track_plan["slug"]
    actions = []
    for scene in track_plan.get("scenes", []):
        actions.append(
            {
                "id": f"{slug}.scene.{scene['index']:02d}",
                "type": "create_arrangement_locator",
                "scene_name": scene["name"],
                "bar_start": scene["bar_start"],
                "bar_length": scene["bar_length"],
                "arrangement_note": scene["arrangement_note"],
                "approval_gate": "live_set_mutation",
            }
        )
    return actions


def build_layer_actions(
    track_plan: dict[str, Any],
    session_tracks: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    slug = track_plan["slug"]
    actions = []
    for layer in track_plan.get("layers", []):
        session_track = session_tracks.get(layer["session_track"], {})
        actions.append(
            {
                "id": f"{slug}.layer.{layer['id']}",
                "type": "route_midi_layer_and_configure_devices",
                "midi_file": track_plan["midi_file"],
                "midi_track": layer["midi_track"],
                "midi_channels": layer["midi_channels"],
                "session_track": layer["session_track"],
                "session_role": session_track.get("role"),
                "instrument_strategy": session_track.get("instrument_strategy"),
                "gm_placeholder": layer["gm_sound"],
                "traditional_bluegrass_layer": layer["traditional_bluegrass_layer"],
                "alien_electronic_layer": layer["alien_electronic_layer"],
                "device_contracts": layer["device_contracts"],
                "automation_targets": layer["automation_targets"],
                "macro_initialization": [
                    {
                        "target": target,
                        "mode": "write_initial_clip_envelope_or_macro_default",
                    }
                    for target in layer.get("automation_targets", [])
                ],
                "approval_gate": "live_set_mutation",
            }
        )
    return actions


def build_track_plan(
    track_plan: dict[str, Any],
    composition_track: dict[str, Any],
    session_template: dict[str, Any],
    source_pool: list[dict[str, Any]],
) -> dict[str, Any]:
    session_tracks = {track["name"]: track for track in session_template.get("tracks", [])}
    source_candidates = source_candidates_for_track(track_plan, composition_track, source_pool)
    source_deck_track = session_tracks.get("Public Domain Source Deck", {})
    slug = track_plan["slug"]
    preflight_actions = build_preflight_actions(track_plan)
    session_actions = [
        {
            "id": f"{slug}.session.set-tempo-and-swing",
            "type": "set_session_tempo_and_groove",
            "tempo_bpm": track_plan["tempo_bpm"],
            "global_swing": session_template.get("global_swing"),
            "approval_gate": "live_set_mutation",
        },
        {
            "id": f"{slug}.session.import-midi",
            "type": "import_generated_midi",
            "midi_file": track_plan["midi_file"],
            "expected_sha256": track_plan["midi_sha256"],
            "approval_gate": "live_set_mutation",
        },
        {
            "id": f"{slug}.session.configure-returns",
            "type": "create_or_verify_return_tracks",
            "returns": session_template.get("returns", []),
            "approval_gate": "live_set_mutation",
        },
    ]
    scene_actions = build_scene_actions(track_plan)
    layer_actions = build_layer_actions(track_plan, session_tracks)
    source_deck = {
        "session_track": "Public Domain Source Deck",
        "session_role": source_deck_track.get("role"),
        "instrument_strategy": source_deck_track.get("instrument_strategy"),
        "device_contracts": source_deck_track.get("device_contracts", []),
        "automation_targets": source_deck_track.get("automation_targets", []),
        "macro_initialization": [
            {
                "target": target,
                "mode": "write_initial_clip_envelope_or_macro_default",
            }
            for target in source_deck_track.get("automation_targets", [])
        ],
        "default_state": "muted_until_human_provenance_review",
        "candidate_sources": source_candidates,
        "required_checks": [
            "source_id appears in sources/public-domain/download-ledger.json",
            "rights_status is public_domain, cc0, or cc_by",
            "credit line is carried into release notes",
            "no raw sample path is written into tracked repo artifacts",
        ],
        "approval_gate": "live_set_mutation",
    }
    mix_and_release_gates = [
        {
            "id": f"{slug}.mix.headroom-check",
            "type": "operator_check",
            "instruction": "Confirm pre-master headroom is at least -6 dBFS before any limiter.",
            "approval_gate": "export_or_release",
        },
        {
            "id": f"{slug}.release.provenance-check",
            "type": "operator_check",
            "instruction": "Confirm source credits, source ledger records, CI status, and local install receipts before export or release.",
            "approval_gate": "export_or_release",
        },
    ]

    return {
        "title": track_plan["title"],
        "slug": slug,
        "tempo_bpm": track_plan["tempo_bpm"],
        "key_center": track_plan["key_center"],
        "duration_target": track_plan["duration_target"],
        "midi_file": track_plan["midi_file"],
        "midi_sha256": track_plan["midi_sha256"],
        "approximate_bars": track_plan["approximate_bars"],
        "composition_mutation_blueprint": track_plan.get("composition_mutation_blueprint", {}),
        "approval_gates_required": approval_gates_from_actions(
            preflight_actions,
            session_actions,
            scene_actions,
            layer_actions,
            source_deck,
            mix_and_release_gates,
        ),
        "preflight_actions": preflight_actions,
        "session_actions": session_actions,
        "scene_actions": scene_actions,
        "layer_actions": layer_actions,
        "source_deck": source_deck,
        "mix_and_release_gates": mix_and_release_gates,
    }


def render(stable: bool = False) -> dict[str, Any]:
    orchestration = read_json("automation/openai-production-orchestration.json")
    session_template = read_json("automation/live12-session-template.json")
    compositions = read_json("compositions/down-tempo-punk-bluegrass-set.json")
    composition_plans = read_json("compositions/generated/live12-track-build-plans.json")
    source_catalog = read_json("catalogs/public-domain-bluegrass-sources.json")
    source_ledger = read_json("sources/public-domain/download-ledger.json")
    inventory = read_json("inventory/live12-local-inventory.json")
    source_pool = approved_source_pool(source_catalog, source_ledger)
    composition_tracks_by_title = {
        track.get("title"): track for track in compositions.get("tracks", [])
    }

    return {
        "schema_version": 1,
        "generated_at": STABLE_GENERATED_AT if stable else utc_now(),
        "generator": "scripts/render_live12_daw_action_plan.py",
        "source_files": SOURCE_FILES,
        "source_file_sha256": {relative_path: sha256_file(ROOT / relative_path) for relative_path in SOURCE_FILES},
        "purpose": "Reviewable proposal queue for building the generated downtempo punk-bluegrass suite in Ableton Live 12 with Max for Live.",
        "safety": {
            "proposal_only": True,
            "requires_human_approval_before": [
                "account-gated vendor action",
                "Live-set mutation",
                "Max for Live device mutation",
                "private audio upload",
                "export or release",
            ],
            "must_not": [
                "commit .als, .amxd, .alp, plugins, presets, samples, renders, credentials, cookies, or license files",
                "write raw public-domain sample paths into tracked generated artifacts",
                "use unapproved source audio in the Public Domain Source Deck",
                "claim scientific psyche effects without a reviewed study protocol and evidence",
            ],
        },
        "openai_tool_contract": {
            "id": "automate_daw_session",
            "approval_required": True,
            "source_contract": next(
                tool for tool in orchestration.get("tool_contracts", []) if tool.get("id") == "automate_daw_session"
            ),
        },
        "live_template": {
            "name": session_template.get("name"),
            "target_runtime": session_template.get("target_runtime"),
            "tempo_range_bpm": session_template.get("tempo_range_bpm"),
            "track_count": len(session_template.get("tracks", [])),
            "return_count": len(session_template.get("returns", [])),
            "master_bus_targets": session_template.get("master_bus", {}).get("targets", []),
        },
        "inventory_summary": {
            "ableton_live_version": inventory.get("ableton", {}).get("app", {}).get("version"),
            "factory_pack_count": len(inventory.get("ableton", {}).get("factory_packs", [])),
            "arturia_application_count": len(inventory.get("arturia", {}).get("applications", [])),
        },
        "composition_set": compositions.get("set_name"),
        "approved_source_pool": source_pool,
        "tracks": [
            build_track_plan(
                track_plan,
                composition_tracks_by_title.get(track_plan.get("title"), {}),
                session_template,
                source_pool,
            )
            for track_plan in composition_plans.get("tracks", [])
        ],
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
                    "track_count": len(data["tracks"]),
                    "approved_source_count": len(data["approved_source_pool"]),
                    "generated_at": data["generated_at"],
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
