"use client";

import React, { useRef, useEffect, useState } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";

export type AnimationPreset = "hero-rise" | "word-fade" | "scramble-decode" | "counter-roll";

interface KineticTextProps {
  children?: React.ReactNode;
  text?: string;
  as?: "h1" | "h2" | "h3" | "h4" | "p" | "span" | "div";
  className?: string;
  animation?: AnimationPreset;
  delay?: number;
  duration?: number;
  targetNumber?: number; // for counter-roll
}

const GLYPHS = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789!@#$%^&*<>[]{}";

export default function KineticText({
  children,
  text,
  as = "h1",
  className = "",
  animation = "hero-rise",
  delay = 0,
  duration = 0.8,
  targetNumber,
}: KineticTextProps) {
  const rawText = text || (typeof children === "string" ? children : "");
  const containerRef = useRef<HTMLElement>(null);
  const [displayText, setDisplayText] = useState(rawText);

  // 1. Scramble Decode Mode
  useEffect(() => {
    if (animation !== "scramble-decode" || !rawText) return;

    // Check prefers-reduced-motion
    if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setDisplayText(rawText);
      return;
    }

    let iteration = 0;
    const totalIterations = rawText.length * 3;
    let animationFrame: number;

    const timeout = setTimeout(() => {
      const run = () => {
        setDisplayText(
          rawText
            .split("")
            .map((char, index) => {
              if (char === " ") return " ";
              if (index < iteration / 3) {
                return rawText[index];
              }
              return GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
            })
            .join("")
        );

        if (iteration < totalIterations) {
          iteration++;
          animationFrame = requestAnimationFrame(run);
        } else {
          setDisplayText(rawText);
        }
      };
      run();
    }, delay * 1000);

    return () => {
      clearTimeout(timeout);
      if (animationFrame) cancelAnimationFrame(animationFrame);
    };
  }, [rawText, animation, delay]);

  // 2. GSAP Animations (hero-rise, word-fade, counter-roll)
  useGSAP(
    () => {
      if (!containerRef.current) return;

      // Check prefers-reduced-motion
      if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        return;
      }

      if (animation === "counter-roll" && typeof targetNumber === "number") {
        const obj = { val: 0 };
        gsap.to(obj, {
          val: targetNumber,
          duration: duration || 1.5,
          delay,
          ease: "power3.out",
          onUpdate: () => {
            if (containerRef.current) {
              containerRef.current.innerText = Math.round(obj.val).toString();
            }
          },
        });
        return;
      }

      if (animation === "hero-rise") {
        const chars = containerRef.current.querySelectorAll(".kinetic-char");
        if (chars.length > 0) {
          gsap.fromTo(
            chars,
            {
              opacity: 0,
              y: 36,
              rotateX: -70,
              transformOrigin: "50% 100%",
            },
            {
              opacity: 1,
              y: 0,
              rotateX: 0,
              stagger: 0.02,
              duration,
              delay,
              ease: "back.out(1.7)",
            }
          );
        }
      } else if (animation === "word-fade") {
        const words = containerRef.current.querySelectorAll(".kinetic-word");
        if (words.length > 0) {
          gsap.fromTo(
            words,
            {
              opacity: 0,
              y: 20,
              filter: "blur(4px)",
            },
            {
              opacity: 1,
              y: 0,
              filter: "blur(0px)",
              stagger: 0.04,
              duration,
              delay,
              ease: "power3.out",
            }
          );
        }
      }
    },
    { scope: containerRef, dependencies: [rawText, animation, delay, duration, targetNumber] }
  );

  const Tag = as as any;

  // For counter-roll
  if (animation === "counter-roll" && typeof targetNumber === "number") {
    return (
      <Tag ref={containerRef} className={className} aria-label={targetNumber.toString()}>
        0
      </Tag>
    );
  }

  // For scramble-decode
  if (animation === "scramble-decode") {
    return (
      <Tag ref={containerRef} className={className} aria-label={rawText}>
        {displayText}
      </Tag>
    );
  }

  // For hero-rise: split text by words and characters with overflow-hidden mask
  if (animation === "hero-rise") {
    const words = rawText.split(" ");
    return (
      <Tag ref={containerRef} className={className} aria-label={rawText}>
        {words.map((word, wIdx) => (
          <span key={wIdx} className="inline-block whitespace-nowrap overflow-hidden mr-[0.28em] py-0.5">
            {word.split("").map((char, cIdx) => (
              <span
                key={cIdx}
                className="kinetic-char inline-block will-change-transform"
                style={{ perspective: "1000px" }}
              >
                {char}
              </span>
            ))}
          </span>
        ))}
      </Tag>
    );
  }

  // For word-fade: split text into words
  if (animation === "word-fade") {
    const words = rawText.split(" ");
    return (
      <Tag ref={containerRef} className={className} aria-label={rawText}>
        {words.map((word, idx) => (
          <span key={idx} className="kinetic-word inline-block mr-[0.25em] will-change-transform">
            {word}
          </span>
        ))}
      </Tag>
    );
  }

  return (
    <Tag ref={containerRef} className={className}>
      {children || rawText}
    </Tag>
  );
}
