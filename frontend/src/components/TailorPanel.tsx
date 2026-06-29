"use client";

import React, { useState } from "react";
import { Sparkles, Terminal, CheckCircle2, AlertTriangle, AlertCircle, RefreshCw, BarChart2 } from "lucide-react";

interface ResumeParsedData {
  name: string;
  email: string;
  phone?: string;
  links: string[];
  skills: string[];
  education: any[];
  experience: any[];
  projects: any[];
  anchor_line?: string;
  highlights_strip?: any[];
}

interface TailorPanelProps {
  user_id: string;
  parsed_resume: ResumeParsedData;
  onTailorSuccess: (
    tailoredResume: ResumeParsedData,
    gapAnalysis: any,
    truthfulnessReport: any,
    atsScore: number
  ) => void;
  initialJdText?: string;
  onBack?: () => void;
}

const PIPELINE_STEPS = [
  "Stage 1: Analyzing Job Description details...",
  "Stage 2: Aligning optimization techniques...",
  "Stage 3: Running semantic gap analysis...",
  "Stage 4: Executing targeted factual rewrite...",
  "Stage 5: Designing tagline and highlights strip...",
  "Stage 6: Running Truthfulness Gate audit...",
  "Stage 7: Preparing final resume layout..."
];

export default function TailorPanel({ user_id, parsed_resume, onTailorSuccess, initialJdText = "", onBack }: TailorPanelProps) {
  const [jdText, setJdText] = useState(initialJdText);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(0);

  // Simulated active step progression for visual feedback while waiting for API
  const startStepProgression = () => {
    setCurrentStep(0);
    const interval = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev < PIPELINE_STEPS.length - 1) {
          return prev + 1;
        }
        clearInterval(interval);
        return prev;
      });
    }, 2800);
    return interval;
  };

  const handleTailor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!jdText.trim()) return;

    setLoading(true);
    setError(null);
    const progressInterval = startStepProgression();

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
      const response = await fetch(`${backendUrl}/tailor`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: user_id,
          job_id: "job-tailoring-session", // temp session job id
          jd_text: jdText,
          parsed_resume: parsed_resume
        }),
      });

      clearInterval(progressInterval);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to tailor resume.");
      }

      const data = await response.json();
      setCurrentStep(PIPELINE_STEPS.length);
      
      // Delay slightly so the user sees the final step check off
      setTimeout(() => {
        onTailorSuccess(
          data.content_json,
          data.gap_analysis,
          data.truthfulness_report,
          data.ats_score
        );
      }, 500);

    } catch (err: any) {
      clearInterval(progressInterval);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 animate-fade-in">
      <div className="p-6 md:p-8 rounded-3xl glass-card relative overflow-hidden">
        {/* Glow effect */}
        <div className="absolute -top-12 -right-12 w-48 h-48 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none" />

        <div className="flex justify-between items-start mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-500/10 text-indigo-400 rounded-xl">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-850 dark:text-slate-100">Step 2: Resume Tailoring Pipeline</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">Paste the job listing description to tailor your experience factual matches.</p>
            </div>
          </div>
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              className="px-3.5 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-655 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-bold transition shadow-sm"
            >
              &larr; Back to Profile
            </button>
          )}
        </div>

        {!loading ? (
          <form onSubmit={handleTailor} className="space-y-6">
            <div className="space-y-2 text-left">
              <label htmlFor="jd-textarea" className="text-xs font-bold text-slate-550 dark:text-slate-300 uppercase tracking-wider">
                Job Description text
              </label>
              <textarea
                id="jd-textarea"
                rows={8}
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                placeholder="Paste the requirements, role description, and skills listed in the job opening..."
                className="w-full px-4 py-3 rounded-2xl bg-white dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 text-sm focus:border-indigo-500/60 focus:outline-none transition duration-200 text-slate-800 dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-600 font-light resize-y shadow-sm"
                required
              />
            </div>

            <button
              type="submit"
              disabled={!jdText.trim()}
              className="w-full py-3.5 rounded-2xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-semibold text-sm transition duration-200 flex items-center justify-center gap-2 disabled:opacity-50 shadow-sm"
            >
              <RefreshCw className="w-4 h-4" />
              Analyze & Tailor Bullet Points
            </button>

            {error && (
              <div className="p-4 rounded-xl border border-rose-500/20 bg-rose-500/10 text-rose-350 dark:text-rose-300 text-sm flex items-start gap-2">
                <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold">Tailoring Pipeline Failed</span>
                  <p className="text-xs text-rose-450 dark:text-rose-400 mt-1">{error}</p>
                </div>
              </div>
            )}
          </form>
        ) : (
          <div className="py-8 space-y-8 animate-pulse">
            <div className="flex flex-col items-center justify-center space-y-4">
              <div className="relative flex items-center justify-center">
                <div className="w-12 h-12 rounded-full border-4 border-indigo-500/20 border-t-indigo-500 animate-spin" />
                <Terminal className="w-5 h-5 text-indigo-400 absolute" />
              </div>
              <div className="text-center">
                <h4 className="text-sm font-semibold text-slate-805 dark:text-slate-200">Executing 7-Stage Pipeline</h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">This will take ~10-15 seconds as it audits metrics and skills.</p>
              </div>
            </div>

            {/* Pipeline progress bar steps list */}
            <div className="max-w-md mx-auto space-y-3.5 bg-slate-100/50 dark:bg-slate-950/40 p-5 rounded-2xl border border-slate-200 dark:border-slate-850">
              {PIPELINE_STEPS.map((step, idx) => (
                <div key={idx} className="flex items-center gap-3 text-xs text-left">
                  {idx < currentStep ? (
                    <CheckCircle2 className="w-4.5 h-4.5 text-emerald-500 dark:text-emerald-400 shrink-0" />
                  ) : idx === currentStep ? (
                    <div className="w-4.5 h-4.5 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin shrink-0" />
                  ) : (
                    <div className="w-4.5 h-4.5 rounded-full border border-slate-250 dark:border-slate-800 shrink-0" />
                  )}
                  <span className={idx <= currentStep ? "text-slate-800 dark:text-slate-200 font-medium" : "text-slate-400 dark:text-slate-600"}>
                    {step}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
