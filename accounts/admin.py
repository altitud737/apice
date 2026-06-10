from django.contrib import admin
from .models import Company, User

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'company', 'is_staff')
    list_filter = ('company', 'is_staff')
