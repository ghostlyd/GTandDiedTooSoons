{
  "patcher": {
    "appversion": {
      "architecture": "x64",
      "major": 8,
      "minor": 6,
      "modernui": 1,
      "revision": 0
    },
    "bglocked": 0,
    "boxes": [
      {
        "box": {
          "id": "obj-1",
          "maxclass": "comment",
          "patching_rect": [
            30.0,
            25.0,
            720.0,
            22.0
          ],
          "text": "Provenance Sampler"
        }
      },
      {
        "box": {
          "id": "obj-2",
          "maxclass": "comment",
          "patching_rect": [
            30.0,
            55.0,
            720.0,
            22.0
          ],
          "text": "Gate and document public-domain source deck usage without storing raw source audio or rights-uncertain material in the patch."
        }
      },
      {
        "box": {
          "id": "obj-3",
          "maxclass": "comment",
          "patching_rect": [
            30.0,
            90.0,
            720.0,
            22.0
          ],
          "text": "Contract id: m4l.provenance_sampler"
        }
      },
      {
        "box": {
          "id": "obj-4",
          "maxclass": "comment",
          "patching_rect": [
            30.0,
            120.0,
            720.0,
            22.0
          ],
          "text": "Device class: audio_effect"
        }
      },
      {
        "box": {
          "id": "obj-5",
          "maxclass": "comment",
          "patching_rect": [
            30.0,
            150.0,
            720.0,
            22.0
          ],
          "text": "Target tracks: Public Domain Source Deck"
        }
      },
      {
        "box": {
          "id": "obj-6",
          "maxclass": "newobj",
          "patching_rect": [
            30.0,
            195.0,
            90.0,
            22.0
          ],
          "text": "inlet"
        }
      },
      {
        "box": {
          "id": "obj-7",
          "maxclass": "newobj",
          "patching_rect": [
            150.0,
            195.0,
            90.0,
            22.0
          ],
          "text": "outlet"
        }
      },
      {
        "box": {
          "id": "obj-8",
          "maxclass": "live.dial",
          "parameter_enable": 1,
          "patching_rect": [
            30.0,
            240.0,
            180.0,
            48.0
          ],
          "presentation": 1,
          "presentation_rect": [
            30.0,
            240.0,
            180.0,
            48.0
          ],
          "varname": "source_gate"
        }
      },
      {
        "box": {
          "id": "obj-8-comment",
          "maxclass": "comment",
          "patching_rect": [
            230.0,
            240.0,
            360.0,
            22.0
          ],
          "text": "Macro: source_gate"
        }
      },
      {
        "box": {
          "id": "obj-9",
          "maxclass": "live.dial",
          "parameter_enable": 1,
          "patching_rect": [
            30.0,
            280.0,
            180.0,
            48.0
          ],
          "presentation": 1,
          "presentation_rect": [
            30.0,
            280.0,
            180.0,
            48.0
          ],
          "varname": "slice_density"
        }
      },
      {
        "box": {
          "id": "obj-9-comment",
          "maxclass": "comment",
          "patching_rect": [
            230.0,
            280.0,
            360.0,
            22.0
          ],
          "text": "Macro: slice_density"
        }
      },
      {
        "box": {
          "id": "obj-10",
          "maxclass": "live.dial",
          "parameter_enable": 1,
          "patching_rect": [
            30.0,
            320.0,
            180.0,
            48.0
          ],
          "presentation": 1,
          "presentation_rect": [
            30.0,
            320.0,
            180.0,
            48.0
          ],
          "varname": "provenance_hold"
        }
      },
      {
        "box": {
          "id": "obj-10-comment",
          "maxclass": "comment",
          "patching_rect": [
            230.0,
            320.0,
            360.0,
            22.0
          ],
          "text": "Macro: provenance_hold"
        }
      },
      {
        "box": {
          "id": "obj-policy",
          "maxclass": "comment",
          "patching_rect": [
            30.0,
            370.0,
            720.0,
            22.0
          ],
          "text": "Source-only patch blueprint. Do not commit compiled .amxd output."
        }
      }
    ],
    "classnamespace": "box",
    "default_fontface": 0,
    "default_fontname": "Arial",
    "default_fontsize": 12.0,
    "fileversion": 1,
    "gridonopen": 1,
    "gridsize": [
      15.0,
      15.0
    ],
    "lines": [],
    "openinpresentation": 1,
    "rect": [
      0.0,
      0.0,
      900.0,
      640.0
    ]
  }
}
