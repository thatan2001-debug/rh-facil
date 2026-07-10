"""
Puente de compatibilidad — mapea los nombres que usa app.py
a las funciones reales de utils.db
"""
from utils.db import (
    supabase_ok as usar_supabase,
    usuario_obtener, usuario_crear, usuario_activar,
    usuario_desactivar, usuario_cambiar_plan,
    usuario_sumar_docs, usuario_eliminar,
    usuarios_listar, empresa_guardar, empresa_cargar,
    empresa_onboarding_ok, historial_registrar, stats_admin,
)
import hashlib

def _hash(pw): return hashlib.sha256(pw.encode()).hexdigest()

def usuario_login(email: str, password: str):
    email = email.strip().lower()
    u = usuario_obtener(email)
    if not u: return False, "Correo no registrado.", None
    if not u.get("activo", False): return False, "Cuenta pendiente de activación.", None
    if u.get("password_hash") != _hash(password): return False, "Contraseña incorrecta.", None
    return True, "Bienvenido", {
        "email": email,
        "nombre": u.get("nombre",""),
        "plan": u.get("plan","gratuito"),
        "documentos_usados": u.get("docs_usados", 0),
        "es_admin": u.get("es_admin", False),
        "es_demo": u.get("es_demo", False),
    }

def usuario_registrar(email: str, nombre: str, password: str,
                       empresa: str = "", telefono: str = ""):
    email = email.strip().lower()
    if not email or "@" not in email: return False, "Correo inválido."
    if len(password) < 6: return False, "Contraseña mínimo 6 caracteres."
    if not nombre.strip(): return False, "Nombre requerido."
    if usuario_obtener(email): return False, "Ya existe una cuenta con ese correo."
    ok = usuario_crear(email, nombre.strip(), _hash(password))
    if ok: return True, "Registro exitoso. El administrador activará tu cuenta pronto."
    return False, "Error al registrar. Intenta de nuevo."

def usuario_registrar_uso(email: str, cantidad: int):
    usuario_sumar_docs(email, cantidad)

def admin_listar(): return usuarios_listar()
def admin_activar(email): return usuario_activar(email)
def admin_cambiar_plan(email, plan): return usuario_cambiar_plan(email, plan)
def admin_eliminar(email): return usuario_eliminar(email)
def admin_stats(): return stats_admin()
