-- Expected answers for the test residents (test_data/eval_scenarios.json).
-- Test labels only: the scorer never reads this table.

create table if not exists public.eval_scenarios (
  resident_id  text not null references public.residents (id) on delete cascade,
  scenario     text not null,
  expected     jsonb not null,
  primary key (resident_id, scenario)
);
