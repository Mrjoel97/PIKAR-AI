-- PIKAR AI Core Schema (Supabase)

-- Extensions
create extension if not exists pgcrypto;
create extension if not exists "uuid-ossp";

-- Profiles
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text unique,
  full_name text,
  avatar_url text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Projects
create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade,
  name text not null,
  description text,
  settings jsonb default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Conversations
create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects(id) on delete cascade,
  messages jsonb[] default '{}',
  metadata jsonb default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Social Marketing (core subset)
create table if not exists public.social_campaigns (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade,
  campaign_name text not null,
  brand text,
  objective text,
  platforms text[],
  generated_plan jsonb,
  status text default 'draft',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.social_ad_variants (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid references public.social_campaigns(id) on delete cascade,
  platform text,
  variant_name text,
  headline text,
  body text,
  cta text,
  creative_idea text,
  hypothesis text,
  status text default 'draft',
  metrics jsonb default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.social_posts (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid references public.social_campaigns(id) on delete cascade,
  platform text,
  content text,
  media_idea text,
  scheduled_time timestamptz,
  timezone text,
  status text default 'planned',
  metrics jsonb default '{}',
  published_at timestamptz,
  last_result jsonb,
  last_error text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Row Level Security
alter table public.profiles enable row level security;
alter table public.projects enable row level security;
alter table public.conversations enable row level security;
alter table public.social_campaigns enable row level security;
alter table public.social_ad_variants enable row level security;
alter table public.social_posts enable row level security;

-- Policies
create policy "profiles_select_own" on public.profiles for select using (auth.uid() = id);
create policy "profiles_update_own" on public.profiles for update using (auth.uid() = id);

create policy "projects_select_own" on public.projects for select using (auth.uid() = user_id);
create policy "projects_insert_own" on public.projects for insert with check (auth.uid() = user_id);
create policy "projects_update_own" on public.projects for update using (auth.uid() = user_id);

create policy "campaigns_select_own" on public.social_campaigns for select using (auth.uid() = user_id);
create policy "campaigns_insert_own" on public.social_campaigns for insert with check (auth.uid() = user_id);
create policy "campaigns_update_own" on public.social_campaigns for update using (auth.uid() = user_id);

create policy "ad_variants_select" on public.social_ad_variants for select using (
  auth.uid() in (select user_id from public.social_campaigns where id = campaign_id)
);
create policy "ad_variants_insert" on public.social_ad_variants for insert with check (
  auth.uid() in (select user_id from public.social_campaigns where id = campaign_id)
);
create policy "ad_variants_update" on public.social_ad_variants for update using (
  auth.uid() in (select user_id from public.social_campaigns where id = campaign_id)
);

create policy "posts_select" on public.social_posts for select using (
  auth.uid() in (select user_id from public.social_campaigns where id = campaign_id)
);
create policy "posts_insert" on public.social_posts for insert with check (
  auth.uid() in (select user_id from public.social_campaigns where id = campaign_id)
);
create policy "posts_update" on public.social_posts for update using (
  auth.uid() in (select user_id from public.social_campaigns where id = campaign_id)
);

-- Triggers for updated_at
create or replace function public.update_updated_at_column() returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language 'plpgsql';

create trigger update_profiles_updated_at before update on public.profiles for each row execute function public.update_updated_at_column();
create trigger update_projects_updated_at before update on public.projects for each row execute function public.update_updated_at_column();
create trigger update_social_campaigns_updated_at before update on public.social_campaigns for each row execute function public.update_updated_at_column();
create trigger update_social_ad_variants_updated_at before update on public.social_ad_variants for each row execute function public.update_updated_at_column();
create trigger update_social_posts_updated_at before update on public.social_posts for each row execute function public.update_updated_at_column();

-- Profile creation trigger from auth.users
create or replace function public.handle_new_user() returns trigger as $$
begin
  insert into public.profiles (id, full_name, avatar_url) values (new.id, new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'avatar_url');
  return new;
end;
$$ language 'plpgsql' security definer;

create trigger on_auth_user_created after insert on auth.users for each row execute function public.handle_new_user();

