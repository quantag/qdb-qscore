// ============================================================
// MBQC Viewer — ES Module version
// Requires: three.module.js, OrbitControls.js (local files)
// Exports:  initMBQCViewer(THREE, OrbitControls)
// ============================================================
// ============================================================
// Simple export wrapper for external rendering
// ============================================================
export function renderMBQC(scene, THREE, data) {
  const container = document.getElementById('mbqcContainer') 
                 || document.getElementById('threeContainer') 
                 || document.body;

  const zxGraph = data.zx_graph || {};
  const mbqcPattern = data.mbqc_pattern || {};

  const viewer = initMBQCViewer(THREE, OrbitControls, container);
  viewer.compileAndRender = undefined;
  viewer.buildGraph?.(zxGraph, mbqcPattern);
}

export function initMBQCViewer(THREE, OrbitControls, containerEl) {

  // ----- Config -----
  const API_URL = "https://cloud.quantag-it.com/api2/translate";


  // ----- DOM Elements -----
 // const sceneEl   = document.getElementById("scene");
  const sceneEl = containerEl 
               || document.getElementById("mbqcContainer") 
               || document.getElementById("threeContainer") 
               || document.body;

  const statusEl  = document.getElementById("status");
  const animateChk = document.getElementById("animate");

  // ----- Three.js globals -----
  let renderer, scene, camera, controls;
  let nodesGroup, edgesGroup;
  let pulseIdx = 0, order = [];

  // ----- Utility -----
  const setStatus = msg => statusEl.textContent = msg;
  const b64 = s => btoa(unescape(encodeURIComponent(s)));

  // ============================================================
  // Scene setup
  // ============================================================
  function initThree() {
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(sceneEl.clientWidth, sceneEl.clientHeight);
    sceneEl.innerHTML = "";
    sceneEl.appendChild(renderer.domElement);

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b0f14);

    camera = new THREE.PerspectiveCamera(
      45,
      sceneEl.clientWidth / sceneEl.clientHeight,
      0.01,
      2000
    );
    camera.position.set(12, 10, 22);

controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.enableZoom = false;  // disable built-in zoom
controls.minDistance = 3;
controls.maxDistance = 120;

// custom smooth zoom
renderer.domElement.addEventListener("wheel", (e) => {
  e.preventDefault();
  const dir = camera.getWorldDirection(new THREE.Vector3());
  const step = 0.4; // tune this
  const delta = e.deltaY < 0 ? -step : step;
  camera.position.addScaledVector(dir, delta);
  const dist = camera.position.length();
  if (dist < controls.minDistance) camera.position.setLength(controls.minDistance);
  if (dist > controls.maxDistance) camera.position.setLength(controls.maxDistance);
  controls.update();
}, { passive: false });


    const amb = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(amb);
    const dir = new THREE.DirectionalLight(0xffffff, 0.7);
    dir.position.set(5, 10, 7);
    scene.add(dir);

    const grid = new THREE.GridHelper(100, 100, 0x223246, 0x111826);
    grid.position.y = -0.5;
    scene.add(grid);

    nodesGroup = new THREE.Group();
    edgesGroup = new THREE.Group();
    scene.add(edgesGroup);
    scene.add(nodesGroup);

    window.addEventListener("resize", onResize);
    onResize();
    requestAnimationFrame(loop);
  }

  function onResize() {
    if (!renderer) return;
    renderer.setSize(sceneEl.clientWidth, sceneEl.clientHeight);
    camera.aspect = sceneEl.clientWidth / sceneEl.clientHeight;
    camera.updateProjectionMatrix();
  }

  function loop() {
    controls.update();

    // animate pulse along measurement order
    if (order.length && animateChk.checked) {
      const t = (Date.now() % 1000) / 1000; // 0..1
      const idx = Math.floor(t * order.length);
      if (idx !== pulseIdx) {
        pulseIdx = idx;
        highlightNode(order[pulseIdx]);
      }
    }

    renderer.render(scene, camera);
    requestAnimationFrame(loop);
  }

  // ============================================================
  // Graph construction
  // ============================================================
  function nodeColorByType(typeStr) {
    switch (String(typeStr)) {
      case "0": return 0x6b7280; // boundary
      case "1": return 0x22c55e; // Z spider
      case "2": return 0xef4444; // X spider
      default:  return 0x06b6d4; // unknown
    }
  }


