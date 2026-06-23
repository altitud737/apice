"""
Tests del flujo ERP completo: Pedido -> Validacion -> Stock -> MovimientoStock.
"""
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase

from accounts.models import Company
from core.models import Cliente, Vendedor
from inventario.models import Articulo, Almacen, Stock, MovimientoStock
from inventario.services import descontar_stock, reponer_stock
from ventas.exceptions import (
    StockInsuficienteError,
    PedidoEstadoInvalidoError,
    PedidoSinDetallesError,
    EmpresaInconsistenteError,
)
from ventas.models import Pedido, PedidoDetalle


class ERPFlowTestBase(TestCase):
    """Setup compartido: empresa + cliente + vendedor + almacen + 2 articulos con stock."""

    @classmethod
    def setUpTestData(cls):
        cls.empresa = Company.objects.create(name='Empresa Test ERP')
        cls.cliente = Cliente.objects.create(
            empresa=cls.empresa, codigo='C001', razon_social='Cliente Test S.A.'
        )
        cls.vendedor = Vendedor.objects.create(
            empresa=cls.empresa, codigo='V001', nombre='Vendedor Test'
        )
        cls.almacen = Almacen.objects.create(
            empresa=cls.empresa, codigo='A001', nombre='Almacen Principal', tipo='principal'
        )
        cls.art1 = Articulo.objects.create(
            empresa=cls.empresa, codigo='ART1', descripcion='Articulo 1',
            precio_costo=Decimal('50.00'), precio_venta=Decimal('100.00'),
        )
        cls.art2 = Articulo.objects.create(
            empresa=cls.empresa, codigo='ART2', descripcion='Articulo 2',
            precio_costo=Decimal('20.00'), precio_venta=Decimal('40.00'),
        )
        # Stock inicial: 10 unidades de cada articulo
        Stock.objects.create(almacen=cls.almacen, articulo=cls.art1, cantidad=Decimal('10'))
        Stock.objects.create(almacen=cls.almacen, articulo=cls.art2, cantidad=Decimal('10'))

    def _crear_pedido(self, almacen=None):
        return Pedido.objects.create(
            empresa=self.empresa,
            fecha=date.today(),
            cliente=self.cliente,
            vendedor=self.vendedor,
            almacen=almacen if almacen is not None else self.almacen,
        )


class NumeracionAutomaticaTests(ERPFlowTestBase):

    def test_primer_pedido_obtiene_numero_1(self):
        p = self._crear_pedido()
        self.assertEqual(p.numero, 1)

    def test_pedidos_sucesivos_numeracion_incremental(self):
        p1 = self._crear_pedido()
        p2 = self._crear_pedido()
        p3 = self._crear_pedido()
        self.assertEqual([p1.numero, p2.numero, p3.numero], [1, 2, 3])

    def test_numeracion_es_independiente_por_empresa(self):
        empresa2 = Company.objects.create(name='Empresa 2')
        cli2 = Cliente.objects.create(empresa=empresa2, codigo='X', razon_social='X')
        vend2 = Vendedor.objects.create(empresa=empresa2, codigo='X', nombre='X')
        alm2 = Almacen.objects.create(empresa=empresa2, codigo='X', nombre='X')

        p_e1_1 = self._crear_pedido()
        p_e1_2 = self._crear_pedido()
        p_e2_1 = Pedido.objects.create(
            empresa=empresa2, fecha=date.today(),
            cliente=cli2, vendedor=vend2, almacen=alm2,
        )

        self.assertEqual(p_e1_1.numero, 1)
        self.assertEqual(p_e1_2.numero, 2)
        self.assertEqual(p_e2_1.numero, 1)  # empresa distinta, vuelve a 1


