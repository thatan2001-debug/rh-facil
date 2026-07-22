"""
Servicio de empresas (Etapa 4).

Responsabilidades:
- CRUD de empresas
- Listar empresas de un usuario
- Cambiar empresa activa

No mezcla UI ni auth: solo lógica de negocio + BD.
"""

from typing import Optional
from datetime import datetime

from utils.db import _db, supabase_ok


class EmpresaService:
    """Servicio de empresas — funciona sobre Supabase y fallback JSON."""

    # ── Consultas ────────────────────────────────────────────────────────

    def obtener(self, empresa_id: str) -> Optional[dict]:
        """Obtiene una empresa por su UUID."""
        if not empresa_id:
            return None
        if supabase_ok():
            try:
                r = _db().table("empresas").select("*").eq("id", empresa_id).execute()
                return r.data[0] if r.data else None
            except Exception:
                return None
        # Fallback JSON: no aplica en modo simple
        return None

    def listar_de_perfil(self, perfil_id: str) -> list:
        """
        Lista todas las empresas a las que un perfil está vinculado.
        Retorna: [{id, razon_social, rol_codigo, rol_nombre, estado}, ...]
        """
        if not perfil_id or not supabase_ok():
            return []

        try:
            # empresa_usuarios + join implícito con empresas y roles
            r = _db().table("empresa_usuarios").select(
                "id, estado, "
                "empresa:empresas(id, razon_social, nit, logo_url, plan, estado), "
                "rol:roles(id, codigo, nombre)"
            ).eq("perfil_id", perfil_id).eq("estado", "activo").execute()

            resultado = []
            for row in (r.data or []):
                empresa = row.get("empresa") or {}
                rol = row.get("rol") or {}
                if empresa.get("estado") != "activa":
                    continue
                resultado.append({
                    "id":            empresa.get("id"),
                    "razon_social":  empresa.get("razon_social"),
                    "nit":           empresa.get("nit"),
                    "logo_url":      empresa.get("logo_url"),
                    "plan":          empresa.get("plan", "gratuito"),
                    "rol_codigo":    rol.get("codigo"),
                    "rol_nombre":    rol.get("nombre"),
                    "vinculo_id":    row.get("id"),
                })
            return resultado
        except Exception as e:
            try:
                from utils.logs import log_error
                log_error("empresa.listar.error", perfil_id=perfil_id, error=str(e))
            except Exception:
                pass
            return []

    def obtener_por_nit(self, nit: str) -> Optional[dict]:
        """Busca una empresa por NIT."""
        if not nit or not supabase_ok():
            return None
        try:
            r = _db().table("empresas").select("*").eq("nit", nit).execute()
            return r.data[0] if r.data else None
        except Exception:
            return None

    # ── Escritura ────────────────────────────────────────────────────────

    def crear(self, datos: dict, creado_por_perfil_id: str,
               rol_creador: str = "admin_empresa") -> tuple:
        """
        Crea una empresa Y vincula al perfil creador como admin_empresa.
        Retorna: (ok, mensaje, empresa_id)
        """
        if not supabase_ok():
            return False, "Supabase no configurado", None

        razon_social = (datos.get("razon_social") or "").strip()
        if not razon_social:
            return False, "razon_social es obligatorio", None

        # Validar NIT único si viene
        nit = (datos.get("nit") or "").strip()
        if nit:
            existe = self.obtener_por_nit(nit)
            if existe:
                return False, f"Ya existe una empresa con NIT {nit}", None

        payload = {
            "razon_social":        razon_social,
            "nombre_comercial":    datos.get("nombre_comercial"),
            "nit":                 nit or None,
            "direccion":           datos.get("direccion"),
            "ciudad":              datos.get("ciudad"),
            "departamento":        datos.get("departamento"),
            "pais":                datos.get("pais", "Colombia"),
            "telefono":            datos.get("telefono"),
            "correo":              datos.get("correo"),
            "representante_legal": datos.get("representante_legal"),
            "representante_documento": datos.get("representante_documento"),
            "logo_url":            datos.get("logo_url"),
            "membrete_url":        datos.get("membrete_url"),
            "plan":                datos.get("plan", "gratuito"),
            "estado":              "activa",
        }

        # Filtrar None para no sobreescribir defaults
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            r = _db().table("empresas").insert(payload).execute()
            if not r.data:
                return False, "No se pudo crear la empresa", None
            empresa_id = r.data[0]["id"]
        except Exception as e:
            return False, f"Error creando empresa: {e}", None

        # Vincular al creador
        try:
            # Obtener id del rol
            r_rol = _db().table("roles").select("id").eq("codigo", rol_creador).execute()
            if not r_rol.data:
                return False, f"Rol {rol_creador} no existe", empresa_id
            rol_id = r_rol.data[0]["id"]

            _db().table("empresa_usuarios").insert({
                "empresa_id": empresa_id,
                "perfil_id":  creado_por_perfil_id,
                "rol_id":     rol_id,
                "estado":     "activo",
            }).execute()
        except Exception as e:
            try:
                from utils.logs import log_error
                log_error("empresa.crear.vinculo_fallo",
                    empresa_id=empresa_id, error=str(e))
            except Exception:
                pass
            return False, f"Empresa creada pero vinculo falló: {e}", empresa_id

        try:
            from utils.logs import log_info
            log_info("empresa.creada", empresa_id=empresa_id,
                creado_por=creado_por_perfil_id)
        except Exception:
            pass

        return True, "Empresa creada", empresa_id

    def actualizar(self, empresa_id: str, datos: dict) -> tuple:
        """
        Actualiza datos de una empresa.
        Retorna: (ok, mensaje)
        """
        if not supabase_ok():
            return False, "Supabase no configurado"
        if not empresa_id:
            return False, "empresa_id requerido"

        # Solo permitir actualizar campos conocidos
        campos_permitidos = {
            "razon_social", "nombre_comercial", "nit", "direccion",
            "ciudad", "departamento", "pais", "telefono", "correo",
            "representante_legal", "representante_tipo_doc",
            "representante_documento", "logo_url", "membrete_url",
            "zona_horaria", "moneda", "formato_fecha",
            "prefijo_documental", "plan",
        }
        payload = {k: v for k, v in datos.items()
                   if k in campos_permitidos and v is not None}

        if not payload:
            return False, "Nada que actualizar"

        try:
            _db().table("empresas").update(payload).eq("id", empresa_id).execute()
            return True, "Empresa actualizada"
        except Exception as e:
            return False, f"Error: {e}"

    def suspender(self, empresa_id: str) -> bool:
        """Suspende una empresa (soft delete)."""
        if not supabase_ok() or not empresa_id:
            return False
        try:
            _db().table("empresas").update(
                {"estado": "suspendida"}
            ).eq("id", empresa_id).execute()
            return True
        except Exception:
            return False


# Instancia global lista para importar
empresa_service = EmpresaService()
