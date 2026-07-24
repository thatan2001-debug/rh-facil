"""
Servicio de autenticación de Gestor RH IA.

Responsabilidades:
- Hash de contraseñas con Argon2id (algoritmo moderno).
- Verificación de contraseñas con retrocompatibilidad para hashes SHA-256 legacy.
- Detección de hashes obsoletos que requieren re-hash.
- Validación de fortaleza de contraseñas.

Este módulo NO conoce la base de datos. Es una capa pura de crypto.

Uso típico (login):
    from services.auth_service import auth_service

    ok, needs_rehash = auth_service.verify_password(password, hash_almacenado)
    if not ok:
        # contraseña incorrecta
        return
    if needs_rehash:
        # hash legacy, generar uno nuevo y actualizar en BD
        nuevo_hash = auth_service.hash_password(password)
        db.actualizar_hash(email, nuevo_hash)
"""

import hashlib
import re
from typing import Tuple

from argon2 import PasswordHasher
from argon2.exceptions import (
    VerifyMismatchError,
    VerificationError,
    InvalidHash,
)

from config.settings import settings


# ══════════════════════════════════════════════════════════════════════════════
# EVALUACIÓN DE FORTALEZA
# ══════════════════════════════════════════════════════════════════════════════

def evaluar_fortaleza_password(password: str) -> Tuple[bool, list]:
    """
    Evalúa si una contraseña cumple con requisitos mínimos.
    Retorna: (cumple, lista_de_problemas)
    """
    problemas = []
    if not isinstance(password, str) or not password:
        return False, ["Contraseña vacía"]

    if len(password) < 8:
        problemas.append("Debe tener al menos 8 caracteres")

    if len(password) > 128:
        problemas.append("No puede exceder 128 caracteres")

    if not re.search(r"[a-zA-Z]", password):
        problemas.append("Debe contener al menos una letra")

    if not re.search(r"[0-9\W]", password):
        problemas.append("Debe contener al menos un número o carácter especial")

    comunes = {
        "12345678", "password", "contraseña", "admin123", "qwerty123",
        "password1", "letmein1", "iloveyou", "welcome1", "monkey12",
        "123456789", "abcdef12", "gestorrh", "admin2026",
    }
    if password.lower() in comunes:
        problemas.append("Es una contraseña muy común, elige otra")

    return len(problemas) == 0, problemas


# ══════════════════════════════════════════════════════════════════════════════
# DETECCIÓN DE TIPO DE HASH
# ══════════════════════════════════════════════════════════════════════════════

_RE_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_RE_ARGON2 = re.compile(r"^\$argon2[id]+\$")


def es_hash_argon2(hash_str: str) -> bool:
    return bool(hash_str and _RE_ARGON2.match(hash_str))


def es_hash_sha256(hash_str: str) -> bool:
    return bool(hash_str and _RE_SHA256.match(hash_str))


def _hash_sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _constant_time_equals(a: str, b: str) -> bool:
    """Comparación en tiempo constante — evita timing attacks."""
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a.encode(), b.encode()):
        result |= x ^ y
    return result == 0


# ══════════════════════════════════════════════════════════════════════════════
# SERVICIO PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

class AuthService:
    """
    Servicio de autenticación con Argon2id.
    Los parámetros se leen de settings.argon2 (configurables por env vars).
    """

    def __init__(self):
        self._ph = PasswordHasher(
            time_cost=settings.argon2["time_cost"],
            memory_cost=settings.argon2["memory_cost"],
            parallelism=settings.argon2["parallelism"],
        )

    def hash_password(self, password: str) -> str:
        """Genera hash Argon2id. Lanza ValueError si es débil."""
        cumple, problemas = evaluar_fortaleza_password(password)
        if not cumple:
            raise ValueError("Contraseña débil: " + "; ".join(problemas))
        return self._ph.hash(password)

    def verify_password(self, password: str, hash_almacenado: str
                         ) -> Tuple[bool, bool]:
        """
        Verifica contraseña. Retorna (correcta, necesita_rehash).
        Detecta automáticamente Argon2 vs SHA-256 legacy.
        """
        if not password or not hash_almacenado:
            return False, False

        # ── Caso 1: Hash Argon2 (moderno) ────────────────────────────────
        if es_hash_argon2(hash_almacenado):
            try:
                self._ph.verify(hash_almacenado, password)
                needs_rehash = self._ph.check_needs_rehash(hash_almacenado)
                return True, needs_rehash
            except VerifyMismatchError:
                return False, False
            except (VerificationError, InvalidHash):
                return False, False

        # ── Caso 2: Hash SHA-256 (legacy) ────────────────────────────────
        if es_hash_sha256(hash_almacenado):
            hash_calculado = _hash_sha256(password)
            if _constant_time_equals(hash_calculado, hash_almacenado):
                # Correcta pero necesita re-hash a Argon2
                return True, True
            return False, False

        # ── Caso 3: Hash desconocido ─────────────────────────────────────
        return False, False


# Instancia global lista para importar
auth_service = AuthService()
