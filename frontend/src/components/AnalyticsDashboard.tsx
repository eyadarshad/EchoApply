"use client";

import React, { useEffect, useState } from "react";
import { BarChart3, TrendingUp, Award, Calendar, Loader2 } from "lucide-react";
import { getBackendUrl, getAuthHeaders } from "../lib/api";

interface AnalyticsData {
  total_applied: number;
  conversion_funnel: {
    pending: number;
    applied: number;
    interviewing: number;
    offered: number;
  };
  avg_ats_score: number;
  applications_timeline: Array<{ date: string; count: number }>;
}

export default function AnalyticsDashboard() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [hoveredBar, setHoveredBar] = useState<string | null>(null);

  useEffect(() => {
    const userId = localStorage.getItem("userId") || "00000000-0000-0000-0000-000000000001";
    fetchAnalytics(userId);
  }, []);

  const fetchAnalytics = async (uid: string) => {
    try {
      const res = await fetch(`${getBackendUrl()}/api/analytics/summary?user_id=${uid}`, {
        headers: getAuthHeaders()
      });
      if (res.ok) {
        const d = await res.json();
        setData(d);
      }
    } catch (err) {
      console.error("Error loading analytics:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="w-6 h-6 animate-spin text-teal-500" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center p-8 text-slate-400">
        No analytics data available.
      </div>
    );
  }

  const funnelKeys = Object.keys(data.conversion_funnel) as Array<keyof typeof data.conversion_funnel>;
  const funnelMax = Math.max(...Object.values(data.conversion_funnel), 1);
  const interviewRate = data.total_applied > 0 
    ? Math.round(((data.conversion_funnel.interviewing + data.conversion_funnel.offered) / data.total_applied) * 100) 
    : 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-teal-500" /> Application Analytics
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">Real-time performance tracking and match score trends</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="p-4 rounded-2xl bg-white/50 dark:bg-slate-900/30 border border-slate-250/60 dark:border-slate-800 shadow-sm flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-teal-500/10 text-teal-500 dark:text-teal-400">
            <Calendar className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-slate-400">Total Applied</div>
            <div className="text-xl font-black text-slate-800 dark:text-slate-100 mt-0.5">{data.total_applied}</div>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-white/50 dark:bg-slate-900/30 border border-slate-250/60 dark:border-slate-800 shadow-sm flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-500 dark:text-emerald-400">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-slate-400">Interview Rate</div>
            <div className="text-xl font-black text-slate-800 dark:text-slate-100 mt-0.5">{interviewRate}%</div>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-white/50 dark:bg-slate-900/30 border border-slate-250/60 dark:border-slate-800 shadow-sm flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-500 dark:text-amber-400">
            <Award className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-slate-400">Avg ATS Score</div>
            <div className="text-xl font-black text-slate-800 dark:text-slate-100 mt-0.5">{Math.round(data.avg_ats_score)}%</div>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Funnel SVG Chart */}
        <div className="p-5 rounded-2xl bg-white/50 dark:bg-slate-900/30 border border-slate-250/60 dark:border-slate-800 shadow-sm space-y-4">
          <h3 className="text-xs font-bold text-slate-500 dark:text-slate-300 uppercase tracking-wider">Conversion Funnel</h3>
          
          <div className="flex flex-col gap-3">
            {funnelKeys.map((key) => {
              const val = data.conversion_funnel[key];
              const pct = (val / funnelMax) * 100;
              return (
                <div 
                  key={key} 
                  className="space-y-1"
                  onMouseEnter={() => setHoveredBar(key)}
                  onMouseLeave={() => setHoveredBar(null)}
                >
                  <div className="flex justify-between text-xs font-medium">
                    <span className="capitalize text-slate-600 dark:text-slate-300">{key}</span>
                    <span className="text-slate-400 dark:text-slate-500">{val} jobs</span>
                  </div>
                  <div className="h-6 w-full bg-slate-100 dark:bg-slate-800/50 rounded-lg overflow-hidden border border-slate-200/40 dark:border-slate-800">
                    <div 
                      className={`h-full rounded-lg bg-gradient-to-r transition-all duration-500 ${
                        key === "offered" ? "from-emerald-500 to-teal-400" :
                        key === "interviewing" ? "from-teal-500 to-teal-400" :
                        key === "applied" ? "from-violet-500 to-purple-400" :
                        "from-slate-400 to-slate-300"
                      }`}
                      style={{ width: `${Math.max(pct, 5)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Timeline SVG Chart */}
        <div className="p-5 rounded-2xl bg-white/50 dark:bg-slate-900/30 border border-slate-250/60 dark:border-slate-800 shadow-sm space-y-4 flex flex-col justify-between">
          <h3 className="text-xs font-bold text-slate-500 dark:text-slate-300 uppercase tracking-wider">Application Timeline</h3>
          
          <div className="h-36 w-full flex items-end gap-1.5 pt-4">
            {data.applications_timeline.length === 0 ? (
              <div className="w-full h-full flex items-center justify-center text-xs text-slate-400">
                No recent application activity.
              </div>
            ) : (
              data.applications_timeline.map((item, idx) => {
                const maxCount = Math.max(...data.applications_timeline.map(t => t.count), 1);
                const heightPct = (item.count / maxCount) * 100;
                return (
                  <div key={idx} className="flex-1 flex flex-col items-center gap-1.5 group h-full justify-end">
                    <div className="relative w-full bg-teal-500/20 dark:bg-teal-500/10 rounded-t border border-teal-500/20 hover:bg-teal-500/40 transition-all cursor-pointer" style={{ height: `${heightPct}%` }}>
                      {/* Tooltip */}
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block bg-slate-950 text-white text-[9px] font-bold py-1 px-1.5 rounded whitespace-nowrap shadow-md z-10">
                        {item.count} applications
                      </div>
                    </div>
                    <span className="text-[8px] text-slate-400 truncate w-full text-center">
                      {item.date.split("-").slice(1).join("/")}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

