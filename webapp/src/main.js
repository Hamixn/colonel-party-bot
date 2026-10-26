import { Api } from './api.js';
import { Haptic } from './haptic.js';
import { Sound } from './sound.js';

class DossierApp {
  constructor() {
    this.profile = null;
    this.activeSheet = 'sheet-profile';
    this.isDarkroom = false;
    this.isCardFlipped = false;
    this.vuAnimationId = null;
    this.isTapePlaying = false;
    this.rescueTimerInterval = null;

    this.setupTelegram();
    this.setupAudioAutoplayGuard();
    this.init();
  }

  setupTelegram() {
    if (window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp;
      tg.ready();
      tg.expand();
      try {
        tg.setHeaderColor('#0a0709');
        tg.setBackgroundColor('#0a0709');
      } catch (e) {}
    }
  }

  setupAudioAutoplayGuard() {
    // Resume audio context on first user tap anywhere
    const resume = () => {
      Sound.ensureContext();
      Sound.startAmbient();
      window.removeEventListener('click', resume);
      window.removeEventListener('touchstart', resume);
    };
    window.addEventListener('click', resume, { once: true });
    window.addEventListener('touchstart', resume, { once: true });
  }

  async init() {
    this.bindEvents();
    await this.loadGuestData();

    // Hide loader
    const loader = document.getElementById('loading-screen');
    if (loader) {
      loader.style.opacity = '0';
      setTimeout(() => loader.remove(), 400);
    }
  }

  async loadGuestData() {
    try {
      this.profile = await Api.getMe();
      this.renderProfile();
    } catch (e) {
      console.warn('Could not load profile:', e);
    }
  }

  renderProfile() {
    if (!this.profile) return;

    // Subject data
    const nameEl = document.getElementById('prof-name');
    if (nameEl) nameEl.textContent = this.profile.full_name || 'مهمان عمارت';

    const cardNameFront = document.getElementById('card-name-front');
    if (cardNameFront) cardNameFront.textContent = this.profile.full_name || 'مهمان عمارت';

    const roleEl = document.getElementById('prof-role');
    const isPlayer = this.profile.role === 'role_player';
    if (roleEl) {
      roleEl.textContent = isPlayer ? 'بازیکن طلسم (قربانی در حیاط)' : 'بلوند بی‌گناه (سالن اختصاصی)';
      roleEl.style.color = isPlayer ? '#8f1d24' : '#cfa84e';
    }

    const pinEl = document.getElementById('prof-pin');
    const pinBack = document.getElementById('card-pin-back');
    const pin = this.profile.soul_pin || '---';
    if (pinEl) pinEl.textContent = pin;
    if (pinBack) pinBack.textContent = pin;

    const teamEl = document.getElementById('prof-team');
    if (teamEl) teamEl.textContent = this.profile.team_name || `تیم ${this.profile.team_number || 1}`;

    const carEl = document.getElementById('prof-car');
    if (carEl) carEl.textContent = `خودروی شماره ${this.profile.car_number || 1}`;

    const driverEl = document.getElementById('prof-driver');
    if (driverEl) driverEl.textContent = this.profile.driver_name || 'تعیین نشده';

    const passEl = document.getElementById('prof-passengers');
    if (passEl) {
      if (this.profile.teammates && this.profile.teammates.length > 0) {
        passEl.textContent = this.profile.teammates.join('، ');
      } else {
        passEl.textContent = 'در حال تکمیل ظرفیت ۴ نفره';
      }
    }
  }

