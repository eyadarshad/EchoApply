"use client";

import React from "react";
import { Toaster } from "sonner";
import { ThemeProvider } from "../components/ThemeContext";
import ThreeBackground from "../components/ThreeBackground";
import ErrorBoundary from "../components/ErrorBoundary";
import { AuthProvider } from "../context/AuthContext";
import CustomCursor from "../components/CustomCursor";
import PretextCuteSnake from "../components/PretextCuteSnake";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";

/**
 * Client-side layout providers wrapper.
 * Wraps children with: ErrorBoundary → AuthProvider → ThemeProvider → ThreeBackground → PretextCuteSnake → Toaster → CustomCursor → AnimatePresence (Transitions)
 */
export default function Providers({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <ErrorBoundary>
      <AuthProvider>
        <ThemeProvider>
          <ThreeBackground />
          <PretextCuteSnake />
          <CustomCursor />
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: "var(--toast-bg, #1e293b)",
                border: "1px solid var(--toast-border, #334155)",
                color: "var(--toast-text, #f1f5f9)",
                fontSize: "13px",
                fontWeight: 500,
                borderRadius: "12px",
                boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
              },
            }}
            richColors
            closeButton
          />
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
              className="w-full min-h-screen"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </ThemeProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}
