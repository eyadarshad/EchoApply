"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import PageHero from "@/components/PageHero";
import AuditScoreGauge from "@/components/AuditScoreGauge";
import AuditCriterionCard from "@/components/AuditCriterionCard";
import TopChangesRoadmap, { TopChangeItem } from "@/components/TopChangesRoadmap";
import KineticText from "@/components/KineticText";
import PretextReflow from "@/components/PretextReflow";
import { apiFetch, getBackendUrl } from "@/lib/api";
import {
  UploadCloud,
  FileText,
  Sparkles,
  ChevronDown,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ArrowRight,
  RefreshCw,
  Eye,
  FileSearch,
  Zap,
} from "lucide-react";
import { toast } from "sonner";

interface AuditCriterion {
  id: string;
  name: string;
  max_points: number;
  awarded_points: number;
  status: string;
  finding: string;
  action?: string | null;
}

interface AuditDimension {
  name: string;
  subtitle: string;
  score: number;
  max_score: number;
  criteria: AuditCriterion[];
}

interface AuditReport {
  audit_type: string;
  total_score: number;
  max_score: number;
  quality_label: string;
  criteria_checked: number;
  criteria_passed: number;
  criteria_stronger: number;
  criteria_attention: number;
  criteria_skipped: number;
  top_3_changes: TopChangeItem[];
  dimensions: AuditDimension[];
  extracted_text_snippet?: string;
  previous_score?: number | null;
  score_delta?: number | null;
}

const COMMON_ROLES = [
  "AI / ML Engineer",
  "Fullstack Software Engineer",
  "Frontend Developer",
  "Backend Developer",
  "Data Scientist",
  "DevOps / Cloud Engineer",
];

