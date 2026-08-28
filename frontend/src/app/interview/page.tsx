"use client";
 
import React, { useState, useEffect } from "react";
import { Play, ArrowRight, Loader2, Sparkles, Award, CheckCircle, RefreshCw, MessageSquare, Clipboard, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { apiFetch } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import Navbar from "@/components/Navbar";
import PageHero from "@/components/PageHero";

interface FeedbackResult {
  score: number;
  star_compliance: string;
  tech_depth: string;
  communication_clarity: string;
  constructive_tips: string[];
}

export default function InterviewPage() {
  const { user_id } = useAuth();
  const userId = user_id || "00000000-0000-0000-0000-000000000001";
  
  // Setup inputs
  const [jobTitle, setJobTitle] = useState<string>("Software Engineer");
  const [jdText, setJdText] = useState<string>("");
  
  // States
  const [interviewStarted, setInterviewStarted] = useState<boolean>(false);
  const [loadingQuestions, setLoadingQuestions] = useState<boolean>(false);
  const [questions, setQuestions] = useState<string[]>([]);
  const [currentIdx, setCurrentIdx] = useState<number>(0);
  
  // Answer handling
  const [userAnswer, setUserAnswer] = useState<string>("");
  const [submittingAnswer, setSubmittingAnswer] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<FeedbackResult | null>(null);
  
  // Final summary
  const [allScores, setAllScores] = useState<number[]>([]);
  const [completed, setCompleted] = useState<boolean>(false);

  const handleStartInterview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!jdText.trim()) {
      toast.error("Please paste the job description first.");
      return;
    }

    setLoadingQuestions(true);
    try {
      const data = await apiFetch<{ questions: string[] }>("/api/interview/questions", {
        method: "POST",
        body: JSON.stringify({
          user_id: userId,
          job_title: jobTitle.trim(),
          jd_text: jdText.trim()
        })
      });

      setQuestions(data.questions);
      setInterviewStarted(true);
      setCurrentIdx(0);
      setUserAnswer("");
      setFeedback(null);
      setAllScores([]);
      setCompleted(false);
      toast.success("Interview started! Good luck!");
    } catch (err: any) {
      const msg = err.message || "Failed to load questions.";
      const isAuth = msg.toLowerCase().includes("token") || msg.toLowerCase().includes("expired") || msg.toLowerCase().includes("401");
      toast.error(isAuth ? "Session expired. Please sign in again." : msg);
    } finally {
      setLoadingQuestions(false);
    }
  };

  const handleSubmitAnswer = async () => {
    if (!userAnswer.trim()) {
      toast.error("Please write your answer before submitting.");
      return;
    }

    setSubmittingAnswer(true);
    try {
      const gradeRes = await apiFetch<FeedbackResult>("/api/interview/grade", {
        method: "POST",
        body: JSON.stringify({
          question: questions[currentIdx],
          answer: userAnswer.trim()
        })
      });

      setFeedback(gradeRes);
      setAllScores((prev) => [...prev, gradeRes.score]);
      toast.success(`Graded successfully! Score: ${gradeRes.score}/100`);
    } catch (err: any) {
      toast.error(err.message || "Grading request failed.");
    } finally {
      setSubmittingAnswer(false);
    }
  };

  const handleNext = () => {
    if (currentIdx + 1 < questions.length) {
      setCurrentIdx((prev) => prev + 1);
      setUserAnswer("");
      setFeedback(null);
    } else {
      setCompleted(true);
    }
  };

  const handleReset = () => {
    setInterviewStarted(false);
    setQuestions([]);
    setCurrentIdx(0);
    setUserAnswer("");
    setFeedback(null);
    setAllScores([]);
    setCompleted(false);
  };

  const averageScore = allScores.length > 0 
    ? Math.round(allScores.reduce((a, b) => a + b, 0) / allScores.length) 
    : 0;

  return (
    <div className="min-h-screen bg-transparent text-slate-900 dark:text-white flex flex-col items-center">
      <Navbar />

      <div className="w-full max-w-5xl px-4 pt-24 pb-16 space-y-8 animate-fade-in">
        <PageHero
          badge="AI STAR Method Coach"
          title="AI Mock Interview Practice"
          subtitle="Challenge yourself with role-specific technical and behavioral questions with instant STAR compliance evaluations."
          breadcrumbs={[
            { label: "Home", href: "/" },
            { label: "Practice Suite", href: "/interview" },
            { label: "Mock Interview" },
          ]}
        />

        {/* Setup Screen */}
        {!interviewStarted && (
          <div className="p-6 rounded-3xl bg-slate-900/40 backdrop-blur-md border border-slate-800 space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-200">Set Up Mock Interview Session</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Our AI hiring manager will analyze your resume against this job description to generate 5 targeted questions.
                </p>
              </div>
            </div>

            <form onSubmit={handleStartInterview} className="space-y-4">
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Target Role / Job Title</label>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] text-slate-500">Presets:</span>
                    <button
                      type="button"
                      onClick={() => {
                        setJobTitle("Full-Stack Engineer");
                        setJdText("We are seeking a Senior Full-Stack Engineer skilled in TypeScript, Next.js, Python/FastAPI, and PostgreSQL. You will design scalable web applications, implement AI workflows, optimize API response times, and collaborate in an agile cross-functional engineering team.");
                      }}
                      className="text-[10px] px-2 py-0.5 rounded-md bg-teal-500/10 text-teal-400 hover:bg-teal-500/20 transition font-medium"
                    >
                      Full-Stack
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setJobTitle("Frontend React Developer");
                        setJdText("Looking for a Frontend Developer proficient in React, Next.js, TailwindCSS, responsive UI design, and web performance optimization. Experience with TypeScript, animations, and state management is highly valued.");
                      }}
                      className="text-[10px] px-2 py-0.5 rounded-md bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 transition font-medium"
                    >
                      Frontend
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setJobTitle("Backend Python Engineer");
                        setJdText("Seeking a Backend Software Engineer with deep expertise in Python, FastAPI, PostgreSQL, Redis, Docker, and REST/GraphQL API design. Must understand microservices, async concurrency, and automated testing.");
                      }}
                      className="text-[10px] px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 transition font-medium"
                    >
                      Backend
                    </button>
                  </div>
                </div>

                <input
                  type="text"
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-xs focus:border-teal-500 outline-none text-slate-200"
                  placeholder="e.g. Full-Stack Developer"
                  required
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Target Job Description (JD)</label>
                <textarea
                  value={jdText}
                  onChange={(e) => setJdText(e.target.value)}
                  rows={5}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-xs focus:border-teal-500 outline-none text-slate-200 resize-none font-mono"
                  placeholder="Paste target job requirements and qualifications here or select a preset above..."
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loadingQuestions || !jdText.trim()}
                className="w-full py-3.5 px-4 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-700 hover:to-emerald-700 text-white text-xs font-bold transition disabled:opacity-50 flex items-center justify-center gap-2 shadow-lg shadow-teal-500/20 active:scale-[0.99]"
              >
                {loadingQuestions ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Generating 5 custom questions...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" /> Start AI Interview Session
                  </>
                )}
              </button>
            </form>
          </div>
        )}

        {/* Active Interview Panel */}
        {interviewStarted && !completed && (
          <div className="grid md:grid-cols-5 gap-6 items-start">
            {/* Left Question Side */}
            <div className="md:col-span-3 p-6 rounded-3xl bg-slate-900/40 backdrop-blur-md border border-slate-800 space-y-4">
              <div className="flex justify-between items-center text-xs font-bold text-slate-400">
                <span className="uppercase tracking-wider text-teal-400">Question {currentIdx + 1} of {questions.length}</span>
                <span>Role: {jobTitle}</span>
              </div>
              
              <h3 className="text-sm font-bold text-slate-200 leading-relaxed bg-slate-950/50 p-4 rounded-2xl border border-slate-800">
                {questions[currentIdx]}
              </h3>

              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Your Response (STAR Method)</label>
                  {!feedback && (
                    <button
                      type="button"
                      onClick={() => setUserAnswer("In my previous project, we observed high latency spikes on our main API under peak traffic. As the lead developer, my task was to reduce response latency below 200ms without increasing infrastructure costs. I implemented Redis caching with invalidation hooks, optimized our SQL indexing, and refactored synchronous endpoints to asynchronous FastAPI workers. As a result, our p99 response times dropped by 65%, database CPU usage decreased by 40%, and we maintained 99.99% uptime during product launch.")}
                      className="text-[10px] text-teal-400 hover:text-teal-300 transition underline underline-offset-2"
                    >
                      Fill Example STAR Answer
                    </button>
                  )}
                </div>
                <textarea
                  value={userAnswer}
                  onChange={(e) => setUserAnswer(e.target.value)}
                  disabled={feedback !== null || submittingAnswer}
                  rows={7}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-xs focus:border-teal-500 outline-none text-slate-200 resize-none leading-relaxed"
                  placeholder="Structure your answer using the STAR method: describe the Situation, Task, Action, and Result..."
                />
              </div>

              <div className="flex justify-between items-center pt-2">
                {feedback === null ? (
                  <button
                    onClick={handleSubmitAnswer}
                    disabled={submittingAnswer || !userAnswer.trim()}
                    className="py-2.5 px-6 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold transition disabled:opacity-50 flex items-center gap-1.5 shadow-lg shadow-teal-500/20"
                  >
                    {submittingAnswer && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                    Submit Response for AI Grading
                  </button>
                ) : (
                  <button
                    onClick={handleNext}
                    className="py-2.5 px-6 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition flex items-center gap-1.5 shadow-lg shadow-emerald-500/20"
                  >
                    Next Question <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                )}

                <button
                  onClick={handleReset}
                  className="text-xs text-slate-500 hover:text-slate-400 flex items-center gap-1"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Start Over
                </button>
              </div>
            </div>

            {/* Right Grading Feedback Side */}
            <div className="md:col-span-2 space-y-4">
              {feedback === null ? (
                <div className="p-6 rounded-3xl bg-slate-900/20 border border-slate-800 text-center py-16 text-slate-400 space-y-2">
                  <MessageSquare className="w-8 h-8 text-slate-600 mx-auto" />
                  <p className="text-xs font-bold">Awaiting Submission</p>
                  <p className="text-[10px] text-slate-500 leading-normal max-w-xs mx-auto">
                    Type out your response and submit it. Gemini will grade your answer and output STAR method feedback here.
                  </p>
                </div>
              ) : (
                <div className="p-6 rounded-3xl bg-slate-900/40 backdrop-blur-md border border-slate-800 space-y-4 animate-fade-in">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Gemini Evaluation</h4>
                    <div className="flex items-center gap-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded text-[10px] font-extrabold">
                      <Award className="w-3.5 h-3.5" /> {feedback.score}/100
                    </div>
                  </div>

                  <div className="space-y-3 pt-2 border-t border-slate-800/60">
                    <div className="space-y-1">
                      <div className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">STAR Compliance</div>
                      <p className="text-xs text-slate-300 leading-relaxed">{feedback.star_compliance}</p>
                    </div>

                    <div className="space-y-1">
                      <div className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Technical Depth</div>
                      <p className="text-xs text-slate-300 leading-relaxed">{feedback.tech_depth}</p>
                    </div>

                    <div className="space-y-1">
                      <div className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Communication Clarity</div>
                      <p className="text-xs text-slate-300 leading-relaxed">{feedback.communication_clarity}</p>
                    </div>

                    {feedback.constructive_tips.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Constructive Tips</div>
                        <ul className="space-y-1">
                          {feedback.constructive_tips.map((tip, idx) => (
                            <li key={idx} className="text-[11px] text-amber-400/80 leading-normal flex items-start gap-1">
                              <span>•</span>
                              <span>{tip}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Final Report Screen */}
        {completed && (
          <div className="p-8 rounded-3xl bg-slate-900/40 backdrop-blur-md border border-slate-800 text-center space-y-6 max-w-lg mx-auto">
            <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto" />
            <div className="space-y-2">
              <h2 className="text-xl font-black text-slate-100">Session Completed!</h2>
              <p className="text-xs text-slate-400">Excellent effort! You have completed all 5 mock interview questions.</p>
            </div>

            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 flex items-center justify-between">
              <span className="text-xs text-slate-400">Average Performance Score</span>
              <span className="text-2xl font-black text-teal-400">{averageScore}%</span>
            </div>

            <button
              onClick={handleReset}
              className="w-full py-3 px-4 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold transition flex items-center justify-center gap-1.5"
            >
              <RefreshCw className="w-4 h-4" /> Start New Session
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

