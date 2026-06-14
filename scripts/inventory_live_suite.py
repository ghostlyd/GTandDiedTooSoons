#!/usr/bin/env python3
"""Create a non-sensitive Ableton/Arturia inventory snapshot."""

from __future__ import annotations

import argparse
import json
import os
import platform
import plistlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HOME = Path.home()


def expand(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def display_path(path: Path) -> str:
    try:
        return "~/" + str(path.resolve().relative_to(HOME))
    except ValueError:
        return str(path)


def child_dirs(root: Path) -> list[dict[str, str]]:
    if not root.exists():
        return []
    return [
        {"name": child.name, "path": display_path(child)}
        for child in sorted(root.iterdir(), key=lambda p: p.name.lower())
        if child.is_dir() and not child.name.startswith(".")
    ]


def child_names(root: Path, exclude: set[str] | None = None) -> list[str]:
    excluded = exclude or set()
    return [
        child.name
        for child in sorted(root.iterdir(), key=lambda p: p.name.lower())
        if child.is_dir() and not child.name.startswith(".") and child.name not in excluded
    ] if root.exists() else []


def plist_version(app_path: Path) -> str | None:
    info = app_path / "Contents" / "Info.plist"
    if not info.exists():
        return None
    try:
        with info.open("rb") as handle:
            data = plistlib.load(handle)
        return data.get("CFBundleShortVersionString") or data.get("CFBundleVersion")
    except (OSError, plistlib.InvalidFileException):
        return None


def count_extensions(root: Path, extensions: set[str], max_files: int = 25000) -> dict[str, int]:
    counts = {ext: 0 for ext in sorted(extensions)}
    if not root.exists():
        return counts

    seen = 0
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in {"Crash", "Logs"}]
        for filename in filenames:
            seen += 1
            suffix = Path(filename).suffix.lower()
            if suffix in counts:
                counts[suffix] += 1
            if seen >= max_files:
                counts["_truncated"] = 1
                return counts
    return counts


def sqlite_rows(path: Path, query: str) -> tuple[list[tuple[Any, ...]], str | None]:
    if not path.exists():
        return [], "database not found"
    try:
        uri = path.resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            return connection.execute(query).fetchall(), None
    except sqlite3.Error as exc:
        return [], f"{type(exc).__name__}: {exc}"


