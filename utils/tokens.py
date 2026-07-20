"""
Sistema de tokens de activación de cuenta — Gestor RH IA.
Genera un token de 6 dígitos + enlace de activación y lo envía por correo.
Los tokens expiran en 24 horas.
"""

import os
import random
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from utils.db import _db
from utils.correo import _config_smtp as _cfg, smtp_configurado

# ── Storage de tokens ────────────────────────────────────────────────────────
_TOKENS_JSON = Path("salidas/.tokens_activacion.json")

# Validez del token (24 horas)
TOKEN_VALIDEZ_HORAS = 24

# URL base de la app (para el link de activación)
def _url_app() -> str:
    return os.getenv("APP_URL", "https://rh-facil.onrender.com").rstrip("/")


# ══════════════════════════════════════════════════════════════════════════════
# GENERAR Y GUARDAR TOKEN
# ══════════════════════════════════════════════════════════════════════════════

def _generar_token_6_digitos() -> str:
    """Genera un código numérico de 6 dígitos (100000-999999)."""
    return f"{random.randint(100000, 999999)}"


def _generar_token_link() -> str:
    """Genera un token largo aleatorio para el enlace de activación."""
    return hashlib.sha256(os.urandom(32)).hexdigest()[:32]


def crear_token_activacion(email: str) -> dict:
    """
    Crea un token de activación para el usuario.
    Retorna: {codigo, token_link, url_activacion, expira_en}
    """
    email = email.strip().lower()
    codigo     = _generar_token_6_digitos()
    token_link = _generar_token_link()
    expira_en  = datetime.now() + timedelta(hours=TOKEN_VALIDEZ_HORAS)

    payload = {
        "email":      email,
        "codigo":     codigo,
        "token_link": token_link,
        "expira_en":  expira_en.isoformat(),
        "usado":      False,
        "creado_en":  datetime.now().isoformat(),
    }

    # Guardar en Supabase si disponible, sino JSON
    sb = _db()
    if sb:
        try:
            # Invalidar tokens anteriores del mismo email
            sb.table("tokens_activacion").update({"usado": True})\
                .eq("email", email).execute()
            # Crear el nuevo
            sb.table("tokens_activacion").insert(payload).execute()
        except Exception as e:
            print(f"Aviso: no se pudo guardar token en Supabase ({e}). Usando JSON.")
            _guardar_json(payload)
    else:
        _guardar_json(payload)

    url_activacion = f"{_url_app()}/?activar={token_link}"

    return {
        "codigo":         codigo,
        "token_link":     token_link,
        "url_activacion": url_activacion,
        "expira_en":      expira_en,
    }


def _guardar_json(payload: dict):
    _TOKENS_JSON.parent.mkdir(exist_ok=True)
    tokens = []
    if _TOKENS_JSON.exists():
        try:
            tokens = json.load(open(_TOKENS_JSON, encoding="utf-8"))
        except Exception:
            tokens = []
    # Invalidar tokens anteriores del mismo email
    for t in tokens:
        if t.get("email") == payload["email"]:
            t["usado"] = True
    tokens.append(payload)
    # Limpiar tokens usados de hace más de 7 días
    limite = (datetime.now() - timedelta(days=7)).isoformat()
    tokens = [t for t in tokens if t.get("creado_en", "") > limite or not t.get("usado")]
    with open(_TOKENS_JSON, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False, default=str)


# ══════════════════════════════════════════════════════════════════════════════
# VALIDAR TOKEN
# ══════════════════════════════════════════════════════════════════════════════

def validar_por_codigo(email: str, codigo: str) -> tuple[bool, str]:
    """Valida un código de 6 dígitos. Retorna (ok, mensaje)."""
    email = email.strip().lower()
    codigo = codigo.strip()
    if not codigo.isdigit() or len(codigo) != 6:
        return False, "El código debe tener 6 dígitos."
    return _buscar_y_validar(email=email, codigo=codigo)


