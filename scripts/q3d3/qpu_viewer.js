// qpu_viewer.js
import { VRButton } from "https://cdn.jsdelivr.net/npm/three@0.158.0/examples/jsm/webxr/VRButton.js";

export function initViewer(THREE, OrbitControls, renderQPU) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0b0d10);

  const w = window.innerWidth;
  const h = window.innerHeight;

  const camera = new THREE.PerspectiveCamera(60, w / h, 0.1, 5000);
  camera.position.set(0, -45, 70);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(w, h);
  renderer.xr.enabled = true; // Enable WebXR
  document.body.appendChild(renderer.domElement);

  // Add VR button
  document.body.appendChild(VRButton.createButton(renderer));

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.zoomSpeed = 1.0;
  controls.minDistance = 10;
  controls.maxDistance = 2000;

  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const dir = new THREE.DirectionalLight(0xffffff, 0.7);
  dir.position.set(40, -30, 80);
  scene.add(dir);

  window.addEventListener("resize", () => {
    const w = window.innerWidth;
    const h = window.innerHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  });

  renderer.setAnimationLoop(() => {
    controls.update();
    renderer.render(scene, camera);
  });

  const ctx = {
    THREE,
    scene,
    camera,
    controls,
    renderer,
    renderQPU,
    gateLib: null,
    currentData: null
  };
  return ctx;
}

export async function setGateLibrary(modulePath, ctx) {
  if (ctx.gateLib?.dispose) {
    try {
      ctx.gateLib.dispose();
    } catch {}
  }
  const mod = await import(modulePath + `?v=${Date.now()}`);
  if (!mod.getMeshForGate) throw new Error("Gate library missing getMeshForGate()");
  ctx.gateLib = mod;
}

export function renderFromData(ctx, data) {
  const { scene, THREE, renderQPU, gateLib } = ctx;
  if (!gateLib) throw new Error("Gate library not set");
  renderQPU(data, scene, THREE, gateLib);
}
