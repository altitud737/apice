"""
URLs para la integración de WhatsApp Business API
"""
from django.urls import path
from . import whatsapp_views

app_name = 'whatsapp'

urlpatterns = [
    # Configuración
    path('settings/', whatsapp_views.whatsapp_settings, name='settings'),
    
    # Mensajes
    path('messages/', whatsapp_views.whatsapp_messages, name='messages'),
    path('send/', whatsapp_views.send_whatsapp_message, name='send_message'),
]
