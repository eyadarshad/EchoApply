"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { gsap } from "gsap";
import { Sun, Moon, Cpu, Volume2, VolumeX, Loader2, FileText, Mic, Briefcase, BarChart3, Sparkles } from "lucide-react";
import { useTheme } from "../components/ThemeContext";
import ResumeUpload from "../components/ResumeUpload";
import GuidedTour from "../components/GuidedTour";
import { audioEngine } from "./AudioEngine";
import { useAuth } from "../context/AuthContext";
import AuthPortal from "../components/AuthPortal";
import ScrollReveal from "../components/ScrollReveal";
import CoverLetterPanel from "../components/CoverLetterPanel";
import ChatBot from "../components/ChatBot";
import OnboardingChecklist from "../components/OnboardingChecklist";
import AnalyticsDashboard from "../components/AnalyticsDashboard";
import PretextFluidText from "../components/PretextFluidText";
import Navbar from "../components/Navbar";

export default function Home() {
  const { user_id, email, logout, loading } = useAuth();

  // Auth modal interceptor states
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authModalMode, setAuthModalMode] = useState<'login' | 'register'>('login');
  const [authPromptReason, setAuthPromptReason] = useState("");
  const [showCoverLetter, setShowCoverLetter] = useState(false);
  const [showInterviewPrep, setShowInterviewPrep] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [hasResume, setHasResume] = useState(false);

  useEffect(() => {
    // GSAP Staggered entry animation timeline
    const tl = gsap.timeline({ defaults: { ease: "power4.out", duration: 1.0 } });
    
    tl.fromTo(".hero-badge", { opacity: 0, y: -30 }, { opacity: 1, y: 0 })
      .fromTo(".hero-title", { opacity: 0, y: 30 }, { opacity: 1, y: 0 }, "-=0.7")
      .fromTo(".hero-subtitle", { opacity: 0, y: 20 }, { opacity: 1, y: 0 }, "-=0.7")
      .fromTo(".guided-tour-container", { opacity: 0, y: 20 }, { opacity: 1, y: 0 }, "-=0.6")
      .fromTo(".main-card-container", { opacity: 0, y: 40, scale: 0.98 }, { opacity: 1, y: 0, scale: 1 }, "-=0.6");

    return () => {
      // Ensure audio stops if component unmounts
      audioEngine.stop();
    };
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-teal-500 animate-spin" />
          <p className="text-xs text-slate-400 font-semibold uppercase tracking-widest">Checking Authentication...</p>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen w-full flex flex-col items-center p-6 md:p-12 selection:bg-teal-500 selection:text-white relative">
      {/* Decorative Blur Orbs */}
      <div className="accent-glow-spot top-12 left-12 animate-pulse" style={{ animationDuration: "12s" }} />
      <div className="accent-glow-spot bottom-12 right-12 animate-pulse" style={{ animationDuration: "8s" }} />

      {/* Modern Executive Clean Navbar & Flyout Hub */}
      <Navbar
        user_id={user_id}
        email={email}
        onLogout={logout}
        onOpenAuth={(reason, mode) => {
          setAuthPromptReason(reason);
          setAuthModalMode(mode);
          setShowAuthModal(true);
        }}
        onOpenCoverLetter={() => setShowCoverLetter(true)}
        onOpenInterviewPrep={() => setShowInterviewPrep(true)}
        onOpenAnalytics={() => setShowAnalytics(true)}
      />

      <div className="max-w-4xl w-full text-center space-y-8">
        <ScrollReveal direction="up" duration={0.8}>
          <div className="space-y-4">
            <div className="hero-badge inline-flex items-center gap-2 px-3 py-1 rounded-full border border-teal-500/20 bg-teal-500/10 text-teal-600 dark:text-teal-400 text-xs font-semibold uppercase tracking-wider">
              AI-Powered Career Hub
            </div>
            <h1 className="hero-title text-4xl md:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white">
              Echo Apply
            </h1>
            <div className="hero-subtitle max-w-xl mx-auto">
              <PretextFluidText
                text="Upload your resume PDF to instantly extract structured profile details, discover highly matched job opportunities, and tailor documents matching ATS keywords."
                className="text-slate-600 dark:text-slate-400 text-sm md:text-base font-light leading-relaxed text-center"
                lineHeight={26}
              />
            </div>
          </div>
        </ScrollReveal>

        {/* Guided Walkthrough Tour */}
        <ScrollReveal direction="up" delay={0.2}>
          <div className="guided-tour-container mt-6">
            <GuidedTour />
          </div>
        </ScrollReveal>

        {/* Feature Launchpad Suite */}
        <ScrollReveal direction="up" delay={0.25}>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-8">
            {/* CV Audit */}
            <a
              href="/audit/cv"
              className="p-6 rounded-3xl glass-card border border-teal-500/20 hover:border-teal-500/50 hover:shadow-xl hover:shadow-teal-500/10 hover:-translate-y-1 transition-all group block relative overflow-hidden"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 rounded-2xl bg-teal-500/10 text-teal-600 dark:text-teal-400 flex items-center justify-center border border-teal-500/20 group-hover:scale-110 transition-transform">
                  <FileText className="w-6 h-6" />
                </div>
                <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-md bg-teal-500/15 text-teal-600 dark:text-teal-300 border border-teal-500/30">
                  25 Criteria
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-800 dark:text-slate-100 mb-1 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                25-Criteria CV Audit
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                Scan ATS readability, quantified bullet impact, and get your top 3 prioritized fixes.
              </p>
            </a>

            {/* LinkedIn Profile Audit */}
            <a
              href="/audit/linkedin"
              className="p-6 rounded-3xl glass-card border border-sky-500/20 hover:border-sky-500/50 hover:shadow-xl hover:shadow-sky-500/10 hover:-translate-y-1 transition-all group block relative overflow-hidden"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 rounded-2xl bg-sky-500/10 text-sky-600 dark:text-sky-400 flex items-center justify-center border border-sky-500/20 group-hover:scale-110 transition-transform">
                  <Sparkles className="w-6 h-6" />
                </div>
                <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-md bg-sky-500/15 text-sky-600 dark:text-sky-300 border border-sky-500/30">
                  Recruiter SEO
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-800 dark:text-slate-100 mb-1 group-hover:text-sky-600 dark:group-hover:text-sky-400 transition-colors">
                LinkedIn Profile Audit
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                27 search checks, keyword positioning, and 3 AI-optimized headline formulas.
              </p>
            </a>

            {/* Resume Tailor */}
            <a
              href="/tailor"
              className="p-6 rounded-3xl glass-card border border-emerald-500/20 hover:border-emerald-500/50 hover:shadow-xl hover:shadow-emerald-500/10 hover:-translate-y-1 transition-all group block relative overflow-hidden"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center border border-emerald-500/20 group-hover:scale-110 transition-transform">
                  <Briefcase className="w-6 h-6" />
                </div>
                <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-md bg-emerald-500/15 text-emerald-600 dark:text-emerald-300 border border-emerald-500/30">
                  7-Stage AI
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-800 dark:text-slate-100 mb-1 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                AI Resume Tailoring
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                Rewrite bullet points against exact JD keywords with 100% truthfulness verification.
              </p>
            </a>

            {/* Cover Letter */}
            <a
              href="/cover-letter"
              className="p-6 rounded-3xl glass-card border border-teal-500/20 hover:border-teal-500/50 hover:shadow-xl hover:shadow-teal-500/10 hover:-translate-y-1 transition-all group block relative overflow-hidden"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 rounded-2xl bg-teal-500/10 text-teal-600 dark:text-teal-400 flex items-center justify-center border border-teal-500/20 group-hover:scale-110 transition-transform">
                  <FileText className="w-6 h-6" />
                </div>
                <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-md bg-teal-500/15 text-teal-600 dark:text-teal-300 border border-teal-500/30">
                  Studio
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-800 dark:text-slate-100 mb-1 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                Cover Letter Studio
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                Generate high-converting letters tailored to company ethos and your key career wins.
              </p>
            </a>

            {/* AI Mock Interview */}
            <a
              href="/interview"
              className="p-6 rounded-3xl glass-card border border-indigo-500/20 hover:border-indigo-500/50 hover:shadow-xl hover:shadow-indigo-500/10 hover:-translate-y-1 transition-all group block relative overflow-hidden sm:col-span-2 lg:col-span-2"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center border border-indigo-500/20 group-hover:scale-110 transition-transform">
                  <Mic className="w-6 h-6" />
                </div>
                <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-md bg-indigo-500/15 text-indigo-600 dark:text-indigo-300 border border-indigo-500/30">
                  STAR Method Drill
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-800 dark:text-slate-100 mb-1 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                AI Mock Interview Simulator
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                Practice role-specific technical and behavioral questions with instant STAR evaluation and scoring.
              </p>
            </a>
          </div>
        </ScrollReveal>

        {/* Bouncing Scroll Down Chevron Indicator */}
        <motion.div 
          onClick={() => {
            document.getElementById("resume-workspace")?.scrollIntoView({ behavior: "smooth" });
          }}
          className="flex flex-col items-center justify-center gap-1 mt-6 cursor-pointer text-slate-400 dark:text-slate-500 hover:text-teal-600 dark:hover:text-teal-400 transition-colors duration-300 z-10 select-none"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <span className="text-[9px] uppercase font-black tracking-widest opacity-80">Scroll to Workspace</span>
          <motion.div
            animate={{ y: [0, 5, 0] }}
            transition={{ repeat: Infinity, duration: 1.6, ease: "easeInOut" }}
            className="p-1 rounded-full bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800/80 shadow"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5" className="w-3.5 h-3.5 text-teal-500">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          </motion.div>
        </motion.div>

        {/* Onboarding Checklist Guide */}
        <ScrollReveal direction="up" delay={0.28}>
          <div className="mt-8 w-full">
            <OnboardingChecklist hasResume={hasResume} />
          </div>
        </ScrollReveal>

        {/* Primary Resume Engine Intake UI */}
        <ScrollReveal direction="up" delay={0.3}>
          <div id="resume-workspace" className="main-card-container mt-10 scroll-mt-24">
            <ResumeUpload 
              userId={user_id}
              onRequireAuth={(reason) => {
                setAuthPromptReason(reason);
                setAuthModalMode("login");
                setShowAuthModal(true);
              }}
              onResumeLoaded={(loaded) => setHasResume(loaded)}
            />
          </div>
        </ScrollReveal>
      </div>

      {/* Interactive Modal Auth overlay */}
      {showAuthModal && (
        <AuthPortal
          onClose={() => setShowAuthModal(false)}
          initialMode={authModalMode}
          promptReason={authPromptReason}
        />
      )}

      {/* Cover Letter Modal Overlay */}
      {showCoverLetter && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl glass-card p-6 relative">
            <button
              onClick={() => setShowCoverLetter(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 text-lg font-bold z-10"
              aria-label="Close modal"
            >
              ✕
            </button>
            <CoverLetterPanel user_id={user_id || ""} />
          </div>
        </div>
      )}
      {/* Interview Prep Modal Overlay */}
      {showInterviewPrep && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl glass-card p-6 relative">
            <button
              onClick={() => setShowInterviewPrep(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 text-lg font-bold z-10"
              aria-label="Close modal"
            >
              ✕
            </button>
            <div className="p-4">
              <h2 className="text-xl font-bold text-slate-800 dark:text-slate-200 mb-4 flex items-center gap-2">
                <Mic className="w-5 h-5 text-teal-600" /> AI Interview Preparation
              </h2>
              <p className="text-slate-600 dark:text-slate-400 mb-6">
                Practice with AI-generated interview questions tailored to your target role and job description.
                Get instant feedback using the STAR method evaluation.
              </p>
              <a
                href="/interview"
                onClick={() => setShowInterviewPrep(false)}
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-semibold text-sm transition shadow-lg shadow-teal-600/20"
              >
                <Briefcase className="w-4 h-4" />
                Launch Interview Simulator
              </a>
            </div>
          </div>
        </div>
      )}



      {/* Analytics Modal Overlay */}
      {showAnalytics && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl glass-card p-6 relative">
            <button
              onClick={() => setShowAnalytics(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 text-lg font-bold z-10"
              aria-label="Close modal"
            >
              ✕
            </button>
            <div className="p-2">
              <AnalyticsDashboard />
            </div>
          </div>
        </div>
      )}
      {/* AI Chatbot Widget */}
      <ChatBot />
    </main>
  );
}

