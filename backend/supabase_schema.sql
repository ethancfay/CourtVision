-- CourtVision database setup. Paste into Supabase > SQL Editor and click Run.
-- The backend uses the service_role key, which bypasses row level security.
-- RLS is turned on with no public policies, so the public anon key cannot read or change data.

create table teams (
  team_id text primary key,
  name text not null,
  abbr text not null,
  conference text,
  division text,
  win_count int default 0,
  loss_count int default 0,
  off_rtg float,
  def_rtg float,
  pace float,
  updated_at timestamptz default now()
);

create table players (
  player_id text primary key,
  name text not null,
  team_id text references teams(team_id),
  position text,
  status text default 'active',
  season_avg jsonb,
  updated_at timestamptz default now()
);

create table games (
  game_id text primary key,
  game_date date not null,
  home_team_id text,
  away_team_id text,
  home_team_name text,
  away_team_name text,
  home_team_abbr text,
  away_team_abbr text,
  home_score int,
  away_score int,
  status text,   -- 'upcoming', 'live', 'final'
  quarter int,
  clock text,
  tipoff_time text,
  updated_at timestamptz default now()
);

create table player_game_stats (
  id bigint generated always as identity primary key,
  player_id text,
  game_id text,
  team_id text,
  pts int, reb int, ast int, stl int, blk int,
  turnovers int, fgm int, fga int, fg_pct float,
  plus_minus int, minutes text,
  last5_pts int[],
  league_rank_pts int,
  league_rank_reb int,
  league_rank_ast int,
  matchup_avg_pts float,
  updated_at timestamptz default now(),
  unique(player_id, game_id)
);

create table predictions (
  game_id text primary key,
  winner text,
  winner_abbr text,
  confidence int,
  score_home int,
  score_away int,
  key_factors jsonb,
  result text,   -- 'pending', 'correct', 'incorrect'
  created_at timestamptz default now()
);

create table player_cards (
  id bigint generated always as identity primary key,
  player_id text,
  game_id text,
  report text,
  projection jsonb,
  trend text,
  created_at timestamptz default now(),
  unique(player_id, game_id)
);

create table media_takes (
  id text primary key,
  personality text not null,
  outlet text not null,
  outlet_color text,
  avatar text,
  take_text text not null,
  category text,
  agrees int default 0,
  disagrees int default 0,
  created_at timestamptz default now()
);

create table take_verdicts (
  take_id text primary key references media_takes(id),
  steelman text,
  challenge text,
  verdict_label text,
  created_at timestamptz default now()
);

alter table teams enable row level security;
alter table players enable row level security;
alter table games enable row level security;
alter table player_game_stats enable row level security;
alter table predictions enable row level security;
alter table player_cards enable row level security;
alter table media_takes enable row level security;
alter table take_verdicts enable row level security;

-- Sample media takes (fictional hosts) for the Take Verdicts page
insert into media_takes (id, personality, outlet, outlet_color, avatar, take_text, category, agrees, disagrees) values
  ('t001', 'Max Loudmouth', 'Hot Take Hour (sample)', '#CC0000', 'ML', 'LeBron James is NO LONGER the best player on his own team. Anthony Davis has taken over. Full stop.', 'hot', 1243, 2891),
  ('t002', 'Dana Film-Room', 'Courtside Pod (sample)', '#CC0000', 'DF', 'The Celtics are the most complete team in the East and it''s not particularly close. Their defense is historically elite.', 'stat-backed', 4102, 891),
  ('t003', 'Coach Ray', 'Locker Room Talk (sample)', '#8B5CF6', 'CR', 'Nikola Jokic is the greatest offensive player at any position I have ever seen in my lifetime. He sees things no one else sees.', 'popular', 6741, 1204),
  ('t004', 'Sam Stats', 'Box Score Daily (sample)', '#E87722', 'SS', 'The Warriors dynasty is officially over. This roster has no path back to the Finals. Steph deserves better.', 'hot', 3218, 2544),
  ('t005', 'Jordan Rumor', 'Trade Machine Live (sample)', '#CC0000', 'JR', 'The Lakers should re-sign LeBron no matter what it does to their cap sheet.', 'prediction', 2987, 761),
  ('t006', 'Pat Contrarian', 'Hot Take Hour (sample)', '#1D4ED8', 'PC', 'Jayson Tatum is NOT a superstar. He disappears in big moments. Show me a ring.', 'hot', 891, 5432),
  ('t007', 'Alex Analytics', 'Courtside Pod (sample)', '#CC0000', 'AA', 'Victor Wembanyama is already the most unique player to ever enter the NBA. His combination of size and skill has no historical precedent.', 'popular', 7823, 445),
  ('t008', 'Big Vic', 'Locker Room Talk (sample)', '#CC0000', 'BV', 'The Miami Heat culture is the gold standard of the NBA. No team does more with less. Every year they compete. Every. Single. Year.', 'popular', 3341, 1122)
on conflict (id) do nothing;
