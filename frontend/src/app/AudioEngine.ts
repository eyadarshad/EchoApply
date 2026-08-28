"use client";

class AudioEngine {
  private ctx: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private filter: BiquadFilterNode | null = null;
  private oscillators: OscillatorNode[] = [];
  private oscGains: GainNode[] = [];
  private isPlaying = false;
  private currentChordIndex = 0;
  private timerId: any = null;

  // C3, E3, G3, B3 (Cmaj7), F3, A3, C4, E4 (Fmaj7), A2, C3, E3, G3 (Am7), G2, B2, D3, E3 (G6)
  private chords = [
    [130.81, 164.81, 196.00, 246.94], // Cmaj7
    [174.61, 220.00, 261.63, 329.63], // Fmaj7
    [110.00, 130.81, 164.81, 196.00], // Am7
    [98.00, 123.47, 146.83, 164.81],  // G6
  ];

  constructor() {
    // Audio Context is initialized lazily on user interaction
  }

  private init() {
    if (this.ctx) return;
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    this.ctx = new AudioContextClass();
    
    // Create master chain
    this.filter = this.ctx.createBiquadFilter();
    this.filter.type = "lowpass";
    this.filter.frequency.setValueAtTime(320, this.ctx.currentTime);
    this.filter.Q.setValueAtTime(1.5, this.ctx.currentTime);

    this.masterGain = this.ctx.createGain();
    this.masterGain.gain.setValueAtTime(0.0, this.ctx.currentTime); // start silent

    // Connect: oscillators -> oscGains -> filter -> masterGain -> destination
    this.filter.connect(this.masterGain);
    this.masterGain.connect(this.ctx.destination);
  }

  public start() {
    this.init();
    if (this.isPlaying || !this.ctx || !this.masterGain || !this.filter) return;

    this.isPlaying = true;
    
    // Fade in master volume
    const now = this.ctx.currentTime;
    this.masterGain.gain.cancelScheduledValues(now);
    this.masterGain.gain.linearRampToValueAtTime(0.18, now + 1.5); // Warm, non-obtrusive volume

    // Initialize oscillators for 4-voice polyphony
    this.oscillators = [];
    this.oscGains = [];
    
    for (let i = 0; i < 4; i++) {
      const osc = this.ctx.createOscillator();
      // Triangle waves give a soft, woodwind-like timbre
      osc.type = "triangle";
      
      const oscGain = this.ctx.createGain();
      oscGain.gain.setValueAtTime(0.0, now);

      osc.connect(oscGain);
      oscGain.connect(this.filter);
      
      osc.start(now);
      
      this.oscillators.push(osc);
      this.oscGains.push(oscGain);
    }

    // Play initial chord and start sequencer
    this.playChord(this.chords[this.currentChordIndex]);
    this.scheduleNextChord();
  }

  private playChord(frequencies: number[]) {
    if (!this.ctx || this.oscillators.length < 4 || this.oscGains.length < 4) return;
    const now = this.ctx.currentTime;

    // Slowly fade out previous oscillators and fade in new frequencies
    for (let i = 0; i < 4; i++) {
      const osc = this.oscillators[i];
      const oscGain = this.oscGains[i];
      const freq = frequencies[i];

      // Smoothly ramp down
      oscGain.gain.cancelScheduledValues(now);
      oscGain.gain.setValueAtTime(oscGain.gain.value, now);
      oscGain.gain.linearRampToValueAtTime(0.0, now + 1.2);

      // Program frequency shift slightly delayed after silence
      setTimeout(() => {
        if (!this.isPlaying || !this.ctx) return;
        const shiftTime = this.ctx.currentTime;
        osc.frequency.setValueAtTime(freq, shiftTime);
        
        // Slow swell in of the new voice
        oscGain.gain.cancelScheduledValues(shiftTime);
        oscGain.gain.setValueAtTime(0.0, shiftTime);
        oscGain.gain.linearRampToValueAtTime(0.25, shiftTime + 2.5);
      }, 1250);
    }
  }

  private scheduleNextChord() {
    this.timerId = setInterval(() => {
      if (!this.isPlaying) return;
      this.currentChordIndex = (this.currentChordIndex + 1) % this.chords.length;
      this.playChord(this.chords[this.currentChordIndex]);
    }, 7500); // Shift chords every 7.5 seconds
  }

  public stop() {
    if (this.timerId) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
    
    if (!this.isPlaying || !this.ctx || !this.masterGain) return;
    
    const now = this.ctx.currentTime;
    this.masterGain.gain.cancelScheduledValues(now);
    this.masterGain.gain.linearRampToValueAtTime(0.0, now + 1.0); // Fade out master

    setTimeout(() => {
      this.oscillators.forEach(osc => {
        try {
          osc.stop();
        } catch (e) {}
      });
      this.oscillators = [];
      this.oscGains = [];
      this.isPlaying = false;
    }, 1100);
  }

  public isEnabled(): boolean {
    return this.isPlaying;
  }

  public playClick() {
    if (!this.isPlaying) return;
    this.init();
    if (!this.ctx) return;

    const now = this.ctx.currentTime;
    
    // Quick sine wave chirp for tactile click feedback
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    
    osc.type = "sine";
    osc.frequency.setValueAtTime(800, now);
    osc.frequency.exponentialRampToValueAtTime(150, now + 0.08);

    gain.gain.setValueAtTime(0.08, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.08);

    osc.connect(gain);
    gain.connect(this.ctx.destination);

    osc.start(now);
    osc.stop(now + 0.09);
  }

  public playBumpSound() {
    if (!this.isPlaying) return;
    this.init();
    if (!this.ctx) return;

    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = "sine";
    osc.frequency.setValueAtTime(320, now);
    osc.frequency.exponentialRampToValueAtTime(120, now + 0.15);

    gain.gain.setValueAtTime(0.18, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.18);

    osc.connect(gain);
    gain.connect(this.ctx.destination);

    osc.start(now);
    osc.stop(now + 0.2);
  }

  public playVictoryChime() {
    if (!this.isPlaying) return;
    this.init();
    if (!this.ctx) return;

    const notes = [523.25, 659.25, 783.99, 1046.50]; // C5 -> E5 -> G5 -> C6
    const startTime = this.ctx.currentTime;

    notes.forEach((freq, idx) => {
      if (!this.ctx) return;
      const noteTime = startTime + idx * 0.075;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, noteTime);

      gain.gain.setValueAtTime(0.0, noteTime);
      gain.gain.linearRampToValueAtTime(0.18, noteTime + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, noteTime + 0.22);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(noteTime);
      osc.stop(noteTime + 0.24);
    });
  }
}

// Export singleton instance
export const audioEngine = new AudioEngine();
export default audioEngine;
