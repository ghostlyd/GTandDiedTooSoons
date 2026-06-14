#!/usr/bin/env python3
"""Validate repository contracts that do not require Ableton or Arturia installs."""

from __future__ import annotations

import json
import posixpath
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


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
    "sources/public-domain/download-ledger.json",
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
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
LEDGER_CATALOG_MIRRORED_FIELDS = ["name", "source_url", "rights_status", "credit_line", "browser_evidence", "rights_evidence"]


def https_host(value: str) -> str | None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return parsed.netloc.lower()


def host_matches(host: str, allowed_hosts: list[str]) -> bool:
    for allowed in allowed_hosts:
        allowed_lower = allowed.lower()
        if host == allowed_lower:
            return True
    return False


def allowed_path(path: str, prefixes: list[str]) -> bool:
    canonical_path = canonical_url_path(path)
    for prefix in prefixes:
        canonical_prefix = canonical_url_path(prefix)
        if canonical_path == canonical_prefix:
            return True
        prefix_with_boundary = canonical_prefix if canonical_prefix.endswith("/") else canonical_prefix + "/"
        if canonical_path.startswith(prefix_with_boundary):
            return True
    return False


def canonical_url_path(path: str) -> str:
    decoded = unquote(path)
    if any(segment in (".", "..") for segment in decoded.split("/")):
        raise ValueError(f"URL path contains dot segments: {path}")

    normalized = posixpath.normpath(decoded)
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    if decoded.endswith("/") and not normalized.endswith("/"):
        normalized += "/"
    if normalized != decoded:
        raise ValueError(f"URL path is not canonical: {path}")
    return normalized


def is_allowed_path(path: str, prefixes: list[str]) -> bool:
    try:
        return allowed_path(path, prefixes)
    except ValueError:
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
            allowed_prefixes = entry.get("allowed_download_path_prefixes") or []
            if not allowed_prefixes:
                fail(errors, f"Approved source missing allowed_download_path_prefixes: {entry.get('id')}")
            elif not is_allowed_path(urlparse(entry["download_url"]).path, allowed_prefixes):
                fail(errors, f"Approved source download path is not allowed for {entry.get('id')}")
            evidence = entry.get("browser_evidence") or {}
            for evidence_field in ["captured_url", "artifact_path", "captured_at"]:
                if not evidence.get(evidence_field):
                    fail(errors, f"Approved source missing browser_evidence.{evidence_field}: {entry.get('id')}")
            if evidence.get("captured_url") and not https_host(evidence["captured_url"]):
                fail(errors, f"browser_evidence.captured_url must be https for {entry.get('id')}")
            rights_evidence = entry.get("rights_evidence") or {}
            for evidence_field in ["evidence_url", "captured_at", "rights_summary", "reuse_scope", "credit_recommendation"]:
                if not rights_evidence.get(evidence_field):
                    fail(errors, f"Approved source missing rights_evidence.{evidence_field}: {entry.get('id')}")
            if rights_evidence.get("evidence_url") and not https_host(rights_evidence["evidence_url"]):
                fail(errors, f"rights_evidence.evidence_url must be https for {entry.get('id')}")


