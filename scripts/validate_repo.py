#!/usr/bin/env python3
"""Validate repository contracts that do not require Ableton or Arturia installs."""

from __future__ import annotations

import hashlib
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
    "docs/openai-production-swarm-queue.md",
    "docs/source-acquisition-policy.md",
    "docs/playwright-source-capture.md",
    "docs/recommended-packs.md",
    "docs/live12-daw-mutation-runbook.md",
    "docs/live12-daw-mutation-queue-runbook.md",
    "docs/public-domain-source-deck.md",
    "catalogs/recommended-packs.json",
    "catalogs/library-installation-plan.json",
    "catalogs/public-domain-bluegrass-sources.json",
    "automation/openai-production-orchestration.json",
    "automation/max-for-live-device-contracts.json",
    "automation/generated/openai-worker-briefs.json",
    "automation/generated/openai-production-swarm-queue.json",
    "automation/generated/live12-daw-action-plan.json",
    "automation/generated/live12-daw-mutation-package.json",
    "automation/generated/live12-daw-mutation-runbook.json",
    "automation/generated/live12-daw-mutation-queue-runbook.json",
    "automation/generated/public-domain-source-deck.json",
    "automation/generated/max-for-live-device-contracts.json",
    "automation/live12-session-template.json",
    "automation/worker-chain.json",
    "compositions/down-tempo-punk-bluegrass-set.json",
    "compositions/generated/README.md",
    "compositions/generated/live12-track-build-plans.json",
    "scripts/inventory_live_suite.py",
    "scripts/fetch_public_domain_audio.py",
    "scripts/render_composition_sketches.py",
    "scripts/render_openai_production_swarm_queue.py",
    "scripts/render_live12_daw_action_plan.py",
    "scripts/render_live12_daw_mutation_package.py",
    "scripts/render_live12_daw_mutation_runbook.py",
    "scripts/render_live12_daw_mutation_queue_runbook.py",
    "scripts/render_public_domain_source_deck.py",
    "scripts/render_max_for_live_device_contracts.py",
    "scripts/prepare_live12_daw_mutation.py",
    "scripts/prepare_live12_daw_mutation_queue.py",
    "scripts/stage_live12_daw_import_bundle.py",
    "scripts/record_live12_daw_mutation_receipt.py",
    "scripts/render_openai_worker_briefs.py",
    "scripts/test_openai_production_swarm_queue.py",
    "scripts/test_max_for_live_device_contracts.py",
    "scripts/test_live12_daw_mutation_preflight.py",
    "scripts/test_live12_daw_mutation_runbook.py",
    "scripts/test_live12_daw_mutation_queue_runbook.py",
    "scripts/test_public_domain_source_deck.py",
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
DOWNLOADABLE_RIGHTS = {"public_domain", "cc0", "cc_by"}
SKIP_BINARY_SCAN_PARTS = {".git", "output", "__pycache__"}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
LEDGER_CATALOG_MIRRORED_FIELDS = ["name", "source_url", "rights_status", "credit_line", "browser_evidence", "rights_evidence"]
PACK_VENDORS = {"Ableton", "Arturia"}
PACK_PRIORITIES = {"high", "medium", "low"}
INVENTORY_SCHEMA_VERSION = 1
LIVE_DATABASE_READ_STATUSES = {"ok", "degraded"}
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
    "automation/generated/live12-daw-mutation-package.json",
    "compositions/down-tempo-punk-bluegrass-set.json",
    "catalogs/public-domain-bluegrass-sources.json",
    "catalogs/library-installation-plan.json",
    "inventory/live12-local-inventory.json",
}
EXPECTED_OPENAI_SWARM_QUEUE_SOURCES = {
    "automation/openai-production-orchestration.json",
    "automation/worker-chain.json",
    "automation/generated/openai-worker-briefs.json",
    "automation/generated/live12-daw-mutation-package.json",
    "automation/generated/live12-daw-mutation-queue-runbook.json",
    "automation/generated/public-domain-source-deck.json",
    "compositions/generated/live12-track-build-plans.json",
}
EXPECTED_COMPOSITION_SKETCH_SOURCES = {
    "compositions/down-tempo-punk-bluegrass-set.json",
    "automation/live12-session-template.json",
}
EXPECTED_DAW_ACTION_PLAN_SOURCES = {
    "automation/openai-production-orchestration.json",
    "automation/live12-session-template.json",
    "compositions/down-tempo-punk-bluegrass-set.json",
    "compositions/generated/live12-track-build-plans.json",
    "catalogs/public-domain-bluegrass-sources.json",
    "sources/public-domain/download-ledger.json",
    "inventory/live12-local-inventory.json",
}
EXPECTED_PUBLIC_DOMAIN_SOURCE_DECK_SOURCES = {
    "catalogs/public-domain-bluegrass-sources.json",
    "sources/public-domain/download-ledger.json",
    "automation/generated/live12-daw-action-plan.json",
}
EXPECTED_DAW_MUTATION_PACKAGE_SOURCES = {
    "automation/generated/live12-daw-action-plan.json",
    "automation/live12-session-template.json",
    "compositions/generated/live12-track-build-plans.json",
}
EXPECTED_DAW_MUTATION_RUNBOOK_SOURCES = {
    "automation/generated/live12-daw-mutation-package.json",
    "automation/generated/live12-daw-action-plan.json",
    "automation/generated/max-for-live-device-contracts.json",
}
EXPECTED_DAW_MUTATION_QUEUE_RUNBOOK_SOURCES = {
    "automation/generated/live12-daw-mutation-package.json",
    "automation/generated/max-for-live-device-contracts.json",
    "scripts/prepare_live12_daw_mutation_queue.py",
    "scripts/stage_live12_daw_import_bundle.py",
    "scripts/record_live12_daw_mutation_receipt.py",
}
EXPECTED_DAW_APPROVAL_GATES = {"private_audio_upload", "live_set_mutation", "export_or_release"}
REQUIRED_DAW_ACTION_GROUP_GATES = {
    "session_actions": "live_set_mutation",
    "scene_actions": "live_set_mutation",
    "layer_actions": "live_set_mutation",
    "mix_and_release_gates": "export_or_release",
}
EXPECTED_DAW_MUTATION_TOP_LEVEL_KEYS = {
    "composition_set",
    "generated_at",
    "generator",
    "jobs",
    "live_template",
    "purpose",
    "receipt_contract",
    "safety",
    "schema_version",
    "source_file_sha256",
    "source_files",
    "source_plan",
}
EXPECTED_DAW_MUTATION_SAFETY_KEYS = {
    "local_only",
    "must_not",
    "requires_operator_approval_before_execution",
}
EXPECTED_DAW_MUTATION_RECEIPT_CONTRACT_KEYS = {
    "git_policy",
    "output_root",
    "prohibited_artifacts",
    "required_fields",
    "required_postflight_checks",
}
EXPECTED_DAW_MUTATION_APPROVAL_BOUNDARIES = [
    "Live-set mutation",
    "Max for Live device mutation",
    "private audio upload",
    "export or release",
]
EXPECTED_DAW_MUTATION_MUST_NOT = [
    "commit .als, .amxd, .alp, plugins, presets, samples, renders, credentials, cookies, or license files",
    "mark a mutation applied before Ableton Live or Max for Live confirms the change",
    "load unapproved source audio into the Public Domain Source Deck",
    "export or publish from a mutation preflight run",
]
EXPECTED_DAW_MUTATION_JOB_KEYS = {
    "affected_returns",
    "affected_tracks",
    "approval_gates_required",
    "approval_required_before_execution",
    "blocked_action_groups",
    "executable_action_groups",
    "executable_action_ids",
    "execution_mode",
    "id",
    "local_output_policy",
    "midi_artifact",
    "mutation_action_count",
    "plan_track_sha256",
    "preflight_action_ids",
    "rollback",
    "source_deck_policy",
    "track_slug",
    "track_title",
}
EXPECTED_DAW_MUTATION_RECEIPT_FIELDS = [
    "run_id",
    "track_slug",
    "track_title",
    "execution_status",
    "operator_approval_reference",
    "rollback_copy_reference",
    "mutation_package_sha256",
    "plan_track_sha256",
    "midi_verification",
    "affected_tracks",
    "affected_returns",
    "applied_action_ids",
    "skipped_action_ids",
    "required_postflight_checks",
    "created_artifacts",
    "redactions",
]
EXPECTED_DAW_MUTATION_POSTFLIGHT_CHECKS = [
    "rollback copy exists outside Git before mutation",
    "generated MIDI hash matched before import",
    "affected tracks match mutation package scope",
    "Public Domain Source Deck remains muted until provenance review",
    "no export, render, .als, .amxd, sample, preset, credential, cookie, or license artifact is committed",
    "python3 scripts/validate_repo.py passes after metadata updates",
]
EXPECTED_DAW_MUTATION_PROHIBITED_ARTIFACTS = [
    ".als",
    ".amxd",
    ".alp",
    "plugins",
    "presets",
    "samples",
    "renders",
    "credentials",
    "cookies",
    "license files",
    "private audio",
]
EXPECTED_DAW_MUTATION_LOCAL_OUTPUT_POLICY = {
    "receipt_root": "output/daw-mutations",
    "git_policy": "ignored_local_only",
}
EXPECTED_DAW_MUTATION_EXECUTION_MODE = "local_preflight_then_human_approved_daw_mutation"
EXPECTED_DAW_MUTATION_EXECUTABLE_GROUPS = ["session_actions", "scene_actions", "layer_actions", "source_deck"]
EXPECTED_DAW_MUTATION_BLOCKED_GROUPS = ["mix_and_release_gates"]
EXPECTED_DAW_MUTATION_RUNBOOK_TOP_LEVEL_KEYS = {
    "approval_policy",
    "artifact_policy",
    "composition_set",
    "execution_status",
    "generated_at",
    "generator",
    "live_template",
    "phase_contract",
    "purpose",
    "queue_command",
    "schema_version",
    "source_file_sha256",
    "source_files",
    "total_planned_action_count",
    "track_count",
    "tracks",
}
EXPECTED_DAW_MUTATION_RUNBOOK_PHASE_ORDER = [
    "preflight",
    "stage_import_bundle",
    "apply_live_mutation",
    "record_receipt",
    "postflight",
]
EXPECTED_DAW_MUTATION_RUNBOOK_REQUIRED_FLAGS = [
    "--launch-ableton",
    "--confirm-live-mutation",
    "--operator-approval-reference",
    "--rollback-copy-reference",
]
EXPECTED_DAW_MUTATION_RUNBOOK_TRACK_KEYS = {
    "affected_returns",
    "affected_tracks",
    "approval_required_before_execution",
    "blocked_action_groups",
    "commands",
    "execution_status",
    "max_for_live_device_ids",
    "max_for_live_devices",
    "midi_artifact",
    "operator_evidence",
    "operator_phase_order",
    "planned_action_count",
    "postflight_checks",
    "queue_order",
    "source_deck_policy",
    "track_slug",
    "track_title",
}
STABLE_GENERATED_AT = "1970-01-01T00:00:00Z"
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


def as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def as_list(value: object) -> list:
    return value if isinstance(value, list) else []


def require_dict(value: object, label: str, errors: list[str]) -> dict:
    if not isinstance(value, dict):
        fail(errors, f"{label} must be an object")
        return {}
    return value


def require_list(value: object, label: str, errors: list[str]) -> list:
    if not isinstance(value, list):
        fail(errors, f"{label} must be a list")
        return []
    return value