def validar_por_link(token_link: str) -> tuple[bool, str, str]:
    """Valida un token de enlace. Retorna (ok, mensaje, email)."""
    if not token_link or len(token_link) < 20:
        return False, "Enlace de activación inválido.", ""
    ok, msg, email = _buscar_y_validar(token_link=token_link, retorna_email=True)
    return ok, msg, email


def _buscar_y_validar(email: str = "", codigo: str = "",
                        token_link: str = "", retorna_email: bool = False):
    """Busca y valida un token. Marca como usado si es válido."""
    sb = _db()
    token = None

    if sb:
        try:
            q = sb.table("tokens_activacion").select("*").eq("usado", False)
            if token_link:
                q = q.eq("token_link", token_link)
            else:
                q = q.eq("email", email).eq("codigo", codigo)
            r = q.order("creado_en", desc=True).limit(1).execute()
            token = (r.data or [None])[0]
        except Exception as e:
            print(f"Aviso: fallback a JSON ({e})")

    if not token and _TOKENS_JSON.exists():
        try:
            tokens = json.load(open(_TOKENS_JSON, encoding="utf-8"))
            candidatos = [t for t in tokens if not t.get("usado")]
            if token_link:
                token = next((t for t in candidatos if t.get("token_link") == token_link), None)
            else:
                token = next((t for t in candidatos
                              if t.get("email") == email and t.get("codigo") == codigo), None)
        except Exception:
            pass

    if not token:
        return (False, "Código incorrecto o expirado.", "") if retorna_email \
                else (False, "Código incorrecto o expirado.")

    # Verificar expiración
    try:
        expira = datetime.fromisoformat(str(token["expira_en"]).replace("Z",""))
        if datetime.now() > expira:
            return (False, "El código expiró. Solicita uno nuevo.", "") if retorna_email \
                    else (False, "El código expiró. Solicita uno nuevo.")
    except Exception:
        pass

    # Marcar como usado
    _marcar_usado(token.get("token_link"), token.get("email"))

    email_final = token.get("email", "")
    if retorna_email:
        return True, "Token válido.", email_final
    return True, "Token válido."


