# SOLARIS refinement handover 4 October 2026

Production resumed on 4 October at William's request. The camera, accessibility and layout corrections are committed locally on `work/website` and described in [docs/IMPECCABLE-REFINEMENT.md](docs/IMPECCABLE-REFINEMENT.md); they are not yet published. Both SOLARIS final renders (their scene now has a real olive planting pit and fuller garden planting), packaging, final browser/camera QA and the public release are pending, waiting for the shared GPU. The first release below remains the historical verified delivery. See the collection's [refinement handoff](../../ARCHITECTURE-REFINEMENT-HANDOFF.md) for current state.

# First release — 3 October 2026

**Complete, public and live:** [SOLARIS](https://20-solaris.williamking.workers.dev) · [source](https://github.com/WilliamHenryKing/20-solaris). All 70 local browser checks and 17 live asset hashes passed; desktop and phone live checks were clean. Exact application commit, Cloudflare version, limits and maintenance commands are in [docs/RELEASE.md](docs/RELEASE.md). Documentation commits after this release do not change its application identity.

## Earlier implementation handoff (historical)

# Implementation handoff

SOLARIS implementation is ready for root's sequential build/browser/GPU verification queue. Do not treat implemented source or typechecking as visual acceptance.

Root supplies generated hero and interior assets, and coordinates public GitHub/Cloudflare publishing explicitly authorized by William. Publication is pending verification and root release work; no deployment was run by this agent.

Edit `src/content.ts` for project names, categories, city/year and project paragraphs; `src/main.tsx` for routing/pages/enquiry; `src/style.css` for tokens and responsive compositions; `src/Pavilion.tsx` for the original curved concrete pavilion. Keep all source/assets/dependencies local.

Browser checks required: desktop and 390px/320px layouts, all nav/hash routes and history, category filters, project-next loop, brief downloaded contents, manual/OS reduced motion, pavilion sun and camera controls, offscreen/hidden pause and disposal, unavailable-WebGL fallback, resize, focus/keyboard, console errors and actual rendering performance. Diagnostics are exposed through window.__SOLARIS_DIAGNOSTICS__ (ready, renders, paused, sun, view, disposed). No browser or build has been run by this implementation agent.

Three.js is split behind React.lazy and only requested when the light-lab section comes within 400px of the viewport. Static original architectural imagery remains visible during deferred loading. Typecheck and Biome pass after the split. Root reported an initial production build pass before this final loading adjustment; final build/browser checks belong to root's release queue.

Pavilion visual refinement after root's actual screenshot review: reduced exposure/IBL/fill, contrasting olive-grey ground and sandstone plinth, explicit shadow projection update, lower camera, original seeded concrete and timber bump surfaces, board seams/tie-hole details, slatted bench and oculus trim. Diagnostics now include actual renderer drawCalls, triangles, geometries, textures, DPR and shadow map size. Local original favicon supplied. New capture review remains root-owned; typecheck and Biome pass.
