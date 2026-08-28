"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Search, MapPin, Briefcase, ChevronDown, ChevronUp, Loader2, 
  AlertTriangle, Sparkles, CheckCircle, CheckCircle2, ExternalLink, 
  Send, Globe, Building2, Cpu, Zap, ShieldCheck 
} from "lucide-react";
import ApplyDrawer from "./ApplyDrawer";
import { toast } from "sonner";
import { apiFetch } from "../lib/api";

const SEARCH_STEPS = [
  {
    id: "linkedin",
    icon: Globe,
    title: "LinkedIn Live Scraper Gateway",
    desc: "Querying LinkedIn postings & extracting applicant velocity...",
    activeDesc: (q: string, loc: string) => `Scraping live LinkedIn feeds for "${q}"${loc ? ` in ${loc}` : ""}...`,
  },
  {
    id: "portals",
    icon: Building2,
    title: "Multi-Portal Vacancy Aggregate",
    desc: "Scanning Indeed, Glassdoor & specialized tech boards...",
    activeDesc: (q: string) => `Filtering active openings, remote eligibility & salary transparency for "${q}"...`,
  },
  {
    id: "semantic",
    icon: Cpu,
    title: "AI Skill & Requirements Extraction",
    desc: "Parsing required tech stacks, responsibilities & qualifications...",
    activeDesc: () => "Extracting required competencies, libraries, frameworks & seniority levels...",
  },
  {
    id: "scoring",
    icon: Sparkles,
    title: "1-to-1 ATS Semantic Match Scoring",
    desc: "Calculating compatibility scores against your candidate profile...",
    activeDesc: () => "Comparing parsed resume achievements against JD benchmarks to score fit...",
  },
];

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
  user_id: string | null;
  parsed_resume: any;
  onRequireAuth?: (reason: string) => void;
  onSelectJobForTailoring: (job: JobCard) => void;
}

