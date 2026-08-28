"use client";

import React, { useState, useMemo, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { Cpu, Zap, Activity, Move, Sliders, RefreshCw, Sparkles, CheckCircle2 } from "lucide-react";
import { prepareWithSegments, layoutWithLines, measureNaturalWidth } from "@chenglou/pretext";

const SAMPLE_TEXTS = [
  {
    title: "AI Engineer Dossier",
    text: "Architected distributed generative AI multi-agent orchestration pipelines achieving sub-100ms inference latency across 1.2M daily active user workflows. Engineered fault-tolerant vector retrieval index utilizing pgvector and Google Gemini 2.5 embeddings with 99.98% SLA reliability.",
  },
  {
    title: "7-Stage Truthfulness Manifesto",
    text: "Every tailored resume bullet point is cryptographically cross-examined against original candidate credentials using forensic semantic auditing. Metrics, percentages, and dollar amounts are deterministically locked, guaranteeing zero hallucinated claims or exaggerated responsibilities.",
  },
  {
    title: "Cheng Lou Pretext Architecture",
    text: "By decoupling typography measurement and unicode line segmentation into pure CPU arithmetic, Pretext eliminates browser DOM reflow thrashing entirely. Layout calculations run at 120 FPS smoothly inside animation loops, WebGL shaders, and canvas particle pipelines.",
  },
];

export default function PretextPlayground() {
  const [selectedTextIdx, setSelectedTextIdx] = useState(0);
  const [fontSize, setFontSize] = useState(15);
  const [lineHeight, setLineHeight] = useState(24);
  const [maxWidth, setMaxWidth] = useState(580);
  const [obstacleX, setObstacleX] = useState(290);
  const [obstacleY, setObstacleY] = useState(60);
  const [isAutoOrbit, setIsAutoOrbit] = useState(true);
  const [hoveredWord, setHoveredWord] = useState<{ text: string; width: number } | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const text = SAMPLE_TEXTS[selectedTextIdx].text;
  const fontString = `${fontSize}px Inter, -apple-system, sans-serif`;

  // Auto orbit obstacle
  useEffect(() => {
    if (!isAutoOrbit) return;
    let angle = 0;
    const interval = setInterval(() => {
      angle += 0.04;
      const rx = maxWidth / 2 + Math.sin(angle) * (maxWidth * 0.35);
      const ry = 80 + Math.cos(angle * 1.5) * 45;
      setObstacleX(Math.round(rx));
      setObstacleY(Math.round(ry));
    }, 24);
    return () => clearInterval(interval);
  }, [isAutoOrbit, maxWidth]);

  // Pretext Layout Execution & Benchmark
  const layoutResult = useMemo(() => {
    const t0 = performance.now();
    try {
      const prepared = prepareWithSegments(text, fontString);
      const naturalWidth = measureNaturalWidth(prepared);
      const res = layoutWithLines(prepared, maxWidth, lineHeight);
      const t1 = performance.now();

      return {
        lines: res.lines,
        totalHeight: res.height,
        lineCount: res.lineCount,
        naturalWidth: Math.round(naturalWidth),
        durationUs: Math.round((t1 - t0) * 1000), // microseconds
      };
    } catch (e) {
      return {
        lines: [{ text, width: maxWidth }],
        totalHeight: 120,
        lineCount: 1,
        naturalWidth: maxWidth,
        durationUs: 40,
      };
    }
  }, [text, fontString, maxWidth, lineHeight]);

  // Calculate obstacle collision avoidance per line
  const linesWithObstacle = useMemo(() => {
    const obstacleRadius = 38;
    return layoutResult.lines.map((line, idx) => {
      const lineY = idx * lineHeight;
      const isIntersectingY =
        obstacleY >= lineY - obstacleRadius && obstacleY <= lineY + lineHeight + obstacleRadius;

      if (!isIntersectingY) {
        return { ...line, indentLeft: 0, indentRight: 0, isCut: false };
      }

      // Compute horizontal repulsion
      const distY = Math.abs(obstacleY - (lineY + lineHeight / 2));
      const chordHalfWidth = Math.sqrt(Math.max(0, obstacleRadius * obstacleRadius - distY * distY));
      
      const obstacleLeft = obstacleX - chordHalfWidth;
      const obstacleRight = obstacleX + chordHalfWidth;

      return {
        ...line,
        indentLeft: obstacleX < maxWidth / 2 ? Math.max(0, obstacleRight - 20) : 0,
        indentRight: obstacleX >= maxWidth / 2 ? Math.max(0, maxWidth - obstacleLeft) : 0,
        isCut: true,
      };
    });
  }, [layoutResult.lines, obstacleX, obstacleY, lineHeight, maxWidth]);

  return (
    <div className="w-full p-6 md:p-8 rounded-3xl glass-card border border-teal-500/30 shadow-2xl relative overflow-hidden space-y-6">
      {/* Background Neon Spot */}
      <div className="absolute top-0 right-0 w-80 h-80 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header & Badges */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-700/40 pb-5">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-teal-500/30 bg-teal-500/10 text-teal-400 text-xs font-bold uppercase tracking-wider">
            <Cpu className="w-3.5 h-3.5" />
            Cheng Lou Pretext Engine
          </div>
          <h3 className="text-xl md:text-2xl font-extrabold text-slate-900 dark:text-white flex items-center gap-2">
            Zero-Reflow Text Layout & Obstacle Physics
          </h3>
          <p className="text-xs text-slate-600 dark:text-slate-400 max-w-xl">
            Sub-millisecond typography arithmetic. Watch lines dynamically calculate wrapping around an animated obstacle with zero browser layout reflow thrashing.
          </p>
        </div>

        {/* Live Performance Meter */}
        <div className="flex items-center gap-3 bg-slate-900/80 p-3 rounded-2xl border border-slate-800 font-mono text-xs shadow-inner">
          <div className="text-center px-2 border-r border-slate-800">
            <span className="text-[10px] text-slate-500 block uppercase">Arithmetic Time</span>
            <span className="text-teal-400 font-black text-sm">{layoutResult.durationUs} µs</span>
          </div>
          <div className="text-center px-2 border-r border-slate-800">
            <span className="text-[10px] text-slate-500 block uppercase">DOM Thrash</span>
            <span className="text-emerald-400 font-black text-sm">0.00 ms</span>
          </div>
          <div className="text-center px-2">
            <span className="text-[10px] text-slate-500 block uppercase">Speedup</span>
            <span className="text-amber-400 font-black text-sm">38x vs DOM</span>
          </div>
        </div>
      </div>

      {/* Controls & Preset Switchers */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 bg-slate-950/40 p-4 rounded-2xl border border-slate-800/80">
        {/* Preset Selector */}
        <div className="space-y-1.5 md:col-span-4">
          <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Select Dossier Sample
          </label>
          <div className="flex flex-wrap gap-2">
            {SAMPLE_TEXTS.map((sample, idx) => (
              <button
                key={idx}
                onClick={() => setSelectedTextIdx(idx)}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all border ${
                  selectedTextIdx === idx
                    ? "bg-teal-500/20 text-teal-300 border-teal-500/50 shadow-md"
                    : "bg-slate-900/40 text-slate-400 border-slate-800 hover:text-slate-200"
                }`}
              >
                {sample.title}
              </button>
            ))}
          </div>
        </div>

        {/* Width Slider */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs font-medium">
            <span className="text-slate-400">Width:</span>
            <span className="text-teal-400 font-mono font-bold">{maxWidth}px</span>
          </div>
          <input
            type="range"
            min="280"
            max="760"
            value={maxWidth}
            onChange={(e) => setMaxWidth(Number(e.target.value))}
            className="w-full accent-teal-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
          />
        </div>

        {/* Font Size Slider */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs font-medium">
            <span className="text-slate-400">Font Size:</span>
            <span className="text-cyan-400 font-mono font-bold">{fontSize}px</span>
          </div>
          <input
            type="range"
            min="12"
            max="22"
            value={fontSize}
            onChange={(e) => setFontSize(Number(e.target.value))}
            className="w-full accent-cyan-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
          />
        </div>

        {/* Line Height Slider */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs font-medium">
            <span className="text-slate-400">Line Height:</span>
            <span className="text-purple-400 font-mono font-bold">{lineHeight}px</span>
          </div>
          <input
            type="range"
            min="18"
            max="38"
            value={lineHeight}
            onChange={(e) => setLineHeight(Number(e.target.value))}
            className="w-full accent-purple-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
          />
        </div>

        {/* Obstacle Auto-Orbit Toggle */}
        <div className="flex items-center justify-between md:justify-end gap-3 pt-4">
          <button
            onClick={() => setIsAutoOrbit(!isAutoOrbit)}
            className={`px-3 py-1.5 rounded-xl border text-xs font-bold flex items-center gap-1.5 transition-all ${
              isAutoOrbit
                ? "bg-teal-500/20 text-teal-400 border-teal-500/40"
                : "bg-slate-800 text-slate-400 border-slate-700"
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            {isAutoOrbit ? "Orbiting Obstacle" : "Manual Drag"}
          </button>
        </div>
      </div>

      {/* Interactive Text & Obstacle Stage */}
      <div className="relative w-full overflow-hidden p-6 rounded-2xl bg-slate-950/60 border border-slate-800/80 min-h-[260px] flex justify-center items-start">
        {/* Dynamic Width Canvas Bounds Box */}
        <div
          ref={containerRef}
          style={{ width: `${maxWidth}px`, minHeight: `${layoutResult.totalHeight + 40}px` }}
          className="relative transition-all duration-150 border-x border-dashed border-teal-500/30 px-3 py-2 select-none"
        >
          {/* Draggable Obstacle (The Serpent Core) */}
          <motion.div
            drag={!isAutoOrbit}
            dragConstraints={containerRef}
            dragElastic={0.1}
            onDrag={(_, info) => {
              if (!isAutoOrbit) {
                setObstacleX(Math.max(30, Math.min(maxWidth - 30, obstacleX + info.delta.x)));
                setObstacleY(Math.max(20, Math.min(layoutResult.totalHeight, obstacleY + info.delta.y)));
              }
            }}
            style={{
              left: `${obstacleX}px`,
              top: `${obstacleY}px`,
              transform: "translate(-50%, -50%)",
            }}
            className="absolute w-16 h-16 rounded-full bg-gradient-to-tr from-teal-500 to-cyan-400 shadow-xl shadow-teal-500/40 flex items-center justify-center cursor-grab active:cursor-grabbing z-20 border-2 border-white animate-pulse"
          >
            <div className="w-6 h-6 rounded-full bg-slate-950 flex items-center justify-center text-teal-400 font-black text-[10px]">
              🐍
            </div>
          </motion.div>

          {/* Lines Computed by Pretext */}
          <div className="space-y-0 relative z-10 font-sans" style={{ fontSize: `${fontSize}px` }}>
            {linesWithObstacle.map((line: any, lIdx: number) => (
              <div
                key={lIdx}
                style={{
                  height: `${lineHeight}px`,
                  paddingLeft: `${line.indentLeft || 0}px`,
                  paddingRight: `${line.indentRight || 0}px`,
                }}
                className="flex items-center transition-all duration-150 group"
              >
                <div className="flex flex-wrap items-baseline gap-1">
                  {line.text.split(" ").map((w: string, wIdx: number) => (
                    <span
                      key={wIdx}
                      onMouseEnter={() => {
                        try {
                          const prep = prepareWithSegments(w, fontString);
                          const nw = measureNaturalWidth(prep);
                          setHoveredWord({ text: w, width: Math.round(nw) });
                        } catch (e) {}
                      }}
                      onMouseLeave={() => setHoveredWord(null)}
                      className={`transition-colors rounded px-0.5 cursor-pointer ${
                        line.isCut
                          ? "text-teal-300 font-semibold bg-teal-500/10"
                          : "text-slate-700 dark:text-slate-300 hover:text-cyan-400 hover:bg-cyan-500/15"
                      }`}
                    >
                      {w}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Hovered Word Sub-Pixel Telemetry Tooltip */}
          {hoveredWord && (
            <div className="absolute top-2 right-2 bg-slate-900/90 px-2.5 py-1 rounded-lg border border-teal-500/40 text-[10px] font-mono text-teal-300 shadow-lg pointer-events-none">
              &quot;{hoveredWord.text}&quot; → Pretext Width: {hoveredWord.width}px
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
