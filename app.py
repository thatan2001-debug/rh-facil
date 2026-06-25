"""RH Fácil v5 — Login + 5 diseños + correo SMTP + ingresos variables + bug fix"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date, datetime
import zipfile, io

from utils.validar_datos import cargar_y_validar
from utils.calcular_liquidacion import calcular_liquidacion_df, SALARIO_MINIMO_2026, AUXILIO_TRANSPORTE_2026
from utils.plantillas_disenio import (
    generar_certificado, generar_vacaciones, generar_liquidacion,
    nombre_disenio, PALETAS,
)
from utils.plan_control import PLANES, link_whatsapp
from utils.auth import login, registrar, registrar_uso_usuario, obtener_limite_plan
from utils.correo import enviar_documentos, smtp_configurado, instrucciones_gmail
from utils.estilos import CSS

st.set_page_config(page_title="RH Fácil", page_icon="📄", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

CARPETA_SALIDAS = Path("salidas"); CARPETA_SALIDAS.mkdir(exist_ok=True)
CARPETA_ASSETS  = Path("assets");  CARPETA_ASSETS.mkdir(exist_ok=True)
PLANTILLA_EXCEL = Path("plantillas/Base_Empleados.xlsx")

# ── Sesión ──────────────────────────────────────────────────────────────────
for k,v in [("usuario",None),("datos_empresa",{"nombre":"","nit":"",
    "representante":"","correo_empresa":"","logo_path":None}),
    ("df_empleados",None),("archivos_generados",[]),("disenio_seleccionado",1)]:
    if k not in st.session_state: st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA DE LOGIN / REGISTRO
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.usuario:
    col_izq, col_centro, col_der = st.columns([1,2,1])
    with col_centro:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align:center;margin-bottom:1.5rem'>
            <div style='font-size:2.5rem'>📄</div>
            <h1 style='color:#1B3F6E;margin:0'>RH Fácil</h1>
            <p style='color:#6B7280;margin-top:4px'>Documentos laborales para PYMES colombianas</p>
        </div>""", unsafe_allow_html=True)

        tab_login, tab_registro = st.tabs(["🔐 Iniciar sesión", "✨ Crear cuenta"])

        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            email_l    = st.text_input("Correo electrónico", key="l_email",
                placeholder="tucorreo@empresa.com")
            password_l = st.text_input("Contraseña", type="password", key="l_pass")

            if st.button("Ingresar", type="primary", use_container_width=True):
                ok, msg, datos = login(email_l, password_l)
                if ok:
                    st.session_state.usuario = datos
                    st.rerun()
                else:
                    st.error(msg)

            st.divider()
            st.markdown("""
            <div style='background:#EFF6FF;border-radius:10px;padding:1rem;margin-top:0.5rem'>
                <p style='margin:0;font-size:0.85rem;color:#1B3F6E;font-weight:600'>
                    🎯 Cuenta Demo — acceso completo</p>
                <p style='margin:4px 0 0;font-size:0.82rem;color:#374151'>
                    <b>Usuario:</b> demo@rhfacil.co<br>
                    <b>Contraseña:</b> RHFacil2026</p>
            </div>""", unsafe_allow_html=True)

        with tab_registro:
            st.markdown("<br>", unsafe_allow_html=True)
            nombre_r   = st.text_input("Nombre completo", key="r_nombre")
            email_r    = st.text_input("Correo electrónico", key="r_email")
            password_r = st.text_input("Contraseña (mín. 6 caracteres)", type="password", key="r_pass")
            password_r2= st.text_input("Confirmar contraseña", type="password", key="r_pass2")

            if st.button("Crear cuenta gratis", type="primary", use_container_width=True):
                if password_r != password_r2:
                    st.error("Las contraseñas no coinciden.")
                else:
                    ok, msg = registrar(email_r, nombre_r, password_r)
                    if ok:
                        st.success(f"✅ {msg} Ya puedes iniciar sesión.")
                    else:
                        st.error(msg)
    st.stop()

# ── Usuario autenticado ──────────────────────────────────────────────────────
usuario    = st.session_state.usuario
plan_info  = obtener_limite_plan(usuario["plan"])
empresa_ok = bool(st.session_state.datos_empresa["nombre"] and
                  st.session_state.datos_empresa["nit"])

# ── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"## 📄 RH Fácil")
    st.caption(f"Hola, **{usuario['nombre'].split()[0]}** 👋")
    st.divider()

    pagina = st.radio("nav", [
        "🏠  Inicio", "🏢  Mi empresa", "👥  Empleados",
        "🎨  Diseño de plantillas", "⚡  Generar docs", "💎  Planes",
    ], label_visibility="collapsed")

    st.divider()
    docs_usados = usuario.get("documentos_usados", 0)
    max_docs    = plan_info["max_docs"]
    sin_limite  = not plan_info["tiene_limite"]

    st.markdown(f"""
    <div class="sidebar-plan-badge">
        <div class="sidebar-plan-nombre">Plan {usuario['plan'].capitalize()}</div>
        <div class="sidebar-plan-docs">
            {'✅ Documentos ilimitados' if sin_limite
             else f'📄 {docs_usados} usados · {max(0, max_docs-docs_usados)} restantes'}
        </div>
    </div>""", unsafe_allow_html=True)

    if not sin_limite and max_docs > 0:
        prog = min(docs_usados / max_docs, 1.0)
        st.progress(prog)

    st.divider()
    st.markdown(
        f'<p style="color:rgba(255,255,255,0.5);font-size:0.72rem">'
        f'{"✅" if empresa_ok else "⬜"} Empresa configurada<br>'
        f'{"✅" if st.session_state.df_empleados is not None else "⬜"} Empleados cargados<br>'
        f'🎨 Diseño #{st.session_state.disenio_seleccionado}: '
        f'{nombre_disenio(st.session_state.disenio_seleccionado)}</p>',
        unsafe_allow_html=True)

    st.divider()
    if st.button("🚪 Cerrar sesión", use_container_width=True):
        st.session_state.usuario = None
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# INICIO
# ══════════════════════════════════════════════════════════════════════════════
if pagina == "🏠  Inicio":
    st.markdown("# Genera documentos laborales en minutos")
    st.markdown("<p style='color:#6B7280'>Certificados, vacaciones y liquidaciones según el CST colombiano 2026.</p>", unsafe_allow_html=True)
    st.divider()
    c1,c2,c3 = st.columns(3)
    c1.metric("⏱ Por certificado","< 3 seg","vs 15 min manual")
    c2.metric("📋 Conceptos liquidación","6 conceptos","CST 2026")
    c3.metric("🎨 Diseños disponibles","5 plantillas","Elige la tuya")
    st.divider()
    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown("### 1️⃣ Empresa y diseño"); st.write("Configura tus datos y elige entre 5 plantillas profesionales.")
    with c2:
        st.markdown("### 2️⃣ Empleados"); st.write("Sube el Excel con tu personal. Descarga la plantilla actualizada.")
    with c3:
        st.markdown("### 3️⃣ Genera y envía"); st.write("PDF por empleado + ZIP + envío directo al correo de cada uno.")
    st.divider()
    st.warning(f"⚖️ Las liquidaciones son una **estimación de referencia**. No reemplazan el concepto de un contador o abogado laboral. SMMLV 2026: **${SALARIO_MINIMO_2026:,.0f}** · Auxilio transporte: **${AUXILIO_TRANSPORTE_2026:,.0f}**".replace(",","."))

# ══════════════════════════════════════════════════════════════════════════════
# MI EMPRESA
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🏢  Mi empresa":
    st.markdown("# Datos de tu empresa")
    with st.form("form_empresa"):
        c1,c2 = st.columns(2)
        with c1:
            nombre     = st.text_input("Razón social *", value=st.session_state.datos_empresa["nombre"], placeholder="Distribuciones ABC SAS")
            nit        = st.text_input("NIT *", value=st.session_state.datos_empresa["nit"], placeholder="900123456-7")
            correo_emp = st.text_input("Correo corporativo *", value=st.session_state.datos_empresa.get("correo_empresa",""), placeholder="rrhh@miempresa.com", help="Se usa para enviar documentos a empleados y como remitente en los correos.")
        with c2:
            representante = st.text_input("Representante legal *", value=st.session_state.datos_empresa["representante"], placeholder="Nombre completo para la firma")
            logo = st.file_uploader("Logo / Membrete (PNG o JPG)", type=["png","jpg","jpeg"], help="Aparece en el encabezado de todos los documentos")

        guardar = st.form_submit_button("Guardar datos", type="primary")
        if guardar:
            if not nombre or not nit or not representante or not correo_emp:
                st.error("Completa todos los campos obligatorios (*).")
            else:
                logo_path = st.session_state.datos_empresa.get("logo_path")
                if logo:
                    ext = logo.name.split(".")[-1]
                    logo_path = str(CARPETA_ASSETS / f"logo_empresa.{ext}")
                    with open(logo_path,"wb") as f: f.write(logo.getbuffer())
                st.session_state.datos_empresa = {"nombre":nombre,"nit":nit,
                    "representante":representante,"correo_empresa":correo_emp,"logo_path":logo_path}
                st.success("✅ Datos guardados.")

    if st.session_state.datos_empresa.get("logo_path"):
        lp = st.session_state.datos_empresa["logo_path"]
        if Path(lp).exists():
            st.image(lp, width=120, caption="Logo actual")

    st.divider()
    st.markdown("### Configuración de correo (SMTP)")
    if smtp_configurado():
        st.success("✅ SMTP configurado. Los envíos de correo están activos.")
    else:
        st.warning("⚠️ SMTP no configurado. Activa el envío de correos en Render → Environment.")
        with st.expander("📧 Cómo configurar Gmail para envíos automáticos"):
            st.markdown(instrucciones_gmail())

