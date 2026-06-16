"""
Modelos del módulo Inventario: Artículo, Almacén, Stock, MovimientoStock.
Reutiliza accounts.Company como Empresa vía erp_core.TenantModel.
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from decimal import Decimal

from erp_core.models import TenantModel


class Articulo(TenantModel):
    codigo = models.CharField(max_length=30, verbose_name='Código')
    descripcion = models.CharField(max_length=200, verbose_name='Descripción')
    unidad_medida = models.CharField(max_length=20, default='unidad', verbose_name='Unidad de medida')
    precio_costo = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), verbose_name='Precio costo')
    precio_venta = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), verbose_name='Precio venta')
    activo = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        db_table = 'articulo'
        verbose_name = 'Artículo'
        verbose_name_plural = 'Artículos'
        ordering = ['codigo']
        unique_together = [('empresa', 'codigo')]

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"


class Almacen(TenantModel):
    TIPO_CHOICES = [
        ('principal', 'Principal'),
        ('sucursal', 'Sucursal'),
        ('deposito', 'Depósito'),
        ('transito', 'En Tránsito'),
        ('virtual', 'Virtual'),
    ]

    codigo = models.CharField(max_length=20, verbose_name='Código')
    nombre = models.CharField(max_length=100, verbose_name='Nombre')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='principal', verbose_name='Tipo')
    direccion = models.CharField(max_length=255, blank=True, default='', verbose_name='Dirección')
    activo = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        db_table = 'almacen'
        verbose_name = 'Almacén'
        verbose_name_plural = 'Almacenes'
        ordering = ['nombre']
        unique_together = [('empresa', 'codigo')]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Stock(models.Model):
    """
    Stock por almacén y artículo.
    No hereda de TenantModel porque la empresa se deriva del almacén/artículo.
    """
    almacen = models.ForeignKey(Almacen, on_delete=models.CASCADE, related_name='stocks', verbose_name='Almacén')
    articulo = models.ForeignKey(Articulo, on_delete=models.CASCADE, related_name='stocks', verbose_name='Artículo')
    cantidad = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), verbose_name='Cantidad')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        db_table = 'stock'
        verbose_name = 'Stock'
        verbose_name_plural = 'Stocks'
        unique_together = [('almacen', 'articulo')]
        ordering = ['articulo__codigo']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gte=0),
                name='stock_cantidad_no_negativa',
            ),
        ]

    def __str__(self):
        return f"{self.articulo.codigo} @ {self.almacen.codigo}: {self.cantidad}"

    def clean(self):
        super().clean()
        if self.cantidad is not None and self.cantidad < 0:
            raise ValidationError({'cantidad': 'El stock no puede ser negativo.'})
        if self.articulo_id and self.almacen_id and self.articulo.empresa_id != self.almacen.empresa_id:
            raise ValidationError('Artículo y almacén deben pertenecer a la misma empresa.')


class MovimientoStock(TenantModel):
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('transferencia', 'Transferencia'),
        ('ajuste', 'Ajuste'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name='Tipo')
    articulo = models.ForeignKey(Articulo, on_delete=models.PROTECT, related_name='movimientos', verbose_name='Artículo')
    almacen_origen = models.ForeignKey(
        Almacen,
        on_delete=models.PROTECT,
        related_name='movimientos_origen',
        null=True,
        blank=True,
        verbose_name='Almacén origen',
    )
    almacen_destino = models.ForeignKey(
        Almacen,
        on_delete=models.PROTECT,
        related_name='movimientos_destino',
        null=True,
        blank=True,
        verbose_name='Almacén destino',
    )
    cantidad = models.DecimalField(max_digits=18, decimal_places=2, verbose_name='Cantidad')
    fecha = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')
    referencia = models.CharField(max_length=100, blank=True, default='', verbose_name='Referencia')
    observaciones = models.TextField(blank=True, default='', verbose_name='Observaciones')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_stock',
        verbose_name='Usuario',
    )

    class Meta:
        db_table = 'movimiento_stock'
        verbose_name = 'Movimiento de Stock'
        verbose_name_plural = 'Movimientos de Stock'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.articulo.codigo}: {self.cantidad}"
