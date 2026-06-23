"""
Servicio para integración con Zoho Mail API
Maneja autenticación OAuth, lectura y envío de emails
"""
import requests
import json
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class ZohoMailService:
    """
    Servicio para interactuar con Zoho Mail API
    """
    
    def __init__(self, integration):
        """
        Args:
            integration: Instancia de ZohoMailIntegration
        """
        self.integration = integration
        self.base_url = integration.api_base_url
        self.region = integration.region
    
    def get_oauth_url(self, redirect_uri):
        """
        Genera URL para OAuth de Zoho Mail
        
        Args:
            redirect_uri: URL de callback después de autorización
        
        Returns:
            str: URL de autorización
        """
        auth_url = f"https://accounts.zoho.{self.region}/oauth/v2/auth"
        params = {
            'client_id': self.integration.client_id,
            'response_type': 'code',
            'scope': 'ZohoMail.messages.ALL,ZohoMail.folders.ALL,ZohoMail.accounts.READ',
            'redirect_uri': redirect_uri,
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{query_string}"
    
    def exchange_code_for_token(self, code, redirect_uri):
        """
        Intercambia código de autorización por tokens
        
        Args:
            code: Código de autorización de OAuth
            redirect_uri: URL de callback
        
        Returns:
            dict: Tokens y metadata
        """
        try:
            token_url = f"https://accounts.zoho.{self.region}/oauth/v2/token"
            
            data = {
                'client_id': self.integration.client_id,
                'client_secret': self.integration.client_secret,
                'code': code,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            }
            
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Guardar tokens
            self.integration.access_token = token_data.get('access_token')
            self.integration.refresh_token = token_data.get('refresh_token')
            
            # Calcular expiración
            expires_in = token_data.get('expires_in', 3600)
            self.integration.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
            
            self.integration.is_active = True
            self.integration.save()
            
            logger.info(f"Tokens obtenidos para {self.integration.company.name}")
            return token_data
            
        except Exception as e:
            logger.error(f"Error intercambiando código por token: {e}")
            raise
    
    def refresh_access_token(self):
        """
        Refresca el access token usando el refresh token
        
        Returns:
            bool: True si se refrescó exitosamente
        """
        try:
            token_url = f"https://accounts.zoho.{self.region}/oauth/v2/token"
            
            data = {
                'client_id': self.integration.client_id,
                'client_secret': self.integration.client_secret,
                'refresh_token': self.integration.refresh_token,
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Actualizar access token
            self.integration.access_token = token_data.get('access_token')
            
            # Calcular nueva expiración
            expires_in = token_data.get('expires_in', 3600)
            self.integration.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
            
            self.integration.save()
            
            logger.info(f"Token refrescado para {self.integration.company.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error refrescando token: {e}")
            return False
    
    def _get_valid_token(self):
        """
        Obtiene un token válido, refrescándolo si es necesario
        
        Returns:
            str: Access token válido
        """
        if not self.integration.is_token_valid:
            self.refresh_access_token()
        
        return self.integration.access_token
    
    def _make_request(self, method, endpoint, **kwargs):
        """
        Hace una petición a la API de Zoho Mail
        
        Args:
            method: GET, POST, PUT, DELETE
            endpoint: Endpoint de la API
            **kwargs: Argumentos adicionales para requests
        
        Returns:
            dict: Respuesta de la API
        """
        token = self._get_valid_token()
        
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f'Zoho-oauthtoken {token}'
        
        url = f"{self.base_url}/{endpoint}"
        
        response = requests.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        
        return response.json()
    
    def get_account_details(self):
        """
        Obtiene detalles de la cuenta de Zoho Mail
        
        Returns:
            dict: Información de la cuenta
        """
        try:
            data = self._make_request('GET', 'accounts')
            
            if data.get('status', {}).get('code') == 200:
                accounts = data.get('data', [])
                if accounts:
                    account = accounts[0]
                    
                    # Guardar account_id
                    self.integration.account_id = account.get('accountId')
                    self.integration.save()
                    
                    return account
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo detalles de cuenta: {e}")
            return None
    
    def get_folders(self):
        """
        Obtiene las carpetas de la cuenta
        
        Returns:
            list: Lista de carpetas
        """
        try:
            account_id = self.integration.account_id
            endpoint = f'accounts/{account_id}/folders'
            
            data = self._make_request('GET', endpoint)
            
            if data.get('status', {}).get('code') == 200:
                return data.get('data', [])
            
            return []
            
        except Exception as e:
            logger.error(f"Error obteniendo carpetas: {e}")
            return []
    
    def get_messages(self, folder='inbox', limit=50, offset=0):
        """
        Obtiene mensajes de una carpeta
        
        Args:
            folder: Nombre de la carpeta (inbox, sent, drafts, etc.)
            limit: Cantidad de mensajes a obtener
            offset: Offset para paginación
        
        Returns:
            list: Lista de mensajes
        """
        try:
            account_id = self.integration.account_id
            endpoint = f'accounts/{account_id}/messages/view'
            
            params = {
                'foldername': folder,
                'limit': limit,
                'start': offset
            }
            
            data = self._make_request('GET', endpoint, params=params)
            
            if data.get('status', {}).get('code') == 200:
                return data.get('data', [])
            
            return []
            
        except Exception as e:
            logger.error(f"Error obteniendo mensajes: {e}")
            return []
    
    def get_message_details(self, message_id):
        """
        Obtiene detalles completos de un mensaje
        
        Args:
            message_id: ID del mensaje
        
        Returns:
            dict: Detalles del mensaje
        """
        try:
            account_id = self.integration.account_id
            endpoint = f'accounts/{account_id}/messages/{message_id}'
            
            data = self._make_request('GET', endpoint)
            
            if data.get('status', {}).get('code') == 200:
                return data.get('data')
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo detalles de mensaje: {e}")
            return None
    
    def send_email(self, to_addresses, subject, body, cc_addresses=None, bcc_addresses=None, from_address=None):
        """
        Envía un email
        
        Args:
            to_addresses: Lista de destinatarios o string separado por comas
            subject: Asunto del email
            body: Cuerpo del email (HTML)
            cc_addresses: Lista de CC (opcional)
            bcc_addresses: Lista de BCC (opcional)
            from_address: Email del remitente (opcional, usa el de la integración)
        
        Returns:
            dict: Respuesta de la API
        """
        try:
            account_id = self.integration.account_id
            endpoint = f'accounts/{account_id}/messages'
            
            # Preparar destinatarios
            if isinstance(to_addresses, str):
                to_addresses = [addr.strip() for addr in to_addresses.split(',')]
            
            to_list = [{'address': addr} for addr in to_addresses]
            
            # Preparar CC
            cc_list = []
            if cc_addresses:
                if isinstance(cc_addresses, str):
                    cc_addresses = [addr.strip() for addr in cc_addresses.split(',')]
                cc_list = [{'address': addr} for addr in cc_addresses]
            
            # Preparar BCC
            bcc_list = []
            if bcc_addresses:
                if isinstance(bcc_addresses, str):
                    bcc_addresses = [addr.strip() for addr in bcc_addresses.split(',')]
                bcc_list = [{'address': addr} for addr in bcc_addresses]
            
            # Construir payload
            payload = {
                'fromAddress': from_address or self.integration.email_address,
                'toAddress': ','.join(to_addresses),
                'subject': subject,
                'content': body,
                'mailFormat': 'html'
            }
            
            if cc_list:
                payload['ccAddress'] = ','.join([addr['address'] for addr in cc_list])
            
            if bcc_list:
                payload['bccAddress'] = ','.join([addr['address'] for addr in bcc_list])
            
            data = self._make_request('POST', endpoint, json=payload)
            
            logger.info(f"Email enviado desde {self.integration.company.name}")
            return data
            
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
            raise
    
    def mark_as_read(self, message_id):
        """
        Marca un mensaje como leído
        
        Args:
            message_id: ID del mensaje
        
        Returns:
            bool: True si se marcó exitosamente
        """
        try:
            account_id = self.integration.account_id
            endpoint = f'accounts/{account_id}/messages/{message_id}/read'
            
            self._make_request('PUT', endpoint)
            return True
            
        except Exception as e:
            logger.error(f"Error marcando mensaje como leído: {e}")
            return False
    
    def delete_message(self, message_id):
        """
        Elimina un mensaje
        
        Args:
            message_id: ID del mensaje
        
        Returns:
            bool: True si se eliminó exitosamente
        """
        try:
            account_id = self.integration.account_id
            endpoint = f'accounts/{account_id}/messages/{message_id}'
            
            self._make_request('DELETE', endpoint)
            return True
            
        except Exception as e:
            logger.error(f"Error eliminando mensaje: {e}")
            return False
