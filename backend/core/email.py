"""Envío minimalista de correos con la librería estándar de Python (smtplib)."""
import os
import smtplib
from email.message import EmailMessage


def send_email(to_email, subject, body_text):
    """Envía un correo o lo imprime en consola si no hay servidor SMTP configurado."""
    host = os.environ.get("SMTP_HOST")
    if not host:
        # ponytail: sin servidor SMTP configurado (desarrollo o pruebas), imprimir en log/consola
        print(f"\n[EMAIL a {to_email}] Asunto: {subject}\n{body_text}\n")
        return False

    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    sender = os.environ.get("SMTP_FROM", user or "noreply@restaurante.local")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(body_text)

    with smtplib.SMTP(host, port) as server:
        if os.environ.get("SMTP_STARTTLS", "1") != "0":
            server.starttls()
        if user and password:
            server.login(user, password)
        server.send_message(msg)
    return True
