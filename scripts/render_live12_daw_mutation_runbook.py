#!/usr/bin/env python3
"""Render a deterministic operator runbook for local Live 12 DAW mutations."""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "automation" / "generated" / "live12-daw-mutation-runbook.json"
DEFAULT_MARKDOWN_OUTPUT = ROOT / "docs" / "live12-daw-mutation-runbook.md"
STABLE_GENERATED_AT = "1970-01-01T00:00:00Z"

SOURCE_FILES = [
    "automation/generated/live12-daw-mutation-package.json",
    "automation/generated/live12-daw-action-plan.json",
    "automation/generated/max-for-live-device-contracts.json",
]
PHASE_ORDER = [
    "preflight",
    "stage_import_bundle",
    "apply_live_mutation",
    "record_receipt",
    "postflight",
]
REQUIRED_LAUNCH_FLAGS = [
    "--launch-ableton",
    "--confirm-live-mutation",
    "--operator-approval-reference",
    "--rollback-copy-reference",
]


def read_json(relative_path: str) -> dict[str, Any]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def command_line(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


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


def build_commands(track_slug: str) -> dict[str, list[str]]:
    request_path = f"output/daw-mutations/{track_slug}/mutation-request.json"
    evidence_path = f"output/daw-mutations/{track_slug}/operator-evidence.json"
    return {
        "preflight": [
            "python3",
            "scripts/prepare_live12_daw_mutation.py",
            "--track",
            track_slug,
        ],
        "stage_import_bundle": [
            "python3",
            "scripts/stage_live12_daw_import_bundle.py",
            "--request",
            request_path,
        ],
        "apply_live_mutation": [
            "python3",
            "scripts/stage_live12_daw_import_bundle.py",
            "--request",
            request_path,
            "--launch-ableton",
            "--confirm-live-mutation",
            "--operator-approval-reference",
            "<approval-id>",
            "--rollback-copy-reference",
            "<rollback-note>",
        ],
        "record_receipt": [
            "python3",
            "scripts/record_live12_daw_mutation_receipt.py",
            "--request",
            request_path,
            "--evidence",
            evidence_path,
        ],
    }


def build_track_entry(
    job: dict[str, Any],
    max_contracts: dict[str, Any],
    postflight_checks: list[str],
    queue_order: int,
) -> dict[str, Any]:
    max_devices = max_devices_for_job(job, max_contracts)
    return {
        "queue_order": queue_order,
        "track_slug": job["track_slug"],
        "track_title": job["track_title"],
        "execution_status": "not_applied",
        "operator_phase_order": PHASE_ORDER,
        "planned_action_count": job["mutation_action_count"],
        "approval_required_before_execution": job["approval_required_before_execution"],
        "blocked_action_groups": job["blocked_action_groups"],
        "affected_tracks": job["affected_tracks"],
        "affected_returns": job["affected_returns"],
        "midi_artifact": job["midi_artifact"],
        "source_deck_policy": job["source_deck_policy"],
        "max_for_live_device_ids": [device["id"] for device in max_devices],
        "max_for_live_devices": max_devices,
        "commands": build_commands(job["track_slug"]),
        "operator_evidence": {
            "template_path": f"output/daw-import-bundles/{job['track_slug']}/operator-evidence-template.json",
            "local_evidence_path": f"output/daw-mutations/{job['track_slug']}/operator-evidence.json",
            "receipt_output_path": f"output/daw-mutations/{job['track_slug']}/applied-receipt.json",
            "required_reference_fields": [
                "operator_approval_reference",
                "rollback_copy_reference",
            ],
        },
        "postflight_checks": postflight_checks,
    }


def render(stable: bool = False) -> dict[str, Any]:
    package = read_json("automation/generated/live12-daw-mutation-package.json")
    daw_plan = read_json("automation/generated/live12-daw-action-plan.json")
    max_contracts = read_json("automation/generated/max-for-live-device-contracts.json")
    postflight_checks = package["receipt_contract"]["required_postflight_checks"]
    tracks = [
        build_track_entry(job, max_contracts, postflight_checks, queue_order)
        for queue_order, job in enumerate(package.get("jobs", []), start=1)
    ]
    return {
        "schema_version": 1,
        "generated_at": STABLE_GENERATED_AT if stable else utc_now(),
        "generator": "scripts/render_live12_daw_mutation_runbook.py",
        "source_files": SOURCE_FILES,
        "source_file_sha256": {relative_path: sha256_file(ROOT / relative_path) for relative_path in SOURCE_FILES},
        "purpose": "Operator-facing runbook for applying approved local Ableton Live 12 / Max for Live mutation jobs without committing DAW binaries or audio artifacts.",
        "execution_status": "operator_runbook_not_applied",
        "composition_set": package.get("composition_set"),
        "live_template": daw_plan.get("live_template", {}),
        "track_count": len(tracks),
        "total_planned_action_count": sum(track["planned_action_count"] for track in tracks),
        "queue_command": [
            "python3",
            "scripts/prepare_live12_daw_mutation_queue.py",
        ],
        "approval_policy": {
            "status": "blocked_until_operator_approval_and_rollback_reference",
            "required_cli_flags": REQUIRED_LAUNCH_FLAGS,
            "approval_gates": package["safety"]["requires_operator_approval_before_execution"],
            "must_not": package["safety"]["must_not"],
        },
        "artifact_policy": {
            "git_policy": "text_contracts_only",
            "local_output_roots": [
                "output/daw-mutations",
                "output/daw-import-bundles",
                "output/daw-mutation-queue",
            ],
            "must_not_commit": [
                "Ableton Live sets",
                "compiled Max for Live devices",
                "source audio",
                "renders",
                "credentials",
                "cookies",
                "license files",
            ],
        },
        "phase_contract": [
            {
                "id": "preflight",
                "operator_goal": "Create the local mutation request and receipt template, then verify MIDI hashes before touching Live.",
            },
            {
                "id": "stage_import_bundle",
                "operator_goal": "Copy the generated MIDI sketch into an ignored import bundle and inspect the launch plan.",
            },
            {
                "id": "apply_live_mutation",
                "operator_goal": "Launch Ableton only after approval and rollback references are ready.",
            },
            {
                "id": "record_receipt",
                "operator_goal": "Record what was applied, skipped, created, and redacted from operator evidence.",
            },
            {
                "id": "postflight",
                "operator_goal": "Run repository validation and confirm no DAW binaries, source audio, renders, or credentials entered Git.",
            },
        ],
        "tracks": tracks,
    }


def render_markdown(runbook: dict[str, Any]) -> str:
    lines = [
        "# Live 12 DAW Mutation Runbook",
        "",
        f"Generated by `{runbook['generator']}` from the committed mutation contracts.",
        "",
        "Status: `operator_runbook_not_applied`.",
        "",
        "Do not commit Ableton sets, Max devices, source audio, renders, credentials, cookies, or license files.",
        "",
        "## Queue Preparation",
        "",
        "Run the full queue staging command when preparing the whole set:",
        "",
        "```bash",
        command_line(runbook["queue_command"]),
        "```",
        "",
        "All Ableton launches remain blocked until the launch command includes `--launch-ableton`, `--confirm-live-mutation`, `--operator-approval-reference`, and `--rollback-copy-reference`.",
        "",
        "Public Domain Source Deck remains muted until provenance review.",
        "",
        "## Approval Boundary",
        "",
    ]
    for gate in runbook["approval_policy"]["approval_gates"]:
        lines.append(f"- {gate}")
    lines.extend(
        [
            "",
            "## Phase Contract",
            "",
        ]
    )
    for phase in runbook["phase_contract"]:
        lines.append(f"- `{phase['id']}`: {phase['operator_goal']}")
    lines.extend(["", "## Track Queue", ""])
    for track in runbook["tracks"]:
        lines.extend(
            [
                f"### {track['queue_order']}. {track['track_title']}",
                "",
                f"- Track slug: `{track['track_slug']}`",
                f"- Planned actions: `{track['planned_action_count']}`",
                f"- Affected tracks: `{len(track['affected_tracks'])}`",
                f"- Max for Live source devices: `{len(track['max_for_live_device_ids'])}`",
                f"- Source deck state: `{track['source_deck_policy']['default_state']}`",
                "",
                "Preflight:",
                "",
                "```bash",
                command_line(track["commands"]["preflight"]),
                "```",
                "",
                "Stage import bundle:",
                "",
                "```bash",
                command_line(track["commands"]["stage_import_bundle"]),
                "```",
                "",
                "Apply Live mutation after approval and rollback evidence:",
                "",
                "```bash",
                command_line(track["commands"]["apply_live_mutation"]),
                "```",
                "",
                "Record receipt:",
                "",
                "```bash",
                command_line(track["commands"]["record_receipt"]),
                "```",
                "",
                "Max for Live source devices:",
                "",
            ]
        )
        for device in track["max_for_live_devices"]:
            lines.append(f"- `{device['id']}` on {', '.join(device['target_tracks'])}")
        lines.extend(["", "Postflight checks:", ""])
        for check in track["postflight_checks"]:
            lines.append(f"- {check}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON path.")
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT, help="Output Markdown runbook path.")
    parser.add_argument("--stable", action="store_true", help="Use deterministic generated_at value.")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = render(stable=args.stable)
    markdown = render_markdown(data)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "schema_version": data["schema_version"],
                    "track_count": data["track_count"],
                    "generated_at": data["generated_at"],
                    "execution_status": data["execution_status"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(markdown, encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"Wrote {args.markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
