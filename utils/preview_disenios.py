"""
Genera imágenes PNG de previsualización de cada uno de los 5 diseños.
Usa pdftoppm (disponible en el servidor de Render y en Ubuntu).
Las imágenes se cachean en assets/previews/ para no regenerarlas cada vez.
"""

import subprocess
from pathlib import Path
from datetime import datetime
import pandas as pd

CARPETA_PREVIEWS = Path("assets/previews")

# Empleado y empresa de muestra para las previsualizaciones
EMPRESA_DEMO = {
    "nombre": "Tu Empresa SAS",
    "nit": "900.123.456-7",
    "representante": "María González",
    "correo_empresa": "rrhh@tuempresa.com",
    "logo_path": None,
}

EMPLEADO_DEMO = {
    "Nombre": "Carlos Rodríguez",
    "Documento": "1.020.304.050",
    "Cargo": "Auxiliar Administrativo",
    "Salario": 2200000,
    "Fecha ingreso": "01/03/2023",
    "Tipo contrato": "Indefinido",
    "Ingreso promedio variable": 0,
    "Fecha retiro": "25/06/2026",
    "Cuenta bancaria": "Bancolombia Ahorros #456789",
}


def _pdf_a_png(ruta_pdf: str, ruta_png_base: str, dpi: int = 130) -> str | None:
    """Convierte la primera página de un PDF a PNG usando pdftoppm."""
    try:
        resultado = subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), "-l", "1",
             ruta_pdf, ruta_png_base],
            capture_output=True, timeout=30,
        )
        if resultado.returncode == 0:
            # pdftoppm genera archivo con sufijo -1.png
            png = Path(f"{ruta_png_base}-1.png")
            if png.exists():
                return str(png)
    except Exception as e:
        print(f"Error convirtiendo PDF a PNG: {e}")
    return None


def generar_previews(forzar: bool = False) -> dict[int, str | None]:
    """
    Genera o recupera las imágenes de previsualización de los 5 diseños.
    Retorna {1: 'ruta.png', 2: 'ruta.png', ...}
    Si forzar=False, usa caché si ya existen.
    """
    from utils.plantillas_disenio import generar_certificado, generar_liquidacion
    from utils.calcular_liquidacion import calcular_liquidacion_fila

    CARPETA_PREVIEWS.mkdir(parents=True, exist_ok=True)
    resultado_cert = {}
    resultado_liq  = {}

    # Pre-calcular liquidación demo
    try:
        fila = pd.Series({
            "Nombre": EMPLEADO_DEMO["Nombre"],
            "Documento": EMPLEADO_DEMO["Documento"],
            "Cargo": EMPLEADO_DEMO["Cargo"],
            "Salario": EMPLEADO_DEMO["Salario"],
            "Fecha ingreso": EMPLEADO_DEMO["Fecha ingreso"],
            "Fecha retiro": EMPLEADO_DEMO["Fecha retiro"],
            "Tipo contrato": EMPLEADO_DEMO["Tipo contrato"],
            "Cuenta bancaria": EMPLEADO_DEMO["Cuenta bancaria"],
        })
        liq_demo = calcular_liquidacion_fila(fila, motivo_retiro="renuncia")
    except Exception:
        liq_demo = None

    for d in range(1, 6):
        # ── Certificado ──────────────────────────────────────────────────────
        png_cert = CARPETA_PREVIEWS / f"cert_d{d}-1.png"  # pdftoppm agrega -1
        if not forzar and png_cert.exists():
            resultado_cert[d] = str(png_cert)
        else:
            pdf_cert = str(CARPETA_PREVIEWS / f"cert_d{d}.pdf")
            try:
                generar_certificado(EMPLEADO_DEMO, EMPRESA_DEMO, pdf_cert, d)
                png = _pdf_a_png(pdf_cert, str(CARPETA_PREVIEWS / f"cert_d{d}"))
                resultado_cert[d] = png
                Path(pdf_cert).unlink(missing_ok=True)
            except Exception as e:
                print(f"Error preview cert diseño {d}: {e}")
                resultado_cert[d] = None

        # ── Liquidación ───────────────────────────────────────────────────────
        png_liq = CARPETA_PREVIEWS / f"liq_d{d}-1.png"  # pdftoppm agrega -1
        if not forzar and png_liq.exists():
            resultado_liq[d] = str(png_liq)
        elif liq_demo:
            pdf_liq = str(CARPETA_PREVIEWS / f"liq_d{d}.pdf")
            try:
                generar_liquidacion(liq_demo, EMPRESA_DEMO, pdf_liq, d)
                png = _pdf_a_png(pdf_liq, str(CARPETA_PREVIEWS / f"liq_d{d}"))
                resultado_liq[d] = png
                Path(pdf_liq).unlink(missing_ok=True)
            except Exception as e:
                print(f"Error preview liq diseño {d}: {e}")
                resultado_liq[d] = None
        else:
            resultado_liq[d] = None

    return resultado_cert, resultado_liq


def limpiar_previews():
    """Elimina todas las imágenes de caché para forzar regeneración."""
    for f in CARPETA_PREVIEWS.glob("*.png"):
        f.unlink()
    for f in CARPETA_PREVIEWS.glob("*.pdf"):
        f.unlink()
