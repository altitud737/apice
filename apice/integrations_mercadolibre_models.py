"""
Modelos para integración con MercadoLibre
"""
from django.db import models
from django.utils import timezone
from datetime import timedelta
from accounts.models import User, Company


class MercadoLibreOAuthState(models.Model):
    """
    Almacena tokens de state OAuth temporalmente para validar callbacks.
    Se usa en lugar de session para que el callback funcione sin login_required.
    """
    state = models.CharField(max_length=255, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'mercadolibre_oauth_states'
        indexes = [
            models.Index(fields=['state', 'created_at']),
        ]
    
    def is_valid(self):
        """State válido por 10 minutos"""
        return timezone.now() < self.created_at + timedelta(minutes=10)
    
    @classmethod
    def cleanup_expired(cls):
        """Limpia states expirados (más de 10 minutos)"""
        cutoff = timezone.now() - timedelta(minutes=10)
        cls.objects.filter(created_at__lt=cutoff).delete()


class MercadoLibreIntegration(models.Model):
    """
    Credenciales OAuth de MercadoLibre por empresa (multi-tenant).
    Cada empresa puede tener una cuenta de ML conectada.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='mercadolibre_integrations',
        help_text='Empresa dueña de esta integración',
        null=True,
    )
    connected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ml_integrations_connected',
        help_text='Usuario que conectó esta integración'
    )

    # Datos de MercadoLibre
    ml_user_id = models.CharField(max_length=100, unique=True, db_index=True)
    nickname = models.CharField(max_length=255, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    site_id = models.CharField(max_length=10, default='MLA', help_text='Sitio ML (MLA=Argentina)')

    # Tokens OAuth
    access_token = models.TextField()
    refresh_token = models.TextField()
    token_expires_at = models.DateTimeField()

    # Estado
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    auto_reply_enabled = models.BooleanField(
        default=False,
        help_text='Responder automáticamente preguntas usando plantillas con keywords'
    )

    class Meta:
        db_table = 'mercadolibre_integrations'
        verbose_name = 'Integración MercadoLibre'
        verbose_name_plural = 'Integraciones MercadoLibre'
        ordering = ['-created_at']

    def __str__(self):
        return f"ML: {self.nickname or self.ml_user_id} ({self.company.name})"

    def is_token_expired(self):
        return timezone.now() >= self.token_expires_at

    def needs_refresh(self):
        return timezone.now() >= (self.token_expires_at - timedelta(hours=1))


class MercadoLibreProduct(models.Model):
    """
    Publicación/Item de MercadoLibre sincronizado
    """
    integration = models.ForeignKey(
        MercadoLibreIntegration,
        on_delete=models.CASCADE,
        related_name='products'
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='ml_products')

    ml_item_id = models.CharField(max_length=50, unique=True, db_index=True)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, default='')
    category_id = models.CharField(max_length=50, blank=True, default='')
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency_id = models.CharField(max_length=10, default='ARS')
    available_quantity = models.IntegerField(default=0)
    sold_quantity = models.IntegerField(default=0)
    condition = models.CharField(max_length=20, default='new')
    listing_type_id = models.CharField(max_length=50, blank=True, default='')
    permalink = models.URLField(max_length=500, blank=True, default='')
    thumbnail = models.URLField(max_length=500, blank=True, default='')
    status = models.CharField(max_length=30, default='active', db_index=True)

    last_synced_at = models.DateTimeField(null=True, blank=True)
    raw_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mercadolibre_products'
        verbose_name = 'Producto MercadoLibre'
        verbose_name_plural = 'Productos MercadoLibre'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.ml_item_id}: {self.title}"


class MercadoLibreOrder(models.Model):
    """
    Orden de MercadoLibre → se mapea a Deal en el CRM
    """
    STATUS_CHOICES = [
        ('confirmed', 'Confirmada'),
        ('payment_required', 'Pago Requerido'),
        ('payment_in_process', 'Pago en Proceso'),
        ('paid', 'Pagada'),
        ('partially_paid', 'Parcialmente Pagada'),
        ('cancelled', 'Cancelada'),
        ('invalid', 'Inválida'),
    ]

    integration = models.ForeignKey(
        MercadoLibreIntegration,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='ml_orders')

    ml_order_id = models.BigIntegerField(unique=True, db_index=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='confirmed')
    status_detail = models.CharField(max_length=100, blank=True, default='')

    # Comprador
    buyer_id = models.BigIntegerField(db_index=True)
    buyer_nickname = models.CharField(max_length=255, blank=True, default='')
    buyer_first_name = models.CharField(max_length=255, blank=True, default='')
    buyer_last_name = models.CharField(max_length=255, blank=True, default='')
    buyer_email = models.EmailField(blank=True, default='')
    buyer_phone = models.CharField(max_length=50, blank=True, default='')

    # Montos
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency_id = models.CharField(max_length=10, default='ARS')

    # Envío
    shipping_id = models.BigIntegerField(null=True, blank=True)
    shipping_status = models.CharField(max_length=50, blank=True, default='')
    shipping_tracking_number = models.CharField(max_length=100, blank=True, default='')
    shipping_carrier = models.CharField(max_length=100, blank=True, default='')
    shipping_receiver_address = models.JSONField(null=True, blank=True, help_text='Dirección del comprador')

    # Pago
    payment_method = models.CharField(max_length=50, blank=True, default='')

    # Relaciones CRM
    contact = models.ForeignKey(
        'apice.Contact',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ml_orders',
        help_text='Contacto CRM creado a partir del comprador'
    )
    deal = models.ForeignKey(
        'apice.Deal',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ml_orders',
        help_text='Deal CRM creado a partir de la orden'
    )
    lead = models.ForeignKey(
        'apice.Lead',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ml_orders',
        help_text='Lead CRM creado a partir de la orden'
    )

    # Fechas ML
    date_created = models.DateTimeField(null=True, blank=True)
    date_closed = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(null=True, blank=True)

    raw_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mercadolibre_orders'
        verbose_name = 'Orden MercadoLibre'
        verbose_name_plural = 'Órdenes MercadoLibre'
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['buyer_id']),
            models.Index(fields=['status', 'date_created']),
        ]

    def __str__(self):
        return f"Orden #{self.ml_order_id} - {self.buyer_nickname} (${self.total_amount})"


class MercadoLibreOrderItem(models.Model):
    """
    Items individuales dentro de una orden
    """
    order = models.ForeignKey(
        MercadoLibreOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        MercadoLibreProduct,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='order_items'
    )

    ml_item_id = models.CharField(max_length=50)
    title = models.CharField(max_length=500)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency_id = models.CharField(max_length=10, default='ARS')
    category_id = models.CharField(max_length=50, blank=True, default='')
    thumbnail = models.URLField(max_length=500, blank=True, default='')
    variation_id = models.BigIntegerField(null=True, blank=True)
    variation_attributes = models.JSONField(null=True, blank=True, help_text='Ej: [{"name": "Color", "value": "Azul"}]')

    class Meta:
        db_table = 'mercadolibre_order_items'
        verbose_name = 'Item de Orden MercadoLibre'
        verbose_name_plural = 'Items de Orden MercadoLibre'

    def __str__(self):
        return f"{self.title} x{self.quantity}"


class MercadoLibreMessage(models.Model):
    """
    Mensajes de MercadoLibre (post-venta) → se mapean al Inbox del CRM
    """
    integration = models.ForeignKey(
        MercadoLibreIntegration,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='ml_messages')

    ml_message_id = models.CharField(max_length=100, unique=True, db_index=True)
    pack_id = models.CharField(max_length=100, blank=True, default='', db_index=True)
    order = models.ForeignKey(
        MercadoLibreOrder,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='messages'
    )

    # Participantes
    sender_id = models.BigIntegerField()
    sender_nickname = models.CharField(max_length=255, blank=True, default='')
    receiver_id = models.BigIntegerField()
    is_from_buyer = models.BooleanField(default=True)

    # Contenido
    text = models.TextField(blank=True, default='')
    message_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, default='available')

    # CRM
    contact = models.ForeignKey(
        'apice.Contact',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ml_messages'
    )

    # Inbox tracking
    read_at = models.DateTimeField(null=True, blank=True, help_text='Fecha en que se leyó el mensaje')

    raw_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mercadolibre_messages'
        verbose_name = 'Mensaje MercadoLibre'
        verbose_name_plural = 'Mensajes MercadoLibre'
        ordering = ['-message_date']

    def __str__(self):
        direction = "←" if self.is_from_buyer else "→"
        return f"{direction} {self.sender_nickname}: {self.text[:50]}"


class MercadoLibreQuestion(models.Model):
    """
    Preguntas pre-venta en publicaciones → se mapean a Leads
    """
    STATUS_CHOICES = [
        ('UNANSWERED', 'Sin Responder'),
        ('ANSWERED', 'Respondida'),
        ('CLOSED_UNANSWERED', 'Cerrada sin Respuesta'),
        ('UNDER_REVIEW', 'En Revisión'),
        ('DELETED', 'Eliminada'),
    ]

    integration = models.ForeignKey(
        MercadoLibreIntegration,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='ml_questions')

    ml_question_id = models.BigIntegerField(unique=True, db_index=True)
    ml_item_id = models.CharField(max_length=50, db_index=True)

    # Pregunta
    from_id = models.BigIntegerField(db_index=True)
    from_nickname = models.CharField(max_length=255, blank=True, default='')
    text = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='UNANSWERED')
    date_created = models.DateTimeField(null=True, blank=True)

    # Respuesta
    answer_text = models.TextField(blank=True, default='')
    answer_date = models.DateTimeField(null=True, blank=True)

    # Producto relacionado
    product = models.ForeignKey(
        MercadoLibreProduct,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='questions'
    )

    # CRM
    lead = models.ForeignKey(
        'apice.Lead',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ml_questions'
    )

    # Auto-reply tracking
    auto_replied = models.BooleanField(default=False)
    auto_reply_template = models.ForeignKey(
        'MercadoLibreReplyTemplate',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='questions_answered',
        help_text='Template usado para la respuesta automática'
    )

    # Módulo A: Bandeja de preguntas
    answered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ml_questions_answered',
        help_text='Usuario que respondió manualmente'
    )
    is_ignored = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    raw_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mercadolibre_questions'
        verbose_name = 'Pregunta MercadoLibre'
        verbose_name_plural = 'Preguntas MercadoLibre'
        ordering = ['-date_created']

    def __str__(self):
        return f"Q#{self.ml_question_id} - {self.from_nickname}: {self.text[:50]}"


class MercadoLibreReplyTemplate(models.Model):
    """
    Plantillas de respuesta reutilizables para MercadoLibre.
    Sirven para respuesta rápida manual Y para auto-reply (si tiene keywords).
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='ml_reply_templates'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ml_reply_templates'
    )

    name = models.CharField(max_length=200, help_text='Nombre identificador de la plantilla')
    keywords = models.JSONField(
        default=list,
        blank=True,
        help_text='Keywords que activan auto-reply. Vacío = solo respuesta manual.'
    )
    response_text = models.TextField(help_text='Texto de la respuesta')
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(
        default=0,
        help_text='Mayor prioridad se evalúa primero (0 = normal)'
    )

    # Dónde se puede usar como respuesta rápida
    usable_in_questions = models.BooleanField(
        default=True,
        help_text='Disponible como respuesta rápida en preguntas pre-venta'
    )
    usable_in_messages = models.BooleanField(
        default=False,
        help_text='Disponible como respuesta rápida en mensajes post-venta'
    )

    # Métricas
    times_used = models.IntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mercadolibre_reply_templates'
        verbose_name = 'Plantilla de Respuesta ML'
        verbose_name_plural = 'Plantillas de Respuesta ML'
        ordering = ['-priority', 'name']

    def __str__(self):
        keywords_str = ', '.join(self.keywords[:3]) if self.keywords else 'solo manual'
        return f"{self.name} ({keywords_str})"

    def is_auto_reply_capable(self):
        return bool(self.keywords)


