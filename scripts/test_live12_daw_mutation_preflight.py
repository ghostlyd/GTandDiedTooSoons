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
