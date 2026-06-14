#!/usr/bin/env python3
"""Regression probes for the generated OpenAI production swarm queue."""

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
COMMITTED_JSON = ROOT / "automation" / "generated" / "openai-production-swarm-queue.json"
COMMITTED_MARKDOWN = ROOT / "docs" / "openai-production-swarm-queue.md"
EXPECTED_SOURCE_FILES = [
    "automation/openai-production-orchestration.json",
    "automation/worker-chain.json",
    "automation/generated/openai-worker-briefs.json",
    "automation/generated/live12-daw-mutation-package.json",
    "automation/generated/live12-daw-mutation-queue-runbook.json",
    "automation/generated/public-domain-source-deck.json",
    "compositions/generated/live12-track-build-plans.json",
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
    with tempfile.TemporaryDirectory(prefix="openai-production-swarm-queue-test-") as temp_dir:
        temp_root = Path(temp_dir)
        generated_json = temp_root / "openai-production-swarm-queue.json"
        generated_markdown = temp_root / "openai-production-swarm-queue.md"
        render_result = run_command(
            [
                PYTHON,
                "scripts/render_openai_production_swarm_queue.py",
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

        queue = load_json(generated_json)
        worker_briefs = load_json(ROOT / "automation" / "generated" / "openai-worker-briefs.json")
        package = load_json(ROOT / "automation" / "generated" / "live12-daw-mutation-package.json")
        role_ids = [brief["role_id"] for brief in worker_briefs["briefs"]]
        track_slugs = [job["track_slug"] for job in package["jobs"]]

        if generated_json.read_text(encoding="utf-8") != COMMITTED_JSON.read_text(encoding="utf-8"):
            print(diff_text(COMMITTED_JSON, generated_json), file=sys.stderr)
            return 1
        if generated_markdown.read_text(encoding="utf-8") != COMMITTED_MARKDOWN.read_text(encoding="utf-8"):
            print(diff_text(COMMITTED_MARKDOWN, generated_markdown), file=sys.stderr)
            return 1

        if queue.get("schema_version") != 1:
            print("OpenAI production swarm queue must use schema_version 1.", file=sys.stderr)
            return 1
        if queue.get("source_files") != EXPECTED_SOURCE_FILES:
            print("OpenAI production swarm queue source files changed unexpectedly.", file=sys.stderr)
            return 1
        if queue.get("queue_policy", {}).get("execution_status") != "planned_not_executed":
            print("OpenAI production swarm queue must remain planned_not_executed.", file=sys.stderr)
            return 1
        if queue.get("queue_policy", {}).get("api_execution_status") != "not_called_ci_safe":
            print("OpenAI production swarm queue must not require OpenAI API calls in CI.", file=sys.stderr)
            return 1
        if queue.get("queue_policy", {}).get("git_policy") != "metadata_only_no_private_audio":
            print("OpenAI production swarm queue must be metadata-only.", file=sys.stderr)
            return 1

        if queue.get("role_order") != role_ids:
            print("OpenAI production swarm queue role_order must mirror worker briefs.", file=sys.stderr)
            return 1
        tracks = queue.get("tracks", [])
        if [track.get("track_slug") for track in tracks] != track_slugs:
            print("OpenAI production swarm queue track order must mirror the mutation package.", file=sys.stderr)
            return 1
        if queue.get("track_count") != len(track_slugs):
            print("OpenAI production swarm queue track_count is stale.", file=sys.stderr)
            return 1
        if queue.get("role_count") != len(role_ids):
            print("OpenAI production swarm queue role_count is stale.", file=sys.stderr)
            return 1
        if queue.get("task_count") != len(track_slugs) * len(role_ids):
            print("OpenAI production swarm queue task_count is stale.", file=sys.stderr)
            return 1

        valid_surfaces = {"responses_api", "agents_sdk", "realtime_api", "audio_transcription", "apps_sdk_mcp"}
        for track in tracks:
            tasks = track.get("tasks", [])
            if [task.get("role_id") for task in tasks] != role_ids:
                print(f"Track task order must mirror role order: {track.get('track_slug')}", file=sys.stderr)
                return 1
            if track.get("daw_queue", {}).get("launch_status") != "blocked_until_per_track_confirm_live_mutation":
                print(f"Track DAW queue launch status must stay blocked: {track.get('track_slug')}", file=sys.stderr)
                return 1
            if track.get("source_deck_state") != "muted_until_human_provenance_review":
                print(f"Track source deck must remain muted by default: {track.get('track_slug')}", file=sys.stderr)
                return 1
            for index, task in enumerate(tasks, start=1):
                expected_task_id = f"{track['track_slug']}.{task['role_id']}.{index:02d}"
                if task.get("task_id") != expected_task_id:
                    print(f"Task id is stale: {expected_task_id}", file=sys.stderr)
                    return 1
                if task.get("suggested_openai_surface", {}).get("id") not in valid_surfaces:
                    print(f"Task references an unknown OpenAI surface: {task.get('task_id')}", file=sys.stderr)
                    return 1
                if task.get("execution_status") != "not_started":
                    print(f"Task must not claim execution: {task.get('task_id')}", file=sys.stderr)
                    return 1
                if not task.get("tool_contract_ids"):
                    print(f"Task must include tool_contract_ids: {task.get('task_id')}", file=sys.stderr)
                    return 1
                if index == 1 and task.get("depends_on"):
                    print(f"First task must not depend on prior task: {task.get('task_id')}", file=sys.stderr)
                    return 1
                if index > 1 and task.get("depends_on") != [tasks[index - 2]["task_id"]]:
                    print(f"Task dependency chain is stale: {task.get('task_id')}", file=sys.stderr)
                    return 1
                if index < len(tasks) and task.get("handoff_to_task_id") != tasks[index]["task_id"]:
                    print(f"Task handoff is stale: {task.get('task_id')}", file=sys.stderr)
                    return 1
                if index == len(tasks) and task.get("handoff_to_task_id") is not None:
                    print(f"Final task must not hand off to another task: {task.get('task_id')}", file=sys.stderr)
                    return 1

        markdown = generated_markdown.read_text(encoding="utf-8")
        for required_text in [
            "# OpenAI Production Swarm Queue",
            "planned_not_executed",
            "No OpenAI API call is made by this renderer or CI check.",
            "Agents SDK handoffs",
            "Responses API structured outputs",
            "Rail Yard Ghost in the Control Room",
        ]:
            if required_text not in markdown:
                print(f"OpenAI production swarm queue markdown missing: {required_text}", file=sys.stderr)
                return 1

        assert_no_sensitive_paths(queue, "openai production swarm queue")
        assert_no_sensitive_paths({"markdown": markdown}, "openai production swarm queue markdown")

    print("OpenAI production swarm queue probes passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
