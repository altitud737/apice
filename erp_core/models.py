"""
Modelos ERP Core: entidades base reutilizables (Idioma, Cliente, Vendedor).
La entidad Empresa se reutiliza desde accounts.Company.
"""
from django.db import models
from django.conf import settings


class TenantModel(models.Model):
    """
    Modelo abstracto multiempresa.
    Reutiliza accounts.Company como entidad Empresa.
    """
    empresa = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        verbose_name='Empresa',
        related_name='%(app_label)s_%(class)s_set',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado')

    class Meta:
        abstract = True


class Idioma(models.Model):
    """
    Idiomas disponibles en el sistema (entidad global, no multiempresa).
    """
    codigo = models.CharField(max_length=10, unique=True, verbose_name='Código')
    descripcion = models.CharField(max_length=100, verbose_name='Descripción')
    activo = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        db_table = 'idioma'
        verbose_name = 'Idioma'
        verbose_name_plural = 'Idiomas'
        ordering = ['descripcion']

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"


class Cliente(TenantModel):
    """
    Cliente del ERP (entidad de facturación/ventas).
    Relacionado opcionalmente con apice.Contact para integración con CRM.
    """
    codigo = models.CharField(max_length=20, verbose_name='Código')
    razon_social = models.CharField(max_length=200, verbose_name='Razón Social')
    cuit = models.CharField(max_length=20, blank=True, default='', verbose_name='CUIT')
    email = models.EmailField(blank=True, default='', verbose_name='Email')
    telefono = models.CharField(max_length=50, blank=True, default='', verbose_name='Teléfono')
    direccion = models.CharField(max_length=255, blank=True, default='', verbose_name='Dirección')
    activo = models.BooleanField(default=True, verbose_name='Activo')

    # Integración opcional con CRM existente
    contacto_crm = models.ForeignKey(
        'apice.Contact',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cliente_erp',
        verbose_name='Contacto CRM',
        help_text='Vínculo opcional con contacto del CRM',
    )

    class Meta:
        db_table = 'cliente'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['razon_social']
        unique_together = [('empresa', 'codigo')]

    def __str__(self):
        return f"{self.codigo} - {self.razon_social}"


class Vendedor(TenantModel):
    """
    Vendedor del ERP.
    Relacionado opcionalmente con accounts.User para integración con autenticación.
    """
    codigo = models.CharField(max_length=20, verbose_name='Código')
    nombre = models.CharField(max_length=100, verbose_name='Nombre')
    email = models.EmailField(blank=True, default='', verbose_name='Email')
    telefono = models.CharField(max_length=50, blank=True, default='', verbose_name='Teléfono')
    activo = models.BooleanField(default=True, verbose_name='Activo')

    # Vínculo opcional con usuario del sistema
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendedor_erp',
        verbose_name='Usuario del sistema',
        help_text='Vínculo opcional con usuario del sistema',
    )

    class Meta:
        db_table = 'vendedor'
        verbose_name = 'Vendedor'
        verbose_name_plural = 'Vendedores'
        ordering = ['nombre']
        unique_together = [('empresa', 'codigo')]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
