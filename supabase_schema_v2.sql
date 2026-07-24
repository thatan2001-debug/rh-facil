-- ═══════════════════════════════════════════════════════════════════════════
-- Migración 004 — Multiempresa (Etapa 4)
-- ═══════════════════════════════════════════════════════════════════════════
-- Ejecutar en Supabase → SQL Editor → New Query → Run
--
-- Esta migración es ADITIVA:
-- - Crea nuevas tablas (empresas, perfiles, empresa_usuarios, roles, permisos)
-- - NO borra ni modifica las tablas actuales (usuarios, empresas_multi, etc.)
-- - Un script Python migrará los datos actuales a las nuevas tablas
-- ═══════════════════════════════════════════════════════════════════════════

-- ── EXTENSIONES ─────────────────────────────────────────────────────────────
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";


-- ═══════════════════════════════════════════════════════════════════════════
-- TABLA: empresas (nueva estructura)
-- ═══════════════════════════════════════════════════════════════════════════
-- Nota: existe una tabla vieja llamada "empresas" con estructura diferente
-- (contenía password_hash, etc). Se renombra a "empresas_legacy" antes de crear esta.

do $$
begin
    if exists (select 1 from information_schema.tables
                where table_schema = 'public' and table_name = 'empresas'
                and exists (select 1 from information_schema.columns
                            where table_schema = 'public'
                              and table_name = 'empresas'
                              and column_name = 'password_hash')) then
        alter table empresas rename to empresas_legacy;
    end if;
end $$;

create table if not exists empresas (
    id                 uuid primary key default gen_random_uuid(),
    razon_social       text not null,
    nombre_comercial   text,
    nit                text,
    direccion          text,
    ciudad             text,
    departamento       text,
    pais               text default 'Colombia',
    telefono           text,
    correo             text,
    representante_legal        text,
    representante_tipo_doc     text default 'CC',
    representante_documento    text,
    logo_url           text,
    membrete_url       text,
    zona_horaria       text default 'America/Bogota',
    moneda             text default 'COP',
    formato_fecha      text default 'DD/MM/YYYY',
    prefijo_documental text default 'DOC',
    consecutivo_actual integer default 0,
    plan               text default 'gratuito',
    estado             text default 'activa'
                       check (estado in ('activa','suspendida','eliminada')),
    metadata           jsonb default '{}'::jsonb,
    created_at         timestamptz default now(),
    updated_at         timestamptz default now()
);

create index if not exists idx_empresas_estado on empresas(estado);
create index if not exists idx_empresas_nit on empresas(nit) where nit is not null;

comment on table empresas is
    'Empresas registradas en el SaaS. Cada empresa es un tenant.';


-- ═══════════════════════════════════════════════════════════════════════════
-- TABLA: perfiles
-- ═══════════════════════════════════════════════════════════════════════════
-- Perfil de usuario del sistema (separado de la tabla legacy "usuarios").
-- El email es único a nivel global (un correo = un perfil).

create table if not exists perfiles (
    id            uuid primary key default gen_random_uuid(),
    email         text unique not null,
    nombre        text not null,
    telefono      text,
    password_hash text not null,  -- Argon2 (o SHA-256 legacy durante migración)
    activo        boolean default false,
    es_superadmin boolean default false,
    ultimo_login  timestamptz,
    created_at    timestamptz default now(),
    updated_at    timestamptz default now()
);

create index if not exists idx_perfiles_email on perfiles(email);
create index if not exists idx_perfiles_activo on perfiles(activo);

comment on table perfiles is
    'Perfil global de usuario. El email es único. Un perfil puede pertenecer a varias empresas via empresa_usuarios.';


-- ═══════════════════════════════════════════════════════════════════════════
-- TABLA: roles
-- ═══════════════════════════════════════════════════════════════════════════

create table if not exists roles (
    id          uuid primary key default gen_random_uuid(),
    codigo      text unique not null,  -- 'superadmin', 'admin_empresa', 'rrhh', 'lectura'
    nombre      text not null,
    descripcion text,
    es_sistema  boolean default true,  -- roles del sistema no se pueden borrar
    created_at  timestamptz default now()
);

comment on table roles is
    'Roles del sistema. Los es_sistema=true no se pueden eliminar.';


-- ═══════════════════════════════════════════════════════════════════════════
-- TABLA: permisos
-- ═══════════════════════════════════════════════════════════════════════════

create table if not exists permisos (
    id          uuid primary key default gen_random_uuid(),
    codigo      text unique not null,  -- ej: 'empleados.crear', 'documentos.aprobar'
    nombre      text not null,
    descripcion text,
    modulo      text not null,  -- 'empleados', 'documentos', 'liquidaciones', etc.
    created_at  timestamptz default now()
);

create index if not exists idx_permisos_modulo on permisos(modulo);


