"use client";

import React, { useState, useEffect } from "react";
import { Loader2, X, CheckCircle, AlertTriangle, Sparkles, Send, ArrowRight } from "lucide-react";
import { apiFetch } from "../lib/api";

interface ScreenQuestionDraft {
  question_id: string;
  question_text: string;
  drafted_answer: string;
  confidence: number;
  needs_user_input: boolean;
  warning_message?: string;
}

interface ApplyDrawerProps {
  userId: string;
  jobId: string;
  jobTitle: string;
  jobCompany: string;
  jobApplyUrl?: string;
  onClose: () => void;
  onSuccess: () => void;
  onAgentTriggered?: (taskId: string) => void;
}

export default function ApplyDrawer({
  userId,
  jobId,
  jobTitle,
  jobCompany,
  jobApplyUrl,
  onClose,
  onSuccess,
  onAgentTriggered,
}: ApplyDrawerProps) {
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [questions, setQuestions] = useState<ScreenQuestionDraft[]>([]);
  const [status, setStatus] = useState<"draft" | "submitted">("draft");
  const [optInAgent, setOptInAgent] = useState(true);
  const [actionRequired, setActionRequired] = useState<{ type: string; message: string; screenshot?: string } | null>(null);

  const fetchDraft = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const effectiveUserId = userId && userId.trim() ? userId : (typeof window !== "undefined" ? localStorage.getItem("user_id") || "guest" : "guest");
      
      const data = await apiFetch(`/apply/draft`, {
        method: "POST",
        body: JSON.stringify({
          user_id: effectiveUserId,
          job_id: jobId,
        }),
      });

      setQuestions(data.questions || []);
    } catch (err: any) {
      const msg = err.message || "Failed to load application draft.";
      if (msg.includes("401") || msg.includes("Unauthorized") || msg.includes("token")) {
        setError("Please sign in to personalize application questions with your resume.");
      } else if (msg.includes("Failed to fetch") || msg.includes("NetworkError") || msg.includes("Unable to connect")) {
        setError("Unable to connect to the server. Please check if the backend is running and try again.");
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDraft();
  }, [userId, jobId]);

  const handleAnswerChange = (idx: number, val: string) => {
    const updated = [...questions];
    updated[idx].drafted_answer = val;
    updated[idx].needs_user_input = false;
    setQuestions(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setError(null);

      const answersDict: Record<string, string> = {};
      questions.forEach((q) => {
        answersDict[q.question_text] = q.drafted_answer;
      });

      const effectiveUserId = userId && userId.trim() ? userId : (typeof window !== "undefined" ? localStorage.getItem("user_id") || "" : "");
      if (!effectiveUserId) {
        throw new Error("Please sign in to submit applications through Echo Apply Copilot.");
      }

      const data = await apiFetch(`/apply/submit`, {
        method: "POST",
        body: JSON.stringify({
          user_id: effectiveUserId,
          job_id: jobId,
          answers: answersDict,
          opt_in_agent: optInAgent,
        }),
      });

      if (data.status === "needs_action") {
        setActionRequired(data.action_required);
      } else if (data.status === "running") {
        if (onAgentTriggered) {
          onAgentTriggered(data.application_id);
        }
        setStatus("submitted");
        onSuccess();
      } else {
        setStatus("submitted");
        onSuccess();
      }
    } catch (err: any) {
      setError(err.message || "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-xl max-h-screen bg-white/90 dark:bg-slate-950/90 border-l border-slate-200 dark:border-slate-850 backdrop-blur-2xl shadow-2xl z-50 flex flex-col transform transition-transform duration-300 ease-out animate-slide-in text-slate-850 dark:text-slate-100">
      {/* Header */}
      <div className="p-6 border-b border-slate-200 dark:border-slate-800/80 flex justify-between items-center bg-slate-50/50 dark:bg-slate-900/40">
        <div>
          <span className="text-[10px] font-bold text-teal-600 dark:text-teal-400 uppercase tracking-widest animate-pulse">
            Application Copilot
          </span>
          <h3 className="text-lg font-bold text-slate-850 dark:text-slate-100 mt-1">
            {jobTitle}
          </h3>
          <p className="text-sm text-slate-550 dark:text-slate-400 mt-0.5">{jobCompany}</p>
        </div>
        <button
          onClick={onClose}
          className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800/80 text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-all border border-transparent hover:border-slate-200 dark:hover:border-slate-700/50"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Stepper Progress Indicator */}
      <div className="px-6 py-4 bg-slate-50/30 dark:bg-slate-900/10 border-b border-slate-200 dark:border-slate-800/50 flex items-center justify-between text-[11px] font-bold">
        <div className="flex items-center space-x-2">
          <div className={`w-5 h-5 rounded-full flex items-center justify-center border text-[9px] ${
            status === "submitted" || actionRequired ? "bg-teal-600 border-teal-600 text-white" : "bg-teal-600/10 border-teal-500/30 text-teal-600 dark:text-teal-400"
          }`}>1</div>
          <span className={status === "submitted" || actionRequired ? "text-slate-400 font-light" : "text-slate-800 dark:text-slate-200"}>Review Answers</span>
        </div>
        <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
        <div className="flex items-center space-x-2">
          <div className={`w-5 h-5 rounded-full flex items-center justify-center border text-[9px] ${
            status === "submitted" ? "bg-teal-600 border-teal-600 text-white" :
            actionRequired ? "bg-amber-500 border-amber-500 text-white" : "bg-slate-100 dark:bg-slate-950 border-slate-200 dark:border-slate-800 text-slate-400"
          }`}>2</div>
          <span className={
            status === "submitted" ? "text-slate-400 font-light" :
            actionRequired ? "text-amber-600 dark:text-amber-400" : "text-slate-400 font-light"
          }>Run Copilot</span>
        </div>
        <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
        <div className="flex items-center space-x-2">
          <div className={`w-5 h-5 rounded-full flex items-center justify-center border text-[9px] ${
            status === "submitted" ? "bg-teal-600 border-teal-600 text-white" : "bg-slate-100 dark:bg-slate-950 border-slate-200 dark:border-slate-800 text-slate-400"
          }`}>3</div>
          <span className={status === "submitted" ? "text-slate-800 dark:text-slate-200" : "text-slate-400 font-light"}>Done</span>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {loading ? (
          <div className="h-full flex flex-col justify-center items-center py-20 space-y-4">
            <Loader2 className="w-10 h-10 text-teal-500 animate-spin" />
            <p className="text-slate-500 dark:text-slate-400 text-sm animate-pulse">
              Analyzing job and drafting screening answers...
            </p>
          </div>
        ) : error ? (
          <div className="p-5 rounded-2xl bg-rose-500/5 dark:bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-300 text-sm space-y-3">
            <div className="flex items-start space-x-2">
              <AlertTriangle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
              <p className="flex-1">{error}</p>
            </div>
            <div className="flex items-center space-x-3 pt-2">
              <button
                type="button"
                onClick={fetchDraft}
                className="px-4 py-2 bg-teal-600 hover:bg-teal-500 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-teal-500/20"
              >
                Retry
              </button>
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-xl text-xs font-semibold transition-all"
              >
                Close Panel
              </button>
            </div>
          </div>
        ) : status === "submitted" ? (
          <div className="h-full flex flex-col justify-center items-center py-12 space-y-6 text-center">
            <div className="w-16 h-16 bg-teal-500/10 dark:bg-teal-500/20 border border-teal-500/30 rounded-full flex justify-center items-center text-teal-500 dark:text-teal-400 animate-bounce">
              <CheckCircle className="w-10 h-10" />
            </div>
            <div>
              <h4 className="text-xl font-bold text-slate-850 dark:text-slate-100">
                Copilot Materials Prepared!
              </h4>
              <p className="text-slate-500 dark:text-slate-400 text-sm max-w-sm mt-2">
                All tailored documents, resumes, and screening answers have been generated.
              </p>
            </div>
            
            <div className="w-full max-w-sm flex flex-col gap-3">
              {jobApplyUrl && (
                <a
                  href={jobApplyUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full py-3 bg-teal-600 hover:bg-teal-500 text-white rounded-xl text-sm font-bold text-center transition-all shadow-lg shadow-teal-500/25 flex justify-center items-center space-x-2"
                >
                  <span>Open Application Page ↗</span>
                </a>
              )}
              <button
                onClick={() => {
                  onSuccess();
                  onClose();
                }}
                className="w-full py-3 bg-slate-100 hover:bg-slate-200 dark:bg-slate-900 dark:hover:bg-slate-800 text-slate-750 dark:text-slate-200 border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-semibold transition-all"
              >
                Mark as Applied & Save
              </button>
            </div>
            
            <div className="p-4 rounded-xl bg-slate-50/50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800/80 text-left text-xs text-slate-600 dark:text-slate-400 max-w-sm space-y-2 w-full">
              <p className="font-semibold text-slate-700 dark:text-slate-300 mb-1">Copilot Status:</p>
              <div className="flex justify-between">
                <span>Tailored Resume:</span>
                <span className="text-teal-600 dark:text-teal-400 font-medium">Ready</span>
              </div>
              <div className="flex justify-between">
                <span>Screening Answers:</span>
                <span className="text-teal-600 dark:text-teal-400 font-medium">Prepared</span>
              </div>
            </div>
          </div>
        ) : actionRequired ? (
          <div className="h-full flex flex-col justify-center items-center py-12 space-y-6 text-center animate-fade-in">
            <div className="w-16 h-16 bg-amber-500/10 dark:bg-amber-500/20 border border-amber-500/30 rounded-full flex justify-center items-center text-amber-550 dark:text-amber-400 animate-pulse">
              <AlertTriangle className="w-10 h-10" />
            </div>
            <div>
              <h4 className="text-xl font-bold text-slate-850 dark:text-slate-100">
                Action Required (Copilot Mode)
              </h4>
              <p className="text-slate-500 dark:text-slate-400 text-sm max-w-sm mt-2">
                {actionRequired.message}
              </p>
            </div>
            
            {actionRequired.screenshot && (
              <div className="w-full max-w-sm rounded-xl overflow-hidden border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/60 p-3 text-left">
                <span className="text-[10px] font-bold text-slate-400 block mb-1 uppercase tracking-wider">Form Screenshot Captured</span>
                <p className="text-xs text-slate-500">File: <code className="text-slate-800 dark:text-slate-300 font-mono">{actionRequired.screenshot}</code> is saved in the workspace.</p>
              </div>
            )}

            <div className="flex flex-col space-y-3 w-full max-w-sm pt-4">
              <button
                onClick={() => {
                  setStatus("submitted");
                  onSuccess();
                }}
                className="w-full py-2.5 bg-teal-600 hover:bg-teal-500 text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-teal-500/20 flex justify-center items-center space-x-2"
              >
                <span>Mark as Applied & Save</span>
              </button>
              <button
                onClick={() => setActionRequired(null)}
                className="w-full py-2.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-900 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl text-sm font-semibold transition-all border border-slate-200 dark:border-slate-800"
              >
                Go Back to Form
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="p-4 rounded-2xl bg-teal-500/5 dark:bg-teal-500/10 border border-teal-500/10 dark:border-teal-500/20 flex items-start space-x-3">
              <Sparkles className="w-5 h-5 text-teal-600 dark:text-teal-400 mt-0.5 flex-shrink-0" />
              <div className="text-xs text-teal-800 dark:text-teal-300 leading-relaxed">
                <span className="font-bold text-teal-700 dark:text-teal-200">Factual Tailoring:</span> We parsed your resume and drafted answers conforming to your verified skills. Please review and clarify items labeled <strong>Needs Attention</strong>.
              </div>
            </div>

            {/* Questions List */}
            <div className="space-y-5">
              {questions.map((q, idx) => (
                <div
                  key={q.question_id}
                  className={`p-5 rounded-2xl border backdrop-blur-md transition-all duration-300 hover:shadow-sm ${
                    q.needs_user_input
                      ? "border-amber-500/30 bg-amber-550/5 dark:bg-amber-500/5 shadow-inner"
                      : "border-slate-200 dark:border-slate-800/80 bg-white/40 dark:bg-slate-900/20"
                  }`}
                >
                  <div className="flex justify-between items-start space-x-2 mb-3">
                    <label className="text-sm font-bold text-slate-800 dark:text-slate-200 leading-snug">
                      {q.question_text}
                    </label>
                    {q.needs_user_input ? (
                      <span className="text-[9px] font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 bg-amber-500/10 px-2.5 py-1 rounded-full border border-amber-500/20 flex items-center space-x-1 flex-shrink-0">
                        <AlertTriangle className="w-3 h-3 mr-0.5" />
                        <span>Needs Input</span>
                      </span>
                    ) : (
                      <span className="text-[9px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20 flex items-center space-x-1 flex-shrink-0">
                        <CheckCircle className="w-3 h-3 mr-0.5" />
                        <span>Auto-Filled</span>
                      </span>
                    )}
                  </div>

                  {q.warning_message && (
                    <p className="text-xs text-amber-700 dark:text-amber-300/80 mb-3 leading-relaxed bg-amber-500/10 px-3 py-1.5 rounded-xl border border-amber-500/10">
                      {q.warning_message}
                    </p>
                  )}

                  <textarea
                    rows={3}
                    value={q.drafted_answer}
                    onChange={(e) => handleAnswerChange(idx, e.target.value)}
                    required
                    placeholder="Enter your answer here..."
                    className="w-full px-4 py-2.5 rounded-xl bg-white/80 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200 text-sm focus:outline-none focus:border-teal-500 transition-all placeholder-slate-400 dark:placeholder-slate-600 focus:ring-1 focus:ring-teal-500/20 outline-none"
                  />
                </div>
              ))}
            </div>

            {/* Opt-in to Application Copilot Checkbox */}
            <div className="p-4 rounded-2xl bg-teal-500/5 dark:bg-teal-950/20 border border-teal-500/10 space-y-3">
              <label className="flex items-start space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={optInAgent}
                  onChange={(e) => setOptInAgent(e.target.checked)}
                  className="mt-1 rounded border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-955 text-teal-650 focus:ring-teal-500/25 focus:ring-offset-white dark:focus:ring-offset-slate-950 w-4 h-4"
                />
                <div className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                  <span className="font-semibold text-slate-800 dark:text-slate-200">Prepare with Application Copilot (Playwright)</span>
                  <p className="text-slate-500 dark:text-slate-400 mt-1">
                    Runs a background session to inspect the application page, align your skills, pre-fill details, and prepare screening answers for copy-pasting.
                  </p>
                  <p className="text-teal-600 dark:text-teal-400 font-medium mt-1">
                    ✓ 100% Policy-Safe: The copilot prepares materials for you but never clicks submit.
                  </p>
                </div>
              </label>
            </div>

            {/* Action Bar */}
            <div className="pt-4 border-t border-slate-200 dark:border-slate-900 flex justify-end space-x-3">
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 text-sm font-semibold hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-800 dark:hover:text-slate-100 transition-all"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-6 py-2.5 bg-teal-650 hover:bg-teal-600 disabled:bg-teal-600/50 text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-teal-600/25 flex items-center space-x-2"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Preparing...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span>Prepare Application</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

