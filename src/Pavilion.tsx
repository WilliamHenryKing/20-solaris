import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollToPlugin } from "gsap/ScrollToPlugin";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useEffect, useRef, useState } from "react";
import * as T from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

gsap.registerPlugin(useGSAP, ScrollTrigger, ScrollToPlugin);

// Reverting a context renders its recorded timeline at the start before cleanups run.
// That render is bookkeeping, not a camera move, so the journey ignores it.
const reverting = () =>
  Boolean((gsap.core as unknown as { reverting?: () => unknown }).reverting?.());

const chapters = [
  { label: "Arrival", progress: 0, caption: "Arrival — the curved wall gathers the sun." },
  {
    label: "Under the oculus",
    progress: 0.5,
    caption: "Under the oculus — daylight becomes a room.",
  },
  { label: "Toward the garden", progress: 1, caption: "Toward the garden — the threshold opens." },
];
const viewpoints = [
  { label: "Perspective", caption: "Perspective — the whole courtyard at once." },
  { label: "Courtyard", caption: "Courtyard — standing inside the curve." },
  { label: "Above", caption: "Above — the plan, drawn in sunlight." },
];
const chapterFor = (value: number) => (value < 0.32 ? 0 : value < 0.72 ? 1 : 2);
/** scroll: native scroll drives the camera. paused: held by the visitor. manual: the sun or the
 * controls took over. view: a named viewpoint replaced the journey composition. */
