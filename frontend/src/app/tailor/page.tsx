"use client";

import React, { useState, useEffect } from "react";
import Navbar from "@/components/Navbar";
import PageHero from "@/components/PageHero";
import TailorPanel from "@/components/TailorPanel";
import TemplateSelector from "@/components/TemplateSelector";
import { useAuth } from "@/context/AuthContext";
import { Sparkles, FileText, ArrowRight, RefreshCw, UploadCloud, CheckCircle2, TrendingUp } from "lucide-react";
import { toast } from "sonner";

export default function TailorStudioPage() {
  const { user_id } = useAuth();
  const effectiveUserId = user_id || "00000000-0000-0000-0000-000000000001";

  const [parsedResume, setParsedResume] = useState<any>(null);
  const [tailoredResume, setTailoredResume] = useState<any>(null);
  const [gapAnalysis, setGapAnalysis] = useState<any>(null);
  const [atsScore, setAtsScore] = useState<number | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("smartapply_parsed_resume");
      if (stored) {
        try {
          setParsedResume(JSON.parse(stored));
        } catch (e) {
          console.error("Failed to parse saved resume:", e);
        }
      }
    }
  }, []);

  const handleTailorSuccess = (
    tailored: any,
    gap: any,
    truthReport: any,
    score: number
  ) => {
    setTailoredResume(tailored);
    setGapAnalysis(gap);
    setAtsScore(score);
    toast.success("Resume tailored successfully with 100% truthfulness verification!");
  };

  return (
    <div className="min-h-screen bg-transparent text-slate-900 dark:text-white flex flex-col items-center">
      {/* Navbar */}
      <Navbar />

      {/* Main Container */}
      <main className="w-full max-w-5xl px-4 pt-24 pb-16 space-y-8">
        {/* Page Hero */}
        <PageHero
          badge="7-Stage AI Tailoring Engine"
          title="AI Resume Tailoring Studio"
          subtitle="Align your bullet points, keywords, and technical accomplishments directly to the target job description with 100% truthfulness guarantees."
          breadcrumbs={[
            { label: "Home", href: "/" },
            { label: "Application Suite", href: "/tailor" },
            { label: "AI Tailoring Studio" },
          ]}
        />

        {/* State 1: No Resume Uploaded */}
        {!parsedResume && (
          <div className="p-8 md:p-12 rounded-3xl glass-card border border-slate-200 dark:border-slate-800 text-center space-y-4 max-w-xl mx-auto">
            <div className="w-16 h-16 rounded-2xl bg-teal-500/10 text-teal-600 dark:text-teal-400 flex items-center justify-center mx-auto border border-teal-500/20">
              <UploadCloud className="w-8 h-8" />
            </div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">
              No Resume Uploaded Yet
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Please upload or parse your resume first so the AI engine can analyze your real experience and align it with target job descriptions.
            </p>
            <a
              href="/#resume-workspace"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-semibold text-sm transition shadow-lg shadow-teal-600/20"
            >
              <FileText className="w-4 h-4" />
              <span>Upload Resume on Home Page</span>
            </a>
          </div>
        )}

        {/* State 2: Tailoring Form */}
        {parsedResume && !tailoredResume && (
          <div className="w-full max-w-4xl mx-auto">
            <TailorPanel
              user_id={effectiveUserId}
              parsed_resume={parsedResume}
              onTailorSuccess={handleTailorSuccess}
            />
          </div>
        )}

        {/* State 3: Tailored Result & Preview */}
        {tailoredResume && (
          <div className="w-full max-w-4xl mx-auto space-y-6 animate-fadeIn">
            {/* Score Banner */}
            <div className="p-6 rounded-3xl glass-card border border-emerald-500/20 flex flex-col sm:flex-row items-center justify-between gap-4 bg-emerald-500/5">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">
                    Tailoring Completed
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Your resume has been rewritten to match the target job description.
                  </p>
                </div>
              </div>

              {atsScore !== null && (
                <div className="flex items-center gap-2 px-4 py-2 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 font-bold text-sm">
                  <TrendingUp className="w-4 h-4" />
                  <span>ATS Match: {atsScore}%</span>
                </div>
              )}

              <button
                onClick={() => setTailoredResume(null)}
                className="inline-flex items-center gap-1.5 text-xs text-teal-600 dark:text-teal-400 hover:underline font-semibold"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Tailor for Another Job
              </button>
            </div>

            {/* Template Selector & PDF Exporter */}
            <TemplateSelector
              parsed_resume={tailoredResume}
            />
          </div>
        )}
      </main>
    </div>
  );
}
