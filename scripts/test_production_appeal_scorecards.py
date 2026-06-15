#!/usr/bin/env python3
"""Regression probes for generated production appeal scorecards."""

from __future__ import annotations

import difflib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
COMMITTED_JSON = ROOT / "automation" / "generated" / "production-appeal-scorecards.json"
COMMITTED_MARKDOWN = ROOT / "docs" / "production-appeal-scorecards.md"
EXPECTED_SOURCE_FILES = [
    "compositions/down-tempo-punk-bluegrass-set.json",
    "compositions/generated/live12-track-build-plans.json",
    "automation/generated/max-for-live-device-contracts.json",
    "automation/generated/live12-daw-action-plan.json",
    "automation/generated/public-domain-source-deck.json",
]
REQUIRED_DIMENSIONS = [
    "entrainment",
    "hook_repetition",
    "call_response",
    "spectral_contrast",
    "spatial_motion",
    "dynamic_surprise",
    "tactile_performance_risk",
    "provenance_resonance",
]
BLOCKED_BINARY_EXTENSIONS = (".als", ".amxd", ".alp", ".wav", ".aiff", ".flac", ".mp3", ".m4a", ".ogg")


def run_command(args: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=False, capture_output=True, text=True)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def diff_text(expected_path: Path, actual_path: Path) -> str:
    expected = expected_path.read_text(encoding="utf-8").splitlines(keepends=True)
    actual = actual_path.read_text(encoding="utf-8").splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            expected,
            actual,
            fromfile=str(expected_path.relative_to(ROOT)),
            tofile=str(actual_path),
        )
    )


def iter_string_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            values.extend(iter_string_values(item))
        return values
    if isinstance(value, dict):
        values = []
        for item in value.values():
            values.extend(iter_string_values(item))
        return values
    return []


def assert_no_sensitive_paths(data: object, label: str) -> None:
    for value in iter_string_values(data):
        if "/Users/" in value:
            raise AssertionError(f"{label} leaked an absolute user path: {value}")
        if "sources/public-domain/raw/" in value:
            raise AssertionError(f"{label} leaked a raw public-domain source path: {value}")
        if "/" in value and value.endswith(BLOCKED_BINARY_EXTENSIONS):
            raise AssertionError(f"{label} carried a blocked binary/audio artifact path: {value}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="production-appeal-scorecards-test-") as temp_dir:
        temp_root = Path(temp_dir)
        generated_json = temp_root / "production-appeal-scorecards.json"
        generated_markdown = temp_root / "production-appeal-scorecards.md"
        render_result = run_command(
            [
                PYTHON,
                "scripts/render_production_appeal_scorecards.py",
                "--stable",
                "--output",
                str(generated_json),
                "--markdown-output",
                str(generated_markdown),
            ]
        )
        if render_result.returncode != 0:
            print(render_result.stdout, file=sys.stderr)
            print(render_result.stderr, file=sys.stderr)
            return render_result.returncode

        scorecards = load_json(generated_json)
        build_plans = load_json(ROOT / "compositions" / "generated" / "live12-track-build-plans.json")
        track_slugs = [track["slug"] for track in build_plans["tracks"]]

        if generated_json.read_text(encoding="utf-8") != COMMITTED_JSON.read_text(encoding="utf-8"):
            print(diff_text(COMMITTED_JSON, generated_json), file=sys.stderr)
            return 1
        if generated_markdown.read_text(encoding="utf-8") != COMMITTED_MARKDOWN.read_text(encoding="utf-8"):
            print(diff_text(COMMITTED_MARKDOWN, generated_markdown), file=sys.stderr)
            return 1

        if scorecards.get("schema_version") != 1:
            print("Production appeal scorecards must use schema_version 1.", file=sys.stderr)
            return 1
        if scorecards.get("source_files") != EXPECTED_SOURCE_FILES:
            print("Production appeal scorecards source files changed unexpectedly.", file=sys.stderr)
            return 1
        claims_policy = scorecards.get("claims_policy", {})
        if claims_policy.get("claim_status") != "hypotheses_not_proof":
            print("Production appeal scorecards must not claim proof.", file=sys.stderr)
            return 1
        if claims_policy.get("strong_claims_allowed") is not False:
            print("Production appeal scorecards must block strong psychological claims.", file=sys.stderr)
            return 1
        if "approved study protocol" not in " ".join(claims_policy.get("required_before_strong_claim", [])):
            print("Production appeal scorecards must require an approved study protocol.", file=sys.stderr)
            return 1

        cards = scorecards.get("scorecards", [])
        if scorecards.get("track_count") != len(track_slugs) or [card.get("track_slug") for card in cards] != track_slugs:
            print("Production appeal scorecards must mirror generated track order.", file=sys.stderr)
            return 1
        for card in cards:
            dimension_ids = [dimension.get("id") for dimension in card.get("dimensions", [])]
            if dimension_ids != REQUIRED_DIMENSIONS:
                print(f"Production appeal dimensions are stale: {card.get('track_slug')}", file=sys.stderr)
                return 1
            if not card.get("max_for_live_levers"):
                print(f"Scorecard must include Max for Live levers: {card.get('track_slug')}", file=sys.stderr)
                return 1
            if card.get("claim_status") != "hypothesis_not_validated":
                print(f"Track scorecard must remain hypothesis_not_validated: {card.get('track_slug')}", file=sys.stderr)
                return 1
            if card.get("study_gate", {}).get("requires_listener_protocol") is not True:
                print(f"Track scorecard must require listener protocol: {card.get('track_slug')}", file=sys.stderr)
                return 1
            if "export_or_release" not in card.get("approval_gates", []):
                print(f"Track scorecard must include export_or_release gate: {card.get('track_slug')}", file=sys.stderr)
                return 1
            for dimension in card["dimensions"]:
                if dimension.get("score") not in {1, 2, 3, 4, 5}:
                    print(f"Dimension score out of range: {card.get('track_slug')} {dimension.get('id')}", file=sys.stderr)
                    return 1
                for field in ["production_evidence", "daw_levers", "measurement_prompt"]:
                    if not dimension.get(field):
                        print(f"Dimension missing {field}: {card.get('track_slug')} {dimension.get('id')}", file=sys.stderr)
                        return 1

        markdown = generated_markdown.read_text(encoding="utf-8")
        for required_text in [
            "# Production Appeal Scorecards",
            "Hypotheses, not proof.",
            "Do not claim scientifically proven psychological effects",
            "Rail Yard Ghost in the Control Room",
            "spatial_motion",
            "approved study protocol",
        ]:
            if required_text not in markdown:
                print(f"Production appeal scorecard markdown missing: {required_text}", file=sys.stderr)
                return 1

        assert_no_sensitive_paths(scorecards, "production appeal scorecards")
        assert_no_sensitive_paths({"markdown": markdown}, "production appeal scorecards markdown")

    print("Production appeal scorecard probes passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
