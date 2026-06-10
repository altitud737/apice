"""
Vistas para la integración de WhatsApp Business API
"""
import json
import logging
import secrets
from datetime import datetime, timezone as dt_timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction

from .whatsapp_models import (
    WhatsAppIntegration, 
    WhatsAppMessage, 
    WhatsAppWebhookEvent
)
from .whatsapp_service import WhatsAppService, get_whatsapp_service
from .models import Lead, Contact

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """
    Endpoint para el webhook de WhatsApp Business API
    
    GET: Verificación del webhook por parte de Meta
    POST: Recepción de eventos (mensajes, estados, etc.)
    """
    
    if request.method == "GET":
        # Verificación del webhook
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        
        logger.info(f"Verificación de webhook - Mode: {mode}, Token: {token}")
        
        if mode == "subscribe":
            # Buscar una integración activa con este token
            try:
                integration = WhatsAppIntegration.objects.filter(
                    verify_token=token,
                    is_active=True
                ).first()
                
                if integration:
                    logger.info(f"Webhook verificado exitosamente para {integration.company.name}")
                    return HttpResponse(challenge, content_type="text/plain")
                else:
                    logger.warning(f"Token de verificación inválido: {token}")
                    return HttpResponse("Forbidden", status=403)
                    
            except Exception as e:
                logger.error(f"Error en verificación de webhook: {str(e)}")
                return HttpResponse("Error", status=500)
        
        return HttpResponse("Bad Request", status=400)
    
    elif request.method == "POST":
        # Recepción de eventos
        try:
            payload = json.loads(request.body.decode('utf-8'))
            logger.info(f"Webhook recibido: {json.dumps(payload, indent=2)}")
            
            # Procesar el payload
            process_whatsapp_webhook(payload)
            
            return JsonResponse({"status": "success"}, status=200)
            
        except json.JSONDecodeError as e:
            logger.error(f"Error al decodificar JSON del webhook: {str(e)}")
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            logger.error(f"Error procesando webhook de WhatsApp: {str(e)}", exc_info=True)
            return JsonResponse({"error": str(e)}, status=500)


def process_whatsapp_webhook(payload):
    """
    Procesa el payload del webhook de WhatsApp
    
    Args:
        payload: Diccionario con los datos del webhook
    """
    try:
        # Extraer información del payload
        entry = payload.get('entry', [])
        
        if not entry:
            logger.warning("Webhook sin entradas")
            return
        
        for entry_item in entry:
            changes = entry_item.get('changes', [])
            
            for change in changes:
                value = change.get('value', {})
                
                # Obtener metadata
                metadata = value.get('metadata', {})
                phone_number_id = metadata.get('phone_number_id')
                
                if not phone_number_id:
                    logger.warning("Webhook sin phone_number_id")
                    continue
                
                # Buscar la integración correspondiente
                try:
                    integration = WhatsAppIntegration.objects.get(
                        phone_number_id=phone_number_id,
                        is_active=True
                    )
                except WhatsAppIntegration.DoesNotExist:
                    logger.warning(f"No se encontró integración para phone_number_id: {phone_number_id}")
                    continue
                
                # Determinar el tipo de evento
                if 'messages' in value:
                    # Mensaje entrante
                    process_incoming_messages(integration, value)
                
                elif 'statuses' in value:
                    # Actualización de estado de mensaje
                    process_message_statuses(integration, value)
                
                # Guardar el evento completo
                event_type = 'message' if 'messages' in value else 'status' if 'statuses' in value else 'other'
                WhatsAppWebhookEvent.objects.create(
                    company=integration.company,
                    integration=integration,
                    event_type=event_type,
                    raw_payload=payload,
                    processed=True,
                    processed_at=timezone.now()
                )
                
    except Exception as e:
        logger.error(f"Error procesando webhook: {str(e)}", exc_info=True)


