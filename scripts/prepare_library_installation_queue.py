#!/usr/bin/env python3
"""Prepare local-only library/account action requests and receipt scaffolds."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "automation" / "generated" / "library-installation-queue.json"
DEFAULT_OUTPUT_DIR = ROOT / "output" / "library-installation"
STABLE_GENERATED_AT = "1970-01-01T00:00:00Z"
OFFICIAL_VENDOR_HOSTS = {
    "Ableton": ["www.ableton.com"],
    "Arturia": ["www.arturia.com"],
}


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


def repo_reference(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "external_output_override"


def output_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def item_ref(path: Path, output_dir: Path) -> str:
    return str(path.resolve().relative_to(output_dir.resolve()))


def validate_queue_sources(queue: dict[str, Any]) -> list[str]:
    errors = []
    for relative_path in queue.get("source_files", []):
        path = Path(relative_path)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"Invalid queue source path: {relative_path}")
            continue
        full_path = ROOT / path
        if not full_path.exists():
            errors.append(f"Missing queue source file: {relative_path}")
            continue
        expected_hash = queue.get("source_file_sha256", {}).get(relative_path)
        if expected_hash != sha256_file(full_path):
            errors.append(f"Stale queue source hash: {relative_path}")
    policy = queue.get("queue_policy", {})
    if policy.get("execution_status") != "planned_not_executed":
        errors.append("library installation queue must be planned_not_executed")
    if policy.get("ci_install_allowed") is not False:
        errors.append("library installation queue must block CI vendor actions")
    if policy.get("requires_human_confirmation") is not True:
        errors.append("library installation queue must require human confirmation")
    return errors


def approval_state(item: dict[str, Any]) -> dict[str, str]:
    return {
        gate: "required_not_granted"
        for gate in item.get("approval_gates_required", [])
    }


def build_request(
    queue: dict[str, Any],
    queue_path: Path,
    item: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    catalog_id = item["catalog_id"]
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "generator": "scripts/prepare_library_installation_queue.py",
        "run_id": f"{generated_at.replace(':', '').replace('-', '')}.{catalog_id}",
        "execution_status": "prepared_not_executed",
        "vendor_action_status": "not_opened_not_logged_in_not_installed",
        "queue_source": {
            "path": repo_reference(queue_path),
            "sha256": sha256_file(queue_path),
        },
        "inventory_source": {
            "path": "inventory/live12-local-inventory.json",
            "sha256": queue["source_file_sha256"]["inventory/live12-local-inventory.json"],
        },
        "queue_item_id": item["id"],
        "catalog_id": catalog_id,
        "vendor": item["vendor"],
        "name": item["name"],
        "priority": item["priority"],
        "status": item["status"],
        "action_class": item["action_class"],
        "source_url": item["source_url"],
        "official_allowed_hosts": OFFICIAL_VENDOR_HOSTS.get(item["vendor"], []),
        "install_route": item["install_route"],
        "local_signal": item["local_signal"],
        "project_use": item["project_use"],
        "approval_gates_required": item["approval_gates_required"],
        "approval_state": approval_state(item),
        "requires_human_confirmation": item["requires_human_confirmation"],
        "ci_install_allowed": item["ci_install_allowed"],
        "automation_mode": item["automation_mode"],
        "operator_next_step": item["operator_next_step"],
        "receipt_required_fields": item["receipt"]["required_fields"],
        "post_action_validation": item["post_action_validation"],
    }


def build_receipt_template(item: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": request["run_id"],
        "catalog_id": item["catalog_id"],
        "vendor": item["vendor"],
        "name": item["name"],
        "execution_status": "template_not_applied",
        "required_fields": item["receipt"]["required_fields"],
        "field_defaults": {
            "operator_approval_reference": "",
            "official_surface": "",
            "entitlement_reference_redacted": "",
            "purchase_or_license_change_reference": "",
            "inventory_before_sha256": request["inventory_source"]["sha256"],
            "inventory_after_sha256": "",
            "observed_local_signal": item["local_signal"],
            "created_artifacts": [],
            "redactions": [
                "credentials excluded",
                "account identifiers redacted",
                "commercial assets excluded from Git",
            ],
            "post_action_validation": item["post_action_validation"],
        },
        "git_policy": "ignored_local_only",
    }


def build_evidence_draft(item: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    return {
        "operator_approval_reference": "",
        "official_surface": "",
        "entitlement_reference_redacted": "",
        "purchase_or_license_change_reference": "",
        "inventory_before_sha256": request["inventory_source"]["sha256"],
        "inventory_after_sha256": "",
        "observed_local_signal": item["local_signal"],
        "action_outcome": "not_attempted",
        "performed_actions": [],
        "created_artifacts": [],
        "redactions": [
            "credentials excluded",
            "account identifiers redacted",
            "commercial assets excluded from Git",
        ],
        "post_action_validation": item["post_action_validation"],
    }


def build_launch_plan(item: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": request["generated_at"],
        "generator": "scripts/prepare_library_installation_queue.py",
        "catalog_id": item["catalog_id"],
        "vendor": item["vendor"],
        "name": item["name"],
        "launch_status": "blocked_until_operator_approval",
        "vendor_action_status": "not_opened_not_logged_in_not_installed",
        "official_surface": {
            "source_url": item["source_url"],
            "allowed_hosts": OFFICIAL_VENDOR_HOSTS.get(item["vendor"], []),
            "operator_note": item["operator_next_step"],
        },
        "approval_gates_required": item["approval_gates_required"],
        "requires_before_any_vendor_action": [
            "operator approval reference",
            "confirmed official host or official vendor application",
            "no credential capture",
            "no purchase or license change without a separate reference",
        ],
        "blocked_actions": [
            "vendor authentication",
            "purchase or license change",
            "download or installer execution",
            "Ableton Live library mutation",
            "Arturia Software Center state mutation",
        ],
    }


def artifact_entry(path: Path, output_dir: Path) -> dict[str, str]:
    return {
        "path": item_ref(path, output_dir),
        "sha256": sha256_file(path),
    }


def prepare_item(
    queue: dict[str, Any],
    queue_path: Path,
    item: dict[str, Any],
    output_dir: Path,
    generated_at: str,
) -> dict[str, Any]:
    catalog_id = item["catalog_id"]
    item_dir = output_dir / catalog_id
    request = build_request(queue, queue_path, item, generated_at)
    receipt_template = build_receipt_template(item, request)
    evidence_draft = build_evidence_draft(item, request)
    launch_plan = build_launch_plan(item, request)

    request_path = item_dir / "installation-request.json"
    receipt_template_path = item_dir / "receipt-template.json"
    evidence_path = item_dir / "operator-evidence.json"
    launch_plan_path = item_dir / "launch-plan.json"

    write_json(request_path, request)
    write_json(receipt_template_path, receipt_template)
    write_json(evidence_path, evidence_draft)
    write_json(launch_plan_path, launch_plan)

    return {
        "catalog_id": catalog_id,
        "vendor": item["vendor"],
        "name": item["name"],
        "queue_item_id": item["id"],
        "execution_status": "prepared_not_executed",
        "vendor_action_status": "not_opened_not_logged_in_not_installed",
        "approval_gates_required": item["approval_gates_required"],
        "request": artifact_entry(request_path, output_dir),
        "receipt_template": artifact_entry(receipt_template_path, output_dir),
        "operator_evidence_draft": artifact_entry(evidence_path, output_dir),
        "launch_plan": artifact_entry(launch_plan_path, output_dir),
    }


def build_manifest(
    queue: dict[str, Any],
    queue_path: Path,
    output_dir: Path,
    generated_at: str,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "generator": "scripts/prepare_library_installation_queue.py",
        "execution_status": "prepared_not_executed",
        "vendor_action_status": "not_opened_not_logged_in_not_installed",
        "artifact_root": repo_reference(output_dir),
        "queue_source": {
            "path": repo_reference(queue_path),
            "sha256": sha256_file(queue_path),
        },
        "inventory_source": {
            "path": "inventory/live12-local-inventory.json",
            "sha256": queue["source_file_sha256"]["inventory/live12-local-inventory.json"],
        },
        "item_count": len(items),
        "approval_gates_required": queue["queue_policy"]["blocked_without_approval"],
        "git_policy": "ignored_local_only",
        "items": items,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE, help="Generated library installation queue JSON.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Local-only output directory.")
    parser.add_argument("--stable", action="store_true", help="Use deterministic generated_at and run_id values.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    queue_path = output_path(args.queue)
    if not queue_path.exists():
        print(f"Missing library installation queue: {args.queue}", file=sys.stderr)
        return 1

    queue = read_json(queue_path)
    errors = validate_queue_sources(queue)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    output_dir = output_path(args.output_dir)
    generated_at = STABLE_GENERATED_AT if args.stable else utc_now()
    items = [
        prepare_item(queue, queue_path, item, output_dir, generated_at)
        for item in queue.get("queue", [])
    ]
    manifest = build_manifest(queue, queue_path, output_dir, generated_at, items)
    manifest_path = output_dir / "queue-manifest.json"
    write_json(manifest_path, manifest)
    print(
        json.dumps(
            {
                "execution_status": manifest["execution_status"],
                "item_count": manifest["item_count"],
                "output": repo_reference(manifest_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
