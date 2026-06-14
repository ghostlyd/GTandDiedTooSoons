#!/usr/bin/env python3
"""Render a deterministic Live 12 DAW mutation queue operator runbook."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "automation" / "generated" / "live12-daw-mutation-queue-runbook.json"
DEFAULT_MARKDOWN_OUTPUT = ROOT / "docs" / "live12-daw-mutation-queue-runbook.md"
STABLE_GENERATED_AT = "1970-01-01T00:00:00Z"

SOURCE_FILES = [
    "automation/generated/live12-daw-mutation-package.json",
    "automation/generated/max-for-live-device-contracts.json",
    "scripts/prepare_live12_daw_mutation_queue.py",
    "scripts/stage_live12_daw_import_bundle.py",
    "scripts/record_live12_daw_mutation_receipt.py",
]

PREPARE_QUEUE_COMMAND = [
    "python3",
    "scripts/prepare_live12_daw_mutation_queue.py",
    "--stable",
]


def read_json(relative_path: str) -> dict[str, Any]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


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


def path_for_slug(root: str, slug: str, filename: str) -> str:
    return str(Path(root) / slug / filename)


def midi_staged_path(job: dict[str, Any]) -> str:
    midi_name = Path(job["midi_artifact"]["path"]).name
    return str(Path("output/daw-import-bundles") / job["track_slug"] / "midi" / midi_name)


def max_devices_for_job(job: dict[str, Any], max_contracts: dict[str, Any]) -> list[str]:
    affected_tracks = set(job.get("affected_tracks", []))
    track_slug = job["track_slug"]
    device_ids = []
    for device in max_contracts.get("devices", []):
        target_tracks = set(device.get("target_tracks", []))
        track_slugs = set(device.get("track_slugs", []))
        if track_slug in track_slugs or affected_tracks.intersection(target_tracks):
            device_ids.append(device["id"])
    return device_ids


def track_entry(job: dict[str, Any], max_contracts: dict[str, Any]) -> dict[str, Any]:
    slug = job["track_slug"]
    mutation_request = path_for_slug("output/daw-mutations", slug, "mutation-request.json")
    operator_evidence = path_for_slug("output/daw-mutations", slug, "operator-evidence.json")
    staged_request = path_for_slug("output/daw-import-bundles", slug, "mutation-request.json")
    bundle_manifest = path_for_slug("output/daw-import-bundles", slug, "bundle-manifest.json")
    launch_plan = path_for_slug("output/daw-import-bundles", slug, "launch-plan.json")
    applied_receipt = path_for_slug("output/daw-import-bundles", slug, "applied-receipt.json")
    return {
        "track_slug": slug,
        "track_title": job["track_title"],
        "execution_mode": job["execution_mode"],
        "planned_action_count": len(job.get("executable_action_ids", [])),
        "approval_gates_required": job.get("approval_gates_required", []),
        "blocked_action_groups": job.get("blocked_action_groups", []),
        "request_path": mutation_request,
        "receipt_template_path": path_for_slug("output/daw-mutations", slug, "receipt-template.json"),
        "operator_evidence_path": operator_evidence,
        "bundle_manifest_path": bundle_manifest,
        "launch_plan_path": launch_plan,
        "staged_midi_path": midi_staged_path(job),
        "prepare_track_command": [
            "python3",
            "scripts/prepare_live12_daw_mutation.py",
            "--track",
            slug,
            "--stable",
        ],
        "stage_bundle_command": [
            "python3",
            "scripts/stage_live12_daw_import_bundle.py",
            "--request",
            mutation_request,
            "--stable",
        ],
        "gated_launch_command": [
            "python3",
            "scripts/stage_live12_daw_import_bundle.py",
            "--request",
            mutation_request,
            "--launch-ableton",
            "--confirm-live-mutation",
            "--operator-approval-reference",
            "<approval-ref>",
            "--rollback-copy-reference",
            "<rollback-copy-ref>",
        ],
        "receipt_command": [
            "python3",
            "scripts/record_live12_daw_mutation_receipt.py",
            "--request",
            staged_request,
            "--evidence",
            operator_evidence,
            "--output",
            applied_receipt,
        ],
        "max_for_live_device_ids": max_devices_for_job(job, max_contracts),
    }


def render(stable: bool = False) -> dict[str, Any]:
    package = read_json("automation/generated/live12-daw-mutation-package.json")
    max_contracts = read_json("automation/generated/max-for-live-device-contracts.json")
    tracks = [track_entry(job, max_contracts) for job in package.get("jobs", [])]
    return {
        "schema_version": 1,
        "generated_at": STABLE_GENERATED_AT if stable else utc_now(),
        "generator": "scripts/render_live12_daw_mutation_queue_runbook.py",
        "source_files": SOURCE_FILES,
        "source_file_sha256": {relative_path: sha256_file(ROOT / relative_path) for relative_path in SOURCE_FILES},
        "purpose": "Operator runbook for preparing local-only Ableton Live 12 / Max for Live mutation queues without automatic DAW launch.",
        "queue_policy": {
            "execution_status": "queued_not_launched",
            "launch_status": "blocked_until_per_track_confirm_live_mutation",
            "git_policy": "ignored_local_only",
            "artifact_roots": [
                "output/daw-mutations",
                "output/daw-import-bundles",
                "output/daw-mutation-queue",
            ],
            "must_not_commit": [
                "Ableton sets",
                "compiled Max for Live devices",
                "rendered audio",
                "raw source audio",
                "credentials",
                "cookies",
                "license files",
            ],
        },
        "prepare_queue_command": PREPARE_QUEUE_COMMAND,
        "queue_manifest_path": "output/daw-mutation-queue/queue-manifest.json",
        "receipt_contract": package["receipt_contract"],
        "max_for_live_device_count": max_contracts["device_count"],
        "track_count": len(tracks),
        "total_planned_action_count": sum(track["planned_action_count"] for track in tracks),
        "tracks": tracks,
    }


def render_markdown(runbook: dict[str, Any]) -> str:
    prepare_command = " ".join(runbook["prepare_queue_command"])
    lines = [
        "# Live 12 DAW Mutation Queue Runbook",
        "",
        "Generated operator handoff for local-only Ableton Live 12 / Max for Live DAW mutation queues.",
        "",
        f"Status: `{runbook['queue_policy']['execution_status']}`.",
        "",
        "Do not commit Ableton sets, Max devices, rendered audio, raw source audio, credentials, cookies, or license files.",
        "",
        "## Queue Preparation",
        "",
        "```bash",
        prepare_command,
        "```",
        "",
        f"Queue manifest: `{runbook['queue_manifest_path']}`",
        "",
        "## Track Commands",
        "",
    ]
    for track in runbook["tracks"]:
        lines.extend(
            [
                f"### {track['track_title']}",
                "",
                f"- Track slug: `{track['track_slug']}`",
                f"- Planned action count: `{track['planned_action_count']}`",
                f"- Request: `{track['request_path']}`",
                f"- Bundle manifest: `{track['bundle_manifest_path']}`",
                f"- Launch plan: `{track['launch_plan_path']}`",
                f"- Max for Live devices: {', '.join(f'`{device_id}`' for device_id in track['max_for_live_device_ids'])}",
                "",
                "Stage bundle:",
                "",
                "```bash",
                " ".join(track["stage_bundle_command"]),
                "```",
                "",
                "Gated Ableton launch:",
                "",
                "```bash",
                " ".join(track["gated_launch_command"]),
                "```",
                "",
                "Record receipt:",
                "",
                "```bash",
                " ".join(track["receipt_command"]),
                "```",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON path.")
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT, help="Output Markdown path.")
    parser.add_argument("--stable", action="store_true", help="Use deterministic generated_at value.")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing outputs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runbook = render(stable=args.stable)
    markdown = render_markdown(runbook)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "schema_version": runbook["schema_version"],
                    "execution_status": runbook["queue_policy"]["execution_status"],
                    "track_count": runbook["track_count"],
                    "total_planned_action_count": runbook["total_planned_action_count"],
                    "generated_at": runbook["generated_at"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    output = args.output if args.output.is_absolute() else ROOT / args.output
    markdown_output = args.markdown_output if args.markdown_output.is_absolute() else ROOT / args.markdown_output
    write_json(output, runbook)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(markdown, encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Wrote {markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
