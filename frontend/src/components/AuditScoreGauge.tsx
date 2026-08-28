"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { TrendingUp, Award, Sparkles, AlertCircle } from "lucide-react";
import KineticText from "./KineticText";

interface AuditScoreGaugeProps {
  score: number;
  maxScore?: number;
  qualityLabel?: string;
  previousScore?: number | null;
  scoreDelta?: number | null;
  variant?: "teal" | "linkedin";
  size?: "md" | "lg";
}

export default function AuditScoreGauge({
  score,
  maxScore = 100,
  qualityLabel,
  previousScore,
  scoreDelta,
  variant = "teal",
  size = "lg",
}: AuditScoreGaugeProps) {
  const [animatedScore, setAnimatedScore] = useState(0);
  const radius = size === "lg" ? 82 : 64;
  const strokeWidth = size === "lg" ? 14 : 10;
  const circumference = 2 * Math.PI * radius;
  const viewBoxSize = (radius + strokeWidth) * 2;

  // Tier color selection
  let color = "#0d9488"; // default teal
  let bgGlow = "rgba(13, 148, 136, 0.15)";
  let badgeColor = "bg-teal-500/10 text-teal-600 dark:text-teal-400 border-teal-500/20";

  if (variant === "linkedin") {
    color = score >= 75 ? "#0a66c2" : score >= 50 ? "#0284c7" : "#e11d48";
    bgGlow = "rgba(10, 102, 194, 0.15)";
    badgeColor = "bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20";
  } else {
    if (score >= 85) {
      color = "#10b981"; // Emerald
      bgGlow = "rgba(16, 185, 129, 0.18)";
      badgeColor = "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20";
    } else if (score >= 70) {
      color = "#0d9488"; // Teal
      bgGlow = "rgba(13, 148, 136, 0.15)";
      badgeColor = "bg-teal-500/10 text-teal-600 dark:text-teal-400 border-teal-500/20";
    } else if (score >= 50) {
      color = "#f59e0b"; // Amber
      bgGlow = "rgba(245, 158, 11, 0.15)";
      badgeColor = "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20";
    } else {
      color = "#f43f5e"; // Rose
      bgGlow = "rgba(244, 63, 94, 0.15)";
      badgeColor = "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20";
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedScore(score);
    }, 100);
    return () => clearTimeout(timer);
  }, [score]);

  const offset = circumference - (animatedScore / maxScore) * circumference;

  return (
    <div className="flex flex-col items-center justify-center p-6 rounded-3xl glass-card relative overflow-hidden border border-teal-500/15 shadow-xl transition-all duration-300">
      {/* Background Ambient Glow */}
      <div
        className="absolute inset-0 pointer-events-none blur-3xl opacity-40 transition-colors duration-700"
        style={{ backgroundColor: bgGlow }}
      />

      <div className="relative flex items-center justify-center">
        {/* SVG Circular Progress Gauge */}
        <svg
          width={viewBoxSize}
          height={viewBoxSize}
          className="transform -rotate-90 transition-all duration-300"
        >
          {/* Background Track */}
          <circle
            cx={radius + strokeWidth}
            cy={radius + strokeWidth}
            r={radius}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-slate-200 dark:text-slate-800"
            fill="transparent"
          />
          {/* Progress Stroke */}
          <circle
            cx={radius + strokeWidth}
            cy={radius + strokeWidth}
            r={radius}
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            fill="transparent"
            style={{
              transition: "stroke-dashoffset 1.4s cubic-bezier(0.16, 1, 0.3, 1)",
            }}
          />
        </svg>

        {/* Center Score Display */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <div className="flex items-baseline">
            <KineticText
              as="span"
              animation="counter-roll"
              targetNumber={score}
              duration={1.4}
              className="text-4xl md:text-5xl font-black text-slate-900 dark:text-white tracking-tight"
            />
            <span className="text-slate-400 text-lg font-bold ml-0.5">/{maxScore}</span>
          </div>
          <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-0.5">
            Audit Score
          </span>
        </div>
      </div>

      {/* Quality Badge */}
      {qualityLabel && (
        <div className="mt-4 flex flex-col items-center gap-1.5 z-10">
          <span
            className={`inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-bold border uppercase tracking-wider ${badgeColor}`}
          >
            {score >= 75 ? (
              <Award className="w-3.5 h-3.5" />
            ) : score >= 50 ? (
              <Sparkles className="w-3.5 h-3.5" />
            ) : (
              <AlertCircle className="w-3.5 h-3.5" />
            )}
            {qualityLabel}
          </span>

          {/* Delta comparison badge if previous score exists */}
          {scoreDelta !== null && scoreDelta !== undefined && (
            <span
              className={`inline-flex items-center gap-1 text-xs font-semibold ${
                scoreDelta >= 0 ? "text-emerald-500" : "text-rose-500"
              }`}
            >
              <TrendingUp className={`w-3.5 h-3.5 ${scoreDelta < 0 ? "rotate-180" : ""}`} />
              {scoreDelta >= 0 ? `+${scoreDelta}` : scoreDelta} points from previous audit
            </span>
          )}
        </div>
      )}
    </div>
  );
}
