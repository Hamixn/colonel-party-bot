import * as THREE from 'three';
import { Haptic } from '../haptic.js';
import { Sound } from '../sound.js';

export class MidnightScene {
  constructor(container, profile) {
    this.container = container;
    this.profile = profile || {};
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0a0002);
    this.scene.fog = new THREE.FogExp2(0x1a0004, 0.15);

    this.camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 50);
    this.camera.position.set(0, 0, 5.5);

    this.lanternGroup = new THREE.Group();
    this.scene.add(this.lanternGroup);

    this.clock = new THREE.Clock();
    this.flameLight = null;
    this.swingVelocity = { x: 0, z: 0 };
    this.swingAngle = { x: 0, z: 0 };

    this.heartbeatTimer = 0;

    this.setupLighting();
    this.createRedLantern();
    this.createGardenEnvelopes();
    this.setupInteractions();
  }

  setupLighting() {
    // Pure monochrome red ambient
    const ambient = new THREE.AmbientLight(0x330005, 1.2);
    this.scene.add(ambient);

    // Dynamic red flame point light
    this.flameLight = new THREE.PointLight(0xff0022, 4.0, 12);
    this.flameLight.position.set(0, 0.1, 0);
    this.scene.add(this.flameLight);
  }

  createRedLantern() {
    // 1. Lantern Top Dome & Chimney (Aged Cast Iron)
    const capGeo = new THREE.CylinderGeometry(0.5, 0.9, 0.45, 16);
    const ironMat = new THREE.MeshStandardMaterial({
      color: 0x1a0508,
      metalness: 0.9,
      roughness: 0.5
    });
    const cap = new THREE.Mesh(capGeo, ironMat);
    cap.position.y = 1.35;
    this.lanternGroup.add(cap);

    // Hanging Loop / Handle
    const loopGeo = new THREE.TorusGeometry(0.35, 0.05, 8, 20);
    const loop = new THREE.Mesh(loopGeo, ironMat);
    loop.position.y = 1.8;
    this.lanternGroup.add(loop);

    // 2. Red Glass Cylinder (Translucent red safe-light)
    const glassGeo = new THREE.CylinderGeometry(0.85, 0.75, 1.6, 24, 1, true);
    const glassMat = new THREE.MeshPhysicalMaterial({
      color: 0xff0015,
      emissive: 0x66000a,
      roughness: 0.1,
      transmission: 0.85,
      thickness: 0.5,
      transparent: true,
      opacity: 0.85
    });
    const glass = new THREE.Mesh(glassGeo, glassMat);
    glass.position.y = 0.35;
    this.lanternGroup.add(glass);

    // 3. Protective Iron Wire Cage Ribs
    for (let i = 0; i < 6; i++) {
      const angle = (i / 6) * Math.PI * 2;
      const wireGeo = new THREE.CylinderGeometry(0.025, 0.025, 1.65, 8);
      const wire = new THREE.Mesh(wireGeo, ironMat);
      wire.position.set(Math.cos(angle) * 0.88, 0.35, Math.sin(angle) * 0.88);
      this.lanternGroup.add(wire);
    }

    // 4. Lantern Base Tank
    const baseGeo = new THREE.CylinderGeometry(0.85, 1.05, 0.6, 16);
    const base = new THREE.Mesh(baseGeo, ironMat);
    base.position.y = -0.7;
    this.lanternGroup.add(base);

    // 5. Red Flame Core (Volumetric glowing core)
    const flameGeo = new THREE.OctahedronGeometry(0.18, 2);
    const flameMat = new THREE.MeshBasicMaterial({
      color: 0xff4455
    });
    this.flameMesh = new THREE.Mesh(flameGeo, flameMat);
    this.flameMesh.position.y = 0.2;
    this.lanternGroup.add(this.flameMesh);

    // Instructions Banner under the lantern
    const bannerCanvas = document.createElement('canvas');
    bannerCanvas.width = 512;
    bannerCanvas.height = 120;
    const bctx = bannerCanvas.getContext('2d');
    bctx.fillStyle = '#100003';
    bctx.fillRect(0, 0, 512, 120);
    bctx.strokeStyle = '#ff0033';
    bctx.lineWidth = 3;
    bctx.strokeRect(10, 10, 492, 100);

    bctx.font = 'bold 30px Vazirmatn, sans-serif';
    bctx.fillStyle = '#ff3344';
    bctx.textAlign = 'center';
    bctx.fillText('🔴 تنها نور مجاز در تاریکی حیاط', 256, 52);
    bctx.font = '22px Vazirmatn, sans-serif';
    bctx.fillStyle = '#ff8899';
    bctx.fillText('برای ثبت رمز معما، روی صفحه ضربه بزنید', 256, 90);

    const bannerTex = new THREE.CanvasTexture(bannerCanvas);
    const bannerMesh = new THREE.Mesh(
      new THREE.PlaneGeometry(3.0, 0.7),
      new THREE.MeshBasicMaterial({ map: bannerTex })
    );
    bannerMesh.position.set(0, -1.6, 0.2);
    this.lanternGroup.add(bannerMesh);
  }

  createGardenEnvelopes() {
    // Represent the 2 team envelopes in the garden
    this.envelopesGroup = new THREE.Group();
    this.scene.add(this.envelopesGroup);

    const envGeo = new THREE.BoxGeometry(0.7, 0.45, 0.04);

    const r1Solved = this.profile.riddle_1_solved === 1;
    const r2Solved = this.profile.riddle_2_solved === 1;

    // Envelope 1
    const env1Mat = new THREE.MeshStandardMaterial({
      color: r1Solved ? 0x00ff66 : 0xcc1122,
      emissive: r1Solved ? 0x004411 : 0x550000,
      roughness: 0.3
    });
    const env1 = new THREE.Mesh(envGeo, env1Mat);
    env1.position.set(-1.8, 0.8, -1.5);
    env1.rotation.set(0.1, 0.3, -0.2);
    this.envelopesGroup.add(env1);

    // Envelope 2
    const env2Mat = new THREE.MeshStandardMaterial({
      color: r2Solved ? 0x00ff66 : 0xcc1122,
      emissive: r2Solved ? 0x004411 : 0x550000,
      roughness: 0.3
    });
    const env2 = new THREE.Mesh(envGeo, env2Mat);
    env2.position.set(1.8, 0.8, -1.5);
    env2.rotation.set(-0.1, -0.3, 0.2);
    this.envelopesGroup.add(env2);
  }

  setupInteractions() {
    // Accelerometer & Gyroscope swinging
    window.addEventListener('deviceorientation', (e) => {
      if (e.gamma !== null && e.beta !== null) {
        this.swingAngle.z = e.gamma * 0.02;
        this.swingAngle.x = (e.beta - 45) * 0.015;
      }
    });

    // Touch swipe swinging
    let prev = { x: 0, y: 0 };
    window.addEventListener('pointermove', (e) => {
      const dx = e.clientX - prev.x;
      const dy = e.clientY - prev.y;
      prev = { x: e.clientX, y: e.clientY };

      this.swingVelocity.z += dx * 0.0008;
      this.swingVelocity.x += dy * 0.0008;
    });

    // Tap to open Riddle Solve Modal
    window.addEventListener('pointerup', (e) => {
      if (Math.abs(this.swingVelocity.x) < 0.01) {
        this.openRiddleModal();
      }
    });
  }

  openRiddleModal() {
    Haptic.impact('medium');
    const modal = document.getElementById('modal-solve');
    if (modal) {
      modal.classList.add('visible');
      const input = document.getElementById('riddle-input');
      if (input) input.focus();
    }
  }

  update() {
    const time = this.clock.getElapsedTime();

    // Physics swinging lantern
    this.swingVelocity.x += (this.swingAngle.x - this.lanternGroup.rotation.x) * 0.04;
    this.swingVelocity.z += (this.swingAngle.z - this.lanternGroup.rotation.z) * 0.04;

    this.swingVelocity.x *= 0.94; // damping
    this.swingVelocity.z *= 0.94;

    this.lanternGroup.rotation.x += this.swingVelocity.x;
    this.lanternGroup.rotation.z += this.swingVelocity.z;

    // Red flame flicker
    if (this.flameLight) {
      const flicker = Math.sin(time * 18) * 0.3 + Math.cos(time * 29) * 0.2;
      this.flameLight.intensity = 3.6 + flicker;
      this.flameMesh.scale.setScalar(1.0 + flicker * 0.15);
    }

    // Periodic eerie heartbeat
    this.heartbeatTimer += 0.016;
    if (this.heartbeatTimer > 6.0) {
      this.heartbeatTimer = 0;
      Haptic.heartbeat();
    }
  }

  render(renderer) {
    this.update();
    renderer.render(this.scene, this.camera);
  }

  resize(width, height) {
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
  }
}
