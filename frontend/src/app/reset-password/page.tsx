"use client";

import React, { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { Lock, ShieldAlert, Loader2, KeyRound } from "lucide-react";
import { toast } from "sonner";

export default function ResetPasswordPage() {
  const { resetPassword, isDevMode } = useAuth();
  
  const [password, setPassword] = useState<string>("");
  const [confirmPassword, setConfirmPassword] = useState<string>("");
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim() || !confirmPassword.trim()) {
      toast.error("Please fill in both password fields");
      return;
    }
    if (password !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }
    if (password.length < 6) {
      toast.error("Password must be at least 6 characters long");
      return;
    }

    setSubmitting(true);
    try {
      await resetPassword(password);
      if (isDevMode) {
        toast.success("Password reset simulated successfully (Sandbox Mode)!");
      } else {
        toast.success("Password updated successfully! Redirecting you to login...");
      }
      setTimeout(() => {
        window.location.href = "/";
      }, 2000);
    } catch (err: any) {
      toast.error(err.message || "Failed to update password. Link may be expired.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100 py-12 px-4 relative overflow-hidden">
      {/* Abstract Glowing Background Orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-[100px] pointer-events-none animate-pulse"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-[100px] pointer-events-none animate-pulse"></div>

      <div className="w-full max-w-md space-y-8 z-10">
        <div className="text-center space-y-3">
          <div className="mx-auto h-12 w-12 rounded-2xl bg-gradient-to-tr from-teal-500 to-violet-600 flex items-center justify-center shadow-lg shadow-teal-500/20 border border-teal-400/20">
            <KeyRound className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-black bg-gradient-to-r from-white via-slate-100 to-teal-300 bg-clip-text text-transparent">
              Set New Password
            </h1>
            <p className="text-xs text-slate-400 mt-1 font-semibold tracking-wide">
              Securely update your candidate credentials
            </p>
          </div>
        </div>

        {/* Form Container */}
        <div className="rounded-3xl bg-slate-900/40 backdrop-blur-xl border border-slate-800/80 p-8 shadow-2xl space-y-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* New Password */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">New Password</label>
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
              </div>
            </div>

            {/* Confirm Password */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Confirm New Password</label>
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

            {/* Submit Button */}
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-teal-600 to-violet-600 hover:from-teal-500 hover:to-violet-500 text-white font-bold text-xs transition-all duration-300 flex items-center justify-center gap-1.5 shadow-lg shadow-teal-600/10 disabled:opacity-50 disabled:cursor-not-allowed mt-6"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Updating Password...
                </>
              ) : (
                "Update Password"
              )}
            </button>
          </form>

          {/* Security Banner */}
          <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-900 flex gap-2">
            <ShieldAlert className="w-4 h-4 text-teal-400 shrink-0 mt-0.5" />
            <div className="text-[10px] text-slate-400 leading-relaxed">
              Once submitted, your session tokens will automatically update. You will be redirected to log in using your new credentials.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

