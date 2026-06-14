#!/usr/bin/env python3
"""Regression probes for the generated Live 12 DAW mutation operator runbook."""

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
COMMITTED_JSON = ROOT / "automation" / "generated" / "live12-daw-mutation-runbook.json"
COMMITTED_MARKDOWN = ROOT / "docs" / "live12-daw-mutation-runbook.md"
EXPECTED_SOURCE_FILES = [
    "automation/generated/live12-daw-mutation-package.json",
    "automation/generated/live12-daw-action-plan.json",
    "automation/generated/max-for-live-device-contracts.json",
]
EXPECTED_PHASE_ORDER = [
    "preflight",
    "stage_import_bundle",
    "apply_live_mutation",
    "record_receipt",
    "postflight",
]
EXPECTED_TRACK_SLUGS = [
    "good-vibrations-in-a-burned-barn",
    "a-p-carter-in-the-warehouse",
    "no-gods-no-masters-no-quantize",
    "possum-kingdom-afterhours",
    "the-ballad-of-the-broken-controller",
]
BLOCKED_BINARY_EXTENSIONS = (".als", ".amxd", ".alp", ".wav", ".aiff", ".flac", ".mp3", ".m4a", ".ogg")


def run_command(args: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=False, capture_output=True, text=True)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def expected_track_slugs(package_jobs: list[dict[str, Any]]) -> list[str]:
    source_order = [*EXPECTED_TRACK_SLUGS]
    source_order.extend(
        job["track_slug"]
        for job in package_jobs
        if job.get("track_slug") and job["track_slug"] not in source_order
    )
    return source_order


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


def assert_markdown_clean(markdown: str) -> None:
    if "/Users/" in markdown:
        raise AssertionError("runbook markdown leaked an absolute user path")
    if "sources/public-domain/raw/" in markdown:
        raise AssertionError("runbook markdown leaked a raw public-domain source path")
    for token in markdown.split():
        normalized_token = token.strip("`.,)")
        if "/" in token and normalized_token.endswith(BLOCKED_BINARY_EXTENSIONS):
            raise AssertionError(f"runbook markdown carried a blocked binary/audio artifact path: {token}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="live12-daw-mutation-runbook-test-") as temp_dir:
        temp_root = Path(temp_dir)
        generated_json = temp_root / "live12-daw-mutation-runbook.json"
        generated_markdown = temp_root / "live12-daw-mutation-runbook.md"
        render_result = run_command(
            [
                PYTHON,
                "scripts/render_live12_daw_mutation_runbook.py",
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
        max_contracts = load_json(ROOT / "automation" / "generated" / "max-for-live-device-contracts.json")
        expected_device_ids = [device["id"] for device in max_contracts["devices"]]
        package_jobs_by_slug = {job["track_slug"]: job for job in package["jobs"]}
        expected_slugs = expected_track_slugs(package["jobs"])

        if generated_json.read_text(encoding="utf-8") != COMMITTED_JSON.read_text(encoding="utf-8"):
            print(diff_text(COMMITTED_JSON, generated_json), file=sys.stderr)
            return 1
        if generated_markdown.read_text(encoding="utf-8") != COMMITTED_MARKDOWN.read_text(encoding="utf-8"):
            print(diff_text(COMMITTED_MARKDOWN, generated_markdown), file=sys.stderr)
            return 1

        if runbook.get("schema_version") != 1:
            print("DAW mutation runbook must use schema_version 1.", file=sys.stderr)
            return 1
        if runbook.get("execution_status") != "operator_runbook_not_applied":
            print("DAW mutation runbook must not claim a Live mutation was applied.", file=sys.stderr)
            return 1
        if runbook.get("source_files") != EXPECTED_SOURCE_FILES:
            print("DAW mutation runbook source files changed unexpectedly.", file=sys.stderr)
            return 1
        approval_policy = runbook.get("approval_policy", {})
        if approval_policy.get("status") != "blocked_until_operator_approval_and_rollback_reference":
            print("DAW mutation runbook must stay blocked until approval and rollback evidence exist.", file=sys.stderr)
            return 1
        if approval_policy.get("required_cli_flags") != [
            "--launch-ableton",
            "--confirm-live-mutation",
            "--operator-approval-reference",
            "--rollback-copy-reference",
        ]:
            print("DAW mutation runbook must document the exact Ableton launch approval flags.", file=sys.stderr)
            return 1

        tracks = runbook.get("tracks", [])
        if [track.get("track_slug") for track in tracks] != expected_slugs:
            print("DAW mutation runbook must preserve mutation package track order.", file=sys.stderr)
            return 1
        if runbook.get("track_count") != len(expected_slugs):
            print("DAW mutation runbook must summarize the generated track count.", file=sys.stderr)
            return 1

        for index, track in enumerate(tracks, start=1):
            slug = track["track_slug"]
            package_job = package_jobs_by_slug[slug]
            if track.get("queue_order") != index:
                print("DAW mutation runbook track queue_order must be one-based and ordered.", file=sys.stderr)
                return 1
            if track.get("operator_phase_order") != EXPECTED_PHASE_ORDER:
                print("DAW mutation runbook must expose the expected operator phase order.", file=sys.stderr)
                return 1
            if track.get("planned_action_count") != package_job["mutation_action_count"]:
                print("DAW mutation runbook planned_action_count must mirror the mutation package.", file=sys.stderr)
                return 1
            if track.get("max_for_live_device_ids") != expected_device_ids:
                print("DAW mutation runbook must include ordered Max for Live device ids for each track.", file=sys.stderr)
                return 1
            if track.get("source_deck_policy", {}).get("default_state") != "muted_until_human_provenance_review":
                print("DAW mutation runbook must keep the Public Domain Source Deck muted by default.", file=sys.stderr)
                return 1
            commands = track.get("commands", {})
            if commands.get("preflight", [])[:3] != ["python3", "scripts/prepare_live12_daw_mutation.py", "--track"]:
                print("DAW mutation runbook must include the per-track preflight command.", file=sys.stderr)
                return 1
            launch_command = commands.get("apply_live_mutation", [])
            for required in [
                "--launch-ableton",
                "--confirm-live-mutation",
                "--operator-approval-reference",
                "<approval-id>",
                "--rollback-copy-reference",
                "<rollback-note>",
            ]:
                if required not in launch_command:
                    print(f"DAW mutation runbook launch command missing {required}.", file=sys.stderr)
                    return 1
            receipt_command = commands.get("record_receipt", [])
            if "scripts/record_live12_daw_mutation_receipt.py" not in receipt_command:
                print("DAW mutation runbook must include the receipt recording command.", file=sys.stderr)
                return 1

        markdown = generated_markdown.read_text(encoding="utf-8")
        for required_text in [
            "# Live 12 DAW Mutation Runbook",
            "Do not commit Ableton sets, Max devices, source audio, renders, credentials, cookies, or license files.",
            "## Track Queue",
            "Good Vibrations in a Burned Barn",
            "python3 scripts/prepare_live12_daw_mutation_queue.py",
            "--confirm-live-mutation",
            "Public Domain Source Deck remains muted",
        ]:
            if required_text not in markdown:
                print(f"DAW mutation runbook markdown missing: {required_text}", file=sys.stderr)
                return 1

        assert_no_sensitive_paths(runbook, "DAW mutation runbook")
        assert_markdown_clean(markdown)

    print("Live 12 DAW mutation runbook probes passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
