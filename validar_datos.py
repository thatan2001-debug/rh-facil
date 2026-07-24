"""
Historial visual del empleado (Etapa 10 — Opción B).

Muestra una línea de tiempo de todos los documentos generados para un
empleado, junto con eventos clave (ingreso, cambios registrados, retiro).

Se integra en la ficha del empleado o en su desplegable.
"""

import streamlit as st
from datetime import datetime
from utils.historial import obtener_por_empleado


# Iconos por tipo de documento (para el timeline)
ICONOS = {
    "certificado_con_salario":  "📄",
    "certificado_sin_salario":  "📄",
    "carta_vacaciones":         "🏖️",
    "liquidacion_prestaciones": "💰",
    "contrato_indefinido":      "📝",
    "contrato_fijo":            "📝",
    "contrato_obra":            "📝",
    "contrato_prestacion":      "📝",
    "otrosi":                   "✍️",
    "carta_terminacion":        "📮",
    "carta_no_renovacion":      "📮",
    "carta_aceptacion_renuncia":"📮",
    "cambio_horario":           "⏰",
    "cambio_cargo":             "💼",
    "cambio_salario":           "💵",
    "cambio_sede":              "🏢",
    "ascenso":                  "🚀",
    "reconocimiento":           "🏆",
    "permiso_remunerado":       "🌴",
    "permiso_no_remunerado":    "🌴",
    "constancia_retiro":        "📄",
    "entrega_dotacion":         "👕",
    "autorizacion_descuento":   "✍️",
    "paz_salvo":                "✅",
}

# Nombres legibles
NOMBRES = {
    "certificado_con_salario":  "Certificado con salario",
    "certificado_sin_salario":  "Certificado sin salario",
    "carta_vacaciones":         "Carta de vacaciones",
    "liquidacion_prestaciones": "Liquidación de prestaciones",
    "contrato_indefinido":      "Contrato indefinido",
    "contrato_fijo":            "Contrato a término fijo",
    "contrato_obra":            "Contrato por obra o labor",
    "contrato_prestacion":      "Contrato de prestación",
    "otrosi":                   "Otrosí al contrato",
    "carta_terminacion":        "Carta de terminación",
    "carta_no_renovacion":      "Carta de no renovación",
    "carta_aceptacion_renuncia":"Aceptación de renuncia",
    "cambio_horario":           "Cambio de horario",
    "cambio_cargo":             "Cambio de cargo",
    "cambio_salario":           "Cambio salarial",
    "cambio_sede":              "Cambio de sede",
    "ascenso":                  "Ascenso",
    "reconocimiento":           "Reconocimiento",
    "permiso_remunerado":       "Permiso remunerado",
    "permiso_no_remunerado":    "Permiso no remunerado",
    "constancia_retiro":        "Constancia de retiro",
    "entrega_dotacion":         "Entrega de dotación",
    "autorizacion_descuento":   "Autorización de descuento",
    "paz_salvo":                "Paz y salvo",
}

# Colores del timeline por categoría (para la barra lateral)
COLORES_CATEGORIA = {
    "documentos":     "#2D6BE4",  # azul
    "cambios":        "#B45309",  # naranja
    "reconocimiento": "#059669",  # verde
    "retiro":         "#DC2626",  # rojo
    "hito":           "#7C3AED",  # púrpura
}


def _clasificar(tipo_doc: str) -> str:
    if tipo_doc in ("ascenso", "reconocimiento"):
        return "reconocimiento"
    if tipo_doc in ("carta_terminacion", "carta_no_renovacion",
                     "carta_aceptacion_renuncia", "constancia_retiro",
                     "liquidacion_prestaciones", "paz_salvo"):
        return "retiro"
    if tipo_doc.startswith("cambio_") or tipo_doc == "otrosi":
        return "cambios"
    return "documentos"


def _formato_fecha(fecha_raw: str) -> str:
    """Convierte cualquier formato de fecha a 'dd MMM yyyy' legible."""
    if not fecha_raw:
        return "—"
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f",
                 "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
                 "%d/%m/%Y", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(str(fecha_raw)[:19], fmt)
            meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                     "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
            return f"{dt.day:02d} {meses[dt.month-1]} {dt.year}"
        except ValueError:
            continue
    return str(fecha_raw)[:10]


