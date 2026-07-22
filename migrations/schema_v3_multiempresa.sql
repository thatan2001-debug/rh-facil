-- ═══════════════════════════════════════════════════════════════════════════
-- Gestor RH IA — Schema completo v3 (MVP SaaS multiempresa)
-- ═══════════════════════════════════════════════════════════════════════════
-- Fecha: 2026-07-21
-- Autor: refactor arquitectónico Etapa 2 → 4
--
-- IMPORTANTE:
--   1. Ejecutar este script en el SQL Editor de Supabase
--   2. Este script es IDEMPOTENTE — se puede correr varias veces sin romper
--   3. NO borra las tablas antiguas — coexisten hasta migración de datos
--   4. Después de correr, ejecutar `seed_roles_permisos.sql` para datos iniciales
--
-- Este schema cubre:
--   - Autenticación (perfiles vinculados a auth.users)
--   - Multiempresa (empresas + empresa_usuarios N:M)
--   - Autorización (roles + permisos + rol_permisos)
--   - Estructura organizacional (sedes, áreas, cargos)
--   - Empleados persistentes (con restricción única empresa+documento)
--   - Motor de plantillas (plantillas + versiones)
--   - Documentos generados (con historial completo)
--   - Aprobaciones y envíos
--   - Liquidaciones con parámetros por año
--   - Auditoría completa
--   - RLS estricto por empresa
-- ═══════════════════════════════════════════════════════════════════════════

-- ── Extensiones necesarias ─────────────────────────────────────────────────
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";


-- ═══════════════════════════════════════════════════════════════════════════
-- 1. EMPRESAS
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists empresas (
    id                          uuid primary key default gen_random_uuid(),
    razon_social                text not null,
    nombre_comercial            text,
    nit                         text not null,
    tipo_documento_empresa      text default 'NIT',
    direccion                   text,
    ciudad                      text,
    departamento                text,
    pais                        text default 'Colombia',
    telefono                    text,
    correo                      text,
    representante_legal         text,
    representante_tipo_documento text default 'CC',
    representante_documento     text,
    logo_url                    text,
    membrete_url                text,
    zona_horaria                text default 'America/Bogota',
    moneda                      text default 'COP',
    formato_fecha               text default 'DD/MM/YYYY',
    prefijo_documental          text default 'DOC',
    consecutivo_actual          integer default 0,
    estado                      text default 'activa' check (estado in ('activa','suspendida','cancelada')),
    plan                        text default 'gratuito',
    fecha_inicio_plan           timestamptz,
    fecha_fin_plan              timestamptz,
    created_at                  timestamptz default now(),
    updated_at                  timestamptz default now(),
    unique(nit)
);

create index if not exists idx_empresas_nit    on empresas(nit);
create index if not exists idx_empresas_estado on empresas(estado);


-- ═══════════════════════════════════════════════════════════════════════════
-- 2. PERFILES DE USUARIO (vinculado a auth.users de Supabase Auth)
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists perfiles (
    id            uuid primary key,   -- corresponde a auth.users.id
    nombre        text not null,
    apellido      text,
    telefono      text,
    documento     text,
    tipo_documento text default 'CC',
    activo        boolean default true,
    ultimo_login  timestamptz,
    created_at    timestamptz default now(),
    updated_at    timestamptz default now()
);

comment on table perfiles is 'Perfil extendido de usuario. La autenticación real vive en auth.users';


-- ═══════════════════════════════════════════════════════════════════════════
-- 3. ROLES
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists roles (
    id            uuid primary key default gen_random_uuid(),
    empresa_id    uuid references empresas(id) on delete cascade, -- null = rol de sistema
    codigo        text not null,      -- ej: 'admin_empresa', 'rrhh'
    nombre        text not null,
    descripcion   text,
    es_sistema    boolean default false,
    estado        text default 'activo',
    created_at    timestamptz default now(),
    unique(empresa_id, codigo)
);

create index if not exists idx_roles_empresa on roles(empresa_id);


