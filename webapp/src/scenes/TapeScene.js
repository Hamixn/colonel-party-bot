import * as THREE from 'three';
import { Sound } from '../sound.js';
import { Haptic } from '../haptic.js';

export class TapeScene {
  constructor(container) {
    this.container = container;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
    this.camera.position.set(0, 0, 6.5);

    this.tapeGroup = new THREE.Group();
    this.scene.add(this.tapeGroup);

    this.isPlaying = false;
    this.reelSpeed = 0;
    this.vuNeedle = null;
    this.playBtnMesh = null;
    this.playBtnOriginalY = 0;

    this.clock = new THREE.Clock();

    this.setupLighting();
    this.createTapeDeck();
    this.setupInteractions();
  }

  setupLighting() {
    const ambient = new THREE.AmbientLight(0x221a24, 1.5);
    this.scene.add(ambient);

    // Warm desk spotlight
    const spot = new THREE.SpotLight(0xffddaa, 3, 15, Math.PI / 4, 0.4);
    spot.position.set(0, 4, 5);
    this.scene.add(spot);

    // Greenish vintage VU meter light
    const vuLight = new THREE.PointLight(0xffb84d, 1.2, 3);
    vuLight.position.set(1.2, 0.9, 0.5);
    this.scene.add(vuLight);
  }

