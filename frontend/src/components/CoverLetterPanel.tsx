"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, Sparkles, Download, Copy, CheckCircle2, AlertCircle, Loader2, RefreshCw, ChevronDown } from "lucide-react";
import { toast } from "sonner";
import { getBackendUrl, getAuthHeaders } from "../lib/api";

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
  color_theme?: Record<string, string>;
  font_family?: string;
  executive_summary?: string;
  certifications?: string[];
  languages?: string[];
  scroll_stop_hook?: string;
}

interface CoverLetterPanelProps {
  user_id: string;
  parsed_resume?: ResumeParsedData;
  jdText?: string;
  companyName?: string;
  roleTitle?: string;
  defaultExpanded?: boolean;
}

export default function CoverLetterPanel({
  user_id,
  parsed_resume,
  jdText = "",
  companyName = "",
  roleTitle = "",
  defaultExpanded = false,
}: CoverLetterPanelProps) {
  const extractResumeObject = (data: any): ResumeParsedData | null => {
    if (!data) return null;
    if (data.parsed_resume && typeof data.parsed_resume === "object") {
      return data.parsed_resume;
    }
    if (data.name || data.skills || data.experience) {
      return data;
    }
    return null;
  };

  const [jd, setJd] = useState(jdText);
  const [coverLetter, setCoverLetter] = useState("");
  const [wordCount, setWordCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(defaultExpanded || !parsed_resume);
  const [localResume, setLocalResume] = useState<ResumeParsedData | null>(extractResumeObject(parsed_resume));
  const [loadingProfile, setLoadingProfile] = useState(false);

  useEffect(() => {
    if (parsed_resume) {
      setLocalResume(extractResumeObject(parsed_resume));
    }
  }, [parsed_resume]);

  useEffect(() => {
    if (!localResume) {
      const fetchProfile = async () => {
        setLoadingProfile(true);
        let databaseLoaded = false;
        if (user_id) {
          try {
            const res = await fetch(`${getBackendUrl()}/profiles/${user_id}`, {
              headers: getAuthHeaders()
            });
            if (res.ok) {
              const data = await res.json();
              const extracted = extractResumeObject(data);
              if (extracted) {
                setLocalResume(extracted);
                databaseLoaded = true;
              }
            }
          } catch (err) {
            console.error("Error fetching profile for cover letter:", err);
          }
        }

        if (!databaseLoaded && typeof window !== "undefined") {
          // Fallback to localStorage
          try {
            const keys = ["echoapply_parsed_resume", "smartapply_parsed_resume", "parsed_resume"];
            for (const k of keys) {
              const cached = localStorage.getItem(k);
              if (cached) {
                const parsed = JSON.parse(cached);
                const extracted = extractResumeObject(parsed);
                if (extracted) {
                  setLocalResume(extracted);
                  databaseLoaded = true;
                  break;
                }
              }
            }
          } catch (e) {
            console.error("Error loading cached local resume:", e);
          }
        }

        setLoadingProfile(false);
      };
      fetchProfile();
    }
  }, [localResume, user_id]);

  const activeResume = extractResumeObject(localResume || parsed_resume);

  const handleGenerate = async () => {
    if (!activeResume) {
      toast.error("Please upload your resume first to generate a tailored cover letter.");
      return;
    }
    if (!jd || jd.trim().length < 20) {
      toast.error("Please provide a job description or select a sample JD preset.");
      return;
    }

    setLoading(true);
    setError(null);
    setCoverLetter("");

    try {
      const backendUrl = getBackendUrl();
      const response = await fetch(`${backendUrl}/api/cover-letter/generate`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          user_id: user_id || "00000000-0000-0000-0000-000000000001",
          jd_text: jd,
          parsed_resume: activeResume,
          company_name: companyName || "Hiring Team",
          role_title: roleTitle || "Target Position",
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Generation failed");
      }

      const data = await response.json();
      if (data.status === "success") {
        setCoverLetter(data.cover_letter_text);
        setWordCount(data.word_count);
        toast.success(`Tailored cover letter generated! (${data.word_count} words)`);
      } else {
        throw new Error(data.error || "Unknown error occurred");
      }
    } catch (err: any) {
      setError(err.message);
      toast.error(`Generation error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(coverLetter);
    setCopied(true);
    toast.success("Cover letter copied to clipboard!");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadPdf = async () => {
    const resumeToUse = activeResume;
    if (!resumeToUse) {
      toast.error("Resume details missing. Please upload your resume first.");
      return;
    }
    try {
      const backendUrl = getBackendUrl();
      const response = await fetch(`${backendUrl}/api/cover-letter/download-pdf`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          user_id: user_id || "00000000-0000-0000-0000-000000000001",
          jd_text: jd,
          parsed_resume: resumeToUse,
          company_name: companyName || "Hiring Team",
          role_title: roleTitle || "Target Position",
        }),
      });

      if (!response.ok) throw new Error("PDF generation failed");

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "cover_letter.pdf";
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Cover letter PDF downloaded!");
    } catch (err: any) {
      toast.error(`Download failed: ${err.message}`);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header Toggle */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 rounded-xl bg-gradient-to-r from-violet-500/5 to-fuchsia-500/5 border border-violet-500/20 hover:border-violet-500/40 transition-all group"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-violet-500/10 text-violet-500">
            <FileText className="w-4 h-4" />
          </div>
          <div className="text-left">
            <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 group-hover:text-violet-600 dark:group-hover:text-violet-400 transition">
              AI Cover Letter Generator
            </h3>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Generate a tailored cover letter from your resume + job description
            </p>
          </div>
        </div>
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="w-4 h-4 text-slate-400" />
        </motion.div>
      </button>

      {/* Expandable Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="space-y-4 pt-1">
              {/* Attached Profile Indicator */}
              <div className="flex items-center justify-between px-3 py-2 rounded-xl bg-slate-100 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 text-xs">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${activeResume ? "bg-emerald-500 animate-pulse" : "bg-amber-500"}`} />
                  <span className="text-slate-700 dark:text-slate-300 font-medium">
                    {activeResume ? (
                      <>
                        Active Profile: <strong className="text-slate-900 dark:text-white">{activeResume.name || "Candidate"}</strong>
                        {activeResume.skills?.length ? ` (${activeResume.skills.length} skills detected)` : ""}
                      </>
                    ) : (
                      "No resume attached. Upload your resume above to personalize."
                    )}
                  </span>
                </div>
                {loadingProfile && (
                  <span className="text-slate-400 flex items-center gap-1">
                    <Loader2 className="w-3 h-3 animate-spin" /> Syncing profile...
                  </span>
                )}
              </div>

              {/* JD Input */}
              {!coverLetter && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Target Job Description
                    </label>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[11px] text-slate-400">Quick Presets:</span>
                      <button
                        type="button"
                        onClick={() => setJd("We are seeking a Senior Full-Stack Engineer skilled in TypeScript, Next.js, Python/FastAPI, and PostgreSQL. You will design scalable web applications, implement AI workflows, optimize API response times, and collaborate in an agile cross-functional engineering team.")}
                        className="text-[10px] px-2 py-0.5 rounded-md bg-violet-500/10 text-violet-600 dark:text-violet-400 hover:bg-violet-500/20 transition font-medium"
                      >
                        Full-Stack
                      </button>
                      <button
                        type="button"
                        onClick={() => setJd("Looking for a Frontend Developer proficient in React, Next.js, TailwindCSS, responsive UI design, and web performance optimization. Experience with Framer Motion, TypeScript, and state management is highly valued.")}
                        className="text-[10px] px-2 py-0.5 rounded-md bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/20 transition font-medium"
                      >
                        Frontend
                      </button>
                    </div>
                  </div>

                  <textarea
                    value={jd}
                    onChange={(e) => setJd(e.target.value)}
                    placeholder="Paste the target job description or company requirements here..."
                    rows={5}
                    className="w-full p-4 rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-sm text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 resize-none transition shadow-sm"
                  />

                  <button
                    onClick={handleGenerate}
                    disabled={loading || !jd.trim()}
                    className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-700 hover:to-fuchsia-700 text-white text-sm font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-violet-500/20 active:scale-[0.99]"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Generating Tailored Cover Letter...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        Generate Cover Letter
                      </>
                    )}
                  </button>
                </div>
              )}

              {/* Error */}
              {error && (
                <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {error}
                </div>
              )}

              {/* Generated Cover Letter */}
              {coverLetter && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="space-y-3"
                >
                  {/* Stats Bar */}
                  <div className="flex items-center justify-between px-1">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                      <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold">
                        Generated • {wordCount} words
                      </span>
                    </div>
                    <button
                      onClick={() => {
                        setCoverLetter("");
                        setWordCount(0);
                      }}
                      className="flex items-center gap-1 text-[11px] text-slate-500 hover:text-violet-500 transition"
                    >
                      <RefreshCw className="w-3 h-3" />
                      Regenerate
                    </button>
                  </div>

                  {/* Letter Content */}
                  <div className="p-5 rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 max-h-[400px] overflow-y-auto scrollbar-none">
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      {coverLetter.split("\n\n").map((paragraph, i) => (
                        <p
                          key={i}
                          className="text-[13px] text-slate-700 dark:text-slate-300 leading-relaxed mb-3 last:mb-0"
                        >
                          {paragraph}
                        </p>
                      ))}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    <button
                      onClick={handleCopy}
                      className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition"
                    >
                      {copied ? (
                        <>
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          Copy Text
                        </>
                      )}
                    </button>
                    <button
                      onClick={handleDownloadPdf}
                      className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-700 text-white text-xs font-semibold transition shadow-lg shadow-violet-500/20"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Download PDF
                    </button>
                  </div>
                </motion.div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
