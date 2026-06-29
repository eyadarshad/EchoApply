"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { gsap } from "gsap";
import { Sun, Moon, Cpu, RefreshCw } from "lucide-react";
import { useTheme } from "../components/ThemeContext";
import ResumeUpload from "../components/ResumeUpload";

export default function Home() {
  const { theme, toggleTheme } = useTheme();
  const [healthStatus, setHealthStatus] = useState<string | null>(null);
  const [echoInput, setEchoInput] = useState("");
  const [echoResult, setEchoResult] = useState<string | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [loadingEcho, setLoadingEcho] = useState(false);
  const [showDiagnostics, setShowDiagnostics] = useState(false);

  useEffect(() => {
    // GSAP Staggered entry animation timeline
    const tl = gsap.timeline({ defaults: { ease: "power4.out", duration: 1.0 } });
    
    tl.fromTo(".hero-badge", { opacity: 0, y: -30 }, { opacity: 1, y: 0 })
      .fromTo(".hero-title", { opacity: 0, y: 30 }, { opacity: 1, y: 0 }, "-=0.7")
      .fromTo(".hero-subtitle", { opacity: 0, y: 20 }, { opacity: 1, y: 0 }, "-=0.7")
      .fromTo(".main-card-container", { opacity: 0, y: 40, scale: 0.98 }, { opacity: 1, y: 0, scale: 1 }, "-=0.6");
  }, []);

  const checkHealth = async () => {
    setLoadingHealth(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
      const res = await fetch(`${backendUrl}/health`);
      const data = await res.json();
      setHealthStatus(JSON.stringify(data));
    } catch (err: any) {
      setHealthStatus(`Error: ${err.message}`);
    } finally {
      setLoadingHealth(false);
    }
  };

  const checkEcho = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!echoInput.trim()) return;
    setLoadingEcho(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
      const res = await fetch(`${backendUrl}/echo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: echoInput }),
      });
      const data = await res.json();
      setEchoResult(JSON.stringify(data));
    } catch (err: any) {
      setEchoResult(`Error: ${err.message}`);
    } finally {
      setLoadingEcho(false);
    }
  };

  return (
    <main className="min-h-screen flex flex-col items-center p-6 md:p-12 selection:bg-indigo-500 selection:text-white relative">
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
            All Phases Active & Verified
          </div>
          <h1 className="hero-title text-4xl md:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            AI Resume & Smart Apply
          </h1>
          <p className="hero-subtitle text-slate-600 dark:text-slate-400 text-base md:text-lg max-w-xl mx-auto font-light leading-relaxed">
            Upload your resume PDF to parse it, extract structured details using Gemini, and enrich the profile via GitHub.
          </p>
        </div>

        {/* Primary Resume Engine Intake UI */}
        <div className="main-card-container mt-8">
          <ResumeUpload />
        </div>

        {/* Diagnostics Collapsible Toggle */}
        <div className="pt-12 text-center">
          <button
            onClick={() => setShowDiagnostics(!showDiagnostics)}
            className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 underline font-medium transition"
          >
            {showDiagnostics ? "Hide Diagnostic Tools" : "Show Diagnostic Tools"}
          </button>
        </div>

        {/* Diagnostic Testing Area */}
        {showDiagnostics && (
          <div className="grid md:grid-cols-2 gap-6 mt-6 text-left border-t border-slate-200 dark:border-slate-900 pt-8 animate-fade-in">
            {/* Health Check Card */}
            <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-900 bg-white/40 dark:bg-slate-900/20 backdrop-blur-xl flex flex-col justify-between space-y-6">
              <div>
                <h3 className="text-sm font-semibold text-indigo-600 dark:text-indigo-400">Backend Health Check</h3>
                <p className="text-xs text-slate-500 mt-1">
                  Validate connections and databases.
                </p>
              </div>
              <div className="space-y-4">
                <button
                  onClick={checkHealth}
                  disabled={loadingHealth}
                  className="w-full py-2 px-3 rounded-lg font-medium text-xs text-center border border-indigo-500/50 bg-indigo-500/10 hover:bg-indigo-500/20 active:bg-indigo-500/30 text-indigo-600 dark:text-indigo-300 disabled:opacity-50 transition duration-200"
                >
                  {loadingHealth ? "Checking..." : "Trigger Health Check"}
                </button>
                {healthStatus && (
                  <pre className="p-3 rounded-lg bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-900 text-xs font-mono text-emerald-600 dark:text-emerald-400 overflow-x-auto">
                    {healthStatus}
                  </pre>
                )}
              </div>
            </div>

            {/* Request Echo Card */}
            <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-900 bg-white/40 dark:bg-slate-900/20 backdrop-blur-xl flex flex-col justify-between space-y-6">
              <div>
                <h3 className="text-sm font-semibold text-indigo-600 dark:text-indigo-400">HTTP API Echo Test</h3>
                <p className="text-xs text-slate-500 mt-1">
                  Verify typed JSON serialization.
                </p>
              </div>
              <form onSubmit={checkEcho} className="space-y-4">
                <input
                  type="text"
                  value={echoInput}
                  onChange={(e) => setEchoInput(e.target.value)}
                  placeholder="Enter message..."
                  className="w-full px-3 py-2 rounded-lg bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-900 text-xs text-slate-800 dark:text-slate-100 focus:border-indigo-500 focus:outline-none transition duration-200"
                />
                <button
                  type="submit"
                  disabled={loadingEcho}
                  className="w-full py-2 px-3 rounded-lg font-medium text-xs text-center bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white disabled:opacity-50 transition duration-200"
                >
                  {loadingEcho ? "Sending..." : "Test Echo POST"}
                </button>
                {echoResult && (
                  <pre className="p-3 rounded-lg bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-900 text-xs font-mono text-emerald-600 dark:text-emerald-400 overflow-x-auto">
                    {echoResult}
                  </pre>
                )}
              </form>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
