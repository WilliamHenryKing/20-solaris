import { useEffect, useRef, useState } from "react";
import * as T from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

declare global {
  interface Window {
    __SOLARIS_DIAGNOSTICS__?: {
      ready: boolean;
      renders: number;
      paused: boolean;
      sun: number;
      view: number;
      disposed: boolean;
      drawCalls: number;
      triangles: number;
      geometries: number;
      textures: number;
      dpr: number;
      shadowMap: number;
    };
  }
}
export function Pavilion({ reduced }: { reduced: boolean }) {
  const host = useRef<HTMLDivElement>(null);
  const controller = useRef<{ sun: (n: number) => void; view: (n: number) => void } | null>(null);
  const [sun, setSun] = useState(42);
  const [view, setView] = useState(0);
  const [failed, setFailed] = useState(false);
  const settings = useRef({ sun: 42, view: 0 });
  useEffect(() => {
    if (!host.current) return;
    const el = host.current;
    let renderer: T.WebGLRenderer;
    try {
      renderer = new T.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      setFailed(true);
      return;
    }
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.6));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = T.PCFShadowMap;
    renderer.toneMapping = T.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.82;
    el.appendChild(renderer.domElement);
    const scene = new T.Scene();
    scene.background = new T.Color("#9a9e8d");
    const camera = new T.PerspectiveCamera(35, 1, 0.1, 2000);
    const target = new T.Vector3(0, 1, 0);
    const pmrem = new T.PMREMGenerator(renderer);
    const env = new RoomEnvironment();
    const envTarget = pmrem.fromScene(env, 0.04);
    scene.environment = envTarget.texture;
    scene.environmentIntensity = 0.22;
    env.dispose();
    const surface = (timber: boolean) => {
      const canvas = document.createElement("canvas");
      canvas.width = 512;
      canvas.height = 512;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Material canvas unavailable");
      const pixels = ctx.createImageData(512, 512);
      let seed = 91;
      for (let y = 0; y < 512; y++)
        for (let x = 0; x < 512; x++) {
          seed = (seed * 1664525 + 1013904223) >>> 0;
          const noise = seed / 4294967296;
          const grain = timber
            ? Math.sin(x * 0.4 + Math.sin(y * 0.015) * 4) * 18 + Math.sin(x * 1.4) * 5
            : 0;
          const value = 145 + grain + noise * 55;
          const offset = (y * 512 + x) * 4;
          pixels.data[offset] = value;
          pixels.data[offset + 1] = value;
          pixels.data[offset + 2] = value;
          pixels.data[offset + 3] = 255;
        }
      ctx.putImageData(pixels, 0, 0);
      const texture = new T.CanvasTexture(canvas);
      texture.wrapS = texture.wrapT = T.RepeatWrapping;
      texture.repeat.set(timber ? 2 : 3, timber ? 1 : 3);
      return texture;
    };
    const concreteTexture = surface(false),
      woodTexture = surface(true);
    const concrete = new T.MeshStandardMaterial({
      color: "#d5cfbc",
      roughness: 0.92,
      bumpMap: concreteTexture,
      bumpScale: 0.016,
    });
    const floor = new T.MeshStandardMaterial({
      color: "#b7ac92",
      roughness: 0.92,
      bumpMap: concreteTexture,
      bumpScale: 0.013,
    });
    const blue = new T.MeshStandardMaterial({ color: "#263dbd", roughness: 0.52 });
    const wood = new T.MeshStandardMaterial({
      color: "#765034",
      roughness: 0.76,
      bumpMap: woodTexture,
      bumpScale: 0.018,
    });
    const trim = new T.MeshStandardMaterial({ color: "#655f4f", roughness: 0.74 });
    const mesh = (g: T.BufferGeometry, m: T.Material, x: number, y: number, z: number) => {
      const o = new T.Mesh(g, m);
      o.position.set(x, y, z);
      o.castShadow = true;
      o.receiveShadow = true;
      scene.add(o);
      return o;
    };
    const ground = mesh(
      new T.PlaneGeometry(2000, 2000),
      new T.MeshStandardMaterial({ color: "#9a9e8d", roughness: 1 }),
      0,
      -0.11,
      0,
    );
    ground.rotation.x = -Math.PI / 2;
    mesh(new T.CylinderGeometry(4.8, 4.8, 0.18, 96), floor, 0, 0, 0);
    mesh(new T.CylinderGeometry(4.815, 4.815, 0.035, 96), trim, 0, -0.072, 0);
    // Fine stone paving joints establish scale without competing with the changing sunlight.
    const jointMaterial = new T.MeshStandardMaterial({ color: "#898572", roughness: 1 });
    const pavingJoints = new T.InstancedMesh(new T.BoxGeometry(1, 1, 1), jointMaterial, 22);
    const jointTransform = new T.Object3D();
    for (let i = 0; i < 11; i++) {
      const offset = (i - 5) * 0.8;
      const length = Math.sqrt(4.77 ** 2 - offset ** 2) * 2;
      jointTransform.position.set(offset, 0.094, 0);
      jointTransform.scale.set(0.009, 0.002, length);
      jointTransform.updateMatrix();
      pavingJoints.setMatrixAt(i, jointTransform.matrix);
      jointTransform.position.set(0, 0.094, offset);
      jointTransform.scale.set(length, 0.002, 0.009);
      jointTransform.updateMatrix();
      pavingJoints.setMatrixAt(i + 11, jointTransform.matrix);
    }
    pavingJoints.receiveShadow = true;
    scene.add(pavingJoints);
    // A curved wall, deliberately open to the courtyard.
    const arc = new T.Shape();
    const outer = 3.45,
      inner = 3.16;
    arc.absarc(0, 0, outer, 0.12, Math.PI * 1.12, false);
    arc.lineTo(inner * Math.cos(Math.PI * 1.12), inner * Math.sin(Math.PI * 1.12));
    arc.absarc(0, 0, inner, Math.PI * 1.12, 0.12, true);
    arc.closePath();
    const wallGeo = new T.ExtrudeGeometry(arc, {
      depth: 2.65,
      bevelEnabled: true,
      bevelThickness: 0.045,
      bevelSize: 0.045,
      bevelSegments: 2,
      steps: 1,
      curveSegments: 64,
    });
    wallGeo.rotateX(-Math.PI / 2);
    mesh(wallGeo, concrete, 0, 0.12, 0);
    // Cast-concrete board seams and tie-hole impressions are scaled to the architecture.
    for (const y of [0.95, 1.82]) {
      const points = Array.from({ length: 81 }, (_, i) => {
        const a = 0.12 + (i / 80) * Math.PI;
        return new T.Vector3(Math.cos(a) * 3.457, y, -Math.sin(a) * 3.457);
      });
      mesh(new T.TubeGeometry(new T.CatmullRomCurve3(points), 80, 0.009, 4, false), trim, 0, 0, 0);
    }
    const wallTies = new T.InstancedMesh(new T.CircleGeometry(0.019, 10), trim, 39);
    const tieTransform = new T.Object3D();
    for (let i = 0; i < 13; i++) {
      const a = 0.14 + (i / 12) * Math.PI;
      for (let row = 0; row < 3; row++) {
        tieTransform.position.set(Math.cos(a) * 3.458, 0.53 + row * 0.87, -Math.sin(a) * 3.458);
        tieTransform.rotation.y = Math.PI / 2 + a;
        tieTransform.updateMatrix();
        wallTies.setMatrixAt(i * 3 + row, tieTransform.matrix);
      }
    }
    scene.add(wallTies);
    // Thin floating elliptical roof with an oculus for the sun.
    const roofShape = new T.Shape();
    roofShape.absellipse(0, 0, 4.05, 3.6, 0, Math.PI * 2, false, 0);
    const hole = new T.Path();
    hole.absarc(0.4, 0.1, 1.32, 0, Math.PI * 2, true);
    roofShape.holes.push(hole);
    const roofGeo = new T.ExtrudeGeometry(roofShape, {
      depth: 0.19,
      bevelEnabled: true,
      bevelThickness: 0.045,
      bevelSize: 0.045,
      bevelSegments: 3,
      curveSegments: 80,
    });
    roofGeo.rotateX(-Math.PI / 2);
    mesh(roofGeo, concrete, 0, 2.96, 0);
    const rim = mesh(new T.TorusGeometry(1.32, 0.025, 8, 80), trim, 0.4, 2.97, -0.1);
    rim.rotation.x = Math.PI / 2;
    for (const [x, z] of [
      [-2.9, -1.9],
      [2.85, -1.65],
      [2.7, 1.7],
    ] as [number, number][])
      mesh(new T.CylinderGeometry(0.08, 0.08, 2.9, 20), concrete, x, 1.55, z);
    for (let i = 0; i < 5; i++)
      mesh(new T.BoxGeometry(2, 0.095, 0.086), wood, -0.45, 0.58, 1.8 + i * 0.1);
    for (const x of [-1.2, 0.3]) mesh(new T.BoxGeometry(0.1, 0.45, 0.4), blue, x, 0.3, 2);
    // A tapered, open-rim planter and real branch silhouette replace the former spherical canopy.
    const planterProfile = [
      new T.Vector2(0.36, 0),
      new T.Vector2(0.4, 0.035),
      new T.Vector2(0.51, 0.5),
      new T.Vector2(0.51, 0.54),
      new T.Vector2(0.47, 0.54),
      new T.Vector2(0.47, 0.49),
      new T.Vector2(0.37, 0.08),
    ];
    mesh(new T.LatheGeometry(planterProfile, 64), concrete, -1.35, 0.1, 1);
    const soil = new T.MeshStandardMaterial({ color: "#5e5949", roughness: 1 });
    mesh(new T.CylinderGeometry(0.452, 0.452, 0.035, 48), soil, -1.35, 0.59, 1);
    const bark = new T.MeshStandardMaterial({
      color: "#796d53",
      roughness: 0.98,
      bumpMap: woodTexture,
      bumpScale: 0.028,
    });
    const treeBase = new T.Vector3(-1.35, 0.6, 1);
    const trunkPath = new T.CatmullRomCurve3([
      new T.Vector3(0, 0, 0),
      new T.Vector3(0.035, 0.43, 0.015),
      new T.Vector3(-0.025, 0.88, 0.025),
      new T.Vector3(0.085, 1.22, -0.005),
      new T.Vector3(0.12, 1.58, 0.065),
    ]);
    const trunkGeometry = new T.TubeGeometry(trunkPath, 24, 0.032, 7, false);
    // Taper the sampled tube around its curve, retaining a naturally uneven trunk.
    const trunkPositions = trunkGeometry.getAttribute("position");
    for (let i = 0; i < trunkPositions.count; i++) {
      const t = Math.floor(i / 8) / 24;
      const centre = trunkPath.getPointAt(Math.min(t, 1));
      const point = new T.Vector3().fromBufferAttribute(trunkPositions, i);
      point
        .sub(centre)
        .multiplyScalar(1.35 - t * 0.95)
        .add(centre);
      trunkPositions.setXYZ(i, point.x, point.y, point.z);
    }
    trunkGeometry.computeVertexNormals();
    mesh(trunkGeometry, bark, treeBase.x, treeBase.y, treeBase.z);
    let treeSeed = 147;
    const random = () => {
      treeSeed = (treeSeed * 16807) % 2147483647;
      return (treeSeed - 1) / 2147483646;
    };
    const branches: Array<{ start: T.Vector3; end: T.Vector3; radius: number }> = [];
    const twigTips: T.Vector3[] = [];
    for (let i = 0; i < 10; i++) {
      const angle = i * 2.399 + 0.3;
      const height = 0.7 + i * 0.072;
      const reach = 0.53 - Math.max(0, i - 6) * 0.055 + random() * 0.08;
      const start = new T.Vector3(0.01 + height * 0.04, height, 0.025);
      const elbow = new T.Vector3(
        Math.cos(angle) * reach * 0.52,
        height + 0.2,
        Math.sin(angle) * reach * 0.52,
      );
      const end = new T.Vector3(
        Math.cos(angle) * reach,
        height + 0.35 + random() * 0.17,
        Math.sin(angle) * reach,
      );
      branches.push(
        { start, end: elbow, radius: 0.018 - i * 0.0006 },
        { start: elbow, end, radius: 0.01 },
      );
      for (let fork = 0; fork < 4; fork++) {
        const t = 0.3 + fork * 0.19;
        const forkStart = elbow.clone().lerp(end, t);
        const forkAngle = angle + (fork % 2 === 0 ? 0.85 : -0.85);
        const tip = forkStart
          .clone()
          .add(
            new T.Vector3(
              Math.cos(forkAngle) * 0.17,
              0.09 + random() * 0.12,
              Math.sin(forkAngle) * 0.17,
            ),
          );
        branches.push({ start: forkStart, end: tip, radius: 0.005 });
        twigTips.push(tip);
      }
      twigTips.push(end);
    }
    const branchMesh = new T.InstancedMesh(
      new T.CylinderGeometry(0.55, 1, 1, 6),
      bark,
      branches.length,
    );
    const branchTransform = new T.Object3D();
    const up = new T.Vector3(0, 1, 0);
    for (let i = 0; i < branches.length; i++) {
      const branch = branches[i];
      if (!branch) continue;
      const direction = branch.end.clone().sub(branch.start);
      branchTransform.position.copy(branch.start).add(branch.end).multiplyScalar(0.5).add(treeBase);
      branchTransform.quaternion.setFromUnitVectors(up, direction.clone().normalize());
      branchTransform.scale.set(branch.radius, direction.length(), branch.radius);
      branchTransform.updateMatrix();
      branchMesh.setMatrixAt(i, branchTransform.matrix);
    }
    branchMesh.castShadow = true;
    branchMesh.receiveShadow = true;
    scene.add(branchMesh);
    // Each narrow olive leaf is folded along its midrib, producing a silver/green light response.
    const leafGeometry = new T.BufferGeometry();
    leafGeometry.setAttribute(
      "position",
      new T.Float32BufferAttribute(
        [0, 0, 0, -0.018, 0.058, 0.004, 0, 0.065, 0.012, 0.018, 0.058, 0.004, 0, 0.14, 0],
        3,
      ),
    );
    leafGeometry.setIndex([0, 1, 2, 0, 2, 3, 1, 4, 2, 2, 4, 3]);
    leafGeometry.computeVertexNormals();
    const foliageMaterial = new T.MeshStandardMaterial({
      color: "#a8ae86",
      roughness: 0.84,
      metalness: 0,
      side: T.DoubleSide,
    });
    const leafCount = twigTips.length * 28;
    const foliage = new T.InstancedMesh(leafGeometry, foliageMaterial, leafCount);
    const leafTransform = new T.Object3D();
    const leafColor = new T.Color();
    for (let i = 0; i < leafCount; i++) {
      const tip = twigTips[Math.floor(i / 28)];
      if (!tip) continue;
      const angle = random() * Math.PI * 2;
      const reach = Math.sqrt(random()) * 0.19;
      leafTransform.position
        .copy(tip)
        .add(treeBase)
        .add(
          new T.Vector3(Math.cos(angle) * reach, (random() - 0.3) * 0.23, Math.sin(angle) * reach),
        );
      leafTransform.rotation.set(
        (random() - 0.5) * 1.8,
        random() * Math.PI * 2,
        (random() - 0.5) * 2.5,
      );
      leafTransform.scale.setScalar(0.72 + random() * 0.65);
      leafTransform.updateMatrix();
      foliage.setMatrixAt(i, leafTransform.matrix);
      leafColor.setHSL(0.17 + random() * 0.04, 0.13 + random() * 0.12, 0.38 + random() * 0.2);
      foliage.setColorAt(i, leafColor);
    }
    foliage.castShadow = true;
    foliage.receiveShadow = true;
    scene.add(foliage);
    // Small pale stones finish the planting bed; one instanced draw call keeps the detail inexpensive.
    const gravel = new T.InstancedMesh(new T.IcosahedronGeometry(1, 0), floor, 65);
    const gravelTransform = new T.Object3D();
    for (let i = 0; i < 65; i++) {
      const a = random() * Math.PI * 2;
      const radius = Math.sqrt(random()) * 0.43;
      gravelTransform.position.set(
        treeBase.x + Math.cos(a) * radius,
        0.62,
        treeBase.z + Math.sin(a) * radius,
      );
      gravelTransform.rotation.set(random(), random(), random());
      gravelTransform.scale.set(0.023 + random() * 0.015, 0.012, 0.017 + random() * 0.017);
      gravelTransform.updateMatrix();
      gravel.setMatrixAt(i, gravelTransform.matrix);
    }
    gravel.receiveShadow = true;
    scene.add(gravel);
    for (let i = 0; i < 4; i++)
      mesh(new T.BoxGeometry(1.9, 0.09, 0.55), concrete, 0, -0.02 - i * 0.035, 4.35 + i * 0.55);
    const light = new T.DirectionalLight("#fff1d0", 3.2);
    light.castShadow = true;
    light.shadow.mapSize.set(2048, 2048);
    Object.assign(light.shadow.camera, {
      left: -9,
      right: 9,
      top: 9,
      bottom: -9,
      near: 0.1,
      far: 40,
    });
    light.shadow.bias = -0.0003;
    light.shadow.camera.updateProjectionMatrix();
    light.shadow.normalBias = 0.025;
    scene.add(light);
    scene.add(new T.HemisphereLight("#dce5ff", "#827256", 0.34));
    const diag = {
      ready: true,
      renders: 0,
      paused: false,
      sun: 42,
      view: 0,
      disposed: false,
      drawCalls: 0,
      triangles: 0,
      geometries: 0,
      textures: 0,
      dpr: renderer.getPixelRatio(),
      shadowMap: 2048,
    };
    window.__SOLARIS_DIAGNOSTICS__ = diag;
    let visible = true,
      frame = 0,
      dirty = true;
    const desired = new T.Vector3(8.5, 5.3, 11.5);
    camera.position.copy(desired);
    controller.current = {
      sun(n) {
        diag.sun = n;
        const a = (n / 100) * Math.PI * 0.86 + 0.15;
        light.position.set(Math.cos(a) * 11, 2.5 + Math.sin(a) * 7, Math.sin(a) * 5 - 7);
        dirty = true;
      },
      view(n) {
        diag.view = n;
        const positions = [
          [8.5, 5.3, 11.5],
          [-8, 4.8, 9],
          [0.1, 13, 8],
        ];
        desired.set(...(positions[n] as [number, number, number]));
        if (reduced) camera.position.copy(desired);
        dirty = true;
      },
    };
    controller.current.sun(settings.current.sun);
    controller.current.view(settings.current.view);
    const resize = () => {
      const w = el.clientWidth,
        h = el.clientHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.fov = camera.aspect < 1 ? 52 : 35;
      camera.updateProjectionMatrix();
      dirty = true;
    };
    const ro = new ResizeObserver(resize);
    ro.observe(el);
    resize();
    const tick = () => {
      frame = 0;
      diag.paused = !visible || document.hidden;
      if (diag.paused) return;
      if (!reduced && camera.position.distanceTo(desired) > 0.01) {
        camera.position.lerp(desired, 0.075);
        dirty = true;
      }
      camera.lookAt(target);
      if (dirty) {
        renderer.render(scene, camera);
        diag.drawCalls = renderer.info.render.calls;
        diag.triangles = renderer.info.render.triangles;
        diag.geometries = renderer.info.memory.geometries;
        diag.textures = renderer.info.memory.textures;
        diag.renders++;
        dirty = false;
      }
      frame = requestAnimationFrame(tick);
    };
    const wake = () => {
      if (!frame) frame = requestAnimationFrame(tick);
    };
    const io = new IntersectionObserver(([entry]) => {
      visible = entry?.isIntersecting ?? false;
      wake();
    });
    io.observe(el);
    document.addEventListener("visibilitychange", wake);
    wake();
    return () => {
      diag.disposed = true;
      cancelAnimationFrame(frame);
      ro.disconnect();
      io.disconnect();
      document.removeEventListener("visibilitychange", wake);
      controller.current = null;
      scene.traverse((o) => {
        if (o instanceof T.Mesh) {
          o.geometry.dispose();
          for (const m of Array.isArray(o.material) ? o.material : [o.material]) m.dispose();
          if (o instanceof T.InstancedMesh) o.dispose();
        }
      });
      envTarget.dispose();
      concreteTexture.dispose();
      woodTexture.dispose();
      light.shadow.dispose();
      pmrem.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [reduced]);
  return (
    <section className="pavilion-section" aria-labelledby="pavilion-title">
      <div className="section-label">03 / THE DAYLIGHT LAB</div>
      <div className="pavilion-top">
        <h2 id="pavilion-title">
          Same place.
          <br />
          Different light.
        </h2>
        <p>
          Move the sun. Watch a room become something new.
          <br />
          An original architectural light study, built in 3D.
        </p>
      </div>
      <div className="pavilion-stage">
        <div
          className="scene-host"
          ref={host}
          role="img"
          aria-label="Curved concrete courtyard pavilion with an open circular skylight and changing sun shadows"
        />
        {failed && (
          <div className="scene-fallback">
            <span>◯</span>
            <h3>Daylight Pavilion</h3>
            <p>
              A curved concrete shelter with an open skylight. Morning light traces the courtyard;
              midday lights the centre; evening stretches the shadows.
            </p>
            <p>Interactive 3D is unavailable in this browser.</p>
          </div>
        )}
        <div className="scene-caption">
          SOLARIS STUDY 001
          <br />
          CONCRETE / LIGHT / OPEN SPACE
        </div>
        <fieldset className="view-controls" aria-label="Pavilion viewpoints">
          {["Perspective", "Courtyard", "Above"].map((v, i) => (
            <button
              type="button"
              key={v}
              aria-pressed={view === i}
              onClick={() => {
                setView(i);
                settings.current.view = i;
                controller.current?.view(i);
              }}
            >
              {v}
            </button>
          ))}
        </fieldset>
      </div>
      <div className="sun-control">
        <span>09:00</span>
        <label>
          Sun position{" "}
          <input
            type="range"
            min="0"
            max="100"
            value={sun}
            onChange={(e) => {
              const n = Number(e.target.value);
              setSun(n);
              settings.current.sun = n;
              controller.current?.sun(n);
            }}
            aria-valuetext={`${Math.round(9 + sun * 0.09)}:00 approximate sunlight study`}
          />
        </label>
        <span>18:00</span>
        <output>
          {sun < 33
            ? "Morning / long shadows"
            : sun < 67
              ? "Midday / overhead light"
              : "Evening / warm edges"}
        </output>
      </div>
    </section>
  );
}
