"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircle, Send, X, Minimize2, Loader2, Sparkles, User, Bot, AlertCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../lib/api";
import { toast } from "sonner";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatBot() {
  const { user_id, isDevMode } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [history, setHistory] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hi! I'm your Echo Apply career assistant. Ask me anything about resume optimization, interview prep, or job search strategies!",
    },
  ]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history, loading]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || loading) return;

    const userMessage = message.trim();
    setMessage("");
    setHistory((prev) => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);
    setError(null);

    try {
      // Gather resume context if available locally
      let context = "";
      const savedProfile = localStorage.getItem("user_profile_cache");
      if (savedProfile) {
        try {
          const parsed = JSON.parse(savedProfile);
          context = `Candidate Profile: ${JSON.stringify(parsed.skills || [])} experience: ${JSON.stringify(parsed.experience || [])}`;
        } catch (_) {}
      }

      const data = await apiFetch<{ reply: string }>("/api/chat/message", {
        method: "POST",
        body: JSON.stringify({
          message: userMessage,
          history: history.map((h) => ({ role: h.role, content: h.content })),
          context: context || null,
        }),
      });

      if (!data.reply || !data.reply.trim()) {
        throw new Error("AI service returned an empty response. Please try again.");
      }
      setHistory((prev) => [...prev, { role: "assistant", content: data.reply }]);
    } catch (err: any) {
      console.error("Chat error:", err);
      const msg = err.message || "Unknown error";
      const isAuth = msg.toLowerCase().includes("token") || msg.toLowerCase().includes("401") || msg.toLowerCase().includes("expired");
      const displayMsg = isAuth 
        ? "Your session has expired. Please sign out and sign back in."
        : msg;
      setError(displayMsg);
      setHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Sorry, I ran into an issue: ${displayMsg}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
      {/* Expanded Chat window */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 50, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
            className="w-[360px] md:w-[400px] h-[500px] rounded-2xl glass-card flex flex-col overflow-hidden shadow-2xl border border-teal-500/20 mb-4 bg-slate-900/95 dark:bg-slate-950/95 backdrop-blur-xl"
            style={{ maxHeight: "calc(100vh - 100px)" }}
          >
            {/* Window Header - Fixed height to prevent cutoff */}
            <div className="flex-shrink-0 p-4 border-b border-slate-800/80 bg-slate-950/80 flex items-center justify-between min-h-[60px]">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400 flex-shrink-0">
                  <Sparkles className="w-4 h-4 animate-pulse" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider truncate">Career Assistant</h3>
                  <p className="text-[10px] text-teal-400 font-semibold uppercase tracking-widest truncate">Online & Ready</p>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition flex-shrink-0"
              >
                <Minimize2 className="w-4 h-4" />
              </button>
            </div>

            {/* Chat Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0" ref={scrollRef}>
              {(!user_id && !isDevMode) ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-3">
                  <MessageCircle className="w-12 h-12 text-slate-600 animate-bounce" />
                  <p className="text-sm font-semibold text-slate-300">Authentication Required</p>
                  <p className="text-xs text-slate-400">Please sign in to chat with our AI Career Assistant.</p>
                </div>
              ) : (
                <>
                  {error && (
                    <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs">
                      <AlertCircle className="w-4 h-4 flex-shrink-0" />
                      <span>{error}</span>
                    </div>
                  )}
                  {history.map((msg, index) => (
                    <div
                      key={index}
                      className={`flex gap-3 max-w-[85%] ${msg.role === "user" ? "ml-auto flex-row-reverse" : "mr-auto"}`}
                    >
                      <div
                        className={`w-7 h-7 rounded-full flex items-center justify-center text-xs shrink-0 ${
                          msg.role === "user"
                            ? "bg-teal-600 text-white"
                            : "bg-slate-800 text-teal-400 border border-slate-700"
                        }`}
                      >
                        {msg.role === "user" ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                      </div>
                      <div
                        className={`p-3 rounded-2xl text-xs leading-relaxed ${
                          msg.role === "user"
                            ? "bg-teal-600 text-white rounded-tr-none"
                            : "bg-slate-800/80 text-slate-200 rounded-tl-none border border-slate-700/30"
                        }`}
                      >
                        {msg.content}
                      </div>
                    </div>
                  ))}
                  {loading && (
                    <div className="flex gap-3 max-w-[85%] mr-auto">
                      <div className="w-7 h-7 rounded-full bg-slate-800 text-teal-400 border border-slate-700 flex items-center justify-center text-xs">
                        <Bot className="w-3.5 h-3.5" />
                      </div>
                      <div className="p-3 rounded-2xl rounded-tl-none bg-slate-800/80 border border-slate-700/30 text-slate-400 flex items-center gap-1">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span className="text-[10px] uppercase font-bold tracking-wider">Thinking...</span>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Chat Footer */}
            {(user_id || isDevMode) && (
              <form onSubmit={handleSend} className="p-3 bg-slate-950/60 border-t border-slate-800/80 flex gap-2">
                <input
                  type="text"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Ask about resume tips, interview prep..."
                  className="flex-1 bg-slate-900 border border-slate-850 rounded-xl px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-teal-500/50"
                  disabled={loading}
                />
                <button
                  type="submit"
                  disabled={loading || !message.trim()}
                  className="p-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white disabled:opacity-40 disabled:hover:bg-teal-600 transition flex items-center justify-center shadow-md shadow-teal-600/10"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
            )}
            {(!user_id && !isDevMode) && (
              <div className="p-3 bg-slate-950/60 border-t border-slate-800/80 text-center text-xs text-slate-500">
                Sign in to start chatting
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating Action Button (FAB) */}
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        className="w-12 h-12 rounded-full bg-teal-600 hover:bg-teal-500 flex items-center justify-center text-white shadow-xl shadow-teal-600/20 cursor-pointer border border-teal-500/30"
        aria-label="Toggle AI Chatbot"
      >
        {isOpen ? <X className="w-5 h-5" /> : <MessageCircle className="w-5 h-5" />}
      </motion.button>
    </div>
  );
}
