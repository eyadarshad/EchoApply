"use client";

import React, { useState, useEffect } from "react";
import { Loader2, X, CheckCircle, AlertTriangle, Sparkles, Send, ArrowRight } from "lucide-react";

interface ScreenQuestionDraft {
  question_id: string;
  question_text: string;
  drafted_answer: string;
  confidence: number;
  needs_user_input: bool;
  warning_message?: string;
}

interface ApplyDrawerProps {
  userId: string;
  jobId: string;
  jobTitle: string;
  jobCompany: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function ApplyDrawer({
  userId,
  jobId,
  jobTitle,
  jobCompany,
  onClose,
  onSuccess,
}: ApplyDrawerProps) {
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [questions, setQuestions] = useState<ScreenQuestionDraft[]>([]);
  const [status, setStatus] = useState<"draft" | "submitted">("draft");

  useEffect(() => {
    async function fetchDraft() {
      try {
        setLoading(true);
        setError(null);
        
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
        const response = await fetch(`${backendUrl}/apply/draft`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            user_id: userId,
            job_id: jobId,
          }),
        });

        if (!response.ok) {
          throw new Error("Failed to fetch screening questions.");
        }

        const data = await response.json();
        setQuestions(data.questions || []);
      } catch (err: any) {
        setError(err.message || "An unexpected error occurred.");
      } finally {
        setLoading(false);
      }
    }

    fetchDraft();
  }, [userId, jobId]);

  const handleAnswerChange = (idx: number, val: string) => {
    const updated = [...questions];
    updated[idx].drafted_answer = val;
    // Clear need for input since user has modified/reviewed it
    updated[idx].needs_user_input = false;
    setQuestions(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setError(null);

      // Map questions to simple ID -> Answer dict
      const answersDict: Record<string, string> = {};
      questions.forEach((q) => {
        answersDict[q.question_id] = q.drafted_answer;
      });

      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
      const response = await fetch(`${backendUrl}/apply/submit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: userId,
          job_id: jobId,
          answers: answersDict,
          opt_in_agent: false,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to submit application.");
      }

      setStatus("submitted");
      onSuccess();
    } catch (err: any) {
      setError(err.message || "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-xl bg-slate-950/95 border-l border-slate-800/80 backdrop-blur-2xl shadow-2xl z-50 flex flex-col transform transition-transform duration-300 ease-out animate-slide-in">
      {/* Header */}
      <div className="p-6 border-b border-slate-800/80 flex justify-between items-center bg-slate-900/40">
        <div>
          <span className="text-xs font-semibold text-indigo-400 uppercase tracking-widest">
            Smart Apply (Tier 1)
          </span>
          <h3 className="text-lg font-bold text-slate-100 mt-1">
            {jobTitle}
          </h3>
          <p className="text-sm text-slate-400 mt-0.5">{jobCompany}</p>
        </div>
        <button
          onClick={onClose}
          className="p-2 rounded-xl hover:bg-slate-800/80 text-slate-400 hover:text-slate-200 transition-all border border-transparent hover:border-slate-700/50"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {loading ? (
          <div className="h-full flex flex-col justify-center items-center py-20 space-y-4">
            <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
            <p className="text-slate-400 text-sm animate-pulse">
              Analyzing job and drafting screening answers...
            </p>
          </div>
        ) : error ? (
          <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm space-y-3">
            <p>{error}</p>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-semibold transition-all"
            >
              Close Panel
            </button>
          </div>
        ) : status === "submitted" ? (
          <div className="h-full flex flex-col justify-center items-center py-12 space-y-6 text-center">
            <div className="w-16 h-16 bg-emerald-500/20 border border-emerald-500/30 rounded-full flex justify-center items-center text-emerald-400 animate-bounce">
              <CheckCircle className="w-10 h-10" />
            </div>
            <div>
              <h4 className="text-xl font-bold text-slate-100">
                Application Submitted!
              </h4>
              <p className="text-slate-400 text-sm max-w-sm mt-2">
                Your application for <strong>{jobTitle}</strong> at <strong>{jobCompany}</strong> has been successfully recorded.
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 text-left text-xs text-slate-400 max-w-sm space-y-2">
              <p className="font-semibold text-slate-300 mb-1">Recorded details:</p>
              <div className="flex justify-between">
                <span>Status:</span>
                <span className="text-emerald-400 font-medium">Applied</span>
              </div>
              <div className="flex justify-between">
                <span>Applied at:</span>
                <span>{new Date().toLocaleDateString()}</span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-indigo-600/20 flex items-center space-x-2"
            >
              <span>Back to Job Search</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="p-4 rounded-2xl bg-indigo-500/5 border border-indigo-500/10 flex items-start space-x-3">
              <Sparkles className="w-5 h-5 text-indigo-400 mt-0.5 flex-shrink-0" />
              <div className="text-xs text-indigo-300 leading-relaxed">
                <span className="font-bold text-indigo-200">Factual Tailoring:</span> We parsed your resume and drafted answers conforming to your verified skills. Please review and clarify items labeled <strong>Needs Attention</strong>.
              </div>
            </div>

            {/* Questions List */}
            <div className="space-y-5">
              {questions.map((q, idx) => (
                <div
                  key={q.question_id}
                  className={`p-4 rounded-2xl border transition-all ${
                    q.needs_user_input
                      ? "border-amber-500/30 bg-amber-500/5"
                      : "border-slate-800/80 bg-slate-900/30"
                  }`}
                >
                  <div className="flex justify-between items-start space-x-2 mb-2">
                    <label className="text-sm font-bold text-slate-200">
                      {q.question_text}
                    </label>
                    {q.needs_user_input ? (
                      <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20 flex items-center space-x-1 flex-shrink-0">
                        <AlertTriangle className="w-3 h-3 mr-0.5" />
                        <span>Needs Input</span>
                      </span>
                    ) : (
                      <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 flex items-center space-x-1 flex-shrink-0">
                        <CheckCircle className="w-3 h-3 mr-0.5" />
                        <span>Auto-Filled</span>
                      </span>
                    )}
                  </div>

                  {q.warning_message && (
                    <p className="text-xs text-amber-300/80 mb-2 leading-relaxed bg-amber-500/10 px-3 py-1.5 rounded-xl border border-amber-500/10">
                      {q.warning_message}
                    </p>
                  )}

                  <textarea
                    rows={3}
                    value={q.drafted_answer}
                    onChange={(e) => handleAnswerChange(idx, e.target.value)}
                    required
                    placeholder="Enter your answer here..."
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-sm focus:outline-none focus:border-indigo-500 transition-all placeholder-slate-600 focus:ring-1 focus:ring-indigo-500/20"
                  />
                </div>
              ))}
            </div>

            {/* Action Bar */}
            <div className="pt-4 border-t border-slate-900 flex justify-end space-x-3">
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 text-sm font-semibold hover:bg-slate-800 hover:text-slate-100 transition-all"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/50 text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-indigo-600/25 flex items-center space-x-2"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Submitting...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span>Submit Application</span>
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
