"""
Servicio para interactuar con WhatsApp Business API
"""
import requests
import logging
from django.utils import timezone
from .whatsapp_models import WhatsAppIntegration, WhatsAppMessage

logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    Servicio para enviar y gestionar mensajes de WhatsApp Business API
    """
    BASE_URL = "https://graph.facebook.com/v22.0"
    
    def __init__(self, integration):
        """
        Inicializa el servicio con una integración de WhatsApp
        
        Args:
            integration: Instancia de WhatsAppIntegration
        """
        self.integration = integration
        self.phone_number_id = integration.phone_number_id
        self.access_token = integration.access_token
    
    def send_text_message(self, to_number, message_text, user=None):
        """
        Envía un mensaje de texto a un número de WhatsApp
        
        Args:
            to_number: Número de teléfono del destinatario (formato: 5491112345678)
            message_text: Texto del mensaje
            user: Usuario que envía el mensaje (opcional)
        
        Returns:
            dict: Respuesta de la API con message_id o error
        """
        url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message_text
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Guardar el mensaje en la base de datos
            if 'messages' in data and len(data['messages']) > 0:
                message_id = data['messages'][0]['id']
                
                WhatsAppMessage.objects.create(
                    company=self.integration.company,
                    integration=self.integration,
                    message_id=message_id,
                    wamid=message_id,
                    from_number=self.integration.phone_number or self.phone_number_id,
                    to_number=to_number,
                    message_type='text',
                    direction='outbound',
                    status='sent',
                    text_body=message_text,
                    timestamp=timezone.now(),
                    sent_by=user,
                    raw_data=data
                )
                
                logger.info(f"Mensaje enviado exitosamente a {to_number}: {message_id}")
                return {
                    'success': True,
                    'message_id': message_id,
                    'data': data
                }
            
            return {
                'success': False,
                'error': 'No se recibió ID de mensaje en la respuesta'
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al enviar mensaje de WhatsApp: {str(e)}")
            error_message = str(e)
            
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_message = error_data.get('error', {}).get('message', str(e))
                except:
                    error_message = e.response.text or str(e)
            
            return {
                'success': False,
                'error': error_message
            }
    
    def send_template_message(self, to_number, template_name, language='es', components=None, user=None):
        """
        Envía un mensaje usando una plantilla aprobada de WhatsApp
        
        Args:
            to_number: Número de teléfono del destinatario
            template_name: Nombre de la plantilla aprobada
            language: Código de idioma (default: 'es')
            components: Lista de componentes de la plantilla (opcional)
            user: Usuario que envía el mensaje (opcional)
        
        Returns:
            dict: Respuesta de la API
        """
        url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        template_payload = {
            "name": template_name,
            "language": {
                "code": language
            }
        }
        
        if components:
            template_payload["components"] = components
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "template",
            "template": template_payload
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Guardar el mensaje en la base de datos
            if 'messages' in data and len(data['messages']) > 0:
                message_id = data['messages'][0]['id']
                
                WhatsAppMessage.objects.create(
                    company=self.integration.company,
                    integration=self.integration,
                    message_id=message_id,
                    wamid=message_id,
                    from_number=self.integration.phone_number or self.phone_number_id,
                    to_number=to_number,
                    message_type='template',
                    direction='outbound',
                    status='sent',
                    text_body=f"Template: {template_name}",
                    timestamp=timezone.now(),
                    sent_by=user,
                    raw_data=data
                )
                
                logger.info(f"Plantilla '{template_name}' enviada a {to_number}: {message_id}")
                return {
                    'success': True,
                    'message_id': message_id,
                    'data': data
                }
            
            return {
                'success': False,
                'error': 'No se recibió ID de mensaje en la respuesta'
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al enviar plantilla de WhatsApp: {str(e)}")
            error_message = str(e)
            
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_message = error_data.get('error', {}).get('message', str(e))
                except:
                    error_message = e.response.text or str(e)
            
            return {
                'success': False,
                'error': error_message
            }
    
    def mark_message_as_read(self, message_id):
        """
        Marca un mensaje como leído
        
        Args:
            message_id: ID del mensaje de WhatsApp
        
        Returns:
            dict: Respuesta de la API
        """
        url = f"{self.BASE_URL}/{self.phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            return {
                'success': True,
                'data': response.json()
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al marcar mensaje como leído: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_media_url(self, media_id):
        """
        Obtiene la URL de un archivo multimedia
        
        Args:
            media_id: ID del archivo multimedia
        
        Returns:
            str: URL del archivo o None si hay error
        """
        url = f"{self.BASE_URL}/{media_id}"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return data.get('url')
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener URL de media: {str(e)}")
            return None
    
    def download_media(self, media_url):
        """
        Descarga un archivo multimedia
        
        Args:
            media_url: URL del archivo multimedia
        
        Returns:
            bytes: Contenido del archivo o None si hay error
        """
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        try:
            response = requests.get(media_url, headers=headers)
            response.raise_for_status()
            
            return response.content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al descargar media: {str(e)}")
            return None


def get_whatsapp_service(company):
    """
    Obtiene una instancia del servicio de WhatsApp para una empresa
    
    Args:
        company: Instancia de Company
    
    Returns:
        WhatsAppService o None si no hay integración activa
    """
    try:
        integration = WhatsAppIntegration.objects.get(
            company=company,
            is_active=True
        )
        return WhatsAppService(integration)
    except WhatsAppIntegration.DoesNotExist:
        logger.warning(f"No hay integración de WhatsApp activa para {company}")
        return None