# ══════════════════════════════════════════════════════════════════════════════
# DISEÑO DE PLANTILLAS
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🎨  Diseño de plantillas":
    st.markdown("# Elige el diseño de tus documentos")
    st.markdown("<p style='color:#6B7280'>Selecciona la plantilla que mejor represente tu empresa. Aplica a certificados, vacaciones y liquidaciones.</p>", unsafe_allow_html=True)
    st.divider()

    # Mostrar los 5 diseños como cards visuales
    cols = st.columns(5)
    for i, col in enumerate(cols, 1):
        paleta = PALETAS[i]
        p_hex  = paleta["primario"].hexval() if hasattr(paleta["primario"],"hexval") else "#1B3F6E"
        s_hex  = paleta["secundario"].hexval() if hasattr(paleta["secundario"],"hexval") else "#2D6BE4"
        a_hex  = paleta["acento"].hexval() if hasattr(paleta["acento"],"hexval") else "#EFF6FF"
        seleccionado = st.session_state.disenio_seleccionado == i

        with col:
            st.markdown(f"""
            <div style="border:3px solid {'#2D6BE4' if seleccionado else '#E5E7EB'};
                border-radius:12px;overflow:hidden;margin-bottom:8px;
                box-shadow:{'0 0 0 3px #DBEAFE' if seleccionado else 'none'}">
                <div style="background:{p_hex};padding:14px;text-align:center">
                    <div style="color:white;font-weight:700;font-size:0.85rem">EMPRESA S.A.S</div>
                    <div style="color:rgba(255,255,255,0.7);font-size:0.7rem">NIT #900.123.456</div>
                </div>
                <div style="background:white;padding:10px">
                    <div style="background:{a_hex};border-left:3px solid {s_hex};
                        padding:6px 8px;margin-bottom:6px;font-size:0.7rem;color:#374151">
                        Certificación Laboral
                    </div>
                    <div style="height:4px;background:{s_hex};border-radius:2px;width:60%;margin-bottom:4px"></div>
                    <div style="height:3px;background:#E5E7EB;border-radius:2px;width:80%;margin-bottom:4px"></div>
                    <div style="height:3px;background:#E5E7EB;border-radius:2px;width:70%"></div>
                    <div style="margin-top:8px;padding-top:6px;border-top:1px solid #E5E7EB;
                        font-size:0.65rem;color:#6B7280">Representante Legal</div>
                </div>
            </div>
            <div style="text-align:center;font-size:0.78rem;font-weight:{'700' if seleccionado else '400'};
                color:{'#1B3F6E' if seleccionado else '#6B7280'}">
                {'✅ ' if seleccionado else ''}Diseño {i}<br>{paleta['nombre']}
            </div>""", unsafe_allow_html=True)

            if st.button(f"{'✓ Seleccionado' if seleccionado else 'Seleccionar'}",
                         key=f"btn_d{i}", use_container_width=True,
                         type="primary" if seleccionado else "secondary"):
                st.session_state.disenio_seleccionado = i
                st.rerun()

    st.divider()
    d = st.session_state.disenio_seleccionado
    st.info(f"🎨 Diseño activo: **{nombre_disenio(d)}** — Se aplicará a todos los documentos que generes.")

    # Generar PDF de muestra
    if empresa_ok:
        if st.button("👁️ Generar documento de muestra con este diseño", type="primary"):
            from utils.calcular_liquidacion import calcular_liquidacion_fila
            emp_demo = {"Nombre":"Ejemplo Empleado","Documento":"1000000001",
                "Cargo":"Auxiliar Administrativo","Salario":1800000,
                "Fecha ingreso":"01/01/2024","Tipo contrato":"Indefinido",
                "Ingreso promedio variable":0}
            ruta_demo = str(CARPETA_SALIDAS / f"muestra_disenio_{d}.pdf")
            generar_certificado(emp_demo, st.session_state.datos_empresa, ruta_demo, d)
            with open(ruta_demo,"rb") as f:
                st.download_button("⬇️ Descargar muestra (PDF)",f,
                    file_name=f"muestra_{nombre_disenio(d).replace(' ','_')}.pdf",
                    mime="application/pdf", type="primary")
    else:
        st.info("💡 Completa los datos de tu empresa para generar una muestra con tu logo y nombre.")

