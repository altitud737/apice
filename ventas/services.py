"""
Servicios de dominio del módulo Ventas.

Orquestan operaciones que tocan múltiples modelos:
- Confirmación de pedidos (valida + descuenta stock + registra movimientos)
- Cancelación de pedidos confirmados (repone stock + registra movimientos)
"""
from django.db import transaction

from inventario.models import Stock
from inventario.services import descontar_stock, reponer_stock
from .exceptions import (
    StockInsuficienteError,
    PedidoEstadoInvalidoError,
    PedidoSinDetallesError,
    EmpresaInconsistenteError,
)


def validar_pedido_para_confirmar(pedido):
    """Validaciones previas a confirmar (sin tocar stock)."""
    if pedido.estado != 'borrador':
        raise PedidoEstadoInvalidoError(
            f"Solo se pueden confirmar pedidos en estado 'borrador'. "
            f"Estado actual: '{pedido.estado}'."
        )
    if pedido.almacen_id is None:
        raise PedidoEstadoInvalidoError(
            "El pedido debe tener un almacén asignado antes de confirmar."
        )
    if pedido.almacen.empresa_id != pedido.empresa_id:
        raise EmpresaInconsistenteError("El almacén pertenece a otra empresa.")

    detalles = list(pedido.detalles.select_related('articulo').all())
    if not detalles:
        raise PedidoSinDetallesError("El pedido no tiene detalles cargados.")

    for d in detalles:
        if d.articulo.empresa_id != pedido.empresa_id:
            raise EmpresaInconsistenteError(
                f"El artículo {d.articulo} pertenece a otra empresa."
            )
    return detalles


def validar_stock_disponible(pedido, detalles=None):
    """
    Verifica que haya stock suficiente para todos los detalles del pedido.
    Lanza StockInsuficienteError ante el primer faltante.
    """
    if detalles is None:
        detalles = list(pedido.detalles.select_related('articulo').all())

    # Consolidar cantidades por artículo (un mismo artículo puede aparecer en varias líneas)
    requerido = {}
    for d in detalles:
        requerido[d.articulo_id] = requerido.get(d.articulo_id, 0) + d.cantidad

    for articulo_id, qty_requerida in requerido.items():
        stock = (
            Stock.objects
            .filter(articulo_id=articulo_id, almacen=pedido.almacen)
            .first()
        )
        disponible = stock.cantidad if stock else 0
        if disponible < qty_requerida:
            articulo = next(d.articulo for d in detalles if d.articulo_id == articulo_id)
            raise StockInsuficienteError(
                articulo, pedido.almacen, disponible, qty_requerida
            )


@transaction.atomic
def confirmar_pedido(pedido, usuario=None):
    """
    Confirma un pedido:
      1. Valida estado y precondiciones.
      2. Bloquea pedido y valida stock disponible.
      3. Descuenta stock y genera MovimientoStock por cada detalle.
      4. Recalcula totales.
      5. Pasa estado a 'confirmado'.

    Todo en una transacción atómica. Cualquier error revierte completamente.
    """
    # Recargar con lock para evitar doble confirmación
    from .models import Pedido
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)

    detalles = validar_pedido_para_confirmar(pedido)
    validar_stock_disponible(pedido, detalles)

    referencia = f"Pedido #{pedido.numero}"

    for d in detalles:
        descontar_stock(
            articulo=d.articulo,
            almacen=pedido.almacen,
            cantidad=d.cantidad,
            referencia=referencia,
            usuario=usuario,
        )

    pedido.recalcular_totales(persistir=False)
    pedido.estado = 'confirmado'
    pedido.save(update_fields=['estado', 'subtotal', 'impuesto', 'total', 'updated_at'])
    return pedido


@transaction.atomic
def cancelar_pedido(pedido, usuario=None):
    """
    Cancela un pedido:
      - Si está en 'borrador': simplemente marca cancelado.
      - Si ya tenía stock descontado ('confirmado','en_proceso','entregado','facturado'):
        repone stock y genera MovimientoStock de entrada por cada detalle.
    """
    from .models import Pedido
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)

    if pedido.estado == 'cancelado':
        return pedido  # idempotente

    if pedido.tiene_stock_descontado:
        if pedido.almacen_id is None:
            raise PedidoEstadoInvalidoError(
                "Pedido confirmado sin almacén asignado: inconsistencia de datos."
            )
        referencia = f"Cancelación pedido #{pedido.numero}"
        for d in pedido.detalles.select_related('articulo').all():
            reponer_stock(
                articulo=d.articulo,
                almacen=pedido.almacen,
                cantidad=d.cantidad,
                referencia=referencia,
                usuario=usuario,
            )

    pedido.estado = 'cancelado'
    pedido.save(update_fields=['estado', 'updated_at'])
    return pedido