def require_non_empty_string(value: object, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value:
        fail(errors, f"{label} must be a non-empty string")


def require_optional_string(value: object, label: str, errors: list[str]) -> None:
    if value is not None and not isinstance(value, str):
        fail(errors, f"{label} must be a string or null")


def require_bool(value: object, label: str, errors: list[str]) -> None:
    if not isinstance(value, bool):
        fail(errors, f"{label} must be a boolean")


def validate_string_items(values: list, label: str, errors: list[str]) -> None:
    for index, item in enumerate(values):
        if not isinstance(item, str) or not item:
            fail(errors, f"{label}[{index}] must be a non-empty string")


def validate_named_path_items(values: list, label: str, errors: list[str]) -> None:
    for index, item in enumerate(values):
        if not isinstance(item, dict):
            fail(errors, f"{label}[{index}] must be an object")
            continue
        for field in ["name", "path"]:
            require_non_empty_string(item.get(field), f"{label}[{index}].{field}", errors)


def validate_plugin_root_items(values: list, label: str, errors: list[str]) -> None:
    for index, item in enumerate(values):
        if not isinstance(item, dict):
            fail(errors, f"{label}[{index}] must be an object")
            continue
        require_non_empty_string(item.get("path"), f"{label}[{index}].path", errors)
        require_bool(item.get("exists"), f"{label}[{index}].exists", errors)
        arturia_plugins = require_list(item.get("arturia_plugins"), f"{label}[{index}].arturia_plugins", errors)
        validate_string_items(arturia_plugins, f"{label}[{index}].arturia_plugins", errors)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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
        "automation/generated/live12-daw-action-plan.json",
        "automation/generated/live12-daw-mutation-package.json",
        "automation/generated/live12-daw-mutation-runbook.json",
        "automation/generated/live12-daw-mutation-queue-runbook.json",
        "automation/generated/openai-production-swarm-queue.json",
        "automation/generated/public-domain-source-deck.json",
        "automation/live12-session-template.json",
        "automation/worker-chain.json",
        "compositions/down-tempo-punk-bluegrass-set.json",
    ]:
        data = load_json(root / rel, errors)
        if data and data.get("schema_version") != 1:
            fail(errors, f"{rel}: expected schema_version 1")


def validate_inventory_snapshot(root: Path, errors: list[str]) -> None:
    data = require_dict(
        load_json(root / "inventory/live12-local-inventory.json", errors),
        "inventory/live12-local-inventory.json",
        errors,
    )
    schema_version = data.get("schema_version")
    if isinstance(schema_version, bool) or not isinstance(schema_version, int) or schema_version != INVENTORY_SCHEMA_VERSION:
        fail(errors, "inventory/live12-local-inventory.json: expected schema_version 1")

    ableton = require_dict(data.get("ableton"), "inventory.ableton", errors)
    arturia = require_dict(data.get("arturia"), "inventory.arturia", errors)
    plugins = require_dict(data.get("plugins"), "inventory.plugins", errors)

    ableton_app = require_dict(ableton.get("app"), "inventory.ableton.app", errors)
    require_non_empty_string(ableton_app.get("name"), "inventory.ableton.app.name", errors)
    require_non_empty_string(ableton_app.get("path"), "inventory.ableton.app.path", errors)
    require_bool(ableton_app.get("exists"), "inventory.ableton.app.exists", errors)
    if "version" not in ableton_app:
        fail(errors, "inventory.ableton.app missing version")
    else:
        require_optional_string(ableton_app.get("version"), "inventory.ableton.app.version", errors)

    validate_named_path_items(
        require_list(ableton.get("factory_packs"), "inventory.ableton.factory_packs", errors),
        "inventory.ableton.factory_packs",
        errors,
    )
    live_database = require_dict(ableton.get("live_database"), "inventory.ableton.live_database", errors)
    for field in ["installed_pack_places", "indexed_pack_candidates", "available_not_installed", "read_errors"]:
        validate_string_items(
            require_list(live_database.get(field), f"inventory.ableton.live_database.{field}", errors),
            f"inventory.ableton.live_database.{field}",
            errors,
        )
    for field in ["file_database", "file_database_exists", "read_status"]:
        if field not in live_database:
            fail(errors, f"inventory.ableton.live_database missing {field}")
    require_non_empty_string(live_database.get("file_database"), "inventory.ableton.live_database.file_database", errors)
    require_bool(live_database.get("file_database_exists"), "inventory.ableton.live_database.file_database_exists", errors)
    require_non_empty_string(live_database.get("read_status"), "inventory.ableton.live_database.read_status", errors)
    if live_database.get("read_status") not in LIVE_DATABASE_READ_STATUSES:
        fail(errors, f"inventory.ableton.live_database.read_status is unsupported: {live_database.get('read_status')}")

    validate_named_path_items(
        require_list(arturia.get("applications"), "inventory.arturia.applications", errors),
        "inventory.arturia.applications",
        errors,
    )
    resources = require_dict(arturia.get("resources"), "inventory.arturia.resources", errors)
    for field in ["products", "preset_products", "sample_products"]:
        validate_string_items(
            require_list(resources.get(field), f"inventory.arturia.resources.{field}", errors),
            f"inventory.arturia.resources.{field}",
            errors,
        )
    for field in ["resource_root", "resource_root_exists", "preset_root", "sample_root"]:
        if field not in resources:
            fail(errors, f"inventory.arturia.resources missing {field}")
    require_non_empty_string(resources.get("resource_root"), "inventory.arturia.resources.resource_root", errors)
    require_bool(resources.get("resource_root_exists"), "inventory.arturia.resources.resource_root_exists", errors)
    require_non_empty_string(resources.get("preset_root"), "inventory.arturia.resources.preset_root", errors)
    require_non_empty_string(resources.get("sample_root"), "inventory.arturia.resources.sample_root", errors)

    validate_plugin_root_items(
        require_list(plugins.get("vst3_roots"), "inventory.plugins.vst3_roots", errors),
        "inventory.plugins.vst3_roots",
        errors,
    )
    validate_plugin_root_items(
        require_list(plugins.get("audio_unit_roots"), "inventory.plugins.audio_unit_roots", errors),
        "inventory.plugins.audio_unit_roots",
        errors,
    )


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
    daw_tools = [tool for tool in data.get("tool_contracts", []) if tool.get("id") == "automate_daw_session"]
    if daw_tools and "automation/generated/live12-daw-action-plan.json" not in daw_tools[0].get("input_scope", []):
        fail(errors, "automate_daw_session input_scope must include automation/generated/live12-daw-action-plan.json")

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
    inventory = as_dict(load_json(root / "inventory/live12-local-inventory.json", errors))
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

    project_context = require_dict(data.get("project_context"), "Generated OpenAI worker briefs project_context", errors)
    inventory_summary = require_dict(
        project_context.get("inventory_summary"),
        "Generated OpenAI worker briefs inventory_summary",
        errors,
    )
    ableton = as_dict(inventory.get("ableton"))
    live_database = as_dict(ableton.get("live_database"))
    factory_packs = as_list(ableton.get("factory_packs"))
    ableton_app = as_dict(ableton.get("app"))
    arturia = as_dict(inventory.get("arturia"))
    arturia_resources = as_dict(arturia.get("resources"))
    expected_inventory_summary = {
        "ableton_live": {
            "exists": ableton_app.get("exists", False),
            "name": ableton_app.get("name"),
            "version": ableton_app.get("version"),
            "factory_pack_count": len(factory_packs),
            "installed_factory_packs": [
                item.get("name") for item in factory_packs if isinstance(item, dict) and item.get("name")
            ],
            "indexed_pack_candidate_count": len(as_list(live_database.get("indexed_pack_candidates"))),
            "available_not_installed_count": len(as_list(live_database.get("available_not_installed"))),
            "live_database_read_status": live_database.get("read_status", "unknown"),
        },
        "arturia": {
            "application_count": len(as_list(arturia.get("applications"))),
            "resource_product_count": len(as_list(arturia_resources.get("products"))),
            "preset_product_folder_count": len(as_list(arturia_resources.get("preset_products"))),
            "sample_product_folder_count": len(as_list(arturia_resources.get("sample_products"))),
        },
    }
    if inventory_summary != expected_inventory_summary:
        fail(errors, "Generated OpenAI worker briefs inventory_summary must match inventory/live12-local-inventory.json")

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


