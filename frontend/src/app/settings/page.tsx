"use client";

import React, { useEffect, useState } from "react";
import { 
  Trash2, AlertTriangle, Plus, Bell, ShieldAlert, 
  Loader2, ArrowLeft, User, KeyRound, Cookie, CreditCard, 
  X, CheckCircle, RefreshCw, Eye, EyeOff, Lock 
} from "lucide-react";
import { toast } from "sonner";
import { apiFetch, getBackendUrl, getAuthHeaders } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import AuthPortal from "../../components/AuthPortal";

interface SavedAlert {
  id: string;
  keywords: string;
  location: string | null;
  alert_interval: string;
  created_at: string;
}

export default function SettingsPage() {
  const { user_id, email, logout: authLogout, resetPassword, loading } = useAuth();
  const [showAuthModal, setShowAuthModal] = useState<boolean>(false);
  
  // Navigation / Tab state
  const [activeTab, setActiveTab] = useState<"profile" | "alerts" | "security" | "cookies" | "privacy">("profile");

  // Profile preferences
  const [userId, setUserId] = useState<string>("");
  const [name, setName] = useState<string>("Candidate");
  const [phone, setPhone] = useState<string>("+1-234-567-8900");
  const [githubUrl, setGithubUrl] = useState<string>("");
  const [linkedinUrl, setLinkedinUrl] = useState<string>("");
  const [major, setMajor] = useState<string>("Computer Science");
  const [location, setLocation] = useState<string>("Remote");
  const [skills, setSkills] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState<string>("");
  const [experience, setExperience] = useState<any[]>([]);
  const [education, setEducation] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [savingSettings, setSavingSettings] = useState<boolean>(false);

  // Password reset inside settings
  const [newPassword, setNewPassword] = useState<string>("");
  const [confirmNewPassword, setConfirmNewPassword] = useState<string>("");
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [updatingPassword, setUpdatingPassword] = useState<boolean>(false);

  // Billing status
  const [tier, setTier] = useState<string>("free");
  const [billingStatus, setBillingStatus] = useState<string>("active");
  const [loadingBilling, setLoadingBilling] = useState<boolean>(false);
  const [checkingOut, setCheckingOut] = useState<boolean>(false);

  // Job alerts
  const [alerts, setAlerts] = useState<SavedAlert[]>([]);
  const [alertKeywords, setAlertKeywords] = useState<string>("");
  const [alertLocation, setAlertLocation] = useState<string>("");
  const [alertInterval, setAlertInterval] = useState<string>("weekly");
  const [addingAlert, setAddingAlert] = useState<boolean>(false);

  // Cookies platform sync status info
  const [syncStatuses, setSyncStatuses] = useState<Record<string, boolean>>({
    linkedin: false,
    indeed: false,
    glassdoor: false
  });
  const [loadingCookies, setLoadingCookies] = useState<boolean>(false);
  const [activeLoginPlatform, setActiveLoginPlatform] = useState<string | null>(null);

  // GDPR deletion
  const [deleting, setDeleting] = useState<boolean>(false);
  const [confirmDelete, setConfirmDelete] = useState<boolean>(false);

  useEffect(() => {
    if (!loading && user_id) {
      setUserId(user_id);
      loadSavedProfile(user_id);
      loadSavedAlerts(user_id);
      loadBillingStatus(user_id);
      loadSyncStatuses(user_id);
    }
  }, [user_id, loading]);

  const loadSyncStatuses = async (uid: string) => {
    try {
      const data = await apiFetch<Record<string, boolean>>(`/api/auth/sync-status?user_id=${uid}`);
      setSyncStatuses(data);
    } catch (err) {
      console.error("Failed to load platform sync statuses", err);
    }
  };

  const loadSavedProfile = async (uid: string) => {
    try {
      const data = await apiFetch<any>(`/profiles/${uid}`);
      setMajor(data.major || "Computer Science");
      setLocation(data.location || "Remote");
      if (data.parsed_resume) {
        setName(data.parsed_resume.name || "Candidate");
        setPhone(data.parsed_resume.phone || "");
        setSkills(data.parsed_resume.skills || []);
        setExperience(data.parsed_resume.experience || []);
        setEducation(data.parsed_resume.education || []);
        setProjects(data.parsed_resume.projects || []);
        
        // Try to extract social links
        const links = data.parsed_resume.links || [];
        const githubLink = links.find((l: string) => l.includes("github.com"));
        const linkedinLink = links.find((l: string) => l.includes("linkedin.com"));
        if (githubLink) setGithubUrl(githubLink);
        if (linkedinLink) setLinkedinUrl(linkedinLink);
      }
    } catch (err) {
      console.error("Failed to load profile details", err);
    }
  };

  const loadBillingStatus = async (uid: string) => {
    setLoadingBilling(true);
    try {
      const data = await apiFetch<any>(`/api/billing/status?user_id=${uid}`);
      setTier(data.tier || "free");
      setBillingStatus(data.status || "active");
    } catch (err) {
      console.error("Failed to load billing status", err);
    } finally {
      setLoadingBilling(false);
    }
  };

  const loadSavedAlerts = async (uid: string) => {
    try {
      const data = await apiFetch<SavedAlert[]>(`/api/jobs/alerts?user_id=${uid}`);
      setAlerts(data);
    } catch (err: any) {
      // Gracefully handle if saved_searches table doesn't exist yet
      if (!err.message?.includes("saved_searches")) {
        console.error("Error loading alerts:", err);
      }
    }
  };

  const handleOpenLoginWindow = async (platform: string) => {
    setActiveLoginPlatform(platform);
    toast.info(`Opening secure browser window for ${platform.toUpperCase()}... Please log in inside that window.`);
    try {
      const data = await apiFetch<{ status: string; message: string }>("/api/auth/open-login-window", {
        method: "POST",
        body: JSON.stringify({
          user_id: userId,
          platform: platform
        })
      });
      if (data.status === "success") {
        toast.success(data.message || `Successfully synchronized ${platform} cookies!`);
        loadSyncStatuses(userId);
      } else if (data.status === "cancelled") {
        toast.warning(data.message || `Authentication window closed or timed out.`);
      } else {
        toast.error(data.message || `Login failed. Make sure Playwright is installed on the server.`);
      }
    } catch (err: any) {
      console.error("Error opening login window:", err);
      const msg = err.message || String(err);
      if (msg.includes("playwright") || msg.includes("browser") || msg.includes("Executable")) {
        toast.error("Playwright browser not installed on server. Run: playwright install chromium");
      } else {
        toast.error(`Login window error: ${msg}`);
      }
    } finally {
      setActiveLoginPlatform(null);
    }
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingSettings(true);
    try {
      const links = [];
      if (githubUrl.trim()) links.push(githubUrl.trim());
      if (linkedinUrl.trim()) links.push(linkedinUrl.trim());

      await apiFetch("/profiles", {
        method: "POST",
        body: JSON.stringify({
          user_id: userId,
          major: major,
          location: location,
          parsed_resume: {
            name: name.trim(),
            email: email || "user@example.com",
            phone: phone.trim(),
            links: links,
            skills: skills,
            education: education,
            experience: experience,
            projects: projects
          }
        })
      });
      toast.success("Career profile updated successfully!");
    } catch (err: any) {
      toast.error(err.message || "Failed to update profile settings.");
    } finally {
      setSavingSettings(false);
    }
  };

  const handleCreateAlert = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!alertKeywords.trim()) {
      toast.error("Please enter keywords for the alert");
      return;
    }
    
    setAddingAlert(true);
    try {
      const newAlert = await apiFetch<SavedAlert>("/api/jobs/alerts", {
        method: "POST",
        body: JSON.stringify({
          user_id: userId,
          keywords: alertKeywords.trim(),
          location: alertLocation.trim() || null,
          alert_interval: alertInterval
        })
      });
      
      setAlerts((prev) => [newAlert, ...prev]);
      setAlertKeywords("");
      setAlertLocation("");
      toast.success(`Subscribed to job alerts for "${alertKeywords.trim()}"!`);
    } catch (err: any) {
      toast.error(err.message || "Failed to create alert.");
    } finally {
      setAddingAlert(false);
    }
  };

  const handleDeleteAlert = async (alertId: string) => {
    try {
      await apiFetch(`/api/jobs/alerts/${alertId}`, { method: "DELETE" });
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
      toast.success("Alert removed.");
    } catch (err: any) {
      toast.error(err.message || "Failed to delete alert.");
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPassword.trim() || !confirmNewPassword.trim()) {
      toast.error("Please fill in both password fields");
      return;
    }
    if (newPassword !== confirmNewPassword) {
      toast.error("Passwords do not match");
      return;
    }
    if (newPassword.length < 6) {
      toast.error("Password must be at least 6 characters long");
      return;
    }

    setUpdatingPassword(true);
    try {
      await resetPassword(newPassword);
      toast.success("Your password has been securely updated.");
      setNewPassword("");
      setConfirmNewPassword("");
    } catch (err: any) {
      toast.error(err.message || "Failed to update password.");
    } finally {
      setUpdatingPassword(false);
    }
  };

  const handleUpgrade = async () => {
    setCheckingOut(true);
    try {
      const checkoutData = await apiFetch<{ checkout_url: string }>("/api/billing/checkout", {
        method: "POST",
        body: JSON.stringify({
          user_id: userId,
          tier: "pro",
          success_url: window.location.origin + "/settings?checkout=success",
          cancel_url: window.location.origin + "/settings?checkout=cancel"
        })
      });
      if (checkoutData.checkout_url) {
        window.location.href = checkoutData.checkout_url;
      }
    } catch (err: any) {
      toast.error(err.message || "Checkout session initialization failed.");
    } finally {
      setCheckingOut(false);
    }
  };

  const handleDeleteAccount = async () => {
    setDeleting(true);
    try {
      await apiFetch(`/api/user/delete?user_id=${userId}`, { method: "DELETE" });
      toast.success("Your profile and all credentials have been permanently erased.");
      await authLogout();
      setTimeout(() => {
        window.location.href = "/";
      }, 2000);
    } catch (err: any) {
      toast.error(err.message || "Failed to delete account.");
      setDeleting(false);
    }
  };

  const handleAddSkill = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanSkill = skillInput.trim();
    if (cleanSkill && !skills.includes(cleanSkill)) {
      setSkills([...skills, cleanSkill]);
      setSkillInput("");
    }
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    setSkills(skills.filter((s) => s !== skillToRemove));
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-teal-500 animate-spin" />
          <p className="text-xs text-slate-400 font-semibold uppercase tracking-widest animate-pulse">Loading Preferences...</p>
        </div>
      </div>
    );
  }

  if (!user_id) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100 relative overflow-hidden">
        <div className="max-w-md w-full p-8 rounded-3xl bg-slate-900/40 backdrop-blur-xl border border-slate-800 text-center space-y-5 shadow-2xl z-10">
          <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto animate-bounce" />
          <h2 className="text-lg font-bold">Authentication Required</h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            Please sign in to customize your career preferences, set up automatic job alerts, and manage subscription details.
          </p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => setShowAuthModal(true)}
              className="px-6 py-2.5 rounded-xl bg-teal-650 hover:bg-teal-600 text-white text-xs font-bold transition shadow-lg shadow-teal-600/10"
            >
              Sign In Now
            </button>
            <a
              href="/"
              className="px-6 py-2.5 rounded-xl border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-350 text-xs font-semibold transition"
            >
              Go to Home
            </a>
          </div>
        </div>

        {showAuthModal && (
          <AuthPortal
            onClose={() => setShowAuthModal(false)}
          />
        )}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-teal-950 text-slate-100 py-16 px-4">
      <div className="max-w-5xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl font-black text-slate-100">Account Preferences & Settings</h1>
            <p className="text-xs text-slate-400">Configure your candidate profile, sync tokens, credentials, and GDPR controls</p>
          </div>
          <a href="/" className="text-xs text-teal-400 hover:text-teal-300 flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Dashboard
          </a>
        </div>

        {/* Dashboard Frame Grid */}
        <div className="grid md:grid-cols-4 gap-6">
          
          {/* Navigation Sidebar */}
          <div className="flex flex-col gap-1.5 p-4 rounded-2xl bg-slate-900/40 backdrop-blur-md border border-slate-800 h-fit">
            <button
              onClick={() => setActiveTab("profile")}
              className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-bold transition ${
                activeTab === "profile" ? "bg-teal-600 text-white" : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/50"
              }`}
            >
              <User className="w-4 h-4" /> Profile Details
            </button>
            <button
              onClick={() => setActiveTab("alerts")}
              className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-bold transition ${
                activeTab === "alerts" ? "bg-teal-600 text-white" : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/50"
              }`}
            >
              <Bell className="w-4 h-4" /> Job Alerts
            </button>
            <button
              onClick={() => setActiveTab("security")}
              className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-bold transition ${
                activeTab === "security" ? "bg-teal-600 text-white" : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/50"
              }`}
            >
              <KeyRound className="w-4 h-4" /> Security & Billing
            </button>
            <button
              onClick={() => setActiveTab("cookies")}
              className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-bold transition ${
                activeTab === "cookies" ? "bg-teal-600 text-white" : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/50"
              }`}
            >
              <Cookie className="w-4 h-4" /> Extension Sync
            </button>
            <button
              onClick={() => setActiveTab("privacy")}
              className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-bold transition ${
                activeTab === "privacy" ? "bg-teal-600 text-white" : "text-rose-500/80 hover:text-rose-400 hover:bg-rose-500/5"
              }`}
            >
              <ShieldAlert className="w-4 h-4" /> Privacy Controls
            </button>
          </div>

          {/* Tab Content Display Area */}
          <div className="md:col-span-3 space-y-6">
            
            {/* 1. Profile Details tab */}
            {activeTab === "profile" && (
              <div className="p-6 rounded-2xl bg-slate-900/40 backdrop-blur-md border border-slate-800 space-y-6">
                <div className="border-b border-slate-800 pb-3">
                  <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                    <User className="w-4.5 h-4.5 text-teal-500" /> Career Profile Preferences
                  </h2>
                  <p className="text-[10px] text-slate-400 mt-0.5">Define details for AI tailoring and autofill suggestions</p>
                </div>

                <form onSubmit={handleSaveProfile} className="space-y-6">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Full Name</label>
                      <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="bg-slate-950 border border-slate-800 focus:border-teal-500/80 rounded-xl px-3 py-2 text-xs outline-none text-slate-200 transition"
                      />
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Contact Phone</label>
                      <input
                        type="text"
                        value={phone}
                        placeholder="+92-300-1234567"
                        onChange={(e) => setPhone(e.target.value)}
                        className="bg-slate-950 border border-slate-800 focus:border-teal-500/80 rounded-xl px-3 py-2 text-xs outline-none text-slate-200 transition"
                      />
                    </div>
                  </div>

                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Target Major / Field</label>
                      <input
                        type="text"
                        value={major}
                        onChange={(e) => setMajor(e.target.value)}
                        className="bg-slate-950 border border-slate-800 focus:border-teal-500/80 rounded-xl px-3 py-2 text-xs outline-none text-slate-200 transition"
                      />
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Preferred Location</label>
                      <input
                        type="text"
                        value={location}
                        onChange={(e) => setLocation(e.target.value)}
                        className="bg-slate-950 border border-slate-800 focus:border-teal-500/80 rounded-xl px-3 py-2 text-xs outline-none text-slate-200 transition"
                      />
                    </div>
                  </div>

                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">GitHub Profile URL</label>
                      <input
                        type="text"
                        value={githubUrl}
                        placeholder="https://github.com/username"
                        onChange={(e) => setGithubUrl(e.target.value)}
                        className="bg-slate-950 border border-slate-800 focus:border-teal-500/80 rounded-xl px-3 py-2 text-xs outline-none text-slate-200 transition"
                      />
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">LinkedIn Profile URL</label>
                      <input
                        type="text"
                        value={linkedinUrl}
                        placeholder="https://linkedin.com/in/username"
                        onChange={(e) => setLinkedinUrl(e.target.value)}
                        className="bg-slate-950 border border-slate-800 focus:border-teal-500/80 rounded-xl px-3 py-2 text-xs outline-none text-slate-200 transition"
                      />
                    </div>
                  </div>

                  {/* Skills Chip Management */}
                  <div className="flex flex-col gap-2">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Skills & Expertise</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={skillInput}
                        placeholder="Add a skill (e.g. Next.js)"
                        onChange={(e) => setSkillInput(e.target.value)}
                        className="bg-slate-950 border border-slate-800 focus:border-teal-500/80 rounded-xl px-3 py-2 text-xs outline-none text-slate-200 transition flex-1"
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            handleAddSkill(e);
                          }
                        }}
                      />
                      <button
                        type="button"
                        onClick={handleAddSkill}
                        className="px-4 py-2 bg-teal-650 hover:bg-teal-600 text-white rounded-xl text-xs font-bold transition"
                      >
                        Add
                      </button>
                    </div>
                    {/* Chips lists */}
                    <div className="flex flex-wrap gap-1.5 pt-2">
                      {skills.length === 0 ? (
                        <span className="text-[10px] text-slate-500 italic">No skills registered. Upload a resume or add skills above to start matching.</span>
                      ) : (
                        skills.map((s, idx) => (
                          <div key={idx} className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-teal-950/40 border border-teal-900/60 text-[10px] font-semibold text-teal-400">
                            {s}
                            <button
                              type="button"
                              onClick={() => handleRemoveSkill(s)}
                              className="text-slate-400 hover:text-rose-400 transition"
                            >
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Experience Section */}
                  <div className="flex flex-col gap-4 border-t border-slate-800/60 pt-6">
                    <div className="flex justify-between items-center">
                      <label className="text-[11px] font-bold uppercase tracking-wider text-slate-300">Work Experience</label>
                      <button
                        type="button"
                        onClick={() => setExperience([...experience, { role: "", company: "", start_date: "", end_date: "", bullets: [] }])}
                        className="px-3 py-1 rounded bg-teal-950 border border-teal-900/60 hover:bg-teal-900/50 text-[10px] font-bold text-teal-400 transition"
                      >
                        + Add Experience
                      </button>
                    </div>
                    
                    {experience.length === 0 ? (
                      <span className="text-[10px] text-slate-500 italic">No work experience entries registered.</span>
                    ) : (
                      <div className="space-y-4">
                        {experience.map((exp, idx) => (
                          <div key={idx} className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3 relative">
                            <button
                              type="button"
                              onClick={() => setExperience(experience.filter((_, i) => i !== idx))}
                              className="absolute top-3 right-3 text-slate-500 hover:text-rose-400 transition"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                            <div className="grid sm:grid-cols-2 gap-3">
                              <div className="flex flex-col gap-1">
                                <span className="text-[9px] font-semibold text-slate-400">Job Title / Role</span>
                                <input
                                  type="text"
                                  value={exp.role || ""}
                                  onChange={(e) => {
                                    const updated = [...experience];
                                    updated[idx].role = e.target.value;
                                    setExperience(updated);
                                  }}
                                  className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-205 outline-none focus:border-teal-500 transition"
                                />
                              </div>
                              <div className="flex flex-col gap-1">
                                <span className="text-[9px] font-semibold text-slate-400">Company Name</span>
                                <input
                                  type="text"
                                  value={exp.company || ""}
                                  onChange={(e) => {
                                    const updated = [...experience];
                                    updated[idx].company = e.target.value;
                                    setExperience(updated);
                                  }}
                                  className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-205 outline-none focus:border-teal-500 transition"
                                />
                              </div>
                            </div>
                            <div className="grid sm:grid-cols-2 gap-3">
                              <div className="flex flex-col gap-1">
                                <span className="text-[9px] font-semibold text-slate-400">Start Date</span>
                                <input
                                  type="text"
                                  placeholder="e.g. Jan 2023"
                                  value={exp.start_date || ""}
                                  onChange={(e) => {
                                    const updated = [...experience];
                                    updated[idx].start_date = e.target.value;
                                    setExperience(updated);
                                  }}
                                  className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-205 outline-none focus:border-teal-500 transition"
                                />
                              </div>
                              <div className="flex flex-col gap-1">
                                <span className="text-[9px] font-semibold text-slate-400">End Date</span>
                                <input
                                  type="text"
                                  placeholder="e.g. Present"
                                  value={exp.end_date || ""}
                                  onChange={(e) => {
                                    const updated = [...experience];
                                    updated[idx].end_date = e.target.value;
                                    setExperience(updated);
                                  }}
                                  className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-205 outline-none focus:border-teal-500 transition"
                                />
                              </div>
                            </div>
                            <div className="flex flex-col gap-1">
                              <span className="text-[9px] font-semibold text-slate-400">Key Achievements (One bullet point per line)</span>
                              <textarea
                                value={(exp.bullets || []).join("\n")}
                                rows={3}
                                onChange={(e) => {
                                  const updated = [...experience];
                                  updated[idx].bullets = e.target.value.split("\n");
                                  setExperience(updated);
                                }}
                                className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-205 outline-none focus:border-teal-500 transition font-sans leading-relaxed"
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Education Section */}
                  <div className="flex flex-col gap-4 border-t border-slate-800/60 pt-6">
                    <div className="flex justify-between items-center">
                      <label className="text-[11px] font-bold uppercase tracking-wider text-slate-300">Education</label>
                      <button
                        type="button"
                        onClick={() => setEducation([...education, { school: "", degree: "", date: "" }])}
                        className="px-3 py-1 rounded bg-teal-950 border border-teal-900/60 hover:bg-teal-900/50 text-[10px] font-bold text-teal-400 transition"
                      >
                        + Add Education
                      </button>
                    </div>
                    
                    {education.length === 0 ? (
                      <span className="text-[10px] text-slate-500 italic">No education entries registered.</span>
                    ) : (
                      <div className="grid sm:grid-cols-2 gap-4">
                        {education.map((edu, idx) => (
                          <div key={idx} className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3 relative">
                            <button
                              type="button"
                              onClick={() => setEducation(education.filter((_, i) => i !== idx))}
                              className="absolute top-3 right-3 text-slate-500 hover:text-rose-400 transition"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                            <div className="flex flex-col gap-1">
                              <span className="text-[9px] font-semibold text-slate-400">School / University</span>
                              <input
                                type="text"
                                value={edu.school || ""}
                                onChange={(e) => {
                                  const updated = [...education];
                                  updated[idx].school = e.target.value;
                                  setEducation(updated);
                                }}
                                className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-205 outline-none focus:border-teal-500 transition"
                              />
                            </div>
                            <div className="flex flex-col gap-1">
                              <span className="text-[9px] font-semibold text-slate-400">Degree / Qualification</span>
                              <input
                                type="text"
                                value={edu.degree || ""}
                                onChange={(e) => {
                                  const updated = [...education];
                                  updated[idx].degree = e.target.value;
                                  setEducation(updated);
                                }}
                                className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-205 outline-none focus:border-teal-500 transition"
                              />
                            </div>
                            <div className="flex flex-col gap-1">
                              <span className="text-[9px] font-semibold text-slate-400">Graduation Date</span>
                              <input
                                type="text"
                                placeholder="e.g. 2023"
                                value={edu.date || ""}
                                onChange={(e) => {
                                  const updated = [...education];
                                  updated[idx].date = e.target.value;
                                  setEducation(updated);
                                }}
                                className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-205 outline-none focus:border-teal-500 transition"
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Projects Section */}
                  <div className="flex flex-col gap-4 border-t border-slate-800/60 pt-6 pb-6">
                    <div className="flex justify-between items-center">
                      <label className="text-[11px] font-bold uppercase tracking-wider text-slate-300">Academic & Side Projects</label>
                      <button
                        type="button"
                        onClick={() => setProjects([...projects, { name: "", bullets: [] }])}
                        className="px-3 py-1 rounded bg-teal-950 border border-teal-900/60 hover:bg-teal-900/50 text-[10px] font-bold text-teal-400 transition"
                      >
                        + Add Project
                      </button>
                    </div>
                    
                    {projects.length === 0 ? (
                      <span className="text-[10px] text-slate-500 italic">No project entries registered.</span>
                    ) : (
                      <div className="space-y-4">
                        {projects.map((proj, idx) => (
                          <div key={idx} className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3 relative">
                            <button
                              type="button"
                              onClick={() => setProjects(projects.filter((_, i) => i !== idx))}
                              className="absolute top-3 right-3 text-slate-500 hover:text-rose-400 transition"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                            <div className="flex flex-col gap-1">
                              <span className="text-[9px] font-semibold text-slate-400">Project Name</span>
                              <input
                                type="text"
                                value={proj.name || ""}
                                onChange={(e) => {
                                  const updated = [...projects];
                                  updated[idx].name = e.target.value;
                                  setProjects(updated);
                                }}
                                className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-205 outline-none focus:border-teal-500 transition"
                              />
                            </div>
                            <div className="flex flex-col gap-1">
                              <span className="text-[9px] font-semibold text-slate-400">Project Achievements (One bullet point per line)</span>
                              <textarea
                                value={(proj.bullets || []).join("\n")}
                                rows={3}
                                onChange={(e) => {
                                  const updated = [...projects];
                                  updated[idx].bullets = e.target.value.split("\n");
                                  setProjects(updated);
                                }}
                                className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-205 outline-none focus:border-teal-500 transition font-sans leading-relaxed"
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <button
                    type="submit"
                    disabled={savingSettings}
                    className="px-5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50"
                  >
                    {savingSettings && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                    Save Profile Settings
                  </button>
                </form>
              </div>
            )}

            {/* 2. Job Alerts tab */}
            {activeTab === "alerts" && (
              <div className="p-6 rounded-2xl bg-slate-900/40 backdrop-blur-md border border-slate-800 space-y-6">
                <div className="border-b border-slate-800 pb-3">
                  <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                    <Bell className="w-4.5 h-4.5 text-emerald-500" /> Automated Job Matching Alerts
                  </h2>
                  <p className="text-[10px] text-slate-400 mt-0.5">Receive structured email alerts when new matched vacancies are fetched</p>
                </div>

                <form onSubmit={handleCreateAlert} className="grid grid-cols-4 gap-2">
                  <input
                    type="text"
                    placeholder="Keywords (e.g. React Developer)"
                    value={alertKeywords}
                    onChange={(e) => setAlertKeywords(e.target.value)}
                    className="col-span-2 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-xs focus:border-teal-500 outline-none text-slate-200"
                  />
                  <input
                    type="text"
                    placeholder="Location (e.g. Remote)"
                    value={alertLocation}
                    onChange={(e) => setAlertLocation(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-xs focus:border-teal-500 outline-none text-slate-200"
                  />
                  <button
                    type="submit"
                    disabled={addingAlert}
                    className="bg-emerald-650 hover:bg-emerald-600 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-1"
                  >
                    {addingAlert ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-4.5 h-4.5" />}
                    Add Alert
                  </button>
                </form>

                {/* List of active alerts */}
                <div className="space-y-2.5 pt-2 border-t border-slate-800/60">
                  {alerts.length === 0 ? (
                    <p className="text-xs text-slate-500 text-center py-4">No active job alerts. Add one above to start matching.</p>
                  ) : (
                    alerts.map((a) => (
                      <div key={a.id} className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-800 transition">
                        <div className="space-y-0.5">
                          <div className="text-xs font-bold text-slate-200">{a.keywords}</div>
                          <div className="text-[10px] text-slate-400">
                            Location: {a.location || "Anywhere"} &nbsp;|&nbsp; Frequency: {a.alert_interval}
                          </div>
                        </div>
                        <button
                          onClick={() => handleDeleteAlert(a.id)}
                          className="p-2 rounded-lg bg-slate-900 hover:bg-rose-500/10 text-slate-400 hover:text-rose-500 transition"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* 3. Security & Billing tab */}
            {activeTab === "security" && (
              <div className="space-y-6">
                
                {/* Billing Summary */}
                <div className="p-6 rounded-2xl bg-slate-900/40 backdrop-blur-md border border-slate-800 space-y-4">
                  <div className="border-b border-slate-800 pb-3">
                    <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                      <CreditCard className="w-4.5 h-4.5 text-teal-400" /> Platform Billing Subscription
                    </h2>
                    <p className="text-[10px] text-slate-400 mt-0.5">Manage your service levels, checkout history, and account features</p>
                  </div>

                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-4 rounded-xl bg-slate-950/60 border border-slate-800 gap-4">
                    <div className="space-y-1">
                      <div className="text-xs font-semibold text-slate-400">Current Status:</div>
                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-0.5 rounded-full bg-teal-500/20 text-teal-400 border border-teal-500/20 text-[10px] font-bold uppercase tracking-wider">
                          {tier} plan
                        </span>
                        <span className="text-[10px] text-slate-500">• {billingStatus}</span>
                      </div>
                    </div>

                    {tier === "free" ? (
                      <button
                        onClick={handleUpgrade}
                        disabled={checkingOut}
                        className="px-4 py-2.5 bg-gradient-to-r from-teal-650 to-violet-600 hover:from-teal-600 hover:to-violet-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-lg shadow-teal-600/10"
                      >
                        {checkingOut ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CreditCard className="w-4 h-4" />}
                        Upgrade to Pro Plan
                      </button>
                    ) : (
                      <div className="text-xs text-emerald-400 font-bold flex items-center gap-1.5">
                        <CheckCircle className="w-4.5 h-4.5" /> Premium Subscription Active
                      </div>
                    )}
                  </div>
                </div>

                {/* Password update Form */}
                <div className="p-6 rounded-2xl bg-slate-900/40 backdrop-blur-md border border-slate-800 space-y-4">
                  <div className="border-b border-slate-800 pb-3">
                    <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                      <KeyRound className="w-4.5 h-4.5 text-violet-500" /> Account Security Credentials
                    </h2>
                    <p className="text-[10px] text-slate-400 mt-0.5">Securely change your credential password</p>
                  </div>

                  <form onSubmit={handlePasswordChange} className="space-y-4">
                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="flex flex-col gap-1.5">
                        <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">New Password</label>
                        <div className="relative">
                          <input
                            type={showPassword ? "text" : "password"}
                            required
                            placeholder="••••••••"
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            className="w-full bg-slate-950/80 border border-slate-800 focus:border-teal-500/80 rounded-xl pl-9 pr-10 py-2 text-xs outline-none text-slate-200 transition"
                          />
                          <Lock className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                          <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute right-3 top-2.5 text-slate-500 hover:text-slate-350"
                          >
                            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                        </div>
                      </div>

                      <div className="flex flex-col gap-1.5">
                        <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Confirm New Password</label>
                        <div className="relative">
                          <input
                            type={showPassword ? "text" : "password"}
                            required
                            placeholder="••••••••"
                            value={confirmNewPassword}
                            onChange={(e) => setConfirmNewPassword(e.target.value)}
                            className="w-full bg-slate-950/80 border border-slate-800 focus:border-teal-500/80 rounded-xl pl-9 pr-3 py-2 text-xs outline-none text-slate-200 transition"
                          />
                          <Lock className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                        </div>
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={updatingPassword}
                      className="px-4 py-2 rounded-xl bg-violet-650 hover:bg-violet-600 disabled:opacity-50 text-white text-xs font-bold flex items-center gap-1.5 transition"
                    >
                      {updatingPassword && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                      Update Account Password
                    </button>
                  </form>
                </div>
              </div>
            )}

            {/* 4. Extension Sync & Cookies tab */}
            {activeTab === "cookies" && (
              <div className="p-6 rounded-2xl bg-slate-900/40 backdrop-blur-md border border-slate-800 space-y-6">
                <div className="border-b border-slate-800 pb-3">
                  <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                    <Cookie className="w-4.5 h-4.5 text-amber-500" /> Platform Login & Cookie Sync
                  </h2>
                  <p className="text-[10px] text-slate-400 mt-0.5">Authorize and link your LinkedIn, Indeed, and Glassdoor accounts for background agent application matching</p>
                </div>

                {/* Secure Sync Notice */}
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <p className="text-xs text-slate-300 leading-relaxed">
                    Our AI background agent automates job matching and application draft submission on your behalf.
                    To access restricted boards, we require session cookies. Click **"Login via Browser"** below to securely open a window, sign in, and automatically synchronize credentials. 
                    All tokens are encrypted in the database using **AES-256**.
                  </p>
                </div>

                {/* Platforms Grid */}
                <div className="grid sm:grid-cols-3 gap-4">
                  {(["linkedin", "indeed", "glassdoor"] as const).map((plat) => {
                    const isSynced = syncStatuses[plat];
                    const isActiveSync = activeLoginPlatform === plat;
                    const labelMap: Record<string, string> = {
                      linkedin: "LinkedIn",
                      indeed: "Indeed",
                      glassdoor: "Glassdoor"
                    };

                    return (
                      <div key={plat} className="p-5 rounded-2xl bg-slate-950 border border-slate-800 flex flex-col justify-between space-y-4 hover:border-slate-800 transition shadow-sm">
                        <div className="space-y-2">
                          <div className="flex justify-between items-center">
                            <span className="text-xs font-bold text-slate-200">{labelMap[plat]}</span>
                            <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider ${
                              isSynced 
                                ? "bg-emerald-500/10 text-emerald-450 border border-emerald-500/25"
                                : "bg-amber-500/10 text-amber-450 border border-amber-500/25"
                            }`}>
                              {isSynced ? "Linked" : "Not Synced"}
                            </span>
                          </div>
                          <p className="text-[10px] text-slate-500 font-light leading-relaxed">
                            {plat === "linkedin" 
                              ? "Allows searching high-tier developer opportunities and submitting LinkedIn Easy Apply templates."
                              : plat === "indeed"
                              ? "Allows searching international listings and auto-filling Indeed application forms."
                              : "Provides direct company reviews, wage indexes, and Glassdoor application forms."
                            }
                          </p>
                        </div>

                        <button
                          onClick={() => handleOpenLoginWindow(plat)}
                          disabled={activeLoginPlatform !== null}
                          className={`w-full py-2 rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5 ${
                            isActiveSync 
                              ? "bg-amber-500/20 border border-amber-500/30 text-amber-400"
                              : isSynced 
                              ? "bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-330"
                              : "bg-teal-600 hover:bg-teal-500 text-white shadow-md shadow-teal-600/10"
                          }`}
                        >
                          {isActiveSync ? (
                            <>
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              Logging in...
                            </>
                          ) : (
                            <>
                              <RefreshCw className="w-3.5 h-3.5" />
                              {isSynced ? "Re-sync Session" : "Login via Browser"}
                            </>
                          )}
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 5. GDPR Privacy Controls tab */}
            {activeTab === "privacy" && (
              <div className="p-6 rounded-2xl bg-rose-500/5 backdrop-blur-md border border-rose-500/10 space-y-4">
                <div className="border-b border-rose-500/10 pb-3">
                  <h2 className="text-sm font-bold text-rose-500 flex items-center gap-2">
                    <ShieldAlert className="w-4.5 h-4.5" /> GDPR Compliance: Wipe Account Data
                  </h2>
                  <p className="text-[10px] text-rose-400/80 mt-0.5">General Data Protection Regulation (GDPR) right to erasure controls</p>
                </div>

                <p className="text-xs text-slate-400 leading-relaxed">
                  In compliance with the General Data Protection Regulation (GDPR) Right to Erasure (Article 17), 
                  triggering account deletion permanently wipes your profile, uploaded resume documents, application history, 
                  and all synchronized platform session cookies from our databases and servers. **This action cannot be undone.**
                </p>

                {!confirmDelete ? (
                  <button
                    onClick={() => setConfirmDelete(true)}
                    className="px-4 py-2.5 rounded-xl border border-rose-500/20 bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 text-xs font-bold transition flex items-center gap-1.5"
                  >
                    <AlertTriangle className="w-4 h-4" /> Request Account Erasure
                  </button>
                ) : (
                  <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 space-y-3">
                    <p className="text-xs text-rose-500 font-bold flex items-center gap-1.5">
                      <AlertTriangle className="w-4.5 h-4.5" /> Are you absolutely sure you want to permanently delete all your data?
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={handleDeleteAccount}
                        disabled={deleting}
                        className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold flex items-center gap-1.5 transition disabled:opacity-50 animate-pulse"
                      >
                        {deleting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                        Confirm Permanent Deletion
                      </button>
                      <button
                        onClick={() => setConfirmDelete(false)}
                        disabled={deleting}
                        className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-350 text-xs font-semibold transition"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

          </div>
        </div>

      </div>
    </div>
  );
}

