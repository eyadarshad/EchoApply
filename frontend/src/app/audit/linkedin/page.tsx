"use client";

import React, { useState } from "react";
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
  Linkedin,
  UploadCloud,
  Sparkles,
  ChevronDown,
  Copy,
  Check,
  RefreshCw,
  ArrowRight,
  FileText,
  HelpCircle,
  Eye,
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

interface SuggestedWording {
  headline_ideas: string[];
  about_section_outline: string;
  skills_roadmap: string[];
}

interface LinkedInAuditReport {
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
  suggested_wording?: SuggestedWording | null;
  extracted_text_snippet?: string;
  previous_score?: number | null;
  score_delta?: number | null;
}

export default function LinkedInAuditPage() {
  const [inputMode, setInputMode] = useState<"pdf" | "text">("pdf");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [headline, setHeadline] = useState("");
  const [about, setAbout] = useState("");
  const [experience, setExperience] = useState("");
  const [skills, setSkills] = useState("");
  const [targetRole, setTargetRole] = useState("AI / Machine Learning Engineer");
  const [isAuditing, setIsAuditing] = useState(false);
  const [auditProgressStage, setAuditProgressStage] = useState(0);
  const [auditReport, setAuditReport] = useState<LinkedInAuditReport | null>(null);
  const [activeDimensionIndex, setActiveDimensionIndex] = useState<number | null>(0);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [copiedAbout, setCopiedAbout] = useState(false);

  const PROGRESS_STAGES = [
    "Parsing LinkedIn profile structure & metadata...",
    "Auditing headline recruiter keyword density...",
    "Analyzing About section storytelling & proof points...",
    "Scanning skills alignment & endorsement signals...",
    "Generating 3 optimized headline variations...",
  ];

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        toast.error("Please upload a LinkedIn profile PDF (saved from 'More → Save to PDF').");
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleCopyText = (text: string, index?: number) => {
    navigator.clipboard.writeText(text);
    if (index !== undefined) {
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    } else {
      setCopiedAbout(true);
      setTimeout(() => setCopiedAbout(false), 2000);
    }
    toast.success("Copied to clipboard!");
  };

  const handleRunAudit = async () => {
    if (inputMode === "pdf" && !selectedFile) {
      toast.error("Please upload your LinkedIn profile PDF.");
      return;
    }
    if (inputMode === "text" && !headline && !about && !experience) {
      toast.error("Please fill in at least your Headline, About, or Experience.");
      return;
    }

    setIsAuditing(true);
    setAuditProgressStage(0);

    const stageInterval = setInterval(() => {
      setAuditProgressStage((prev) => (prev < PROGRESS_STAGES.length - 1 ? prev + 1 : prev));
    }, 550);

    try {
      const formData = new FormData();
      if (inputMode === "pdf" && selectedFile) {
        formData.append("file", selectedFile);
      }

      formData.append(
        "data_json",
        JSON.stringify({
          target_role: targetRole,
          headline,
          about,
          experience,
          skills,
          user_id: typeof window !== "undefined" ? localStorage.getItem("user_id") : null,
        })
      );

      const data = await apiFetch<LinkedInAuditReport>("/audit/linkedin", {
        method: "POST",
        body: formData,
      });

      setAuditReport(data);
      toast.success("LinkedIn Audit complete!");
    } catch (err: any) {
      console.error("LinkedIn audit error:", err);
      toast.error(err.message || "Failed to audit LinkedIn profile.");
    } finally {
      clearInterval(stageInterval);
      setIsAuditing(false);
    }
  };

  return (
    <div className="min-h-screen bg-transparent text-slate-900 dark:text-white flex flex-col items-center">
      {/* Navbar */}
      <Navbar />

      {/* Main Container */}
      <main className="w-full max-w-5xl px-4 pt-24 pb-16 space-y-10">
        {/* Page Hero */}
        <PageHero
          badge="Recruiter SEO & Profile Optimizer"
          title="Free AI LinkedIn Profile Audit"
          subtitle="Score your LinkedIn profile across 27 recruiter discovery criteria, get 3 AI-optimized headlines, and master the About section storytelling formula."
          breadcrumbs={[
            { label: "Home", href: "/" },
            { label: "Career Audit", href: "/audit/linkedin" },
            { label: "LinkedIn Audit" },
          ]}
        />

        {/* Input Form */}
        {!auditReport && (
          <div className="w-full max-w-3xl mx-auto p-6 md:p-8 rounded-3xl glass-card border border-sky-500/20 shadow-2xl space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <Linkedin className="w-5 h-5 text-sky-600 dark:text-sky-400" />
                  Audit Your LinkedIn Profile
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Analyze recruiter visibility, search keywords, and storytelling quality.
                </p>
              </div>

              {/* Mode Toggle */}
              <div className="flex items-center p-1 rounded-2xl bg-slate-100 dark:bg-slate-800 text-xs font-semibold">
                <button
                  type="button"
                  onClick={() => setInputMode("pdf")}
                  className={`px-3 py-1.5 rounded-xl transition-all ${
                    inputMode === "pdf"
                      ? "bg-sky-600 text-white shadow-md"
                      : "text-slate-600 dark:text-slate-400"
                  }`}
                >
                  Upload PDF
                </button>
                <button
                  type="button"
                  onClick={() => setInputMode("text")}
                  className={`px-3 py-1.5 rounded-xl transition-all ${
                    inputMode === "text"
                      ? "bg-sky-600 text-white shadow-md"
                      : "text-slate-600 dark:text-slate-400"
                  }`}
                >
                  Paste Text
                </button>
              </div>
            </div>

            {/* Target Role */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                Target Role / Industry:
              </label>
              <input
                type="text"
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                placeholder="e.g. AI / Machine Learning Engineer, Senior Product Manager"
                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-sm focus:outline-none focus:border-sky-500"
              />
            </div>

            {/* Mode 1: PDF Upload */}
            {inputMode === "pdf" && (
              <div className="space-y-3">
                <label className="flex flex-col items-center justify-center border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-3xl p-8 cursor-pointer hover:border-sky-500 dark:hover:border-sky-400 transition-colors bg-white/30 dark:bg-slate-900/30">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <div className="p-3.5 rounded-2xl bg-sky-500/10 text-sky-600 dark:text-sky-400 mb-3 border border-sky-500/20">
                    <UploadCloud className="w-6 h-6" />
                  </div>
                  <span className="text-sm font-bold text-slate-800 dark:text-slate-200">
                    {selectedFile ? selectedFile.name : "Upload LinkedIn Profile PDF"}
                  </span>
                  <span className="text-xs text-slate-500 dark:text-slate-400 mt-1 text-center max-w-sm">
                    {selectedFile
                      ? `${(selectedFile.size / 1024).toFixed(1)} KB • Ready to audit`
                      : "On your LinkedIn profile page, click 'More' → 'Save to PDF' then upload here."}
                  </span>
                </label>
              </div>
            )}

            {/* Mode 2: Structured Text */}
            {inputMode === "text" && (
              <div className="space-y-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Current Headline:
                  </label>
                  <input
                    type="text"
                    value={headline}
                    onChange={(e) => setHeadline(e.target.value)}
                    placeholder="e.g. AI Engineer @ Tech | Python, PyTorch, LLMs"
                    className="w-full px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-xs focus:outline-none focus:border-sky-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    About Section:
                  </label>
                  <textarea
                    rows={4}
                    value={about}
                    onChange={(e) => setAbout(e.target.value)}
                    placeholder="Paste your current LinkedIn About summary..."
                    className="w-full px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-xs focus:outline-none focus:border-sky-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Experience Bullets:
                  </label>
                  <textarea
                    rows={3}
                    value={experience}
                    onChange={(e) => setExperience(e.target.value)}
                    placeholder="Paste recent work experience bullets..."
                    className="w-full px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-xs focus:outline-none focus:border-sky-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Skills List:
                  </label>
                  <input
                    type="text"
                    value={skills}
                    onChange={(e) => setSkills(e.target.value)}
                    placeholder="e.g. Python, PyTorch, FastAPI, Machine Learning, Docker"
                    className="w-full px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 text-xs focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>
            )}

            {/* Run Audit Button */}
            <button
              onClick={handleRunAudit}
              disabled={isAuditing || (inputMode === "pdf" && !selectedFile)}
              className="w-full py-4 rounded-2xl bg-gradient-to-r from-sky-600 via-sky-500 to-blue-600 text-white font-bold text-sm md:text-base flex items-center justify-center gap-2 shadow-lg shadow-sky-500/25 hover:shadow-sky-500/40 hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50 disabled:pointer-events-none transition-all"
            >
              {isAuditing ? (
                <>
                  <RefreshCw className="w-5 h-5 animate-spin" />
                  <span>Auditing LinkedIn Profile...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  <span>Audit LinkedIn Profile & Generate Headlines</span>
                </>
              )}
            </button>

            {/* Progress Stage */}
            {isAuditing && (
              <div className="p-4 rounded-2xl bg-slate-900/80 text-white text-center space-y-2 animate-fadeIn">
                <KineticText
                  as="p"
                  animation="scramble-decode"
                  className="text-xs font-mono text-sky-300"
                >
                  {PROGRESS_STAGES[auditProgressStage]}
                </KineticText>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-sky-400 to-blue-500 h-full transition-all duration-300"
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
            {/* Top Score Banner */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
              <div className="md:col-span-1">
                <AuditScoreGauge
                  score={auditReport.total_score}
                  maxScore={auditReport.max_score}
                  qualityLabel={auditReport.quality_label}
                  previousScore={auditReport.previous_score}
                  scoreDelta={auditReport.score_delta}
                  variant="linkedin"
                  size="lg"
                />
              </div>

              <div className="md:col-span-2 p-6 md:p-8 rounded-3xl glass-card border border-sky-500/15 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                    Recruiter SEO & Profile Breakdown
                  </h3>
                  <button
                    onClick={() => {
                      setAuditReport(null);
                      setSelectedFile(null);
                    }}
                    className="inline-flex items-center gap-1 text-xs text-sky-600 dark:text-sky-400 hover:underline font-semibold"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    Re-audit Profile
                  </button>
                </div>

                <PretextReflow
                  text={`Your profile scored ${auditReport.total_score}/100 for recruiter search positioning in ${targetRole}. We checked ${auditReport.criteria_checked} parameters covering headline keyword weighting, top-3 pinned skill alignment, and About section storytelling.`}
                  className="text-xs md:text-sm text-slate-600 dark:text-slate-300 leading-relaxed"
                />

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                  <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-center">
                    <span className="text-lg font-black text-emerald-600 dark:text-emerald-400 block">
                      {auditReport.criteria_passed}
                    </span>
                    <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase">
                      Passed
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

            {/* Suggested Profile Wording Studio (FlyRank feature) */}
            {auditReport.suggested_wording && (
              <div className="p-6 md:p-8 rounded-3xl glass-card border border-sky-500/20 shadow-xl space-y-6">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="p-1.5 rounded-xl bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/20">
                      <Sparkles className="w-4 h-4" />
                    </span>
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                      Suggested Profile Wording Studio
                    </h3>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    High-converting copy tailored to boost recruiter search index (SSI) and profile views.
                  </p>
                </div>

                {/* 3 Headline Variations */}
                <div className="space-y-3">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                    3 Recruiter-Optimized Headlines:
                  </span>
                  <div className="space-y-2.5">
                    {auditReport.suggested_wording.headline_ideas.map((headlineText, hIdx) => (
                      <div
                        key={hIdx}
                        className="p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/40 dark:bg-slate-900/40 backdrop-blur-md flex items-center justify-between gap-4 hover:border-sky-500/40 transition-colors"
                      >
                        <div className="space-y-1 min-w-0">
                          <span className="text-[10px] font-bold text-sky-600 dark:text-sky-400 uppercase tracking-wider">
                            Option {hIdx + 1}:
                          </span>
                          <p className="text-xs md:text-sm font-semibold text-slate-900 dark:text-white">
                            {headlineText}
                          </p>
                        </div>
                        <button
                          onClick={() => handleCopyText(headlineText, hIdx)}
                          className="px-3 py-1.5 rounded-xl bg-sky-500/10 hover:bg-sky-500/20 text-sky-600 dark:text-sky-400 text-xs font-bold flex items-center gap-1.5 transition-colors flex-shrink-0"
                        >
                          {copiedIndex === hIdx ? (
                            <>
                              <Check className="w-3.5 h-3.5 text-emerald-500" />
                              <span>Copied!</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5" />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* About Section Outline */}
                {auditReport.suggested_wording.about_section_outline && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                        About Section Narrative Formula:
                      </span>
                      <button
                        onClick={() =>
                          handleCopyText(auditReport.suggested_wording!.about_section_outline)
                        }
                        className="text-xs text-sky-600 dark:text-sky-400 hover:underline font-semibold flex items-center gap-1"
                      >
                        {copiedAbout ? (
                          <>
                            <Check className="w-3 h-3 text-emerald-500" />
                            <span>Copied!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3" />
                            <span>Copy Outline</span>
                          </>
                        )}
                      </button>
                    </div>
                    <div className="p-4 rounded-2xl bg-sky-950/20 border border-sky-500/20 text-xs text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
                      {auditReport.suggested_wording.about_section_outline}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Top 3 Prioritized Changes */}
            <TopChangesRoadmap
              changes={auditReport.top_3_changes}
              actionCtaLabel="View Suggestion"
            />

            {/* 6 Dimensions Breakdown */}
            <div className="space-y-4">
              <div className="space-y-1">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  Detailed 27-Criteria LinkedIn Breakdown
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Inspect individual search visibility, storytelling, and proof of work evaluations.
                </p>
              </div>

              <div className="space-y-3">
                {auditReport.dimensions.map((dim, dimIdx) => {
                  const isExpanded = activeDimensionIndex === dimIdx;
                  const scorePercent = Math.round((dim.score / Math.max(dim.max_score, 1)) * 100);

                  return (
                    <div
                      key={dimIdx}
                      className="rounded-3xl glass-card border border-sky-500/15 overflow-hidden transition-all duration-300"
                    >
                      <button
                        type="button"
                        onClick={() => setActiveDimensionIndex(isExpanded ? null : dimIdx)}
                        className="w-full p-5 flex items-center justify-between gap-4 text-left select-none hover:bg-sky-500/5 transition-colors"
                      >
                        <div className="space-y-0.5 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-black px-2 py-0.5 rounded-lg bg-sky-500/15 text-sky-700 dark:text-sky-300">
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
          </div>
        )}
      </main>
    </div>
  );
}
