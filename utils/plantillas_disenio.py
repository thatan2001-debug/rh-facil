"""
5 diseños profesionales de plantillas PDF para RH Fácil.
Cada diseño aplica a: certificados laborales, cartas de vacaciones y liquidaciones.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, KeepTogether,
)
from pathlib import Path
from datetime import datetime
from utils.numero_letras import numero_a_letras
from utils.calcular_liquidacion import AUXILIO_TRANSPORTE_2026

# ── Paletas de color por diseño ──────────────────────────────────────────────
PALETAS = {
    1: {  # Clásico Corporativo — Azul profundo + blanco
        "primario": colors.HexColor("#1B3F6E"),
        "secundario": colors.HexColor("#2D6BE4"),
        "acento": colors.HexColor("#E8F0FD"),
        "texto": colors.HexColor("#111827"),
        "gris": colors.HexColor("#6B7280"),
        "borde": colors.HexColor("#DBEAFE"),
        "nombre": "Clásico Corporativo",
    },
    2: {  # Ejecutivo Oscuro — Gris antracita + dorado
        "primario": colors.HexColor("#1F2937"),
        "secundario": colors.HexColor("#B45309"),
        "acento": colors.HexColor("#FEF3C7"),
        "texto": colors.HexColor("#111827"),
        "gris": colors.HexColor("#6B7280"),
        "borde": colors.HexColor("#E5E7EB"),
        "nombre": "Ejecutivo Oscuro",
    },
    3: {  # Verde Institucional — Verde oscuro + crema
        "primario": colors.HexColor("#064E3B"),
        "secundario": colors.HexColor("#059669"),
        "acento": colors.HexColor("#ECFDF5"),
        "texto": colors.HexColor("#111827"),
        "gris": colors.HexColor("#6B7280"),
        "borde": colors.HexColor("#D1FAE5"),
        "nombre": "Verde Institucional",
    },
    4: {  # Moderno Minimalista — Negro + rojo coral
        "primario": colors.HexColor("#111827"),
        "secundario": colors.HexColor("#DC2626"),
        "acento": colors.HexColor("#FEF2F2"),
        "texto": colors.HexColor("#111827"),
        "gris": colors.HexColor("#6B7280"),
        "borde": colors.HexColor("#FEE2E2"),
        "nombre": "Moderno Minimalista",
    },
    5: {  # Profesional Violeta — Púrpura + plata
        "primario": colors.HexColor("#4C1D95"),
        "secundario": colors.HexColor("#7C3AED"),
        "acento": colors.HexColor("#F5F3FF"),
        "texto": colors.HexColor("#111827"),
        "gris": colors.HexColor("#6B7280"),
        "borde": colors.HexColor("#EDE9FE"),
        "nombre": "Profesional Violeta",
    },
}


def _fmt(valor):
    try:
        return f"$ {float(valor):,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return str(valor)


def _causa_retiro(motivo: str) -> str:
    mapa = {
        "renuncia": "Retiro Voluntario",
        "despido_sin_justa_causa": "Despido Sin Justa Causa",
        "mutuo_acuerdo": "Mutuo Acuerdo",
        "vencimiento_contrato": "Vencimiento de Contrato",
    }
    return mapa.get(str(motivo).lower(), motivo.replace("_", " ").title())


def _estilos_para(paleta: dict) -> dict:
    base = getSampleStyleSheet()
    return {
        "empresa": ParagraphStyle("empresa", parent=base["Normal"],
            fontSize=13, fontName="Helvetica-Bold", textColor=paleta["primario"], spaceAfter=1),
        "nit": ParagraphStyle("nit", parent=base["Normal"],
            fontSize=9, textColor=paleta["gris"], spaceAfter=8),
        "titulo": ParagraphStyle("titulo", parent=base["Normal"],
            fontSize=13, fontName="Helvetica-Bold", alignment=TA_CENTER,
            textColor=paleta["primario"], spaceBefore=6, spaceAfter=12),
        "cuerpo": ParagraphStyle("cuerpo", parent=base["Normal"],
            fontSize=10.5, leading=16, alignment=TA_JUSTIFY, spaceAfter=10,
            textColor=paleta["texto"]),
        "firma_nombre": ParagraphStyle("firma_nombre", parent=base["Normal"],
            fontSize=10.5, fontName="Helvetica-Bold", textColor=paleta["texto"]),
        "firma_cargo": ParagraphStyle("firma_cargo", parent=base["Normal"],
            fontSize=9.5, textColor=paleta["gris"]),
        "nota": ParagraphStyle("nota", parent=base["Normal"],
            fontSize=8, textColor=paleta["gris"], alignment=TA_JUSTIFY, spaceBefore=12),
        "paz_salvo": ParagraphStyle("paz_salvo", parent=base["Normal"],
            fontSize=9.5, leading=14, alignment=TA_JUSTIFY, spaceAfter=8),
        "seccion": ParagraphStyle("seccion", parent=base["Normal"],
            fontSize=9, fontName="Helvetica-Bold", textColor=paleta["primario"],
            spaceBefore=6, spaceAfter=3),
    }


def _pie(canvas, doc, paleta: dict):
    canvas.saveState()
    canvas.setStrokeColor(paleta["borde"])
    canvas.line(2*cm, 1.6*cm, letter[0]-2*cm, 1.6*cm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(paleta["gris"])
    canvas.drawString(2*cm, 1.2*cm,
        f"Generado el {datetime.today().strftime('%d/%m/%Y %H:%M')} — RH Fácil")
    canvas.drawRightString(letter[0]-2*cm, 1.2*cm,
        "Estimación de referencia. Validar con contador o abogado laboral.")
    canvas.restoreState()


def _encabezado_disenio(elementos, datos_empresa, estilos, paleta, disenio):
    """Encabezado diferente según el diseño seleccionado."""
    nombre = datos_empresa.get("nombre", "")
    nit    = datos_empresa.get("nit", "")
    logo   = datos_empresa.get("logo_path")

    if disenio == 1:
        # Barra superior azul con texto blanco
        fila = [[
            Paragraph(f'<font color="white"><b>{nombre}</b></font>',
                ParagraphStyle("h1", fontSize=13, fontName="Helvetica-Bold",
                    textColor=colors.white)),
            Paragraph(f'<font color="white">Nit #{nit}</font>',
                ParagraphStyle("h2", fontSize=10, textColor=colors.white,
                    alignment=TA_RIGHT)),
        ]]
        t = Table(fila, colWidths=[11*cm, 6.5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), paleta["primario"]),
            ("TOPPADDING", (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
            ("LEFTPADDING", (0,0), (-1,-1), 12),
            ("RIGHTPADDING", (0,0), (-1,-1), 12),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        elementos.append(t)
        elementos.append(Spacer(1, 10))

    elif disenio == 2:
        # Logo + texto + línea dorada
        if logo and Path(logo).exists():
            try:
                img = Image(logo, width=2.5*cm, height=2.5*cm)
                img.hAlign = "LEFT"
                elementos.append(img)
                elementos.append(Spacer(1, 4))
            except Exception:
                pass
        elementos.append(Paragraph(nombre, estilos["empresa"]))
        elementos.append(Paragraph(f"Nit: {nit}", estilos["nit"]))
        elementos.append(HRFlowable(width="100%", thickness=2,
            color=paleta["secundario"], spaceAfter=10))

    elif disenio == 3:
        # Borde izquierdo verde + empresa a la derecha del logo
        fila = [[
            Paragraph(f"<b>{nombre}</b>", estilos["empresa"]),
            Paragraph(f"Nit #{nit}", ParagraphStyle("nr", fontSize=10,
                textColor=paleta["gris"], alignment=TA_RIGHT)),
        ]]
        t = Table(fila, colWidths=[10*cm, 7.5*cm])
        t.setStyle(TableStyle([
            ("LEFTPADDING", (0,0), (-1,-1), 8),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LINEBEFORE", (0,0), (0,-1), 4, paleta["secundario"]),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        elementos.append(t)
        elementos.append(HRFlowable(width="100%", thickness=0.5,
            color=paleta["borde"], spaceAfter=10))

    elif disenio == 4:
        # Minimalista: solo texto sin adornos, línea roja delgada
        elementos.append(Paragraph(nombre.upper(), ParagraphStyle("mn",
            fontSize=14, fontName="Helvetica-Bold",
            textColor=paleta["primario"], spaceAfter=2)))
        elementos.append(Paragraph(f"NIT {nit}", ParagraphStyle("mn2",
            fontSize=9, textColor=paleta["secundario"], spaceAfter=4)))
        elementos.append(HRFlowable(width="100%", thickness=1.5,
            color=paleta["secundario"], spaceAfter=10))

    elif disenio == 5:
        # Violeta: caja degradada con logo
        fila = [[
            Paragraph(f'<font color="white"><b>{nombre}</b><br/>'
                      f'<font size="9">Nit #{nit}</font></font>',
                ParagraphStyle("h5", fontSize=12, fontName="Helvetica-Bold",
                    textColor=colors.white, leading=18)),
            Paragraph('', ParagraphStyle("e")),
        ]]
        t = Table(fila, colWidths=[14*cm, 3.5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), paleta["primario"]),
            ("TOPPADDING", (0,0), (-1,-1), 12),
            ("BOTTOMPADDING", (0,0), (-1,-1), 12),
            ("LEFTPADDING", (0,0), (-1,-1), 14),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ROUNDEDCORNERS", [6]),
        ]))
        elementos.append(t)
        elementos.append(Spacer(1, 10))


# ══════════════════════════════════════════════════════════════════════════════
# CERTIFICADO LABORAL
# ══════════════════════════════════════════════════════════════════════════════
def generar_certificado(empleado: dict, datos_empresa: dict,
                         ruta_salida: str, disenio: int = 1):
    paleta  = PALETAS.get(disenio, PALETAS[1])
    estilos = _estilos_para(paleta)
    doc = SimpleDocTemplate(ruta_salida, pagesize=letter,
        topMargin=1.8*cm, bottomMargin=2.2*cm,
        leftMargin=2.2*cm, rightMargin=2.2*cm)
    el = []
    _encabezado_disenio(el, datos_empresa, estilos, paleta, disenio)
    el.append(Paragraph("CERTIFICACIÓN LABORAL", estilos["titulo"]))

    fi = empleado.get("Fecha ingreso", "")
    if hasattr(fi, "strftime"): fi = fi.strftime("%d/%m/%Y")

    salario     = float(empleado.get("Salario", 0) or 0)
    salario_fmt = _fmt(salario)
    tipo        = empleado.get("Tipo contrato", "")
    contrato_t  = f", bajo contrato {tipo.lower()}," if tipo else ","

    # Ingresos variables
    ing_variable = empleado.get("Ingreso promedio variable", 0)
    ing_variable = float(ing_variable) if ing_variable else 0
    texto_variable = ""
    if ing_variable > 0:
        texto_variable = (
            f" Adicionalmente, recibe ingresos variables con un promedio mensual de "
            f"<b>{_fmt(ing_variable)}</b>."
        )

    cuerpo = (
        f"La empresa <b>{datos_empresa.get('nombre','')}</b>, identificada con NIT "
        f"<b>{datos_empresa.get('nit','')}</b>, certifica que "
        f"<b>{empleado.get('Nombre','')}</b>, identificado(a) con cédula No. "
        f"<b>{empleado.get('Documento','')}</b>, labora en la compañía desde el "
        f"<b>{fi}</b>{contrato_t} desempeñando el cargo de "
        f"<b>{empleado.get('Cargo','')}</b>, con un salario mensual de "
        f"<b>{salario_fmt}</b>.{texto_variable}"
    )
    el.append(Paragraph(cuerpo, estilos["cuerpo"]))
    el.append(Paragraph(
        "Se expide a solicitud del interesado(a) para los fines que estime pertinentes.",
        estilos["cuerpo"]))
    el.append(Spacer(1, 40))
    el.append(Paragraph("Cordialmente,", estilos["cuerpo"]))
    el.append(Spacer(1, 28))
    el.append(HRFlowable(width=7*cm, thickness=0.7, color=paleta["primario"], spaceAfter=4))
    el.append(Paragraph(datos_empresa.get("representante",""), estilos["firma_nombre"]))
    el.append(Paragraph(f"Representante Legal — {datos_empresa.get('nombre','')}", estilos["firma_cargo"]))
    el.append(Paragraph(
        "Documento generado automáticamente. Verifique los datos antes del uso oficial.",
        estilos["nota"]))
    doc.build(el, onFirstPage=lambda c,d: _pie(c,d,paleta),
                  onLaterPages=lambda c,d: _pie(c,d,paleta))


# ══════════════════════════════════════════════════════════════════════════════
# CARTA DE VACACIONES
# ══════════════════════════════════════════════════════════════════════════════
def generar_vacaciones(empleado: dict, datos_empresa: dict, ruta_salida: str,
                        fecha_inicio: str, fecha_fin: str, disenio: int = 1):
    paleta  = PALETAS.get(disenio, PALETAS[1])
    estilos = _estilos_para(paleta)
    doc = SimpleDocTemplate(ruta_salida, pagesize=letter,
        topMargin=1.8*cm, bottomMargin=2.2*cm,
        leftMargin=2.2*cm, rightMargin=2.2*cm)
    el = []
    _encabezado_disenio(el, datos_empresa, estilos, paleta, disenio)
    el.append(Paragraph("CARTA DE VACACIONES", estilos["titulo"]))
    el.append(Paragraph(f"Señor(a) <b>{empleado.get('Nombre','')}</b>:", estilos["cuerpo"]))
    el.append(Paragraph(
        f"Por medio de la presente se le informa que disfrutará su período de vacaciones "
        f"desde el <b>{fecha_inicio}</b> hasta el <b>{fecha_fin}</b>, de acuerdo con lo "
        f"establecido en el Art. 186 del Código Sustantivo del Trabajo.", estilos["cuerpo"]))
    el.append(Paragraph(
        "Le solicitamos entregar sus responsabilidades antes de iniciar el período de descanso.",
        estilos["cuerpo"]))
    el.append(Spacer(1, 40))
    el.append(Paragraph("Cordialmente,", estilos["cuerpo"]))
    el.append(Spacer(1, 28))
    el.append(HRFlowable(width=7*cm, thickness=0.7, color=paleta["primario"], spaceAfter=4))
    el.append(Paragraph(datos_empresa.get("representante",""), estilos["firma_nombre"]))
    el.append(Paragraph(f"Representante Legal — {datos_empresa.get('nombre','')}", estilos["firma_cargo"]))
    doc.build(el, onFirstPage=lambda c,d: _pie(c,d,paleta),
                  onLaterPages=lambda c,d: _pie(c,d,paleta))


# ══════════════════════════════════════════════════════════════════════════════
# LIQUIDACIÓN
# ══════════════════════════════════════════════════════════════════════════════
def generar_liquidacion(resultado: dict, datos_empresa: dict,
                         ruta_salida: str, disenio: int = 1):
    paleta  = PALETAS.get(disenio, PALETAS[1])
    estilos = _estilos_para(paleta)
    doc = SimpleDocTemplate(ruta_salida, pagesize=letter,
        topMargin=1.8*cm, bottomMargin=2.2*cm,
        leftMargin=2.2*cm, rightMargin=2.2*cm)
    el = []
    _encabezado_disenio(el, datos_empresa, estilos, paleta, disenio)
    el.append(Paragraph("LIQUIDACION DE PRESTACIONES SOCIALES", estilos["titulo"]))

    salario       = float(resultado.get("Salario base", 0))
    auxilio_si    = resultado.get("Auxilio transporte incluido", "No") == "Sí"
    auxilio_val   = AUXILIO_TRANSPORTE_2026 if auxilio_si else 0
    dias_total    = resultado.get("Dias totales (base 360)", 0)
    dias_semi     = resultado.get("Dias semestre actual (prima)", 0)
    cesantias     = resultado.get("Cesantias (Art. 249 CST)", 0)
    intereses     = resultado.get("Intereses cesantias 12% (Ley 52/75)", 0)
    vacaciones    = resultado.get("Vacaciones (Art. 186 CST)", 0)
    prima         = resultado.get("Prima semestral (Art. 306 CST)", 0)
    sal_pend      = resultado.get("Salario pendiente (estimado)", 0)
    indem         = resultado.get("Indemnizacion (Art. 64 CST)", 0)
    total_liq     = resultado.get("TOTAL LIQUIDACION ESTIMADA", 0)
    eps_val       = round(salario * 0.04, 2)
    pension_val   = round(salario * 0.04, 2)
    total_desc    = round(eps_val + pension_val, 2)
    total_neto    = round(total_liq - total_desc, 2)

    # Datos empleado
    datos_emp = [
        ["Apellidos y Nombre", resultado.get("Nombre","")],
        ["Cédula No.", resultado.get("Documento","")],
        ["Cuenta Bancaria", resultado.get("Cuenta bancaria","")],
        ["Causa Liquidación", _causa_retiro(resultado.get("Motivo retiro","renuncia"))],
        ["Fecha de Retiro", resultado.get("Fecha corte","")],
        ["Fecha de Ingreso", resultado.get("Fecha ingreso","")],
        ["Total días a liquidar", str(dias_total)],
    ]
    t_emp = Table(datos_emp, colWidths=[5*cm, 11.5*cm])
    t_emp.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("GRID", (0,0), (-1,-1), 0.5, paleta["borde"]),
        ("BACKGROUND", (0,0), (0,-1), paleta["acento"]),
        ("TEXTCOLOR", (0,0), (0,-1), paleta["primario"]),
    ]))
    el.append(t_emp)
    el.append(Spacer(1, 8))

    # Sueldo
    t_sueldo = Table([
        ["SUELDO MENSUAL", "", _fmt(salario)],
        ["Auxilio de transporte", "", _fmt(auxilio_val) if auxilio_si else "No aplica"],
        ["Base prestacional", "", _fmt(salario + auxilio_val) if auxilio_si else _fmt(salario)],
    ], colWidths=[10*cm, 1*cm, 5.5*cm])
    t_sueldo.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,0), "Helvetica-Bold"),
        ("FONTNAME", (0,2), (-1,2), "Helvetica-Bold"),
        ("BACKGROUND", (0,2), (-1,2), paleta["acento"]),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (2,0), (2,-1), "RIGHT"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("GRID", (0,0), (-1,-1), 0.5, paleta["borde"]),
    ]))
    el.append(t_sueldo)
    el.append(Spacer(1, 8))

    # Prestaciones
    filas = [["Concepto", "Días", "Valor"],
        [f"Cesantías (8.33%)", str(dias_total), _fmt(cesantias)],
        ["Intereses Cesantías (12% anual)", str(dias_total), _fmt(intereses)],
        ["Vacaciones (4.17%)", str(dias_total), _fmt(vacaciones)],
        [f"Prima de Servicios (8.33% — {dias_semi} días semestre)", str(dias_semi), _fmt(prima)],
        ["Salario pendiente del período", "–", _fmt(sal_pend)],
    ]
    if indem > 0:
        filas.append(["Indemnización (Art. 64 CST)", "–", _fmt(indem)])
    filas.append(["TOTAL LIQUIDACIÓN", "", _fmt(total_liq)])

    t_prest = Table(filas, colWidths=[10*cm, 2*cm, 4.5*cm])
    t_prest.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), paleta["primario"]),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("BACKGROUND", (0,-1), (-1,-1), paleta["acento"]),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0,-1), (-1,-1), paleta["primario"]),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (1,0), (2,-1), "RIGHT"),
        ("GRID", (0,0), (-1,-1), 0.5, paleta["borde"]),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
    ]))
    el.append(t_prest)
    el.append(Spacer(1, 8))

    # Descuentos
    t_desc = Table([
        ["Menos:", "", ""],
        ["EPS (4%)", "4%", _fmt(eps_val)],
        ["Pensión (4%)", "4%", _fmt(pension_val)],
        ["TOTAL DESCUENTOS SEGURIDAD SOCIAL", "", _fmt(total_desc)],
        ["LIQUIDACIÓN NETA A PAGAR", "", _fmt(total_neto)],
    ], colWidths=[10*cm, 2*cm, 4.5*cm])
    t_desc.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,0), "Helvetica-Bold"),
        ("FONTNAME", (0,3), (-1,4), "Helvetica-Bold"),
        ("BACKGROUND", (0,4), (-1,4), paleta["secundario"]),
        ("TEXTCOLOR", (0,4), (-1,4), colors.white),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (1,0), (2,-1), "RIGHT"),
        ("GRID", (0,0), (-1,-1), 0.5, paleta["borde"]),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
    ]))
    el.append(t_desc)
    el.append(Spacer(1, 12))

    # Paz y salvo
    letras = numero_a_letras(total_neto)
    el.append(KeepTogether([
        Paragraph(f"La suma de: <b>{letras} M/Cte {_fmt(total_neto)}</b>", estilos["paz_salvo"]),
        Spacer(1, 6),
        Paragraph(
            f"Declaro que a la Fecha la Empresa <b>{datos_empresa.get('nombre','')}</b> "
            f"con Nit#<b>{datos_empresa.get('nit','')}</b>, queda a "
            f"<b>PAZ y SALVO</b> por concepto de <b>PRESTACIONES SOCIALES</b>.",
            estilos["paz_salvo"]),
        Spacer(1, 28),
        HRFlowable(width=7*cm, thickness=0.7, color=paleta["primario"], spaceAfter=4),
        Paragraph("<b>Recibí</b>", estilos["firma_nombre"]),
        Paragraph(resultado.get("Nombre",""), estilos["firma_nombre"]),
        Paragraph(f"C.C.: {resultado.get('Documento','')}", estilos["firma_cargo"]),
    ]))
    el.append(Paragraph(
        "<b>Aviso:</b> Liquidación ESTIMADA (base 360 días). No incluye mora en cesantías, "
        "embargos, horas extras ni casos especiales. Valide con su contador.",
        estilos["nota"]))

    doc.build(el, onFirstPage=lambda c,d: _pie(c,d,paleta),
                  onLaterPages=lambda c,d: _pie(c,d,paleta))


def nombre_disenio(d: int) -> str:
    return PALETAS.get(d, PALETAS[1])["nombre"]


def previsualizacion_disenio(d: int) -> dict:
    """Retorna metadata del diseño para mostrar en la UI."""
    p = PALETAS.get(d, PALETAS[1])
    return {
        "nombre": p["nombre"],
        "primario": p["primario"].hexval() if hasattr(p["primario"], "hexval") else "#1B3F6E",
        "secundario": p["secundario"].hexval() if hasattr(p["secundario"], "hexval") else "#2D6BE4",
    }