function makeEdges(edges, positions, group) {
  // visual style – same blue hue as before
  const edgeColor = 0x3b82f6;
  const edgeRadius = 0.06; // controls thickness

  edges.forEach(([a, b]) => {
    const pa = positions.get(a);
    const pb = positions.get(b);
    if (!pa || !pb) return;

    // compute midpoint, length, and orientation
    const dir = new THREE.Vector3().subVectors(pb, pa);
    const len = dir.length();
    const mid = new THREE.Vector3().addVectors(pa, pb).multiplyScalar(0.5);

    // geometry & material
    const geom = new THREE.CylinderGeometry(edgeRadius, edgeRadius, len, 8, 1);
    const mat = new THREE.MeshStandardMaterial({
      color: edgeColor,
      transparent: true,
      opacity: 0.85,
      metalness: 0.4,
      roughness: 0.25,
      emissive: new THREE.Color(0x1d4ed8), // faint glow
      emissiveIntensity: 0.25
    });

    const cyl = new THREE.Mesh(geom, mat);
    cyl.position.copy(mid);
    cyl.quaternion.setFromUnitVectors(
      new THREE.Vector3(0, 1, 0),
      dir.clone().normalize()
    );

    group.add(cyl);
  });
}


  function buildGraph(zxGraph, mbqc) {
    nodesGroup.clear();
    edgesGroup.clear();

    const verts = zxGraph.vertices || [];
    const edges = zxGraph.edges || [];
    const vById = new Map();
    verts.forEach(v => vById.set(v.id, v));

    // derive measurement order
    order = (mbqc && Array.isArray(mbqc.order)) ? mbqc.order.slice() : verts.map(v => v.id);
    const orderIndex = new Map(order.map((v,i)=>[v,i]));

    // compute positions
    const positions = new Map();
    verts.forEach((v,i)=>{
      const x = typeof v.qubit === "number" ? v.qubit : i;
      const z = typeof v.row === "number" ? v.row : (orderIndex.get(v.id) ?? 0);
      positions.set(v.id, new THREE.Vector3(x*2.0, 0, z*1.2));
    });

    // edges
    makeEdges(edges, positions, edgesGroup);  
    // nodes
    verts.forEach(v=>{
      const p=positions.get(v.id);
      const color=nodeColorByType(v.type);
      const geom=new THREE.SphereGeometry(0.4,24,24);
      const mat=new THREE.MeshStandardMaterial({color,metalness:0.2,roughness:0.4});
      const mesh=new THREE.Mesh(geom,mat);
      mesh.position.copy(p);
      mesh.userData={id:v.id};
      nodesGroup.add(mesh);
      const label=makeLabel(`#${v.id}`);
      label.position.copy(p.clone().add(new THREE.Vector3(0,0.9,0)));
      nodesGroup.add(label);
    });

    // measurement labels
    if(mbqc && Array.isArray(mbqc.measurements)){
      mbqc.measurements.forEach(m=>{
        const p=positions.get(m.v);
        if(!p) return;
        const label=makeLabel(`${m.basis}${m.angle?`:${m.angle.toFixed(2)}`:""}`,10,"#9ca3af");
        label.position.copy(p.clone().add(new THREE.Vector3(0,-0.9,0)));
        nodesGroup.add(label);
      });
    }

    centerCamera(positions);
  }

  function centerCamera(positions) {
    let minX=+Infinity,maxX=-Infinity,minZ=+Infinity,maxZ=-Infinity;
    positions.forEach(p=>{
      minX=Math.min(minX,p.x); maxX=Math.max(maxX,p.x);
      minZ=Math.min(minZ,p.z); maxZ=Math.max(maxZ,p.z);
    });
    const cx=(minX+maxX)/2, cz=(minZ+maxZ)/2;
    controls.target.set(cx,0,cz);
    camera.position.set(cx+6,8,cz+14);
    controls.update();
  }

function makeLabel(text, fontSize = 10, color = "#e6edf3") {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  const pad = 6;

  ctx.font = `${fontSize}px monospace`;
  const w = ctx.measureText(text).width + pad * 2;
  const h = fontSize + pad * 2;

  canvas.width = w * 2;
  canvas.height = h * 2;
  ctx.scale(2, 2);

  ctx.font = `${fontSize}px monospace`;
  ctx.fillStyle = "rgba(11,15,20,0.5)"; // lighter background
  ctx.fillRect(0, 0, w, h);
  ctx.fillStyle = color;
  ctx.fillText(text, pad, pad + fontSize * 0.8);

  const tex = new THREE.CanvasTexture(canvas);
  tex.needsUpdate = true;

  const mat = new THREE.SpriteMaterial({
    map: tex,
    transparent: true,
    opacity: 0.75,
    depthWrite: false
  });
  const sprite = new THREE.Sprite(mat);

  // smaller overall scale
  const scale = 0.5;
  sprite.scale.set((w / 20) * scale, (h / 20) * scale, 1);
  return sprite;
}


  function highlightNode(nodeId){
    nodesGroup.children.forEach(obj=>{
      if(!(obj instanceof THREE.Mesh)) return;
      if(obj.userData.id===nodeId){
        obj.material.emissive=new THREE.Color(0xfbbf24);
        obj.material.emissiveIntensity=0.8;
        obj.scale.set(1.2,1.2,1.2);
      } else {
        obj.material.emissive=new THREE.Color(0x000000);
        obj.material.emissiveIntensity=0.0;
        obj.scale.set(1.0,1.0,1.0);
      }
    });
  }

  // ============================================================
  // API call
  // ============================================================
  async function compileAndRender(qasmText) {
    const payload = { src: btoa(unescape(encodeURIComponent(qasmText))), output: "all" };
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    buildGraph(data.zx_graph, data.mbqc_pattern);
  }

  initThree();
  return { compileAndRender };
}

