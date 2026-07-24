"""
Servicio de roles y permisos (Etapa 4).

Verifica qué acciones puede hacer un usuario en una empresa específica.

Uso:
    from services.roles_service import roles_service

    # ¿Puede el usuario X generar documentos en la empresa Y?
    if roles_service.puede(perfil_id, empresa_id, "documentos.generar"):
        # generar documento
        pass
    else:
        # error de permisos
        pass
"""

from typing import Optional, Set

from utils.db import _db, supabase_ok


class RolesService:
    """Servicio de roles y permisos."""

    def __init__(self):
        # Cache simple de permisos por rol
        self._cache_permisos_rol = {}
        self._cache_rol_de_usuario = {}

    def _invalidar_cache(self):
        self._cache_permisos_rol.clear()
        self._cache_rol_de_usuario.clear()

    # ── Consultas ────────────────────────────────────────────────────────

    def obtener_rol_de_usuario(self, perfil_id: str,
                                 empresa_id: str) -> Optional[dict]:
        """
        Obtiene el rol de un perfil en una empresa específica.
        Retorna: {id, codigo, nombre} o None si no está vinculado.
        """
        if not perfil_id or not empresa_id or not supabase_ok():
            return None

        cache_key = (perfil_id, empresa_id)
        if cache_key in self._cache_rol_de_usuario:
            return self._cache_rol_de_usuario[cache_key]

        try:
            r = _db().table("empresa_usuarios").select(
                "rol_id, estado, rol:roles(id, codigo, nombre)"
            ).eq("perfil_id", perfil_id).eq("empresa_id", empresa_id).execute()

            if not r.data:
                self._cache_rol_de_usuario[cache_key] = None
                return None

            vinculo = r.data[0]
            if vinculo.get("estado") != "activo":
                self._cache_rol_de_usuario[cache_key] = None
                return None

            rol = vinculo.get("rol") or {}
            resultado = {
                "id":     rol.get("id"),
                "codigo": rol.get("codigo"),
                "nombre": rol.get("nombre"),
            }
            self._cache_rol_de_usuario[cache_key] = resultado
            return resultado
        except Exception:
            return None

    def obtener_permisos_de_rol(self, rol_id: str) -> Set[str]:
        """Retorna un set de códigos de permiso para un rol."""
        if not rol_id or not supabase_ok():
            return set()

        if rol_id in self._cache_permisos_rol:
            return self._cache_permisos_rol[rol_id]

        try:
            r = _db().table("rol_permisos").select(
                "permiso:permisos(codigo)"
            ).eq("rol_id", rol_id).execute()

            permisos = set()
            for row in (r.data or []):
                p = row.get("permiso") or {}
                if p.get("codigo"):
                    permisos.add(p["codigo"])

            self._cache_permisos_rol[rol_id] = permisos
            return permisos
        except Exception:
            return set()

    # ── Verificación de permisos ─────────────────────────────────────────

    def puede(self, perfil_id: str, empresa_id: str,
                permiso_codigo: str) -> bool:
        """
        Verifica si un usuario tiene un permiso específico en una empresa.

        Args:
            perfil_id: UUID del perfil
            empresa_id: UUID de la empresa
            permiso_codigo: código del permiso (ej: 'empleados.crear')

        Returns:
            True si tiene el permiso, False si no.
        """
        if not perfil_id or not empresa_id or not permiso_codigo:
            return False

        # Superadmins pueden todo
        if self._es_superadmin(perfil_id):
            return True

        # Obtener rol del usuario en la empresa
        rol = self.obtener_rol_de_usuario(perfil_id, empresa_id)
        if not rol or not rol.get("id"):
            return False

        # Obtener permisos del rol
        permisos = self.obtener_permisos_de_rol(rol["id"])
        return permiso_codigo in permisos

    def puede_cualquiera(self, perfil_id: str, empresa_id: str,
                          permisos: list) -> bool:
        """True si tiene AL MENOS UNO de los permisos."""
        return any(self.puede(perfil_id, empresa_id, p) for p in permisos)

    def puede_todos(self, perfil_id: str, empresa_id: str,
                      permisos: list) -> bool:
        """True si tiene TODOS los permisos."""
        return all(self.puede(perfil_id, empresa_id, p) for p in permisos)

    def _es_superadmin(self, perfil_id: str) -> bool:
        """Verifica si un perfil es superadmin."""
        if not perfil_id or not supabase_ok():
            return False
        try:
            r = _db().table("perfiles").select("es_superadmin").eq("id", perfil_id).execute()
            return bool(r.data and r.data[0].get("es_superadmin"))
        except Exception:
            return False

    # ── Vinculación usuario ↔ empresa ────────────────────────────────────

    def vincular(self, perfil_id: str, empresa_id: str, rol_codigo: str,
                   invitado_por: str = None) -> tuple:
        """
        Vincula un perfil a una empresa con un rol específico.
        Retorna: (ok, mensaje)
        """
        if not supabase_ok():
            return False, "Supabase no configurado"

        # Obtener rol_id
        try:
            r = _db().table("roles").select("id").eq("codigo", rol_codigo).execute()
            if not r.data:
                return False, f"Rol '{rol_codigo}' no existe"
            rol_id = r.data[0]["id"]
        except Exception as e:
            return False, f"Error: {e}"

        # Verificar si ya está vinculado
        try:
            r = _db().table("empresa_usuarios").select("id, estado")\
                .eq("perfil_id", perfil_id).eq("empresa_id", empresa_id).execute()
            if r.data:
                vinculo_id = r.data[0]["id"]
                # Ya existe → reactivar y cambiar rol
                _db().table("empresa_usuarios").update({
                    "rol_id": rol_id, "estado": "activo",
                }).eq("id", vinculo_id).execute()
                self._invalidar_cache()
                return True, "Vínculo actualizado"
        except Exception:
            pass

        # Crear vínculo nuevo
        try:
            _db().table("empresa_usuarios").insert({
                "perfil_id":    perfil_id,
                "empresa_id":   empresa_id,
                "rol_id":       rol_id,
                "estado":       "activo",
                "invitado_por": invitado_por,
            }).execute()
            self._invalidar_cache()
            return True, "Usuario vinculado"
        except Exception as e:
            return False, f"Error: {e}"

    def desvincular(self, perfil_id: str, empresa_id: str) -> bool:
        """Remueve el vínculo (soft: estado=removido)."""
        if not supabase_ok():
            return False
        try:
            _db().table("empresa_usuarios").update(
                {"estado": "removido"}
            ).eq("perfil_id", perfil_id).eq("empresa_id", empresa_id).execute()
            self._invalidar_cache()
            return True
        except Exception:
            return False

    def cambiar_rol(self, perfil_id: str, empresa_id: str,
                     nuevo_rol_codigo: str) -> tuple:
        """Cambia el rol de un usuario en una empresa."""
        return self.vincular(perfil_id, empresa_id, nuevo_rol_codigo)

    # ── Consultas de usuarios de empresa ─────────────────────────────────

    def listar_usuarios_de_empresa(self, empresa_id: str) -> list:
        """
        Lista todos los usuarios vinculados a una empresa.
        Retorna: [{perfil_id, email, nombre, rol_codigo, rol_nombre, estado}]
        """
        if not empresa_id or not supabase_ok():
            return []
        try:
            r = _db().table("empresa_usuarios").select(
                "id, estado, "
                "perfil:perfiles(id, email, nombre, activo), "
                "rol:roles(id, codigo, nombre)"
            ).eq("empresa_id", empresa_id).execute()

            resultado = []
            for row in (r.data or []):
                perfil = row.get("perfil") or {}
                rol = row.get("rol") or {}
                resultado.append({
                    "vinculo_id":  row.get("id"),
                    "perfil_id":   perfil.get("id"),
                    "email":       perfil.get("email"),
                    "nombre":      perfil.get("nombre"),
                    "activo":      perfil.get("activo", False),
                    "rol_codigo":  rol.get("codigo"),
                    "rol_nombre":  rol.get("nombre"),
                    "estado":      row.get("estado"),
                })
            return resultado
        except Exception:
            return []


# Instancia global
roles_service = RolesService()
