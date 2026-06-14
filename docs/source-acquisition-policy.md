# Source Acquisition Policy

The project needs deep old-time, bluegrass-adjacent source literacy without creating copyright, privacy, or provenance risk.

## Rules

1. Use trusted sources first: Library of Congress, Citizen DJ, Internet Archive items with clear metadata, university archives, and rights-cleared artist-provided material.
2. Treat modern bluegrass recordings as copyrighted by default.
3. For a U.S. workflow on June 14, 2026, treat sound recordings first published before 1926 as the safest public-domain recording pool under the Music Modernization Act schedule, while still checking composition/lyrics rights separately.
4. Treat "no known restrictions" as a research signal, not automatic commercial clearance.
5. Download only entries with explicit source URL, rights status, credit line, and `approved_for_download: true`.
6. Keep downloaded audio outside Git under `sources/public-domain/raw/`.
7. Commit provenance metadata, not raw commercial audio.
8. Do not bypass paywalls, account gates, robots policies, DRM, or terms of service.

## Playwright Use

Playwright may be used to:

- capture catalog metadata for manual review
- save screenshots/traces for reproducibility in `output/playwright/`
- verify page text, links, and rights notices

Playwright must not be used to mass-download copyrighted recordings or defeat site controls.

## Recommended Public-Domain Direction

Bluegrass as a named commercial genre mostly emerges after the earliest public-domain sound recording cutoff. For sampling, the safer source pool is old-time fiddle, banjo, string-band, hymnal, shape-note, cylinder, and early country material that predates or directly informs bluegrass.

Key starting points are versioned in `catalogs/public-domain-bluegrass-sources.json`, including Library of Congress Citizen DJ Folk Music, UCSB Cylinder Audio Archive, Internet Archive Great 78, the Henry Reed Collection, and Library of Congress bluegrass/folklife guides.

Reference for U.S. pre-1972 sound recording terms: https://www.copyright.gov/music-modernization/pre1972-soundrecordings/
