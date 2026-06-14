#!/usr/bin/env python3
"""Render deterministic Live-importable MIDI sketches from composition manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "compositions" / "generated"
STABLE_GENERATED_AT = "1970-01-01T00:00:00Z"
PPQ = 480
BAR_TICKS = PPQ * 4
SOURCE_FILES = [
    "compositions/down-tempo-punk-bluegrass-set.json",
    "automation/live12-session-template.json",
]


ROOT_TO_MIDI = {
    "C": 48,
    "C#": 49,
    "Db": 49,
    "D": 50,
    "D#": 51,
    "Eb": 51,
    "E": 52,
    "F": 53,
    "F#": 54,
    "Gb": 54,
    "G": 55,
    "G#": 56,
    "Ab": 56,
    "A": 57,
    "A#": 58,
    "Bb": 58,
    "B": 59,
}

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "pentatonic": [0, 3, 5, 7, 10],
}

LAYER_DEFINITIONS = [
    {
        "id": "aeroband_banjo_lead",
        "session_track": "AeroBand Banjo Lead",
        "midi_track": "AeroBand Banjo Lead",
        "channel": 0,
        "program": 105,
        "gm_sound": "Banjo",
        "motif": "Sixteenth-note forward roll with section-density changes.",
        "traditional": True,
        "electronic": False,
    },
    {
        "id": "fiddle_hybrid_strings",
        "session_track": "Fiddle / Hybrid Strings",
        "midi_track": "Fiddle / Hybrid Strings",
        "channel": 1,
        "program": 40,
        "gm_sound": "Violin",
        "motif": "Long root/fifth drones and answer tones for fiddle-family contour.",
        "traditional": True,
        "electronic": True,
    },
    {
        "id": "mandolin_chop",
        "session_track": "Mandolin Chop",
        "midi_track": "Mandolin Chop",
        "channel": 2,
        "program": 25,
        "gm_sound": "Steel Guitar proxy",
        "motif": "Short offbeat chop chords on beats two and four.",
        "traditional": True,
        "electronic": False,
    },
    {
        "id": "dobro_metallic_slide",
        "session_track": "Dobro / Metallic Slide",
        "midi_track": "Dobro / Metallic Slide",
        "channel": 3,
        "program": 26,
        "gm_sound": "Jazz Guitar proxy",
        "motif": "Sparse slide-like approaches into section roots.",
        "traditional": True,
        "electronic": True,
    },
    {
        "id": "upright_bass_sub",
        "session_track": "Upright Bass / Sub",
        "midi_track": "Upright Bass / Sub",
        "channel": 4,
        "program": 32,
        "gm_sound": "Acoustic Bass",
        "motif": "Root/fifth walk doubled conceptually by sidechained sub.",
        "traditional": True,
        "electronic": True,
    },
    {
        "id": "acoustic_guitar_boom_chuck",
        "session_track": "Acoustic Guitar Boom-Chuck",
        "midi_track": "Acoustic Guitar Boom-Chuck",
        "channel": 5,
        "program": 25,
        "gm_sound": "Steel Guitar",
        "motif": "Alternating bass-note boom and short chord chuck for bluegrass rhythm drive.",
        "traditional": True,
        "electronic": False,
    },
    {
        "id": "punk_kit",
        "session_track": "Punk Kit",
        "midi_track": "Punk Kit",
        "channel": 9,
        "program": None,
        "gm_sound": "GM Drum Kit",
        "motif": "Dry kick/snare/hat hits with end-of-section fills.",
        "traditional": False,
        "electronic": False,
    },
    {
        "id": "deep_house_machines",
        "session_track": "Deep House Machines",
        "midi_track": "Deep House Machines",
        "channel": 9,
        "program": None,
        "gm_sound": "GM drum machine plus synth-stab channel",
        "motif": "Four-on-floor kick, hats, claps, and minor chord stabs.",
        "traditional": False,
        "electronic": True,
    },
    {
        "id": "alien_sky",
        "session_track": "Alien Sky",
        "midi_track": "Alien Sky",
        "channel": 11,
        "program": 89,
        "gm_sound": "Warm Pad",
        "motif": "Wide held tones for Granulator/PitchLoop/spectral processing.",
        "traditional": False,
        "electronic": True,
    },
]


@dataclass(frozen=True)
class MidiEvent:
    tick: int
    priority: int
    data: bytes


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(relative_path: str) -> dict[str, Any]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "untitled"


def parse_duration_seconds(value: str) -> int:
    minutes, seconds = value.split(":", 1)
    return int(minutes) * 60 + int(seconds)


def normalize_root(key_center: str) -> str:
    lowered = key_center.lower()
    if lowered.startswith("b flat") or lowered.startswith("bb"):
        return "Bb"
    token = key_center.split()[0].strip()
    return {"A#": "Bb"}.get(token, token)


def scale_for_key(key_center: str) -> list[int]:
    lowered = key_center.lower()
    for name, scale in SCALES.items():
        if name in lowered:
            return scale
    return SCALES["minor"] if "minor" in lowered else SCALES["major"]


def degree(root: int, scale: list[int], index: int, octave: int = 0) -> int:
    scale_index = index % len(scale)
    octave_offset = index // len(scale)
    return root + scale[scale_index] + 12 * (octave + octave_offset)


def varlen(value: int) -> bytes:
    buffer = value & 0x7F
    value >>= 7
    while value:
        buffer <<= 8
        buffer |= (value & 0x7F) | 0x80
        value >>= 7
    output = bytearray()
    while True:
        output.append(buffer & 0xFF)
        if buffer & 0x80:
            buffer >>= 8
        else:
            break
    return bytes(output)


def meta_text(kind: int, value: str) -> bytes:
    payload = value.encode("utf-8")
    return bytes([0xFF, kind]) + varlen(len(payload)) + payload


def track_name(value: str) -> bytes:
    return meta_text(0x03, value)


def marker(value: str) -> bytes:
    return meta_text(0x06, value)


def tempo_event(bpm: int) -> bytes:
    micros = round(60_000_000 / bpm)
    return bytes([0xFF, 0x51, 0x03]) + micros.to_bytes(3, "big")


def time_signature_event() -> bytes:
    return bytes([0xFF, 0x58, 0x04, 0x04, 0x02, 0x18, 0x08])


def program_change(channel: int, program: int) -> bytes:
    return bytes([0xC0 | channel, program])


def controller(channel: int, cc: int, value: int) -> bytes:
    return bytes([0xB0 | channel, cc, max(0, min(127, value))])


def note_on(channel: int, note: int, velocity: int) -> bytes:
    return bytes([0x90 | channel, max(0, min(127, note)), max(1, min(127, velocity))])


def note_off(channel: int, note: int) -> bytes:
    return bytes([0x80 | channel, max(0, min(127, note)), 0])


def add_note(events: list[MidiEvent], tick: int, length: int, channel: int, note: int, velocity: int) -> None:
    if length <= 0:
        return
    events.append(MidiEvent(tick, 2, note_on(channel, note, velocity)))
    events.append(MidiEvent(tick + length, 1, note_off(channel, note)))


def build_scenes(track: dict[str, Any]) -> list[dict[str, Any]]:
    tempo = int(track["tempo_bpm"])
    total_seconds = parse_duration_seconds(track["duration_target"])
    raw_bars = total_seconds / ((60 / tempo) * 4)
    arrangement = track.get("arrangement", [])
    section_count = max(1, len(arrangement))
    bars_per_section = max(4, int(math.ceil(raw_bars / section_count / 4)) * 4)

    scenes = []
    for index, description in enumerate(arrangement):
        scenes.append(
            {
                "index": index + 1,
                "name": f"{index + 1:02d} {description}",
                "bar_start": index * bars_per_section + 1,
                "bar_length": bars_per_section,
                "arrangement_note": description,
            }
        )
    return scenes


def note_context(track: dict[str, Any]) -> tuple[int, list[int]]:
    root_name = normalize_root(track["key_center"])
    root = ROOT_TO_MIDI.get(root_name, 48)
    return root, scale_for_key(track["key_center"])


def render_banjo(events: list[MidiEvent], root: int, scale: list[int], bars: int, density_shift: int = 0) -> None:
    pattern = [0, 2, 4, 2, 5, 4, 2, 0]
    step = PPQ // 2
    for bar in range(bars):
        for i, degree_index in enumerate(pattern):
            tick = bar * BAR_TICKS + i * step
            note = degree(root + 24, scale, degree_index + density_shift)
            velocity = 78 + ((bar + i) % 4) * 5
            add_note(events, tick, int(step * 0.72), 0, note, velocity)


def render_fiddle(events: list[MidiEvent], root: int, scale: list[int], bars: int) -> None:
    for bar in range(0, bars, 2):
        tick = bar * BAR_TICKS
        add_note(events, tick, BAR_TICKS * 2 - PPQ // 2, 1, degree(root + 24, scale, 0), 62)
        add_note(events, tick + PPQ, BAR_TICKS * 2 - PPQ, 1, degree(root + 24, scale, 4), 54)


def render_mandolin(events: list[MidiEvent], root: int, scale: list[int], bars: int) -> None:
    chord = [degree(root + 24, scale, 0), degree(root + 24, scale, 2), degree(root + 24, scale, 4)]
    for bar in range(bars):
        for beat in [1, 3]:
            tick = bar * BAR_TICKS + beat * PPQ
            for note in chord:
                add_note(events, tick, PPQ // 5, 2, note, 72)


def render_dobro(events: list[MidiEvent], root: int, scale: list[int], bars: int) -> None:
    for bar in range(0, bars, 4):
        target = degree(root + 24, scale, (bar // 4) % 5)
        tick = bar * BAR_TICKS + PPQ * 2
        add_note(events, tick, PPQ, 3, target - 2, 50)
        add_note(events, tick + PPQ, PPQ * 2, 3, target, 66)


def render_bass(events: list[MidiEvent], root: int, scale: list[int], bars: int) -> None:
    for bar in range(bars):
        notes = [degree(root - 12, scale, 0), degree(root - 12, scale, 4)]
        for beat, note in zip([0, 2], notes, strict=True):
            add_note(events, bar * BAR_TICKS + beat * PPQ, PPQ + PPQ // 2, 4, note, 86)
        add_note(events, bar * BAR_TICKS + 3 * PPQ, PPQ // 2, 4, degree(root - 12, scale, 5), 60)


def render_acoustic_guitar(events: list[MidiEvent], root: int, scale: list[int], bars: int) -> None:
    chord = [degree(root + 12, scale, 0), degree(root + 12, scale, 2), degree(root + 12, scale, 4)]
    bass_notes = [degree(root, scale, 0), degree(root, scale, 4)]
    for bar in range(bars):
        base = bar * BAR_TICKS
        for beat, note in zip([0, 2], bass_notes, strict=True):
            add_note(events, base + beat * PPQ, PPQ // 2, 5, note, 68)
        for beat in [1, 3]:
            tick = base + beat * PPQ
            for note in chord:
                add_note(events, tick, PPQ // 4, 5, note, 76)


def render_punk_kit(events: list[MidiEvent], bars: int) -> None:
    kick, snare, hat, crash = 36, 38, 42, 49
    for bar in range(bars):
        base = bar * BAR_TICKS
        for beat in [0, 2]:
            add_note(events, base + beat * PPQ, PPQ // 6, 9, kick, 100)
        for beat in [1, 3]:
            add_note(events, base + beat * PPQ, PPQ // 6, 9, snare, 112)
        for eighth in range(8):
            add_note(events, base + eighth * (PPQ // 2), PPQ // 8, 9, hat, 62 + (eighth % 2) * 12)
        if bar % 8 == 7:
            for offset in [PPQ * 3, PPQ * 3 + PPQ // 2, PPQ * 3 + PPQ * 3 // 4]:
                add_note(events, base + offset, PPQ // 8, 9, snare, 96)
            add_note(events, base, PPQ // 4, 9, crash, 84)


def render_house(events: list[MidiEvent], root: int, scale: list[int], bars: int) -> None:
    kick, clap, open_hat = 36, 39, 46
    stab_channel = 10
    chord = [degree(root + 12, scale, 0), degree(root + 12, scale, 2), degree(root + 12, scale, 4)]
    events.append(MidiEvent(0, 0, program_change(stab_channel, 88)))
    events.append(MidiEvent(0, 0, controller(stab_channel, 10, 38)))
    for bar in range(bars):
        base = bar * BAR_TICKS
        for beat in range(4):
            add_note(events, base + beat * PPQ, PPQ // 6, 9, kick, 92)
        for beat in [1, 3]:
            add_note(events, base + beat * PPQ, PPQ // 6, 9, clap, 78)
        for offbeat in [PPQ // 2, PPQ + PPQ // 2, PPQ * 2 + PPQ // 2, PPQ * 3 + PPQ // 2]:
            add_note(events, base + offbeat, PPQ // 7, 9, open_hat, 58)
        if bar % 2 == 0:
            for note in chord:
                add_note(events, base + PPQ, PPQ // 2, stab_channel, note, 64)


def render_alien_sky(events: list[MidiEvent], root: int, scale: list[int], bars: int) -> None:
    for bar in range(0, bars, 4):
        tick = bar * BAR_TICKS
        add_note(events, tick, BAR_TICKS * 4 - PPQ, 11, degree(root + 36, scale, 0), 42)
        add_note(events, tick + PPQ, BAR_TICKS * 4 - PPQ * 2, 11, degree(root + 36, scale, 4), 36)


RENDERERS = {
    "aeroband_banjo_lead": render_banjo,
    "fiddle_hybrid_strings": render_fiddle,
    "mandolin_chop": render_mandolin,
    "dobro_metallic_slide": render_dobro,
    "upright_bass_sub": render_bass,
    "acoustic_guitar_boom_chuck": render_acoustic_guitar,
    "punk_kit": render_punk_kit,
    "deep_house_machines": render_house,
    "alien_sky": render_alien_sky,
}


def encode_track(events: list[MidiEvent], end_tick: int) -> bytes:
    events = sorted(events, key=lambda item: (item.tick, item.priority, item.data))
    output = bytearray()
    previous_tick = 0
    for event in events:
        output.extend(varlen(event.tick - previous_tick))
        output.extend(event.data)
        previous_tick = event.tick
    output.extend(varlen(max(0, end_tick - previous_tick)))
    output.extend(b"\xFF\x2F\x00")
    return b"MTrk" + struct.pack(">I", len(output)) + bytes(output)


def render_midi(track: dict[str, Any], scenes: list[dict[str, Any]], output_path: Path) -> None:
    bars = sum(scene["bar_length"] for scene in scenes)
    end_tick = bars * BAR_TICKS
    root, scale = note_context(track)
    midi_tracks: list[bytes] = []

    conductor = [
        MidiEvent(0, 0, track_name("Conductor")),
        MidiEvent(0, 0, tempo_event(int(track["tempo_bpm"]))),
        MidiEvent(0, 0, time_signature_event()),
    ]
    for scene in scenes:
        conductor.append(MidiEvent((scene["bar_start"] - 1) * BAR_TICKS, 0, marker(scene["name"])))
    midi_tracks.append(encode_track(conductor, end_tick))

    for layer in LAYER_DEFINITIONS:
        events = [
            MidiEvent(0, 0, track_name(layer["midi_track"])),
            MidiEvent(0, 0, controller(int(layer["channel"]), 10, 64)),
        ]
        if layer["program"] is not None:
            events.append(MidiEvent(0, 0, program_change(int(layer["channel"]), int(layer["program"]))))

        renderer = RENDERERS[layer["id"]]
        if layer["id"] in {"punk_kit"}:
            renderer(events, bars)
        else:
            renderer(events, root, scale, bars)
        midi_tracks.append(encode_track(events, end_tick))

    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(midi_tracks), PPQ)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(header + b"".join(midi_tracks))


def build_plan_entry(track: dict[str, Any], session_template: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    slug = slugify(track["title"])
    scenes = build_scenes(track)
    midi_rel = Path("midi") / f"{slug}.mid"
    midi_path = output_dir / midi_rel
    render_midi(track, scenes, midi_path)

    session_tracks = {item["name"]: item for item in session_template.get("tracks", [])}
    layers = []
    for layer in LAYER_DEFINITIONS:
        session_track = session_tracks.get(layer["session_track"], {})
        layers.append(
            {
                "id": layer["id"],
                "session_track": layer["session_track"],
                "midi_track": layer["midi_track"],
                "midi_channels": [10, 11] if layer["id"] == "deep_house_machines" else [layer["channel"] + 1],
                "gm_sound": layer["gm_sound"],
                "motif": layer["motif"],
                "traditional_bluegrass_layer": layer["traditional"],
                "alien_electronic_layer": layer["electronic"],
                "device_contracts": session_track.get("device_contracts", []),
                "automation_targets": session_track.get("automation_targets", []),
            }
        )

    return {
        "title": track["title"],
        "slug": slug,
        "tempo_bpm": track["tempo_bpm"],
        "key_center": track["key_center"],
        "duration_target": track["duration_target"],
        "approximate_bars": sum(scene["bar_length"] for scene in scenes),
        "midi_file": str(Path("compositions/generated") / midi_rel),
        "midi_sha256": sha256_file(midi_path),
        "midi_byte_size": midi_path.stat().st_size,
        "scenes": scenes,
        "layers": layers,
        "max_for_live_focus": track.get("max_for_live_focus", []),
        "bluegrass_core": track.get("bluegrass_core", []),
        "electronic_dna": track.get("electronic_dna", []),
        "punk_spirit": track.get("punk_spirit", []),
        "production_constraints": [
            "Import MIDI into Ableton Live 12, then map each MIDI track to the matching session-template track.",
            "Keep Public Domain Source Deck muted until the source ledger approves the selected audio.",
            "Do not commit rendered audio, .als, .amxd, commercial packs, samples, presets, or controller recordings.",
            "Before Live-set mutation, save a local rollback copy and record the affected tracks/devices.",
        ],
    }


def render(output_dir: Path = DEFAULT_OUTPUT_DIR, stable: bool = False) -> dict[str, Any]:
    composition = read_json("compositions/down-tempo-punk-bluegrass-set.json")
    session_template = read_json("automation/live12-session-template.json")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "midi").mkdir(parents=True, exist_ok=True)

    plans = [build_plan_entry(track, session_template, output_dir) for track in composition.get("tracks", [])]
    return {
        "schema_version": 1,
        "generated_at": STABLE_GENERATED_AT if stable else utc_now(),
        "generator": "scripts/render_composition_sketches.py",
        "source_files": SOURCE_FILES,
        "source_file_sha256": {relative_path: sha256_file(ROOT / relative_path) for relative_path in SOURCE_FILES},
        "purpose": "Deterministic MIDI and Live-build plans for standalone downtempo punk-bluegrass tracks.",
        "ableton_import_notes": [
            "Create or open a Live 12 session from automation/live12-session-template.json.",
            "Drag each .mid file into Live and route generated MIDI tracks to matching session tracks.",
            "Replace GM placeholder sounds with the documented Ableton/Arturia instruments only after license verification.",
            "Use Max for Live device contracts in each plan as the automation target list.",
        ],
        "tracks": plans,
    }


def write_readme(output_dir: Path) -> None:
    lines = [
        "# Generated Composition Sketches",
        "",
        "This directory contains deterministic composition artifacts rendered from:",
        "",
        "- `compositions/down-tempo-punk-bluegrass-set.json`",
        "- `automation/live12-session-template.json`",
        "",
        "The `.mid` files are generated note/control sketches for Ableton Live import. They do not contain sampled audio, Ableton Live Sets, Max for Live devices, Arturia presets, commercial pack content, private recordings, credentials, cookies, or license files.",
        "",
        "Regenerate and verify with:",
        "",
        "```bash",
        "python3 scripts/render_composition_sketches.py --stable",
        "python3 scripts/validate_repo.py",
        "```",
        "",
    ]
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def write_manifest(manifest: dict[str, Any], output_dir: Path) -> None:
    output_path = output_dir / "live12-track-build-plans.json"
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    write_readme(output_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for JSON and MIDI outputs.")
    parser.add_argument("--stable", action="store_true", help="Use a fixed timestamp for committed/CI output.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    manifest = render(output_dir=output_dir, stable=args.stable)
    write_manifest(manifest, output_dir)
    print(json.dumps({"tracks": len(manifest["tracks"]), "output_dir": str(output_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