type Owner = "scroll" | "paused" | "manual" | "view";
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
      journeyProgress: number;
      journeyOwner: string;
      chapter: number;
      cameraPosition: number[];
      lookTarget: number[];
      journeyTriggerCount: number;
    };
  }
}
export function Pavilion({ reduced }: { reduced: boolean }) {
  const journeyRoot = useRef<HTMLDivElement>(null);
  const manualControls = useRef<HTMLElement>(null);
  const progress = useRef(0);
  const [owner, setOwnerState] = useState<Owner>("scroll");
  const ownerRef = useRef<Owner>("scroll");
  const setOwner = (next: Owner) => {
    ownerRef.current = next;
    setOwnerState(next);
  };
  const timeline = useRef<gsap.core.Timeline | null>(null);
  const scrollTween = useRef<gsap.core.Tween | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [chapter, setChapter] = useState(0);
  const chapterRef = useRef(0);
  const changeChapter = (next: number) => {
    if (chapterRef.current === next) return;
    chapterRef.current = next;
    setChapter(next);
  };
  const host = useRef<HTMLDivElement>(null);
  const controller = useRef<{
    sun: (n: number) => void;
    view: (n: number) => void;
    journey: (n: number, force?: boolean) => void;
    freeze: () => void;
  } | null>(null);
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
    // A lost context shows the drawn fallback. Three restores its own GL state; only the
    // reflection map (render-target contents are lost) needs rebuilding.
    const onLost = (event: Event) => {
      event.preventDefault();
      envTarget.dispose();
      setFailed(true);
    };
    const onRestored = () => {
      envTarget = buildEnvironment();
      scene.environment = envTarget.texture;
      setFailed(false);
      dirty = true;
      wake();
    };
    renderer.domElement.addEventListener("webglcontextlost", onLost);
    renderer.domElement.addEventListener("webglcontextrestored", onRestored);
    renderer.shadowMap.type = T.PCFShadowMap;
    renderer.toneMapping = T.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.82;
    el.appendChild(renderer.domElement);
    const scene = new T.Scene();
    scene.background = new T.Color("#9a9e8d");
    const camera = new T.PerspectiveCamera(35, 1, 0.1, 2000);
    const target = new T.Vector3(0, 1, 0);
    const buildEnvironment = () => {
      const room = new RoomEnvironment();
      const generator = new T.PMREMGenerator(renderer);
      const result = generator.fromScene(room, 0.04);
      room.dispose();
      generator.dispose();
      return result;
    };
    let envTarget = buildEnvironment();
    scene.environment = envTarget.texture;
    scene.environmentIntensity = 0.22;
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
      journeyProgress: 0,
      journeyOwner: "scroll",
      chapter: 0,
      cameraPosition: [0, 0, 0],
      lookTarget: [0, 0, 0],
      journeyTriggerCount: 0,
    };
    window.__SOLARIS_DIAGNOSTICS__ = diag;
    let visible = true,
      frame = 0,
      dirty = true;
    const desired = new T.Vector3(8.5, 5.3, 11.5);
    const makeRoute = (portrait: boolean) =>
      new T.CatmullRomCurve3([
        new T.Vector3(portrait ? 7 : 8.5, 5.3, portrait ? 13.5 : 11.5),
        new T.Vector3(3.2, 2.5, 5.4),
        new T.Vector3(0.4, 1.8, 2.2),
        new T.Vector3(-1.8, 1.7, 0.6),
      ]);
    const desktopRoute = makeRoute(false);
    const portraitRoute = makeRoute(true);
    camera.position.copy(desired);
    controller.current = {
      sun(n) {
        diag.sun = n;
        const a = (n / 100) * Math.PI * 0.86 + 0.15;
        light.position.set(Math.cos(a) * 11, 2.5 + Math.sin(a) * 7, Math.sin(a) * 5 - 7);
        dirty = true;
      },
      freeze() {
        desired.copy(camera.position);
        dirty = true;
      },
      journey(n, force = false) {
        if (!force && (ownerRef.current !== "scroll" || reduced)) return;
        const route = camera.aspect < 1 ? portraitRoute : desktopRoute;
        route.getPoint(Math.max(0, Math.min(1, n)), desired);
        target.set(-n * 0.8, 1.1 + Math.sin(n * Math.PI) * 0.7, -n * 2.3);
        camera.position.copy(desired);
        dirty = true;
      },
      view(n) {
        target.set(0, 1, 0);
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
    controller.current.journey(progress.current);
    const resize = () => {
      const w = el.clientWidth,
        h = el.clientHeight;
      renderer.setPixelRatio(Math.min(devicePixelRatio, 1.6));
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.fov = camera.aspect < 1 ? 52 : 35;
      camera.updateProjectionMatrix();
      if (ownerRef.current === "scroll" && !reduced) controller.current?.journey(progress.current);
      dirty = true;
    };
    const ro = new ResizeObserver(resize);
    ro.observe(el);
    resize();
    controller.current.journey(progress.current);
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
        diag.journeyProgress = progress.current;
        // A visitor's choice outranks the motion setting; named viewpoints report as manual.
        const held = ownerRef.current;
        diag.journeyOwner =
          held === "view"
            ? "manual"
            : held !== "scroll"
              ? held
              : reduced
                ? "reduced-motion"
                : "scroll";
        diag.chapter = chapterRef.current;
        camera.position.toArray(diag.cameraPosition);
        target.toArray(diag.lookTarget);
        diag.journeyTriggerCount = ScrollTrigger.getAll().filter(
          (trigger) => trigger.trigger === journeyRoot.current,
        ).length;
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
    // The newest record wins when the browser batches an enter and a leave together.
    const io = new IntersectionObserver((entries) => {
      visible = entries.at(-1)?.isIntersecting ?? false;
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
      renderer.domElement.removeEventListener("webglcontextlost", onLost);
      renderer.domElement.removeEventListener("webglcontextrestored", onRestored);
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
      renderer.dispose();
      // Release the GL context now rather than at garbage collection (browsers cap live contexts).
      renderer.forceContextLoss();
      renderer.domElement.remove();
    };
  }, [reduced]);

  // Changing the motion preference starts a fresh, scroll-owned journey.
  const lastReduced = useRef(reduced);
  useEffect(() => {
    if (lastReduced.current === reduced) return;
    lastReduced.current = reduced;
    ownerRef.current = "scroll";
    setOwnerState("scroll");
  }, [reduced]);
  // Chapter jumps live outside the useGSAP context so a revert cannot rewind the page.
  useEffect(() => () => void scrollTween.current?.kill(), []);
  useGSAP(
    () => {
      if (reduced || failed || !journeyRoot.current) return;
      const playhead = { value: 0 };
      timeline.current = gsap
        .timeline({
          scrollTrigger: {
            trigger: journeyRoot.current,
            start: "top top",
            end: "bottom bottom",
            scrub: true,
          },
        })
        .to(playhead, {
          value: 1,
          ease: "none",
          duration: 1,
          onUpdate: () => {
            if (reverting()) return;
            progress.current = playhead.value;
            if (ownerRef.current !== "scroll" || document.hidden) return;
            controller.current?.journey(playhead.value);
            changeChapter(chapterFor(playhead.value));
          },
        });
      // This section mounts late and changes the page height; re-measure every trigger.
      const refresh = requestAnimationFrame(() => ScrollTrigger.refresh());
      return () => {
        cancelAnimationFrame(refresh);
        scrollTween.current?.kill();
        timeline.current = null;
      };
    },
    { scope: journeyRoot, dependencies: [reduced, failed], revertOnUpdate: true },
  );
  const journeyLive = !reduced && !failed;
  const resumeJourney = () => {
    setOwner("scroll");
    controller.current?.journey(progress.current, true);
    changeChapter(chapterFor(progress.current));
  };
  const jumpToChapter = (index: number) => {
    const destination = chapters[index];
    if (!destination) return;
    setAnnouncement(`${destination.label} view`);
    scrollTween.current?.kill();
    const trigger = timeline.current?.scrollTrigger;
    if (journeyLive && trigger) {
      // The journey keeps its runway: travel there and let the scroll own the camera.
      resumeJourney();
      scrollTween.current = gsap.to(window, {
        duration: 0.9,
        ease: "power2.inOut",
        scrollTo: {
          y: trigger.start + (trigger.end - trigger.start) * destination.progress,
          autoKill: true,
        },
      });
      return;
    }
    // Without a scroll journey the chapter is an explicit cut that the visitor owns.
    progress.current = destination.progress;
    setOwner("manual");
    controller.current?.journey(destination.progress, true);
    changeChapter(index);
  };
  const finishJourney = () => {
    setOwner("manual");
    controller.current?.freeze();
    // Bring the controls up with as much of the stage as fits above them.
    manualControls.current?.scrollIntoView({ behavior: "instant", block: "end" });
    manualControls.current?.focus({ preventScroll: true });
  };
  const caption = owner === "view" ? viewpoints[view]?.caption : chapters[chapter]?.caption;
  const holdOrResume = () => {
    if (ownerRef.current === "scroll") {
      setOwner("paused");
      controller.current?.freeze();
    } else resumeJourney();
  };
  return (
    <>
      <div className={`sunlight-journey ${journeyLive ? "" : "journey-static"}`} ref={journeyRoot}>
        <div className="journey-sticky">
          <div className="journey-toolbar">
            <p>
              {!journeyLive
                ? "Choose a chapter or a viewpoint."
                : owner === "scroll"
                  ? "Follow the daylight through the courtyard."
                  : "The camera is yours. Resume to follow the scroll."}
            </p>
            <button type="button" onClick={finishJourney}>
              Skip to the controls
            </button>
            {journeyLive && (
              <button type="button" onClick={holdOrResume}>
                {owner === "scroll" ? "Pause journey" : "Resume journey"}
              </button>
            )}
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
                <div className="fallback-oculus" aria-hidden="true" />
                <h3>Daylight Pavilion</h3>
                <p>
                  A curved concrete shelter with an open skylight. Morning light traces the
                  courtyard; midday lights the centre; evening stretches the shadows.
                </p>
                <p>Interactive 3D is unavailable in this browser.</p>
              </div>
            )}
            <div className="scene-caption">{caption}</div>
          </div>
          <div className="journey-chapters">
            {chapters.map((item, i) => (
              <button
                type="button"
                key={item.label}
                aria-pressed={owner !== "view" && chapter === i}
                disabled={failed}
                onClick={() => jumpToChapter(i)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <p className="sr-only" aria-live="polite">
            {announcement}
          </p>
        </div>
      </div>
      <section
        ref={manualControls}
        className="pavilion-manual"
        tabIndex={-1}
        aria-label="Manual pavilion controls"
      >
        <fieldset className="view-controls" aria-label="Pavilion viewpoints">
          {viewpoints.map((item, i) => (
            <button
              type="button"
              key={item.label}
              aria-pressed={owner === "view" && view === i}
              onClick={() => {
                setOwner("view");
                setView(i);
                settings.current.view = i;
                controller.current?.view(i);
                setAnnouncement(`${item.label} viewpoint`);
              }}
            >
              {item.label}
            </button>
          ))}
        </fieldset>
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
                // Moving the sun holds the current camera until the visitor resumes.
                if (ownerRef.current === "scroll") {
                  setOwner("manual");
                  controller.current?.freeze();
                }
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
    </>
  );
}
