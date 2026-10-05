# SOLARIS architectural world rendering

Recorded from the completed final render metadata (UTC assembly: wide 5 October 2026, detail 5 October 2026). These are original, fictional architectural scenes built in Blender Python, with photographed CC0 surface maps and a CC0 environment image. They are not photographs of built commissions.

## Delivered source and evidence

- `assets/source/architecture-world.blend` is the editable wide-view scene, with image textures and its HDRI packed into the file. Opening this native source does not require the separate raw maps or a network connection. The final metadata records `texturesPacked: true`; packaging does not run a second Blender packed-file audit.
- `tools/worlds/solaris.py` contains the authored world and both camera compositions. `tools/worlds/world_common.py` contains the material, UV, vegetation and modeling helpers. `tools/render-architecture-cuda.py` is the helper source imported by that module; run `tools/render-world.py` as the project entry point.
- `tools/worlds/cloth/solaris.json` contains the evaluated settled cloth geometry used by the world loader, with its recorded bake metadata. `assets/source/cloth-study.blend` retains the editable simulation setup, collision proxies and rest mesh. `tools/bake-cloth.py` is the local reconstruction source; `docs/render/cloth.json` preserves the supplied metadata/settings and any metadata sidecars.
- `docs/render/wide.json` and `detail.json` are copies of the actual final render metadata. Their matching `*-machine.json` files are the original machine-guard records. `docs/render/package.json` records source/output hashes and whether the separately encoded WebPs existed at packaging time.
- The earlier `docs/live-report.json` and `docs/RELEASE.md` were preserved under `docs/releases/first-2026-10-03/` if no earlier snapshot existed. They describe the first release, not this render revision.

Both final frames are **3200 × 2000**, 16-bit PNG render outputs. Cycles used **CUDA GPU rendering with CPU devices disabled**, followed by **OptiX denoising**. OptiX here names the denoiser, not the rendering compute backend. Sampling targets were **768 for the wide view** and **1024 for detail**, with an adaptive noise threshold of **0.005** and a **96-sample minimum**. Adaptive sampling means these caps are not a claim that every pixel received the maximum sample count.

### Actual image completion method

- Wide: checkpointed border regions with 64px overscan.
- Detail: checkpointed border regions with 64px overscan.

Where checkpointed regions are recorded above, the final image was assembled from eight independently completed CUDA border renders on a 4 × 2 grid, with 64px overscan clipped at the frame edges. The camera and full-resolution pixel grid remain fixed. Assembly copies the central uint16 pixels without blending or resampling; recorded PNG colour chunks are preserved. This is an assembled image, not a single uninterrupted full-frame GPU render. Region denoising can differ from full-frame denoising; seam inspection is a separate visual review, not certified by this packaging operation.

`docs/render/checkpoints/{wide,detail}/` retains the actual checkpoint manifest, construction receipts and every region's raw metadata and machine samples when that view used regions. Region PNGs are not duplicated into this repository; their original byte counts and SHA-256 receipts remain in the manifest. Aggregate machine elapsed time sums guarded phases; sample clocks belong to their named phase and do not claim continuous monitoring between resumptions. `assets/source/checkpoint-tools/` archives the orchestration, border-render and guard source used by the collection. These archived helpers retain collection-specific paths/runtime assumptions and require adaptation before standalone use; they are not shared runtime imports.

| View | Recorded Blender | Recorded CUDA device | Sample cap | Adaptive minimum | Evaluated triangles |
| --- | --- | --- | --- | --- | --- |
| Wide | 5.2.2 LTS | NVIDIA GeForce RTX 2060 | 768 | 96 | 2,452,090 |
| Detail | 5.2.2 LTS | NVIDIA GeForce RTX 2060 | 1024 | 96 | 2,452,090 |

The JSON records describe these particular jobs. They do not establish a general performance benchmark, browser acceptance, user approval, live publication or a claim of photorealism.

## Reproduce or edit

Open the packed file in Blender to edit objects, materials, lights or the wide camera. Its recorded Blender version is 5.2.2 LTS; different versions or drivers may produce different results. Select an available NVIDIA CUDA device in Blender's Cycles preferences when rendering interactively.

For source reconstruction, use Python 3 and Blender on `PATH`, and run these commands from this project's root. The fetcher downloads only the six texture IDs used by the palette and the final Kloofendal HDRI, then checks every file's recorded byte count and SHA-256. It skips already verified files. Raw downloads live in ignored `assets/source/textures/`; they are not duplicated in the repository.

The project-local `render-world.py` commands below reproduce an ordinary full image on a machine with sufficient memory. They do not resume region checkpoints or promise byte-identical output to the assembled delivery. For the exact original region contract, inspect the archived source and checkpoint manifests; install OpenCV/NumPy in an isolated Python environment and adapt the recorded runtime/output paths before using that orchestration.

