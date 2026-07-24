"""
Configuración central de Gestor RH IA.
Carga variables de entorno, las valida y las expone como constantes.

Uso:
    from config.settings import settings

    if settings.is_production:
        ...

    smtp = settings.smtp  # dict con configuración SMTP

Reglas:
- En development: las variables faltantes se rellenan con defaults inseguros y
  se muestra un warning en logs.
- En production: si falta cualquier variable crítica, la app NO arranca.
"""

import os
import sys
from typing import Optional


# ── Carga de .env ────────────────────────────────────────────────────────────
# python-dotenv es opcional en producción (Render ya inyecta variables),
# pero muy útil en desarrollo local.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv no instalado — solo importa en dev, no rompe en prod
    pass


class ConfigError(Exception):
    """Se lanza cuando falta configuración crítica en producción."""
    pass


class Settings:
    """
    Configuración centralizada de la aplicación.
    Se instancia una sola vez al arrancar (patrón singleton implícito por import).
    """

    def __init__(self):
        # ── Entorno ──────────────────────────────────────────────────────────
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        if self.environment not in ("development", "production", "test"):
            raise ConfigError(
                f"ENVIRONMENT inválido: '{self.environment}'. "
                f"Valores permitidos: development, production, test"
            )

        # ── URL pública ──────────────────────────────────────────────────────
        default_url = "http://localhost:8501" if self.is_development else ""
        self.app_url = os.getenv("APP_URL", default_url).rstrip("/")

        # ── Supabase ─────────────────────────────────────────────────────────
        self.supabase_url = os.getenv("SUPABASE_URL", "").strip()
        self.supabase_key = os.getenv("SUPABASE_KEY", "").strip()

        # ── SMTP ─────────────────────────────────────────────────────────────
        self.smtp = {
            "host":     os.getenv("SMTP_HOST", "smtp-relay.brevo.com"),
            "port":     int(os.getenv("SMTP_PORT", "587")),
            "user":     os.getenv("SMTP_USER", ""),
            "password": os.getenv("SMTP_PASS", ""),
            "from":     os.getenv("SMTP_FROM", "Gestor RH IA <noreply@gestorrh.co>"),
        }

        # ── Argon2 ───────────────────────────────────────────────────────────
        self.argon2 = {
            "time_cost":   int(os.getenv("ARGON2_TIME_COST", "3")),
            "memory_cost": int(os.getenv("ARGON2_MEMORY_COST", "65536")),
            "parallelism": int(os.getenv("ARGON2_PARALLELISM", "4")),
        }

        # ── Rate limiting ────────────────────────────────────────────────────
        self.login = {
            "max_intentos":     int(os.getenv("LOGIN_MAX_INTENTOS", "5")),
            "ventana_minutos":  int(os.getenv("LOGIN_VENTANA_MINUTOS", "15")),
            "bloqueo_minutos":  int(os.getenv("LOGIN_BLOQUEO_MINUTOS", "15")),
        }

        # ── Comercial ────────────────────────────────────────────────────────
        self.whatsapp_numero = os.getenv("WHATSAPP_NUMERO", "573001234567")

        # ── Validación final ─────────────────────────────────────────────────
        self._validar()

    # ── Propiedades convenientes ─────────────────────────────────────────────
    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_test(self) -> bool:
        return self.environment == "test"

    @property
    def supabase_configurado(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    @property
    def smtp_configurado(self) -> bool:
        return bool(self.smtp["user"] and self.smtp["password"])

    # ── Validación por entorno ───────────────────────────────────────────────
    def _validar(self):
        """
        Valida que la configuración sea coherente con el entorno.
        En producción, faltas críticas hacen que la app NO arranque.
        """
        problemas_criticos = []
        problemas_warn = []

        # En producción, Supabase es OBLIGATORIO
        if self.is_production:
            if not self.supabase_url:
                problemas_criticos.append("SUPABASE_URL no está configurado")
            if not self.supabase_key:
                problemas_criticos.append("SUPABASE_KEY no está configurado")
            if not self.app_url:
                problemas_criticos.append("APP_URL no está configurado")
            if not self.smtp_configurado:
                problemas_warn.append(
                    "SMTP no configurado — no se podrán enviar correos "
                    "(activación de cuentas, envío de documentos)"
                )

        # En desarrollo, solo mostramos warnings
        else:
            if not self.supabase_configurado:
                problemas_warn.append(
                    "Supabase no configurado — usando fallback JSON local"
                )
            if not self.smtp_configurado:
                problemas_warn.append("SMTP no configurado")

        if problemas_criticos:
            mensaje = (
                "\n\n"
                "╔══════════════════════════════════════════════════════════════╗\n"
                "║  ERROR CRÍTICO — Gestor RH IA no puede arrancar             ║\n"
                "╠══════════════════════════════════════════════════════════════╣\n"
                f"║  Entorno: {self.environment.upper():<50}║\n"
                "║                                                              ║\n"
                "║  Problemas detectados:                                       ║\n"
            )
            for p in problemas_criticos:
                mensaje += f"║   • {p:<57}║\n"
            mensaje += (
                "║                                                              ║\n"
                "║  Solución:                                                   ║\n"
                "║   • Verifica que las variables estén en Render → Environment ║\n"
                "║   • O cambia ENVIRONMENT=development para desarrollo local   ║\n"
                "║   • Ver .env.example para la lista completa                  ║\n"
                "╚══════════════════════════════════════════════════════════════╝\n"
            )
            raise ConfigError(mensaje)

        # Warnings en desarrollo — no bloquean
        if problemas_warn and self.is_development:
            print("\n⚠️  Advertencias de configuración (modo desarrollo):", file=sys.stderr)
            for p in problemas_warn:
                print(f"   • {p}", file=sys.stderr)
            print(file=sys.stderr)

    def resumen(self) -> str:
        """Retorna un resumen legible (sin secretos) para debugging."""
        return (
            f"Gestor RH IA — Configuración\n"
            f"  Entorno:            {self.environment}\n"
            f"  URL:                {self.app_url}\n"
            f"  Supabase:           {'✅' if self.supabase_configurado else '❌'}\n"
            f"  SMTP:               {'✅' if self.smtp_configurado else '❌'}\n"
            f"  Argon2 memory:      {self.argon2['memory_cost']} KB\n"
            f"  Rate limit:         {self.login['max_intentos']} intentos / "
            f"{self.login['ventana_minutos']} min\n"
        )


# ── Instancia única global ───────────────────────────────────────────────────
# Se inicializa al importar el módulo. Si algo crítico falla en producción,
# la app no arranca — esto es intencional.
try:
    settings = Settings()
except ConfigError as e:
    # En producción, error crítico. En desarrollo, se decide en _validar().
    # Solo hacemos sys.exit si NO estamos en modo test/pytest
    _en_test = (
        os.getenv("PYTEST_CURRENT_TEST") is not None
        or "pytest" in sys.modules
        or "unittest" in sys.modules
        or any("test" in arg for arg in sys.argv)
    )
    if not _en_test:
        print(str(e), file=sys.stderr)
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            sys.exit(1)
    raise
