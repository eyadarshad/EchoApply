"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Global Error Boundary — catches unhandled React component errors
 * and displays a graceful recovery UI instead of a white screen.
 */
export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    console.error("[ErrorBoundary] Caught error:", error, errorInfo);

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
      const user_id = typeof window !== "undefined" ? localStorage.getItem("user_id") || undefined : undefined;

      fetch(`${backendUrl}/api/errors/log`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          error_name: error.name || "Error",
          error_message: error.message || "Unknown error occurred",
          stack_trace: errorInfo.componentStack || error.stack || undefined,
          url: typeof window !== "undefined" ? window.location.href : undefined,
          user_id: user_id,
        }),
      }).catch((fetchErr) => {
        console.warn("[ErrorBoundary] Failed to send logs to backend:", fetchErr);
      });
    } catch (reportErr) {
      console.warn("[ErrorBoundary] Error during reporting handler:", reportErr);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center p-8">
          <div className="max-w-md w-full text-center space-y-6">
            {/* Icon */}
            <div className="mx-auto w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
              <AlertTriangle className="w-8 h-8 text-rose-500" />
            </div>

            {/* Title */}
            <div className="space-y-2">
              <h2 className="text-xl font-bold text-slate-800 dark:text-slate-200">
                Something went wrong
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                An unexpected error occurred. Your data is safe — try refreshing the page.
              </p>
            </div>

            {/* Error details (collapsible) */}
            {this.state.error && (
              <details className="text-left bg-slate-100 dark:bg-slate-900/50 rounded-xl p-4 border border-slate-200 dark:border-slate-800">
                <summary className="text-xs font-semibold text-slate-500 cursor-pointer hover:text-slate-700 dark:hover:text-slate-300">
                  Technical Details
                </summary>
                <pre className="mt-3 text-[10px] text-rose-500 dark:text-rose-400 overflow-auto max-h-32 font-mono leading-relaxed">
                  {this.state.error.message}
                  {this.state.errorInfo?.componentStack && (
                    <>
                      {"\n\nComponent Stack:"}
                      {this.state.errorInfo.componentStack}
                    </>
                  )}
                </pre>
              </details>
            )}

            {/* Actions */}
            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleReset}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-sm font-semibold transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>
              <button
                onClick={() => window.location.reload()}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-sm font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
              >
                Reload Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

