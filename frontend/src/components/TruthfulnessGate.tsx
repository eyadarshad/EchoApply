"use client";

import React, { useState } from "react";
import { ShieldAlert, CheckCircle2, ChevronRight, XCircle, AlertCircle, Play, Edit3, Save } from "lucide-react";

interface BulletVerification {
  rewritten_bullet: string;
  is_fabricated: boolean;
  justification: string;
  suggested_fix: string;
}

interface TruthfulnessCheckResult {
  is_fabricated: boolean;
  verification_report: BulletVerification[];
}

interface GapAnalysisResult {
  matched_skills: string[];
  missing_skills: string[];
  partial_matches: Array<{
    jd_skill: string;
    user_skill: string;
    reason: string;
  }>;
}

interface ResumeParsedData {
  name: string;
  email: string;
  phone?: string;
  links: string[];
  skills: string[];
  education: any[];
  experience: any[];
  projects: any[];
  anchor_line?: string;
  highlights_strip?: any[];
}

interface TruthfulnessGateProps {
  atsScore: number;
  gapAnalysis: GapAnalysisResult;
  truthfulnessReport: TruthfulnessCheckResult;
  tailoredResume: ResumeParsedData;
  onFinalApprove: (finalResume: ResumeParsedData) => void;
  onReset: () => void;
}

