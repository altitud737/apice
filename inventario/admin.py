from django.contrib import admin
from .models import Articulo, Almacen, Stock, MovimientoStock


@admin.register(Articulo)
class ArticuloAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descripcion', 'unidad_medida', 'precio_costo', 'precio_venta', 'empresa', 'activo')
    list_filter = ('empresa', 'activo', 'unidad_medida')
    search_fields = ('codigo', 'descripcion')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'tipo', 'empresa', 'activo')
    list_filter = ('empresa', 'tipo', 'activo')
    search_fields = ('codigo', 'nombre')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('articulo', 'almacen', 'cantidad', 'updated_at')
    list_filter = ('almacen', 'almacen__empresa')
    search_fields = ('articulo__codigo', 'articulo__descripcion', 'almacen__codigo')
    readonly_fields = ('updated_at',)


@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'tipo', 'articulo', 'almacen_origen', 'almacen_destino', 'cantidad', 'empresa', 'usuario')
    list_filter = ('empresa', 'tipo', 'fecha')
    search_fields = ('articulo__codigo', 'articulo__descripcion', 'referencia')
    readonly_fields = ('fecha', 'created_at', 'updated_at')
    date_hierarchy = 'fecha'
