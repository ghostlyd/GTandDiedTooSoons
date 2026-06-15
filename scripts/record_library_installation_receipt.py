#!/usr/bin/env python3
"""Record a local-only library/account action receipt from operator evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_NAME = "receipt.json"
STABLE_RECORDED_AT = "1970-01-01T00:00:00Z"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SECRET_VALUE_PATTERN = re.compile(r"(?:sk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]{20,})")
BLOCKED_ARTIFACT_EXTENSIONS = (".als", ".amxd", ".alp", ".wav", ".aiff", ".flac", ".mp3", ".m4a", ".ogg")
ACTION_OUTCOMES = {
    "installed_or_enabled",
    "already_present_confirmed",
    "deferred_no_install_performed",
    "skipped_no_entitlement",
    "blocked_pending_purchase_approval",
    "failed_vendor_error",
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


def local_reference(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "external_path_redacted"


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


def validate_string_hygiene(data: dict[str, Any], label: str) -> list[str]:
    errors = []
    for value in iter_string_values(data):
        if "/Users/" in value or "/Applications/" in value or value.startswith(("~/", "file://")):
            errors.append(f"{label} must not contain local absolute paths or file URLs: {value}")
        if "sources/public-domain/raw/" in value:
            errors.append(f"{label} must not contain raw source paths: {value}")
        if "/" in value and value.lower().endswith(BLOCKED_ARTIFACT_EXTENSIONS):
            errors.append(f"{label} must not contain DAW, installer, or audio artifact paths: {value}")
        if SECRET_VALUE_PATTERN.search(value):
            errors.append(f"{label} must not contain API tokens or bearer credentials")
    return errors


def require_non_empty_string(value: object, field: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} is required")
        return ""
    return value.strip()


def require_string_list(value: object, field: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        errors.append(f"{field} must be a list of non-empty strings")
        return []
    return value


def require_sha256(value: object, field: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not SHA256_PATTERN.match(value):
        errors.append(f"{field} must be a lowercase SHA-256")
        return ""
    return value


def validate_created_artifacts(value: object, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        errors.append("created_artifacts must be a list of objects")
        return []
    for artifact in value:
        if artifact.get("git_policy") != "not_committed":
            errors.append("created_artifacts entries must use git_policy not_committed")
        require_non_empty_string(artifact.get("type"), "created_artifacts.type", errors)
        require_non_empty_string(artifact.get("reference"), "created_artifacts.reference", errors)
    return value


def validate_evidence(request: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if request.get("execution_status") != "prepared_not_executed":
        errors.append("request execution_status must be prepared_not_executed")
    if request.get("vendor_action_status") != "not_opened_not_logged_in_not_installed":
        errors.append("request must begin from not_opened_not_logged_in_not_installed")
    if request.get("ci_install_allowed") is not False:
        errors.append("request must block CI installs")

    for gate, state in request.get("approval_state", {}).items():
        if state != "required_not_granted":
            errors.append(f"request approval state must not be pregranted: {gate}")
    require_non_empty_string(evidence.get("operator_approval_reference"), "operator_approval_reference", errors)
    require_non_empty_string(evidence.get("official_surface"), "official_surface", errors)
    require_non_empty_string(evidence.get("entitlement_reference_redacted"), "entitlement_reference_redacted", errors)
    require_non_empty_string(evidence.get("purchase_or_license_change_reference"), "purchase_or_license_change_reference", errors)
    require_sha256(evidence.get("inventory_before_sha256"), "inventory_before_sha256", errors)
    require_sha256(evidence.get("inventory_after_sha256"), "inventory_after_sha256", errors)
    require_non_empty_string(evidence.get("observed_local_signal"), "observed_local_signal", errors)
    performed_actions = require_string_list(evidence.get("performed_actions"), "performed_actions", errors)
    post_action_validation = require_string_list(evidence.get("post_action_validation"), "post_action_validation", errors)
    action_outcome = require_non_empty_string(evidence.get("action_outcome"), "action_outcome", errors)
    if action_outcome and action_outcome not in ACTION_OUTCOMES:
        errors.append(f"unsupported action_outcome: {action_outcome}")
    if post_action_validation != request.get("post_action_validation"):
        errors.append("post_action_validation must exactly match request")
    if not performed_actions:
        errors.append("performed_actions must account for the attempted or deferred operator action")
    validate_created_artifacts(evidence.get("created_artifacts"), errors)
    errors.extend(validate_string_hygiene(evidence, "operator evidence"))
    return errors


def build_receipt(
    request: dict[str, Any],
    evidence: dict[str, Any],
    request_path: Path,
    evidence_path: Path,
    recorded_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "recorded_at": recorded_at,
        "generator": "scripts/record_library_installation_receipt.py",
        "run_id": request["run_id"],
        "catalog_id": request["catalog_id"],
        "vendor": request["vendor"],
        "name": request["name"],
        "execution_status": "recorded_from_operator_evidence",
        "action_outcome": evidence["action_outcome"],
        "operator_approval_reference": evidence["operator_approval_reference"],
        "source_url": request["source_url"],
        "official_surface": evidence["official_surface"],
        "entitlement_reference_redacted": evidence["entitlement_reference_redacted"],
        "purchase_or_license_change_reference": evidence["purchase_or_license_change_reference"],
        "inventory_before_sha256": evidence["inventory_before_sha256"],
        "inventory_after_sha256": evidence["inventory_after_sha256"],
        "observed_local_signal": evidence["observed_local_signal"],
        "performed_actions": evidence["performed_actions"],
        "created_artifacts": evidence["created_artifacts"],
        "redactions": [
            "credentials excluded",
            "account identifiers redacted",
            "commercial assets excluded from Git",
            "local artifact paths summarized",
        ],
        "post_action_validation": evidence["post_action_validation"],
        "approval_gates_required": request["approval_gates_required"],
        "source_request": {
            "path": local_reference(request_path),
            "sha256": sha256_file(request_path),
        },
        "source_evidence": {
            "path": local_reference(evidence_path),
            "sha256": sha256_file(evidence_path),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path, help="Prepared installation-request.json path.")
    parser.add_argument("--evidence", required=True, type=Path, help="Operator evidence JSON path.")
    parser.add_argument("--output", type=Path, help="Output receipt JSON path.")
    parser.add_argument("--stable", action="store_true", help="Use deterministic recorded_at value.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request_path = args.request if args.request.is_absolute() else ROOT / args.request
    evidence_path = args.evidence if args.evidence.is_absolute() else ROOT / args.evidence
    if not request_path.exists():
        print(f"Missing library installation request: {args.request}", file=sys.stderr)
        return 1
    if not evidence_path.exists():
        print(f"Missing operator evidence: {args.evidence}", file=sys.stderr)
        return 1

    request = read_json(request_path)
    evidence = read_json(evidence_path)
    errors = validate_evidence(request, evidence)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    recorded_at = STABLE_RECORDED_AT if args.stable else utc_now()
    receipt = build_receipt(request, evidence, request_path, evidence_path, recorded_at)
    output_path = args.output
    if output_path is None:
        output_path = request_path.parent / DEFAULT_OUTPUT_NAME
    elif not output_path.is_absolute():
        output_path = ROOT / output_path
    write_json(output_path, receipt)
    print(
        json.dumps(
            {
                "catalog_id": receipt["catalog_id"],
                "execution_status": receipt["execution_status"],
                "action_outcome": receipt["action_outcome"],
                "output": local_reference(output_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
