"use client";

import React, { useState, useEffect } from "react";
import { CheckSquare, Square, CheckCircle2, ChevronDown, ChevronUp, Sparkles, Settings, FileUp, Bell, Zap } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface ChecklistItem {
  id: string;
  label: string;
  desc: string;
  completed: boolean;
  actionText: string;
  actionHref: string;
  icon: React.ReactNode;
}

interface OnboardingChecklistProps {
  hasResume: boolean;
}

export default function OnboardingChecklist({ hasResume }: OnboardingChecklistProps) {
  const [isOpen, setIsOpen] = useState(true);
  const [isDismissed, setIsDismissed] = useState(false);
  const [completedSteps, setCompletedSteps] = useState<Record<string, boolean>>({
    uploadResume: false,
    syncCredentials: false,
    configureAlerts: false,
    tryInterview: false
  });

  useEffect(() => {
    // Load dismissed status
    const dismissed = localStorage.getItem("smartapply_checklist_dismissed");
    if (dismissed === "true") {
      setIsDismissed(true);
    }

    // Load custom manual checkmarks from localStorage
    const savedSteps = localStorage.getItem("smartapply_checklist_steps");
    if (savedSteps) {
      try {
        setCompletedSteps(JSON.parse(savedSteps));
      } catch (e) {
        console.error(e);
      }
    }
  }, []);

  // Sync auto-computed resume step
  useEffect(() => {
    if (hasResume) {
      updateStep("uploadResume", true);
    }
  }, [hasResume]);

  const updateStep = (stepId: string, val: boolean) => {
    setCompletedSteps((prev) => {
      const updated = { ...prev, [stepId]: val };
      localStorage.setItem("smartapply_checklist_steps", JSON.stringify(updated));
      return updated;
    });
  };

  const handleDismiss = () => {
    setIsDismissed(true);
    localStorage.setItem("smartapply_checklist_dismissed", "true");
  };

  if (isDismissed) return null;

  const checklistData = [
    {
      id: "uploadResume",
      label: "Upload & Parse Resume",
      desc: "Import your PDF resume to extract key details and activate semantic job matching.",
      completed: completedSteps.uploadResume || hasResume,
      actionText: "Upload PDF",
      actionHref: "#resume-workspace",
      icon: <FileUp className="w-4 h-4 text-teal-500" />
    },
    {
      id: "syncCredentials",
      label: "Sync Job Board Sessions",
      desc: "Connect your LinkedIn / Indeed accounts in Settings for background autofill drafting.",
      completed: completedSteps.syncCredentials,
      actionText: "Sync Now",
      actionHref: "/settings",
      icon: <Settings className="w-4 h-4 text-teal-500" />
    },
    {
      id: "configureAlerts",
      label: "Set Up Job Alerts",
      desc: "Subscribe to custom matching alerts to get notified about matched vacancy listings.",
      completed: completedSteps.configureAlerts,
      actionText: "Configure Alerts",
      actionHref: "/settings",
      icon: <Bell className="w-4 h-4 text-teal-500" />
    },
    {
      id: "tryInterview",
      label: "Launch AI Interview Prep",
      desc: "Practice with customized Gemini questions and receive constructive STAR method feedback.",
      completed: completedSteps.tryInterview,
      actionText: "Launch prep",
      actionHref: "/interview",
      icon: <Zap className="w-4 h-4 text-teal-500" />
    }
  ];

  const totalSteps = checklistData.length;
  const completedCount = checklistData.filter((item) => item.completed).length;
  const progressPercent = Math.round((completedCount / totalSteps) * 100);

  return (
    <div className="w-full max-w-4xl mx-auto rounded-3xl bg-slate-900/40 backdrop-blur-xl border border-slate-800 overflow-hidden shadow-xl shadow-teal-500/5 transition-all duration-300">
      {/* Header */}
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between p-5 cursor-pointer hover:bg-slate-900/20 transition duration-200 select-none"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-teal-500/10 text-teal-400 rounded-xl">
            <Sparkles className="w-5 h-5" />
          </div>
          <div className="text-left">
            <h3 className="text-sm font-bold text-slate-200">Onboarding Checklist</h3>
            <p className="text-[10px] text-slate-400 font-semibold tracking-wide">
              {completedCount} of {totalSteps} tasks completed ({progressPercent}%)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Progress Bar */}
          <div className="hidden sm:block w-36 h-2 rounded-full bg-slate-800 overflow-hidden border border-slate-800">
            <div 
              className="h-full bg-gradient-to-r from-teal-500 to-violet-600 rounded-full transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          <button className="text-slate-400 hover:text-slate-200 transition">
            {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Checklist List */}
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="overflow-hidden border-t border-slate-800/60 bg-slate-950/20"
          >
            <div className="p-5 space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                {checklistData.map((item) => (
                  <div 
                    key={item.id}
                    className={`p-4 rounded-2xl border transition duration-300 flex items-start gap-3.5 ${
                      item.completed 
                        ? "bg-teal-500/5 border-teal-500/20 text-slate-350"
                        : "bg-slate-950/40 border-slate-800 hover:border-slate-700 text-slate-200"
                    }`}
                  >
                    {/* Checkbox toggle */}
                    <button 
                      onClick={() => updateStep(item.id, !item.completed)}
                      className="mt-0.5 text-teal-400 hover:text-teal-300 shrink-0 transition"
                    >
                      {item.completed ? (
                        <CheckCircle2 className="w-5 h-5 text-teal-500 fill-teal-500/10" />
                      ) : (
                        <div className="w-5 h-5 rounded-lg border-2 border-slate-600 hover:border-teal-500 transition" />
                      )}
                    </button>

                    <div className="flex-1 space-y-1.5 text-left">
                      <div className="flex items-center gap-1.5">
                        <span className="shrink-0">{item.icon}</span>
                        <h4 className={`text-xs font-bold ${item.completed ? "line-through text-slate-500" : ""}`}>
                          {item.label}
                        </h4>
                      </div>
                      <p className="text-[10px] text-slate-400 leading-relaxed font-light">{item.desc}</p>
                      
                      {!item.completed && (
                        <a 
                          href={item.actionHref}
                          className="inline-block text-[9px] font-bold text-teal-400 hover:text-teal-300 hover:underline uppercase tracking-wider pt-0.5"
                        >
                          {item.actionText} &rarr;
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Complete banner/dismiss option */}
              <div className="flex items-center justify-between pt-3 border-t border-slate-800/60 text-[10px] text-slate-500 font-semibold uppercase tracking-wider">
                <span>{progressPercent === 100 ? "🎉 Congratulations! You are all set!" : "Complete all tasks to optimize matches"}</span>
                <button 
                  onClick={handleDismiss}
                  className="text-slate-400 hover:text-rose-400 transition"
                >
                  Dismiss Checklist
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

