import * as THREE from 'three';
import { Haptic } from '../haptic.js';

export class CardScene {
  constructor(container, profile) {
    this.container = container;
    this.profile = profile || {};
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
    this.camera.position.set(0, 0, 7.5);

    this.cardGroup = new THREE.Group();
    this.scene.add(this.cardGroup);

    this.targetRotation = { x: 0, y: 0 };
    this.currentRotation = { x: 0, y: 0 };
    this.isFlipped = false;
    this.flipProgress = 0; // 0 to Math.PI

    this.candleLight = null;
    this.clock = new THREE.Clock();

    this.setupLighting();
    this.create3DCard();
    this.setupInteractions();
  }

  setupLighting() {
    const ambient = new THREE.AmbientLight(0x2a1835, 1.2);
    this.scene.add(ambient);

    // Warm candle point light
    this.candleLight = new THREE.PointLight(0xffaa44, 2.5, 15);
    this.candleLight.position.set(2.5, 2.5, 4);
    this.scene.add(this.candleLight);

    // Subtle rim light
    const rimLight = new THREE.DirectionalLight(0x8844ff, 0.8);
    rimLight.position.set(-4, -2, -2);
    this.scene.add(rimLight);
  }

  createCardCanvas(isBack = false) {
    const canvas = document.createElement('canvas');
    canvas.width = 1024;
    canvas.height = 1350;
    const ctx = canvas.getContext('2d');

    // Background gradient
    const grad = ctx.createLinearGradient(0, 0, 0, 1350);
    if (!isBack) {
      grad.addColorStop(0, '#1a101b');
      grad.addColorStop(0.5, '#0e0811');
      grad.addColorStop(1, '#050306');
    } else {
      grad.addColorStop(0, '#140b17');
      grad.addColorStop(0.5, '#0a050d');
      grad.addColorStop(1, '#050207');
    }
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 1024, 1350);

    // Gothic border
    ctx.strokeStyle = '#d4af50';
    ctx.lineWidth = 6;
    ctx.strokeRect(36, 36, 1024 - 72, 1350 - 72);

    ctx.strokeStyle = '#8a202a';
    ctx.lineWidth = 2;
    ctx.strokeRect(52, 52, 1024 - 104, 1350 - 104);

    // Corner ornaments
    const corners = [[36, 36], [1024 - 36, 36], [36, 1350 - 36], [1024 - 36, 1350 - 36]];
    ctx.fillStyle = '#d4af50';
    corners.forEach(([x, y]) => {
      ctx.beginPath();
      ctx.arc(x, y, 12, 0, Math.PI * 2);
      ctx.fill();
    });

    ctx.textAlign = 'center';
    ctx.direction = 'rtl';

