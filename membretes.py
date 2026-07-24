"""
Envío de documentos por correo electrónico vía SMTP.
Compatible con Gmail (requiere contraseña de aplicación) y otros proveedores.

Configuración en Render → Environment Variables:
  SMTP_HOST     smtp.gmail.com
  SMTP_PORT     587
  SMTP_USER     tucorreo@gmail.com
  SMTP_PASS     contraseña_de_aplicacion_gmail
  SMTP_FROM     Gestor RH IA <tucorreo@gmail.com>
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path


def _config_smtp() -> dict:
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", 587)),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASS", ""),
        "from": os.getenv("SMTP_FROM", "Gestor RH IA <noreply@gestorrh.co>"),
    }


def smtp_configurado() -> bool:
    cfg = _config_smtp()
    return bool(cfg["user"] and cfg["password"])


def enviar_documentos(
    destinatario_email: str,
    destinatario_nombre: str,
    empresa_nombre: str,
    tipo_documento: str,
    rutas_pdf: list[str],
    correo_empresa: str = "",
) -> tuple[bool, str]:
    """
    Envía uno o varios PDFs por correo al empleado.

    Retorna (éxito, mensaje).
    """
    cfg = _config_smtp()
    if not cfg["user"] or not cfg["password"]:
        return False, (
            "SMTP no configurado. Agrega las variables de entorno "
            "SMTP_HOST, SMTP_USER y SMTP_PASS en Render → Environment."
        )

    remitente = correo_empresa if correo_empresa else cfg["from"]

    msg = MIMEMultipart()
    msg["From"]    = cfg["from"]
    msg["To"]      = destinatario_email
    msg["Subject"] = f"{tipo_documento} — {empresa_nombre}"
    msg["Reply-To"] = correo_empresa if correo_empresa else cfg["user"]

    cuerpo = f"""Estimado(a) {destinatario_nombre},

Adjunto encontrará su {tipo_documento.lower()} emitido por {empresa_nombre}.

Si tiene alguna inquietud sobre este documento, no dude en comunicarse con el área administrativa.

Cordialmente,
{empresa_nombre}

---
Documento generado automáticamente por Gestor RH IA.
Este correo fue enviado desde {remitente}.
"""
    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

    # Adjuntar PDFs
    for ruta in rutas_pdf:
        p = Path(ruta)
        if p.exists():
            with open(p, "rb") as f:
                parte = MIMEApplication(f.read(), Name=p.name)
            parte["Content-Disposition"] = f'attachment; filename="{p.name}"'
            msg.attach(parte)

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["from"], [destinatario_email], msg.as_string())
        return True, f"Correo enviado a {destinatario_email}"
    except smtplib.SMTPAuthenticationError:
        return False, (
            "Error de autenticación SMTP. Verifica usuario y contraseña de aplicación."
        )
    except smtplib.SMTPException as e:
        return False, f"Error SMTP: {e}"
    except Exception as e:
        return False, f"Error inesperado al enviar correo: {e}"


def instrucciones_gmail() -> str:
    return """
**Cómo configurar Gmail para envío automático:**

1. Entra a tu cuenta Google → Seguridad → Verificación en 2 pasos (actívala si no está)
2. En Seguridad → Contraseñas de aplicaciones → crea una para "Gestor RH IA"
3. Copia la contraseña de 16 caracteres que genera Google
4. En Render → tu servicio → Environment → agrega:
   - `SMTP_HOST` = `smtp.gmail.com`
   - `SMTP_PORT` = `587`
   - `SMTP_USER` = `tucorreo@gmail.com`
   - `SMTP_PASS` = `contraseña de 16 caracteres`
   - `SMTP_FROM` = `Gestor RH IA <tucorreo@gmail.com>`
