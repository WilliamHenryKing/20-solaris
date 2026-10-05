# Mechanical detector — 3 October 2026

One manual scan ran after the refined UI and world gallery were implemented. Context had reported no active automatic hook in this session. The exact output is retained in `impeccable-detect.json`; the detector was not repeatedly rerun.

Two warnings identified `font-family: Arial` on `.sun-mark` and `.studio-sun`. Those obsolete declarations were inherited from the removed Unicode sun glyph. Both are deleted; the marks are authored SVG geometry and the website retains its self-hosted Manrope typography. No rule was disabled.

## Second pass — 4 October 2026

The journey ownership, layout and type-floor corrections justified one more manual scan. Impeccable `context` reported `SCOPED_EXISTING_ALLOWED`; `impeccable detect --json src` returned no findings. `impeccable-detect.json` now holds this output.

The scan is mechanical evidence only. It does not certify visual quality, responsive behavior, keyboard access or acceptance; those need the separate browser receipts.

## Third pass — 5 October 2026

The release review changed `src/main.tsx`, `src/Pavilion.tsx` and `src/style.css`. One more manual scan of the released source returned no findings; `impeccable-detect.json` now holds this output.
