"use client";

import React, { useMemo, useRef, useEffect, useState } from "react";
import { prepareWithSegments, layoutWithLines } from "@chenglou/pretext";
import { pretextSnakeEngine, SnakeState } from "../lib/pretextSnakeEngine";

interface PretextFluidTextProps {
  text: string;
  className?: string;
  font?: string;
  lineHeight?: number;
  as?: "p" | "span" | "div" | "h1" | "h2" | "h3";
}

interface WordLayout {
  word: string;
  lineIdx: number;
  wordIdx: number;
  baseX: number;
  baseY: number;
}

/**
 * PretextFluidText
 * Real-time text parting component powered by Cheng Lou's @chenglou/pretext layout arithmetic.
 * Words dynamically dodge and part around the crawling snake in real-time with zero browser layout reflows!
 */
export default function PretextFluidText({
  text,
  className = "text-slate-600 dark:text-slate-400 text-sm md:text-base leading-relaxed font-light",
  font = "15px Inter, -apple-system, sans-serif",
  lineHeight = 26,
  as: Component = "p",
}: PretextFluidTextProps) {
  const containerRef = useRef<HTMLElement>(null);
  const wordsRef = useRef<Map<string, HTMLSpanElement>>(new Map());
  const [containerWidth, setContainerWidth] = useState(600);

  // ResizeObserver for dynamic width
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width > 0) {
          setContainerWidth(Math.floor(entry.contentRect.width));
        }
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Compute exact Pretext lines & word coordinate layout
  const layout = useMemo(() => {
    if (!text || typeof text !== "string") {
      return { lines: [], words: [] };
    }

    try {
      const prepared = prepareWithSegments(text, font);
      const res = layoutWithLines(prepared, Math.max(120, containerWidth), lineHeight);

      const wordsList: WordLayout[] = [];
      res.lines.forEach((line, lIdx) => {
        const rawWords = line.text.split(/(\s+)/);
        let currX = 0;

        rawWords.forEach((token, wIdx) => {
          if (!token.trim()) {
            currX += 6; // approximate space
            return;
          }

          // Measure single token width with Pretext
          let tokenWidth = 30;
          try {
            const prepToken = prepareWithSegments(token, font);
            const tokenRes = layoutWithLines(prepToken, 500, lineHeight);
            tokenWidth = tokenRes.lines[0]?.width || 30;
          } catch (e) {}

          wordsList.push({
            word: token,
            lineIdx: lIdx,
            wordIdx: wIdx,
            baseX: currX,
            baseY: lIdx * lineHeight,
          });

          currX += tokenWidth + 5;
        });
      });

      return { lines: res.lines, words: wordsList };
    } catch (err) {
      // Fallback
      return {
        lines: [{ text, width: containerWidth }],
        words: text.split(" ").map((w, idx) => ({
          word: w,
          lineIdx: 0,
          wordIdx: idx,
          baseX: idx * 40,
          baseY: 0,
        })),
      };
    }
  }, [text, font, containerWidth, lineHeight]);

  // Subscribe to 60FPS Snake Engine updates and apply sub-pixel parting displacement
  useEffect(() => {
    const handleSnakeMove = (snake: SnakeState) => {
      if (!containerRef.current || !snake.active) return;
      const rect = containerRef.current.getBoundingClientRect();

      // Check if snake is near this text block
      const margin = 50;
      const isSnakeNear =
        snake.head.x >= rect.left - margin &&
        snake.head.x <= rect.right + margin &&
        snake.head.y >= rect.top - margin &&
        snake.head.y <= rect.bottom + margin;

      const repulsionRadius = 45; // Radius around snake body that pushes text aside

      layout.words.forEach((w) => {
        const key = `${w.lineIdx}-${w.wordIdx}`;
        const el = wordsRef.current.get(key);
        if (!el) return;

        if (!isSnakeNear) {
          // Reset transform smoothly
          if (el.style.transform && el.style.transform !== "none") {
            el.style.transform = "none";
            el.style.color = "";
            el.style.textShadow = "";
          }
          return;
        }

        // Absolute viewport coordinate of word center
        const wordX = rect.left + w.baseX + 15;
        const wordY = rect.top + w.baseY + lineHeight / 2;

        let totalDispX = 0;
        let totalDispY = 0;
        let minDistance = Infinity;

        // Check head repulsion
        const hDx = wordX - snake.head.x;
        const hDy = wordY - snake.head.y;
        const hDist = Math.hypot(hDx, hDy);
        if (hDist < repulsionRadius && hDist > 0) {
          const force = (1 - hDist / repulsionRadius) * 26; // up to 26px repulsion
          totalDispX += (hDx / hDist) * force;
          totalDispY += (hDy / hDist) * force * 0.7;
          minDistance = Math.min(minDistance, hDist);
        }

        // Check first 8 body segments repulsion
        const checkCount = Math.min(8, snake.segments.length);
        for (let i = 0; i < checkCount; i++) {
          const seg = snake.segments[i];
          const sDx = wordX - seg.x;
          const sDy = wordY - seg.y;
          const sDist = Math.hypot(sDx, sDy);
          if (sDist < repulsionRadius && sDist > 0) {
            const force = (1 - sDist / repulsionRadius) * 20 * (1 - i / checkCount);
            totalDispX += (sDx / sDist) * force;
            totalDispY += (sDy / sDist) * force * 0.5;
            minDistance = Math.min(minDistance, sDist);
          }
        }

        // Apply dynamic parting transform
        if (minDistance < repulsionRadius) {
          el.style.transform = `translate(${totalDispX.toFixed(1)}px, ${totalDispY.toFixed(1)}px) scale(1.03)`;
          el.style.color = "var(--snake-text-glow, #10b981)";
          el.style.textShadow = "0 0 8px rgba(16, 185, 129, 0.4)";
          el.style.transition = "transform 0.06s ease-out";
        } else if (el.style.transform && el.style.transform !== "none") {
          el.style.transform = "none";
          el.style.color = "";
          el.style.textShadow = "";
          el.style.transition = "transform 0.32s cubic-bezier(0.2, 0.9, 0.3, 1), color 0.28s";
        }
      });
    };

    const unsubscribe = pretextSnakeEngine.subscribe(handleSnakeMove);
    return () => unsubscribe();
  }, [layout.words, lineHeight]);

  return (
    <Component
      ref={containerRef as any}
      className={`pretext-fluid-text relative transition-all duration-200 select-text ${className}`}
    >
      {layout.lines.map((line, lIdx) => (
        <span key={lIdx} className="block my-0.5" style={{ minHeight: `${lineHeight}px` }}>
          {line.text.split(/(\s+)/).map((token, wIdx) => {
            if (!token.trim()) {
              return <span key={wIdx}>{token}</span>;
            }
            const key = `${lIdx}-${wIdx}`;
            return (
              <span
                key={wIdx}
                ref={(node) => {
                  if (node) wordsRef.current.set(key, node);
                  else wordsRef.current.delete(key);
                }}
                className="pretext-word-token inline-block transition-transform duration-75 will-change-transform"
              >
                {token}
              </span>
            );
          })}
        </span>
      ))}
    </Component>
  );
}