def validate_download_ledger(root: Path, errors: list[str]) -> None:
    ledger = load_json(root / "sources/public-domain/download-ledger.json", errors)
    catalog = load_json(root / "catalogs/public-domain-bluegrass-sources.json", errors)
    sources_by_id = {entry.get("id"): entry for entry in catalog.get("sources", []) if entry.get("id")}
    approved_sources = {
        entry.get("id"): entry
        for entry in catalog.get("sources", [])
        if entry.get("id") and entry.get("approved_for_download")
    }
    ledger_keys = {(record.get("source_id"), record.get("download_url")) for record in ledger.get("downloads", [])}

    for source_id, source in approved_sources.items():
        if (source_id, source.get("download_url")) not in ledger_keys:
            fail(errors, f"Approved source missing download ledger record: {source_id}")

    if ledger and ledger.get("schema_version") != 1:
        fail(errors, "sources/public-domain/download-ledger.json: expected schema_version 1")

    for record in ledger.get("downloads", []):
        for field in [
            "source_id",
            "name",
            "fetched_at",
            "local_file",
            "sha256",
            "byte_size",
            "source_url",
            "download_url",
            "rights_status",
            "credit_line",
            "browser_evidence",
            "rights_evidence",
            "transformation",
        ]:
            if field not in record or record[field] in ("", None):
                fail(errors, f"download ledger record missing {field}: {record}")

        source = sources_by_id.get(record.get("source_id"))
        if not source:
            fail(errors, f"download ledger source_id is not in catalog: {record.get('source_id')}")
            continue
        if not source.get("approved_for_download"):
            fail(errors, f"download ledger source is not approved in catalog: {record.get('source_id')}")
        if record.get("download_url") != source.get("download_url"):
            fail(errors, f"download ledger URL does not match catalog for {record.get('source_id')}")
        for field in LEDGER_CATALOG_MIRRORED_FIELDS:
            if record.get(field) != source.get(field):
                fail(errors, f"download ledger {field} does not match catalog for {record.get('source_id')}")
        if record.get("rights_status") not in DOWNLOADABLE_RIGHTS:
            fail(errors, f"download ledger has non-downloadable rights status: {record.get('source_id')}")
        if not https_host(record.get("source_url", "")):
            fail(errors, f"download ledger source_url must be https: {record.get('source_id')}")
        if not https_host(record.get("download_url", "")):
            fail(errors, f"download ledger download_url must be https: {record.get('source_id')}")
        final_url = record.get("final_url")
        if final_url and not https_host(final_url):
            fail(errors, f"download ledger final_url must be https when present: {record.get('source_id')}")
        if not isinstance(record.get("byte_size"), int) or record.get("byte_size", 0) <= 0:
            fail(errors, f"download ledger byte_size must be positive integer: {record.get('source_id')}")
        if not SHA256_PATTERN.match(str(record.get("sha256", ""))):
            fail(errors, f"download ledger sha256 must be lowercase hex SHA-256: {record.get('source_id')}")
        allowed_hosts = source.get("allowed_download_hosts") or []
        download_host = https_host(record.get("download_url", ""))
        if download_host and not host_matches(download_host, allowed_hosts):
            fail(errors, f"download ledger download host is not allowed: {record.get('source_id')}")
        final_host = https_host(record.get("final_url", "")) if record.get("final_url") else None
        if final_host and not host_matches(final_host, allowed_hosts):
            fail(errors, f"download ledger final host is not allowed: {record.get('source_id')}")
        allowed_prefixes = source.get("allowed_download_path_prefixes") or []
        download_path = urlparse(record.get("download_url", "")).path
        if not allowed_prefixes or not is_allowed_path(download_path, allowed_prefixes):
            fail(errors, f"download ledger download path is not allowed: {record.get('source_id')}")
        final_path = urlparse(record.get("final_url", "")).path if record.get("final_url") else None
        if final_path and not is_allowed_path(final_path, allowed_prefixes):
            fail(errors, f"download ledger final path is not allowed: {record.get('source_id')}")

        local_file = Path(str(record.get("local_file", "")))
        if local_file.is_absolute() or local_file.parts[:3] != ("sources", "public-domain", "raw"):
            fail(errors, f"download ledger local_file must be under sources/public-domain/raw/: {record.get('source_id')}")

        evidence = record.get("browser_evidence") or {}
        for evidence_field in ["captured_url", "artifact_path", "captured_at"]:
            if not evidence.get(evidence_field):
                fail(errors, f"download ledger missing browser_evidence.{evidence_field}: {record.get('source_id')}")
        if evidence.get("captured_url") and not https_host(evidence["captured_url"]):
            fail(errors, f"download ledger browser_evidence.captured_url must be https: {record.get('source_id')}")
        rights_evidence = record.get("rights_evidence") or {}
        for evidence_field in ["evidence_url", "captured_at", "rights_summary", "reuse_scope", "credit_recommendation"]:
            if not rights_evidence.get(evidence_field):
                fail(errors, f"download ledger missing rights_evidence.{evidence_field}: {record.get('source_id')}")
        if rights_evidence.get("evidence_url") and not https_host(rights_evidence["evidence_url"]):
            fail(errors, f"download ledger rights_evidence.evidence_url must be https: {record.get('source_id')}")


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


def validate_tracked_raw_source_files(root: Path, errors: list[str]) -> None:
    result = subprocess.run(
        ["git", "ls-files", "sources/public-domain/raw"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        fail(errors, f"Unable to inspect tracked raw source files: {result.stderr.strip()}")
        return

    allowed = {"sources/public-domain/raw/.gitkeep"}
    for rel in result.stdout.splitlines():
        if rel not in allowed:
            fail(errors, f"Raw source file must not be tracked: {rel}")


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
    validate_download_ledger(root, errors)
    validate_json_contracts(root, errors)
    validate_binary_hygiene(root, errors)
    validate_tracked_raw_source_files(root, errors)

    if errors:
        print("Repository validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