    if (!isBack) {
      // FRONT OF CARD
      ctx.font = 'bold 36px Vazirmatn, sans-serif';
      ctx.fillStyle = '#b0a8b5';
      ctx.fillText('PROJECT BLACKOUT', 512, 160);

      ctx.font = 'bold 54px Vazirmatn, sans-serif';
      ctx.fillStyle = '#d4af50';
      ctx.fillText('مهمانی باغ سرهنگ', 512, 240);

      // Divider line
      ctx.strokeStyle = '#d4af50';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(300, 280);
      ctx.lineTo(724, 280);
      ctx.stroke();

      // Guest Name Badge
      ctx.fillStyle = 'rgba(212, 175, 80, 0.12)';
      ctx.strokeStyle = '#d4af50';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.roundRect(160, 360, 704, 130, 20);
      ctx.fill();
      ctx.stroke();

      ctx.font = 'bold 64px Vazirmatn, sans-serif';
      ctx.fillStyle = '#ffffff';
      ctx.fillText(this.profile.full_name || 'مهمان ویژه', 512, 445);

      // Role Section
      const isPlayer = this.profile.role !== 'role_blonde';
      ctx.font = 'bold 44px Vazirmatn, sans-serif';
      ctx.fillStyle = isPlayer ? '#eb2d2d' : '#ff7da5';
      ctx.fillText(isPlayer ? 'نقش: بازیکن طلسم و بقا' : 'نقش: بلوند بی‌گناه (حاشیه امن)', 512, 590);

      ctx.font = 'bold 30px Vazirmatn, sans-serif';
      ctx.fillStyle = '#a098a5';
      ctx.fillText(isPlayer ? "THE HUNTER'S PREY" : 'SAFE ZONE VIP', 512, 645);

      // Soul ID Pill
      const serial = this.profile.serial_number || 1;
      ctx.fillStyle = '#1b1220';
      ctx.strokeStyle = '#8a202a';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.roundRect(312, 730, 400, 75, 16);
      ctx.fill();
      ctx.stroke();

      ctx.font = 'bold 36px Vazirmatn, sans-serif';
      ctx.fillStyle = '#d4af50';
      ctx.fillText(`SOUL - #${String(serial).padStart(2, '0')}`, 512, 782);

      // Transport Status
      ctx.font = '28px Vazirmatn, sans-serif';
      ctx.fillStyle = '#d0c8d8';
      const carText = this.profile.has_car === 1
        ? `🚗 راننده خودروی شماره ${this.profile.car_number || 1}`
        : `🚶 همسفر خودروی شماره ${this.profile.car_number || 1}`;
      ctx.fillText(carText, 512, 880);

      // Instructions hint
      ctx.font = '24px Vazirmatn, sans-serif';
      ctx.fillStyle = '#b08a30';
      ctx.fillText('پنجشنبه ۷ آبان ۱۳۵۶ — ساعت ۱۷:۳۰ ورودی صدرا', 512, 1020);

      ctx.font = 'bold 22px Vazirmatn, sans-serif';
      ctx.fillStyle = '#7a7082';
      ctx.fillText('(برای مشاهده کد رمز و پشت کارت، روی کارت ضربه بزنید)', 512, 1200);

    } else {
      // BACK OF CARD
      ctx.font = 'bold 46px Vazirmatn, sans-serif';
      ctx.fillStyle = '#d4af50';
      ctx.fillText('پرونده‌ی سری و محرمانه', 512, 160);

      // Soul PIN Code (Big Mysterious Box)
      ctx.fillStyle = '#1c0f14';
      ctx.strokeStyle = '#d4af50';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.roundRect(240, 260, 544, 180, 24);
      ctx.fill();
      ctx.stroke();

      ctx.font = '30px Vazirmatn, sans-serif';
      ctx.fillStyle = '#b0a8b5';
      ctx.fillText('کد رمز ۳ رقمی روح شما:', 512, 320);

      ctx.font = 'bold 72px Vazirmatn, sans-serif';
      ctx.fillStyle = '#ff3344';
      ctx.fillText(this.profile.soul_pin || '210', 512, 405);

      // Warning
      ctx.font = '26px Vazirmatn, sans-serif';
      ctx.fillStyle = '#e09090';
      ctx.fillText('⚠️ این کد را از ۵ تسخیرشده پنهان نگه دارید!', 512, 490);

      // Carpool & Convoy Info
      ctx.fillStyle = 'rgba(212, 175, 80, 0.08)';
      ctx.strokeStyle = 'rgba(212, 175, 80, 0.3)';
      ctx.beginPath();
      ctx.roundRect(140, 560, 744, 300, 20);
      ctx.fill();
      ctx.stroke();

      ctx.font = 'bold 32px Vazirmatn, sans-serif';
      ctx.fillStyle = '#d4af50';
      ctx.fillText('🚗 مشخصات کاروان صدرا (۱۳ خودرو)', 512, 620);

      ctx.font = '28px Vazirmatn, sans-serif';
      ctx.fillStyle = '#ffffff';
      ctx.fillText(`خودروی شماره: ${this.profile.car_number || 1}`, 512, 680);

      const driverContact = this.profile.driver_contact || this.profile.driver_name || 'در حال تعیین';
      ctx.fillText(`راننده: ${driverContact}`, 512, 740);

      ctx.font = '24px Vazirmatn, sans-serif';
      ctx.fillStyle = '#b0a8b5';
      ctx.fillText('حرکت رأس ساعت ۱۷:۳۰ از ورودی صدرا', 512, 805);

      // Gate locking notice
      ctx.font = 'bold 24px Vazirmatn, sans-serif';
      ctx.fillStyle = '#eb2d2d';
      ctx.fillText('⛔️ دروازه عمارت از ۱۸:۱۵ تا ۲۴:۰۰ قفل مطلق است!', 512, 940);

      ctx.font = '22px Vazirmatn, sans-serif';
      ctx.fillStyle = '#7a7082';
      ctx.fillText('(برای بازگشت به روی کارت، دوباره لمس کنید)', 512, 1200);
    }

