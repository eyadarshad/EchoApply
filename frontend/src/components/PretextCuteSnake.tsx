"use client";

import React, { useEffect, useRef } from "react";
import { pretextSnakeEngine, SnakeState } from "../lib/pretextSnakeEngine";

interface SnakePalette {
  body: string;
  camo: string;
  belly: string;
  rib: string;
  cheeks: string;
  nostrils: string;
  mouth: string;
  tongue: string;
  eyeBase: string;
  shadowColor: string;
  shadowBlur: number;
}

const LIGHT_PALETTE: SnakePalette = {
  body: "#72a348", // Meadow Green (matches user reference pic)
  camo: "#527930", // Deep Olive Spots
  belly: "#fbf3a3", // Custard Cream Underbelly
  rib: "#dfcf68", // Warm Gold Ribs
  cheeks: "#ff6378", // Coral Pink Blush
  nostrils: "#4a6828", // Forest Green Nostrils
  mouth: "#38241b", // Dark Chocolate Smile
  tongue: "#ff4f68", // Sweet Berry Tongue
  eyeBase: "#231713", // Deep Glossy Obsidian
  shadowColor: "rgba(0, 0, 0, 0.15)",
  shadowBlur: 8,
};

const DARK_PALETTE: SnakePalette = {
  body: "#14b8a6", // Luminous Cyan Teal (matches Dark Mode theme)
  camo: "#0f766e", // Deep Marine Teal Spots
  belly: "#99f6e4", // Radiant Aqua Mint Glow Underbelly
  rib: "#2dd4bf", // Bright Cyan Ribs
  cheeks: "#fb7185", // Vivid Neon Rose Glow Blush
  nostrils: "#134e4a", // Deep Emerald Nostrils
  mouth: "#042f2e", // Deep Obsidian Cyan Smile
  tongue: "#f43f5e", // Radiant Coral Tongue
  eyeBase: "#020617", // Deep Onyx
  shadowColor: "rgba(20, 184, 166, 0.4)", // Teal Cyber Aura Glow
  shadowBlur: 14,
};

