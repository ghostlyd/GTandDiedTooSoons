#!/usr/bin/env python3
"""Render a deterministic OpenAI production swarm queue from repo manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "automation" / "generated" / "openai-production-swarm-queue.json"
DEFAULT_MARKDOWN_OUTPUT = ROOT / "docs" / "openai-production-swarm-queue.md"
STABLE_GENERATED_AT = "1970-01-01T00:00:00Z"

SOURCE_FILES = [
    "automation/openai-production-orchestration.json",
    "automation/worker-chain.json",
    "automation/generated/openai-worker-briefs.json",
    "automation/generated/live12-daw-mutation-package.json",
    "automation/generated/live12-daw-mutation-queue-runbook.json",
    "automation/generated/public-domain-source-deck.json",
    "compositions/generated/live12-track-build-plans.json",
]

GLOBAL_TASK_MUST_NOT = [
    "call OpenAI APIs from CI",
    "include private rehearsal audio",
    "include unreleased lyrics",
    "read credentials, cookies, license files, or account artifacts",
    "mutate Ableton Live, Max for Live, vendor accounts, exports, or releases without approval evidence",
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


def ordered_unique(values: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def lookup_by(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {item[key]: item for item in items if item.get(key)}


def role_instruction(role_id: str, track: dict[str, Any]) -> str:
    title = track["title"]
    instructions = {
        "archivist": f"Review public-domain source candidates and historical motif notes for {title}; return rights/provenance notes and unresolved risks only.",
        "controller_engineer": f"Map AeroBand banjo-controller performance constraints for {title}; return controller and MIDI articulation proposals only.",
        "max_device_builder": f"Translate {title} device needs into Max for Live source-contract work items; return source-only patch notes and automation targets.",
        "arrangement_producer": f"Refine {title} arrangement tension, hook density, and bluegrass/electronic/punk balance; return structured arrangement deltas.",
        "mix_engineer": f"Prepare {title} mix translation and spatial review notes; return checklist items and problem-frequency hypotheses, not audio.",
        "release_qa": f"Gate {title} for provenance, CI, source credits, export readiness, and residual risk; return release blockers and required evidence.",
    }
    return instructions.get(role_id, f"Produce a role-scoped metadata-only production brief for {title}.")


def task_packet(
    track: dict[str, Any],
    build_plan: dict[str, Any],
    mutation_job: dict[str, Any],
    queue_track: dict[str, Any],
    source_assignment: dict[str, Any],
    brief: dict[str, Any],
    index: int,
    role_count: int,
) -> dict[str, Any]:
    role_id = brief["role_id"]
    task_id = f"{track['slug']}.{role_id}.{index:02d}"
    previous_task_id = None if index == 1 else f"{track['slug']}.{track['role_order'][index - 2]}.{index - 1:02d}"
    next_task_id = None if index == role_count else f"{track['slug']}.{track['role_order'][index]}.{index + 1:02d}"
    tool_ids = [tool["id"] for tool in brief.get("tool_contracts", []) if tool.get("id")]
    approval_ids = [gate["id"] for gate in brief.get("approval_required", []) if gate.get("id")]
    input_paths = ordered_unique(
        [
            *brief.get("repo_context", []),
            "automation/generated/openai-worker-briefs.json",
            "automation/generated/live12-daw-mutation-package.json",
            "automation/generated/live12-daw-mutation-queue-runbook.json",
            "automation/generated/public-domain-source-deck.json",
            "compositions/generated/live12-track-build-plans.json",
        ]
    )
    return {
        "task_id": task_id,
        "sequence": index,
        "role_id": role_id,
        "role_name": brief.get("role_name"),
        "execution_status": "not_started",
        "suggested_openai_surface": brief.get("suggested_openai_surface", {}),
        "tool_contract_ids": tool_ids,
        "approval_gate_ids": approval_ids,
        "allowed_repo_inputs": input_paths,
        "depends_on": [] if previous_task_id is None else [previous_task_id],
        "handoff_to_task_id": next_task_id,
        "handoff_contract": {
            "format": "structured_json_summary",
            "must_include": [
                "decisions",
                "unresolved_risks",
                "approval_gate_impacts",
                "next_role_context",
            ],
        },
        "prompt_packet": {
            "brief_ref": f"automation/generated/openai-worker-briefs.json#role_id={role_id}",
            "track_ref": f"compositions/generated/live12-track-build-plans.json#track_slug={track['slug']}",
            "mutation_job_ref": f"automation/generated/live12-daw-mutation-package.json#track_slug={track['slug']}",
            "daw_queue_ref": f"automation/generated/live12-daw-mutation-queue-runbook.json#track_slug={track['slug']}",
            "source_deck_ref": f"automation/generated/public-domain-source-deck.json#track_slug={track['slug']}",
            "instruction": role_instruction(role_id, build_plan),
            "track_summary": {
                "title": build_plan.get("title"),
                "tempo_bpm": build_plan.get("tempo_bpm"),
                "key_center": build_plan.get("key_center"),
                "duration_target": build_plan.get("duration_target"),
                "max_for_live_focus": build_plan.get("max_for_live_focus", []),
                "source_candidate_count": source_assignment.get("candidate_source_count", 0),
                "planned_daw_action_count": mutation_job.get("mutation_action_count", 0),
            },
            "must_not": ordered_unique([*brief.get("must_not", []), *GLOBAL_TASK_MUST_NOT]),
        },
        "expected_outputs": brief.get("expected_outputs", []),
        "local_output_policy": {
            "path": f"output/openai-swarm/{track['slug']}/{role_id}.json",
            "git_policy": "ignored_local_only",
            "content": "metadata_only_role_output",
        },
        "daw_context": {
            "request_path": queue_track.get("request_path"),
            "bundle_manifest_path": queue_track.get("bundle_manifest_path"),
            "launch_plan_path": queue_track.get("launch_plan_path"),
            "launch_requires_approval": True,
        },
    }


def track_packet(
    build_plan: dict[str, Any],
    mutation_job: dict[str, Any],
    queue_track: dict[str, Any],
    source_assignment: dict[str, Any],
    briefs: list[dict[str, Any]],
    role_order: list[str],
    queue_policy: dict[str, Any],
) -> dict[str, Any]:
    track = {
        "slug": build_plan["slug"],
        "role_order": role_order,
    }
    tasks = [
        task_packet(
            track,
            build_plan,
            mutation_job,
            queue_track,
            source_assignment,
            brief,
            index,
            len(briefs),
        )
        for index, brief in enumerate(briefs, start=1)
    ]
    return {
        "track_slug": build_plan["slug"],
        "track_title": build_plan["title"],
        "tempo_bpm": build_plan.get("tempo_bpm"),
        "key_center": build_plan.get("key_center"),
        "duration_target": build_plan.get("duration_target"),
        "mutation_job_id": mutation_job.get("id"),
        "planned_daw_action_count": mutation_job.get("mutation_action_count", 0),
        "source_deck_state": source_assignment.get("deck_state"),
        "source_candidate_ids": source_assignment.get("candidate_source_ids", []),
        "daw_queue": {
            "request_path": queue_track.get("request_path"),
            "bundle_manifest_path": queue_track.get("bundle_manifest_path"),
            "launch_plan_path": queue_track.get("launch_plan_path"),
            "launch_status": queue_policy.get("launch_status"),
        },
        "tasks": tasks,
    }


def render(stable: bool = False) -> dict[str, Any]:
    orchestration = read_json("automation/openai-production-orchestration.json")
    worker_chain = read_json("automation/worker-chain.json")
    worker_briefs = read_json("automation/generated/openai-worker-briefs.json")
    mutation_package = read_json("automation/generated/live12-daw-mutation-package.json")
    queue_runbook = read_json("automation/generated/live12-daw-mutation-queue-runbook.json")
    source_deck = read_json("automation/generated/public-domain-source-deck.json")
    build_plans = read_json("compositions/generated/live12-track-build-plans.json")

    briefs = worker_briefs.get("briefs", [])
    role_order = [brief["role_id"] for brief in briefs]
    jobs_by_slug = lookup_by(mutation_package.get("jobs", []), "track_slug")
    queue_by_slug = lookup_by(queue_runbook.get("tracks", []), "track_slug")
    source_assignments_by_slug = lookup_by(source_deck.get("track_assignments", []), "track_slug")
    tracks = [
        track_packet(
            build_plan,
            jobs_by_slug[build_plan["slug"]],
            queue_by_slug[build_plan["slug"]],
            source_assignments_by_slug[build_plan["slug"]],
            briefs,
            role_order,
            queue_runbook["queue_policy"],
        )
        for build_plan in build_plans.get("tracks", [])
    ]
    return {
        "schema_version": 1,
        "generated_at": STABLE_GENERATED_AT if stable else utc_now(),
        "generator": "scripts/render_openai_production_swarm_queue.py",
        "source_files": SOURCE_FILES,
        "source_file_sha256": {relative_path: sha256_file(ROOT / relative_path) for relative_path in SOURCE_FILES},
        "purpose": "Metadata-only OpenAI production swarm queue tying role-scoped worker briefs to each generated track and DAW mutation handoff.",
        "official_docs_basis": [
            {
                "surface": "Responses API structured outputs",
                "url": "https://developers.openai.com/api/docs/guides/structured-outputs",
                "project_use": "Track and role packets can be sent as structured inputs for proposal generation without mutating local state.",
            },
            {
                "surface": "Agents SDK handoffs",
                "url": "https://openai.github.io/openai-agents-python/handoffs/",
                "project_use": "Role order is represented as explicit task dependencies and handoff targets.",
            },
            {
                "surface": "Agents SDK tracing",
                "url": "https://openai.github.io/openai-agents-python/tracing/",
                "project_use": "Future runs should keep redacted traces for handoffs, tool calls, approvals, and unresolved risk notes.",
            },
            {
                "surface": "Apps SDK MCP",
                "url": "https://developers.openai.com/apps-sdk/build/mcp-server",
                "project_use": "Future ChatGPT control surfaces should expose narrow project tools instead of arbitrary shell, account, or DAW access.",
            },
        ],
        "queue_policy": {
            "execution_status": "planned_not_executed",
            "api_execution_status": "not_called_ci_safe",
            "git_policy": "metadata_only_no_private_audio",
            "credentials_required_for_generation": False,
            "local_output_root": "output/openai-swarm",
            "trace_policy": "redacted_agent_traces_only",
            "blocked_without_approval": [
                gate.get("id")
                for gate in orchestration.get("approval_gates", [])
                if gate.get("id") in {"source_download", "private_audio_upload", "vendor_account_action", "purchase_or_license_change", "live_set_mutation", "export_or_release"}
            ],
            "must_not_commit": [
                "raw private audio",
                "raw source audio",
                "unreleased lyrics",
                "OpenAI API keys",
                "vendor credentials",
                "cookies",
                "license files",
                "Ableton sets",
                "compiled Max for Live devices",
                "rendered audio",
            ],
        },
        "role_order": role_order,
        "role_count": len(role_order),
        "track_count": len(tracks),
        "task_count": sum(len(track["tasks"]) for track in tracks),
        "tracks": tracks,
    }


def render_markdown(queue: dict[str, Any]) -> str:
    lines = [
        "# OpenAI Production Swarm Queue",
        "",
        "Generated metadata-only queue for role-scoped OpenAI production workers.",
        "",
        f"Status: `{queue['queue_policy']['execution_status']}`.",
        "",
        "No OpenAI API call is made by this renderer or CI check.",
        "",
        "This queue is designed for future Agents SDK handoffs and Responses API structured outputs while keeping DAW, account, source-download, private-audio, and export actions behind explicit approval gates.",
        "",
        "## Official Surfaces",
        "",
    ]
    for doc in queue["official_docs_basis"]:
        lines.append(f"- {doc['surface']}: {doc['url']}")
    lines.extend(
        [
            "",
            "## Queue Summary",
            "",
            f"- Tracks: `{queue['track_count']}`",
            f"- Roles per track: `{queue['role_count']}`",
            f"- Total tasks: `{queue['task_count']}`",
            f"- Local output root: `{queue['queue_policy']['local_output_root']}`",
            "",
            "## Tracks",
            "",
        ]
    )
    for track in queue["tracks"]:
        lines.extend(
            [
                f"### {track['track_title']}",
                "",
                f"- Track slug: `{track['track_slug']}`",
                f"- Tempo/key: `{track['tempo_bpm']} BPM`, `{track['key_center']}`",
                f"- Source deck state: `{track['source_deck_state']}`",
                f"- Planned DAW actions: `{track['planned_daw_action_count']}`",
                f"- DAW request: `{track['daw_queue']['request_path']}`",
                "",
            ]
        )
        for task in track["tasks"]:
            surface = task["suggested_openai_surface"].get("id")
            gates = ", ".join(f"`{gate_id}`" for gate_id in task["approval_gate_ids"]) or "`none`"
            tools = ", ".join(f"`{tool_id}`" for tool_id in task["tool_contract_ids"])
            lines.extend(
                [
                    f"- `{task['task_id']}` - {task['role_name']} via `{surface}`",
                    f"  Tools: {tools}. Approval gates: {gates}.",
                ]
            )
        lines.append("")
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
    queue = render(stable=args.stable)
    markdown = render_markdown(queue)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "schema_version": queue["schema_version"],
                    "execution_status": queue["queue_policy"]["execution_status"],
                    "track_count": queue["track_count"],
                    "role_count": queue["role_count"],
                    "task_count": queue["task_count"],
                    "generated_at": queue["generated_at"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    output = args.output if args.output.is_absolute() else ROOT / args.output
    markdown_output = args.markdown_output if args.markdown_output.is_absolute() else ROOT / args.markdown_output
    write_json(output, queue)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(markdown, encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Wrote {markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
