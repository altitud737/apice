"""
Context processors para ERP
"""
from accounts.models import UserNotification


def unread_notifications(request):
    """Agrega el conteo de notificaciones no leídas al contexto global"""
    if request.user.is_authenticated and not request.user.is_superadmin:
        count = UserNotification.objects.filter(
            user=request.user,
            is_read=False,
            notification__is_active=True
        ).count()
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}


def mercadolibre_integration(request):
    """Agrega estado de integración ML, conteo de preguntas pendientes y mensajes no leídos al contexto global"""
    defaults = {
        'ml_integration_active': False,
        'ml_pending_questions_count': 0,
        'ml_unread_messages_count': 0,
    }
    if request.user.is_authenticated and not request.user.is_superadmin and hasattr(request, 'company'):
        from crm.integrations_mercadolibre_models import (
            MercadoLibreIntegration, MercadoLibreQuestion, MercadoLibreMessage,
        )
        active_integration = MercadoLibreIntegration.objects.filter(
            company=request.company, is_active=True
        ).first()
        if active_integration:
            defaults['ml_integration_active'] = True
            defaults['ml_pending_questions_count'] = MercadoLibreQuestion.objects.filter(
                integration=active_integration,
                status='UNANSWERED',
                is_ignored=False,
            ).count()
            defaults['ml_unread_messages_count'] = MercadoLibreMessage.objects.filter(
                integration=active_integration,
                is_from_buyer=True,
                read_at__isnull=True,
            ).exclude(pack_id='').values('pack_id').distinct().count()
    return defaults
