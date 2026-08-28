"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Download, Loader2, FileText, Palette, Sparkles, 
  Briefcase, Layout, CheckCircle2, AlertCircle, XCircle, 
  Wand2, Printer, Code, Info, ExternalLink 
} from "lucide-react";
import { toast } from "sonner";
import { getBackendUrl, getAuthHeaders } from "../lib/api";

const TEMPLATES = [
  { 
    id: "classic", 
    name: "Classic", 
    icon: FileText, 
    desc: "100% ATS-Friendly traditional serif layout. Maximized machine readability for corporate ATS portals (Workday, Taleo, Greenhouse).", 
    color: "#475569",
    atsStatus: "high",
    atsLabel: "100% ATS Friendly (Simple)",
    atsDesc: "Pure single-column semantic layout with standard headers. Parses flawlessly on 100% of Applicant Tracking Systems without parsing errors."
  },
  { 
    id: "modern", 
    name: "Modern", 
    icon: Sparkles, 
    desc: "Tech-forward sans-serif with subtle accents. Perfect balance of ATS safety and modern tech aesthetics.", 
    color: "#4f46e5",
    atsStatus: "high",
    atsLabel: "95% ATS Friendly",
    atsDesc: "Clean structured layout with technical skill pills. Highly optimized for Tech, SaaS, and fast-moving companies."
  },
  { 
    id: "minimal", 
    name: "Minimal", 
    icon: Layout, 
    desc: "Surgical precision & whitespace-heavy layout. Ultra-clean readability for engineers, quants, and consultants.", 
    color: "#64748b",
    atsStatus: "high",
    atsLabel: "98% ATS Friendly",
    atsDesc: "Distraction-free typographic hierarchy with high signal-to-noise ratio. Exceptional parsing for both ATS bots and senior engineers."
  },
  { 
    id: "creative", 
    name: "Creative", 
    icon: Palette, 
    desc: "Bold gradient header with personality-driven transformation storytelling. Ideal for Design, Marketing, and Startups.", 
    color: "#7c3aed",
    atsStatus: "medium",
    atsLabel: "Moderate ATS (Startup/Portfolio)",
    atsDesc: "Vibrant visual flair and highlight matrix. Best for startup applications, portfolio submissions, or direct recruiter outreach."
  },
  { 
    id: "executive", 
    name: "Executive", 
    icon: Briefcase, 
    desc: "High-end luxury two-column corporate layout with champagne gold accents. Engineered for cold emailing C-suite executives and VPs.", 
    color: "#0f766e",
    atsStatus: "low",
    atsLabel: "Cold Email Luxury (Least ATS)",
    atsDesc: "Designed to captivate human eyes in direct cold emails and executive pitches. Two-column luxury layout not intended for automated portal parsers."
  },
];

interface TemplateSelectorProps {
  parsed_resume: any;
  selectedJob?: any;
}

