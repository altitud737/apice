"""
URLs para gestión de email
"""
from django.urls import path
from . import mail_views

urlpatterns = [
    # OAuth (solo para conectar después de que el admin configure)
    path('connect/', mail_views.mail_connect, name='mail_connect'),
    path('callback/', mail_views.mail_callback, name='mail_callback'),
    path('disconnect/', mail_views.mail_disconnect, name='mail_disconnect'),
    
    # Bandeja de entrada
    path('inbox/', mail_views.mail_inbox, name='mail_inbox'),
    path('view/<str:message_id>/', mail_views.mail_view, name='mail_view'),
    
    # Componer y enviar
    path('compose/', mail_views.mail_compose, name='mail_compose'),
    
    # Acciones
    path('delete/<str:message_id>/', mail_views.mail_delete, name='mail_delete'),
    
    # API
    path('status/', mail_views.mail_status, name='mail_status'),
]
