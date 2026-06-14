#!/usr/bin/env python3
"""Validate repository contracts that do not require Ableton or Arturia installs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_FILES = [
    "README.md",
    "LICENSE",
    "AGENTS.md",
    ".github/workflows/live12-foundation-ci.yml",
    "docs/production-system.md",
    "docs/live12-m4l-ci-cd.md",
    "docs/openai-orchestration.md",
    "docs/source-acquisition-policy.md",
    "docs/playwright-source-capture.md",
    "docs/recommended-packs.md",
    "catalogs/recommended-packs.json",
    "catalogs/public-domain-bluegrass-sources.json",
    "automation/live12-session-template.json",
    "automation/worker-chain.json",
    "compositions/down-tempo-punk-bluegrass-set.json",
    "scripts/inventory_live_suite.py",
    "scripts/fetch_public_domain_audio.py",
]

SECRET_NAMES = {".env", "id_rsa", "id_ed25519", "license.key"}
BLOCKED_EXTENSIONS = {
    ".alp",
    ".als",
    ".amxd",
    ".app",
    ".aif",
    ".aiff",
    ".component",
    ".flac",
    ".m4a",
    ".mp3",
    ".ogg",
    ".vst3",
    ".wav",
}
RIGHTS_STATUSES = {"public_domain", "cc0", "cc_by", "no_known_restrictions", "rights_assessment_required", "research_only"}
DOWNLOADABLE_RIGHTS = {"public_domain", "cc0", "cc_by", "no_known_restrictions"}
SKIP_BINARY_SCAN_PARTS = {".git", "output", "__pycache__"}


def https_host(value: str) -> str | None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return parsed.netloc.lower()


def host_matches(host: str, allowed_hosts: list[str]) -> bool:
    for allowed in allowed_hosts:
        allowed_lower = allowed.lower()
        if host == allowed_lower or host.endswith("." + allowed_lower):
            return True
    return False


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - validator should report any parse/read problem.
        fail(errors, f"{path}: {exc}")
        return {}


def validate_required_files(root: Path, errors: list[str]) -> None:
    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            fail(errors, f"Missing required file: {rel}")


def validate_recommended_packs(root: Path, errors: list[str]) -> None:
    data = load_json(root / "catalogs/recommended-packs.json", errors)
    ids = set()
    for item in data.get("items", []):
        for field in ["id", "vendor", "name", "priority", "status", "source_url", "license_action", "project_use"]:
            if not item.get(field):
                fail(errors, f"recommended-packs item missing {field}: {item}")
        if item.get("id") in ids:
            fail(errors, f"Duplicate recommended pack id: {item.get('id')}")
        ids.add(item.get("id"))
        if not str(item.get("source_url", "")).startswith("https://"):
            fail(errors, f"Pack source_url must be https: {item.get('id')}")


def validate_sources(root: Path, errors: list[str]) -> None:
    data = load_json(root / "catalogs/public-domain-bluegrass-sources.json", errors)
    ids = set()
    for entry in data.get("sources", []):
        for field in ["id", "name", "type", "source_url", "rights_status", "approved_for_download", "credit_line", "project_use"]:
            if field not in entry or entry[field] in ("", None):
                fail(errors, f"source entry missing {field}: {entry}")
        if entry.get("id") in ids:
            fail(errors, f"Duplicate source id: {entry.get('id')}")
        ids.add(entry.get("id"))
        if entry.get("rights_status") not in RIGHTS_STATUSES:
            fail(errors, f"Unknown rights_status for {entry.get('id')}: {entry.get('rights_status')}")
        source_host = https_host(entry.get("source_url", ""))
        if not source_host:
            fail(errors, f"source_url must be an https URL: {entry.get('id')}")
        if entry.get("approved_for_download"):
            if entry.get("rights_status") not in DOWNLOADABLE_RIGHTS:
                fail(errors, f"Approved source has non-downloadable rights status: {entry.get('id')}")
            if not entry.get("download_url"):
                fail(errors, f"Approved source is missing download_url: {entry.get('id')}")
                continue
            download_host = https_host(entry["download_url"])
            if not download_host:
                fail(errors, f"Approved source download_url must be https: {entry.get('id')}")
                continue
            allowed_hosts = entry.get("allowed_download_hosts") or ([source_host] if source_host else [])
            if not host_matches(download_host, allowed_hosts):
                fail(errors, f"Approved source download host is not allowed for {entry.get('id')}: {download_host}")
            evidence = entry.get("browser_evidence") or {}
            for evidence_field in ["captured_url", "artifact_path", "captured_at"]:
                if not evidence.get(evidence_field):
                    fail(errors, f"Approved source missing browser_evidence.{evidence_field}: {entry.get('id')}")
            if evidence.get("captured_url") and not https_host(evidence["captured_url"]):
                fail(errors, f"browser_evidence.captured_url must be https for {entry.get('id')}")


def validate_binary_hygiene(root: Path, errors: list[str]) -> None:
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if any(part in SKIP_BINARY_SCAN_PARTS for part in rel.parts):
            continue
        if rel.parts[:3] == ("sources", "public-domain", "raw") and path.name != ".gitkeep":
            continue
        if path.is_dir():
            continue
        if path.name in SECRET_NAMES:
            fail(errors, f"Potential secret committed: {rel}")
        if path.suffix.lower() in BLOCKED_EXTENSIONS:
            fail(errors, f"Blocked binary/commercial asset committed: {rel}")


def validate_json_contracts(root: Path, errors: list[str]) -> None:
    for rel in [
        "automation/live12-session-template.json",
        "automation/worker-chain.json",
        "compositions/down-tempo-punk-bluegrass-set.json",
    ]:
        data = load_json(root / rel, errors)
        if data and data.get("schema_version") != 1:
            fail(errors, f"{rel}: expected schema_version 1")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []

    validate_required_files(root, errors)
    validate_recommended_packs(root, errors)
    validate_sources(root, errors)
    validate_json_contracts(root, errors)
    validate_binary_hygiene(root, errors)

    if errors:
        print("Repository validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