def validate_openai_production_swarm_queue(root: Path, errors: list[str]) -> None:
    data = load_json(root / "automation/generated/openai-production-swarm-queue.json", errors)
    markdown_path = root / "docs/openai-production-swarm-queue.md"
    orchestration = load_json(root / "automation/openai-production-orchestration.json", errors)
    worker_briefs = load_json(root / "automation/generated/openai-worker-briefs.json", errors)
    mutation_package = load_json(root / "automation/generated/live12-daw-mutation-package.json", errors)
    queue_runbook = load_json(root / "automation/generated/live12-daw-mutation-queue-runbook.json", errors)
    source_deck = load_json(root / "automation/generated/public-domain-source-deck.json", errors)
    build_plans = load_json(root / "compositions/generated/live12-track-build-plans.json", errors)
    if not data or not worker_briefs or not mutation_package or not queue_runbook or not build_plans:
        return

    if data.get("schema_version") != 1:
        fail(errors, "Generated OpenAI production swarm queue must use schema_version 1")
    if data.get("generated_at") != STABLE_GENERATED_AT:
        fail(errors, "Generated OpenAI production swarm queue must be committed with stable generated_at")
    if data.get("generator") != "scripts/render_openai_production_swarm_queue.py":
        fail(errors, "Generated OpenAI production swarm queue must name scripts/render_openai_production_swarm_queue.py as generator")

    source_files = set(data.get("source_files", []))
    if source_files != EXPECTED_OPENAI_SWARM_QUEUE_SOURCES:
        fail(errors, "Generated OpenAI production swarm queue source_files must match expected source manifests")
    source_hashes = data.get("source_file_sha256") or {}
    if set(source_hashes) != EXPECTED_OPENAI_SWARM_QUEUE_SOURCES:
        fail(errors, "Generated OpenAI production swarm queue source_file_sha256 keys must match expected source manifests")
    for source_file in source_files:
        if Path(source_file).is_absolute() or ".." in Path(source_file).parts or not (root / source_file).exists():
            fail(errors, f"Generated OpenAI production swarm queue source file is invalid: {source_file}")
            continue
        expected_hash = source_hashes.get(source_file)
        if not SHA256_PATTERN.match(str(expected_hash or "")):
            fail(errors, f"Generated OpenAI production swarm queue source hash is invalid: {source_file}")
        elif expected_hash != sha256_file(root / source_file):
            fail(errors, f"Generated OpenAI production swarm queue source hash is stale: {source_file}")

    queue_policy = require_dict(data.get("queue_policy"), "Generated OpenAI production swarm queue queue_policy", errors)
    if queue_policy.get("execution_status") != "planned_not_executed":
        fail(errors, "Generated OpenAI production swarm queue must stay planned_not_executed")
    if queue_policy.get("api_execution_status") != "not_called_ci_safe":
        fail(errors, "Generated OpenAI production swarm queue must not require OpenAI API calls in CI")
    if queue_policy.get("git_policy") != "metadata_only_no_private_audio":
        fail(errors, "Generated OpenAI production swarm queue must use metadata_only_no_private_audio git policy")
    if queue_policy.get("credentials_required_for_generation") is not False:
        fail(errors, "Generated OpenAI production swarm queue generation must not require credentials")
    if queue_policy.get("local_output_root") != "output/openai-swarm":
        fail(errors, "Generated OpenAI production swarm queue local_output_root is stale")
    if not OPENAI_APPROVAL_GATES.issubset(set(queue_policy.get("blocked_without_approval", []))):
        fail(errors, "Generated OpenAI production swarm queue must block all OpenAI approval gates before execution")
    if "OpenAI API keys" not in queue_policy.get("must_not_commit", []):
        fail(errors, "Generated OpenAI production swarm queue must block API key commits")

    role_ids = [brief.get("role_id") for brief in worker_briefs.get("briefs", [])]
    if data.get("role_order") != role_ids:
        fail(errors, "Generated OpenAI production swarm queue role_order must mirror worker briefs")
    jobs = mutation_package.get("jobs", [])
    build_tracks = build_plans.get("tracks", [])
    if [track.get("slug") for track in build_tracks] != [job.get("track_slug") for job in jobs]:
        fail(errors, "Generated OpenAI production swarm queue source track order inputs disagree")
    if data.get("track_count") != len(jobs):
        fail(errors, "Generated OpenAI production swarm queue track_count must mirror mutation package")
    if data.get("role_count") != len(role_ids):
        fail(errors, "Generated OpenAI production swarm queue role_count must mirror worker briefs")
    if data.get("task_count") != len(jobs) * len(role_ids):
        fail(errors, "Generated OpenAI production swarm queue task_count must equal tracks times roles")

    surface_ids = {surface.get("id") for surface in orchestration.get("api_surfaces", [])}
    tool_ids = {tool.get("id") for tool in orchestration.get("tool_contracts", [])}
    gate_ids = {gate.get("id") for gate in orchestration.get("approval_gates", [])}
    queue_tracks_by_slug = {track.get("track_slug"): track for track in queue_runbook.get("tracks", [])}
    source_assignments_by_slug = {assignment.get("track_slug"): assignment for assignment in source_deck.get("track_assignments", [])}
    worker_briefs_by_role = {brief.get("role_id"): brief for brief in worker_briefs.get("briefs", [])}

    tracks = data.get("tracks", [])
    if [track.get("track_slug") for track in tracks] != [job.get("track_slug") for job in jobs]:
        fail(errors, "Generated OpenAI production swarm queue track order must mirror mutation package")
    for track, job, build_track in zip(tracks, jobs, build_tracks, strict=False):
        slug = job.get("track_slug")
        if track.get("track_slug") != build_track.get("slug") or track.get("track_title") != build_track.get("title"):
            fail(errors, f"Generated OpenAI production swarm queue track identity is stale: {slug}")
        if track.get("mutation_job_id") != job.get("id"):
            fail(errors, f"Generated OpenAI production swarm queue mutation job id is stale: {slug}")
        if track.get("planned_daw_action_count") != job.get("mutation_action_count"):
            fail(errors, f"Generated OpenAI production swarm queue planned DAW action count is stale: {slug}")
        source_assignment = source_assignments_by_slug.get(slug, {})
        if track.get("source_deck_state") != source_assignment.get("deck_state"):
            fail(errors, f"Generated OpenAI production swarm queue source deck state is stale: {slug}")
        if track.get("source_candidate_ids") != source_assignment.get("candidate_source_ids", []):
            fail(errors, f"Generated OpenAI production swarm queue source candidate ids are stale: {slug}")
        queue_track = queue_tracks_by_slug.get(slug, {})
        expected_daw_queue = {
            "request_path": queue_track.get("request_path"),
            "bundle_manifest_path": queue_track.get("bundle_manifest_path"),
            "launch_plan_path": queue_track.get("launch_plan_path"),
            "launch_status": queue_runbook.get("queue_policy", {}).get("launch_status"),
        }
        if track.get("daw_queue") != expected_daw_queue:
            fail(errors, f"Generated OpenAI production swarm queue DAW queue refs are stale: {slug}")

        tasks = track.get("tasks", [])
        if [task.get("role_id") for task in tasks] != role_ids:
            fail(errors, f"Generated OpenAI production swarm queue task order must mirror role order: {slug}")
        for index, task in enumerate(tasks, start=1):
            role_id = task.get("role_id")
            brief = worker_briefs_by_role.get(role_id, {})
            expected_task_id = f"{slug}.{role_id}.{index:02d}"
            if task.get("task_id") != expected_task_id:
                fail(errors, f"Generated OpenAI production swarm queue task id is stale: {expected_task_id}")
            if task.get("sequence") != index or task.get("execution_status") != "not_started":
                fail(errors, f"Generated OpenAI production swarm queue task execution state is stale: {expected_task_id}")
            surface_id = (task.get("suggested_openai_surface") or {}).get("id")
            if surface_id not in surface_ids:
                fail(errors, f"Generated OpenAI production swarm queue task references unknown OpenAI surface: {expected_task_id}")
            if set(task.get("tool_contract_ids", [])) - tool_ids:
                fail(errors, f"Generated OpenAI production swarm queue task references unknown tool contract: {expected_task_id}")
            if set(task.get("approval_gate_ids", [])) - gate_ids:
                fail(errors, f"Generated OpenAI production swarm queue task references unknown approval gate: {expected_task_id}")
            expected_depends = [] if index == 1 else [tasks[index - 2].get("task_id")]
            if task.get("depends_on") != expected_depends:
                fail(errors, f"Generated OpenAI production swarm queue task dependency is stale: {expected_task_id}")
            expected_handoff = None if index == len(tasks) else tasks[index].get("task_id")
            if task.get("handoff_to_task_id") != expected_handoff:
                fail(errors, f"Generated OpenAI production swarm queue task handoff is stale: {expected_task_id}")
            for rel in task.get("allowed_repo_inputs", []):
                path = Path(str(rel))
                if path.is_absolute() or ".." in path.parts or not (root / path).exists():
                    fail(errors, f"Generated OpenAI production swarm queue allowed input is invalid: {expected_task_id}: {rel}")
            output_policy = task.get("local_output_policy", {})
            output_path = Path(str(output_policy.get("path", "")))
            if output_path.parts[:2] != ("output", "openai-swarm") or output_policy.get("git_policy") != "ignored_local_only":
                fail(errors, f"Generated OpenAI production swarm queue output policy must stay ignored local-only: {expected_task_id}")
            prompt_packet = task.get("prompt_packet", {})
            if prompt_packet.get("brief_ref") != f"automation/generated/openai-worker-briefs.json#role_id={role_id}":
                fail(errors, f"Generated OpenAI production swarm queue prompt brief ref is stale: {expected_task_id}")
            if "call OpenAI APIs from CI" not in prompt_packet.get("must_not", []):
                fail(errors, f"Generated OpenAI production swarm queue prompt guardrails must block CI API calls: {expected_task_id}")
            if task.get("expected_outputs") != brief.get("expected_outputs", []):
                fail(errors, f"Generated OpenAI production swarm queue expected outputs are stale: {expected_task_id}")

    markdown = markdown_path.read_text(encoding="utf-8") if markdown_path.exists() else ""
    for expected_text in [
        "# OpenAI Production Swarm Queue",
        "planned_not_executed",
        "No OpenAI API call is made by this renderer or CI check.",
        "Agents SDK handoffs",
        "Responses API structured outputs",
    ]:
        if expected_text not in markdown:
            fail(errors, f"Generated OpenAI production swarm queue markdown is missing required text: {expected_text}")

    for string_value in iter_string_values(data):
        if "/Users/" in string_value:
            fail(errors, "Generated OpenAI production swarm queue must not contain absolute user paths")
        if "sources/public-domain/raw/" in string_value or AUDIO_PATH_PATTERN.search(string_value):
            fail(errors, f"Generated OpenAI production swarm queue must not contain raw audio paths: {string_value}")
        if SECRET_VALUE_PATTERN.search(string_value):
            fail(errors, "Generated OpenAI production swarm queue must not contain API tokens or bearer credentials")
    if "/Users/" in markdown or "sources/public-domain/raw/" in markdown or SECRET_VALUE_PATTERN.search(markdown):
        fail(errors, "Generated OpenAI production swarm queue markdown contains sensitive local data")