def process_incoming_messages(integration, value):
    """
    Procesa mensajes entrantes de WhatsApp
    
    Args:
        integration: Instancia de WhatsAppIntegration
        value: Diccionario con los datos del mensaje
    """
    messages = value.get('messages', [])
    contacts = value.get('contacts', [])
    
    # Crear un mapa de contactos por número
    contact_map = {}
    for contact_data in contacts:
        wa_id = contact_data.get('wa_id')
        profile = contact_data.get('profile', {})
        name = profile.get('name', '')
        contact_map[wa_id] = name
    
    for message_data in messages:
        try:
            message_id = message_data.get('id')
            from_number = message_data.get('from')
            timestamp = message_data.get('timestamp')
            message_type = message_data.get('type')
            
            # Verificar si el mensaje ya existe
            if WhatsAppMessage.objects.filter(message_id=message_id).exists():
                logger.info(f"Mensaje {message_id} ya existe, omitiendo")
                continue
            
            # Obtener el nombre del contacto
            contact_name = contact_map.get(from_number, '')
            
            # Extraer el contenido según el tipo de mensaje
            text_body = None
            media_id = None
            caption = None
            
            if message_type == 'text':
                text_body = message_data.get('text', {}).get('body', '')
            
            elif message_type == 'image':
                image_data = message_data.get('image', {})
                media_id = image_data.get('id')
                caption = image_data.get('caption', '')
                text_body = f"[Imagen] {caption}" if caption else "[Imagen]"
            
            elif message_type == 'document':
                doc_data = message_data.get('document', {})
                media_id = doc_data.get('id')
                filename = doc_data.get('filename', 'documento')
                caption = doc_data.get('caption', '')
                text_body = f"[Documento: {filename}] {caption}" if caption else f"[Documento: {filename}]"
            
            elif message_type == 'audio':
                audio_data = message_data.get('audio', {})
                media_id = audio_data.get('id')
                text_body = "[Audio]"
            
            elif message_type == 'video':
                video_data = message_data.get('video', {})
                media_id = video_data.get('id')
                caption = video_data.get('caption', '')
                text_body = f"[Video] {caption}" if caption else "[Video]"
            
            elif message_type == 'location':
                location_data = message_data.get('location', {})
                latitude = location_data.get('latitude')
                longitude = location_data.get('longitude')
                text_body = f"[Ubicación: {latitude}, {longitude}]"
            
            # Crear el mensaje en la base de datos
            with transaction.atomic():
                whatsapp_message = WhatsAppMessage.objects.create(
                    company=integration.company,
                    integration=integration,
                    message_id=message_id,
                    wamid=message_id,
                    from_number=from_number,
                    to_number=integration.phone_number or integration.phone_number_id,
                    contact_name=contact_name,
                    message_type=message_type,
                    direction='inbound',
                    status='received',
                    text_body=text_body,
                    media_id=media_id,
                    caption=caption,
                    timestamp=datetime.fromtimestamp(int(timestamp), tz=dt_timezone.utc),
                    raw_data=message_data
                )
                
                # Auto-crear lead o contacto si está configurado
                if integration.auto_create_leads:
                    create_lead_from_message(integration, whatsapp_message, from_number, contact_name, text_body)
                
                elif integration.auto_create_contacts:
                    create_contact_from_message(integration, whatsapp_message, from_number, contact_name)
                
                logger.info(f"Mensaje guardado: {message_id} de {from_number}")
                
        except Exception as e:
            logger.error(f"Error procesando mensaje individual: {str(e)}", exc_info=True)


def process_message_statuses(integration, value):
    """
    Procesa actualizaciones de estado de mensajes
    
    Args:
        integration: Instancia de WhatsAppIntegration
        value: Diccionario con los datos del estado
    """
    statuses = value.get('statuses', [])
    
    for status_data in statuses:
        try:
            message_id = status_data.get('id')
            status = status_data.get('status')  # sent, delivered, read, failed
            timestamp = status_data.get('timestamp')
            
            # Actualizar el mensaje en la base de datos
            WhatsAppMessage.objects.filter(
                message_id=message_id
            ).update(
                status=status
            )
            
            logger.info(f"Estado actualizado para mensaje {message_id}: {status}")
            
        except Exception as e:
            logger.error(f"Error actualizando estado de mensaje: {str(e)}", exc_info=True)


def create_lead_from_message(integration, whatsapp_message, phone_number, contact_name, message_text):
    """
    Crea un lead automáticamente desde un mensaje de WhatsApp
    
    Args:
        integration: Instancia de WhatsAppIntegration
        whatsapp_message: Instancia de WhatsAppMessage
        phone_number: Número de teléfono del contacto
        contact_name: Nombre del contacto
        message_text: Texto del mensaje
    """
    try:
        # Verificar si ya existe un lead o contacto con este número
        existing_lead = Lead.objects.filter(
            company=integration.company,
            phone=phone_number
        ).first()
        
        existing_contact = Contact.objects.filter(
            company=integration.company,
            phone=phone_number
        ).first()
        
        if existing_lead:
            # Asociar el mensaje al lead existente
            whatsapp_message.lead = existing_lead
            whatsapp_message.save()
            logger.info(f"Mensaje asociado a lead existente: {existing_lead.id}")
            return
        
        if existing_contact:
            # Asociar el mensaje al contacto existente
            whatsapp_message.contact = existing_contact
            whatsapp_message.save()
            logger.info(f"Mensaje asociado a contacto existente: {existing_contact.id}")
            return
        
        # Crear un nuevo lead
        lead = Lead.objects.create(
            company=integration.company,
            name=contact_name or f"WhatsApp {phone_number}",
            email=f"whatsapp_{phone_number}@placeholder.com",  # Email placeholder
            phone=phone_number,
            message=message_text or "Mensaje de WhatsApp",
            source='whatsapp',
            status='new',
            metadata={
                'whatsapp_message_id': whatsapp_message.message_id,
                'contact_name': contact_name
            }
        )
        
        # Asociar el mensaje al lead
        whatsapp_message.lead = lead
        whatsapp_message.save()
        
        logger.info(f"Lead creado automáticamente: {lead.id} para {phone_number}")
        
    except Exception as e:
        logger.error(f"Error creando lead desde mensaje: {str(e)}", exc_info=True)