-- ═══════════════════════════════════════════════════════════════════════════
-- 4. PERMISOS
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists permisos (
    id            uuid primary key default gen_random_uuid(),
    codigo        text not null unique,   -- ej: 'empleados.crear'
    modulo        text not null,          -- ej: 'empleados'
    accion        text not null,          -- ej: 'crear'
    nombre        text not null,
    descripcion   text,
    created_at    timestamptz default now()
);

create index if not exists idx_permisos_modulo on permisos(modulo);


-- ═══════════════════════════════════════════════════════════════════════════
-- 5. ROL_PERMISOS (N:M)
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists rol_permisos (
    rol_id      uuid references roles(id)    on delete cascade,
    permiso_id  uuid references permisos(id) on delete cascade,
    primary key (rol_id, permiso_id)
);


-- ═══════════════════════════════════════════════════════════════════════════
-- 6. EMPRESA_USUARIOS (N:M — un usuario puede pertenecer a varias empresas)
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists empresa_usuarios (
    id            uuid primary key default gen_random_uuid(),
    empresa_id    uuid not null references empresas(id)  on delete cascade,
    usuario_id    uuid not null references perfiles(id)  on delete cascade,
    rol_id        uuid not null references roles(id),
    estado        text default 'activo' check (estado in ('activo','inactivo','suspendido')),
    created_at    timestamptz default now(),
    updated_at    timestamptz default now(),
    unique(empresa_id, usuario_id)
);

create index if not exists idx_eu_empresa on empresa_usuarios(empresa_id);
create index if not exists idx_eu_usuario on empresa_usuarios(usuario_id);


-- ═══════════════════════════════════════════════════════════════════════════
-- 7. SEDES
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists sedes (
    id            uuid primary key default gen_random_uuid(),
    empresa_id    uuid not null references empresas(id) on delete cascade,
    nombre        text not null,
    direccion     text,
    ciudad        text,
    departamento  text,
    telefono      text,
    responsable   text,
    estado        text default 'activa',
    created_at    timestamptz default now(),
    updated_at    timestamptz default now(),
    unique(empresa_id, nombre)
);

create index if not exists idx_sedes_empresa on sedes(empresa_id);


-- ═══════════════════════════════════════════════════════════════════════════
-- 8. ÁREAS / DEPARTAMENTOS
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists areas (
    id            uuid primary key default gen_random_uuid(),
    empresa_id    uuid not null references empresas(id) on delete cascade,
    nombre        text not null,
    descripcion   text,
    responsable   text,
    estado        text default 'activa',
    created_at    timestamptz default now(),
    updated_at    timestamptz default now(),
    unique(empresa_id, nombre)
);

create index if not exists idx_areas_empresa on areas(empresa_id);


-- ═══════════════════════════════════════════════════════════════════════════
-- 9. CARGOS
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists cargos (
    id            uuid primary key default gen_random_uuid(),
    empresa_id    uuid not null references empresas(id) on delete cascade,
    nombre        text not null,
    descripcion   text,
    funciones     text,
    nivel_jerarquico text,
    estado        text default 'activo',
    created_at    timestamptz default now(),
    updated_at    timestamptz default now(),
    unique(empresa_id, nombre)
);

create index if not exists idx_cargos_empresa on cargos(empresa_id);


