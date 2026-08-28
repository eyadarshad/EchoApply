"use client";

import React, { useEffect, useRef } from "react";
import { audioEngine } from "../app/AudioEngine";

/**
 * Ultra-Low Latency, Hardware-Accelerated Custom Cyber Pointer.
 * 
 * Performance Highlights:
 * 1. Zero React re-renders on mousemove / hover (Pure GPU composited DOM transforms).
 * 2. translate3d(x, y, 0) with will-change: transform runs directly on the GPU compositor thread.
 * 3. 1:1 Zero-lag precision pointer + silky 120 FPS lerped ambient aura.
 * 4. Passive event listeners ({ passive: true }) to prevent blocking browser input threads.
 * 5. Automatic coarse-pointer (mobile / tablet) and prefers-reduced-motion bypass.
 */
export default function CustomCursor() {
  const pointerRef = useRef<HTMLDivElement>(null);
  const glowRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Check for touch / coarse pointer or reduced motion preference
    if (typeof window === "undefined") return;
    if (window.matchMedia("(pointer: coarse)").matches) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let mouseX = -100;
    let mouseY = -100;
    let glowX = -100;
    let glowY = -100;
    let isVisible = false;
    let isHovered = false;
    let isClicked = false;
    let rafId: number | null = null;

    const pointerEl = pointerRef.current;
    const glowEl = glowRef.current;

    if (!pointerEl || !glowEl) return;

    // Update positions on animation frame (synced with hardware refresh rate: 60/120/144/240Hz)
    const tick = () => {
      if (isVisible) {
        // Direct 1:1 hardware pointer follow (0ms lag)
        pointerEl.style.transform = `translate3d(${mouseX - 3}px, ${mouseY - 2}px, 0) scale(${isClicked ? 0.82 : isHovered ? 1.18 : 1})`;

        // Smooth spring/lerp for ambient glow trailing
        const lerpFactor = 0.22;
        glowX += (mouseX - glowX) * lerpFactor;
        glowY += (mouseY - glowY) * lerpFactor;
        glowEl.style.transform = `translate3d(${glowX - 24}px, ${glowY - 24}px, 0) scale(${isClicked ? 1.6 : isHovered ? 1.35 : 1})`;
      }
      rafId = requestAnimationFrame(tick);
    };

    rafId = requestAnimationFrame(tick);

    const onMouseMove = (e: MouseEvent) => {
      mouseX = e.clientX;
      mouseY = e.clientY;

      if (!isVisible) {
        isVisible = true;
        glowX = mouseX;
        glowY = mouseY;
        pointerEl.style.opacity = "1";
        glowEl.style.opacity = "0.75";
      }
    };

    const onMouseDown = () => {
      isClicked = true;
      try {
        audioEngine.playClick();
      } catch {
        // Safe failover
      }
    };

    const onMouseUp = () => {
      isClicked = false;
    };

    const onMouseOver = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null;
      if (!target) return;

      const interactive =
        target.tagName === "BUTTON" ||
        target.tagName === "A" ||
        target.tagName === "INPUT" ||
        target.tagName === "SELECT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "LABEL" ||
        target.isContentEditable ||
        target.closest("button") !== null ||
        target.closest("a") !== null ||
        target.closest('[role="button"]') !== null ||
        target.classList.contains("cursor-pointer");

      if (interactive !== isHovered) {
        isHovered = interactive;
        if (isHovered) {
          pointerEl.setAttribute("data-hover", "true");
          glowEl.setAttribute("data-hover", "true");
        } else {
          pointerEl.removeAttribute("data-hover");
          glowEl.removeAttribute("data-hover");
        }
      }
    };

    const onMouseLeave = () => {
      isVisible = false;
      pointerEl.style.opacity = "0";
      glowEl.style.opacity = "0";
    };

    const onMouseEnter = () => {
      isVisible = true;
      pointerEl.style.opacity = "1";
      glowEl.style.opacity = "0.75";
    };

    const onSnakeCursorRespawn = (e: Event) => {
      const customEvent = e as CustomEvent<{ clientX: number; clientY: number }>;
      if (customEvent.detail) {
        mouseX = customEvent.detail.clientX;
        mouseY = customEvent.detail.clientY;
        glowX = mouseX;
        glowY = mouseY;
        isVisible = true;
        pointerEl.style.opacity = "1";
        glowEl.style.opacity = "0.9";
        // Warp animation pulse
        pointerEl.style.transform = `translate3d(${mouseX - 3}px, ${mouseY - 2}px, 0) scale(1.6)`;
        setTimeout(() => {
          if (pointerEl) {
            pointerEl.style.transform = `translate3d(${mouseX - 3}px, ${mouseY - 2}px, 0) scale(1)`;
          }
        }, 220);
      }
    };

    window.addEventListener("mousemove", onMouseMove, { passive: true });
    window.addEventListener("mousedown", onMouseDown, { passive: true });
    window.addEventListener("mouseup", onMouseUp, { passive: true });
    window.addEventListener("snake-cursor-respawn", onSnakeCursorRespawn);
    document.addEventListener("mouseover", onMouseOver, { passive: true });
    document.addEventListener("mouseleave", onMouseLeave, { passive: true });
    document.addEventListener("mouseenter", onMouseEnter, { passive: true });

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mousedown", onMouseDown);
      window.removeEventListener("mouseup", onMouseUp);
      window.removeEventListener("snake-cursor-respawn", onSnakeCursorRespawn);
      document.removeEventListener("mouseover", onMouseOver);
      document.removeEventListener("mouseleave", onMouseLeave);
      document.removeEventListener("mouseenter", onMouseEnter);
    };
  }, []);

  return (
    <>
      {/* 1. Ambient Dynamic Glow Aura (Smooth Trailing GPU Composited Layer) */}
      <div
        ref={glowRef}
        aria-hidden="true"
        className="fixed top-0 left-0 pointer-events-none z-[99998] rounded-full w-12 h-12 bg-teal-500/20 dark:bg-teal-400/25 blur-md opacity-0 transition-opacity duration-200 will-change-transform data-[hover=true]:bg-teal-400/35 data-[hover=true]:w-14 data-[hover=true]:h-14"
        style={{
          transform: "translate3d(-100px, -100px, 0)",
        }}
      />

      {/* 2. Sharp Precision Triangular Cyber Pointer (Zero-Lag Direct GPU Composited Layer) */}
      <div
        ref={pointerRef}
        aria-hidden="true"
        className="fixed top-0 left-0 pointer-events-none z-[99999] opacity-0 transition-opacity duration-150 will-change-transform group"
        style={{
          transform: "translate3d(-100px, -100px, 0)",
        }}
      >
        <svg
          width="26"
          height="26"
          viewBox="0 0 26 26"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="drop-shadow-[0_2px_8px_rgba(0,0,0,0.4)] pointer-svg"
        >
          <path
            d="M3 2v18.5l5.2-5.2 3.8 8.8 3.3-1.4-3.8-8.8 6.5-.4L3 2z"
            className="pointer-path fill-slate-900 dark:fill-white stroke-white dark:stroke-slate-950 stroke-[1.5] transition-colors duration-150"
          />
        </svg>
      </div>

      <style jsx global>{`
        div[data-hover="true"] .pointer-path {
          fill: #14b8a6 !important;
          stroke: #0f172a !important;
        }
        :global(.dark) div[data-hover="true"] .pointer-path {
          fill: #2dd4bf !important;
          stroke: #020617 !important;
        }
      `}</style>
    </>
  );
}
