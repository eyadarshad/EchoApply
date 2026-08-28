"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Cpu, Sun, Moon, Volume2, VolumeX, FileText, Mic, BarChart3, 
  Settings, LogOut, LogIn, UserPlus, Sparkles, ChevronRight, 
  ShieldCheck, ArrowUpRight 
} from "lucide-react";
import { useTheme } from "./ThemeContext";
import { audioEngine } from "../app/AudioEngine";

interface NavbarProps {
  user_id?: string | null;
  email?: string | null;
  onLogout?: () => void;
  onOpenAuth?: (reason: string, mode: "login" | "register") => void;
  onOpenCoverLetter?: () => void;
  onOpenInterviewPrep?: () => void;
  onOpenAnalytics?: () => void;
}

export default function Navbar({
  user_id = null,
  email = null,
  onLogout,
  onOpenAuth,
  onOpenCoverLetter,
  onOpenInterviewPrep,
  onOpenAnalytics,
}: NavbarProps = {}) {
  const { theme, toggleTheme } = useTheme();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isMuted, setIsMuted] = useState(true);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsMenuOpen(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsMenuOpen(false);
      }
    };

    if (isMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isMenuOpen]);

  const handleToggleAudio = () => {
    if (isMuted) {
      audioEngine.start();
      setIsMuted(false);
    } else {
      audioEngine.stop();
      setIsMuted(true);
    }
  };

  const initials = email ? email.substring(0, 2).toUpperCase() : "AI";

  return (
    <header className="w-full max-w-4xl flex justify-between items-center py-2.5 px-4 md:px-6 rounded-2xl glass-card z-30 mb-8 relative border border-slate-200/50 dark:border-slate-800/80 shadow-lg shadow-black/5 backdrop-blur-xl shrink-0">
      {/* Brand Logo & Title */}
      <div className="flex items-center gap-2.5 shrink-0">
        <a href="/" className="flex items-center gap-2.5 group shrink-0">
          <div className="relative flex items-center justify-center group-hover:scale-105 transition-transform shrink-0">
            <img src="/logo.png" alt="Echo Apply Logo" className="w-7 h-7 object-contain dark:invert transition-all" />
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-500 animate-pulse ring-2 ring-white dark:ring-slate-950" />
          </div>
          <span className="font-extrabold tracking-tight text-slate-800 dark:text-slate-100 text-sm whitespace-nowrap inline-flex items-center gap-1.5">
            Echo Apply <span className="text-teal-600 dark:text-teal-400 font-mono text-xs font-bold">AI</span>
          </span>
        </a>
      </div>

      {/* Desktop Quick Nav Suite */}
      <nav className="hidden md:flex items-center gap-1 text-xs font-semibold text-slate-600 dark:text-slate-300 shrink-0">
        <a
          href="/audit/cv"
          className="px-2.5 py-1.5 rounded-xl whitespace-nowrap hover:bg-teal-500/10 hover:text-teal-600 dark:hover:text-teal-400 transition-colors"
        >
          CV Audit
        </a>
        <a
          href="/audit/linkedin"
          className="px-2.5 py-1.5 rounded-xl whitespace-nowrap hover:bg-sky-500/10 hover:text-sky-600 dark:hover:text-sky-400 transition-colors"
        >
          LinkedIn Audit
        </a>
        <a
          href="/tailor"
          className="px-2.5 py-1.5 rounded-xl whitespace-nowrap hover:bg-emerald-500/10 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
        >
          Tailor
        </a>
        <a
          href="/cover-letter"
          className="px-2.5 py-1.5 rounded-xl whitespace-nowrap hover:bg-teal-500/10 hover:text-teal-600 dark:hover:text-teal-400 transition-colors"
        >
          Cover Letter
        </a>
        <a
          href="/interview"
          className="px-2.5 py-1.5 rounded-xl whitespace-nowrap hover:bg-indigo-500/10 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
        >
          Interview
        </a>
      </nav>

      {/* Right Controls & Hamburger Hub */}
      <div className="flex items-center gap-2 shrink-0 relative" ref={menuRef}>
        {user_id && (
          <div className="hidden xl:inline-flex items-center gap-1.5 py-1 px-2.5 rounded-full bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/50 text-[11px] font-medium text-slate-600 dark:text-slate-300">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="truncate max-w-[110px]">{email}</span>
          </div>
        )}
        {/* Quick Audio Synthesizer Mini Toggle */}
        <motion.button
          onClick={handleToggleAudio}
          whileHover={{ scale: 1.08 }}
          whileTap={{ scale: 0.92 }}
          className={`p-2 rounded-xl border transition-all duration-200 flex items-center justify-center gap-1 ${
            !isMuted
              ? "bg-teal-500/20 border-teal-500/40 text-teal-600 dark:text-teal-400 shadow-sm"
              : "bg-slate-100 dark:bg-slate-800/40 border-slate-200 dark:border-slate-700/40 text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
          }`}
          title={isMuted ? "Unmute Ambient Pad" : "Mute Ambient Pad"}
          aria-label="Toggle Ambient Audio"
        >
          {!isMuted ? (
            <>
              <Volume2 className="w-4 h-4" />
              <div className="flex gap-0.5 items-end h-2.5 px-0.5">
                <span className="w-0.5 bg-teal-600 dark:bg-teal-400 animate-audio-bar-1 rounded-full h-full" />
                <span className="w-0.5 bg-teal-600 dark:bg-teal-400 animate-audio-bar-2 rounded-full h-full" style={{ animationDelay: "0.15s" }} />
                <span className="w-0.5 bg-teal-600 dark:bg-teal-400 animate-audio-bar-3 rounded-full h-full" style={{ animationDelay: "0.3s" }} />
              </div>
            </>
          ) : (
            <VolumeX className="w-4 h-4" />
          )}
        </motion.button>

        {/* Quick Theme Switcher */}
        <motion.button
          onClick={toggleTheme}
          whileHover={{ scale: 1.08, rotate: 15 }}
          whileTap={{ scale: 0.92 }}
          className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800/40 hover:bg-slate-200/60 dark:hover:bg-slate-700/50 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700/40 shadow-sm transition"
          title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
          aria-label="Toggle Theme"
        >
          {theme === "dark" ? (
            <Sun className="w-4 h-4 text-amber-400" />
          ) : (
            <Moon className="w-4 h-4 text-teal-600" />
          )}
        </motion.button>

        {/* Master Animated Morphing Hamburger Button */}
        <motion.button
          onClick={() => setIsMenuOpen(!isMenuOpen)}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className={`p-2.5 rounded-xl border transition-all flex items-center justify-center gap-2 ${
            isMenuOpen
              ? "bg-teal-600 text-white border-teal-500 shadow-md shadow-teal-500/20"
              : "bg-slate-100 dark:bg-slate-800/60 hover:bg-slate-200/80 dark:hover:bg-slate-700/70 text-slate-800 dark:text-slate-200 border-slate-200 dark:border-slate-700/60"
          }`}
          aria-label={isMenuOpen ? "Close navigation menu" : "Open navigation menu"}
          aria-expanded={isMenuOpen}
        >
          <div className="w-4 h-4 flex flex-col justify-between items-center relative">
            <motion.span
              animate={isMenuOpen ? { rotate: 45, y: 6.5 } : { rotate: 0, y: 0 }}
              transition={{ duration: 0.22, ease: "easeInOut" }}
              className={`w-4 h-0.5 rounded-full block ${isMenuOpen ? "bg-white" : "bg-slate-800 dark:bg-slate-200"}`}
            />
            <motion.span
              animate={isMenuOpen ? { opacity: 0, scale: 0.5 } : { opacity: 1, scale: 1 }}
              transition={{ duration: 0.15 }}
              className={`w-4 h-0.5 rounded-full block ${isMenuOpen ? "bg-white" : "bg-slate-800 dark:bg-slate-200"}`}
            />
            <motion.span
              animate={isMenuOpen ? { rotate: -45, y: -6.5 } : { rotate: 0, y: 0 }}
              transition={{ duration: 0.22, ease: "easeInOut" }}
              className={`w-4 h-0.5 rounded-full block ${isMenuOpen ? "bg-white" : "bg-slate-800 dark:bg-slate-200"}`}
            />
          </div>
          <span className="text-xs font-bold hidden sm:inline-block">Menu</span>
        </motion.button>

        {/* ═══════════════════════════════════════════════════════ */}
        {/* Floating Command Center Flyout Drawer */}
        {/* ═══════════════════════════════════════════════════════ */}
        <AnimatePresence>
          {isMenuOpen && (
            <motion.div
              initial={{ opacity: 0, y: 12, scale: 0.96, transformOrigin: "top right" }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.96 }}
              transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
              className="absolute right-0 top-14 w-80 sm:w-88 rounded-3xl border border-slate-200/80 dark:border-slate-800/90 bg-white/95 dark:bg-slate-950/95 backdrop-blur-2xl text-slate-800 dark:text-slate-100 shadow-2xl shadow-black/20 p-4 z-50 space-y-4"
            >
              {/* Header: Candidate Identity Strip */}
              {user_id ? (
                <div className="p-3.5 rounded-2xl bg-gradient-to-br from-teal-500/10 via-slate-100/50 dark:via-slate-900/40 to-indigo-500/10 border border-teal-500/20 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500 to-indigo-600 flex items-center justify-center font-bold text-white text-sm shadow-md">
                      {initials}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-bold text-slate-900 dark:text-white truncate max-w-[140px]">
                          {email?.split("@")[0] || "Candidate"}
                        </span>
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      </div>
                      <p className="text-[10px] text-slate-500 dark:text-slate-400 font-mono truncate max-w-[150px]">
                        {email}
                      </p>
                    </div>
                  </div>
                  <span className="px-2 py-0.5 rounded-md bg-teal-500/20 text-teal-600 dark:text-teal-300 text-[10px] font-extrabold tracking-wider border border-teal-500/30 uppercase">
                    PRO
                  </span>
                </div>
              ) : (
                <div className="p-3.5 rounded-2xl bg-slate-100/80 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                  <div>
                    <h4 className="text-xs font-bold text-slate-900 dark:text-white">Guest Candidate</h4>
                    <p className="text-[10px] text-slate-500 dark:text-slate-400">Sign in to save and tailor resumes</p>
                  </div>
                  <button
                    onClick={() => {
                      setIsMenuOpen(false);
                      onOpenAuth?.("access full career hub features", "login");
                    }}
                    className="px-3 py-1.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-xs font-bold transition shadow-sm"
                  >
                    Sign In
                  </button>
                </div>
              )}

              {/* Section 1: AI Career Tools & Generators */}
              {/* Section 1: Audit & Discovery Tools */}
              <div className="space-y-1.5">
                <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider px-2">
                  Audit &amp; Recruiter Score
                </div>

                {/* CV Audit */}
                <a
                  href="/audit/cv"
                  onClick={() => setIsMenuOpen(false)}
                  className="w-full flex items-center justify-between p-2.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors group text-left"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-teal-500/10 text-teal-600 dark:text-teal-400 group-hover:scale-105 transition-transform">
                      <FileText className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-800 dark:text-slate-200 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                        25-Criteria CV Audit
                      </div>
                      <p className="text-[10px] text-slate-500 dark:text-slate-400">
                        ATS score, bullet impact &amp; top 3 fixes
                      </p>
                    </div>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:translate-x-0.5 transition-transform" />
                </a>

                {/* LinkedIn Profile Audit */}
                <a
                  href="/audit/linkedin"
                  onClick={() => setIsMenuOpen(false)}
                  className="w-full flex items-center justify-between p-2.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors group text-left"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-sky-500/10 text-sky-600 dark:text-sky-400 group-hover:scale-105 transition-transform">
                      <Sparkles className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-800 dark:text-slate-200 group-hover:text-sky-600 dark:group-hover:text-sky-400 transition-colors">
                        LinkedIn Profile Audit
                      </div>
                      <p className="text-[10px] text-slate-500 dark:text-slate-400">
                        Recruiter SEO &amp; 3 headline formulas
                      </p>
                    </div>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:translate-x-0.5 transition-transform" />
                </a>
              </div>

              {/* Section 2: AI Application Studio */}
              <div className="space-y-1.5 pt-2 border-t border-slate-200/60 dark:border-slate-800/60">
                <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider px-2">
                  Application Studio
                </div>

                {/* Resume Tailor */}
                <a
                  href="/tailor"
                  onClick={() => setIsMenuOpen(false)}
                  className="w-full flex items-center justify-between p-2.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors group text-left"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 group-hover:scale-105 transition-transform">
                      <Sparkles className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-800 dark:text-slate-200 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                        AI Resume Tailoring
                      </div>
                      <p className="text-[10px] text-slate-500 dark:text-slate-400">
                        7-stage JD alignment &amp; gap audit
                      </p>
                    </div>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:translate-x-0.5 transition-transform" />
                </a>

                {/* Cover Letter Generator */}
                <a
                  href="/cover-letter"
                  onClick={() => setIsMenuOpen(false)}
                  className="w-full flex items-center justify-between p-2.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors group text-left"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-teal-500/10 text-teal-600 dark:text-teal-400 group-hover:scale-105 transition-transform">
                      <FileText className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-800 dark:text-slate-200 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                        Cover Letter Generator
                      </div>
                      <p className="text-[10px] text-slate-500 dark:text-slate-400">
                        Tailored psychological outreach letters
                      </p>
                    </div>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:translate-x-0.5 transition-transform" />
                </a>

                {/* AI Interview Prep */}
                <a
                  href="/interview"
                  onClick={() => setIsMenuOpen(false)}
                  className="w-full flex items-center justify-between p-2.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors group text-left"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 group-hover:scale-105 transition-transform">
                      <Mic className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-800 dark:text-slate-200 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                        AI Interview Simulator
                      </div>
                      <p className="text-[10px] text-slate-500 dark:text-slate-400">
                        Real-time role-specific Q&amp;A drills
                      </p>
                    </div>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:translate-x-0.5 transition-transform" />
                </a>

                {/* Job & Match Analytics */}
                {onOpenAnalytics && (
                  <button
                    onClick={() => {
                      setIsMenuOpen(false);
                      if (!user_id && onOpenAuth) {
                        onOpenAuth("view your application conversion metrics", "login");
                      } else {
                        onOpenAnalytics();
                      }
                    }}
                    className="w-full flex items-center justify-between p-2.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors group text-left"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 group-hover:scale-105 transition-transform">
                        <BarChart3 className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="text-xs font-bold text-slate-800 dark:text-slate-200 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                          Career Analytics
                        </div>
                        <p className="text-[10px] text-slate-500 dark:text-slate-400">
                          Conversion rates &amp; match telemetry
                        </p>
                      </div>
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:translate-x-0.5 transition-transform" />
                  </button>
                )}
              </div>

              {/* Section 2: Account & System Settings */}
              <div className="pt-2 border-t border-slate-200/80 dark:border-slate-800/80 space-y-1">
                <a
                  href="/settings"
                  onClick={(e) => {
                    if (!user_id) {
                      e.preventDefault();
                      setIsMenuOpen(false);
                      onOpenAuth?.("access account & API settings", "login");
                    }
                  }}
                  className="w-full flex items-center justify-between p-2.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-slate-200/60 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                      <Settings className="w-4 h-4" />
                    </div>
                    <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Account &amp; Security Settings
                    </span>
                  </div>
                  <ArrowUpRight className="w-3.5 h-3.5 text-slate-400" />
                </a>

                {/* Sign Out / Sign In Action */}
                {user_id ? (
                  <button
                    onClick={() => {
                      setIsMenuOpen(false);
                      onLogout?.();
                    }}
                    className="w-full flex items-center gap-3 p-2.5 rounded-xl text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 transition-colors text-left"
                  >
                    <div className="p-2 rounded-lg bg-rose-500/10 text-rose-600 dark:text-rose-400">
                      <LogOut className="w-4 h-4" />
                    </div>
                    <span className="text-xs font-bold">Sign Out</span>
                  </button>
                ) : (
                  <div className="grid grid-cols-2 gap-2 pt-1">
                    <button
                      onClick={() => {
                        setIsMenuOpen(false);
                        onOpenAuth?.("", "login");
                      }}
                      className="py-2 px-3 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-800 dark:text-slate-200 font-bold text-xs transition text-center"
                    >
                      Sign In
                    </button>
                    <button
                      onClick={() => {
                        setIsMenuOpen(false);
                        onOpenAuth?.("", "register");
                      }}
                      className="py-2 px-3 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-bold text-xs transition text-center shadow-md shadow-teal-600/20"
                    >
                      Register
                    </button>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </header>
  );
}
