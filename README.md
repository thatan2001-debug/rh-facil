# Gestor RH IA

Plataforma SaaS de gestión documental de Recursos Humanos para PYMES colombianas.

**Estado:** MVP en producción · Etapa 2 de seguridad completada · [rh-facil.onrender.com](https://rh-facil.onrender.com)

---

## Qué hace

- Genera certificados laborales, cartas de vacaciones, contratos, otrosí y cartas de terminación en PDF
- Calcula liquidaciones de prestaciones sociales conforme al CST colombiano
- Gestiona base de datos de empleados (importación desde Excel + CRUD)
- Envía documentos por correo automáticamente
- Multiempresa preparado para contadores y gestores

---

## Instalación local

### Requisitos
- Python 3.11 o superior
- Cuenta en Supabase (opcional en desarrollo, obligatorio en producción)
- Cuenta en Brevo para SMTP (opcional en desarrollo)

### Pasos

```bash
# 1. Clonar el repo
git clone https://github.com/thatan2001-debug/gestorh.git
cd gestorh

# 2. Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate      # Linux/Mac
# .venv\Scripts\activate       # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables
cp .env.example .env
# Editar .env con tus credenciales

# 5. Ejecutar migraciones en Supabase (una vez)
# → Ver sección "Configuración de Supabase" abajo

# 6. Crear el primer administrador
python scripts/crear_primer_admin.py

# 7. Ejecutar la app
streamlit run app.py
```

Abre http://localhost:8501

---

## Variables de entorno

Ver [`.env.example`](.env.example) para la lista completa.

**Mínimo para desarrollo:**
```bash
ENVIRONMENT=development
```

**Mínimo para producción:**
```bash
ENVIRONMENT=production
APP_URL=https://rh-facil.onrender.com
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=service_role_key
SMTP_HOST=smtp-relay.brevo.com
SMTP_USER=xxx
SMTP_PASS=xxx
SMTP_FROM=noreply@dominio.com
```

**IMPORTANTE:** en producción, si falta cualquier variable crítica, la app **NO arranca**.

---

## Configuración de Supabase

1. Crea proyecto en [supabase.com](https://supabase.com)
2. Copia `SUPABASE_URL` y `service_role_key` (Settings → API)
3. Ve al SQL Editor y ejecuta los archivos en `migrations/` en orden:

```
migrations/supabase_schema_v2.sql    # Schema principal
migrations/003_intentos_login.sql    # Rate limiting
```

4. Verifica que las políticas RLS estén habilitadas (Table Editor → cada tabla → RLS)

---

## Ejecutar pruebas

```bash
# Tests unitarios de cálculos legales (17 tests)
python tests/test_calculos.py

# Tests del servicio de autenticación (21 tests)
python tests/test_auth_service.py

# Tests de configuración (12 tests)
python tests/test_settings.py
```

Todos deben pasar antes de hacer merge a main.

---

## Despliegue en Render

### Configuración
- **Runtime:** Python 3.11
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`
- **Environment:** configurar todas las variables de `.env.example`

### Keep-alive
Render en plan gratuito duerme la app después de 15 minutos.

Configura UptimeRobot (gratis) para hacer ping cada 5 minutos:
- URL: `https://tu-app.onrender.com`
- Ver [`KEEP_ALIVE.md`](KEEP_ALIVE.md) para detalles

---

## Configuración del correo (Brevo)

1. Regístrate gratis en [brevo.com](https://www.brevo.com) — 300 correos/día
2. En Brevo: Senders & IP → verifica el correo remitente
3. En Brevo: SMTP & API → SMTP → generar clave
4. Configura las variables `SMTP_*` en `.env` (o Render Environment)

---

## Arquitectura

```
gestorh/
├── app.py                          # Router principal Streamlit
├── config/
│   └── settings.py                 # Configuración central
├── services/                       # Capa de lógica (S2.2+)
│   ├── auth_service.py            # Argon2 + retrocompat SHA-256
│   └── rate_limit_service.py      # Rate limiting login
├── utils/                          # Utilidades y capas legacy
│   ├── auth.py                    # Interfaz de login/registro
│   ├── db.py                      # Base de datos (Supabase + JSON fallback)
│   ├── calcular_liquidacion.py    # Motor legal
│   ├── plantillas_disenio.py      # Generación PDF
│   └── ...
├── scripts/
│   └── crear_primer_admin.py      # Script seguro para primer admin
├── migrations/                     # SQL de Supabase
│   ├── supabase_schema_v2.sql
│   └── 003_intentos_login.sql
├── tests/
│   ├── test_calculos.py           # 17 tests
│   ├── test_auth_service.py       # 21 tests
│   └── test_settings.py           # 12 tests
├── requirements.txt
├── .env.example
└── SECURITY.md                    # Guía de seguridad completa
```

---

## Solución de errores comunes

### La app no arranca en producción
- Verifica que `ENVIRONMENT=production` esté configurado en Render
- Verifica que `SUPABASE_URL` y `SUPABASE_KEY` estén configuradas
- Ver logs de Render en el dashboard

### Los usuarios no pueden entrar después de la migración
- Los usuarios con hash SHA-256 legacy se migran automáticamente al primer login
- Si un usuario reporta "contraseña incorrecta", verifica que su cuenta esté activada por admin
- Si sigue fallando, resetea su contraseña con:
  ```bash
  python scripts/crear_primer_admin.py  # opción reset
  ```

### Cuenta bloqueada temporalmente
- Sistema de rate limiting: 5 intentos fallidos en 15 min → bloqueo 15 min
- Espera 15 minutos o el admin puede limpiar los intentos manualmente en la tabla `intentos_login`

### Correos no llegan
- Verifica que el remitente esté verificado en Brevo
- Verifica que `SMTP_PASS` sea la clave SMTP (no la contraseña de la cuenta)
- Los correos pueden llegar a spam la primera vez

---

## Roadmap

**Ya completado:**
- ✅ Etapa 1: Auditoría
- ✅ Etapa 2: Seguridad (S2.1 a S2.5) — Argon2, rate limiting, sin credenciales

**Próximas etapas:**
- 🔜 Etapa 3: Refactor arquitectónico de `app.py`
- 🔜 Etapa 4: Multiempresa real con roles y permisos
- 🔜 Etapa 5: Empleados persistentes con validaciones
- 🔜 Etapa 6: Motor de plantillas DOCX

Ver [`SECURITY.md`](SECURITY.md) para el historial de cambios de seguridad.

---

## Contribuir

- Trabaja en ramas `feature/*`
- Todos los cambios requieren tests que pasen localmente
- Ver [`SECURITY.md`](SECURITY.md) para prácticas de seguridad
- Nunca subir `.env` ni credenciales al repositorio

---

## Licencia

Proyecto privado. Todos los derechos reservados.

**Contacto:** Jhonathan Castaño Varela · Medellín, Colombia