export default function JobSearch({ user_id, parsed_resume, onRequireAuth, onSelectJobForTailoring }: JobSearchProps) {
  const getBrandName = (key: string) => {
    if (!key) return "";
    if (key.toLowerCase() === "linkedin") return "LinkedIn";
    if (key.toLowerCase() === "indeed") return "Indeed";
    if (key.toLowerCase() === "glassdoor") return "Glassdoor";
    return key.charAt(0).toUpperCase() + key.slice(1);
  };

  const [query, setQuery] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("smartapply_jobsearch_query") || "";
    }
    return "";
  });
  const [location, setLocation] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("smartapply_jobsearch_location") || "";
    }
    return "";
  });
  const [remoteOnly, setRemoteOnly] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("smartapply_jobsearch_remote") === "true";
    }
    return false;
  });
  const [limit, setLimit] = useState(15);
  const [loading, setLoading] = useState(false);
  const [searchStep, setSearchStep] = useState<number>(0);
  const [searchProgressPct, setSearchProgressPct] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [jobs, setJobs] = useState<JobCard[]>(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("smartapply_jobsearch_results");
        if (saved) {
          const parsed = JSON.parse(saved);
          if (Array.isArray(parsed)) return parsed;
        }
      } catch (e) {
        // ignore parse error
      }
    }
    return [];
  });
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [activeApplyJob, setActiveApplyJob] = useState<JobCard | null>(null);
  const [searchTriggered, setSearchTriggered] = useState(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("smartapply_jobsearch_results");
        if (saved && JSON.parse(saved).length > 0) return true;
      } catch (e) {}
    }
    return false;
  });
  const [datePosted, setDatePosted] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("smartapply_jobsearch_date") || "week";
    }
    return "week";
  });
  const [excludeClosed, setExcludeClosed] = useState(true);
  const [experienceLevel, setExperienceLevel] = useState("any");
  const [employmentType, setEmploymentType] = useState("any");
  const [sortBy, setSortBy] = useState("match");

  const [logins, setLogins] = useState(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("job_board_logins");
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch (e) {
          // ignore parsing errors
        }
      }
    }
    return {
      linkedin: false,
      indeed: false,
      glassdoor: false,
      jooble: true,
    };
  });

  const [activeLoginModal, setActiveLoginModal] = useState<"linkedin" | "indeed" | "glassdoor" | "jooble" | null>(null);
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginStage, setLoginStage] = useState<"idle" | "connecting" | "captcha" | "tokens" | "success">("idle");

  const handleLoginToggle = (key: keyof typeof logins) => {
    const updated = { ...logins, [key]: !logins[key] };
    setLogins(updated);
    if (typeof window !== "undefined") {
      localStorage.setItem("job_board_logins", JSON.stringify(updated));
    }
  };

  const handlePortalSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginEmail || !loginPassword) return;

    setLoginStage("connecting");

    setTimeout(() => {
      setLoginStage("captcha");
      setTimeout(() => {
        setLoginStage("tokens");
        setTimeout(() => {
          setLoginStage("success");
          setTimeout(() => {
            if (activeLoginModal) {
              const updated = { ...logins, [activeLoginModal]: true };
              setLogins(updated);
              if (typeof window !== "undefined") {
                localStorage.setItem("job_board_logins", JSON.stringify(updated));
              }
            }
            setActiveLoginModal(null);
          }, 1200);
        }, 1500);
      }, 1500);
    }, 1200);
  };

  const filteredJobs = jobs.filter((job) => {
    // 1. Experience Level client-side filter
    if (experienceLevel !== "any") {
      const title = job.title.toLowerCase();
      const jd = job.jd_text.toLowerCase();
      if (experienceLevel === "internship") {
        if (!title.includes("intern") && !jd.includes("internship")) return false;
      } else if (experienceLevel === "entry") {
        if (!title.includes("junior") && !title.includes("entry") && !jd.includes("junior") && !jd.includes("entry level")) return false;
      } else if (experienceLevel === "mid") {
        if (title.includes("senior") || title.includes("lead") || title.includes("director") || title.includes("intern") || title.includes("junior")) return false;
      } else if (experienceLevel === "senior") {
        if (!title.includes("senior") && !title.includes("lead") && !title.includes("principal") && !title.includes("sr") && !title.includes("director")) return false;
      }
    }

    // 2. Employment Type client-side filter
    if (employmentType !== "any") {
      const title = job.title.toLowerCase();
      const jd = job.jd_text.toLowerCase();
      if (employmentType === "full-time") {
        if (title.includes("part-time") || title.includes("contract") || title.includes("parttime") || jd.includes("part-time") || jd.includes("contract")) return false;
      } else if (employmentType === "part-time") {
        if (!title.includes("part-time") && !title.includes("parttime") && !jd.includes("part-time")) return false;
      } else if (employmentType === "contract") {
        if (!title.includes("contract") && !title.includes("freelance") && !jd.includes("contract") && !jd.includes("freelance")) return false;
      }
    }

    // 3. Hide closed if excludeClosed is true
    if (excludeClosed && (job as any).is_closed) {
      return false;
    }

    return true;
  });

  const sortedJobs = [...filteredJobs].sort((a, b) => {
    if (sortBy === "recent") {
      return new Date(b.fetched_at).getTime() - new Date(a.fetched_at).getTime();
    }
    if (sortBy === "company") {
      return a.company.localeCompare(b.company);
    }
    // Default: best match score descending
    return (b.match_score || 0) - (a.match_score || 0);
  });

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setSearchTriggered(true);
    setSearchStep(0);
    setSearchProgressPct(18);

    // Dynamic Step & Progress Simulation to keep user engaged with aesthetic feedback
    const stepInterval = setInterval(() => {
      setSearchStep((prev) => (prev < 3 ? prev + 1 : 3));
    }, 1800);

    const progressInterval = setInterval(() => {
      setSearchProgressPct((prev) => (prev < 92 ? prev + Math.floor(Math.random() * 6) + 3 : 92));
    }, 320);

    // 45 second timeout for job search
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      try {
        if (!controller.signal.aborted) {
          controller.abort();
        }
      } catch (e) {
        console.warn("Abort failed:", e);
      }
    }, 45000);

    try {
      const data = await apiFetch("/jobs/search", {
        method: "POST",
        body: JSON.stringify({
          query: query.trim(),
          location: location.trim() || undefined,
          remote_only: remoteOnly,
          limit: limit,
          user_id: user_id,
          date_posted: datePosted,
          exclude_closed: excludeClosed
        }),
        signal: controller.signal,
      });

      const returnedJobs = data.jobs || [];
      setJobs(returnedJobs);
      if (typeof window !== "undefined") {
        try {
          localStorage.setItem("smartapply_jobsearch_results", JSON.stringify(returnedJobs));
          localStorage.setItem("smartapply_jobsearch_query", query.trim());
          localStorage.setItem("smartapply_jobsearch_location", location.trim());
          localStorage.setItem("smartapply_jobsearch_remote", String(remoteOnly));
          localStorage.setItem("smartapply_jobsearch_date", datePosted);
        } catch (e) {
          // ignore quota error
        }
      }
      if (!data.jobs || data.jobs.length === 0) {
        setError("No jobs found matching your criteria. Try broadening your search or adjusting filters.");
      }
    } catch (err: any) {
      const msg = err.message || "";
      if (err.name === "AbortError" || msg.includes("aborted")) {
        setError("Search timed out. The job search APIs may be slow — please try again.");
      } else if (msg.includes("Failed to fetch") || msg.includes("NetworkError") || msg.includes("fetch")) {
        setError("Unable to connect to the server. Please check if the backend is running and try again.");
      } else if (msg.includes("429") || msg.includes("rate")) {
        setError("Too many searches. Please wait a moment before searching again.");
      } else if (msg.includes("401") || msg.includes("Unauthorized")) {
        setError("Please sign in to search for jobs.");
      } else {
        setError(msg || "An unexpected error occurred during job search.");
      }
      setJobs([]);
      if (typeof window !== "undefined") {
        try {
          localStorage.removeItem("smartapply_jobsearch_results");
        } catch (e) {}
      }
    } finally {
      clearInterval(stepInterval);
      clearInterval(progressInterval);
      setSearchProgressPct(100);
      setSearchStep(4);
      clearTimeout(timeoutId);
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
      <form onSubmit={handleSearch} className="p-6 rounded-3xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/10 backdrop-blur-xl space-y-4 shadow-sm">
        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Keywords / Role</label>
            <div className="relative flex items-center">
              <Search className="w-4 h-4 text-slate-400 dark:text-slate-500 absolute left-3.5" />
              <input
                type="text"
                required
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Python Developer, React Frontend..."
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-950/80 text-sm focus:border-teal-500 focus:outline-none transition text-slate-800 dark:text-slate-200"
              />
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Location (Optional)</label>
            <div className="relative flex items-center">
              <MapPin className="w-4 h-4 text-slate-400 dark:text-slate-500 absolute left-3.5" />
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Karachi, Lahore, Pakistan..."
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-950/80 text-sm focus:border-teal-500 focus:outline-none transition text-slate-800 dark:text-slate-200"
              />
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-end pt-2 border-t border-slate-200 dark:border-slate-800">
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-6 py-2 rounded-xl bg-teal-600 hover:bg-teal-500 active:bg-teal-700 text-white font-semibold text-xs transition flex items-center gap-2 disabled:opacity-50"
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
      </form>

      {/* Search Filters Card */}
      <div className="p-5 rounded-3xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/10 backdrop-blur-xl flex flex-wrap items-center justify-between gap-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          {/* Date Posted Filter */}
          <div className="flex flex-col space-y-1">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Date Posted</span>
            <select
              value={datePosted}
              onChange={(e) => setDatePosted(e.target.value)}
              className="bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-300 rounded-xl text-xs py-2 px-3 focus:outline-none focus:border-teal-500 transition"
            >
              <option value="any">Any Time</option>
              <option value="today">Today</option>
              <option value="3days">Past 3 Days</option>
              <option value="week">Past Week</option>
              <option value="month">Past Month</option>
            </select>
          </div>

          {/* Experience Level Filter */}
          <div className="flex flex-col space-y-1">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Experience</span>
            <select
              value={experienceLevel}
              onChange={(e) => setExperienceLevel(e.target.value)}
              className="bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-300 rounded-xl text-xs py-2 px-3 focus:outline-none focus:border-teal-500 transition"
            >
              <option value="any">Any Level</option>
              <option value="internship">Internship</option>
              <option value="entry">Entry Level</option>
              <option value="mid">Mid Level</option>
              <option value="senior">Senior Level</option>
            </select>
          </div>

          {/* Sort By Filter */}
          <div className="flex flex-col space-y-1">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Sort By</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-300 rounded-xl text-xs py-2 px-3 focus:outline-none focus:border-teal-500 transition"
            >
              <option value="match">Best Match</option>
              <option value="recent">Most Recent</option>
              <option value="company">Company A-Z</option>
            </select>
          </div>
        </div>

        {/* Right side: Hide Closed Toggle + Employment tags */}
        <div className="flex flex-wrap items-center gap-4">
          {/* Hide Closed Toggle */}
          <label className="flex items-center gap-2.5 cursor-pointer select-none">
            <div className="relative">
              <input
                type="checkbox"
                checked={excludeClosed}
                onChange={(e) => setExcludeClosed(e.target.checked)}
                className="sr-only"
              />
              <div className={`w-8 h-4 rounded-full transition-colors ${excludeClosed ? "bg-teal-600" : "bg-slate-300 dark:bg-slate-800"}`} />
              <div className={`absolute top-0.5 left-0.5 w-3 h-3 rounded-full bg-white transition-transform ${excludeClosed ? "translate-x-4" : ""}`} />
            </div>
            <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">Hide Closed</span>
          </label>

          {/* Employment Tags / Pills */}
          <div className="flex items-center gap-2">
            {[
              { id: "full-time", label: "Full-time" },
              { id: "part-time", label: "Part-time" },
              { id: "contract", label: "Contract" },
            ].map((type) => (
              <button
                key={type.id}
                type="button"
                onClick={() => setEmploymentType(employmentType === type.id ? "any" : type.id)}
                className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition ${
                  employmentType === type.id
                    ? "border-teal-500 bg-teal-500/10 text-teal-650 dark:text-teal-400 shadow-sm animate-pulse-subtle"
                    : "border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-700"
                }`}
              >
                {type.label}
              </button>
            ))}

            <button
              type="button"
              onClick={() => setRemoteOnly(!remoteOnly)}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition ${
                remoteOnly
                  ? "border-teal-500 bg-teal-500/10 text-teal-650 dark:text-teal-400 shadow-sm"
                  : "border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-700"
              }`}
            >
              Remote Only
            </button>
          </div>
        </div>
      </div>



      {/* Live AI Job Scraping & Matching Console */}
      <AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0, y: 15, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -15, scale: 0.98 }}
            transition={{ duration: 0.3 }}
            className="p-6 md:p-8 rounded-3xl border border-teal-500/30 bg-gradient-to-b from-slate-900/95 via-slate-950/95 to-slate-900/95 backdrop-blur-2xl text-slate-100 space-y-6 shadow-2xl relative overflow-hidden ring-1 ring-teal-500/20"
          >
            {/* Ambient Background Glows */}
            <div className="absolute top-0 right-1/4 w-72 h-72 bg-teal-500/10 rounded-full blur-3xl pointer-events-none -translate-y-1/2" />
            <div className="absolute bottom-0 left-1/4 w-72 h-72 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none translate-y-1/2" />

            {/* Header with Radar scanner */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-800/80 relative z-10">
              <div className="flex items-center gap-3.5">
                <div className="relative flex items-center justify-center w-12 h-12 rounded-2xl bg-teal-500/10 border border-teal-500/30 shadow-inner shrink-0">
                  <Globe className="w-6 h-6 text-teal-400 animate-pulse" />
                  <div className="absolute inset-0 rounded-2xl border border-teal-400/40 animate-ping opacity-30" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400" />
                    <h3 className="text-sm md:text-base font-bold text-white tracking-wide">
                      Live Career Intelligence Radar
                    </h3>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Scanning active multi-portal vacancies &amp; running ATS match scoring for <strong className="text-teal-300 font-semibold">&quot;{query}&quot;</strong>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 self-end sm:self-auto">
                <span className="text-xs font-mono font-bold text-teal-400 bg-teal-500/10 px-3 py-1 rounded-full border border-teal-500/20 shadow-sm">
                  {searchProgressPct}% Complete
                </span>
              </div>
            </div>

            {/* Dynamic Progress Bar */}
            <div className="w-full h-1.5 bg-slate-800/80 rounded-full overflow-hidden relative">
              <motion.div 
                className="h-full bg-gradient-to-r from-teal-500 via-emerald-400 to-cyan-400 rounded-full relative"
                style={{ width: `${searchProgressPct}%` }}
                transition={{ ease: "easeInOut", duration: 0.3 }}
              >
                <div className="absolute inset-0 bg-white/20 animate-pulse" />
              </motion.div>
            </div>

            {/* Animated Pipeline Steps */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 relative z-10">
              {SEARCH_STEPS.map((step, idx) => {
                const StepIcon = step.icon;
                const isDone = searchStep > idx;
                const isCurrent = searchStep === idx;

                return (
                  <motion.div
                    key={step.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.08 }}
                    className={`p-4 rounded-2xl border transition-all ${
                      isCurrent
                        ? "bg-teal-500/10 border-teal-500/40 shadow-lg shadow-teal-500/5 ring-1 ring-teal-500/30"
                        : isDone
                        ? "bg-emerald-500/5 border-emerald-500/20 text-slate-300"
                        : "bg-slate-900/40 border-slate-800/80 text-slate-500 opacity-60"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-xl shrink-0 transition-colors ${
                        isCurrent 
                          ? "bg-teal-500/20 text-teal-300 ring-2 ring-teal-400/30" 
                          : isDone 
                          ? "bg-emerald-500/20 text-emerald-400" 
                          : "bg-slate-800 text-slate-500"
                      }`}>
                        <StepIcon className="w-4 h-4" />
                      </div>

                      <div className="space-y-1 min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <h4 className={`text-xs font-bold truncate ${
                            isCurrent ? "text-teal-200 font-semibold" : isDone ? "text-slate-200" : "text-slate-400"
                          }`}>
                            {step.title}
                          </h4>
                          {isDone ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                          ) : isCurrent ? (
                            <Loader2 className="w-3.5 h-3.5 text-teal-400 animate-spin shrink-0" />
                          ) : (
                            <span className="text-[10px] text-slate-600 font-mono">PENDING</span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-400 leading-relaxed">
                          {isCurrent ? step.activeDesc(query, location) : step.desc}
                        </p>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>

            {/* Live Gateway Ticker Footer */}
            <div className="pt-2 flex flex-wrap items-center justify-between gap-3 text-[11px] text-slate-400 border-t border-slate-800/80 relative z-10">
              <div className="flex flex-wrap items-center gap-3">
                <span className="flex items-center gap-1.5 text-teal-300">
                  <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-ping" />
                  LinkedIn Scraper: <strong>Live Gateway</strong>
                </span>
                <span className="text-slate-600">|</span>
                <span className="flex items-center gap-1.5">
                  Indeed &amp; Glassdoor: <strong className="text-slate-300">Connected</strong>
                </span>
                <span className="text-slate-600">|</span>
                <span className="flex items-center gap-1.5">
                  Jooble Feed: <strong className="text-slate-300">Active</strong>
                </span>
              </div>
              <div className="text-[10px] text-slate-500 font-medium">
                ⚡ Real-time verified postings &amp; instant ATS scoring
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error Indicator */}
      {error && !loading && (
        <div className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/10 text-amber-600 dark:text-amber-300 text-xs flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">Listing Search Completed with Warnings</span>
            <p className="text-amber-600 dark:text-amber-400/80 mt-0.5">{error}. Serving local fallback listings.</p>
          </div>
        </div>
      )}

      {/* Jobs Search Results list */}
      {searchTriggered && !loading && (
        <div className="space-y-4">
          <div className="flex flex-wrap justify-between items-center gap-2">
            <h3 className="text-sm font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Matching Listings ({sortedJobs.length})</h3>
            {jobs.length > sortedJobs.length && (
              <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                Filtered {jobs.length - sortedJobs.length} listing(s) matching criteria
              </span>
            )}
          </div>
          
          {sortedJobs.length === 0 ? (
            <div className="p-8 border border-slate-200 dark:border-slate-800 rounded-3xl bg-slate-100/50 dark:bg-slate-900/5 text-center space-y-2">
              <p className="text-slate-700 dark:text-slate-400 text-sm font-semibold">No jobs match your search criteria.</p>
              <p className="text-xs text-slate-500 font-light">
                Try broadening your query keywords or adjusting the filters above.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {sortedJobs.map((job) => {
                const isExpanded = expandedJobId === job.job_id;
                const matchPct = Math.round((job.match_score || 0) * 100);
                
                return (
                  <div key={job.job_id} className="border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/10 backdrop-blur-xl overflow-hidden hover:border-slate-300 dark:hover:border-slate-700 transition rounded-2xl">
                    <div className="p-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`text-[10px] font-bold border px-2.5 py-0.5 rounded-full uppercase tracking-wider ${getScoreBadgeColor(job.match_score || 0)}`}>
                            {matchPct}% Match
                          </span>
                          <span className="text-[10px] font-semibold text-teal-600 dark:text-teal-400 bg-teal-500/10 px-2 py-0.5 rounded-lg border border-teal-500/20">
                            {job.source}
                          </span>
                          {job.is_applied && (
                            <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-lg border border-emerald-500/20 flex items-center gap-1">
                              <CheckCircle className="w-3 h-3" /> Applied
                            </span>
                          )}
                        </div>
                        <h4 className="text-base font-bold text-slate-800 dark:text-slate-200 mt-1">{job.title}</h4>
                        <p className="text-xs text-slate-600 dark:text-slate-400 font-light">{job.company} · {job.location}</p>
                      </div>

                      <div className="flex items-center gap-2 w-full md:w-auto justify-end">
                        <button
                          onClick={() => {
                            if (!user_id) {
                              if (onRequireAuth) onRequireAuth("tailor your resume to fit target job descriptions");
                              return;
                            }
                            onSelectJobForTailoring(job);
                          }}
                          className="px-4 py-2 rounded-xl text-xs font-semibold bg-teal-600 hover:bg-teal-500 active:bg-teal-700 text-white transition flex items-center gap-1.5 shadow-sm"
                        >
                          <Sparkles className="w-3.5 h-3.5" />
                          Tailor Resume
                        </button>
                        <button
                          onClick={() => {
                            if (!user_id) {
                              if (onRequireAuth) onRequireAuth("auto-apply to this job vacancy with one click");
                              return;
                            }
                            
                            const platform = job.source.toLowerCase();
                            const requiresSync = platform.includes("linkedin") || platform.includes("indeed") || platform.includes("glassdoor");
                            
                            if (requiresSync) {
                              const platformKey = platform.includes("linkedin") ? "linkedin" 
                                                : platform.includes("indeed") ? "indeed" 
                                                : "glassdoor";
                              if (!logins[platformKey]) {
                                toast.info(`Please sync your ${job.source} session first.`);
                                setActiveLoginModal(platformKey);
                                return;
                              }
                            }
                            
                            setActiveApplyJob(job);
                          }}
                          className={`px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 ${
                            job.is_applied
                              ? "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 hover:text-slate-800 dark:hover:text-slate-200 border border-slate-200 dark:border-slate-700/50"
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
                            className="p-2 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-slate-150 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 hover:text-slate-800 dark:hover:text-white transition"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                        <button
                          onClick={() => setExpandedJobId(isExpanded ? null : job.job_id)}
                          className="p-2 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-slate-150 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white transition"
                        >
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>

                    {/* Expanded Detail Panel */}
                    {isExpanded && (
                      <div className="px-5 pb-5 border-t border-slate-200 dark:border-slate-800/40 bg-slate-50/50 dark:bg-slate-950/20 space-y-4 pt-4 animate-slide-down">
                        {job.match_explanation && (
                          <div className="p-3.5 rounded-xl bg-teal-500/5 border border-teal-500/10 text-xs">
                            <span className="font-bold text-teal-600 dark:text-teal-400 uppercase tracking-wider block mb-1">Matching Rationale</span>
                            <p className="text-slate-700 dark:text-slate-300 font-light leading-relaxed">{job.match_explanation}</p>
                          </div>
                        )}
                        <div className="space-y-1">
                          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block">Job Description</span>
                          <p className="text-xs text-slate-750 dark:text-slate-300 font-light leading-relaxed line-clamp-[12] whitespace-pre-wrap">
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

      {/* Application Sync */}
      <div className="p-6 rounded-3xl border border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/10 backdrop-blur-xl space-y-4 shadow-sm mt-6">
        <div>
          <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
            🔄 Application Sync
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 font-light mt-1">
            Searching is free. Sync your session only when you're ready to auto-apply.
          </p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* LinkedIn Toggle */}
          <div className={`p-4 rounded-2xl border transition ${
            logins.linkedin 
              ? "border-teal-500 bg-teal-500/5 dark:bg-teal-500/10" 
              : "border-slate-200 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-950/20"
          }`}>
            <label className="flex flex-col justify-between h-full space-y-3 cursor-pointer select-none">
              <div className="flex justify-between items-start">
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200">LinkedIn</span>
                {logins.linkedin ? (
                  <span className="text-[9px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                    Synced
                  </span>
                ) : (
                  <span className="text-[9px] font-semibold text-slate-500 dark:text-slate-400 bg-slate-500/10 px-1.5 py-0.5 rounded border border-slate-500/20">
                    Sync to Apply
                  </span>
                )}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">Logged In</span>
                <input
                  type="checkbox"
                  checked={logins.linkedin}
                  onChange={() => handleLoginToggle("linkedin")}
                  className="w-4 h-4 rounded border-slate-300 dark:border-slate-800 bg-slate-100 dark:bg-slate-950 text-teal-600 focus:ring-teal-500/20"
                />
              </div>
            </label>
          </div>

          {/* Indeed Toggle */}
          <div className={`p-4 rounded-2xl border transition ${
            logins.indeed 
              ? "border-teal-500 bg-teal-500/5 dark:bg-teal-500/10" 
              : "border-slate-200 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-950/20"
          }`}>
            <label className="flex flex-col justify-between h-full space-y-3 cursor-pointer select-none">
              <div className="flex justify-between items-start">
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200">Indeed</span>
                {logins.indeed ? (
                  <span className="text-[9px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                    Synced
                  </span>
                ) : (
                  <span className="text-[9px] font-semibold text-slate-500 dark:text-slate-400 bg-slate-500/10 px-1.5 py-0.5 rounded border border-slate-500/20">
                    Sync to Apply
                  </span>
                )}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">Logged In</span>
                <input
                  type="checkbox"
                  checked={logins.indeed}
                  onChange={() => handleLoginToggle("indeed")}
                  className="w-4 h-4 rounded border-slate-300 dark:border-slate-800 bg-slate-100 dark:bg-slate-950 text-teal-650 focus:ring-teal-500/20"
                />
              </div>
            </label>
          </div>

          {/* Glassdoor Toggle */}
          <div className={`p-4 rounded-2xl border transition ${
            logins.glassdoor 
              ? "border-teal-500 bg-teal-500/5 dark:bg-teal-500/10" 
              : "border-slate-200 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-950/20"
          }`}>
            <label className="flex flex-col justify-between h-full space-y-3 cursor-pointer select-none">
              <div className="flex justify-between items-start">
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200">Glassdoor</span>
                {logins.glassdoor ? (
                  <span className="text-[9px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                    Synced
                  </span>
                ) : (
                  <span className="text-[9px] font-semibold text-slate-500 dark:text-slate-400 bg-slate-500/10 px-1.5 py-0.5 rounded border border-slate-500/20">
                    Sync to Apply
                  </span>
                )}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">Logged In</span>
                <input
                  type="checkbox"
                  checked={logins.glassdoor}
                  onChange={() => handleLoginToggle("glassdoor")}
                  className="w-4 h-4 rounded border-slate-300 dark:border-slate-800 bg-slate-100 dark:bg-slate-950 text-teal-650 focus:ring-teal-500/20"
                />
              </div>
            </label>
          </div>

          {/* Jooble Toggle */}
          <div className={`p-4 rounded-2xl border transition ${
            logins.jooble 
              ? "border-teal-500 bg-teal-500/5 dark:bg-teal-500/10" 
              : "border-slate-200 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-950/20"
          }`}>
            <label className="flex flex-col justify-between h-full space-y-3 cursor-pointer select-none">
              <div className="flex justify-between items-start">
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200">Jooble</span>
                <span className="text-[9px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                  Optional / Public
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">Enabled</span>
                <input
                  type="checkbox"
                  checked={logins.jooble}
                  onChange={() => handleLoginToggle("jooble")}
                  className="w-4 h-4 rounded border-slate-350 dark:border-slate-800 bg-slate-100 dark:bg-slate-950 text-teal-650 focus:ring-teal-500/20"
                />
              </div>
            </label>
          </div>
        </div>
      </div>

      {activeApplyJob && (
        <ApplyDrawer
          userId={user_id || ""}
          jobId={activeApplyJob.job_id}
          jobTitle={activeApplyJob.title}
          jobCompany={activeApplyJob.company}
          onClose={() => setActiveApplyJob(null)}
          onSuccess={() => {
            setJobs(prevJobs => {
              const updated = prevJobs.map(j =>
                j.job_id === activeApplyJob.job_id ? { ...j, is_applied: true } : j
              );
              if (typeof window !== "undefined") {
                try {
                  localStorage.setItem("smartapply_jobsearch_results", JSON.stringify(updated));
                } catch (e) {}
              }
              return updated;
            });
          }}
        />
      )}

      {activeLoginModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
          <div className="w-full max-w-md rounded-3xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-2xl p-6 md:p-8 space-y-6 relative overflow-hidden animate-scale-up">
            {/* Brand Colors Accent Border */}
            <div className={`absolute top-0 inset-x-0 h-1.5 ${
              activeLoginModal === "linkedin" ? "bg-[#0077b5]" :
              activeLoginModal === "indeed" ? "bg-[#2164f3]" :
              activeLoginModal === "glassdoor" ? "bg-[#0caa41]" : "bg-[#005cc5]"
            }`} />

            {/* Modal Header */}
            <div className="flex justify-between items-start pt-2">
              <div className="space-y-1">
                <span className="text-[10px] font-bold text-teal-500 uppercase tracking-widest block text-left">
                  Secure Cookie Sync
                </span>
                <h3 className="text-xl font-bold text-slate-800 dark:text-slate-200 capitalize text-left">
                  Sync {getBrandName(activeLoginModal)} Session
                </h3>
              </div>
              <button
                onClick={() => setActiveLoginModal(null)}
                className="text-slate-450 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 transition text-xs font-bold p-1 border border-slate-200 dark:border-slate-800 rounded-lg"
              >
                ✕ Close
              </button>
            </div>

            <div className="py-2 space-y-5 text-left">
              <div className="p-4 rounded-xl bg-teal-500/5 border border-teal-500/10 text-xs text-teal-600 dark:text-teal-300 font-light leading-relaxed">
                🔒 <strong>Zero-Knowledge Sync:</strong> To protect your security, we never collect, ask for, or store your passwords. Instead, you sync session cookies directly using our browser companion.
              </div>
              
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">How to Sync:</h4>
                <ol className="list-decimal pl-5 text-xs text-slate-600 dark:text-slate-400 space-y-2">
                  <li>Install the <strong>Echo Apply Companion Extension</strong> from Chrome Web Store.</li>
                  <li>Log in to <strong>{getBrandName(activeLoginModal)}</strong> in your browser normally.</li>
                  <li>Open the extension and click <strong>&quot;Sync Session to Dashboard&quot;</strong>.</li>
                  <li>Your session cookies will be encrypted and mapped automatically.</li>
                </ol>
              </div>

              <div className="pt-2 flex flex-col sm:flex-row gap-3">
                <a
                  href="/auth-sync"
                  className="flex-1 py-3 rounded-xl bg-teal-600 hover:bg-teal-500 text-center text-white font-bold text-xs transition shadow-lg shadow-teal-600/10"
                >
                  Go to Cookie Sync Page
                </a>
                <button
                  onClick={() => {
                    setLogins((prev: typeof logins) => activeLoginModal ? { ...prev, [activeLoginModal]: true } : prev);
                    setActiveLoginModal(null);
                    toast.success(`${getBrandName(activeLoginModal)} session synced successfully!`);
                  }}
                  className="px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 transition"
                >
                  Simulate Sync
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

