"""
Selector de empresa (Etapa 4 S4.4).

Se muestra cuando el usuario tiene múltiples empresas vinculadas.
También permite cambiar de empresa sin cerrar sesión.

Uso:
    from utils.selector_empresa import (
        cargar_empresas_del_usuario,
        seleccionar_empresa_activa,
        mostrar_selector_si_necesario,
        cambiar_empresa,
    )
"""

import streamlit as st

from services.empresa_service import empresa_service
from services.perfil_service import perfil_service


# ══════════════════════════════════════════════════════════════════════════════
# ESTADO EN SESIÓN
# ══════════════════════════════════════════════════════════════════════════════

def _get_perfil_id_actual() -> str:
    """Retorna el perfil_id del usuario logueado (según session_state)."""
    u = st.session_state.get("usuario") or {}
    # perfil_id se guarda al iniciar sesión (ver app.py después del login)
    return u.get("perfil_id") or ""


def cargar_empresas_del_usuario():
    """
    Carga las empresas del usuario actual y las guarda en session_state.
    Si el usuario tiene UNA sola empresa, se selecciona automáticamente.
    """
    perfil_id = _get_perfil_id_actual()
    if not perfil_id:
        return []

    empresas = empresa_service.listar_de_perfil(perfil_id)
    st.session_state["mis_empresas"] = empresas

    # Auto-seleccionar si es solo una
    if len(empresas) == 1:
        st.session_state["empresa_activa"] = empresas[0]
    elif len(empresas) == 0:
        st.session_state["empresa_activa"] = None

    return empresas


def cambiar_empresa(empresa_id: str) -> bool:
    """Cambia la empresa activa por otro id."""
    empresas = st.session_state.get("mis_empresas") or []
    for emp in empresas:
        if emp.get("id") == empresa_id:
            st.session_state["empresa_activa"] = emp
            return True
    return False


def obtener_empresa_activa() -> dict:
    """Retorna la empresa activa actual (dict con id, razon_social, rol, etc.)."""
    return st.session_state.get("empresa_activa") or {}


def obtener_rol_activo() -> str:
    """Retorna el código del rol del usuario en la empresa activa."""
    return obtener_empresa_activa().get("rol_codigo") or ""


# ══════════════════════════════════════════════════════════════════════════════
# UI: SELECTOR DE EMPRESA
# ══════════════════════════════════════════════════════════════════════════════

def mostrar_selector_si_necesario() -> bool:
    """
    Si el usuario tiene múltiples empresas y no ha elegido una,
    muestra el selector. Retorna True si el flujo debe pausarse
    (mostrando el selector), False si ya hay empresa activa.
    """
    # Cargar empresas si no están cargadas
    if "mis_empresas" not in st.session_state:
        cargar_empresas_del_usuario()

    empresas = st.session_state.get("mis_empresas") or []
    empresa_activa = st.session_state.get("empresa_activa")

    # Ya tiene empresa activa → seguir
    if empresa_activa:
        return False

    # No tiene ninguna empresa vinculada
    if not empresas:
        _mostrar_pantalla_sin_empresa()
        return True

    # Tiene múltiples empresas → mostrar selector
    _mostrar_selector_empresas(empresas)
    return True


def _mostrar_selector_empresas(empresas: list):
    """Renderiza el selector de empresa."""
    st.markdown("""
    <div style='background:linear-gradient(135deg,#1B3F6E,#2D6BE4);
        border-radius:16px;padding:2.2rem 2.5rem;margin-bottom:1.5rem;color:white'>
        <h1 style='margin:0 0 .5rem;font-size:1.6rem'>
            🏢 Selecciona la empresa con la que quieres trabajar</h1>
        <p style='margin:0;opacity:.9'>
            Tienes acceso a <b>%d empresas</b>. Elige una para continuar.</p>
    </div>
    """ % len(empresas), unsafe_allow_html=True)

    for emp in empresas:
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"""
                ### {emp.get('razon_social','Sin nombre')}
                **NIT:** {emp.get('nit','—')} · **Tu rol:** {emp.get('rol_nombre','—')} · **Plan:** {emp.get('plan','gratuito').capitalize()}
                """)
            with col2:
                if st.button("Ingresar →", key=f"btn_enter_{emp.get('id','')}",
                              type="primary", use_container_width=True):
                    st.session_state["empresa_activa"] = emp
                    st.rerun()
            st.divider()


def _mostrar_pantalla_sin_empresa():
    """Cuando el usuario no está vinculado a ninguna empresa activa."""
    st.warning("""
    ⚠️ **No estás vinculado a ninguna empresa activa.**

    Puede que:
    - No hayas sido invitado a ninguna empresa aún
    - Tu vínculo esté suspendido
    - Necesites crear tu propia empresa

    Contacta a un administrador o crea tu empresa a continuación.
    """)

    with st.expander("➕ Crear una nueva empresa"):
        st.markdown("Serás el administrador de esta empresa.")
        with st.form("crear_empresa_inicial"):
            razon = st.text_input("Razón social *", placeholder="Distribuciones XYZ SAS")
            nit = st.text_input("NIT (opcional)")
            ciudad = st.text_input("Ciudad")
            rep = st.text_input("Representante legal")

            enviado = st.form_submit_button("Crear empresa", type="primary")
            if enviado:
                if not razon.strip():
                    st.error("La razón social es obligatoria")
                else:
                    perfil_id = _get_perfil_id_actual()
                    ok, msg, emp_id = empresa_service.crear({
                        "razon_social": razon,
                        "nit": nit,
                        "ciudad": ciudad,
                        "representante_legal": rep,
                    }, creado_por_perfil_id=perfil_id)
                    if ok:
                        # Recargar empresas
                        cargar_empresas_del_usuario()
                        st.success(f"✅ Empresa creada: {razon}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")


# ══════════════════════════════════════════════════════════════════════════════
# UI: CAMBIAR EMPRESA (en sidebar)
# ══════════════════════════════════════════════════════════════════════════════

def mostrar_cambio_empresa_en_sidebar():
    """
    Muestra el nombre de la empresa activa y un botón para cambiar.
    Ideal para incluir en el sidebar de la app.
    """
    empresas = st.session_state.get("mis_empresas") or []
    activa = obtener_empresa_activa()

    if not activa:
        return

    st.markdown("---")
    st.caption("🏢 Empresa activa")
    st.markdown(f"**{activa.get('razon_social','—')}**")
    st.caption(f"Tu rol: {activa.get('rol_nombre','—')}")

    if len(empresas) > 1:
        if st.button("🔄 Cambiar empresa", use_container_width=True,
                      key="btn_cambiar_empresa"):
            st.session_state["empresa_activa"] = None
            st.rerun()
