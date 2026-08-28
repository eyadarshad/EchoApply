"use client";

import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { Mail, Lock, Eye, EyeOff, ShieldCheck, HelpCircle, Loader2, X } from "lucide-react";
import { toast } from "sonner";

interface AuthPortalProps {
  onClose?: () => void;
  initialMode?: 'login' | 'register' | 'forgot';
  promptReason?: string;
}

export default function AuthPortal({ onClose, initialMode = 'login', promptReason }: AuthPortalProps = {}) {
  const { login, signup, forgotPassword, isDevMode } = useAuth();
  
  const [mode, setMode] = useState<'login' | 'register' | 'forgot'>(initialMode);
  const [email, setEmail] = useState<string>("candidate@example.com");
  const [password, setPassword] = useState<string>("password123");
  const [confirmPassword, setConfirmPassword] = useState<string>("password123");
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);

  const validateEmail = (val: string) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      toast.error("Please enter your email address");
      return;
    }
    if (!validateEmail(email)) {
      toast.error("Invalid email address format");
      return;
    }

    if (mode === "forgot") {
      setSubmitting(true);
      try {
        await forgotPassword(email.trim());
        if (isDevMode) {
          toast.success("Password reset link simulated successfully (Sandbox Mode)!");
        } else {
          toast.success("Password reset link sent! Please check your email inbox.");
        }
        setMode("login");
      } catch (err: any) {
        toast.error(err.message || "Failed to request password reset.");
      } finally {
        setSubmitting(false);
      }
      return;
    }

    if (!password.trim()) {
      toast.error("Please enter your password");
      return;
    }
    if (mode === "register" && password !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }
    if (mode === "register" && password.length < 6) {
      toast.error("Password must be at least 6 characters long");
      return;
    }

    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email.trim(), password);
        toast.success(`Welcome back! Logged in as ${email.trim()}`);
        if (onClose) onClose();
      } else {
        await signup(email.trim(), password);
        if (isDevMode) {
          toast.success("Account created successfully (Sandbox Mode)!");
          if (onClose) onClose();
        } else {
          toast.success("Confirmation email sent! Please check your inbox.");
          setMode("login");
        }
      }
    } catch (err: any) {
      toast.error(err.message || "Authentication failed. Try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const renderContent = () => {
    return (
      <div className="w-full max-w-md space-y-8 z-10">
        <div className="text-center space-y-3">
          {/* Logo container */}
          <div className="mx-auto h-14 w-14 rounded-2xl bg-white/10 dark:bg-slate-900 flex items-center justify-center shadow-lg shadow-teal-500/20 border border-teal-500/30 p-2.5">
            <img src="/logo.png" alt="Echo Apply Logo" className="w-8 h-8 object-contain invert brightness-125" />
          </div>
          <div>
            <h1 className="text-3xl font-black bg-gradient-to-r from-white via-slate-100 to-teal-300 bg-clip-text text-transparent">
              Echo Apply
            </h1>
            <p className="text-xs text-slate-400 mt-1 font-semibold tracking-wide">
              {mode === "login"
                ? "Sign in to access your dashboard"
                : mode === "register"
                ? "Register a secure new candidate account"
                : "Reset your password via recovery link"}
            </p>
          </div>
        </div>

        {/* Auth Card Container */}
        <div className="rounded-3xl bg-slate-900/40 backdrop-blur-xl border border-slate-800/80 p-8 shadow-2xl space-y-6 relative">
          {/* Close Button */}
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="absolute top-4 right-4 text-slate-500 hover:text-slate-300 p-1.5 transition rounded-lg hover:bg-slate-800/50"
              aria-label="Close Auth Panel"
            >
              <X className="w-4 h-4" />
            </button>
          )}

          {/* Prompt Reason Banner */}
          {promptReason && (
            <div className="p-3.5 rounded-xl border border-teal-500/20 bg-teal-500/5 text-[10px] text-teal-300 font-semibold leading-relaxed">
              🔒 Please sign in or register to {promptReason}.
            </div>
          )}

          {/* Tabs - Hidden in forgot password mode */}
          {mode !== "forgot" && (
            <div className="flex p-1 rounded-xl bg-slate-950/80 border border-slate-900">
              <button
                onClick={() => { setMode("login"); setPassword(""); setConfirmPassword(""); }}
                className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all duration-300 ${
                  mode === "login" ? "bg-teal-600 text-white shadow-md shadow-teal-600/10" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Sign In
              </button>
              <button
                onClick={() => { setMode("register"); setPassword(""); setConfirmPassword(""); }}
                className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all duration-300 ${
                  mode === "register" ? "bg-teal-600 text-white shadow-md shadow-teal-600/10" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Register
              </button>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email Field */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Email Address</label>
              <div className="relative">
                <input
                  type="email"
                  required
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-slate-950/80 border border-slate-800 focus:border-teal-500/80 rounded-xl pl-9 pr-3 py-2.5 text-xs outline-none text-slate-200 transition"
                />
                <Mail className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
              </div>
            </div>

            {/* Password Field */}
            {mode !== "forgot" && (
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-slate-950/80 border border-slate-800 focus:border-teal-500/80 rounded-xl pl-9 pr-10 py-2.5 text-xs outline-none text-slate-200 transition"
                  />
                  <Lock className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-3 text-slate-500 hover:text-slate-300 transition"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            )}

            {/* Confirm Password Field (only for Registration) */}
            {mode === "register" && (
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Confirm Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full bg-slate-950/80 border border-slate-800 focus:border-teal-500/80 rounded-xl pl-9 pr-10 py-2.5 text-xs outline-none text-slate-200 transition"
                  />
                  <Lock className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                </div>
              </div>
            )}

            {/* Forgot Password Toggle Link */}
            {mode === "login" && (
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => setMode("forgot")}
                  className="text-[10px] text-teal-400 hover:text-teal-300 font-semibold transition"
                >
                  Forgot Password?
                </button>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-teal-600 to-violet-600 hover:from-teal-500 hover:to-violet-500 text-white font-bold text-xs transition-all duration-300 flex items-center justify-center gap-1.5 shadow-lg shadow-teal-600/10 disabled:opacity-50 disabled:cursor-not-allowed mt-6"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  {mode === "login"
                    ? "Signing In..."
                    : mode === "register"
                    ? "Registering..."
                    : "Sending Request..."}
                </>
              ) : mode === "login" ? (
                "Sign In"
              ) : mode === "register" ? (
                "Register Account"
              ) : (
                "Send Reset Link"
              )}
            </button>

            {/* Return to Sign In (Forgot Mode) */}
            {mode === "forgot" && (
              <div className="text-center pt-2">
                <button
                  type="button"
                  onClick={() => setMode("login")}
                  className="text-[10px] text-slate-400 hover:text-slate-200 font-semibold transition"
                >
                  ← Back to Sign In
                </button>
              </div>
            )}
          </form>

          {/* Mode Warning Banner */}
          <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-900 flex gap-2">
            <HelpCircle className="w-4 h-4 text-teal-400 shrink-0 mt-0.5" />
            <div className="text-[10px] text-slate-400 leading-relaxed">
              {isDevMode ? (
                <span className="text-amber-400 font-bold">
                  SANDBOX MODE ACTIVE: Supabase credentials unset. Any email/password will create a mock local account instantly.
                </span>
              ) : (
                <span>
                  PRODUCTION AUTH ACTIVE: Connection secured. Credentials are verified by Supabase Auth over encrypted TLS connections.
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  if (onClose) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md overflow-y-auto">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-[100px] pointer-events-none animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-[100px] pointer-events-none animate-pulse"></div>
        {renderContent()}
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100 py-12 px-4 relative overflow-hidden">
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-[100px] pointer-events-none animate-pulse"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-[100px] pointer-events-none animate-pulse"></div>
      {renderContent()}
    </div>
  );
}

