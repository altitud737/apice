"""
Vistas de notificaciones del sistema para usuarios
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from accounts.models import UserNotification


@login_required
def notifications_list(request):
    """Lista de notificaciones del usuario"""
    notifications = UserNotification.objects.filter(
        user=request.user,
        notification__is_active=True
    ).select_related('notification')
    
    unread_count = notifications.filter(is_read=False).count()
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'crm/notifications.html', context)


@login_required
@require_POST
def notification_mark_read(request, notification_id):
    """Marcar una notificación como leída"""
    user_notification = get_object_or_404(
        UserNotification,
        id=notification_id,
        user=request.user
    )
    user_notification.is_read = True
    user_notification.read_at = timezone.now()
    user_notification.save()
    
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def notifications_mark_all_read(request):
    """Marcar todas las notificaciones como leídas"""
    UserNotification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True, read_at=timezone.now())
    
    return JsonResponse({'status': 'ok'})
