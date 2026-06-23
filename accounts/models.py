from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
import uuid


class ERPUserManager(UserManager):
    """
    Manager que extiende el UserManager de Django para que `createsuperuser`
    (built-in) también marque al usuario como administrador global del ERP
    (`is_superadmin=True`). Mantiene compatibilidad total con la API estándar.
    """

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_superadmin', True)
        return super().create_superuser(username, email=email, password=password, **extra_fields)

class Company(models.Model):
    INDUSTRY_CHOICES = [
        ('metalurgica', 'Metalúrgica'),
        ('construccion', 'Construcción'),
        ('educacion', 'Educación'),
        ('tecnologia', 'Tecnología'),
        ('salud', 'Salud'),
        ('comercio', 'Comercio'),
        ('servicios', 'Servicios'),
        ('manufactura', 'Manufactura'),
        ('agricultura', 'Agricultura'),
        ('transporte', 'Transporte'),
        ('inmobiliaria', 'Inmobiliaria'),
        ('gastronomia', 'Gastronomía'),
        ('otro', 'Otro'),
    ]
    
    IVA_CHOICES = [
        ('responsable_inscripto', 'Responsable Inscripto'),
        ('monotributo', 'Monotributo'),
        ('exento', 'Exento'),
    ]

    # Código de empresa (alineado con esquema ERP: VARCHAR(10) único).
    # Nullable para no romper registros existentes; se completa al editar/crear.
    codigo = models.CharField(
        max_length=10,
        unique=True,
        null=True,
        blank=True,
        verbose_name='Código de empresa',
        help_text='Código corto único de la empresa (ERP).',
    )
    name = models.CharField(max_length=255)
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES, default='otro', verbose_name='Industria')
    description = models.TextField(blank=True, null=True, verbose_name='Descripción')
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name='Ubicación')
    api_key = models.CharField(max_length=64, unique=True, blank=True, editable=False)
    is_active = models.BooleanField(default=True, verbose_name='Activa')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Fiscal (Module E)
    iva_condition = models.CharField(max_length=30, blank=True, default='', choices=IVA_CHOICES, verbose_name='Condición IVA')
    iibb_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Alícuota IIBB (%)', help_text='Alícuota de Ingresos Brutos en porcentaje')
    province = models.CharField(max_length=50, blank=True, default='', verbose_name='Provincia')
    ml_commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=13, verbose_name='Comisión ML (%)', help_text='Porcentaje estimado de comisión de MercadoLibre')

    class Meta:
        db_table = 'empresa'
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = uuid.uuid4().hex
        super().save(*args, **kwargs)

    def __str__(self):
        # Prefiere mostrar 'codigo - name' si hay codigo, sino solo name.
        if self.codigo:
            return f"{self.codigo} - {self.name}"
        return self.name

class User(AbstractUser):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    is_superadmin = models.BooleanField(default=False, help_text="Super administrador con acceso total al sistema")
    is_company_admin = models.BooleanField(default=False, help_text="Administrador de la empresa")
    
    # Permisos de usuario
    can_send_emails = models.BooleanField(default=True, verbose_name='Puede enviar emails')
    can_view_contacts = models.BooleanField(default=True, verbose_name='Puede ver contactos')
    can_view_deals = models.BooleanField(default=True, verbose_name='Puede ver deals')
    can_view_pipeline = models.BooleanField(default=True, verbose_name='Puede ver pipeline')
    can_view_settings = models.BooleanField(default=False, verbose_name='Puede ver configuración')
    can_manage_users = models.BooleanField(default=False, verbose_name='Puede gestionar usuarios')
    can_view_integrations = models.BooleanField(default=True, verbose_name='Puede ver integraciones')
    
    last_activity = models.DateTimeField(null=True, blank=True, verbose_name='Última actividad')

    objects = ERPUserManager()

    def save(self, *args, **kwargs):
        # Mantener consistencia: cualquier superuser de Django es también
        # administrador global del ERP.
        if self.is_superuser:
            self.is_superadmin = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username


class SupportTicket(models.Model):
    """
    Tickets de soporte que los clientes envían al super admin
    """
    CATEGORY_CHOICES = [
        ('security', 'Problema de Seguridad'),
        ('improvement', 'Mejora'),
        ('integration', 'Integración'),
        ('other', 'Otro'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Abierto'),
        ('in_progress', 'En Progreso'),
        ('resolved', 'Resuelto'),
        ('closed', 'Cerrado'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_tickets')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='support_tickets')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    subject = models.CharField(max_length=255, verbose_name='Asunto')
    message = models.TextField(verbose_name='Mensaje')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    admin_response = models.TextField(blank=True, null=True, verbose_name='Respuesta del Admin')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Ticket de Soporte'
        verbose_name_plural = 'Tickets de Soporte'
    
    def __str__(self):
        return f"{self.get_category_display()} - {self.subject}"


class SystemNotification(models.Model):
    """
    Notificaciones del sistema enviadas por el super admin a todos los usuarios.
    Ej: actualizaciones del CRM, nuevas funcionalidades, mantenimiento, etc.
    """
    CATEGORY_CHOICES = [
        ('update', 'Actualización'),
        ('feature', 'Nueva Funcionalidad'),
        ('maintenance', 'Mantenimiento'),
        ('announcement', 'Anuncio'),
        ('security', 'Seguridad'),
    ]
    
    title = models.CharField(max_length=255, verbose_name='Título')
    message = models.TextField(verbose_name='Mensaje')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='announcement')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_notifications')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notificación del Sistema'
        verbose_name_plural = 'Notificaciones del Sistema'
    
    def __str__(self):
        return self.title
    
    def get_category_icon(self):
        icons = {
            'update': '🔄',
            'feature': '✨',
            'maintenance': '🔧',
            'announcement': '📢',
            'security': '🔒',
        }
        return icons.get(self.category, '📢')


class UserNotification(models.Model):
    """
    Relación entre notificación y usuario, trackea si fue leída.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification = models.ForeignKey(SystemNotification, on_delete=models.CASCADE, related_name='user_notifications')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-notification__created_at']
        unique_together = ['user', 'notification']
        verbose_name = 'Notificación de Usuario'
        verbose_name_plural = 'Notificaciones de Usuario'
    
    def __str__(self):
        return f"{self.user.username} - {self.notification.title}"


class DemoRequest(models.Model):
    """
    Solicitudes de demo de potenciales clientes
    """
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('contacted', 'Contactado'),
        ('account_created', 'Cuenta Creada'),
        ('rejected', 'Rechazado'),
    ]
    
    name = models.CharField(max_length=255, verbose_name='Nombre')
    email = models.EmailField(verbose_name='Email')
    company = models.CharField(max_length=255, verbose_name='Empresa')
    message = models.TextField(verbose_name='¿Qué te interesaría encontrar en el sistema?')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Estado')
    admin_notes = models.TextField(blank=True, null=True, verbose_name='Notas del Admin')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Solicitud')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Solicitud de Demo'
        verbose_name_plural = 'Solicitudes de Demo'
    
    def __str__(self):
        return f"{self.name} - {self.company} ({self.email})"
