"""
Email service para envío de emails transaccionales.
Soporta SMTP para desarrollo y producción.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("auth-svc.email")


class EmailService:
    """Servicio para envío de emails."""
    
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.from_email = settings.smtp_from_email
        self.from_name = settings.smtp_from_name
        self.frontend_url = settings.frontend_url
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Envía un email.
        
        Args:
            to_email: Email del destinatario
            subject: Asunto del email
            html_content: Contenido HTML del email
            text_content: Contenido en texto plano (fallback)
        
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        try:
            # Si no hay credenciales configuradas, solo logear
            if not self.smtp_user or not self.smtp_password:
                logger.warning(
                    "email_not_sent_no_credentials",
                    extra={
                        "to_email": to_email,
                        "subject": subject,
                        "reason": "SMTP credentials not configured"
                    }
                )
                logger.info(f"[DEV MODE] Email would be sent to {to_email}")
                logger.info(f"[DEV MODE] Subject: {subject}")
                logger.info(f"[DEV MODE] Content:\n{html_content}")
                return True
            
            # Crear mensaje
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            
            # Agregar contenido texto plano y HTML
            if text_content:
                part1 = MIMEText(text_content, "plain")
                message.attach(part1)
            
            part2 = MIMEText(html_content, "html")
            message.attach(part2)
            
            # Enviar email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to_email, message.as_string())
            
            logger.info(
                "email_sent",
                extra={
                    "to_email": to_email,
                    "subject": subject
                }
            )
            return True
            
        except Exception as e:
            logger.error(
                "email_send_failed",
                extra={
                    "to_email": to_email,
                    "subject": subject,
                    "error": str(e)
                }
            )
            return False
    
    async def send_verification_email(self, to_email: str, token: str, user_name: str) -> bool:
        """
        Envía email de verificación de cuenta.
        
        Args:
            to_email: Email del usuario
            token: Token de verificación
            user_name: Nombre del usuario
        
        Returns:
            True si se envió correctamente
        """
        verification_url = f"{self.frontend_url}/verify-email?token={token}"
        
        subject = "Verifica tu email - Mi Mascota"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
                <h1 style="color: #4CAF50; margin-bottom: 20px;">¡Bienvenido a Mi Mascota! 🐾</h1>
                
                <p>Hola <strong>{user_name}</strong>,</p>
                
                <p>Gracias por registrarte en Mi Mascota. Para completar tu registro, necesitamos verificar tu email.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                       style="background-color: #4CAF50; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Verificar mi email
                    </a>
                </div>
                
                <p>O copia y pega este enlace en tu navegador:</p>
                <p style="background-color: #e9ecef; padding: 10px; border-radius: 5px; word-break: break-all;">
                    {verification_url}
                </p>
                
                <p style="color: #666; font-size: 14px; margin-top: 30px;">
                    Este enlace expirará en 24 horas.<br>
                    Si no creaste esta cuenta, puedes ignorar este email.
                </p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="color: #999; font-size: 12px; text-align: center;">
                    Mi Mascota - Tu compañero en el cuidado de tus mascotas<br>
                    Este es un email automático, por favor no respondas a este mensaje.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        ¡Bienvenido a Mi Mascota!
        
        Hola {user_name},
        
        Gracias por registrarte. Para completar tu registro, verifica tu email haciendo click en el siguiente enlace:
        
        {verification_url}
        
        Este enlace expirará en 24 horas.
        
        Si no creaste esta cuenta, puedes ignorar este email.
        
        ---
        Mi Mascota
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)
    
    async def send_password_reset_email(self, to_email: str, token: str, user_name: str) -> bool:
        """
        Envía email de recuperación de contraseña.
        
        Args:
            to_email: Email del usuario
            token: Token de reset
            user_name: Nombre del usuario
        
        Returns:
            True si se envió correctamente
        """
        reset_url = f"{self.frontend_url}/reset-password?token={token}"
        
        subject = "Recupera tu contraseña - Mi Mascota"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
                <h1 style="color: #FF9800; margin-bottom: 20px;">Recuperación de Contraseña 🔐</h1>
                
                <p>Hola <strong>{user_name}</strong>,</p>
                
                <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background-color: #FF9800; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Restablecer contraseña
                    </a>
                </div>
                
                <p>O copia y pega este enlace en tu navegador:</p>
                <p style="background-color: #e9ecef; padding: 10px; border-radius: 5px; word-break: break-all;">
                    {reset_url}
                </p>
                
                <p style="color: #666; font-size: 14px; margin-top: 30px;">
                    Este enlace expirará en 1 hora.<br>
                    Si no solicitaste este cambio, ignora este email y tu contraseña permanecerá sin cambios.
                </p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="color: #999; font-size: 12px; text-align: center;">
                    Mi Mascota - Tu compañero en el cuidado de tus mascotas<br>
                    Este es un email automático, por favor no respondas a este mensaje.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Recuperación de Contraseña
        
        Hola {user_name},
        
        Recibimos una solicitud para restablecer tu contraseña. Haz click en el siguiente enlace:
        
        {reset_url}
        
        Este enlace expirará en 1 hora.
        
        Si no solicitaste este cambio, ignora este email.
        
        ---
        Mi Mascota
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)
    
    async def send_password_changed_email(self, to_email: str, user_name: str) -> bool:
        """
        Envía email de confirmación de cambio de contraseña.
        
        Args:
            to_email: Email del usuario
            user_name: Nombre del usuario
        
        Returns:
            True si se envió correctamente
        """
        subject = "Tu contraseña ha sido cambiada - Mi Mascota"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
                <h1 style="color: #4CAF50; margin-bottom: 20px;">Contraseña Actualizada ✓</h1>
                
                <p>Hola <strong>{user_name}</strong>,</p>
                
                <p>Tu contraseña ha sido cambiada exitosamente.</p>
                
                <p style="color: #666; font-size: 14px; margin-top: 30px;">
                    Si no realizaste este cambio, contacta inmediatamente a nuestro equipo de soporte.
                </p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="color: #999; font-size: 12px; text-align: center;">
                    Mi Mascota - Tu compañero en el cuidado de tus mascotas<br>
                    Este es un email automático, por favor no respondas a este mensaje.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Contraseña Actualizada
        
        Hola {user_name},
        
        Tu contraseña ha sido cambiada exitosamente.
        
        Si no realizaste este cambio, contacta inmediatamente a nuestro equipo de soporte.
        
        ---
        Mi Mascota
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)


# Singleton
email_service = EmailService()
