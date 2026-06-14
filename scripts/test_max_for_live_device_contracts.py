#!/usr/bin/env python3
"""Regression probes for source-only Max for Live device contracts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
GENERATED_CONTRACTS = ROOT / "automation" / "generated" / "max-for-live-device-contracts.json"
PATCH_SOURCE_DIR = ROOT / "max-for-live" / "patches"
EXPECTED_BANJO_MACROS = ["velocity_curve", "roll_density", "pluck_decay", "humanize_ms"]


def run_command(args: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=False, capture_output=True, text=True)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_device_contracts() -> set[str]:
    session_template = load_json(ROOT / "automation" / "live12-session-template.json")
    build_plans = load_json(ROOT / "compositions" / "generated" / "live12-track-build-plans.json")
    contracts = {
        contract
        for track in session_template["tracks"]
        for contract in track.get("device_contracts", [])
    }
    contracts.update(
        contract
        for track in build_plans["tracks"]
        for layer in track["layers"]
        for contract in layer.get("device_contracts", [])
    )
    return contracts


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


def assert_source_only(data: dict[str, Any], label: str) -> None:
    for value in iter_string_values(data):
        if "/Users/" in value:
            raise AssertionError(f"{label} leaked an absolute user path: {value}")
        if "/" in value and value.endswith((".amxd", ".als", ".alp", ".wav", ".aiff", ".flac", ".mp3", ".m4a", ".ogg")):
            raise AssertionError(f"{label} referenced a blocked binary/audio artifact: {value}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="m4l-contracts-test-") as temp_dir:
        temp_root = Path(temp_dir)
        rendered_contracts = temp_root / "max-for-live-device-contracts.json"
        rendered_patches = temp_root / "patches"
        render_result = run_command(
            [
                PYTHON,
                "scripts/render_max_for_live_device_contracts.py",
                "--stable",
                "--output",
                str(rendered_contracts),
                "--patch-output-dir",
                str(rendered_patches),
            ]
        )
        if render_result.returncode != 0:
            print(render_result.stdout, file=sys.stderr)
            print(render_result.stderr, file=sys.stderr)
            return render_result.returncode

        generated = load_json(GENERATED_CONTRACTS)
        rendered = load_json(rendered_contracts)
        if rendered != generated:
            print("Generated Max for Live device contracts are not in sync.", file=sys.stderr)
            return 1

        expected_contracts = collect_device_contracts()
        generated_contracts = {device["id"] for device in generated["devices"]}
        if generated_contracts != expected_contracts:
            print("Generated Max for Live device contracts must cover every session/build-plan device contract.", file=sys.stderr)
            print(f"missing: {sorted(expected_contracts - generated_contracts)}", file=sys.stderr)
            print(f"extra: {sorted(generated_contracts - expected_contracts)}", file=sys.stderr)
            return 1

        if generated.get("artifact_policy", {}).get("git_policy") != "source_only_no_amxd":
            print("Max for Live artifact policy must block compiled .amxd artifacts.", file=sys.stderr)
            return 1
        assert_source_only(generated, "Max for Live generated contracts")

        devices = {device["id"]: device for device in generated["devices"]}
        banjo_mapper = devices["m4l.aeroband_banjo_mapper"]
        if banjo_mapper.get("device_class") != "midi_effect":
            print("AeroBand banjo mapper must be a MIDI effect contract.", file=sys.stderr)
            return 1
        if banjo_mapper.get("target_tracks") != ["AeroBand Banjo Lead"]:
            print("AeroBand banjo mapper must target only the controller lead track.", file=sys.stderr)
            return 1
        if banjo_mapper.get("macro_controls") != EXPECTED_BANJO_MACROS:
            print("AeroBand banjo mapper macros must mirror the track automation targets.", file=sys.stderr)
            return 1
        if "AeroBand MIDI guitar/controller" not in banjo_mapper.get("performance_inputs", []):
            print("AeroBand banjo mapper must document the performer controller input.", file=sys.stderr)
            return 1

        for device in generated["devices"]:
            patch_path = ROOT / device["source_patch"]
            rendered_patch_path = rendered_patches / patch_path.name
            for candidate in [patch_path, rendered_patch_path]:
                if candidate.suffix != ".maxpat" or not candidate.exists():
                    print(f"Missing source .maxpat patch: {candidate}", file=sys.stderr)
                    return 1
                patch = load_json(candidate)
                if "patcher" not in patch:
                    print(f"Source .maxpat patch missing patcher root: {candidate}", file=sys.stderr)
                    return 1
                live_dials = [
                    box["box"]
                    for box in patch["patcher"].get("boxes", [])
                    if box.get("box", {}).get("maxclass") == "live.dial"
                ]
                dial_varnames = [dial.get("varname") for dial in live_dials]
                if dial_varnames != device["macro_controls"]:
                    print(f"Source .maxpat live.dial varnames must mirror macro controls: {candidate}", file=sys.stderr)
                    return 1
                if any(dial.get("parameter_enable") != 1 for dial in live_dials):
                    print(f"Source .maxpat live.dial boxes must be Live-parameter enabled: {candidate}", file=sys.stderr)
                    return 1
                assert_source_only(patch, str(candidate))

    print("Max for Live device contract probes passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
