#!/usr/bin/env python3
"""Record a local-only Ableton Live 12 DAW mutation receipt from operator evidence."""

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
DEFAULT_OUTPUT_NAME = "applied-receipt.json"
STABLE_RECORDED_AT = "1970-01-01T00:00:00Z"
SECRET_VALUE_PATTERN = re.compile(r"(?:sk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]{20,})")
BLOCKED_ARTIFACT_EXTENSIONS = (".als", ".amxd", ".alp", ".wav", ".aiff", ".flac", ".mp3", ".m4a", ".ogg")


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


def local_reference(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return "external_path_redacted"


def validate_string_hygiene(data: dict[str, Any], label: str) -> list[str]:
    errors = []
    for value in iter_string_values(data):
        if "/Users/" in value or value.startswith(("~/", "file://")):
            errors.append(f"{label} must not contain absolute user paths: {value}")
        if "sources/public-domain/raw/" in value:
            errors.append(f"{label} must not contain raw source paths: {value}")
        if "/" in value and value.lower().endswith(BLOCKED_ARTIFACT_EXTENSIONS):
            errors.append(f"{label} must not contain blocked DAW/audio artifact paths: {value}")
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


def validate_evidence(request: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if request.get("execution_status") != "prepared_not_applied":
        errors.append("request execution_status must be prepared_not_applied")
    approval_state = request.get("approval_state", {})
    if approval_state.get("export_or_release") != "blocked_in_preflight":
        errors.append("request must keep export_or_release blocked in preflight")
    if request.get("midi_verification", {}).get("verified") is not True:
        errors.append("request MIDI verification must be true")

    require_non_empty_string(evidence.get("operator_approval_reference"), "operator_approval_reference", errors)
    require_non_empty_string(evidence.get("rollback_copy_reference"), "rollback_copy_reference", errors)
    applied_action_ids = require_string_list(evidence.get("applied_action_ids"), "applied_action_ids", errors)
    skipped_action_ids = require_string_list(evidence.get("skipped_action_ids"), "skipped_action_ids", errors)
    postflight_checks = require_string_list(evidence.get("postflight_checks"), "postflight_checks", errors)

    planned_ids = set(request.get("planned_action_ids", []))
    supplied_ids = set(applied_action_ids) | set(skipped_action_ids)
    unknown_ids = sorted(supplied_ids - planned_ids)
    if unknown_ids:
        errors.append(f"unknown action ids: {', '.join(unknown_ids)}")
    overlapping_ids = sorted(set(applied_action_ids) & set(skipped_action_ids))
    if overlapping_ids:
        errors.append(f"action ids cannot be both applied and skipped: {', '.join(overlapping_ids)}")
    unaccounted_ids = sorted(planned_ids - supplied_ids)
    if unaccounted_ids:
        errors.append(f"unaccounted action ids: {', '.join(unaccounted_ids)}")

    expected_checks = request.get("required_postflight_checks", [])
    if postflight_checks != expected_checks:
        errors.append("postflight_checks must exactly match request required_postflight_checks")

    created_artifacts = evidence.get("created_artifacts", [])
    if not isinstance(created_artifacts, list) or not all(isinstance(item, dict) for item in created_artifacts):
        errors.append("created_artifacts must be a list of objects")
    for artifact in created_artifacts if isinstance(created_artifacts, list) else []:
        if artifact.get("git_policy") != "not_committed":
            errors.append("created_artifacts entries must use git_policy not_committed")

    errors.extend(validate_string_hygiene(evidence, "operator evidence"))
    return errors


def build_receipt(
    request: dict[str, Any],
    evidence: dict[str, Any],
    request_path: Path,
    evidence_path: Path,
    recorded_at: str,
) -> dict[str, Any]:
    planned_ids = set(request.get("planned_action_ids", []))
    supplied_ids = set(evidence.get("applied_action_ids", [])) | set(evidence.get("skipped_action_ids", []))
    return {
        "schema_version": 1,
        "recorded_at": recorded_at,
        "generator": "scripts/record_live12_daw_mutation_receipt.py",
        "run_id": request["run_id"],
        "track_slug": request["track_slug"],
        "track_title": request["track_title"],
        "execution_status": "recorded_from_operator_evidence",
        "operator_approval_reference": evidence["operator_approval_reference"],
        "rollback_copy_reference": evidence["rollback_copy_reference"],
        "mutation_package_sha256": request["mutation_package_sha256"],
        "plan_track_sha256": request["plan_track_sha256"],
        "midi_verification": request["midi_verification"],
        "affected_tracks": request["affected_tracks"],
        "affected_returns": request["affected_returns"],
        "applied_action_ids": evidence["applied_action_ids"],
        "skipped_action_ids": evidence["skipped_action_ids"],
        "unaccounted_action_ids": sorted(planned_ids - supplied_ids),
        "required_postflight_checks": request["required_postflight_checks"],
        "created_artifacts": evidence.get("created_artifacts", []),
        "redactions": [
            "absolute local paths redacted or summarized",
            "private audio content excluded",
            "credentials, cookies, license files, and account artifacts excluded",
            "DAW binaries and audio artifacts excluded from Git",
        ],
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
    parser.add_argument("--request", required=True, type=Path, help="Prepared mutation-request.json path.")
    parser.add_argument("--evidence", required=True, type=Path, help="Operator evidence JSON path.")
    parser.add_argument("--output", type=Path, help="Output receipt JSON path.")
    parser.add_argument("--stable", action="store_true", help="Use deterministic recorded_at value.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request_path = args.request if args.request.is_absolute() else ROOT / args.request
    evidence_path = args.evidence if args.evidence.is_absolute() else ROOT / args.evidence
    if not request_path.exists():
        print(f"Missing mutation request: {args.request}", file=sys.stderr)
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
                "track_slug": receipt["track_slug"],
                "execution_status": receipt["execution_status"],
                "applied_action_count": len(receipt["applied_action_ids"]),
                "skipped_action_count": len(receipt["skipped_action_ids"]),
                "output": local_reference(output_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
