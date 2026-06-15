#!/usr/bin/env python3
"""Regression probes for the generated library installation queue."""

from __future__ import annotations

import difflib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
COMMITTED_JSON = ROOT / "automation" / "generated" / "library-installation-queue.json"
COMMITTED_MARKDOWN = ROOT / "docs" / "library-installation-queue.md"
EXPECTED_SOURCE_FILES = [
    "catalogs/library-installation-plan.json",
    "catalogs/recommended-packs.json",
    "inventory/live12-local-inventory.json",
    "automation/openai-production-orchestration.json",
]
OFFICIAL_HOSTS = {
    "Ableton": "www.ableton.com",
    "Arturia": "www.arturia.com",
}
LOCAL_STATUSES = {"observed_local", "installed"}
PURCHASE_GATED_STATUSES = {"account_or_purchase_required"}
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
        if "/Users/" in value or "/Applications/" in value:
            raise AssertionError(f"{label} leaked a local absolute path: {value}")
        if "sources/public-domain/raw/" in value:
            raise AssertionError(f"{label} leaked a raw source path: {value}")
        if "/" in value and value.endswith(BLOCKED_BINARY_EXTENSIONS):
            raise AssertionError(f"{label} carried a blocked audio/DAW artifact path: {value}")


def expected_inventory_summary(inventory: dict[str, Any]) -> dict[str, Any]:
    ableton = inventory.get("ableton", {})
    arturia = inventory.get("arturia", {})
    plugins = inventory.get("plugins", {})
    live_database = ableton.get("live_database", {})
    resources = arturia.get("resources", {})
    applications = arturia.get("applications", [])
    application_names = {item.get("name") for item in applications if isinstance(item, dict)}
    return {
        "ableton_live": {
            "exists": ableton.get("app", {}).get("exists", False),
            "name": ableton.get("app", {}).get("name"),
            "version": ableton.get("app", {}).get("version"),
            "factory_pack_count": len(ableton.get("factory_packs", [])),
            "indexed_pack_candidate_count": len(live_database.get("indexed_pack_candidates", [])),
            "available_not_installed_count": len(live_database.get("available_not_installed", [])),
            "live_database_read_status": live_database.get("read_status", "unknown"),
        },
        "arturia": {
            "application_count": len(applications),
            "software_center_present": "Arturia Software Center.app" in application_names,
            "resource_product_count": len(resources.get("products", [])),
            "preset_product_folder_count": len(resources.get("preset_products", [])),
            "sample_product_folder_count": len(resources.get("sample_products", [])),
        },
        "plugins": {
            "vst3_root_count": len(plugins.get("vst3_roots", [])),
            "audio_unit_root_count": len(plugins.get("audio_unit_roots", [])),
        },
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="library-installation-queue-test-") as temp_dir:
        temp_root = Path(temp_dir)
        generated_json = temp_root / "library-installation-queue.json"
        generated_markdown = temp_root / "library-installation-queue.md"
        render_result = run_command(
            [
                PYTHON,
                "scripts/render_library_installation_queue.py",
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
        install_plan = load_json(ROOT / "catalogs" / "library-installation-plan.json")
        recommended = load_json(ROOT / "catalogs" / "recommended-packs.json")
        inventory = load_json(ROOT / "inventory" / "live12-local-inventory.json")

        if generated_json.read_text(encoding="utf-8") != COMMITTED_JSON.read_text(encoding="utf-8"):
            print(diff_text(COMMITTED_JSON, generated_json), file=sys.stderr)
            return 1
        if generated_markdown.read_text(encoding="utf-8") != COMMITTED_MARKDOWN.read_text(encoding="utf-8"):
            print(diff_text(COMMITTED_MARKDOWN, generated_markdown), file=sys.stderr)
            return 1

        if queue.get("schema_version") != 1:
            print("Library installation queue must use schema_version 1.", file=sys.stderr)
            return 1
        if queue.get("generated_at") != "1970-01-01T00:00:00Z":
            print("Library installation queue must be committed with stable generated_at.", file=sys.stderr)
            return 1
        if queue.get("generator") != "scripts/render_library_installation_queue.py":
            print("Library installation queue generator is stale.", file=sys.stderr)
            return 1
        if queue.get("source_files") != EXPECTED_SOURCE_FILES:
            print("Library installation queue source_files changed unexpectedly.", file=sys.stderr)
            return 1
        if set(queue.get("source_file_sha256", {})) != set(EXPECTED_SOURCE_FILES):
            print("Library installation queue source hashes must cover expected source files.", file=sys.stderr)
            return 1

        policy = queue.get("queue_policy", {})
        if policy.get("execution_status") != "planned_not_executed":
            print("Library installation queue must remain planned_not_executed.", file=sys.stderr)
            return 1
        if policy.get("credentials_required_for_generation") is not False:
            print("Library installation queue generation must not require credentials.", file=sys.stderr)
            return 1
        if policy.get("ci_install_allowed") is not False:
            print("Library installation queue must not permit installs from CI.", file=sys.stderr)
            return 1
        if policy.get("local_output_root") != "output/library-installation":
            print("Library installation queue local output root is stale.", file=sys.stderr)
            return 1
        for required_gate in ["vendor_account_action", "purchase_or_license_change"]:
            if required_gate not in policy.get("blocked_without_approval", []):
                print(f"Library installation queue must block {required_gate}.", file=sys.stderr)
                return 1
        for forbidden in ["vendor credentials", "session cookies", "license files", "installer packages", "commercial pack content"]:
            if forbidden not in policy.get("must_not_commit", []):
                print(f"Library installation queue must block commits of {forbidden}.", file=sys.stderr)
                return 1

        if queue.get("inventory_summary") != expected_inventory_summary(inventory):
            print("Library installation queue inventory summary is stale.", file=sys.stderr)
            return 1

        recommended_by_id = {item["id"]: item for item in recommended["items"]}
        plan_items = install_plan["items"]
        install_queue = queue.get("queue", [])
        if queue.get("install_item_count") != len(plan_items) or len(install_queue) != len(plan_items):
            print("Library installation queue item count must mirror the installation plan.", file=sys.stderr)
            return 1
        if [item.get("catalog_id") for item in install_queue] != [item.get("id") for item in plan_items]:
            print("Library installation queue order must mirror the installation plan.", file=sys.stderr)
            return 1

        for index, (queue_item, plan_item) in enumerate(zip(install_queue, plan_items, strict=False), start=1):
            catalog_id = plan_item["id"]
            if queue_item.get("queue_order") != index or queue_item.get("id") != f"library-install.{catalog_id}":
                print(f"Library installation queue item id/order is stale: {catalog_id}", file=sys.stderr)
                return 1
            for field in ["vendor", "name", "priority", "status", "source_url", "install_route", "local_signal", "project_use"]:
                if queue_item.get(field) != plan_item.get(field):
                    print(f"Library installation queue item field {field} is stale: {catalog_id}", file=sys.stderr)
                    return 1
            host = urlparse(queue_item.get("source_url", "")).netloc.lower()
            if host != OFFICIAL_HOSTS.get(queue_item.get("vendor")):
                print(f"Library installation queue source host is not official: {catalog_id}", file=sys.stderr)
                return 1
            expected_gates = ["vendor_account_action"]
            if plan_item.get("status") in PURCHASE_GATED_STATUSES:
                expected_gates.append("purchase_or_license_change")
            if queue_item.get("approval_gates_required") != expected_gates:
                print(f"Library installation queue approval gates are stale: {catalog_id}", file=sys.stderr)
                return 1
            if queue_item.get("ci_install_allowed") is not False:
                print(f"Library installation queue item must block CI installs: {catalog_id}", file=sys.stderr)
                return 1
            if queue_item.get("requires_human_confirmation") is not True:
                print(f"Library installation queue item must require human confirmation: {catalog_id}", file=sys.stderr)
                return 1
            if "install" in " ".join(queue_item.get("automation_steps", [])).lower():
                print(f"Library installation queue automation_steps must not be executable install instructions: {catalog_id}", file=sys.stderr)
                return 1
            if queue_item.get("recommended") != (catalog_id in recommended_by_id):
                print(f"Library installation queue recommended flag is stale: {catalog_id}", file=sys.stderr)
                return 1
            if catalog_id in recommended_by_id:
                if queue_item.get("recommended_catalog_ref") != f"catalogs/recommended-packs.json#id={catalog_id}":
                    print(f"Library installation queue recommended ref is stale: {catalog_id}", file=sys.stderr)
                    return 1

        local_recommended = [item for item in recommended["items"] if item.get("status") in LOCAL_STATUSES]
        if queue.get("recommended_local_item_count") != len(local_recommended):
            print("Library installation queue local recommended count is stale.", file=sys.stderr)
            return 1

        markdown = generated_markdown.read_text(encoding="utf-8")
        for required_text in [
            "# Library Installation Queue",
            "planned_not_executed",
            "No vendor login, purchase, install, DAW launch, or OpenAI API call is performed",
            "Do not commit vendor credentials, session cookies, license files, installer packages, commercial pack content, presets, samples, or renders.",
            "python3 scripts/prepare_library_installation_queue.py --stable",
            "python3 scripts/record_library_installation_receipt.py --request output/library-installation/<catalog-id>/installation-request.json --evidence output/library-installation/<catalog-id>/operator-evidence.json",
            "python3 scripts/inventory_live_suite.py --output inventory/live12-local-inventory.json",
        ]:
            if required_text not in markdown:
                print(f"Library installation queue markdown missing: {required_text}", file=sys.stderr)
                return 1

        assert_no_sensitive_paths(queue, "library installation queue")
        assert_no_sensitive_paths({"markdown": markdown}, "library installation queue markdown")

    print("Library installation queue probes passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
