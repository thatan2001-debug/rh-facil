"""
Control de planes y límites de uso — RH Fácil.

Plan Gratuito: 5 documentos O 3 días desde el primer uso, lo que llegue primero.
Los datos se guardan en un archivo local JSON (por sesión de servidor).
Para producción real con múltiples usuarios, migrar a SQLite o Supabase.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

PLANES = {
    "gratuito": {
        "nombre": "Gratuito",
        "precio": 0,
        "max_documentos": 5,
        "dias_prueba": 3,
        "descripcion": "Ideal para probar la herramienta",
        "features": [
            "Hasta 5 documentos en total",
            "3 días de acceso",
            "Certificados laborales",
            "Cartas de vacaciones",
            "Liquidaciones básicas",
        ],
        "limite": True,
        "whatsapp": False,
    },
    "basico": {
        "nombre": "Básico",
        "precio": 29900,
        "max_documentos": 50,
        "dias_prueba": None,
        "descripcion": "Para pequeñas empresas",
        "features": [
            "Hasta 50 documentos al mes",
            "Certificados laborales",
            "Cartas de vacaciones",
            "Liquidaciones básicas",
            "Soporte por WhatsApp",
        ],
        "limite": True,
        "whatsapp": True,
    },
    "pro": {
        "nombre": "Pro",
        "precio": 69900,
        "max_documentos": 9999,
        "dias_prueba": None,
        "descripcion": "Para empresas en crecimiento",
        "features": [
            "Documentos ilimitados",
            "Todos los documentos del plan Básico",
            "Logo de empresa en documentos",
            "Plantillas personalizadas",
            "Soporte prioritario",
        ],
        "limite": False,
        "whatsapp": True,
    },
    "empresarial": {
        "nombre": "Empresarial",
        "precio": 149900,
        "max_documentos": 9999,
        "dias_prueba": None,
        "descripcion": "Para contadores y outsourcing",
        "features": [
            "Todo lo del plan Pro",
            "Múltiples empresas",
            "API de integración (próximamente)",
            "Capacitación personalizada",
            "Gerente de cuenta dedicado",
        ],
        "limite": False,
        "whatsapp": True,
    },
}

ARCHIVO_ESTADO = Path("salidas/.uso_plan.json")
WHATSAPP_NUMERO = "573001234567"  # Cambiar por número real


def _cargar_estado():
    if ARCHIVO_ESTADO.exists():
        try:
            with open(ARCHIVO_ESTADO) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _guardar_estado(estado: dict):
    ARCHIVO_ESTADO.parent.mkdir(exist_ok=True)
    with open(ARCHIVO_ESTADO, "w") as f:
        json.dump(estado, f)


def inicializar_plan():
    """Crea el estado inicial si no existe. Retorna el estado actual."""
    estado = _cargar_estado()
    if estado is None:
        estado = {
            "plan": "gratuito",
            "documentos_usados": 0,
            "primera_vez": datetime.now().isoformat(),
            "activo": True,
        }
        _guardar_estado(estado)
    return estado


def obtener_estado_plan():
    """Retorna dict con info completa del plan actual y sus límites."""
    estado = inicializar_plan()
    plan_key = estado.get("plan", "gratuito")
    plan_info = PLANES[plan_key]

    docs_usados = estado.get("documentos_usados", 0)
    primera_vez = datetime.fromisoformat(estado.get("primera_vez", datetime.now().isoformat()))
    dias_transcurridos = (datetime.now() - primera_vez).days

    # Verificar si el plan gratuito expiró
    plan_expirado = False
    razon_expiracion = ""
    if plan_key == "gratuito":
        if docs_usados >= plan_info["max_documentos"]:
            plan_expirado = True
            razon_expiracion = f"Alcanzaste el límite de {plan_info['max_documentos']} documentos gratuitos"
        elif dias_transcurridos >= plan_info["dias_prueba"]:
            plan_expirado = True
            razon_expiracion = f"Tu período de prueba de {plan_info['dias_prueba']} días ha terminado"

    docs_restantes = max(0, plan_info["max_documentos"] - docs_usados) if plan_info["limite"] else None
    dias_restantes = max(0, plan_info["dias_prueba"] - dias_transcurridos) if plan_key == "gratuito" else None

    return {
        "plan_key": plan_key,
        "plan_nombre": plan_info["nombre"],
        "plan_precio": plan_info["precio"],
        "documentos_usados": docs_usados,
        "documentos_max": plan_info["max_documentos"],
        "documentos_restantes": docs_restantes,
        "dias_restantes": dias_restantes,
        "plan_expirado": plan_expirado,
        "razon_expiracion": razon_expiracion,
        "puede_generar": not plan_expirado,
        "features": plan_info["features"],
        "limite": plan_info["limite"],
    }


def registrar_uso(cantidad_docs: int):
    """Suma documentos generados al contador."""
    estado = inicializar_plan()
    estado["documentos_usados"] = estado.get("documentos_usados", 0) + cantidad_docs
    _guardar_estado(estado)


def link_whatsapp(mensaje: str = "") -> str:
    """Genera link de WhatsApp con mensaje pre-escrito."""
    if not mensaje:
        mensaje = (
            "Hola, quiero suscribirme a RH Fácil. "
            "¿Me pueden dar información sobre los planes disponibles?"
        )
    import urllib.parse
    return f"https://wa.me/{WHATSAPP_NUMERO}?text={urllib.parse.quote(mensaje)}"
