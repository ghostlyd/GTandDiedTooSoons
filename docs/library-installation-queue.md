# Library Installation Queue

Generated operator handoff for approval-gated Ableton and Arturia library/account actions.

- Execution status: `planned_not_executed`
- No vendor login, purchase, install, DAW launch, or OpenAI API call is performed by this renderer or CI check.
- Do not commit vendor credentials, session cookies, license files, installer packages, commercial pack content, presets, samples, or renders.
- Local receipt root: `output/library-installation` (`ignored_local_only`).
- Inventory refresh: `python3 scripts/inventory_live_suite.py --output inventory/live12-local-inventory.json`

## Inventory Summary

- Ableton Live: `Ableton Live 12 Suite.app` version `12.4.2 (2026-06-04_a687113d71)`; factory packs `9`; available-not-present candidates `34`.
- Arturia: applications `56`; Software Center present `True`; resource products `94`.
- Plugin roots: VST3 `2`; Audio Unit `2`.

## Queue Policy

- Blocked approval gates: `vendor_account_action, purchase_or_license_change`
- Git policy: `metadata_only_no_commercial_assets`
- CI vendor actions allowed: `False`

## Vendor Routes

### Ableton

- Allowed hosts: `www.ableton.com`
- Route: Ableton Live Browser > Packs, or authenticated Ableton account page for already licensed content.
- Boundary: Use official Ableton UI/account surfaces only after approval; record redacted receipts and refresh inventory.

### Arturia

- Allowed hosts: `www.arturia.com`
- Route: Arturia Software Center, Arturia product page, or authenticated Arturia account page.
- Boundary: Use official Arturia UI/account surfaces only after approval; record redacted receipts and refresh inventory.

## Queue Items

### 1. Drum Booth

- Catalog id: `ableton-drum-booth`
- Vendor: `Ableton`
- Priority/status: `high` / `live_database_available_not_installed`
- Action class: `available_in_live_database_pending_operator_action`
- Approval gates: `vendor_account_action`
- Official URL: https://www.ableton.com/en/packs/drum-booth/
- Route: Ableton Live Browser > Packs, or Ableton account if licensed.
- Local signal: Present in Live database pack index; absent from installed Factory Packs places.
- Project use: Dry room acoustic drums for punk kit attack and reinforcement under electronic drums.
- Operator next step: Check the Live Browser database entry, then act through the official Ableton surface after approval.
- Receipt template: `output/library-installation/ableton-drum-booth/receipt.json`

### 2. Drum Essentials

- Catalog id: `ableton-drum-essentials`
- Vendor: `Ableton`
- Priority/status: `high` / `live_database_available_not_installed`
- Action class: `available_in_live_database_pending_operator_action`
- Approval gates: `vendor_account_action`
- Official URL: https://www.ableton.com/en/packs/drum-essentials/
- Route: Ableton Live Browser > Packs; official page lists Live 12 compatibility.
- Local signal: Present in Live database pack index; absent from installed Factory Packs places.
- Project use: Core drum racks, MIDI clips, and one-shots for fast beat sketching and kit layering.
- Operator next step: Check the Live Browser database entry, then act through the official Ableton surface after approval.
- Receipt template: `output/library-installation/ableton-drum-essentials/receipt.json`

### 3. String Quartet by Spitfire Audio

- Catalog id: `ableton-string-quartet`
- Vendor: `Ableton`
- Priority/status: `high` / `live_database_available_not_installed`
- Action class: `available_in_live_database_pending_operator_action`
- Approval gates: `vendor_account_action`
- Official URL: https://www.ableton.com/en/packs/string-quartet/
- Route: Ableton Live Browser > Packs, or Ableton account if licensed.
- Local signal: Present in Live database pack index; absent from installed Factory Packs places.
- Project use: Bowed, pizzicato, and tremolo string gestures for fiddle-family arrangements.
- Operator next step: Check the Live Browser database entry, then act through the official Ableton surface after approval.
- Receipt template: `output/library-installation/ableton-string-quartet/receipt.json`

### 4. Sequencers

- Catalog id: `ableton-sequencers`
- Vendor: `Ableton`
- Priority/status: `high` / `live_database_available_not_installed`
- Action class: `available_in_live_database_pending_operator_action`
- Approval gates: `vendor_account_action`
- Official URL: https://www.ableton.com/en/packs/sequencers/
- Route: Ableton Live Browser > Packs; requires compatible Max for Live license.
- Local signal: Present in Live database pack index; absent from installed Factory Packs places.
- Project use: Generative MIDI sequencing for banjo rolls, house stabs, and worker-agent arrangement sketches.
- Operator next step: Check the Live Browser database entry, then act through the official Ableton surface after approval.
- Receipt template: `output/library-installation/ableton-sequencers/receipt.json`

