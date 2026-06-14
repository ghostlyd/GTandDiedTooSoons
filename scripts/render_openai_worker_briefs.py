#!/usr/bin/env python3
"""Render metadata-only OpenAI worker briefs from versioned project manifests."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "automation/generated/openai-worker-briefs.json"
STABLE_GENERATED_AT = "1970-01-01T00:00:00Z"

SOURCE_FILES = [
    "automation/openai-production-orchestration.json",
    "automation/worker-chain.json",
    "automation/live12-session-template.json",
    "compositions/down-tempo-punk-bluegrass-set.json",
    "catalogs/public-domain-bluegrass-sources.json",
    "catalogs/library-installation-plan.json",
    "inventory/live12-local-inventory.json",
]

ROLE_TOOL_MAP = {
    "archivist": ["validate_source_rights", "render_worker_brief"],
    "controller_engineer": ["read_inventory", "propose_session_change", "automate_daw_session"],
    "max_device_builder": ["read_inventory", "propose_session_change", "automate_daw_session"],
    "arrangement_producer": ["render_worker_brief", "propose_session_change"],
    "mix_engineer": ["read_inventory", "automate_daw_session", "render_release_checklist"],
    "release_qa": ["validate_source_rights", "read_inventory", "render_release_checklist"],
}

ROLE_SURFACE_MAP = {
    "archivist": "responses_api",
    "controller_engineer": "agents_sdk",
    "max_device_builder": "agents_sdk",
    "arrangement_producer": "responses_api",
    "mix_engineer": "agents_sdk",
    "release_qa": "responses_api",
}

ROLE_APPROVAL_MAP = {
    "archivist": ["source_download"],
    "controller_engineer": ["live_set_mutation"],
    "max_device_builder": ["live_set_mutation"],
    "arrangement_producer": ["live_set_mutation", "private_audio_upload"],
    "mix_engineer": ["private_audio_upload", "live_set_mutation", "export_or_release"],
    "release_qa": ["source_download", "vendor_account_action", "purchase_or_license_change", "export_or_release"],
}

ROLE_CONTEXT_MAP = {
    "archivist": [
        "catalogs/public-domain-bluegrass-sources.json",
        "sources/public-domain/download-ledger.json",
        "docs/source-acquisition-policy.md",
    ],
    "controller_engineer": [
        "automation/live12-session-template.json",
        "inventory/live12-local-inventory.json",
        "docs/live12-m4l-ci-cd.md",
    ],
    "max_device_builder": [
        "automation/live12-session-template.json",
        "automation/openai-production-orchestration.json",
        "docs/live12-m4l-ci-cd.md",
    ],
    "arrangement_producer": [
        "compositions/down-tempo-punk-bluegrass-set.json",
        "automation/live12-session-template.json",
        "docs/production-system.md",
    ],
    "mix_engineer": [
        "automation/live12-session-template.json",
        "inventory/live12-local-inventory.json",
        "docs/production-system.md",
    ],
    "release_qa": [
        ".github/workflows/live12-foundation-ci.yml",
        "catalogs/library-installation-plan.json",
        "catalogs/public-domain-bluegrass-sources.json",
        "sources/public-domain/download-ledger.json",
    ],
}


def load_json(relative_path: str) -> dict[str, Any]:
    path = ROOT / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def next_role(role_id: str, handoff_order: list[str]) -> str | None:
    try:
        index = handoff_order.index(role_id)
    except ValueError:
        return None
    if index + 1 >= len(handoff_order):
        return None
    return handoff_order[index + 1]


def split_role_inputs(inputs: list[str]) -> tuple[list[str], list[str]]:
    repo_inputs = []
    local_only_inputs = []
    for value in inputs:
        candidate = ROOT / value
        if candidate.exists() and not Path(value).is_absolute() and ".." not in Path(value).parts:
            repo_inputs.append(value)
        else:
            local_only_inputs.append(value)
    return repo_inputs, local_only_inputs


def summarize_inventory(inventory: dict[str, Any]) -> dict[str, Any]:
    ableton = inventory.get("ableton", {})
    arturia = inventory.get("arturia", {})
    live_database = ableton.get("live_database", {})
    factory_packs = ableton.get("factory_packs", [])

    return {
        "ableton_live": {
            "exists": ableton.get("app", {}).get("exists", False),
            "name": ableton.get("app", {}).get("name"),
            "version": ableton.get("app", {}).get("version"),
            "factory_pack_count": len(factory_packs),
            "installed_factory_packs": [item.get("name") for item in factory_packs if item.get("name")],
            "indexed_pack_candidate_count": len(live_database.get("indexed_pack_candidates", [])),
            "available_not_installed_count": len(live_database.get("available_not_installed", [])),
            "live_database_read_status": live_database.get("read_status", "unknown"),
        },
        "arturia": {
            "application_count": len(arturia.get("applications", [])),
            "resource_product_count": len(arturia.get("resource_products", [])),
            "preset_product_folder_count": len(arturia.get("preset_product_folders", [])),
            "sample_product_folder_count": len(arturia.get("sample_product_folders", [])),
        },
    }


def approved_source_summary(source_catalog: dict[str, Any]) -> list[dict[str, Any]]:
    approved = []
    for source in source_catalog.get("sources", []):
        if not source.get("approved_for_download"):
            continue
        approved.append(
            {
                "id": source.get("id"),
                "name": source.get("name"),
                "rights_status": source.get("rights_status"),
                "credit_line": source.get("credit_line"),
                "project_use": source.get("project_use"),
            }
        )
    return approved


def library_install_summary(install_plan: dict[str, Any]) -> dict[str, Any]:
    items = install_plan.get("items", [])
    high_priority = [
        {
            "id": item.get("id"),
            "vendor": item.get("vendor"),
            "name": item.get("name"),
            "status": item.get("status"),
        }
        for item in items
        if item.get("priority") == "high"
    ]
    automation_candidates = [
        {
            "id": item.get("id"),
            "vendor": item.get("vendor"),
            "name": item.get("name"),
            "status": item.get("status"),
            "install_route": item.get("install_route"),
        }
        for item in items
        if item.get("status")
        in {"live_database_available_not_installed", "account_login_required", "account_or_purchase_required"}
    ]
    return {
        "high_priority_items": high_priority,
        "account_or_daw_automation_candidates": automation_candidates,
    }


def tool_lookup(orchestration: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {tool.get("id"): tool for tool in orchestration.get("tool_contracts", []) if tool.get("id")}


def approval_lookup(orchestration: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {gate.get("id"): gate for gate in orchestration.get("approval_gates", []) if gate.get("id")}


def surface_lookup(orchestration: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {surface.get("id"): surface for surface in orchestration.get("api_surfaces", []) if surface.get("id")}


def build_brief(
    role: dict[str, Any],
    handoff_order: list[str],
    orchestration: dict[str, Any],
    track_titles: list[str],
    live_track_names: list[str],
) -> dict[str, Any]:
    role_id = role["id"]
    tools = tool_lookup(orchestration)
    approvals = approval_lookup(orchestration)
    surfaces = surface_lookup(orchestration)
    tool_ids = ROLE_TOOL_MAP.get(role_id, ["render_worker_brief"])
    approval_ids = ROLE_APPROVAL_MAP.get(role_id, [])
    surface_id = ROLE_SURFACE_MAP.get(role_id, "responses_api")
    repo_inputs, local_only_inputs = split_role_inputs(role.get("inputs", []))

    return {
        "role_id": role_id,
        "role_name": role.get("name"),
        "mission": f"Own {', '.join(role.get('owns', []))} for GTandDiedTooSoons without crossing data, rights, account, or DAW approval boundaries.",
        "owns": role.get("owns", []),
        "allowed_inputs": repo_inputs,
        "local_only_inputs": local_only_inputs,
        "expected_outputs": role.get("outputs", []),
        "must_not": role.get("must_not", []),
        "suggested_openai_surface": {
            "id": surface_id,
            "name": surfaces.get(surface_id, {}).get("name"),
            "use": surfaces.get(surface_id, {}).get("use"),
        },
        "tool_contracts": [
            {
                "id": tool_id,
                "input_scope": tools.get(tool_id, {}).get("input_scope", []),
                "output": tools.get(tool_id, {}).get("output"),
                "approval_required": tools.get(tool_id, {}).get("approval_required", False),
                "must_not": tools.get(tool_id, {}).get("must_not", []),
            }
            for tool_id in tool_ids
        ],
        "repo_context": ROLE_CONTEXT_MAP.get(role_id, []),
        "approval_required": [
            {
                "id": approval_id,
                "trigger": approvals.get(approval_id, {}).get("trigger"),
                "required_evidence": approvals.get(approval_id, {}).get("required_evidence", []),
            }
            for approval_id in approval_ids
        ],
        "handoff_to": next_role(role_id, handoff_order),
        "track_context": track_titles,
        "live_session_context": live_track_names,
    }


def render(stable: bool = False) -> dict[str, Any]:
    orchestration = load_json("automation/openai-production-orchestration.json")
    worker_chain = load_json("automation/worker-chain.json")
    session_template = load_json("automation/live12-session-template.json")
    compositions = load_json("compositions/down-tempo-punk-bluegrass-set.json")
    source_catalog = load_json("catalogs/public-domain-bluegrass-sources.json")
    install_plan = load_json("catalogs/library-installation-plan.json")
    inventory = load_json("inventory/live12-local-inventory.json")

    track_titles = [track.get("title") for track in compositions.get("tracks", []) if track.get("title")]
    live_track_names = [track.get("name") for track in session_template.get("tracks", []) if track.get("name")]
    handoff_order = worker_chain.get("handoff_order", [])

    return {
        "schema_version": 1,
        "generated_at": STABLE_GENERATED_AT if stable else utc_now(),
        "generator": "scripts/render_openai_worker_briefs.py",
        "source_files": SOURCE_FILES,
        "orchestration_contract": {
            "name": orchestration.get("name"),
            "purpose": orchestration.get("purpose"),
            "operating_assumptions": orchestration.get("operating_assumptions", []),
            "official_docs_consulted": orchestration.get("official_docs_consulted", []),
        },
        "project_context": {
            "composition_set": compositions.get("set_name"),
            "track_titles": track_titles,
            "live_template": session_template.get("name"),
            "live_tracks": live_track_names,
            "inventory_summary": summarize_inventory(inventory),
            "approved_public_domain_sources": approved_source_summary(source_catalog),
            "library_installation": library_install_summary(install_plan),
        },
        "briefs": [
            build_brief(role, handoff_order, orchestration, track_titles, live_track_names)
            for role in worker_chain.get("roles", [])
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON path.")
    parser.add_argument("--stable", action="store_true", help="Use deterministic generated_at value.")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = render(stable=args.stable)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "schema_version": data["schema_version"],
                    "brief_count": len(data["briefs"]),
                    "source_file_count": len(data["source_files"]),
                    "generated_at": data["generated_at"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        display_path = args.output.relative_to(ROOT)
    except ValueError:
        display_path = args.output
    print(f"Wrote {display_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
