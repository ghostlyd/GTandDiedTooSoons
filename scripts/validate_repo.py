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
    "catalogs/library-installation-plan.json",
    "catalogs/public-domain-bluegrass-sources.json",
    "automation/openai-production-orchestration.json",
    "automation/generated/openai-worker-briefs.json",
    "automation/live12-session-template.json",
    "automation/worker-chain.json",
    "compositions/down-tempo-punk-bluegrass-set.json",
    "scripts/inventory_live_suite.py",
    "scripts/fetch_public_domain_audio.py",
    "scripts/render_openai_worker_briefs.py",
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
PACK_VENDORS = {"Ableton", "Arturia"}
PACK_PRIORITIES = {"high", "medium", "low"}
RECOMMENDED_PACK_STATUSES = {
    "observed_local",
    "installed",
    "live_database_available_not_installed",
    "account_login_required",
    "account_or_purchase_required",
    "official_free_not_installed",
}
INSTALL_PLAN_STATUSES = {
    "live_database_available_not_installed",
    "account_login_required",
    "account_or_purchase_required",
    "official_free_not_installed",
    "official_free_download_manual_install",
}
LOCAL_RECOMMENDATION_STATUSES = {"observed_local", "installed"}
OFFICIAL_PACK_HOSTS = {
    "Ableton": {"www.ableton.com"},
    "Arturia": {"www.arturia.com"},
}
OFFICIAL_OPENAI_DOC_HOSTS = {"developers.openai.com", "openai.github.io"}
OPENAI_API_SURFACES = {"responses_api", "agents_sdk", "realtime_api", "audio_transcription", "apps_sdk_mcp"}
OPENAI_DATA_CLASSES = {
    "public_repo_metadata",
    "local_inventory",
    "public_domain_metadata",
    "private_rehearsal_audio",
    "account_credentials",
    "licensed_assets",
}
OPENAI_TOOL_CONTRACTS = {
    "read_inventory",
    "validate_source_rights",
    "render_worker_brief",
    "propose_session_change",
    "automate_vendor_install",
    "automate_daw_session",
    "render_release_checklist",
}
OPENAI_APPROVAL_GATES = {
    "source_download",
    "private_audio_upload",
    "vendor_account_action",
    "purchase_or_license_change",
    "live_set_mutation",
    "export_or_release",
}
EXPECTED_WORKER_BRIEF_SOURCES = {
    "automation/openai-production-orchestration.json",
    "automation/worker-chain.json",
    "automation/live12-session-template.json",
    "compositions/down-tempo-punk-bluegrass-set.json",
    "catalogs/public-domain-bluegrass-sources.json",
    "catalogs/library-installation-plan.json",
    "inventory/live12-local-inventory.json",
}
AUDIO_PATH_PATTERN = re.compile(r"(?:^|[/\\\s])[\w .~/-]+\.(?:aif|aiff|flac|m4a|mp3|ogg|wav)\b", re.IGNORECASE)
SECRET_VALUE_PATTERN = re.compile(r"(?:sk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]{20,})")


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
    install_plan = load_json(root / "catalogs/library-installation-plan.json", errors)
    install_plan_ids = {item.get("id") for item in install_plan.get("items", []) if item.get("id")}
    ids = set()
    for item in data.get("items", []):
        for field in ["id", "vendor", "name", "priority", "status", "source_url", "license_action", "project_use"]:
            if not item.get(field):
                fail(errors, f"recommended-packs item missing {field}: {item}")
        if item.get("id") in ids:
            fail(errors, f"Duplicate recommended pack id: {item.get('id')}")
        ids.add(item.get("id"))
        if item.get("vendor") not in PACK_VENDORS:
            fail(errors, f"Unknown recommended pack vendor: {item.get('id')}: {item.get('vendor')}")
        if item.get("priority") not in PACK_PRIORITIES:
            fail(errors, f"Unknown recommended pack priority: {item.get('id')}: {item.get('priority')}")
        if item.get("status") not in RECOMMENDED_PACK_STATUSES:
            fail(errors, f"Unknown recommended pack status: {item.get('id')}: {item.get('status')}")
        source_host = https_host(item.get("source_url", ""))
        if not source_host:
            fail(errors, f"Pack source_url must be https: {item.get('id')}")
        elif source_host not in OFFICIAL_PACK_HOSTS.get(item.get("vendor"), set()):
            fail(errors, f"Pack source_url must use official {item.get('vendor')} host: {item.get('id')}: {source_host}")
        if item.get("status") not in LOCAL_RECOMMENDATION_STATUSES and item.get("id") not in install_plan_ids:
            fail(errors, f"Non-local recommended pack missing from installation plan: {item.get('id')}")