-- ═══════════════════════════════════════════════════════════════════════════
-- 10. EMPLEADOS (persistentes, con TODOS los campos)
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists empleados_v2 (
    id                      uuid primary key default gen_random_uuid(),
    empresa_id              uuid not null references empresas(id) on delete cascade,
    codigo                  text,
    -- Documento
    tipo_documento          text default 'CC',
    numero_documento        text not null,
    -- Nombres
    nombres                 text not null,
    apellidos               text not null,
    nombre_completo         text generated always as (nombres || ' ' || apellidos) stored,
    -- Personal
    fecha_nacimiento        date,
    direccion               text,
    ciudad                  text,
    departamento            text,
    telefono                text,
    correo_personal         text,
    correo_corporativo      text,
    estado_civil            text,
    -- Contacto emergencia
    contacto_emergencia_nombre text,
    contacto_emergencia_telefono text,
    contacto_emergencia_parentesco text,
    -- Laboral
    cargo_id                uuid references cargos(id),
    cargo_texto             text,   -- por si no se usa el catálogo
    area_id                 uuid references areas(id),
    area_texto              text,
    sede_id                 uuid references sedes(id),
    jefe_id                 uuid references empleados_v2(id),
    -- Fechas
    fecha_ingreso           date not null,
    fecha_retiro            date,
    tipo_contrato           text default 'Indefinido' check (
        tipo_contrato in ('Indefinido','Fijo','Obra o labor','Prestacion de servicios','Aprendizaje','Practica')
    ),
    fecha_inicio_contrato   date,
    fecha_fin_contrato      date,
    -- Compensación
    salario                 numeric(15,2) default 0,
    auxilio_transporte      numeric(15,2) default 0,
    tipo_salario            text default 'fijo' check (tipo_salario in ('fijo','variable','integral')),
    ingreso_promedio_variable numeric(15,2) default 0,
    -- Jornada
    jornada                 text default 'Diurna' check (jornada in ('Diurna','Nocturna','Mixta','Turnos')),
    horario                 text,
    modalidad               text default 'Presencial' check (modalidad in ('Presencial','Remoto','Hibrido')),
    -- Seguridad social
    eps                     text,
    arl                     text,
    caja_compensacion       text,
    fondo_pension           text,
    fondo_cesantias         text,
    -- Bancos
    banco                   text,
    tipo_cuenta             text,
    numero_cuenta           text,
    -- Estado
    activo                  boolean default true,
    motivo_retiro           text,
    -- Metadatos
    created_by              uuid references perfiles(id),
    created_at              timestamptz default now(),
    updated_at              timestamptz default now(),
    -- Restricción única
    unique(empresa_id, numero_documento)
);

create index if not exists idx_emp_v2_empresa on empleados_v2(empresa_id);
create index if not exists idx_emp_v2_doc     on empleados_v2(empresa_id, numero_documento);
create index if not exists idx_emp_v2_activo  on empleados_v2(empresa_id, activo);
create index if not exists idx_emp_v2_cargo   on empleados_v2(cargo_id);
create index if not exists idx_emp_v2_area    on empleados_v2(area_id);


-- ═══════════════════════════════════════════════════════════════════════════
-- 11. FIRMANTES (para documentos)
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists firmantes (
    id            uuid primary key default gen_random_uuid(),
    empresa_id    uuid not null references empresas(id) on delete cascade,
    nombre        text not null,
    cargo         text not null,
    correo        text,
    firma_url     text,   -- URL de la imagen de firma
    tipos_documento text[], -- para qué tipos de doc puede firmar
    orden         integer default 0,
    estado        text default 'activo',
    created_at    timestamptz default now(),
    updated_at    timestamptz default now()
);

create index if not exists idx_firmantes_empresa on firmantes(empresa_id);


-- ═══════════════════════════════════════════════════════════════════════════
-- 12. PLANTILLAS
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists plantillas (
    id                    uuid primary key default gen_random_uuid(),
    empresa_id            uuid references empresas(id) on delete cascade, -- null = plantilla de sistema
    codigo                text not null,
    nombre                text not null,
    tipo_documento        text not null,  -- 'certificado_laboral', 'carta_vacaciones', etc.
    descripcion           text,
    requiere_aprobacion   boolean default false,
    requiere_firma        boolean default false,
    genera_word           boolean default true,
    genera_pdf            boolean default true,
    version_actual_id     uuid,   -- FK a plantilla_versiones, se actualiza
    activa                boolean default true,
    created_by            uuid references perfiles(id),
    created_at            timestamptz default now(),
    updated_at            timestamptz default now(),
    unique(empresa_id, codigo)
);

create index if not exists idx_plantillas_empresa on plantillas(empresa_id);
create index if not exists idx_plantillas_tipo    on plantillas(tipo_documento);


