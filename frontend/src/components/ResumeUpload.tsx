"use client";

import React, { useState } from "react";
import { Upload, FileText, CheckCircle2, AlertCircle, Github, Download, Award, Loader2 } from "lucide-react";

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

  const [activeTab, setActiveTab] = useState<"experience" | "projects" | "education" | "skills" | "github">("experience");
  const [downloading, setDownloading] = useState<string | null>(null);

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
      const res = await fetch(`${backendUrl}/render?format=${format}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(intakeResult.parsed_resume),
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

  const resume = intakeResult?.parsed_resume;
  const github = intakeResult?.github_enriched;

  return (
    <div className="w-full max-w-4xl mx-auto space-y-8">
      {/* Upload Zone */}
      {!intakeResult && (
        <form onSubmit={handleUpload} className="p-8 border border-dashed border-slate-800 rounded-3xl bg-slate-900/20 backdrop-blur-xl flex flex-col items-center justify-center space-y-6 hover:border-indigo-500/40 transition duration-300">
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
      )}

      {/* Result Profile view */}
      {intakeResult && resume && (
        <div className="p-6 md:p-8 rounded-3xl border border-slate-800 bg-slate-900/30 backdrop-blur-2xl space-y-8">
          {/* Header Card */}
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 pb-6 border-b border-slate-800">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <h2 className="text-2xl font-bold text-white">{resume.name}</h2>
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
            </div>

            {/* Document Render Controls */}
            <div className="flex gap-3">
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
                }}
                className="px-4 py-2 rounded-xl text-xs font-semibold border border-slate-700 text-slate-400 hover:bg-slate-800 transition"
              >
                Reset
              </button>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex border-b border-slate-800 overflow-x-auto whitespace-nowrap">
            {(["experience", "projects", "education", "skills", "github"] as const).map((tab) => {
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
                        {exp.bullets.map((bullet, bIdx) => (
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
                        {proj.bullets.map((bullet, bIdx) => (
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
          </div>
        </div>
      )}
    </div>
  );
}