def validate_library_installation_plan(root: Path, errors: list[str]) -> None:
    data = load_json(root / "catalogs/library-installation-plan.json", errors)
    if data and data.get("schema_version") != 1:
        fail(errors, "catalogs/library-installation-plan.json: expected schema_version 1")

    ids = set()
    for item in data.get("items", []):
        for field in ["id", "vendor", "name", "priority", "status", "source_url", "install_route", "local_signal", "project_use"]:
            if not item.get(field):
                fail(errors, f"library installation plan item missing {field}: {item}")
        if item.get("id") in ids:
            fail(errors, f"Duplicate library installation plan id: {item.get('id')}")
        ids.add(item.get("id"))
        if item.get("vendor") not in PACK_VENDORS:
            fail(errors, f"Unknown library installation plan vendor: {item.get('id')}: {item.get('vendor')}")
        if item.get("priority") not in PACK_PRIORITIES:
            fail(errors, f"Unknown library installation plan priority: {item.get('id')}: {item.get('priority')}")
        if item.get("status") not in INSTALL_PLAN_STATUSES:
            fail(errors, f"Unknown library installation plan status: {item.get('id')}: {item.get('status')}")
        source_host = https_host(item.get("source_url", ""))
        if not source_host:
            fail(errors, f"Library installation plan source_url must be https: {item.get('id')}")
        elif source_host not in OFFICIAL_PACK_HOSTS.get(item.get("vendor"), set()):
            fail(errors, f"Library installation plan source_url must use official {item.get('vendor')} host: {item.get('id')}: {source_host}")


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
        "automation/openai-production-orchestration.json",
        "automation/generated/openai-worker-briefs.json",
        "automation/live12-session-template.json",
        "automation/worker-chain.json",
        "compositions/down-tempo-punk-bluegrass-set.json",
    ]:
        data = load_json(root / rel, errors)
        if data and data.get("schema_version") != 1:
            fail(errors, f"{rel}: expected schema_version 1")


