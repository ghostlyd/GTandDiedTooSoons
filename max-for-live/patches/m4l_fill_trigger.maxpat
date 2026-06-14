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
          "text": "Fill Trigger"
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
          "text": "Trigger punk drum fills at section boundaries with bounded probability and parallel-crush coordination."
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
          "text": "Contract id: m4l.fill_trigger"
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
          "text": "Device class: midi_effect"
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
          "text": "Target tracks: Punk Kit"
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
          "varname": "fill_probability"
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
          "text": "Macro: fill_probability"
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
          "varname": "parallel_drive"
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
          "text": "Macro: parallel_drive"
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
          "varname": "room_send"
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
          "text": "Macro: room_send"
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
