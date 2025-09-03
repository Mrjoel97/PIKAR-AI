---
type: "always_apply"
---

# Pikar AI Core Migration: Base44 to Vercel AI + Supabase Backend

You are an expert full-stack developer tasked with performing a critical migration of the Pikar AI application. Your mission is to completely eliminate Base44 SDK and establish a production-ready backend infrastructure.

## 🎯 MISSION OBJECTIVES

### Primary Goals:
1. **ELIMINATE** every trace of Base44 SDK from the codebase
2. **REPLACE** with Vercel AI SDK + OpenAI integration
3. **MIGRATE** to Supabase backend with full production setup
4. **PRESERVE** existing functionality and codebase structure
5. **PREPARE** for production while enabling future enhancements

## 🔍 PHASE 1: BASE44 SDK COMPLETE ERADICATION

### 1.1 Deep Code Analysis
```bash
# Search commands to identify ALL Base44 references:
grep -r "base44" . --include="*.js" --include="*.ts" --include="*.jsx" --include="*.tsx"
grep -r "Base44" . --include="*.json" --include="*.md" --include="*.yml" --include="*.yaml"
find . -name "*base44*" -type f
find . -name "*Base44*" -type f
```

### 1.2 Complete Removal Checklist
- [ ] Remove Base44 from package.json dependencies
- [ ] Remove Base44 from package-lock.json/yarn.lock
- [ ] Delete all Base44 import statements
- [ ] Remove Base44 configuration files
- [ ] Delete Base44 utility functions
- [ ] Remove Base44 environment variables
- [ ] Clean Base44 from TypeScript types/interfaces
- [ ] Remove Base44 from documentation/comments
- [ ] Delete any Base44 test files
- [ ] Clear Base44 from build configurations

### 1.3 Verification Protocol
```bash
# After removal, verify ZERO results from:
grep -r "base44\|Base44" . --exclude-dir=node_modules
```

## 🚀 PHASE 2: VERCEL AI SDK + OPENAI INTEGRATION

### 2.1 Installation & Setup
```bash
npm install ai @ai-sdk/openai
npm install @vercel/ai-sdk
npm uninstall base44  # Ensure complete removal
```

### 2.2 OpenAI Configuration
```typescript
// lib/ai-config.ts
import { openai } from '@ai-sdk/openai';

export const aiConfig = {
  model: openai('gpt-4-turbo-preview'), // or your preferred model
  apiKey: process.env.OPENAI_API_KEY,
  maxTokens: 4096,
  temperature: 0.7
};
```

### 2.3 Core AI Integration Pattern
```typescript
// Replace ALL Base44 usage with this pattern:
import { generateText, streamText } from 'ai';
import { aiConfig } from '@/lib/ai-config';

// For text generation
const result = await generateText({
  model: aiConfig.model,
  prompt: 'Your prompt here',
  maxTokens: aiConfig.maxTokens,
  temperature: aiConfig.temperature
});

// For streaming responses
const { textStream } = await streamText({
  model: aiConfig.model,
  prompt: 'Your prompt here'
});
```

### 2.4 Component Migration Strategy
- **Identify** every component using Base44
- **Map** Base44 functions to Vercel AI SDK equivalents
- **Replace** incrementally, testing each component
- **Maintain** existing props and interfaces where possible
- **Update** TypeScript types for new AI responses

## 🗄️ PHASE 3: SUPABASE BACKEND MIGRATION

### 3.1 Supabase Project Setup
```bash
npm install @supabase/supabase-js
npm install @supabase/auth-helpers-nextjs  # if using Next.js
```

### 3.2 Environment Configuration
```env
# .env.local
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
OPENAI_API_KEY=your_openai_api_key
```

### 3.3 Supabase Client Setup
```typescript
// lib/supabase.ts
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// For server-side operations
export const supabaseAdmin = createClient(
  supabaseUrl,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  {
    auth: {
      autoRefreshToken: false,
      persistSession: false
    }
  }
);
```

### 3.4 Database Schema Design

#### Core Tables Structure:
```sql
-- Users table (extends Supabase auth.users)
CREATE TABLE public.profiles (
  id UUID REFERENCES auth.users ON DELETE CASCADE,
  username TEXT UNIQUE,
  full_name TEXT,
  avatar_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  PRIMARY KEY (id)
);

-- Projects/Sessions table
CREATE TABLE public.projects (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  settings JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- AI Conversations table
CREATE TABLE public.conversations (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE,
  messages JSONB[] DEFAULT '{}',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- App-specific tables (add based on your Pikar AI features)
-- Add your domain-specific tables here
```

