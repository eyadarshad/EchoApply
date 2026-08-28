"use client";

import React, { useMemo, useRef, useEffect, useState } from "react";
import { prepareWithSegments, layoutWithLines, measureNaturalWidth } from "@chenglou/pretext";

interface PretextReflowProps {
  text: string;
  className?: string;
  font?: string;
  maxWidth?: number;
  lineHeight?: number;
  highlightKeywords?: string[];
  interactiveWords?: boolean;
  onWordHover?: (word: string | null, rect?: { x: number; y: number }) => void;
}

/**
 * PretextReflow
 * High-performance text rendering leveraging Cheng Lou's @chenglou/pretext arithmetic layout engine.
 * Computes sub-pixel line breaking and segment positioning with zero DOM reflow thrashing.
 */
export default function PretextReflow({
  text,
  className = "text-sm text-slate-700 dark:text-slate-300 leading-relaxed",
  font = "14px Inter, -apple-system, sans-serif",
  maxWidth = 600,
  lineHeight = 22,
  highlightKeywords = [],
  interactiveWords = false,
  onWordHover,
}: PretextReflowProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(maxWidth);
  const [computeTimeMs, setComputeTimeMs] = useState<number>(0);
  const [hoveredWordIndex, setHoveredWordIndex] = useState<string | null>(null);

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

  // Pretext Layout Pipeline: prepare segments once, layout on width change
  const layoutData = useMemo(() => {
    if (!text || typeof text !== "string") {
      return { lines: [], totalHeight: 0, naturalWidth: 0, lineCount: 0, computeMs: 0 };
    }

    const t0 = typeof performance !== "undefined" ? performance.now() : 0;
    try {
      // 1. Prepare text with segments (tokenized unicode segmentation & advance cache)
      const prepared = prepareWithSegments(text, font);
      const naturalWidth = measureNaturalWidth(prepared);
      
      // 2. Pure arithmetic line breaking & wrapping
      const targetWidth = Math.max(120, containerWidth);
      const result = layoutWithLines(prepared, targetWidth, lineHeight);
      
      const t1 = typeof performance !== "undefined" ? performance.now() : 0;
      const ms = Math.round((t1 - t0) * 1000) / 1000;

      return {
        lines: result.lines || [],
        totalHeight: result.height || (result.lines.length * lineHeight),
        lineCount: result.lineCount || result.lines.length,
        naturalWidth,
        computeMs: ms,
      };
    } catch (err) {
      // Fallback for non-standard environments
      const rawLines = text.split("\n").filter(Boolean);
      return {
        lines: rawLines.map((l) => ({ text: l, width: containerWidth })),
        totalHeight: rawLines.length * lineHeight,
        lineCount: rawLines.length,
        naturalWidth: containerWidth,
        computeMs: 0,
      };
    }
  }, [text, font, containerWidth, lineHeight]);

  useEffect(() => {
    if (layoutData.computeMs > 0) {
      setComputeTimeMs(layoutData.computeMs);
    }
  }, [layoutData.computeMs]);

  // Keyword highlight matcher
  const highlightRegex = useMemo(() => {
    if (!highlightKeywords || highlightKeywords.length === 0) return null;
    const escaped = highlightKeywords
      .filter((k) => k && k.trim().length > 1)
      .map((k) => k.replace(/[-\/\\^$*+?.()|[\]{}]/g, "\\$&"));
    if (escaped.length === 0) return null;
    return new RegExp(`\\b(${escaped.join("|")})\\b`, "gi");
  }, [highlightKeywords]);

  const renderLineContent = (lineText: string, lineIndex: number) => {
    if (!highlightRegex && !interactiveWords) {
      return lineText;
    }

    const words = lineText.split(/(\s+)/);
    return words.map((word, wIdx) => {
      const wordKey = `${lineIndex}-${wIdx}`;
      const isKeyword = highlightRegex ? Boolean(word.match(highlightRegex)) : false;
      const isHovered = hoveredWordIndex === wordKey;

      if (!word.trim()) {
        return <span key={wIdx}>{word}</span>;
      }

      return (
        <span
          key={wIdx}
          className={`inline-block transition-all duration-150 rounded px-0.5 ${
            isKeyword
              ? "bg-teal-500/15 text-teal-600 dark:text-teal-300 font-semibold border-b border-teal-500/40"
              : ""
          } ${
            interactiveWords
              ? "hover:bg-sky-500/20 hover:text-sky-600 dark:hover:text-sky-300 cursor-pointer select-text"
              : ""
          } ${isHovered ? "scale-105 -translate-y-0.5 text-teal-500" : ""}`}
          onMouseEnter={(e) => {
            if (interactiveWords) {
              setHoveredWordIndex(wordKey);
              if (onWordHover) {
                const rect = e.currentTarget.getBoundingClientRect();
                onWordHover(word, { x: rect.left, y: rect.top });
              }
            }
          }}
          onMouseLeave={() => {
            if (interactiveWords) {
              setHoveredWordIndex(null);
              if (onWordHover) onWordHover(null);
            }
          }}
        >
          {word}
        </span>
      );
    });
  };

  return (
    <div
      ref={containerRef}
      className={`pretext-text-node relative w-full transition-all duration-200 ${className}`}
      data-pretext-lines={layoutData.lineCount}
      data-pretext-ms={computeTimeMs}
    >
      {layoutData.lines.map((line: any, idx: number) => (
        <div
          key={idx}
          className="pretext-line my-0.5 flex flex-wrap items-baseline"
          style={{ minHeight: `${lineHeight}px` }}
        >
          {renderLineContent(line.text, idx)}
        </div>
      ))}
    </div>
  );
}
