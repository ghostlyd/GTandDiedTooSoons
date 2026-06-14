#!/usr/bin/env python3
"""Stage a local Ableton Live 12 import bundle from a prepared DAW mutation request."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "output" / "daw-import-bundles"
DEFAULT_ABLETON_APP = "Ableton Live 12 Suite"
STABLE_STAGED_AT = "1970-01-01T00:00:00Z"


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


def validate_request(request: dict[str, Any], request_path: Path) -> list[str]:
    errors = []
    if request.get("execution_status") != "prepared_not_applied":
        errors.append("mutation request execution_status must be prepared_not_applied")
    approval_state = request.get("approval_state", {})
    if approval_state.get("live_set_mutation") != "required_not_granted":
        errors.append("mutation request must require live_set_mutation approval")
    if approval_state.get("export_or_release") != "blocked_in_preflight":
        errors.append("mutation request must block export_or_release in preflight")
    midi_path_value = request.get("midi_verification", {}).get("path")
    if not isinstance(midi_path_value, str) or not midi_path_value:
        errors.append("mutation request missing midi_verification.path")
    else:
        midi_path = Path(midi_path_value)
        if midi_path.is_absolute() or ".." in midi_path.parts or midi_path.parts[:3] != ("compositions", "generated", "midi"):
            errors.append(f"mutation request MIDI path must stay under compositions/generated/midi: {midi_path_value}")
        elif not (ROOT / midi_path).exists():
            errors.append(f"mutation request MIDI file is missing: {midi_path_value}")
    if not request_path.exists():
        errors.append(f"mutation request file is missing: {request_path}")
    return errors


def build_operator_evidence_template(
    request: dict[str, Any],
    approval_reference: str,
    rollback_reference: str,
) -> dict[str, Any]:
    return {
        "operator_approval_reference": approval_reference,
        "rollback_copy_reference": rollback_reference,
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


def stage_bundle(
    request: dict[str, Any],
    request_path: Path,
    output_dir: Path,
    staged_at: str,
    ableton_app: str,
    approval_reference: str,
    rollback_reference: str,
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    track_slug = request["track_slug"]
    bundle_root = output_dir / track_slug
    midi_source = ROOT / request["midi_verification"]["path"]
    staged_midi = bundle_root / "midi" / midi_source.name
    staged_request = bundle_root / "mutation-request.json"
    staged_midi.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(midi_source, staged_midi)
    shutil.copy2(request_path, staged_request)
    staged_midi_sha256 = sha256_file(staged_midi)
    if staged_midi_sha256 != request["midi_verification"]["expected_sha256"]:
        raise ValueError("staged MIDI hash did not match the mutation request")

    launch_plan = {
        "schema_version": 1,
        "staged_at": staged_at,
        "track_slug": track_slug,
        "track_title": request["track_title"],
        "launch_status": "blocked_until_confirm_live_mutation",
        "ableton_app": ableton_app,
        "launch_command": [
            "open",
            "-a",
            ableton_app,
            repo_relative(staged_midi),
        ],
        "requires": [
            "--launch-ableton",
            "--confirm-live-mutation",
            "--operator-approval-reference",
            "--rollback-copy-reference",
        ],
        "blocked_actions": [
            "export",
            "release",
            "commit Ableton or Max binaries",
            "load unapproved source audio",
        ],
    }
    evidence_template = build_operator_evidence_template(request, approval_reference, rollback_reference)
    bundle_manifest = {
        "schema_version": 1,
        "staged_at": staged_at,
        "generator": "scripts/stage_live12_daw_import_bundle.py",
        "execution_status": "staged_not_launched",
        "track_slug": track_slug,
        "track_title": request["track_title"],
        "source_request": {
            "path": repo_relative(request_path),
            "sha256": sha256_file(request_path),
        },
        "staged_request": {
            "path": repo_relative(staged_request),
            "sha256": sha256_file(staged_request),
        },
        "midi_staging": {
            "source_path": request["midi_verification"]["path"],
            "staged_path": repo_relative(staged_midi),
            "sha256": staged_midi_sha256,
        },
        "launch_plan": repo_relative(bundle_root / "launch-plan.json"),
        "operator_evidence_template": repo_relative(bundle_root / "operator-evidence-template.json"),
        "receipt_command": [
            "python3",
            "scripts/record_live12_daw_mutation_receipt.py",
            "--request",
            repo_relative(staged_request),
            "--evidence",
            repo_relative(bundle_root / "operator-evidence-template.json"),
        ],
        "git_policy": "ignored_local_only",
    }
    write_json(bundle_root / "bundle-manifest.json", bundle_manifest)
    write_json(bundle_root / "launch-plan.json", launch_plan)
    write_json(bundle_root / "operator-evidence-template.json", evidence_template)
    return staged_midi, bundle_manifest, launch_plan


def launch_ableton(staged_midi: Path, ableton_app: str) -> Any:
    import subprocess

    return subprocess.run(
        ["open", "-a", ableton_app, str(staged_midi)],
        check=False,
        capture_output=True,
        text=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path, help="Prepared mutation-request.json path.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Local-only bundle output directory.")
    parser.add_argument("--stable", action="store_true", help="Use deterministic staged_at value.")
    parser.add_argument("--ableton-app", default=DEFAULT_ABLETON_APP, help="macOS Ableton application name for launch plans.")
    parser.add_argument("--launch-ableton", action="store_true", help="Launch Ableton with the staged MIDI file after staging.")
    parser.add_argument("--confirm-live-mutation", action="store_true", help="Required with --launch-ableton to acknowledge local DAW mutation risk.")
    parser.add_argument("--operator-approval-reference", default="", help="Required approval reference when launching Ableton.")
    parser.add_argument("--rollback-copy-reference", default="", help="Required rollback reference when launching Ableton.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request_path = args.request if args.request.is_absolute() else ROOT / args.request
    if not request_path.exists():
        print(f"Missing mutation request: {args.request}", file=sys.stderr)
        return 1
    request = read_json(request_path)
    errors = validate_request(request, request_path)
    if args.launch_ableton:
        if not args.confirm_live_mutation:
            errors.append("--confirm-live-mutation is required with --launch-ableton")
        if not args.operator_approval_reference:
            errors.append("--operator-approval-reference is required with --launch-ableton")
        if not args.rollback_copy_reference:
            errors.append("--rollback-copy-reference is required with --launch-ableton")
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    staged_at = STABLE_STAGED_AT if args.stable else utc_now()
    try:
        staged_midi, bundle_manifest, launch_plan = stage_bundle(
            request,
            request_path,
            output_dir,
            staged_at,
            args.ableton_app,
            args.operator_approval_reference,
            args.rollback_copy_reference,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    launch_status = "not_requested"
    if args.launch_ableton:
        launch_result = launch_ableton(staged_midi, args.ableton_app)
        if launch_result.returncode != 0:
            print(launch_result.stdout, file=sys.stderr)
            print(launch_result.stderr, file=sys.stderr)
            return launch_result.returncode
        launch_status = "open_command_sent"

    print(
        json.dumps(
            {
                "track_slug": request["track_slug"],
                "execution_status": bundle_manifest["execution_status"],
                "launch_status": launch_status,
                "bundle_root": str((output_dir / request["track_slug"]).relative_to(ROOT) if not args.output_dir.is_absolute() else output_dir / request["track_slug"]),
                "staged_midi": launch_plan["launch_command"][-1],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