### 3.5 Row Level Security (RLS)
```sql
-- Enable RLS on all tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

-- Policies for profiles
CREATE POLICY "Users can view own profile" ON public.profiles
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.profiles
  FOR UPDATE USING (auth.uid() = id);

-- Policies for projects
CREATE POLICY "Users can view own projects" ON public.projects
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create own projects" ON public.projects
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own projects" ON public.projects
  FOR UPDATE USING (auth.uid() = user_id);

-- Policies for conversations
CREATE POLICY "Users can view own conversations" ON public.conversations
  FOR SELECT USING (
    auth.uid() IN (
      SELECT user_id FROM public.projects WHERE id = project_id
    )
  );
```

### 3.6 Database Functions & Triggers
```sql
-- Updated timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to all tables
CREATE TRIGGER update_profiles_updated_at 
  BEFORE UPDATE ON public.profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at 
  BEFORE UPDATE ON public.projects
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Profile creation trigger
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, avatar_url)
  VALUES (NEW.id, NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'avatar_url');
  RETURN NEW;
END;
$$ language 'plpgsql' SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

### 3.7 Authentication Setup
```typescript
// lib/auth.ts
import { supabase } from './supabase';

export const auth = {
  signUp: async (email: string, password: string, metadata?: any) => {
    return await supabase.auth.signUp({
      email,
      password,
      options: {
        data: metadata
      }
    });
  },

  signIn: async (email: string, password: string) => {
    return await supabase.auth.signInWithPassword({
      email,
      password
    });
  },

  signOut: async () => {
    return await supabase.auth.signOut();
  },

  getCurrentUser: async () => {
    return await supabase.auth.getUser();
  }
};
```

### 3.8 API Layer Setup
```typescript
// lib/api.ts - Centralized API functions
export const api = {
  // Projects
  async createProject(data: ProjectData) {
    const { data: result, error } = await supabase
      .from('projects')
      .insert(data)
      .select()
      .single();
    
    if (error) throw error;
    return result;
  },

  async getProjects(userId: string) {
    const { data, error } = await supabase
      .from('projects')
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: false });
    
    if (error) throw error;
    return data;
  },

  // AI Conversations
  async saveConversation(projectId: string, messages: any[]) {
    const { data, error } = await supabase
      .from('conversations')
      .insert({
        project_id: projectId,
        messages: messages
      })
      .select()
      .single();
    
    if (error) throw error;
    return data;
  },

  // Add more API functions based on your app's needs
};
```

## ⚠️ CRITICAL MIGRATION REQUIREMENTS

### Code Integrity Rules
1. **NEVER** break existing component interfaces
2. **PRESERVE** all current functionality during migration
3. **MAINTAIN** existing file structure and organization
4. **TEST** each migrated component before proceeding
5. **BACKUP** critical data before database migration

### Quality Assurance Protocol
```typescript
// Add comprehensive error handling
try {
  const result = await aiFunction();
  return result;
} catch (error) {
  console.error('AI operation failed:', error);
  // Implement fallback or graceful degradation
  throw new Error('AI service temporarily unavailable');
}
```

### Production Readiness Checklist
- [ ] All Base44 references completely removed
- [ ] Vercel AI SDK fully integrated with OpenAI
- [ ] Supabase database schema deployed
- [ ] Authentication system functional
- [ ] RLS policies properly configured
- [ ] API endpoints tested and working
- [ ] Error handling implemented
- [ ] Environment variables configured
- [ ] Type safety maintained
- [ ] Performance optimizations in place

## 🎯 SUCCESS VERIFICATION

### Final Validation Tests
1. **Zero Base44**: `grep -r "base44\|Base44" . --exclude-dir=node_modules` returns nothing
2. **AI Functionality**: All AI features work with OpenAI through Vercel AI SDK
3. **Backend Operations**: Database CRUD operations function correctly
4. **Authentication**: User signup, login, and session management work
5. **Data Integrity**: All existing data successfully migrated
6. **Performance**: Application performance maintained or improved

## 🔮 FUTURE-READY ARCHITECTURE

### Scalable Structure
- Modular component architecture
- Centralized API layer for easy expansion
- Flexible database schema for new features
- Comprehensive TypeScript types
- Clean separation of concerns

### Enhancement Ready
- Easy addition of new AI models
- Simple integration of additional Supabase features
- Extensible authentication with OAuth providers
- Scalable database design for growing data needs
- Clean codebase for team collaboration

Execute this migration methodically, testing each phase thoroughly before proceeding. The goal is a clean, production-ready Pikar AI application with zero Base44 remnants and a robust Supabase backend foundation.