def _marcar_usado(token_link: str, email: str):
    """Marca el token como usado."""
    sb = _db()
    if sb:
        try:
            sb.table("tokens_activacion").update({"usado": True})\
                .eq("token_link", token_link).execute()
        except Exception:
            pass
    if _TOKENS_JSON.exists():
        try:
            tokens = json.load(open(_TOKENS_JSON, encoding="utf-8"))
            for t in tokens:
                if t.get("token_link") == token_link:
                    t["usado"] = True
            with open(_TOKENS_JSON, "w", encoding="utf-8") as f:
                json.dump(tokens, f, indent=2, ensure_ascii=False, default=str)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# ENVIAR CORREO DE ACTIVACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def enviar_correo_activacion(email: str, nombre: str,
                              codigo: str, url_activacion: str) -> tuple[bool, str]:
    """Envía correo con código de 6 dígitos y enlace de activación."""
    if not smtp_configurado():
        return False, (
            "SMTP no configurado. El administrador puede activarte manualmente. "
            f"Tu código es: {codigo}"
        )

    cfg = _cfg()
    asunto = "🚀 Activa tu cuenta en Gestor RH IA"

    html = f"""
    <div style="font-family:-apple-system,Arial,sans-serif;max-width:600px;
        margin:0 auto;background:#F8FAFC;padding:20px">

      <div style="background:linear-gradient(135deg,#1B3F6E,#2D6BE4);
          color:white;padding:32px 24px;border-radius:14px 14px 0 0;text-align:center">
        <h1 style="margin:0;font-size:1.5rem">Gestor RH IA</h1>
        <p style="margin:8px 0 0;opacity:.9;font-size:.95rem">
          Documentos laborales para PYMES colombianas
        </p>
      </div>

      <div style="background:white;padding:32px 24px;border-radius:0 0 14px 14px">
        <h2 style="color:#1B3F6E;font-size:1.2rem;margin:0 0 16px">
          ¡Bienvenido, {nombre.split()[0]}! 👋
        </h2>

        <p style="color:#374151;line-height:1.6;font-size:.95rem">
          Gracias por registrarte. Para activar tu cuenta y empezar a generar
          documentos laborales, tienes <b>dos opciones</b>:
        </p>

        <!-- OPCIÓN 1: Enlace directo -->
        <div style="background:#EFF6FF;border-left:4px solid #2D6BE4;
            padding:16px 20px;border-radius:8px;margin:20px 0">
          <p style="margin:0 0 12px;color:#1B3F6E;font-weight:600;font-size:.9rem">
            ✅ Opción 1 — Activación con un clic
          </p>
          <a href="{url_activacion}" style="display:inline-block;background:#2D6BE4;
              color:white;text-decoration:none;padding:12px 28px;border-radius:8px;
              font-weight:700;font-size:.95rem">
            🚀 Activar mi cuenta
          </a>
          <p style="margin:12px 0 0;color:#6B7280;font-size:.78rem">
            Si el botón no funciona, copia y pega este enlace en tu navegador:<br>
            <a href="{url_activacion}" style="color:#2D6BE4;word-break:break-all">
              {url_activacion}
            </a>
          </p>
        </div>

        <!-- OPCIÓN 2: Código de respaldo -->
        <div style="background:#F9FAFB;border:1px dashed #D1D5DB;
            padding:16px 20px;border-radius:8px;margin:20px 0;text-align:center">
          <p style="margin:0 0 8px;color:#6B7280;font-weight:600;font-size:.9rem">
            🔑 Opción 2 — Código de respaldo
          </p>
          <p style="margin:0 0 12px;color:#374151;font-size:.85rem">
            Si el enlace no funciona, ingresa este código en la pantalla de activación:
          </p>
          <div style="background:#1B3F6E;color:white;padding:16px 24px;
              border-radius:10px;font-size:2rem;font-weight:800;
              letter-spacing:.4rem;font-family:monospace;margin:12px 0">
            {codigo}
          </div>
          <p style="margin:8px 0 0;color:#9CA3AF;font-size:.75rem">
            Este código expira en 24 horas
          </p>
        </div>

        <div style="border-top:1px solid #E5E7EB;margin-top:24px;padding-top:16px">
          <p style="color:#6B7280;font-size:.8rem;line-height:1.5;margin:0">
            Si no te registraste en Gestor RH IA, ignora este correo.
            Nadie más puede acceder a tu cuenta sin este código.
          </p>
        </div>
      </div>

      <div style="text-align:center;padding:16px;color:#9CA3AF;font-size:.75rem">
        © 2026 Gestor RH IA · Medellín, Colombia<br>
        Este es un correo automático, por favor no respondas.
      </div>
    </div>
    """

    texto_plano = f"""
Bienvenido a Gestor RH IA, {nombre}!

Para activar tu cuenta tienes dos opciones:

OPCIÓN 1 — Enlace de activación (clic aquí):
{url_activacion}

OPCIÓN 2 — Código de 6 dígitos:
{codigo}

Ingresa el código en la pantalla de activación.
Este código expira en 24 horas.

Si no te registraste, ignora este correo.

© 2026 Gestor RH IA
"""

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"]    = cfg["from"]
        msg["To"]      = email
        msg.attach(MIMEText(texto_plano, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as srv:
            srv.starttls()
            srv.login(cfg["user"], cfg["password"])
            srv.sendmail(cfg["user"], [email], msg.as_string())

        return True, "Correo de activación enviado correctamente."
    except Exception as e:
        return False, f"Error enviando correo: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# FLUJO COMPLETO: crear + enviar + retornar info
# ══════════════════════════════════════════════════════════════════════════════

def enviar_activacion_completa(email: str, nombre: str) -> tuple[bool, str, dict]:
    """
    Flujo unificado: genera token + envía correo.
    Retorna (ok, mensaje, datos) donde datos incluye el código (para mostrarlo si SMTP falla).
    """
    datos = crear_token_activacion(email)
    ok_envio, msg_envio = enviar_correo_activacion(
        email=email,
        nombre=nombre,
        codigo=datos["codigo"],
        url_activacion=datos["url_activacion"],
    )
    return ok_envio, msg_envio, datos