export default function TemplateSelector({ parsed_resume, selectedJob }: TemplateSelectorProps) {
  const getRecommendation = () => {
    if (!selectedJob) return "modern";
    const title = (selectedJob.title || "").toLowerCase();
    const desc = (selectedJob.description || "").toLowerCase();
    const company = (selectedJob.company || "").toLowerCase();

    if (
      title.includes("director") ||
      title.includes("vp") ||
      title.includes("head") ||
      title.includes("chief") ||
      title.includes("executive") ||
      title.includes("partner")
    ) {
      return "executive";
    }

    if (
      company.includes("bank") ||
      company.includes("capital") ||
      company.includes("invest") ||
      company.includes("legal") ||
      company.includes("consulting") ||
      company.includes("mckinsey") ||
      company.includes("goldman") ||
      title.includes("lawyer") ||
      title.includes("analyst") ||
      title.includes("accountant")
    ) {
      return "classic";
    }

    if (
      title.includes("designer") ||
      title.includes("ui") ||
      title.includes("ux") ||
      title.includes("creative") ||
      title.includes("art") ||
      title.includes("brand") ||
      title.includes("marketing") ||
      title.includes("copywriter") ||
      title.includes("content")
    ) {
      return "creative";
    }

    if (
      title.includes("principal") ||
      title.includes("architect") ||
      title.includes("staff") ||
      title.includes("researcher") ||
      title.includes("scientist") ||
      title.includes("security") ||
      title.includes("systems") ||
      desc.includes("c++") ||
      desc.includes("rust")
    ) {
      return "minimal";
    }

    return "modern";
  };

  const [recommendedId, setRecommendedId] = useState<string>("modern");
  const [selected, setSelected] = useState<string>("modern");
  const [generating, setGenerating] = useState<boolean>(false);
  const [generationProgress, setGenerationProgress] = useState<string>("");
  const [showGuide, setShowGuide] = useState<boolean>(false);

  useEffect(() => {
    const rec = getRecommendation();
    setRecommendedId(rec);
    setSelected(rec);
  }, [selectedJob]);

  const currentTemplate = TEMPLATES.find((t) => t.id === selected) || TEMPLATES[1];

  // Helper for simulated progress steps
  const startProgressTimer = () => {
    const progressSteps = [
      "Executing psychological scroll-stop hooks & taglines...",
      "Amplifying project capabilities with Google's XYZ impact formula...",
      "Calibrating ATS keywords & single-page A4 density budget...",
      "Compiling 100% vector-crisp HTML & PDF layout..."
    ];
    let stepIdx = 0;
    return setInterval(() => {
      if (stepIdx < progressSteps.length) {
        setGenerationProgress(progressSteps[stepIdx]);
        stepIdx++;
      }
    }, 2000);
  };

  // 1. Interactive Preview & Save as PDF (Browser Engine)
  const handlePreviewAndPrint = async () => {
    setGenerating(true);
    setGenerationProgress("Preparing high-fidelity browser print preview...");
    const progressInterval = startProgressTimer();

    try {
      const res = await fetch(`${getBackendUrl()}/api/resume/generate-styled-html`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ 
          template: selected, 
          parsed_resume,
          job_description: selectedJob?.jd_text || null
        }),
      });

      clearInterval(progressInterval);

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: "Generation failed" }));
        throw new Error(errData.detail || "AI HTML generation failed");
      }

      const data = await res.json();
      const printWindow = window.open("", "_blank");
      if (printWindow) {
        printWindow.document.open();
        printWindow.document.write(data.html);
        printWindow.document.close();
        toast.success(`Opened ${currentTemplate.name} Resume preview in new tab! Use "Save as PDF" to save.`);
      } else {
        // Fallback if popup blocked: download HTML
        const blob = new Blob([data.html], { type: "text/html" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `resume_${selected}_1page.html`;
        a.click();
        URL.revokeObjectURL(url);
        toast.info("Popup blocked. Downloaded HTML file. Open in Chrome and press Ctrl+P!");
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to generate preview");
    } finally {
      setGenerating(false);
      setGenerationProgress("");
    }
  };

  // 2. Download HTML File Directly
  const handleDownloadHtml = async () => {
    setGenerating(true);
    setGenerationProgress("Exporting standalone HTML resume...");

    try {
      const res = await fetch(`${getBackendUrl()}/api/resume/download-html`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ 
          template: selected, 
          parsed_resume 
        }),
      });

      if (!res.ok) {
        throw new Error("Failed to export HTML resume");
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `resume_${selected}_A4_1page.html`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Downloaded HTML resume! Open in any browser and press Ctrl+P to save as PDF.");
    } catch (err: any) {
      toast.error(err.message || "Failed to download HTML");
    } finally {
      setGenerating(false);
      setGenerationProgress("");
    }
  };

  // 3. Direct Backend PDF Download
  const handleDownloadPdf = async () => {
    setGenerating(true);
    setGenerationProgress("Compiling strict 1-Page A4 PDF...");
    const progressInterval = startProgressTimer();

    try {
      const res = await fetch(`${getBackendUrl()}/api/resume/generate-styled`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ 
          template: selected, 
          parsed_resume,
          job_description: selectedJob?.jd_text || null
        }),
      });
      
      clearInterval(progressInterval);
      
      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: "Generation failed" }));
        throw new Error(errData.detail || "PDF generation failed");
      }
      
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `resume_${selected}_A4_1page.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`1-Page A4 AI Resume (${currentTemplate.name}) downloaded!`);
    } catch (err: any) {
      toast.error(err.message || "Failed to download PDF");
    } finally {
      setGenerating(false);
      setGenerationProgress("");
    }
  };

  const getAtsBadge = (status: string) => {
    switch (status) {
      case "high":
        return <span className="px-1.5 py-0.5 rounded text-[8px] font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">ATS: High</span>;
      case "medium":
        return <span className="px-1.5 py-0.5 rounded text-[8px] font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">ATS: Med</span>;
      case "low":
      default:
        return <span className="px-1.5 py-0.5 rounded text-[8px] font-bold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">ATS: Low</span>;
    }
  };

  const getAtsIcon = (status: string) => {
    switch (status) {
      case "high":
        return <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />;
      case "medium":
        return <AlertCircle className="w-4 h-4 text-amber-500 shrink-0" />;
      case "low":
      default:
        return <XCircle className="w-4 h-4 text-rose-500 shrink-0" />;
    }
  };

  return (
    <div className="space-y-4 p-5 rounded-2xl bg-white/50 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 shadow-sm">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-sm font-bold text-slate-700 dark:text-slate-200 flex items-center gap-2">
            <Wand2 className="w-4 h-4 text-teal-500" />
            AI Resume Generator
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">Select a style — AI rewrites &amp; optimizes your resume for it</p>
        </div>
        <button
          onClick={() => setShowGuide(!showGuide)}
          className="text-xs text-teal-600 dark:text-teal-400 hover:underline flex items-center gap-1 font-semibold"
        >
          <Info className="w-3.5 h-3.5" />
          {showGuide ? "Hide Guide" : "Print as PDF Guide"}
        </button>
      </div>

      {/* Guide Dropdown */}
      <AnimatePresence>
        {showGuide && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="p-3.5 rounded-xl bg-teal-500/10 border border-teal-500/20 text-xs text-teal-900 dark:text-teal-200 space-y-2 overflow-hidden"
          >
            <div className="font-bold flex items-center gap-1.5">
              <Printer className="w-4 h-4 text-teal-600 dark:text-teal-400" />
              How to Save as a Crisp 1-Page A4 PDF in Browser:
            </div>
            <ol className="list-decimal list-inside space-y-1 text-[11px] leading-relaxed text-slate-700 dark:text-slate-300">
              <li>Click <strong>&quot;Preview &amp; Save as PDF&quot;</strong> to open the high-res resume tab.</li>
              <li>Press <kbd className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 font-mono text-[10px]">Ctrl + P</kbd> (or click the floating Print button).</li>
              <li>In the Print dialog, set Destination to <strong>&quot;Save as PDF&quot;</strong>.</li>
              <li>Set Paper Size to <strong>A4</strong> and Margins to <strong>None / Default</strong>.</li>
              <li>Check <strong>&quot;Background graphics&quot;</strong> to preserve accent colors and click <strong>Save</strong>!</li>
            </ol>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid grid-cols-5 gap-2.5">
        {TEMPLATES.map((t) => {
          const Icon = t.icon;
          const active = selected === t.id;
          const isRecommended = t.id === recommendedId;
          return (
            <motion.button
              key={t.id}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => setSelected(t.id)}
              disabled={generating}
              className={`relative flex flex-col items-center gap-2 p-3 rounded-xl border text-center transition-all ${
                active
                  ? "border-teal-500 bg-teal-500/10 shadow-sm"
                  : "border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/10 hover:border-slate-400 dark:hover:border-slate-700"
              } ${generating ? "opacity-60 pointer-events-none" : ""}`}
            >
              {isRecommended && (
                <div className="absolute -top-1.5 -right-1 px-1 py-0.5 rounded bg-teal-600 text-[6px] font-black text-white uppercase tracking-wider shadow">
                  Rec
                </div>
              )}
              <Icon className="w-5 h-5" style={{ color: active ? t.color : "#94a3b8" }} />
              <span className={`text-[11px] font-bold ${active ? "text-teal-600 dark:text-teal-400" : "text-slate-500"}`}>
                {t.name}
              </span>
              <div className="mt-1">
                {getAtsBadge(t.atsStatus)}
              </div>
            </motion.button>
          );
        })}
      </div>

      {/* Selected Details Box */}
      <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/40 border border-slate-100 dark:border-slate-800/80 space-y-2.5 animate-fade-in">
        <div className="flex justify-between items-start gap-4">
          <p className="text-xs text-slate-600 dark:text-slate-300 font-medium leading-relaxed">
            {currentTemplate.desc}
          </p>
          {selected === recommendedId && (
            <span className="shrink-0 text-[9px] font-bold text-teal-600 dark:text-teal-400 bg-teal-500/10 px-2 py-0.5 rounded border border-teal-500/20 uppercase tracking-wider">
              ✨ Best Match
            </span>
          )}
        </div>
        
        {selected === recommendedId && selectedJob && (
          <div className="text-[10px] text-slate-500 dark:text-slate-400 border-t border-slate-200/40 dark:border-slate-800/40 pt-2 font-medium">
            💡 AI Recommendation: We suggest the <strong className="text-teal-600 dark:text-teal-400">{currentTemplate.name}</strong> layout. Its single-page parsing structure matches recruiting standards for {selectedJob.title || "this position"}.
          </div>
        )}
        
        <div className="flex items-start gap-2 pt-2 border-t border-slate-200/50 dark:border-slate-800/50">
          {getAtsIcon(currentTemplate.atsStatus)}
          <div>
            <h4 className="text-[11px] font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1">
              {currentTemplate.atsLabel}
            </h4>
            <p className="text-[10px] text-slate-400 leading-normal mt-0.5">
              {currentTemplate.atsDesc}
            </p>
          </div>
        </div>
      </div>

      {/* Generation Progress */}
      {generating && generationProgress && (
        <div className="p-3 rounded-xl bg-teal-500/5 border border-teal-500/10 flex items-center gap-3 animate-fade-in">
          <div className="relative">
            <Loader2 className="w-5 h-5 text-teal-500 animate-spin" />
            <div className="absolute inset-0 rounded-full bg-teal-500/20 animate-ping" />
          </div>
          <div>
            <p className="text-xs font-semibold text-teal-700 dark:text-teal-300">{generationProgress}</p>
            <p className="text-[10px] text-teal-600/70 dark:text-teal-400/70 mt-0.5">AI is optimizing your resume with psychological hooks, XYZ impact &amp; 1-Page A4 budgeting</p>
          </div>
        </div>
      )}

      {/* Action Buttons Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1">
        {/* Primary Action: Browser Print / Save as PDF */}
        <button
          onClick={handlePreviewAndPrint}
          disabled={generating}
          className="sm:col-span-2 flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 text-white text-xs font-bold transition-all disabled:opacity-50 shadow-md shadow-teal-600/20 relative overflow-hidden group"
        >
          {generating ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Generating Resume...
            </>
          ) : (
            <>
              <Printer className="w-4 h-4 group-hover:scale-110 transition-transform" />
              Preview &amp; Save as PDF (Browser Engine)
              <ExternalLink className="w-3 h-3 opacity-70" />
            </>
          )}
          <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
        </button>

        {/* Secondary Action: Download HTML */}
        <button
          onClick={handleDownloadHtml}
          disabled={generating}
          className="flex items-center justify-center gap-1.5 py-3 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold border border-slate-200 dark:border-slate-700 transition-all disabled:opacity-50"
        >
          <Code className="w-3.5 h-3.5 text-teal-500" />
          Download HTML
        </button>
      </div>

      {/* Direct PDF Download Link */}
      <div className="text-center pt-1">
        <button
          onClick={handleDownloadPdf}
          disabled={generating}
          className="text-[11px] text-slate-500 hover:text-teal-600 dark:hover:text-teal-400 inline-flex items-center gap-1 font-medium transition-colors"
        >
          <Download className="w-3 h-3" />
          Or direct download pre-rendered PDF ({currentTemplate.name})
        </button>
      </div>
    </div>
  );
}
