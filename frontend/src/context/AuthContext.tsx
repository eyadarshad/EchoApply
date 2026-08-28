"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "../lib/supabaseClient";
import { getBackendUrl } from "../lib/api";

export interface UserContextType {
  user_id: string | null;
  email: string | null;
  loading: boolean;
  isDevMode: boolean;
  login: (email: string, pass: string) => Promise<void>;
  signup: (email: string, pass: string) => Promise<void>;
  logout: () => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  resetPassword: (newPassword: string) => Promise<void>;
  getValidToken: () => Promise<string | null>;
}

const AuthContext = createContext<UserContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [userId, setUserId] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isDevMode, setIsDevMode] = useState<boolean>(true);

  useEffect(() => {
    // Check if Supabase keys exist and client is available
    if (supabase) {
      setIsDevMode(false);
      
      // Load initial session
      supabase.auth.getSession().then(({ data: { session } }) => {
        if (session) {
          setUserId(session.user.id);
          setEmail(session.user.email || null);
          localStorage.setItem("supabase_access_token", session.access_token);
          localStorage.setItem("user_id", session.user.id);
          localStorage.setItem("userId", session.user.id); // duplicate key compatibility
        }
        setLoading(false);
      });

      // Listen for auth state updates
      const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
        if (session) {
          setUserId(session.user.id);
          setEmail(session.user.email || null);
          localStorage.setItem("supabase_access_token", session.access_token);
          localStorage.setItem("user_id", session.user.id);
          localStorage.setItem("userId", session.user.id);
        } else {
          setUserId(null);
          setEmail(null);
          localStorage.removeItem("supabase_access_token");
          localStorage.removeItem("user_id");
          localStorage.removeItem("userId");
        }
        setLoading(false);
      });

      return () => {
        subscription.unsubscribe();
      };
    } else {
      // Fallback: Sandbox Developer Mode
      loggerWarn("Supabase configurations not set. Booting in DEVELOPMENT/SANDBOX Authentication Mode.");
      setIsDevMode(true);
      const storedToken = localStorage.getItem("supabase_access_token");
      const storedDevId = localStorage.getItem("user_id") || localStorage.getItem("userId");
      
      if (storedDevId) {
        setUserId(storedDevId);
        setEmail("dev@localhost");
      }
      setLoading(false);
    }
  }, []);

  const login = async (emailInput: string, passInput: string) => {
    setLoading(true);
    try {
      if (supabase) {
        const { error, data } = await supabase.auth.signInWithPassword({
          email: emailInput,
          password: passInput,
        });
        if (error) throw error;
        if (data.session) {
          setUserId(data.session.user.id);
          setEmail(data.session.user.email || null);
        }
      } else {
        // Dev Sandbox Mock Login
        const mockId = generateMockUUID(emailInput);
        setUserId(mockId);
        setEmail(emailInput);
        localStorage.setItem("user_id", mockId);
        localStorage.setItem("userId", mockId);
        localStorage.setItem("supabase_access_token", "mock_dev_access_token");
        
        // Register user automatically in mock backend database if missing
        try {
          await fetch(`${getBackendUrl()}/profiles`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Dev-User-Id": mockId
            },
            body: JSON.stringify({
              user_id: mockId,
              parsed_resume: {
                name: emailInput.split("@")[0],
                email: emailInput,
                skills: [],
                education: [],
                experience: [],
                projects: []
              }
            })
          });
        } catch (err) {}
      }
    } finally {
      setLoading(false);
    }
  };

  const signup = async (emailInput: string, passInput: string) => {
    setLoading(true);
    try {
      if (supabase) {
        const { error } = await supabase.auth.signUp({
          email: emailInput,
          password: passInput,
        });
        if (error) throw error;
      } else {
        // Dev Sandbox Mock Signup
        const mockId = generateMockUUID(emailInput);
        setUserId(mockId);
        setEmail(emailInput);
        localStorage.setItem("user_id", mockId);
        localStorage.setItem("userId", mockId);
        localStorage.setItem("supabase_access_token", "mock_dev_access_token");

        // Save profile
        try {
          await fetch(`${getBackendUrl()}/profiles`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Dev-User-Id": mockId
            },
            body: JSON.stringify({
              user_id: mockId,
              parsed_resume: {
                name: emailInput.split("@")[0],
                email: emailInput,
                skills: [],
                education: [],
                experience: [],
                projects: []
              }
            })
          });
        } catch (err) {}
      }
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    setLoading(true);
    try {
      if (supabase) {
        await supabase.auth.signOut();
      }
      setUserId(null);
      setEmail(null);
      localStorage.removeItem("supabase_access_token");
      localStorage.removeItem("user_id");
      localStorage.removeItem("userId");
    } finally {
      setLoading(false);
    }
  };

  const forgotPassword = async (emailInput: string) => {
    setLoading(true);
    try {
      if (supabase) {
        const { error } = await supabase.auth.resetPasswordForEmail(emailInput, {
          redirectTo: window.location.origin + "/reset-password",
        });
        if (error) throw error;
      } else {
        // Dev Sandbox Mock
        console.log(`[Sandbox] Forgot password email simulated to: ${emailInput}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const resetPassword = async (newPassword: string) => {
    setLoading(true);
    try {
      if (supabase) {
        const { error } = await supabase.auth.updateUser({
          password: newPassword,
        });
        if (error) throw error;
      } else {
        // Dev Sandbox Mock
        console.log("[Sandbox] Password updated successfully.");
      }
    } finally {
      setLoading(false);
    }
  };

  const getValidToken = async (): Promise<string | null> => {
    if (!supabase) {
      return localStorage.getItem("supabase_access_token") || "mock_dev_access_token";
    }
    try {
      const { data: { session }, error } = await supabase.auth.getSession();
      if (error || !session) {
        return null;
      }
      localStorage.setItem("supabase_access_token", session.access_token);
      return session.access_token;
    } catch (err) {
      console.error("Error getting valid session token:", err);
      return null;
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user_id: userId,
        email,
        loading,
        isDevMode,
        login,
        signup,
        logout,
        forgotPassword,
        resetPassword,
        getValidToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

// Helpers
function generateMockUUID(email: string): string {
  // Return consistent UUIDs for mock testing users
  if (email === "dev@localhost") return "00000000-0000-0000-0000-000000000001";
  let hash = 0;
  for (let i = 0; i < email.length; i++) {
    hash = (hash << 5) - hash + email.charCodeAt(i);
    hash |= 0;
  }
  const hex = Math.abs(hash).toString(16).padStart(12, "0");
  return `00000000-0000-0000-0000-${hex}`;
}

function loggerWarn(msg: string) {
  console.warn(`[AuthContext] ${msg}`);
}
