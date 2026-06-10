from django.db import models
from django.conf import settings
from django.utils import timezone

class TenantModel(models.Model):
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Pipeline(TenantModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_default = models.BooleanField(default=False)
    color = models.CharField(max_length=7, default='#10b981')  # emerald-500
    
    class Meta:
        db_table = 'crm_pipeline'
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        return self.name

class Contact(TenantModel):
    CONTACT_TYPE_CHOICES = [
        ('persona', 'Persona'),
        ('empresa', 'Empresa'),
    ]
    
    SOURCE_CHOICES = [
        ('website', 'Sitio Web'),
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('mercadolibre', 'MercadoLibre'),
        ('whatsapp', 'WhatsApp'),
        ('landing', 'Landing Page'),
        ('google_ads', 'Google Ads'),
        ('referral', 'Referido'),
        ('manual', 'Manual'),
        ('other', 'Otro'),
    ]
    
    contact_type = models.CharField(max_length=20, choices=CONTACT_TYPE_CHOICES, default='persona')
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, default='Nuevo')
    interest_level = models.CharField(max_length=50, default='Medio')
    next_action_date = models.DateField(blank=True, null=True)
    source = models.CharField(max_length=100, choices=SOURCE_CHOICES, default='manual', help_text='Origen del contacto')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='owned_contacts')

    class Meta:
        db_table = 'crm_contact'

    def __str__(self):
        return self.name
    
    def get_source_icon(self):
        """Retorna el emoji/icono para el origen del contacto"""
        icons = {
            'website': '🌐',
            'facebook': '📘',
            'instagram': '📸',
            'mercadolibre': '🛒',
            'whatsapp': '🟢',
            'landing': '📄',
            'google_ads': '📢',
            'referral': '👥',
            'manual': '✍️',
            'other': '📌',
        }
        return icons.get(self.source, '✍️')

class Stage(TenantModel):
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name='stages', null=True, blank=True)
    name = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'crm_stage'
        ordering = ['order']

    def __str__(self):
        return self.name

class Deal(TenantModel):
    title = models.CharField(max_length=255)
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    probability = models.PositiveIntegerField(default=50)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='deals')
    stage = models.ForeignKey(Stage, on_delete=models.CASCADE, related_name='deals')
    expected_close_date = models.DateField(blank=True, null=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='owned_deals')

    class Meta:
        db_table = 'crm_deal'

    def __str__(self):
        return self.title

class Activity(TenantModel):
    TYPE_CHOICES = [
        ('Note', 'Nota'),
        ('StatusChange', 'Cambio de Estado'),
        ('DealCreated', 'Oportunidad Creada'),
        ('TaskCompleted', 'Tarea Completada'),
    ]
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='activities')
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='Note')
    description = models.TextField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'crm_activity'
        ordering = ['-created_at']

class Task(TenantModel):
    PRIORITY_CHOICES = [
        ('Alta', 'Alta'),
        ('Media', 'Media'),
        ('Baja', 'Baja'),
    ]
    title = models.CharField(max_length=255)
    due_date = models.DateField(blank=True, null=True)
    priority = models.CharField(max_length=50, choices=PRIORITY_CHOICES, default='Media')
    completed = models.BooleanField(default=False)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_tasks')

    class Meta:
        db_table = 'crm_task'

    def __str__(self):
        return self.title

class MessageTemplate(TenantModel):
    name = models.CharField(max_length=255)
    message = models.TextField()
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'crm_messagetemplate'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Lead(TenantModel):
    SOURCE_CHOICES = [
        ('website', 'Sitio Web'),
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('mercadolibre', 'MercadoLibre'),
        ('whatsapp', 'WhatsApp'),
        ('landing', 'Landing Page'),
        ('google_ads', 'Google Ads'),
        ('referral', 'Referido'),
        ('other', 'Otro'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'Nuevo'),
        ('contacted', 'Contactado'),
        ('qualified', 'Calificado'),
        ('converted', 'Convertido'),
        ('lost', 'Perdido'),
    ]
    
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    source = models.CharField(max_length=100, choices=SOURCE_CHOICES, default='website')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    metadata = models.JSONField(null=True, blank=True, help_text='Datos adicionales como página, campaña, IP, etc.')
    converted_to_contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='original_lead')
    
    class Meta:
        db_table = 'crm_lead'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.email}"
    
    def get_source_icon(self):
        """Retorna el emoji/icono para el origen del lead"""
        icons = {
            'website': '🌐',
            'facebook': '📘',
            'instagram': '📸',
            'mercadolibre': '🛒',
            'whatsapp': '🟢',
            'landing': '📄',
            'google_ads': '📢',
            'referral': '👥',
            'other': '📌',
        }
        return icons.get(self.source, '📌')


# Importar modelos de MercadoLibre
from .integrations_mercadolibre_models import (
    MercadoLibreOAuthState,
    MercadoLibreIntegration,
    MercadoLibreWebhookEvent,
    MercadoLibreProduct,
    MercadoLibreOrder,
    MercadoLibreOrderItem,
    MercadoLibreMessage,
    MercadoLibreQuestion,
    MercadoLibreReplyTemplate,
)

# Importar modelos de Mail
from .mail_models import ZohoMailIntegration, EmailMessage, EmailDraft

# Importar modelos de WhatsApp
from .whatsapp_models import WhatsAppIntegration, WhatsAppMessage, WhatsAppWebhookEvent, WhatsAppTemplate