def validate_openai_orchestration(root: Path, errors: list[str]) -> None:
    data = load_json(root / "automation/openai-production-orchestration.json", errors)
    if not data:
        return

    docs = data.get("official_docs_consulted", [])
    if not docs:
        fail(errors, "OpenAI orchestration contract must list official docs consulted")
    for doc_url in docs:
        host = https_host(doc_url)
        if host not in OFFICIAL_OPENAI_DOC_HOSTS:
            fail(errors, f"OpenAI docs URL must use an official OpenAI docs host: {doc_url}")

    api_surface_ids = set()
    for surface in data.get("api_surfaces", []):
        for field in ["id", "name", "use", "guardrails"]:
            if not surface.get(field):
                fail(errors, f"OpenAI api surface missing {field}: {surface}")
        surface_id = surface.get("id")
        if surface_id in api_surface_ids:
            fail(errors, f"Duplicate OpenAI api surface id: {surface_id}")
        api_surface_ids.add(surface_id)
        if surface_id not in OPENAI_API_SURFACES:
            fail(errors, f"Unknown OpenAI api surface id: {surface_id}")
        if not isinstance(surface.get("guardrails"), list):
            fail(errors, f"OpenAI api surface guardrails must be a list: {surface_id}")

    data_class_ids = set()
    for data_class in data.get("data_classes", []):
        for field in ["id", "examples", "allowed_in_repo", "allowed_for_openai", "notes"]:
            if field not in data_class or data_class[field] in ("", None):
                fail(errors, f"OpenAI data class missing {field}: {data_class}")
        data_class_id = data_class.get("id")
        if data_class_id in data_class_ids:
            fail(errors, f"Duplicate OpenAI data class id: {data_class_id}")
        data_class_ids.add(data_class_id)
        if data_class_id not in OPENAI_DATA_CLASSES:
            fail(errors, f"Unknown OpenAI data class id: {data_class_id}")
        if data_class_id in {"account_credentials", "licensed_assets"}:
            if data_class.get("allowed_in_repo") is not False or data_class.get("allowed_for_openai") is not False:
                fail(errors, f"{data_class_id} must be blocked from repo and OpenAI use")
        if data_class_id == "private_rehearsal_audio" and data_class.get("allowed_in_repo") is not False:
            fail(errors, "private_rehearsal_audio must be blocked from repo storage")

    tool_ids = set()
    for tool in data.get("tool_contracts", []):
        for field in ["id", "input_scope", "output", "approval_required", "must_not"]:
            if field not in tool or tool[field] in ("", None):
                fail(errors, f"OpenAI tool contract missing {field}: {tool}")
        tool_id = tool.get("id")
        if tool_id in tool_ids:
            fail(errors, f"Duplicate OpenAI tool contract id: {tool_id}")
        tool_ids.add(tool_id)
        if tool_id not in OPENAI_TOOL_CONTRACTS:
            fail(errors, f"Unknown OpenAI tool contract id: {tool_id}")
        if not isinstance(tool.get("approval_required"), bool):
            fail(errors, f"OpenAI tool contract approval_required must be boolean: {tool_id}")
        if not isinstance(tool.get("input_scope"), list) or not isinstance(tool.get("must_not"), list):
            fail(errors, f"OpenAI tool contract input_scope and must_not must be lists: {tool_id}")
        for scope in tool.get("input_scope", []):
            if Path(scope).is_absolute() or ".." in Path(scope).parts:
                fail(errors, f"OpenAI tool contract input_scope must be repo-relative: {tool_id}: {scope}")
            elif not (root / scope).exists():
                fail(errors, f"OpenAI tool contract input_scope does not exist: {tool_id}: {scope}")
    for required_tool in ["automate_vendor_install", "automate_daw_session", "propose_session_change"]:
        matching = [tool for tool in data.get("tool_contracts", []) if tool.get("id") == required_tool]
        if not matching or matching[0].get("approval_required") is not True:
            fail(errors, f"{required_tool} must require approval")

    gate_ids = set()
    for gate in data.get("approval_gates", []):
        for field in ["id", "trigger", "required_evidence", "approver"]:
            if not gate.get(field):
                fail(errors, f"OpenAI approval gate missing {field}: {gate}")
        gate_id = gate.get("id")
        if gate_id in gate_ids:
            fail(errors, f"Duplicate OpenAI approval gate id: {gate_id}")
        gate_ids.add(gate_id)
        if gate_id not in OPENAI_APPROVAL_GATES:
            fail(errors, f"Unknown OpenAI approval gate id: {gate_id}")
        if not isinstance(gate.get("required_evidence"), list):
            fail(errors, f"OpenAI approval gate required_evidence must be a list: {gate_id}")

    bridge = data.get("max_for_live_bridge") or {}
    for field in ["strategy", "allowed_outputs", "blocked_outputs", "rollback_path"]:
        if not bridge.get(field):
            fail(errors, f"max_for_live_bridge missing {field}")


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