class MercadoLibreCategory(models.Model):
    """
    Categorías de MercadoLibre cacheadas localmente para navegación rápida.
    Se sincronizan desde la API de ML bajo demanda.
    """
    ml_category_id = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=300)
    ml_parent_id = models.CharField(max_length=50, blank=True, default='', db_index=True,
                                     help_text='ML category_id del padre (string)')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='children_set',
    )
    path_from_root = models.JSONField(
        default=list, blank=True,
        help_text='Lista de {id, name} desde la raíz hasta esta categoría',
    )
    picture = models.URLField(max_length=500, blank=True, default='')
    total_items_in_this_category = models.IntegerField(default=0)
    has_children = models.BooleanField(default=True)
    site_id = models.CharField(max_length=10, default='MLA')

    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mercadolibre_categories'
        verbose_name = 'Categoría MercadoLibre'
        verbose_name_plural = 'Categorías MercadoLibre'
        ordering = ['name']
        indexes = [
            models.Index(fields=['ml_parent_id', 'site_id']),
        ]

    def __str__(self):
        return f"{self.ml_category_id}: {self.name}"

    @property
    def breadcrumb(self):
        """Return path_from_root as a readable string."""
        return ' > '.join(item.get('name', '') for item in (self.path_from_root or []))


class MercadoLibreWebhookEvent(models.Model):
    """
    Eventos de webhook para procesamiento y auditoría
    """
    TOPIC_CHOICES = [
        ('messages', 'Mensajes'),
        ('questions', 'Preguntas'),
        ('orders_v2', 'Órdenes'),
        ('items', 'Publicaciones'),
        ('shipments', 'Envíos'),
        ('claims', 'Reclamos'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('processed', 'Procesado'),
        ('failed', 'Fallido'),
        ('ignored', 'Ignorado'),
    ]

    integration = models.ForeignKey(
        MercadoLibreIntegration,
        on_delete=models.CASCADE,
        related_name='webhook_events',
        null=True, blank=True
    )

    topic = models.CharField(max_length=50)
    resource = models.CharField(max_length=500)
    ml_user_id = models.CharField(max_length=100, db_index=True)
    application_id = models.CharField(max_length=50, blank=True, default='')
    attempts = models.IntegerField(default=1)
    sent_date = models.DateTimeField(null=True, blank=True)

    raw_payload = models.JSONField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    error_message = models.TextField(blank=True, default='')
    retry_count = models.IntegerField(default=0)

    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'mercadolibre_webhook_events'
        verbose_name = 'Evento Webhook MercadoLibre'
        verbose_name_plural = 'Eventos Webhook MercadoLibre'
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['status', 'received_at']),
            models.Index(fields=['ml_user_id', 'topic']),
        ]

    def __str__(self):
        return f"{self.topic} - {self.ml_user_id} ({self.status})"
