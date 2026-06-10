"""
Script para generar API Keys para empresas existentes que no tienen una.
Ejecutar con: python manage.py shell < generate_api_keys.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import Company

# Generar API Keys para empresas que no tienen
companies_updated = 0
for company in Company.objects.all():
    if not company.api_key:
        company.save()  # El método save() generará automáticamente la API Key
        companies_updated += 1
        print(f"✓ API Key generada para: {company.name}")
        print(f"  API Key: {company.api_key}")
    else:
        print(f"○ {company.name} ya tiene API Key: {company.api_key}")

print(f"\n✓ {companies_updated} empresas actualizadas con API Keys")
print("\nIMPORTANTE: Guarda estas API Keys de forma segura.")
print("Las necesitarás para configurar los formularios web de tus clientes.")
