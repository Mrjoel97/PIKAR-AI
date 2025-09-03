import { createClient, SupabaseClient } from '@supabase/supabase-js'

// Expect Vite env vars in production. Do NOT expose service role keys in client code.
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  // Soft warning to help configuration; avoid crashing in dev
  console.warn('Supabase env not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY')
}

export const supabase: SupabaseClient = createClient(
  SUPABASE_URL || 'https://example.supabase.co',
  SUPABASE_ANON_KEY || 'anon-key-placeholder'
)

export default supabase

