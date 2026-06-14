#!/usr/bin/env python3
"""Create a non-sensitive Ableton/Arturia inventory snapshot."""

from __future__ import annotations

import argparse
import json
import os
import platform
import plistlib
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


def build_inventory() -> dict[str, Any]:
    ableton_app = expand(os.getenv("ABLETON_APP", "/Applications/Ableton Live 12 Suite.app"))
    factory_packs = expand(os.getenv("ABLETON_FACTORY_PACKS_DIR", "~/Music/Ableton/Factory Packs"))
    user_library = expand(os.getenv("ABLETON_USER_LIBRARY_DIR", "~/Music/Ableton/User Library"))
    ableton_support = expand(os.getenv("ABLETON_SUPPORT_DIR", "~/Library/Application Support/Ableton"))
    arturia_apps = expand(os.getenv("ARTURIA_APP_DIR", "/Applications/Arturia"))
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
        },
        "arturia": {
            "app_root": display_path(arturia_apps),
            "applications": child_dirs(arturia_apps),
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
        "## Arturia Applications",
        "",
    ])
    lines.extend(f"- {app['name']}" for app in arturia["applications"])
    if not arturia["applications"]:
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
            "arturia_app_count": len(inventory["arturia"]["applications"]),
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
