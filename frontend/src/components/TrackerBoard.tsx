"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Briefcase, ArrowRightLeft, Calendar, Award, Trash2, CheckCircle2, ChevronRight, X, ExternalLink } from "lucide-react";
import { audioEngine } from "../app/AudioEngine";
import { apiFetch } from "../lib/api";

interface Application {
  id: string;
  status: string;
  applied_at: string | null;
  job_id: string;
  title: string;
  company: string;
  location?: string;
  source: string;
  apply_url?: string;
}

interface TrackerBoardProps {
  user_id: string;
}

const COLUMNS = [
  { id: "applied", label: "Applied / Submitted", color: "border-teal-500/30 text-teal-400 bg-teal-500/5" },
  { id: "interviewing", label: "Interviewing", color: "border-amber-500/30 text-amber-400 bg-amber-500/5" },
  { id: "offer", label: "Offers Extended", color: "border-emerald-500/30 text-emerald-400 bg-emerald-500/5" },
  { id: "rejected", label: "Closed / Rejected", color: "border-rose-500/30 text-rose-400 bg-rose-500/5" }
];

export default function TrackerBoard({ user_id }: TrackerBoardProps) {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCard, setSelectedCard] = useState<Application | null>(null);

  const fetchApplications = async () => {
    try {
      setLoading(true);
      const data = await apiFetch(`/api/applications/${user_id}`);
      if (data.status === "success") {
        setApplications(data.applications || []);
      }
    } catch (err) {
      console.error("Failed to load applications:", err);
      setError("Unable to connect to application tracking server.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user_id) {
      fetchApplications();
    }
  }, [user_id]);

  const updateAppStatus = async (appId: string, newStatus: string) => {
    try {
      audioEngine.playClick();
      // Optimistic update
      setApplications((prev) =>
        prev.map((app) => (app.id === appId ? { ...app, status: newStatus } : app))
      );
      
      const data = await apiFetch(`/api/applications/update-status`, {
        method: "POST",
        body: JSON.stringify({
          application_id: appId,
          status: newStatus
        })
      });
      if (data.status !== "success") {
        fetchApplications(); // Revert on failure
      }
    } catch (err) {
      console.error("Failed to update status:", err);
      fetchApplications();
    }
  };

  const getColIcon = (colId: string) => {
    switch (colId) {
      case "applied": return <Briefcase className="w-4 h-4 text-teal-400" />;
      case "interviewing": return <Calendar className="w-4 h-4 text-amber-400" />;
      case "offer": return <Award className="w-4 h-4 text-emerald-400" />;
      default: return <X className="w-4 h-4 text-rose-400" />;
    }
  };

  return (
    <div className="space-y-6 text-left">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-xl font-bold text-slate-800 dark:text-slate-200">Job Application Tracker</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">Manage and update progress states for all tailored auto-apply applications.</p>
        </div>
      </div>

      {loading && applications.length === 0 ? (
        <div className="flex justify-center items-center py-20">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            className="w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full"
          />
        </div>
      ) : applications.length === 0 ? (
        <div className="p-10 text-center rounded-2xl border border-dashed border-slate-300 dark:border-slate-800 text-slate-500">
          <Briefcase className="w-10 h-10 mx-auto mb-4 stroke-1 opacity-60" />
          <p className="text-sm font-semibold">No applications tracked yet.</p>
          <p className="text-xs mt-1">Applications submitted through our Smart Auto-Apply drawer will automatically appear here!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 items-start">
          {COLUMNS.map((col) => {
            const colApps = applications.filter((app) => app.status === col.id);
            
            return (
              <div
                key={col.id}
                className="flex flex-col rounded-2xl bg-slate-100/60 dark:bg-slate-900/10 border border-slate-200 dark:border-slate-800/80 p-4 min-h-[450px]"
              >
                {/* Column Title */}
                <div className={`flex justify-between items-center px-2 py-1.5 rounded-xl border ${col.color} mb-4 font-bold text-xs`}>
                  <div className="flex items-center gap-2">
                    {getColIcon(col.id)}
                    <span>{col.label}</span>
                  </div>
                  <span className="bg-white/10 px-2 py-0.5 rounded-md text-[10px]">{colApps.length}</span>
                </div>

                {/* Cards Container */}
                <div className="flex-1 space-y-3 overflow-y-auto max-h-[500px] scrollbar-none pr-1">
                  <AnimatePresence mode="popLayout">
                    {colApps.map((app) => (
                      <motion.div
                        key={app.id}
                        layout
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        transition={{ type: "spring", stiffness: 350, damping: 25 }}
                        onClick={() => setSelectedCard(app)}
                        className="p-4 rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800/60 hover:border-teal-500/50 dark:hover:border-teal-500/50 shadow-sm cursor-pointer transition flex flex-col gap-2 group text-left"
                      >
                        <div className="flex justify-between items-start gap-2">
                          <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 group-hover:text-teal-600 dark:group-hover:text-teal-400 line-clamp-2">{app.title}</h4>
                          <span className="text-[10px] bg-teal-500/10 text-teal-600 dark:text-teal-400 px-2 py-0.5 rounded uppercase font-bold tracking-wider">{app.source}</span>
                        </div>
                        
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 font-semibold">{app.company}</p>
                        
                        {app.location && (
                          <p className="text-[10px] text-slate-450 dark:text-slate-450">{app.location}</p>
                        )}

                        <div className="flex justify-between items-center mt-2 pt-2 border-t border-slate-100 dark:border-slate-800/80">
                          <span className="text-[9px] text-slate-400 font-light">
                            {app.applied_at ? new Date(app.applied_at).toLocaleDateString() : "Recently"}
                          </span>
                          
                          {/* Shifter actions */}
                          <div className="flex gap-1">
                            {COLUMNS.map((c) => {
                              if (c.id === app.status) return null;
                              return (
                                <button
                                  key={c.id}
                                  title={`Move to ${c.label}`}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    updateAppStatus(app.id, c.id);
                                  }}
                                  className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded text-slate-400 hover:text-slate-200 transition"
                                >
                                  {getColIcon(c.id)}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Details Dialog */}
      <AnimatePresence>
        {selectedCard && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/65 backdrop-blur-sm">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-md p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl relative space-y-4"
            >
              <button
                onClick={() => setSelectedCard(null)}
                className="absolute top-4 right-4 p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded transition text-slate-400 hover:text-slate-250"
              >
                <X className="w-4 h-4" />
              </button>

              <div className="flex items-center gap-3">
                <span className="text-xs bg-teal-500/10 text-teal-600 dark:text-teal-400 px-2.5 py-1 rounded font-bold uppercase tracking-wider">{selectedCard.source}</span>
                <span className={`text-[10px] px-2.5 py-0.5 rounded-full border ${COLUMNS.find(c => c.id === selectedCard.status)?.color} font-bold`}>
                  {COLUMNS.find(c => c.id === selectedCard.status)?.label}
                </span>
              </div>

              <div>
                <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 leading-snug">{selectedCard.title}</h3>
                <p className="text-sm font-semibold text-slate-500 dark:text-slate-400 mt-1">{selectedCard.company}</p>
                {selectedCard.location && (
                  <p className="text-xs text-slate-450 dark:text-slate-450 mt-0.5">{selectedCard.location}</p>
                )}
              </div>

              <div className="py-2 border-y border-slate-100 dark:border-slate-800 flex justify-between text-xs text-slate-500 dark:text-slate-300">
                <span>Applied On:</span>
                <span className="font-semibold text-slate-700 dark:text-slate-200">
                  {selectedCard.applied_at ? new Date(selectedCard.applied_at).toLocaleString() : "Recently"}
                </span>
              </div>

              <div className="flex gap-3">
                {selectedCard.apply_url && (
                  <a
                    href={selectedCard.apply_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    View Job Post
                  </a>
                )}
                
                <button
                  onClick={() => {
                    // Just simulated deletion
                    setApplications(prev => prev.filter(a => a.id !== selectedCard.id));
                    setSelectedCard(null);
                  }}
                  className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-rose-500/20 text-rose-500 hover:bg-rose-500/10 text-xs font-semibold transition"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Remove
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

