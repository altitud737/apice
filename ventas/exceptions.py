"""Excepciones de dominio del módulo Ventas/Inventario."""


class ERPBusinessError(Exception):
    """Base para errores de negocio del ERP."""
    pass


class StockInsuficienteError(ERPBusinessError):
    """Se intentó descontar más stock del disponible."""
    def __init__(self, articulo, almacen, disponible, solicitado):
        self.articulo = articulo
        self.almacen = almacen
        self.disponible = disponible
        self.solicitado = solicitado
        super().__init__(
            f"Stock insuficiente para {articulo} en {almacen}: "
            f"disponible={disponible}, solicitado={solicitado}"
        )


class PedidoNoEditableError(ERPBusinessError):
    """Se intentó modificar un pedido que no está en estado editable."""
    pass


class PedidoEstadoInvalidoError(ERPBusinessError):
    """Transición de estado de pedido no permitida."""
    pass


class EmpresaInconsistenteError(ERPBusinessError):
    """Las entidades relacionadas pertenecen a empresas distintas."""
    pass


class PedidoSinDetallesError(ERPBusinessError):
    """Se intentó confirmar un pedido sin detalles."""
    pass
