from django.contrib import admin
from .models import Idioma, EmpresaIdioma, Cliente, Vendedor


@admin.register(Idioma)
class IdiomaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descripcion', 'activo')
    list_filter = ('activo',)
    search_fields = ('codigo', 'descripcion')


@admin.register(EmpresaIdioma)
class EmpresaIdiomaAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'idioma', 'es_predeterminado', 'created_at')
    list_filter = ('empresa', 'idioma', 'es_predeterminado')
    search_fields = ('empresa__name', 'idioma__codigo', 'idioma__descripcion')
    readonly_fields = ('created_at',)


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