  bindEvents() {
    // Tab switching (both top tabs and bottom nav)
    const allTabTriggers = document.querySelectorAll('[data-sheet]');
    allTabTriggers.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetSheet = btn.dataset.sheet;
        this.switchSheet(targetSheet);
      });
    });

    // Sound toggle button
    const btnSound = document.getElementById('btn-sound-toggle');
    if (btnSound) {
      btnSound.addEventListener('click', () => {
        const active = Sound.toggleMute();
        btnSound.textContent = active ? '🔊 صدا' : '🔇 صامت';
        Haptic.impact('light');
      });
    }

    // Invitation Card 3D Flip on click
    const cardBox = document.getElementById('card-inspect-box');
    const cardFlipper = document.getElementById('card-flipper-el');
    if (cardBox && cardFlipper) {
      cardBox.addEventListener('click', () => {
        this.isCardFlipped = !this.isCardFlipped;
        cardFlipper.classList.toggle('flipped', this.isCardFlipped);
        Sound.playPaperRustle();
        Haptic.impact('medium');
      });
    }

    // Narration Audio Button
    const btnNarration = document.getElementById('btn-play-narration');
    if (btnNarration) {
      btnNarration.addEventListener('click', () => {
        Haptic.impact('medium');
        Sound.playTrack('./audio/welcome_narration.mp3', () => {
          btnNarration.querySelector('span:last-child').textContent = 'شنیدن فایل صوتی بازجویی و روایت سرهنگ';
        });
        btnNarration.querySelector('span:last-child').textContent = 'در حال پخش فایل صوتی بازجویی...';
      });
    }

    // Nagra Tape Deck Controls
    const btnTapePlay = document.getElementById('btn-tape-play');
    const btnTapePause = document.getElementById('btn-tape-pause');
    const btnTapeRewind = document.getElementById('btn-tape-rewind');
    const cassetteBody = document.getElementById('cassette-body-el');

    if (btnTapePlay) {
      btnTapePlay.addEventListener('click', () => {
        Haptic.impact('heavy');
        this.isTapePlaying = true;
        if (cassetteBody) cassetteBody.classList.add('spinning');
        btnTapePlay.classList.add('pressed');
        if (btnTapePause) btnTapePause.classList.remove('pressed');

        Sound.playTrack('./audio/colonel_tape.wav', () => {
          this.isTapePlaying = false;
          if (cassetteBody) cassetteBody.classList.remove('spinning');
          btnTapePlay.classList.remove('pressed');
        });

        this.startVUMeterLoop();
      });
    }

    if (btnTapePause) {
      btnTapePause.addEventListener('click', () => {
        Haptic.impact('medium');
        this.isTapePlaying = false;
        if (cassetteBody) cassetteBody.classList.remove('spinning');
        if (btnTapePlay) btnTapePlay.classList.remove('pressed');
        btnTapePause.classList.add('pressed');
        Sound.stopTrack();
      });
    }

    if (btnTapeRewind) {
      btnTapeRewind.addEventListener('click', () => {
        Haptic.impact('medium');
        Sound.playTapeClick();
        if (Sound.audioElement) {
          Sound.audioElement.currentTime = 0;
        }
      });
    }

    // Blueprint Hotspot Pins
    const pinInfo = document.getElementById('pin-info-display');
    const pinData = {
      '1': '🚪 **[نقطه ۱: کوچه باغ صدرا و دروازه اصلی]**\nدرب‌های عمارت دقیقاً رأس ساعت ۱۸:۱۵ برای همیشه قفل زنجیر می‌شوند. خروج تا پایان سحرگاه امکان‌پذیر نیست.',
      '2': '🌊 **[نقطه ۲: استخر خشکیده حیاط]**\nمحل اختفای پاکت اول طلسم. در تاریکی شب، روح سرگردان سرهنگ در مدار این استخر به دنبال متجاوزان به حریم باغ می‌گردد.',
      '3': '🥂 **[نقطه ۳: سالن شیشه‌ای مشرف به حیاط]**\nپناهگاه امن بلوندهای بی‌گناه. از پنجره‌های این سالن دید کامل به حیاط وجود دارد و اهرم ژنراتور نور حیات باغ در اینجاست.',
      '4': '📸 **[نقطه ۴: تاریک‌خانه عکاسی سرهنگ]**\nاتاق چاپ عکس سرهنگ با نور سرخ. سرهنگ در سال ۱۳۵۶ به این نور عادت داشته و در بازی نیمه‌شب به نور سرخ نابیناست!'
    };

    document.querySelectorAll('.map-pin').forEach(pinEl => {
      pinEl.addEventListener('click', () => {
        const pinId = pinEl.dataset.pin;
        Haptic.impact('light');
        Sound.playTypewriter();
        if (pinInfo && pinData[pinId]) {
          pinInfo.innerHTML = pinData[pinId].replace(/\n/g, '<br>');
        }
      });
    });

    // Darkroom safe-light toggle
    const btnDarkroom = document.getElementById('btn-darkroom');
    const midnightPanel = document.getElementById('midnight-panel-box');
    if (btnDarkroom) {
      btnDarkroom.addEventListener('click', () => {
        this.isDarkroom = !this.isDarkroom;
        Haptic.notification('warning');
        Sound.playTapeClick();
        if (midnightPanel) midnightPanel.classList.toggle('darkroom-active', this.isDarkroom);
        btnDarkroom.textContent = this.isDarkroom ? '⚪️ خروج از تاریک‌خانه سرخ' : '🔴 فعال‌سازی حالت تاریک‌خانه سرخ (نور ایمن)';
      });
    }

    // Envelope Wax Seals & Poem Reveal
    const setupEnvelope = (btnId, poemId, sealId) => {
      const btnOpen = document.getElementById(btnId);
      const poemEl = document.getElementById(poemId);
      const sealEl = document.getElementById(sealId);
      if (btnOpen && poemEl) {
        btnOpen.addEventListener('click', () => {
          Sound.playWaxBreak();
          Haptic.impact('heavy');
          poemEl.classList.add('revealed');
          if (sealEl) sealEl.style.opacity = '0.3';
          btnOpen.style.display = 'none';
        });
      }
    };
    setupEnvelope('btn-open-env-1', 'poem-1', 'seal-1');
    setupEnvelope('btn-open-env-2', 'poem-2', 'seal-2');

    // Riddle Solve Submit
    const setupSolve = (btnId, inputId, riddleNum) => {
      const btn = document.getElementById(btnId);
      const input = document.getElementById(inputId);
      if (btn && input) {
        btn.addEventListener('click', async () => {
          const val = input.value.trim();
          if (!val) return;
          Haptic.impact('medium');
          Sound.playTypewriter();
          btn.textContent = '...';

          try {
            const res = await Api.solveRiddle(val);
            if (res.status === 'riddle_solved' || res.status === 'both_solved') {
              Haptic.notification('success');
              alert(`🎉 تبریک! پاسخ پاکت ${riddleNum} صحیح بود و در پرونده تیم ثبت شد.`);
              btn.textContent = '✅ حل شد';
              btn.disabled = true;
              input.disabled = true;
            } else {
              Haptic.notification('error');
              alert('❌ پاسخ اشتباه است! رمز دیگری امتحان کنید.');
              btn.textContent = 'ثبت';
            }
          } catch (e) {
            alert('⚠️ خطا در ارتباط با سرور.');
            btn.textContent = 'ثبت';
          }
        });
      }
    };
    setupSolve('btn-solve-1', 'input-solve-1', 1);
    setupSolve('btn-solve-2', 'input-solve-2', 2);

    // Courtyard Rescue Knife Switch
    const btnRescue = document.getElementById('btn-rescue-lever');
    if (btnRescue) {
      btnRescue.addEventListener('click', async () => {
        Haptic.notification('warning');
        Sound.playSwitchClank();
        btnRescue.disabled = true;

        try {
          const res = await Api.triggerRescue();
          if (res.success) {
            this.trigger10SecondFlash();
          } else {
            alert(res.error || 'سقف استفاده از نور حیات باغ پر شده است.');
          }
        } catch (e) {
          // Local preview fallback
          this.trigger10SecondFlash();
        } finally {
          setTimeout(() => { btnRescue.disabled = false; }, 12000);
        }
      });
    }
  }

  trigger10SecondFlash() {
    const overlay = document.getElementById('rescue-flash-overlay');
    const countEl = document.getElementById('rescue-timer-count');
    if (!overlay) return;

    overlay.classList.add('active');
    let timeLeft = 10;
    if (countEl) countEl.textContent = timeLeft;

    if (this.rescueTimerInterval) clearInterval(this.rescueTimerInterval);
    this.rescueTimerInterval = setInterval(() => {
      timeLeft--;
      if (countEl) countEl.textContent = timeLeft;
      Haptic.impact('light');

      if (timeLeft <= 0) {
        clearInterval(this.rescueTimerInterval);
        overlay.classList.remove('active');
      }
    }, 1000);
  }

  startVUMeterLoop() {
    const needle = document.getElementById('vu-needle-el');
    if (!needle) return;

    const update = () => {
      if (this.isTapePlaying) {
        const level = Sound.getAudioFrequencyLevel(); // 0.0 to 1.0
        // Needle angle: from -35deg to +25deg
        const angle = -35 + (level * 60) + (Math.random() * 4 - 2);
        needle.style.transform = `rotate(${angle}deg)`;
        this.vuAnimationId = requestAnimationFrame(update);
      } else {
        needle.style.transform = 'rotate(-35deg)';
      }
    };
    update();
  }

  switchSheet(sheetId) {
    if (this.activeSheet === sheetId) return;

    Sound.playPaperRustle();
    Haptic.selection();

    // Deactivate previous
    document.querySelectorAll('.folder-sheet').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('[data-sheet]').forEach(b => b.classList.remove('active'));

    // Activate target
    const target = document.getElementById(sheetId);
    if (target) target.classList.add('active');

    document.querySelectorAll(`[data-sheet="${sheetId}"]`).forEach(b => b.classList.add('active'));
    this.activeSheet = sheetId;
  }
}

// Boot application
window.addEventListener('DOMContentLoaded', () => {
  window.app = new DossierApp();
});
