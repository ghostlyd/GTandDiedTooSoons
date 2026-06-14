#!/usr/bin/env python3
"""Prepare a local-only Ableton Live 12 DAW mutation request and receipt template."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = ROOT / "automation" / "generated" / "live12-daw-mutation-package.json"
DEFAULT_OUTPUT_DIR = ROOT / "output" / "daw-mutations"
STABLE_GENERATED_AT = "1970-01-01T00:00:00Z"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_package_sources(package: dict[str, Any]) -> list[str]:
    errors = []
    for relative_path in package.get("source_files", []):
        path = Path(relative_path)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"Invalid package source path: {relative_path}")
            continue
        full_path = ROOT / path
        if not full_path.exists():
            errors.append(f"Missing package source file: {relative_path}")
            continue
        expected_hash = package.get("source_file_sha256", {}).get(relative_path)
        actual_hash = sha256_file(full_path)
        if expected_hash != actual_hash:
            errors.append(f"Stale package source hash: {relative_path}")
    return errors


def package_reference(package_path: Path) -> str:
    try:
        return str(package_path.relative_to(ROOT))
    except ValueError:
        return "external_package_override"


def build_request(
    package: dict[str, Any],
    package_path: Path,
    job: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    midi_path = ROOT / job["midi_artifact"]["path"]
    actual_midi_hash = sha256_file(midi_path)
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "generator": "scripts/prepare_live12_daw_mutation.py",
        "run_id": f"{generated_at.replace(':', '').replace('-', '')}.{job['track_slug']}",
        "execution_status": "prepared_not_applied",
        "track_slug": job["track_slug"],
        "track_title": job["track_title"],
        "mutation_job_id": job["id"],
        "mutation_package_path": package_reference(package_path),
        "mutation_package_sha256": sha256_file(package_path),
        "plan_track_sha256": job["plan_track_sha256"],
        "execution_mode": job["execution_mode"],
        "approval_state": {
            "live_set_mutation": "required_not_granted",
            "private_audio_upload": "required_not_granted",
            "export_or_release": "blocked_in_preflight",
        },
        "rollback": job["rollback"],
        "midi_verification": {
            "path": job["midi_artifact"]["path"],
            "expected_sha256": job["midi_artifact"]["sha256"],
            "actual_sha256": actual_midi_hash,
            "verified": actual_midi_hash == job["midi_artifact"]["sha256"],
        },
        "affected_tracks": job["affected_tracks"],
        "affected_returns": job["affected_returns"],
        "preflight_action_ids": job["preflight_action_ids"],
        "planned_action_ids": job["executable_action_ids"],
        "blocked_action_groups": job["blocked_action_groups"],
        "required_postflight_checks": package["receipt_contract"]["required_postflight_checks"],
        "prohibited_artifacts": package["receipt_contract"]["prohibited_artifacts"],
    }


def build_receipt_template(package: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": request["run_id"],
        "track_slug": request["track_slug"],
        "track_title": request["track_title"],
        "execution_status": "template_not_applied",
        "operator_approval_reference": "",
        "rollback_copy_reference": "",
        "mutation_package_sha256": request["mutation_package_sha256"],
        "plan_track_sha256": request["plan_track_sha256"],
        "midi_verification": request["midi_verification"],
        "affected_tracks": request["affected_tracks"],
        "affected_returns": request["affected_returns"],
        "applied_action_ids": [],
        "skipped_action_ids": [],
        "required_postflight_checks": package["receipt_contract"]["required_postflight_checks"],
        "created_artifacts": [],
        "redactions": [
            "no absolute home paths",
            "no private audio content",
            "no credentials, cookies, license files, or account artifacts",
            "no .als, .amxd, .alp, sample, preset, plugin, render, or export artifacts in Git",
        ],
    }


def build_operator_evidence_draft(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "operator_approval_reference": "",
        "rollback_copy_reference": "",
        "applied_action_ids": [],
        "skipped_action_ids": request["planned_action_ids"],
        "created_artifacts": [
            {
                "type": "local_ableton_session",
                "reference": "Fill after Ableton Live confirms the local set mutation.",
                "git_policy": "not_committed",
            }
        ],
        "postflight_checks": request["required_postflight_checks"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", required=True, help="Track slug from the generated DAW mutation package.")
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE, help="Generated DAW mutation package JSON.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Local-only output directory.")
    parser.add_argument("--stable", action="store_true", help="Use deterministic generated_at and run_id values.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package_path = args.package if args.package.is_absolute() else ROOT / args.package
    if not package_path.exists():
        print(f"Missing DAW mutation package: {args.package}", file=sys.stderr)
        return 1

    package = read_json(package_path)
    source_errors = validate_package_sources(package)
    if source_errors:
        for error in source_errors:
            print(error, file=sys.stderr)
        return 1

    jobs = {job.get("track_slug"): job for job in package.get("jobs", [])}
    job = jobs.get(args.track)
    if not job:
        print(f"Unknown track slug: {args.track}", file=sys.stderr)
        return 1

    midi_path = ROOT / job["midi_artifact"]["path"]
    if not midi_path.exists():
        print(f"Missing MIDI artifact for track {args.track}: {job['midi_artifact']['path']}", file=sys.stderr)
        return 1

    generated_at = STABLE_GENERATED_AT if args.stable else utc_now()
    request = build_request(package, package_path, job, generated_at)
    if not request["midi_verification"]["verified"]:
        print(f"MIDI hash mismatch for track {args.track}", file=sys.stderr)
        return 1
    receipt = build_receipt_template(package, request)
    evidence_draft = build_operator_evidence_draft(request)

    output_root = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    track_output = output_root / args.track
    write_json(track_output / "mutation-request.json", request)
    write_json(track_output / "receipt-template.json", receipt)
    write_json(track_output / "operator-evidence.json", evidence_draft)
    print(
        json.dumps(
            {
                "track_slug": args.track,
                "execution_status": request["execution_status"],
                "output_dir": str(track_output if args.output_dir.is_absolute() else track_output.relative_to(ROOT)),
                "planned_action_count": len(request["planned_action_ids"]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
