create table food_log (
  id bigint primary key generated always as identity,
  user_id bigint references users(id),
  timestamp timestamptz not null default now(),
  estimated_calories int,
  protein_grams int,
  fat_grams int,
  carbs_grams int,
  image_urls text[],
  ai_description text,
  ai_confidence numeric,
  created_at timestamptz default now()
);

