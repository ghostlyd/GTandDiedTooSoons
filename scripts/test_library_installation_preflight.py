#!/usr/bin/env python3
"""Regression probes for local library/account action preflight receipts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
QUEUE_PATH = ROOT / "automation" / "generated" / "library-installation-queue.json"
APPROVAL_REFERENCE = "operator-approved-vendor-action-001"
PURCHASE_REFERENCE_NOT_APPLICABLE = "not_applicable_no_license_change"
BLOCKED_EXTENSIONS = (".als", ".amxd", ".alp", ".wav", ".aiff", ".flac", ".mp3", ".m4a", ".ogg")


def run_command(args: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=False, capture_output=True, text=True)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
        if "/Users/" in value or "/Applications/" in value or value.startswith(("~/", "file://")):
            raise AssertionError(f"{label} leaked a local path or file URL: {value}")
        if "sources/public-domain/raw/" in value:
            raise AssertionError(f"{label} leaked a raw source path: {value}")
        if "/" in value and value.lower().endswith(BLOCKED_EXTENSIONS):
            raise AssertionError(f"{label} carried a blocked binary/audio artifact path: {value}")
        lowered = value.lower()
        for forbidden in ["password", "session cookie", "license key", "serial number", "bearer "]:
            if forbidden in lowered:
                raise AssertionError(f"{label} carried credential-like text: {value}")


def expected_item_paths(catalog_id: str) -> dict[str, str]:
    prefix = catalog_id
    return {
        "request": f"{prefix}/installation-request.json",
        "receipt_template": f"{prefix}/receipt-template.json",
        "operator_evidence_draft": f"{prefix}/operator-evidence.json",
        "launch_plan": f"{prefix}/launch-plan.json",
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="library-installation-preflight-test-") as temp_dir:
        temp_root = Path(temp_dir)
        output_dir = temp_root / "library-installation"
        queue = load_json(QUEUE_PATH)
        queue_items = queue["queue"]

        prepare_result = run_command(
            [
                PYTHON,
                "scripts/prepare_library_installation_queue.py",
                "--queue",
                str(QUEUE_PATH),
                "--output-dir",
                str(output_dir),
                "--stable",
            ]
        )
        if prepare_result.returncode != 0:
            print(prepare_result.stdout, file=sys.stderr)
            print(prepare_result.stderr, file=sys.stderr)
            return prepare_result.returncode

        manifest_path = output_dir / "queue-manifest.json"
        if not manifest_path.exists():
            print("Library installation preflight must write queue-manifest.json.", file=sys.stderr)
            return 1
        manifest = load_json(manifest_path)
        if manifest.get("schema_version") != 1:
            print("Library installation preflight manifest must use schema_version 1.", file=sys.stderr)
            return 1
        if manifest.get("generated_at") != "1970-01-01T00:00:00Z":
            print("Library installation preflight manifest must use stable generated_at in stable mode.", file=sys.stderr)
            return 1
        if manifest.get("generator") != "scripts/prepare_library_installation_queue.py":
            print("Library installation preflight manifest generator is stale.", file=sys.stderr)
            return 1
        if manifest.get("execution_status") != "prepared_not_executed":
            print("Library installation preflight must not claim vendor actions executed.", file=sys.stderr)
            return 1
        if manifest.get("vendor_action_status") != "not_opened_not_logged_in_not_installed":
            print("Library installation preflight must not open vendor sessions.", file=sys.stderr)
            return 1
        if manifest.get("queue_source", {}).get("path") != "automation/generated/library-installation-queue.json":
            print("Library installation preflight manifest must reference the generated queue.", file=sys.stderr)
            return 1
        if manifest.get("artifact_root") != "external_output_override":
            print("Absolute temp output roots must be redacted in the manifest.", file=sys.stderr)
            return 1
        if manifest.get("item_count") != len(queue_items):
            print("Library installation preflight item count must mirror generated queue.", file=sys.stderr)
            return 1
        if [item.get("catalog_id") for item in manifest.get("items", [])] != [item.get("catalog_id") for item in queue_items]:
            print("Library installation preflight item order must mirror generated queue.", file=sys.stderr)
            return 1

        for manifest_item, queue_item in zip(manifest.get("items", []), queue_items, strict=False):
            catalog_id = queue_item["catalog_id"]
            if manifest_item.get("execution_status") != "prepared_not_executed":
                print(f"Preflight item must not claim execution: {catalog_id}", file=sys.stderr)
                return 1
            expected_paths = expected_item_paths(catalog_id)
            for key, rel_path in expected_paths.items():
                entry = manifest_item.get(key, {})
                if entry.get("path") != rel_path:
                    print(f"Preflight {key} path is stale for {catalog_id}.", file=sys.stderr)
                    return 1
                if not (output_dir / rel_path).exists():
                    print(f"Preflight missing {key} artifact for {catalog_id}.", file=sys.stderr)
                    return 1
                if not isinstance(entry.get("sha256"), str) or len(entry["sha256"]) != 64:
                    print(f"Preflight {key} must include a SHA-256 for {catalog_id}.", file=sys.stderr)
                    return 1

            request = load_json(output_dir / expected_paths["request"])
            receipt_template = load_json(output_dir / expected_paths["receipt_template"])
            evidence_draft = load_json(output_dir / expected_paths["operator_evidence_draft"])
            launch_plan = load_json(output_dir / expected_paths["launch_plan"])

            for field in ["catalog_id", "vendor", "name", "status", "source_url", "approval_gates_required"]:
                if request.get(field) != queue_item.get(field):
                    print(f"Preflight request {field} is stale for {catalog_id}.", file=sys.stderr)
                    return 1
            approval_state = request.get("approval_state", {})
            if set(approval_state) != set(queue_item.get("approval_gates_required", [])):
                print(f"Preflight request approval_state gates are stale for {catalog_id}.", file=sys.stderr)
                return 1
            if any(value != "required_not_granted" for value in approval_state.values()):
                print(f"Preflight request must not pregrant approval for {catalog_id}.", file=sys.stderr)
                return 1
            if request.get("execution_status") != "prepared_not_executed":
                print(f"Preflight request must not claim execution for {catalog_id}.", file=sys.stderr)
                return 1
            if request.get("ci_install_allowed") is not False or request.get("requires_human_confirmation") is not True:
                print(f"Preflight request must preserve CI/action gates for {catalog_id}.", file=sys.stderr)
                return 1

            if receipt_template.get("execution_status") != "template_not_applied":
                print(f"Receipt template must not claim execution for {catalog_id}.", file=sys.stderr)
                return 1
            if receipt_template.get("required_fields") != queue_item.get("receipt", {}).get("required_fields"):
                print(f"Receipt template fields are stale for {catalog_id}.", file=sys.stderr)
                return 1

            if evidence_draft.get("operator_approval_reference") != "":
                print(f"Evidence draft must not prefill approval reference for {catalog_id}.", file=sys.stderr)
                return 1
            if evidence_draft.get("purchase_or_license_change_reference") != "":
                print(f"Evidence draft must not prefill purchase/license reference for {catalog_id}.", file=sys.stderr)
                return 1
            if evidence_draft.get("action_outcome") != "not_attempted":
                print(f"Evidence draft action_outcome must start not_attempted for {catalog_id}.", file=sys.stderr)
                return 1
            if evidence_draft.get("post_action_validation") != queue_item.get("post_action_validation"):
                print(f"Evidence draft post-action validation is stale for {catalog_id}.", file=sys.stderr)
                return 1

            official_host = urlparse(queue_item["source_url"]).netloc.lower()
            if launch_plan.get("launch_status") != "blocked_until_operator_approval":
                print(f"Launch plan must block vendor action for {catalog_id}.", file=sys.stderr)
                return 1
            if launch_plan.get("official_surface", {}).get("source_url") != queue_item["source_url"]:
                print(f"Launch plan source URL is stale for {catalog_id}.", file=sys.stderr)
                return 1
            if official_host not in launch_plan.get("official_surface", {}).get("allowed_hosts", []):
                print(f"Launch plan must carry official allowed host for {catalog_id}.", file=sys.stderr)
                return 1
            if any("open " in value.lower() for value in iter_string_values(launch_plan)):
                print(f"Launch plan must not include executable open commands for {catalog_id}.", file=sys.stderr)
                return 1

            assert_no_sensitive_paths(request, "library request")
            assert_no_sensitive_paths(receipt_template, "library receipt template")
            assert_no_sensitive_paths(evidence_draft, "library evidence draft")
            assert_no_sensitive_paths(launch_plan, "library launch plan")

        first_item = queue_items[0]
        first_catalog_id = first_item["catalog_id"]
        first_request_path = output_dir / expected_item_paths(first_catalog_id)["request"]
        first_evidence_path = output_dir / expected_item_paths(first_catalog_id)["operator_evidence_draft"]
        invalid_result = run_command(
            [
                PYTHON,
                "scripts/record_library_installation_receipt.py",
                "--request",
                str(first_request_path),
                "--evidence",
                str(first_evidence_path),
                "--stable",
            ]
        )
        if invalid_result.returncode == 0:
            print("Receipt recorder must reject evidence without approval reference.", file=sys.stderr)
            return 1

        valid_evidence = load_json(first_evidence_path)
        valid_evidence.update(
            {
                "operator_approval_reference": APPROVAL_REFERENCE,
                "official_surface": "Ableton Live Browser > Packs",
                "entitlement_reference_redacted": "entitlement confirmed without account identifier",
                "purchase_or_license_change_reference": PURCHASE_REFERENCE_NOT_APPLICABLE,
                "inventory_before_sha256": manifest["inventory_source"]["sha256"],
                "inventory_after_sha256": manifest["inventory_source"]["sha256"],
                "observed_local_signal": first_item["local_signal"],
                "action_outcome": "deferred_no_install_performed",
                "performed_actions": ["reviewed_official_surface", "no_vendor_state_change"],
                "created_artifacts": [
                    {
                        "type": "redacted_vendor_action_note",
                        "reference": "operator confirmed no vendor state change",
                        "git_policy": "not_committed",
                    }
                ],
            }
        )
        write_json(first_evidence_path, valid_evidence)

        receipt_output_path = output_dir / first_catalog_id / "recorded-receipt.json"
        valid_result = run_command(
            [
                PYTHON,
                "scripts/record_library_installation_receipt.py",
                "--request",
                str(first_request_path),
                "--evidence",
                str(first_evidence_path),
                "--output",
                str(receipt_output_path),
                "--stable",
            ]
        )
        if valid_result.returncode != 0:
            print(valid_result.stdout, file=sys.stderr)
            print(valid_result.stderr, file=sys.stderr)
            return valid_result.returncode
        receipt = load_json(receipt_output_path)
        if receipt.get("execution_status") != "recorded_from_operator_evidence":
            print("Recorded receipt execution status is stale.", file=sys.stderr)
            return 1
        if receipt.get("operator_approval_reference") != APPROVAL_REFERENCE:
            print("Recorded receipt must carry operator approval reference.", file=sys.stderr)
            return 1
        if receipt.get("purchase_or_license_change_reference") != PURCHASE_REFERENCE_NOT_APPLICABLE:
            print("Recorded receipt must carry purchase/license-change reference.", file=sys.stderr)
            return 1
        if receipt.get("action_outcome") != "deferred_no_install_performed":
            print("Recorded receipt action outcome is stale.", file=sys.stderr)
            return 1
        assert_no_sensitive_paths(receipt, "library recorded receipt")

    print("Library installation preflight probes passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