5. Guarda y redespliega. Listo.
"""


# ══════════════════════════════════════════════════════════════════════════════
# CORREO DE ACTIVACIÓN DE CUENTA
# ══════════════════════════════════════════════════════════════════════════════

def enviar_correo_activacion(
    destinatario_email: str,
    destinatario_nombre: str,
    codigo: str,
    link_activacion: str,
) -> tuple[bool, str]:
    """
    Envía correo de bienvenida con token de 6 dígitos y link de activación.
    Retorna (éxito, mensaje).
    """
    cfg = _config_smtp()
    if not cfg["user"] or not cfg["password"]:
        return False, "SMTP no configurado. Configura SMTP_HOST, SMTP_USER y SMTP_PASS."

    msg = MIMEMultipart("alternative")
    msg["From"]    = cfg["from"]
    msg["To"]      = destinatario_email
    msg["Subject"] = "🎉 Activa tu cuenta en Gestor RH IA"

    # Versión texto plano (para clientes que no muestran HTML)
    texto = f"""Hola {destinatario_nombre},

¡Bienvenido(a) a Gestor RH IA!

Para activar tu cuenta usa cualquiera de estas dos opciones:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPCIÓN 1: Copia tu código de activación
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tu código de 6 dígitos:  {codigo}

Ingresa este código en la pantalla de "Activar cuenta".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPCIÓN 2: Haz clic en el enlace
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{link_activacion}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏱️  Este código expira en 24 horas.

Si no solicitaste esta cuenta, ignora este correo.

Saludos,
Equipo Gestor RH IA
"""

    # Versión HTML — más profesional
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#F3F4F6;font-family:-apple-system,Segoe UI,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:32px 12px">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0"
      style="background:white;border-radius:14px;overflow:hidden;
             box-shadow:0 4px 20px rgba(0,0,0,.08)">

      <!-- Header -->
      <tr><td style="background:linear-gradient(135deg,#1B3F6E,#2D6BE4);
        padding:32px 40px;text-align:center">
        <div style="color:white;font-size:1.6rem;font-weight:800">
          👋 ¡Bienvenido(a)!
        </div>
        <div style="color:rgba(255,255,255,.85);font-size:.95rem;margin-top:6px">
          Gestor RH IA
        </div>
      </td></tr>

      <!-- Cuerpo -->
      <tr><td style="padding:36px 40px">
        <p style="font-size:1.05rem;color:#111827;line-height:1.5;margin:0 0 20px">
          Hola <b>{destinatario_nombre}</b>,
        </p>
        <p style="color:#374151;line-height:1.6;margin:0 0 24px">
          Gracias por registrarte. Para empezar a usar la aplicación
          necesitas activar tu cuenta. Elige una de estas dos opciones:
        </p>

        <!-- Botón grande -->
        <table cellpadding="0" cellspacing="0" style="margin:0 auto">
          <tr><td align="center" style="background:#2D6BE4;border-radius:10px">
            <a href="{link_activacion}"
              style="display:inline-block;padding:14px 40px;color:white;
                     text-decoration:none;font-weight:700;font-size:1rem">
              ✅ Activar mi cuenta
            </a>
          </td></tr>
        </table>

        <!-- Divisor -->
        <div style="text-align:center;margin:32px 0 24px;color:#9CA3AF;font-size:.85rem">
          ─── o usa el código manualmente ───
        </div>

        <!-- Código -->
        <div style="background:#F0F9FF;border:2px dashed #93C5FD;
          border-radius:10px;padding:20px;text-align:center">
          <div style="color:#1E40AF;font-size:.8rem;font-weight:600;
            text-transform:uppercase;letter-spacing:.05em">
            Tu código de activación
          </div>
          <div style="color:#1B3F6E;font-size:2.2rem;font-weight:800;
            letter-spacing:.3em;margin-top:8px;font-family:monospace">
            {codigo}
          </div>
        </div>

        <p style="color:#6B7280;font-size:.85rem;line-height:1.5;
          margin:24px 0 0;text-align:center">
          ⏱️ Este código expira en <b>24 horas</b>.<br/>
          Si no solicitaste esta cuenta, ignora este correo.
        </p>
      </td></tr>

      <!-- Footer -->
      <tr><td style="background:#F9FAFB;padding:20px 40px;text-align:center;
        border-top:1px solid #E5E7EB">
        <div style="color:#6B7280;font-size:.8rem">
          © 2026 Gestor RH IA · Documentos laborales para PYMES colombianas
        </div>
      </td></tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""

    msg.attach(MIMEText(texto, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["user"], [destinatario_email], msg.as_string())
        return True, f"Correo de activación enviado a {destinatario_email}"
    except Exception as e:
        return False, f"Error enviando correo de activación: {e}"
