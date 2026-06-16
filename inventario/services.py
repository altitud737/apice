"""
Servicios de dominio del módulo Inventario.

Toda operación que modifica stock debe pasar por estos servicios para garantizar:
- Atomicidad transaccional
- Bloqueo pesimista contra concurrencia
- Registro automático en MovimientoStock
- Validación de stock no negativo
"""
from decimal import Decimal
from django.db import transaction

from .models import Stock, MovimientoStock, Articulo, Almacen
from ventas.exceptions import StockInsuficienteError, EmpresaInconsistenteError


def obtener_o_crear_stock(articulo: Articulo, almacen: Almacen, lock: bool = False) -> Stock:
    """
    Obtiene la fila de Stock para (articulo, almacen) o la crea con cantidad=0.
    Si lock=True, aplica select_for_update sobre la fila.
    """
    if articulo.empresa_id != almacen.empresa_id:
        raise EmpresaInconsistenteError(
            f"Artículo (empresa={articulo.empresa_id}) y almacén "
            f"(empresa={almacen.empresa_id}) pertenecen a empresas distintas."
        )

    qs = Stock.objects.filter(articulo=articulo, almacen=almacen)
    if lock:
        qs = qs.select_for_update()
    stock = qs.first()
    if stock is None:
        stock, _ = Stock.objects.get_or_create(
            articulo=articulo, almacen=almacen, defaults={'cantidad': Decimal('0.00')}
        )
        if lock:
            stock = Stock.objects.select_for_update().get(pk=stock.pk)
    return stock


def registrar_movimiento(
    *,
    tipo: str,
    articulo: Articulo,
    cantidad: Decimal,
    almacen_origen: Almacen = None,
    almacen_destino: Almacen = None,
    referencia: str = '',
    observaciones: str = '',
    usuario=None,
) -> MovimientoStock:
    """
    Crea un registro de MovimientoStock. NO modifica Stock (eso lo hace el caller).
    La empresa se deriva del artículo.
    """
    return MovimientoStock.objects.create(
        empresa=articulo.empresa,
        tipo=tipo,
        articulo=articulo,
        almacen_origen=almacen_origen,
        almacen_destino=almacen_destino,
        cantidad=cantidad,
        referencia=referencia,
        observaciones=observaciones,
        usuario=usuario,
    )


@transaction.atomic
def descontar_stock(
    articulo: Articulo,
    almacen: Almacen,
    cantidad: Decimal,
    *,
    referencia: str = '',
    usuario=None,
) -> MovimientoStock:
    """
    Descuenta `cantidad` del stock de `articulo` en `almacen` y genera el MovimientoStock.
    Aplica bloqueo pesimista. Lanza StockInsuficienteError si no alcanza.
    """
    if cantidad <= 0:
        raise ValueError("La cantidad a descontar debe ser mayor a 0.")

    stock = obtener_o_crear_stock(articulo, almacen, lock=True)
    if stock.cantidad < cantidad:
        raise StockInsuficienteError(articulo, almacen, stock.cantidad, cantidad)

    stock.cantidad = stock.cantidad - cantidad
    stock.save(update_fields=['cantidad', 'updated_at'])

    return registrar_movimiento(
        tipo='salida',
        articulo=articulo,
        cantidad=cantidad,
        almacen_origen=almacen,
        referencia=referencia,
        usuario=usuario,
    )


@transaction.atomic
def reponer_stock(
    articulo: Articulo,
    almacen: Almacen,
    cantidad: Decimal,
    *,
    referencia: str = '',
    usuario=None,
) -> MovimientoStock:
    """
    Aumenta `cantidad` del stock de `articulo` en `almacen` y genera el MovimientoStock.
    """
    if cantidad <= 0:
        raise ValueError("La cantidad a reponer debe ser mayor a 0.")

    stock = obtener_o_crear_stock(articulo, almacen, lock=True)
    stock.cantidad = stock.cantidad + cantidad
    stock.save(update_fields=['cantidad', 'updated_at'])

    return registrar_movimiento(
        tipo='entrada',
        articulo=articulo,
        cantidad=cantidad,
        almacen_destino=almacen,
        referencia=referencia,
        usuario=usuario,
    )
