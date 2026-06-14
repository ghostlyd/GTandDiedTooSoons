#!/usr/bin/env python3
"""Render a deterministic public-domain source deck manifest and operator handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "automation" / "generated" / "public-domain-source-deck.json"
DEFAULT_MARKDOWN_OUTPUT = ROOT / "docs" / "public-domain-source-deck.md"
STABLE_GENERATED_AT = "1970-01-01T00:00:00Z"

SOURCE_FILES = [
    "catalogs/public-domain-bluegrass-sources.json",
    "sources/public-domain/download-ledger.json",
    "automation/generated/live12-daw-action-plan.json",
]


def read_json(relative_path: str) -> dict[str, Any]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def approved_sources(catalog: dict[str, Any], ledger: dict[str, Any]) -> list[dict[str, Any]]:
    catalog_by_id = {
        source["id"]: source
        for source in catalog.get("sources", [])
        if source.get("id")
    }
    sources = []
    for record in ledger.get("downloads", []):
        source = catalog_by_id.get(record.get("source_id"), {})
        sources.append(
            {
                "source_id": record["source_id"],
                "name": record["name"],
                "rights_status": record["rights_status"],
                "sha256": record["sha256"],
                "byte_size": record["byte_size"],
                "content_type": record.get("content_type"),
                "credit_line": record["credit_line"],
                "source_url": record["source_url"],
                "item_url": source.get("item_url"),
                "project_use": source.get("project_use", record.get("transformation", "")),
                "transformation": record["transformation"],
                "browser_evidence": record["browser_evidence"],
                "rights_evidence": record["rights_evidence"],
                "local_file_policy": "raw_audio_ignored_metadata_only",
            }
        )
    return sources


def track_assignments(daw_plan: dict[str, Any]) -> list[dict[str, Any]]:
    assignments = []
    for track in daw_plan.get("tracks", []):
        source_deck = track.get("source_deck", {})
        candidates = source_deck.get("candidate_sources", [])
        assignments.append(
            {
                "track_slug": track["slug"],
                "track_title": track["title"],
                "deck_state": source_deck.get("default_state"),
                "approval_gate": source_deck.get("approval_gate"),
                "session_track": source_deck.get("session_track"),
                "candidate_source_ids": [candidate["source_id"] for candidate in candidates],
                "candidate_source_count": len(candidates),
                "required_before_unmute": source_deck.get("required_checks", []),
            }
        )
    return assignments


def render(stable: bool = False) -> dict[str, Any]:
    catalog = read_json("catalogs/public-domain-bluegrass-sources.json")
    ledger = read_json("sources/public-domain/download-ledger.json")
    daw_plan = read_json("automation/generated/live12-daw-action-plan.json")
    sources = approved_sources(catalog, ledger)
    assignments = track_assignments(daw_plan)
    return {
        "schema_version": 1,
        "generated_at": STABLE_GENERATED_AT if stable else utc_now(),
        "generator": "scripts/render_public_domain_source_deck.py",
        "source_files": SOURCE_FILES,
        "source_file_sha256": {relative_path: sha256_file(ROOT / relative_path) for relative_path in SOURCE_FILES},
        "purpose": "Metadata-only public-domain source deck handoff for Ableton Live 12 / Max for Live sampling and reference work.",
        "deck_policy": {
            "session_track": "Public Domain Source Deck",
            "default_state": "muted_until_human_provenance_review",
            "approval_gate": "live_set_mutation",
            "unmute_policy": "Only unmute after rights/provenance review, source credit review, and operator approval.",
        },
        "artifact_policy": {
            "git_policy": "metadata_only_no_raw_audio",
            "raw_audio_root": "sources/public-domain/raw",
            "must_not_commit": [
                "raw source audio",
                "downloaded samples",
                "rendered audio",
                "Ableton sets",
                "compiled Max for Live devices",
                "credentials",
                "cookies",
                "license files",
            ],
        },
        "approved_source_count": len(sources),
        "approved_sources": sources,
        "track_assignment_count": len(assignments),
        "track_assignments": assignments,
    }


def render_markdown(deck: dict[str, Any]) -> str:
    lines = [
        "# Public-Domain Source Deck",
        "",
        "Generated metadata only from the source catalog, download ledger, and DAW action plan.",
        "",
        f"Default state: `{deck['deck_policy']['default_state']}`.",
        "",
        "raw source audio must remain outside Git in the ignored public-domain raw source folder.",
        "",
        "## Approved Sources",
        "",
    ]
    for source in deck["approved_sources"]:
        lines.extend(
            [
                f"### {source['name']}",
                "",
                f"- Source ID: `{source['source_id']}`",
                f"- Rights status: `{source['rights_status']}`",
                f"- SHA-256: `{source['sha256']}`",
                f"- Byte size: `{source['byte_size']}`",
                f"- Credit: {source['credit_line']}",
                f"- Project use: {source['project_use']}",
                f"- Reuse scope: {source['rights_evidence']['reuse_scope']}",
                "",
            ]
        )
    lines.extend(["## Track Assignments", ""])
    for assignment in deck["track_assignments"]:
        lines.extend(
            [
                f"### {assignment['track_title']}",
                "",
                f"- Track slug: `{assignment['track_slug']}`",
                f"- Deck state: `{assignment['deck_state']}`",
                f"- Candidate source count: `{assignment['candidate_source_count']}`",
                f"- Candidate source IDs: {', '.join(f'`{source_id}`' for source_id in assignment['candidate_source_ids'])}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON path.")
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT, help="Output Markdown path.")
    parser.add_argument("--stable", action="store_true", help="Use deterministic generated_at value.")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing outputs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = render(stable=args.stable)
    markdown = render_markdown(data)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "schema_version": data["schema_version"],
                    "approved_source_count": data["approved_source_count"],
                    "track_assignment_count": data["track_assignment_count"],
                    "generated_at": data["generated_at"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(markdown, encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"Wrote {args.markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
