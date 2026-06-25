"""
Sistema de autenticación simple para RH Fácil.
Usuarios guardados en JSON local. Para producción migrar a Supabase/PostgreSQL.
"""

import json
import hashlib
import os
from pathlib import Path
from datetime import datetime

ARCHIVO_USUARIOS = Path("salidas/.usuarios.json")

# ── Usuarios precargados (demo + admin) ─────────────────────────────────────
USUARIOS_INICIALES = {
    "demo@rhfacil.co": {
        "nombre": "Usuario Demo",
        "password_hash": hashlib.sha256("RHFacil2026".encode()).hexdigest(),
        "plan": "pro",
        "documentos_usados": 0,
        "fecha_registro": "2026-01-01",
        "activo": True,
        "es_demo": True,
    },
    "admin@rhfacil.co": {
        "nombre": "Administrador",
        "password_hash": hashlib.sha256("Admin2026*".encode()).hexdigest(),
        "plan": "empresarial",
        "documentos_usados": 0,
        "fecha_registro": "2026-01-01",
        "activo": True,
        "es_demo": False,
    },
}


def _cargar_usuarios() -> dict:
    if ARCHIVO_USUARIOS.exists():
        try:
            with open(ARCHIVO_USUARIOS) as f:
                return json.load(f)
        except Exception:
            pass
    # Primera vez: crear con usuarios iniciales
    _guardar_usuarios(USUARIOS_INICIALES)
    return USUARIOS_INICIALES.copy()


def _guardar_usuarios(usuarios: dict):
    ARCHIVO_USUARIOS.parent.mkdir(exist_ok=True)
    with open(ARCHIVO_USUARIOS, "w") as f:
        json.dump(usuarios, f, indent=2)


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def login(email: str, password: str) -> tuple[bool, str, dict | None]:
    """
    Intenta hacer login.
    Retorna (éxito, mensaje, datos_usuario | None)
    """
    email = email.strip().lower()
    usuarios = _cargar_usuarios()

    if email not in usuarios:
        return False, "Correo no registrado.", None

    usuario = usuarios[email]
    if not usuario.get("activo", True):
        return False, "Esta cuenta está desactivada.", None

    if usuario["password_hash"] != _hash(password):
        return False, "Contraseña incorrecta.", None

    return True, "¡Bienvenido!", {
        "email": email,
        "nombre": usuario["nombre"],
        "plan": usuario["plan"],
        "documentos_usados": usuario.get("documentos_usados", 0),
        "es_demo": usuario.get("es_demo", False),
    }


def registrar(email: str, nombre: str, password: str) -> tuple[bool, str]:
    """Registra un nuevo usuario con plan gratuito."""
    email = email.strip().lower()
    if not email or "@" not in email:
        return False, "Correo electrónico inválido."
    if len(password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres."
    if not nombre.strip():
        return False, "Ingresa tu nombre."

    usuarios = _cargar_usuarios()
    if email in usuarios:
        return False, "Ya existe una cuenta con ese correo."

    usuarios[email] = {
        "nombre": nombre.strip(),
        "password_hash": _hash(password),
        "plan": "gratuito",
        "documentos_usados": 0,
        "fecha_registro": datetime.now().strftime("%Y-%m-%d"),
        "activo": True,
        "es_demo": False,
    }
    _guardar_usuarios(usuarios)
    return True, "Cuenta creada exitosamente."


def registrar_uso_usuario(email: str, cantidad: int):
    """Suma documentos usados al contador del usuario."""
    usuarios = _cargar_usuarios()
    if email in usuarios:
        usuarios[email]["documentos_usados"] = (
            usuarios[email].get("documentos_usados", 0) + cantidad
        )
        _guardar_usuarios(usuarios)


def obtener_limite_plan(plan: str) -> dict:
    from utils.plan_control import PLANES
    info = PLANES.get(plan, PLANES["gratuito"])
    return {
        "max_docs": info["max_documentos"],
        "tiene_limite": info["limite"],
        "dias_prueba": info.get("dias_prueba"),
    }
