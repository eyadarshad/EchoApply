"use client";

import React, { useState } from "react";
import ResumeUpload from "../components/ResumeUpload";

export default function Home() {
  const [healthStatus, setHealthStatus] = useState<string | null>(null);
  const [echoInput, setEchoInput] = useState("");
  const [echoResult, setEchoResult] = useState<string | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [loadingEcho, setLoadingEcho] = useState(false);
  const [showDiagnostics, setShowDiagnostics] = useState(false);

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
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center p-6 md:p-12 selection:bg-indigo-500 selection:text-white relative">
      {/* Radial Background Gradients */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-950/20 via-slate-950 to-slate-950 -z-10" />

      <div className="max-w-4xl w-full text-center space-y-8 mt-8">
        <div className="space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-400 text-xs font-semibold uppercase tracking-wider">
            Phase 1 Resume Core Active
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-indigo-400 bg-clip-text text-transparent">
            AI Resume & Smart Apply
          </h1>
          <p className="text-slate-400 text-base md:text-lg max-w-xl mx-auto font-light">
            Upload your resume PDF to parse it with PyMuPDF, extract structured details using Gemini, and enrich the profile via GitHub.
          </p>
        </div>

        {/* Primary Resume Engine Intake UI */}
        <div className="mt-8">
          <ResumeUpload />
        </div>

        {/* Diagnostics Collapsible Toggle */}
        <div className="pt-12 text-center">
          <button
            onClick={() => setShowDiagnostics(!showDiagnostics)}
            className="text-xs text-slate-500 hover:text-slate-300 underline font-medium transition"
          >
            {showDiagnostics ? "Hide Diagnostic Tools" : "Show Diagnostic Tools"}
          </button>
        </div>

        {/* Diagnostic Testing Area */}
        {showDiagnostics && (
          <div className="grid md:grid-cols-2 gap-6 mt-6 text-left border-t border-slate-900 pt-8 animate-fade-in">
            {/* Health Check Card */}
            <div className="p-6 rounded-2xl border border-slate-900 bg-slate-900/20 backdrop-blur-xl flex flex-col justify-between space-y-6">
              <div>
                <h3 className="text-sm font-semibold text-indigo-400">Backend Health Check</h3>
                <p className="text-xs text-slate-500 mt-1">
                  Validate connections and databases.
                </p>
              </div>
              <div className="space-y-4">
                <button
                  onClick={checkHealth}
                  disabled={loadingHealth}
                  className="w-full py-2 px-3 rounded-lg font-medium text-xs text-center border border-indigo-500/50 bg-indigo-500/10 hover:bg-indigo-500/20 active:bg-indigo-500/30 text-indigo-300 disabled:opacity-50 transition duration-200"
                >
                  {loadingHealth ? "Checking..." : "Trigger Health Check"}
                </button>
                {healthStatus && (
                  <pre className="p-3 rounded-lg bg-slate-950 border border-slate-900 text-xs font-mono text-emerald-400 overflow-x-auto">
                    {healthStatus}
                  </pre>
                )}
              </div>
            </div>

            {/* Request Echo Card */}
            <div className="p-6 rounded-2xl border border-slate-900 bg-slate-900/20 backdrop-blur-xl flex flex-col justify-between space-y-6">
              <div>
                <h3 className="text-sm font-semibold text-indigo-400">HTTP API Echo Test</h3>
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
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-900 text-xs focus:border-indigo-500 focus:outline-none transition duration-200"
                />
                <button
                  type="submit"
                  disabled={loadingEcho}
                  className="w-full py-2 px-3 rounded-lg font-medium text-xs text-center bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white disabled:opacity-50 transition duration-200"
                >
                  {loadingEcho ? "Sending..." : "Test Echo POST"}
                </button>
                {echoResult && (
                  <pre className="p-3 rounded-lg bg-slate-950 border border-slate-900 text-xs font-mono text-emerald-400 overflow-x-auto">
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
