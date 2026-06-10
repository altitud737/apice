"""
Vistas para gestión de email en Apice
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from .mail_models import ZohoMailIntegration, EmailMessage, EmailDraft
from .mail_service import ZohoMailService
import json
from datetime import datetime


# Vista de configuración eliminada - solo el super admin puede configurar Zoho Mail
# desde el panel de administración


@login_required
def mail_connect(request):
    """
    Inicia el flujo OAuth de Zoho Mail
    """
    company = request.user.company
    
    try:
        integration = ZohoMailIntegration.objects.get(company=company)
    except ZohoMailIntegration.DoesNotExist:
        messages.error(request, 'Primero debes configurar las credenciales de Zoho Mail.')
        return redirect('apice:mail_settings')
    
    # Generar URL de autorización
    service = ZohoMailService(integration)
    redirect_uri = request.build_absolute_uri(reverse('apice:mail_callback'))
    auth_url = service.get_oauth_url(redirect_uri)
    
    return redirect(auth_url)


@login_required
def mail_callback(request):
    """
    Callback de OAuth de Zoho Mail
    """
    code = request.GET.get('code')
    error = request.GET.get('error')
    
    if error:
        messages.error(request, f'Error en autorización: {error}')
        return redirect('apice:mail_settings')
    
    if not code:
        messages.error(request, 'No se recibió código de autorización.')
        return redirect('apice:mail_settings')
    
    company = request.user.company
    
    try:
        integration = ZohoMailIntegration.objects.get(company=company)
        service = ZohoMailService(integration)
        
        # Intercambiar código por tokens
        redirect_uri = request.build_absolute_uri(reverse('apice:mail_callback'))
        service.exchange_code_for_token(code, redirect_uri)
        
        # Obtener detalles de la cuenta
        service.get_account_details()
        
        messages.success(request, '¡Zoho Mail conectado exitosamente!')
        return redirect('apice:mail_inbox')
        
    except Exception as e:
        messages.error(request, f'Error conectando Zoho Mail: {str(e)}')
        return redirect('apice:mail_settings')


@login_required
def mail_disconnect(request):
    """
    Desconecta Zoho Mail
    """
    if request.method == 'POST':
        company = request.user.company
        
        try:
            integration = ZohoMailIntegration.objects.get(company=company)
            integration.is_active = False
            integration.access_token = ''
            integration.refresh_token = ''
            integration.save()
            
            messages.success(request, 'Zoho Mail desconectado.')
        except ZohoMailIntegration.DoesNotExist:
            pass
    
    return redirect('apice:mail_settings')


@login_required
def mail_inbox(request):
    """
    Bandeja de entrada de emails
    """
    company = request.user.company
    
    try:
        integration = ZohoMailIntegration.objects.get(company=company)
    except ZohoMailIntegration.DoesNotExist:
        messages.warning(request, 'El email no está configurado. Contacta al administrador para la configuración.')
        return redirect('apice:dashboard')
    
    # Si existe pero no está activa (no se ha conectado con OAuth)
    if not integration.is_active:
        messages.info(request, 'Debes conectar tu cuenta de Zoho Mail.')
        return redirect('apice:mail_connect')
    
    # Obtener carpeta de la URL
    folder = request.GET.get('folder', 'inbox')
    page = int(request.GET.get('page', 1))
    limit = 20
    offset = (page - 1) * limit
    
    try:
        service = ZohoMailService(integration)
        
        # Obtener mensajes
        messages_data = service.get_messages(folder=folder, limit=limit, offset=offset)
        
        # Obtener carpetas
        folders = service.get_folders()
        
        context = {
            'integration': integration,
            'messages': messages_data,
            'folders': folders,
            'current_folder': folder,
            'page': page,
            'has_next': len(messages_data) == limit,
        }
        
        return render(request, 'apice/mail_inbox.html', context)
        
    except Exception as e:
        messages.error(request, f'Error cargando emails: {str(e)}')
        return redirect('apice:dashboard')


@login_required
def mail_view(request, message_id):
    """
    Ver detalles de un email
    """
    company = request.user.company
    
    try:
        integration = ZohoMailIntegration.objects.get(company=company, is_active=True)
        service = ZohoMailService(integration)
        
        # Obtener detalles del mensaje
        message = service.get_message_details(message_id)
        
        if message:
            # Marcar como leído
            service.mark_as_read(message_id)
            
            context = {
                'integration': integration,
                'message': message,
            }
            return render(request, 'apice/mail_view.html', context)
        else:
            messages.error(request, 'No se pudo cargar el email.')
            return redirect('apice:mail_inbox')
            
    except Exception as e:
        messages.error(request, f'Error cargando email: {str(e)}')
        return redirect('apice:mail_inbox')


@login_required
def mail_compose(request):
    """
    Componer nuevo email
    """
    company = request.user.company
    
    try:
        integration = ZohoMailIntegration.objects.get(company=company, is_active=True)
    except ZohoMailIntegration.DoesNotExist:
        messages.warning(request, 'Primero debes conectar tu cuenta de Zoho Mail.')
        return redirect('apice:mail_settings')
    
    if request.method == 'POST':
        to_addresses = request.POST.get('to')
        cc_addresses = request.POST.get('cc', '')
        bcc_addresses = request.POST.get('bcc', '')
        subject = request.POST.get('subject')
        body = request.POST.get('body')
        
        try:
            service = ZohoMailService(integration)
            
            # Enviar email
            service.send_email(
                to_addresses=to_addresses,
                subject=subject,
                body=body,
                cc_addresses=cc_addresses if cc_addresses else None,
                bcc_addresses=bcc_addresses if bcc_addresses else None
            )
            
            messages.success(request, 'Email enviado exitosamente.')
            return redirect('apice:mail_inbox')
            
        except Exception as e:
            messages.error(request, f'Error enviando email: {str(e)}')
    
    # Pre-cargar datos si viene de un lead o contacto
    to_email = request.GET.get('to', '')
    subject = request.GET.get('subject', '')
    
    context = {
        'integration': integration,
        'to_email': to_email,
        'subject': subject,
    }
    return render(request, 'apice/mail_compose.html', context)


@login_required
@require_http_methods(["POST"])
def mail_delete(request, message_id):
    """
    Eliminar un email
    """
    company = request.user.company
    
    try:
        integration = ZohoMailIntegration.objects.get(company=company, is_active=True)
        service = ZohoMailService(integration)
        
        if service.delete_message(message_id):
            messages.success(request, 'Email eliminado.')
        else:
            messages.error(request, 'No se pudo eliminar el email.')
            
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    
    return redirect('apice:mail_inbox')


@login_required
def mail_status(request):
    """
    Estado de la integración de Zoho Mail (API endpoint)
    """
    company = request.user.company
    
    try:
        integration = ZohoMailIntegration.objects.get(company=company)
        
        data = {
            'is_connected': integration.is_active,
            'email': integration.email_address,
            'last_sync': integration.last_sync.isoformat() if integration.last_sync else None,
            'token_valid': integration.is_token_valid,
        }
        
        return JsonResponse(data)
        
    except ZohoMailIntegration.DoesNotExist:
        return JsonResponse({
            'is_connected': False,
            'email': None,
            'last_sync': None,
            'token_valid': False,
        })
