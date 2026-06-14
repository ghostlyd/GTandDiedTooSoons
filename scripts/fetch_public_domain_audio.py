#!/usr/bin/env python3
"""Fetch explicitly approved public-domain source audio with provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse


DOWNLOADABLE_RIGHTS = {"public_domain", "cc0", "cc_by"}


def require_https_url(value: str, field: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{field} must be an https URL: {value}")
    return parsed.netloc.lower()


def host_matches(host: str, allowed_hosts: list[str]) -> bool:
    normalized = host.lower()
    for allowed in allowed_hosts:
        allowed_normalized = allowed.lower()
        if normalized == allowed_normalized:
            return True
    return False


def allowed_download_hosts(entry: dict) -> list[str]:
    explicit = entry.get("allowed_download_hosts") or []
    if explicit:
        return explicit
    return [require_https_url(entry["source_url"], "source_url")]


def allowed_download_path_prefixes(entry: dict) -> list[str]:
    return entry.get("allowed_download_path_prefixes") or []


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


def path_matches_prefix(path: str, prefixes: list[str]) -> bool:
    canonical_path = canonical_url_path(path)
    for prefix in prefixes:
        canonical_prefix = canonical_url_path(prefix)
        if canonical_path == canonical_prefix:
            return True
        prefix_with_boundary = canonical_prefix if canonical_prefix.endswith("/") else canonical_prefix + "/"
        if canonical_path.startswith(prefix_with_boundary):
            return True
    return False


def require_allowed_download_url(entry: dict, value: str, field: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{field} must be an https URL: {value}")

    host = parsed.netloc.lower()
    allowed_hosts = allowed_download_hosts(entry)
    if not host_matches(host, allowed_hosts):
        raise ValueError(f"{entry['id']} {field} host {host} is not in allowed_download_hosts: {allowed_hosts}")

    prefixes = allowed_download_path_prefixes(entry)
    if not prefixes:
        raise ValueError(f"{entry['id']} requires allowed_download_path_prefixes before download")
    if not path_matches_prefix(parsed.path, prefixes):
        raise ValueError(f"{entry['id']} {field} path is outside allowed_download_path_prefixes: {parsed.path}")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-")


def load_catalog(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def filename_from_url(url: str) -> str:
    name = Path(urlparse(url).path).name
    return name or "downloaded-audio"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch(entry: dict, destination: Path, max_mb: int) -> dict:
    url = entry["download_url"]
    max_bytes = max_mb * 1024 * 1024
    partial = destination.with_name(destination.name + ".part")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "GTandDiedTooSoons-provenance-fetcher/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            final_url = response.geturl()
            require_allowed_download_url(entry, final_url, "final_url")

            length = response.headers.get("Content-Length")
            if length and int(length) > max_bytes:
                raise ValueError(f"Refusing download larger than {max_mb} MB: {url}")

            total = 0
            with partial.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError(f"Refusing download that exceeded {max_mb} MB while streaming: {url}")
                    handle.write(chunk)
            partial.replace(destination)
            return {
                "byte_size": total,
                "content_type": response.headers.get("Content-Type"),
                "final_url": final_url,
            }
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def validate_download_entry(entry: dict) -> None:
    if entry.get("rights_status") not in DOWNLOADABLE_RIGHTS:
        raise ValueError(f"{entry['id']} is approved but has non-downloadable rights status: {entry.get('rights_status')}")
    if not entry.get("download_url"):
        raise ValueError(f"{entry['id']} is approved but missing download_url")

    require_https_url(entry["source_url"], "source_url")
    require_allowed_download_url(entry, entry["download_url"], "download_url")

    evidence = entry.get("browser_evidence") or {}
    if not evidence.get("captured_url") or not evidence.get("artifact_path") or not evidence.get("captured_at"):
        raise ValueError(f"{entry['id']} requires browser_evidence with captured_url, artifact_path, and captured_at before download")

    require_https_url(evidence["captured_url"], "browser_evidence.captured_url")

    rights_evidence = entry.get("rights_evidence") or {}
    required_rights_fields = ["evidence_url", "captured_at", "rights_summary", "reuse_scope", "credit_recommendation"]
    missing = [field for field in required_rights_fields if not rights_evidence.get(field)]
    if missing:
        raise ValueError(f"{entry['id']} requires rights_evidence fields before download: {', '.join(missing)}")
    require_https_url(rights_evidence["evidence_url"], "rights_evidence.evidence_url")


def load_ledger(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": 1, "generated_at": None, "downloads": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError(f"{path} must use schema_version 1")
    data.setdefault("downloads", [])
    return data


def upsert_ledger_record(path: Path, record: dict) -> None:
    ledger = load_ledger(path)
    ledger["downloads"] = [
        item
        for item in ledger["downloads"]
        if not (item.get("source_id") == record["source_id"] and item.get("download_url") == record["download_url"])
    ]
    ledger["downloads"].append(record)
    ledger["downloads"].sort(key=lambda item: (item.get("source_id", ""), item.get("local_file", "")))
    ledger["generated_at"] = record["fetched_at"]
    write_json_atomic(path, ledger)


def write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def build_ledger_record(entry: dict, target_file: Path, fetch_metadata: dict, fetched_at: str) -> dict:
    return {
        "source_id": entry["id"],
        "name": entry["name"],
        "fetched_at": fetched_at,
        "local_file": str(target_file),
        "sha256": file_sha256(target_file),
        "byte_size": target_file.stat().st_size,
        "content_type": fetch_metadata.get("content_type"),
        "download_url": entry["download_url"],
        "final_url": fetch_metadata.get("final_url"),
        "source_url": entry["source_url"],
        "rights_status": entry["rights_status"],
        "credit_line": entry["credit_line"],
        "browser_evidence": entry["browser_evidence"],
        "rights_evidence": entry["rights_evidence"],
        "transformation": "none; raw source audio fetched for local Ableton/Sampler use",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default="catalogs/public-domain-bluegrass-sources.json")
    parser.add_argument("--output-dir", default="sources/public-domain/raw")
    parser.add_argument("--ledger", default="sources/public-domain/download-ledger.json")
    parser.add_argument("--execute", action="store_true", help="Actually download approved entries. Default is preview only.")
    parser.add_argument("--source-id", action="append", default=[], help="Fetch only the approved source id. Repeat for multiple ids.")
    parser.add_argument("--max-mb", type=int, default=250)
    args = parser.parse_args()

    catalog = load_catalog(Path(args.catalog))
    output_root = Path(args.output_dir)
    downloadable = []
    approved_ids = set()
    requested_ids = set(args.source_id)

    for entry in catalog.get("sources", []):
        if not entry.get("approved_for_download"):
            continue
        approved_ids.add(entry.get("id"))
        validate_download_entry(entry)
        if requested_ids and entry.get("id") not in requested_ids:
            continue
        downloadable.append(entry)

    missing_ids = sorted(requested_ids - approved_ids)
    if missing_ids:
        print(f"Requested source id is not approved or does not exist: {', '.join(missing_ids)}", file=sys.stderr)
        return 1

    if not downloadable:
        print("No matching approved downloads found. Review catalog entries and set approved_for_download only after rights checks.")
        return 0

    for entry in downloadable:
        target_dir = output_root / slug(entry["id"])
        filename = filename_from_url(entry["download_url"])
        target_file = target_dir / filename
        provenance_file = target_dir / "PROVENANCE.json"

        print(f"{'Downloading' if args.execute else 'Would download'} {entry['id']} -> {target_file}")
        if args.execute:
            target_dir.mkdir(parents=True, exist_ok=True)
            fetch_metadata = fetch(entry, target_file, args.max_mb)
            fetched_at = utc_now_iso()
            ledger_record = build_ledger_record(entry, target_file, fetch_metadata, fetched_at)
            provenance = {
                "fetched_at": fetched_at,
                "source": entry,
                "local_file": str(target_file),
                "sha256": ledger_record["sha256"],
                "byte_size": ledger_record["byte_size"],
                "content_type": ledger_record["content_type"],
                "final_url": ledger_record["final_url"],
            }
            write_json_atomic(provenance_file, provenance)
            print(f"Wrote {provenance_file}")
            upsert_ledger_record(Path(args.ledger), ledger_record)
            print(f"Updated {args.ledger}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
