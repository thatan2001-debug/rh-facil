"""
Puente de compatibilidad — mapea los nombres que usa app.py a funciones
reales de utils.db y utils.auth.

⚠️ Migrado en S2.2 a usar auth_service (Argon2 + retrocompat SHA-256).
"""
from utils.db import (
    supabase_ok as usar_supabase,
    usuario_obtener, usuario_crear, usuario_activar,
    usuario_desactivar, usuario_cambiar_plan,
    usuario_sumar_docs, usuario_eliminar,
    usuarios_listar, empresa_guardar, empresa_cargar,
    empresa_onboarding_ok, historial_registrar, stats_admin,
)
from utils.auth import login as _login_real, registrar as _registrar_real


def usuario_login(email: str, password: str):
    """
    Login que retorna el mismo shape que app.py espera.
    Usa Argon2 vía utils.auth.login (con retrocompat SHA-256).
    """
    ok, msg, u = _login_real(email, password)
    if not ok:
        return False, msg, None
    return True, msg, {
        "email":              u["email"],
        "nombre":             u["nombre"],
        "plan":               u["plan"],
        "documentos_usados":  u.get("docs_usados", 0),
        "es_admin":           u.get("es_admin", False),
        "es_demo":            u.get("es_demo", False),
    }


def usuario_registrar(email: str, nombre: str, password: str,
                       empresa: str = "", telefono: str = ""):
    """Registro que usa Argon2 vía utils.auth.registrar."""
    return _registrar_real(email, nombre, password)


def usuario_registrar_uso(email: str, cantidad: int):
    usuario_sumar_docs(email, cantidad)


def admin_listar(): return usuarios_listar()
def admin_activar(email): return usuario_activar(email)
def admin_cambiar_plan(email, plan): return usuario_cambiar_plan(email, plan)
def admin_eliminar(email): return usuario_eliminar(email)
def admin_stats(): return stats_admin()