-- ═══════════════════════════════════════════════════════════════════════════
-- TABLA: rol_permisos
-- ═══════════════════════════════════════════════════════════════════════════

create table if not exists rol_permisos (
    rol_id     uuid references roles(id) on delete cascade,
    permiso_id uuid references permisos(id) on delete cascade,
    primary key (rol_id, permiso_id)
);


-- ═══════════════════════════════════════════════════════════════════════════
-- TABLA: empresa_usuarios (relación N:M)
-- ═══════════════════════════════════════════════════════════════════════════

create table if not exists empresa_usuarios (
    id          uuid primary key default gen_random_uuid(),
    empresa_id  uuid not null references empresas(id) on delete cascade,
    perfil_id   uuid not null references perfiles(id) on delete cascade,
    rol_id      uuid not null references roles(id),
    estado      text default 'activo'
                check (estado in ('activo','suspendido','removido')),
    invitado_por uuid references perfiles(id),
    created_at  timestamptz default now(),
    updated_at  timestamptz default now(),
    unique (empresa_id, perfil_id)
);

create index if not exists idx_empresa_usuarios_perfil on empresa_usuarios(perfil_id);
create index if not exists idx_empresa_usuarios_empresa on empresa_usuarios(empresa_id);
create index if not exists idx_empresa_usuarios_estado on empresa_usuarios(estado);

comment on table empresa_usuarios is
    'Vincula perfiles con empresas. Un perfil puede estar en múltiples empresas con diferentes roles.';


-- ═══════════════════════════════════════════════════════════════════════════
-- DATOS INICIALES — Roles del sistema
-- ═══════════════════════════════════════════════════════════════════════════

insert into roles (codigo, nombre, descripcion, es_sistema) values
    ('superadmin',    'Superadministrador',
     'Acceso total al sistema. Administra empresas y planes.', true),
    ('admin_empresa', 'Administrador de empresa',
     'Administra su empresa: usuarios, empleados, documentos, configuración.', true),
    ('rrhh',          'Recursos Humanos',
     'Gestiona empleados y genera documentos. No administra usuarios.', true),
    ('lectura',       'Solo lectura',
     'Puede consultar información pero no modificar.', true)
on conflict (codigo) do nothing;


-- ═══════════════════════════════════════════════════════════════════════════
-- DATOS INICIALES — Permisos del sistema
-- ═══════════════════════════════════════════════════════════════════════════

insert into permisos (codigo, nombre, descripcion, modulo) values
    -- Empleados
    ('empleados.ver',      'Ver empleados',      'Consultar lista y ficha',      'empleados'),
    ('empleados.crear',    'Crear empleados',    'Registrar nuevos empleados',   'empleados'),
    ('empleados.editar',   'Editar empleados',   'Modificar datos existentes',   'empleados'),
    ('empleados.eliminar', 'Eliminar empleados', 'Retirar o eliminar (soft)',    'empleados'),
    ('empleados.importar', 'Importar Excel',     'Importar empleados masivos',   'empleados'),
    ('empleados.exportar', 'Exportar empleados', 'Descargar en Excel',           'empleados'),

    -- Documentos
    ('documentos.ver',      'Ver documentos',     'Consultar documentos generados', 'documentos'),
    ('documentos.generar',  'Generar documentos', 'Crear certificados, cartas, etc.', 'documentos'),
    ('documentos.aprobar',  'Aprobar documentos', 'Aprobar antes de firma',         'documentos'),
    ('documentos.enviar',   'Enviar por correo',  'Envío automático de docs',       'documentos'),
    ('documentos.eliminar', 'Eliminar documentos','Anular documentos',              'documentos'),

    -- Liquidaciones
    ('liquidaciones.ver',      'Ver liquidaciones',      'Consultar histórico',    'liquidaciones'),
    ('liquidaciones.calcular', 'Calcular liquidaciones', 'Generar cálculos',       'liquidaciones'),
    ('liquidaciones.aprobar',  'Aprobar liquidaciones',  'Aprobar antes de pago',  'liquidaciones'),

    -- Empresa
    ('empresa.ver_datos',   'Ver datos de empresa',    'Consultar configuración',  'empresa'),
    ('empresa.editar_datos','Editar datos de empresa', 'Modificar razón social, etc.', 'empresa'),
    ('empresa.configurar',  'Configurar empresa',      'Firmantes, plantillas, etc.',  'empresa'),

    -- Usuarios
    ('usuarios.ver',      'Ver usuarios',      'Ver lista de usuarios de la empresa', 'usuarios'),
    ('usuarios.invitar',  'Invitar usuarios',  'Agregar nuevos usuarios',              'usuarios'),
    ('usuarios.editar',   'Editar usuarios',   'Cambiar rol o estado',                 'usuarios'),
    ('usuarios.eliminar', 'Eliminar usuarios', 'Remover de la empresa',                'usuarios'),

    -- Plantillas
    ('plantillas.ver',      'Ver plantillas',      'Consultar plantillas',      'plantillas'),
    ('plantillas.crear',    'Crear plantillas',    'Subir DOCX o crear',        'plantillas'),
    ('plantillas.editar',   'Editar plantillas',   'Modificar variables',       'plantillas'),
    ('plantillas.eliminar', 'Eliminar plantillas', 'Deshabilitar plantilla',    'plantillas'),

    -- Auditoría y reportes
    ('reportes.ver',   'Ver reportes',   'Consultar dashboards y reportes',  'reportes'),
    ('auditoria.ver',  'Ver auditoría',  'Consultar registro de acciones',   'auditoria'),

    -- Superadmin
    ('sistema.administrar_empresas', 'Administrar empresas', 'Ver todas las empresas del SaaS', 'sistema'),
    ('sistema.administrar_planes',   'Administrar planes',   'Cambiar planes y suscripciones',   'sistema')