def ableton_database_inventory(support_root: Path) -> dict[str, Any]:
    database_root = support_root / "Live Database"
    file_databases = sorted(database_root.glob("Live-files-*.db"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    file_database = file_databases[0] if file_databases else database_root / "Live-files-12300.db"

    read_errors = []
    installed_rows, installed_error = sqlite_rows(
        file_database,
        """
        SELECT f.name
        FROM places p
        JOIN files f ON p.file_id = f.file_id
        WHERE p.level = 0 AND p.folder_kind = 0
        ORDER BY lower(f.name)
        """,
    )
    if installed_error:
        read_errors.append(f"installed_pack_places: {installed_error}")

    indexed_rows, indexed_error = sqlite_rows(
        file_database,
        """
        SELECT child.name
        FROM files child
        WHERE child.parent_id = (SELECT file_id FROM files WHERE name = '<packs>' LIMIT 1)
        ORDER BY lower(child.name)
        """,
    )
    if indexed_error:
        read_errors.append(f"indexed_pack_candidates: {indexed_error}")

    installed = [row[0] for row in installed_rows]
    indexed = [row[0] for row in indexed_rows]
    return {
        "file_database": display_path(file_database),
        "file_database_exists": file_database.exists(),
        "read_status": "ok" if file_database.exists() and not read_errors else "degraded",
        "read_errors": read_errors,
        "installed_pack_places": installed,
        "indexed_pack_candidates": indexed,
        "available_not_installed": [name for name in indexed if name not in installed],
    }


def arturia_resource_inventory(root: Path) -> dict[str, Any]:
    excluded_products = {"Presets", "Samples", "Shared", "Arturia Software Center"}
    presets = root / "Presets"
    samples = root / "Samples"
    return {
        "resource_root": display_path(root),
        "resource_root_exists": root.exists(),
        "products": child_names(root, excluded_products),
        "preset_products": child_names(presets, {"Shared"}),
        "sample_products": child_names(samples),
        "preset_root": display_path(presets),
        "sample_root": display_path(samples),
    }


def build_inventory() -> dict[str, Any]:
    ableton_app = expand(os.getenv("ABLETON_APP", "/Applications/Ableton Live 12 Suite.app"))
    factory_packs = expand(os.getenv("ABLETON_FACTORY_PACKS_DIR", "~/Music/Ableton/Factory Packs"))
    user_library = expand(os.getenv("ABLETON_USER_LIBRARY_DIR", "~/Music/Ableton/User Library"))
    ableton_support = expand(os.getenv("ABLETON_SUPPORT_DIR", "~/Library/Application Support/Ableton"))
    arturia_apps = expand(os.getenv("ARTURIA_APP_DIR", "/Applications/Arturia"))
    arturia_resources = expand(os.getenv("ARTURIA_RESOURCE_DIR", "/Library/Arturia"))
    vst3_roots = [
        expand("~/Library/Audio/Plug-Ins/VST3"),
        expand("/Library/Audio/Plug-Ins/VST3"),
    ]
    au_roots = [
        expand("~/Library/Audio/Plug-Ins/Components"),
        expand("/Library/Audio/Plug-Ins/Components"),
    ]

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "host": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "ableton": {
            "app": {
                "name": ableton_app.name,
                "path": display_path(ableton_app),
                "exists": ableton_app.exists(),
                "version": plist_version(ableton_app),
            },
            "factory_packs_root": display_path(factory_packs),
            "factory_packs": child_dirs(factory_packs),
            "user_library": {
                "path": display_path(user_library),
                "exists": user_library.exists(),
                "counts": count_extensions(user_library, {".adg", ".adv", ".alc", ".amxd", ".als", ".wav", ".aif", ".aiff"}),
            },
            "support_dir": {
                "path": display_path(ableton_support),
                "exists": ableton_support.exists(),
                "children": [entry["name"] for entry in child_dirs(ableton_support)],
            },
            "live_database": ableton_database_inventory(ableton_support),
        },
        "arturia": {
            "app_root": display_path(arturia_apps),
            "applications": child_dirs(arturia_apps),
            "resources": arturia_resource_inventory(arturia_resources),
        },
        "plugins": {
            "vst3_roots": [
                {"path": display_path(root), "exists": root.exists(), "arturia_plugins": [p["name"] for p in child_dirs(root) if "arturia" in p["name"].lower()]}
                for root in vst3_roots
            ],
            "audio_unit_roots": [
                {"path": display_path(root), "exists": root.exists(), "arturia_plugins": [p["name"] for p in child_dirs(root) if "arturia" in p["name"].lower()]}
                for root in au_roots
            ],
        },
    }


def write_markdown(inventory: dict[str, Any], path: Path) -> None:
    ableton = inventory["ableton"]
    arturia = inventory["arturia"]
    lines = [
        "# Live 12 Local Inventory",
        "",
        f"Generated: `{inventory['generated_at']}`",
        "",
        "## Ableton",
        "",
        f"- App: `{ableton['app']['name']}`",
        f"- Version: `{ableton['app']['version'] or 'not detected'}`",
        f"- Path: `{ableton['app']['path']}`",
        "",
        "### Factory Packs",
        "",
    ]
    lines.extend(f"- {pack['name']}" for pack in ableton["factory_packs"])
    if not ableton["factory_packs"]:
        lines.append("- None detected")
    lines.extend([
        "",
        "### Live Database Pack Index",
        "",
        f"- Installed pack places: `{len(ableton['live_database']['installed_pack_places'])}`",
        f"- Indexed pack candidates: `{len(ableton['live_database']['indexed_pack_candidates'])}`",
        f"- Available/not installed candidates: `{len(ableton['live_database']['available_not_installed'])}`",
        "",
        "Installed pack places:",
        "",
    ])
    lines.extend(f"- {name}" for name in ableton["live_database"]["installed_pack_places"])
    lines.extend([
        "",
        "Available/not installed candidates:",
        "",
    ])
    lines.extend(f"- {name}" for name in ableton["live_database"]["available_not_installed"])
    lines.extend([
        "",
        "## Arturia Applications",
        "",
    ])
    lines.extend(f"- {app['name']}" for app in arturia["applications"])
    if not arturia["applications"]:
        lines.append("- None detected")
    resources = arturia["resources"]
    lines.extend([
        "",
        "## Arturia Resources",
        "",
        f"- Resource root: `{resources['resource_root']}`",
        f"- Installed resource products: `{len(resources['products'])}`",
        f"- Preset product folders: `{len(resources['preset_products'])}`",
        f"- Sample product folders: `{len(resources['sample_products'])}`",
        "",
        "### Preset Product Folders",
        "",
    ])
    lines.extend(f"- {name}" for name in resources["preset_products"])
    if not resources["preset_products"]:
        lines.append("- None detected")
    lines.extend([
        "",
        "### Sample Product Folders",
        "",
    ])
    lines.extend(f"- {name}" for name in resources["sample_products"])
    if not resources["sample_products"]:
        lines.append("- None detected")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="inventory/live12-local-inventory.json", help="JSON output path")
    parser.add_argument("--dry-run", action="store_true", help="Build inventory and print summary without writing files")
    args = parser.parse_args()

    inventory = build_inventory()
    output = Path(args.output)

    if args.dry_run:
        print(json.dumps({
            "ableton_version": inventory["ableton"]["app"]["version"],
            "factory_pack_count": len(inventory["ableton"]["factory_packs"]),
            "ableton_indexed_pack_count": len(inventory["ableton"]["live_database"]["indexed_pack_candidates"]),
            "ableton_available_not_installed_count": len(inventory["ableton"]["live_database"]["available_not_installed"]),
            "arturia_app_count": len(inventory["arturia"]["applications"]),
            "arturia_resource_product_count": len(inventory["arturia"]["resources"]["products"]),
            "arturia_preset_product_count": len(inventory["arturia"]["resources"]["preset_products"]),
            "arturia_sample_product_count": len(inventory["arturia"]["resources"]["sample_products"]),
        }, indent=2))
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(inventory, output.with_suffix(".md"))
    print(f"Wrote {output}")
    print(f"Wrote {output.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
