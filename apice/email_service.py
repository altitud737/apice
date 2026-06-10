"""
Servicio de Email para Apice
Maneja el envío de emails transaccionales usando Zoho ZeptoMail
"""
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """
    Servicio centralizado para envío de emails transaccionales
    Soporta Zoho ZeptoMail en producción y console en desarrollo
    """
    
    @staticmethod
    def send_welcome_email(user):
        """
        Envía email de bienvenida al nuevo usuario
        """
        try:
            subject = f'¡Bienvenido a {user.company.name}!'
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = user.email
            
            # Texto plano
            text_content = f"""
            Hola {user.username},
            
            ¡Bienvenido a tu nuevo Apice!
            
            Tu cuenta ha sido creada exitosamente.
            Empresa: {user.company.name}
            API Key: {user.company.api_key}
            
            Puedes comenzar a usar Apice ahora mismo.
            
            Saludos,
            El equipo de Apice
            """
            
            # HTML (opcional)
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #10b981;">¡Bienvenido a {user.company.name}!</h2>
                    <p>Hola <strong>{user.username}</strong>,</p>
                    <p>Tu cuenta ha sido creada exitosamente en nuestro Apice.</p>
                    <div style="background-color: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <p style="margin: 5px 0;"><strong>Empresa:</strong> {user.company.name}</p>
                        <p style="margin: 5px 0;"><strong>API Key:</strong> <code>{user.company.api_key}</code></p>
                    </div>
                    <p>Puedes comenzar a usar Apice ahora mismo.</p>
                    <p style="margin-top: 30px;">Saludos,<br>El equipo de Apice</p>
                </div>
            </body>
            </html>
            """
            
            # Crear email con texto plano y HTML
            msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            logger.info(f"Email de bienvenida enviado a {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando email de bienvenida: {e}")
            return False
    
    @staticmethod
    def send_lead_notification(lead, user):
        """
        Notifica al usuario sobre un nuevo lead
        """
        try:
            subject = f'Nuevo Lead: {lead.name}'
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = user.email
            
            text_content = f"""
            Hola {user.username},
            
            Se ha creado un nuevo lead en tu apice:
            
            Nombre: {lead.name}
            Email: {lead.email}
            Teléfono: {lead.phone}
            Empresa: {lead.company_name}
            Fuente: {lead.get_source_display()}
            
            Revisa Apice para más detalles.
            
            Saludos,
            El equipo de Apice
            """
            
            send_mail(
                subject,
                text_content,
                from_email,
                [to_email],
                fail_silently=False,
            )
            
            logger.info(f"Notificación de lead enviada a {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando notificación de lead: {e}")
            return False
    
    @staticmethod
    def send_password_reset_email(user, reset_link):
        """
        Envía email de recuperación de contraseña
        """
        try:
            subject = 'Recuperación de Contraseña - Apice'
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = user.email
            
            text_content = f"""
            Hola {user.username},
            
            Has solicitado recuperar tu contraseña.
            
            Haz clic en el siguiente enlace para crear una nueva contraseña:
            {reset_link}
            
            Si no solicitaste este cambio, ignora este email.
            
            Saludos,
            El equipo de Apice
            """
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #10b981;">Recuperación de Contraseña</h2>
                    <p>Hola <strong>{user.username}</strong>,</p>
                    <p>Has solicitado recuperar tu contraseña.</p>
                    <div style="margin: 30px 0;">
                        <a href="{reset_link}" style="background-color: #10b981; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                            Crear Nueva Contraseña
                        </a>
                    </div>
                    <p style="color: #666; font-size: 14px;">Si no solicitaste este cambio, ignora este email.</p>
                    <p style="margin-top: 30px;">Saludos,<br>El equipo de Apice</p>
                </div>
            </body>
            </html>
            """
            
            msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            logger.info(f"Email de recuperación enviado a {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando email de recuperación: {e}")
            return False
    
    @staticmethod
    def send_custom_email(to_email, subject, message, html_message=None, from_email=None):
        """
        Envía un email personalizado
        
        Args:
            to_email: Email del destinatario
            subject: Asunto del email
            message: Mensaje en texto plano
            html_message: Mensaje en HTML (opcional)
            from_email: Email del remitente (opcional, usa DEFAULT_FROM_EMAIL si no se especifica)
        """
        try:
            if from_email is None:
                from_email = settings.DEFAULT_FROM_EMAIL
            
            if html_message:
                msg = EmailMultiAlternatives(subject, message, from_email, [to_email])
                msg.attach_alternative(html_message, "text/html")
                msg.send()
            else:
                send_mail(
                    subject,
                    message,
                    from_email,
                    [to_email],
                    fail_silently=False,
                )
            
            logger.info(f"Email personalizado enviado a {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando email personalizado: {e}")
            return False
    
    @staticmethod
    def send_bulk_email(recipients, subject, message, html_message=None):
        """
        Envía email a múltiples destinatarios
        
        Args:
            recipients: Lista de emails
            subject: Asunto del email
            message: Mensaje en texto plano
            html_message: Mensaje en HTML (opcional)
        """
        try:
            from_email = settings.DEFAULT_FROM_EMAIL
            
            if html_message:
                msg = EmailMultiAlternatives(subject, message, from_email, recipients)
                msg.attach_alternative(html_message, "text/html")
                msg.send()
            else:
                send_mail(
                    subject,
                    message,
                    from_email,
                    recipients,
                    fail_silently=False,
                )
            
            logger.info(f"Email masivo enviado a {len(recipients)} destinatarios")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando email masivo: {e}")
            return False
