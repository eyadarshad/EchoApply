"use client";

import React, { useState } from "react";

export default function Home() {
  const [healthStatus, setHealthStatus] = useState<string | null>(null);
  const [echoInput, setEchoInput] = useState("");
  const [echoResult, setEchoResult] = useState<string | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [loadingEcho, setLoadingEcho] = useState(false);

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
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6 md:p-24 selection:bg-indigo-500 selection:text-white">
      {/* Background decoration */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-indigo-950/30 via-slate-950 to-slate-950 -z-10" />

      <div className="max-w-3xl w-full text-center space-y-8">
        <div className="space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-400 text-xs font-semibold uppercase tracking-wider">
            Phase 0 Scaffold Active
          </div>
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-indigo-400 bg-clip-text text-transparent">
            AI Resume & Smart Apply
          </h1>
          <p className="text-slate-400 text-lg md:text-xl max-w-xl mx-auto font-light">
            An intelligent tailoring pipeline, jobs aggregator, and semi-automated application engine.
          </p>
        </div>

        {/* API Verification Grid */}
        <div className="grid md:grid-cols-2 gap-6 mt-12 text-left">
          {/* Health Check Card */}
          <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/40 backdrop-blur-xl hover:border-slate-700 transition duration-300 flex flex-col justify-between space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-indigo-300">Backend Health Check</h3>
              <p className="text-sm text-slate-400 mt-1">
                Verify database connectivity, services status, and schema integrity.
              </p>
            </div>
            <div className="space-y-4">
              <button
                onClick={checkHealth}
                disabled={loadingHealth}
                className="w-full py-2.5 px-4 rounded-xl font-medium text-sm text-center border border-indigo-500/50 bg-indigo-500/10 hover:bg-indigo-500/20 active:bg-indigo-500/30 text-indigo-300 disabled:opacity-50 transition duration-200"
              >
                {loadingHealth ? "Checking..." : "Trigger Health Check"}
              </button>
              {healthStatus && (
                <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-emerald-400 overflow-x-auto">
                  {healthStatus}
                </pre>
              )}
            </div>
          </div>

          {/* Request Echo Card */}
          <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/40 backdrop-blur-xl hover:border-slate-700 transition duration-300 flex flex-col justify-between space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-indigo-300">HTTP API Echo Test</h3>
              <p className="text-sm text-slate-400 mt-1">
                Test request payload serialization and typed contract structure.
              </p>
            </div>
            <form onSubmit={checkEcho} className="space-y-4">
              <input
                type="text"
                value={echoInput}
                onChange={(e) => setEchoInput(e.target.value)}
                placeholder="Enter test message..."
                className="w-full px-4 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm focus:border-indigo-500 focus:outline-none transition duration-200"
              />
              <button
                type="submit"
                disabled={loadingEcho}
                className="w-full py-2.5 px-4 rounded-xl font-medium text-sm text-center bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white disabled:opacity-50 transition duration-200"
              >
                {loadingEcho ? "Sending..." : "Test Echo POST"}
              </button>
              {echoResult && (
                <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-emerald-400 overflow-x-auto">
                  {echoResult}
                </pre>
              )}
            </form>
          </div>
        </div>
      </div>
    </main>
  );
}
