"use client";

import React, { useState } from "react";
import { CheckCircle2, AlertTriangle, XCircle, HelpCircle, ChevronDown } from "lucide-react";
import PretextReflow from "./PretextReflow";

export interface AuditCriterionItem {
  id: string;
  name: string;
  max_points: number;
  awarded_points: number;
  status: string; // 'looks_good' | 'could_be_stronger' | 'needs_attention' | 'could_not_check'
  finding: string;
  action?: string | null;
  scoring_method?: string;
}

interface AuditCriterionCardProps {
  criterion: AuditCriterionItem;
}

export default function AuditCriterionCard({ criterion }: AuditCriterionCardProps) {
  const [isOpen, setIsOpen] = useState(false);

  // Status configuration
  let statusBadge = {
    label: "Looks good",
    icon: CheckCircle2,
    badgeClasses: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
    dotClasses: "bg-emerald-500",
  };

  if (criterion.status === "could_be_stronger") {
    statusBadge = {
      label: "Could be stronger",
      icon: AlertTriangle,
      badgeClasses: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
      dotClasses: "bg-amber-500",
    };
  } else if (criterion.status === "needs_attention") {
    statusBadge = {
      label: "Needs attention",
      icon: XCircle,
      badgeClasses: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20",
      dotClasses: "bg-rose-500",
    };
  } else if (criterion.status === "could_not_check") {
    statusBadge = {
      label: "Could not check",
      icon: HelpCircle,
      badgeClasses: "bg-slate-500/10 text-slate-500 dark:text-slate-400 border-slate-500/20",
      dotClasses: "bg-slate-400",
    };
  }

  const IconComponent = statusBadge.icon;

  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/40 dark:bg-slate-900/40 backdrop-blur-md p-4 transition-all duration-200 hover:border-teal-500/30 hover:shadow-md">
      {/* Header row */}
      <div
        className="flex items-center justify-between gap-3 cursor-pointer select-none"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-3 min-w-0">
          <IconComponent className={`w-5 h-5 flex-shrink-0 ${statusBadge.badgeClasses.split(" ")[1]}`} />
          <div className="min-w-0">
            <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200 truncate">
              {criterion.name}
            </h4>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Status Badge */}
          <span
            className={`hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${statusBadge.badgeClasses}`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${statusBadge.dotClasses}`} />
            {statusBadge.label}
          </span>

          {/* Points */}
          <span className="text-xs font-bold px-2 py-0.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
            {criterion.awarded_points}/{criterion.max_points} pts
          </span>

          <ChevronDown
            className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${
              isOpen ? "rotate-180" : ""
            }`}
          />
        </div>
      </div>

      {/* Expanded Content */}
      {isOpen && (
        <div className="mt-3.5 pt-3.5 border-t border-slate-100 dark:border-slate-800/80 space-y-2.5 text-xs">
          {/* Mobile Badge */}
          <div className="sm:hidden">
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${statusBadge.badgeClasses}`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${statusBadge.dotClasses}`} />
              {statusBadge.label}
            </span>
          </div>

          {/* What we found (Pretext Zero-Reflow Text) */}
          <div>
            <span className="font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider text-[10px]">
              What our engine found:
            </span>
            <div className="mt-0.5">
              <PretextReflow
                text={criterion.finding}
                className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed"
                highlightKeywords={["ATS", "LinkedIn", "GitHub", "Experience", "Projects", "Skills", "Education", "XYZ", "metrics", "quantified"]}
                interactiveWords={true}
              />
            </div>
          </div>

          {/* Action Recommendation (Pretext Zero-Reflow Text) */}
          {criterion.action && (
            <div className="p-2.5 rounded-xl bg-teal-50/50 dark:bg-teal-950/20 border border-teal-500/20 text-teal-900 dark:text-teal-200">
              <span className="font-bold uppercase tracking-wider text-[10px] text-teal-700 dark:text-teal-400">
                Recommended Action:
              </span>
              <div className="mt-0.5 font-medium">
                <PretextReflow
                  text={criterion.action}
                  className="text-xs text-teal-950 dark:text-teal-200 leading-relaxed"
                  highlightKeywords={["ATS", "headings", "Experience", "Education", "Projects", "numbers", "action verbs", "bullets", "headline"]}
                  interactiveWords={true}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
