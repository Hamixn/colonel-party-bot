/**
 * Audio Engine: Web Audio API synthesis + real audio track player.
 * Drives the 3D cassette VU meter with real-time frequency analysis.
 */

class SoundEngine {
  constructor() {
    this.ctx = null;
    this.isMuted = false;
    this.analyser = null;
    this.dataArray = null;
    this.audioElement = null;
    this.audioSourceNode = null;
    this.isPlayingTape = false;
    this.ambientGain = null;
  }

  init() {
    if (this.ctx) return;
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioContext();
      this.analyser = this.ctx.createAnalyser();
      this.analyser.fftSize = 64;
      this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);

      // Ambient low-drone oscillator
      this.startAmbientDrone();
    } catch (e) {
      console.warn('Web Audio not supported:', e);
    }
  }

  startAmbientDrone() {
    if (!this.ctx) return;
    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      const filter = this.ctx.createBiquadFilter();

      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(55, this.ctx.currentTime); // Low A

      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(140, this.ctx.currentTime);

      gain.gain.setValueAtTime(0.04, this.ctx.currentTime);
      this.ambientGain = gain;

      osc.connect(filter);
      filter.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
    } catch (e) {}
  }

  playTape(audioPath = './audio/welcome_narration.mp3') {
    this.init();
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }

    if (!this.audioElement) {
      this.audioElement = new Audio(audioPath);
      this.audioElement.crossOrigin = 'anonymous';

      if (this.ctx && this.analyser) {
        try {
          this.audioSourceNode = this.ctx.createMediaElementSource(this.audioElement);
          this.audioSourceNode.connect(this.analyser);
          this.analyser.connect(this.ctx.destination);
        } catch (e) {
          // In case cross-origin or already connected
        }
      }
    } else {
      this.audioElement.src = audioPath;
    }

    this.audioElement.play().then(() => {
      this.isPlayingTape = true;
    }).catch(e => {
      console.warn('Autoplay prevented:', e);
    });

    this.audioElement.onended = () => {
      this.isPlayingTape = false;
    };
  }

  stopTape() {
    if (this.audioElement) {
      this.audioElement.pause();
      this.isPlayingTape = false;
    }
  }

  toggleTape(audioPath) {
    if (this.isPlayingTape) {
      this.stopTape();
      return false;
    } else {
      this.playTape(audioPath);
      return true;
    }
  }

  getAudioLevel() {
    if (!this.analyser || !this.dataArray || !this.isPlayingTape) {
      return 0;
    }
    this.analyser.getByteFrequencyData(this.dataArray);
    let sum = 0;
    for (let i = 0; i < this.dataArray.length; i++) {
      sum += this.dataArray[i];
    }
    return sum / (this.dataArray.length * 255); // 0.0 to 1.0
  }

  playMechanicalClick() {
    this.init();
    if (!this.ctx) return;
    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(320, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(40, this.ctx.currentTime + 0.06);

      gain.gain.setValueAtTime(0.3, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.06);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
      osc.stop(this.ctx.currentTime + 0.07);
    } catch (e) {}
  }

  playUnlockChime() {
    this.init();
    if (!this.ctx) return;
    try {
      [440, 554, 659, 880].forEach((freq, idx) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, this.ctx.currentTime + idx * 0.08);

        gain.gain.setValueAtTime(0, this.ctx.currentTime + idx * 0.08);
        gain.gain.linearRampToValueAtTime(0.2, this.ctx.currentTime + idx * 0.08 + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + idx * 0.08 + 0.5);

        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(this.ctx.currentTime + idx * 0.08);
        osc.stop(this.ctx.currentTime + idx * 0.08 + 0.6);
      });
    } catch (e) {}
  }

  toggleMute() {
    this.isMuted = !this.isMuted;
    if (this.ctx) {
      if (this.isMuted) {
        this.ctx.suspend();
      } else {
        this.ctx.resume();
      }
    }
    if (this.audioElement) {
      this.audioElement.muted = this.isMuted;
    }
    return !this.isMuted;
  }
}

export const Sound = new SoundEngine();