def mostrar_historial_empleado(email_empresa: str, empleado: dict,
                                 limite: int = 50):
    """
    Renderiza la línea de tiempo del empleado.

    Args:
        email_empresa: email del usuario (para filtrar historial)
        empleado: dict con datos del empleado
        limite: máximo de eventos a mostrar
    """
    doc_emp = empleado.get("documento", "")
    nombre_emp = empleado.get("nombre", "")
    fecha_ingreso = empleado.get("fecha_ingreso", "")
    fecha_retiro = empleado.get("fecha_retiro", "")

    # ── Cargar historial ────────────────────────────────────────────
    try:
        eventos_bd = obtener_por_empleado(email_empresa, doc_emp, limite=limite)
    except Exception:
        eventos_bd = []

    # ── Construir lista de eventos (BD + eventos sintéticos) ────────
    eventos = []

    # Evento sintético: ingreso
    if fecha_ingreso:
        eventos.append({
            "tipo":       "ingreso",
            "fecha_raw":  fecha_ingreso,
            "titulo":     "Ingreso a la empresa",
            "subtitulo":  f"Cargo inicial: {empleado.get('cargo', '—')}",
            "icono":      "🎯",
            "categoria":  "hito",
        })

    # Eventos del historial de documentos
    for e in eventos_bd:
        tipo = e.get("tipo_documento", "")
        eventos.append({
            "tipo":       tipo,
            "fecha_raw":  e.get("generado_en") or e.get("fecha_generacion", ""),
            "titulo":     NOMBRES.get(tipo, tipo.replace("_", " ").title()),
            "subtitulo":  _extraer_subtitulo(e),
            "icono":      ICONOS.get(tipo, "📄"),
            "categoria":  _clasificar(tipo),
        })

    # Evento sintético: retiro (si aplica)
    if fecha_retiro:
        eventos.append({
            "tipo":       "retiro",
            "fecha_raw":  fecha_retiro,
            "titulo":     "Retiro de la empresa",
            "subtitulo":  "Empleado retirado",
            "icono":      "🚪",
            "categoria":  "retiro",
        })

    # Ordenar cronológicamente (más recientes primero)
    def _parse_para_orden(fecha_raw):
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                     "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(str(fecha_raw)[:19], fmt)
            except ValueError:
                continue
        return datetime.min

    eventos.sort(key=lambda x: _parse_para_orden(x["fecha_raw"]), reverse=True)

    # ── Encabezado ──────────────────────────────────────────────────
    st.markdown(f"### 📊 Historial de **{nombre_emp}**")

    c1, c2, c3, c4 = st.columns(4)
    total = len(eventos_bd)
    contratos_gen = sum(1 for e in eventos_bd if "contrato" in e.get("tipo_documento", ""))
    cambios = sum(1 for e in eventos_bd
                    if e.get("tipo_documento", "").startswith("cambio_")
                    or e.get("tipo_documento") == "otrosi")
    reconocimientos = sum(1 for e in eventos_bd
                            if e.get("tipo_documento") in ("ascenso", "reconocimiento"))

    c1.metric("📄 Documentos", total)
    c2.metric("📝 Contratos", contratos_gen)
    c3.metric("✍️ Cambios", cambios)
    c4.metric("🏆 Reconocimientos", reconocimientos)

    st.divider()

    # ── Timeline ────────────────────────────────────────────────────
    if not eventos:
        st.info(
            "📭 Este empleado aún no tiene documentos generados. "
            "Cuando se generen certificados, contratos o cartas, aparecerán aquí."
        )
        return

    # Filtro por categoría
    with st.expander("🔎 Filtrar por tipo", expanded=False):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        f_docs = col_f1.checkbox("📄 Documentos", value=True, key=f"f_docs_{doc_emp}")
        f_cambios = col_f2.checkbox("✍️ Cambios", value=True, key=f"f_cambios_{doc_emp}")
        f_reconoc = col_f3.checkbox("🏆 Reconocimientos", value=True, key=f"f_rec_{doc_emp}")
        f_retiro = col_f4.checkbox("🚪 Retiro", value=True, key=f"f_ret_{doc_emp}")

    categorias_filtro = set()
    if f_docs: categorias_filtro.update(["documentos", "hito"])
    if f_cambios: categorias_filtro.add("cambios")
    if f_reconoc: categorias_filtro.add("reconocimiento")
    if f_retiro: categorias_filtro.add("retiro")

    eventos_filtrados = [e for e in eventos if e["categoria"] in categorias_filtro]

    if not eventos_filtrados:
        st.info("No hay eventos que coincidan con los filtros seleccionados.")
        return

    # Renderizar timeline
    st.markdown("### 📅 Línea de tiempo")
    st.caption(f"Mostrando {len(eventos_filtrados)} evento(s), más recientes primero")

    for i, evento in enumerate(eventos_filtrados):
        color = COLORES_CATEGORIA.get(evento["categoria"], "#6B7280")
        fecha_fmt = _formato_fecha(evento["fecha_raw"])

        # Cada evento como una card con borde de color
        st.markdown(f"""
        <div style="
            border-left: 4px solid {color};
            background: #F9FAFB;
            padding: 12px 16px;
            margin-bottom: 8px;
            border-radius: 4px;
        ">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="font-size: 1.5rem;">{evento["icono"]}</div>
                <div style="flex: 1;">
                    <div style="font-weight: 600; color: #111827; font-size: 1rem;">
                        {evento["titulo"]}
                    </div>
                    <div style="color: #6B7280; font-size: 0.9rem; margin-top: 2px;">
                        {evento["subtitulo"]}
                    </div>
                </div>
                <div style="
                    color: {color};
                    font-weight: 600;
                    font-size: 0.85rem;
                    text-align: right;
                ">{fecha_fmt}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _extraer_subtitulo(evento: dict) -> str:
    """Genera un subtítulo informativo según el tipo de evento."""
    tipo = evento.get("tipo_documento", "")

    # Motivo de retiro para liquidaciones
    if tipo == "liquidacion_prestaciones":
        motivo = evento.get("motivo_retiro") or evento.get("detalles", {})
        if isinstance(motivo, dict):
            motivo = motivo.get("motivo_retiro", "")
        if motivo:
            return f"Motivo: {motivo.replace('_', ' ').capitalize()}"
        return "Liquidación generada"

    # Info por defecto
    if evento.get("enviado_por_correo"):
        return "✉️ Enviado por correo"

    return "Documento generado"