-- ═══════════════════════════════════════════════════════════════════════════
-- 13. PLANTILLA_VERSIONES
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists plantilla_versiones (
    id              uuid primary key default gen_random_uuid(),
    plantilla_id    uuid not null references plantillas(id) on delete cascade,
    version         integer not null,
    archivo_url     text,   -- URL del DOCX en storage
    contenido_texto text,   -- fallback textual
    variables_json  jsonb,  -- {"NOMBRE": {"tipo":"string","obligatoria":true}, ...}
    activa          boolean default false,
    created_by      uuid references perfiles(id),
    created_at      timestamptz default now(),
    unique(plantilla_id, version)
);

alter table plantillas
    add constraint fk_plantillas_version
    foreign key (version_actual_id) references plantilla_versiones(id) on delete set null;


-- ═══════════════════════════════════════════════════════════════════════════
-- 14. DOCUMENTOS (registro de cada documento generado)
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists documentos (
    id                      uuid primary key default gen_random_uuid(),
    empresa_id              uuid not null references empresas(id) on delete cascade,
    empleado_id             uuid references empleados_v2(id),
    plantilla_id            uuid references plantillas(id),
    plantilla_version_id    uuid references plantilla_versiones(id),
    tipo_documento          text not null,
    consecutivo             integer,
    nombre_archivo          text not null,
    archivo_word_url        text,
    archivo_pdf_url         text,
    archivo_word_bytes      bytea,   -- opcional si no hay storage externo
    archivo_pdf_bytes       bytea,
    datos_generacion_json   jsonb,   -- valores usados para las variables
    estado                  text default 'borrador' check (
        estado in ('borrador','pendiente','en_revision','aprobado','rechazado',
                   'firmado','enviado','anulado','archivado')
    ),
    created_by              uuid references perfiles(id),
    created_at              timestamptz default now(),
    aprobado_by             uuid references perfiles(id),
    aprobado_at             timestamptz,
    firmado_by              uuid references perfiles(id),
    firmado_at              timestamptz,
    enviado_at              timestamptz,
    observaciones           text
);

create index if not exists idx_docs_empresa   on documentos(empresa_id);
create index if not exists idx_docs_empleado  on documentos(empleado_id);
create index if not exists idx_docs_tipo      on documentos(tipo_documento);
create index if not exists idx_docs_estado    on documentos(estado);
create index if not exists idx_docs_created   on documentos(created_at desc);


-- ═══════════════════════════════════════════════════════════════════════════
-- 15. DOCUMENTO_APROBACIONES
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists documento_aprobaciones (
    id            uuid primary key default gen_random_uuid(),
    documento_id  uuid not null references documentos(id) on delete cascade,
    usuario_id    uuid not null references perfiles(id),
    estado        text not null check (estado in ('aprobado','rechazado')),
    comentario    text,
    fecha         timestamptz default now()
);

create index if not exists idx_aprobaciones_doc on documento_aprobaciones(documento_id);


-- ═══════════════════════════════════════════════════════════════════════════
-- 16. DOCUMENTO_ENVIOS
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists documento_envios (
    id                uuid primary key default gen_random_uuid(),
    documento_id      uuid not null references documentos(id) on delete cascade,
    destinatario      text not null,
    cc                text,
    asunto            text,
    mensaje           text,
    estado            text default 'pendiente' check (estado in ('pendiente','enviado','error')),
    error             text,
    intentos          integer default 0,
    fecha_envio       timestamptz,
    usuario_id        uuid references perfiles(id),
    created_at        timestamptz default now()
);

create index if not exists idx_envios_doc on documento_envios(documento_id);


-- ═══════════════════════════════════════════════════════════════════════════
-- 17. HISTORIAL_EMPLEADO
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists historial_empleado (
    id            uuid primary key default gen_random_uuid(),
    empresa_id    uuid not null references empresas(id) on delete cascade,
    empleado_id   uuid not null references empleados_v2(id) on delete cascade,
    tipo_evento   text not null,   -- 'ingreso', 'cambio_salario', 'cambio_cargo', etc.
    descripcion   text,
    datos_json    jsonb,
    created_by    uuid references perfiles(id),
    created_at    timestamptz default now()
);

