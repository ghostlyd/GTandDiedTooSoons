#!/usr/bin/env python3
"""Prepare and stage a full-set local Ableton Live 12 DAW mutation queue."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import prepare_live12_daw_mutation as preflight
import stage_live12_daw_import_bundle as bundle_stage


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = ROOT / "automation" / "generated" / "live12-daw-mutation-package.json"
DEFAULT_MAX_CONTRACTS = ROOT / "automation" / "generated" / "max-for-live-device-contracts.json"
DEFAULT_MUTATION_OUTPUT_DIR = ROOT / "output" / "daw-mutations"
DEFAULT_BUNDLE_OUTPUT_DIR = ROOT / "output" / "daw-import-bundles"
DEFAULT_QUEUE_OUTPUT_DIR = ROOT / "output" / "daw-mutation-queue"
STABLE_GENERATED_AT = preflight.STABLE_GENERATED_AT


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def output_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def common_artifact_base(paths: list[Path]) -> Path:
    resolved_paths = [path.resolve() for path in paths]
    common_path = Path(os.path.commonpath([str(path) for path in resolved_paths]))
    if common_path == Path("/"):
        raise ValueError("output directories must share a non-root artifact base")
    return common_path


def artifact_ref(path: Path, artifact_base: Path) -> str:
    return str(path.resolve().relative_to(artifact_base))


def validate_max_contracts(max_contracts: dict[str, Any], max_contracts_path: Path) -> list[str]:
    errors = []
    if max_contracts.get("artifact_policy", {}).get("git_policy") != "source_only_no_amxd":
        errors.append("Max for Live contracts must use source_only_no_amxd git policy")
    if not max_contracts.get("devices"):
        errors.append("Max for Live contracts must include at least one device")
    for device in max_contracts.get("devices", []):
        source_patch = device.get("source_patch")
        if not isinstance(source_patch, str) or not source_patch.endswith(".maxpat"):
            errors.append(f"Max for Live device missing .maxpat source patch: {device.get('id')}")
            continue
        source_patch_path = Path(source_patch)
        if source_patch_path.is_absolute() or ".." in source_patch_path.parts:
            errors.append(f"Invalid Max for Live source patch path: {source_patch}")
            continue
        if not (ROOT / source_patch_path).exists():
            errors.append(f"Missing Max for Live source patch: {source_patch}")
    if not max_contracts_path.exists():
        errors.append(f"Missing Max for Live contract bundle: {max_contracts_path}")
    return errors


def max_devices_for_job(job: dict[str, Any], max_contracts: dict[str, Any]) -> list[dict[str, Any]]:
    affected_tracks = set(job.get("affected_tracks", []))
    track_slug = job["track_slug"]
    devices = []
    for device in max_contracts.get("devices", []):
        target_tracks = device.get("target_tracks", [])
        track_slugs = device.get("track_slugs", [])
        if track_slug not in track_slugs and not affected_tracks.intersection(target_tracks):
            continue
        devices.append(
            {
                "id": device["id"],
                "display_name": device["display_name"],
                "device_class": device["device_class"],
                "approval_gate": device["approval_gate"],
                "target_tracks": target_tracks,
                "macro_controls": device["macro_controls"],
                "source_patch": device["source_patch"],
                "source_patch_sha256": device["source_patch_sha256"],
            }
        )
    return devices


def build_track_queue_entry(
    request: dict[str, Any],
    request_path: Path,
    receipt_template_path: Path,
    bundle_root: Path,
    staged_midi: Path,
    bundle_manifest: dict[str, Any],
    launch_plan: dict[str, Any],
    max_devices: list[dict[str, Any]],
    artifact_base: Path,
) -> dict[str, Any]:
    bundle_manifest_path = bundle_root / "bundle-manifest.json"
    launch_plan_path = bundle_root / "launch-plan.json"
    evidence_template_path = bundle_root / "operator-evidence-template.json"
    return {
        "track_slug": request["track_slug"],
        "track_title": request["track_title"],
        "execution_status": "queued_not_launched",
        "approval_state": request["approval_state"],
        "planned_action_count": len(request["planned_action_ids"]),
        "launch_status": launch_plan["launch_status"],
        "request": {
            "path": artifact_ref(request_path, artifact_base),
            "sha256": preflight.sha256_file(request_path),
        },
        "receipt_template": {
            "path": artifact_ref(receipt_template_path, artifact_base),
            "sha256": preflight.sha256_file(receipt_template_path),
        },
        "bundle_manifest": {
            "path": artifact_ref(bundle_manifest_path, artifact_base),
            "sha256": preflight.sha256_file(bundle_manifest_path),
            "git_policy": bundle_manifest["git_policy"],
        },
        "launch_plan": {
            "path": artifact_ref(launch_plan_path, artifact_base),
            "launch_status": launch_plan["launch_status"],
            "requires": launch_plan["requires"],
        },
        "operator_evidence_template": {
            "path": artifact_ref(evidence_template_path, artifact_base),
            "sha256": preflight.sha256_file(evidence_template_path),
        },
        "staged_midi": {
            "path": artifact_ref(staged_midi, artifact_base),
            "sha256": bundle_manifest["midi_staging"]["sha256"],
        },
        "max_for_live_devices": max_devices,
    }


def build_queue_manifest(
    package: dict[str, Any],
    package_path: Path,
    max_contracts: dict[str, Any],
    max_contracts_path: Path,
    queue_output_dir: Path,
    artifact_base: Path,
    generated_at: str,
    track_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "generator": "scripts/prepare_live12_daw_mutation_queue.py",
        "execution_status": "queued_not_launched",
        "artifact_base": bundle_stage.repo_relative(artifact_base),
        "queue_manifest": artifact_ref(queue_output_dir / "queue-manifest.json", artifact_base),
        "mutation_package": {
            "path": preflight.package_reference(package_path),
            "sha256": preflight.sha256_file(package_path),
        },
        "max_for_live_contracts": {
            "path": bundle_stage.repo_relative(max_contracts_path),
            "sha256": preflight.sha256_file(max_contracts_path),
            "device_count": max_contracts["device_count"],
            "git_policy": max_contracts["artifact_policy"]["git_policy"],
        },
        "track_count": len(track_entries),
        "total_planned_action_count": sum(track["planned_action_count"] for track in track_entries),
        "approval_gates_required": package["safety"]["requires_operator_approval_before_execution"],
        "blocked_action_groups": ["mix_and_release_gates"],
        "launch_policy": {
            "status": "blocked_until_per_track_confirm_live_mutation",
            "required_flags": [
                "--launch-ableton",
                "--confirm-live-mutation",
                "--operator-approval-reference",
                "--rollback-copy-reference",
            ],
        },
        "receipt_contract": package["receipt_contract"],
        "tracks": track_entries,
        "git_policy": "ignored_local_only",
    }


def prepare_track(
    package: dict[str, Any],
    package_path: Path,
    max_contracts: dict[str, Any],
    job: dict[str, Any],
    mutation_output_dir: Path,
    bundle_output_dir: Path,
    generated_at: str,
    ableton_app: str,
    artifact_base: Path,
) -> dict[str, Any]:
    midi_path = ROOT / job["midi_artifact"]["path"]
    if not midi_path.exists():
        raise ValueError(f"Missing MIDI artifact for track {job['track_slug']}: {job['midi_artifact']['path']}")

    request = preflight.build_request(package, package_path, job, generated_at)
    if not request["midi_verification"]["verified"]:
        raise ValueError(f"MIDI hash mismatch for track {job['track_slug']}")
    receipt = preflight.build_receipt_template(package, request)

    track_output = mutation_output_dir / job["track_slug"]
    request_path = track_output / "mutation-request.json"
    receipt_template_path = track_output / "receipt-template.json"
    write_json(request_path, request)
    write_json(receipt_template_path, receipt)

    staged_midi, bundle_manifest, launch_plan = bundle_stage.stage_bundle(
        request,
        request_path,
        bundle_output_dir,
        generated_at,
        ableton_app,
        "",
        "",
    )
    bundle_root = bundle_output_dir / job["track_slug"]
    return build_track_queue_entry(
        request,
        request_path,
        receipt_template_path,
        bundle_root,
        staged_midi,
        bundle_manifest,
        launch_plan,
        max_devices_for_job(job, max_contracts),
        artifact_base,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE, help="Generated DAW mutation package JSON.")
    parser.add_argument("--max-contracts", type=Path, default=DEFAULT_MAX_CONTRACTS, help="Generated source-only Max for Live device contracts JSON.")
    parser.add_argument("--mutation-output-dir", type=Path, default=DEFAULT_MUTATION_OUTPUT_DIR, help="Local-only mutation request output directory.")
    parser.add_argument("--bundle-output-dir", type=Path, default=DEFAULT_BUNDLE_OUTPUT_DIR, help="Local-only import bundle output directory.")
    parser.add_argument("--queue-output-dir", type=Path, default=DEFAULT_QUEUE_OUTPUT_DIR, help="Local-only queue manifest output directory.")
    parser.add_argument("--ableton-app", default=bundle_stage.DEFAULT_ABLETON_APP, help="macOS Ableton application name for launch plans.")
    parser.add_argument("--stable", action="store_true", help="Use deterministic generated_at value.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package_path = output_path(args.package)
    max_contracts_path = output_path(args.max_contracts)
    if not package_path.exists():
        print(f"Missing DAW mutation package: {args.package}", file=sys.stderr)
        return 1
    if not max_contracts_path.exists():
        print(f"Missing Max for Live contract bundle: {args.max_contracts}", file=sys.stderr)
        return 1

    package = preflight.read_json(package_path)
    max_contracts = preflight.read_json(max_contracts_path)
    source_errors = preflight.validate_package_sources(package)
    source_errors.extend(validate_max_contracts(max_contracts, max_contracts_path))
    if source_errors:
        for error in source_errors:
            print(error, file=sys.stderr)
        return 1

    mutation_output_dir = output_path(args.mutation_output_dir)
    bundle_output_dir = output_path(args.bundle_output_dir)
    queue_output_dir = output_path(args.queue_output_dir)
    try:
        artifact_base = common_artifact_base([mutation_output_dir, bundle_output_dir, queue_output_dir])
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    generated_at = STABLE_GENERATED_AT if args.stable else preflight.utc_now()
    try:
        tracks = [
            prepare_track(
                package,
                package_path,
                max_contracts,
                job,
                mutation_output_dir,
                bundle_output_dir,
                generated_at,
                args.ableton_app,
                artifact_base,
            )
            for job in package.get("jobs", [])
        ]
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    queue_manifest = build_queue_manifest(
        package,
        package_path,
        max_contracts,
        max_contracts_path,
        queue_output_dir,
        artifact_base,
        generated_at,
        tracks,
    )
    queue_manifest_path = queue_output_dir / "queue-manifest.json"
    write_json(queue_manifest_path, queue_manifest)
    print(
        json.dumps(
            {
                "execution_status": queue_manifest["execution_status"],
                "queue_manifest": bundle_stage.repo_relative(queue_manifest_path),
                "track_count": queue_manifest["track_count"],
                "total_planned_action_count": queue_manifest["total_planned_action_count"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
