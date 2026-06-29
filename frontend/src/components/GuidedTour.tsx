"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, Search, Play, CheckCircle } from "lucide-react";

interface Step {
  id: number;
  title: string;
  shortDesc: string;
  icon: React.ReactNode;
  details: string[];
}

export default function GuidedTour() {
  const [activeStep, setActiveStep] = useState<number>(1);

  const steps: Step[] = [
    {
      id: 1,
      title: "1. Upload & Enrich",
      shortDesc: "Setup your professional profile",
      icon: <FileText className="w-5 h-5" />,
      details: [
        "Upload any standard PDF resume to instantly extract details using Gemini.",
        "Add your GitHub profile to enrich your credentials with real repository statistics.",
        "Or fill out your profile manually to build your baseline resume from scratch."
      ]
    },
    {
      id: 2,
      title: "2. Discover & Match",
      shortDesc: "Find matching jobs with smart math",
      icon: <Search className="w-5 h-5" />,
      details: [
        "Search through thousands of live listings aggregated from major platforms.",
        "Our engine ranks jobs using a balanced 50% semantic and 50% keyword blend.",
        "View direct match percentages and transparent explanations for every job listing."
      ]
    },
    {
      id: 3,
      title: "3. Tailor & Apply",
      shortDesc: "Customize and automate applications",
      icon: <Play className="w-5 h-5" />,
      details: [
        "Tailor your resume specifically for the target job description to match ATS criteria.",
        "Review bullet points in the Truthfulness Gate to ensure no details were fabricated.",
        "Opt-in to the browser agent to auto-fill forms and draft answers in a safe sandbox."
      ]
    }
  ];

  return (
    <div className="w-full max-w-4xl mx-auto rounded-3xl glass-card p-6 md:p-8 space-y-6 text-left animate-fade-in">
      <div>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-indigo-500/20 bg-indigo-500/5 text-indigo-600 dark:text-indigo-400 text-xs font-semibold uppercase tracking-wider mb-2">
          New to SmartApply?
        </div>
        <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">
          How It Works: 3-Step Guided Workspace
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Follow this guided tour to go from an uploaded PDF to a tailored resume and auto-filled application in minutes.
        </p>
      </div>

      {/* Stepper Tabs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {steps.map((step) => {
          const isActive = activeStep === step.id;
          return (
            <button
              key={step.id}
              onClick={() => setActiveStep(step.id)}
              className={`relative flex items-center gap-4 p-4 rounded-2xl border text-left transition duration-300 group overflow-hidden ${
                isActive
                  ? "border-indigo-500/30 bg-indigo-500/5 dark:bg-indigo-500/10 shadow-sm"
                  : "border-slate-200 dark:border-slate-800 bg-white/30 dark:bg-slate-900/10 hover:border-slate-300 dark:hover:border-slate-700"
              }`}
            >
              {/* Highlight active underline capsule */}
              {isActive && (
                <motion.div
                  layoutId="active-step-capsule"
                  className="absolute inset-0 bg-indigo-500/5 dark:bg-indigo-500/10 z-0 pointer-events-none"
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                />
              )}

              <div
                className={`p-3 rounded-xl z-10 transition duration-300 ${
                  isActive
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-200"
                }`}
              >
                {step.icon}
              </div>

              <div className="space-y-0.5 z-10">
                <h4 className="text-sm font-bold text-slate-800 dark:text-slate-200">
                  {step.title}
                </h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-normal">
                  {step.shortDesc}
                </p>
              </div>
            </button>
          );
        })}
      </div>

      {/* Step Detail Panel */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800/80 bg-white/20 dark:bg-slate-900/10 p-6 min-h-[140px] flex items-center">
        <AnimatePresence mode="wait">
          {steps.map((step) => {
            if (step.id !== activeStep) return null;
            return (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className="w-full space-y-3"
              >
                <h4 className="text-sm font-semibold text-indigo-600 dark:text-indigo-400">
                  Key Steps & Features:
                </h4>
                <ul className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {step.details.map((detail, idx) => (
                    <li
                      key={idx}
                      className="flex gap-2.5 items-start text-xs text-slate-600 dark:text-slate-300 leading-relaxed bg-white/30 dark:bg-slate-900/20 p-3.5 rounded-xl border border-slate-200/50 dark:border-slate-800/50 shadow-sm"
                    >
                      <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                      <span>{detail}</span>
                    </li>
                  ))}
                </ul>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
