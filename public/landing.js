const revealItems = document.querySelectorAll(".reveal");
const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const markInitiallyVisible = () => {
  revealItems.forEach((item) => {
    const bounds = item.getBoundingClientRect();
    if (bounds.top < window.innerHeight * 0.92) {
      item.classList.add("is-visible");
    }
  });
};

if ("IntersectionObserver" in window) {
  markInitiallyVisible();
  document.documentElement.classList.add("js-enabled");

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
        }
      });
    },
    { threshold: 0.18 }
  );

  revealItems.forEach((item) => observer.observe(item));
}

const stage = document.querySelector(".hero-stage");
const tiltCard = document.querySelector(".tilt-card");

if (stage && tiltCard && !prefersReducedMotion) {
  stage.addEventListener("pointermove", (event) => {
    const bounds = stage.getBoundingClientRect();
    const x = (event.clientX - bounds.left) / bounds.width - 0.5;
    const y = (event.clientY - bounds.top) / bounds.height - 0.5;

    tiltCard.style.transform = `rotateX(${9 - y * 8}deg) rotateY(${-14 + x * 12}deg) rotateZ(2deg)`;
  });

  stage.addEventListener("pointerleave", () => {
    tiltCard.style.transform = "rotateX(9deg) rotateY(-14deg) rotateZ(2deg)";
  });
}

document.querySelector(".signup-form")?.addEventListener("submit", (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button");
  if (!button) return;

  button.textContent = "Demo request noted";
  button.disabled = true;
});

async function initWebGPUBackdrop() {
  const canvas = document.querySelector("#webgpu-backdrop");
  if (!canvas || prefersReducedMotion || !navigator.gpu) return;

  let renderer;
  let scene;
  let camera;

  try {
    const [THREE, tsl] = await Promise.all([
      import("https://esm.sh/three@0.183.0/webgpu"),
      import("https://esm.sh/three@0.183.0/tsl"),
    ]);

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(42, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(0, 0, 8.5);

    renderer = new THREE.WebGPURenderer({
      canvas,
      alpha: true,
      antialias: true,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
    renderer.setSize(window.innerWidth, window.innerHeight, false);

    await renderer.init();

    const ambient = new THREE.AmbientLight(0xb8ccff, 0.9);
    scene.add(ambient);

    const key = new THREE.DirectionalLight(0xffffff, 1.1);
    key.position.set(-2, 3, 4);
    scene.add(key);

    const tunnel = new THREE.Group();
    scene.add(tunnel);

    const ringGeometry = new THREE.TorusGeometry(2.1, 0.012, 12, 160);
    const ribbonGeometry = new THREE.TorusKnotGeometry(1.2, 0.011, 180, 8, 3, 7);
    const pulseGeometry = new THREE.IcosahedronGeometry(0.06, 2);

    const cyanMaterial = makePulseMaterial(THREE, tsl, 0x62e4ff, 0.48);
    const violetMaterial = makePulseMaterial(THREE, tsl, 0x9b6cff, 0.34);
    const stormMaterial = makePulseMaterial(THREE, tsl, 0x74f0b3, 0.42);

    for (let i = 0; i < 9; i += 1) {
      const ring = new THREE.Mesh(ringGeometry, i % 3 === 0 ? stormMaterial : i % 2 ? violetMaterial : cyanMaterial);
      ring.position.z = -i * 0.82;
      ring.rotation.x = Math.PI / 2.35;
      ring.rotation.y = i * 0.17;
      ring.scale.setScalar(1 + i * 0.105);
      tunnel.add(ring);
    }

    for (let i = 0; i < 4; i += 1) {
      const ribbon = new THREE.Mesh(ribbonGeometry, i % 2 ? violetMaterial : cyanMaterial);
      ribbon.position.set(i % 2 ? 1.6 : -1.7, i * 0.34 - 0.55, -1.4 - i * 0.7);
      ribbon.rotation.set(0.8 + i * 0.24, i * 0.7, 0.2);
      ribbon.scale.setScalar(0.82 + i * 0.12);
      tunnel.add(ribbon);
    }

    for (let i = 0; i < 36; i += 1) {
      const pulse = new THREE.Mesh(pulseGeometry, i % 2 ? stormMaterial : cyanMaterial);
      const angle = i * 0.72;
      const radius = 1.7 + Math.sin(i) * 0.34;
      pulse.position.set(Math.cos(angle) * radius, Math.sin(angle * 0.8) * 1.15, -0.12 * i);
      pulse.userData.speed = 0.18 + (i % 5) * 0.025;
      pulse.userData.phase = angle;
      tunnel.add(pulse);
    }

    const resize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
      renderer.setSize(window.innerWidth, window.innerHeight, false);
    };

    window.addEventListener("resize", resize);

    renderer.backend?.device?.lost?.then((info) => {
      console.warn("WebGPU device lost:", info.message);
      renderer.setAnimationLoop(null);
      canvas.classList.remove("is-ready");
      window.removeEventListener("resize", resize);
      renderer.dispose();
      if (info.reason === "unknown") {
        initWebGPUBackdrop();
      }
    });

    const clock = new THREE.Clock();
    canvas.classList.add("is-ready");

    const animate = () => {
      const elapsed = clock.getElapsedTime();
      tunnel.rotation.z = elapsed * 0.045;
      tunnel.rotation.y = Math.sin(elapsed * 0.17) * 0.16;

      tunnel.children.forEach((child, index) => {
        if (child.userData.speed) {
          child.position.z += child.userData.speed * 0.016;
          if (child.position.z > 1.2) child.position.z = -5.2;
          child.scale.setScalar(1 + Math.sin(elapsed * 2 + child.userData.phase) * 0.22);
        } else {
          child.rotation.z += 0.0018 + index * 0.00015;
        }
      });

      renderer.render(scene, camera);
    };

    renderer.setAnimationLoop(animate);
  } catch (error) {
    console.warn("WebGPU backdrop unavailable; using CSS fallback.", error);
    canvas.classList.remove("is-ready");
  }
}

function makePulseMaterial(THREE, tsl, hex, opacity) {
  const { color, normalWorld, oscSine, positionLocal, time } = tsl;
  const material = new THREE.MeshStandardNodeMaterial({
    transparent: true,
    opacity,
    roughness: 0.2,
    metalness: 0.1,
    depthWrite: false,
  });

  const shimmer = oscSine(time.mul(0.6).add(positionLocal.x.mul(1.7))).mul(0.34).add(0.74);
  material.colorNode = color(hex).mul(shimmer);
  material.emissiveNode = color(hex).mul(shimmer.mul(0.7));
  material.positionNode = positionLocal.add(
    normalWorld.mul(oscSine(time.mul(1.35).add(positionLocal.y.mul(2.4))).mul(0.035))
  );

  return material;
}

initWebGPUBackdrop();
