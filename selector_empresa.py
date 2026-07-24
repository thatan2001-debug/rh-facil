"""
Servicio de perfiles (Etapa 4).

Un "perfil" es la identidad global del usuario en el SaaS (email único).
Un perfil puede estar vinculado a varias empresas con diferentes roles.

Este servicio se usa junto con auth_service:
- auth_service: hashea/verifica contraseñas
- perfil_service: gestiona los datos del perfil (nombre, activo, etc.)
"""

from typing import Optional

from utils.db import _db, supabase_ok


class PerfilService:
    """Servicio de perfiles de usuario."""

    def obtener_por_email(self, email: str) -> Optional[dict]:
        """Obtiene un perfil por email."""
        if not email or not supabase_ok():
            return None
        email = email.strip().lower()
        try:
            r = _db().table("perfiles").select("*").eq("email", email).execute()
            return r.data[0] if r.data else None
        except Exception:
            return None

    def obtener_por_id(self, perfil_id: str) -> Optional[dict]:
        """Obtiene un perfil por UUID."""
        if not perfil_id or not supabase_ok():
            return None
        try:
            r = _db().table("perfiles").select("*").eq("id", perfil_id).execute()
            return r.data[0] if r.data else None
        except Exception:
            return None

    def crear(self, email: str, nombre: str, password_hash: str,
               es_superadmin: bool = False, activo: bool = False) -> tuple:
        """
        Crea un perfil nuevo.
        Retorna: (ok, mensaje, perfil_id)
        """
        if not supabase_ok():
            return False, "Supabase no configurado", None

        email = email.strip().lower()
        if not email or "@" not in email:
            return False, "Email inválido", None

        # Verificar que no exista
        if self.obtener_por_email(email):
            return False, "Ya existe un perfil con ese email", None

        try:
            r = _db().table("perfiles").insert({
                "email":         email,
                "nombre":        nombre.strip(),
                "password_hash": password_hash,
                "activo":        activo,
                "es_superadmin": es_superadmin,
            }).execute()
            if not r.data:
                return False, "No se pudo crear el perfil", None
            return True, "Perfil creado", r.data[0]["id"]
        except Exception as e:
            return False, f"Error: {e}", None

    def actualizar_password_hash(self, email: str, nuevo_hash: str) -> bool:
        """Actualiza el hash de contraseña de un perfil (usado por auth_service en rehash)."""
        if not supabase_ok() or not email:
            return False
        email = email.strip().lower()
        try:
            _db().table("perfiles").update(
                {"password_hash": nuevo_hash}
            ).eq("email", email).execute()
            return True
        except Exception:
            return False

    def activar(self, email: str) -> bool:
        """Marca un perfil como activo."""
        if not supabase_ok() or not email:
            return False
        try:
            _db().table("perfiles").update(
                {"activo": True}
            ).eq("email", email.strip().lower()).execute()
            return True
        except Exception:
            return False

    def registrar_login(self, perfil_id: str) -> bool:
        """Actualiza ultimo_login al momento actual."""
        from datetime import datetime
        if not supabase_ok() or not perfil_id:
            return False
        try:
            _db().table("perfiles").update(
                {"ultimo_login": datetime.now().isoformat()}
            ).eq("id", perfil_id).execute()
            return True
        except Exception:
            return False


perfil_service = PerfilService()
