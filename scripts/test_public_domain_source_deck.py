#!/usr/bin/env python3
"""Regression probes for the generated public-domain source deck manifest."""

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
COMMITTED_JSON = ROOT / "automation" / "generated" / "public-domain-source-deck.json"
COMMITTED_MARKDOWN = ROOT / "docs" / "public-domain-source-deck.md"
EXPECTED_SOURCE_FILES = [
    "catalogs/public-domain-bluegrass-sources.json",
    "sources/public-domain/download-ledger.json",
    "automation/generated/live12-daw-action-plan.json",
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


def expected_track_slugs(action_plan: dict[str, Any]) -> list[str]:
    source_order = [*EXPECTED_TRACK_SLUGS]
    source_order.extend(
        track["slug"]
        for track in action_plan.get("tracks", [])
        if track.get("slug") and track["slug"] not in source_order
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


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="public-domain-source-deck-test-") as temp_dir:
        temp_root = Path(temp_dir)
        generated_json = temp_root / "public-domain-source-deck.json"
        generated_markdown = temp_root / "public-domain-source-deck.md"
        render_result = run_command(
            [
                PYTHON,
                "scripts/render_public_domain_source_deck.py",
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

        deck = load_json(generated_json)
        action_plan = load_json(ROOT / "automation" / "generated" / "live12-daw-action-plan.json")
        ledger = load_json(ROOT / "sources" / "public-domain" / "download-ledger.json")
        ledger_ids = [record["source_id"] for record in ledger["downloads"]]

        if generated_json.read_text(encoding="utf-8") != COMMITTED_JSON.read_text(encoding="utf-8"):
            print(diff_text(COMMITTED_JSON, generated_json), file=sys.stderr)
            return 1
        if generated_markdown.read_text(encoding="utf-8") != COMMITTED_MARKDOWN.read_text(encoding="utf-8"):
            print(diff_text(COMMITTED_MARKDOWN, generated_markdown), file=sys.stderr)
            return 1

        if deck.get("schema_version") != 1:
            print("Public-domain source deck must use schema_version 1.", file=sys.stderr)
            return 1
        if deck.get("source_files") != EXPECTED_SOURCE_FILES:
            print("Public-domain source deck source files changed unexpectedly.", file=sys.stderr)
            return 1
        if deck.get("deck_policy", {}).get("default_state") != "muted_until_human_provenance_review":
            print("Public-domain source deck must remain muted by default.", file=sys.stderr)
            return 1
        if deck.get("deck_policy", {}).get("approval_gate") != "live_set_mutation":
            print("Public-domain source deck must require live_set_mutation approval.", file=sys.stderr)
            return 1
        artifact_policy = deck.get("artifact_policy", {})
        if artifact_policy.get("git_policy") != "metadata_only_no_raw_audio":
            print("Public-domain source deck must use metadata_only_no_raw_audio git policy.", file=sys.stderr)
            return 1
        if "raw source audio" not in artifact_policy.get("must_not_commit", []):
            print("Public-domain source deck must block raw source audio commits.", file=sys.stderr)
            return 1

        approved_sources = deck.get("approved_sources", [])
        if deck.get("approved_source_count") != len(ledger_ids) or [source["source_id"] for source in approved_sources] != ledger_ids:
            print("Public-domain source deck approved sources must mirror the download ledger order.", file=sys.stderr)
            return 1
        for source in approved_sources:
            for field in ["source_id", "name", "rights_status", "sha256", "byte_size", "credit_line", "project_use", "rights_evidence", "browser_evidence"]:
                if source.get(field) in ("", None):
                    print(f"Public-domain source deck source missing {field}: {source.get('source_id')}", file=sys.stderr)
                    return 1
            if source.get("rights_status") != "public_domain":
                print("Public-domain source deck approved sources must be public_domain.", file=sys.stderr)
                return 1
            if "download_url" in source or "local_file" in source or "final_url" in source:
                print("Public-domain source deck must not expose raw download or local file fields.", file=sys.stderr)
                return 1

        track_assignments = deck.get("track_assignments", [])
        if [track["track_slug"] for track in track_assignments] != expected_track_slugs(action_plan):
            print("Public-domain source deck must preserve DAW action-plan track order.", file=sys.stderr)
            return 1
        action_tracks = {track["slug"]: track for track in action_plan["tracks"]}
        for assignment in track_assignments:
            source_deck = action_tracks[assignment["track_slug"]]["source_deck"]
            expected_ids = [candidate["source_id"] for candidate in source_deck["candidate_sources"]]
            if assignment.get("candidate_source_ids") != expected_ids:
                print("Public-domain source deck track assignment must mirror action-plan candidates.", file=sys.stderr)
                return 1
            if assignment.get("deck_state") != source_deck["default_state"]:
                print("Public-domain source deck track assignment must mirror source deck default state.", file=sys.stderr)
                return 1
            if assignment.get("required_before_unmute") != source_deck["required_checks"]:
                print("Public-domain source deck unmute requirements must mirror the action plan.", file=sys.stderr)
                return 1

        markdown = generated_markdown.read_text(encoding="utf-8")
        for required_text in [
            "# Public-Domain Source Deck",
            "metadata only",
            "muted_until_human_provenance_review",
            "Devil's dream reel - excerpt 001",
            "Good Vibrations in a Burned Barn",
            "raw source audio must remain outside Git",
        ]:
            if required_text not in markdown:
                print(f"Public-domain source deck markdown missing: {required_text}", file=sys.stderr)
                return 1

        assert_no_sensitive_paths(deck, "public-domain source deck")
        assert_no_sensitive_paths({"markdown": markdown}, "public-domain source deck markdown")

    print("Public-domain source deck probes passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
