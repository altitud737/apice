from django.contrib import admin
from .models import Company, User

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'name', 'is_active', 'created_at')
    list_filter = ('is_active', 'industry')
    search_fields = ('codigo', 'name')

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'company', 'is_staff')
    list_filter = ('company', 'is_staff')
