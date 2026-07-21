"""
Tests de la configuración central.
Verifican que settings carga bien, valida entornos y bloquea producción sin
variables críticas.

Ejecutar:
    python tests/test_settings.py

O con pytest:
    pytest tests/test_settings.py -v
"""

import sys
import os
import importlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _limpiar_env():
    """Elimina todas las variables relevantes para tests aislados."""
    vars_a_limpiar = [
        "ENVIRONMENT", "APP_URL", "SUPABASE_URL", "SUPABASE_KEY",
        "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "SMTP_FROM",
        "ARGON2_TIME_COST", "LOGIN_MAX_INTENTOS", "WHATSAPP_NUMERO",
    ]
    for v in vars_a_limpiar:
        os.environ.pop(v, None)


def _recargar_settings():
    """Fuerza recarga del módulo settings después de cambiar env vars."""
    if "config.settings" in sys.modules:
        del sys.modules["config.settings"]
    from config.settings import Settings
    return Settings()


# ══════════════════════════════════════════════════════════════════════════════
# TESTS DE ENTORNO
# ══════════════════════════════════════════════════════════════════════════════

def test_development_por_defecto():
    """Sin ENVIRONMENT definido, arranca como development."""
    _limpiar_env()
    s = _recargar_settings()
    assert s.is_development, "Debe ser development por defecto"
    assert not s.is_production


def test_production_explicito():
    """Con ENVIRONMENT=production y todas las vars, arranca bien."""
    _limpiar_env()
    os.environ.update({
        "ENVIRONMENT": "production",
        "APP_URL": "https://miapp.com",
        "SUPABASE_URL": "https://x.supabase.co",
        "SUPABASE_KEY": "fake_key_123",
        "SMTP_HOST": "smtp.brevo.com",
        "SMTP_USER": "user",
        "SMTP_PASS": "pass",
        "SMTP_FROM": "test@example.com",
    })
    s = _recargar_settings()
    assert s.is_production


def test_production_sin_supabase_falla():
    """En producción sin SUPABASE_URL debe lanzar ConfigError."""
    _limpiar_env()
    os.environ.update({
        "ENVIRONMENT": "production",
        "APP_URL": "https://miapp.com",
    })
    try:
        _recargar_settings()
        assert False, "Debería haber lanzado ConfigError"
    except Exception as e:
        assert "SUPABASE_URL" in str(e), \
            f"Error debe mencionar SUPABASE_URL, dijo: {e}"


def test_production_sin_app_url_falla():
    """En producción sin APP_URL debe fallar."""
    _limpiar_env()
    os.environ.update({
        "ENVIRONMENT": "production",
        "SUPABASE_URL": "https://x.supabase.co",
        "SUPABASE_KEY": "fake",
    })
    try:
        _recargar_settings()
        assert False, "Debería haber fallado"
    except Exception as e:
        assert "APP_URL" in str(e)


def test_environment_invalido_falla():
    """Un valor de ENVIRONMENT no permitido debe fallar."""
    _limpiar_env()
    os.environ["ENVIRONMENT"] = "banana"
    try:
        _recargar_settings()
        assert False, "Debería haber fallado con ENVIRONMENT inválido"
    except Exception as e:
        assert "banana" in str(e) or "invalid" in str(e).lower()


def test_development_sin_supabase_arranca():
    """En development sin Supabase debe arrancar (solo warning)."""
    _limpiar_env()
    os.environ["ENVIRONMENT"] = "development"
    s = _recargar_settings()
    assert not s.supabase_configurado
    assert s.is_development


# ══════════════════════════════════════════════════════════════════════════════
# TESTS DE VALORES
# ══════════════════════════════════════════════════════════════════════════════

def test_supabase_configurado_detecta_ambas_vars():
    """supabase_configurado debe ser True solo si AMBAS vars están."""
    _limpiar_env()
    os.environ["SUPABASE_URL"] = "https://x.supabase.co"
    s = _recargar_settings()
    assert not s.supabase_configurado, "Con solo URL no está configurado"

    _limpiar_env()
    os.environ["SUPABASE_URL"] = "https://x.supabase.co"
    os.environ["SUPABASE_KEY"] = "abc"
    s = _recargar_settings()
    assert s.supabase_configurado


def test_argon2_valores_default():
    """Valores por defecto de Argon2 son seguros (2026)."""
    _limpiar_env()
    s = _recargar_settings()
    # Estos son mínimos seguros según OWASP
    assert s.argon2["memory_cost"] >= 19456, \
        f"memory_cost {s.argon2['memory_cost']} < 19456 KB (mínimo OWASP)"
    assert s.argon2["time_cost"] >= 2


def test_app_url_sin_slash_final():
    """APP_URL no debe tener slash al final (para concatenar rutas limpio)."""
    _limpiar_env()
    os.environ["APP_URL"] = "https://miapp.com/"
    s = _recargar_settings()
    assert s.app_url == "https://miapp.com", \
        f"Slash final no removido: {s.app_url}"


def test_smtp_puerto_es_int():
    """SMTP_PORT debe convertirse a int."""
    _limpiar_env()
    os.environ["SMTP_PORT"] = "465"
    s = _recargar_settings()
    assert isinstance(s.smtp["port"], int)
    assert s.smtp["port"] == 465


def test_login_config_completa():
    """Configuración de rate limiting está completa."""
    _limpiar_env()
    s = _recargar_settings()
    assert "max_intentos" in s.login
    assert "ventana_minutos" in s.login
    assert "bloqueo_minutos" in s.login
    assert s.login["max_intentos"] >= 3, \
        "max_intentos < 3 es demasiado estricto"


# ══════════════════════════════════════════════════════════════════════════════
# TESTS DE RESUMEN
# ══════════════════════════════════════════════════════════════════════════════

def test_resumen_no_contiene_secretos():
    """El resumen() no debe filtrar contraseñas ni claves."""
    _limpiar_env()
    os.environ.update({
        "SUPABASE_KEY": "SECRET_KEY_DO_NOT_LOG_ABCD1234",
        "SMTP_PASS": "SECRET_PASS_XYZ",
    })
    s = _recargar_settings()
    r = s.resumen()
    assert "SECRET_KEY_DO_NOT_LOG_ABCD1234" not in r, \
        "SUPABASE_KEY se filtró en resumen"
    assert "SECRET_PASS_XYZ" not in r, \
        "SMTP_PASS se filtró en resumen"


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
            print(f"  💥 {name}\n     Excepción: {e}")

    print()
    print(f"{'=' * 60}")
    print(f"RESULTADO: {pasados}/{len(tests)} tests pasaron")
    if fallados:
        print("❌ FALLARON:")
        for name, msg in fallados:
            print(f"  • {name}: {msg}")
    else:
        print("🎉 Todos los tests de settings pasaron")
    print(f"{'=' * 60}")
    return len(fallados) == 0


if __name__ == "__main__":
    print("Ejecutando tests de configuración...\n")
    exito = _run_all()
    sys.exit(0 if exito else 1)