on conflict (codigo) do nothing;


-- ═══════════════════════════════════════════════════════════════════════════
-- DATOS INICIALES — Asignación de permisos a roles
-- ═══════════════════════════════════════════════════════════════════════════

-- SUPERADMIN → todos los permisos
insert into rol_permisos (rol_id, permiso_id)
    select r.id, p.id from roles r, permisos p
    where r.codigo = 'superadmin'
on conflict do nothing;

-- ADMIN DE EMPRESA → todo excepto sistema.*
insert into rol_permisos (rol_id, permiso_id)
    select r.id, p.id from roles r, permisos p
    where r.codigo = 'admin_empresa'
      and p.modulo != 'sistema'
on conflict do nothing;

-- RRHH → empleados + documentos + liquidaciones + reportes (sin usuarios, sin config empresa)
insert into rol_permisos (rol_id, permiso_id)
    select r.id, p.id from roles r, permisos p
    where r.codigo = 'rrhh'
      and (
        p.modulo in ('empleados', 'documentos', 'liquidaciones', 'reportes')
        or p.codigo in ('empresa.ver_datos', 'plantillas.ver')
      )
on conflict do nothing;

-- LECTURA → solo permisos .ver
insert into rol_permisos (rol_id, permiso_id)
    select r.id, p.id from roles r, permisos p
    where r.codigo = 'lectura'
      and p.codigo like '%.ver'
on conflict do nothing;


-- ═══════════════════════════════════════════════════════════════════════════
-- RLS BÁSICO (S4.5 lo hará estricto por empresa)
-- ═══════════════════════════════════════════════════════════════════════════

alter table empresas          enable row level security;
alter table perfiles          enable row level security;
alter table empresa_usuarios  enable row level security;
alter table roles             enable row level security;
alter table permisos          enable row level security;
alter table rol_permisos      enable row level security;

-- Por ahora política permisiva para service_role — S4.5 la endurecerá
drop policy if exists "empresas_service"          on empresas;
drop policy if exists "perfiles_service"          on perfiles;
drop policy if exists "empresa_usuarios_service"  on empresa_usuarios;
drop policy if exists "roles_service"             on roles;
drop policy if exists "permisos_service"          on permisos;
drop policy if exists "rol_permisos_service"      on rol_permisos;

create policy "empresas_service"         on empresas         for all to service_role using (true) with check (true);
create policy "perfiles_service"         on perfiles         for all to service_role using (true) with check (true);
create policy "empresa_usuarios_service" on empresa_usuarios for all to service_role using (true) with check (true);
create policy "roles_service"            on roles            for all to service_role using (true) with check (true);
create policy "permisos_service"         on permisos         for all to service_role using (true) with check (true);
create policy "rol_permisos_service"     on rol_permisos     for all to service_role using (true) with check (true);


-- ═══════════════════════════════════════════════════════════════════════════
-- FUNCIÓN: touch_updated_at (para triggers)
-- ═══════════════════════════════════════════════════════════════════════════

create or replace function touch_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_empresas_updated_at on empresas;
create trigger trg_empresas_updated_at
    before update on empresas
    for each row execute function touch_updated_at();

drop trigger if exists trg_perfiles_updated_at on perfiles;
create trigger trg_perfiles_updated_at
    before update on perfiles
    for each row execute function touch_updated_at();

drop trigger if exists trg_empresa_usuarios_updated_at on empresa_usuarios;
create trigger trg_empresa_usuarios_updated_at
    before update on empresa_usuarios
    for each row execute function touch_updated_at();


-- ═══════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN — Ejecuta esto después para confirmar que todo funcionó
-- ═══════════════════════════════════════════════════════════════════════════
-- select count(*) as total_roles from roles;          -- Debe ser 4
-- select count(*) as total_permisos from permisos;    -- Debe ser ~30
-- select r.codigo, count(rp.permiso_id) as permisos
--   from roles r
--   left join rol_permisos rp on rp.rol_id = r.id
--   group by r.codigo
--   order by r.codigo;
