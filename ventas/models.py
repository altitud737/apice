"""
Modelos del módulo Ventas: Pedido, PedidoDetalle.
Reutiliza Cliente, Vendedor, Articulo.
"""
from django.db import models, transaction
from django.core.exceptions import ValidationError
from decimal import Decimal

from erp_core.models import TenantModel, Cliente, Vendedor
from inventario.models import Articulo, Almacen

IVA_ALICUOTA = Decimal('0.21')
ESTADOS_EDITABLES = {'borrador'}
ESTADOS_CON_STOCK_DESCONTADO = {'confirmado', 'en_proceso', 'entregado', 'facturado'}


class Pedido(TenantModel):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('confirmado', 'Confirmado'),
        ('en_proceso', 'En Proceso'),
        ('entregado', 'Entregado'),
        ('facturado', 'Facturado'),
        ('cancelado', 'Cancelado'),
    ]

    numero = models.IntegerField(verbose_name='Número', blank=True, null=True)
    fecha = models.DateField(verbose_name='Fecha')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='pedidos', verbose_name='Cliente')
    vendedor = models.ForeignKey(Vendedor, on_delete=models.PROTECT, related_name='pedidos', verbose_name='Vendedor')
    almacen = models.ForeignKey(
        Almacen,
        on_delete=models.PROTECT,
        related_name='pedidos',
        verbose_name='Almacén',
        null=True,
        blank=True,
        help_text='Almacén desde el cual se descontará el stock al confirmar.',
    )
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador', verbose_name='Estado')

    subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), verbose_name='Subtotal')
    impuesto = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), verbose_name='Impuesto')
    total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), verbose_name='Total')
    observaciones = models.TextField(blank=True, default='', verbose_name='Observaciones')

    class Meta:
        db_table = 'pedido'
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-fecha', '-numero']
        unique_together = [('empresa', 'numero')]

    def __str__(self):
        num = self.numero if self.numero is not None else 's/n'
        cliente = self.cliente.razon_social if self.cliente_id else '(sin cliente)'
        return f"Pedido #{num} - {cliente}"

    # ------------------------------------------------------------------
    # Validaciones
    # ------------------------------------------------------------------
    def clean(self):
        super().clean()
        if self.cliente_id and self.cliente.empresa_id != self.empresa_id:
            raise ValidationError({'cliente': 'El cliente pertenece a otra empresa.'})
        if self.vendedor_id and self.vendedor.empresa_id != self.empresa_id:
            raise ValidationError({'vendedor': 'El vendedor pertenece a otra empresa.'})
        if self.almacen_id and self.almacen.empresa_id != self.empresa_id:
            raise ValidationError({'almacen': 'El almacén pertenece a otra empresa.'})

    # ------------------------------------------------------------------
    # Numeración automática por empresa
    # ------------------------------------------------------------------
    def _asignar_numero(self):
        """Asigna numero = MAX(numero)+1 dentro de la empresa, con lock."""
        with transaction.atomic():
            ultimo = (
                Pedido.objects
                .select_for_update()
                .filter(empresa=self.empresa)
                .aggregate(models.Max('numero'))
            )['numero__max']
            self.numero = (ultimo or 0) + 1

    def save(self, *args, **kwargs):
        if self.numero is None and self.empresa_id:
            self._asignar_numero()
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Cálculo de totales
    # ------------------------------------------------------------------
    def recalcular_totales(self, persistir: bool = True):
        detalles = self.detalles.all()
        subtotal = sum((d.subtotal for d in detalles), Decimal('0.00'))
        impuesto = (subtotal * IVA_ALICUOTA).quantize(Decimal('0.01'))
        self.subtotal = subtotal.quantize(Decimal('0.01'))
        self.impuesto = impuesto
        self.total = (self.subtotal + self.impuesto).quantize(Decimal('0.01'))
        if persistir and self.pk:
            super().save(update_fields=['subtotal', 'impuesto', 'total', 'updated_at'])

    # ------------------------------------------------------------------
    # Helpers de estado
    # ------------------------------------------------------------------
    @property
    def es_editable(self) -> bool:
        return self.estado in ESTADOS_EDITABLES

    @property
    def tiene_stock_descontado(self) -> bool:
        return self.estado in ESTADOS_CON_STOCK_DESCONTADO

    def confirmar(self, usuario=None):
        """Atajo: delega en services.confirmar_pedido."""
        from .services import confirmar_pedido
        return confirmar_pedido(self, usuario=usuario)

    def cancelar(self, usuario=None):
        """Atajo: delega en services.cancelar_pedido."""
        from .services import cancelar_pedido
        return cancelar_pedido(self, usuario=usuario)


class PedidoDetalle(models.Model):
    """
    Detalle de pedido. La empresa se deriva del pedido padre.
    """
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles', verbose_name='Pedido')
    articulo = models.ForeignKey(Articulo, on_delete=models.PROTECT, related_name='pedido_detalles', verbose_name='Artículo')
    cantidad = models.DecimalField(max_digits=18, decimal_places=2, verbose_name='Cantidad')
    precio_unitario = models.DecimalField(max_digits=18, decimal_places=2, verbose_name='Precio unitario')
    descuento = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), verbose_name='Descuento')

    class Meta:
        db_table = 'pedido_detalle'
        verbose_name = 'Detalle de Pedido'
        verbose_name_plural = 'Detalles de Pedidos'
        ordering = ['id']

    def __str__(self):
        return f"{self.pedido.numero} - {self.articulo.codigo} x {self.cantidad}"

    @property
    def subtotal(self):
        return (self.cantidad * self.precio_unitario) - self.descuento

    def clean(self):
        super().clean()
        if self.pedido_id and self.articulo_id:
            if self.articulo.empresa_id != self.pedido.empresa_id:
                raise ValidationError({'articulo': 'El artículo pertenece a otra empresa.'})
        if self.cantidad is not None and self.cantidad <= 0:
            raise ValidationError({'cantidad': 'La cantidad debe ser mayor a 0.'})
        if self.pedido_id and not self.pedido.es_editable:
            raise ValidationError('No se puede modificar el detalle de un pedido no editable.')