create index if not exists idx_hist_empleado on historial_empleado(empleado_id, created_at desc);


-- ═══════════════════════════════════════════════════════════════════════════
-- 18. AUDITORÍA (global — todas las acciones sensibles)
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists auditoria (
    id                  uuid primary key default gen_random_uuid(),
    empresa_id          uuid references empresas(id) on delete set null,
    usuario_id          uuid references perfiles(id) on delete set null,
    accion              text not null,
    modulo              text not null,
    registro_tabla      text,
    registro_id         text,
    valor_anterior_json jsonb,
    valor_nuevo_json    jsonb,
    ip_origen           text,
    user_agent          text,
    created_at          timestamptz default now()
);

create index if not exists idx_auditoria_empresa on auditoria(empresa_id, created_at desc);
create index if not exists idx_auditoria_usuario on auditoria(usuario_id, created_at desc);
create index if not exists idx_auditoria_accion  on auditoria(accion);


-- ═══════════════════════════════════════════════════════════════════════════
-- 19. PARÁMETROS LABORALES (por año, versionados)
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists parametros_laborales (
    id                                uuid primary key default gen_random_uuid(),
    pais                              text default 'Colombia',
    anio                              integer not null,
    salario_minimo                    numeric(15,2) not null,
    auxilio_transporte                numeric(15,2) not null,
    tope_auxilio_transporte           numeric(15,2),  -- suele ser 2 SMMLV
    porcentaje_intereses_cesantias    numeric(5,2) default 12.00,
    dias_base_ano                     integer default 360,
    dias_prima_ano                    integer default 30,
    dias_vacaciones_ano               integer default 15,
    fuente                            text,   -- decreto o ley
    fecha_inicio_vigencia             date not null,
    fecha_fin_vigencia                date,
    estado                            text default 'vigente' check (estado in ('vigente','anterior')),
    created_at                        timestamptz default now(),
    unique(pais, anio)
);

create index if not exists idx_param_anio on parametros_laborales(pais, anio);


-- ═══════════════════════════════════════════════════════════════════════════
-- 20. LIQUIDACIONES (guardadas)
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists liquidaciones (
    id                    uuid primary key default gen_random_uuid(),
    empresa_id            uuid not null references empresas(id) on delete cascade,
    empleado_id           uuid not null references empleados_v2(id),
    parametro_laboral_id  uuid references parametros_laborales(id),
    fecha_ingreso         date not null,
    fecha_retiro          date not null,
    motivo_retiro         text not null,
    dias_pendientes_fijo  integer default 0,
    salario_base          numeric(15,2) not null,
    tipo_contrato         text,
    total                 numeric(15,2) default 0,
    total_indemnizacion   numeric(15,2) default 0,
    documento_id          uuid references documentos(id),   -- PDF generado
    estado                text default 'preliminar' check (estado in ('preliminar','validada','pagada')),
    observaciones         text,
    created_by            uuid references perfiles(id),
    created_at            timestamptz default now(),
    updated_at            timestamptz default now(),
    check (fecha_retiro >= fecha_ingreso)
);

create index if not exists idx_liq_empresa  on liquidaciones(empresa_id);
create index if not exists idx_liq_empleado on liquidaciones(empleado_id);


-- ═══════════════════════════════════════════════════════════════════════════
-- 21. LIQUIDACION_CONCEPTOS (detalle desglosado)
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists liquidacion_conceptos (
    id                  uuid primary key default gen_random_uuid(),
    liquidacion_id      uuid not null references liquidaciones(id) on delete cascade,
    concepto            text not null,      -- 'Cesantias', 'Intereses', 'Prima', 'Vacaciones', 'Indemnizacion'
    articulo            text,               -- referencia CST
    base                numeric(15,2),
    dias                integer,
    formula             text,
    valor               numeric(15,2) not null,
    orden               integer default 0,
    observaciones       text
);