### 5. Chop and Swing

- Catalog id: `ableton-chop-and-swing`
- Vendor: `Ableton`
- Priority/status: `high` / `live_database_available_not_installed`
- Action class: `available_in_live_database_pending_operator_action`
- Approval gates: `vendor_account_action`
- Official URL: https://www.ableton.com/en/packs/chop-and-swing/
- Route: Ableton Live Browser > Packs.
- Local signal: Present in Live database pack index; absent from installed Factory Packs places.
- Project use: Sampling-first grooves and chops for transforming public-domain fiddle/banjo fragments.
- Operator next step: Check the Live Browser database entry, then act through the official Ableton surface after approval.
- Receipt template: `output/library-installation/ableton-chop-and-swing/receipt.json`

### 6. Drive and Glow

- Catalog id: `ableton-drive-and-glow`
- Vendor: `Ableton`
- Priority/status: `high` / `live_database_available_not_installed`
- Action class: `available_in_live_database_pending_operator_action`
- Approval gates: `vendor_account_action`
- Official URL: https://www.ableton.com/en/packs/drive-and-glow/
- Route: Purchase/install through Ableton account or Live Browser if entitled.
- Local signal: Present in Live database pack index; absent from installed Factory Packs places.
- Project use: Saturated indie guitars, basses, drums, and synth textures for punk/electronic crossover.
- Operator next step: Check the Live Browser database entry, then act through the official Ableton surface after approval.
- Receipt template: `output/library-installation/ableton-drive-and-glow/receipt.json`

### 7. Electric Keyboards

- Catalog id: `ableton-electric-keyboards`
- Vendor: `Ableton`
- Priority/status: `medium` / `live_database_available_not_installed`
- Action class: `available_in_live_database_pending_operator_action`
- Approval gates: `vendor_account_action`
- Official URL: https://www.ableton.com/en/packs/electric-keyboards/
- Route: Ableton Live Browser > Packs.
- Local signal: Present in Live database pack index; absent from installed Factory Packs places.
- Project use: Organic EP/organ layers for deep-house harmonic anchors.
- Operator next step: Check the Live Browser database entry, then act through the official Ableton surface after approval.
- Receipt template: `output/library-installation/ableton-electric-keyboards/receipt.json`

### 8. Generators by Iftah

- Catalog id: `ableton-generators-by-iftah`
- Vendor: `Ableton`
- Priority/status: `medium` / `live_database_available_not_installed`
- Action class: `available_in_live_database_pending_operator_action`
- Approval gates: `vendor_account_action`
- Official URL: https://www.ableton.com/en/packs/generators-by-iftah/
- Route: Ableton Live Browser > Packs; requires compatible Live/Max for Live license.
- Local signal: Present in Live database pack index; absent from installed Factory Packs places.
- Project use: Pattern and phrase generation for controlled swarm-composition experiments.
- Operator next step: Check the Live Browser database entry, then act through the official Ableton surface after approval.
- Receipt template: `output/library-installation/ableton-generators-by-iftah/receipt.json`

### 9. Performance Pack by Iftah

- Catalog id: `ableton-performance-pack-by-iftah`
- Vendor: `Ableton`
- Priority/status: `medium` / `live_database_available_not_installed`
- Action class: `available_in_live_database_pending_operator_action`
- Approval gates: `vendor_account_action`
- Official URL: https://www.ableton.com/en/packs/performance-pack/
- Route: Ableton Live Browser > Packs; requires compatible Live/Max for Live license.
- Local signal: Present in Live database pack index; absent from installed Factory Packs places.
- Project use: Live set control, macros, and performance operations for DJ/lead-controller execution.
- Operator next step: Check the Live Browser database entry, then act through the official Ableton surface after approval.
- Receipt template: `output/library-installation/ableton-performance-pack-by-iftah/receipt.json`

### 10. DM-307A Free Pack

- Catalog id: `ableton-dm-307a-free-pack`
- Vendor: `Ableton`
- Priority/status: `medium` / `account_login_required`
- Action class: `account_entitlement_review_required`
- Approval gates: `vendor_account_action`
- Official URL: https://www.ableton.com/en/packs/dm-307a-free-pack/
- Route: Log in to Ableton, download official .alp if entitled, open with Ableton Live, then delete installer.
- Local signal: Not present in Live database pack index; official page marks it discontinued but downloadable.
- Project use: Industrial, house, techno, and organic percussion for alien drum layers.
- Operator next step: Confirm account entitlement through the official vendor surface after approval.
- Receipt template: `output/library-installation/ableton-dm-307a-free-pack/receipt.json`

