#!/usr/bin/env python3
"""Render an approval-gated library installation queue."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "automation" / "generated" / "library-installation-queue.json"
DEFAULT_MARKDOWN_OUTPUT = ROOT / "docs" / "library-installation-queue.md"
STABLE_GENERATED_AT = "1970-01-01T00:00:00Z"

SOURCE_FILES = [
    "catalogs/library-installation-plan.json",
    "catalogs/recommended-packs.json",
    "inventory/live12-local-inventory.json",
    "automation/openai-production-orchestration.json",
]

PURCHASE_GATED_STATUSES = {"account_or_purchase_required"}
LOCAL_STATUSES = {"observed_local", "installed"}
STATUS_ACTION_CLASSES = {
    "live_database_available_not_installed": "available_in_live_database_pending_operator_action",
    "account_login_required": "account_entitlement_review_required",
    "account_or_purchase_required": "entitlement_or_purchase_review_required",
    "official_free_not_installed": "official_free_content_pending_operator_action",
    "official_free_download_manual_install": "official_free_download_pending_manual_action",
}
OFFICIAL_VENDOR_ROUTES = {
    "Ableton": {
        "allowed_hosts": ["www.ableton.com"],
        "operator_route": "Ableton Live Browser > Packs, or authenticated Ableton account page for already licensed content.",
        "supervised_automation_boundary": "Use official Ableton UI/account surfaces only after approval; record redacted receipts and refresh inventory.",
    },
    "Arturia": {
        "allowed_hosts": ["www.arturia.com"],
        "operator_route": "Arturia Software Center, Arturia product page, or authenticated Arturia account page.",
        "supervised_automation_boundary": "Use official Arturia UI/account surfaces only after approval; record redacted receipts and refresh inventory.",
    },
}
MUST_NOT_COMMIT = [
    "vendor credentials",
    "session cookies",
    "license files",
    "installer packages",
    "commercial pack content",
    "presets",
    "samples",
    "renders",
]
RECEIPT_FIELDS = [
    "run_id",
    "catalog_id",
    "vendor",
    "name",
    "execution_status",
    "operator_approval_reference",
    "source_url",
    "official_surface",
    "entitlement_reference_redacted",
    "purchase_or_license_change_reference",
    "inventory_before_sha256",
    "inventory_after_sha256",
    "observed_local_signal",
    "created_artifacts",
    "redactions",
    "post_action_validation",
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


def counter_dict(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def as_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def inventory_summary(inventory: dict[str, Any]) -> dict[str, Any]:
    ableton = inventory.get("ableton", {})
    arturia = inventory.get("arturia", {})
    plugins = inventory.get("plugins", {})
    live_database = ableton.get("live_database", {})
    resources = arturia.get("resources", {})
    applications = as_list(arturia.get("applications"))
    application_names = {item.get("name") for item in applications if isinstance(item, dict)}
    return {
        "ableton_live": {
            "exists": ableton.get("app", {}).get("exists", False),
            "name": ableton.get("app", {}).get("name"),
            "version": ableton.get("app", {}).get("version"),
            "factory_pack_count": len(as_list(ableton.get("factory_packs"))),
            "indexed_pack_candidate_count": len(as_list(live_database.get("indexed_pack_candidates"))),
            "available_not_installed_count": len(as_list(live_database.get("available_not_installed"))),
            "live_database_read_status": live_database.get("read_status", "unknown"),
        },
        "arturia": {
            "application_count": len(applications),
            "software_center_present": "Arturia Software Center.app" in application_names,
            "resource_product_count": len(as_list(resources.get("products"))),
            "preset_product_folder_count": len(as_list(resources.get("preset_products"))),
            "sample_product_folder_count": len(as_list(resources.get("sample_products"))),
        },
        "plugins": {
            "vst3_root_count": len(as_list(plugins.get("vst3_roots"))),
            "audio_unit_root_count": len(as_list(plugins.get("audio_unit_roots"))),
        },
    }


def approval_gates_for(status: str) -> list[str]:
    gates = ["vendor_account_action"]
    if status in PURCHASE_GATED_STATUSES:
        gates.append("purchase_or_license_change")
    return gates


def item_operator_note(status: str) -> str:
    if status == "live_database_available_not_installed":
        return "Check the Live Browser database entry, then act through the official Ableton surface after approval."
    if status == "account_login_required":
        return "Confirm account entitlement through the official vendor surface after approval."
    if status == "account_or_purchase_required":
        return "Confirm entitlement first; any purchase or license change needs separate approval evidence."
    if status == "official_free_not_installed":
        return "Confirm the free official page and entitlement boundary before acting."
    if status == "official_free_download_manual_install":
        return "Confirm the official page and local manual action boundary before acting."
    return "Review official vendor state and capture approval evidence before acting."


def build_queue_item(
    index: int,
    item: dict[str, Any],
    recommended_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    catalog_id = item["id"]
    is_recommended = catalog_id in recommended_by_id
    status = item.get("status", "")
    receipt_path = f"output/library-installation/{catalog_id}/receipt-template.json"
    return {
        "id": f"library-install.{catalog_id}",
        "queue_order": index,
        "catalog_id": catalog_id,
        "vendor": item.get("vendor"),
        "name": item.get("name"),
        "priority": item.get("priority"),
        "status": status,
        "action_class": STATUS_ACTION_CLASSES.get(status, "operator_review_required"),
        "source_url": item.get("source_url"),
        "source_catalog_ref": f"catalogs/library-installation-plan.json#id={catalog_id}",
        "recommended": is_recommended,
        "recommended_catalog_ref": f"catalogs/recommended-packs.json#id={catalog_id}" if is_recommended else None,
        "project_use": item.get("project_use"),
        "install_route": item.get("install_route"),
        "local_signal": item.get("local_signal"),
        "approval_gates_required": approval_gates_for(status),
        "requires_human_confirmation": True,
        "ci_install_allowed": False,
        "automation_mode": "supervised_official_surface_after_approval",
        "automation_steps": [
            "Review source_url on the official vendor host.",
            "Confirm entitlement, account session, and purchase boundary outside CI.",
            "Perform the approved vendor UI/app action through a supervised authenticated session.",
            "Refresh inventory with the tracked inventory script.",
            "Record a redacted receipt under the ignored local receipt root before updating tracked metadata.",
        ],
        "operator_next_step": item_operator_note(status),
        "receipt": {
            "template_path": receipt_path,
            "git_policy": "ignored_local_only",
            "required_fields": RECEIPT_FIELDS,
        },
        "post_action_validation": [
            "python3 scripts/inventory_live_suite.py --output inventory/live12-local-inventory.json",
            "python3 scripts/validate_repo.py",
            "python3 scripts/test_library_installation_queue.py",
            "python3 scripts/test_library_installation_preflight.py",
        ],
    }


def build_queue(stable: bool) -> dict[str, Any]:
    install_plan = read_json("catalogs/library-installation-plan.json")
    recommended = read_json("catalogs/recommended-packs.json")
    inventory = read_json("inventory/live12-local-inventory.json")
    orchestration = read_json("automation/openai-production-orchestration.json")

    recommended_by_id = {item["id"]: item for item in recommended.get("items", []) if item.get("id")}
    plan_items = install_plan.get("items", [])
    queue_items = [
        build_queue_item(index, item, recommended_by_id)
        for index, item in enumerate(plan_items, start=1)
    ]
    local_recommended_items = [
        item
        for item in recommended.get("items", [])
        if item.get("status") in LOCAL_STATUSES
    ]
    approval_gate_ids = {gate.get("id"): gate for gate in orchestration.get("approval_gates", []) if gate.get("id")}
    approval_gates = [
        approval_gate_ids[gate_id]
        for gate_id in ["vendor_account_action", "purchase_or_license_change"]
        if gate_id in approval_gate_ids
    ]

    source_hashes = {
        source_file: sha256_file(ROOT / source_file)
        for source_file in SOURCE_FILES
    }
    return {
        "schema_version": 1,
        "generated_at": STABLE_GENERATED_AT if stable else utc_now(),
        "generator": "scripts/render_library_installation_queue.py",
        "purpose": "Metadata-only operator queue for approval-gated Ableton and Arturia library/account actions.",
        "source_files": SOURCE_FILES,
        "source_file_sha256": source_hashes,
        "queue_policy": {
            "execution_status": "planned_not_executed",
            "api_execution_status": "not_called_ci_safe",
            "credentials_required_for_generation": False,
            "requires_human_confirmation": True,
            "ci_install_allowed": False,
            "automation_scope": "official_surface_metadata_queue_only",
            "git_policy": "metadata_only_no_commercial_assets",
            "local_output_root": "output/library-installation",
            "blocked_without_approval": ["vendor_account_action", "purchase_or_license_change"],
            "must_not_commit": MUST_NOT_COMMIT,
        },
        "approval_gates": approval_gates,
        "official_vendor_routes": [
            {
                "vendor": vendor,
                **route,
            }
            for vendor, route in sorted(OFFICIAL_VENDOR_ROUTES.items())
        ],
        "inventory_summary": inventory_summary(inventory),
        "install_item_count": len(plan_items),
        "recommended_item_count": len(recommended.get("items", [])),
        "recommended_local_item_count": len(local_recommended_items),
        "summary": {
            "by_vendor": counter_dict([item.get("vendor", "unknown") for item in queue_items]),
            "by_priority": counter_dict([item.get("priority", "unknown") for item in queue_items]),
            "by_status": counter_dict([item.get("status", "unknown") for item in queue_items]),
            "by_action_class": counter_dict([item.get("action_class", "unknown") for item in queue_items]),
            "purchase_or_license_change_required_count": sum(
                1 for item in queue_items if "purchase_or_license_change" in item.get("approval_gates_required", [])
            ),
        },
        "operator_commands": {
            "prepare_local_preflight": [
                "python3",
                "scripts/prepare_library_installation_queue.py",
                "--stable",
            ],
            "record_receipt": [
                "python3",
                "scripts/record_library_installation_receipt.py",
                "--request",
                "output/library-installation/<catalog-id>/installation-request.json",
                "--evidence",
                "output/library-installation/<catalog-id>/operator-evidence.json",
            ],
            "refresh_inventory_after_action": [
                "python3",
                "scripts/inventory_live_suite.py",
                "--output",
                "inventory/live12-local-inventory.json",
            ],
            "validate_repo": ["python3", "scripts/validate_repo.py"],
            "probe_queue": ["python3", "scripts/test_library_installation_queue.py"],
            "probe_preflight": ["python3", "scripts/test_library_installation_preflight.py"],
        },
        "receipt_contract": {
            "output_root": "output/library-installation",
            "git_policy": "ignored_local_only",
            "required_fields": RECEIPT_FIELDS,
            "required_post_action_validation": [
                "refreshed inventory snapshot",
                "redacted official-surface receipt",
                "repository validation passed",
            ],
            "prohibited_artifacts": MUST_NOT_COMMIT,
        },
        "local_recommended_items": [
            {
                "id": item.get("id"),
                "vendor": item.get("vendor"),
                "name": item.get("name"),
                "status": item.get("status"),
                "source_url": item.get("source_url"),
                "project_use": item.get("project_use"),
            }
            for item in local_recommended_items
        ],
        "queue": queue_items,
    }


def command_string(parts: list[str]) -> str:
    return " ".join(parts)


def render_markdown(queue: dict[str, Any]) -> str:
    policy = queue["queue_policy"]
    inventory = queue["inventory_summary"]
    commands = queue["operator_commands"]
    lines = [
        "# Library Installation Queue",
        "",
        "Generated operator handoff for approval-gated Ableton and Arturia library/account actions.",
        "",
        f"- Execution status: `{policy['execution_status']}`",
        "- No vendor login, purchase, install, DAW launch, or OpenAI API call is performed by this renderer or CI check.",
        "- Do not commit vendor credentials, session cookies, license files, installer packages, commercial pack content, presets, samples, or renders.",
        f"- Local receipt root: `{policy['local_output_root']}` (`ignored_local_only`).",
        f"- Prepare local queue: `{command_string(commands['prepare_local_preflight'])}`",
        f"- Inventory refresh: `{command_string(commands['refresh_inventory_after_action'])}`",
        f"- Receipt recorder: `{command_string(commands['record_receipt'])}`",
        "",
        "## Inventory Summary",
        "",
        f"- Ableton Live: `{inventory['ableton_live']['name']}` version `{inventory['ableton_live']['version']}`; factory packs `{inventory['ableton_live']['factory_pack_count']}`; available-not-present candidates `{inventory['ableton_live']['available_not_installed_count']}`.",
        f"- Arturia: applications `{inventory['arturia']['application_count']}`; Software Center present `{inventory['arturia']['software_center_present']}`; resource products `{inventory['arturia']['resource_product_count']}`.",
        f"- Plugin roots: VST3 `{inventory['plugins']['vst3_root_count']}`; Audio Unit `{inventory['plugins']['audio_unit_root_count']}`.",
        "",
        "## Queue Policy",
        "",
        f"- Blocked approval gates: `{', '.join(policy['blocked_without_approval'])}`",
        f"- Git policy: `{policy['git_policy']}`",
        f"- CI vendor actions allowed: `{policy['ci_install_allowed']}`",
        "",
        "## Vendor Routes",
        "",
    ]
    for route in queue["official_vendor_routes"]:
        lines.extend(
            [
                f"### {route['vendor']}",
                "",
                f"- Allowed hosts: `{', '.join(route['allowed_hosts'])}`",
                f"- Route: {route['operator_route']}",
                f"- Boundary: {route['supervised_automation_boundary']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Queue Items",
            "",
        ]
    )
    for item in queue["queue"]:
        gates = ", ".join(item["approval_gates_required"])
        lines.extend(
            [
                f"### {item['queue_order']}. {item['name']}",
                "",
                f"- Catalog id: `{item['catalog_id']}`",
                f"- Vendor: `{item['vendor']}`",
                f"- Priority/status: `{item['priority']}` / `{item['status']}`",
                f"- Action class: `{item['action_class']}`",
                f"- Approval gates: `{gates}`",
                f"- Official URL: {item['source_url']}",
                f"- Route: {item['install_route']}",
                f"- Local signal: {item['local_signal']}",
                f"- Project use: {item['project_use']}",
                f"- Operator next step: {item['operator_next_step']}",
                f"- Receipt template: `{item['receipt']['template_path']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Post-Action Checks",
            "",
            f"1. `{command_string(commands['refresh_inventory_after_action'])}`",
            f"2. `{command_string(commands['validate_repo'])}`",
            f"3. `{command_string(commands['probe_queue'])}`",
            f"4. `{command_string(commands['probe_preflight'])}`",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stable", action="store_true", help="Use stable generated_at for committed artifacts.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="JSON output path.")
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT, help="Markdown output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    queue = build_queue(stable=args.stable)
    write_json(args.output, queue)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(render_markdown(queue) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
