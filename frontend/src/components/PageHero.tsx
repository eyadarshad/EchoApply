"use client";

import React from "react";
import Link from "next/link";
import { ChevronRight, ArrowLeft } from "lucide-react";
import KineticText from "./KineticText";

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface PageHeroProps {
  badge?: string;
  title: string;
  subtitle?: string;
  breadcrumbs?: BreadcrumbItem[];
  backHref?: string;
  backLabel?: string;
  children?: React.ReactNode;
  align?: "center" | "left";
}

export default function PageHero({
  badge,
  title,
  subtitle,
  breadcrumbs,
  backHref,
  backLabel,
  children,
  align = "center",
}: PageHeroProps) {
  const isCentered = align === "center";

  return (
    <section className={`relative w-full max-w-4xl pt-4 pb-8 space-y-4 ${isCentered ? "text-center mx-auto" : "text-left"}`}>
      {/* Decorative Blur Glows */}
      <div className="accent-glow-spot -top-10 left-1/4 animate-pulse" style={{ animationDuration: "10s" }} />

      {/* Navigation: Back link & Breadcrumbs */}
      <div className={`flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-2 ${isCentered ? "justify-center" : "justify-start"}`}>
        {backHref && (
          <Link
            href={backHref}
            className="inline-flex items-center gap-1 text-teal-600 dark:text-teal-400 hover:text-teal-700 dark:hover:text-teal-300 font-medium transition-colors mr-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            {backLabel || "Back"}
          </Link>
        )}

        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav aria-label="Breadcrumb" className="inline-flex items-center gap-1.5">
            {breadcrumbs.map((item, idx) => (
              <React.Fragment key={idx}>
                {idx > 0 && <ChevronRight className="w-3 h-3 text-slate-400" />}
                {item.href ? (
                  <Link href={item.href} className="hover:text-teal-500 transition-colors">
                    {item.label}
                  </Link>
                ) : (
                  <span className="text-slate-800 dark:text-slate-200 font-semibold">{item.label}</span>
                )}
              </React.Fragment>
            ))}
          </nav>
        )}
      </div>

      {/* Badge */}
      {badge && (
        <div className={`flex ${isCentered ? "justify-center" : "justify-start"}`}>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-teal-500/20 bg-teal-500/10 text-teal-600 dark:text-teal-400 text-xs font-semibold uppercase tracking-wider shadow-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse" />
            {badge}
          </span>
        </div>
      )}

      {/* Title with Kinetic Character Rise */}
      <KineticText
        as="h1"
        animation="hero-rise"
        duration={0.85}
        className="text-3xl md:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white leading-tight"
      >
        {title}
      </KineticText>

      {/* Subtitle with Word Fade */}
      {subtitle && (
        <KineticText
          as="p"
          animation="word-fade"
          delay={0.2}
          duration={0.7}
          className={`text-slate-600 dark:text-slate-400 text-sm md:text-base font-light leading-relaxed max-w-2xl ${isCentered ? "mx-auto" : ""}`}
        >
          {subtitle}
        </KineticText>
      )}

      {/* Optional Custom Slots (CTAs, stats) */}
      {children && <div className={`pt-2 ${isCentered ? "flex justify-center" : ""}`}>{children}</div>}
    </section>
  );
}