export default function CvAuditPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [targetRole, setTargetRole] = useState("AI / ML Engineer");
  const [isAuditing, setIsAuditing] = useState(false);
  const [auditProgressStage, setAuditProgressStage] = useState(0);
  const [auditReport, setAuditReport] = useState<AuditReport | null>(null);
  const [savedResumeExists, setSavedResumeExists] = useState(false);
  const [useSavedResume, setUseSavedResume] = useState(false);
  const [showRawText, setShowRawText] = useState(false);
  const [activeDimensionIndex, setActiveDimensionIndex] = useState<number | null>(0);

  const PROGRESS_STAGES = [
    "Extracting text & ATS reading order...",
    "Scanning contact details & external links...",
    "Evaluating experience & quantified bullets...",
    "Cross-referencing target role keyword depth...",
    "Ranking top 3 high-impact fixes...",
  ];

  useEffect(() => {
    // Check if user has saved profile in localStorage
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("smartapply_parsed_resume");
      if (stored) {
        setSavedResumeExists(true);
      }
    }
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        toast.error("Please upload a PDF document for ATS precision.");
        return;
      }
      setSelectedFile(file);
      setUseSavedResume(false);
    }
  };

  const handleRunAudit = async () => {
    if (!selectedFile && !useSavedResume) {
      toast.error("Please upload your resume PDF or use your saved profile.");
      return;
    }

    setIsAuditing(true);
    setAuditProgressStage(0);

    // Cycle scanning animation stages
    const stageInterval = setInterval(() => {
      setAuditProgressStage((prev) => (prev < PROGRESS_STAGES.length - 1 ? prev + 1 : prev));
    }, 550);

    try {
      const formData = new FormData();
      if (selectedFile && !useSavedResume) {
        formData.append("file", selectedFile);
      }

      let parsedProfile = null;
      if (useSavedResume && typeof window !== "undefined") {
        const stored = localStorage.getItem("smartapply_parsed_resume");
        if (stored) {
          parsedProfile = JSON.parse(stored);
        }
      }

      formData.append(
        "data_json",
        JSON.stringify({
          target_role: targetRole,
          parsed_resume: parsedProfile,
          user_id: typeof window !== "undefined" ? localStorage.getItem("user_id") : null,
        })
      );

      const data = await apiFetch<AuditReport>("/audit/cv", {
        method: "POST",
        body: formData,
      });

      setAuditReport(data);
      toast.success("CV Audit complete! Your score is ready.");
    } catch (err: any) {
      console.error("Audit error:", err);
      toast.error(err.message || "Failed to audit resume. Please try again.");
    } finally {
      clearInterval(stageInterval);
      setIsAuditing(false);
    }
  };

  return (
    <div className="min-h-screen bg-transparent text-slate-900 dark:text-white flex flex-col items-center">
      {/* Universal Navbar */}
      <Navbar />

      {/* Main Container */}
      <main className="w-full max-w-5xl px-4 pt-24 pb-16 space-y-10">
        {/* Page Hero */}
        <PageHero
          badge="25-Criteria ATS Audit Engine"
          title="Free AI Resume & CV Audit"
          subtitle="Get a comprehensive ATS compatibility breakdown, quantified bullet impact scoring, and prioritized fixes to land more interviews."
          breadcrumbs={[
            { label: "Home", href: "/" },
            { label: "Career Audit", href: "/audit/cv" },
            { label: "CV Audit" },
          ]}
        />

        {/* Input & Upload Zone */}
        {!auditReport && (
          <div className="w-full max-w-3xl mx-auto p-6 md:p-8 rounded-3xl glass-card border border-teal-500/20 shadow-2xl space-y-6">
            <div className="space-y-2">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <FileSearch className="w-5 h-5 text-teal-600 dark:text-teal-400" />
                1. Select Target Role & Upload Document
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Our engine compares your experience, tools, and quantified metrics directly against recruiter benchmarks.
              </p>
            </div>

            {/* Target Role Selector */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                Target Role / Track:
              </label>
              <div className="flex flex-wrap gap-2">
                {COMMON_ROLES.map((role) => (
                  <button
                    key={role}
                    type="button"
                    onClick={() => setTargetRole(role)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
                      targetRole === role
                        ? "bg-teal-500/20 border-teal-500 text-teal-700 dark:text-teal-300 shadow-sm"
                        : "bg-slate-100/60 dark:bg-slate-800/60 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-teal-500/40"
                    }`}
                  >
                    {role}
                  </button>
                ))}
              </div>
            </div>

            {/* Upload Box or Saved Profile Toggle */}
            <div className="space-y-3">
              {savedResumeExists && (
                <div className="flex items-center justify-between p-3.5 rounded-2xl bg-teal-500/10 border border-teal-500/20">
                  <div className="flex items-center gap-2.5 text-xs">
                    <Zap className="w-4 h-4 text-teal-600 dark:text-teal-400" />
                    <span className="font-semibold text-slate-800 dark:text-slate-200">
                      Use saved resume from your profile
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setUseSavedResume(!useSavedResume);
                      setSelectedFile(null);
                    }}
                    className={`px-3 py-1 rounded-xl text-xs font-bold transition-all ${
                      useSavedResume
                        ? "bg-teal-600 text-white shadow-md"
                        : "bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300"
                    }`}
                  >
                    {useSavedResume ? "Selected ✓" : "Use Saved"}
                  </button>
                </div>
              )}

              {!useSavedResume && (
                <label className="flex flex-col items-center justify-center border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-3xl p-8 cursor-pointer hover:border-teal-500 dark:hover:border-teal-400 transition-colors bg-white/30 dark:bg-slate-900/30">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <div className="p-3.5 rounded-2xl bg-teal-500/10 text-teal-600 dark:text-teal-400 mb-3 border border-teal-500/20">
                    <UploadCloud className="w-6 h-6" />
                  </div>
                  <span className="text-sm font-bold text-slate-800 dark:text-slate-200">
                    {selectedFile ? selectedFile.name : "Click to upload your resume (PDF)"}
                  </span>
                  <span className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    {selectedFile
                      ? `${(selectedFile.size / 1024).toFixed(1)} KB • Ready to audit`
                      : "Drag & drop or browse from your computer (Max 10MB)"}
                  </span>
                </label>
              )}
            </div>

            {/* Run Audit Button */}
            <button
              onClick={handleRunAudit}
              disabled={isAuditing || (!selectedFile && !useSavedResume)}
              className="w-full py-4 rounded-2xl bg-gradient-to-r from-teal-600 via-teal-500 to-emerald-500 text-white font-bold text-sm md:text-base flex items-center justify-center gap-2 shadow-lg shadow-teal-500/25 hover:shadow-teal-500/40 hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50 disabled:pointer-events-none transition-all"
            >
              {isAuditing ? (
                <>
                  <RefreshCw className="w-5 h-5 animate-spin" />
                  <span>Auditing Resume...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  <span>Run 25-Criteria ATS Audit</span>
                </>
              )}
            </button>

            {/* Scanning Progress Stage Indicator */}
            {isAuditing && (
              <div className="p-4 rounded-2xl bg-slate-900/80 text-white text-center space-y-2 animate-fadeIn">
                <KineticText
                  as="p"
                  animation="scramble-decode"
                  className="text-xs font-mono text-teal-300"
                >
                  {PROGRESS_STAGES[auditProgressStage]}
                </KineticText>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-teal-400 to-emerald-400 h-full transition-all duration-300"
                    style={{
                      width: `${((auditProgressStage + 1) / PROGRESS_STAGES.length) * 100}%`,
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Audit Results Dashboard */}
        {auditReport && (
          <div className="space-y-8 animate-fadeIn">
            {/* Top Score Banner & Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
              {/* Score Gauge */}
              <div className="md:col-span-1">
                <AuditScoreGauge
                  score={auditReport.total_score}
                  maxScore={auditReport.max_score}
                  qualityLabel={auditReport.quality_label}
                  previousScore={auditReport.previous_score}
                  scoreDelta={auditReport.score_delta}
                  variant="teal"
                  size="lg"
                />
              </div>

              {/* High-level Narrative & Stats */}
              <div className="md:col-span-2 p-6 md:p-8 rounded-3xl glass-card border border-teal-500/15 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                    Audit Performance Breakdown
                  </h3>
                  <button
                    onClick={() => {
                      setAuditReport(null);
                      setSelectedFile(null);
                    }}
                    className="inline-flex items-center gap-1 text-xs text-teal-600 dark:text-teal-400 hover:underline font-semibold"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    Re-audit Document
                  </button>
                </div>

                {/* Pretext Reflow Narrative */}
                <PretextReflow
                  text={`Your resume scored ${auditReport.total_score} out of 100 on our ATS and recruiter evaluation benchmark for ${targetRole}. We evaluated ${auditReport.criteria_checked} specific criteria across document readability, link validity, quantified bullet metrics, and target role alignment.`}
                  className="text-xs md:text-sm text-slate-600 dark:text-slate-300 leading-relaxed"
                />

                {/* Stat Badges Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                  <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-center">
                    <span className="text-lg font-black text-emerald-600 dark:text-emerald-400 block">
                      {auditReport.criteria_passed}
                    </span>
                    <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase">
                      Passed (Looks Good)
                    </span>
                  </div>

                  <div className="p-3 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-center">
                    <span className="text-lg font-black text-amber-600 dark:text-amber-400 block">
                      {auditReport.criteria_stronger}
                    </span>
                    <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase">
                      Could Be Stronger
                    </span>
                  </div>

                  <div className="p-3 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-center">
                    <span className="text-lg font-black text-rose-600 dark:text-rose-400 block">
                      {auditReport.criteria_attention}
                    </span>
                    <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase">
                      Needs Attention
                    </span>
                  </div>

                  <div className="p-3 rounded-2xl bg-slate-500/10 border border-slate-500/20 text-center">
                    <span className="text-lg font-black text-slate-600 dark:text-slate-400 block">
                      {auditReport.criteria_skipped}
                    </span>
                    <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase">
                      Not Checked
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Start with these 3 changes (FlyRank style) */}
            <TopChangesRoadmap
              changes={auditReport.top_3_changes}
              onApplyAction={() => {
                window.location.href = "/tailor";
              }}
              actionCtaLabel="Fix in AI Tailor Studio"
            />

            {/* 6 Dimensions Accordion Breakdown */}
            <div className="space-y-4">
              <div className="space-y-1">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  Detailed 25-Criteria Breakdown
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Click each dimension below to inspect individual criteria findings and recommended actions.
                </p>
              </div>

              <div className="space-y-3">
                {auditReport.dimensions.map((dim, dimIdx) => {
                  const isExpanded = activeDimensionIndex === dimIdx;
                  const scorePercent = Math.round((dim.score / Math.max(dim.max_score, 1)) * 100);

                  return (
                    <div
                      key={dimIdx}
                      className="rounded-3xl glass-card border border-teal-500/15 overflow-hidden transition-all duration-300"
                    >
                      {/* Dimension Accordion Header */}
                      <button
                        type="button"
                        onClick={() => setActiveDimensionIndex(isExpanded ? null : dimIdx)}
                        className="w-full p-5 flex items-center justify-between gap-4 text-left select-none hover:bg-teal-500/5 transition-colors"
                      >
                        <div className="space-y-0.5 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-black px-2 py-0.5 rounded-lg bg-teal-500/15 text-teal-700 dark:text-teal-300">
                              #{dimIdx + 1}
                            </span>
                            <h4 className="text-sm md:text-base font-bold text-slate-900 dark:text-white truncate">
                              {dim.name}
                            </h4>
                          </div>
                          <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                            {dim.subtitle}
                          </p>
                        </div>

                        <div className="flex items-center gap-3 flex-shrink-0">
                          <span className="text-xs md:text-sm font-bold text-slate-800 dark:text-slate-200">
                            {dim.score}/{dim.max_score} pts ({scorePercent}%)
                          </span>
                          <ChevronDown
                            className={`w-5 h-5 text-slate-400 transition-transform duration-200 ${
                              isExpanded ? "rotate-180" : ""
                            }`}
                          />
                        </div>
                      </button>

                      {/* Criteria Items List */}
                      {isExpanded && (
                        <div className="p-5 pt-0 space-y-2.5 border-t border-slate-200/40 dark:border-slate-800/40 mt-1">
                          {dim.criteria.map((crit) => (
                            <AuditCriterionCard key={crit.id} criterion={crit} />
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Extracted Text Inspector Drawer */}
            {auditReport.extracted_text_snippet && (
              <div className="rounded-2xl glass-card border border-slate-200 dark:border-slate-800 p-4">
                <button
                  type="button"
                  onClick={() => setShowRawText(!showRawText)}
                  className="w-full flex items-center justify-between text-xs font-semibold text-slate-700 dark:text-slate-300"
                >
                  <span className="flex items-center gap-1.5">
                    <Eye className="w-4 h-4 text-teal-600 dark:text-teal-400" />
                    Inspect Text Our Engine Could Read (ATS Parsed View)
                  </span>
                  <ChevronDown
                    className={`w-4 h-4 text-slate-400 transition-transform ${
                      showRawText ? "rotate-180" : ""
                    }`}
                  />
                </button>

                {showRawText && (
                  <div className="mt-3 p-3.5 rounded-xl bg-slate-950 text-slate-300 text-xs font-mono whitespace-pre-wrap max-h-60 overflow-y-auto border border-slate-800">
                    {auditReport.extracted_text_snippet}
                  </div>
                )}
              </div>
            )}

            {/* Bottom Actions Hub */}
            <div className="p-6 md:p-8 rounded-3xl glass-card border border-teal-500/20 flex flex-col sm:flex-row items-center justify-between gap-4 bg-gradient-to-r from-teal-500/5 to-emerald-500/5">
              <div>
                <h4 className="text-base font-bold text-slate-900 dark:text-white">
                  Ready to optimize this resume for higher callback rates?
                </h4>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Use our AI Tailoring Studio to instantly apply recommended XYZ bullets and keywords.
                </p>
              </div>

              <div className="flex items-center gap-3 w-full sm:w-auto">
                <Link
                  href="/tailor"
                  className="w-full sm:w-auto px-6 py-3 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs md:text-sm flex items-center justify-center gap-2 shadow-md hover:shadow-teal-500/20 transition-all"
                >
                  <span>Launch Tailoring Studio</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
