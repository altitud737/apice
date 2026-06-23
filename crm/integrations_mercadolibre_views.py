"""
Vistas para integración con MercadoLibre
"""
import json
import secrets
import logging

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from django.shortcuts import get_object_or_404

from .integrations_mercadolibre_models import (
    MercadoLibreOAuthState,
    MercadoLibreIntegration,
    MercadoLibreWebhookEvent,
    MercadoLibreReplyTemplate,
    MercadoLibreProduct,
    MercadoLibreQuestion,
    MercadoLibreMessage,
    MercadoLibreOrder,
    MercadoLibreCategory,
)
from .integrations_mercadolibre_services import (
    MercadoLibreOAuthService,
    MercadoLibreEventProcessor,
    MercadoLibreProductService,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OAuth Flow
# ---------------------------------------------------------------------------
@login_required
def mercadolibre_connect(request):
    """Inicia el flujo OAuth de MercadoLibre."""
    company = request.user.company
    if not company:
        messages.error(request, 'No tienes una empresa asignada.')
        return redirect('crm:integrations')

    existing = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()
    if existing:
        messages.info(request, 'Ya tienes una cuenta de MercadoLibre conectada.')
        return redirect('crm:integrations')

    state = secrets.token_urlsafe(32)
    
    # Guardar state en DB en lugar de session
    MercadoLibreOAuthState.cleanup_expired()
    MercadoLibreOAuthState.objects.create(
        state=state,
        user=request.user,
        company=company,
    )

    oauth = MercadoLibreOAuthService()
    auth_url = oauth.get_authorization_url(state=state)

    logger.info(f"User {request.user.id} (company={company.id}) iniciando OAuth ML")
    return redirect(auth_url)


def mercadolibre_callback(request):
    """Callback OAuth de MercadoLibre: intercambia code por tokens."""
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')

    if error:
        desc = request.GET.get('error_description', 'Error desconocido')
        logger.error(f"OAuth error: {error} - {desc}")
        return redirect('crm:integrations')

    if not code or not state:
        logger.error("Missing code or state in callback")
        return redirect('crm:integrations')

    # Validar state desde DB
    try:
        oauth_state = MercadoLibreOAuthState.objects.get(state=state)
        if not oauth_state.is_valid():
            logger.warning(f"Expired OAuth state: {state}")
            oauth_state.delete()
            return redirect('crm:integrations')
        
        user = oauth_state.user
        company = oauth_state.company
        oauth_state.delete()
    except MercadoLibreOAuthState.DoesNotExist:
        logger.warning(f"Invalid OAuth state: {state}")
        return redirect('crm:integrations')

    try:
        oauth = MercadoLibreOAuthService()
        token_data = oauth.exchange_code_for_token(code)
        user_info = oauth.get_user_info(token_data['access_token'])

        # Check if this ML account is already linked to another company
        existing = MercadoLibreIntegration.objects.filter(
            ml_user_id=token_data['user_id']
        ).first()
        if existing and existing.company_id != company.id:
            messages.error(request, 'Esta cuenta de MercadoLibre ya está vinculada a otra empresa.')
            return redirect('crm:integrations')

        integration, created = MercadoLibreIntegration.objects.update_or_create(
            company=company,
            ml_user_id=token_data['user_id'],
            defaults={
                'connected_by': user,
                'access_token': token_data['access_token'],
                'refresh_token': token_data['refresh_token'],
                'token_expires_at': token_data['token_expires_at'],
                'nickname': user_info.get('nickname', ''),
                'email': user_info.get('email', ''),
                'site_id': user_info.get('site_id', 'MLA'),
                'is_active': True,
            }
        )

        # Re-authenticate user so session is restored after external redirect
        auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        action = 'conectada' if created else 'actualizada'
        logger.info(f"ML integration {action}: company={company.id}, ml_user={token_data['user_id']}")
        messages.success(request, f'¡Cuenta de MercadoLibre {action}! Usuario: {user_info.get("nickname")}')

    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        messages.error(request, f'Error al conectar con MercadoLibre: {str(e)}')

    return redirect('crm:integrations')


@login_required
def mercadolibre_disconnect(request):
    """Desconecta la integración de MercadoLibre."""
    if request.method != 'POST':
        return redirect('crm:integrations')

    company = request.user.company
    try:
        integration = MercadoLibreIntegration.objects.get(company=company, is_active=True)
        integration.is_active = False
        integration.save()
        logger.info(f"ML disconnected: company={company.id}")
        messages.success(request, 'Integración de MercadoLibre desconectada.')
    except MercadoLibreIntegration.DoesNotExist:
        messages.warning(request, 'No tienes una integración activa de MercadoLibre.')

    return redirect('crm:integrations')


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------
@csrf_exempt
@require_http_methods(["POST"])
def mercadolibre_webhook(request):
    """
    Webhook endpoint para MercadoLibre.
    
    POST /webhooks/mercadolibre/
    
    Payload: {"topic": "orders_v2", "user_id": 123, "resource": "/orders/456", ...}
    
    MUST return 200 quickly to avoid ML retries.
    """
    try:
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error("ML webhook: invalid JSON")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        topic = payload.get('topic', '')
        ml_user_id = str(payload.get('user_id', ''))
        resource = payload.get('resource', '')
        application_id = str(payload.get('application_id', ''))
        attempts = payload.get('attempts', 1)
        sent_date = payload.get('sent', '')

        if not all([topic, ml_user_id, resource]):
            logger.error(f"ML webhook: missing fields → {payload}")
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        logger.info(f"ML webhook: topic={topic}, user_id={ml_user_id}, resource={resource}")

        # Find integration
        try:
            integration = MercadoLibreIntegration.objects.get(
                ml_user_id=ml_user_id, is_active=True
            )
        except MercadoLibreIntegration.DoesNotExist:
            logger.warning(f"ML webhook: no integration for user {ml_user_id}")
            return JsonResponse({'status': 'ignored', 'reason': 'no_integration'})

        # Store webhook event
        webhook_event = MercadoLibreWebhookEvent.objects.create(
            integration=integration,
            topic=topic,
            resource=resource,
            ml_user_id=ml_user_id,
            application_id=application_id,
            attempts=attempts,
            raw_payload=payload,
            status='pending',
        )

        # Process synchronously (replace with Celery task in production)
        try:
            processor = MercadoLibreEventProcessor(integration)

            if topic in ('orders_v2', 'orders'):
                processor.process_order(resource)
            elif topic == 'questions':
                processor.process_question(resource)
            elif topic == 'messages':
                processor.process_message(resource)
            elif topic == 'items':
                processor.process_item(resource)
            elif topic == 'shipments':
                processor.process_shipment(resource)
            else:
                logger.info(f"ML webhook: unhandled topic '{topic}'")
                webhook_event.status = 'ignored'
                webhook_event.save()
                return JsonResponse({'status': 'ignored', 'reason': 'unhandled_topic'})

            webhook_event.status = 'processed'
            webhook_event.processed_at = timezone.now()
            webhook_event.save()
            logger.info(f"ML webhook event {webhook_event.id} processed")

        except Exception as e:
            webhook_event.status = 'failed'
            webhook_event.error_message = str(e)[:1000]
            webhook_event.retry_count += 1
            webhook_event.save()
            logger.error(f"ML webhook event {webhook_event.id} failed: {e}", exc_info=True)

        return JsonResponse({'status': 'received', 'event_id': webhook_event.id})

    except Exception as e:
        logger.error(f"ML webhook unexpected error: {e}", exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)


# ---------------------------------------------------------------------------
# Status page
# ---------------------------------------------------------------------------
@login_required
def mercadolibre_status(request):
    """Muestra el estado de la integración de MercadoLibre."""
    company = request.user.company

    try:
        integration = MercadoLibreIntegration.objects.get(company=company, is_active=True)
        recent_events = integration.webhook_events.order_by('-received_at')[:20]
        orders_count = integration.orders.count()
        questions_count = integration.questions.count()
        products_count = integration.products.count()
        
        # Get actual lists for display
        products_list = integration.products.order_by('-created_at')[:5]
        questions_list = integration.questions.order_by('-date_created')[:5]

        context = {
            'integration': integration,
            'is_connected': True,
            'token_expired': integration.is_token_expired(),
            'needs_refresh': integration.needs_refresh(),
            'recent_events': recent_events,
            'orders_count': orders_count,
            'questions_count': questions_count,
            'products_count': products_count,
            'products_list': products_list,
            'questions_list': questions_list,
        }
    except MercadoLibreIntegration.DoesNotExist:
        context = {'is_connected': False}

    return render(request, 'crm/integrations/mercadolibre_status.html', context)


# ---------------------------------------------------------------------------
# Auto-Reply Templates CRUD
# ---------------------------------------------------------------------------
@login_required
def autoreply_templates_list(request):
    """Lista todas las plantillas de respuesta automática."""
    company = request.user.company
    templates = MercadoLibreReplyTemplate.objects.filter(company=company)

    # Check if ML is connected
    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    context = {
        'templates': templates,
        'is_connected': integration is not None,
    }
    return render(request, 'crm/integrations/mercadolibre_autoreply_list.html', context)


@login_required
def autoreply_template_create(request):
    """Crea una nueva plantilla de respuesta automática."""
    company = request.user.company

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        keywords_raw = request.POST.get('keywords', '').strip()
        response_text = request.POST.get('response_text', '').strip()
        priority = request.POST.get('priority', '0')
        is_active = request.POST.get('is_active') == 'on'

        if not name or not response_text:
            messages.error(request, 'Nombre y texto de respuesta son obligatorios.')
            return render(request, 'crm/integrations/mercadolibre_autoreply_form.html', {
                'form_data': request.POST,
            })

        # Parse keywords: comma-separated
        keywords = [k.strip().lower() for k in keywords_raw.split(',') if k.strip()]

        if not keywords:
            messages.error(request, 'Debés agregar al menos una palabra clave.')
            return render(request, 'crm/integrations/mercadolibre_autoreply_form.html', {
                'form_data': request.POST,
            })

        try:
            priority_int = int(priority)
        except ValueError:
            priority_int = 0

        MercadoLibreReplyTemplate.objects.create(
            company=company,
            created_by=request.user,
            name=name,
            keywords=keywords,
            response_text=response_text,
            priority=priority_int,
            is_active=is_active,
        )

        messages.success(request, f'Plantilla "{name}" creada correctamente.')
        return redirect('crm:mercadolibre:autoreply_list')

    return render(request, 'crm/integrations/mercadolibre_autoreply_form.html', {})


@login_required
def autoreply_template_edit(request, template_id):
    """Edita una plantilla de respuesta automática existente."""
    company = request.user.company
    template = get_object_or_404(
        MercadoLibreReplyTemplate, id=template_id, company=company
    )

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        keywords_raw = request.POST.get('keywords', '').strip()
        response_text = request.POST.get('response_text', '').strip()
        priority = request.POST.get('priority', '0')
        is_active = request.POST.get('is_active') == 'on'

        if not name or not response_text:
            messages.error(request, 'Nombre y texto de respuesta son obligatorios.')
            return render(request, 'crm/integrations/mercadolibre_autoreply_form.html', {
                'template': template,
                'form_data': request.POST,
            })

        keywords = [k.strip().lower() for k in keywords_raw.split(',') if k.strip()]

        if not keywords:
            messages.error(request, 'Debés agregar al menos una palabra clave.')
            return render(request, 'crm/integrations/mercadolibre_autoreply_form.html', {
                'template': template,
                'form_data': request.POST,
            })

        try:
            priority_int = int(priority)
        except ValueError:
            priority_int = 0

        template.name = name
        template.keywords = keywords
        template.response_text = response_text
        template.priority = priority_int
        template.is_active = is_active
        template.save()

        messages.success(request, f'Plantilla "{name}" actualizada correctamente.')
        return redirect('crm:mercadolibre:autoreply_list')

    return render(request, 'crm/integrations/mercadolibre_autoreply_form.html', {
        'template': template,
    })


@login_required
def autoreply_template_delete(request, template_id):
    """Elimina una plantilla de respuesta automática."""
    company = request.user.company
    template = get_object_or_404(
        MercadoLibreReplyTemplate, id=template_id, company=company
    )

    if request.method == 'POST':
        name = template.name
        template.delete()
        messages.success(request, f'Plantilla "{name}" eliminada.')
        return redirect('crm:mercadolibre:autoreply_list')

    return redirect('crm:mercadolibre:autoreply_list')


@login_required
def autoreply_template_toggle(request, template_id):
    """Activa/desactiva una plantilla de respuesta automática (AJAX)."""
    company = request.user.company
    template = get_object_or_404(
        MercadoLibreReplyTemplate, id=template_id, company=company
    )

    if request.method == 'POST':
        template.is_active = not template.is_active
        template.save(update_fields=['is_active', 'updated_at'])
        return JsonResponse({
            'status': 'ok',
            'is_active': template.is_active,
            'message': f'Plantilla {"activada" if template.is_active else "desactivada"}.',
        })

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ---------------------------------------------------------------------------
# Product Management
# ---------------------------------------------------------------------------
@login_required
def products_list(request):
    """Lista productos de MercadoLibre con filtros por estado y stock bajo."""
    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        messages.warning(request, 'Conecta tu cuenta de MercadoLibre primero.')
        return redirect('crm:mercadolibre:status')

    # Filtros
    status_filter = request.GET.get('status', '')
    low_stock = request.GET.get('low_stock', '')
    search = request.GET.get('q', '').strip()

    products = MercadoLibreProduct.objects.filter(
        company=company, integration=integration
    )

    if status_filter:
        products = products.filter(status=status_filter)
    if low_stock == '1':
        products = products.filter(available_quantity__lte=MercadoLibreProductService.LOW_STOCK_THRESHOLD)
    if search:
        products = products.filter(title__icontains=search)

    products = products.order_by('-updated_at')

    # Stats
    total = MercadoLibreProduct.objects.filter(company=company).count()
    active_count = MercadoLibreProduct.objects.filter(company=company, status='active').count()
    paused_count = MercadoLibreProduct.objects.filter(company=company, status='paused').count()
    low_stock_count = MercadoLibreProduct.objects.filter(
        company=company, available_quantity__lte=MercadoLibreProductService.LOW_STOCK_THRESHOLD
    ).count()

    context = {
        'products': products,
        'integration': integration,
        'status_filter': status_filter,
        'low_stock_filter': low_stock,
        'search': search,
        'total': total,
        'active_count': active_count,
        'paused_count': paused_count,
        'low_stock_count': low_stock_count,
    }
    return render(request, 'crm/integrations/mercadolibre_products.html', context)


@login_required
def products_sync(request):
    """Sincroniza todos los productos desde MercadoLibre."""
    if request.method != 'POST':
        return redirect('crm:mercadolibre:products_list')

    company = request.user.company
    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        messages.error(request, 'No hay integración activa.')
        return redirect('crm:mercadolibre:products_list')

    try:
        service = MercadoLibreProductService(integration)
        stats = service.sync_products()

        if stats['skipped'] > 0:
            messages.warning(
                request,
                f'Sincronización parcial: {stats["skipped"]} productos bloqueados por restricciones '
                f'de cuenta de test de MercadoLibre. Con una cuenta real esto funciona correctamente.'
            )

        if stats['created'] > 0 or stats['updated'] > 0:
            messages.success(
                request,
                f'Sincronización completada: {stats["created"]} nuevos, '
                f'{stats["updated"]} actualizados'
                f'{", " + str(stats["errors"]) + " errores" if stats["errors"] else ""} '
                f'(de {stats["total"]} productos).'
            )
        elif stats['total'] == 0:
            messages.info(request, 'No se encontraron productos para sincronizar.')
        elif stats['skipped'] == stats['total']:
            messages.warning(
                request,
                'No se pudieron sincronizar productos. Las cuentas de test de MercadoLibre '
                'bloquean el acceso a la API de items. Los productos se sincronizarán '
                'automáticamente cuando lleguen preguntas o se reciban webhooks.'
            )
    except Exception as e:
        logger.error(f"Product sync error: {e}", exc_info=True)
        messages.error(request, f'Error al sincronizar: {str(e)}')

    return redirect('crm:mercadolibre:products_list')


@login_required
def product_edit(request, product_id):
    """Edita precio, stock o título de un producto."""
    company = request.user.company
    product = get_object_or_404(MercadoLibreProduct, id=product_id, company=company)

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        messages.error(request, 'No hay integración activa.')
        return redirect('crm:mercadolibre:products_list')

    if request.method == 'POST':
        update_data = {}
        new_price = request.POST.get('price', '').strip()
        new_stock = request.POST.get('available_quantity', '').strip()
        new_title = request.POST.get('title', '').strip()

        if new_price:
            try:
                update_data['price'] = float(new_price)
            except ValueError:
                messages.error(request, 'El precio debe ser un número válido.')
                return render(request, 'crm/integrations/mercadolibre_product_edit.html', {
                    'product': product,
                })

        if new_stock:
            try:
                update_data['available_quantity'] = int(new_stock)
            except ValueError:
                messages.error(request, 'El stock debe ser un número entero.')
                return render(request, 'crm/integrations/mercadolibre_product_edit.html', {
                    'product': product,
                })

        if new_title and new_title != product.title:
            update_data['title'] = new_title

        if not update_data:
            messages.info(request, 'No se detectaron cambios.')
            return redirect('crm:mercadolibre:products_list')

        try:
            service = MercadoLibreProductService(integration)
            service.update_product(product_id, update_data)
            messages.success(request, f'Producto "{product.title}" actualizado en MercadoLibre.')
        except Exception as e:
            logger.error(f"Product update error: {e}", exc_info=True)
            messages.error(request, f'Error al actualizar: {str(e)}')

        return redirect('crm:mercadolibre:products_list')

    return render(request, 'crm/integrations/mercadolibre_product_edit.html', {
        'product': product,
    })


@login_required
def product_change_status(request, product_id, new_status):
    """Pausa, activa o cierra una publicación."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    company = request.user.company
    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        return JsonResponse({'error': 'No hay integración activa'}, status=400)

    try:
        service = MercadoLibreProductService(integration)
        product = service.change_product_status(product_id, new_status)

        status_labels = {'active': 'activada', 'paused': 'pausada', 'closed': 'cerrada'}
        label = status_labels.get(new_status, new_status)

        # Si es AJAX (fetch), devolver JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'ok',
                'product_status': product.status,
                'message': f'Publicación {label}.',
            })

        messages.success(request, f'Publicación "{product.title}" {label}.')
    except Exception as e:
        logger.error(f"Product status change error: {e}", exc_info=True)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': str(e)}, status=500)
        messages.error(request, f'Error: {str(e)}')

    return redirect('crm:mercadolibre:products_list')


# ---------------------------------------------------------------------------
# Products JSON API (for frontend tables / AJAX)
# ---------------------------------------------------------------------------
@login_required
def products_api_list(request):
    """API JSON: lista productos con filtros. Para consumo desde JS/frontend."""
    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        return JsonResponse({'error': 'No integration'}, status=400)

    status_filter = request.GET.get('status', '')
    low_stock = request.GET.get('low_stock', '')
    search = request.GET.get('q', '')

    products = MercadoLibreProduct.objects.filter(
        company=company, integration=integration
    )

    if status_filter:
        products = products.filter(status=status_filter)
    if low_stock == '1':
        products = products.filter(available_quantity__lte=MercadoLibreProductService.LOW_STOCK_THRESHOLD)
    if search:
        products = products.filter(title__icontains=search)

    products = products.order_by('-updated_at')

    data = []
    for p in products:
        data.append({
            'id': p.id,
            'ml_item_id': p.ml_item_id,
            'title': p.title,
            'price': float(p.price),
            'currency_id': p.currency_id,
            'available_quantity': p.available_quantity,
            'sold_quantity': p.sold_quantity,
            'status': p.status,
            'condition': p.condition,
            'thumbnail': p.thumbnail,
            'permalink': p.permalink,
            'listing_type_id': p.listing_type_id,
            'low_stock': p.available_quantity <= MercadoLibreProductService.LOW_STOCK_THRESHOLD,
            'last_synced_at': p.last_synced_at.isoformat() if p.last_synced_at else None,
            'updated_at': p.updated_at.isoformat(),
        })

    return JsonResponse({'products': data, 'count': len(data)})


@login_required
def status_api(request):
    """JSON API for status page polling - returns latest questions and events."""
    company = request.user.company

    try:
        integration = MercadoLibreIntegration.objects.get(company=company, is_active=True)
    except MercadoLibreIntegration.DoesNotExist:
        return JsonResponse({'error': 'not_connected'}, status=404)

    questions = integration.questions.order_by('-date_created')[:10]
    events = integration.webhook_events.order_by('-received_at')[:20]

    questions_data = []
    for q in questions:
        questions_data.append({
            'id': q.ml_question_id,
            'from_nickname': q.from_nickname or f'Usuario #{q.from_id}',
            'from_initial': (q.from_nickname[0] if q.from_nickname else '?'),
            'text': q.text,
            'status': q.status,
            'date_created': q.date_created.strftime('%d/%m %H:%M') if q.date_created else '',
            'answer_text': q.answer_text or '',
            'auto_replied': q.auto_replied,
        })

    events_data = []
    for e in events:
        topic_labels = {
            'orders_v2': 'Nueva orden', 'orders': 'Nueva orden',
            'questions': 'Nueva pregunta', 'items': 'Producto actualizado',
            'messages': 'Nuevo mensaje', 'shipments': 'Envio actualizado',
        }
        events_data.append({
            'id': e.id,
            'topic': e.topic,
            'label': topic_labels.get(e.topic, e.topic),
            'status': e.status,
            'received_at': e.received_at.strftime('%d/%m %H:%M') if e.received_at else '',
        })

    return JsonResponse({
        'questions': questions_data,
        'events': events_data,
        'counts': {
            'orders': integration.orders.count(),
            'questions': integration.questions.count(),
            'products': integration.products.count(),
            'events': len(events_data),
        },
    })


# ---------------------------------------------------------------------------
# MODULE A: Questions Inbox (Bandeja de Preguntas Pre-venta)
# ---------------------------------------------------------------------------
@login_required
def questions_inbox(request):
    """
    Página principal de la bandeja de preguntas.
    Renderiza el contenedor; la lista se carga via HTMX partial.
    """
    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        messages.warning(request, 'Conectá tu cuenta de MercadoLibre primero.')
        return redirect('crm:mercadolibre:status')

    # Counts for filter tabs — scoped to active integration
    qs_base = MercadoLibreQuestion.objects.filter(integration=integration, is_ignored=False)
    counts = {
        'all': qs_base.count(),
        'unanswered': qs_base.filter(status='UNANSWERED').count(),
        'answered': qs_base.filter(status='ANSWERED').count(),
    }

    context = {
        'integration': integration,
        'counts': counts,
        'current_filter': request.GET.get('status', ''),
    }
    return render(request, 'crm/integrations/mercadolibre_questions_inbox.html', context)


@login_required
def questions_inbox_list(request):
    """
    HTMX partial: devuelve la lista filtrada de preguntas.
    Soporta filtro por status y búsqueda por texto.
    """
    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    qs = MercadoLibreQuestion.objects.filter(
        integration=integration, is_ignored=False
    ).select_related('product') if integration else MercadoLibreQuestion.objects.none()

    # Filters
    status_filter = request.GET.get('status', '')
    search = request.GET.get('q', '').strip()

    if status_filter in ('UNANSWERED', 'ANSWERED'):
        qs = qs.filter(status=status_filter)
    if search:
        qs = qs.filter(text__icontains=search)

    qs = qs.order_by('-date_created')[:50]

    context = {
        'questions': qs,
        'current_filter': status_filter,
        'search': search,
    }
    return render(request, 'crm/integrations/_questions_list.html', context)


@login_required
def question_detail(request, question_id):
    """
    HTMX partial: detalle de una pregunta con formulario de respuesta.
    Marca la pregunta como leída al abrirla.
    """
    company = request.user.company
    question = get_object_or_404(
        MercadoLibreQuestion, id=question_id, company=company
    )

    # Mark as read
    if not question.read_at:
        question.read_at = timezone.now()
        question.save(update_fields=['read_at'])

    # Quick-reply templates
    from .integrations_mercadolibre_models import MercadoLibreReplyTemplate
    templates = MercadoLibreReplyTemplate.objects.filter(
        company=company,
        is_active=True,
        usable_in_questions=True,
    ).order_by('-priority', 'name')

    context = {
        'question': question,
        'reply_templates': templates,
    }
    return render(request, 'crm/integrations/_question_detail.html', context)


@login_required
@require_http_methods(["POST"])
def question_reply(request, question_id):
    """
    Envía respuesta manual a una pregunta de MercadoLibre.
    POST con campo 'reply_text'. Retorna partial HTMX actualizado.
    """
    company = request.user.company
    question = get_object_or_404(
        MercadoLibreQuestion, id=question_id, company=company
    )

    reply_text = request.POST.get('reply_text', '').strip()
    template_id = request.POST.get('template_id', '').strip()

    if not reply_text:
        return render(request, 'crm/integrations/_question_detail.html', {
            'question': question,
            'reply_templates': MercadoLibreReplyTemplate.objects.filter(
                company=company, is_active=True, usable_in_questions=True,
            ).order_by('-priority', 'name'),
            'error': 'El texto de respuesta no puede estar vacío.',
        })

    # Get integration for API call
    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        return render(request, 'crm/integrations/_question_detail.html', {
            'question': question,
            'error': 'No hay integración activa con MercadoLibre.',
        })

    try:
        from .integrations_mercadolibre_services import MercadoLibreAPIClient
        api = MercadoLibreAPIClient(integration)
        api.answer_question(question.ml_question_id, reply_text)

        # Update local DB
        question.answer_text = reply_text
        question.answer_date = timezone.now()
        question.status = 'ANSWERED'
        question.answered_by = request.user
        update_fields = ['answer_text', 'answer_date', 'status', 'answered_by']

        # Track template usage if used
        if template_id:
            try:
                tpl = MercadoLibreReplyTemplate.objects.get(
                    id=int(template_id), company=company
                )
                tpl.times_used += 1
                tpl.last_used_at = timezone.now()
                tpl.save(update_fields=['times_used', 'last_used_at', 'updated_at'])
            except (MercadoLibreReplyTemplate.DoesNotExist, ValueError):
                pass

        question.save(update_fields=update_fields)
        logger.info(f"Manual reply sent to Q#{question.ml_question_id} by {request.user.email}")

    except Exception as e:
        logger.error(f"Manual reply error for Q#{question.ml_question_id}: {e}", exc_info=True)
        return render(request, 'crm/integrations/_question_detail.html', {
            'question': question,
            'reply_templates': MercadoLibreReplyTemplate.objects.filter(
                company=company, is_active=True, usable_in_questions=True,
            ).order_by('-priority', 'name'),
            'error': f'Error al enviar respuesta: {str(e)}',
        })

    # Re-fetch and return updated detail
    question.refresh_from_db()
    templates = MercadoLibreReplyTemplate.objects.filter(
        company=company, is_active=True, usable_in_questions=True,
    ).order_by('-priority', 'name')

    return render(request, 'crm/integrations/_question_detail.html', {
        'question': question,
        'reply_templates': templates,
        'success': 'Respuesta enviada correctamente.',
    })


@login_required
@require_http_methods(["POST"])
def question_ignore(request, question_id):
    """
    Marca/desmarca una pregunta como ignorada.
    Retorna partial HTMX de la lista actualizada.
    """
    company = request.user.company
    question = get_object_or_404(
        MercadoLibreQuestion, id=question_id, company=company
    )

    question.is_ignored = not question.is_ignored
    question.save(update_fields=['is_ignored'])

    action = 'ignorada' if question.is_ignored else 'restaurada'
    logger.info(f"Question #{question.ml_question_id} {action} by {request.user.email}")

    # Return updated list via HTMX
    if request.htmx:
        integration = MercadoLibreIntegration.objects.filter(
            company=company, is_active=True
        ).first()
        qs = MercadoLibreQuestion.objects.filter(
            integration=integration, is_ignored=False
        ).select_related('product').order_by('-date_created')[:50] if integration else MercadoLibreQuestion.objects.none()

        status_filter = request.GET.get('status', '')
        if status_filter in ('UNANSWERED', 'ANSWERED'):
            qs = qs.filter(status=status_filter)

        return render(request, 'crm/integrations/_questions_list.html', {
            'questions': qs,
            'current_filter': status_filter,
        })

    return redirect('crm:mercadolibre:questions_inbox')


# ---------------------------------------------------------------------------
# MODULE B: Messages Inbox (Bandeja de Mensajes Post-venta)
# ---------------------------------------------------------------------------
from django.db.models import Max, Count, Q, Subquery, OuterRef


@login_required
def messages_inbox(request):
    """
    Página principal de la bandeja de mensajes post-venta.
    Agrupa mensajes por pack_id (conversación).
    """
    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        messages.warning(request, 'Conectá tu cuenta de MercadoLibre primero.')
        return redirect('crm:mercadolibre:status')

    # Count conversations (unique pack_ids) with unread buyer messages
    all_packs = MercadoLibreMessage.objects.filter(
        integration=integration
    ).exclude(pack_id='').values('pack_id').distinct().count()

    unread_packs = MercadoLibreMessage.objects.filter(
        integration=integration,
        is_from_buyer=True,
        read_at__isnull=True,
    ).exclude(pack_id='').values('pack_id').distinct().count()

    counts = {
        'all': all_packs,
        'unread': unread_packs,
    }

    context = {
        'integration': integration,
        'counts': counts,
        'current_filter': request.GET.get('filter', ''),
    }
    return render(request, 'crm/integrations/mercadolibre_messages_inbox.html', context)


@login_required
def messages_inbox_list(request):
    """
    HTMX partial: lista de conversaciones agrupadas por pack_id.
    Cada item muestra el último mensaje y el nombre del comprador.
    """
    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        return render(request, 'crm/integrations/_conversations_list.html', {
            'conversations': [],
        })

    # Get all unique pack_ids with latest message info
    packs_qs = MercadoLibreMessage.objects.filter(
        integration=integration
    ).exclude(pack_id='').values('pack_id').annotate(
        last_date=Max('message_date'),
        msg_count=Count('id'),
        unread_count=Count('id', filter=Q(is_from_buyer=True, read_at__isnull=True)),
    ).order_by('-last_date')

    filter_type = request.GET.get('filter', '')
    search = request.GET.get('q', '').strip()

    if filter_type == 'unread':
        packs_qs = packs_qs.filter(unread_count__gt=0)

    packs_qs = packs_qs[:50]

    # Enrich each pack with the latest message and buyer info
    conversations = []
    for pack in packs_qs:
        pack_messages = MercadoLibreMessage.objects.filter(
            integration=integration,
            pack_id=pack['pack_id'],
        ).select_related('order')

        latest_msg = pack_messages.order_by('-message_date').first()
        if not latest_msg:
            continue

        # Get buyer info from the first buyer message or order
        buyer_msg = pack_messages.filter(is_from_buyer=True).first()
        buyer_name = ''
        if buyer_msg:
            buyer_name = buyer_msg.sender_nickname
        if not buyer_name and latest_msg.order:
            buyer_name = latest_msg.order.buyer_nickname

        # Search filter
        if search and search.lower() not in (buyer_name or '').lower() and search.lower() not in (latest_msg.text or '').lower():
            continue

        conversations.append({
            'pack_id': pack['pack_id'],
            'buyer_name': buyer_name or f'Comprador',
            'last_message': latest_msg.text[:120] if latest_msg.text else '',
            'last_date': pack['last_date'],
            'msg_count': pack['msg_count'],
            'unread_count': pack['unread_count'],
            'is_from_buyer': latest_msg.is_from_buyer,
            'order': latest_msg.order,
        })

    context = {
        'conversations': conversations,
        'current_filter': filter_type,
        'search': search,
    }
    return render(request, 'crm/integrations/_conversations_list.html', context)


@login_required
def conversation_detail(request, pack_id):
    """
    HTMX partial: detalle de una conversación (todos los mensajes del pack).
    Marca mensajes del comprador como leídos.
    """
    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        return render(request, 'crm/integrations/_conversation_detail.html', {
            'error': 'No hay integración activa.',
        })

    msgs = MercadoLibreMessage.objects.filter(
        integration=integration,
        pack_id=pack_id,
    ).select_related('order').order_by('message_date')

    if not msgs.exists():
        return render(request, 'crm/integrations/_conversation_detail.html', {
            'error': 'Conversación no encontrada.',
        })

    # Mark unread buyer messages as read
    msgs.filter(is_from_buyer=True, read_at__isnull=True).update(read_at=timezone.now())

    messages_list = list(msgs)
    first_msg = messages_list[0]

    # Buyer info
    buyer_msg = next((m for m in messages_list if m.is_from_buyer), None)
    buyer_name = ''
    if buyer_msg:
        buyer_name = buyer_msg.sender_nickname
    if not buyer_name and first_msg.order:
        buyer_name = first_msg.order.buyer_nickname

    # Order info
    order = first_msg.order

    # Reply templates
    templates = MercadoLibreReplyTemplate.objects.filter(
        company=company,
        is_active=True,
        usable_in_messages=True,
    ).order_by('-priority', 'name')

    context = {
        'pack_id': pack_id,
        'messages_list': messages_list,
        'buyer_name': buyer_name or 'Comprador',
        'order': order,
        'reply_templates': templates,
        'integration': integration,
    }
    return render(request, 'crm/integrations/_conversation_detail.html', context)


@login_required
@require_http_methods(["POST"])
def message_reply(request, pack_id):
    """
    Envía un mensaje de respuesta en una conversación post-venta.
    """
    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        return render(request, 'crm/integrations/_conversation_detail.html', {
            'error': 'No hay integración activa con MercadoLibre.',
        })

    reply_text = request.POST.get('reply_text', '').strip()

    if not reply_text:
        # Re-render detail with error
        return _render_conversation_detail(request, integration, pack_id, error='El mensaje no puede estar vacío.')

    # Find a buyer message to get buyer_id
    buyer_msg = MercadoLibreMessage.objects.filter(
        integration=integration,
        pack_id=pack_id,
        is_from_buyer=True,
    ).first()

    if not buyer_msg:
        return _render_conversation_detail(request, integration, pack_id, error='No se encontró información del comprador.')

    seller_id = int(integration.ml_user_id)
    buyer_id = buyer_msg.sender_id

    try:
        from .integrations_mercadolibre_services import MercadoLibreAPIClient
        api = MercadoLibreAPIClient(integration)
        result = api.send_message(pack_id, seller_id, buyer_id, reply_text)

        # Save the sent message locally
        new_msg_id = result.get('id', f'local_{timezone.now().timestamp()}')
        MercadoLibreMessage.objects.create(
            integration=integration,
            company=company,
            ml_message_id=str(new_msg_id),
            pack_id=pack_id,
            order=buyer_msg.order,
            sender_id=seller_id,
            sender_nickname=integration.nickname or 'Vendedor',
            receiver_id=buyer_id,
            is_from_buyer=False,
            text=reply_text,
            message_date=timezone.now(),
            status='available',
            contact=buyer_msg.contact,
            read_at=timezone.now(),
            raw_data=result,
        )

        # Track template usage
        template_id = request.POST.get('template_id', '').strip()
        if template_id:
            try:
                tpl = MercadoLibreReplyTemplate.objects.get(id=int(template_id), company=company)
                tpl.times_used += 1
                tpl.last_used_at = timezone.now()
                tpl.save(update_fields=['times_used', 'last_used_at', 'updated_at'])
            except (MercadoLibreReplyTemplate.DoesNotExist, ValueError):
                pass

        logger.info(f"Manual message sent to pack {pack_id} by {request.user.email}")
        return _render_conversation_detail(request, integration, pack_id, success='Mensaje enviado correctamente.')

    except Exception as e:
        logger.error(f"Message reply error for pack {pack_id}: {e}", exc_info=True)
        return _render_conversation_detail(request, integration, pack_id, error=f'Error al enviar mensaje: {str(e)}')


def _render_conversation_detail(request, integration, pack_id, error=None, success=None):
    """Helper to re-render conversation detail with optional messages."""
    company = request.user.company
    msgs = MercadoLibreMessage.objects.filter(
        integration=integration,
        pack_id=pack_id,
    ).select_related('order').order_by('message_date')

    messages_list = list(msgs)
    first_msg = messages_list[0] if messages_list else None

    buyer_msg = next((m for m in messages_list if m.is_from_buyer), None)
    buyer_name = ''
    if buyer_msg:
        buyer_name = buyer_msg.sender_nickname
    if not buyer_name and first_msg and first_msg.order:
        buyer_name = first_msg.order.buyer_nickname

    templates = MercadoLibreReplyTemplate.objects.filter(
        company=company,
        is_active=True,
        usable_in_messages=True,
    ).order_by('-priority', 'name')

    return render(request, 'crm/integrations/_conversation_detail.html', {
        'pack_id': pack_id,
        'messages_list': messages_list,
        'buyer_name': buyer_name or 'Comprador',
        'order': first_msg.order if first_msg else None,
        'reply_templates': templates,
        'integration': integration,
        'error': error,
        'success': success,
    })


# ---------------------------------------------------------------------------
# MODULE C: Order Detail View
# ---------------------------------------------------------------------------
from django.http import HttpResponse


@login_required
def order_detail(request, order_id):
    """
    Página de detalle de una orden individual.
    Muestra comprador, ítems, pago, envío con tracking en tiempo real.
    """
    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        messages.warning(request, 'Conectá tu cuenta de MercadoLibre primero.')
        return redirect('crm:mercadolibre:status')

    order = get_object_or_404(
        MercadoLibreOrder,
        id=order_id,
        integration=integration,
    )

    items = order.items.select_related('product').all()

    # Fetch shipment tracking in real-time if shipping_id exists
    shipment_data = None
    shipping_steps = []
    if order.shipping_id:
        try:
            from .integrations_mercadolibre_services import MercadoLibreAPIClient
            api = MercadoLibreAPIClient(integration)
            shipment_data = api.get_shipment(order.shipping_id)

            # Update cached fields if we got fresh data
            _update_order_shipping_cache(order, shipment_data)

            # Build shipping progress steps
            shipping_steps = _build_shipping_steps(shipment_data)
        except Exception as e:
            logger.warning(f"Failed to fetch shipment {order.shipping_id}: {e}")

    # Messages in this order's pack (if any)
    order_messages = MercadoLibreMessage.objects.filter(
        integration=integration,
        order=order,
    ).order_by('-message_date')[:5]

    context = {
        'order': order,
        'items': items,
        'integration': integration,
        'shipment_data': shipment_data,
        'shipping_steps': shipping_steps,
        'order_messages': order_messages,
    }
    return render(request, 'crm/integrations/mercadolibre_order_detail.html', context)


@login_required
def shipment_label_download(request, order_id):
    """
    Proxy view: downloads the shipment label PDF from ML API
    and streams it to the browser.
    """
    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        return HttpResponse('No hay integración activa.', status=403)

    order = get_object_or_404(
        MercadoLibreOrder,
        id=order_id,
        integration=integration,
    )

    if not order.shipping_id:
        return HttpResponse('Esta orden no tiene envío asociado.', status=404)

    try:
        from .integrations_mercadolibre_services import MercadoLibreAPIClient
        api = MercadoLibreAPIClient(integration)
        pdf_bytes = api.get_shipment_label_pdf(order.shipping_id)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="etiqueta_orden_{order.ml_order_id}.pdf"'
        return response

    except Exception as e:
        logger.error(f"Label download error for shipping {order.shipping_id}: {e}", exc_info=True)
        return HttpResponse(f'Error al descargar etiqueta: {str(e)}', status=502)


@login_required
def orders_list(request):
    """
    Lista de órdenes de MercadoLibre con filtros.
    """
    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        messages.warning(request, 'Conectá tu cuenta de MercadoLibre primero.')
        return redirect('crm:mercadolibre:status')

    qs = MercadoLibreOrder.objects.filter(
        integration=integration,
    ).prefetch_related('items').order_by('-date_created')

    status_filter = request.GET.get('status', '')
    search = request.GET.get('q', '').strip()

    if status_filter:
        qs = qs.filter(status=status_filter)

    if search:
        qs = qs.filter(
            Q(buyer_nickname__icontains=search) |
            Q(ml_order_id__icontains=search) |
            Q(buyer_first_name__icontains=search) |
            Q(buyer_last_name__icontains=search)
        )

    orders = qs[:50]

    # Counts
    all_orders = MercadoLibreOrder.objects.filter(integration=integration)
    counts = {
        'all': all_orders.count(),
        'paid': all_orders.filter(status='paid').count(),
        'confirmed': all_orders.filter(status='confirmed').count(),
        'cancelled': all_orders.filter(status='cancelled').count(),
    }

    context = {
        'orders': orders,
        'integration': integration,
        'counts': counts,
        'current_filter': status_filter,
        'search': search,
    }
    return render(request, 'crm/integrations/mercadolibre_orders_list.html', context)


def _update_order_shipping_cache(order, shipment_data):
    """Update cached shipping fields from real-time API data."""
    changed = False

    tracking = shipment_data.get('tracking_number', '')
    if tracking and tracking != order.shipping_tracking_number:
        order.shipping_tracking_number = tracking
        changed = True

    carrier = ''
    logistic_type = shipment_data.get('logistic_type', '')
    if logistic_type:
        carrier = logistic_type.replace('_', ' ').title()
    shipping_option = shipment_data.get('shipping_option', {})
    if shipping_option.get('name'):
        carrier = shipping_option['name']
    if carrier and carrier != order.shipping_carrier:
        order.shipping_carrier = carrier
        changed = True

    new_status = shipment_data.get('status', '')
    if new_status and new_status != order.shipping_status:
        order.shipping_status = new_status
        changed = True

    # Cache receiver address
    receiver = shipment_data.get('receiver_address', {})
    if receiver and receiver != order.shipping_receiver_address:
        order.shipping_receiver_address = {
            'city': receiver.get('city', {}).get('name', ''),
            'state': receiver.get('state', {}).get('name', ''),
            'zip_code': receiver.get('zip_code', ''),
            'street_name': receiver.get('street_name', ''),
            'street_number': receiver.get('street_number', ''),
            'comment': receiver.get('comment', ''),
        }
        changed = True

    if changed:
        order.save(update_fields=[
            'shipping_tracking_number', 'shipping_carrier',
            'shipping_status', 'shipping_receiver_address', 'updated_at',
        ])


def _build_shipping_steps(shipment_data):
    """
    Build a list of shipping progress steps from ML shipment data.
    Returns list of dicts: {label, status, date, is_current}
    """
    status = shipment_data.get('status', '')
    substatus = shipment_data.get('substatus', '')

    # Define the standard Mercado Envíos flow
    STEPS = [
        ('pending', 'Preparando'),
        ('ready_to_ship', 'Listo para enviar'),
        ('shipped', 'En camino'),
        ('delivered', 'Entregado'),
    ]

    # Map status to step index
    status_index = {s[0]: i for i, s in enumerate(STEPS)}
    current_idx = status_index.get(status, -1)

    # Handle special statuses
    if status == 'not_delivered':
        current_idx = 3  # after shipped
    elif status == 'cancelled':
        return [{'label': 'Cancelado', 'status': 'cancelled', 'date': None, 'is_current': True}]

    steps = []
    for i, (step_key, step_label) in enumerate(STEPS):
        step = {
            'label': step_label,
            'status': 'completed' if i < current_idx else ('current' if i == current_idx else 'pending'),
            'is_current': i == current_idx,
            'date': None,
        }

        # Add substatus info to current step
        if i == current_idx and substatus:
            readable = substatus.replace('_', ' ').title()
            step['sublabel'] = readable

        steps.append(step)

    # Special: not_delivered
    if status == 'not_delivered':
        steps.append({
            'label': 'No entregado',
            'status': 'error',
            'is_current': True,
            'date': None,
            'sublabel': substatus.replace('_', ' ').title() if substatus else '',
        })

    return steps


# ---------------------------------------------------------------------------
# MODULE D: Buyer Profile (Perfil Unificado del Comprador)
# ---------------------------------------------------------------------------
from django.db.models import Sum


@login_required
def buyer_profile(request, buyer_id):
    """
    Perfil unificado de un comprador: órdenes, preguntas, mensajes, reclamos.
    Agrega datos de distintas tablas por buyer_id.
    """
    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        messages.warning(request, 'Conectá tu cuenta de MercadoLibre primero.')
        return redirect('crm:mercadolibre:status')

    buyer_id = int(buyer_id)

    # --- Orders ---
    orders = MercadoLibreOrder.objects.filter(
        integration=integration,
        buyer_id=buyer_id,
    ).prefetch_related('items').order_by('-date_created')

    if not orders.exists():
        # Try to find the buyer in questions
        question = MercadoLibreQuestion.objects.filter(
            integration=integration,
            from_id=buyer_id,
        ).first()
        if not question:
            messages.error(request, 'Comprador no encontrado.')
            return redirect('crm:mercadolibre:orders_list')

    # Buyer info from first order or question
    first_order = orders.first()
    buyer_info = {
        'buyer_id': buyer_id,
        'nickname': '',
        'first_name': '',
        'last_name': '',
        'email': '',
        'phone': '',
    }
    if first_order:
        buyer_info.update({
            'nickname': first_order.buyer_nickname,
            'first_name': first_order.buyer_first_name,
            'last_name': first_order.buyer_last_name,
            'email': first_order.buyer_email,
            'phone': first_order.buyer_phone,
        })

    # --- Stats ---
    stats = orders.aggregate(
        total_spent=Sum('total_amount'),
    )
    stats['order_count'] = orders.count()
    stats['total_spent'] = stats['total_spent'] or 0
    if orders.exists():
        stats['first_order'] = orders.last().date_created
        stats['last_order'] = orders.first().date_created
    else:
        stats['first_order'] = None
        stats['last_order'] = None

    # --- Questions ---
    questions = MercadoLibreQuestion.objects.filter(
        integration=integration,
        from_id=buyer_id,
    ).select_related('product').order_by('-date_created')

    # --- Messages ---
    buyer_messages = MercadoLibreMessage.objects.filter(
        integration=integration,
        sender_id=buyer_id,
        is_from_buyer=True,
    ).values_list('pack_id', flat=True).distinct()

    # Get full conversations for those packs
    conversations = []
    for pack_id in buyer_messages[:20]:
        if not pack_id:
            continue
        latest = MercadoLibreMessage.objects.filter(
            integration=integration,
            pack_id=pack_id,
        ).order_by('-message_date').first()
        if latest:
            msg_count = MercadoLibreMessage.objects.filter(
                integration=integration,
                pack_id=pack_id,
            ).count()
            conversations.append({
                'pack_id': pack_id,
                'last_message': latest.text[:100] if latest.text else '',
                'last_date': latest.message_date,
                'msg_count': msg_count,
                'order': latest.order,
            })

    # --- Claims (real-time, with error handling) ---
    claims = []
    claims_error = None
    try:
        from .integrations_mercadolibre_services import MercadoLibreAPIClient
        api = MercadoLibreAPIClient(integration)
        claims_data = api.get_buyer_claims(int(integration.ml_user_id), buyer_id)
        claims = claims_data.get('data', claims_data.get('results', []))
    except Exception as e:
        claims_error = str(e)
        logger.warning(f"Failed to fetch claims for buyer {buyer_id}: {e}")

    # --- CRM Contact link ---
    contact = None
    if first_order and first_order.contact:
        contact = first_order.contact

    active_tab = request.GET.get('tab', 'orders')

    context = {
        'buyer': buyer_info,
        'stats': stats,
        'orders': orders[:20],
        'questions': questions[:20],
        'conversations': conversations,
        'claims': claims,
        'claims_error': claims_error,
        'contact': contact,
        'integration': integration,
        'active_tab': active_tab,
    }
    return render(request, 'crm/integrations/mercadolibre_buyer_profile.html', context)


# ---------------------------------------------------------------------------
# MODULE E: Business Metrics Dashboard
# ---------------------------------------------------------------------------
from datetime import timedelta, date
from decimal import Decimal
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncDate


@login_required
def metrics_dashboard(request):
    """
    Dashboard de métricas de negocio: ventas, ganancia estimada,
    reputación del vendedor, publicaciones de bajo rendimiento.
    """
    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        messages.warning(request, 'Conectá tu cuenta de MercadoLibre primero.')
        return redirect('crm:mercadolibre:status')

    # --- Period selection ---
    period = request.GET.get('period', '30')
    try:
        days = int(period)
    except ValueError:
        days = 30

    today = timezone.now().date()
    start_date = today - timedelta(days=days)
    prev_start = start_date - timedelta(days=days)

    # --- Current period orders (paid only for revenue) ---
    current_orders = MercadoLibreOrder.objects.filter(
        integration=integration,
        date_created__date__gte=start_date,
        date_created__date__lte=today,
    )
    paid_orders = current_orders.filter(status='paid')

    # --- Previous period for comparison ---
    prev_orders = MercadoLibreOrder.objects.filter(
        integration=integration,
        date_created__date__gte=prev_start,
        date_created__date__lt=start_date,
    )
    prev_paid = prev_orders.filter(status='paid')

    # --- KPIs ---
    current_revenue = paid_orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    prev_revenue = prev_paid.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    current_count = paid_orders.count()
    prev_count = prev_paid.count()
    avg_ticket = (current_revenue / current_count) if current_count > 0 else Decimal('0')

    # Revenue change %
    if prev_revenue > 0:
        revenue_change = ((current_revenue - prev_revenue) / prev_revenue * 100)
    else:
        revenue_change = Decimal('100') if current_revenue > 0 else Decimal('0')

    # Order count change %
    if prev_count > 0:
        count_change = ((current_count - prev_count) / prev_count * 100)
    else:
        count_change = 100 if current_count > 0 else 0

    # --- Profit estimation ---
    ml_commission = company.ml_commission_rate or Decimal('13')
    iva_rate = Decimal('21') if company.iva_condition == 'responsable_inscripto' else Decimal('0')
    iibb_rate = company.iibb_rate or Decimal('0')

    commission_amount = current_revenue * ml_commission / 100
    iva_amount = current_revenue * iva_rate / 100 if iva_rate else Decimal('0')
    iibb_amount = current_revenue * iibb_rate / 100 if iibb_rate else Decimal('0')
    estimated_profit = current_revenue - commission_amount - iva_amount - iibb_amount

    # --- Daily sales chart data ---
    daily_sales = (
        paid_orders
        .annotate(day=TruncDate('date_created'))
        .values('day')
        .annotate(total=Sum('total_amount'), count=Count('id'))
        .order_by('day')
    )

    chart_labels = []
    chart_values = []
    chart_counts = []
    # Fill all days in range (including zeros)
    day_map = {str(d['day']): d for d in daily_sales}
    current_day = start_date
    while current_day <= today:
        day_str = str(current_day)
        chart_labels.append(current_day.strftime('%d/%m'))
        if day_str in day_map:
            chart_values.append(float(day_map[day_str]['total']))
            chart_counts.append(day_map[day_str]['count'])
        else:
            chart_values.append(0)
            chart_counts.append(0)
        current_day += timedelta(days=1)

    # --- All orders status breakdown ---
    all_current = current_orders.count()
    cancelled_count = current_orders.filter(status='cancelled').count()

    # --- Seller reputation (real-time) ---
    reputation = None
    try:
        from .integrations_mercadolibre_services import MercadoLibreAPIClient
        api = MercadoLibreAPIClient(integration)
        user_data = api.get_seller_reputation()
        rep = user_data.get('seller_reputation', {})
        transactions = rep.get('transactions', {})
        reputation = {
            'level_id': rep.get('level_id', ''),
            'power_seller': rep.get('power_seller_status', ''),
            'total_transactions': transactions.get('total', 0),
            'completed': transactions.get('completed', 0),
            'canceled': transactions.get('canceled', 0),
            'ratings': transactions.get('ratings', {}),
            'metrics': rep.get('metrics', {}),
        }
    except Exception as e:
        logger.warning(f"Failed to fetch seller reputation: {e}")

    # --- Low-performing products (active, high stock, low sales) ---
    from .integrations_mercadolibre_models import MercadoLibreProduct
    low_performers = (
        MercadoLibreProduct.objects.filter(
            integration=integration,
            status='active',
        )
        .filter(available_quantity__gt=0)
        .order_by('sold_quantity')[:10]
    )

    # --- Top-selling products ---
    from django.db.models import F
    top_sellers = (
        MercadoLibreProduct.objects.filter(
            integration=integration,
            status='active',
        )
        .filter(sold_quantity__gt=0)
        .order_by('-sold_quantity')[:10]
    )

    import json

    context = {
        'integration': integration,
        'company': company,
        'period': days,
        # KPIs
        'current_revenue': current_revenue,
        'revenue_change': revenue_change,
        'current_count': current_count,
        'count_change': count_change,
        'avg_ticket': avg_ticket,
        'all_orders_count': all_current,
        'cancelled_count': cancelled_count,
        # Profit
        'commission_amount': commission_amount,
        'iva_amount': iva_amount,
        'iibb_amount': iibb_amount,
        'estimated_profit': estimated_profit,
        'ml_commission': ml_commission,
        'iva_rate': iva_rate,
        'iibb_rate': iibb_rate,
        # Chart
        'chart_labels': json.dumps(chart_labels),
        'chart_values': json.dumps(chart_values),
        'chart_counts': json.dumps(chart_counts),
        # Reputation
        'reputation': reputation,
        # Products
        'low_performers': low_performers,
        'top_sellers': top_sellers,
    }
    return render(request, 'crm/integrations/mercadolibre_metrics_dashboard.html', context)


# ---------------------------------------------------------------------------
# MODULE F: Product Ads (Publicidad)
# ---------------------------------------------------------------------------


@login_required
def ads_list(request):
    """
    Lista de campañas de Product Ads con estado, budget e items.
    Datos en tiempo real desde la API de ML.
    """
    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        messages.warning(request, 'Conectá tu cuenta de MercadoLibre primero.')
        return redirect('crm:mercadolibre:status')

    from .integrations_mercadolibre_services import MercadoLibreAPIClient
    api = MercadoLibreAPIClient(integration)

    campaigns = []
    ads_error = None

    try:
        campaigns_data = api.get_ad_campaigns()
        # The API may return a list directly or an object with 'results'
        if isinstance(campaigns_data, list):
            raw_campaigns = campaigns_data
        else:
            raw_campaigns = campaigns_data.get('results', campaigns_data.get('campaigns', []))

        for camp in raw_campaigns:
            campaign_id = camp.get('campaign_id') or camp.get('id', '')
            campaign = {
                'id': campaign_id,
                'name': camp.get('name', f'Campaña {campaign_id}'),
                'status': camp.get('status', 'unknown'),
                'daily_budget': camp.get('daily_budget', 0),
                'total_budget': camp.get('total_budget', 0),
                'start_date': camp.get('start_date', ''),
                'items': [],
                'items_count': 0,
            }

            # Try to fetch items for each campaign
            try:
                items_data = api.get_campaign_items(campaign_id)
                if isinstance(items_data, list):
                    items_list = items_data
                else:
                    items_list = items_data.get('results', items_data.get('items', []))

                campaign['items_count'] = len(items_list)

                # Enrich items with product data from local DB
                from .integrations_mercadolibre_models import MercadoLibreProduct
                for item in items_list[:10]:
                    item_id = item.get('item_id', item.get('id', ''))
                    product = MercadoLibreProduct.objects.filter(
                        integration=integration,
                        ml_item_id=item_id,
                    ).first()

                    campaign['items'].append({
                        'item_id': item_id,
                        'status': item.get('status', ''),
                        'title': product.title if product else item_id,
                        'thumbnail': product.thumbnail if product else '',
                        'price': product.price if product else 0,
                    })
            except Exception:
                pass  # Items fetch may fail, campaign still shown

            campaigns.append(campaign)

    except Exception as e:
        ads_error = str(e)
        logger.warning(f"Failed to fetch ad campaigns: {e}")

    context = {
        'integration': integration,
        'campaigns': campaigns,
        'ads_error': ads_error,
    }
    return render(request, 'crm/integrations/mercadolibre_ads_list.html', context)


@login_required
def ad_campaign_toggle(request, campaign_id):
    """
    Toggle a campaign's status between active and paused.
    POST only.
    """
    if request.method != 'POST':
        return redirect('crm:mercadolibre:ads_list')

    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        return redirect('crm:mercadolibre:status')

    action = request.POST.get('action', 'paused')  # 'active' or 'paused'
    if action not in ('active', 'paused'):
        action = 'paused'

    from .integrations_mercadolibre_services import MercadoLibreAPIClient
    api = MercadoLibreAPIClient(integration)

    try:
        api.update_campaign_status(campaign_id, action)
        label = 'activada' if action == 'active' else 'pausada'
        messages.success(request, f'Campaña {label} correctamente.')
    except Exception as e:
        logger.error(f"Failed to toggle campaign {campaign_id}: {e}", exc_info=True)
        messages.error(request, f'Error al cambiar estado de campaña: {str(e)}')

    return redirect('crm:mercadolibre:ads_list')


@login_required
def ad_campaign_budget(request, campaign_id):
    """
    Update a campaign's daily budget. POST only.
    """
    if request.method != 'POST':
        return redirect('crm:mercadolibre:ads_list')

    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        return redirect('crm:mercadolibre:status')

    try:
        new_budget = float(request.POST.get('daily_budget', 0))
        if new_budget <= 0:
            messages.error(request, 'El presupuesto debe ser mayor a 0.')
            return redirect('crm:mercadolibre:ads_list')

        from .integrations_mercadolibre_services import MercadoLibreAPIClient
        api = MercadoLibreAPIClient(integration)
        api.update_campaign_budget(campaign_id, new_budget)
        messages.success(request, f'Presupuesto actualizado a ${new_budget:.0f}/día.')
    except ValueError:
        messages.error(request, 'Presupuesto inválido.')
    except Exception as e:
        logger.error(f"Failed to update budget for campaign {campaign_id}: {e}", exc_info=True)
        messages.error(request, f'Error al actualizar presupuesto: {str(e)}')

    return redirect('crm:mercadolibre:ads_list')


# ---------------------------------------------------------------------------
# MODULE G: Offers & Promotions (Ofertas y Promociones)
# ---------------------------------------------------------------------------


@login_required
def promotions_list(request):
    """
    Lista de publicaciones con sus ofertas activas + campañas comerciales disponibles.
    Datos en tiempo real del API.
    """
    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        messages.warning(request, 'Conectá tu cuenta de MercadoLibre primero.')
        return redirect('crm:mercadolibre:status')

    from .integrations_mercadolibre_services import MercadoLibreAPIClient
    from .integrations_mercadolibre_models import MercadoLibreProduct
    api = MercadoLibreAPIClient(integration)

    active_tab = request.GET.get('tab', 'products')

    # --- Products with their promotions ---
    products_with_promos = []
    promos_error = None

    if active_tab == 'products':
        try:
            promos_data = api.get_seller_promotions()
            if isinstance(promos_data, list):
                promo_items = promos_data
            else:
                promo_items = promos_data.get('results', promos_data.get('items', []))

            promos_by_item = {}
            for p in promo_items:
                item_id = p.get('item_id', '')
                if item_id not in promos_by_item:
                    promos_by_item[item_id] = []
                promos_by_item[item_id].append({
                    'id': p.get('id', p.get('promotion_id', '')),
                    'deal_price': p.get('deal_price', 0),
                    'original_price': p.get('original_price', p.get('price', 0)),
                    'start_date': p.get('start_date', ''),
                    'finish_date': p.get('finish_date', ''),
                    'status': p.get('status', ''),
                    'type': p.get('type', p.get('promotion_type', '')),
                })

            products = MercadoLibreProduct.objects.filter(
                integration=integration,
                status='active',
            ).order_by('title')[:100]

            for product in products:
                promos = promos_by_item.get(product.ml_item_id, [])
                discount_pct = 0
                if promos and promos[0].get('original_price') and promos[0].get('deal_price'):
                    orig = float(promos[0]['original_price'])
                    deal = float(promos[0]['deal_price'])
                    if orig > 0:
                        discount_pct = round((1 - deal / orig) * 100)

                products_with_promos.append({
                    'product': product,
                    'promos': promos,
                    'has_promo': len(promos) > 0,
                    'discount_pct': discount_pct,
                })

        except Exception as e:
            promos_error = str(e)
            logger.warning(f"Failed to fetch seller promotions: {e}")

            products = MercadoLibreProduct.objects.filter(
                integration=integration,
                status='active',
            ).order_by('title')[:100]
            for product in products:
                products_with_promos.append({
                    'product': product,
                    'promos': [],
                    'has_promo': False,
                    'discount_pct': 0,
                })

    # --- Commercial campaigns (Hot Sale, CyberMonday, etc) ---
    campaigns = []
    campaigns_error = None

    if active_tab == 'campaigns':
        try:
            camps_data = api.get_available_campaigns()
            if isinstance(camps_data, list):
                campaigns = camps_data
            else:
                campaigns = camps_data.get('results', camps_data.get('promotions', []))
        except Exception as e:
            campaigns_error = str(e)
            logger.warning(f"Failed to fetch available campaigns: {e}")

    context = {
        'integration': integration,
        'active_tab': active_tab,
        'products_with_promos': products_with_promos,
        'promos_error': promos_error,
        'campaigns': campaigns,
        'campaigns_error': campaigns_error,
    }
    return render(request, 'crm/integrations/mercadolibre_promotions.html', context)


@login_required
def promotion_create(request, item_id):
    """Create a price discount on a product. POST only."""
    if request.method != 'POST':
        return redirect('crm:mercadolibre:promotions_list')

    company = request.user.company
    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        return redirect('crm:mercadolibre:status')

    try:
        deal_price = float(request.POST.get('deal_price', 0))
        finish_date = request.POST.get('finish_date', '')

        if deal_price <= 0:
            messages.error(request, 'El precio de oferta debe ser mayor a 0.')
            return redirect('crm:mercadolibre:promotions_list')

        if not finish_date:
            messages.error(request, 'Seleccioná una fecha de fin.')
            return redirect('crm:mercadolibre:promotions_list')

        start = timezone.now().strftime('%Y-%m-%dT%H:%M:%S.000-03:00')
        finish = f"{finish_date}T23:59:59.000-03:00"

        from .integrations_mercadolibre_services import MercadoLibreAPIClient
        api = MercadoLibreAPIClient(integration)
        api.create_item_promotion(item_id, deal_price, start, finish)

        messages.success(request, f'Oferta creada: ${deal_price:.0f} hasta {finish_date}.')

    except Exception as e:
        logger.error(f"Failed to create promotion for {item_id}: {e}", exc_info=True)
        messages.error(request, f'Error al crear oferta: {str(e)}')

    return redirect('crm:mercadolibre:promotions_list')


@login_required
def promotion_delete(request, item_id, promotion_id):
    """Delete/cancel a promotion. POST only."""
    if request.method != 'POST':
        return redirect('crm:mercadolibre:promotions_list')

    company = request.user.company
    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        return redirect('crm:mercadolibre:status')

    try:
        from .integrations_mercadolibre_services import MercadoLibreAPIClient
        api = MercadoLibreAPIClient(integration)
        api.delete_item_promotion(item_id, promotion_id)
        messages.success(request, 'Oferta eliminada correctamente.')
    except Exception as e:
        logger.error(f"Failed to delete promotion {promotion_id} for {item_id}: {e}", exc_info=True)
        messages.error(request, f'Error al eliminar oferta: {str(e)}')

    return redirect('crm:mercadolibre:promotions_list')


# ---------------------------------------------------------------------------
# MODULE H: Categories Index & Item Creation
# ---------------------------------------------------------------------------


def _fetch_category_detail(api, cat_id):
    """Fetch a single category detail (for picture URL). Returns dict or None."""
    try:
        return api.get_category(cat_id)
    except Exception:
        return None


def _sync_root_categories(api, site_id='MLA'):
    """Sync root categories from ML API into local cache if stale (>24h).
    Fetches individual category details in parallel to get picture URLs."""
    from datetime import timedelta as td
    from concurrent.futures import ThreadPoolExecutor
    cutoff = timezone.now() - td(hours=24)
    existing = MercadoLibreCategory.objects.filter(
        ml_parent_id='', site_id=site_id, synced_at__gte=cutoff,
    ).count()
    if existing > 0:
        return

    try:
        cats = api.get_site_categories(site_id)

        # Fetch individual details in parallel to get picture URLs
        with ThreadPoolExecutor(max_workers=6) as executor:
            details_map = {}
            futures = {
                executor.submit(_fetch_category_detail, api, c['id']): c['id']
                for c in cats
            }
            for future in futures:
                cat_id = futures[future]
                try:
                    details_map[cat_id] = future.result()
                except Exception:
                    details_map[cat_id] = None

        for c in cats:
            detail = details_map.get(c['id'])
            picture = ''
            if detail:
                picture = detail.get('picture', '') or ''
            MercadoLibreCategory.objects.update_or_create(
                ml_category_id=c['id'],
                defaults={
                    'name': c.get('name', ''),
                    'ml_parent_id': '',
                    'parent': None,
                    'path_from_root': [{'id': c['id'], 'name': c.get('name', '')}],
                    'picture': picture,
                    'total_items_in_this_category': c.get('total_items_in_this_category', 0),
                    'has_children': True,
                    'site_id': site_id,
                },
            )
    except Exception as e:
        logger.warning(f"Failed to sync root categories: {e}")


def _sync_category_children(api, category_id):
    """Sync a category's children from ML API into local cache.
    Fetches individual child details in parallel to get picture URLs."""
    from datetime import timedelta as td
    from concurrent.futures import ThreadPoolExecutor
    cutoff = timezone.now() - td(hours=24)
    existing = MercadoLibreCategory.objects.filter(
        ml_parent_id=category_id, synced_at__gte=cutoff,
    ).count()
    if existing > 0:
        return MercadoLibreCategory.objects.filter(ml_parent_id=category_id).order_by('name')

    try:
        cat_data = api.get_category(category_id)
        children = cat_data.get('children_categories', [])
        path = cat_data.get('path_from_root', [])

        parent_obj, _ = MercadoLibreCategory.objects.update_or_create(
            ml_category_id=category_id,
            defaults={
                'name': cat_data.get('name', ''),
                'path_from_root': path,
                'picture': cat_data.get('picture', '') or '',
                'total_items_in_this_category': cat_data.get('total_items_in_this_category', 0),
                'has_children': len(children) > 0,
            },
        )

        # Fetch individual child details in parallel to get picture URLs
        details_map = {}
        if children:
            with ThreadPoolExecutor(max_workers=6) as executor:
                futures = {
                    executor.submit(_fetch_category_detail, api, ch['id']): ch['id']
                    for ch in children
                }
                for future in futures:
                    ch_id = futures[future]
                    try:
                        details_map[ch_id] = future.result()
                    except Exception:
                        details_map[ch_id] = None

        for child in children:
            child_path = path + [{'id': child['id'], 'name': child.get('name', '')}]
            detail = details_map.get(child['id'])
            picture = ''
            child_has_children = True
            if detail:
                picture = detail.get('picture', '') or ''
                child_children = detail.get('children_categories', [])
                child_has_children = len(child_children) > 0
            MercadoLibreCategory.objects.update_or_create(
                ml_category_id=child['id'],
                defaults={
                    'name': child.get('name', ''),
                    'ml_parent_id': category_id,
                    'parent': parent_obj,
                    'path_from_root': child_path,
                    'picture': picture,
                    'total_items_in_this_category': child.get('total_items_in_this_category', 0),
                    'has_children': child_has_children,
                    'site_id': parent_obj.site_id,
                },
            )
        return MercadoLibreCategory.objects.filter(ml_parent_id=category_id).order_by('name')

    except Exception as e:
        logger.warning(f"Failed to sync children for category {category_id}: {e}")
        return MercadoLibreCategory.objects.filter(ml_parent_id=category_id).order_by('name')


@login_required
def categories_index(request):
    """Browseable category tree."""
    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        messages.warning(request, 'Conectá tu cuenta de MercadoLibre primero.')
        return redirect('crm:mercadolibre:status')

    from .integrations_mercadolibre_services import MercadoLibreAPIClient
    api = MercadoLibreAPIClient(integration)
    site_id = integration.site_id or 'MLA'

    parent_id = request.GET.get('parent', '')
    breadcrumb = []
    categories = []

    if parent_id:
        children_qs = _sync_category_children(api, parent_id)
        categories = list(children_qs)
        parent_cat = MercadoLibreCategory.objects.filter(ml_category_id=parent_id).first()
        if parent_cat and parent_cat.path_from_root:
            breadcrumb = parent_cat.path_from_root
    else:
        _sync_root_categories(api, site_id)
        categories = list(
            MercadoLibreCategory.objects.filter(ml_parent_id='', site_id=site_id).order_by('name')
        )

    context = {
        'integration': integration,
        'categories': categories,
        'parent_id': parent_id,
        'breadcrumb': breadcrumb,
    }
    return render(request, 'crm/integrations/mercadolibre_categories.html', context)


@login_required
def category_children_api(request, category_id):
    """JSON API endpoint for AJAX category drill-down."""
    company = request.user.company
    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        return JsonResponse({'error': 'No integration'}, status=400)

    from .integrations_mercadolibre_services import MercadoLibreAPIClient
    api = MercadoLibreAPIClient(integration)

    children_qs = _sync_category_children(api, category_id)
    children = [
        {
            'id': c.ml_category_id,
            'name': c.name,
            'has_children': c.has_children,
            'total_items': c.total_items_in_this_category,
            'picture': c.picture or '',
        }
        for c in children_qs
    ]

    parent_cat = MercadoLibreCategory.objects.filter(ml_category_id=category_id).first()
    path = parent_cat.path_from_root if parent_cat else []

    return JsonResponse({
        'children': children,
        'path_from_root': path,
        'has_children': len(children) > 0,
    })


@login_required
def root_categories_api(request):
    """JSON API: return root categories for the embedded browser in item_create."""
    company = request.user.company
    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        return JsonResponse({'error': 'No integration'}, status=400)

    from .integrations_mercadolibre_services import MercadoLibreAPIClient
    api = MercadoLibreAPIClient(integration)
    site_id = integration.site_id or 'MLA'

    _sync_root_categories(api, site_id)
    cats = MercadoLibreCategory.objects.filter(
        ml_parent_id='', site_id=site_id,
    ).order_by('name')
    categories = [
        {
            'id': c.ml_category_id,
            'name': c.name,
            'has_children': c.has_children,
            'total_items': c.total_items_in_this_category,
            'picture': c.picture or '',
        }
        for c in cats
    ]
    return JsonResponse({'categories': categories})


@login_required
def category_attributes_api(request, category_id):
    """JSON API: get required attributes for a category."""
    company = request.user.company
    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        return JsonResponse({'error': 'No integration'}, status=400)

    from .integrations_mercadolibre_services import MercadoLibreAPIClient
    api = MercadoLibreAPIClient(integration)

    try:
        attrs = api.get_category_attributes(category_id)
        filtered = []
        for attr in attrs:
            tags = attr.get('tags', {})
            if tags.get('required') or tags.get('catalog_required'):
                filtered.append({
                    'id': attr['id'],
                    'name': attr.get('name', attr['id']),
                    'type': attr.get('value_type', 'string'),
                    'required': True,
                    'values': [
                        {'id': v.get('id', ''), 'name': v.get('name', '')}
                        for v in attr.get('values', [])
                    ],
                    'hint': attr.get('hint', ''),
                })
        return JsonResponse({'attributes': filtered})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def predict_category_api(request):
    """JSON API: predict category from product title."""
    company = request.user.company
    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        return JsonResponse({'error': 'No integration'}, status=400)

    title = request.GET.get('q', '').strip()
    if not title:
        return JsonResponse({'predictions': []})

    from .integrations_mercadolibre_services import MercadoLibreAPIClient
    api = MercadoLibreAPIClient(integration)
    site_id = integration.site_id or 'MLA'

    try:
        results = api.predict_category(title, site_id)
        predictions = []
        if isinstance(results, list):
            for r in results[:5]:
                predictions.append({
                    'category_id': r.get('category_id', ''),
                    'category_name': r.get('category_name', ''),
                    'domain': r.get('domain_name', ''),
                })
        return JsonResponse({'predictions': predictions})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def item_create(request):
    """Create a new MercadoLibre listing from the CRM."""
    company = request.user.company

    integration = MercadoLibreIntegration.objects.filter(
        company=company, is_active=True
    ).first()

    if not integration:
        messages.warning(request, 'Conectá tu cuenta de MercadoLibre primero.')
        return redirect('crm:mercadolibre:status')

    from .integrations_mercadolibre_services import MercadoLibreAPIClient
    api = MercadoLibreAPIClient(integration)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category_id = request.POST.get('category_id', '').strip()
        category_name = request.POST.get('category_name', '').strip()
        price = request.POST.get('price', '0').strip()
        quantity = request.POST.get('available_quantity', '1').strip()
        condition = request.POST.get('condition', 'new')
        listing_type = request.POST.get('listing_type_id', 'gold_special')
        description = request.POST.get('description', '').strip()
        currency = request.POST.get('currency_id', 'ARS')
        pictures_urls = request.POST.get('pictures', '').strip()

        # Validation
        errors = []
        if not title:
            errors.append('El título es obligatorio.')
        if not category_id:
            errors.append('Seleccioná una categoría.')
        try:
            price_val = float(price)
            if price_val <= 0:
                errors.append('El precio debe ser mayor a 0.')
        except ValueError:
            errors.append('Precio inválido.')
        try:
            qty_val = int(quantity)
            if qty_val < 1:
                errors.append('La cantidad debe ser al menos 1.')
        except ValueError:
            errors.append('Cantidad inválida.')

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'crm/integrations/mercadolibre_item_create.html', {
                'integration': integration, 'form_data': request.POST,
            })

        # Build pictures array
        pictures = []
        if pictures_urls:
            for url in pictures_urls.split('\n'):
                url = url.strip()
                if url:
                    pictures.append({'source': url})

        # Build item payload
        item_data = {
            'title': title,
            'category_id': category_id,
            'price': float(price),
            'currency_id': currency,
            'available_quantity': int(quantity),
            'buying_mode': 'buy_it_now',
            'condition': condition,
            'listing_type_id': listing_type,
        }
        if pictures:
            item_data['pictures'] = pictures

        # Collect dynamic attributes
        attributes = []
        for key, value in request.POST.items():
            if key.startswith('attr_') and value.strip():
                attr_id = key[5:]
                attributes.append({'id': attr_id, 'value_name': value.strip()})
        if attributes:
            item_data['attributes'] = attributes

        try:
            result = api.create_item(item_data)
            new_item_id = result.get('id', '')

            # Upload description if provided
            if description and new_item_id:
                try:
                    api.upload_item_description(new_item_id, description)
                except Exception as desc_err:
                    logger.warning(f"Failed to upload description for {new_item_id}: {desc_err}")

            # Save to local DB
            MercadoLibreProduct.objects.update_or_create(
                ml_item_id=new_item_id,
                defaults={
                    'integration': integration,
                    'company': company,
                    'title': result.get('title', title),
                    'category_id': result.get('category_id', category_id),
                    'price': result.get('price', price),
                    'currency_id': result.get('currency_id', 'ARS'),
                    'available_quantity': result.get('available_quantity', int(quantity)),
                    'condition': result.get('condition', condition),
                    'listing_type_id': result.get('listing_type_id', listing_type),
                    'permalink': result.get('permalink', ''),
                    'thumbnail': result.get('thumbnail', ''),
                    'status': result.get('status', 'active'),
                    'description': description,
                    'raw_data': result,
                    'last_synced_at': timezone.now(),
                },
            )

            messages.success(request, f'Publicación creada exitosamente: {new_item_id}')
            return redirect('crm:mercadolibre:products_list')

        except Exception as e:
            logger.error(f"Failed to create ML item: {e}", exc_info=True)
            error_detail = str(e)
            try:
                err_body = e.response.text
                err_data = json.loads(err_body)
                if 'cause' in err_data:
                    causes = err_data['cause']
                    if isinstance(causes, list) and causes:
                        error_detail = '; '.join(c.get('message', str(c)) for c in causes)
                elif 'message' in err_data:
                    error_detail = err_data['message']
            except Exception:
                pass
            messages.error(request, f'Error al crear publicación: {error_detail}')
            return render(request, 'crm/integrations/mercadolibre_item_create.html', {
                'integration': integration, 'form_data': request.POST,
            })

    # GET: show empty form
    return render(request, 'crm/integrations/mercadolibre_item_create.html', {
        'integration': integration, 'form_data': {},
    })