create index if not exists idx_liq_conceptos on liquidacion_conceptos(liquidacion_id);


-- ═══════════════════════════════════════════════════════════════════════════
-- 22. PLANES (SaaS)
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists planes (
    id                        uuid primary key default gen_random_uuid(),
    codigo                    text unique not null,
    nombre                    text not null,
    precio_mensual            numeric(15,2) default 0,
    precio_anual              numeric(15,2) default 0,
    max_empleados             integer,
    max_documentos_mes        integer,
    max_usuarios              integer default 1,
    max_empresas              integer default 1,
    permite_word              boolean default true,
    permite_correo            boolean default false,
    permite_plantillas_custom boolean default false,
    permite_multiempresa      boolean default false,
    features_json             jsonb,
    orden                     integer default 0,
    activo                    boolean default true,
    created_at                timestamptz default now()
);


-- ═══════════════════════════════════════════════════════════════════════════
-- 23. SUSCRIPCIONES
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists suscripciones (
    id                uuid primary key default gen_random_uuid(),
    empresa_id        uuid not null references empresas(id) on delete cascade,
    plan_id           uuid not null references planes(id),
    fecha_inicio      date not null default current_date,
    fecha_fin         date,
    estado            text default 'activa' check (estado in ('activa','vencida','cancelada','suspendida')),
    created_at        timestamptz default now(),
    updated_at        timestamptz default now()
);

create index if not exists idx_susc_empresa on suscripciones(empresa_id);


-- ═══════════════════════════════════════════════════════════════════════════
-- 24. USO MENSUAL (para límites de plan)
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists uso_mensual (
    id                    uuid primary key default gen_random_uuid(),
    empresa_id            uuid not null references empresas(id) on delete cascade,
    anio                  integer not null,
    mes                   integer not null,
    documentos_generados  integer default 0,
    correos_enviados      integer default 0,
    empleados_activos     integer default 0,
    created_at            timestamptz default now(),
    updated_at            timestamptz default now(),
    unique(empresa_id, anio, mes)
);


-- ═══════════════════════════════════════════════════════════════════════════
-- 25. INTENTOS DE LOGIN (para rate limiting)
-- ═══════════════════════════════════════════════════════════════════════════
create table if not exists intentos_login (
    id            uuid primary key default gen_random_uuid(),
    email         text not null,
    ip_origen     text,
    exitoso       boolean default false,
    user_agent    text,
    created_at    timestamptz default now()
);

create index if not exists idx_intentos_email on intentos_login(email, created_at desc);


-- ═══════════════════════════════════════════════════════════════════════════
-- TRIGGERS: actualizar updated_at automáticamente
-- ═══════════════════════════════════════════════════════════════════════════
create or replace function trg_actualizar_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

-- Aplicar a todas las tablas con updated_at
do $$
declare
    t text;
