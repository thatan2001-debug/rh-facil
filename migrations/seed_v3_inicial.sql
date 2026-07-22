-- ═══════════════════════════════════════════════════════════════════════════
-- Gestor RH IA — Seed inicial (v3)
-- ═══════════════════════════════════════════════════════════════════════════
-- Ejecutar DESPUÉS de schema_v3_multiempresa.sql
-- Este script es idempotente — inserta solo si no existe
-- ═══════════════════════════════════════════════════════════════════════════

-- ═══════════════════════════════════════════════════════════════════════════
-- 1. PERMISOS (catálogo global)
-- ═══════════════════════════════════════════════════════════════════════════
insert into permisos (codigo, modulo, accion, nombre, descripcion) values
    -- Empresas
    ('empresa.ver',           'empresa',   'ver',    'Ver empresa',           'Ver los datos de la empresa'),
    ('empresa.editar',        'empresa',   'editar', 'Editar empresa',        'Modificar datos de la empresa'),

    -- Empleados
    ('empleados.crear',       'empleados', 'crear',  'Crear empleados',       'Crear nuevos empleados'),
    ('empleados.ver',         'empleados', 'ver',    'Ver empleados',         'Ver la lista y detalle de empleados'),
    ('empleados.editar',      'empleados', 'editar', 'Editar empleados',      'Modificar datos de empleados'),
    ('empleados.eliminar',    'empleados', 'eliminar','Eliminar empleados',   'Eliminar empleados'),
    ('empleados.importar',    'empleados', 'importar','Importar empleados',   'Cargar empleados desde Excel'),

    -- Documentos
    ('documentos.generar',    'documentos','generar','Generar documentos',    'Crear documentos (certificados, cartas, etc.)'),
    ('documentos.ver',        'documentos','ver',    'Ver documentos',        'Ver documentos generados'),
    ('documentos.aprobar',    'documentos','aprobar','Aprobar documentos',    'Aprobar documentos pendientes'),
    ('documentos.firmar',     'documentos','firmar', 'Firmar documentos',     'Firmar documentos aprobados'),
    ('documentos.enviar',     'documentos','enviar', 'Enviar documentos',     'Enviar documentos por correo'),
    ('documentos.anular',     'documentos','anular', 'Anular documentos',     'Marcar documentos como anulados'),

    -- Liquidaciones
    ('liquidaciones.crear',   'liquidaciones','crear','Crear liquidaciones',   'Calcular liquidaciones'),
    ('liquidaciones.ver',     'liquidaciones','ver',  'Ver liquidaciones',     'Consultar liquidaciones'),
    ('liquidaciones.validar', 'liquidaciones','validar','Validar liquidaciones','Marcar liquidación como validada'),

    -- Plantillas
    ('plantillas.crear',      'plantillas','crear',  'Crear plantillas',      'Crear plantillas personalizadas'),
    ('plantillas.editar',     'plantillas','editar', 'Editar plantillas',     'Modificar plantillas'),
    ('plantillas.eliminar',   'plantillas','eliminar','Eliminar plantillas',  'Eliminar plantillas'),

    -- Estructura organizacional
    ('sedes.gestionar',       'estructura','gestionar','Gestionar sedes',     'Crear/editar/eliminar sedes'),
    ('areas.gestionar',       'estructura','gestionar','Gestionar áreas',     'Crear/editar/eliminar áreas'),
    ('cargos.gestionar',      'estructura','gestionar','Gestionar cargos',    'Crear/editar/eliminar cargos'),
    ('firmantes.gestionar',   'estructura','gestionar','Gestionar firmantes', 'Crear/editar/eliminar firmantes'),

    -- Usuarios
    ('usuarios.crear',        'usuarios',  'crear',  'Invitar usuarios',      'Invitar nuevos usuarios a la empresa'),
    ('usuarios.editar',       'usuarios',  'editar', 'Editar usuarios',       'Cambiar rol de usuarios'),
    ('usuarios.desactivar',   'usuarios',  'desactivar','Desactivar usuarios','Desactivar usuarios de la empresa'),

    -- Reportes
    ('reportes.ver',          'reportes',  'ver',    'Ver reportes',          'Ver dashboards y reportes'),
    ('reportes.exportar',     'reportes',  'exportar','Exportar reportes',    'Descargar reportes en Excel/CSV'),

    -- Auditoría
    ('auditoria.ver',         'auditoria', 'ver',    'Ver auditoría',         'Ver log de auditoría'),

    -- Sistema (solo superadmin)
    ('sistema.superadmin',    'sistema',   'admin',  'Superadministrador',    'Acceso total al sistema'),
    ('sistema.parametros',    'sistema',   'editar', 'Editar parámetros',     'Modificar parámetros laborales globales')

on conflict (codigo) do nothing;


-- ═══════════════════════════════════════════════════════════════════════════
-- 2. ROLES DE SISTEMA (empresa_id = null)
-- ═══════════════════════════════════════════════════════════════════════════
insert into roles (codigo, nombre, descripcion, es_sistema, empresa_id) values
    ('superadmin',    'Superadministrador',        'Acceso total al sistema',              true, null),
    ('admin_empresa', 'Administrador de empresa',  'Administrador con todos los permisos', true, null),
    ('rrhh',          'Recursos Humanos',          'Gestión de empleados y documentos',    true, null),
    ('aprobador',     'Aprobador',                 'Aprueba y firma documentos',           true, null),
    ('operador',      'Operador',                  'Genera documentos sin aprobar',        true, null),
    ('consultor',     'Consultor',                 'Solo lectura de datos',                true, null),
    ('empleado',      'Empleado',                  'Consulta sus propios documentos',      true, null)
