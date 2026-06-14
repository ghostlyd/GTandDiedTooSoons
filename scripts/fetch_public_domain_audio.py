#!/usr/bin/env python3
"""Fetch explicitly approved public-domain source audio with provenance."""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


DOWNLOADABLE_RIGHTS = {"public_domain", "cc0", "cc_by", "no_known_restrictions"}


def require_https_url(value: str, field: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{field} must be an https URL: {value}")
    return parsed.netloc.lower()


def host_matches(host: str, allowed_hosts: list[str]) -> bool:
    normalized = host.lower()
    for allowed in allowed_hosts:
        allowed_normalized = allowed.lower()
        if normalized == allowed_normalized or normalized.endswith("." + allowed_normalized):
            return True
    return False


def allowed_download_hosts(entry: dict) -> list[str]:
    explicit = entry.get("allowed_download_hosts") or []
    if explicit:
        return explicit
    return [require_https_url(entry["source_url"], "source_url")]


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-")


def load_catalog(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def filename_from_url(url: str) -> str:
    name = Path(urlparse(url).path).name
    return name or "downloaded-audio"


def fetch(entry: dict, destination: Path, max_mb: int) -> None:
    url = entry["download_url"]
    allowed_hosts = allowed_download_hosts(entry)
    max_bytes = max_mb * 1024 * 1024
    partial = destination.with_name(destination.name + ".part")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "GTandDiedTooSoons-provenance-fetcher/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            final_url = response.geturl()
            final_host = require_https_url(final_url, "final_url")
            if not host_matches(final_host, allowed_hosts):
                raise ValueError(f"Redirected download host {final_host} is not allowed for {entry['id']}: {allowed_hosts}")

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
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def validate_download_entry(entry: dict) -> None:
    if entry.get("rights_status") not in DOWNLOADABLE_RIGHTS:
        raise ValueError(f"{entry['id']} is approved but has non-downloadable rights status: {entry.get('rights_status')}")
    if not entry.get("download_url"):
        raise ValueError(f"{entry['id']} is approved but missing download_url")

    require_https_url(entry["source_url"], "source_url")
    download_host = require_https_url(entry["download_url"], "download_url")
    allowed_hosts = allowed_download_hosts(entry)
    if not host_matches(download_host, allowed_hosts):
        raise ValueError(f"{entry['id']} download host {download_host} is not in allowed_download_hosts: {allowed_hosts}")

    evidence = entry.get("browser_evidence") or {}
    if not evidence.get("captured_url") or not evidence.get("artifact_path") or not evidence.get("captured_at"):
        raise ValueError(f"{entry['id']} requires browser_evidence with captured_url, artifact_path, and captured_at before download")

    require_https_url(evidence["captured_url"], "browser_evidence.captured_url")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default="catalogs/public-domain-bluegrass-sources.json")
    parser.add_argument("--output-dir", default="sources/public-domain/raw")
    parser.add_argument("--execute", action="store_true", help="Actually download approved entries. Default is preview only.")
    parser.add_argument("--max-mb", type=int, default=250)
    args = parser.parse_args()

    catalog = load_catalog(Path(args.catalog))
    output_root = Path(args.output_dir)
    downloadable = []

    for entry in catalog.get("sources", []):
        if not entry.get("approved_for_download"):
            continue
        validate_download_entry(entry)
        downloadable.append(entry)

    if not downloadable:
        print("No approved downloads found. Review catalog entries and set approved_for_download only after rights checks.")
        return 0

    for entry in downloadable:
        target_dir = output_root / slug(entry["id"])
        filename = filename_from_url(entry["download_url"])
        target_file = target_dir / filename
        provenance_file = target_dir / "PROVENANCE.json"

        print(f"{'Downloading' if args.execute else 'Would download'} {entry['id']} -> {target_file}")
        if args.execute:
            target_dir.mkdir(parents=True, exist_ok=True)
            fetch(entry, target_file, args.max_mb)
            provenance = {
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": entry,
                "local_file": str(target_file),
            }
            provenance_file.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"Wrote {provenance_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