```powershell
python tools/fetch-render-textures.py
blender --background --factory-startup --python tools/render-world.py -- --scene solaris --view wide --quality final --output output/render/solaris-wide.png
blender --background --factory-startup --python tools/render-world.py -- --scene solaris --view detail --quality final --output output/render/solaris-detail.png
```

To construct and save the scene without rendering, add `--validate` to either render command. To inspect geometry at the lighter draft configuration, use `--quality draft`. Each construction command saves its own packed `.blend` beside the requested output. The detailed source camera is rebuilt with `--view detail`; the packaged native `.blend` starts on the wide camera.

The reproduction commands configure CUDA and refuse a CPU fallback. They do not reproduce the external machine-supervision wrapper that wrote the delivered guard logs. Run resource-heavy jobs sequentially. The website does not execute these Python tools or request their texture files.

## Gravity-settled cloth

The packaged cloth export contains 7,171 vertices and 7,000 faces. Its recorded method is: **Blender Cloth gravity and self-collision; no analytic final fold surface**. Recorded final frame: **130**; Blender version: **5.2.2 LTS**. The exact rest pose, collision and gravity settings are retained in `docs/render/cloth.json` when supplied by the baker. These are actual source records, not a visual-quality or physical-validation claim.

Blender Cloth simulation is a CPU operation separate from the CUDA image rendering described above. The delivered world loads the exported settled vertices and rest-fabric UVs; it does not run a live cloth simulation during every final render. To recompute the cloth, run the local baker, then deliberately replace the geometry export before rebuilding the world:

```powershell
blender --background --factory-startup --python tools/bake-cloth.py -- --scene solaris --output output/cloth/solaris.json
Copy-Item -LiteralPath output/cloth/solaris.json -Destination tools/worlds/cloth/solaris.json
```

The editable `cloth-study.blend` must be distinguished from its external point-cache files. The baker uses a disk-backed simulation cache; this packaging operation copies the native `.blend` and evaluated JSON, but does not copy that external cache directory or claim that the native file contains self-contained baked playback. A hidden object named `SETTLED SNAPSHOT / unhide to inspect without cache` preserves the actual settled mesh independently of that cache; unhide it to inspect the final geometry. Keep the generated `output/cloth/` cache when rebaking locally. The exported JSON is sufficient for the world loader's settled geometry; rebake from the native setup/source when a fresh simulation is needed.

## Materials, transformations and attribution

Original work includes scene geometry, object placement, cameras, joinery, vegetation construction and lighting composition. Photographic surface maps and the environment are from [Poly Haven under CC0 1.0](https://polyhaven.com/license). Exact URLs, authors, original file names, byte sizes and SHA-256 hashes are retained in `assets/source/texture-manifest.json`.

| Asset | Creator and role | Source |
| --- | --- | --- |
| `fine_grained_wood` | Rob Tuytel (All) | [Poly Haven asset](https://polyhaven.com/a/fine_grained_wood) |
| `rosewood_veneer1` | Jenelle van Heerden (All) | [Poly Haven asset](https://polyhaven.com/a/rosewood_veneer1) |
| `marble_01` | Rob Tuytel (All) | [Poly Haven asset](https://polyhaven.com/a/marble_01) |
| `plastered_wall` | Amal Kumar (All) | [Poly Haven asset](https://polyhaven.com/a/plastered_wall) |
| `rough_linen` | colormass (Photography); Rico Cilliers (Processing) | [Poly Haven asset](https://polyhaven.com/a/rough_linen) |
| `concrete_wall_004` | Dario Barresi (Processing); Charlotte Baglioni (Photography) | [Poly Haven asset](https://polyhaven.com/a/concrete_wall_004) |
| `kloofendal_48d_partly_cloudy` | Greg Zaal (All) | [Poly Haven asset](https://polyhaven.com/a/kloofendal_48d_partly_cloudy) |

The full acquisition manifest also retains unused candidates such as the earlier dawn environment and ground texture. The fetcher retrieves only the seven asset IDs listed above. No external model geometry was used.

Material maps are reused through physical-scale UV mapping, including cylindrical UVs where appropriate, selective stone/concrete UV crops and recolouring. Wood is tinted, roughness/normal strengths are tuned, and the photographed linen colour is remapped while retaining its weave. This is an authored adaptation of those source maps, not a claim that every material is a literal scanned specimen of the named design finish.

Glazing uses a straight-through shadow-ray approximation so clear windows transmit direct lighting while refractive caustics are disabled; camera, reflection and refraction rays use the glass shader. Bounce emitters are hidden from camera/glossy/transmission visibility to keep them from becoming luminous rectangles in the architecture. These deliberate rendering approximations are recorded in `world_common.py`.

## Website delivery boundary

The wide delivery names are `solaris-world.webp` and `solaris-world-mobile.webp`. Detail uses `solaris-light-study.webp` and `solaris-light-study-mobile.webp`, all in `public/images/`. WebP conversion is a separate operation; the packaging script does not encode images, run a website build, inspect a browser, commit, push or deploy. Older ImageGen/licensed image provenance remains in `ASSETS.md`.
