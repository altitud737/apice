import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import Company, User
from apice.models import Stage, Contact, Deal
from datetime import date, timedelta

print("Creando datos de prueba...")

# Obtener o crear empresa
if Company.objects.exists():
    company = Company.objects.first()
    print(f"✓ Usando empresa existente: {company.name}")
else:
    company = Company.objects.create(name="Empresa Demo")
    print(f"✓ Empresa creada: {company.name}")

# Crear usuario admin
if not User.objects.filter(username='admin').exists():
    user = User.objects.create_superuser(
        username='admin',
        email='admin@demo.com',
        password='admin123',
        company=company
    )
    print(f"✓ Usuario admin creado (username: admin, password: admin123)")
else:
    user = User.objects.get(username='admin')
    print(f"✓ Usuario admin ya existe")

# Crear etapas del pipeline si no existen
if not Stage.objects.filter(company=company).exists():
    stages_names = ['Prospecto', 'Calificado', 'Propuesta', 'Negociación', 'Cerrada Ganada', 'Cerrada Perdida']
    stages_objs = []
    for i, name in enumerate(stages_names):
        stage = Stage.objects.create(company=company, name=name, order=i)
        stages_objs.append(stage)
        print(f"✓ Etapa creada: {name}")
else:
    stages_objs = list(Stage.objects.filter(company=company).order_by('order'))
    print(f"✓ Etapas ya existen ({len(stages_objs)} etapas)")

# Crear contactos si no existen
if not Contact.objects.filter(company=company).exists():
    contacts_data = [
        {
            'name': 'Juan Pérez',
            'email': 'juan@techcorp.com',
            'phone': '+54 11 1234-5678',
            'company_name': 'Tech Corp',
            'status': 'Calificado',
            'interest_level': 'Alto'
        },
        {
            'name': 'María García',
            'email': 'maria@globalsolutions.com',
            'phone': '+54 11 8765-4321',
            'company_name': 'Global Solutions',
            'status': 'Nuevo',
            'interest_level': 'Medio'
        },
        {
            'name': 'Carlos Rodríguez',
            'email': 'carlos@innovatech.com',
            'phone': '+54 11 5555-1234',
            'company_name': 'Innova Tech',
            'status': 'Contactado',
            'interest_level': 'Alto'
        },
        {
            'name': 'Ana Martínez',
            'email': 'ana@digitalplus.com',
            'phone': '+54 11 9999-8888',
            'company_name': 'Digital Plus',
            'status': 'Calificado',
            'interest_level': 'Medio'
        },
        {
            'name': 'Roberto Silva',
            'email': 'roberto@smartbiz.com',
            'phone': '+54 11 7777-6666',
            'company_name': 'Smart Biz',
            'status': 'Nuevo',
            'interest_level': 'Bajo'
        }
    ]
    
    contacts = []
    for contact_data in contacts_data:
        contact = Contact.objects.create(
            company=company,
            owner=user,
            **contact_data
        )
        contacts.append(contact)
        print(f"✓ Contacto creado: {contact.name}")
else:
    contacts = list(Contact.objects.filter(company=company))
    print(f"✓ Contactos ya existen ({len(contacts)} contactos)")

# Crear deals si no existen
if not Deal.objects.filter(company=company).exists():
    deals_data = [
        {
            'title': 'Implementación Apice',
            'value': 5000,
            'probability': 70,
            'contact': contacts[0],
            'stage': stages_objs[2],  # Propuesta
            'expected_close_date': date.today() + timedelta(days=15)
        },
        {
            'title': 'Consultoría IT',
            'value': 2500,
            'probability': 40,
            'contact': contacts[1],
            'stage': stages_objs[1],  # Calificado
            'expected_close_date': date.today() + timedelta(days=30)
        },
        {
            'title': 'Desarrollo Web',
            'value': 8000,
            'probability': 60,
            'contact': contacts[2],
            'stage': stages_objs[3],  # Negociación
            'expected_close_date': date.today() + timedelta(days=20)
        },
        {
            'title': 'Soporte Técnico Anual',
            'value': 3500,
            'probability': 80,
            'contact': contacts[3],
            'stage': stages_objs[2],  # Propuesta
            'expected_close_date': date.today() + timedelta(days=10)
        },
        {
            'title': 'Migración Cloud',
            'value': 12000,
            'probability': 30,
            'contact': contacts[4],
            'stage': stages_objs[0],  # Prospecto
            'expected_close_date': date.today() + timedelta(days=45)
        },
        {
            'title': 'Capacitación Staff',
            'value': 1500,
            'probability': 90,
            'contact': contacts[0],
            'stage': stages_objs[4],  # Cerrada Ganada
            'expected_close_date': date.today() - timedelta(days=5)
        }
    ]
    
    for deal_data in deals_data:
        deal = Deal.objects.create(
            company=company,
            owner=user,
            **deal_data
        )
        print(f"✓ Deal creado: {deal.title} - ${deal.value}")
else:
    print(f"✓ Deals ya existen ({Deal.objects.filter(company=company).count()} deals)")

print("\n✅ Configuración completada!")
print(f"\n📊 Resumen:")
print(f"   - Empresa: {company.name}")
print(f"   - Usuario: admin / admin123")
print(f"   - Contactos: {Contact.objects.filter(company=company).count()}")
print(f"   - Etapas: {Stage.objects.filter(company=company).count()}")
print(f"   - Oportunidades: {Deal.objects.filter(company=company).count()}")
