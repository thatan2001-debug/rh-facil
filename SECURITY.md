# Guía de Seguridad — Gestor RH IA

**Versión:** 1.0 · Julio 2026
**Alcance:** MVP SaaS documental

Este documento describe las prácticas de seguridad de Gestor RH IA. Se
mantiene actualizado con cada sub-etapa del roadmap de seguridad.

---

## 1. Principios fundamentales

1. **Ningún secreto vive en el repositorio.** Contraseñas, claves API, tokens,
   URLs privadas y credenciales SMTP van en variables de entorno.
2. **La app rechaza arrancar en producción si le faltan variables críticas.**
   No hay "modo degradado con contraseñas por defecto" en producción.
3. **Los hashes de contraseñas usan Argon2id.** Los hashes SHA-256 legacy se
   migran automáticamente al primer login.
4. **RLS (Row Level Security) aísla datos entre empresas.** Un usuario de
   empresa A no puede leer/escribir datos de empresa B.
5. **Auditoría de acciones sensibles.** Cambios de contraseña, activaciones de
   cuenta, generación de documentos, cambios de rol quedan registrados.

---

## 2. Gestión de secretos

### 2.1 Variables de entorno requeridas

Ver [`.env.example`](.env.example) para la lista completa. En resumen:

| Variable | Obligatoria en producción | Ejemplo |
|---|---|---|
| `ENVIRONMENT` | Sí | `production` |
| `APP_URL` | Sí | `https://rh-facil.onrender.com` |
| `SUPABASE_URL` | Sí | `https://xxx.supabase.co` |
| `SUPABASE_KEY` | Sí | (service_role key) |
| `SMTP_HOST` | Sí (para envío de correos) | `smtp-relay.brevo.com` |
| `SMTP_USER` | Sí | (login SMTP) |
| `SMTP_PASS` | Sí | (clave SMTP) |
| `SMTP_FROM` | Sí | `Gestor RH IA <noreply@...>` |

### 2.2 Nunca comitear a Git

- El archivo `.env` está en `.gitignore` y **nunca** debe subirse.
- Antes de cada commit, verifica que no hay secretos en el diff:
  ```bash
  git diff --cached | grep -iE "password|secret|api_key|token" && echo "⚠️ REVISAR"
  ```
- Si alguna vez subiste un secreto: **rótalo inmediatamente** en el proveedor
  (Brevo, Supabase, etc.), no basta con borrar el commit.

### 2.3 Rotación de claves

| Clave | Frecuencia recomendada |
|---|---|
| `SUPABASE_KEY` | Al detectar filtración |
| `SMTP_PASS` | Cada 6 meses o al detectar filtración |
| Contraseñas de administradores | Cada 3 meses |

---

## 3. Autenticación (estado actual)

### 3.1 Hash de contraseñas

**Al 20 de julio de 2026:**

- Nuevas contraseñas: **Argon2id** con parámetros por defecto seguros:
  - `time_cost=3`
  - `memory_cost=65536` (64 MB)
  - `parallelism=4`
- Contraseñas legacy con SHA-256: se aceptan **una sola vez** al login. En
  ese momento se re-hashean a Argon2id y se actualizan en base de datos.
- Se rechaza cualquier hash débil restante al momento de crear/cambiar
  contraseña.

### 3.2 Rate limiting

- **5 intentos fallidos** en 15 minutos → bloqueo temporal de 15 minutos.
- El bloqueo aplica por `(email, IP)` combinado.
- Los intentos fallidos quedan registrados en tabla `intentos_login`.

### 3.3 Sesiones

- Streamlit maneja sesiones en `st.session_state` — vive en memoria del server
  mientras el navegador está abierto.
- **Limitación conocida:** no hay expiración explícita. Roadmap: agregar TTL.

---

## 4. Autorización (roadmap)

Actualmente: solo hay `es_admin: True/False`.

**Roadmap (Etapa 4):**

- Tabla `roles` con: Superadmin, Admin de empresa, RRHH, Aprobador, Empleado
- Tabla `permisos` granular (ej: `empleados.crear`, `documentos.aprobar`)
- Tabla `empresa_usuarios` con relación N:M usuario ↔ empresa
- Todas las queries pasan por el rol y permisos del usuario en esa empresa

---

## 5. Aislamiento multiempresa (roadmap)

Actualmente: RLS está activo pero con política permisiva (`service_role for all`).
**No hay aislamiento real entre empresas.**

**Roadmap (Etapa 4):**

- Políticas RLS por `empresa_id` en tablas: empleados, documentos, historial,
  liquidaciones, plantillas
- Tests automáticos que verifican que:
  - Usuario de empresa A no puede leer empleado de empresa B
  - Usuario de empresa A no puede escribir empleado de empresa B
  - Solo Superadmin puede saltar el aislamiento

---

## 6. Primer administrador

**No hay administradores hardcoded en el código.**

Para crear el primer administrador:

```bash
# Localmente, con variables de entorno cargadas:
python scripts/crear_primer_admin.py \
    --email admin@tuempresa.co \
    --nombre "Nombre Apellido"

# El script pedirá la contraseña por prompt (nunca en línea de comandos)
# La hasheará con Argon2 e insertará en Supabase
```

Después del primer admin, los siguientes se crean desde el panel de admin de
la app.

---

## 7. Correo transaccional

- Se usa **Brevo** (antes Sendinblue) — 300 correos/día en plan gratuito.
- El remitente debe estar verificado en Brevo antes de enviar.
- Los correos de activación incluyen enlace y código de respaldo (24h vida).
- Nunca se guardan contraseñas SMTP en código.

---

## 8. Datos sensibles

### 8.1 Qué se considera sensible

- Contraseñas de usuarios (hasheadas, nunca claras)
- Datos personales de empleados (cédula, correo, teléfono, dirección, salario)
- Datos comerciales de empresas (NIT, representante legal)
- Documentos generados (contratos, liquidaciones, certificados)

### 8.2 Cómo se protegen

- **En tránsito:** HTTPS obligatorio (Render lo provee automáticamente).
- **En reposo:** Supabase encripta la base de datos.
- **En logs:** los logs NO deben contener contraseñas, tokens, ni datos
  personales completos. El módulo `utils/logs.py` requiere revisión.
- **En backups:** Supabase hace backups automáticos (revisar plan).

### 8.3 Ley 1581 de 2012 (Colombia)

Aplicable al tratamiento de datos personales. La app debe:

- Solicitar consentimiento antes de tratar datos personales
- Permitir al titular consultar y rectificar sus datos
- No transferir datos a terceros sin autorización

Estado actual: **pendiente** — se abordará en Etapa 8.

---

## 9. Reporte de vulnerabilidades

Si encuentras una vulnerabilidad de seguridad:

1. **NO la publiques en GitHub Issues ni en foros públicos.**
2. Envía un correo a: `seguridad@tudominio.com` (cambiar por el correo real)
3. Incluye: descripción, pasos para reproducir, impacto estimado
4. Nos comprometemos a responder en 48 horas hábiles

---

## 10. Historial de cambios de seguridad

| Fecha | Sub-etapa | Cambio |
|---|---|---|
| 2026-07-20 | S2.1 | `.env.example` + `.gitignore` + `config/settings.py` + este documento |
| Pendiente | S2.2 | Argon2 con retrocompatibilidad SHA-256 |
| Pendiente | S2.3 | Eliminar credenciales hardcoded, script de primer admin |
| Pendiente | S2.4 | Rate limiting en login |
| Pendiente | S2.5 | Bloqueo de fallback JSON en producción |