# ══════════════════════════════════════════════════════════════════════════════
# EMPLEADOS
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "👥  Empleados":
    st.markdown("# Cargar empleados")
    if PLANTILLA_EXCEL.exists():
        with open(PLANTILLA_EXCEL,"rb") as f:
            st.download_button("⬇️ Descargar plantilla Excel",f,
                file_name="Base_Empleados_RHFacil.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.caption("Obligatorios: **Nombre, Documento, Cargo, Salario, Fecha ingreso** · Nuevos: **Cuenta bancaria, Ingreso promedio variable, Correo**")
    st.divider()
    archivo = st.file_uploader("Sube tu Excel de empleados", type=["xlsx"])
    if archivo:
        df, err_col, err_fila = cargar_y_validar(archivo)
        if err_col:
            for e in err_col: st.error(e)
        else:
            if err_fila:
                st.warning(f"⚠️ {len(err_fila)} problema(s):")
                for e in err_fila: st.write(f"- {e}")
            else:
                st.success(f"✅ {len(df)} empleado(s) cargados sin errores.")
            st.dataframe(df, use_container_width=True)
            if not err_fila:
                st.session_state.df_empleados = df
            elif st.button("Continuar con filas válidas"):
                st.session_state.df_empleados = df

# ══════════════════════════════════════════════════════════════════════════════
# GENERAR DOCUMENTOS
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "⚡  Generar docs":
    st.markdown("# Generar documentos")
    if not empresa_ok:
        st.error("⚠️ Completa los **datos de tu empresa** primero."); st.stop()
    if st.session_state.df_empleados is None:
        st.error("⚠️ Carga una **base de empleados** primero."); st.stop()

    df             = st.session_state.df_empleados
    datos_empresa  = st.session_state.datos_empresa
    disenio        = st.session_state.disenio_seleccionado
    max_docs       = plan_info["max_docs"]
    sin_limite     = not plan_info["tiene_limite"]
    docs_usados    = usuario.get("documentos_usados",0)
    docs_restantes = None if sin_limite else max(0, max_docs - docs_usados)

    c1,c2,c3 = st.columns(3)
    c1.metric("Empresa", datos_empresa["nombre"])
    c2.metric("Empleados", len(df))
    c3.metric("Diseño activo", f"#{disenio} {nombre_disenio(disenio)}")
    st.divider()

    # ── BUG FIX: checkboxes sin valor por defecto True ──
    st.markdown("### Selecciona qué documentos generar")
    c1,c2,c3 = st.columns(3)
    with c1: gen_cert = st.checkbox("📋 Certificados laborales")
    with c2: gen_vac  = st.checkbox("🏖️ Cartas de vacaciones")
    with c3: gen_liq  = st.checkbox("💰 Liquidaciones de prestaciones")

    # Ingresos variables (solo para certificados)
    ing_variable_global = 0
    if gen_cert:
        st.markdown("**Certificados laborales:**")
        tiene_variable = st.radio(
            "¿Algún empleado tiene ingresos variables?",
            ["No", "Sí — usar el valor del Excel por empleado",
             "Sí — aplicar un valor global a todos"],
            horizontal=True,
        )
        if tiene_variable == "Sí — aplicar un valor global a todos":
            ing_variable_global = st.number_input(
                "Promedio mensual de ingresos variables ($)",
                min_value=0, value=0, step=50000,
                help="Se incluirá en todos los certificados de esta generación.")

    # Vacaciones
    fecha_ini_vac = fecha_fin_vac = None
    if gen_vac:
        st.markdown("**Período de vacaciones:**")
        c1,c2 = st.columns(2)
        with c1: fecha_ini_vac = st.date_input("Fecha inicio", date.today(), key="vi")
        with c2: fecha_fin_vac = st.date_input("Fecha fin", date.today(), key="vf")

    # Liquidaciones
    fecha_corte_liq = None; motivo_retiro = "renuncia"
    if gen_liq:
        st.markdown("**Liquidaciones:**")
        c1,c2 = st.columns(2)
        with c1:
            fecha_corte_liq = st.date_input("Fecha de corte (activos)", date.today())
        with c2:
            MOTIVOS = {"renuncia":"Renuncia voluntaria","despido_sin_justa_causa":"Despido sin justa causa (Art.64 CST)",
                "mutuo_acuerdo":"Mutuo acuerdo","vencimiento_contrato":"Vencimiento de contrato"}
            motivo_retiro = st.selectbox("Motivo de retiro",
                list(MOTIVOS.keys()), format_func=lambda x: MOTIVOS[x])
        if motivo_retiro == "despido_sin_justa_causa":
            st.warning("⚠️ La indemnización es una estimación. Valídala con un abogado laboral.")

    # Correo
    st.divider()
    enviar_correos = False
    if smtp_configurado():
        enviar_correos = st.checkbox(
            "📧 Enviar documentos por correo a cada empleado",
            help="Requiere que cada empleado tenga correo en el Excel.")
    else:
        st.caption("💡 Configura SMTP en 'Mi empresa' para habilitar el envío por correo.")

    st.divider()
    tipos = sum([gen_cert, gen_vac, gen_liq])
    docs_a_generar = len(df) * tipos
    if not sin_limite and docs_restantes is not None and docs_a_generar > docs_restantes:
        st.warning(f"⚠️ Se generarán {min(docs_a_generar, docs_restantes)} de {docs_a_generar} docs (límite de plan).")

    if st.button("🚀 Generar documentos", type="primary"):
        if tipos == 0:
            st.error("Selecciona al menos un tipo de documento."); st.stop()

        archivos_generados = []; errores = []; contador = 0
        limite = docs_restantes if not sin_limite else 99999
        barra  = st.progress(0, text="Generando…")
        total  = len(df) * tipos

        for paso, (_, fila) in enumerate(df.iterrows()):
            if contador >= limite: break
            empleado = fila.to_dict()
            nb = str(fila.get("Nombre","x")).strip().replace(" ","_")
            pdfs_empleado = []

            if gen_cert and contador < limite:
                # Ingresos variables
                if tiene_variable == "Sí — usar el valor del Excel por empleado":
                    empleado["Ingreso promedio variable"] = fila.get("Ingreso promedio variable", 0) or 0
                elif tiene_variable == "Sí — aplicar un valor global a todos":
                    empleado["Ingreso promedio variable"] = ing_variable_global
                try:
                    ruta = str(CARPETA_SALIDAS / f"Certificado_{nb}.pdf")
                    generar_certificado(empleado, datos_empresa, ruta, disenio)
                    archivos_generados.append(Path(ruta)); pdfs_empleado.append(ruta)
                    contador += 1
                except Exception as e:
                    errores.append(f"Cert {fila.get('Nombre')}: {e}")

            if gen_vac and contador < limite:
                try:
                    ruta = str(CARPETA_SALIDAS / f"Vacaciones_{nb}.pdf")
                    generar_vacaciones(empleado, datos_empresa, ruta,
                        fecha_ini_vac.strftime("%d/%m/%Y"), fecha_fin_vac.strftime("%d/%m/%Y"), disenio)
                    archivos_generados.append(Path(ruta)); pdfs_empleado.append(ruta)
                    contador += 1
                except Exception as e:
                    errores.append(f"Vac {fila.get('Nombre')}: {e}")

            # Envío por correo individual
            if enviar_correos and pdfs_empleado:
                correo_emp_dest = str(fila.get("Correo","")).strip()
                if correo_emp_dest and "@" in correo_emp_dest:
                    ok_mail, msg_mail = enviar_documentos(
                        correo_emp_dest, str(fila.get("Nombre","")),
                        datos_empresa["nombre"], "Documentos laborales",
                        pdfs_empleado, datos_empresa.get("correo_empresa",""))
                    if not ok_mail: errores.append(f"Correo {fila.get('Nombre')}: {msg_mail}")

            barra.progress(min((paso+1)/len(df), 1.0))

        # Liquidaciones en bloque
        if gen_liq and contador < limite:
            df_res, err_liq = calcular_liquidacion_df(
                df.copy(),
                fecha_corte_default=datetime(fecha_corte_liq.year,
                    fecha_corte_liq.month, fecha_corte_liq.day),
                motivo_retiro=motivo_retiro)
            errores.extend(err_liq)
            for _, res in df_res.iterrows():
                if contador >= limite: break
                nb = str(res["Nombre"]).strip().replace(" ","_")
                try:
                    ruta = str(CARPETA_SALIDAS / f"Liquidacion_{nb}.pdf")
                    generar_liquidacion(res.to_dict(), datos_empresa, ruta, disenio)
                    archivos_generados.append(Path(ruta))
                    contador += 1
                    if enviar_correos:
                        correo_emp_dest = str(df.loc[df["Nombre"]==res["Nombre"],"Correo"].values[0] if "Correo" in df.columns else "").strip()
                        if correo_emp_dest and "@" in correo_emp_dest:
                            enviar_documentos(correo_emp_dest, res["Nombre"],
                                datos_empresa["nombre"], "Liquidación de Prestaciones Sociales",
                                [ruta], datos_empresa.get("correo_empresa",""))
                except Exception as e:
                    errores.append(f"Liq {res['Nombre']}: {e}")

            if not df_res.empty:
                ruta_xls = str(CARPETA_SALIDAS / "Resumen_Liquidaciones.xlsx")
                df_res.to_excel(ruta_xls, index=False)
                archivos_generados.append(Path(ruta_xls))

        barra.progress(1.0, text="¡Listo!")
        registrar_uso_usuario(usuario["email"], contador)
        usuario["documentos_usados"] = usuario.get("documentos_usados",0) + contador
        st.session_state.archivos_generados = archivos_generados

        if errores:
            st.warning(f"{len(errores)} error(es):")
            for e in errores: st.write(f"- {e}")
        if archivos_generados:
            st.success(f"✅ {contador} documento(s) generados con el diseño **{nombre_disenio(disenio)}**.")

    # Descargar ZIP
    if st.session_state.archivos_generados:
        st.divider()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf,"w") as zf:
            for p in st.session_state.archivos_generados:
                if Path(p).exists(): zf.write(p, Path(p).name)
        buf.seek(0)
        st.download_button("⬇️ Descargar todos los documentos (ZIP)", buf,
            file_name=f"RHFacil_{datos_empresa['nombre'].replace(' ','_')}_{date.today()}.zip",
            mime="application/zip", type="primary")
        with st.expander("Ver archivos generados"):
            for p in st.session_state.archivos_generados:
                st.write(f"- {Path(p).name}")