class CalculoTotalesTests(ERPFlowTestBase):

    def test_subtotal_impuesto_total_se_calculan_al_agregar_detalle(self):
        p = self._crear_pedido()
        PedidoDetalle.objects.create(
            pedido=p, articulo=self.art1, cantidad=Decimal('2'),
            precio_unitario=Decimal('100.00'),
        )
        p.refresh_from_db()
        self.assertEqual(p.subtotal, Decimal('200.00'))
        self.assertEqual(p.impuesto, Decimal('42.00'))   # 21%
        self.assertEqual(p.total, Decimal('242.00'))

    def test_totales_se_actualizan_al_agregar_segundo_detalle(self):
        p = self._crear_pedido()
        PedidoDetalle.objects.create(
            pedido=p, articulo=self.art1, cantidad=Decimal('1'),
            precio_unitario=Decimal('100.00'),
        )
        PedidoDetalle.objects.create(
            pedido=p, articulo=self.art2, cantidad=Decimal('3'),
            precio_unitario=Decimal('40.00'),
        )
        p.refresh_from_db()
        self.assertEqual(p.subtotal, Decimal('220.00'))
        self.assertEqual(p.total, Decimal('266.20'))

    def test_descuento_se_aplica_en_subtotal(self):
        p = self._crear_pedido()
        PedidoDetalle.objects.create(
            pedido=p, articulo=self.art1, cantidad=Decimal('2'),
            precio_unitario=Decimal('100.00'), descuento=Decimal('50.00'),
        )
        p.refresh_from_db()
        self.assertEqual(p.subtotal, Decimal('150.00'))

    def test_totales_se_actualizan_al_eliminar_detalle(self):
        p = self._crear_pedido()
        d1 = PedidoDetalle.objects.create(
            pedido=p, articulo=self.art1, cantidad=Decimal('2'),
            precio_unitario=Decimal('100.00'),
        )
        d2 = PedidoDetalle.objects.create(
            pedido=p, articulo=self.art2, cantidad=Decimal('1'),
            precio_unitario=Decimal('40.00'),
        )
        d2.delete()
        p.refresh_from_db()
        self.assertEqual(p.subtotal, Decimal('200.00'))


class ValidacionStockTests(ERPFlowTestBase):

    def test_stock_no_negativo_validation(self):
        s = Stock.objects.get(articulo=self.art1, almacen=self.almacen)
        s.cantidad = Decimal('-1')
        with self.assertRaises(ValidationError):
            s.full_clean()

    def test_descontar_stock_funciona_si_hay_disponibilidad(self):
        descontar_stock(self.art1, self.almacen, Decimal('3'), referencia='test')
        s = Stock.objects.get(articulo=self.art1, almacen=self.almacen)
        self.assertEqual(s.cantidad, Decimal('7'))
        self.assertEqual(
            MovimientoStock.objects.filter(articulo=self.art1, tipo='salida').count(), 1
        )

    def test_descontar_stock_falla_si_no_alcanza(self):
        with self.assertRaises(StockInsuficienteError):
            descontar_stock(self.art1, self.almacen, Decimal('999'))
        # No debe haberse modificado el stock
        s = Stock.objects.get(articulo=self.art1, almacen=self.almacen)
        self.assertEqual(s.cantidad, Decimal('10'))

    def test_reponer_stock_aumenta_y_crea_movimiento(self):
        reponer_stock(self.art1, self.almacen, Decimal('5'), referencia='ingreso')
        s = Stock.objects.get(articulo=self.art1, almacen=self.almacen)
        self.assertEqual(s.cantidad, Decimal('15'))
        self.assertEqual(
            MovimientoStock.objects.filter(articulo=self.art1, tipo='entrada').count(), 1
        )


