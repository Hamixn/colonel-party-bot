import * as THREE from 'three';
import { Api } from './api.js';
import { Haptic } from './haptic.js';
import { Sound } from './sound.js';
import { CardScene } from './scenes/CardScene.js';
import { TapeScene } from './scenes/TapeScene.js';
import { MidnightScene } from './scenes/MidnightScene.js';
import { LoungeScene } from './scenes/LoungeScene.js';

class App {
  constructor() {
    this.container = document.getElementById('canvas-container');
    this.loader = document.getElementById('loader');
    this.nameDisplay = document.getElementById('guest-name-display');

    this.profile = null;
    this.activeSceneName = 'card';
    this.scenes = {};

    this.setupTelegramWebApp();
    this.setupThreeRenderer();
    this.setupUI();
    this.init();
  }

  setupTelegramWebApp() {
    if (window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp;
      tg.ready();
      tg.expand();
      try {
        tg.setHeaderColor('#050406');
        tg.setBackgroundColor('#050406');
      } catch (e) {}
    }
  }

  setupThreeRenderer() {
    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: 'high-performance'
    });
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.1;
    this.container.appendChild(this.renderer.domElement);

    window.addEventListener('resize', () => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      this.renderer.setSize(width, height);
      Object.values(this.scenes).forEach(s => s.resize && s.resize(width, height));
    });
  }

  setupUI() {
    // Sound toggle
    const btnSound = document.getElementById('btn-sound');
    btnSound.addEventListener('click', () => {
      const active = Sound.toggleMute();
      btnSound.textContent = active ? '🔊 صدا' : '🔇 صامت';
      Haptic.impact('light');
    });

    // Gyroscope permission request (for iOS)
    const btnGyro = document.getElementById('btn-gyro');
    btnGyro.addEventListener('click', async () => {
      Haptic.impact('light');
      if (typeof DeviceOrientationEvent !== 'undefined' && typeof DeviceOrientationEvent.requestPermission === 'function') {
        try {
          const perm = await DeviceOrientationEvent.requestPermission();
          if (perm === 'granted') {
            btnGyro.textContent = '✅ سنسور فعال';
          }
        } catch (e) {
          console.warn('Gyro permission rejected:', e);
        }
      } else {
        btnGyro.textContent = '✅ سنسور فعال';
      }
    });

    // Navigation Items
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
      item.addEventListener('click', () => {
        const sceneName = item.dataset.scene;
        this.switchScene(sceneName);
      });
    });

    // Riddle Modal controls
    const modalSolve = document.getElementById('modal-solve');
    const btnCloseSolve = document.getElementById('btn-close-solve');
    const btnSubmitRiddle = document.getElementById('btn-submit-riddle');
    const inputRiddle = document.getElementById('riddle-input');

    btnCloseSolve.addEventListener('click', () => {
      modalSolve.classList.remove('visible');
    });

    btnSubmitRiddle.addEventListener('click', async () => {
      const answer = inputRiddle.value.trim();
      if (!answer) return;

      btnSubmitRiddle.disabled = true;
      btnSubmitRiddle.textContent = 'در حال رمزگشایی...';

      try {
        const res = await Api.submitRiddle(answer);
        if (res.status === 'both_solved' || res.status === 'riddle_solved') {
          Haptic.notification('success');
          Sound.playUnlockChime();
          alert('🎉 معمای تیم با موفقیت حل شد!');
          modalSolve.classList.remove('visible');
        } else if (res.status === 'already_solved' || res.status === 'already_both_solved') {
          alert('این معما قبلاً توسط تیم شما حل شده است!');
          modalSolve.classList.remove('visible');
        } else {
          Haptic.jumpscare();
          alert('⚠️ پاسخ اشتباه است! صدای شکستن شاخه‌ها پخش شد... سرهنگ صدای شما را شنید!');
        }
      } catch (e) {
        alert('خطا در ثبت پاسخ: ' + e.message);
      } finally {
        btnSubmitRiddle.disabled = false;
        btnSubmitRiddle.textContent = 'ارسال رمز معما';
        inputRiddle.value = '';
      }
    });
  }

  async init() {
    try {
      this.profile = await Api.getProfile();
      this.nameDisplay.textContent = `${this.profile.full_name} (${this.profile.role === 'role_blonde' ? 'بلوند' : 'بازیکن'})`;
    } catch (e) {
      this.profile = Api.getMockProfile();
      this.nameDisplay.textContent = this.profile.full_name;
    }

    // Initialize Scenes
    this.scenes = {
      card: new CardScene(this.container, this.profile),
      tape: new TapeScene(this.container),
      midnight: new MidnightScene(this.container, this.profile),
      radar: new MidnightScene(this.container, this.profile),
      lounge: new LoungeScene(this.container, this.profile)
    };

    // Hide loader smoothly
    setTimeout(() => {
      this.loader.style.opacity = '0';
      setTimeout(() => this.loader.remove(), 500);
    }, 400);

    // Default Scene: If Blonde -> Lounge / Card; If Player -> Card
    this.switchScene('card');

    // Main animation loop
    this.animate();
  }

  switchScene(sceneName) {
    if (!this.scenes[sceneName]) return;
    this.activeSceneName = sceneName;
    Haptic.selection();

    // Update bottom nav highlighting
    document.querySelectorAll('.nav-item').forEach(item => {
      item.classList.toggle('active', item.dataset.scene === sceneName);
    });

    // If midnight or radar -> activate red safe-light mode styling
    if (sceneName === 'midnight' || sceneName === 'radar') {
      document.body.classList.add('red-mode');
    } else {
      document.body.classList.remove('red-mode');
    }
  }

  animate() {
    requestAnimationFrame(() => this.animate());
    const currentScene = this.scenes[this.activeSceneName];
    if (currentScene) {
      currentScene.render(this.renderer);
    }
  }
}

// Launch app on load
window.addEventListener('DOMContentLoaded', () => {
  new App();
});