def validate_generated_daw_action_plan(root: Path, errors: list[str]) -> None:
    data = load_json(root / "automation/generated/live12-daw-action-plan.json", errors)
    orchestration = load_json(root / "automation/openai-production-orchestration.json", errors)
    session_template = load_json(root / "automation/live12-session-template.json", errors)
    compositions = load_json(root / "compositions/down-tempo-punk-bluegrass-set.json", errors)
    composition_plans = load_json(root / "compositions/generated/live12-track-build-plans.json", errors)
    source_catalog = load_json(root / "catalogs/public-domain-bluegrass-sources.json", errors)
    source_ledger = load_json(root / "sources/public-domain/download-ledger.json", errors)
    inventory = as_dict(load_json(root / "inventory/live12-local-inventory.json", errors))
    if not data or not session_template or not composition_plans:
        return

    if data.get("schema_version") != 1:
        fail(errors, "Generated DAW action plan must use schema_version 1")
    if data.get("generated_at") != STABLE_GENERATED_AT:
        fail(errors, "Generated DAW action plan must be committed with stable generated_at")
    if data.get("generator") != "scripts/render_live12_daw_action_plan.py":
        fail(errors, "Generated DAW action plan must name scripts/render_live12_daw_action_plan.py as generator")

    source_files = set(data.get("source_files", []))
    if source_files != EXPECTED_DAW_ACTION_PLAN_SOURCES:
        fail(errors, "Generated DAW action plan source_files must match expected source manifests")
    source_hashes = data.get("source_file_sha256") or {}
    for source_file in source_files:
        if Path(source_file).is_absolute() or ".." in Path(source_file).parts or not (root / source_file).exists():
            fail(errors, f"Generated DAW action plan source file is invalid: {source_file}")
            continue
        expected_hash = source_hashes.get(source_file)
        if not SHA256_PATTERN.match(str(expected_hash or "")):
            fail(errors, f"Generated DAW action plan source hash is invalid: {source_file}")
        elif expected_hash != sha256_file(root / source_file):
            fail(errors, f"Generated DAW action plan source hash is stale: {source_file}")

    safety = require_dict(data.get("safety"), "Generated DAW action plan safety", errors)
    if safety.get("proposal_only") is not True:
        fail(errors, "Generated DAW action plan safety.proposal_only must be true")
    for field in ["requires_human_approval_before", "must_not"]:
        validate_string_items(require_list(safety.get(field), f"Generated DAW action plan safety.{field}", errors), f"Generated DAW action plan safety.{field}", errors)

    tool_contract = require_dict(data.get("openai_tool_contract"), "Generated DAW action plan openai_tool_contract", errors)
    if tool_contract.get("id") != "automate_daw_session" or tool_contract.get("approval_required") is not True:
        fail(errors, "Generated DAW action plan must bind to the approval-required automate_daw_session tool")
    orchestration_daw_tools = [tool for tool in orchestration.get("tool_contracts", []) if tool.get("id") == "automate_daw_session"]
    if not orchestration_daw_tools:
        fail(errors, "Generated DAW action plan cannot find automate_daw_session in orchestration contract")
    elif tool_contract.get("source_contract") != orchestration_daw_tools[0]:
        fail(errors, "Generated DAW action plan source_contract must mirror automate_daw_session")

    live_template = require_dict(data.get("live_template"), "Generated DAW action plan live_template", errors)
    if live_template.get("name") != session_template.get("name"):
        fail(errors, "Generated DAW action plan live_template.name must match session template")
    if live_template.get("target_runtime") != session_template.get("target_runtime"):
        fail(errors, "Generated DAW action plan live_template.target_runtime must match session template")
    if live_template.get("tempo_range_bpm") != session_template.get("tempo_range_bpm"):
        fail(errors, "Generated DAW action plan live_template tempo_range_bpm must match session template")
    if live_template.get("track_count") != len(session_template.get("tracks", [])):
        fail(errors, "Generated DAW action plan live_template.track_count is stale")
    if live_template.get("return_count") != len(session_template.get("returns", [])):
        fail(errors, "Generated DAW action plan live_template.return_count is stale")

    ableton = as_dict(inventory.get("ableton"))
    arturia = as_dict(inventory.get("arturia"))
    expected_inventory_summary = {
        "ableton_live_version": as_dict(ableton.get("app")).get("version"),
        "factory_pack_count": len(as_list(ableton.get("factory_packs"))),
        "arturia_application_count": len(as_list(arturia.get("applications"))),
    }
    if data.get("inventory_summary") != expected_inventory_summary:
        fail(errors, "Generated DAW action plan inventory_summary must match inventory/live12-local-inventory.json")

    approved_sources = {
        source.get("id"): source
        for source in source_catalog.get("sources", [])
        if source.get("id") and source.get("approved_for_download")
    }
    ledger_by_source = {
        record.get("source_id"): record
        for record in source_ledger.get("downloads", [])
        if record.get("source_id")
    }
    approved_pool = data.get("approved_source_pool", [])
    pool_ids = {entry.get("source_id") for entry in approved_pool}
    pool_by_id = {entry.get("source_id"): entry for entry in approved_pool if entry.get("source_id")}
    if pool_ids != set(approved_sources).intersection(ledger_by_source):
        fail(errors, "Generated DAW action plan approved_source_pool must match approved source ledger records")
    for source_entry in approved_pool:
        source_id = source_entry.get("source_id")
        record = ledger_by_source.get(source_id, {})
        source = approved_sources.get(source_id, {})
        for field in ["name", "rights_status", "credit_line", "sha256", "byte_size"]:
            if source_entry.get(field) != record.get(field):
                fail(errors, f"Generated DAW action plan source pool {field} is stale for {source_id}")
        if source_entry.get("project_use") != source.get("project_use"):
            fail(errors, f"Generated DAW action plan source pool project_use is stale for {source_id}")

    source_track_titles = [track.get("title") for track in compositions.get("tracks", [])]
    generated_track_titles = [track.get("title") for track in data.get("tracks", [])]
    build_plan_track_titles = [track.get("title") for track in composition_plans.get("tracks", [])]
    if generated_track_titles != source_track_titles or generated_track_titles != build_plan_track_titles:
        fail(errors, "Generated DAW action plan track order must match composition and generated build plans")

    tempo_range = session_template.get("tempo_range_bpm", [0, 999])
    session_tracks = {track.get("name"): track for track in session_template.get("tracks", [])}
    session_returns = session_template.get("returns", [])
    build_plans_by_slug = {track.get("slug"): track for track in composition_plans.get("tracks", [])}
    all_action_ids = set()

    for track in data.get("tracks", []):
        title = track.get("title")
        slug = track.get("slug")
        build_plan = build_plans_by_slug.get(slug)
        if not build_plan:
            fail(errors, f"Generated DAW action plan track slug is not in build plans: {slug}")
            continue
        for field in ["tempo_bpm", "key_center", "duration_target", "midi_file", "midi_sha256", "approximate_bars"]:
            if track.get(field) != build_plan.get(field):
                fail(errors, f"Generated DAW action plan track {field} is stale: {title}")
        if not tempo_range[0] <= track.get("tempo_bpm", 0) <= tempo_range[1]:
            fail(errors, f"Generated DAW action plan tempo is outside session range: {title}")
        actual_approval_gates = set()

        for action_group in ["preflight_actions", "session_actions", "scene_actions", "layer_actions", "mix_and_release_gates"]:
            actions = require_list(track.get(action_group), f"Generated DAW action plan {title}.{action_group}", errors)
            for action in actions:
                action_id = action.get("id")
                if not action_id:
                    fail(errors, f"Generated DAW action plan action missing id: {title}.{action_group}")
                elif action_id in all_action_ids:
                    fail(errors, f"Generated DAW action plan action id is duplicated: {action_id}")
                all_action_ids.add(action_id)
                approval_gate = action.get("approval_gate")
                if approval_gate and approval_gate not in OPENAI_APPROVAL_GATES:
                    fail(errors, f"Generated DAW action plan action references unknown approval gate: {action_id}: {approval_gate}")
                if approval_gate:
                    actual_approval_gates.add(approval_gate)
                required_gate = REQUIRED_DAW_ACTION_GROUP_GATES.get(action_group)
                if required_gate and approval_gate != required_gate:
                    fail(errors, f"Generated DAW action plan {action_group} action must require {required_gate}: {action_id}")

        preflight_actions = track.get("preflight_actions", [])
        private_upload_checks = [
            action for action in preflight_actions
            if action.get("approval_gate") == "private_audio_upload"
        ]
        if not private_upload_checks:
            fail(errors, f"Generated DAW action plan preflight must include private_audio_upload boundary: {title}")

        if len(track.get("scene_actions", [])) != len(build_plan.get("scenes", [])):
            fail(errors, f"Generated DAW action plan scene count is stale: {title}")
        for action, scene in zip(track.get("scene_actions", []), build_plan.get("scenes", []), strict=False):
            for field in ["bar_start", "bar_length", "arrangement_note"]:
                if action.get(field) != scene.get(field):
                    fail(errors, f"Generated DAW action plan scene {field} is stale: {title}: {action.get('id')}")

        layers_by_id = {layer.get("id"): layer for layer in build_plan.get("layers", [])}
        if len(track.get("layer_actions", [])) != len(layers_by_id):
            fail(errors, f"Generated DAW action plan layer action count is stale: {title}")
        for action in track.get("layer_actions", []):
            layer_id = action.get("id", "").split(".layer.", 1)[-1]
            layer = layers_by_id.get(layer_id)
            if not layer:
                fail(errors, f"Generated DAW action plan layer id is not in build plan: {title}: {layer_id}")
                continue
            session_track_name = action.get("session_track")
            session_track = session_tracks.get(session_track_name)
            if not session_track:
                fail(errors, f"Generated DAW action plan layer references unknown session track: {title}: {session_track_name}")
                continue
            for field in ["midi_track", "midi_channels", "gm_placeholder", "traditional_bluegrass_layer", "alien_electronic_layer", "device_contracts", "automation_targets"]:
                expected_field = "gm_sound" if field == "gm_placeholder" else field
                if action.get(field) != layer.get(expected_field):
                    fail(errors, f"Generated DAW action plan layer {field} is stale: {title}: {layer_id}")
            if action.get("instrument_strategy") != session_track.get("instrument_strategy"):
                fail(errors, f"Generated DAW action plan layer instrument_strategy is stale: {title}: {layer_id}")
            if action.get("device_contracts") != session_track.get("device_contracts", []):
                fail(errors, f"Generated DAW action plan layer device contracts must mirror session template: {title}: {layer_id}")
            macro_targets = [macro.get("target") for macro in action.get("macro_initialization", [])]
            if macro_targets != action.get("automation_targets", []):
                fail(errors, f"Generated DAW action plan macro initialization must cover automation targets: {title}: {layer_id}")

        configure_returns = [
            action for action in track.get("session_actions", [])
            if action.get("type") == "create_or_verify_return_tracks"
        ]
        if not configure_returns or configure_returns[0].get("returns") != session_returns:
            fail(errors, f"Generated DAW action plan return setup is stale: {title}")

        source_deck = require_dict(track.get("source_deck"), f"Generated DAW action plan source_deck for {title}", errors)
        source_deck_session_track = session_tracks.get(source_deck.get("session_track"))
        if not source_deck_session_track:
            fail(errors, f"Generated DAW action plan source_deck references unknown track: {title}")
        else:
            for field in ["role", "instrument_strategy", "device_contracts", "automation_targets"]:
                source_deck_field = "session_role" if field == "role" else field
                if source_deck.get(source_deck_field) != source_deck_session_track.get(field, [] if field in {"device_contracts", "automation_targets"} else None):
                    fail(errors, f"Generated DAW action plan source_deck {source_deck_field} is stale: {title}")
            macro_targets = [macro.get("target") for macro in source_deck.get("macro_initialization", [])]
            if macro_targets != source_deck.get("automation_targets", []):
                fail(errors, f"Generated DAW action plan source_deck macro initialization must cover automation targets: {title}")
        if source_deck.get("default_state") != "muted_until_human_provenance_review":
            fail(errors, f"Generated DAW action plan source_deck must default muted: {title}")
        for candidate in source_deck.get("candidate_sources", []):
            source_id = candidate.get("source_id")
            if source_id not in pool_ids:
                fail(errors, f"Generated DAW action plan source candidate is not in approved pool: {title}: {candidate.get('source_id')}")
            elif candidate != pool_by_id[source_id]:
                fail(errors, f"Generated DAW action plan source candidate metadata is stale: {title}: {source_id}")
        if source_deck.get("approval_gate") != "live_set_mutation":
            fail(errors, f"Generated DAW action plan source_deck must require live_set_mutation: {title}")
        else:
            actual_approval_gates.add("live_set_mutation")
        if set(track.get("approval_gates_required", [])) != actual_approval_gates:
            fail(errors, f"Generated DAW action plan approval_gates_required must match emitted action gates: {title}")
        if not EXPECTED_DAW_APPROVAL_GATES.issubset(actual_approval_gates):
            fail(errors, f"Generated DAW action plan track must require private audio, Live mutation, and export/release gates: {title}")

    for string_value in iter_string_values(data):
        if "/Users/" in string_value:
            fail(errors, "Generated DAW action plan must not contain absolute user paths")
        if "sources/public-domain/raw/" in string_value or AUDIO_PATH_PATTERN.search(string_value):
            fail(errors, f"Generated DAW action plan must not contain raw audio paths: {string_value}")
        if SECRET_VALUE_PATTERN.search(string_value):
            fail(errors, "Generated DAW action plan must not contain API tokens or bearer credentials")


