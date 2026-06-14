#!/usr/bin/env python3
"""Regression probes for the generated Live 12 DAW mutation queue runbook."""

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
COMMITTED_JSON = ROOT / "automation" / "generated" / "live12-daw-mutation-queue-runbook.json"
COMMITTED_MARKDOWN = ROOT / "docs" / "live12-daw-mutation-queue-runbook.md"
EXPECTED_SOURCE_FILES = [
    "automation/generated/live12-daw-mutation-package.json",
    "automation/generated/max-for-live-device-contracts.json",
    "scripts/prepare_live12_daw_mutation_queue.py",
    "scripts/stage_live12_daw_import_bundle.py",
    "scripts/record_live12_daw_mutation_receipt.py",
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
    with tempfile.TemporaryDirectory(prefix="live12-daw-mutation-queue-runbook-test-") as temp_dir:
        temp_root = Path(temp_dir)
        generated_json = temp_root / "live12-daw-mutation-queue-runbook.json"
        generated_markdown = temp_root / "live12-daw-mutation-queue-runbook.md"
        render_result = run_command(
            [
                PYTHON,
                "scripts/render_live12_daw_mutation_queue_runbook.py",
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

        runbook = load_json(generated_json)
        package = load_json(ROOT / "automation" / "generated" / "live12-daw-mutation-package.json")
        package_jobs = package.get("jobs", [])

        if generated_json.read_text(encoding="utf-8") != COMMITTED_JSON.read_text(encoding="utf-8"):
            print(diff_text(COMMITTED_JSON, generated_json), file=sys.stderr)
            return 1
        if generated_markdown.read_text(encoding="utf-8") != COMMITTED_MARKDOWN.read_text(encoding="utf-8"):
            print(diff_text(COMMITTED_MARKDOWN, generated_markdown), file=sys.stderr)
            return 1

        if runbook.get("schema_version") != 1:
            print("Queue runbook must use schema_version 1.", file=sys.stderr)
            return 1
        if runbook.get("source_files") != EXPECTED_SOURCE_FILES:
            print("Queue runbook source files changed unexpectedly.", file=sys.stderr)
            return 1

        queue_policy = runbook.get("queue_policy", {})
        if queue_policy.get("execution_status") != "queued_not_launched":
            print("Queue runbook must stay queued_not_launched.", file=sys.stderr)
            return 1
        if queue_policy.get("launch_status") != "blocked_until_per_track_confirm_live_mutation":
            print("Queue runbook must block Ableton launches until per-track confirmation.", file=sys.stderr)
            return 1
        if "--launch-ableton" in runbook.get("prepare_queue_command", []):
            print("Queue preparation command must not launch Ableton.", file=sys.stderr)
            return 1

        tracks = runbook.get("tracks", [])
        if runbook.get("track_count") != len(package_jobs) or len(tracks) != len(package_jobs):
            print("Queue runbook must contain one entry per mutation package job.", file=sys.stderr)
            return 1
        if [track.get("track_slug") for track in tracks] != [job.get("track_slug") for job in package_jobs]:
            print("Queue runbook must preserve mutation package track order.", file=sys.stderr)
            return 1

        package_jobs_by_slug = {job["track_slug"]: job for job in package_jobs}
        for track in tracks:
            track_slug = track["track_slug"]
            job = package_jobs_by_slug[track_slug]
            if track.get("planned_action_count") != len(job.get("executable_action_ids", [])):
                print(f"Queue runbook planned action count is stale: {track_slug}", file=sys.stderr)
                return 1
            for path_field in ["request_path", "bundle_manifest_path", "launch_plan_path", "operator_evidence_path"]:
                value = track.get(path_field, "")
                if not isinstance(value, str) or not value.startswith("output/"):
                    print(f"Queue runbook {path_field} must point at ignored output/: {track_slug}", file=sys.stderr)
                    return 1
            launch_command = track.get("gated_launch_command", [])
            for required_arg in [
                "--launch-ableton",
                "--confirm-live-mutation",
                "--operator-approval-reference",
                "--rollback-copy-reference",
            ]:
                if required_arg not in launch_command:
                    print(f"Queue runbook gated launch missing {required_arg}: {track_slug}", file=sys.stderr)
                    return 1
            receipt_command = track.get("receipt_command", [])
            if receipt_command[:2] != ["python3", "scripts/record_live12_daw_mutation_receipt.py"]:
                print(f"Queue runbook receipt command is stale: {track_slug}", file=sys.stderr)
                return 1
            if not track.get("max_for_live_device_ids"):
                print(f"Queue runbook must include Max for Live device ids: {track_slug}", file=sys.stderr)
                return 1

        markdown = generated_markdown.read_text(encoding="utf-8")
        for required_text in [
            "# Live 12 DAW Mutation Queue Runbook",
            "queued_not_launched",
            "python3 scripts/prepare_live12_daw_mutation_queue.py --stable",
            "Rail Yard Ghost in the Control Room",
            "Do not commit Ableton sets, Max devices, rendered audio, raw source audio, credentials, cookies, or license files.",
        ]:
            if required_text not in markdown:
                print(f"Queue runbook markdown missing: {required_text}", file=sys.stderr)
                return 1

        assert_no_sensitive_paths(runbook, "queue runbook")
        assert_no_sensitive_paths({"markdown": markdown}, "queue runbook markdown")

    print("Live 12 DAW mutation queue runbook probes passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
