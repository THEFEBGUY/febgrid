import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL?.trim();
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY?.trim();

export const isSupabaseMagicLinkAvailable = Boolean(supabaseUrl && supabaseAnonKey);

let client: SupabaseClient | null = null;

export function getSupabaseClient(): SupabaseClient | null {
  if (!isSupabaseMagicLinkAvailable || !supabaseUrl || !supabaseAnonKey) return null;
  client ??= createClient(supabaseUrl, supabaseAnonKey, {
    auth: { detectSessionInUrl: true, persistSession: true },
  });
  return client;
}
