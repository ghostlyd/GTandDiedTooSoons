#!/usr/bin/env python3
"""Render source-only Max for Live device contract bundle and .maxpat blueprints."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACTS = ROOT / "automation" / "max-for-live-device-contracts.json"
DEFAULT_SESSION_TEMPLATE = ROOT / "automation" / "live12-session-template.json"
DEFAULT_BUILD_PLANS = ROOT / "compositions" / "generated" / "live12-track-build-plans.json"
DEFAULT_OUTPUT = ROOT / "automation" / "generated" / "max-for-live-device-contracts.json"
DEFAULT_PATCH_OUTPUT_DIR = ROOT / "max-for-live" / "patches"
STABLE_GENERATED_AT = "1970-01-01T00:00:00Z"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return "external_path_redacted"


def patch_filename(device_id: str) -> str:
    return f"{device_id.replace('.', '_')}.maxpat"


def collect_usage(session_template: dict[str, Any], build_plans: dict[str, Any]) -> dict[str, dict[str, Any]]:
    usage: dict[str, dict[str, Any]] = {}

    def entry(contract: str) -> dict[str, Any]:
        return usage.setdefault(
            contract,
            {
                "target_tracks": set(),
                "performance_inputs": set(),
                "layer_ids": set(),
                "track_slugs": set(),
                "automation_targets": set(),
                "traditional_bluegrass_layer": False,
                "alien_electronic_layer": False,
            },
        )

    for track in session_template.get("tracks", []):
        for contract in track.get("device_contracts", []):
            contract_usage = entry(contract)
            contract_usage["target_tracks"].add(track["name"])
            if track.get("input"):
                contract_usage["performance_inputs"].add(track["input"])

    for track_plan in build_plans.get("tracks", []):
        for layer in track_plan.get("layers", []):
            for contract in layer.get("device_contracts", []):
                contract_usage = entry(contract)
                contract_usage["target_tracks"].add(layer["session_track"])
                contract_usage["layer_ids"].add(layer["id"])
                contract_usage["track_slugs"].add(track_plan["slug"])
                contract_usage["automation_targets"].update(layer.get("automation_targets", []))
                contract_usage["traditional_bluegrass_layer"] = (
                    contract_usage["traditional_bluegrass_layer"] or layer.get("traditional_bluegrass_layer", False)
                )
                contract_usage["alien_electronic_layer"] = (
                    contract_usage["alien_electronic_layer"] or layer.get("alien_electronic_layer", False)
                )

    return usage


def sorted_usage(contract_usage: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_tracks": sorted(contract_usage["target_tracks"]),
        "performance_inputs": sorted(contract_usage["performance_inputs"]),
        "layer_ids": sorted(contract_usage["layer_ids"]),
        "track_slugs": sorted(contract_usage["track_slugs"]),
        "automation_targets": sorted(contract_usage["automation_targets"]),
        "traditional_bluegrass_layer": contract_usage["traditional_bluegrass_layer"],
        "alien_electronic_layer": contract_usage["alien_electronic_layer"],
    }


def validate_definitions(source_contracts: dict[str, Any], usage: dict[str, dict[str, Any]]) -> list[str]:
    errors = []
    defined = {device.get("id") for device in source_contracts.get("devices", [])}
    referenced = set(usage)
    missing = sorted(referenced - defined)
    extra = sorted(defined - referenced)
    if missing:
        errors.append(f"Missing Max for Live device definitions: {', '.join(missing)}")
    if extra:
        errors.append(f"Unused Max for Live device definitions: {', '.join(extra)}")
    for device in source_contracts.get("devices", []):
        if not device.get("id", "").startswith("m4l."):
            errors.append(f"Device id must start with m4l.: {device.get('id')}")
        if device.get("device_class") not in {"midi_effect", "audio_effect"}:
            errors.append(f"Device class must be midi_effect or audio_effect: {device.get('id')}")
        if not device.get("macro_controls"):
            errors.append(f"Device must expose at least one macro control: {device.get('id')}")
    return errors


def maxpat_box(box_id: str, maxclass: str, text: str, x: float, y: float, width: float = 720.0) -> dict[str, Any]:
    box: dict[str, Any] = {
        "id": box_id,
        "maxclass": maxclass,
        "patching_rect": [x, y, width, 22.0],
    }
    if text:
        box["text"] = text
    return {"box": box}


def live_dial_box(box_id: str, varname: str, x: float, y: float) -> dict[str, Any]:
    return {
        "box": {
            "id": box_id,
            "maxclass": "live.dial",
            "parameter_enable": 1,
            "patching_rect": [x, y, 180.0, 48.0],
            "presentation": 1,
            "presentation_rect": [x, y, 180.0, 48.0],
            "varname": varname,
        }
    }


def render_patch(device: dict[str, Any], device_usage: dict[str, Any]) -> dict[str, Any]:
    boxes = [
        maxpat_box("obj-1", "comment", device["display_name"], 30.0, 25.0),
        maxpat_box("obj-2", "comment", device["purpose"], 30.0, 55.0),
        maxpat_box("obj-3", "comment", f"Contract id: {device['id']}", 30.0, 90.0),
        maxpat_box("obj-4", "comment", f"Device class: {device['device_class']}", 30.0, 120.0),
        maxpat_box("obj-5", "comment", f"Target tracks: {', '.join(device_usage['target_tracks'])}", 30.0, 150.0),
        maxpat_box("obj-6", "newobj", "inlet", 30.0, 195.0, 90.0),
        maxpat_box("obj-7", "newobj", "outlet", 150.0, 195.0, 90.0),
    ]
    y = 240.0
    for index, macro in enumerate(device["macro_controls"], start=8):
        boxes.append(live_dial_box(f"obj-{index}", macro, 30.0, y))
        boxes.append(maxpat_box(f"obj-{index}-comment", "comment", f"Macro: {macro}", 230.0, y, 360.0))
        y += 40.0
    boxes.append(maxpat_box("obj-policy", "comment", "Source-only patch blueprint. Do not commit compiled .amxd output.", 30.0, y + 10.0))
    return {
        "patcher": {
            "fileversion": 1,
            "appversion": {
                "major": 8,
                "minor": 6,
                "revision": 0,
                "architecture": "x64",
                "modernui": 1,
            },
            "classnamespace": "box",
            "rect": [0.0, 0.0, 900.0, 640.0],
            "bglocked": 0,
            "openinpresentation": 1,
            "default_fontsize": 12.0,
            "default_fontface": 0,
            "default_fontname": "Arial",
            "gridonopen": 1,
            "gridsize": [15.0, 15.0],
            "boxes": boxes,
            "lines": [],
        }
    }


def render_bundle(
    source_contracts: dict[str, Any],
    usage: dict[str, dict[str, Any]],
    output: Path,
    patch_output_dir: Path,
    generated_at: str,
    source_files: list[Path],
) -> dict[str, Any]:
    devices = []
    for device in source_contracts["devices"]:
        device_usage = sorted_usage(usage[device["id"]])
        patch_path = patch_output_dir / patch_filename(device["id"])
        write_json(patch_path, render_patch(device, device_usage))
        source_patch = DEFAULT_PATCH_OUTPUT_DIR / patch_path.name
        devices.append(
            {
                "id": device["id"],
                "display_name": device["display_name"],
                "device_class": device["device_class"],
                "purpose": device["purpose"],
                "approval_gate": "live_set_mutation",
                "target_tracks": device_usage["target_tracks"],
                "performance_inputs": device_usage["performance_inputs"],
                "macro_controls": device["macro_controls"],
                "automation_targets_observed": device_usage["automation_targets"],
                "track_slugs": device_usage["track_slugs"],
                "layer_ids": device_usage["layer_ids"],
                "traditional_bluegrass_layer": device_usage["traditional_bluegrass_layer"],
                "alien_electronic_layer": device_usage["alien_electronic_layer"],
                "implementation_hints": device["implementation_hints"],
                "source_patch": repo_relative(source_patch),
                "source_patch_sha256": sha256_file(patch_path),
            }
        )

    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "generator": "scripts/render_max_for_live_device_contracts.py",
        "purpose": source_contracts["purpose"],
        "source_files": [repo_relative(path) for path in source_files],
        "source_file_sha256": {repo_relative(path): sha256_file(path) for path in source_files},
        "artifact_policy": source_contracts["artifact_policy"],
        "device_count": len(devices),
        "devices": devices,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contracts", type=Path, default=DEFAULT_CONTRACTS, help="Source Max for Live device contracts JSON.")
    parser.add_argument("--session-template", type=Path, default=DEFAULT_SESSION_TEMPLATE, help="Live 12 session template JSON.")
    parser.add_argument("--build-plans", type=Path, default=DEFAULT_BUILD_PLANS, help="Generated track build plans JSON.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Generated Max for Live contract bundle JSON.")
    parser.add_argument("--patch-output-dir", type=Path, default=DEFAULT_PATCH_OUTPUT_DIR, help="Directory for generated .maxpat source patches.")
    parser.add_argument("--stable", action="store_true", help="Use deterministic generated_at value.")
    return parser.parse_args()


def resolved(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    args = parse_args()
    contracts_path = resolved(args.contracts)
    session_template_path = resolved(args.session_template)
    build_plans_path = resolved(args.build_plans)
    output_path = resolved(args.output)
    patch_output_dir = resolved(args.patch_output_dir)
    for required_path in [contracts_path, session_template_path, build_plans_path]:
        if not required_path.exists():
            print(f"Missing required input: {required_path}", file=sys.stderr)
            return 1

    source_contracts = read_json(contracts_path)
    session_template = read_json(session_template_path)
    build_plans = read_json(build_plans_path)
    usage = collect_usage(session_template, build_plans)
    errors = validate_definitions(source_contracts, usage)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    generated_at = STABLE_GENERATED_AT if args.stable else utc_now()
    bundle = render_bundle(
        source_contracts,
        usage,
        output_path,
        patch_output_dir,
        generated_at,
        [contracts_path, session_template_path, build_plans_path],
    )
    write_json(output_path, bundle)
    print(
        json.dumps(
            {
                "device_count": bundle["device_count"],
                "output": repo_relative(output_path),
                "patch_output_dir": repo_relative(patch_output_dir),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
