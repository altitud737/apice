"""
Signals del módulo Ventas.

- Recalcular totales del Pedido cuando cambian sus detalles.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import PedidoDetalle


@receiver(post_save, sender=PedidoDetalle, dispatch_uid='ventas_recalcular_post_save')
def _recalcular_totales_on_detalle_save(sender, instance, **kwargs):
    if instance.pedido_id:
        instance.pedido.recalcular_totales()


@receiver(post_delete, sender=PedidoDetalle, dispatch_uid='ventas_recalcular_post_delete')
def _recalcular_totales_on_detalle_delete(sender, instance, **kwargs):
    if instance.pedido_id:
        try:
            pedido = instance.pedido
        except Exception:
            return
        pedido.recalcular_totales()