# ══════════════════════════════════════════════════════════════════════════════
# PLANES
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "💎  Planes":
    st.markdown("# Planes y precios")
    st.markdown("<p style='color:#6B7280'>Escríbenos por WhatsApp y activamos tu plan en minutos.</p>", unsafe_allow_html=True)
    st.divider()
    cols = st.columns(4)
    plan_keys = ["gratuito","basico","pro","empresarial"]
    for col, key in zip(cols, plan_keys):
        plan = PLANES[key]
        precio = "Gratis" if plan["precio"]==0 else f"${plan['precio']:,}".replace(",",".")
        periodo = "" if plan["precio"]==0 else "/mes"
        activo  = usuario["plan"] == key
        features = "".join([f'<div class="plan-feature">✓ {f}</div>' for f in plan["features"]])
        with col:
            st.markdown(f"""
            <div class="plan-card {'destacado' if key in ('basico','pro') else ''}">
                <div style="font-weight:700;font-size:1rem;margin-bottom:.5rem">{plan['nombre']}</div>
                <div class="plan-precio">{precio}</div>
                <div class="plan-periodo">{periodo}</div>
                <hr style="border-color:#E5E7EB;margin:.6rem 0">
                {features}
            </div>""", unsafe_allow_html=True)
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            if activo:
                st.markdown("<p style='text-align:center;font-size:0.8rem;color:#059669'>✅ Plan actual</p>", unsafe_allow_html=True)
            else:
                msg = f"Quiero activar el plan {plan['nombre']} de RH Fácil (${plan['precio']:,}/mes). Mi correo es {usuario['email']}".replace(",",".")
                st.link_button("💬 Activar por WhatsApp", link_whatsapp(msg), use_container_width=True)
    st.divider()
    st.markdown("<p style='text-align:center;color:#6B7280;font-size:0.85rem'>💳 Aceptamos transferencia, Nequi y PSE · Activación en menos de 2 horas · Cancela cuando quieras</p>", unsafe_allow_html=True)
