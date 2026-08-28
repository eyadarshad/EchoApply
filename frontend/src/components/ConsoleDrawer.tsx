"use client";

import React, { useEffect, useState, useRef } from "react";
import { X, Terminal, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { apiFetch } from "@/lib/api";

interface ConsoleDrawerProps {
  taskId: string | null;
  onClose: () => void;
  visible: boolean;
}

export default function ConsoleDrawer({ taskId, onClose, visible }: ConsoleDrawerProps) {
  const [logs, setLogs] = useState<string[]>([]);
  const [status, setStatus] = useState<"running" | "success" | "failed" | "needs_action">("running");
  const consoleEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!taskId || !visible) {
      setLogs([]);
      setStatus("running");
      return;
    }

    setLogs(["[SYSTEM] Connecting to secure live console channel..."]);
    
    // Connect to WebSocket endpoint
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    const wsUrl = backendUrl.replace(/^http/, "ws");
    
    const token = typeof window !== "undefined" ? localStorage.getItem("supabase_access_token") : null;
    const devUserId = typeof window !== "undefined" ? localStorage.getItem("user_id") : null;
    let wsQueryParams = "";
    if (token) {
      wsQueryParams = `?token=${encodeURIComponent(token)}`;
    } else if (devUserId) {
      wsQueryParams = `?dev_user_id=${encodeURIComponent(devUserId)}`;
    }
    
    const ws = new WebSocket(`${wsUrl}/api/ws/apply/${taskId}${wsQueryParams}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setLogs((prev) => [...prev, "[SYSTEM] Connection established. Listening for agent milestones..."]);
    };

    ws.onmessage = (event) => {
      const msg = event.data;
      setLogs((prev) => [...prev, msg]);
      
      // Auto-detect status changes from log keywords
      if (msg.toLowerCase().includes("finished successfully") || msg.toLowerCase().includes("submission success")) {
        setStatus("success");
      } else if (msg.toLowerCase().includes("failed") || msg.toLowerCase().includes("error")) {
        setStatus("failed");
      } else if (msg.toLowerCase().includes("action required") || msg.toLowerCase().includes("unmapped required field") || msg.toLowerCase().includes("login block")) {
        setStatus("needs_action");
      }
    };

    ws.onerror = () => {
      setLogs((prev) => [...prev, "[SYSTEM ERROR] WebSocket connection failed. Attempting status polling..."]);
    };

    // Polling status fallback
    const interval = setInterval(async () => {
      try {
        const data = await apiFetch(`/api/apply/status/${taskId}`);
        if (data.status && data.status !== "running" && data.status !== "pending") {
          setStatus(data.status);
          clearInterval(interval);
        }
      } catch (err) {
        console.error("Status check failed:", err);
      }
    }, 3000);

    return () => {
      clearInterval(interval);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [taskId, visible]);

  // Scroll to bottom on log updates
  useEffect(() => {
    consoleEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: 100 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 100 }}
          className="fixed bottom-0 left-0 right-0 z-50 p-4 md:p-6 bg-slate-950/90 backdrop-blur-xl border-t border-slate-800 shadow-2xl flex flex-col h-[350px] font-mono text-xs text-slate-300"
        >
          {/* Header */}
          <div className="flex justify-between items-center pb-3 border-b border-slate-800 mb-3">
            <div className="flex items-center gap-2 font-bold text-slate-200">
              <Terminal className="w-4 h-4 text-teal-500" />
              <span>AGENT AUTOMATION CONSOLE</span>
              <span className="text-slate-500 font-normal">|</span>
              <span className="text-[10px] bg-slate-800 px-2 py-0.5 rounded text-slate-400 uppercase tracking-wider">{taskId?.slice(0, 8)}</span>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                {status === "running" && (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-teal-400" />
                    <span className="text-teal-400 font-bold uppercase tracking-wider text-[10px]">Processing Form</span>
                  </>
                )}
                {status === "success" && (
                  <>
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-400 font-bold uppercase tracking-wider text-[10px]">Copilot Ready</span>
                  </>
                )}
                {status === "needs_action" && (
                  <>
                    <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
                    <span className="text-amber-400 font-bold uppercase tracking-wider text-[10px]">Input Required</span>
                  </>
                )}
                {status === "failed" && (
                  <>
                    <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                    <span className="text-rose-400 font-bold uppercase tracking-wider text-[10px]">Execution Failed</span>
                  </>
                )}
              </div>
              
              <button
                onClick={onClose}
                className="p-1 hover:bg-slate-800 rounded transition text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Logs Viewport */}
          <div className="flex-1 overflow-y-auto space-y-2 bg-slate-900/50 p-4 rounded-xl border border-slate-900 scrollbar-thin select-text">
            {logs.map((log, index) => {
              let color = "text-slate-300";
              if (log.includes("[SYSTEM]")) color = "text-teal-400 font-bold";
              else if (log.includes("[SYSTEM ERROR]") || log.toLowerCase().includes("failed") || log.toLowerCase().includes("error")) color = "text-rose-400";
              else if (log.toLowerCase().includes("success") || log.toLowerCase().includes("uploaded resume")) color = "text-emerald-400";
              else if (log.toLowerCase().includes("injecting") || log.toLowerCase().includes("retrieved")) color = "text-amber-400";

              return (
                <div key={index} className={`${color} leading-relaxed break-all`}>
                  <span className="text-slate-600 mr-2">[{new Date().toLocaleTimeString()}]</span>
                  {log}
                </div>
              );
            })}
            <div ref={consoleEndRef} />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