export default function PretextCuteSnake() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Animation timers for facial expressions
  const faceStateRef = useRef({
    isBlinking: false,
    nextBlinkTime: 0,
    tongueOut: false,
    nextTongueTime: 0,
    tonguePhase: 0,
  });

  useEffect(() => {
    pretextSnakeEngine.start();
    return () => pretextSnakeEngine.stop();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const handleResize = () => {
      if (!canvas) return;
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    handleResize();
    window.addEventListener("resize", handleResize);

    const handleSnakeUpdate = (state: SnakeState) => {
      if (!ctx || !canvas) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (!state.active) return;

      const now = performance.now();
      const face = faceStateRef.current;

      const scrollX = window.scrollX || window.pageXOffset || 0;
      const scrollY = window.scrollY || window.pageYOffset || 0;

      const screenHeadX = state.head.x - scrollX;
      const screenHeadY = state.head.y - scrollY;

      // Skip drawing if completely off-screen
      if (
        screenHeadX < -150 ||
        screenHeadX > canvas.width + 150 ||
        screenHeadY < -150 ||
        screenHeadY > canvas.height + 150
      ) {
        return;
      }

      // Check current theme dynamically per frame
      const isDarkMode =
        typeof document !== "undefined" &&
        document.documentElement.classList.contains("dark");
      const palette = isDarkMode ? DARK_PALETTE : LIGHT_PALETTE;

      // 1. Kawaii eye blinking timer
      if (!state.isInjured && !state.isVictorious && now > face.nextBlinkTime) {
        face.isBlinking = true;
        face.nextBlinkTime = now + 2400 + Math.random() * 2600;
        setTimeout(() => {
          face.isBlinking = false;
        }, 130);
      }

      // 2. Playful forked tongue flick timer
      if (!state.isInjured && now > face.nextTongueTime) {
        face.tongueOut = true;
        face.nextTongueTime = now + 1800 + Math.random() * 2200;
        face.tonguePhase = 0;
      }

      if (face.tongueOut) {
        face.tonguePhase += 0.2;
        if (face.tonguePhase > Math.PI) {
          face.tongueOut = false;
        }
      }

      ctx.save();
      ctx.globalAlpha = 1.0;

      // ==========================================
      // A. CHUBBY BODY & SEGMENTED UNDERBELLY
      // ==========================================
      const segCount = state.segments.length;

      // 1. Draw Upper Body Base Tube
      if (segCount > 2) {
        ctx.save();
        ctx.lineCap = "round";
        ctx.lineJoin = "round";

        ctx.lineWidth = 22;
        ctx.strokeStyle = palette.body;
        ctx.beginPath();
        ctx.moveTo(screenHeadX, screenHeadY);
        for (let i = 0; i < segCount - 1; i++) {
          const seg1 = state.segments[i];
          const seg2 = state.segments[i + 1];
          const xc = (seg1.x + seg2.x) / 2 - scrollX;
          const yc = (seg1.y + seg2.y) / 2 - scrollY;
          ctx.quadraticCurveTo(seg1.x - scrollX, seg1.y - scrollY, xc, yc);
        }
        ctx.stroke();

        // 2. Draw Segmented Creamy/Mint Underbelly
        ctx.lineWidth = 13;
        ctx.strokeStyle = palette.belly;
        ctx.beginPath();
        ctx.moveTo(screenHeadX, screenHeadY);
        for (let i = 0; i < segCount - 1; i++) {
          const seg1 = state.segments[i];
          const seg2 = state.segments[i + 1];
          const xc = (seg1.x + seg2.x) / 2 - scrollX;
          const yc = (seg1.y + seg2.y) / 2 - scrollY;
          ctx.quadraticCurveTo(seg1.x - scrollX, seg1.y - scrollY, xc, yc);
        }
        ctx.stroke();
        ctx.restore();
      }

      // 3. Draw Body Scales, Dark Olive/Teal Spots, and Underbelly Ribs
      state.segments.forEach((seg, idx) => {
        const taper = 1 - idx / segCount;
        const radius = Math.max(3.5, 11 * taper);

        const prev = idx === 0 ? state.head : state.segments[idx - 1];
        const segAngle = Math.atan2(prev.y - seg.y, prev.x - seg.x);

        ctx.save();
        ctx.translate(seg.x - scrollX, seg.y - scrollY);
        ctx.rotate(segAngle);

        // Top Back
        ctx.fillStyle = palette.body;
        ctx.beginPath();
        ctx.arc(0, 0, radius, 0, Math.PI * 2);
        ctx.fill();

        // Belly Arc
        ctx.fillStyle = palette.belly;
        ctx.beginPath();
        ctx.arc(0, radius * 0.25, radius * 0.85, 0, Math.PI);
        ctx.fill();

        // Subtle Belly Rib Line
        if (idx % 2 === 0) {
          ctx.strokeStyle = palette.rib;
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.arc(0, radius * 0.25, radius * 0.8, 0.2, Math.PI - 0.2);
          ctx.stroke();
        }

        // Camouflage Spots on upper back
        if (idx % 3 === 0 && idx < segCount - 2) {
          ctx.fillStyle = palette.camo;
          ctx.beginPath();
          ctx.ellipse(0, -radius * 0.45, radius * 0.4, radius * 0.25, 0.2, 0, Math.PI * 2);
          ctx.fill();
        }

        ctx.restore();
      });

      // Perky Tail Tip
      if (segCount > 0) {
        const tail = state.segments[segCount - 1];
        ctx.save();
        ctx.translate(tail.x - scrollX, tail.y - scrollY);
        ctx.fillStyle = palette.body;
        ctx.beginPath();
        ctx.arc(0, 0, 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }

      // ==========================================
      // B. ADORABLE KAWAII HEAD
      // ==========================================
      ctx.save();
      const shakeOffset = state.isInjured
        ? Math.sin(now * 0.08) * 3
        : state.isVictorious
        ? Math.sin(now * 0.04) * 2
        : 0;
      ctx.translate(screenHeadX + shakeOffset, screenHeadY);
      ctx.rotate(state.angle);

      const headRadius = 24;

      // 1. Soft Theme Glow / Shadow
      ctx.shadowColor = palette.shadowColor;
      ctx.shadowBlur = palette.shadowBlur;
      ctx.shadowOffsetY = isDarkMode ? 0 : 3;

      // 2. Base Head Outline
      ctx.fillStyle = palette.body;
      ctx.beginPath();
      ctx.arc(0, 0, headRadius, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowColor = "transparent";

      // 3. Camouflage Spots on Top of Head
      ctx.fillStyle = palette.camo;
      ctx.beginPath();
      ctx.ellipse(-2, -14, 7, 5, -0.1, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.ellipse(-13, -8, 5, 4, -0.3, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.ellipse(11, -10, 6, 4.5, 0.2, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.ellipse(2, -19, 4, 3, 0.1, 0, Math.PI * 2);
      ctx.fill();

      // 4. Creamy Custard / Mint Lower Face & Cheeks
      ctx.fillStyle = palette.belly;
      ctx.beginPath();
      ctx.moveTo(-headRadius, 2);
      ctx.bezierCurveTo(-headRadius, 18, -12, headRadius + 1, 0, headRadius + 1);
      ctx.bezierCurveTo(12, headRadius + 1, headRadius, 18, headRadius, 2);
      ctx.bezierCurveTo(headRadius * 0.7, -4, -headRadius * 0.7, -4, -headRadius, 2);
      ctx.closePath();
      ctx.fill();

      // 5. Cute Blushing Cheeks
      ctx.fillStyle = palette.cheeks;
      ctx.beginPath();
      ctx.ellipse(-14, 6, 4.8, 3.2, -0.05, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.ellipse(14, 6, 4.8, 3.2, 0.05, 0, Math.PI * 2);
      ctx.fill();

      // 6. Cute Nostril Dots
      ctx.fillStyle = palette.nostrils;
      ctx.beginPath();
      ctx.arc(-2.2, 2.5, 0.9, 0, Math.PI * 2);
      ctx.arc(2.2, 2.5, 0.9, 0, Math.PI * 2);
      ctx.fill();

      // 7. Cat-like `w` Mouth Smile
      ctx.strokeStyle = palette.mouth;
      ctx.lineWidth = 1.8;
      ctx.lineCap = "round";

      if (state.isInjured) {
        // Cute wavy dazed mouth ~
        ctx.beginPath();
        ctx.moveTo(-5, 7);
        ctx.quadraticCurveTo(-2, 4, 0, 7);
        ctx.quadraticCurveTo(2, 10, 5, 7);
        ctx.stroke();
      } else if (state.isVictorious) {
        // Big open happy smile :D
        ctx.fillStyle = palette.tongue;
        ctx.beginPath();
        ctx.arc(0, 5, 5.5, 0, Math.PI);
        ctx.fill();
        ctx.stroke();
      } else {
        // Normal happy `w` smile
        ctx.beginPath();
        ctx.arc(-3.2, 6, 3.4, 0.1, Math.PI - 0.2);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(3.2, 6, 3.4, 0.2, Math.PI - 0.1);
        ctx.stroke();
      }

      // 8. Playful Forked Tongue Flicking Out
      if (face.tongueOut && !state.isInjured) {
        const tongueLength = 7 + Math.sin(face.tonguePhase) * 6;
        ctx.fillStyle = palette.tongue;
        ctx.strokeStyle = palette.tongue;
        ctx.lineWidth = 2.4;
        ctx.lineCap = "round";

        ctx.beginPath();
        ctx.moveTo(0, 9);
        ctx.lineTo(0, 9 + tongueLength);
        ctx.stroke();

        ctx.lineWidth = 1.6;
        ctx.beginPath();
        ctx.moveTo(0, 9 + tongueLength);
        ctx.lineTo(-3, 9 + tongueLength + 3.5);
        ctx.moveTo(0, 9 + tongueLength);
        ctx.lineTo(3, 9 + tongueLength + 3.5);
        ctx.stroke();
      }

      // 9. Eyes
      const eyeY = 0;
      const eyeXOffset = 10;
      const eyeRadius = 5.2;

      if (state.isInjured) {
        // Dizzy Spiral Eyes
        ctx.strokeStyle = palette.eyeBase;
        ctx.lineWidth = 2.0;

        ctx.beginPath();
        ctx.arc(-eyeXOffset, eyeY, 3.5, 0, Math.PI * 1.5);
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(eyeXOffset, eyeY, 3.5, 0, Math.PI * 1.5);
        ctx.stroke();

        // Cute Little Head Bump / Swelling with Band-Aid 🩹
        ctx.save();
        ctx.fillStyle = "#ffb3ba";
        ctx.beginPath();
        ctx.arc(2, -headRadius + 2, 5.5, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = "#fef08a";
        ctx.fillRect(-1, -headRadius - 1.5, 6, 4);
        ctx.fillRect(1, -headRadius - 3.5, 2, 8);
        ctx.restore();
      } else if (state.isVictorious) {
        // Joyful squinting anime eyes (> ‿ <)
        ctx.strokeStyle = palette.eyeBase;
        ctx.lineWidth = 2.4;
        ctx.lineCap = "round";

        // Left >
        ctx.beginPath();
        ctx.moveTo(-eyeXOffset - 4, eyeY - 2);
        ctx.lineTo(-eyeXOffset + 3, eyeY);
        ctx.lineTo(-eyeXOffset - 4, eyeY + 2);
        ctx.stroke();

        // Right <
        ctx.beginPath();
        ctx.moveTo(eyeXOffset + 4, eyeY - 2);
        ctx.lineTo(eyeXOffset - 3, eyeY);
        ctx.lineTo(eyeXOffset + 4, eyeY + 2);
        ctx.stroke();
      } else if (face.isBlinking) {
        // Happy curved eyes ^ ^
        ctx.strokeStyle = palette.eyeBase;
        ctx.lineWidth = 2.4;
        ctx.beginPath();
        ctx.arc(-eyeXOffset, eyeY + 1, 4.2, Math.PI + 0.2, -0.2);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(eyeXOffset, eyeY + 1, 4.2, Math.PI + 0.2, -0.2);
        ctx.stroke();
      } else {
        // Big Glossy Catchlight Eyes (From Image)
        ctx.fillStyle = palette.eyeBase;
        ctx.beginPath();
        ctx.arc(-eyeXOffset, eyeY, eyeRadius, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(-eyeXOffset - 1.4, eyeY - 1.6, 2.1, 0, Math.PI * 2);
        ctx.fill();

        ctx.beginPath();
        ctx.arc(-eyeXOffset + 1.8, eyeY + 1.8, 1.0, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = palette.eyeBase;
        ctx.beginPath();
        ctx.arc(eyeXOffset, eyeY, eyeRadius, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(eyeXOffset - 1.4, eyeY - 1.6, 2.1, 0, Math.PI * 2);
        ctx.fill();

        ctx.beginPath();
        ctx.arc(eyeXOffset + 1.8, eyeY + 1.8, 1.0, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.restore();

      // ==========================================
      // C. DIZZY ORBITING STARS (When Injured)
      // ==========================================
      if (state.isInjured) {
        ctx.save();
        const orbitAngle = (now * 0.008) % (Math.PI * 2);
        const starColors = ["#facc15", "#fbbf24", "#fef08a"];

        for (let i = 0; i < 3; i++) {
          const a = orbitAngle + (i * Math.PI * 2) / 3;
          const starX = screenHeadX + Math.cos(a) * 28;
          const starY = screenHeadY - 14 + Math.sin(a) * 10;

          ctx.fillStyle = starColors[i];
          ctx.shadowColor = "#facc15";
          ctx.shadowBlur = 8;
          ctx.font = "bold 14px sans-serif";
          ctx.fillText("💫", starX - 7, starY + 5);
        }
        ctx.restore();
      }

      // ==========================================
      // D. VICTORY CELEBRATION SPARKLES (When Catches Cursor)
      // ==========================================
      if (state.victorySparkles.length > 0) {
        ctx.save();
        state.victorySparkles.forEach((sp) => {
          const sx = sp.x - scrollX;
          const sy = sp.y - scrollY;
          ctx.globalAlpha = Math.max(0, sp.life);
          ctx.fillStyle = sp.color;
          ctx.shadowColor = sp.color;
          ctx.shadowBlur = 6;
          ctx.beginPath();
          ctx.arc(sx, sy, 3.5 * sp.life, 0, Math.PI * 2);
          ctx.fill();
        });
        ctx.restore();
      }

      ctx.restore();
    };

    const unsubscribe = pretextSnakeEngine.subscribe(handleSnakeUpdate);

    return () => {
      unsubscribe();
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none w-full h-full"
      style={{ zIndex: 15 }}
    />
  );
}
