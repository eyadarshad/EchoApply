"use client";

import React, { useEffect, useState, useRef } from "react";
import { motion, useMotionValue, useSpring } from "framer-motion";
import { audioEngine } from "../app/AudioEngine";

export default function CustomCursor() {
  const [isHovered, setIsHovered] = useState(false);
  const [isClicked, setIsClicked] = useState(false);
  const [isVisible, setIsVisible] = useState(false);

  // Raw cursor coordinate values
  const cursorX = useMotionValue(-100);
  const cursorY = useMotionValue(-100);

  // Spring animations for trailing ring inertia
  const springConfig = { stiffness: 350, damping: 28 };
  const springX = useSpring(cursorX, springConfig);
  const springY = useSpring(cursorY, springConfig);

  useEffect(() => {
    const moveCursor = (e: MouseEvent) => {
      cursorX.set(e.clientX);
      cursorY.set(e.clientY);
      if (!isVisible) setIsVisible(true);
    };

    const handleMouseLeave = () => setIsVisible(false);
    const handleMouseEnter = () => setIsVisible(true);

    const handleMouseDown = () => {
      setIsClicked(true);
      // Play programmatically synthesized audio click chime
      audioEngine.playClick();
    };
    
    const handleMouseUp = () => setIsClicked(false);

    // Event delegation to capture hovers on all current/future interactive tags
    const handleMouseOver = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null;
      if (!target) return;
      
      const isInteractive =
        target.tagName === "BUTTON" ||
        target.tagName === "A" ||
        target.tagName === "LABEL" ||
        target.tagName === "INPUT" ||
        target.tagName === "SELECT" ||
        target.tagName === "TEXTAREA" ||
        target.closest("button") ||
        target.closest("a") ||
        target.closest('[role="button"]') ||
        target.classList.contains("cursor-pointer");

      setIsHovered(!!isInteractive);
    };

    window.addEventListener("mousemove", moveCursor);
    document.addEventListener("mouseleave", handleMouseLeave);
    document.addEventListener("mouseenter", handleMouseEnter);
    window.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("mouseup", handleMouseUp);
    window.addEventListener("mouseover", handleMouseOver);

    return () => {
      window.removeEventListener("mousemove", moveCursor);
      document.removeEventListener("mouseleave", handleMouseLeave);
      document.removeEventListener("mouseenter", handleMouseEnter);
      window.removeEventListener("mousedown", handleMouseDown);
      window.removeEventListener("mouseup", handleMouseUp);
      window.removeEventListener("mouseover", handleMouseOver);
    };
  }, [cursorX, cursorY, isVisible]);

  if (!isVisible) return null;

  return (
    <>
      {/* 1. Core Pointer Center Dot */}
      <motion.div
        className="fixed w-2 h-2 bg-indigo-500 rounded-full pointer-events-none z-50 mix-blend-difference"
        style={{
          left: cursorX,
          top: cursorY,
          translateX: "-50%",
          translateY: "-50%",
        }}
        animate={{
          scale: isClicked ? 0.6 : isHovered ? 1.5 : 1,
          backgroundColor: isHovered ? "#818cf8" : "#6366f1",
        }}
        transition={{ type: "spring", stiffness: 450, damping: 25 }}
      />

      {/* 2. Trailing Ring with Orbiting Nodes */}
      <motion.div
        className="fixed w-8 h-8 border border-indigo-500/50 dark:border-indigo-400/40 rounded-full pointer-events-none z-50 flex items-center justify-center"
        style={{
          left: springX,
          top: springY,
          translateX: "-50%",
          translateY: "-50%",
        }}
        animate={{
          scale: isClicked ? 1.3 : isHovered ? 1.8 : 1,
          borderColor: isHovered ? "#818cf8" : "rgba(99, 102, 241, 0.4)",
        }}
        transition={{ type: "spring", stiffness: 350, damping: 28 }}
      >
        {/* Orbit wrapper for rotators */}
        <motion.div
          className="relative w-full h-full"
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 4, ease: "linear" }}
        >
          {/* Node 1 */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1.5 h-1.5 bg-indigo-400 rounded-full shadow-sm shadow-indigo-500/50" />
          {/* Node 2 */}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 w-1.5 h-1.5 bg-violet-400 rounded-full shadow-sm shadow-violet-500/50" />
        </motion.div>
      </motion.div>
    </>
  );
}
