"""
Tests del servicio de autenticación (services/auth_service.py).

Cubre:
- Fortaleza de contraseñas
- Hash con Argon2
- Verificación de hash Argon2
- Verificación de hash SHA-256 legacy (retrocompat)
- Detección de necesidad de re-hash
- Rechazo de contraseñas comunes

Ejecutar:
    python tests/test_auth_service.py
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ══════════════════════════════════════════════════════════════════════════════
# TESTS DE FORTALEZA
# ══════════════════════════════════════════════════════════════════════════════

def test_password_vacio_rechazado():
    from services.auth_service import evaluar_fortaleza_password
    ok, p = evaluar_fortaleza_password("")
    assert not ok, "Contraseña vacía debería fallar"


def test_password_corto_rechazado():
    from services.auth_service import evaluar_fortaleza_password
    ok, p = evaluar_fortaleza_password("abc123")
    assert not ok, "Contraseña de 6 chars debe fallar"
    assert any("8 caracteres" in x for x in p)


def test_password_sin_numero_rechazado():
    from services.auth_service import evaluar_fortaleza_password
    ok, p = evaluar_fortaleza_password("solamenteletras")
    assert not ok, "Sin número ni caracter especial debe fallar"


def test_password_sin_letra_rechazado():
    from services.auth_service import evaluar_fortaleza_password
    ok, p = evaluar_fortaleza_password("12345678")
    assert not ok, "Solo números debe fallar"


def test_password_comun_rechazado():
    from services.auth_service import evaluar_fortaleza_password
    ok, p = evaluar_fortaleza_password("Password1")  # tiene mayús+minus+num
    # Password no está exactamente en la lista comun (está "password" que sí),
    # aquí verificamos que password1 sí se detecta
    ok2, p2 = evaluar_fortaleza_password("password1")
    assert not ok2, "'password1' está en la lista de comunes"


def test_password_valida_aceptada():
    from services.auth_service import evaluar_fortaleza_password
    ok, p = evaluar_fortaleza_password("MiClave123!")
    assert ok, f"Contraseña válida rechazada: {p}"


# ══════════════════════════════════════════════════════════════════════════════
# TESTS DE HASHING (ARGON2)
# ══════════════════════════════════════════════════════════════════════════════

def test_hash_password_genera_argon2():
    from services.auth_service import AuthService, es_hash_argon2
    auth = AuthService()
    h = auth.hash_password("MiClave123!")
    assert es_hash_argon2(h), f"Hash generado no es Argon2: {h[:20]}..."
    assert h.startswith("$argon2"), "Argon2 debe empezar con $argon2"


def test_hash_password_debil_lanza_error():
    from services.auth_service import AuthService
    auth = AuthService()
    try:
        auth.hash_password("123")
        assert False, "Debería haber lanzado ValueError"
    except ValueError as e:
        assert "débil" in str(e).lower() or "debil" in str(e).lower()


def test_hash_password_es_diferente_cada_vez():
    """Argon2 usa salt aleatorio — mismo password → hashes distintos."""
    from services.auth_service import AuthService
    auth = AuthService()
    h1 = auth.hash_password("MiClave123!")
    h2 = auth.hash_password("MiClave123!")
    assert h1 != h2, "Argon2 debe usar salt aleatorio"


# ══════════════════════════════════════════════════════════════════════════════
# TESTS DE VERIFICACIÓN ARGON2
# ══════════════════════════════════════════════════════════════════════════════

def test_verify_argon2_correcta():
    from services.auth_service import AuthService
    auth = AuthService()
    h = auth.hash_password("MiClave123!")
    ok, needs_rehash = auth.verify_password("MiClave123!", h)
    assert ok, "Contraseña correcta debe verificar"
    assert not needs_rehash, "Hash recién creado no necesita re-hash"


def test_verify_argon2_incorrecta():
    from services.auth_service import AuthService
    auth = AuthService()
    h = auth.hash_password("MiClave123!")
    ok, _ = auth.verify_password("OtraClave456!", h)
    assert not ok, "Contraseña incorrecta debe fallar"


def test_verify_argon2_password_vacio():
    from services.auth_service import AuthService
    auth = AuthService()
    h = auth.hash_password("MiClave123!")
    ok, _ = auth.verify_password("", h)
    assert not ok


# ══════════════════════════════════════════════════════════════════════════════
# TESTS DE RETROCOMPATIBILIDAD SHA-256
# ══════════════════════════════════════════════════════════════════════════════

def test_verify_sha256_legacy_correcta():
    """
    Prueba crítica: un usuario con hash SHA-256 legacy puede entrar,
    y el sistema indica que necesita re-hash.
    """
    import hashlib
    from services.auth_service import AuthService

    # Simulamos un hash SHA-256 legacy (como los que había antes)
    password_original = "ContraseñaVieja123"
    hash_legacy = hashlib.sha256(password_original.encode()).hexdigest()

    auth = AuthService()
    ok, needs_rehash = auth.verify_password(password_original, hash_legacy)

    assert ok, "Usuario con hash SHA-256 debe poder entrar"
    assert needs_rehash, "Hash SHA-256 legacy debe indicar re-hash"


def test_verify_sha256_legacy_incorrecta():
    """SHA-256 legacy con contraseña mala debe fallar."""
    import hashlib
    from services.auth_service import AuthService

    hash_legacy = hashlib.sha256(b"correcta").hexdigest()
    auth = AuthService()
    ok, _ = auth.verify_password("incorrecta", hash_legacy)
    assert not ok


def test_rehash_ciclo_completo():
    """
    Simula el ciclo completo:
    1. Usuario tiene hash SHA-256
    2. Ingresa con contraseña correcta → verifica OK + needs_rehash=True
    3. Sistema genera nuevo hash Argon2
    4. Usuario entra de nuevo → verifica OK + needs_rehash=False
    """
    import hashlib
    from services.auth_service import AuthService

    password = "MiClaveSegura99!"

    # 1. Hash legacy SHA-256 (así estaba antes en BD)
    hash_legacy = hashlib.sha256(password.encode()).hexdigest()

    auth = AuthService()

    # 2. Primer login: verifica con SHA-256, indica que necesita rehash
    ok, needs_rehash = auth.verify_password(password, hash_legacy)
    assert ok, "Login con SHA-256 legacy debe pasar"
    assert needs_rehash, "Debe indicar que necesita rehash"

    # 3. Sistema genera nuevo hash Argon2
    hash_argon2 = auth.hash_password(password)
    assert hash_argon2.startswith("$argon2"), "Nuevo hash debe ser Argon2"

    # 4. Login futuro con el nuevo hash
    ok2, needs_rehash2 = auth.verify_password(password, hash_argon2)
    assert ok2, "Login con Argon2 debe pasar"
    assert not needs_rehash2, "Argon2 fresh no necesita rehash"


# ══════════════════════════════════════════════════════════════════════════════
# TESTS DE CASOS BORDE
# ══════════════════════════════════════════════════════════════════════════════

def test_verify_hash_invalido():
    """Un hash que no es Argon2 ni SHA-256 debe fallar sin explotar."""
    from services.auth_service import AuthService
    auth = AuthService()
    ok, needs_rehash = auth.verify_password("cualquier", "hash_invalido")
    assert not ok
    assert not needs_rehash


def test_verify_hash_vacio():
    from services.auth_service import AuthService
    auth = AuthService()
    ok, _ = auth.verify_password("pw", "")
    assert not ok


def test_verify_hash_none():
    from services.auth_service import AuthService
    auth = AuthService()
    ok, _ = auth.verify_password("pw", None)
    assert not ok


def test_deteccion_hash_argon2():
    from services.auth_service import es_hash_argon2
    assert es_hash_argon2("$argon2id$v=19$m=65536,t=3,p=4$abc$def")
    assert es_hash_argon2("$argon2i$v=19$m=65536,t=3,p=4$abc$def")
    assert not es_hash_argon2("abc123")
    assert not es_hash_argon2("")
    assert not es_hash_argon2(None)


def test_deteccion_hash_sha256():
    from services.auth_service import es_hash_sha256
    import hashlib
    h = hashlib.sha256(b"test").hexdigest()
    assert es_hash_sha256(h), "SHA-256 real debe detectarse"
    assert not es_hash_sha256("abc")
    assert not es_hash_sha256("$argon2id$xyz")
    # Longitud correcta pero contiene mayúsculas
    assert not es_hash_sha256("A" * 64)


def test_constant_time_equals():
    """La comparación en tiempo constante debe funcionar correctamente."""
    from services.auth_service import _constant_time_equals
    assert _constant_time_equals("abc", "abc")
    assert not _constant_time_equals("abc", "abd")
    assert not _constant_time_equals("abc", "abcd")  # diferentes longitudes
    assert _constant_time_equals("", "")


# ══════════════════════════════════════════════════════════════════════════════
# EJECUCIÓN
# ══════════════════════════════════════════════════════════════════════════════

def _run_all():
    tests = [(name, fn) for name, fn in globals().items()
              if name.startswith("test_") and callable(fn)]
    pasados = 0
    fallados = []
    for name, fn in tests:
        try:
            fn()
            pasados += 1
            print(f"  ✅ {name}")
        except AssertionError as e:
            fallados.append((name, str(e)))
            print(f"  ❌ {name}\n     {e}")
        except Exception as e:
            fallados.append((name, f"Excepción: {e}"))
            print(f"  💥 {name}\n     Excepción: {type(e).__name__}: {e}")

    print()
    print(f"{'=' * 60}")
    print(f"RESULTADO: {pasados}/{len(tests)} tests pasaron")
    if fallados:
        print("❌ FALLARON:")
        for name, msg in fallados:
            print(f"  • {name}: {msg}")
    else:
        print("🎉 Todos los tests de auth_service pasaron")
    print(f"{'=' * 60}")
    return len(fallados) == 0


if __name__ == "__main__":
    print("Ejecutando tests de auth_service...\n")
    exito = _run_all()
    sys.exit(0 if exito else 1)
