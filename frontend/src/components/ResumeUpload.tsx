"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Upload, FileText, CheckCircle2, AlertCircle, Github, Download, Award, Loader2, Sparkles, RefreshCw, Edit, Save, Plus, Trash2 } from "lucide-react";
import TailorPanel from "./TailorPanel";
import TruthfulnessGate from "./TruthfulnessGate";
import JobSearch from "./JobSearch";
import { apiFetch } from "../lib/api";
import TemplateSelector from "./TemplateSelector";
import TrackerBoard from "./TrackerBoard";
import type { ResumeParsedData, GitHubEnrichedData, IntakeResult } from "../lib/types";

export type { ResumeParsedData, GitHubEnrichedData, IntakeResult };

interface ResumeUploadProps {
  userId: string | null;
  onRequireAuth: (reason: string) => void;
  onResumeLoaded?: (loaded: boolean) => void;
}

export default function ResumeUpload({ userId, onRequireAuth, onResumeLoaded }: ResumeUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [intakeResult, setIntakeResult] = useState<{
    user_id: string;
    parsed_resume: ResumeParsedData;
    github_enriched: GitHubEnrichedData | null;
  } | null>(null);

  const [activeTab, setActiveTab] = useState<"experience" | "projects" | "education" | "skills" | "github" | "jobs" | "templates" | "tracker">("experience");
  const [downloading, setDownloading] = useState<string | null>(null);
  const [selectedJdText, setSelectedJdText] = useState<string>("");

  // Tailoring Pipeline States
  const [tailorStep, setTailorStep] = useState<"idle" | "input" | "gate" | "done">("idle");
  const [tailoredResume, setTailoredResume] = useState<ResumeParsedData | null>(null);
  const [gapAnalysis, setGapAnalysis] = useState<any | null>(null);
  const [truthfulnessReport, setTruthfulnessReport] = useState<any | null>(null);
  const [atsScore, setAtsScore] = useState<number>(0);

  // Per-section editing states
  const [isEditingContact, setIsEditingContact] = useState(false);
  const [isEditingExp, setIsEditingExp] = useState(false);
  const [isEditingProj, setIsEditingProj] = useState(false);
  const [isEditingEdu, setIsEditingEdu] = useState(false);
  const [isEditingSkills, setIsEditingSkills] = useState(false);
  const [editedResume, setEditedResume] = useState<ResumeParsedData | null>(null);
  const [savingCorrections, setSavingCorrections] = useState(false);

  // Load existing profile from DB if userId is provided, fallback to localStorage
  useEffect(() => {
    async function loadExistingProfile() {
      if (!userId) {
        // No user ID — try localStorage for anonymous session
        try {
          const cached = localStorage.getItem("smartapply_parsed_resume");
          if (cached) {
            const parsed = JSON.parse(cached);
            if (parsed && parsed.parsed_resume) {
              setIntakeResult(parsed);
            }
          }
        } catch (e) { /* ignore parse errors */ }
        return;
      }
      try {
        const data = await apiFetch(`/profiles/${userId}`);
        if (data && data.parsed_resume) {
          const result = {
            user_id: userId,
            parsed_resume: data.parsed_resume,
            github_enriched: null
          };
          setIntakeResult(result);
          // Cache to localStorage for persistence across page navigations
          try {
            localStorage.setItem("smartapply_parsed_resume", JSON.stringify(result));
          } catch (e) { /* storage full */ }
        } else {
          // DB returned no data — try localStorage fallback
          try {
            const cached = localStorage.getItem("smartapply_parsed_resume");
            if (cached) {
              const parsed = JSON.parse(cached);
              if (parsed && parsed.parsed_resume) {
                setIntakeResult(parsed);
              }
            }
          } catch (e) { /* ignore */ }
        }
      } catch (err: any) {
        console.warn("Failed to load existing profile from DB:", err.message);
        // Fallback to localStorage
        try {
          const cached = localStorage.getItem("smartapply_parsed_resume");
          if (cached) {
            const parsed = JSON.parse(cached);
            if (parsed && parsed.parsed_resume) {
              setIntakeResult(parsed);
            }
          }
        } catch (e) { /* ignore */ }
      }
    }

    loadExistingProfile();
  }, [userId]);

  // Sync loaded resume status with parent component
  useEffect(() => {
    if (onResumeLoaded) {
      onResumeLoaded(!!intakeResult);
    }
  }, [intakeResult, onResumeLoaded]);

  // Manual Entry States
  const [isManualEntry, setIsManualEntry] = useState(false);
  const [manualName, setManualName] = useState("");
  const [manualEmail, setManualEmail] = useState("");
  const [manualPhone, setManualPhone] = useState("");
  const [manualSkills, setManualSkills] = useState("");
  const [manualRole, setManualRole] = useState("");
  const [manualCompany, setManualCompany] = useState("");
  const [manualStartDate, setManualStartDate] = useState("");
  const [manualEndDate, setManualEndDate] = useState("");
  const [manualBullets, setManualBullets] = useState("");

  const handleTailorSuccess = (
    tailored: ResumeParsedData,
    gaps: any,
    truth: any,
    score: number
  ) => {
    setTailoredResume(tailored);
    setGapAnalysis(gaps);
    setTruthfulnessReport(truth);
    setAtsScore(score);
    setTailorStep("gate");
  };

  const handleFinalApprove = (finalized: ResumeParsedData) => {
    setTailoredResume(finalized);
    setTailorStep("done");
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const data = await apiFetch("/intake", {
        method: "POST",
        body: formData,
      });
      setIntakeResult(data);
      // Persist to localStorage for cross-navigation persistence
      try {
        localStorage.setItem("smartapply_parsed_resume", JSON.stringify(data));
      } catch (e) { /* storage full */ }

      // If user is logged in, automatically save/persist the parsed resume to their database profile
      if (userId) {
        try {
          await apiFetch("/profiles", {
            method: "POST",
            body: JSON.stringify({
              user_id: userId,
              parsed_resume: data.parsed_resume,
              major: "Computer Science"
            })
          });
        } catch (dbErr) {
          console.error("Failed to automatically sync uploaded resume with DB profile:", dbErr);
        }
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (format: "pdf" | "docx") => {
    if (!intakeResult) return;
    setDownloading(format);
    try {
      const dataToRender = tailoredResume || intakeResult.parsed_resume;
      const res = await apiFetch(`/render?format=${format}`, {
        method: "POST",
        body: JSON.stringify(dataToRender),
      });

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `resume.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Download failed: ${err.message}`);
    } finally {
      setDownloading(null);
    }
  };

  const resume = tailoredResume || intakeResult?.parsed_resume;
  const github = intakeResult?.github_enriched;

  const startEditingSection = (section: "contact" | "experience" | "projects" | "education" | "skills") => {
    setEditedResume(JSON.parse(JSON.stringify(resume)));
    if (section === "contact") setIsEditingContact(true);
    else if (section === "experience") setIsEditingExp(true);
    else if (section === "projects") setIsEditingProj(true);
    else if (section === "education") setIsEditingEdu(true);
    else if (section === "skills") setIsEditingSkills(true);
  };

  const cancelEditingSection = (section: "contact" | "experience" | "projects" | "education" | "skills") => {
    if (section === "contact") setIsEditingContact(false);
    else if (section === "experience") setIsEditingExp(false);
    else if (section === "projects") setIsEditingProj(false);
    else if (section === "education") setIsEditingEdu(false);
    else if (section === "skills") setIsEditingSkills(false);
    setEditedResume(null);
  };

  const handleSaveSection = async (section: "contact" | "experience" | "projects" | "education" | "skills", data: any) => {
    if (!editedResume) return;
    setSavingCorrections(true);
    try {
      let updatedResume;
      if (section === "contact") {
        updatedResume = { 
          ...editedResume, 
          name: data.name,
          email: data.email,
          phone: data.phone,
          links: data.links,
          anchor_line: data.anchor_line
        };
      } else {
        updatedResume = { ...editedResume, [section]: data };
      }

      if (userId) {
        await apiFetch(`/profiles/${userId}`, {
          method: "PATCH",
          body: JSON.stringify({
            parsed_resume: updatedResume
          })
        });
        alert(`${section.charAt(0).toUpperCase() + section.slice(1)} updated successfully!`);
      } else {
        alert(`${section.charAt(0).toUpperCase() + section.slice(1)} updated locally.`);
      }

      if (tailoredResume) {
        setTailoredResume(updatedResume);
      } else if (intakeResult) {
        setIntakeResult({
          ...intakeResult,
          parsed_resume: updatedResume
        });
      }
      
      if (section === "contact") setIsEditingContact(false);
      else if (section === "experience") setIsEditingExp(false);
      else if (section === "projects") setIsEditingProj(false);
      else if (section === "education") setIsEditingEdu(false);
      else if (section === "skills") setIsEditingSkills(false);
      
      setEditedResume(null);
    } catch (err: any) {
      alert(err.message || `Failed to update ${section}.`);
    } finally {
      setSavingCorrections(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-8">
      {/* Upload Zone */}
      {!intakeResult && !isManualEntry && (
        <div className="space-y-4">
          <motion.form
            onSubmit={handleUpload}
            whileHover={{ scale: 1.015, y: -2 }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
            className="p-10 border-2 border-dashed border-slate-300 dark:border-slate-800 rounded-3xl glass-card flex flex-col items-center justify-center space-y-6 hover:border-indigo-500 dark:hover:border-indigo-500/60 transition-all duration-300 shadow-xl shadow-indigo-500/5 relative overflow-hidden group"
          >
            {/* Top accent light */}
            <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-indigo-500 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            
            <div className="p-4 bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 rounded-2xl group-hover:scale-110 group-hover:bg-indigo-500/20 transition-all duration-300">
              <Upload className="w-8 h-8" />
            </div>
            
            <div className="text-center space-y-2">
              <h3 className="text-xl font-extrabold text-slate-800 dark:text-slate-100 tracking-tight">
                Upload your PDF resume
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">
                Drag and drop or browse to import your profile details
              </p>
            </div>
            
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="hidden"
              id="resume-file-input"
            />
            
            <motion.label
              htmlFor="resume-file-input"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="px-8 py-3 rounded-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm transition-all duration-200 cursor-pointer shadow-md shadow-indigo-500/20 inline-flex items-center gap-2"
            >
              {file ? file.name : "Select Resume File"}
            </motion.label>

            {file && (
              <motion.button
                type="submit"
                disabled={uploading}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="w-full max-w-xs py-3 rounded-xl bg-slate-800 hover:bg-slate-700 dark:bg-slate-200 dark:hover:bg-white text-white dark:text-slate-900 font-bold text-sm transition-all duration-200 flex items-center justify-center gap-2 shadow-sm border border-slate-700/20 dark:border-white"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Extracting Credentials...
                  </>
                ) : (
                  "Upload & Parse Profile"
                )}
              </motion.button>
            )}

            {error && (
              <div className="w-full p-4 rounded-xl border border-rose-500/20 bg-rose-500/10 text-rose-600 dark:text-rose-300 text-sm flex items-start gap-2 max-w-md text-left">
                <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold">Extraction Failed</span>
                  <p className="text-xs text-rose-500 dark:text-rose-400 mt-1">{error}</p>
                </div>
              </div>
            )}
          </motion.form>
          
          <div className="text-center">
            <button
              onClick={() => setIsManualEntry(true)}
              className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 dark:hover:text-indigo-300 text-sm font-bold hover:underline transition duration-200"
            >
              Or fill in your details manually &rarr;
            </button>
          </div>
        </div>
      )}

      {/* Manual Entry Form */}
      {!intakeResult && isManualEntry && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!manualName.trim() || !manualEmail.trim()) {
              alert("Name and Email are required.");
              return;
            }
            const bulletsArray = manualBullets
              .split("\n")
              .map((b) => b.trim())
              .filter(Boolean);
            
            const manualProfile: ResumeParsedData = {
              name: manualName.trim(),
              email: manualEmail.trim(),
              phone: manualPhone.trim() || undefined,
              links: [],
              skills: manualSkills
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean),
              education: [],
              experience: [
                {
                  role: manualRole.trim() || "Software Engineer",
                  company: manualCompany.trim() || "Self-Employed",
                  start_date: manualStartDate.trim() || "2023-01",
                  end_date: manualEndDate.trim() || "Present",
                  bullets: bulletsArray.length > 0 ? bulletsArray : ["Developed backend and frontend software services."]
                }
              ],
              projects: []
            };

            // Call POST /profiles to save to DB and trigger embedding generation
            const userId = "manual-" + Math.random().toString(36).substring(2, 9);
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
            
            fetch(`${backendUrl}/profiles`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                user_id: userId,
                parsed_resume: manualProfile
              })
            })
            .then(res => res.json())
            .then(data => {
              setIntakeResult({
                user_id: data.user_id || userId,
                parsed_resume: manualProfile,
                github_enriched: null
              });
            })
            .catch(err => {
              console.error("Failed to save manual profile to backend:", err);
              // Fallback to transient local state
              setIntakeResult({
                user_id: userId,
                parsed_resume: manualProfile,
                github_enriched: null
              });
            });

            setIsManualEntry(false);
          }}
          className="p-8 border border-slate-800 rounded-3xl bg-slate-900/20 backdrop-blur-xl space-y-6 max-w-2xl mx-auto animate-fade-in"
        >
          <div className="flex justify-between items-center pb-4 border-b border-slate-800">
            <h3 className="text-lg font-bold text-slate-200">Manual Profile Setup</h3>
            <button
              type="button"
              onClick={() => setIsManualEntry(false)}
              className="text-slate-400 hover:text-slate-200 text-sm transition"
            >
              Cancel
            </button>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-400">Name *</label>
              <input
                type="text"
                required
                value={manualName}
                onChange={(e) => setManualName(e.target.value)}
                placeholder="Eyad Arshad"
                className="w-full px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/40 text-slate-200 text-sm focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-400">Email *</label>
              <input
                type="email"
                required
                value={manualEmail}
                onChange={(e) => setManualEmail(e.target.value)}
                placeholder="eyad@example.com"
                className="w-full px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/40 text-slate-200 text-sm focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-400">Phone</label>
              <input
                type="text"
                value={manualPhone}
                onChange={(e) => setManualPhone(e.target.value)}
                placeholder="+92-300-1234567"
                className="w-full px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/40 text-slate-200 text-sm focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-400">Skills (comma-separated)</label>
              <input
                type="text"
                value={manualSkills}
                onChange={(e) => setManualSkills(e.target.value)}
                placeholder="Python, FastAPI, React, PostgreSQL"
                className="w-full px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/40 text-slate-200 text-sm focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="border-t border-slate-800 pt-4 space-y-4">
            <h4 className="text-sm font-semibold text-indigo-400">Add Primary Work Experience</h4>
            
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-400">Role Title</label>
                <input
                  type="text"
                  value={manualRole}
                  onChange={(e) => setManualRole(e.target.value)}
                  placeholder="Backend Engineer Intern"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/40 text-slate-200 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-400">Company Name</label>
                <input
                  type="text"
                  value={manualCompany}
                  onChange={(e) => setManualCompany(e.target.value)}
                  placeholder="TechCorp"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/40 text-slate-200 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-400">Start Date</label>
                <input
                  type="text"
                  value={manualStartDate}
                  onChange={(e) => setManualStartDate(e.target.value)}
                  placeholder="2023-06"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/40 text-slate-200 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-400">End Date</label>
                <input
                  type="text"
                  value={manualEndDate}
                  onChange={(e) => setManualEndDate(e.target.value)}
                  placeholder="2023-12 (or 'Present')"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/40 text-slate-200 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-400">Experience Achievements (one per line)</label>
              <textarea
                rows={3}
                value={manualBullets}
                onChange={(e) => setManualBullets(e.target.value)}
                placeholder="Developed backend services using Python and FastAPI.&#10;Optimized database queries decreasing latency by 20%."
                className="w-full px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/40 text-slate-200 text-sm focus:border-indigo-500 focus:outline-none font-sans"
              />
            </div>
          </div>

          <button
            type="submit"
            className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-semibold text-sm transition duration-200"
          >
            Create & Save Profile
          </button>
        </form>
      )}

      {/* 1. Tailor Input Panel */}
      {intakeResult && resume && tailorStep === "input" && (
        <TailorPanel
          user_id={intakeResult.user_id}
          parsed_resume={intakeResult.parsed_resume}
          onTailorSuccess={handleTailorSuccess}
          initialJdText={selectedJdText}
          onBack={() => setTailorStep(tailoredResume ? "done" : "idle")}
        />
      )}

      {/* 2. Truthfulness Gate panel */}
      {intakeResult && resume && tailorStep === "gate" && gapAnalysis && truthfulnessReport && tailoredResume && (
        <TruthfulnessGate
          atsScore={atsScore}
          gapAnalysis={gapAnalysis}
          truthfulnessReport={truthfulnessReport}
          tailoredResume={tailoredResume}
          onFinalApprove={handleFinalApprove}
          onReset={() => setTailorStep("input")}
        />
      )}

      {/* 3. Result Profile view (Idle or Finalized Done state) */}
      {intakeResult && resume && (tailorStep === "idle" || tailorStep === "done") && (
        <div className="p-6 md:p-8 rounded-3xl glass-card space-y-8 animate-fade-in">
          {/* Header Card */}
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 pb-6 border-b border-slate-200 dark:border-slate-800">
            {isEditingContact && editedResume ? (
              <div className="flex flex-col gap-3 w-full max-w-lg mt-2 text-left">
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Full Name</label>
                  <input
                    type="text"
                    value={editedResume.name}
                    onChange={(e) => setEditedResume({ ...editedResume, name: e.target.value })}
                    className="bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
                  />
                </div>
                <div className="flex gap-3">
                  <div className="flex flex-col gap-1 flex-1">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Email Address</label>
                    <input
                      type="email"
                      value={editedResume.email}
                      onChange={(e) => setEditedResume({ ...editedResume, email: e.target.value })}
                      className="bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
                    />
                  </div>
                  <div className="flex flex-col gap-1 flex-1">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Phone</label>
                    <input
                      type="text"
                      value={editedResume.phone || ""}
                      onChange={(e) => setEditedResume({ ...editedResume, phone: e.target.value })}
                      className="bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
                    />
                  </div>
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Tagline / Anchor Line</label>
                  <input
                    type="text"
                    value={editedResume.anchor_line || ""}
                    onChange={(e) => setEditedResume({ ...editedResume, anchor_line: e.target.value })}
                    className="bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
                  />
                </div>
              </div>
            ) : (
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  {tailorStep === "done" ? (
                    <Sparkles className="w-5 h-5 text-indigo-500 dark:text-indigo-400" />
                  ) : (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 dark:text-emerald-400" />
                  )}
                  <h2 className="text-2xl font-bold text-slate-855 dark:text-white">
                    {resume.name}
                    {tailorStep === "done" && (
                      <span className="ml-3 text-xs font-semibold text-indigo-600 dark:text-indigo-400 border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                        Tailored (ATS: {atsScore}%)
                      </span>
                    )}
                  </h2>
                </div>
                <p className="text-sm text-slate-500 dark:text-slate-400">{resume.email} {resume.phone ? `| ${resume.phone}` : ""}</p>
                <div className="flex flex-wrap gap-2 mt-2">
                  {resume.links.map((link, idx) => (
                    <a
                      key={idx}
                      href={link.startsWith("http") ? link : `https://${link}`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
                    >
                      {link}
                    </a>
                  ))}
                </div>
                {resume.anchor_line && (
                  <div className="mt-3 text-sm font-medium italic text-indigo-600 dark:text-indigo-300 border-l-2 border-indigo-500/60 pl-3 py-0.5">
                    &ldquo;{resume.anchor_line}&rdquo;
                  </div>
                )}
              </div>
            )}

            {/* Document Render Controls */}
            <div className="flex gap-3">
              {tailorStep === "idle" && (
                <button
                  onClick={() => setTailorStep("input")}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition flex items-center gap-1.5 shadow-sm"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Tailor for Job
                </button>
              )}
              {tailorStep === "done" && (
                <button
                  onClick={() => setTailorStep("input")}
                  className="px-4 py-2 rounded-xl text-xs font-semibold border border-indigo-500/30 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-500/10 transition flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Re-Tailor
                </button>
              )}
              <button
                onClick={() => handleDownload("pdf")}
                disabled={!!downloading}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-500/10 border border-indigo-500/30 text-indigo-600 dark:text-indigo-300 hover:bg-indigo-500/20 transition flex items-center gap-1.5 disabled:opacity-50"
              >
                {downloading === "pdf" ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Download className="w-3.5 h-3.5" />
                )}
                Download PDF
              </button>
              <button
                onClick={() => handleDownload("docx")}
                disabled={!!downloading}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-300 hover:bg-emerald-500/20 transition flex items-center gap-1.5 disabled:opacity-50"
              >
                {downloading === "docx" ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <FileText className="w-3.5 h-3.5" />
                )}
                Download DOCX
              </button>
              {isEditingContact ? (
                <>
                  <button
                    onClick={() => handleSaveSection("contact", editedResume)}
                    disabled={savingCorrections}
                    className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition flex items-center gap-1.5 shadow-sm disabled:opacity-50"
                  >
                    {savingCorrections ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                    Save Info
                  </button>
                  <button
                    onClick={() => cancelEditingSection("contact")}
                    className="px-4 py-2 rounded-xl text-xs font-semibold border border-slate-350 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <button
                  onClick={() => startEditingSection("contact")}
                  className="px-4 py-2 rounded-xl text-xs font-semibold border border-indigo-500/30 text-indigo-650 dark:text-indigo-400 hover:bg-indigo-500/10 transition flex items-center gap-1.5"
                >
                  <Edit className="w-3.5 h-3.5" />
                  Edit Contact
                </button>
              )}
              <button
                onClick={() => {
                  setFile(null);
                  setIntakeResult(null);
                  setTailorStep("idle");
                  setTailoredResume(null);
                  setGapAnalysis(null);
                  setTruthfulnessReport(null);
                  setAtsScore(0);
                }}
                className="px-4 py-2 rounded-xl text-xs font-semibold border border-slate-350 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                Reset
              </button>
            </div>
          </div>

          {/* Highlights strip callout */}
          {resume.highlights_strip && resume.highlights_strip.length > 0 && (
            <div className="p-5 rounded-2xl bg-indigo-500/5 border border-indigo-500/10 space-y-2 animate-fade-in">
              <h4 className="text-xs font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">Relevance & Highlights</h4>
              <ul className="grid md:grid-cols-2 gap-3 text-xs text-slate-600 dark:text-slate-300 pl-4 list-disc font-light">
                {resume.highlights_strip.map((hl: any, idx: number) => (
                  <li key={idx}>
                    <span className="font-semibold text-slate-700 dark:text-slate-200">{hl.skill}</span>: {hl.relevance_reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Navigation Tabs */}
          <div className="flex gap-2 border-b border-slate-200 dark:border-slate-800/80 pb-2 overflow-x-auto whitespace-nowrap">
            {(["experience", "projects", "education", "skills", "github", "jobs", "templates", "tracker"] as const).map((tab) => {
              if (tab === "github" && !github) return null;
              const isActive = activeTab === tab;
              
              const labelMap: Record<string, string> = {
                experience: "Work History",
                projects: "Projects",
                education: "Education",
                skills: "Skill Map",
                github: "GitHub Insights",
                jobs: "Job Matches",
                templates: "AI Resume",
                tracker: "Tracker",
              };
              
              return (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`relative px-4 py-2 rounded-xl text-sm font-bold transition duration-300 ${
                    isActive
                      ? "text-indigo-600 dark:text-indigo-400"
                      : "text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
                  }`}
                >
                  {isActive && (
                    <motion.div
                      layoutId="active-tab-capsule"
                      className="absolute inset-0 bg-indigo-500/10 dark:bg-indigo-500/10 border-b-2 border-indigo-500 z-0 rounded-xl"
                      transition={{ type: "spring", stiffness: 350, damping: 25 }}
                    />
                  )}
                  <span className="relative z-10">{labelMap[tab]}</span>
                </button>
              );
            })}
          </div>

          {/* Tab Content Panel */}
          <div className="py-4 min-h-[300px]">
            {/* Experience Panel */}
            {activeTab === "experience" && (
              <div className="space-y-6">
                <div className="flex justify-between items-center pb-2 border-b border-slate-200 dark:border-slate-800">
                  <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">Work History</h3>
                  <div className="flex gap-2">
                    {isEditingExp ? (
                      <>
                        <button
                          type="button"
                          onClick={() => handleSaveSection("experience", editedResume?.experience)}
                          disabled={savingCorrections}
                          className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1 shadow-sm disabled:opacity-50"
                        >
                          {savingCorrections ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                          Save
                        </button>
                        <button
                          type="button"
                          onClick={() => cancelEditingSection("experience")}
                          className="px-3 py-1.5 rounded-lg border border-slate-350 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition text-xs font-semibold"
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        onClick={() => startEditingSection("experience")}
                        className="px-3 py-1.5 rounded-lg border border-indigo-500/20 text-indigo-650 dark:text-indigo-400 hover:bg-indigo-500/10 text-xs font-semibold flex items-center gap-1"
                      >
                        <Edit className="w-3.5 h-3.5" />
                        Edit History
                      </button>
                    )}
                  </div>
                </div>

                {isEditingExp && editedResume ? (
                  <div className="space-y-6">
                    {editedResume.experience.map((exp, idx) => (
                      <div key={idx} className="space-y-4 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/40 dark:bg-slate-950/20 text-left">
                        <div className="flex justify-between items-start">
                          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Experience {idx + 1}</span>
                          <button
                            type="button"
                            onClick={() => {
                              const newExperience = [...editedResume.experience];
                              newExperience.splice(idx, 1);
                              setEditedResume({ ...editedResume, experience: newExperience });
                            }}
                            className="text-rose-500 hover:text-rose-400 text-[10px] font-bold uppercase tracking-wider flex items-center gap-1"
                          >
                            <Trash2 className="w-3 h-3" /> Remove
                          </button>
                        </div>
                        <div className="grid md:grid-cols-2 gap-4">
                          <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Role Title</label>
                            <input
                              type="text"
                              value={exp.role}
                              onChange={(e) => {
                                const newExp = [...editedResume.experience];
                                newExp[idx] = { ...exp, role: e.target.value };
                                setEditedResume({ ...editedResume, experience: newExp });
                              }}
                              className="bg-slate-955 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
                            />
                          </div>
                          <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Company Name</label>
                            <input
                              type="text"
                              value={exp.company}
                              onChange={(e) => {
                                const newExp = [...editedResume.experience];
                                newExp[idx] = { ...exp, company: e.target.value };
                                setEditedResume({ ...editedResume, experience: newExp });
                              }}
                              className="bg-slate-955 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
                            />
                          </div>
                        </div>
                        <div className="grid md:grid-cols-2 gap-4">
                          <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Start Date</label>
                            <input
                              type="text"
                              value={exp.start_date}
                              onChange={(e) => {
                                const newExp = [...editedResume.experience];
                                newExp[idx] = { ...exp, start_date: e.target.value };
                                setEditedResume({ ...editedResume, experience: newExp });
                              }}
                              className="bg-slate-955 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
                            />
                          </div>
                          <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">End Date (or 'Present')</label>
                            <input
                              type="text"
                              value={exp.end_date || ""}
                              onChange={(e) => {
                                const newExp = [...editedResume.experience];
                                newExp[idx] = { ...exp, end_date: e.target.value };
                                setEditedResume({ ...editedResume, experience: newExp });
                              }}
                              className="bg-slate-955 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
                            />
                          </div>
                        </div>
                        <div className="flex flex-col gap-1.5">
                          <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Achievement Bullets (one per line)</label>
                          <textarea
                            rows={4}
                            value={exp.bullets.join("\n")}
                            onChange={(e) => {
                              const newExp = [...editedResume.experience];
                              newExp[idx] = { ...exp, bullets: e.target.value.split("\n") };
                              setEditedResume({ ...editedResume, experience: newExp });
                            }}
                            className="bg-slate-955 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none font-sans"
                          />
                        </div>
                      </div>
                    ))}
                    <button
                      type="button"
                      onClick={() => {
                        const newExperience = {
                          role: "",
                          company: "",
                          start_date: "",
                          end_date: "Present",
                          location: "",
                          bullets: []
                        };
                        setEditedResume({ ...editedResume, experience: [...editedResume.experience, newExperience] });
                      }}
                      className="px-4 py-2.5 rounded-xl bg-indigo-600/10 hover:bg-indigo-600/20 border border-indigo-500/20 text-indigo-650 dark:text-indigo-400 text-xs font-semibold transition flex items-center gap-1.5"
                    >
                      <Plus className="w-3.5 h-3.5" /> Add Experience
                    </button>
                  </div>
                ) : (
                  resume.experience.length === 0 ? (
                    <p className="text-slate-500 dark:text-slate-400 text-sm">No work experience listed (Fresher profile).</p>
                  ) : (
                    resume.experience.map((exp, idx) => (
                      <div key={idx} className="space-y-2 text-left">
                        <div className="flex justify-between items-start">
                          <div>
                            <h4 className="text-base font-bold text-slate-800 dark:text-slate-200">{exp.role}</h4>
                            <span className="text-sm text-slate-500 dark:text-slate-400">{exp.company} {exp.location ? `· ${exp.location}` : ""}</span>
                          </div>
                          <span className="text-xs text-indigo-650 dark:text-indigo-400 font-semibold bg-indigo-500/10 px-2.5 py-1 rounded-full">
                            {exp.start_date} &ndash; {exp.end_date || "Present"}
                          </span>
                        </div>
                        <ul className="list-disc pl-5 text-sm text-slate-600 dark:text-slate-300 space-y-1">
                          {exp.bullets.map((bullet: string, bIdx: number) => (
                            <li key={bIdx}>{bullet}</li>
                          ))}
                        </ul>
                      </div>
                    ))
                  )
                )}
              </div>
            )}
            {/* Projects Panel */}
            {activeTab === "projects" && (
              <div className="space-y-6">
                <div className="flex justify-between items-center pb-2 border-b border-slate-200 dark:border-slate-800">
                  <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">Projects</h3>
                  <div className="flex gap-2">
                    {isEditingProj ? (
                      <>
                        <button
                          type="button"
                          onClick={() => handleSaveSection("projects", editedResume?.projects)}
                          disabled={savingCorrections}
                          className="px-3 py-1.5 rounded-lg bg-emerald-650 hover:bg-emerald-650 text-white text-xs font-semibold flex items-center gap-1 shadow-sm disabled:opacity-50"
                        >
                          {savingCorrections ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                          Save
                        </button>
                        <button
                          type="button"
                          onClick={() => cancelEditingSection("projects")}
                          className="px-3 py-1.5 rounded-lg border border-slate-350 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition text-xs font-semibold"
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        onClick={() => startEditingSection("projects")}
                        className="px-3 py-1.5 rounded-lg border border-indigo-500/20 text-indigo-650 dark:text-indigo-400 hover:bg-indigo-500/10 text-xs font-semibold flex items-center gap-1"
                      >
                        <Edit className="w-3.5 h-3.5" />
                        Edit Projects
                      </button>
                    )}
                  </div>
                </div>

                {isEditingProj && editedResume ? (
                  <div className="space-y-6">
                    {editedResume.projects.map((proj, idx) => (
                      <div key={idx} className="space-y-4 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/40 dark:bg-slate-950/20 text-left">
                        <div className="flex justify-between items-start">
                          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Project {idx + 1}</span>
                          <button
                            type="button"
                            onClick={() => {
                              const newProjects = [...editedResume.projects];
                              newProjects.splice(idx, 1);
                              setEditedResume({ ...editedResume, projects: newProjects });
                            }}
                            className="text-rose-500 hover:text-rose-400 text-[10px] font-bold uppercase tracking-wider flex items-center gap-1"
                          >
                            <Trash2 className="w-3 h-3" /> Remove
                          </button>
                        </div>
                        <div className="grid md:grid-cols-2 gap-4">
                          <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Project Name</label>
                            <input
                              type="text"
                              value={proj.name}
                              onChange={(e) => {
                                const newProj = [...editedResume.projects];
                                newProj[idx] = { ...proj, name: e.target.value };
                                setEditedResume({ ...editedResume, projects: newProj });
                              }}
                              className="bg-slate-955 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
                            />
                          </div>
                          <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Project Link</label>
                            <input
                              type="text"
                              value={proj.link || ""}
                              onChange={(e) => {
                                const newProj = [...editedResume.projects];
                                newProj[idx] = { ...proj, link: e.target.value };
                                setEditedResume({ ...editedResume, projects: newProj });
                              }}
                              className="bg-slate-955 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
                            />
                          </div>
                        </div>
                        <div className="flex flex-col gap-1.5">
                          <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Achievement Bullets (one per line)</label>
                          <textarea
                            rows={4}
                            value={proj.bullets.join("\n")}
                            onChange={(e) => {
                              const newProj = [...editedResume.projects];
                              newProj[idx] = { ...proj, bullets: e.target.value.split("\n") };
                              setEditedResume({ ...editedResume, projects: newProj });
                            }}
                            className="bg-slate-955 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none font-sans"
                          />
                        </div>
                      </div>
                    ))}
                    <button
                      type="button"
                      onClick={() => {
                        const newProject = {
                          name: "",
                          link: "",
                          bullets: []
                        };
                        setEditedResume({ ...editedResume, projects: [...editedResume.projects, newProject] });
                      }}
                      className="px-4 py-2.5 rounded-xl bg-indigo-600/10 hover:bg-indigo-600/20 border border-indigo-500/20 text-indigo-650 dark:text-indigo-400 text-xs font-semibold transition flex items-center gap-1.5"
                    >
                      <Plus className="w-3.5 h-3.5" /> Add Project
                    </button>
                  </div>
                ) : (
                  resume.projects.length === 0 ? (
                    <p className="text-slate-500 dark:text-slate-400 text-sm">No personal projects listed.</p>
                  ) : (
                    resume.projects.map((proj, idx) => (
                      <div key={idx} className="space-y-2 text-left">
                        <div className="flex justify-between items-center">
                          <h4 className="text-base font-bold text-slate-800 dark:text-slate-200">{proj.name}</h4>
                          {proj.link && (
                            <a
                              href={proj.link.startsWith("http") ? proj.link : `https://${proj.link}`}
                              target="_blank"
                              rel="noreferrer"
                              className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
                            >
                              Project Link
                            </a>
                          )}
                        </div>
                        <ul className="list-disc pl-5 text-sm text-slate-600 dark:text-slate-300 space-y-1">
                          {proj.bullets.map((bullet: string, bIdx: number) => (
                            <li key={bIdx}>{bullet}</li>
                          ))}
                        </ul>
                      </div>
                    ))
                  )
                )}
              </div>
            )}

            {/* Education Panel */}
            {activeTab === "education" && (
              <div className="space-y-6">
                <div className="flex justify-between items-center pb-2 border-b border-slate-200 dark:border-slate-800">
                  <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">Education</h3>
                  <div className="flex gap-2">
                    {isEditingEdu ? (
                      <>
                        <button
                          type="button"
                          onClick={() => handleSaveSection("education", editedResume?.education)}
                          disabled={savingCorrections}
                          className="px-3 py-1.5 rounded-lg bg-emerald-650 hover:bg-emerald-600 text-white text-xs font-semibold flex items-center gap-1 shadow-sm disabled:opacity-50"
                        >
                          {savingCorrections ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                          Save
                        </button>
                        <button
                          type="button"
                          onClick={() => cancelEditingSection("education")}
                          className="px-3 py-1.5 rounded-lg border border-slate-350 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition text-xs font-semibold"
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        onClick={() => startEditingSection("education")}
                        className="px-3 py-1.5 rounded-lg border border-indigo-500/20 text-indigo-650 dark:text-indigo-400 hover:bg-indigo-500/10 text-xs font-semibold flex items-center gap-1"
                      >
                        <Edit className="w-3.5 h-3.5" />
                        Edit Education
                      </button>
                    )}
                  </div>
                </div>

                {isEditingEdu && editedResume ? (
                  <div className="space-y-6">
                    {editedResume.education.map((edu, idx) => (
                      <div key={idx} className="space-y-4 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/40 dark:bg-slate-950/20 text-left">
                        <div className="flex justify-between items-start">
                          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Education {idx + 1}</span>
                          <button
                            type="button"
                            onClick={() => {
                              const newEducation = [...editedResume.education];
                              newEducation.splice(idx, 1);
                              setEditedResume({ ...editedResume, education: newEducation });
                            }}
                            className="text-rose-500 hover:text-rose-400 text-[10px] font-bold uppercase tracking-wider flex items-center gap-1"
                          >
                            <Trash2 className="w-3 h-3" /> Remove
                          </button>
                        </div>
                        <div className="grid md:grid-cols-2 gap-4">
                          <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Degree</label>
                            <input
                              type="text"
                              value={edu.degree}
                              onChange={(e) => {
                                const newEdu = [...editedResume.education];
                                newEdu[idx] = { ...edu, degree: e.target.value };
                                setEditedResume({ ...editedResume, education: newEdu });
                              }}
                              className="bg-slate-955 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
                            />
                          </div>
                          <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Field of Study / Major</label>
                            <input
                              type="text"
                              value={edu.major || ""}
                              onChange={(e) => {
                                const newEdu = [...editedResume.education];
                                newEdu[idx] = { ...edu, major: e.target.value };
                                setEditedResume({ ...editedResume, education: newEdu });
                              }}
                              className="bg-slate-955 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
                            />
                          </div>
                        </div>
                        <div className="grid md:grid-cols-2 gap-4">
                          <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">School / University</label>
                            <input
                              type="text"
                              value={edu.school}
                              onChange={(e) => {
                                const newEdu = [...editedResume.education];
                                newEdu[idx] = { ...edu, school: e.target.value };
                                setEditedResume({ ...editedResume, education: newEdu });
                              }}
                              className="bg-slate-955 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
                            />
                          </div>
                          <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">GPA</label>
                            <input
                              type="text"
                              value={edu.gpa || ""}
                              onChange={(e) => {
                                const newEdu = [...editedResume.education];
                                newEdu[idx] = { ...edu, gpa: e.target.value };
                                setEditedResume({ ...editedResume, education: newEdu });
                              }}
                              className="bg-slate-955 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
                            />
                          </div>
                        </div>
                        <div className="flex flex-col gap-1.5">
                          <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Dates / Graduation Year</label>
                          <input
                            type="text"
                            value={edu.date}
                            onChange={(e) => {
                              const newEdu = [...editedResume.education];
                              newEdu[idx] = { ...edu, date: e.target.value };
                              setEditedResume({ ...editedResume, education: newEdu });
                            }}
                            className="bg-slate-955 border border-slate-800 focus:border-indigo-500 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none"
                          />
                        </div>
                      </div>
                    ))}
                    <button
                      type="button"
                      onClick={() => {
                        const newEducation = {
                          degree: "",
                          major: "",
                          school: "",
                          date: "",
                          gpa: ""
                        };
                        setEditedResume({ ...editedResume, education: [...editedResume.education, newEducation] });
                      }}
                      className="px-4 py-2.5 rounded-xl bg-indigo-600/10 hover:bg-indigo-600/20 border border-indigo-500/20 text-indigo-650 dark:text-indigo-400 text-xs font-semibold transition flex items-center gap-1.5"
                    >
                      <Plus className="w-3.5 h-3.5" /> Add Education
                    </button>
                  </div>
                ) : (
                  <div className="space-y-6 text-left">
                    {resume.education.map((edu, idx) => (
                      <div key={idx} className="space-y-1">
                        <div className="flex justify-between items-start">
                          <h4 className="text-base font-bold text-slate-800 dark:text-slate-200">
                            {edu.degree} {edu.major ? `in ${edu.major}` : ""}
                          </h4>
                          <span className="text-xs text-indigo-650 dark:text-indigo-400 font-semibold bg-indigo-500/10 px-2.5 py-1 rounded-full">
                            {edu.date}
                          </span>
                        </div>
                        <p className="text-sm text-slate-500 dark:text-slate-400">{edu.school}</p>
                        {edu.gpa && <span className="text-xs text-emerald-600 dark:text-emerald-405 font-semibold">GPA: {edu.gpa}</span>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Skills Panel */}
            {activeTab === "skills" && (
              <div className="space-y-6">
                <div className="flex justify-between items-center pb-2 border-b border-slate-200 dark:border-slate-800">
                  <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">Skill Map</h3>
                  <div className="flex gap-2">
                    {isEditingSkills ? (
                      <>
                        <button
                          type="button"
                          onClick={() => handleSaveSection("skills", editedResume?.skills)}
                          disabled={savingCorrections}
                          className="px-3 py-1.5 rounded-lg bg-emerald-650 hover:bg-emerald-650 text-white text-xs font-semibold flex items-center gap-1 shadow-sm disabled:opacity-50"
                        >
                          {savingCorrections ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                          Save
                        </button>
                        <button
                          type="button"
                          onClick={() => cancelEditingSection("skills")}
                          className="px-3 py-1.5 rounded-lg border border-slate-350 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition text-xs font-semibold"
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        onClick={() => startEditingSection("skills")}
                        className="px-3 py-1.5 rounded-lg border border-indigo-500/20 text-indigo-650 dark:text-indigo-400 hover:bg-indigo-500/10 text-xs font-semibold flex items-center gap-1"
                      >
                        <Edit className="w-3.5 h-3.5" />
                        Edit Skills
                      </button>
                    )}
                  </div>
                </div>

                {isEditingSkills && editedResume ? (
                  <div className="space-y-4 text-left">
                    <div className="flex flex-wrap gap-2.5">
                      {editedResume.skills.map((skill, idx) => (
                        <span
                          key={idx}
                          className="px-3 py-1 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-650 dark:text-indigo-400 text-xs font-semibold flex items-center gap-1.5"
                        >
                          {skill}
                          <button
                            type="button"
                            onClick={() => {
                              const newSkills = [...editedResume.skills];
                              newSkills.splice(idx, 1);
                              setEditedResume({ ...editedResume, skills: newSkills });
                            }}
                            className="text-indigo-600 dark:text-indigo-400 hover:text-rose-500 transition text-[10px] leading-none"
                            aria-label={`Remove ${skill}`}
                          >
                            ✕
                          </button>
                        </span>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="Add new skill..."
                        className="flex-1 px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-955 text-slate-200 text-xs focus:border-indigo-500 outline-none"
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && e.currentTarget.value.trim()) {
                            const newSkill = e.currentTarget.value.trim();
                            const newSkills = [...editedResume.skills, newSkill];
                            setEditedResume({ ...editedResume, skills: newSkills });
                            e.currentTarget.value = "";
                          }
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => {
                          const input = document.querySelector('input[placeholder="Add new skill..."]') as HTMLInputElement;
                          if (input && input.value.trim()) {
                            const newSkill = input.value.trim();
                            const newSkills = [...editedResume.skills, newSkill];
                            setEditedResume({ ...editedResume, skills: newSkills });
                            input.value = "";
                          }
                        }}
                        className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition"
                      >
                        Add
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2.5">
                    {resume.skills.map((skill, idx) => (
                      <span
                        key={idx}
                        className="px-3.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs border border-slate-200 dark:border-slate-700 font-semibold shadow-sm"
                      >
                        {skill}
                      </span>
                    ))}
                    {resume.skills.length === 0 && (
                      <span className="text-xs text-slate-500 dark:text-slate-400">No skills listed</span>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* GitHub Panel */}
            {activeTab === "github" && github && (
              <div className="space-y-6 text-left">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="p-4 rounded-2xl bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex flex-col justify-center shadow-sm">
                    <span className="text-xs text-slate-500 dark:text-slate-400">Total GitHub Stars</span>
                    <span className="text-2xl font-bold text-indigo-650 dark:text-indigo-300 flex items-center gap-1.5 mt-1">
                      <Award className="w-5 h-5 text-yellow-500" />
                      {github.total_stars}
                    </span>
                  </div>
                  <div className="p-4 rounded-2xl bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex flex-col justify-center shadow-sm">
                    <span className="text-xs text-slate-500 dark:text-slate-400">Enriched Username</span>
                    <span className="text-lg font-bold text-slate-800 dark:text-slate-200 mt-1 flex items-center gap-1.5">
                      <Github className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
                      {github.username}
                    </span>
                  </div>
                </div>

                {/* Top Repositories */}
                <div className="space-y-3">
                  <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">Top Repositories</h4>
                  {github.top_repositories.length === 0 ? (
                    <p className="text-slate-500 dark:text-slate-400 text-xs">No repositories found or public access rate-limited.</p>
                  ) : (
                    <div className="grid md:grid-cols-2 gap-4">
                      {github.top_repositories.map((repo, idx) => (
                        <div key={idx} className="p-4 rounded-2xl bg-slate-100/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 flex flex-col justify-between space-y-4 hover:border-indigo-500/20 transition shadow-sm">
                          <div>
                            <div className="flex justify-between items-center">
                              <a
                                href={repo.url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-sm font-bold text-indigo-650 dark:text-indigo-400 hover:underline"
                              >
                                {repo.name}
                              </a>
                              <span className="text-xs text-yellow-600 dark:text-yellow-500 font-semibold bg-yellow-500/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                                ★ {repo.stars}
                              </span>
                            </div>
                            <p className="text-xs text-slate-600 dark:text-slate-400 mt-2 line-clamp-2">{repo.description || "No description provided."}</p>
                          </div>
                          {repo.language && (
                            <span className="text-xs text-slate-700 dark:text-slate-350 font-semibold bg-slate-200 dark:bg-slate-800/80 w-max px-2.5 py-1 rounded-lg">
                              {repo.language}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Jobs Panel */}
            <div className={activeTab === "jobs" ? "block" : "hidden"}>
              <JobSearch
                user_id={userId || intakeResult.user_id}
                parsed_resume={resume}
                onSelectJobForTailoring={(job) => {
                  setSelectedJdText(job.jd_text);
                  setTailorStep("input");
                }}
              />
            </div>
            {/* Templates Panel (AI Resume Generator) */}
            {activeTab === "templates" && (
              <div className="space-y-4">
                <TemplateSelector parsed_resume={resume} />
              </div>
            )}

            {/* Tracker Panel */}
            {activeTab === "tracker" && (
              <div className="space-y-4">
                <TrackerBoard user_id={userId || intakeResult.user_id} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
