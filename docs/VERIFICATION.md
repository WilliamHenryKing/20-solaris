# Verification — 3 October 2026

A sun-led architecture studio with an interactive daylight pavilion.

Production typecheck, Biome and Vite build passed. Chrome 154.0.8037.97 on Windows exercised 70 checks; all passed, no browser/network errors, and zero detected axe A/AA violations in the recorded states. The final report is [verification.json](verification.json). Additional operating-system motion, no-WebGL and scene/form edge cases are in [edge-report.json](edge-report.json).

Desktop 1440 × 900, tablet 768 × 1024, phone 390 × 844, narrow phone 320 × 740 and landscape 844 × 390 were captured. Full route/gallery/detail/studio/brief journeys ran at desktop and phone widths. Images loaded, headings and titles changed, filters worked, phone menus closed correctly, and downloaded brief text matched input selections. Root inspected screenshots and revised visible defects; this is visual self-review, not user/client acceptance.

The Three.js runtime is project-local, capped in resolution and stops when hidden/offscreen or idle. Recorded draw calls and triangles appear in the JSON diagnostics. These are scene counts, not a frame-rate certificate or physical mobile-device benchmark. The build emits a size advisory for the Three.js chunk; AUREL and SOLARIS split Three into separate chunks; SOLARIS waits until its pavilion approaches the viewport, while AUREL mounts its below-fold pavilion with the homepage and STRATA uses Three for its interactive hero. No model or font requests leave the deployed origin.

Reproduce with `bun run check`, `bun run preview`, then `bun run verify:browser` in another terminal. Google Chrome is required by the browser runner. `node tools/verify-release.mjs <live-url>` compares every deployable output hash and exercises live desktop/phone views. Production release identity is recorded separately in RELEASE.md.

The sites are fictional demonstrations. Forms create local text files; no email service, CMS/admin account, analytics or client engagement is implied. Hash routes are client-side; the static host returns 404 for unknown document paths. Hosting and public source publication were explicitly authorized by William.