    return canvas;
  }

  create3DCard() {
    const width = 3.2;
    const height = 4.2;
    const thickness = 0.04;

    const geometry = new THREE.BoxGeometry(width, height, thickness);

    const frontTexture = new THREE.CanvasTexture(this.createCardCanvas(false));
    frontTexture.colorSpace = THREE.SRGBColorSpace;

    const backTexture = new THREE.CanvasTexture(this.createCardCanvas(true));
    backTexture.colorSpace = THREE.SRGBColorSpace;

    // Materials: Gold edges, textured front and back
    const edgeMaterial = new THREE.MeshStandardMaterial({
      color: 0xd4af50,
      metalness: 0.85,
      roughness: 0.25
    });

    const frontMaterial = new THREE.MeshStandardMaterial({
      map: frontTexture,
      roughness: 0.4,
      metalness: 0.15
    });

    const backMaterial = new THREE.MeshStandardMaterial({
      map: backTexture,
      roughness: 0.4,
      metalness: 0.15
    });

    // Box materials array: right, left, top, bottom, front, back
    const materials = [
      edgeMaterial,
      edgeMaterial,
      edgeMaterial,
      edgeMaterial,
      frontMaterial,
      backMaterial
    ];

    this.cardMesh = new THREE.Mesh(geometry, materials);
    this.cardGroup.add(this.cardMesh);
  }

  setupInteractions() {
    let isDragging = false;
    let prevMouse = { x: 0, y: 0 };

    const onPointerDown = (e) => {
      isDragging = true;
      prevMouse = { x: e.clientX, y: e.clientY };
    };

    const onPointerMove = (e) => {
      if (!isDragging) {
        // Subtle tilt on hover
        const normX = (e.clientX / window.innerWidth) * 2 - 1;
        const normY = -(e.clientY / window.innerHeight) * 2 + 1;
        this.targetRotation.y = normX * 0.35 + (this.isFlipped ? Math.PI : 0);
        this.targetRotation.x = -normY * 0.25;
        return;
      }
      const deltaX = e.clientX - prevMouse.x;
      const deltaY = e.clientY - prevMouse.y;
      prevMouse = { x: e.clientX, y: e.clientY };

      this.targetRotation.y += deltaX * 0.01;
      this.targetRotation.x += deltaY * 0.01;
      this.targetRotation.x = Math.max(-0.6, Math.min(0.6, this.targetRotation.x));
    };

    const onPointerUp = (e) => {
      isDragging = false;
    };

    // Click / Tap to flip card
    let startPos = { x: 0, y: 0 };
    window.addEventListener('pointerdown', (e) => {
      startPos = { x: e.clientX, y: e.clientY };
    });

    window.addEventListener('pointerup', (e) => {
      const dist = Math.hypot(e.clientX - startPos.x, e.clientY - startPos.y);
      if (dist < 10) {
        // Pure tap - toggle flip!
        this.toggleFlip();
      }
    });

    window.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);

    // Device Orientation (Gyroscope)
    window.addEventListener('deviceorientation', (e) => {
      if (e.gamma !== null && e.beta !== null) {
        const tiltX = (e.beta - 45) * 0.012; // Beta - forward/backward tilt
        const tiltY = e.gamma * 0.015;        // Gamma - left/right tilt

        this.targetRotation.x = Math.max(-0.5, Math.min(0.5, tiltX));
        this.targetRotation.y = (this.isFlipped ? Math.PI : 0) + Math.max(-0.7, Math.min(0.7, tiltY));
      }
    });
  }

  toggleFlip() {
    this.isFlipped = !this.isFlipped;
    Haptic.selection();
    this.targetRotation.y = this.isFlipped ? Math.PI : 0;
  }

  updateProfile(profile) {
    this.profile = profile;
    this.cardGroup.remove(this.cardMesh);
    this.create3DCard();
  }

  update() {
    const time = this.clock.getElapsedTime();

    // Smooth rotation lerp
    this.currentRotation.x += (this.targetRotation.x - this.currentRotation.x) * 0.08;
    this.currentRotation.y += (this.targetRotation.y - this.currentRotation.y) * 0.08;

    this.cardGroup.rotation.x = this.currentRotation.x;
    this.cardGroup.rotation.y = this.currentRotation.y;

    // Gentle floating breathing animation
    this.cardGroup.position.y = Math.sin(time * 1.5) * 0.06;

    // Candlelight flicker
    if (this.candleLight) {
      this.candleLight.intensity = 2.4 + Math.sin(time * 10) * 0.15 + Math.cos(time * 23) * 0.08;
      this.candleLight.position.x = 2.5 + Math.sin(time * 4) * 0.05;
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
