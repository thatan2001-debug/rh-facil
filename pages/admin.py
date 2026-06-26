"""
Panel de Administrador — RH Fácil
URL: /admin  (Streamlit multipage)
Solo accesible para admin@rhfacil.co
"""

import streamlit as st
import pandas as pd
from utils.auth import (
    login, listar_usuarios, activar_usuario, desactivar_usuario,
    cambiar_plan, eliminar_usuario, stats_resumen, ADMIN_EMAIL,
)
from utils.plan_control import PLANES
from utils.estilos import CSS

st.set_page_config(page_title="Admin — RH Fácil", page_icon="🛡️", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

# ── Colores extra para admin ─────────────────────────────────────────────────
st.markdown("""
<style>
.stat-card {
    background: white;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    text-align: center;
}
.stat-num { font-size: 2rem; font-weight: 700; color: #1B3F6E; line-height: 1; }
.stat-label { font-size: 0.8rem; color: #6B7280; margin-top: 4px; text-transform: uppercase; letter-spacing: .05em; }
.badge-activo   { background:#D1FAE5;color:#065F46;border-radius:20px;padding:2px 10px;font-size:.78rem;font-weight:600; }
.badge-inactivo { background:#FEE2E2;color:#991B1B;border-radius:20px;padding:2px 10px;font-size:.78rem;font-weight:600; }
.badge-pendiente{ background:#FEF3C7;color:#92400E;border-radius:20px;padding:2px 10px;font-size:.78rem;font-weight:600; }
.badge-plan     { background:#EFF6FF;color:#1E40AF;border-radius:20px;padding:2px 8px;font-size:.75rem; }
</style>
""", unsafe_allow_html=True)

# ── Autenticación de admin ───────────────────────────────────────────────────
if "admin_autenticado" not in st.session_state:
    st.session_state.admin_autenticado = False
if "admin_datos" not in st.session_state:
    st.session_state.admin_datos = None

if not st.session_state.admin_autenticado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("""
        <div style='text-align:center;padding:2rem 0 1rem'>
            <div style='font-size:2.5rem'>🛡️</div>
            <h2 style='color:#1B3F6E;margin:0'>Panel de Administrador</h2>
            <p style='color:#6B7280;margin-top:4px;font-size:.9rem'>RH Fácil — Acceso restringido</p>
        </div>""", unsafe_allow_html=True)

        email_a = st.text_input("Correo administrador", placeholder="admin@rhfacil.co")
        pass_a  = st.text_input("Contraseña", type="password")

        if st.button("Acceder al panel", type="primary", use_container_width=True):
            if email_a.strip().lower() != ADMIN_EMAIL:
                st.error("❌ Solo el administrador puede acceder a este panel.")
            else:
                ok, msg, datos = login(email_a, pass_a)
                if ok and datos.get("es_admin"):
                    st.session_state.admin_autenticado = True
                    st.session_state.admin_datos = datos
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
    st.stop()

# ── Panel autenticado ────────────────────────────────────────────────────────
admin = st.session_state.admin_datos
st.markdown(f"""
<div style='display:flex;justify-content:space-between;align-items:center;
    background:linear-gradient(135deg,#1B3F6E,#2D6BE4);border-radius:12px;
    padding:1rem 1.5rem;margin-bottom:1.5rem'>
    <div>
        <span style='color:white;font-size:1.1rem;font-weight:700'>🛡️ Panel de Administrador</span>
        <span style='color:rgba(255,255,255,.7);font-size:.85rem;margin-left:12px'>RH Fácil</span>
    </div>
    <span style='color:rgba(255,255,255,.85);font-size:.85rem'>👤 {admin['nombre']}</span>
</div>""", unsafe_allow_html=True)

# ── Tabs del panel ───────────────────────────────────────────────────────────
tab_dash, tab_usuarios, tab_pendientes = st.tabs([
    "📊 Dashboard", "👥 Todos los usuarios", "⏳ Pendientes de activación"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab_dash:
    stats = stats_resumen()

    c1, c2, c3, c4, c5 = st.columns(5)
    for col, num, label, color in [
        (c1, stats["total"], "Usuarios totales", "#1B3F6E"),
        (c2, stats["activos"], "Activos", "#059669"),
        (c3, stats["pendientes_activacion"], "Pendientes activar", "#D97706"),
        (c4, stats["total"] - stats["activos"], "Desactivados", "#DC2626"),
        (c5, stats["total_docs"], "Documentos generados", "#7C3AED"),
    ]:
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-num" style="color:{color}">{num}</div>
                <div class="stat-label">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Distribución por plan")
    c1, c2, c3, c4 = st.columns(4)
    for col, plan_key in zip([c1,c2,c3,c4], ["gratuito","basico","pro","empresarial"]):
        with col:
            n = stats["por_plan"].get(plan_key, 0)
            plan_nombre = PLANES[plan_key]["nombre"]
            precio = PLANES[plan_key]["precio"]
            ingreso = n * precio
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-num">{n}</div>
                <div class="stat-label">{plan_nombre}</div>
                <div style="font-size:.75rem;color:#059669;margin-top:4px">
                    ${ingreso:,.0f} COP/mes
                </div>
            </div>""".replace(",","."), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    ingreso_total = sum(
        stats["por_plan"].get(k, 0) * PLANES[k]["precio"]
        for k in ["basico","pro","empresarial"]
    )
    st.success(f"💰 **Ingreso mensual estimado: ${ingreso_total:,.0f} COP**".replace(",","."))

    # Alerta pendientes
    if stats["pendientes_activacion"] > 0:
        st.warning(
            f"⏳ **{stats['pendientes_activacion']} usuario(s) esperando activación.** "
            f"Ve a la pestaña 'Pendientes de activación'."
        )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: TODOS LOS USUARIOS
# ══════════════════════════════════════════════════════════════════════════════
with tab_usuarios:
    usuarios = listar_usuarios()

    if not usuarios:
        st.info("No hay usuarios registrados aún.")
    else:
        # Filtros
        c1, c2, c3 = st.columns(3)
        with c1:
            filtro_estado = st.selectbox("Estado", ["Todos","Activos","Inactivos","Pendientes"])
        with c2:
            filtro_plan = st.selectbox("Plan", ["Todos"] + list(PLANES.keys()))
        with c3:
            buscar = st.text_input("Buscar por nombre o correo", placeholder="🔍")

        # Aplicar filtros
        lista = usuarios.copy()
        if filtro_estado == "Activos":
            lista = [u for u in lista if u["activo"] and u["activado_por_admin"]]
        elif filtro_estado == "Inactivos":
            lista = [u for u in lista if not u["activo"] and u["activado_por_admin"]]
        elif filtro_estado == "Pendientes":
            lista = [u for u in lista if not u["activado_por_admin"]]
        if filtro_plan != "Todos":
            lista = [u for u in lista if u["plan"] == filtro_plan]
        if buscar:
            buscar_l = buscar.lower()
            lista = [u for u in lista if buscar_l in u["nombre"].lower()
                     or buscar_l in u["email"].lower()
                     or buscar_l in u.get("empresa","").lower()]

        st.caption(f"Mostrando {len(lista)} de {len(usuarios)} usuarios")
        st.divider()

        for u in lista:
            # Estado del badge
            if not u["activado_por_admin"]:
                badge = '<span class="badge-pendiente">⏳ Pendiente</span>'
            elif u["activo"]:
                badge = '<span class="badge-activo">✅ Activo</span>'
            else:
                badge = '<span class="badge-inactivo">🔴 Inactivo</span>'

            plan_badge = f'<span class="badge-plan">{PLANES.get(u["plan"],{}).get("nombre", u["plan"])}</span>'
            demo_tag   = " 🎯" if u.get("es_demo") else ""

            with st.expander(
                f"{u['nombre']}{demo_tag} · {u['email']} · {u['empresa'] or '—'}",
                expanded=False
            ):
                col_info, col_acciones = st.columns([3, 2])

                with col_info:
                    st.markdown(f"""
                    {badge} {plan_badge}
                    <br><br>
                    <table style="font-size:.9rem;width:100%">
                        <tr><td style="color:#6B7280;width:140px">Nombre</td><td><b>{u['nombre']}</b></td></tr>
                        <tr><td style="color:#6B7280">Correo</td><td>{u['email']}</td></tr>
                        <tr><td style="color:#6B7280">Empresa</td><td>{u.get('empresa') or '—'}</td></tr>
                        <tr><td style="color:#6B7280">Teléfono</td><td>{u.get('telefono') or '—'}</td></tr>
                        <tr><td style="color:#6B7280">Registro</td><td>{u['fecha_registro']}</td></tr>
                        <tr><td style="color:#6B7280">Docs generados</td><td>{u['documentos_usados']}</td></tr>
                    </table>
                    """, unsafe_allow_html=True)

                with col_acciones:
                    st.markdown("**Acciones**")

                    # Activar / Desactivar
                    if not u["activado_por_admin"]:
                        if st.button("✅ Activar cuenta", key=f"act_{u['email']}",
                                     type="primary", use_container_width=True):
                            activar_usuario(u["email"])
                            st.success(f"✅ {u['nombre']} activado.")
                            st.rerun()
                    elif u["activo"]:
                        if st.button("🔴 Desactivar", key=f"des_{u['email']}",
                                     use_container_width=True):
                            desactivar_usuario(u["email"])
                            st.warning(f"Cuenta de {u['nombre']} desactivada.")
                            st.rerun()
                    else:
                        if st.button("✅ Reactivar", key=f"react_{u['email']}",
                                     type="primary", use_container_width=True):
                            activar_usuario(u["email"])
                            st.success(f"✅ {u['nombre']} reactivado.")
                            st.rerun()

                    st.markdown("**Cambiar plan**")
                    nuevo_plan = st.selectbox(
                        "Plan",
                        options=list(PLANES.keys()),
                        index=list(PLANES.keys()).index(u["plan"]),
                        format_func=lambda x: PLANES[x]["nombre"],
                        key=f"plan_{u['email']}",
                        label_visibility="collapsed",
                    )
                    if st.button("Guardar plan", key=f"gplan_{u['email']}",
                                 use_container_width=True):
                        if cambiar_plan(u["email"], nuevo_plan):
                            st.success(f"Plan actualizado a {PLANES[nuevo_plan]['nombre']}.")
                            st.rerun()

                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.popover("🗑️ Eliminar usuario", use_container_width=True):
                        st.warning(f"¿Eliminar permanentemente a **{u['nombre']}**?")
                        if st.button("Sí, eliminar", key=f"del_{u['email']}",
                                     type="primary", use_container_width=True):
                            eliminar_usuario(u["email"])
                            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: PENDIENTES DE ACTIVACIÓN
# ══════════════════════════════════════════════════════════════════════════════
with tab_pendientes:
    pendientes = [u for u in listar_usuarios() if not u["activado_por_admin"]]

    if not pendientes:
        st.success("✅ No hay usuarios pendientes de activación.")
    else:
        st.info(f"⏳ **{len(pendientes)} usuario(s)** esperando que los actives para poder ingresar.")
        st.divider()

        # Activar todos de una vez
        if len(pendientes) > 1:
            if st.button(f"✅ Activar todos ({len(pendientes)} usuarios)",
                         type="primary"):
                for u in pendientes:
                    activar_usuario(u["email"])
                st.success(f"✅ {len(pendientes)} usuarios activados.")
                st.rerun()
            st.divider()

        for u in pendientes:
            c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 1.5, 1.5])
            with c1:
                st.markdown(f"**{u['nombre']}**  \n{u['email']}")
            with c2:
                st.caption(u.get("empresa") or "—")
            with c3:
                st.caption(f"📅 {u['fecha_registro']}")
            with c4:
                if st.button("✅ Activar", key=f"pact_{u['email']}",
                             type="primary", use_container_width=True):
                    activar_usuario(u["email"])
                    st.rerun()
            with c5:
                if st.button("❌ Rechazar", key=f"prej_{u['email']}",
                             use_container_width=True):
                    eliminar_usuario(u["email"])
                    st.rerun()

        st.divider()
        if st.button("🔄 Actualizar lista"):
            st.rerun()

# ── Cerrar sesión ────────────────────────────────────────────────────────────
st.divider()
if st.button("🚪 Cerrar sesión de administrador"):
    st.session_state.admin_autenticado = False
    st.session_state.admin_datos = None
    st.rerun()