def create_contact_from_message(integration, whatsapp_message, phone_number, contact_name):
    """
    Crea un contacto automáticamente desde un mensaje de WhatsApp
    
    Args:
        integration: Instancia de WhatsAppIntegration
        whatsapp_message: Instancia de WhatsAppMessage
        phone_number: Número de teléfono del contacto
        contact_name: Nombre del contacto
    """
    try:
        # Verificar si ya existe un contacto con este número
        existing_contact = Contact.objects.filter(
            company=integration.company,
            phone=phone_number
        ).first()
        
        if existing_contact:
            whatsapp_message.contact = existing_contact
            whatsapp_message.save()
            return
        
        # Crear un nuevo contacto
        contact = Contact.objects.create(
            company=integration.company,
            name=contact_name or f"WhatsApp {phone_number}",
            phone=phone_number,
            source='whatsapp',
            status='Nuevo'
        )
        
        # Asociar el mensaje al contacto
        whatsapp_message.contact = contact
        whatsapp_message.save()
        
        logger.info(f"Contacto creado automáticamente: {contact.id} para {phone_number}")
        
    except Exception as e:
        logger.error(f"Error creando contacto desde mensaje: {str(e)}", exc_info=True)


@login_required
def whatsapp_settings(request):
    """
    Vista para configurar la integración de WhatsApp
    """
    company = request.user.company
    
    # Obtener o crear la integración
    integration, created = WhatsAppIntegration.objects.get_or_create(
        company=company,
        defaults={
            'verify_token': secrets.token_urlsafe(32),
            'is_active': False
        }
    )
    
    if request.method == 'POST':
        # Actualizar la configuración
        integration.phone_number_id = request.POST.get('phone_number_id', '')
        integration.business_account_id = request.POST.get('business_account_id', '')
        integration.access_token = request.POST.get('access_token', '')
        integration.phone_number = request.POST.get('phone_number', '')
        integration.webhook_url = request.POST.get('webhook_url', '')
        integration.verify_token = request.POST.get('verify_token', integration.verify_token)
        integration.auto_create_leads = request.POST.get('auto_create_leads') == 'on'
        integration.auto_create_contacts = request.POST.get('auto_create_contacts') == 'on'
        integration.is_active = request.POST.get('is_active') == 'on'
        
        integration.save()
        
        messages.success(request, 'Configuración de WhatsApp guardada exitosamente')
        return redirect('apice:whatsapp:settings')
    
    context = {
        'integration': integration,
        'webhook_endpoint': request.build_absolute_uri('/webhook/whatsapp/')
    }
    
    return render(request, 'apice/whatsapp_settings.html', context)


@login_required
def whatsapp_messages(request):
    """
    Vista para ver todos los mensajes de WhatsApp
    """
    company = request.user.company
    
    try:
        integration = WhatsAppIntegration.objects.get(company=company, is_active=True)
        messages_list = WhatsAppMessage.objects.filter(
            company=company,
            integration=integration
        ).order_by('-timestamp')[:100]
        
    except WhatsAppIntegration.DoesNotExist:
        integration = None
        messages_list = []
    
    context = {
        'integration': integration,
        'messages': messages_list
    }
    
    return render(request, 'apice/whatsapp_messages.html', context)


@login_required
def send_whatsapp_message(request):
    """
    Vista para enviar un mensaje de WhatsApp (responde siempre JSON)
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        company = request.user.company
        service = get_whatsapp_service(company)
        
        if not service:
            return JsonResponse({
                'success': False,
                'error': 'No hay integración de WhatsApp activa. Configura WhatsApp primero.'
            })
        
        to_number = request.POST.get('to_number', '').strip()
        message_text = request.POST.get('message', '').strip()
        
        if not to_number or not message_text:
            return JsonResponse({
                'success': False,
                'error': 'Número y mensaje son requeridos'
            })
        
        # Enviar el mensaje
        result = service.send_text_message(to_number, message_text, user=request.user)
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error en send_whatsapp_message: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