  createTapeDeck() {
    // 1. Main Chassis (Dark brushed retro metal)
    const chassisGeo = new THREE.BoxGeometry(4.2, 3.2, 0.6);
    const chassisMat = new THREE.MeshStandardMaterial({
      color: 0x18141c,
      roughness: 0.6,
      metalness: 0.8
    });
    const chassis = new THREE.Mesh(chassisGeo, chassisMat);
    this.tapeGroup.add(chassis);

    // Front faceplate (brushed aluminum vintage border)
    const plateGeo = new THREE.BoxGeometry(3.9, 2.9, 0.04);
    const plateMat = new THREE.MeshStandardMaterial({
      color: 0x28232c,
      roughness: 0.4,
      metalness: 0.6
    });
    const plate = new THREE.Mesh(plateGeo, plateMat);
    plate.position.z = 0.31;
    this.tapeGroup.add(plate);

    // 2. Cassette Compartment Inset
    const bayGeo = new THREE.BoxGeometry(2.6, 1.6, 0.12);
    const bayMat = new THREE.MeshStandardMaterial({
      color: 0x0a080d,
      roughness: 0.8
    });
    const bay = new THREE.Mesh(bayGeo, bayMat);
    bay.position.set(-0.5, 0.2, 0.33);
    this.tapeGroup.add(bay);

    // Cassette Tape Body (Vintage cream plastic with label)
    const casGeo = new THREE.BoxGeometry(2.3, 1.4, 0.08);
    const casMat = new THREE.MeshStandardMaterial({
      color: 0x1e1822,
      roughness: 0.5
    });
    const cassette = new THREE.Mesh(casGeo, casMat);
    cassette.position.set(-0.5, 0.2, 0.38);
    this.tapeGroup.add(cassette);

    // Cassette Label ("نوار شماره ۷ سرهنگ — آبان ۱۳۵۶")
    const labelCanvas = document.createElement('canvas');
    labelCanvas.width = 512;
    labelCanvas.height = 128;
    const lctx = labelCanvas.getContext('2d');
    lctx.fillStyle = '#f0e6d2';
    lctx.fillRect(0, 0, 512, 128);
    lctx.fillStyle = '#8a202a';
    lctx.fillRect(0, 0, 512, 16);
    lctx.fillRect(0, 112, 512, 16);
    lctx.font = 'bold 28px sans-serif';
    lctx.fillStyle = '#111';
    lctx.textAlign = 'center';
    lctx.fillText('COLONEL ARCHIVE #7 - 1356', 256, 56);
    lctx.font = '22px sans-serif';
    lctx.fillStyle = '#444';
    lctx.fillText('پاییز ۱۳۵۶ — باغ صدرا', 256, 92);

    const labelTex = new THREE.CanvasTexture(labelCanvas);
    const labelMat = new THREE.MeshBasicMaterial({ map: labelTex });
    const labelMesh = new THREE.Mesh(new THREE.PlaneGeometry(1.8, 0.6), labelMat);
    labelMesh.position.set(-0.5, 0.45, 0.43);
    this.tapeGroup.add(labelMesh);

    // 3. Dual Spinning Reels
    const reelGeo = new THREE.CylinderGeometry(0.36, 0.36, 0.08, 16);
    const reelMat = new THREE.MeshStandardMaterial({
      color: 0xd4af50,
      metalness: 0.9,
      roughness: 0.2
    });

    this.leftReel = new THREE.Mesh(reelGeo, reelMat);
    this.leftReel.rotation.x = Math.PI / 2;
    this.leftReel.position.set(-1.05, 0.05, 0.43);
    this.tapeGroup.add(this.leftReel);

    this.rightReel = new THREE.Mesh(reelGeo, reelMat);
    this.rightReel.rotation.x = Math.PI / 2;
    this.rightReel.position.set(0.05, 0.05, 0.43);
    this.tapeGroup.add(this.rightReel);

    // 4. Analog VU Meter Display
    const vuBoxGeo = new THREE.BoxGeometry(0.9, 0.8, 0.05);
    const vuBoxMat = new THREE.MeshStandardMaterial({
      color: 0x141016,
      roughness: 0.5
    });
    const vuBox = new THREE.Mesh(vuBoxGeo, vuBoxMat);
    vuBox.position.set(1.25, 0.5, 0.33);
    this.tapeGroup.add(vuBox);

    // VU Dial texture
    const vuCanvas = document.createElement('canvas');
    vuCanvas.width = 256;
    vuCanvas.height = 200;
    const vuCtx = vuCanvas.getContext('2d');
    vuCtx.fillStyle = '#fffae0';
    vuCtx.fillRect(0, 0, 256, 200);
    vuCtx.strokeStyle = '#333';
    vuCtx.lineWidth = 3;
    vuCtx.beginPath();
    vuCtx.arc(128, 220, 160, Math.PI * 1.2, Math.PI * 1.8);
    vuCtx.stroke();
    vuCtx.font = 'bold 18px sans-serif';
    vuCtx.fillStyle = '#8a202a';
    vuCtx.fillText('VU dB', 105, 50);

    const vuTex = new THREE.CanvasTexture(vuCanvas);
    const vuDial = new THREE.Mesh(new THREE.PlaneGeometry(0.8, 0.65), new THREE.MeshBasicMaterial({ map: vuTex }));
    vuDial.position.set(1.25, 0.5, 0.36);
    this.tapeGroup.add(vuDial);

    // VU Needle
    const needleGeo = new THREE.BoxGeometry(0.02, 0.45, 0.01);
    const needleMat = new THREE.MeshBasicMaterial({ color: 0xcc2222 });
    this.vuNeedle = new THREE.Mesh(needleGeo, needleMat);
    // Pivot at bottom
    this.vuNeedle.geometry.translate(0, 0.22, 0);
    this.vuNeedle.position.set(1.25, 0.28, 0.38);
    this.vuNeedle.rotation.z = 0.3; // resting angle
    this.tapeGroup.add(this.vuNeedle);

    // 5. Play / Stop Mechanical Button
    const btnGeo = new THREE.BoxGeometry(0.7, 0.35, 0.2);
    const btnMat = new THREE.MeshStandardMaterial({
      color: 0xd4af50,
      metalness: 0.8,
      roughness: 0.3
    });
    this.playBtnMesh = new THREE.Mesh(btnGeo, btnMat);
    this.playBtnOriginalY = -0.95;
    this.playBtnMesh.position.set(-0.5, this.playBtnOriginalY, 0.35);
    this.tapeGroup.add(this.playBtnMesh);

    // Status text on front
    const txtCanvas = document.createElement('canvas');
    txtCanvas.width = 512;
    txtCanvas.height = 90;
    const tctx = txtCanvas.getContext('2d');
    tctx.fillStyle = '#18141c';
    tctx.fillRect(0, 0, 512, 90);
    tctx.font = 'bold 36px Vazirmatn, sans-serif';
    tctx.fillStyle = '#d4af50';
    tctx.textAlign = 'center';
    tctx.fillText('▶️ لمس دکمه جهت پخش نوار سرهنگ', 256, 55);

    const txtMesh = new THREE.Mesh(
      new THREE.PlaneGeometry(2.4, 0.45),
      new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(txtCanvas) })
    );
    txtMesh.position.set(0, -1.3, 0.32);
    this.tapeGroup.add(txtMesh);
  }

  setupInteractions() {
    window.addEventListener('pointerdown', (e) => {
      // Raycast to check if clicked on tape deck or play button
      const raycaster = new THREE.Raycaster();
      const mouse = new THREE.Vector2(
        (e.clientX / window.innerWidth) * 2 - 1,
        -(e.clientY / window.innerHeight) * 2 + 1
      );
      raycaster.setFromCamera(mouse, this.camera);
      const intersects = raycaster.intersectObjects(this.tapeGroup.children, true);

      if (intersects.length > 0) {
        this.togglePlay();
      }
    });
  }

  togglePlay() {
    Sound.playMechanicalClick();
    Haptic.impact('heavy');

    this.isPlaying = Sound.toggleTape('./audio/welcome_narration.mp3');

    // Mechanical button press animation
    this.playBtnMesh.position.y = this.isPlaying
      ? this.playBtnOriginalY - 0.08
      : this.playBtnOriginalY;

    if (this.isPlaying) {
      Haptic.heartbeat();
    }
  }

  update() {
    const time = this.clock.getElapsedTime();

    // Subtle breathing rotation
    this.tapeGroup.rotation.y = Math.sin(time * 0.8) * 0.08;
    this.tapeGroup.rotation.x = Math.sin(time * 0.5) * 0.04;

    // Spin reels if playing
    if (this.isPlaying) {
      this.reelSpeed = THREE.MathUtils.lerp(this.reelSpeed, 4.5, 0.1);
      this.leftReel.rotation.z -= this.reelSpeed * 0.016;
      this.rightReel.rotation.z -= this.reelSpeed * 0.016;

      // React needle to real audio level
      const level = Sound.getAudioLevel();
      // needle angle from 0.4 (left) to -0.6 (right)
      const targetAngle = 0.4 - (level * 1.1) + (Math.sin(time * 30) * 0.05);
      this.vuNeedle.rotation.z = THREE.MathUtils.lerp(this.vuNeedle.rotation.z, targetAngle, 0.25);
    } else {
      this.reelSpeed = THREE.MathUtils.lerp(this.reelSpeed, 0, 0.05);
      this.vuNeedle.rotation.z = THREE.MathUtils.lerp(this.vuNeedle.rotation.z, 0.4, 0.1);
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
