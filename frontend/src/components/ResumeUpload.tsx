"use client";

import React, { useState } from "react";
import { Upload, FileText, CheckCircle2, AlertCircle, Github, Download, Award, Loader2, Sparkles, RefreshCw } from "lucide-react";
import TailorPanel from "./TailorPanel";
import TruthfulnessGate from "./TruthfulnessGate";
import JobSearch from "./JobSearch";

interface ResumeParsedData {
  name: string;
  email: string;
  phone?: string;
  links: string[];
  skills: string[];
  education: Array<{
    degree: string;
    major?: string;
    school: string;
    date: string;
    gpa?: string;
  }>;
  experience: Array<{
    role: string;
    company: string;
    start_date: string;
    end_date?: string;
    location?: string;
    bullets: string[];
  }>;
  projects: Array<{
    name: string;
    link?: string;
    bullets: string[];
  }>;
  anchor_line?: string;
  highlights_strip?: Array<{
    skill: string;
    relevance_reason: string;
  }>;
}

interface GitHubEnrichedData {
  username: string;
  total_stars: number;
  languages: Record<string, number>;
  top_repositories: Array<{
    name: string;
    description?: string;
    language?: string;
    stars: number;
    url: string;
  }>;
}

export default function ResumeUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [intakeResult, setIntakeResult] = useState<{
    user_id: string;
    parsed_resume: ResumeParsedData;
    github_enriched: GitHubEnrichedData | null;
  } | null>(null);

  const [activeTab, setActiveTab] = useState<"experience" | "projects" | "education" | "skills" | "github" | "jobs">("experience");
  const [downloading, setDownloading] = useState<string | null>(null);
  const [selectedJdText, setSelectedJdText] = useState<string>("");

  // Tailoring Pipeline States
  const [tailorStep, setTailorStep] = useState<"idle" | "input" | "gate" | "done">("idle");
  const [tailoredResume, setTailoredResume] = useState<ResumeParsedData | null>(null);
  const [gapAnalysis, setGapAnalysis] = useState<any | null>(null);
  const [truthfulnessReport, setTruthfulnessReport] = useState<any | null>(null);
  const [atsScore, setAtsScore] = useState<number>(0);

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
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
      const res = await fetch(`${backendUrl}/intake`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to extract resume details.");
      }

      const data = await res.json();
      setIntakeResult(data);
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
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
      const dataToRender = tailoredResume || intakeResult.parsed_resume;
      const res = await fetch(`${backendUrl}/render?format=${format}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dataToRender),
      });

      if (!res.ok) {
        throw new Error("Failed to render file");
      }

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

  return (
    <div className="w-full max-w-4xl mx-auto space-y-8">
      {/* Upload Zone */}
      {!intakeResult && !isManualEntry && (
        <div className="space-y-4">
          <form onSubmit={handleUpload} className="p-8 border border-dashed border-slate-800 rounded-3xl bg-slate-900/20 backdrop-blur-xl flex flex-col items-center justify-center space-y-6 hover:border-indigo-500/40 transition duration-300 animate-fade-in">
            <div className="p-4 bg-indigo-500/10 text-indigo-400 rounded-2xl">
              <Upload className="w-8 h-8" />
            </div>
            <div className="text-center space-y-1">
              <h3 className="text-lg font-semibold text-slate-200">Upload your PDF resume</h3>
              <p className="text-sm text-slate-400">Drag and drop or browse to select your PDF file</p>
            </div>
            
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="hidden"
              id="resume-file-input"
            />
            <label
              htmlFor="resume-file-input"
              className="px-6 py-2.5 rounded-xl border border-slate-700 bg-slate-800/50 text-slate-200 hover:bg-slate-700 hover:text-white transition duration-200 cursor-pointer font-medium text-sm"
            >
              {file ? file.name : "Select Resume"}
            </label>

            {file && (
              <button
                type="submit"
                disabled={uploading}
                className="w-full max-w-xs py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-semibold text-sm transition duration-200 flex items-center justify-center gap-2"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Extracting Resume...
                  </>
                ) : (
                  "Upload & Parse Profile"
                )}
              </button>
            )}

            {error && (
              <div className="w-full p-4 rounded-xl border border-rose-500/20 bg-rose-500/10 text-rose-300 text-sm flex items-start gap-2 max-w-md">
                <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold">Extraction Failed</span>
                  <p className="text-xs text-rose-400 mt-1">{error}</p>
                </div>
              </div>
            )}
          </form>
          <div className="text-center">
            <button
              onClick={() => setIsManualEntry(true)}
              className="text-indigo-400 hover:text-indigo-350 text-sm font-semibold hover:underline transition duration-200"
            >
              Or fill in your details manually →
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

            setIntakeResult({
              user_id: "manual-" + Math.random().toString(36).substring(2, 9),
              parsed_resume: manualProfile,
              github_enriched: null
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
        <div className="p-6 md:p-8 rounded-3xl border border-slate-800 bg-slate-900/30 backdrop-blur-2xl space-y-8 animate-fade-in">
          {/* Header Card */}
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 pb-6 border-b border-slate-800">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                {tailorStep === "done" ? (
                  <Sparkles className="w-5 h-5 text-indigo-400" />
                ) : (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                )}
                <h2 className="text-2xl font-bold text-white">
                  {resume.name}
                  {tailorStep === "done" && (
                    <span className="ml-3 text-xs font-semibold text-indigo-400 border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                      Tailored (ATS: {atsScore}%)
                    </span>
                  )}
                </h2>
              </div>
              <p className="text-sm text-slate-400">{resume.email} {resume.phone ? `| ${resume.phone}` : ""}</p>
              <div className="flex flex-wrap gap-2 mt-2">
                {resume.links.map((link, idx) => (
                  <a
                    key={idx}
                    href={link.startsWith("http") ? link : `https://${link}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-indigo-400 hover:underline"
                  >
                    {link}
                  </a>
                ))}
              </div>
              {resume.anchor_line && (
                <div className="mt-3 text-sm font-medium italic text-indigo-300/90 border-l-2 border-indigo-500/60 pl-3 py-0.5">
                  &ldquo;{resume.anchor_line}&rdquo;
                </div>
              )}
            </div>

            {/* Document Render Controls */}
            <div className="flex gap-3">
              {tailorStep === "idle" && (
                <button
                  onClick={() => setTailorStep("input")}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition flex items-center gap-1.5"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Tailor for Job
                </button>
              )}
              {tailorStep === "done" && (
                <button
                  onClick={() => setTailorStep("input")}
                  className="px-4 py-2 rounded-xl text-xs font-semibold border border-indigo-500/30 text-indigo-400 hover:bg-indigo-500/10 transition flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Re-Tailor
                </button>
              )}
              <button
                onClick={() => handleDownload("pdf")}
                disabled={!!downloading}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/20 transition flex items-center gap-1.5 disabled:opacity-50"
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
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/20 transition flex items-center gap-1.5 disabled:opacity-50"
              >
                {downloading === "docx" ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <FileText className="w-3.5 h-3.5" />
                )}
                Download DOCX
              </button>
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
                className="px-4 py-2 rounded-xl text-xs font-semibold border border-slate-700 text-slate-400 hover:bg-slate-800 transition"
              >
                Reset
              </button>
            </div>
          </div>

          {/* Highlights strip callout */}
          {resume.highlights_strip && resume.highlights_strip.length > 0 && (
            <div className="p-5 rounded-2xl bg-indigo-500/5 border border-indigo-500/10 space-y-2 animate-fade-in">
              <h4 className="text-xs font-bold text-indigo-400 uppercase tracking-wider">Relevance & Highlights</h4>
              <ul className="grid md:grid-cols-2 gap-3 text-xs text-slate-300 pl-4 list-disc font-light">
                {resume.highlights_strip.map((hl: any, idx: number) => (
                  <li key={idx}>
                    <span className="font-semibold text-slate-200">{hl.skill}</span>: {hl.relevance_reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Navigation Tabs */}
          <div className="flex border-b border-slate-800 overflow-x-auto whitespace-nowrap">
            {(["experience", "projects", "education", "skills", "github", "jobs"] as const).map((tab) => {
              if (tab === "github" && !github) return null;
              return (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-4 py-2 border-b-2 text-sm font-semibold transition ${
                    activeTab === tab
                      ? "border-indigo-500 text-indigo-400"
                      : "border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              );
            })}
          </div>

          {/* Tab Content Panel */}
          <div className="py-4 min-h-[300px]">
            {/* Experience Panel */}
            {activeTab === "experience" && (
              <div className="space-y-6">
                {resume.experience.length === 0 ? (
                  <p className="text-slate-400 text-sm">No work experience listed (Fresher profile).</p>
                ) : (
                  resume.experience.map((exp, idx) => (
                    <div key={idx} className="space-y-2">
                      <div className="flex justify-between items-start">
                        <div>
                          <h4 className="text-base font-bold text-slate-200">{exp.role}</h4>
                          <span className="text-sm text-slate-400">{exp.company} {exp.location ? `· ${exp.location}` : ""}</span>
                        </div>
                        <span className="text-xs text-indigo-400 font-semibold bg-indigo-500/10 px-2.5 py-1 rounded-full">
                          {exp.start_date} &ndash; {exp.end_date || "Present"}
                        </span>
                      </div>
                      <ul className="list-disc pl-5 text-sm text-slate-300 space-y-1">
                        {exp.bullets.map((bullet: string, bIdx: number) => (
                          <li key={bIdx}>{bullet}</li>
                        ))}
                      </ul>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Projects Panel */}
            {activeTab === "projects" && (
              <div className="space-y-6">
                {resume.projects.length === 0 ? (
                  <p className="text-slate-400 text-sm">No personal projects listed.</p>
                ) : (
                  resume.projects.map((proj, idx) => (
                    <div key={idx} className="space-y-2">
                      <div className="flex justify-between items-center">
                        <h4 className="text-base font-bold text-slate-200">{proj.name}</h4>
                        {proj.link && (
                          <a
                            href={proj.link.startsWith("http") ? proj.link : `https://${proj.link}`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs text-indigo-400 hover:underline"
                          >
                            Project Link
                          </a>
                        )}
                      </div>
                      <ul className="list-disc pl-5 text-sm text-slate-300 space-y-1">
                        {proj.bullets.map((bullet: string, bIdx: number) => (
                          <li key={bIdx}>{bullet}</li>
                        ))}
                      </ul>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Education Panel */}
            {activeTab === "education" && (
              <div className="space-y-6">
                {resume.education.map((edu, idx) => (
                  <div key={idx} className="space-y-1">
                    <div className="flex justify-between items-start">
                      <h4 className="text-base font-bold text-slate-200">
                        {edu.degree} {edu.major ? `in ${edu.major}` : ""}
                      </h4>
                      <span className="text-xs text-indigo-400 font-semibold bg-indigo-500/10 px-2.5 py-1 rounded-full">
                        {edu.date}
                      </span>
                    </div>
                    <p className="text-sm text-slate-400">{edu.school}</p>
                    {edu.gpa && <span className="text-xs text-emerald-400 font-medium">GPA: {edu.gpa}</span>}
                  </div>
                ))}
              </div>
            )}

            {/* Skills Panel */}
            {activeTab === "skills" && (
              <div className="flex flex-wrap gap-2.5">
                {resume.skills.map((skill, idx) => (
                  <span
                    key={idx}
                    className="px-3.5 py-1.5 rounded-xl bg-slate-800 text-slate-300 text-xs border border-slate-700 font-medium"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            )}

            {/* GitHub Panel */}
            {activeTab === "github" && github && (
              <div className="space-y-6">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 flex flex-col justify-center">
                    <span className="text-xs text-slate-400">Total GitHub Stars</span>
                    <span className="text-2xl font-bold text-indigo-300 flex items-center gap-1.5 mt-1">
                      <Award className="w-5 h-5 text-yellow-500" />
                      {github.total_stars}
                    </span>
                  </div>
                  <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 flex flex-col justify-center">
                    <span className="text-xs text-slate-400">Enriched Username</span>
                    <span className="text-lg font-bold text-slate-200 mt-1 flex items-center gap-1.5">
                      <Github className="w-4 h-4 text-indigo-400" />
                      {github.username}
                    </span>
                  </div>
                </div>

                {/* Top Repositories */}
                <div className="space-y-3">
                  <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Top Repositories</h4>
                  {github.top_repositories.length === 0 ? (
                    <p className="text-slate-500 text-xs">No repositories found or public access rate-limited.</p>
                  ) : (
                    <div className="grid md:grid-cols-2 gap-4">
                      {github.top_repositories.map((repo, idx) => (
                        <div key={idx} className="p-4 rounded-2xl bg-slate-950/50 border border-slate-800 flex flex-col justify-between space-y-4 hover:border-slate-750 transition">
                          <div>
                            <div className="flex justify-between items-center">
                              <a
                                href={repo.url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-sm font-bold text-indigo-400 hover:underline"
                              >
                                {repo.name}
                              </a>
                              <span className="text-xs text-yellow-500 font-semibold bg-yellow-500/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                                ★ {repo.stars}
                              </span>
                            </div>
                            <p className="text-xs text-slate-400 mt-2 line-clamp-2">{repo.description || "No description provided."}</p>
                          </div>
                          {repo.language && (
                            <span className="text-xs text-slate-300 font-semibold bg-slate-800/80 w-max px-2.5 py-1 rounded-lg">
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
            {activeTab === "jobs" && (
              <JobSearch
                user_id={intakeResult.user_id}
                parsed_resume={resume}
                onSelectJobForTailoring={(jdText) => {
                  setSelectedJdText(jdText);
                  setTailorStep("input");
                }}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
