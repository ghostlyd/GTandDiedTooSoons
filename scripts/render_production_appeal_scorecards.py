#!/usr/bin/env python3
"""Render production appeal scorecards without making psychological proof claims."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "automation" / "generated" / "production-appeal-scorecards.json"
DEFAULT_MARKDOWN_OUTPUT = ROOT / "docs" / "production-appeal-scorecards.md"
STABLE_GENERATED_AT = "1970-01-01T00:00:00Z"

SOURCE_FILES = [
    "compositions/down-tempo-punk-bluegrass-set.json",
    "compositions/generated/live12-track-build-plans.json",
    "automation/generated/max-for-live-device-contracts.json",
    "automation/generated/live12-daw-action-plan.json",
    "automation/generated/public-domain-source-deck.json",
]

DIMENSION_ORDER = [
    "entrainment",
    "hook_repetition",
    "call_response",
    "spectral_contrast",
    "spatial_motion",
    "dynamic_surprise",
    "tactile_performance_risk",
    "provenance_resonance",
]

DIMENSION_LABELS = {
    "entrainment": "Tempo, pulse, and motor-lock potential",
    "hook_repetition": "Recognizable hook recurrence",
    "call_response": "Human call-response contour",
    "spectral_contrast": "Contrast between acoustic core and alien electronics",
    "spatial_motion": "Width, azimuth, depth, and freeze movement",
    "dynamic_surprise": "Breaks, stops, fills, and expectation resets",
    "tactile_performance_risk": "Audible live-controller and one-take risk",
    "provenance_resonance": "Historically grounded source-deck resonance",
}


def read_json(relative_path: str) -> dict[str, Any]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slug_from_title(title: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "-" for character in title)
    return "-".join(part for part in slug.split("-") if part)


def lookup_by(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {item[key]: item for item in items if item.get(key)}


def ordered_unique(values: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def text_pool(*values: Any) -> str:
    chunks: list[str] = []
    for value in values:
        if isinstance(value, str):
            chunks.append(value)
        elif isinstance(value, list):
            chunks.extend(text_pool(item) for item in value)
        elif isinstance(value, dict):
            chunks.extend(text_pool(item) for item in value.values())
    return " ".join(chunks).lower()


def focus_devices(track_plan: dict[str, Any]) -> list[str]:
    return [
        focus if focus.startswith("m4l.") else f"m4l.{focus}"
        for focus in track_plan.get("max_for_live_focus", [])
    ]


def automation_targets(track_plan: dict[str, Any]) -> list[str]:
    return ordered_unique(
        [
            target
            for layer in track_plan.get("layers", [])
            for target in layer.get("automation_targets", [])
        ]
    )


def score(value: int) -> int:
    return max(1, min(5, value))


def dimension(
    dimension_id: str,
    dimension_score: int,
    production_evidence: list[str],
    daw_levers: list[str],
    measurement_prompt: str,
) -> dict[str, Any]:
    return {
        "id": dimension_id,
        "label": DIMENSION_LABELS[dimension_id],
        "score": score(dimension_score),
        "production_evidence": production_evidence,
        "daw_levers": ordered_unique(daw_levers),
        "measurement_prompt": measurement_prompt,
    }


def build_dimensions(
    composition_track: dict[str, Any],
    track_plan: dict[str, Any],
    source_assignment: dict[str, Any],
) -> list[dict[str, Any]]:
    pool = text_pool(composition_track, track_plan)
    devices = focus_devices(track_plan)
    targets = automation_targets(track_plan)
    scenes = track_plan.get("scenes", [])
    traditional_layer_count = sum(1 for layer in track_plan.get("layers", []) if layer.get("traditional_bluegrass_layer"))
    alien_layer_count = sum(1 for layer in track_plan.get("layers", []) if layer.get("alien_electronic_layer"))
    source_candidate_count = source_assignment.get("candidate_source_count", 0)

    has_house_grid = "m4l.house_grid_conductor" in devices or "four-on-floor" in pool or "kick" in pool
    has_call_response = "m4l.call_response_router" in devices or "call-response" in pool or "answer" in pool
    has_spatial = "m4l.spatial_harmonic_field" in devices or "send_spatial" in targets or "spatial" in pool
    has_risk = "one-take" in pool or "controller" in pool or "failure" in pool or "unquantized" in pool
    has_surprise = any(token in pool for token in ["break", "stop", "fill", "abrupt", "short loud", "no glossy"])

    return [
        dimension(
            "entrainment",
            3 + int(82 <= track_plan.get("tempo_bpm", 0) <= 104) + int(has_house_grid),
            [
                f"Tempo is {track_plan.get('tempo_bpm')} BPM.",
                "Deep-house pulse or kick language is present." if has_house_grid else "Pulse must be verified during local Live staging.",
            ],
            ["m4l.house_grid_conductor", "sidechain_depth", "accent", "swing_amount"],
            "After staging, rate whether the pulse invites head-nod/body-lock within the first 30 seconds without masking the banjo lead.",
        ),
        dimension(
            "hook_repetition",
            2 + int(len(scenes) >= 5) + int("hook" in pool) + int("roll" in pool),
            [
                f"Arrangement has {len(scenes)} generated scenes.",
                "Hook, roll, or refrain language appears in the track brief." if any(token in pool for token in ["hook", "roll", "refrain"]) else "Hook recurrence needs operator confirmation.",
            ],
            ["m4l.roll_probability_engine", "roll_density", "ghost_note_probability", "fill_probability"],
            "Mark the first timestamp where the core motif is recognized, then note whether it returns with meaningful variation.",
        ),
        dimension(
            "call_response",
            2 + int(has_call_response) + int("fiddle" in pool) + int("banjo" in pool),
            [
                "Call-response routing or answer phrases are declared." if has_call_response else "Call-response is not explicit in the source brief.",
                "Banjo/fiddle language supports human conversational contour." if "fiddle" in pool and "banjo" in pool else "Traditional response layers need local verification.",
            ],
            ["m4l.call_response_router", "send_spatial", "vibrato_depth", "room_send"],
            "During a rough playback, log whether response phrases feel conversational rather than stacked or ornamental.",
        ),
        dimension(
            "spectral_contrast",
            1 + min(2, traditional_layer_count // 3) + min(2, alien_layer_count // 2),
            [
                f"Traditional layer count: {traditional_layer_count}.",
                f"Alien/electronic layer count: {alien_layer_count}.",
            ],
            ["m4l.spatial_harmonic_field", "grain_density", "freeze", "spectral_tilt", "filter_cutoff"],
            "Compare acoustic-core audibility against alien texture density; note any section where identity collapses into generic wash.",
        ),
        dimension(
            "spatial_motion",
            2 + int(has_spatial) + int("wide" in pool or "dub" in pool) + int("fade" in pool or "bloom" in pool),
            [
                "Spatial harmonic field or spatial send targets are present." if has_spatial else "Spatial motion levers are not explicit.",
                "Brief references width, dub, fade, bloom, or spatial movement." if any(token in pool for token in ["wide", "dub", "fade", "bloom", "spatial"]) else "Spatial motion needs arrangement annotation.",
            ],
            ["m4l.spatial_harmonic_field", "azimuth", "width", "send_spatial", "grain_density", "freeze"],
            "On headphones and speakers, rate whether spatial movement supports form without pulling the lead instrument out of focus.",
        ),
        dimension(
            "dynamic_surprise",
            2 + int(has_surprise) + int("punk" in pool) + int("m4l.fill_trigger" in devices),
            [
                "Break, stop, fill, or anti-polish language is present." if has_surprise else "Surprise events need local arrangement confirmation.",
                "Punk constraint language appears in the source brief." if "punk" in pool else "Punk contrast needs operator confirmation.",
            ],
            ["m4l.fill_trigger", "parallel_drive", "fill_probability", "chop_gate"],
            "Log whether a break, stop, or fill changes attention without feeling like a random edit.",
        ),
        dimension(
            "tactile_performance_risk",
            2 + int(has_risk) + int("aeroband" in pool) + int("humanize_ms" in targets),
            [
                "AeroBand/controller/live-risk language is present." if has_risk or "aeroband" in pool else "Live controller risk is not explicit.",
                "Humanization or velocity articulation targets are available." if "humanize_ms" in targets or "velocity_curve" in targets else "Controller feel must be checked in Live.",
            ],
            ["m4l.aeroband_banjo_mapper", "velocity_curve", "humanize_ms", "pluck_decay", "downstroke_bias"],
            "During controller rehearsal, note whether imperfections read as human urgency rather than technical failure.",
        ),
        dimension(
            "provenance_resonance",
            2 + int(source_candidate_count > 0) + int(source_assignment.get("deck_state") == "muted_until_human_provenance_review") + int("source" in pool),
            [
                f"Approved source candidate count: {source_candidate_count}.",
                f"Source deck state: {source_assignment.get('deck_state')}.",
            ],
            ["m4l.provenance_sampler", "source_deck_gain", "slice_gate", "credit_review"],
            "Before any unmute, verify whether source use has audible purpose, credit clarity, and rights evidence.",
        ),
    ]


def track_scorecard(
    composition_track: dict[str, Any],
    track_plan: dict[str, Any],
    action_track: dict[str, Any],
    source_assignment: dict[str, Any],
    max_contracts_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    dimensions = build_dimensions(composition_track, track_plan, source_assignment)
    devices = focus_devices(track_plan)
    max_levers = [
        {
            "device_id": device_id,
            "display_name": max_contracts_by_id.get(device_id, {}).get("display_name", device_id),
            "macro_controls": max_contracts_by_id.get(device_id, {}).get("macro_controls", []),
        }
        for device_id in devices
    ]
    approval_gates = ordered_unique([*action_track.get("approval_gates_required", []), "export_or_release"])
    return {
        "track_slug": track_plan["slug"],
        "track_title": track_plan["title"],
        "tempo_bpm": track_plan.get("tempo_bpm"),
        "key_center": track_plan.get("key_center"),
        "duration_target": track_plan.get("duration_target"),
        "claim_status": "hypothesis_not_validated",
        "approval_gates": approval_gates,
        "max_for_live_levers": max_levers,
        "overall_hypothesis_score": round(sum(item["score"] for item in dimensions) / len(dimensions), 2),
        "dimensions": dimensions,
        "study_gate": {
            "requires_listener_protocol": True,
            "minimum_evidence_before_strong_claim": [
                "approved study protocol",
                "consent model",
                "defined listener sample and inclusion criteria",
                "pre/post listening measures or repeated-rating instrument",
                "analysis plan",
                "results linked to release notes",
            ],
        },
    }


def render(stable: bool = False) -> dict[str, Any]:
    compositions = read_json("compositions/down-tempo-punk-bluegrass-set.json")
    build_plans = read_json("compositions/generated/live12-track-build-plans.json")
    max_contracts = read_json("automation/generated/max-for-live-device-contracts.json")
    daw_action_plan = read_json("automation/generated/live12-daw-action-plan.json")
    source_deck = read_json("automation/generated/public-domain-source-deck.json")

    composition_by_slug = {
        slug_from_title(track["title"]): track
        for track in compositions.get("tracks", [])
        if track.get("title")
    }
    action_by_slug = lookup_by(daw_action_plan.get("tracks", []), "slug")
    source_by_slug = lookup_by(source_deck.get("track_assignments", []), "track_slug")
    max_contracts_by_id = lookup_by(max_contracts.get("devices", []), "id")
    scorecards = [
        track_scorecard(
            composition_by_slug[track_plan["slug"]],
            track_plan,
            action_by_slug.get(track_plan["slug"], {}),
            source_by_slug.get(track_plan["slug"], {}),
            max_contracts_by_id,
        )
        for track_plan in build_plans.get("tracks", [])
    ]
    return {
        "schema_version": 1,
        "generated_at": STABLE_GENERATED_AT if stable else utc_now(),
        "generator": "scripts/render_production_appeal_scorecards.py",
        "source_files": SOURCE_FILES,
        "source_file_sha256": {relative_path: sha256_file(ROOT / relative_path) for relative_path in SOURCE_FILES},
        "purpose": "Evidence-readiness scorecards for production decisions that may support listener appeal hypotheses without claiming proof.",
        "claims_policy": {
            "claim_status": "hypotheses_not_proof",
            "strong_claims_allowed": False,
            "allowed_language": [
                "evidence-informed production hypothesis",
                "listening-test candidate",
                "requires validation before psychological claims",
            ],
            "blocked_language": [
                "scientifically proven to affect the human psyche",
                "guaranteed listener response",
                "therapeutic or medical effect",
            ],
            "required_before_strong_claim": [
                "approved study protocol",
                "consent model",
                "data handling plan",
                "listener results",
                "analysis notes",
            ],
        },
        "dimension_order": DIMENSION_ORDER,
        "track_count": len(scorecards),
        "scorecards": scorecards,
    }


def render_markdown(data: dict[str, Any]) -> str:
    lines = [
        "# Production Appeal Scorecards",
        "",
        "Hypotheses, not proof.",
        "",
        "Do not claim scientifically proven psychological effects from these tracks unless an approved study protocol, consent model, data handling plan, listener results, and analysis notes exist in the release evidence.",
        "",
        "## Scorecards",
        "",
    ]
    for card in data["scorecards"]:
        lines.extend(
            [
                f"### {card['track_title']}",
                "",
                f"- Track slug: `{card['track_slug']}`",
                f"- Claim status: `{card['claim_status']}`",
                f"- Overall hypothesis score: `{card['overall_hypothesis_score']}`",
                f"- Study gate: `requires_listener_protocol={str(card['study_gate']['requires_listener_protocol']).lower()}`",
                "",
                "| Dimension | Score | Measurement prompt |",
                "| --- | ---: | --- |",
            ]
        )
        for dimension_item in card["dimensions"]:
            lines.append(
                f"| `{dimension_item['id']}` | {dimension_item['score']} | {dimension_item['measurement_prompt']} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON path.")
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT, help="Output Markdown path.")
    parser.add_argument("--stable", action="store_true", help="Use deterministic generated_at value.")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing outputs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = render(stable=args.stable)
    markdown = render_markdown(data)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "schema_version": data["schema_version"],
                    "claim_status": data["claims_policy"]["claim_status"],
                    "track_count": data["track_count"],
                    "generated_at": data["generated_at"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    output = args.output if args.output.is_absolute() else ROOT / args.output
    markdown_output = args.markdown_output if args.markdown_output.is_absolute() else ROOT / args.markdown_output
    write_json(output, data)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(markdown, encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Wrote {markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
