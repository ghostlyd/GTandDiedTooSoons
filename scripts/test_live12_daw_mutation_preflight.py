#!/usr/bin/env python3
"""Regression probes for Live 12 DAW mutation packages and local receipts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
TRACK_SLUG = "good-vibrations-in-a-burned-barn"
TRACK_TITLE = "Good Vibrations in a Burned Barn"
MAX_CONTRACTS_PATH = ROOT / "automation" / "generated" / "max-for-live-device-contracts.json"
EXPECTED_TRACK_SLUGS = [
    "good-vibrations-in-a-burned-barn",
    "a-p-carter-in-the-warehouse",
    "no-gods-no-masters-no-quantize",
    "possum-kingdom-afterhours",
    "the-ballad-of-the-broken-controller",
]
APPROVAL_REFERENCE = "operator-approved-live-set-mutation-001"
ROLLBACK_REFERENCE = "local rollback copy verified outside git"


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


def assert_no_sensitive_paths(data: dict[str, Any], label: str) -> None:
    for value in iter_string_values(data):
        if "/Users/" in value:
            raise AssertionError(f"{label} leaked an absolute user path: {value}")
        if "sources/public-domain/raw/" in value:
            raise AssertionError(f"{label} leaked a raw public-domain source path: {value}")
        if "/" in value and value.endswith((".als", ".amxd", ".alp", ".wav", ".aiff", ".flac", ".mp3", ".m4a", ".ogg")):
            raise AssertionError(f"{label} carried a blocked binary/audio artifact path: {value}")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="live12-daw-mutation-test-") as temp_dir:
        temp_root = Path(temp_dir)
        package_path = temp_root / "live12-daw-mutation-package.json"
        render_result = run_command(
            [
                PYTHON,
                "scripts/render_live12_daw_mutation_package.py",
                "--stable",
                "--output",
                str(package_path),
            ]
        )
        if render_result.returncode != 0:
            print(render_result.stdout, file=sys.stderr)
            print(render_result.stderr, file=sys.stderr)
            return render_result.returncode

        package = load_json(package_path)
        jobs = package.get("jobs", [])
        if package.get("schema_version") != 1 or len(jobs) != 5:
            print("Mutation package must contain schema_version 1 and one job per generated track.", file=sys.stderr)
            return 1
        first_job = jobs[0]
        if first_job.get("track_slug") != TRACK_SLUG:
            print("Mutation package job order must match the DAW action plan.", file=sys.stderr)
            return 1
        if first_job.get("execution_mode") != "local_preflight_then_human_approved_daw_mutation":
            print("Mutation package must stay in local preflight execution mode.", file=sys.stderr)
            return 1
        if first_job.get("blocked_action_groups") != ["mix_and_release_gates"]:
            print("Mutation package must block export/release actions from DAW mutation preflight.", file=sys.stderr)
            return 1
        if "Public Domain Source Deck" not in first_job.get("affected_tracks", []):
            print("Mutation package must include the muted source deck in affected track scope.", file=sys.stderr)
            return 1
        assert_no_sensitive_paths(package, "mutation package")

        queue_result = run_command(
            [
                PYTHON,
                "scripts/prepare_live12_daw_mutation_queue.py",
                "--package",
                str(package_path),
                "--mutation-output-dir",
                str(temp_root / "queue-preflight"),
                "--bundle-output-dir",
                str(temp_root / "queue-bundles"),
                "--queue-output-dir",
                str(temp_root / "queue"),
                "--stable",
            ]
        )
        if queue_result.returncode != 0:
            print(queue_result.stdout, file=sys.stderr)
            print(queue_result.stderr, file=sys.stderr)
            return queue_result.returncode
        queue_manifest_path = temp_root / "queue" / "queue-manifest.json"
        if not queue_manifest_path.exists():
            print("DAW mutation queue must write queue-manifest.json.", file=sys.stderr)
            return 1
        queue_manifest = load_json(queue_manifest_path)
        if queue_manifest.get("execution_status") != "queued_not_launched":
            print("DAW mutation queue must not claim Ableton was launched.", file=sys.stderr)
            return 1
        queue_tracks = queue_manifest.get("tracks", [])
        if [track.get("track_slug") for track in queue_tracks] != EXPECTED_TRACK_SLUGS:
            print("DAW mutation queue must preserve package track order.", file=sys.stderr)
            return 1
        expected_action_count = sum(job["mutation_action_count"] for job in jobs)
        if queue_manifest.get("total_planned_action_count") != expected_action_count:
            print("DAW mutation queue must summarize planned action count across all tracks.", file=sys.stderr)
            return 1
        max_contracts = load_json(MAX_CONTRACTS_PATH)
        queue_max_contracts = queue_manifest.get("max_for_live_contracts", {})
        if queue_max_contracts.get("path") != "automation/generated/max-for-live-device-contracts.json":
            print("DAW mutation queue must reference the generated Max for Live contract bundle.", file=sys.stderr)
            return 1
        if queue_max_contracts.get("sha256") is None or queue_max_contracts.get("device_count") != max_contracts["device_count"]:
            print("DAW mutation queue must include the Max for Live contract hash and device count.", file=sys.stderr)
            return 1
        if queue_max_contracts.get("git_policy") != "source_only_no_amxd":
            print("DAW mutation queue must keep Max for Live artifacts source-only.", file=sys.stderr)
            return 1
        expected_device_ids = [device["id"] for device in max_contracts["devices"]]
        for track in queue_tracks:
            for key in ["request", "receipt_template", "bundle_manifest", "launch_plan", "operator_evidence_template", "staged_midi"]:
                track_path = temp_root / track[key]["path"]
                if not track_path.exists():
                    print(f"DAW mutation queue missing staged artifact: {track_path}", file=sys.stderr)
                    return 1
            launch_plan = load_json(temp_root / track["launch_plan"]["path"])
            if launch_plan.get("launch_status") != "blocked_until_confirm_live_mutation":
                print("DAW mutation queue must keep each Ableton launch blocked.", file=sys.stderr)
                return 1
            max_devices = track.get("max_for_live_devices", [])
            if [device.get("id") for device in max_devices] != expected_device_ids:
                print("DAW mutation queue must include ordered Max for Live device contracts for each track.", file=sys.stderr)
                return 1
            for device in max_devices:
                patch_path = ROOT / device.get("source_patch", "")
                if patch_path.suffix != ".maxpat" or not patch_path.exists():
                    print(f"DAW mutation queue Max device must reference a committed .maxpat source patch: {patch_path}", file=sys.stderr)
                    return 1
                if device.get("approval_gate") != "live_set_mutation":
                    print("DAW mutation queue Max device entries must require live_set_mutation approval.", file=sys.stderr)
                    return 1
        assert_no_sensitive_paths(queue_manifest, "DAW mutation queue")

        output_dir = temp_root / "preflight"
        preflight_result = run_command(
            [
                PYTHON,
                "scripts/prepare_live12_daw_mutation.py",
                "--track",
                TRACK_SLUG,
                "--package",
                str(package_path),
                "--stable",
                "--output-dir",
                str(output_dir),
            ]
        )
        if preflight_result.returncode != 0:
            print(preflight_result.stdout, file=sys.stderr)
            print(preflight_result.stderr, file=sys.stderr)
            return preflight_result.returncode

        request_path = output_dir / TRACK_SLUG / "mutation-request.json"
        receipt_path = output_dir / TRACK_SLUG / "receipt-template.json"
        if not request_path.exists() or not receipt_path.exists():
            print("DAW mutation preflight must write request and receipt-template JSON files.", file=sys.stderr)
            return 1
        request = load_json(request_path)
        receipt = load_json(receipt_path)
        if request.get("execution_status") != "prepared_not_applied":
            print("DAW mutation request must not claim an applied Live mutation.", file=sys.stderr)
            return 1
        approval_state = request.get("approval_state", {})
        if approval_state.get("live_set_mutation") != "required_not_granted":
            print("DAW mutation request must require live_set_mutation approval before execution.", file=sys.stderr)
            return 1
        if request.get("track_title") != TRACK_TITLE or receipt.get("track_slug") != TRACK_SLUG:
            print("DAW mutation receipt must mirror selected track identity.", file=sys.stderr)
            return 1
        if receipt.get("required_postflight_checks") != package["receipt_contract"]["required_postflight_checks"]:
            print("Receipt template must mirror the package postflight contract.", file=sys.stderr)
            return 1
        assert_no_sensitive_paths(request, "mutation request")
        assert_no_sensitive_paths(receipt, "receipt template")

        bundle_dir = temp_root / "bundle"
        bundle_result = run_command(
            [
                PYTHON,
                "scripts/stage_live12_daw_import_bundle.py",
                "--request",
                str(request_path),
                "--output-dir",
                str(bundle_dir),
                "--stable",
            ]
        )
        if bundle_result.returncode != 0:
            print(bundle_result.stdout, file=sys.stderr)
            print(bundle_result.stderr, file=sys.stderr)
            return bundle_result.returncode
        bundle_root = bundle_dir / TRACK_SLUG
        bundle_manifest_path = bundle_root / "bundle-manifest.json"
        launch_plan_path = bundle_root / "launch-plan.json"
        evidence_template_path = bundle_root / "operator-evidence-template.json"
        staged_midi_path = bundle_root / "midi" / "good-vibrations-in-a-burned-barn.mid"
        for required_path in [bundle_manifest_path, launch_plan_path, evidence_template_path, staged_midi_path]:
            if not required_path.exists():
                print(f"Import bundle missing expected file: {required_path}", file=sys.stderr)
                return 1
        bundle_manifest = load_json(bundle_manifest_path)
        launch_plan = load_json(launch_plan_path)
        evidence_template = load_json(evidence_template_path)
        if bundle_manifest.get("execution_status") != "staged_not_launched":
            print("Import bundle must not claim Ableton was launched.", file=sys.stderr)
            return 1
        if launch_plan.get("launch_status") != "blocked_until_confirm_live_mutation":
            print("Launch plan must require explicit Live mutation confirmation.", file=sys.stderr)
            return 1
        if bundle_manifest.get("midi_staging", {}).get("sha256") != request["midi_verification"]["expected_sha256"]:
            print("Import bundle must preserve the MIDI hash.", file=sys.stderr)
            return 1
        if evidence_template.get("skipped_action_ids") != request["planned_action_ids"]:
            print("Evidence template must account for planned action ids as skipped by default.", file=sys.stderr)
            return 1
        assert_no_sensitive_paths(bundle_manifest, "bundle manifest")
        assert_no_sensitive_paths(launch_plan, "launch plan")
        assert_no_sensitive_paths(evidence_template, "evidence template")

        blocked_launch_result = run_command(
            [
                PYTHON,
                "scripts/stage_live12_daw_import_bundle.py",
                "--request",
                str(request_path),
                "--output-dir",
                str(temp_root / "blocked-launch"),
                "--launch-ableton",
            ]
        )
        if blocked_launch_result.returncode == 0 or "--confirm-live-mutation is required" not in blocked_launch_result.stderr:
            print("Import bundle launcher must reject Ableton launch without explicit confirmation.", file=sys.stderr)
            print(blocked_launch_result.stdout, file=sys.stderr)
            print(blocked_launch_result.stderr, file=sys.stderr)
            return 1

        evidence_path = temp_root / "mutation-evidence.json"
        evidence = {
            "operator_approval_reference": APPROVAL_REFERENCE,
            "rollback_copy_reference": ROLLBACK_REFERENCE,
            "applied_action_ids": [],
            "skipped_action_ids": request["planned_action_ids"],
            "created_artifacts": [
                {
                    "type": "local_ableton_session",
                    "reference": "local-only Ableton set saved outside Git",
                    "git_policy": "not_committed",
                }
            ],
            "postflight_checks": request["required_postflight_checks"],
        }
        write_json(evidence_path, evidence)
        receipt_result = run_command(
            [
                PYTHON,
                "scripts/record_live12_daw_mutation_receipt.py",
                "--request",
                str(request_path),
                "--evidence",
                str(evidence_path),
                "--output",
                str(output_dir / TRACK_SLUG / "applied-receipt.json"),
                "--stable",
            ]
        )
        if receipt_result.returncode != 0:
            print(receipt_result.stdout, file=sys.stderr)
            print(receipt_result.stderr, file=sys.stderr)
            return receipt_result.returncode
        applied_receipt = load_json(output_dir / TRACK_SLUG / "applied-receipt.json")
        if applied_receipt.get("execution_status") != "recorded_from_operator_evidence":
            print("Recorded receipt must use recorded_from_operator_evidence execution status.", file=sys.stderr)
            return 1
        if applied_receipt.get("operator_approval_reference") != APPROVAL_REFERENCE:
            print("Recorded receipt must carry the approval reference.", file=sys.stderr)
            return 1
        if applied_receipt.get("skipped_action_ids") != request["planned_action_ids"]:
            print("Recorded receipt must account for skipped action ids.", file=sys.stderr)
            return 1
        if applied_receipt.get("unaccounted_action_ids") != []:
            print("Recorded receipt must not leave planned action ids unaccounted.", file=sys.stderr)
            return 1
        assert_no_sensitive_paths(applied_receipt, "applied receipt")

        missing_approval_path = temp_root / "missing-approval.json"
        missing_approval = dict(evidence)
        missing_approval["operator_approval_reference"] = ""
        write_json(missing_approval_path, missing_approval)
        missing_approval_result = run_command(
            [
                PYTHON,
                "scripts/record_live12_daw_mutation_receipt.py",
                "--request",
                str(request_path),
                "--evidence",
                str(missing_approval_path),
                "--output",
                str(temp_root / "missing-approval-receipt.json"),
            ]
        )
        if missing_approval_result.returncode == 0 or "operator_approval_reference is required" not in missing_approval_result.stderr:
            print("Receipt recorder must reject missing operator approval.", file=sys.stderr)
            print(missing_approval_result.stdout, file=sys.stderr)
            print(missing_approval_result.stderr, file=sys.stderr)
            return 1

        unknown_action_path = temp_root / "unknown-action.json"
        unknown_action = dict(evidence)
        unknown_action["applied_action_ids"] = ["unknown.action.id"]
        unknown_action["skipped_action_ids"] = request["planned_action_ids"]
        write_json(unknown_action_path, unknown_action)
        unknown_action_result = run_command(
            [
                PYTHON,
                "scripts/record_live12_daw_mutation_receipt.py",
                "--request",
                str(request_path),
                "--evidence",
                str(unknown_action_path),
                "--output",
                str(temp_root / "unknown-action-receipt.json"),
            ]
        )
        if unknown_action_result.returncode == 0 or "unknown action ids" not in unknown_action_result.stderr:
            print("Receipt recorder must reject unknown action ids.", file=sys.stderr)
            print(unknown_action_result.stdout, file=sys.stderr)
            print(unknown_action_result.stderr, file=sys.stderr)
            return 1

        invalid_result = run_command(
            [
                PYTHON,
                "scripts/prepare_live12_daw_mutation.py",
                "--track",
                "missing-track",
                "--package",
                str(package_path),
                "--output-dir",
                str(temp_root / "invalid"),
            ]
        )
        if invalid_result.returncode == 0 or "Unknown track slug" not in invalid_result.stderr:
            print("DAW mutation preflight must reject unknown track slugs.", file=sys.stderr)
            print(invalid_result.stdout, file=sys.stderr)
            print(invalid_result.stderr, file=sys.stderr)
            return 1

    print("Live 12 DAW mutation preflight probes passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
