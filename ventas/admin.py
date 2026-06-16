from django.contrib import admin, messages

from .exceptions import ERPBusinessError
from .models import Pedido, PedidoDetalle


class PedidoDetalleInline(admin.TabularInline):
    model = PedidoDetalle
    extra = 1
    fields = ('articulo', 'cantidad', 'precio_unitario', 'descuento')

    def has_add_permission(self, request, obj=None):
        if obj is not None and not obj.es_editable:
            return False
        return super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj is not None and not obj.es_editable:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and not obj.es_editable:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'fecha', 'cliente', 'vendedor', 'almacen', 'estado', 'total', 'empresa')
    list_filter = ('empresa', 'estado', 'fecha', 'almacen')
    search_fields = ('numero', 'cliente__razon_social', 'vendedor__nombre')
    readonly_fields = ('numero', 'subtotal', 'impuesto', 'total', 'created_at', 'updated_at')
    inlines = [PedidoDetalleInline]
    date_hierarchy = 'fecha'
    actions = ['accion_confirmar_pedidos', 'accion_cancelar_pedidos']

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj is not None and not obj.es_editable:
            # Pedido no editable: bloquear todos los campos de negocio
            bloqueados = ['empresa', 'fecha', 'cliente', 'vendedor', 'almacen',
                          'estado', 'observaciones']
            for f in bloqueados:
                if f not in ro:
                    ro.append(f)
        return ro

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.recalcular_totales()

    @admin.action(description='Confirmar pedidos seleccionados (descontar stock)')
    def accion_confirmar_pedidos(self, request, queryset):
        ok = 0
        for pedido in queryset:
            try:
                pedido.confirmar(usuario=request.user)
                ok += 1
            except ERPBusinessError as e:
                self.message_user(request, f"Pedido #{pedido.numero}: {e}", level=messages.ERROR)
        if ok:
            self.message_user(request, f"{ok} pedido(s) confirmado(s).", level=messages.SUCCESS)

    @admin.action(description='Cancelar pedidos seleccionados (reponer stock si aplica)')
    def accion_cancelar_pedidos(self, request, queryset):
        ok = 0
        for pedido in queryset:
            try:
                pedido.cancelar(usuario=request.user)
                ok += 1
            except ERPBusinessError as e:
                self.message_user(request, f"Pedido #{pedido.numero}: {e}", level=messages.ERROR)
        if ok:
            self.message_user(request, f"{ok} pedido(s) cancelado(s).", level=messages.SUCCESS)


@admin.register(PedidoDetalle)
class PedidoDetalleAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'articulo', 'cantidad', 'precio_unitario', 'descuento')
    list_filter = ('pedido__empresa',)
    search_fields = ('pedido__numero', 'articulo__codigo', 'articulo__descripcion')
