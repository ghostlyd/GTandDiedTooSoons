#!/usr/bin/env python3
"""Regression probes for composition mutation blueprints."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
BLUEPRINTS = ROOT / "compositions" / "composition-mutation-blueprints.json"
COMMITTED_BUILD_PLANS = ROOT / "compositions" / "generated" / "live12-track-build-plans.json"
COMMITTED_README = ROOT / "compositions" / "generated" / "README.md"

EXPECTED_TRADITIONAL = {
    "aeroband_banjo_lead",
    "fiddle_hybrid_strings",
    "mandolin_chop",
    "dobro_metallic_slide",
    "acoustic_guitar_boom_chuck",
    "upright_bass_sub",
}
EXPECTED_ALIEN = {
    "deep_house_machines",
    "alien_sky",
    "public_domain_source_deck",
}
EXPECTED_PUNK = {
    "punk_kit",
    "performance_rule",
    "anti_polish_rule",
}
BLOCKED_BINARY_EXTENSIONS = (".als", ".amxd", ".alp", ".wav", ".aiff", ".flac", ".mp3", ".m4a", ".ogg")


def run_command(args: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=False, capture_output=True, text=True)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def assert_source_only(data: object, label: str) -> None:
    for value in iter_string_values(data):
        if "/Users/" in value:
            raise AssertionError(f"{label} leaked an absolute user path: {value}")
        if "sources/public-domain/raw/" in value:
            raise AssertionError(f"{label} leaked a raw public-domain source path: {value}")
        if "/" in value and value.endswith(BLOCKED_BINARY_EXTENSIONS):
            raise AssertionError(f"{label} carried a blocked binary/audio artifact path: {value}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="composition-blueprints-test-") as temp_dir:
        rendered_dir = Path(temp_dir) / "composition-sketches"
        render_result = run_command(
            [
                PYTHON,
                "scripts/render_composition_sketches.py",
                "--stable",
                "--output-dir",
                str(rendered_dir),
            ]
        )
        if render_result.returncode != 0:
            print(render_result.stdout, file=sys.stderr)
            print(render_result.stderr, file=sys.stderr)
            return render_result.returncode

        blueprints = load_json(BLUEPRINTS)
        generated = load_json(COMMITTED_BUILD_PLANS)
        rendered = load_json(rendered_dir / "live12-track-build-plans.json")

        if generated != rendered:
            print("Generated composition build plans are not in sync with stable render.", file=sys.stderr)
            return 1
        if COMMITTED_README.read_text(encoding="utf-8") != (rendered_dir / "README.md").read_text(encoding="utf-8"):
            print("Generated composition README is not in sync with stable render.", file=sys.stderr)
            return 1

        role_contract = blueprints.get("role_contract", {})
        if set(role_contract.get("required_traditional_role_ids", [])) != EXPECTED_TRADITIONAL:
            print("Traditional bluegrass role contract is stale.", file=sys.stderr)
            return 1
        if set(role_contract.get("required_alien_role_ids", [])) != EXPECTED_ALIEN:
            print("Alien/electronic role contract is stale.", file=sys.stderr)
            return 1
        if set(role_contract.get("required_punk_role_ids", [])) != EXPECTED_PUNK:
            print("Punk role contract is stale.", file=sys.stderr)
            return 1
        if blueprints.get("claims_policy", {}).get("appeal_claim_status") != "hypothesis_not_proof":
            print("Blueprint appeal claims must stay hypothesis_not_proof.", file=sys.stderr)
            return 1

        blueprints_by_slug = {track["slug"]: track for track in blueprints.get("tracks", [])}
        for track in generated.get("tracks", []):
            slug = track["slug"]
            blueprint = track.get("composition_mutation_blueprint", {})
            if blueprint != blueprints_by_slug.get(slug):
                print(f"Generated plan does not mirror source blueprint: {slug}", file=sys.stderr)
                return 1
            if set(blueprint.get("traditional_role_jobs", {})) != EXPECTED_TRADITIONAL:
                print(f"Track does not cover the full traditional bluegrass stack: {slug}", file=sys.stderr)
                return 1
            if set(blueprint.get("alien_role_jobs", {})) != EXPECTED_ALIEN:
                print(f"Track does not cover the alien/electronic stack: {slug}", file=sys.stderr)
                return 1
            if set(blueprint.get("punk_role_jobs", {})) != EXPECTED_PUNK:
                print(f"Track does not cover punk production constraints: {slug}", file=sys.stderr)
                return 1
            focus_devices = {f"m4l.{focus}" for focus in track.get("max_for_live_focus", [])}
            lane_devices = {lane.get("device_id") for lane in blueprint.get("mutation_lanes", [])}
            if not focus_devices.issubset(lane_devices):
                print(f"Track blueprint does not cover Max for Live focus devices: {slug}", file=sys.stderr)
                return 1
            if len(blueprint.get("section_blueprints", [])) != len(track.get("scenes", [])):
                print(f"Track section blueprint count does not match generated scenes: {slug}", file=sys.stderr)
                return 1
            if blueprint.get("source_deck_plan", {}).get("deck_state") != "muted_until_human_provenance_review":
                print(f"Track source deck must default to muted provenance review: {slug}", file=sys.stderr)
                return 1

        assert_source_only(blueprints, "composition mutation blueprints")
        assert_source_only(generated, "generated composition build plans")

    print("Composition mutation blueprint probes passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
