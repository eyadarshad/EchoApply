"use client";

import React, { useEffect } from "react";
import { motion } from "framer-motion";
import { gsap } from "gsap";
import { Sun, Moon, Cpu } from "lucide-react";
import { useTheme } from "../components/ThemeContext";
import ResumeUpload from "../components/ResumeUpload";
import GuidedTour from "../components/GuidedTour";

export default function Home() {
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    // GSAP Staggered entry animation timeline
    const tl = gsap.timeline({ defaults: { ease: "power4.out", duration: 1.0 } });
    
    tl.fromTo(".hero-badge", { opacity: 0, y: -30 }, { opacity: 1, y: 0 })
      .fromTo(".hero-title", { opacity: 0, y: 30 }, { opacity: 1, y: 0 }, "-=0.7")
      .fromTo(".hero-subtitle", { opacity: 0, y: 20 }, { opacity: 1, y: 0 }, "-=0.7")
      .fromTo(".guided-tour-container", { opacity: 0, y: 20 }, { opacity: 1, y: 0 }, "-=0.6")
      .fromTo(".main-card-container", { opacity: 0, y: 40, scale: 0.98 }, { opacity: 1, y: 0, scale: 1 }, "-=0.6");
  }, []);

  return (
    <main className="min-h-screen w-full flex flex-col items-center p-6 md:p-12 selection:bg-indigo-500 selection:text-white relative">
      {/* Decorative Blur Orbs */}
      <div className="accent-glow-spot top-12 left-12 animate-pulse" style={{ animationDuration: "12s" }} />
      <div className="accent-glow-spot bottom-12 right-12 animate-pulse" style={{ animationDuration: "8s" }} />

      {/* Floating Theme Header */}
      <header className="w-full max-w-4xl flex justify-between items-center py-4 px-6 rounded-2xl glass-card z-10 mb-8">
        <div className="flex items-center gap-2">
          <Cpu className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
          <span className="font-bold tracking-tight text-slate-800 dark:text-slate-100 text-sm">
            SmartApply AI
          </span>
        </div>
        
        <motion.button
          onClick={toggleTheme}
          whileHover={{ scale: 1.1, rotate: 15 }}
          whileTap={{ scale: 0.9 }}
          transition={{ type: "spring", stiffness: 400, damping: 15 }}
          className="p-2.5 rounded-xl bg-slate-200/50 dark:bg-slate-800/50 hover:bg-slate-300/50 dark:hover:bg-slate-700/50 text-slate-700 dark:text-slate-200 border border-slate-300/30 dark:border-slate-700/30 shadow-sm"
          aria-label="Toggle Theme"
        >
          {theme === "dark" ? (
            <Sun className="w-4.5 h-4.5 text-amber-500" />
          ) : (
            <Moon className="w-4.5 h-4.5 text-indigo-600" />
          )}
        </motion.button>
      </header>

      <div className="max-w-4xl w-full text-center space-y-8">
        <div className="space-y-4">
          <div className="hero-badge inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-500/20 bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 text-xs font-semibold uppercase tracking-wider">
            AI-Powered Career Hub
          </div>
          <h1 className="hero-title text-4xl md:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            AI Resume & Smart Apply
          </h1>
          <p className="hero-subtitle text-slate-600 dark:text-slate-400 text-sm md:text-base max-w-xl mx-auto font-light leading-relaxed">
            Upload your resume PDF to instantly extract structured profile details, discover highly matched job opportunities, and tailor documents matching ATS keywords.
          </p>
        </div>

        {/* Guided Walkthrough Tour */}
        <div className="guided-tour-container mt-6">
          <GuidedTour />
        </div>

        {/* Primary Resume Engine Intake UI */}
        <div className="main-card-container mt-8">
          <ResumeUpload />
        </div>
      </div>
    </main>
  );
}