def validate_public_domain_source_deck(root: Path, errors: list[str]) -> None:
    data = load_json(root / "automation/generated/public-domain-source-deck.json", errors)
    markdown_path = root / "docs/public-domain-source-deck.md"
    catalog = load_json(root / "catalogs/public-domain-bluegrass-sources.json", errors)
    ledger = load_json(root / "sources/public-domain/download-ledger.json", errors)
    daw_plan = load_json(root / "automation/generated/live12-daw-action-plan.json", errors)
    if not data or not ledger or not daw_plan:
        return

    if data.get("schema_version") != 1:
        fail(errors, "Generated public-domain source deck must use schema_version 1")
    if data.get("generated_at") != STABLE_GENERATED_AT:
        fail(errors, "Generated public-domain source deck must be committed with stable generated_at")
    if data.get("generator") != "scripts/render_public_domain_source_deck.py":
        fail(errors, "Generated public-domain source deck must name scripts/render_public_domain_source_deck.py as generator")

    source_files = set(data.get("source_files", []))
    if source_files != EXPECTED_PUBLIC_DOMAIN_SOURCE_DECK_SOURCES:
        fail(errors, "Generated public-domain source deck source_files must match expected source manifests")
    source_hashes = data.get("source_file_sha256") or {}
    if set(source_hashes) != EXPECTED_PUBLIC_DOMAIN_SOURCE_DECK_SOURCES:
        fail(errors, "Generated public-domain source deck source_file_sha256 keys must match expected source manifests")
    for source_file in source_files:
        if Path(source_file).is_absolute() or ".." in Path(source_file).parts or not (root / source_file).exists():
            fail(errors, f"Generated public-domain source deck source file is invalid: {source_file}")
            continue
        expected_hash = source_hashes.get(source_file)
        if not SHA256_PATTERN.match(str(expected_hash or "")):
            fail(errors, f"Generated public-domain source deck source hash is invalid: {source_file}")
        elif expected_hash != sha256_file(root / source_file):
            fail(errors, f"Generated public-domain source deck source hash is stale: {source_file}")

    deck_policy = require_dict(data.get("deck_policy"), "Generated public-domain source deck deck_policy", errors)
    if deck_policy.get("session_track") != "Public Domain Source Deck":
        fail(errors, "Generated public-domain source deck must target the Public Domain Source Deck track")
    if deck_policy.get("default_state") != "muted_until_human_provenance_review":
        fail(errors, "Generated public-domain source deck must remain muted by default")
    if deck_policy.get("approval_gate") != "live_set_mutation":
        fail(errors, "Generated public-domain source deck must require live_set_mutation approval")

    artifact_policy = require_dict(data.get("artifact_policy"), "Generated public-domain source deck artifact_policy", errors)
    if artifact_policy.get("git_policy") != "metadata_only_no_raw_audio":
        fail(errors, "Generated public-domain source deck git_policy must be metadata_only_no_raw_audio")
    if "raw source audio" not in artifact_policy.get("must_not_commit", []):
        fail(errors, "Generated public-domain source deck must block raw source audio commits")

    catalog_by_id = {
        source.get("id"): source
        for source in catalog.get("sources", [])
        if source.get("id")
    }
    approved_sources = data.get("approved_sources", [])
    ledger_downloads = ledger.get("downloads", [])
    if data.get("approved_source_count") != len(ledger_downloads):
        fail(errors, "Generated public-domain source deck approved_source_count must mirror the download ledger")
    if [source.get("source_id") for source in approved_sources] != [record.get("source_id") for record in ledger_downloads]:
        fail(errors, "Generated public-domain source deck approved source order must mirror the download ledger")
    for source, record in zip(approved_sources, ledger_downloads, strict=False):
        source_id = record.get("source_id")
        catalog_source = catalog_by_id.get(source_id, {})
        for blocked_field in ["download_url", "final_url", "local_file"]:
            if blocked_field in source:
                fail(errors, f"Generated public-domain source deck must not expose {blocked_field}: {source_id}")
        for field in ["source_id", "name", "rights_status", "sha256", "byte_size", "content_type", "credit_line", "source_url", "transformation", "browser_evidence", "rights_evidence"]:
            if source.get(field) != record.get(field):
                fail(errors, f"Generated public-domain source deck source {field} is stale: {source_id}")
        if source.get("project_use") != catalog_source.get("project_use"):
            fail(errors, f"Generated public-domain source deck source project_use is stale: {source_id}")
        if source.get("item_url") != catalog_source.get("item_url"):
            fail(errors, f"Generated public-domain source deck source item_url is stale: {source_id}")
        if source.get("rights_status") != "public_domain":
            fail(errors, f"Generated public-domain source deck source must be public_domain: {source_id}")
        if source.get("local_file_policy") != "raw_audio_ignored_metadata_only":
            fail(errors, f"Generated public-domain source deck source local_file_policy is stale: {source_id}")

    assignments = data.get("track_assignments", [])
    daw_tracks = daw_plan.get("tracks", [])
    if data.get("track_assignment_count") != len(daw_tracks) or len(assignments) != len(daw_tracks):
        fail(errors, "Generated public-domain source deck track assignments must mirror DAW action plan track count")
    if [assignment.get("track_slug") for assignment in assignments] != [track.get("slug") for track in daw_tracks]:
        fail(errors, "Generated public-domain source deck track assignment order must mirror the DAW action plan")
    for assignment, track in zip(assignments, daw_tracks, strict=False):
        source_deck = track.get("source_deck", {})
        expected_candidate_ids = [
            candidate.get("source_id")
            for candidate in source_deck.get("candidate_sources", [])
        ]
        if assignment.get("track_title") != track.get("title"):
            fail(errors, f"Generated public-domain source deck track title is stale: {track.get('slug')}")
        if assignment.get("deck_state") != source_deck.get("default_state"):
            fail(errors, f"Generated public-domain source deck track state is stale: {track.get('slug')}")
        if assignment.get("approval_gate") != source_deck.get("approval_gate"):
            fail(errors, f"Generated public-domain source deck track approval gate is stale: {track.get('slug')}")
        if assignment.get("session_track") != source_deck.get("session_track"):
            fail(errors, f"Generated public-domain source deck track session_track is stale: {track.get('slug')}")
        if assignment.get("candidate_source_ids") != expected_candidate_ids:
            fail(errors, f"Generated public-domain source deck track candidates are stale: {track.get('slug')}")
        if assignment.get("candidate_source_count") != len(expected_candidate_ids):
            fail(errors, f"Generated public-domain source deck track candidate count is stale: {track.get('slug')}")
        if assignment.get("required_before_unmute") != source_deck.get("required_checks", []):
            fail(errors, f"Generated public-domain source deck track unmute checks are stale: {track.get('slug')}")

    markdown = markdown_path.read_text(encoding="utf-8") if markdown_path.exists() else ""
    for expected_text in [
        "# Public-Domain Source Deck",
        "metadata only",
        "muted_until_human_provenance_review",
        "raw source audio must remain outside Git",
    ]:
        if expected_text not in markdown:
            fail(errors, f"Generated public-domain source deck markdown is missing required text: {expected_text}")

    for string_value in iter_string_values(data):
        if "/Users/" in string_value:
            fail(errors, "Generated public-domain source deck must not contain absolute user paths")
        if "sources/public-domain/raw/" in string_value or AUDIO_PATH_PATTERN.search(string_value):
            fail(errors, f"Generated public-domain source deck must not contain raw audio paths: {string_value}")
        if SECRET_VALUE_PATTERN.search(string_value):
            fail(errors, "Generated public-domain source deck must not contain API tokens or bearer credentials")
    if "/Users/" in markdown or "sources/public-domain/raw/" in markdown or SECRET_VALUE_PATTERN.search(markdown):
        fail(errors, "Generated public-domain source deck markdown contains sensitive local data")


def action_ids(track: dict, groups: list[str]) -> list[str]:
    return [
        action.get("id")
        for group in groups
        for action in as_list(track.get(group))
        if isinstance(action, dict) and action.get("id")
    ]


