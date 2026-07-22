-- ═══════════════════════════════════════════════════════════════════════════
-- Migración 003 — Tabla intentos_login (rate limiting)
-- Aplicar en Supabase → SQL Editor → New Query → Run
-- ═══════════════════════════════════════════════════════════════════════════

create table if not exists intentos_login (
    id         uuid primary key default gen_random_uuid(),
    email      text not null,
    ip         text default 'unknown',
    exitoso    boolean not null default false,
    ts         timestamptz not null default now()
);

-- Índices para consultas rápidas del rate limiter
create index if not exists idx_intentos_login_email_ts
    on intentos_login(email, ts desc);

create index if not exists idx_intentos_login_ts
    on intentos_login(ts desc);

-- ── RLS ──────────────────────────────────────────────────────────────────
alter table intentos_login enable row level security;

-- Solo el service_role puede leer/escribir (nadie desde el cliente)
drop policy if exists "intentos_login_service_role" on intentos_login;
create policy "intentos_login_service_role" on intentos_login
    for all to service_role
    using (true)
    with check (true);

-- ── Limpieza automática (opcional): borrar intentos > 24 horas ──────────
-- Ejecuta esto periódicamente o crea un cron job en Supabase:
--   delete from intentos_login where ts < now() - interval '24 hours';

comment on table intentos_login is
    'Registra intentos de login para rate limiting. Se limpia después de 24h.';
