"use client";

import React, { useState, useEffect, useRef } from "react";
import Navbar from "@/components/Navbar";
import PageHero from "@/components/PageHero";
import CoverLetterPanel from "@/components/CoverLetterPanel";
import { useAuth } from "@/context/AuthContext";
import { Sparkles, FileText, Upload, CheckCircle2, AlertCircle, Loader2, RefreshCw, UserCheck } from "lucide-react";
import { getBackendUrl, getAuthHeaders } from "@/lib/api";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";

export default function CoverLetterStudioPage() {
  const { user_id } = useAuth();
  const effectiveUserId = user_id || "00000000-0000-0000-0000-000000000001";
  const [parsedResume, setParsedResume] = useState<any>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load profile from DB or localStorage on mount
  useEffect(() => {
    async function loadResumeProfile() {
      let found = false;

      // 1. Try DB if logged in
      if (user_id) {
        try {
          const res = await fetch(`${getBackendUrl()}/profiles/${user_id}`, {
            headers: getAuthHeaders(),
          });
          if (res.ok) {
            const data = await res.json();
            const resumeObj = data.parsed_resume || (data.name ? data : null);
            if (resumeObj) {
              setParsedResume(resumeObj);
              found = true;
            }
          }
        } catch (e) {
          console.error("DB profile fetch error:", e);
        }
      }

      // 2. Fallback to localStorage
      if (!found && typeof window !== "undefined") {
        const keys = ["echoapply_parsed_resume", "smartapply_parsed_resume", "parsed_resume"];
        for (const k of keys) {
          const stored = localStorage.getItem(k);
          if (stored) {
            try {
              const data = JSON.parse(stored);
              const resumeObj = data.parsed_resume || (data.name ? data : null);
              if (resumeObj) {
                setParsedResume(resumeObj);
                found = true;
                break;
              }
            } catch (e) {
              console.error("Failed to parse cached resume:", e);
            }
          }
        }
      }
    }

    loadResumeProfile();
  }, [user_id]);

  const handleFileUpload = async (file: File) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadError("Please upload a valid PDF resume.");
      toast.error("Only PDF files are currently supported for structured resume parsing.");
      return;
    }

    setUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const backendUrl = getBackendUrl();
      const response = await fetch(`${backendUrl}/intake`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Failed to parse resume PDF.");
      }

      const result = await response.json();
      const resumeData = result.parsed_resume || result;

      setParsedResume(resumeData);

      // Save to localStorage for instant reuse across all suite tools
      if (typeof window !== "undefined") {
        localStorage.setItem("echoapply_parsed_resume", JSON.stringify(result));
        localStorage.setItem("smartapply_parsed_resume", JSON.stringify(result));
      }

      toast.success(`Resume for ${resumeData.name || "Candidate"} parsed & connected!`);
    } catch (err: any) {
      setUploadError(err.message);
      toast.error(`Upload error: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="min-h-screen bg-transparent text-slate-900 dark:text-white flex flex-col items-center">
      {/* Universal Navbar */}
      <Navbar />

      {/* Main Container */}
      <main className="w-full max-w-5xl px-4 pt-24 pb-16 space-y-8">
        {/* Page Hero */}
        <PageHero
          badge="AI Application Suite"
          title="Tailored Cover Letter Generator"
          subtitle="Generate hyper-personalized, ATS-compliant cover letters that match your actual experience to the employer's exact job requirements."
          breadcrumbs={[
            { label: "Home", href: "/" },
            { label: "Application Suite", href: "/cover-letter" },
            { label: "Cover Letter Generator" },
          ]}
        />

        {/* Studio Panel Container */}
        <div className="w-full max-w-4xl mx-auto space-y-6">
          {/* Step 1: Connected Resume Profile Card / Upload Dropzone */}
          <div className="rounded-2xl bg-white/70 dark:bg-slate-900/60 backdrop-blur-xl border border-slate-200/80 dark:border-slate-800 p-5 shadow-sm">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800/80 mb-4">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                  <FileText className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-800 dark:text-slate-200">
                    Step 1: Resume Profile Source
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Your cover letter will be customized using the skills and achievements from this resume.
                  </p>
                </div>
              </div>

              {parsedResume && (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition"
                >
                  <RefreshCw className="w-3 h-3" />
                  Replace Resume
                </button>
              )}
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFileUpload(e.target.files[0]);
                }
              }}
            />

            {/* If Resume Loaded -> Display Profile Summary Pill */}
            {parsedResume ? (
              <motion.div
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-emerald-500/5 dark:bg-emerald-500/10 border border-emerald-500/20"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-500/15 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
                    <UserCheck className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                        {parsedResume.name || "Candidate Profile"}
                      </h3>
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/20 text-emerald-700 dark:text-emerald-300">
                        <CheckCircle2 className="w-2.5 h-2.5" /> Ready
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                      {parsedResume.email || "Profile attached"} &bull; {parsedResume.skills?.length || 0} skills &bull; {parsedResume.experience?.length || 0} work experiences
                    </p>
                  </div>
                </div>

                {parsedResume.skills && parsedResume.skills.length > 0 && (
                  <div className="flex flex-wrap gap-1 max-w-sm justify-end">
                    {parsedResume.skills.slice(0, 4).map((s: string, idx: number) => (
                      <span
                        key={idx}
                        className="px-2 py-0.5 rounded-md text-[10px] bg-slate-200/70 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium"
                      >
                        {s}
                      </span>
                    ))}
                    {parsedResume.skills.length > 4 && (
                      <span className="px-1.5 py-0.5 rounded-md text-[10px] text-slate-400">
                        +{parsedResume.skills.length - 4} more
                      </span>
                    )}
                  </div>
                )}
              </motion.div>
            ) : (
              /* If No Resume Loaded -> Interactive Dropzone */
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragOver(true);
                }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`relative cursor-pointer border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center transition-all ${
                  isDragOver
                    ? "border-violet-500 bg-violet-500/5"
                    : "border-slate-300 dark:border-slate-700 hover:border-violet-500/50 hover:bg-slate-50 dark:hover:bg-slate-800/40"
                }`}
              >
                {uploading ? (
                  <div className="flex flex-col items-center gap-2">
                    <Loader2 className="w-8 h-8 text-violet-500 animate-spin" />
                    <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                      Analyzing and parsing your resume PDF...
                    </p>
                    <p className="text-xs text-slate-400">
                      Extracting your work history, metrics, and core skills.
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-12 h-12 rounded-xl bg-violet-500/10 flex items-center justify-center text-violet-600 dark:text-violet-400 mb-1">
                      <Upload className="w-6 h-6" />
                    </div>
                    <p className="text-sm font-bold text-slate-800 dark:text-slate-200">
                      Drag & Drop your Resume PDF here, or <span className="text-violet-600 dark:text-violet-400 underline underline-offset-2">browse</span>
                    </p>
                    <p className="text-xs text-slate-400 max-w-sm">
                      Upload your PDF to automatically customize and generate tailored cover letters matching any job description.
                    </p>
                  </div>
                )}

                {uploadError && (
                  <div className="mt-3 flex items-center gap-1.5 text-xs text-rose-500 bg-rose-500/10 px-3 py-1.5 rounded-lg border border-rose-500/20">
                    <AlertCircle className="w-3.5 h-3.5" />
                    {uploadError}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Step 2: Cover Letter Generator Panel */}
          <div className="rounded-2xl bg-white/70 dark:bg-slate-900/60 backdrop-blur-xl border border-slate-200/80 dark:border-slate-800 p-5 shadow-sm">
            <CoverLetterPanel
              user_id={effectiveUserId}
              parsed_resume={parsedResume}
              defaultExpanded={true}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