class ConfirmacionPedidoTests(ERPFlowTestBase):

    def test_confirmar_pedido_descuenta_stock_y_crea_movimientos(self):
        p = self._crear_pedido()
        PedidoDetalle.objects.create(
            pedido=p, articulo=self.art1, cantidad=Decimal('3'),
            precio_unitario=Decimal('100.00'),
        )
        PedidoDetalle.objects.create(
            pedido=p, articulo=self.art2, cantidad=Decimal('2'),
            precio_unitario=Decimal('40.00'),
        )

        p.confirmar()

        p.refresh_from_db()
        self.assertEqual(p.estado, 'confirmado')

        s1 = Stock.objects.get(articulo=self.art1, almacen=self.almacen)
        s2 = Stock.objects.get(articulo=self.art2, almacen=self.almacen)
        self.assertEqual(s1.cantidad, Decimal('7'))
        self.assertEqual(s2.cantidad, Decimal('8'))

        movs = MovimientoStock.objects.filter(referencia=f'Pedido #{p.numero}')
        self.assertEqual(movs.count(), 2)
        self.assertTrue(all(m.tipo == 'salida' for m in movs))
        self.assertTrue(all(m.almacen_origen_id == self.almacen.id for m in movs))

    def test_confirmar_pedido_falla_si_stock_insuficiente(self):
        p = self._crear_pedido()
        PedidoDetalle.objects.create(
            pedido=p, articulo=self.art1, cantidad=Decimal('100'),  # solo hay 10
            precio_unitario=Decimal('100.00'),
        )
        with self.assertRaises(StockInsuficienteError):
            p.confirmar()
        # Estado y stock no deben haber cambiado (rollback)
        p.refresh_from_db()
        self.assertEqual(p.estado, 'borrador')
        s = Stock.objects.get(articulo=self.art1, almacen=self.almacen)
        self.assertEqual(s.cantidad, Decimal('10'))
        self.assertEqual(MovimientoStock.objects.count(), 0)

    def test_confirmar_pedido_sin_detalles_falla(self):
        p = self._crear_pedido()
        with self.assertRaises(PedidoSinDetallesError):
            p.confirmar()

    def test_confirmar_pedido_sin_almacen_falla(self):
        p = Pedido.objects.create(
            empresa=self.empresa, fecha=date.today(),
            cliente=self.cliente, vendedor=self.vendedor,
            almacen=None,
        )
        PedidoDetalle.objects.create(
            pedido=p, articulo=self.art1, cantidad=Decimal('1'),
            precio_unitario=Decimal('100.00'),
        )
        with self.assertRaises(PedidoEstadoInvalidoError):
            p.confirmar()

    def test_no_se_puede_confirmar_dos_veces(self):
        p = self._crear_pedido()
        PedidoDetalle.objects.create(
            pedido=p, articulo=self.art1, cantidad=Decimal('1'),
            precio_unitario=Decimal('100.00'),
        )
        p.confirmar()
        with self.assertRaises(PedidoEstadoInvalidoError):
            p.confirmar()

    def test_no_se_puede_modificar_detalles_de_pedido_confirmado(self):
        from django.core.exceptions import ValidationError as DjangoValidationError
        p = self._crear_pedido()
        d = PedidoDetalle.objects.create(
            pedido=p, articulo=self.art1, cantidad=Decimal('1'),
            precio_unitario=Decimal('100.00'),
        )
        p.confirmar()
        p.refresh_from_db()
        d.cantidad = Decimal('5')
        with self.assertRaises(DjangoValidationError):
            d.full_clean()


class CancelacionPedidoTests(ERPFlowTestBase):

    def test_cancelar_pedido_en_borrador_no_toca_stock(self):
        p = self._crear_pedido()
        PedidoDetalle.objects.create(
            pedido=p, articulo=self.art1, cantidad=Decimal('3'),
            precio_unitario=Decimal('100.00'),
        )
        p.cancelar()
        p.refresh_from_db()
        self.assertEqual(p.estado, 'cancelado')
        s = Stock.objects.get(articulo=self.art1, almacen=self.almacen)
        self.assertEqual(s.cantidad, Decimal('10'))  # sin cambios
        self.assertEqual(MovimientoStock.objects.count(), 0)

    def test_cancelar_pedido_confirmado_repone_stock(self):
        p = self._crear_pedido()
        PedidoDetalle.objects.create(
            pedido=p, articulo=self.art1, cantidad=Decimal('3'),
            precio_unitario=Decimal('100.00'),
        )
        p.confirmar()
        p.refresh_from_db()
        s = Stock.objects.get(articulo=self.art1, almacen=self.almacen)
        self.assertEqual(s.cantidad, Decimal('7'))

        p.cancelar()
        p.refresh_from_db()
        self.assertEqual(p.estado, 'cancelado')
        s.refresh_from_db()
        self.assertEqual(s.cantidad, Decimal('10'))  # repuesto

        movs_entrada = MovimientoStock.objects.filter(tipo='entrada')
        self.assertEqual(movs_entrada.count(), 1)


class MultiempresaTests(ERPFlowTestBase):

    def test_no_se_puede_usar_cliente_de_otra_empresa(self):
        from django.core.exceptions import ValidationError as DjangoValidationError
        empresa2 = Company.objects.create(name='Otra')
        cliente_otra = Cliente.objects.create(
            empresa=empresa2, codigo='X', razon_social='X'
        )
        p = Pedido(
            empresa=self.empresa, fecha=date.today(),
            cliente=cliente_otra, vendedor=self.vendedor, almacen=self.almacen,
        )
        with self.assertRaises(DjangoValidationError):
            p.full_clean()

    def test_confirmar_pedido_con_articulo_de_otra_empresa_falla(self):
        empresa2 = Company.objects.create(name='Otra')
        articulo_otra = Articulo.objects.create(
            empresa=empresa2, codigo='X', descripcion='X',
        )
        p = self._crear_pedido()
        # Insertamos detalle saltando clean() (simulando dato corrupto)
        PedidoDetalle.objects.create(
            pedido=p, articulo=articulo_otra, cantidad=Decimal('1'),
            precio_unitario=Decimal('10'),
        )
        with self.assertRaises(EmpresaInconsistenteError):
            p.confirmar()
