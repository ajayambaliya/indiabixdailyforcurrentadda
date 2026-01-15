-- Supabase Schema for CurrentAdda

-- 1. Enable UUID extension if not enabled
create extension if not exists "uuid-ossp";

-- 2. Create Quizzes Table
create table if not exists public.quizzes (
    id uuid primary key default uuid_generate_v4(),
    title text not null,
    slug text not null unique,
    date_str text,
    quiz_date date,
    source_url text,
    created_at timestamptz default now()
);

-- 3. Create Questions Table
create table if not exists public.questions (
    id uuid primary key default uuid_generate_v4(),
    quiz_id uuid references public.quizzes(id) on delete cascade,
    q_index int not null,
    text text not null,
    options jsonb not null,
    answer char(1) not null,
    explanation text,
    category text,
    created_at timestamptz default now()
);

-- 4. Create Profiles Table (for user names)
create table if not exists public.profiles (
    id uuid references auth.users on delete cascade primary key,
    full_name text,
    avatar_url text,
    updated_at timestamptz default now()
);

-- 5. Create Scores Table
create table if not exists public.scores (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid references auth.users on delete cascade not null,
    quiz_id uuid references public.quizzes(id) on delete cascade not null,
    score int not null,
    total_questions int not null,
    created_at timestamptz default now()
);

-- 6. Set up Indexes
create index if not exists quizzes_slug_idx on public.quizzes(slug);
create index if not exists quizzes_date_idx on public.quizzes(quiz_date);
create index if not exists questions_quiz_id_idx on public.questions(quiz_id);
create index if not exists scores_user_id_idx on public.scores(user_id);
create index if not exists scores_quiz_id_idx on public.scores(quiz_id);

-- 7. Enable Row Level Security (RLS)
alter table public.quizzes enable row level security;
alter table public.questions enable row level security;
alter table public.profiles enable row level security;
alter table public.scores enable row level security;

-- 8. Policies for Quizzes (Public Read)
do $$ 
begin
    if not exists (select 1 from pg_policies where policyname = 'Allow public read access for quizzes') then
        create policy "Allow public read access for quizzes" on public.quizzes for select using (true);
    end if;
    if not exists (select 1 from pg_policies where policyname = 'Allow insert for authenticated users on quizzes') then
        create policy "Allow insert for authenticated users on quizzes" on public.quizzes for insert with check (true);
    end if;
    if not exists (select 1 from pg_policies where policyname = 'Allow update for authenticated users on quizzes') then
        create policy "Allow update for authenticated users on quizzes" on public.quizzes for update using (true);
    end if;
end $$;

-- 9. Policies for Questions (Auth Required)
do $$ 
begin
    if not exists (select 1 from pg_policies where policyname = 'Allow auth read access for questions') then
        create policy "Allow auth read access for questions" on public.questions for select using (auth.role() = 'authenticated');
    end if;
    if not exists (select 1 from pg_policies where policyname = 'Allow insert for authenticated users on questions') then
        create policy "Allow insert for authenticated users on questions" on public.questions for insert with check (true);
    end if;
end $$;

-- 10. Policies for Profiles
do $$ 
begin
    if not exists (select 1 from pg_policies where policyname = 'Users can view all profiles') then
        create policy "Users can view all profiles" on public.profiles for select using (true);
    end if;
    if not exists (select 1 from pg_policies where policyname = 'Users can update own profile') then
        create policy "Users can update own profile" on public.profiles for update using (auth.uid() = id);
    end if;
end $$;

-- 11. Policies for Scores
do $$ 
begin
    if not exists (select 1 from pg_policies where policyname = 'Users can view all scores') then
        create policy "Users can view all scores" on public.scores for select using (true);
    end if;
    if not exists (select 1 from pg_policies where policyname = 'Users can insert own scores') then
        create policy "Users can insert own scores" on public.scores for insert with check (auth.uid() = user_id);
    end if;
end $$;

-- 12. Trigger for creating profile on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, full_name)
  values (new.id, new.raw_user_meta_data->>'full_name');
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
