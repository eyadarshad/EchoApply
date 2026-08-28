import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

const isValidUrl = (url?: string): boolean => {
  if (!url) return false;
  return url.startsWith("http://") || url.startsWith("https://");
};

// Export active supabase client if keys are set and valid, otherwise null (triggers dev fallback)
export const supabase = (isValidUrl(supabaseUrl) && supabaseAnonKey)
  ? createClient(supabaseUrl!, supabaseAnonKey)
  : null;
