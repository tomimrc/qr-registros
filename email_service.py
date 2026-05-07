import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


logger = logging.getLogger(__name__)


def _smtp_from_email() -> str:
    return settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME or "kaffagencia@gmail.com"


def send_client_credentials_email(
    *,
    recipient_email: str,
    client_name: str,
    admin_name: str,
    temporary_password: str,
    dashboard_url: str,
    login_email: str,
) -> None:
    if not settings.EMAIL_NOTIFICATIONS_ENABLED:
        logger.info("Email notifications disabled; skipping client credentials email", extra={"recipient_email": recipient_email})
        return

    if not settings.SMTP_HOST:
        raise RuntimeError("SMTP_HOST no está configurado")

    message = EmailMessage()
    message["Subject"] = f"Acceso a Agenciakaff para {client_name}"
    message["From"] = _smtp_from_email()
    message["To"] = recipient_email

    text_body = (
        f"Hola {admin_name},\n\n"
        f"Tu cliente {client_name} ya fue creado en Agenciakaff.\n\n"
        f"Usuario: {login_email}\n"
        f"Contraseña temporal: {temporary_password}\n"
        f"Acceso al panel: {dashboard_url}\n\n"
        "Recomendación: ingresar, cambiar la contraseña temporal y comenzar a configurar el cliente.\n"
    )

    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #0f172a; line-height: 1.6;">
        <h2 style="margin-bottom: 12px;">Tu acceso a Agenciakaff está listo</h2>
        <p>Hola <strong>{admin_name}</strong>,</p>
        <p>El cliente <strong>{client_name}</strong> fue creado correctamente.</p>
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:16px; margin:20px 0;">
          <p style="margin:0 0 8px;"><strong>Usuario:</strong> {login_email}</p>
          <p style="margin:0 0 8px;"><strong>Contraseña temporal:</strong> {temporary_password}</p>
          <p style="margin:0;"><strong>Panel:</strong> <a href="{dashboard_url}">{dashboard_url}</a></p>
        </div>
        <p>Recomendación: entrar al panel y cambiar la contraseña temporal de inmediato.</p>
      </body>
    </html>
    """

    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS) as server:
        if settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL:
            server.starttls(context=context)
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(message)