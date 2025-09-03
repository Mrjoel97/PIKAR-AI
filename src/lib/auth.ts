import { supabase } from './supabase'

export const auth = {
  signUp: async (email: string, password: string, metadata?: any) => {
    return await supabase.auth.signUp({
      email,
      password,
      options: { data: metadata }
    })
  },
  signIn: async (email: string, password: string) => {
    return await supabase.auth.signInWithPassword({ email, password })
  },
  signOut: async () => {
    return await supabase.auth.signOut()
  },
  getCurrentUser: async () => {
    return await supabase.auth.getUser()
  }
}

export default auth

