"use client";

import React, { useEffect, useState } from "react";
import { Check, ArrowRight, Loader2, Sparkles, Shield, Zap, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { getBackendUrl, getAuthHeaders } from "../../lib/api";

const TIERS = [
  {
    id: "free",
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Perfect for casual job seekers looking to optimize a few resumes.",
    features: [
      "1 ATS-Friendly Template (Classic)",
      "Job search with semantic match ranking",
      "Up to 3 tailored resumes per month",
      "Mock auto-apply simulation",
      "Save up to 5 jobs to tracking board"
    ],
    cta: "Current Plan",
    icon: Shield,
    color: "from-slate-500 to-slate-700"
  },
  {
    id: "pro",
    name: "Pro",
    price: "$19",
    period: "per month",
    description: "Accelerate your search with agentic auto-applying and cover letters.",
    features: [
      "All 5 Styled Templates (Classic, Modern, Minimal, Creative, Executive)",
      "Unrestricted AI resume tailoring & suggestions",
      "AI Cover Letter Generator",
      "Automated Playwright auto-apply bot",
      "Sync session credentials (LinkedIn, Indeed, Glassdoor)",
      "Analytics tracking & mock interview prep modules"
    ],
    cta: "Upgrade to Pro",
    popular: true,
    icon: Zap,
    color: "from-teal-500 to-violet-600"
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: "$49",
    period: "per month",
    description: "Power tools for career coaches and professional recruiting teams.",
    features: [
      "Everything in Pro",
      "Unlimited simultaneous candidate profiles",
      "Dedicated high-throughput Chrome sync gateway",
      "Custom screening question semantic memory rules",
      "API access & bulk resume imports",
      "Priority customer support"
    ],
    cta: "Go Enterprise",
    icon: Sparkles,
    color: "from-amber-500 to-rose-600"
  }
];

export default function BillingPage() {
  const [userId, setUserId] = useState<string>("");
  const [currentTier, setCurrentTier] = useState<string>("free");
  const [subStatus, setSubStatus] = useState<string>("active");
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [upgrading, setUpgrading] = useState<string | null>(null);

  useEffect(() => {
    // Retrieve stored user ID
    const storedUserId = localStorage.getItem("userId") || "00000000-0000-0000-0000-000000000001";
    setUserId(storedUserId);
    fetchBillingStatus(storedUserId);
  }, []);

  const fetchBillingStatus = async (uid: string) => {
    try {
      const res = await fetch(`${getBackendUrl()}/api/billing/status?user_id=${uid}`, {
        headers: getAuthHeaders()
      });
      if (res.ok) {
        const data = await res.json();
        setCurrentTier(data.tier);
        setSubStatus(data.status);
        setExpiresAt(data.expires_at);
      }
    } catch (err) {
      console.error("Error fetching billing status:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (tierId: string) => {
    if (tierId === currentTier) {
      toast.info(`You are already on the ${tierId} plan.`);
      return;
    }
    
    setUpgrading(tierId);
    try {
      const res = await fetch(`${getBackendUrl()}/api/billing/checkout`, {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          user_id: userId,
          tier: tierId,
          success_url: window.location.origin + "/billing",
          cancel_url: window.location.href
        })
      });

      if (!res.ok) throw new Error("Checkout session creation failed.");
      const data = await res.json();
      
      toast.success(`Redirecting to upgrade portal...`);
      // In mock mode, this immediately updates subscription and returns a success redirect URL
      window.location.href = data.checkout_url;
    } catch (err: any) {
      toast.error(err.message || "Failed to initiate upgrade.");
      setUpgrading(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100">
        <Loader2 className="w-8 h-8 animate-spin text-teal-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-teal-950 text-slate-100 py-16 px-4">
      <div className="max-w-6xl mx-auto space-y-12">
        <div className="text-center space-y-4">
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-teal-200 via-teal-100 to-purple-200">
            SaaS Subscription Pricing
          </h1>
          <p className="text-slate-400 max-w-xl mx-auto text-sm md:text-base">
            Select the plan that fits your career goals. Upgrade or cancel anytime.
          </p>

          {currentTier !== "free" && (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-teal-500/10 border border-teal-500/20 text-xs font-semibold text-teal-400">
              <Zap className="w-3.5 h-3.5" />
              Active Plan: <span className="uppercase font-bold">{currentTier}</span> ({subStatus})
              {expiresAt && ` — Renews: ${new Date(expiresAt).toLocaleDateString()}`}
            </div>
          )}
        </div>

        <div className="grid md:grid-cols-3 gap-8 items-stretch">
          {TIERS.map((tier) => {
            const Icon = tier.icon;
            const isCurrent = tier.id === currentTier;
            return (
              <div
                key={tier.id}
                className={`relative rounded-3xl p-6 bg-slate-900/40 backdrop-blur-md border transition-all flex flex-col justify-between ${
                  tier.popular
                    ? "border-teal-500/60 shadow-teal-500/10 shadow-2xl scale-[1.02]"
                    : "border-slate-800 hover:border-slate-700"
                }`}
              >
                {tier.popular && (
                  <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-[10px] font-extrabold tracking-widest bg-gradient-to-r from-teal-500 to-purple-500 text-white uppercase shadow">
                    Most Popular
                  </span>
                )}

                <div className="space-y-6">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-xl bg-gradient-to-br ${tier.color} text-white`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-slate-100">{tier.name}</h3>
                      <p className="text-slate-400 text-xs">{tier.price} / {tier.period}</p>
                    </div>
                  </div>

                  <p className="text-xs text-slate-400 leading-relaxed">{tier.description}</p>
                  
                  <div className="border-t border-slate-800/80 pt-4 space-y-3">
                    {tier.features.map((feature, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-xs text-slate-300">
                        <Check className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                        <span>{feature}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mt-8 pt-4">
                  <button
                    onClick={() => handleUpgrade(tier.id)}
                    disabled={isCurrent || upgrading !== null}
                    className={`w-full py-3 px-4 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition ${
                      isCurrent
                        ? "bg-slate-800 text-slate-400 cursor-default"
                        : tier.popular
                        ? "bg-gradient-to-r from-teal-600 to-purple-600 hover:opacity-90 text-white shadow-lg shadow-teal-500/20"
                        : "bg-slate-800 hover:bg-slate-750 text-slate-200"
                    }`}
                  >
                    {upgrading === tier.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : isCurrent ? (
                      "Current Active Plan"
                    ) : (
                      <>
                        {tier.cta}
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        <div className="text-center">
          <a
            href="/"
            className="text-xs font-semibold text-teal-400 hover:text-teal-300 flex items-center justify-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Return to Dashboard
          </a>
        </div>
      </div>
    </div>
  );
}

