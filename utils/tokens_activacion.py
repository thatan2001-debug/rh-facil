"""
Tokens de activación de cuenta para Gestor RH IA.

Flujo:
1. Usuario se registra → se genera token de 6 dígitos + link con hash largo
2. Token/link se envía por correo automáticamente vía SMTP
3. Usuario ingresa el código de 6 dígitos O hace clic en el link
4. La cuenta se activa automáticamente y puede empezar a usar la app

Los tokens expiran en 24 horas.
"""

import os
import json
import secrets
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

# ── Almacenamiento (Supabase con fallback JSON) ────────────────────────────────
_JSON_PATH = Path("salidas/.tokens_activacion.json")
TOKEN_EXPIRACION_HORAS = 24


def _cargar() -> dict:
    if _JSON_PATH.exists():
        try:
            return json.load(open(_JSON_PATH, encoding="utf-8"))
        except Exception:
            pass
    return {}


def _guardar(data: dict):
    _JSON_PATH.parent.mkdir(exist_ok=True)
    with open(_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _db_sb():
    """Cliente Supabase si está disponible."""
    try:
        from utils.db import _db
        return _db()
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# GENERACIÓN Y VALIDACIÓN DE TOKENS
# ══════════════════════════════════════════════════════════════════════════════

def generar_token(email: str) -> tuple[str, str]:
    """
    Genera un token de 6 dígitos + hash largo para el link de activación.
    Retorna: (codigo_6_digitos, hash_link)
    """
    email = email.strip().lower()

    # Código legible de 6 dígitos
    codigo = f"{secrets.randbelow(1000000):06d}"

    # Hash largo para el link (URL-safe)
    hash_link = secrets.token_urlsafe(32)

    # Fecha de expiración
    expira = (datetime.now() + timedelta(hours=TOKEN_EXPIRACION_HORAS)).isoformat()

    payload = {
        "email":       email,
        "codigo":      codigo,
        "hash_link":   hash_link,
        "expira":      expira,
        "usado":       False,
        "creado_en":   datetime.now().isoformat(),
    }

    sb = _db_sb()
    if sb:
        try:
            # Eliminar tokens previos del mismo usuario si existen
            sb.table("tokens_activacion").delete().eq("email", email).execute()
            sb.table("tokens_activacion").insert(payload).execute()
        except Exception as e:
            print(f"Aviso: token no persistido en Supabase ({e}), usando JSON")

    # Siempre respaldar en JSON local también
    tokens = _cargar()
    tokens[email] = payload
    _guardar(tokens)

    return codigo, hash_link


def validar_token(email: str = "", codigo: str = "", hash_link: str = "") -> tuple[bool, str, str]:
    """
    Valida un token por código de 6 dígitos O por hash del link.
    Retorna: (valido, mensaje, email_asociado)
    """
    if not codigo and not hash_link:
        return False, "Debes ingresar un código o link válido.", ""

    sb = _db_sb()

    # Buscar en Supabase primero
    if sb:
        try:
            if hash_link:
                r = sb.table("tokens_activacion").select("*")\
                    .eq("hash_link", hash_link).single().execute()
            else:
                r = sb.table("tokens_activacion").select("*")\
                    .eq("email", email.strip().lower())\
                    .eq("codigo", codigo).single().execute()
            token = r.data
            if token:
                return _validar_payload(token)
        except Exception:
            pass  # cae al fallback JSON

    # Fallback JSON
    tokens = _cargar()
    if hash_link:
        # Buscar por hash del link
        for e, t in tokens.items():
            if t.get("hash_link") == hash_link:
                return _validar_payload(t)
        return False, "Enlace de activación no válido o expirado.", ""
    else:
        # Buscar por código
        email = email.strip().lower()
        t = tokens.get(email)
        if not t:
            return False, "No hay un código de activación pendiente para este correo.", ""
        if t.get("codigo") != codigo.strip():
            return False, "El código ingresado no coincide. Verifica el correo.", ""
        return _validar_payload(t)


def _validar_payload(token: dict) -> tuple[bool, str, str]:
    """Valida que un token no esté usado ni expirado."""
    email = token.get("email", "")
    if token.get("usado"):
        return False, "Este token ya fue utilizado previamente.", email

    try:
        expira = datetime.fromisoformat(str(token.get("expira","")))
        if datetime.now() > expira:
            return False, "El token ha expirado. Solicita uno nuevo.", email
    except Exception:
        return False, "Token con formato inválido.", email

    return True, "Token válido.", email


def marcar_usado(email: str):
    """Marca el token como usado después de activar la cuenta."""
    email = email.strip().lower()
    sb = _db_sb()
    if sb:
        try:
            sb.table("tokens_activacion").update({"usado": True})\
                .eq("email", email).execute()
        except Exception:
            pass

    tokens = _cargar()
    if email in tokens:
        tokens[email]["usado"] = True
        _guardar(tokens)


def limpiar_expirados():
    """Elimina tokens expirados (llamar periódicamente o al iniciar la app)."""
    tokens = _cargar()
    ahora = datetime.now()
    activos = {}
    for e, t in tokens.items():
        try:
            expira = datetime.fromisoformat(str(t.get("expira","")))
            if expira > ahora and not t.get("usado"):
                activos[e] = t
        except Exception:
            pass
    if len(activos) != len(tokens):
        _guardar(activos)
