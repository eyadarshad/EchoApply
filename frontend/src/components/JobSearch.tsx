"use client";

import React, { useState } from "react";
import { Search, MapPin, Briefcase, ChevronDown, ChevronUp, Loader2, AlertTriangle, Sparkles, CheckCircle, ExternalLink, Send } from "lucide-react";
import ApplyDrawer from "./ApplyDrawer";

interface JobCard {
  job_id: string;
  source: string;
  title: string;
  company: string;
  location?: string;
  remote: boolean;
  apply_url?: string;
  jd_text: string;
  fetched_at: string;
  job_hash: string;
  match_score?: number;
  match_explanation?: string;
  is_applied: boolean;
}

interface JobSearchProps {
  user_id: string;
  parsed_resume: any;
  onSelectJobForTailoring: (jdText: string) => void;
}

export default function JobSearch({ user_id, parsed_resume, onSelectJobForTailoring }: JobSearchProps) {
  const [query, setQuery] = useState("");
  const [location, setLocation] = useState("");
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [limit, setLimit] = useState(15);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobs, setJobs] = useState<JobCard[]>([]);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [searchTriggered, setSearchTriggered] = useState(false);
  const [activeApplyJob, setActiveApplyJob] = useState<JobCard | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setSearchTriggered(true);

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
      const res = await fetch(`${backendUrl}/jobs/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query.trim(),
          location: location.trim() || undefined,
          remote_only: remoteOnly,
          limit: limit,
          user_id: user_id
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to search jobs.");
      }

      const data = await res.json();
      setJobs(data.jobs || []);
    } catch (err: any) {
      setError(err.message);
      setJobs([]);
    } finally {
      setLoading(false);
    }
  };

  const getScoreBadgeColor = (score: number) => {
    if (score >= 0.8) return "bg-emerald-500/10 border-emerald-500/30 text-emerald-400";
    if (score >= 0.5) return "bg-amber-500/10 border-amber-500/30 text-amber-400";
    return "bg-slate-800 border-slate-700 text-slate-400";
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Search Input Card */}
      <form onSubmit={handleSearch} className="p-6 rounded-3xl border border-slate-800 bg-slate-900/10 backdrop-blur-xl space-y-4">
        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Keywords / Role</label>
            <div className="relative flex items-center">
              <Search className="w-4 h-4 text-slate-500 absolute left-3.5" />
              <input
                type="text"
                required
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Python Developer, React Frontend..."
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-800 bg-slate-950/80 text-sm focus:border-indigo-500 focus:outline-none transition text-slate-200"
              />
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Location (Optional)</label>
            <div className="relative flex items-center">
              <MapPin className="w-4 h-4 text-slate-500 absolute left-3.5" />
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Karachi, Lahore, Pakistan..."
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-800 bg-slate-950/80 text-sm focus:border-indigo-500 focus:outline-none transition text-slate-200"
              />
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-slate-850">
          <label className="inline-flex items-center gap-2.5 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={remoteOnly}
              onChange={(e) => setRemoteOnly(e.target.checked)}
              className="w-4 h-4 rounded border-slate-800 bg-slate-950 text-indigo-600 focus:ring-indigo-500/20"
            />
            <span className="text-xs text-slate-400 font-medium">Remote Roles Only</span>
          </label>

          <div className="flex items-center gap-3">
            <label className="text-xs text-slate-500 flex items-center gap-2">
              Limit results:
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="bg-slate-950 border border-slate-800 text-slate-300 rounded-lg text-xs py-1 px-2 focus:outline-none"
              >
                <option value={5}>5</option>
                <option value={15}>15</option>
                <option value={30}>30</option>
                <option value={50}>50</option>
              </select>
            </label>

            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="px-6 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-semibold text-xs transition flex items-center gap-2 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Searching...
                </>
              ) : (
                <>
                  <Briefcase className="w-3.5 h-3.5" />
                  Find Jobs
                </>
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Error Indicator */}
      {error && (
        <div className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/10 text-amber-300 text-xs flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">Listing Search Completed with Warnings</span>
            <p className="text-amber-400/80 mt-0.5">{error}. Serving local fallback listings.</p>
          </div>
        </div>
      )}

      {/* Jobs Search Results list */}
      {searchTriggered && !loading && (
        <div className="space-y-4">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Matching Listings ({jobs.length})</h3>
          
          {jobs.length === 0 ? (
            <div className="p-8 border border-slate-850 rounded-3xl bg-slate-900/5 text-center space-y-2">
              <p className="text-slate-400 text-sm font-light">No jobs match your search criteria.</p>
              <p className="text-xs text-slate-500">Try broadening your search (e.g. remove location restrictions or disable remote-only).</p>
            </div>
          ) : (
            <div className="space-y-4">
              {jobs.map((job) => {
                const isExpanded = expandedJobId === job.job_id;
                const matchPct = Math.round((job.match_score || 0) * 100);
                
                return (
                  <div key={job.job_id} className="border border-slate-850 rounded-2xl bg-slate-900/10 backdrop-blur-xl overflow-hidden hover:border-slate-800 transition">
                    <div className="p-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`text-[10px] font-bold border px-2.5 py-0.5 rounded-full uppercase tracking-wider ${getScoreBadgeColor(job.match_score || 0)}`}>
                            {matchPct}% Match
                          </span>
                          <span className="text-[10px] font-semibold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-lg border border-indigo-500/20">
                            {job.source}
                          </span>
                          {job.is_applied && (
                            <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-lg border border-emerald-500/20 flex items-center gap-1">
                              <CheckCircle className="w-3 h-3" /> Applied
                            </span>
                          )}
                        </div>
                        <h4 className="text-base font-bold text-slate-200 mt-1">{job.title}</h4>
                        <p className="text-xs text-slate-400 font-light">{job.company} · {job.location}</p>
                      </div>

                      <div className="flex items-center gap-2 w-full md:w-auto justify-end">
                        <button
                          onClick={() => onSelectJobForTailoring(job.jd_text)}
                          className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white transition flex items-center gap-1.5"
                        >
                          <Sparkles className="w-3.5 h-3.5" />
                          Tailor Resume
                        </button>
                        <button
                          onClick={() => setActiveApplyJob(job)}
                          className={`px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 ${
                            job.is_applied
                              ? "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200 border border-slate-700/50"
                              : "bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white shadow-lg shadow-emerald-600/10"
                          }`}
                        >
                          <Send className="w-3.5 h-3.5" />
                          {job.is_applied ? "Re-apply" : "Apply Now"}
                        </button>
                        {job.apply_url && (
                          <a
                            href={job.apply_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-2 rounded-xl border border-slate-800 hover:bg-slate-800 text-slate-300 hover:text-white transition"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                        <button
                          onClick={() => setExpandedJobId(isExpanded ? null : job.job_id)}
                          className="p-2 rounded-xl border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
                        >
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>

                    {/* Expanded Detail Panel */}
                    {isExpanded && (
                      <div className="px-5 pb-5 border-t border-slate-850/40 bg-slate-950/20 space-y-4 pt-4 animate-slide-down">
                        {job.match_explanation && (
                          <div className="p-3.5 rounded-xl bg-indigo-500/5 border border-indigo-500/10 text-xs">
                            <span className="font-bold text-indigo-400 uppercase tracking-wider block mb-1">Matching Rationale</span>
                            <p className="text-slate-300 font-light leading-relaxed">{job.match_explanation}</p>
                          </div>
                        )}
                        <div className="space-y-1">
                          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Job Description</span>
                          <p className="text-xs text-slate-300 font-light leading-relaxed line-clamp-[12] whitespace-pre-wrap">
                            {job.jd_text}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {activeApplyJob && (
        <ApplyDrawer
          userId={user_id}
          jobId={activeApplyJob.job_id}
          jobTitle={activeApplyJob.title}
          jobCompany={activeApplyJob.company}
          onClose={() => setActiveApplyJob(null)}
          onSuccess={() => {
            setJobs(prevJobs =>
              prevJobs.map(j =>
                j.job_id === activeApplyJob.job_id ? { ...j, is_applied: true } : j
              )
            );
          }}
        />
      )}
    </div>
  );
}
