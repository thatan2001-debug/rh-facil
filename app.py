"""
RH Fácil — Generador de documentos laborales para PYMES (Colombia)
Versión 2.0: Diseño profesional + sistema de planes
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date, datetime
import zipfile
import io

from utils.validar_datos import cargar_y_validar
from utils.calcular_liquidacion import (
    calcular_liquidacion_df, SALARIO_MINIMO_2026, AUXILIO_TRANSPORTE_2026
)
from utils.generar_pdf import (
    generar_certificado_laboral, generar_carta_vacaciones, generar_pdf_liquidacion,
)
from utils.plan_control import (
    obtener_estado_plan, registrar_uso, link_whatsapp, PLANES
)
from utils.estilos import CSS

# ── Configuración de página ────────────────────────────────────────────────
st.set_page_config(
    page_title="RH Fácil — Documentos laborales",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)

# ── Carpetas ───────────────────────────────────────────────────────────────
CARPETA_SALIDAS = Path("salidas")
CARPETA_SALIDAS.mkdir(exist_ok=True)
CARPETA_ASSETS = Path("assets")
CARPETA_ASSETS.mkdir(exist_ok=True)
PLANTILLA_EXCEL = Path("plantillas/Base_Empleados.xlsx")

# ── Estado de sesión ───────────────────────────────────────────────────────
if "datos_empresa" not in st.session_state:
    st.session_state.datos_empresa = {
        "nombre": "", "nit": "", "representante": "", "logo_path": None,
    }
if "df_empleados" not in st.session_state:
    st.session_state.df_empleados = None
if "archivos_generados" not in st.session_state:
    st.session_state.archivos_generados = []

# ── Estado del plan ────────────────────────────────────────────────────────
estado_plan = obtener_estado_plan()
empresa_lista = bool(
    st.session_state.datos_empresa["nombre"] and
    st.session_state.datos_empresa["nit"]
)

# ── SIDEBAR ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📄 RH Fácil")
    st.caption("Documentos laborales en minutos")
    st.divider()

    pagina = st.radio(
        "nav",
        ["🏠  Inicio", "🏢  Mi empresa", "👥  Empleados",
         "⚡  Generar docs", "💎  Planes"],
        label_visibility="collapsed",
    )

    st.divider()

    # Badge del plan actual
    plan_nombre = estado_plan["plan_nombre"]
    docs_usados = estado_plan["documentos_usados"]
    docs_restantes = estado_plan["documentos_restantes"]

    st.markdown(f"""
    <div class="sidebar-plan-badge">
        <div class="sidebar-plan-nombre">Plan {plan_nombre}</div>
        <div class="sidebar-plan-docs">
            {'✅ Sin límite de documentos' if not estado_plan['limite']
             else f'📄 {docs_usados} docs generados · {docs_restantes} restantes'}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if estado_plan["dias_restantes"] is not None:
        dias = estado_plan["dias_restantes"]
        color = "#FCA5A5" if dias <= 1 else "rgba(255,255,255,0.7)"
        st.markdown(
            f'<p style="color:{color};font-size:0.75rem;margin-top:4px">'
            f'⏱ {dias} día{"s" if dias != 1 else ""} de prueba restante{"s" if dias != 1 else ""}'
            f'</p>',
            unsafe_allow_html=True,
        )

    if estado_plan["plan_expirado"] or (
        docs_restantes is not None and docs_restantes <= 1
    ):
        st.markdown(
            f'<a href="{link_whatsapp()}" target="_blank" style="'
            'display:block;background:#25D366;color:white;text-align:center;'
            'padding:8px;border-radius:8px;font-size:0.82rem;font-weight:600;'
            'text-decoration:none;margin-top:8px">💬 Actualizar plan</a>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown(
        f'<p style="color:rgba(255,255,255,0.5);font-size:0.72rem">'
        f'{"✅" if empresa_lista else "⬜"} Empresa configurada<br>'
        f'{"✅" if st.session_state.df_empleados is not None else "⬜"} Empleados cargados'
        f'</p>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA: INICIO
# ══════════════════════════════════════════════════════════════════════════════
if pagina == "🏠  Inicio":
    st.markdown("# Genera documentos laborales en minutos")
    st.markdown(
        "<p style='color:#6B7280;font-size:1.05rem;margin-top:-8px'>"
        "Certificados, cartas de vacaciones y liquidaciones según la ley colombiana. "
        "Para una empresa o cien, en segundos.</p>",
        unsafe_allow_html=True,
    )

    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("⏱ Tiempo por certificado", "< 3 seg", "vs. 15 min manual")
    with col2:
        st.metric("📋 Conceptos liquidación", "6 conceptos", "CST 2026 actualizado")
    with col3:
        st.metric("💼 Ideal para", "1 – 500 empleados", "PYMES colombianas")

    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 1️⃣ Configura tu empresa")
        st.write("Nombre, NIT, representante y logo. Se muestra en todos los documentos.")
    with col2:
        st.markdown("### 2️⃣ Carga tus empleados")
        st.write("Sube un Excel con los datos básicos. Puedes usar nuestra plantilla.")
    with col3:
        st.markdown("### 3️⃣ Genera y descarga")
        st.write("PDF profesional por empleado, todo empaquetado en un ZIP.")

    st.divider()

    st.warning(
        "⚖️ **Aviso legal:** Las liquidaciones son una estimación de referencia "
        "(cesantías, intereses, prima semestral, vacaciones, salario pendiente e indemnización "
        "Art. 64 CST). No reemplazan el concepto de un contador o abogado laboral. "
        f"Salario mínimo 2026: **${SALARIO_MINIMO_2026:,.0f}** · "
        f"Auxilio de transporte: **${AUXILIO_TRANSPORTE_2026:,.0f}**".replace(",", ".")
    )

# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA: MI EMPRESA
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🏢  Mi empresa":
    st.markdown("# Datos de tu empresa")
    st.markdown(
        "<p style='color:#6B7280'>Aparecen en el encabezado y firma de todos los documentos.</p>",
        unsafe_allow_html=True,
    )

    with st.form("form_empresa"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input(
                "Nombre o razón social *",
                value=st.session_state.datos_empresa["nombre"],
                placeholder="Ej: Distribuciones ABC SAS",
            )
            nit = st.text_input(
                "NIT *",
                value=st.session_state.datos_empresa["nit"],
                placeholder="Ej: 900123456-7",
            )
        with col2:
            representante = st.text_input(
                "Representante legal *",
                value=st.session_state.datos_empresa["representante"],
                placeholder="Nombre completo para la firma",
            )
            logo = st.file_uploader(
                "Logo (PNG o JPG, opcional)",
                type=["png", "jpg", "jpeg"],
            )

        guardar = st.form_submit_button("Guardar datos", type="primary")

        if guardar:
            if not nombre or not nit or not representante:
                st.error("Completa los campos obligatorios: nombre, NIT y representante.")
            else:
                logo_path = st.session_state.datos_empresa.get("logo_path")
                if logo is not None:
                    ext = logo.name.split(".")[-1]
                    logo_path = str(CARPETA_ASSETS / f"logo_empresa.{ext}")
                    with open(logo_path, "wb") as f:
                        f.write(logo.getbuffer())
                st.session_state.datos_empresa = {
                    "nombre": nombre, "nit": nit,
                    "representante": representante, "logo_path": logo_path,
                }
                st.success("✅ Datos guardados correctamente.")

    if st.session_state.datos_empresa.get("logo_path"):
        lp = st.session_state.datos_empresa["logo_path"]
        if Path(lp).exists():
            st.image(lp, width=120, caption="Logo actual")

# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA: EMPLEADOS
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "👥  Empleados":
    st.markdown("# Cargar empleados")
    st.markdown(
        "<p style='color:#6B7280'>Sube el Excel con tu base de empleados. "
        "Descarga la plantilla si es la primera vez.</p>",
        unsafe_allow_html=True,
    )

    if PLANTILLA_EXCEL.exists():
        with open(PLANTILLA_EXCEL, "rb") as f:
            st.download_button(
                "⬇️ Descargar plantilla Excel",
                f,
                file_name="Base_Empleados_RHFacil.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    st.caption(
        "Columnas obligatorias: **Nombre, Documento, Cargo, Salario, Fecha ingreso** "
        "· Opcionales: Fecha retiro, Tipo contrato, Correo"
    )
    st.divider()

    archivo = st.file_uploader("Sube tu archivo Excel de empleados", type=["xlsx"])

    if archivo:
        df, errores_columnas, errores_filas = cargar_y_validar(archivo)

        if errores_columnas:
            for err in errores_columnas:
                st.error(err)
        else:
            if errores_filas:
                st.warning(f"⚠️ {len(errores_filas)} problema(s) encontrado(s):")
                for err in errores_filas:
                    st.write(f"- {err}")
            else:
                st.success(f"✅ {len(df)} empleado(s) cargados sin errores.")

            st.dataframe(df, use_container_width=True)

            if not errores_filas:
                st.session_state.df_empleados = df
            else:
                if st.button("Continuar con filas válidas", type="secondary"):
                    st.session_state.df_empleados = df

# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA: GENERAR DOCUMENTOS
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "⚡  Generar docs":
    st.markdown("# Generar documentos")

    # ── Validaciones previas ──
    if not empresa_lista:
        st.error("⚠️ Primero completa los **datos de tu empresa** en la sección 🏢 Mi empresa.")
        st.stop()
    if st.session_state.df_empleados is None:
        st.error("⚠️ Primero carga una **base de empleados** en la sección 👥 Empleados.")
        st.stop()

    # ── Verificar límite del plan ──
    if estado_plan["plan_expirado"]:
        st.markdown(f"""
        <div class="banner-upgrade">
            <h3>⏰ Tu plan gratuito ha expirado</h3>
            <p>{estado_plan['razon_expiracion']}. Actualiza tu plan para seguir generando documentos.</p>
        </div>
        """, unsafe_allow_html=True)
        col1, col2 = st.columns([1, 3])
        with col1:
            st.link_button(
                "💬 Actualizar por WhatsApp",
                link_whatsapp("Hola, quiero actualizar mi plan de RH Fácil."),
            )
        st.stop()

    df = st.session_state.df_empleados
    datos_empresa = st.session_state.datos_empresa

    # ── Resumen ──
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Empresa", datos_empresa["nombre"])
    with col2:
        st.metric("Empleados listos", len(df))
    with col3:
        if estado_plan["limite"] and estado_plan["documentos_restantes"] is not None:
            restantes = estado_plan["documentos_restantes"]
            docs_posibles = min(len(df), restantes)
            st.metric("Docs que puedes generar", docs_posibles,
                      delta=f"{restantes} restantes en plan")
        else:
            st.metric("Documentos", "Sin límite")

    st.divider()
    st.markdown("### Selecciona los documentos")

    col1, col2, col3 = st.columns(3)
    with col1:
        gen_certificados = st.checkbox("📋 Certificados laborales", value=True)
    with col2:
        gen_vacaciones = st.checkbox("🏖️ Cartas de vacaciones")
    with col3:
        gen_liquidacion = st.checkbox("💰 Liquidaciones básicas")

    # ── Configuración de vacaciones ──
    fecha_inicio_vac, fecha_fin_vac = None, None
    if gen_vacaciones:
        st.markdown("**Período de vacaciones:**")
        c1, c2 = st.columns(2)
        with c1:
            fecha_inicio_vac = st.date_input("Fecha inicio", value=date.today())
        with c2:
            fecha_fin_vac = st.date_input("Fecha fin", value=date.today())

    # ── Configuración de liquidación ──
    fecha_corte_liq = None
    motivo_retiro = "renuncia"
    if gen_liquidacion:
        st.markdown("**Configuración de liquidación:**")
        c1, c2 = st.columns(2)
        with c1:
            fecha_corte_liq = st.date_input(
                "Fecha de corte (empleados activos)", value=date.today()
            )
        with c2:
            opciones_motivo = {
                "renuncia": "Renuncia voluntaria (sin indemnización)",
                "despido_sin_justa_causa": "Despido sin justa causa (con indemnización Art. 64 CST)",
                "mutuo_acuerdo": "Mutuo acuerdo (sin indemnización)",
                "vencimiento_contrato": "Vencimiento de contrato (sin indemnización)",
            }
            motivo_retiro = st.selectbox(
                "Motivo de retiro",
                options=list(opciones_motivo.keys()),
                format_func=lambda x: opciones_motivo[x],
            )
        if motivo_retiro == "despido_sin_justa_causa":
            st.warning(
                "⚠️ La indemnización por despido sin justa causa es una estimación. "
                "Valídala con un abogado laboral antes de usarla."
            )

    st.divider()

    # ── Verificar límite antes de generar ──
    tipos_seleccionados = sum([gen_certificados, gen_vacaciones, gen_liquidacion])
    docs_a_generar = len(df) * tipos_seleccionados

    if estado_plan["limite"] and estado_plan["documentos_restantes"] is not None:
        if docs_a_generar > estado_plan["documentos_restantes"]:
            st.warning(
                f"⚠️ Vas a generar **{docs_a_generar} documentos** pero solo tienes "
                f"**{estado_plan['documentos_restantes']} restantes** en tu plan. "
                f"Se procesarán los primeros {estado_plan['documentos_restantes']} documentos."
            )

    if st.button("🚀 Generar documentos", type="primary"):
        if tipos_seleccionados == 0:
            st.error("Selecciona al menos un tipo de documento.")
            st.stop()

        archivos_generados = []
        errores_generacion = []
        docs_limite = (
            estado_plan["documentos_restantes"]
            if estado_plan["limite"] else 9999
        )
        docs_generados_contador = 0
        barra = st.progress(0, text="Generando documentos...")
        total = len(df) * tipos_seleccionados

        for i, (_, fila) in enumerate(df.iterrows()):
            if docs_generados_contador >= docs_limite:
                break

            nombre_base = str(fila.get("Nombre", "empleado")).strip().replace(" ", "_")
            empleado = fila.to_dict()

            if gen_certificados:
                try:
                    ruta = CARPETA_SALIDAS / f"Certificado_{nombre_base}.pdf"
                    generar_certificado_laboral(empleado, datos_empresa, str(ruta))
                    archivos_generados.append(ruta)
                    docs_generados_contador += 1
                except Exception as e:
                    errores_generacion.append(f"Certificado {fila.get('Nombre')}: {e}")
                barra.progress(min((i * tipos_seleccionados + 1) / total, 1.0))

            if gen_vacaciones and docs_generados_contador < docs_limite:
                try:
                    ruta = CARPETA_SALIDAS / f"Vacaciones_{nombre_base}.pdf"
                    generar_carta_vacaciones(
                        empleado, datos_empresa, str(ruta),
                        fecha_inicio=fecha_inicio_vac.strftime("%d/%m/%Y"),
                        fecha_fin=fecha_fin_vac.strftime("%d/%m/%Y"),
                    )
                    archivos_generados.append(ruta)
                    docs_generados_contador += 1
                except Exception as e:
                    errores_generacion.append(f"Vacaciones {fila.get('Nombre')}: {e}")

        # Liquidaciones
        if gen_liquidacion and docs_generados_contador < docs_limite:
            df_calculo = df.copy()
            df_resultados, errores_calculo = calcular_liquidacion_df(
                df_calculo,
                fecha_corte_default=datetime(
                    fecha_corte_liq.year, fecha_corte_liq.month, fecha_corte_liq.day
                ),
                motivo_retiro=motivo_retiro,
            )
            errores_generacion.extend(errores_calculo)
            for _, resultado in df_resultados.iterrows():
                if docs_generados_contador >= docs_limite:
                    break
                nombre_base = str(resultado["Nombre"]).strip().replace(" ", "_")
                try:
                    ruta = CARPETA_SALIDAS / f"Liquidacion_{nombre_base}.pdf"
                    generar_pdf_liquidacion(resultado.to_dict(), datos_empresa, str(ruta))
                    archivos_generados.append(ruta)
                    docs_generados_contador += 1
                except Exception as e:
                    errores_generacion.append(f"Liquidación {resultado['Nombre']}: {e}")

            if not df_resultados.empty:
                ruta_excel = CARPETA_SALIDAS / "Resumen_Liquidaciones.xlsx"
                df_resultados.to_excel(ruta_excel, index=False)
                archivos_generados.append(ruta_excel)

        barra.progress(1.0, text="¡Listo!")
        registrar_uso(docs_generados_contador)
        st.session_state.archivos_generados = archivos_generados

        if errores_generacion:
            st.warning(f"{len(errores_generacion)} error(es):")
            for err in errores_generacion:
                st.write(f"- {err}")

        if archivos_generados:
            st.success(f"✅ {len(archivos_generados)} documento(s) generados correctamente.")

    # ── Descargar ZIP ──
    if st.session_state.archivos_generados:
        st.divider()
        buffer_zip = io.BytesIO()
        with zipfile.ZipFile(buffer_zip, "w") as zipf:
            for ruta in st.session_state.archivos_generados:
                if Path(ruta).exists():
                    zipf.write(ruta, Path(ruta).name)
        buffer_zip.seek(0)
        nombre_empresa = datos_empresa["nombre"].replace(" ", "_")
        st.download_button(
            "⬇️ Descargar todos los documentos (ZIP)",
            data=buffer_zip,
            file_name=f"RHFacil_{nombre_empresa}_{date.today()}.zip",
            mime="application/zip",
            type="primary",
        )

# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA: PLANES
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "💎  Planes":
    st.markdown("# Elige tu plan")
    st.markdown(
        "<p style='color:#6B7280'>Sin complicaciones. Escríbenos por WhatsApp y "
        "activamos tu plan en minutos.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    col1, col2, col3, col4 = st.columns(4)
    columnas = [col1, col2, col3, col4]
    plan_keys = ["gratuito", "basico", "pro", "empresarial"]
    badges = {
        "gratuito": '<span class="badge-gratis">Gratis</span>',
        "basico": '<span class="badge-popular">⭐ Popular</span>',
        "pro": '<span class="badge-pro">Pro</span>',
        "empresarial": "",
    }
    destacados = {"basico", "pro"}

    for col, key in zip(columnas, plan_keys):
        plan = PLANES[key]
        precio_fmt = (
            "Gratis" if plan["precio"] == 0
            else f"${plan['precio']:,}".replace(",", ".")
        )
        periodo = "" if plan["precio"] == 0 else "/ mes"
        features_html = "".join(
            [f'<div class="plan-feature">✓ {f}</div>' for f in plan["features"]]
        )
        destacado_class = "destacado" if key in destacados else ""

        with col:
            st.markdown(f"""
            <div class="plan-card {destacado_class}">
                <div style="margin-bottom:0.5rem">{badges[key]}</div>
                <div style="font-weight:700;font-size:1rem;color:#111827;margin-bottom:0.8rem">
                    {plan['nombre']}
                </div>
                <div class="plan-precio">{precio_fmt}</div>
                <div class="plan-periodo">{periodo}</div>
                <hr style="border-color:#E5E7EB;margin:0.8rem 0">
                <div style="color:#6B7280;font-size:0.8rem;margin-bottom:0.8rem">
                    {plan['descripcion']}
                </div>
                {features_html}
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            if key == "gratuito":
                st.markdown(
                    "<p style='text-align:center;font-size:0.8rem;color:#059669'>"
                    "✅ Ya estás en este plan</p>",
                    unsafe_allow_html=True,
                )
            else:
                mensaje_wa = (
                    f"Hola, quiero activar el plan {plan['nombre']} "
                    f"de RH Fácil (${plan['precio']:,}/mes). ¿Cómo procedo?"
                ).replace(",", ".")
                st.link_button(
                    "💬 Activar por WhatsApp",
                    link_whatsapp(mensaje_wa),
                    use_container_width=True,
                )

    st.divider()
    st.markdown(
        "<p style='text-align:center;color:#6B7280;font-size:0.85rem'>"
        "💳 Aceptamos transferencia bancaria, Nequi y próximamente PSE · "
        "Activación en menos de 2 horas hábiles · "
        "Cancela cuando quieras</p>",
        unsafe_allow_html=True,
    )