def validate_generated_worker_briefs(root: Path, errors: list[str]) -> None:
    data = load_json(root / "automation/generated/openai-worker-briefs.json", errors)
    orchestration = load_json(root / "automation/openai-production-orchestration.json", errors)
    worker_chain = load_json(root / "automation/worker-chain.json", errors)
    if not data or not worker_chain:
        return

    source_files = set(data.get("source_files", []))
    if source_files != EXPECTED_WORKER_BRIEF_SOURCES:
        fail(errors, "Generated OpenAI worker briefs source_files must match expected source manifests")
    for source_file in source_files:
        if Path(source_file).is_absolute() or ".." in Path(source_file).parts or not (root / source_file).exists():
            fail(errors, f"Generated OpenAI worker brief source file is invalid: {source_file}")
    if data.get("generator") != "scripts/render_openai_worker_briefs.py":
        fail(errors, "Generated OpenAI worker briefs must name scripts/render_openai_worker_briefs.py as generator")

    role_ids = [role.get("id") for role in worker_chain.get("roles", [])]
    brief_ids = [brief.get("role_id") for brief in data.get("briefs", [])]
    if brief_ids != role_ids:
        fail(errors, "Generated OpenAI worker brief role order must match automation/worker-chain.json")

    handoff_order = worker_chain.get("handoff_order", [])
    tool_ids = {tool.get("id") for tool in orchestration.get("tool_contracts", [])}
    gate_ids = {gate.get("id") for gate in orchestration.get("approval_gates", [])}
    surface_ids = {surface.get("id") for surface in orchestration.get("api_surfaces", [])}

    for index, brief in enumerate(data.get("briefs", [])):
        role_id = brief.get("role_id")
        for field in [
            "role_id",
            "role_name",
            "mission",
            "owns",
            "allowed_inputs",
            "local_only_inputs",
            "expected_outputs",
            "must_not",
            "suggested_openai_surface",
            "tool_contracts",
            "repo_context",
            "approval_required",
            "track_context",
            "live_session_context",
        ]:
            if field not in brief or brief[field] in ("", None):
                fail(errors, f"Generated OpenAI worker brief missing {field}: {role_id}")
        expected_handoff = handoff_order[index + 1] if index + 1 < len(handoff_order) else None
        if brief.get("handoff_to") != expected_handoff:
            fail(errors, f"Generated OpenAI worker brief has wrong handoff: {role_id}")
        for rel in brief.get("allowed_inputs", []):
            if Path(rel).is_absolute() or ".." in Path(rel).parts or not (root / rel).exists():
                fail(errors, f"Generated OpenAI worker brief allowed_input must be repo-relative metadata: {role_id}: {rel}")
        surface_id = (brief.get("suggested_openai_surface") or {}).get("id")
        if surface_id not in surface_ids:
            fail(errors, f"Generated OpenAI worker brief references unknown surface: {role_id}: {surface_id}")
        for tool in brief.get("tool_contracts", []):
            if tool.get("id") not in tool_ids:
                fail(errors, f"Generated OpenAI worker brief references unknown tool: {role_id}: {tool.get('id')}")
        for gate in brief.get("approval_required", []):
            if gate.get("id") not in gate_ids:
                fail(errors, f"Generated OpenAI worker brief references unknown approval gate: {role_id}: {gate.get('id')}")
        for rel in brief.get("repo_context", []):
            if Path(rel).is_absolute() or ".." in Path(rel).parts or not (root / rel).exists():
                fail(errors, f"Generated OpenAI worker brief repo_context is invalid: {role_id}: {rel}")

    for string_value in iter_string_values(data):
        if "/Users/" in string_value:
            fail(errors, "Generated OpenAI worker briefs must not contain absolute user paths")
        if "sources/public-domain/raw/" in string_value or AUDIO_PATH_PATTERN.search(string_value):
            fail(errors, f"Generated OpenAI worker briefs must not contain raw audio paths: {string_value}")
        if SECRET_VALUE_PATTERN.search(string_value):
            fail(errors, "Generated OpenAI worker briefs must not contain API tokens or bearer credentials")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []

    validate_required_files(root, errors)
    validate_recommended_packs(root, errors)
    validate_library_installation_plan(root, errors)
    validate_sources(root, errors)
    validate_download_ledger(root, errors)
    validate_json_contracts(root, errors)
    validate_openai_orchestration(root, errors)
    validate_generated_worker_briefs(root, errors)
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