begin
    for t in
        select table_name
        from information_schema.columns
        where column_name = 'updated_at'
          and table_schema = 'public'
    loop
        execute format('drop trigger if exists trg_updated_at on %I', t);
        execute format(
            'create trigger trg_updated_at before update on %I
             for each row execute function trg_actualizar_updated_at()', t);
    end loop;
end $$;


-- ═══════════════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY
-- ═══════════════════════════════════════════════════════════════════════════
-- Habilitar RLS en todas las tablas multiempresa
alter table empresas               enable row level security;
alter table perfiles               enable row level security;
alter table empresa_usuarios       enable row level security;
alter table sedes                  enable row level security;
alter table areas                  enable row level security;
alter table cargos                 enable row level security;
alter table empleados_v2           enable row level security;
alter table firmantes              enable row level security;
alter table plantillas             enable row level security;
alter table plantilla_versiones    enable row level security;
alter table documentos             enable row level security;
alter table documento_aprobaciones enable row level security;
alter table documento_envios       enable row level security;
alter table historial_empleado     enable row level security;
alter table auditoria              enable row level security;
alter table liquidaciones          enable row level security;
alter table liquidacion_conceptos  enable row level security;
alter table suscripciones          enable row level security;
alter table uso_mensual            enable row level security;

-- Función auxiliar: obtener empresas del usuario actual
create or replace function auth_empresas_del_usuario()
returns setof uuid as $$
    select empresa_id
    from empresa_usuarios
    where usuario_id = auth.uid()
      and estado = 'activo';
$$ language sql security definer stable;

-- Política: usuarios pueden ver empresas a las que pertenecen
drop policy if exists "empresas_select_own" on empresas;
create policy "empresas_select_own" on empresas
    for select
    using (id in (select auth_empresas_del_usuario()));

-- Política: usuarios pueden ver su propio perfil
drop policy if exists "perfiles_own" on perfiles;
create policy "perfiles_own" on perfiles
    for all
    using (id = auth.uid())
    with check (id = auth.uid());

-- Política: empresa_usuarios — solo ven sus propios registros
drop policy if exists "eu_own" on empresa_usuarios;
create policy "eu_own" on empresa_usuarios
    for select
    using (usuario_id = auth.uid());

-- Política genérica para tablas empresa_id: aislar por empresa
-- (se aplica a: sedes, areas, cargos, empleados_v2, firmantes, plantillas,
--  documentos, historial_empleado, auditoria, liquidaciones, etc.)

drop policy if exists "sedes_por_empresa" on sedes;
create policy "sedes_por_empresa" on sedes
    for all
    using (empresa_id in (select auth_empresas_del_usuario()))
    with check (empresa_id in (select auth_empresas_del_usuario()));

drop policy if exists "areas_por_empresa" on areas;
create policy "areas_por_empresa" on areas
    for all
    using (empresa_id in (select auth_empresas_del_usuario()))
    with check (empresa_id in (select auth_empresas_del_usuario()));

drop policy if exists "cargos_por_empresa" on cargos;
create policy "cargos_por_empresa" on cargos
    for all
    using (empresa_id in (select auth_empresas_del_usuario()))
    with check (empresa_id in (select auth_empresas_del_usuario()));

drop policy if exists "empleados_v2_por_empresa" on empleados_v2;
create policy "empleados_v2_por_empresa" on empleados_v2
    for all
    using (empresa_id in (select auth_empresas_del_usuario()))
    with check (empresa_id in (select auth_empresas_del_usuario()));

drop policy if exists "firmantes_por_empresa" on firmantes;
create policy "firmantes_por_empresa" on firmantes
    for all
    using (empresa_id in (select auth_empresas_del_usuario()))
    with check (empresa_id in (select auth_empresas_del_usuario()));

drop policy if exists "plantillas_por_empresa" on plantillas;
create policy "plantillas_por_empresa" on plantillas
    for all
    using (empresa_id is null or empresa_id in (select auth_empresas_del_usuario()))
    with check (empresa_id in (select auth_empresas_del_usuario()));

drop policy if exists "documentos_por_empresa" on documentos;
create policy "documentos_por_empresa" on documentos
    for all
    using (empresa_id in (select auth_empresas_del_usuario()))
    with check (empresa_id in (select auth_empresas_del_usuario()));

drop policy if exists "historial_por_empresa" on historial_empleado;
create policy "historial_por_empresa" on historial_empleado
    for all
    using (empresa_id in (select auth_empresas_del_usuario()))
    with check (empresa_id in (select auth_empresas_del_usuario()));

drop policy if exists "liquidaciones_por_empresa" on liquidaciones;
create policy "liquidaciones_por_empresa" on liquidaciones
    for all
    using (empresa_id in (select auth_empresas_del_usuario()))
    with check (empresa_id in (select auth_empresas_del_usuario()));

drop policy if exists "auditoria_por_empresa" on auditoria;
create policy "auditoria_por_empresa" on auditoria
    for select
    using (empresa_id in (select auth_empresas_del_usuario()));


-- ═══════════════════════════════════════════════════════════════════════════
-- FIN DEL SCHEMA v3
-- ═══════════════════════════════════════════════════════════════════════════
