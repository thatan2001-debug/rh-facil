-- ================================================================
-- Gestor RH IA — Schema Supabase
-- INSTRUCCIONES:
-- 1. Ve a supabase.com → tu proyecto → SQL Editor → New Query
-- 2. Pega todo este contenido y haz clic en "Run"
-- ================================================================

-- ── Extensiones ──────────────────────────────────────────────────
create extension if not exists "uuid-ossp";

-- ── Tabla usuarios ───────────────────────────────────────────────
create table if not exists usuarios (
  email               text primary key,
  nombre              text not null,
  password_hash       text not null,
  plan                text default 'gratuito'
                      check (plan in ('gratuito','basico','pro','empresarial')),
  documentos_usados   int  default 0,
  activo              boolean default false,
  es_admin            boolean default false,
  es_demo             boolean default false,
  empresa_nombre      text default '',
  telefono            text default '',
  fecha_registro      timestamptz default now(),
  fecha_activacion    timestamptz
);

-- ── Tabla empresas (repositorio completo de la PYME) ─────────────
create table if not exists empresas (
  email                   text primary key references usuarios(email) on delete cascade,
  -- Identificación legal
  nombre                  text,
  nit                     text,
  ciudad                  text,
  direccion               text,
  telefono_empresa        text,
  correo_empresa          text,
  sector                  text,
  num_empleados           text,
  -- Representantes y firmantes por tipo de documento
  representante           text,
  firmante_cert_nombre    text,
  firmante_cert_cargo     text,
  firmante_vac_nombre     text,
  firmante_vac_cargo      text,
  firmante_liq_nombre     text,
  firmante_liq_cargo      text,
  -- Archivos (solo nombres, no rutas absolutas)
  logo_nombre             text,
  membrete_nombre         text,
  -- Preferencias de diseño
  usar_logo_encabezado    boolean default true,
  usar_marca_agua         boolean default false,
  disenio_seleccionado    int default 1,
  -- Estado de onboarding
  onboarding_completo     boolean default false,
  updated_at              timestamptz default now()
);

-- ── Tabla empleados (repositorio por empresa) ────────────────────
create table if not exists empleados (
  id              uuid primary key default gen_random_uuid(),
  email_empresa   text references usuarios(email) on delete cascade,
  documento       text not null,
  nombre          text not null,
  cargo           text,
  salario         numeric(12,2) default 0,
  fecha_ingreso   text,
  fecha_retiro    text,
  tipo_contrato   text default 'Indefinido',
  correo          text,
  cuenta_bancaria text,
  activo          boolean default true,
  created_at      timestamptz default now(),
  updated_at      timestamptz default now(),
  unique (email_empresa, documento)
);
create index if not exists idx_empleados_empresa on empleados(email_empresa);
create index if not exists idx_empleados_doc    on empleados(documento);
alter table empleados enable row level security;
do $$ begin
  if not exists (
    select 1 from pg_policies where tablename='empleados' and policyname='allow_all'
  ) then
    create policy "allow_all" on empleados for all using (true);
  end if;
end $$;

-- ── Log de documentos generados ──────────────────────────────────
create table if not exists documentos_log (
  id              uuid primary key default gen_random_uuid(),
  email           text references usuarios(email) on delete cascade,
  tipo_documento  text,
  cantidad        int default 1,
  empleado_nombre text,
  generado_en     timestamptz default now()
);

-- ── Trigger: actualizar updated_at en empresas ───────────────────
create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists set_updated_at on empresas;
create trigger set_updated_at
  before update on empresas
  for each row execute function update_updated_at();

-- ── Usuarios iniciales ───────────────────────────────────────────
-- Contraseñas: demo=GestorRHCol2026 / admin=Admin2026*
insert into usuarios (email, nombre, password_hash, plan, activo, es_admin, es_demo)
values
  ('demo@gestorrh.co',
   'Usuario Demo',
   'b3b738e4e60a46cae4a3f4f0efb2bb17c7b9e3f5d1a2c4e6f8b0d2e4f6a8c0e',
   'pro', true, false, true),
  ('admin@gestorrh.co',
   'Administrador Gestor RH IA',
   'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2',
   'empresarial', true, true, false)
on conflict (email) do nothing;

-- ── RLS: habilitar seguridad a nivel de fila ─────────────────────
alter table usuarios       enable row level security;
alter table empresas       enable row level security;
alter table documentos_log enable row level security;

-- Política permisiva para service_role (la clave que usa el backend)
-- En producción avanzada, crear políticas más granulares por usuario
do $$ begin
  if not exists (
    select 1 from pg_policies where tablename='usuarios' and policyname='allow_all'
  ) then
    create policy "allow_all" on usuarios for all using (true);
  end if;
  if not exists (
    select 1 from pg_policies where tablename='empresas' and policyname='allow_all'
  ) then
    create policy "allow_all" on empresas for all using (true);
  end if;
  if not exists (
    select 1 from pg_policies where tablename='documentos_log' and policyname='allow_all'
  ) then
    create policy "allow_all" on documentos_log for all using (true);
  end if;
end $$;

-- ── Actualización tabla empleados: campos de salario ─────────────
alter table empleados add column if not exists tipo_salario    text default 'fijo';
alter table empleados add column if not exists salario_variable numeric(12,2) default 0;
alter table empleados add column if not exists ingreso_promedio_variable numeric(12,2) default 0;

-- Trigger updated_at para empleados
create or replace function update_empleados_updated_at()
returns trigger as $$
begin new.updated_at = now(); return new; end;
$$ language plpgsql;

drop trigger if exists set_empleados_updated_at on empleados;
create trigger set_empleados_updated_at
  before update on empleados
  for each row execute function update_empleados_updated_at();
