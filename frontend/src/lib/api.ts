/**
 * Centralized API client for all backend communication.
 * 
 * Single source of truth for:
 * - Backend URL resolution (env-driven, never hardcoded)
 * - WebSocket URL derivation  
 * - Auth token injection (when auth is enabled)
 * - Request error handling
 */

import { supabase } from "./supabaseClient";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

/**
 * Get the backend base URL. Always use this instead of hardcoding localhost.
 */
export function getBackendUrl(): string {
  return BACKEND_URL;
}

/**
 * Get the WebSocket base URL derived from the HTTP backend URL.
 * Swaps http:// → ws:// and https:// → wss://
 */
export function getWsUrl(): string {
  return BACKEND_URL.replace(/^http/, "ws");
}

/**
 * Automatically refresh Supabase token if needed.
 */
async function refreshTokenIfNeeded(): Promise<void> {
  if (supabase) {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        localStorage.setItem("supabase_access_token", session.access_token);
        localStorage.setItem("user_id", session.user.id);
        localStorage.setItem("userId", session.user.id);
      }
    } catch (e) {
      console.error("Failed to automatically refresh Supabase session:", e);
    }
  }
}

/**
 * Get the stored auth token from localStorage (if any).
 */
function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("supabase_access_token");
}

/**
 * Build request headers with optional auth token injection.
 */
export function getAuthHeaders(extraHeaders?: Record<string, string>, isFormData?: boolean): Record<string, string> {
  const headers: Record<string, string> = {};

  if (!isFormData) {
    headers["Content-Type"] = "application/json";
  }

  if (extraHeaders) {
    Object.assign(headers, extraHeaders);
  }

  const token = getAuthToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (typeof window !== "undefined") {
    const devUserId = localStorage.getItem("user_id");
    if (devUserId) {
      headers["X-Dev-User-Id"] = devUserId;
    }
  }

  return headers;
}

/**
 * Typed fetch wrapper that handles:
 * - Backend URL resolution
 * - Auth token injection
 * - JSON parsing
 * - Error normalization
 */
export async function apiFetch<T = any>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  await refreshTokenIfNeeded();
  
  const url = `${BACKEND_URL}${path}`;
  
  const headers = getAuthHeaders(
    options.headers as Record<string, string> | undefined
  );

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (options.body instanceof FormData) {
    delete headers["Content-Type"];
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err: any) {
    if (err.name === "AbortError" || (err.message && err.message.toLowerCase().includes("abort"))) {
      throw new Error("aborted");
    }
    throw new Error("Unable to connect to the server. Please check if the backend is running and try again.");
  }

  if (!response.ok) {
    const errorBody = await response.text();
    let detail = `API Error ${response.status}`;
    try {
      const parsed = JSON.parse(errorBody);
      if (typeof parsed.detail === "string") {
        detail = parsed.detail;
      } else if (Array.isArray(parsed.detail)) {
        detail = parsed.detail.map((err: any) => err.msg || JSON.stringify(err)).join(", ");
      } else if (parsed.detail && typeof parsed.detail === "object") {
        detail = parsed.detail.message || parsed.detail.detail || JSON.stringify(parsed.detail);
      } else if (parsed.message) {
        detail = parsed.message;
      } else {
        detail = JSON.stringify(parsed);
      }
    } catch {
      detail = errorBody || detail;
    }
    throw new Error(detail);
  }

  // Handle non-JSON responses (PDFs, DOCX files)
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  
  // Return the response itself for binary downloads
  return response as unknown as T;
}

/**
 * Upload a file to the backend using multipart/form-data.
 */
export async function apiUpload<T = any>(
  path: string,
  file: File,
  fieldName: string = "file"
): Promise<T> {
  const formData = new FormData();
  formData.append(fieldName, file);

  return apiFetch<T>(path, {
    method: "POST",
    body: formData,
  });
}
