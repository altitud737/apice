from django.db import models
from django.conf import settings
from .models import TenantModel


class WhatsAppIntegration(TenantModel):
    """
    Modelo para almacenar la configuración de WhatsApp Business API
    """
    phone_number_id = models.CharField(max_length=255, help_text='ID del número de teléfono de WhatsApp Business')
    business_account_id = models.CharField(max_length=255, help_text='ID de la cuenta de WhatsApp Business')
    access_token = models.CharField(max_length=500, help_text='Token de acceso permanente de Meta')
    verify_token = models.CharField(max_length=255, help_text='Token de verificación para el webhook')
    webhook_url = models.URLField(blank=True, null=True, help_text='URL actual del webhook (ngrok)')
    phone_number = models.CharField(max_length=50, blank=True, null=True, help_text='Número de teléfono formateado')
    is_active = models.BooleanField(default=True)
    
    # Configuración adicional
    auto_create_leads = models.BooleanField(default=True, help_text='Crear leads automáticamente de mensajes nuevos')
    auto_create_contacts = models.BooleanField(default=False, help_text='Crear contactos automáticamente')
    
    class Meta:
        db_table = 'crm_whatsapp_integration'
        verbose_name = 'Integración de WhatsApp'
        verbose_name_plural = 'Integraciones de WhatsApp'
    
    def __str__(self):
        return f"WhatsApp - {self.phone_number or self.phone_number_id}"


class WhatsAppMessage(TenantModel):
    """
    Modelo para almacenar mensajes de WhatsApp (enviados y recibidos)
    """
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Texto'),
        ('image', 'Imagen'),
        ('document', 'Documento'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('location', 'Ubicación'),
        ('contacts', 'Contactos'),
        ('template', 'Plantilla'),
    ]
    
    DIRECTION_CHOICES = [
        ('inbound', 'Entrante'),
        ('outbound', 'Saliente'),
    ]
    
    STATUS_CHOICES = [
        ('sent', 'Enviado'),
        ('delivered', 'Entregado'),
        ('read', 'Leído'),
        ('failed', 'Fallido'),
        ('received', 'Recibido'),
    ]
    
    integration = models.ForeignKey(WhatsAppIntegration, on_delete=models.CASCADE, related_name='messages')
    message_id = models.CharField(max_length=255, unique=True, help_text='ID del mensaje de WhatsApp')
    wamid = models.CharField(max_length=255, blank=True, null=True, help_text='WhatsApp Message ID')
    
    # Información del contacto
    from_number = models.CharField(max_length=50, help_text='Número de teléfono del remitente')
    to_number = models.CharField(max_length=50, help_text='Número de teléfono del destinatario')
    contact_name = models.CharField(max_length=255, blank=True, null=True, help_text='Nombre del contacto')
    
    # Contenido del mensaje
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text')
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    
    # Contenido
    text_body = models.TextField(blank=True, null=True, help_text='Contenido del mensaje de texto')
    media_url = models.URLField(blank=True, null=True, help_text='URL del archivo multimedia')
    media_id = models.CharField(max_length=255, blank=True, null=True, help_text='ID del archivo multimedia')
    caption = models.TextField(blank=True, null=True, help_text='Descripción de la imagen/video')
    
    # Metadata
    timestamp = models.DateTimeField(help_text='Timestamp del mensaje de WhatsApp')
    raw_data = models.JSONField(blank=True, null=True, help_text='Datos completos del webhook')
    
    # Relaciones con CRM
    lead = models.ForeignKey('Lead', on_delete=models.SET_NULL, null=True, blank=True, related_name='whatsapp_messages')
    contact = models.ForeignKey('Contact', on_delete=models.SET_NULL, null=True, blank=True, related_name='whatsapp_messages')
    
    # Usuario que envió (si es outbound)
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'crm_whatsapp_message'
        ordering = ['-timestamp']
        verbose_name = 'Mensaje de WhatsApp'
        verbose_name_plural = 'Mensajes de WhatsApp'
    
    def __str__(self):
        direction_arrow = '→' if self.direction == 'outbound' else '←'
        return f"{direction_arrow} {self.from_number} - {self.text_body[:50] if self.text_body else self.message_type}"


class WhatsAppWebhookEvent(TenantModel):
    """
    Modelo para registrar todos los eventos del webhook de WhatsApp
    """
    EVENT_TYPE_CHOICES = [
        ('message', 'Mensaje'),
        ('status', 'Estado'),
        ('error', 'Error'),
        ('other', 'Otro'),
    ]
    
    integration = models.ForeignKey(WhatsAppIntegration, on_delete=models.CASCADE, related_name='webhook_events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    raw_payload = models.JSONField(help_text='Payload completo del webhook')
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'crm_whatsapp_webhook_event'
        ordering = ['-created_at']
        verbose_name = 'Evento de Webhook WhatsApp'
        verbose_name_plural = 'Eventos de Webhook WhatsApp'
    
    def __str__(self):
        return f"{self.event_type} - {self.created_at}"


class WhatsAppTemplate(TenantModel):
    """
    Modelo para almacenar plantillas de mensajes de WhatsApp aprobadas por Meta
    """
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
    ]
    
    integration = models.ForeignKey(WhatsAppIntegration, on_delete=models.CASCADE, related_name='templates')
    name = models.CharField(max_length=255, help_text='Nombre de la plantilla en Meta')
    language = models.CharField(max_length=10, default='es', help_text='Código de idioma (ej: es, en)')
    category = models.CharField(max_length=50, help_text='Categoría de la plantilla')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Contenido
    header_text = models.CharField(max_length=60, blank=True, null=True)
    body_text = models.TextField(help_text='Texto del cuerpo de la plantilla')
    footer_text = models.CharField(max_length=60, blank=True, null=True)
    
    # Metadata
    template_id = models.CharField(max_length=255, blank=True, null=True, help_text='ID de la plantilla en Meta')
    components = models.JSONField(blank=True, null=True, help_text='Componentes de la plantilla')
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'crm_whatsapp_template'
        ordering = ['name']
        verbose_name = 'Plantilla de WhatsApp'
        verbose_name_plural = 'Plantillas de WhatsApp'
    
    def __str__(self):
        return f"{self.name} ({self.language})"