def unique_ordered(values: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def validate_generated_daw_mutation_package(root: Path, errors: list[str]) -> None:
    data = load_json(root / "automation/generated/live12-daw-mutation-package.json", errors)
    daw_plan = load_json(root / "automation/generated/live12-daw-action-plan.json", errors)
    session_template = load_json(root / "automation/live12-session-template.json", errors)
    build_plans = load_json(root / "compositions/generated/live12-track-build-plans.json", errors)
    if not data or not daw_plan:
        return

    if data.get("schema_version") != 1:
        fail(errors, "Generated DAW mutation package must use schema_version 1")
    if data.get("generated_at") != STABLE_GENERATED_AT:
        fail(errors, "Generated DAW mutation package must be committed with stable generated_at")
    if data.get("generator") != "scripts/render_live12_daw_mutation_package.py":
        fail(errors, "Generated DAW mutation package must name scripts/render_live12_daw_mutation_package.py as generator")
    if set(data) != EXPECTED_DAW_MUTATION_TOP_LEVEL_KEYS:
        fail(errors, "Generated DAW mutation package top-level keys must exactly match contract")

    source_files = set(data.get("source_files", []))
    if source_files != EXPECTED_DAW_MUTATION_PACKAGE_SOURCES:
        fail(errors, "Generated DAW mutation package source_files must match expected source manifests")
    source_hashes = data.get("source_file_sha256") or {}
    if set(source_hashes) != EXPECTED_DAW_MUTATION_PACKAGE_SOURCES:
        fail(errors, "Generated DAW mutation package source_file_sha256 keys must match expected source manifests")
    for source_file in source_files:
        if Path(source_file).is_absolute() or ".." in Path(source_file).parts or not (root / source_file).exists():
            fail(errors, f"Generated DAW mutation package source file is invalid: {source_file}")
            continue
        expected_hash = source_hashes.get(source_file)
        if not SHA256_PATTERN.match(str(expected_hash or "")):
            fail(errors, f"Generated DAW mutation package source hash is invalid: {source_file}")
        elif expected_hash != sha256_file(root / source_file):
            fail(errors, f"Generated DAW mutation package source hash is stale: {source_file}")

    safety = require_dict(data.get("safety"), "Generated DAW mutation package safety", errors)
    if set(safety) != EXPECTED_DAW_MUTATION_SAFETY_KEYS:
        fail(errors, "Generated DAW mutation package safety keys must exactly match contract")
    if safety.get("local_only") is not True:
        fail(errors, "Generated DAW mutation package safety.local_only must be true")
    for field in ["requires_operator_approval_before_execution", "must_not"]:
        validate_string_items(
            require_list(safety.get(field), f"Generated DAW mutation package safety.{field}", errors),
            f"Generated DAW mutation package safety.{field}",
            errors,
        )
    if safety.get("requires_operator_approval_before_execution") != EXPECTED_DAW_MUTATION_APPROVAL_BOUNDARIES:
        fail(errors, "Generated DAW mutation package approval boundaries must match contract")
    if safety.get("must_not") != EXPECTED_DAW_MUTATION_MUST_NOT:
        fail(errors, "Generated DAW mutation package safety must_not must match contract")

    receipt_contract = require_dict(data.get("receipt_contract"), "Generated DAW mutation package receipt_contract", errors)
    if set(receipt_contract) != EXPECTED_DAW_MUTATION_RECEIPT_CONTRACT_KEYS:
        fail(errors, "Generated DAW mutation package receipt_contract keys must exactly match contract")
    if receipt_contract.get("output_root") != "output/daw-mutations":
        fail(errors, "Generated DAW mutation package receipt output_root must remain output/daw-mutations")
    if receipt_contract.get("git_policy") != "ignored_local_only":
        fail(errors, "Generated DAW mutation package receipt git_policy must remain ignored_local_only")
    if receipt_contract.get("required_fields") != EXPECTED_DAW_MUTATION_RECEIPT_FIELDS:
        fail(errors, "Generated DAW mutation package receipt required_fields must match contract")
    if receipt_contract.get("required_postflight_checks") != EXPECTED_DAW_MUTATION_POSTFLIGHT_CHECKS:
        fail(errors, "Generated DAW mutation package postflight checks must match contract")
    if receipt_contract.get("prohibited_artifacts") != EXPECTED_DAW_MUTATION_PROHIBITED_ARTIFACTS:
        fail(errors, "Generated DAW mutation package prohibited artifacts must match contract")

    if data.get("live_template") != daw_plan.get("live_template"):
        fail(errors, "Generated DAW mutation package live_template must mirror the DAW action plan")
    if data.get("composition_set") != daw_plan.get("composition_set"):
        fail(errors, "Generated DAW mutation package composition_set must mirror the DAW action plan")
    source_plan = require_dict(data.get("source_plan"), "Generated DAW mutation package source_plan", errors)
    expected_source_plan = {
        "path": "automation/generated/live12-daw-action-plan.json",
        "sha256": sha256_file(root / "automation/generated/live12-daw-action-plan.json"),
        "track_count": len(daw_plan.get("tracks", [])),
        "build_plan_track_count": len(build_plans.get("tracks", [])),
        "session_track_count": len(session_template.get("tracks", [])),
    }
    if source_plan != expected_source_plan:
        fail(errors, "Generated DAW mutation package source_plan is stale")

    generated_jobs = data.get("jobs", [])
    daw_tracks = daw_plan.get("tracks", [])
    if [job.get("track_slug") for job in generated_jobs] != [track.get("slug") for track in daw_tracks]:
        fail(errors, "Generated DAW mutation package job order must match the DAW action plan")

    for job, track in zip(generated_jobs, daw_tracks, strict=False):
        slug = track.get("slug")
        if set(job) != EXPECTED_DAW_MUTATION_JOB_KEYS:
            fail(errors, f"Generated DAW mutation package job keys must exactly match contract: {slug}")
        if job.get("id") != f"daw-mutation.{slug}":
            fail(errors, f"Generated DAW mutation package job id is stale: {slug}")
        if job.get("track_slug") != slug or job.get("track_title") != track.get("title"):
            fail(errors, f"Generated DAW mutation package job track identity is stale: {slug}")
        if job.get("execution_mode") != EXPECTED_DAW_MUTATION_EXECUTION_MODE:
            fail(errors, f"Generated DAW mutation package job execution_mode is stale: {slug}")
        if job.get("approval_gates_required") != track.get("approval_gates_required"):
            fail(errors, f"Generated DAW mutation package job approval gates are stale: {slug}")
        if job.get("approval_required_before_execution") != ["live_set_mutation", "private_audio_upload"]:
            fail(errors, f"Generated DAW mutation package job approval boundary is stale: {slug}")
        if job.get("blocked_action_groups") != EXPECTED_DAW_MUTATION_BLOCKED_GROUPS:
            fail(errors, f"Generated DAW mutation package job must block export/release actions: {slug}")
        if job.get("executable_action_groups") != EXPECTED_DAW_MUTATION_EXECUTABLE_GROUPS:
            fail(errors, f"Generated DAW mutation package job executable action groups are stale: {slug}")
        if job.get("preflight_action_ids") != action_ids(track, ["preflight_actions"]):
            fail(errors, f"Generated DAW mutation package job preflight action ids are stale: {slug}")
        expected_executable_ids = action_ids(track, ["session_actions", "scene_actions", "layer_actions"])
        expected_source_deck_action_id = f"{slug}.source-deck.keep-muted-for-provenance-review"
        expected_executable_ids.append(expected_source_deck_action_id)
        if job.get("executable_action_ids") != expected_executable_ids:
            fail(errors, f"Generated DAW mutation package job executable action ids are stale: {slug}")
        if job.get("mutation_action_count") != len(expected_executable_ids):
            fail(errors, f"Generated DAW mutation package job mutation_action_count is stale: {slug}")
        if job.get("plan_track_sha256") != sha256_json(track):
            fail(errors, f"Generated DAW mutation package job plan_track_sha256 is stale: {slug}")
        expected_midi = {
            "path": track.get("midi_file"),
            "sha256": track.get("midi_sha256"),
            "verification_action_id": f"{slug}.preflight.verify-midi-hash",
        }
        if job.get("midi_artifact") != expected_midi:
            fail(errors, f"Generated DAW mutation package job MIDI artifact is stale: {slug}")
        source_deck = track.get("source_deck", {})
        layer_tracks = [
            action.get("session_track")
            for action in track.get("layer_actions", [])
            if action.get("session_track")
        ]
        expected_affected_tracks = unique_ordered(layer_tracks + [source_deck.get("session_track", "")])
        if job.get("affected_tracks") != expected_affected_tracks:
            fail(errors, f"Generated DAW mutation package job affected_tracks are stale: {slug}")
        configure_return_actions = [
            action for action in track.get("session_actions", [])
            if action.get("type") == "create_or_verify_return_tracks"
        ]
        expected_returns = [
            item.get("name")
            for item in (configure_return_actions[0].get("returns", []) if configure_return_actions else [])
            if item.get("name")
        ]
        if job.get("affected_returns") != expected_returns:
            fail(errors, f"Generated DAW mutation package job affected_returns are stale: {slug}")
        expected_source_deck_policy = {
            "session_track": source_deck.get("session_track"),
            "default_state": "muted_until_human_provenance_review",
            "action_id": expected_source_deck_action_id,
            "candidate_source_count": len(source_deck.get("candidate_sources", [])),
            "requires_provenance_review": True,
        }
        if job.get("source_deck_policy") != expected_source_deck_policy:
            fail(errors, f"Generated DAW mutation package source_deck_policy is stale: {slug}")
        if job.get("rollback", {}).get("required") is not True:
            fail(errors, f"Generated DAW mutation package job must require rollback: {slug}")
        if job.get("local_output_policy") != EXPECTED_DAW_MUTATION_LOCAL_OUTPUT_POLICY:
            fail(errors, f"Generated DAW mutation package job local output policy is stale: {slug}")

    for string_value in iter_string_values(data):
        if "/Users/" in string_value:
            fail(errors, "Generated DAW mutation package must not contain absolute user paths")
        if "sources/public-domain/raw/" in string_value or AUDIO_PATH_PATTERN.search(string_value):
            fail(errors, f"Generated DAW mutation package must not contain raw audio paths: {string_value}")
        if SECRET_VALUE_PATTERN.search(string_value):
            fail(errors, "Generated DAW mutation package must not contain API tokens or bearer credentials")


def expected_daw_runbook_commands(slug: str) -> dict[str, list[str]]:
    request_path = f"output/daw-mutations/{slug}/mutation-request.json"
    evidence_path = f"output/daw-mutations/{slug}/operator-evidence.json"
    return {
        "preflight": [
            "python3",
            "scripts/prepare_live12_daw_mutation.py",
            "--track",
            slug,
        ],
        "stage_import_bundle": [
            "python3",
            "scripts/stage_live12_daw_import_bundle.py",
            "--request",
            request_path,
        ],
        "apply_live_mutation": [
            "python3",
            "scripts/stage_live12_daw_import_bundle.py",
            "--request",
            request_path,
            "--launch-ableton",
            "--confirm-live-mutation",
            "--operator-approval-reference",
            "<approval-id>",
            "--rollback-copy-reference",
            "<rollback-note>",
        ],
        "record_receipt": [
            "python3",
            "scripts/record_live12_daw_mutation_receipt.py",
            "--request",
            request_path,
            "--evidence",
            evidence_path,
        ],
    }


def expected_runbook_max_devices(job: dict, max_contracts: dict) -> list[dict]:
    affected_tracks = set(job.get("affected_tracks", []))
    track_slug = job.get("track_slug")
    devices = []
    for device in max_contracts.get("devices", []):
        target_tracks = device.get("target_tracks", [])
        track_slugs = device.get("track_slugs", [])
        if track_slug not in track_slugs and not affected_tracks.intersection(target_tracks):
            continue
        devices.append(
            {
                "id": device.get("id"),
                "display_name": device.get("display_name"),
                "device_class": device.get("device_class"),
                "approval_gate": device.get("approval_gate"),
                "target_tracks": target_tracks,
                "macro_controls": device.get("macro_controls"),
                "source_patch": device.get("source_patch"),
                "source_patch_sha256": device.get("source_patch_sha256"),
            }
        )
    return devices


def validate_generated_daw_mutation_runbook(root: Path, errors: list[str]) -> None:
    data = load_json(root / "automation/generated/live12-daw-mutation-runbook.json", errors)
    markdown_path = root / "docs/live12-daw-mutation-runbook.md"
    package = load_json(root / "automation/generated/live12-daw-mutation-package.json", errors)
    daw_plan = load_json(root / "automation/generated/live12-daw-action-plan.json", errors)
    max_contracts = load_json(root / "automation/generated/max-for-live-device-contracts.json", errors)
    if not data or not package or not max_contracts:
        return

    if data.get("schema_version") != 1:
        fail(errors, "Generated DAW mutation runbook must use schema_version 1")
    if data.get("generated_at") != STABLE_GENERATED_AT:
        fail(errors, "Generated DAW mutation runbook must be committed with stable generated_at")
    if data.get("generator") != "scripts/render_live12_daw_mutation_runbook.py":
        fail(errors, "Generated DAW mutation runbook must name scripts/render_live12_daw_mutation_runbook.py as generator")
    if set(data) != EXPECTED_DAW_MUTATION_RUNBOOK_TOP_LEVEL_KEYS:
        fail(errors, "Generated DAW mutation runbook top-level keys must exactly match contract")
    if data.get("execution_status") != "operator_runbook_not_applied":
        fail(errors, "Generated DAW mutation runbook must not claim a Live mutation was applied")

    source_files = set(data.get("source_files", []))
    if source_files != EXPECTED_DAW_MUTATION_RUNBOOK_SOURCES:
        fail(errors, "Generated DAW mutation runbook source_files must match expected source manifests")
    source_hashes = data.get("source_file_sha256") or {}
    if set(source_hashes) != EXPECTED_DAW_MUTATION_RUNBOOK_SOURCES:
        fail(errors, "Generated DAW mutation runbook source_file_sha256 keys must match expected source manifests")
    for source_file in source_files:
        if Path(source_file).is_absolute() or ".." in Path(source_file).parts or not (root / source_file).exists():
            fail(errors, f"Generated DAW mutation runbook source file is invalid: {source_file}")
            continue
        expected_hash = source_hashes.get(source_file)
        if not SHA256_PATTERN.match(str(expected_hash or "")):
            fail(errors, f"Generated DAW mutation runbook source hash is invalid: {source_file}")
        elif expected_hash != sha256_file(root / source_file):
            fail(errors, f"Generated DAW mutation runbook source hash is stale: {source_file}")

    if data.get("composition_set") != package.get("composition_set"):
        fail(errors, "Generated DAW mutation runbook composition_set must mirror the mutation package")
    if data.get("live_template") != daw_plan.get("live_template"):
        fail(errors, "Generated DAW mutation runbook live_template must mirror the DAW action plan")
    if data.get("queue_command") != ["python3", "scripts/prepare_live12_daw_mutation_queue.py"]:
        fail(errors, "Generated DAW mutation runbook queue command is stale")
    approval_policy = require_dict(data.get("approval_policy"), "Generated DAW mutation runbook approval_policy", errors)
    if approval_policy.get("status") != "blocked_until_operator_approval_and_rollback_reference":
        fail(errors, "Generated DAW mutation runbook approval policy must stay blocked")
    if approval_policy.get("required_cli_flags") != EXPECTED_DAW_MUTATION_RUNBOOK_REQUIRED_FLAGS:
        fail(errors, "Generated DAW mutation runbook approval flags are stale")
    if approval_policy.get("approval_gates") != package.get("safety", {}).get("requires_operator_approval_before_execution"):
        fail(errors, "Generated DAW mutation runbook approval gates must mirror the mutation package")
    if approval_policy.get("must_not") != package.get("safety", {}).get("must_not"):
        fail(errors, "Generated DAW mutation runbook safety boundary must mirror the mutation package")

    artifact_policy = require_dict(data.get("artifact_policy"), "Generated DAW mutation runbook artifact_policy", errors)
    if artifact_policy.get("git_policy") != "text_contracts_only":
        fail(errors, "Generated DAW mutation runbook artifact policy must remain text_contracts_only")
    for required_root in ["output/daw-mutations", "output/daw-import-bundles", "output/daw-mutation-queue"]:
        if required_root not in artifact_policy.get("local_output_roots", []):
            fail(errors, f"Generated DAW mutation runbook artifact policy missing local output root: {required_root}")
    if "source audio" not in artifact_policy.get("must_not_commit", []):
        fail(errors, "Generated DAW mutation runbook artifact policy must block source audio commits")

    phase_contract = require_list(data.get("phase_contract"), "Generated DAW mutation runbook phase_contract", errors)
    if [phase.get("id") for phase in phase_contract if isinstance(phase, dict)] != EXPECTED_DAW_MUTATION_RUNBOOK_PHASE_ORDER:
        fail(errors, "Generated DAW mutation runbook phase order is stale")

    tracks = data.get("tracks", [])
    jobs = package.get("jobs", [])
    if data.get("track_count") != len(jobs) or len(tracks) != len(jobs):
        fail(errors, "Generated DAW mutation runbook track count must mirror the mutation package")
    if data.get("total_planned_action_count") != sum(job.get("mutation_action_count", 0) for job in jobs):
        fail(errors, "Generated DAW mutation runbook total action count must mirror the mutation package")
    if [track.get("track_slug") for track in tracks] != [job.get("track_slug") for job in jobs]:
        fail(errors, "Generated DAW mutation runbook track order must mirror the mutation package")

    postflight_checks = package.get("receipt_contract", {}).get("required_postflight_checks", [])
    for index, (track, job) in enumerate(zip(tracks, jobs, strict=False), start=1):
        slug = job.get("track_slug")
        if set(track) != EXPECTED_DAW_MUTATION_RUNBOOK_TRACK_KEYS:
            fail(errors, f"Generated DAW mutation runbook track keys must exactly match contract: {slug}")
        if track.get("queue_order") != index:
            fail(errors, f"Generated DAW mutation runbook queue order is stale: {slug}")
        if track.get("track_slug") != slug or track.get("track_title") != job.get("track_title"):
            fail(errors, f"Generated DAW mutation runbook track identity is stale: {slug}")
        if track.get("execution_status") != "not_applied":
            fail(errors, f"Generated DAW mutation runbook track must not claim mutation applied: {slug}")
        if track.get("operator_phase_order") != EXPECTED_DAW_MUTATION_RUNBOOK_PHASE_ORDER:
            fail(errors, f"Generated DAW mutation runbook track phase order is stale: {slug}")
        for field in [
            "approval_required_before_execution",
            "blocked_action_groups",
            "affected_tracks",
            "affected_returns",
            "midi_artifact",
            "source_deck_policy",
        ]:
            if track.get(field) != job.get(field):
                fail(errors, f"Generated DAW mutation runbook track {field} must mirror mutation package: {slug}")
        if track.get("planned_action_count") != job.get("mutation_action_count"):
            fail(errors, f"Generated DAW mutation runbook planned action count is stale: {slug}")
        expected_devices = expected_runbook_max_devices(job, max_contracts)
        if track.get("max_for_live_devices") != expected_devices:
            fail(errors, f"Generated DAW mutation runbook Max for Live devices are stale: {slug}")
        if track.get("max_for_live_device_ids") != [device.get("id") for device in expected_devices]:
            fail(errors, f"Generated DAW mutation runbook Max for Live device ids are stale: {slug}")
        if track.get("commands") != expected_daw_runbook_commands(str(slug)):
            fail(errors, f"Generated DAW mutation runbook commands are stale: {slug}")
        expected_evidence = {
            "template_path": f"output/daw-import-bundles/{slug}/operator-evidence-template.json",
            "local_evidence_path": f"output/daw-mutations/{slug}/operator-evidence.json",
            "receipt_output_path": f"output/daw-mutations/{slug}/applied-receipt.json",
            "required_reference_fields": [
                "operator_approval_reference",
                "rollback_copy_reference",
            ],
        }
        if track.get("operator_evidence") != expected_evidence:
            fail(errors, f"Generated DAW mutation runbook operator evidence contract is stale: {slug}")
        if track.get("postflight_checks") != postflight_checks:
            fail(errors, f"Generated DAW mutation runbook postflight checks must mirror mutation package: {slug}")

    markdown = markdown_path.read_text(encoding="utf-8") if markdown_path.exists() else ""
    for expected_text in [
        "# Live 12 DAW Mutation Runbook",
        "Do not commit Ableton sets, Max devices, source audio, renders, credentials, cookies, or license files.",
        "python3 scripts/prepare_live12_daw_mutation_queue.py",
        "--confirm-live-mutation",
        "Public Domain Source Deck remains muted",
    ]:
        if expected_text not in markdown:
            fail(errors, f"Generated DAW mutation runbook markdown is missing required text: {expected_text}")

    for string_value in iter_string_values(data):
        if "/Users/" in string_value:
            fail(errors, "Generated DAW mutation runbook must not contain absolute user paths")
        if "sources/public-domain/raw/" in string_value or AUDIO_PATH_PATTERN.search(string_value):
            fail(errors, f"Generated DAW mutation runbook must not contain raw audio paths: {string_value}")
        if SECRET_VALUE_PATTERN.search(string_value):
            fail(errors, "Generated DAW mutation runbook must not contain API tokens or bearer credentials")
    if "/Users/" in markdown or "sources/public-domain/raw/" in markdown or SECRET_VALUE_PATTERN.search(markdown):
        fail(errors, "Generated DAW mutation runbook markdown contains sensitive local data")


def validate_generated_daw_mutation_queue_runbook(root: Path, errors: list[str]) -> None:
    data = load_json(root / "automation/generated/live12-daw-mutation-queue-runbook.json", errors)
    markdown_path = root / "docs/live12-daw-mutation-queue-runbook.md"
    package = load_json(root / "automation/generated/live12-daw-mutation-package.json", errors)
    max_contracts = load_json(root / "automation/generated/max-for-live-device-contracts.json", errors)
    if not data or not package or not max_contracts:
        return

    if data.get("schema_version") != 1:
        fail(errors, "Generated DAW mutation queue runbook must use schema_version 1")
    if data.get("generated_at") != STABLE_GENERATED_AT:
        fail(errors, "Generated DAW mutation queue runbook must be committed with stable generated_at")
    if data.get("generator") != "scripts/render_live12_daw_mutation_queue_runbook.py":
        fail(errors, "Generated DAW mutation queue runbook must name scripts/render_live12_daw_mutation_queue_runbook.py as generator")

    source_files = set(data.get("source_files", []))
    if source_files != EXPECTED_DAW_MUTATION_QUEUE_RUNBOOK_SOURCES:
        fail(errors, "Generated DAW mutation queue runbook source_files must match expected source manifests")
    source_hashes = data.get("source_file_sha256") or {}
    if set(source_hashes) != EXPECTED_DAW_MUTATION_QUEUE_RUNBOOK_SOURCES:
        fail(errors, "Generated DAW mutation queue runbook source_file_sha256 keys must match expected source manifests")
    for source_file in source_files:
        if Path(source_file).is_absolute() or ".." in Path(source_file).parts or not (root / source_file).exists():
            fail(errors, f"Generated DAW mutation queue runbook source file is invalid: {source_file}")
            continue
        expected_hash = source_hashes.get(source_file)
        if not SHA256_PATTERN.match(str(expected_hash or "")):
            fail(errors, f"Generated DAW mutation queue runbook source hash is invalid: {source_file}")
        elif expected_hash != sha256_file(root / source_file):
            fail(errors, f"Generated DAW mutation queue runbook source hash is stale: {source_file}")

    queue_policy = require_dict(data.get("queue_policy"), "Generated DAW mutation queue runbook queue_policy", errors)
    if queue_policy.get("execution_status") != "queued_not_launched":
        fail(errors, "Generated DAW mutation queue runbook must stay queued_not_launched")
    if queue_policy.get("launch_status") != "blocked_until_per_track_confirm_live_mutation":
        fail(errors, "Generated DAW mutation queue runbook must block Ableton launches until per-track confirmation")
    if queue_policy.get("git_policy") != "ignored_local_only":
        fail(errors, "Generated DAW mutation queue runbook must use ignored_local_only git policy")
    for required_root in ["output/daw-mutations", "output/daw-import-bundles", "output/daw-mutation-queue"]:
        if required_root not in queue_policy.get("artifact_roots", []):
            fail(errors, f"Generated DAW mutation queue runbook missing artifact root: {required_root}")
    if "raw source audio" not in queue_policy.get("must_not_commit", []):
        fail(errors, "Generated DAW mutation queue runbook must block raw source audio commits")

    prepare_queue_command = data.get("prepare_queue_command")
    if prepare_queue_command != ["python3", "scripts/prepare_live12_daw_mutation_queue.py", "--stable"]:
        fail(errors, "Generated DAW mutation queue runbook prepare_queue_command is stale")
    if "--launch-ableton" in prepare_queue_command:
        fail(errors, "Generated DAW mutation queue runbook prepare_queue_command must not launch Ableton")
    if data.get("queue_manifest_path") != "output/daw-mutation-queue/queue-manifest.json":
        fail(errors, "Generated DAW mutation queue runbook queue_manifest_path is stale")
    if data.get("receipt_contract") != package.get("receipt_contract"):
        fail(errors, "Generated DAW mutation queue runbook receipt contract must mirror mutation package")
    if data.get("max_for_live_device_count") != max_contracts.get("device_count"):
        fail(errors, "Generated DAW mutation queue runbook Max for Live device count must mirror contracts")

    tracks = data.get("tracks", [])
    jobs = package.get("jobs", [])
    if data.get("track_count") != len(jobs) or len(tracks) != len(jobs):
        fail(errors, "Generated DAW mutation queue runbook track count must mirror the mutation package")
    if data.get("total_planned_action_count") != sum(len(job.get("executable_action_ids", [])) for job in jobs):
        fail(errors, "Generated DAW mutation queue runbook total action count must mirror the mutation package")
    if [track.get("track_slug") for track in tracks] != [job.get("track_slug") for job in jobs]:
        fail(errors, "Generated DAW mutation queue runbook track order must mirror the mutation package")

    path_fields = [
        "request_path",
        "receipt_template_path",
        "operator_evidence_path",
        "bundle_manifest_path",
        "launch_plan_path",
        "staged_midi_path",
    ]
    for track, job in zip(tracks, jobs, strict=False):
        slug = job.get("track_slug")
        if track.get("track_title") != job.get("track_title"):
            fail(errors, f"Generated DAW mutation queue runbook track title is stale: {slug}")
        if track.get("execution_mode") != job.get("execution_mode"):
            fail(errors, f"Generated DAW mutation queue runbook execution mode is stale: {slug}")
        if track.get("planned_action_count") != len(job.get("executable_action_ids", [])):
            fail(errors, f"Generated DAW mutation queue runbook planned action count is stale: {slug}")
        if track.get("approval_gates_required") != job.get("approval_gates_required"):
            fail(errors, f"Generated DAW mutation queue runbook approval gates are stale: {slug}")
        if track.get("blocked_action_groups") != job.get("blocked_action_groups"):
            fail(errors, f"Generated DAW mutation queue runbook blocked action groups are stale: {slug}")

        for path_field in path_fields:
            value = track.get(path_field)
            path = Path(str(value or ""))
            if not isinstance(value, str) or path.is_absolute() or ".." in path.parts or path.parts[:1] != ("output",):
                fail(errors, f"Generated DAW mutation queue runbook {path_field} must stay under ignored output/: {slug}")

        expected_request = f"output/daw-mutations/{slug}/mutation-request.json"
        expected_evidence = f"output/daw-mutations/{slug}/operator-evidence.json"
        expected_staged_request = f"output/daw-import-bundles/{slug}/mutation-request.json"
        expected_receipt = f"output/daw-import-bundles/{slug}/applied-receipt.json"
        expected_prepare_track = [
            "python3",
            "scripts/prepare_live12_daw_mutation.py",
            "--track",
            str(slug),
            "--stable",
        ]
        if track.get("prepare_track_command") != expected_prepare_track:
            fail(errors, f"Generated DAW mutation queue runbook prepare_track_command is stale: {slug}")
        expected_stage_bundle = [
            "python3",
            "scripts/stage_live12_daw_import_bundle.py",
            "--request",
            expected_request,
            "--stable",
        ]
        if track.get("stage_bundle_command") != expected_stage_bundle:
            fail(errors, f"Generated DAW mutation queue runbook stage_bundle_command is stale: {slug}")
        expected_gated_launch = [
            "python3",
            "scripts/stage_live12_daw_import_bundle.py",
            "--request",
            expected_request,
            "--launch-ableton",
            "--confirm-live-mutation",
            "--operator-approval-reference",
            "<approval-ref>",
            "--rollback-copy-reference",
            "<rollback-copy-ref>",
        ]
        if track.get("gated_launch_command") != expected_gated_launch:
            fail(errors, f"Generated DAW mutation queue runbook gated_launch_command is stale: {slug}")
        expected_receipt_command = [
            "python3",
            "scripts/record_live12_daw_mutation_receipt.py",
            "--request",
            expected_staged_request,
            "--evidence",
            expected_evidence,
            "--output",
            expected_receipt,
        ]
        if track.get("receipt_command") != expected_receipt_command:
            fail(errors, f"Generated DAW mutation queue runbook receipt_command is stale: {slug}")
        expected_device_ids = [device.get("id") for device in expected_runbook_max_devices(job, max_contracts)]
        if track.get("max_for_live_device_ids") != expected_device_ids:
            fail(errors, f"Generated DAW mutation queue runbook Max for Live device ids are stale: {slug}")

    markdown = markdown_path.read_text(encoding="utf-8") if markdown_path.exists() else ""
    for expected_text in [
        "# Live 12 DAW Mutation Queue Runbook",
        "queued_not_launched",
        "python3 scripts/prepare_live12_daw_mutation_queue.py --stable",
        "Do not commit Ableton sets, Max devices, rendered audio, raw source audio, credentials, cookies, or license files.",
    ]:
        if expected_text not in markdown:
            fail(errors, f"Generated DAW mutation queue runbook markdown is missing required text: {expected_text}")

    for string_value in iter_string_values(data):
        if "/Users/" in string_value:
            fail(errors, "Generated DAW mutation queue runbook must not contain absolute user paths")
        if "sources/public-domain/raw/" in string_value or AUDIO_PATH_PATTERN.search(string_value):
            fail(errors, f"Generated DAW mutation queue runbook must not contain raw audio paths: {string_value}")
        if SECRET_VALUE_PATTERN.search(string_value):
            fail(errors, "Generated DAW mutation queue runbook must not contain API tokens or bearer credentials")
    if "/Users/" in markdown or "sources/public-domain/raw/" in markdown or SECRET_VALUE_PATTERN.search(markdown):
        fail(errors, "Generated DAW mutation queue runbook markdown contains sensitive local data")


def read_varlen(data: bytes, index: int) -> tuple[int, int]:
    value = 0
    for _ in range(4):
        if index >= len(data):
            raise ValueError("truncated variable-length value")
        byte = data[index]
        index += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, index
    raise ValueError("variable-length value exceeds four bytes")


def validate_midi_file(path: Path, errors: list[str], expected_track_names: list[str]) -> None:
    try:
        data = path.read_bytes()
    except OSError as exc:
        fail(errors, f"Unable to read MIDI file {path}: {exc}")
        return

    rel = path.name
    if len(data) > 500_000:
        fail(errors, f"MIDI file is unexpectedly large: {rel}")
    if not data.startswith(b"MThd") or len(data) < 14:
        fail(errors, f"MIDI file missing SMF header: {rel}")
        return

    header_length = int.from_bytes(data[4:8], "big")
    if header_length != 6 or len(data) < 8 + header_length:
        fail(errors, f"MIDI file has invalid SMF header length: {rel}")
        return
    midi_format = int.from_bytes(data[8:10], "big")
    track_count = int.from_bytes(data[10:12], "big")
    division = int.from_bytes(data[12:14], "big")
    if midi_format != 1:
        fail(errors, f"MIDI file must be format 1: {rel}")
    if track_count < 2 or track_count > 32:
        fail(errors, f"MIDI file has unexpected track count: {rel}: {track_count}")
    if division <= 0 or division > 960:
        fail(errors, f"MIDI file has unexpected ticks-per-quarter: {rel}: {division}")

    index = 8 + header_length
    parsed_tracks = 0
    track_names = []
    while index < len(data):
        if data[index:index + 4] != b"MTrk":
            fail(errors, f"MIDI file has invalid track chunk: {rel}")
            return
        track_length = int.from_bytes(data[index + 4:index + 8], "big")
        track = data[index + 8:index + 8 + track_length]
        if len(track) != track_length:
            fail(errors, f"MIDI file has truncated track chunk: {rel}")
            return
        parsed_tracks += 1
        cursor = 0
        running_status = None
        track_has_end = False
        while cursor < len(track):
            try:
                _, cursor = read_varlen(track, cursor)
            except ValueError as exc:
                fail(errors, f"MIDI file has invalid delta time in {rel}: {exc}")
                return
            if cursor >= len(track):
                fail(errors, f"MIDI file has truncated event in {rel}")
                return
            status = track[cursor]
            if status < 0x80:
                if running_status is None:
                    fail(errors, f"MIDI file uses running status without previous status: {rel}")
                    return
                status = running_status
            else:
                cursor += 1
                if status < 0xF0:
                    running_status = status

            if status == 0xFF:
                if cursor >= len(track):
                    fail(errors, f"MIDI file has truncated meta event in {rel}")
                    return
                meta_type = track[cursor]
                cursor += 1
                try:
                    length, cursor = read_varlen(track, cursor)
                except ValueError as exc:
                    fail(errors, f"MIDI file has invalid meta event length in {rel}: {exc}")
                    return
                payload = track[cursor:cursor + length]
                if len(payload) != length:
                    fail(errors, f"MIDI file has truncated meta payload in {rel}")
                    return
                if meta_type == 0x2F:
                    track_has_end = True
                    if length != 0:
                        fail(errors, f"MIDI file End-of-Track event must be zero-length: {rel}")
                if meta_type == 0x03:
                    track_names.append(payload.decode("utf-8", errors="ignore"))
                text = payload.decode("utf-8", errors="ignore")
                if "/Users/" in text or "sources/public-domain/raw/" in text or AUDIO_PATH_PATTERN.search(text):
                    fail(errors, f"MIDI file contains local/raw audio path text: {rel}")
                if SECRET_VALUE_PATTERN.search(text):
                    fail(errors, f"MIDI file contains secret-like text: {rel}")
                cursor += length
                continue

            if status in {0xF0, 0xF7}:
                fail(errors, f"MIDI file must not contain SysEx events: {rel}")
                return
            if status >= 0xF0:
                fail(errors, f"MIDI file contains unsupported system event: {rel}: 0x{status:02x}")
                return

            event_type = status & 0xF0
            data_length = 1 if event_type in {0xC0, 0xD0} else 2
            payload = track[cursor:cursor + data_length]
            if len(payload) != data_length:
                fail(errors, f"MIDI file has truncated channel event: {rel}")
                return
            if any(byte > 127 for byte in payload):
                fail(errors, f"MIDI file has invalid channel data byte: {rel}")
                return
            cursor += data_length

        if not track_has_end:
            fail(errors, f"MIDI track is missing End-of-Track meta event: {rel}")
        index += 8 + track_length

    if parsed_tracks != track_count:
        fail(errors, f"MIDI file track count does not match header: {rel}")
    if track_count != len(expected_track_names):
        fail(errors, f"MIDI file track count does not match expected generated layers: {rel}")
    if track_names != expected_track_names:
        fail(errors, f"MIDI file track names do not match manifest layers: {rel}")


def validate_generated_composition_sketches(root: Path, errors: list[str]) -> None:
    data = load_json(root / "compositions/generated/live12-track-build-plans.json", errors)
    compositions = load_json(root / "compositions/down-tempo-punk-bluegrass-set.json", errors)
    session_template = load_json(root / "automation/live12-session-template.json", errors)
    if not data or not compositions or not session_template:
        return

    if data.get("schema_version") != 1:
        fail(errors, "Generated composition sketch plan must use schema_version 1")
    if data.get("generated_at") != STABLE_GENERATED_AT:
        fail(errors, "Generated composition sketch plan must be committed with stable generated_at")
    if data.get("generator") != "scripts/render_composition_sketches.py":
        fail(errors, "Generated composition sketch plan must name scripts/render_composition_sketches.py as generator")

    source_files = set(data.get("source_files", []))
    if source_files != EXPECTED_COMPOSITION_SKETCH_SOURCES:
        fail(errors, "Generated composition sketch source_files must match expected source manifests")
    source_hashes = data.get("source_file_sha256") or {}
    for source_file in source_files:
        if Path(source_file).is_absolute() or ".." in Path(source_file).parts or not (root / source_file).exists():
            fail(errors, f"Generated composition sketch source file is invalid: {source_file}")
            continue
        expected_hash = source_hashes.get(source_file)
        if not SHA256_PATTERN.match(str(expected_hash or "")):
            fail(errors, f"Generated composition sketch source hash is invalid: {source_file}")
        elif expected_hash != sha256_file(root / source_file):
            fail(errors, f"Generated composition sketch source hash is stale: {source_file}")

    source_track_titles = [track.get("title") for track in compositions.get("tracks", [])]
    generated_track_titles = [track.get("title") for track in data.get("tracks", [])]
    if generated_track_titles != source_track_titles:
        fail(errors, "Generated composition sketch track order must match compositions/down-tempo-punk-bluegrass-set.json")

    tempo_range = session_template.get("tempo_range_bpm", [0, 999])
    session_tracks = {track.get("name") for track in session_template.get("tracks", [])}
    device_contracts = {
        contract.removeprefix("m4l.")
        for track in session_template.get("tracks", [])
        for contract in track.get("device_contracts", [])
    }
    declared_midi_files = set()

    for track in data.get("tracks", []):
        title = track.get("title")
        if not isinstance(track.get("approximate_bars"), int) or not 4 <= track.get("approximate_bars", 0) <= 256:
            fail(errors, f"Generated composition sketch has invalid bar count: {title}")
        if not tempo_range[0] <= track.get("tempo_bpm", 0) <= tempo_range[1]:
            fail(errors, f"Generated composition sketch tempo is outside session range: {title}")
        for focus in track.get("max_for_live_focus", []):
            if focus not in device_contracts:
                fail(errors, f"Generated composition sketch references unknown Max for Live focus: {title}: {focus}")
        for layer in track.get("layers", []):
            session_track = layer.get("session_track")
            if session_track not in session_tracks:
                fail(errors, f"Generated composition sketch layer references unknown session track: {title}: {session_track}")
            channels = layer.get("midi_channels", [])
            if not isinstance(channels, list) or not channels or any(not isinstance(channel, int) or channel < 1 or channel > 16 for channel in channels):
                fail(errors, f"Generated composition sketch layer has invalid MIDI channels: {title}: {session_track}")
        midi_file = track.get("midi_file", "")
        midi_path = Path(midi_file)
        if midi_path.is_absolute() or ".." in midi_path.parts or midi_path.parts[:3] != ("compositions", "generated", "midi"):
            fail(errors, f"Generated composition sketch MIDI path must be under compositions/generated/midi: {title}")
            continue
        full_midi_path = root / midi_path
        declared_midi_files.add(str(midi_path))
        if not full_midi_path.exists():
            fail(errors, f"Generated composition sketch MIDI file is missing: {title}: {midi_file}")
            continue
        if track.get("midi_byte_size") != full_midi_path.stat().st_size:
            fail(errors, f"Generated composition sketch MIDI byte size is stale: {title}")
        if not SHA256_PATTERN.match(str(track.get("midi_sha256", ""))):
            fail(errors, f"Generated composition sketch MIDI hash is invalid: {title}")
        elif track.get("midi_sha256") != sha256_file(full_midi_path):
            fail(errors, f"Generated composition sketch MIDI hash is stale: {title}")
        expected_track_names = ["Conductor"] + [layer.get("midi_track", "") for layer in track.get("layers", [])]
        validate_midi_file(full_midi_path, errors, expected_track_names)

    actual_midi_files = {
        str(path.relative_to(root))
        for path in (root / "compositions/generated/midi").glob("*.mid")
    }
    if actual_midi_files != declared_midi_files:
        fail(errors, "Generated composition sketch MIDI files must exactly match manifest")

    expected_generated_files = {
        "compositions/generated/README.md",
        "compositions/generated/live12-track-build-plans.json",
        *declared_midi_files,
    }
    actual_generated_files = {
        str(path.relative_to(root))
        for path in (root / "compositions/generated").rglob("*")
        if path.is_file()
    }
    if actual_generated_files != expected_generated_files:
        fail(errors, "Generated composition sketch directory must contain only declared artifacts")

    for path in root.rglob("*.mid"):
        if any(part in SKIP_BINARY_SCAN_PARTS for part in path.relative_to(root).parts):
            continue
        if str(path.relative_to(root)) not in declared_midi_files:
            fail(errors, f"Unexpected MIDI file outside generated composition manifest: {path.relative_to(root)}")

    for string_value in iter_string_values(data):
        if "/Users/" in string_value:
            fail(errors, "Generated composition sketches must not contain absolute user paths")
        if "sources/public-domain/raw/" in string_value or AUDIO_PATH_PATTERN.search(string_value):
            fail(errors, f"Generated composition sketches must not contain raw audio paths: {string_value}")
        if SECRET_VALUE_PATTERN.search(string_value):
            fail(errors, "Generated composition sketches must not contain API tokens or bearer credentials")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []

    validate_required_files(root, errors)
    validate_recommended_packs(root, errors)
    validate_library_installation_plan(root, errors)
    validate_sources(root, errors)
    validate_download_ledger(root, errors)
    validate_json_contracts(root, errors)
    validate_inventory_snapshot(root, errors)
    validate_openai_orchestration(root, errors)
    validate_generated_worker_briefs(root, errors)
    validate_openai_production_swarm_queue(root, errors)
    validate_generated_daw_action_plan(root, errors)
    validate_public_domain_source_deck(root, errors)
    validate_generated_daw_mutation_package(root, errors)
    validate_generated_daw_mutation_runbook(root, errors)
    validate_generated_daw_mutation_queue_runbook(root, errors)
    validate_generated_composition_sketches(root, errors)
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