export default function TruthfulnessGate({
  atsScore,
  gapAnalysis,
  truthfulnessReport,
  tailoredResume,
  onFinalApprove,
  onReset
}: TruthfulnessGateProps) {
  // Store the list of bullets editable by the user
  const [editedExperiences, setEditedExperiences] = useState(() => {
    return tailoredResume.experience.map((exp) => ({
      ...exp,
      bullets: [...exp.bullets]
    }));
  });

  const [activeEditIdx, setActiveEditIdx] = useState<{ jobIdx: number; bulletIdx: number } | null>(null);
  const [tempEditText, setTempEditText] = useState("");

  const handleStartEdit = (jobIdx: number, bulletIdx: number, text: string) => {
    setActiveEditIdx({ jobIdx, bulletIdx });
    setTempEditText(text);
  };

  const handleSaveEdit = (jobIdx: number, bulletIdx: number) => {
    const updated = [...editedExperiences];
    updated[jobIdx].bullets[bulletIdx] = tempEditText;
    setEditedExperiences(updated);
    setActiveEditIdx(null);
  };

  const handleApplyFix = (jobIdx: number, bulletIdx: number, fixText: string) => {
    const updated = [...editedExperiences];
    updated[jobIdx].bullets[bulletIdx] = fixText;
    setEditedExperiences(updated);
  };

  const handleApprove = () => {
    const finalResume = {
      ...tailoredResume,
      experience: editedExperiences
    };
    onFinalApprove(finalResume);
  };

  // Flat list of verifications corresponding to each bullet for auditing display
  // We can match them based on order
  let bulletCounter = 0;
  const auditReport = truthfulnessReport.verification_report || [];

  return (
    <div className="w-full max-w-4xl mx-auto space-y-8 animate-fade-in pb-16">
      {/* Overview Dashboard Card */}
      <div className="grid md:grid-cols-3 gap-6">
        {/* ATS Score Card */}
        <div className="p-6 rounded-3xl border border-slate-800 bg-slate-900/20 backdrop-blur-xl flex flex-col items-center justify-center text-center relative overflow-hidden">
          <div className="absolute top-0 inset-x-0 h-1 bg-indigo-500" />
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">ATS Score Match</span>
          <div className="relative flex items-center justify-center mt-4">
            <div className="text-4xl font-extrabold text-indigo-400">{atsScore}%</div>
          </div>
          <p className="text-[10px] text-slate-500 mt-3 max-w-[150px]">Score based on semantic keyword match to Job Description.</p>
        </div>

        {/* Matched Skills Card */}
        <div className="p-6 rounded-3xl border border-slate-800 bg-slate-900/20 backdrop-blur-xl flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 inset-x-0 h-1 bg-emerald-500" />
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">Matched Skills</span>
            <div className="flex flex-wrap gap-1.5 max-h-[100px] overflow-y-auto">
              {gapAnalysis.matched_skills.length === 0 ? (
                <span className="text-xs text-slate-500">No matching skills found.</span>
              ) : (
                gapAnalysis.matched_skills.map((skill, idx) => (
                  <span key={idx} className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 text-[10px] border border-emerald-500/20 font-medium">
                    {skill}
                  </span>
                ))
              )}
            </div>
          </div>
          {gapAnalysis.partial_matches.length > 0 && (
            <div className="mt-3 pt-3 border-t border-slate-850 text-[10px] text-indigo-400">
              {gapAnalysis.partial_matches.length} Partial match(es) detected
            </div>
          )}
        </div>

        {/* Gaps/Missing Skills Card */}
        <div className="p-6 rounded-3xl border border-slate-800 bg-slate-900/20 backdrop-blur-xl flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 inset-x-0 h-1 bg-rose-500" />
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">Honest Skill Gaps</span>
            <div className="flex flex-wrap gap-1.5 max-h-[100px] overflow-y-auto">
              {gapAnalysis.missing_skills.length === 0 ? (
                <span className="text-xs text-slate-500">No missing skills! Candidate is 100% matched.</span>
              ) : (
                gapAnalysis.missing_skills.map((skill, idx) => (
                  <span key={idx} className="px-2 py-0.5 rounded-md bg-rose-500/10 text-rose-400 text-[10px] border border-rose-500/20 font-medium">
                    {skill}
                  </span>
                ))
              )}
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-850 text-[10px] text-slate-500">
            *Gaps are kept authentic. No fabrications inserted.
          </div>
        </div>
      </div>

      {/* Truthfulness Gate Warning Banner */}
      {truthfulnessReport.is_fabricated ? (
        <div className="p-5 rounded-2xl border border-amber-500/30 bg-amber-500/10 flex items-start gap-4 text-amber-200">
          <ShieldAlert className="w-6 h-6 shrink-0 mt-0.5 text-amber-400" />
          <div>
            <h4 className="text-sm font-bold">Verification Required: Fabrications Detected</h4>
            <p className="text-xs text-amber-300/80 mt-1">
              Gemini 1.5 Pro has audited the rewrites and flagged additions (like invented metrics or unlisted technologies)
              that are not present in your source resume. Review the flagged bullets below and accept the factual fixes or edit them.
            </p>
          </div>
        </div>
      ) : (
        <div className="p-5 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 flex items-start gap-4 text-emerald-200">
          <CheckCircle2 className="w-6 h-6 shrink-0 mt-0.5 text-emerald-400" />
          <div>
            <h4 className="text-sm font-bold">Truthfulness Gate Cleared</h4>
            <p className="text-xs text-emerald-300/80 mt-1">
              All rewritten experiences conform strictly to the facts of your original resume. No fabrications or unvetted claims were detected.
            </p>
          </div>
        </div>
      )}

      {/* Tagline / Anchor Line Preview Card */}
      {tailoredResume.anchor_line && (
        <div className="p-6 rounded-3xl border border-slate-800 bg-slate-900/10 space-y-2">
          <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">Tailored Tagline (Anchor Line)</span>
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-850 font-serif italic text-base text-slate-200 text-center">
            &ldquo;{tailoredResume.anchor_line}&rdquo;
          </div>
        </div>
      )}

      {/* Interactive Verification List */}
      <div className="space-y-6">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Experience Bullet Points Audit</h3>
        
        <div className="space-y-6">
          {editedExperiences.map((job, jobIdx) => (
            <div key={jobIdx} className="p-6 rounded-3xl border border-slate-800 bg-slate-900/30 space-y-4">
              <div>
                <h4 className="text-base font-bold text-slate-100">{job.role}</h4>
                <span className="text-xs text-slate-400">{job.company} · {job.start_date} &ndash; {job.end_date || "Present"}</span>
              </div>

              <div className="space-y-3.5 pt-2">
                {job.bullets.map((bullet: string, bulletIdx: number) => {
                  const currentCounter = bulletCounter++;
                  const verification: BulletVerification | undefined = auditReport[currentCounter];
                  const isFlagged = verification?.is_fabricated;

                  const isEditing = activeEditIdx?.jobIdx === jobIdx && activeEditIdx?.bulletIdx === bulletIdx;

                  return (
                    <div
                      key={bulletIdx}
                      className={`p-4 rounded-2xl border transition duration-200 space-y-3 ${
                        isFlagged
                          ? "border-amber-500/30 bg-amber-500/5 hover:border-amber-500/50"
                          : "border-slate-800/60 bg-slate-950/40 hover:border-slate-750"
                      }`}
                    >
                      <div className="flex justify-between items-start gap-4">
                        <div className="flex-1">
                          {isEditing ? (
                            <textarea
                              value={tempEditText}
                              onChange={(e) => setTempEditText(e.target.value)}
                              rows={2}
                              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-indigo-500 text-xs text-slate-200 focus:outline-none resize-y"
                            />
                          ) : (
                            <p className="text-xs text-slate-200 font-light leading-relaxed">{bullet}</p>
                          )}
                        </div>

                        {/* Edit / Save controls */}
                        <div className="shrink-0 flex gap-1.5">
                          {isEditing ? (
                            <button
                              onClick={() => handleSaveEdit(jobIdx, bulletIdx)}
                              className="p-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-white transition"
                              title="Save Changes"
                            >
                              <Save className="w-3.5 h-3.5" />
                            </button>
                          ) : (
                            <button
                              onClick={() => handleStartEdit(jobIdx, bulletIdx, bullet)}
                              className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
                              title="Edit Bullet"
                            >
                              <Edit3 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Fabrication Alert & Factual Fix overlay */}
                      {isFlagged && verification && (
                        <div className="p-3.5 rounded-xl bg-amber-500/5 border border-amber-500/20 space-y-2">
                          <div className="flex items-center gap-2 text-[10px] text-amber-400 font-semibold uppercase tracking-wider">
                            <ShieldAlert className="w-4 h-4 text-amber-400" />
                            Auditor Warning: Unverified Claim
                          </div>
                          <p className="text-[10px] text-amber-300/80 italic font-light">{verification.justification}</p>
                          
                          {verification.suggested_fix && bullet !== verification.suggested_fix && (
                            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 pt-1 text-[10px]">
                              <div className="text-emerald-400">
                                <span className="font-semibold block text-[9px] uppercase tracking-wider text-emerald-500">Suggested Factual Fix:</span>
                                &ldquo;{verification.suggested_fix}&rdquo;
                              </div>
                              <button
                                onClick={() => handleApplyFix(jobIdx, bulletIdx, verification.suggested_fix)}
                                className="px-2.5 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 font-semibold border border-amber-500/30 transition duration-150 whitespace-nowrap self-end md:self-center"
                              >
                                Apply Fix
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer controls */}
      <div className="flex flex-col md:flex-row justify-between items-center gap-4 pt-6 border-t border-slate-800">
        <button
          onClick={onReset}
          className="px-6 py-3 rounded-2xl border border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 transition font-medium text-sm w-full md:w-auto"
        >
          Back to Input
        </button>

        <button
          onClick={handleApprove}
          className="px-8 py-3 rounded-2xl bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white font-semibold text-sm transition shadow-lg shadow-emerald-500/10 flex items-center justify-center gap-2 w-full md:w-auto"
        >
          Confirm & Render Documents
        </button>
      </div>
    </div>
  );
}
