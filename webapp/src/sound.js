/**
 * Sound Engine: High-fidelity Web Audio API sound synthesis and real tape audio player.
 * Provides authentic 1970s audio feedback:
 * - Ambient low drone & vintage tape hiss / vinyl crackle
 * - Paper rustle (dossier page turns)
 * - Typewriter clacks
 * - Tape deck mechanical button snaps
 * - Heavy industrial knife-switch clank & electric buzzer
 * - Wax seal break / paper tear
 * - Real-time frequency analysis driving analog VU meter
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
    this.currentTrack = null;
    this.droneGain = null;
    this.hissGain = null;
    this.hasUserInteracted = false;
  }

  ensureContext() {
    if (!this.ctx) {
      try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        this.ctx = new AudioContext();
        this.analyser = this.ctx.createAnalyser();
        this.analyser.fftSize = 64;
        this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
      } catch (e) {
        console.warn('Web Audio not supported:', e);
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  startAmbient() {
    if (this.isMuted) return;
    this.ensureContext();
    if (!this.ctx) return;

    // 1. Low sinister suspense drone
    try {
      const osc = this.ctx.createOscillator();
      const filter = this.ctx.createBiquadFilter();
      const gain = this.ctx.createGain();

      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(48, this.ctx.currentTime); // Low G
      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(110, this.ctx.currentTime);

      gain.gain.setValueAtTime(0.025, this.ctx.currentTime);
      this.droneGain = gain;

      osc.connect(filter);
      filter.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
    } catch (e) {}

    // 2. Vintage tape hiss / vinyl surface noise
    try {
      const bufferSize = this.ctx.sampleRate * 2;
      const noiseBuffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
      const output = noiseBuffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        output[i] = (Math.random() * 2 - 1) * 0.015;
      }

      const whiteNoise = this.ctx.createBufferSource();
      whiteNoise.buffer = noiseBuffer;
      whiteNoise.loop = true;

      const bandpass = this.ctx.createBiquadFilter();
      bandpass.type = 'bandpass';
      bandpass.frequency.setValueAtTime(1800, this.ctx.currentTime);
      bandpass.Q.setValueAtTime(1.5, this.ctx.currentTime);

      const hissGain = this.ctx.createGain();
      hissGain.gain.setValueAtTime(0.012, this.ctx.currentTime);
      this.hissGain = hissGain;

      whiteNoise.connect(bandpass);
      bandpass.connect(hissGain);
      hissGain.connect(this.ctx.destination);
      whiteNoise.start();
    } catch (e) {}
  }

  // Realistic paper rustle sound when turning dossier tabs
  playPaperRustle() {
    if (this.isMuted) return;
    this.ensureContext();
    if (!this.ctx) return;

    try {
      const bufferSize = this.ctx.sampleRate * 0.22;
      const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (bufferSize * 0.35));
      }

      const source = this.ctx.createBufferSource();
      source.buffer = buffer;

      const filter = this.ctx.createBiquadFilter();
      filter.type = 'bandpass';
      filter.frequency.setValueAtTime(1400, this.ctx.currentTime);
      filter.Q.setValueAtTime(2.0, this.ctx.currentTime);

      const gain = this.ctx.createGain();
      gain.gain.setValueAtTime(0.18, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.2);

      source.connect(filter);
      filter.connect(gain);
      gain.connect(this.ctx.destination);
      source.start();
    } catch (e) {}
  }

  // Vintage typewriter key strike
  playTypewriter() {
    if (this.isMuted) return;
    this.ensureContext();
    if (!this.ctx) return;

    try {
      const t = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      // Sharp mechanical clank
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(320 + Math.random() * 80, t);
      osc.frequency.exponentialRampToValueAtTime(80, t + 0.04);

      gain.gain.setValueAtTime(0.25, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.05);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(t);
      osc.stop(t + 0.05);
    } catch (e) {}
  }

  // Heavy tape deck button snap
  playTapeClick() {
    if (this.isMuted) return;
    this.ensureContext();
    if (!this.ctx) return;

    try {
      const t = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'square';
      osc.frequency.setValueAtTime(180, t);
      osc.frequency.exponentialRampToValueAtTime(40, t + 0.08);

      gain.gain.setValueAtTime(0.4, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.09);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(t);
      osc.stop(t + 0.09);
    } catch (e) {}
  }

  // Heavy industrial knife switch clank & electric buzzer
  playSwitchClank() {
    if (this.isMuted) return;
    this.ensureContext();
    if (!this.ctx) return;

    try {
      const t = this.ctx.currentTime;
      // Heavy clank
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(120, t);
      osc.frequency.exponentialRampToValueAtTime(30, t + 0.15);

      gain.gain.setValueAtTime(0.5, t);
      gain.gain.exponentialRampToValueAtTime(0.01, t + 0.16);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(t);
      osc.stop(t + 0.16);

      // Electric spark buzz
      const buzz = this.ctx.createOscillator();
      const buzzGain = this.ctx.createGain();
      buzz.type = 'sawtooth';
      buzz.frequency.setValueAtTime(60, t + 0.05);
      buzzGain.gain.setValueAtTime(0.2, t + 0.05);
      buzzGain.gain.exponentialRampToValueAtTime(0.001, t + 0.35);
      buzz.connect(buzzGain);
      buzzGain.connect(this.ctx.destination);
      buzz.start(t + 0.05);
      buzz.stop(t + 0.35);
    } catch (e) {}
  }

  // Red wax seal breaking / paper tear
  playWaxBreak() {
    if (this.isMuted) return;
    this.ensureContext();
    if (!this.ctx) return;

    try {
      const bufferSize = this.ctx.sampleRate * 0.18;
      const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (bufferSize * 0.2));
      }

      const source = this.ctx.createBufferSource();
      source.buffer = buffer;

      const filter = this.ctx.createBiquadFilter();
      filter.type = 'highpass';
      filter.frequency.setValueAtTime(1200, this.ctx.currentTime);

      const gain = this.ctx.createGain();
      gain.gain.setValueAtTime(0.3, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.18);

      source.connect(filter);
      filter.connect(gain);
      gain.connect(this.ctx.destination);
      source.start();
    } catch (e) {}
  }

  // Plays tape track (colonel_tape.wav or welcome_narration.mp3)
  playTrack(audioPath, onEndedCallback) {
    this.ensureContext();
    this.stopTrack();

    this.playTapeClick();

    if (!this.audioElement) {
      this.audioElement = new Audio();
      this.audioElement.crossOrigin = 'anonymous';

      if (this.ctx && this.analyser) {
        try {
          this.audioSourceNode = this.ctx.createMediaElementSource(this.audioElement);
          this.audioSourceNode.connect(this.analyser);
          this.analyser.connect(this.ctx.destination);
        } catch (e) {}
      }
    }

    this.audioElement.src = audioPath;
    this.currentTrack = audioPath;

    this.audioElement.play().then(() => {
      this.isPlayingTape = true;
    }).catch(e => {
      console.warn('Autoplay prevented:', e);
    });

    this.audioElement.onended = () => {
      this.isPlayingTape = false;
      if (onEndedCallback) onEndedCallback();
    };
  }

  stopTrack() {
    if (this.audioElement && this.isPlayingTape) {
      this.playTapeClick();
      this.audioElement.pause();
      this.audioElement.currentTime = 0;
      this.isPlayingTape = false;
    }
  }

  getAudioFrequencyLevel() {
    if (!this.analyser || !this.isPlayingTape) return 0;
    this.analyser.getByteFrequencyData(this.dataArray);
    let sum = 0;
    const len = Math.min(16, this.dataArray.length);
    for (let i = 0; i < len; i++) {
      sum += this.dataArray[i];
    }
    return Math.min(1.0, (sum / len) / 160);
  }

  toggleMute() {
    this.isMuted = !this.isMuted;
    if (this.isMuted) {
      if (this.droneGain) this.droneGain.gain.setValueAtTime(0, this.ctx.currentTime);
      if (this.hissGain) this.hissGain.gain.setValueAtTime(0, this.ctx.currentTime);
      if (this.audioElement) this.audioElement.muted = true;
    } else {
      if (this.droneGain) this.droneGain.gain.setValueAtTime(0.025, this.ctx.currentTime);
      if (this.hissGain) this.hissGain.gain.setValueAtTime(0.012, this.ctx.currentTime);
      if (this.audioElement) this.audioElement.muted = false;
    }
    return !this.isMuted;
  }
}

export const Sound = new SoundEngine();
