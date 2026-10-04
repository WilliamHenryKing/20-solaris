# SOLARIS — Impeccable refinement

Date: 3 October 2026. Status: source refinement recorded; new render acceptance, browser verification and publication receipts pending.

This record concerns the current refinement of SOLARIS. Earlier release evidence remains historical evidence for that earlier application release, and does not certify these changes.

## Design and interaction changes

- Replaced typographic icon substitutes with authored SVG marks: the sun uses a central disc and eight rays; arrows use a consistent drawn stroke. Both are decorative, hidden from assistive technology and excluded from focus. No emojis are used.
- Removed section kickers that competed with the content. The opening now lets the complete “Designed around the light.” headline, architectural photograph and sun mark establish the practice. Typography, small text and phone composition were adjusted for clearer hierarchy and a more deliberate first viewport.
- Scoped GSAP arrival choreography moves headline lines by 55%, rotates and scales the sun gently, and opens the hero photograph through an inset aperture. Section reveals and restrained project-image drift remain scoped through `useGSAP`, with cleanup on route changes. Reduced motion uses the settled layout.
- Added `WorldGallery` with explicit “The space” and “The detail” buttons, a labelled fieldset and `aria-pressed` state. The controls switch between responsive wide-world and material-detail image contracts. Captions and alternative text describe the chosen composition. These contracts do not imply that their final rendered assets have been approved.
- Added the shared `MaterialStudy` presentation to the deferred study placeholder and the live pavilion introduction. It presents the same architectural image gallery before “Now, move the light.”, keeping the transition coherent while the interactive module loads.
- Preserved viewport-deferred Three.js loading: an intersection observer starts the lazy pavilion import near the section and disconnects afterward. The static study remains useful while loading. The live scene retains its dirty-frame rendering, offscreen and hidden-document pause, capped pixel ratio and resource disposal lifecycle.
- Refined navigation focus behavior: route changes close the menu and focus the main content; choosing the current route also closes the menu and focuses main. Escape closes an expanded menu and returns focus to its trigger. Escape does not redirect focus when the menu is already closed. The skip control targets main content.

## Skill and review scope

The team used one installed official Impeccable skill, with its 24 command playbooks read across the refinement team. The root context pass was already completed once; it was not rerun for this documentation task. The manual detector scan was also run once: its two Arial warnings were fixed. No rerun or automatic hook execution is claimed. User authorization permits hooks, but authorization is not evidence that a hook executed. The installed source is [official Impeccable at its pinned commit](https://github.com/pbakaus/impeccable/blob/e103efe779e2dd01274dabae83531fef00bf2563/plugin/skills/impeccable/SKILL.md).

The intended result preserves SOLARIS's butter, ink and ultramarine palette, generous Manrope typography, inhabited architectural scale and sunlight as the central material. Authored icons and quieter supporting copy reinforce that identity.

## Camera journey and GSAP references

The live Three.js pavilion now follows a continuous camera and look-target path through arrival, beneath the oculus and toward the garden. A scoped `useGSAP` timeline with ScrollTrigger maps native scrolling to the path. Desktop and portrait paths are constructed once; the sampled position vector is reused. Captions change at chapter boundaries. Sticky composition adds no wheel interception or scroll trapping.

Chapter buttons cut to explicit views; Pause/Resume and the keyboard-operable “Skip to the controls” support direct navigation. Choosing a manual viewpoint or moving the sun transfers ownership to the visitor until explicit resume. Reduced motion retains a static composition. Resize reapplies scroll framing only while the journey owns the camera. Cleanup reverts its timeline and trigger; existing visibility gating and GPU disposal remain. Diagnostics expose progress, owner, chapter, camera/target coordinates and trigger count during actual renders. These are implemented features, with current behavioral and visual verification still pending.

The project-local official GSAP references comprise seven skills: core, timeline, React, ScrollTrigger, performance, plugins and utils. Their source is [GreenSock/gsap-skills pinned at `aed9cfd3277740755f6bfc1155c7aa645403b760`](https://github.com/greensock/gsap-skills/tree/aed9cfd3277740755f6bfc1155c7aa645403b760). Installed references guide implementation; they do not certify browser results.

## Pending evidence

Root is still producing and reviewing the new architectural renders. Render receipts, visual acceptance, current browser interaction and accessibility results, and any refinement publication verification must be appended after those checks occur. This document claims none of those steps as complete. It also claims no physical-device testing, measured frame rate, user acceptance or CMS/backend implementation.

### Resumed refinement — 4 October 2026

A fresh root agent resumed this work from the cold handover. Read-only reviews were confirmed in a running page (Chrome with software WebGL, so the busy GPU was not used). These defects were real and are corrected:

- **Pause and chapters collapsed the journey.** Both set a paused state that added `journey-static`, removing the 235vh runway at an unchanged scroll position, so the stage left the viewport and the chosen composition happened off screen. Ownership is now explicit (scroll, paused, manual, named view). Pause holds the camera in place on its runway; chapters travel the native scroll to their point; Resume appears whenever the camera is held. At 1366×657, pause kept the journey height and stage pinned; resume, chapter travel, skip, viewpoint and motion changes behaved as intended.
- **The sticky stage overflowed laptop screens.** 782px of sticky content clipped the chapter row below about 780px. The stage now shortens with the viewport (300–620px), so the chapters stay visible at 1366×657.
- **Small text.** The earlier note that small controls were restored did not hold in the final cascade: measured viewpoint buttons, captions, filters, project captions, detail facts, sun labels, brief preview and footer text were 12–13px. A 14px floor now holds on every route at 1440 and 390px.
- **Coherence and resilience.** The pressed chapter fill used an undefined `--ink` token; it is now defined. The image gallery no longer remounts (and loses its selection) when the study loads. ScrollTrigger re-measures after the late mount. An error boundary keeps the static image if the chunk fails. The first load no longer moves focus past the header. The project-image drift no longer exposes the card background. The hero choreography runs only on the home route. A restored WebGL context rebuilds the reflection map. Unmounting releases the GL context. The footer motion switch keeps one accessible name with `aria-pressed`.

These interim probes predate the final renders and build; they are not release QA. The detector second pass is recorded in [IMPECCABLE-DETECTOR.md](IMPECCABLE-DETECTOR.md).

### Root verification receipts

Pending: render identities and selected assets; final visual review; local browser results; release identity and live verification, if published.
