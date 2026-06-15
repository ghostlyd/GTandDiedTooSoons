# Recommended Ableton and Arturia Libraries

This list is license-aware. Install through official vendor apps, accounts, or download pages only. Do not commit vendor content into Git.

## Already Observed Locally

The current host has Ableton Live 12 Suite 12.4.2 and these Ableton Factory Packs visible under `~/Music/Ableton/Factory Packs`:

- Building Max Devices
- Creative Extensions
- Drone Lab
- Glitch and Wash
- Granulator III
- Inspired by Nature by Dillon Bastan
- Mood Reel
- PitchLoop89
- Voice Box

The current host also has a broad Arturia installation under `/Applications/Arturia`, including Pigments, Analog Lab V, multiple Augmented instruments, V Collection instruments, and Arturia Software Center.

The local Live database also indexes 43 Pack candidates. Of those, 34 are not installed as Factory Pack places on this host, including Drum Booth, Drum Essentials, String Quartet by Spitfire Audio, Sequencers, Chop and Swing, Drive and Glow, Electric Keyboards, Generators by Iftah, and Performance Pack by Iftah. The Arturia resource root at `/Library/Arturia` contains 94 product folders, 98 preset product folders, and 24 sample product folders. Refresh the exact local state with:

```bash
python3 scripts/inventory_live_suite.py
```

The install backlog is versioned in `catalogs/library-installation-plan.json`. Generate the operator queue with:

```bash
python3 scripts/render_library_installation_queue.py --stable
```

Use `docs/library-installation-queue.md` for account-gated Ableton/Arturia actions; it performs no vendor login, purchase, install, DAW launch, or OpenAI API call.
Prepare local ignored request/evidence/receipt scaffolds with:

```bash
python3 scripts/prepare_library_installation_queue.py --stable
```

## Priority Additions

| Priority | Library | Why it fits | Official URL |
| --- | --- | --- | --- |
| High | Ableton Drum Booth | Dry acoustic drums for punk attack and human kit reinforcement. | https://www.ableton.com/en/packs/drum-booth/ |
| High | Ableton String Quartet | Bowed and pizzicato strings for fiddle-like lines and chamber tension. | https://www.ableton.com/en/packs/string-quartet/ |
| High | Ableton Sequencers | Max for Live sequencing for probability, movement, and division-of-labor sketches. | https://www.ableton.com/en/packs/sequencers/ |
| High | Ableton Spectral Textures | Free experimental textures for alien atmospheres and transitions. | https://www.ableton.com/en/packs/spectral-textures/ |
| High | Arturia House Explorations | Deep-house basses, chords, keys, and pads. | https://www.arturia.com/store/presets-sound-banks/house_explorations |
| High | Arturia Guitar Deconstructed | Granular guitar-source material for punk-to-electronica mutation. | https://www.arturia.com/store/presets-sound-banks/rock-music/guitar_deconstructed |
| Medium | Ableton Drive and Glow | Indie, overdriven, and electronic crossover palette. | https://www.ableton.com/en/packs/drive-and-glow/ |
| Medium | Ableton House Racks | Classic house machines and synth racks. | https://www.ableton.com/en/packs/house-racks/ |
| Medium | Ableton DM-307A Free Pack | Industrial/techno drums with organic percussion snippets. | https://www.ableton.com/en/packs/dm-307a-free-pack/ |
| Medium | Arturia Folkloric Strings | Drones, string gestures, and roots-adjacent color. | https://www.arturia.com/store/presets-sound-banks/cinematic-fx/folkloric_strings |
| Medium | Arturia Post-Rock Guitars | MPE-ready guitar swells, drones, and distorted pads. | https://www.arturia.com/store/presets-sound-banks/post_rock_guitars |
| Medium | Arturia Cities In Dust | Ambient, IDM, and distant electronic atmospheres. | https://www.arturia.com/store/presets-sound-banks/cities_in_dust |
| Medium | Arturia Industrial Force | Acid, saturated drums, and aggressive synth energy. | https://www.arturia.com/store/presets-sound-banks/industrial_force |
| Low | Ableton Big Band Essentials 2 | Harmonica, ukulele, nylon guitar, bass guitar, drums, and acoustic colors. | https://www.ableton.com/en/packs/big-band-essentials-2/ |
| Low | Ableton Outer Spaces | Max for Live delay/reverb/spectral space design. | https://www.ableton.com/en/packs/outer-spaces/ |

## Install Notes

- Ableton packs: use Live Browser `Packs`, Ableton account pages, or official `.alp` downloads. Even free Ableton downloads can require login. See https://help.ableton.com/hc/en-us/articles/115001930644-Installing-Live-Packs and https://help.ableton.com/hc/en-us/articles/209072029-Ableton-Live-Pack-FAQ.
- Arturia banks: use the official Sound Bank Store, Analog Lab/Pigments in-app store, `My Products`, or Arturia Software Center where applicable. See https://support.arturia.com/hc/en-us/articles/4409624180882-How-to-acquire-and-install-my-sound-banks.
- DAW/account automation may use official authenticated Ableton and Arturia surfaces when the operator has approved the specific action. Stop before credential entry, OS password prompts, purchases, license or entitlement changes, Live-set mutation, exports, or publishing unless there is explicit action-time confirmation.
- After installing through vendor tools, rerun `python3 scripts/inventory_live_suite.py` and commit only the updated inventory and plan status, never `.alp`, `.vst3`, `.component`, samples, presets, installers, browser profiles, cookies, license files, or Arturia/Ableton account artifacts.