### 11. Spectral Textures

- Catalog id: `ableton-spectral-textures`
- Vendor: `Ableton`
- Priority/status: `high` / `account_login_required`
- Action class: `account_entitlement_review_required`
- Approval gates: `vendor_account_action`
- Official URL: https://www.ableton.com/en/packs/spectral-textures/
- Route: Log in to Ableton, download/install from the official pack page or account if entitled.
- Local signal: Not present in installed Factory Packs places or current Live database pack candidates.
- Project use: Field-recording and additive-synthesis atmospheres for alien transitions.
- Operator next step: Confirm account entitlement through the official vendor surface after approval.
- Receipt template: `output/library-installation/ableton-spectral-textures/receipt.json`

### 12. Electronica Selection

- Catalog id: `arturia-electronica-selection`
- Vendor: `Arturia`
- Priority/status: `high` / `account_or_purchase_required`
- Action class: `entitlement_or_purchase_review_required`
- Approval gates: `vendor_account_action, purchase_or_license_change`
- Official URL: https://www.arturia.com/store/presets-sound-banks/electronica-selection
- Route: Acquire through Arturia Sound Store, then synchronize/install in Analog Lab, Pigments, or Arturia Software Center.
- Local signal: Arturia Software Center and Analog Lab V are installed; this specific bank is not verified as owned.
- Project use: Organic motion, granular detail, cinematic layers, and abstract analog tones.
- Operator next step: Confirm entitlement first; any purchase or license change needs separate approval evidence.
- Receipt template: `output/library-installation/arturia-electronica-selection/receipt.json`

### 13. Dancefloor Selection

- Catalog id: `arturia-dancefloor-selection`
- Vendor: `Arturia`
- Priority/status: `high` / `account_or_purchase_required`
- Action class: `entitlement_or_purchase_review_required`
- Approval gates: `vendor_account_action, purchase_or_license_change`
- Official URL: https://www.arturia.com/store/presets-sound-banks/dancefloor-selection
- Route: Acquire through Arturia Sound Store, then synchronize/install in Analog Lab, Pigments, or Arturia Software Center.
- Local signal: Arturia Software Center and Analog Lab V are installed; this specific bank is not verified as owned.
- Project use: House grooves, euphoric builds, and UKG-adjacent club motion for the deep-house layer.
- Operator next step: Confirm entitlement first; any purchase or license change needs separate approval evidence.
- Receipt template: `output/library-installation/arturia-dancefloor-selection/receipt.json`

### 14. House Explorations

- Catalog id: `arturia-house-explorations`
- Vendor: `Arturia`
- Priority/status: `high` / `account_or_purchase_required`
- Action class: `entitlement_or_purchase_review_required`
- Approval gates: `vendor_account_action, purchase_or_license_change`
- Official URL: https://www.arturia.com/store/presets-sound-banks/house_explorations
- Route: Acquire through Arturia Sound Store, then synchronize/install in Analog Lab, Pigments, or Arturia Software Center.
- Local signal: Arturia Software Center and Analog Lab V are installed; this specific bank is not verified as owned.
- Project use: Deep-house sub bass, chord stabs, EP keys, pads, and leads.
- Operator next step: Confirm entitlement first; any purchase or license change needs separate approval evidence.
- Receipt template: `output/library-installation/arturia-house-explorations/receipt.json`

### 15. Guitar Deconstructed

- Catalog id: `arturia-guitar-deconstructed`
- Vendor: `Arturia`
- Priority/status: `high` / `account_or_purchase_required`
- Action class: `entitlement_or_purchase_review_required`
- Approval gates: `vendor_account_action, purchase_or_license_change`
- Official URL: https://www.arturia.com/store/presets-sound-banks/rock-music/guitar_deconstructed
- Route: Acquire through Arturia Sound Store, then synchronize/install in Analog Lab, Pigments, or Arturia Software Center.
- Local signal: Arturia Software Center and Analog Lab V are installed; this specific bank is not verified as owned.
- Project use: Granular guitar-source presets that bridge punk strum energy and abstract ambience.
- Operator next step: Confirm entitlement first; any purchase or license change needs separate approval evidence.
- Receipt template: `output/library-installation/arturia-guitar-deconstructed/receipt.json`

### 16. Post-Rock Guitars

