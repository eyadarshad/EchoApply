"use client";

import React from "react";

/**
 * Reusable skeleton pulse animation base.
 * Uses CSS animation for smooth shimmer effect.
 */
function SkeletonPulse({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-lg bg-gradient-to-r from-slate-200 via-slate-100 to-slate-200 dark:from-slate-800 dark:via-slate-700 dark:to-slate-800 bg-[length:200%_100%] ${className}`}
      style={{
        animation: "shimmer 1.5s ease-in-out infinite",
      }}
    />
  );
}

/**
 * Job card skeleton — mimics the shape of a loaded JobCard component.
 */
export function JobCardSkeleton() {
  return (
    <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 space-y-3">
      {/* Title row */}
      <div className="flex justify-between items-start">
        <SkeletonPulse className="h-4 w-3/5" />
        <SkeletonPulse className="h-5 w-16 rounded-full" />
      </div>
      {/* Company */}
      <SkeletonPulse className="h-3 w-2/5" />
      {/* Location */}
      <SkeletonPulse className="h-3 w-1/3" />
      {/* Tags row */}
      <div className="flex gap-2 pt-1">
        <SkeletonPulse className="h-6 w-20 rounded-full" />
        <SkeletonPulse className="h-6 w-24 rounded-full" />
        <SkeletonPulse className="h-6 w-16 rounded-full" />
      </div>
      {/* Footer */}
      <div className="flex justify-between items-center pt-2 border-t border-slate-100 dark:border-slate-800">
        <SkeletonPulse className="h-3 w-24" />
        <SkeletonPulse className="h-8 w-20 rounded-lg" />
      </div>
    </div>
  );
}

/**
 * Grid of job card skeletons for loading state.
 */
export function JobSearchSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <JobCardSkeleton key={i} />
      ))}
    </div>
  );
}

/**
 * Profile section skeleton — mimics parsed resume display.
 */
export function ProfileSkeleton() {
  return (
    <div className="space-y-6 p-6 rounded-2xl border border-slate-200 dark:border-slate-800">
      {/* Header */}
      <div className="flex items-center gap-4">
        <SkeletonPulse className="w-14 h-14 rounded-full" />
        <div className="space-y-2 flex-1">
          <SkeletonPulse className="h-5 w-48" />
          <SkeletonPulse className="h-3 w-36" />
        </div>
      </div>
      {/* Skills */}
      <div className="space-y-2">
        <SkeletonPulse className="h-3 w-16" />
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonPulse key={i} className="h-6 w-20 rounded-full" />
          ))}
        </div>
      </div>
      {/* Experience */}
      <div className="space-y-3">
        <SkeletonPulse className="h-3 w-24" />
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="space-y-2 pl-4 border-l-2 border-slate-200 dark:border-slate-800">
            <SkeletonPulse className="h-4 w-56" />
            <SkeletonPulse className="h-3 w-40" />
            <SkeletonPulse className="h-3 w-full" />
            <SkeletonPulse className="h-3 w-4/5" />
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Tracker board column skeleton.
 */
export function TrackerColumnSkeleton() {
  return (
    <div className="flex flex-col rounded-2xl bg-slate-100/60 dark:bg-slate-900/10 border border-slate-200 dark:border-slate-800/80 p-4 min-h-[300px]">
      <SkeletonPulse className="h-8 w-full rounded-xl mb-4" />
      <div className="space-y-3">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 space-y-2">
            <SkeletonPulse className="h-3 w-4/5" />
            <SkeletonPulse className="h-3 w-3/5" />
            <SkeletonPulse className="h-3 w-1/3" />
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Tracker board full skeleton.
 */
export function TrackerBoardSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {Array.from({ length: 4 }).map((_, i) => (
        <TrackerColumnSkeleton key={i} />
      ))}
    </div>
  );
}

/**
 * Inline text skeleton for single-line loading states.
 */
export function TextSkeleton({ width = "w-32" }: { width?: string }) {
  return <SkeletonPulse className={`h-4 ${width} inline-block`} />;
}
