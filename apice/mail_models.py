"""
Modelos para integración de Zoho Mail
Permite a cada empresa conectar su cuenta de Zoho Mail
"""
from django.db import models
from accounts.models import Company
from django.utils import timezone


class ZohoMailIntegration(models.Model):
    """
    Almacena las credenciales de Zoho Mail por empresa
    """
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name='zoho_mail_integration'
    )
    
    # Credenciales de Zoho Mail
    client_id = models.CharField(max_length=255, help_text="Zoho Mail Client ID")
    client_secret = models.CharField(max_length=255, help_text="Zoho Mail Client Secret")
    refresh_token = models.TextField(blank=True, help_text="OAuth Refresh Token")
    access_token = models.TextField(blank=True, help_text="OAuth Access Token")
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Configuración
    account_id = models.CharField(max_length=255, blank=True, help_text="Zoho Account ID")
    email_address = models.EmailField(help_text="Email principal de la cuenta")
    region = models.CharField(
        max_length=20,
        default='com',
        choices=[
            ('com', 'US - mail.zoho.com'),
            ('eu', 'EU - mail.zoho.eu'),
            ('in', 'IN - mail.zoho.in'),
            ('com.au', 'AU - mail.zoho.com.au'),
            ('jp', 'JP - mail.zoho.jp'),
        ],
        help_text="Región de Zoho Mail"
    )
    
    # Estado
    is_active = models.BooleanField(default=False)
    last_sync = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'crm_zohomailintegration'
        verbose_name = "Integración Zoho Mail"
        verbose_name_plural = "Integraciones Zoho Mail"
    
    def __str__(self):
        return f"Zoho Mail - {self.company.name} ({self.email_address})"
    
    @property
    def is_token_valid(self):
        """Verifica si el token de acceso es válido"""
        if not self.token_expires_at:
            return False
        return timezone.now() < self.token_expires_at
    
    @property
    def api_base_url(self):
        """Retorna la URL base de la API según la región"""
        return f"https://mail.zoho.{self.region}/api"


class EmailMessage(models.Model):
    """
    Almacena emails sincronizados desde Zoho Mail
    """
    integration = models.ForeignKey(
        ZohoMailIntegration,
        on_delete=models.CASCADE,
        related_name='emails'
    )
    
    # Identificadores
    message_id = models.CharField(max_length=255, unique=True, help_text="ID del mensaje en Zoho")
    thread_id = models.CharField(max_length=255, blank=True)
    
    # Remitente y destinatarios
    from_address = models.EmailField()
    from_name = models.CharField(max_length=255, blank=True)
    to_addresses = models.TextField(help_text="JSON con lista de destinatarios")
    cc_addresses = models.TextField(blank=True, help_text="JSON con lista de CC")
    bcc_addresses = models.TextField(blank=True, help_text="JSON con lista de BCC")
    
    # Contenido
    subject = models.CharField(max_length=500)
    body_text = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    
    # Metadata
    date_sent = models.DateTimeField()
    date_received = models.DateTimeField()
    
    # Estado
    is_read = models.BooleanField(default=False)
    is_starred = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=False)
    folder = models.CharField(max_length=100, default='inbox')
    
    # Adjuntos
    has_attachments = models.BooleanField(default=False)
    attachments_data = models.TextField(blank=True, help_text="JSON con info de adjuntos")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'crm_emailmessage'
        verbose_name = "Email"
        verbose_name_plural = "Emails"
        ordering = ['-date_received']
        indexes = [
            models.Index(fields=['integration', 'folder', '-date_received']),
            models.Index(fields=['message_id']),
        ]
    
    def __str__(self):
        return f"{self.subject} - {self.from_address}"


class EmailDraft(models.Model):
    """
    Borradores de emails creados en Apice
    """
    integration = models.ForeignKey(
        ZohoMailIntegration,
        on_delete=models.CASCADE,
        related_name='drafts'
    )
    
    # Destinatarios
    to_addresses = models.TextField(help_text="Emails separados por coma")
    cc_addresses = models.TextField(blank=True)
    bcc_addresses = models.TextField(blank=True)
    
    # Contenido
    subject = models.CharField(max_length=500)
    body = models.TextField()
    
    # Estado
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'crm_emaildraft'
        verbose_name = "Borrador de Email"
        verbose_name_plural = "Borradores de Email"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Borrador: {self.subject}"