- Catalog id: `arturia-post-rock-guitars`
- Vendor: `Arturia`
- Priority/status: `medium` / `account_or_purchase_required`
- Action class: `entitlement_or_purchase_review_required`
- Approval gates: `vendor_account_action, purchase_or_license_change`
- Official URL: https://www.arturia.com/store/presets-sound-banks/post_rock_guitars
- Route: Acquire through Arturia Sound Store, then synchronize/install in Analog Lab, Pigments, or Arturia Software Center.
- Local signal: Arturia Software Center and Analog Lab V are installed; this specific bank is not verified as owned.
- Project use: Guitar drones, swells, and cinematic expression for punk/ambient crossover.
- Operator next step: Confirm entitlement first; any purchase or license change needs separate approval evidence.
- Receipt template: `output/library-installation/arturia-post-rock-guitars/receipt.json`

### 17. Folkloric Strings

- Catalog id: `arturia-folkloric-strings`
- Vendor: `Arturia`
- Priority/status: `medium` / `account_or_purchase_required`
- Action class: `entitlement_or_purchase_review_required`
- Approval gates: `vendor_account_action, purchase_or_license_change`
- Official URL: https://www.arturia.com/store/presets-sound-banks/cinematic-fx/folkloric_strings
- Route: Acquire through Arturia Sound Store, then synchronize/install in Analog Lab, Pigments, or Arturia Software Center.
- Local signal: Arturia Software Center and Analog Lab V are installed; this specific bank is not verified as owned.
- Project use: Old-world drones, bowed color, and roots-adjacent string atmosphere.
- Operator next step: Confirm entitlement first; any purchase or license change needs separate approval evidence.
- Receipt template: `output/library-installation/arturia-folkloric-strings/receipt.json`

### 18. Cities In Dust

- Catalog id: `arturia-cities-in-dust`
- Vendor: `Arturia`
- Priority/status: `medium` / `account_or_purchase_required`
- Action class: `entitlement_or_purchase_review_required`
- Approval gates: `vendor_account_action, purchase_or_license_change`
- Official URL: https://www.arturia.com/store/presets-sound-banks/cities_in_dust
- Route: Acquire through Arturia Sound Store, then synchronize/install in Analog Lab, Pigments, or Arturia Software Center.
- Local signal: Arturia Software Center and Analog Lab V are installed; this specific bank is not verified as owned.
- Project use: Ambient, IDM, crystalline, and granular alien-electronica palette.
- Operator next step: Confirm entitlement first; any purchase or license change needs separate approval evidence.
- Receipt template: `output/library-installation/arturia-cities-in-dust/receipt.json`

### 19. Industrial Force

- Catalog id: `arturia-industrial-force`
- Vendor: `Arturia`
- Priority/status: `medium` / `account_or_purchase_required`
- Action class: `entitlement_or_purchase_review_required`
- Approval gates: `vendor_account_action, purchase_or_license_change`
- Official URL: https://www.arturia.com/store/presets-sound-banks/industrial_force
- Route: Acquire through Arturia Sound Store, then synchronize/install in Analog Lab, Pigments, or Arturia Software Center.
- Local signal: Arturia Software Center and Analog Lab V are installed; this specific bank is not verified as owned.
- Project use: Aggressive underground synth and percussion energy for punk-electronica impact.
- Operator next step: Confirm entitlement first; any purchase or license change needs separate approval evidence.
- Receipt template: `output/library-installation/arturia-industrial-force/receipt.json`

### 20. IDM Grooves

- Catalog id: `arturia-idm-grooves`
- Vendor: `Arturia`
- Priority/status: `medium` / `account_or_purchase_required`
- Action class: `entitlement_or_purchase_review_required`
- Approval gates: `vendor_account_action, purchase_or_license_change`
- Official URL: https://www.arturia.com/store/presets-sound-banks/idm_grooves
- Route: Acquire through Arturia Sound Store, then synchronize/install in Analog Lab, Pigments, or Arturia Software Center.
- Local signal: Arturia Software Center and Analog Lab V are installed; this specific bank is not verified as owned.
- Project use: Cerebral drum mechanics and fractured movement for alien-electronica transitions.
- Operator next step: Confirm entitlement first; any purchase or license change needs separate approval evidence.
- Receipt template: `output/library-installation/arturia-idm-grooves/receipt.json`

## Post-Action Checks

1. `python3 scripts/inventory_live_suite.py --output inventory/live12-local-inventory.json`
2. `python3 scripts/validate_repo.py`
3. `python3 scripts/test_library_installation_queue.py`