on conflict (empresa_id, codigo) do nothing;


-- ═══════════════════════════════════════════════════════════════════════════
-- 3. ROL_PERMISOS
-- ═══════════════════════════════════════════════════════════════════════════
-- Superadmin: todos los permisos
insert into rol_permisos (rol_id, permiso_id)
select r.id, p.id
from roles r, permisos p
where r.codigo = 'superadmin' and r.es_sistema = true
on conflict do nothing;

-- Admin de empresa: todos menos sistema.superadmin y sistema.parametros
insert into rol_permisos (rol_id, permiso_id)
select r.id, p.id
from roles r, permisos p
where r.codigo = 'admin_empresa' and r.es_sistema = true
  and p.codigo not in ('sistema.superadmin', 'sistema.parametros')
on conflict do nothing;

-- RRHH: todo lo operativo, no gestiona usuarios ni superadmin
insert into rol_permisos (rol_id, permiso_id)
select r.id, p.id
from roles r, permisos p
where r.codigo = 'rrhh' and r.es_sistema = true
  and p.codigo in (
      'empresa.ver',
      'empleados.crear','empleados.ver','empleados.editar','empleados.eliminar','empleados.importar',
      'documentos.generar','documentos.ver','documentos.enviar','documentos.anular',
      'liquidaciones.crear','liquidaciones.ver',
      'plantillas.crear','plantillas.editar',
      'sedes.gestionar','areas.gestionar','cargos.gestionar','firmantes.gestionar',
      'reportes.ver','reportes.exportar'
  )
on conflict do nothing;

-- Aprobador: ver + aprobar + firmar
insert into rol_permisos (rol_id, permiso_id)
select r.id, p.id
from roles r, permisos p
where r.codigo = 'aprobador' and r.es_sistema = true
  and p.codigo in (
      'empresa.ver',
      'empleados.ver',
      'documentos.ver','documentos.aprobar','documentos.firmar','documentos.enviar',
      'liquidaciones.ver','liquidaciones.validar',
      'reportes.ver'
  )
on conflict do nothing;

-- Operador: crea documentos pero no aprueba
insert into rol_permisos (rol_id, permiso_id)
select r.id, p.id
from roles r, permisos p
where r.codigo = 'operador' and r.es_sistema = true
  and p.codigo in (
      'empresa.ver',
      'empleados.ver','empleados.crear','empleados.editar',
      'documentos.generar','documentos.ver',
      'liquidaciones.crear','liquidaciones.ver',
      'reportes.ver'
  )
on conflict do nothing;

-- Consultor: solo lectura
insert into rol_permisos (rol_id, permiso_id)
select r.id, p.id
from roles r, permisos p
where r.codigo = 'consultor' and r.es_sistema = true
  and p.codigo in (
      'empresa.ver',
      'empleados.ver',
      'documentos.ver',
      'liquidaciones.ver',
      'reportes.ver'
  )
on conflict do nothing;

-- Empleado: ver su propia info (RLS adicional restringe)
insert into rol_permisos (rol_id, permiso_id)
select r.id, p.id
from roles r, permisos p
where r.codigo = 'empleado' and r.es_sistema = true
  and p.codigo in ('documentos.ver')
on conflict do nothing;


-- ═══════════════════════════════════════════════════════════════════════════
-- 4. PLANES SaaS
-- ═══════════════════════════════════════════════════════════════════════════
insert into planes (codigo, nombre, precio_mensual, precio_anual, max_empleados,
                     max_documentos_mes, max_usuarios, max_empresas,
                     permite_word, permite_correo, permite_plantillas_custom,
                     permite_multiempresa, orden) values
    ('gratuito',    'Gratuito',        0,      0,        5,   5,   1, 1, false, false, false, false, 1),
    ('emprendedor', 'Emprendedor',     49900,  499000,   15,  50,  2, 1, true,  true,  false, false, 2),
    ('pyme',        'PYME',            99900,  999000,   50,  200, 5, 1, true,  true,  true,  false, 3),
    ('empresa',     'Empresa',         199900, 1999000,  200, 1000,15, 1, true,  true,  true,  false, 4),
    ('empresarial', 'Empresarial',     299900, 2999000,  9999,9999,50,20,true,  true,  true,  true,  5)
on conflict (codigo) do update set
    precio_mensual = excluded.precio_mensual,
    precio_anual   = excluded.precio_anual,
    max_empleados  = excluded.max_empleados,
    max_documentos_mes = excluded.max_documentos_mes,
    max_usuarios   = excluded.max_usuarios,
    max_empresas   = excluded.max_empresas,
    permite_multiempresa = excluded.permite_multiempresa;


-- ═══════════════════════════════════════════════════════════════════════════
-- 5. PARÁMETROS LABORALES COLOMBIA 2024, 2025, 2026
-- ═══════════════════════════════════════════════════════════════════════════
insert into parametros_laborales (pais, anio, salario_minimo, auxilio_transporte,
                                    tope_auxilio_transporte, fuente,
                                    fecha_inicio_vigencia, estado) values
    ('Colombia', 2024, 1300000, 162000, 2600000, 'Decreto 2292 de 2023', '2024-01-01', 'anterior'),
    ('Colombia', 2025, 1423500, 200000, 2847000, 'Decreto 1572 de 2024', '2025-01-01', 'anterior'),
    ('Colombia', 2026, 1560000, 215000, 3120000, 'Decreto 2026 (estimado)', '2026-01-01', 'vigente')
on conflict (pais, anio) do nothing;


-- ═══════════════════════════════════════════════════════════════════════════
-- FIN DEL SEED
-- ═══════════════════════════════════════════════════════════════════════════
