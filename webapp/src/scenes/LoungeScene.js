import * as THREE from 'three';
import { Api } from '../api.js';
import { Haptic } from '../haptic.js';
import { Sound } from '../sound.js';

export class LoungeScene {
  constructor(container, profile) {
    this.container = container;
    this.profile = profile || {};
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 50);
    this.camera.position.set(0, 0, 6.5);

    this.loungeGroup = new THREE.Group();
    this.scene.add(this.loungeGroup);

    this.clock = new THREE.Clock();
    this.leverPulled = false;
    this.leverMesh = null;
    this.isRescueActive = false;
    this.rescueTimer = 0;
    this.rescueFlashLight = null;

    this.setupLighting();
    this.createLoungeAndLever();
    this.setupInteractions();
  }

  setupLighting() {
    const ambient = new THREE.AmbientLight(0x281914, 1.6);
    this.scene.add(ambient);

    // Warm fireplace glow
    this.fireLight = new THREE.PointLight(0xff6622, 2.5, 12);
    this.fireLight.position.set(-2, 1, 3);
    this.scene.add(this.fireLight);

    // Emergency Courtyard Light (normally off, flashes on rescue)
    this.rescueFlashLight = new THREE.DirectionalLight(0xffffff, 0);
    this.rescueFlashLight.position.set(0, 4, 6);
    this.scene.add(this.rescueFlashLight);
  }

  createLoungeAndLever() {
    // 1. VIP Lounge Panel Background
    const panelGeo = new THREE.BoxGeometry(4.0, 3.2, 0.3);
    const panelMat = new THREE.MeshStandardMaterial({
      color: 0x1a1210,
      roughness: 0.7
    });
    const panel = new THREE.Mesh(panelGeo, panelMat);
    this.loungeGroup.add(panel);

    // Title Plaque ("پناهگاه امن سالن VIP — بلوندهای بی‌گناه")
    const titleCanvas = document.createElement('canvas');
    titleCanvas.width = 512;
    titleCanvas.height = 140;
    const tctx = titleCanvas.getContext('2d');
    tctx.fillStyle = '#140c0a';
    tctx.fillRect(0, 0, 512, 140);
    tctx.strokeStyle = '#d4af50';
    tctx.lineWidth = 3;
    tctx.strokeRect(8, 8, 496, 124);

    tctx.font = 'bold 32px Vazirmatn, sans-serif';
    tctx.fillStyle = '#ff7da5';
    tctx.textAlign = 'center';
    tctx.fillText('🥂 سالن امن VIP و پناهگاه عمارت', 256, 52);
    tctx.font = '24px Vazirmatn, sans-serif';
    tctx.fillStyle = '#d4af50';
    tctx.fillText('اهرم اضطراری: کنترل نور حیات باغ', 256, 100);

    const titleTex = new THREE.CanvasTexture(titleCanvas);
    const titleMesh = new THREE.Mesh(
      new THREE.PlaneGeometry(3.2, 0.9),
      new THREE.MeshBasicMaterial({ map: titleTex })
    );
    titleMesh.position.set(0, 1.0, 0.18);
    this.loungeGroup.add(titleMesh);

    // 2. Mechanical Industrial Lever Base
    const boxGeo = new THREE.BoxGeometry(1.6, 1.4, 0.4);
    const boxMat = new THREE.MeshStandardMaterial({
      color: 0x241c18,
      metalness: 0.8,
      roughness: 0.3
    });
    const leverBox = new THREE.Mesh(boxGeo, boxMat);
    leverBox.position.set(0, -0.4, 0.2);
    this.loungeGroup.add(leverBox);

    // Lever Slot
    const slotGeo = new THREE.BoxGeometry(0.2, 1.0, 0.05);
    const slotMat = new THREE.MeshBasicMaterial({ color: 0x050403 });
    const slot = new THREE.Mesh(slotGeo, slotMat);
    slot.position.set(0, -0.4, 0.41);
    this.loungeGroup.add(slot);

    // 3. Heavy Brass Mechanical Lever Arm
    this.leverPivot = new THREE.Group();
    this.leverPivot.position.set(0, -0.7, 0.38);
    this.loungeGroup.add(this.leverPivot);

    const armGeo = new THREE.CylinderGeometry(0.04, 0.05, 0.85, 12);
    const armMat = new THREE.MeshStandardMaterial({
      color: 0xd4af50,
      metalness: 0.9,
      roughness: 0.2
    });
    const arm = new THREE.Mesh(armGeo, armMat);
    arm.position.y = 0.42;
    this.leverPivot.add(arm);

    // Big Red Knob Handle
    const knobGeo = new THREE.SphereGeometry(0.14, 16, 16);
    const knobMat = new THREE.MeshStandardMaterial({
      color: 0xcc2222,
      roughness: 0.3,
      metalness: 0.1
    });
    const knob = new THREE.Mesh(knobGeo, knobMat);
    knob.position.y = 0.85;
    this.leverPivot.add(knob);

    // Lever resting rotation (Upright ~ -0.4 rad)
    this.leverPivot.rotation.x = -0.4;

    // Status Message Banner
    const statCanvas = document.createElement('canvas');
    statCanvas.width = 512;
    statCanvas.height = 90;
    this.statCtx = statCanvas.getContext('2d');
    this.updateStatusBanner('لمس اهرم برای روشن کردن نور حیات باغ (۱۰ ثانیه)');

    this.statTex = new THREE.CanvasTexture(statCanvas);
    const statMesh = new THREE.Mesh(
      new THREE.PlaneGeometry(2.8, 0.5),
      new THREE.MeshBasicMaterial({ map: this.statTex })
    );
    statMesh.position.set(0, -1.3, 0.2);
    this.loungeGroup.add(statMesh);
  }

  updateStatusBanner(text, isError = false) {
    if (!this.statCtx) return;
    this.statCtx.fillStyle = '#140c0a';
    this.statCtx.fillRect(0, 0, 512, 90);
    this.statCtx.font = 'bold 24px Vazirmatn, sans-serif';
    this.statCtx.fillStyle = isError ? '#ff4444' : '#e0d8cc';
    this.statCtx.textAlign = 'center';
    this.statCtx.fillText(text, 256, 52);
    if (this.statTex) this.statTex.needsUpdate = true;
  }

  setupInteractions() {
    window.addEventListener('pointerdown', async (e) => {
      const raycaster = new THREE.Raycaster();
      const mouse = new THREE.Vector2(
        (e.clientX / window.innerWidth) * 2 - 1,
        -(e.clientY / window.innerHeight) * 2 + 1
      );
      raycaster.setFromCamera(mouse, this.camera);
      const intersects = raycaster.intersectObjects(this.loungeGroup.children, true);

      if (intersects.length > 0 && !this.isRescueActive) {
        await this.pullLever();
      }
    });
  }

  async pullLever() {
    this.isRescueActive = true;
    Sound.playMechanicalClick();
    Haptic.impact('heavy');

    // Pull down animation
    this.leverPivot.rotation.x = 0.5;

    this.updateStatusBanner('💡 نور حیات باغ به مدت ده ثانیه روشن میشود...');

    try {
      await Api.triggerRescue();
    } catch (e) {
      // In case limit reached or error
      if (String(e).includes('حداکثر')) {
        this.updateStatusBanner('⚠️ سقف ۳ بار روشن کردن نور پر شده است!', true);
      }
    }

    // Flash lights for 10 seconds
    this.rescueTimer = 10.0;
  }

  update() {
    const time = this.clock.getElapsedTime();

    // Fireplace flicker
    if (this.fireLight) {
      this.fireLight.intensity = 2.4 + Math.sin(time * 12) * 0.25 + Math.cos(time * 26) * 0.15;
    }

    // Courtyard Rescue Lighting Countdown
    if (this.rescueTimer > 0) {
      this.rescueTimer -= 0.016;
      this.rescueFlashLight.intensity = 3.5 + Math.sin(time * 20) * 0.5;

      if (this.rescueTimer <= 0) {
        this.rescueFlashLight.intensity = 0;
        this.leverPivot.rotation.x = -0.4; // return lever
        this.isRescueActive = false;
        this.updateStatusBanner('نور خاموش شد. آماده برای فعال‌سازی مجدد.');
      }
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
