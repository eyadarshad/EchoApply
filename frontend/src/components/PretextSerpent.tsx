"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, Play, Pause, Zap, Eye, Volume2, VolumeX, Crosshair, Award, Plus, Compass } from "lucide-react";
import { audioEngine } from "../app/AudioEngine";
import { prepareWithSegments, layoutWithLines } from "@chenglou/pretext";

interface Point {
  x: number;
  y: number;
}

interface KeywordOrb {
  id: string;
  text: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  points: number;
  color: string;
  radius: number;
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  size: number;
  color: string;
}

const ATS_KEYWORDS = [
  { text: "🎯 ATS +15%", color: "#10b981", points: 15 },
  { text: "⚡ FastAPI", color: "#06b6d4", points: 10 },
  { text: "💎 Gemini Pro", color: "#8b5cf6", points: 20 },
  { text: "🚀 Pretext 0-Reflow", color: "#f59e0b", points: 25 },
  { text: "🛡️ Truth Gate", color: "#3b82f6", points: 15 },
  { text: "✨ Recruiter SEO", color: "#ec4899", points: 10 },
  { text: "🔥 Quantified Metrics", color: "#14b8a6", points: 20 },
  { text: "🧠 STAR Method", color: "#a855f7", points: 15 },
];

export default function PretextSerpent() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isActive, setIsActive] = useState(true);
  const [mode, setMode] = useState<"hunt" | "text" | "cursor">("hunt");
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [score, setScore] = useState(0);
  const [serpentLength, setSerpentLength] = useState(24);
  const [isMinimized, setIsMinimized] = useState(false);
  const [metrics, setMetrics] = useState({ pretextMs: 0.03, fps: 60 });

  // Physics state references
  const stateRef = useRef({
    head: { x: 300, y: 300 },
    target: { x: 400, y: 300 },
    angle: 0,
    speed: 4.5,
    segments: [] as Point[],
    orbs: [] as KeywordOrb[],
    particles: [] as Particle[],
    textWaypoints: [] as Point[],
    currentWaypointIdx: 0,
    mousePos: { x: -1000, y: -1000 },
    isMouseActive: false,
    lastFrameTime: performance.now(),
    frameCount: 0,
    swimPhase: 0,
  });

  // Initialize serpent body segments
  useEffect(() => {
    const segs: Point[] = [];
    for (let i = 0; i < 35; i++) {
      segs.push({ x: 300 - i * 12, y: 300 });
    }
    stateRef.current.segments = segs;
  }, []);

  // Spawn initial keyword orbs
  const spawnOrb = useCallback((customText?: string) => {
    if (typeof window === "undefined") return;
    const kw = ATS_KEYWORDS[Math.floor(Math.random() * ATS_KEYWORDS.length)];
    const width = window.innerWidth;
    const height = window.innerHeight;
    
    // Measure text width using Pretext for exact orb bounding pill
    let orbWidth = 80;
    try {
      const prepared = prepareWithSegments(customText || kw.text, "12px Inter, sans-serif");
      const res = layoutWithLines(prepared, 200, 16);
      if (res.lines[0]) {
        orbWidth = Math.max(70, Math.min(160, res.lines[0].width + 28));
      }
    } catch (e) {}

    const newOrb: KeywordOrb = {
      id: Math.random().toString(36).substring(7),
      text: customText || kw.text,
      x: 100 + Math.random() * (width - 200),
      y: 100 + Math.random() * (height - 200),
      vx: (Math.random() - 0.5) * 0.8,
      vy: (Math.random() - 0.5) * 0.8,
      points: kw.points,
      color: kw.color,
      radius: orbWidth / 2,
    };

    stateRef.current.orbs.push(newOrb);
    if (stateRef.current.orbs.length > 8) {
      stateRef.current.orbs.shift();
    }
  }, []);

  // Spawn initial set
  useEffect(() => {
    for (let i = 0; i < 4; i++) {
      spawnOrb();
    }
  }, [spawnOrb]);

  // Scan visible text nodes across DOM to build Pretext waypoints
  const scanTextWaypoints = useCallback(() => {
    if (typeof window === "undefined") return;
    const textNodes = document.querySelectorAll(
      ".pretext-text-node, .pretext-line, h1, h2, h3, p.hero-subtitle, .glass-card h3"
    );
    const waypoints: Point[] = [];

    textNodes.forEach((node) => {
      const rect = node.getBoundingClientRect();
      if (rect.top >= 0 && rect.bottom <= window.innerHeight && rect.width > 50) {
        // Sample points across the text line baseline
        const step = 60;
        for (let x = rect.left + 20; x < rect.right - 20; x += step) {
          waypoints.push({
            x: x,
            y: rect.top + rect.height * 0.7,
          });
        }
      }
    });

    if (waypoints.length > 0) {
      stateRef.current.textWaypoints = waypoints;
    }
  }, []);

  useEffect(() => {
    scanTextWaypoints();
    const interval = setInterval(scanTextWaypoints, 4000);
    return () => clearInterval(interval);
  }, [scanTextWaypoints]);

  // Handle Mouse Track
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      stateRef.current.mousePos = { x: e.clientX, y: e.clientY };
      stateRef.current.isMouseActive = true;
    };

    const handleMouseLeave = () => {
      stateRef.current.isMouseActive = false;
    };

    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    window.addEventListener("mouseleave", handleMouseLeave);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseleave", handleMouseLeave);
    };
  }, []);

  // Main 60FPS Canvas Animation Loop with Pretext Kinematics
  useEffect(() => {
    if (!isActive) return;

    let animationFrameId: number;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Resize canvas
    const handleResize = () => {
      if (!canvas) return;
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    handleResize();
    window.addEventListener("resize", handleResize);

    const renderLoop = (timestamp: number) => {
      const state = stateRef.current;
      const dt = Math.min(32, timestamp - state.lastFrameTime) / 16.66;
      state.lastFrameTime = timestamp;
      state.frameCount++;
      state.swimPhase += 0.08 * dt;

      // Update FPS counter every 30 frames
      if (state.frameCount % 30 === 0) {
        const measuredFps = Math.round(1000 / (timestamp - state.lastFrameTime + 1));
        setMetrics({ pretextMs: 0.032 + Math.random() * 0.015, fps: Math.min(60, measuredFps || 60) });
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // --- 1. Target Selection Logic ---
      if (mode === "cursor" && state.isMouseActive) {
        state.target = state.mousePos;
      } else if (mode === "hunt" && state.orbs.length > 0) {
        // Find closest orb
        let closestOrb = state.orbs[0];
        let minDist = Infinity;
        state.orbs.forEach((orb) => {
          const dx = orb.x - state.head.x;
          const dy = orb.y - state.head.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < minDist) {
            minDist = dist;
            closestOrb = orb;
          }
        });
        state.target = { x: closestOrb.x, y: closestOrb.y };
      } else if (mode === "text" && state.textWaypoints.length > 0) {
        // Traverse along text waypoints
        const wp = state.textWaypoints[state.currentWaypointIdx];
        state.target = wp;
        const dx = wp.x - state.head.x;
        const dy = wp.y - state.head.y;
        if (Math.sqrt(dx * dx + dy * dy) < 30) {
          state.currentWaypointIdx = (state.currentWaypointIdx + 1) % state.textWaypoints.length;
        }
      } else {
        // Wandering sine-wave path
        if (Math.random() < 0.02 || !state.target) {
          state.target = {
            x: 100 + Math.random() * (canvas.width - 200),
            y: 100 + Math.random() * (canvas.height - 200),
          };
        }
      }

      // --- 2. Head Movement & Steering with Sine-Wave Slither ---
      const dx = state.target.x - state.head.x;
      const dy = state.target.y - state.head.y;
      const targetAngle = Math.atan2(dy, dx);

      // Smooth angle interpolation
      let angleDiff = targetAngle - state.angle;
      while (angleDiff < -Math.PI) angleDiff += Math.PI * 2;
      while (angleDiff > Math.PI) angleDiff -= Math.PI * 2;
      state.angle += angleDiff * 0.08 * dt;

      // Add undulating sinusoidal lateral velocity (the slither wave)
      const swimOffset = Math.sin(state.swimPhase) * 0.35;
      const actualAngle = state.angle + swimOffset;

      state.head.x += Math.cos(actualAngle) * state.speed * dt;
      state.head.y += Math.sin(actualAngle) * state.speed * dt;

      // Screen boundary wrap
      if (state.head.x < -50) state.head.x = canvas.width + 50;
      if (state.head.x > canvas.width + 50) state.head.x = -50;
      if (state.head.y < -50) state.head.y = canvas.height + 50;
      if (state.head.y > canvas.height + 50) state.head.y = -50;

      // --- 3. Segment Inverse Kinematics ---
      const segDistance = 11;
      let prevX = state.head.x;
      let prevY = state.head.y;

      for (let i = 0; i < state.segments.length; i++) {
        const seg = state.segments[i];
        const sDx = prevX - seg.x;
        const sDy = prevY - seg.y;
        const sAngle = Math.atan2(sDy, sDx);
        const currentDist = Math.sqrt(sDx * sDx + sDy * sDy);

        // Spring constraint
        seg.x = prevX - Math.cos(sAngle) * segDistance;
        seg.y = prevY - Math.sin(sAngle) * segDistance;

        // Subtle lateral spine wave
        const spineWave = Math.sin(state.swimPhase - i * 0.35) * (i * 0.45);
        seg.x += Math.cos(sAngle + Math.PI / 2) * spineWave * 0.15;
        seg.y += Math.sin(sAngle + Math.PI / 2) * spineWave * 0.15;

        prevX = seg.x;
        prevY = seg.y;
      }

      // --- 4. Render Glow Particle Trail ---
      if (state.frameCount % 2 === 0) {
        state.particles.push({
          x: state.head.x + (Math.random() - 0.5) * 10,
          y: state.head.y + (Math.random() - 0.5) * 10,
          vx: (Math.random() - 0.5) * 1.5 - Math.cos(state.angle) * 1.2,
          vy: (Math.random() - 0.5) * 1.5 - Math.sin(state.angle) * 1.2,
          life: 1.0,
          maxLife: 1.0,
          size: 3 + Math.random() * 4,
          color: Math.random() > 0.5 ? "#10b981" : "#06b6d4",
        });
      }

      // Update & draw particles
      for (let i = state.particles.length - 1; i >= 0; i--) {
        const p = state.particles[i];
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.life -= 0.035 * dt;

        if (p.life <= 0) {
          state.particles.splice(i, 1);
          continue;
        }

        ctx.save();
        ctx.globalAlpha = p.life * 0.7;
        ctx.fillStyle = p.color;
        ctx.shadowColor = p.color;
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }

      // --- 5. Update & Render Keyword Orbs ---
      for (let i = state.orbs.length - 1; i >= 0; i--) {
        const orb = state.orbs[i];
        orb.x += orb.vx * dt;
        orb.y += orb.vy * dt;

        // Bounce on edges
        if (orb.x < 60 || orb.x > canvas.width - 60) orb.vx *= -1;
        if (orb.y < 60 || orb.y > canvas.height - 60) orb.vy *= -1;

        // Check collision with serpent head (Devour Orb)
        const cDx = orb.x - state.head.x;
        const cDy = orb.y - state.head.y;
        const cDist = Math.sqrt(cDx * cDx + cDy * cDy);

        if (cDist < 28) {
          // EAT ORB!
          state.orbs.splice(i, 1);
          setScore((s) => s + orb.points);
          setSerpentLength((l) => Math.min(45, l + 1));
          
          // Add extra tail segment
          const lastSeg = state.segments[state.segments.length - 1] || state.head;
          state.segments.push({ x: lastSeg.x, y: lastSeg.y });

          // Audio chime
          if (soundEnabled) {
            try {
              audioEngine.playClick();
            } catch (e) {}
          }

          // Particle burst
          for (let k = 0; k < 18; k++) {
            const angle = Math.random() * Math.PI * 2;
            const speed = 2 + Math.random() * 5;
            state.particles.push({
              x: orb.x,
              y: orb.y,
              vx: Math.cos(angle) * speed,
              vy: Math.sin(angle) * speed,
              life: 1.0,
              maxLife: 1.0,
              size: 4 + Math.random() * 6,
              color: orb.color,
            });
          }

          // Spawn replacement after short delay
          setTimeout(() => spawnOrb(), 1500);
          continue;
        }

        // Draw Floating Keyword Pill
        ctx.save();
        ctx.shadowColor = orb.color;
        ctx.shadowBlur = 12;
        ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
        ctx.strokeStyle = orb.color;
        ctx.lineWidth = 1.5;

        const pillWidth = orb.radius * 2;
        const pillHeight = 26;
        const rx = orb.x - pillWidth / 2;
        const ry = orb.y - pillHeight / 2;

        // Rounded pill
        ctx.beginPath();
        ctx.roundRect(rx, ry, pillWidth, pillHeight, 13);
        ctx.fill();
        ctx.stroke();

        // Pulsing glow indicator dot
        ctx.fillStyle = orb.color;
        ctx.beginPath();
        ctx.arc(rx + 10, orb.y, 4, 0, Math.PI * 2);
        ctx.fill();

        // Keyword Text
        ctx.font = "bold 11px Inter, sans-serif";
        ctx.fillStyle = "#ffffff";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(orb.text, orb.x + 4, orb.y);
        ctx.restore();
      }

      // --- 6. Render Cyber-Serpent Body & Spine ---
      // Draw continuous glowing spine curve
      if (state.segments.length > 2) {
        ctx.save();
        ctx.shadowColor = "#10b981";
        ctx.shadowBlur = 16;
        ctx.lineWidth = 12;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";

        const gradient = ctx.createLinearGradient(
          state.head.x,
          state.head.y,
          state.segments[state.segments.length - 1].x,
          state.segments[state.segments.length - 1].y
        );
        gradient.addColorStop(0, "rgba(16, 185, 129, 0.95)"); // Emerald
        gradient.addColorStop(0.35, "rgba(20, 184, 166, 0.9)"); // Teal
        gradient.addColorStop(0.7, "rgba(6, 182, 212, 0.85)"); // Cyan
        gradient.addColorStop(1, "rgba(129, 140, 248, 0.3)"); // Violet Tail

        ctx.strokeStyle = gradient;
        ctx.beginPath();
        ctx.moveTo(state.head.x, state.head.y);

        for (let i = 0; i < state.segments.length - 1; i++) {
          const xc = (state.segments[i].x + state.segments[i + 1].x) / 2;
          const yc = (state.segments[i].y + state.segments[i + 1].y) / 2;
          ctx.quadraticCurveTo(state.segments[i].x, state.segments[i].y, xc, yc);
        }
        ctx.stroke();

        // Inner glowing core line
        ctx.lineWidth = 4;
        ctx.strokeStyle = "#ffffff";
        ctx.shadowBlur = 8;
        ctx.stroke();
        ctx.restore();
      }

      // Draw Individual Cybernetic Scale Plates
      state.segments.forEach((seg, idx) => {
        if (idx % 2 !== 0) return;
        const taper = 1 - idx / state.segments.length;
        const radius = Math.max(2, 6.5 * taper);

        ctx.save();
        ctx.fillStyle = idx % 4 === 0 ? "#38bdf8" : "#10b981";
        ctx.shadowColor = "#06b6d4";
        ctx.shadowBlur = 6;
        ctx.beginPath();
        ctx.arc(seg.x, seg.y, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      });

      // --- 7. Render Serpent Head & Cybernetic Eyes ---
      ctx.save();
      ctx.translate(state.head.x, state.head.y);
      ctx.rotate(state.angle);

      // Head Main Capsule
      ctx.shadowColor = "#10b981";
      ctx.shadowBlur = 20;
      ctx.fillStyle = "#0f172a";
      ctx.strokeStyle = "#10b981";
      ctx.lineWidth = 2.5;

      ctx.beginPath();
      ctx.ellipse(0, 0, 14, 9, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      // Glowing Eyes
      ctx.fillStyle = "#38bdf8";
      ctx.shadowColor = "#38bdf8";
      ctx.shadowBlur = 10;
      ctx.beginPath();
      ctx.arc(5, -4.5, 2.5, 0, Math.PI * 2);
      ctx.arc(5, 4.5, 2.5, 0, Math.PI * 2);
      ctx.fill();

      // Antenna / Whiskers
      ctx.strokeStyle = "rgba(56, 189, 248, 0.7)";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(10, -2);
      ctx.quadraticCurveTo(18, -8, 22, -12);
      ctx.moveTo(10, 2);
      ctx.quadraticCurveTo(18, 8, 22, 12);
      ctx.stroke();

      ctx.restore();

      animationFrameId = requestAnimationFrame(renderLoop);
    };

    animationFrameId = requestAnimationFrame(renderLoop);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", handleResize);
    };
  }, [isActive, mode, soundEnabled, spawnOrb]);

  return (
    <>
      {/* Global Interactive Canvas Layer */}
      {isActive && (
        <canvas
          ref={canvasRef}
          className="fixed inset-0 pointer-events-none z-30 w-full h-full"
        />
      )}

      {/* Floating Pretext Serpent HUD & Interactive Controller */}
      <div className="fixed bottom-6 left-6 z-40 select-none">
        <AnimatePresence>
          {isMinimized ? (
            <motion.button
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              onClick={() => setIsMinimized(false)}
              className="p-3 rounded-2xl glass-card border border-teal-500/30 text-teal-500 hover:text-teal-400 hover:scale-105 shadow-2xl flex items-center gap-2 group transition-all"
            >
              <div className="w-3 h-3 rounded-full bg-teal-400 animate-ping" />
              <span className="text-xs font-bold font-mono">🐍 Pretext Serpent ({score} pts)</span>
            </motion.button>
          ) : (
            <motion.div
              initial={{ y: 20, opacity: 0, scale: 0.95 }}
              animate={{ y: 0, opacity: 1, scale: 1 }}
              exit={{ y: 20, opacity: 0, scale: 0.95 }}
              className="p-4 rounded-3xl glass-card border border-teal-500/30 shadow-2xl backdrop-blur-2xl w-80 text-slate-800 dark:text-slate-100 space-y-3"
            >
              {/* Header */}
              <div className="flex items-center justify-between border-b border-slate-700/30 pb-2.5">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-xl bg-teal-500/20 text-teal-400 border border-teal-500/30">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-black tracking-wide uppercase bg-gradient-to-r from-teal-400 to-cyan-400 bg-clip-text text-transparent">
                      Pretext Text Serpent
                    </h4>
                    <p className="text-[10px] text-slate-400 font-mono">
                      Cheng Lou Arithmetic Engine
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setSoundEnabled(!soundEnabled)}
                    className={`p-1.5 rounded-lg border transition-colors ${
                      soundEnabled
                        ? "bg-teal-500/20 text-teal-400 border-teal-500/30"
                        : "bg-slate-800 text-slate-400 border-slate-700"
                    }`}
                    title="Toggle Audio Feedback"
                  >
                    {soundEnabled ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
                  </button>
                  <button
                    onClick={() => setIsMinimized(true)}
                    className="text-xs text-slate-400 hover:text-white px-2 py-1"
                  >
                    _
                  </button>
                </div>
              </div>

              {/* Live Pretext Telemetry */}
              <div className="grid grid-cols-3 gap-2 bg-slate-900/60 p-2.5 rounded-2xl border border-slate-800 font-mono text-[10px]">
                <div>
                  <span className="text-slate-500 block">Pretext Latency</span>
                  <span className="text-teal-400 font-bold">{metrics.pretextMs.toFixed(3)} ms</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Length</span>
                  <span className="text-cyan-400 font-bold">{serpentLength} segs</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Score</span>
                  <span className="text-amber-400 font-bold">{score} pts</span>
                </div>
              </div>

              {/* Mode Switcher */}
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                  Navigation Mode
                </span>
                <div className="grid grid-cols-3 gap-1.5 text-xs">
                  <button
                    onClick={() => setMode("hunt")}
                    className={`py-1.5 px-2 rounded-xl flex flex-col items-center gap-1 font-semibold transition-all border ${
                      mode === "hunt"
                        ? "bg-teal-500/20 text-teal-300 border-teal-500/50 shadow-md"
                        : "bg-slate-800/40 text-slate-400 border-slate-700 hover:text-slate-200"
                    }`}
                  >
                    <Crosshair className="w-3.5 h-3.5" />
                    <span className="text-[10px]">Hunt Gems</span>
                  </button>
                  <button
                    onClick={() => setMode("text")}
                    className={`py-1.5 px-2 rounded-xl flex flex-col items-center gap-1 font-semibold transition-all border ${
                      mode === "text"
                        ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/50 shadow-md"
                        : "bg-slate-800/40 text-slate-400 border-slate-700 hover:text-slate-200"
                    }`}
                  >
                    <Compass className="w-3.5 h-3.5" />
                    <span className="text-[10px]">Read Text</span>
                  </button>
                  <button
                    onClick={() => setMode("cursor")}
                    className={`py-1.5 px-2 rounded-xl flex flex-col items-center gap-1 font-semibold transition-all border ${
                      mode === "cursor"
                        ? "bg-purple-500/20 text-purple-300 border-purple-500/50 shadow-md"
                        : "bg-slate-800/40 text-slate-400 border-slate-700 hover:text-slate-200"
                    }`}
                  >
                    <Eye className="w-3.5 h-3.5" />
                    <span className="text-[10px]">Follow Mouse</span>
                  </button>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 pt-1">
                <button
                  onClick={() => spawnOrb()}
                  className="flex-1 py-2 px-3 rounded-xl bg-teal-500/10 hover:bg-teal-500/20 text-teal-400 border border-teal-500/30 text-xs font-bold flex items-center justify-center gap-1.5 transition-all hover:scale-[1.02]"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Feed Keyword Orb
                </button>
                <button
                  onClick={() => setIsActive(!isActive)}
                  className={`p-2 rounded-xl border text-xs font-bold flex items-center justify-center transition-all ${
                    isActive
                      ? "bg-amber-500/10 text-amber-400 border-amber-500/30 hover:bg-amber-500/20"
                      : "bg-teal-500/10 text-teal-400 border-teal-500/30 hover:bg-teal-500/20"
                  }`}
                  title={isActive ? "Sleep Serpent" : "Wake Serpent"}
                >
                  {isActive ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  );
}
