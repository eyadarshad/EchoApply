"use client";

import React from "react";
import { motion } from "framer-motion";
import { Sparkles, Clock, TrendingUp, ArrowRight } from "lucide-react";

export interface TopChangeItem {
  rank: number;
  action: string;
  potential_increase: number;
  estimated_effort: string;
  rationale: string;
}

interface TopChangesRoadmapProps {
  changes: TopChangeItem[];
  onApplyAction?: (action: TopChangeItem) => void;
  actionCtaLabel?: string;
}

export default function TopChangesRoadmap({
  changes,
  onApplyAction,
  actionCtaLabel = "Fix with AI Tailor",
}: TopChangesRoadmapProps) {
  if (!changes || changes.length === 0) return null;

  return (
    <div className="w-full space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-xl bg-teal-500/10 text-teal-600 dark:text-teal-400 border border-teal-500/20">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              Start with these 3 changes
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Ranked by score impact and recruiter discovery value
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {changes.map((item, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: idx * 0.1 }}
            className="flex flex-col justify-between p-5 rounded-3xl glass-card border border-teal-500/15 relative overflow-hidden group hover:border-teal-500/35 hover:shadow-xl transition-all duration-300"
          >
            {/* Top Rank & Badges */}
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                {/* Rank Number Circle */}
                <span className="w-8 h-8 rounded-2xl bg-gradient-to-tr from-teal-600 to-emerald-400 text-white font-extrabold text-sm flex items-center justify-center shadow-md">
                  #{item.rank}
                </span>

                {/* Score Boost */}
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                  <TrendingUp className="w-3 h-3" />
                  Up to +{item.potential_increase} pts
                </span>
              </div>

              {/* Action Title */}
              <h4 className="text-sm font-bold text-slate-900 dark:text-white leading-snug group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                {item.action}
              </h4>

              {/* Rationale */}
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                {item.rationale}
              </p>
            </div>

            {/* Effort & Quick CTA */}
            <div className="mt-4 pt-3 border-t border-slate-200/60 dark:border-slate-800/60 flex items-center justify-between text-xs">
              <span className="inline-flex items-center gap-1 text-slate-500 dark:text-slate-400 text-[11px] font-medium">
                <Clock className="w-3 h-3 text-slate-400" />
                {item.estimated_effort}
              </span>

              {onApplyAction && (
                <button
                  onClick={() => onApplyAction(item)}
                  className="inline-flex items-center gap-1 font-semibold text-teal-600 dark:text-teal-400 hover:text-teal-700 dark:hover:text-teal-300 transition-colors"
                >
                  {actionCtaLabel}
                  <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                </button>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
