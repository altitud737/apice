from django.contrib import admin
from .models import Idioma, Cliente, Vendedor


@admin.register(Idioma)
class IdiomaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descripcion', 'activo')
    list_filter = ('activo',)
    search_fields = ('codigo', 'descripcion')


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'razon_social', 'cuit', 'empresa', 'activo')
    list_filter = ('empresa', 'activo')
    search_fields = ('codigo', 'razon_social', 'cuit', 'email')
    raw_id_fields = ('contacto_crm',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Vendedor)
class VendedorAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'email', 'empresa', 'activo')
    list_filter = ('empresa', 'activo')
    search_fields = ('codigo', 'nombre', 'email')
    raw_id_fields = ('usuario',)
    readonly_fields = ('created_at', 'updated_at')
