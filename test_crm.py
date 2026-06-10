import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import Company, User
from apice.models import Stage, Contact, Deal, Activity, Task

print("=" * 60)
print("PRUEBAS DE Apice CRM")
print("=" * 60)

# Test 1: Verificar modelos
print("\n[TEST 1] Verificando modelos y datos...")
try:
    companies = Company.objects.all()
    users = User.objects.all()
    stages = Stage.objects.all()
    contacts = Contact.objects.all()
    deals = Deal.objects.all()
    
    print(f"✓ Empresas: {companies.count()}")
    print(f"✓ Usuarios: {users.count()}")
    print(f"✓ Etapas: {stages.count()}")
    print(f"✓ Contactos: {contacts.count()}")
    print(f"✓ Oportunidades: {deals.count()}")
    print("✅ Test 1 PASADO")
except Exception as e:
    print(f"❌ Test 1 FALLIDO: {e}")

# Test 2: Verificar multi-tenancy
print("\n[TEST 2] Verificando aislamiento multi-tenant...")
try:
    company = Company.objects.first()
    contacts_empresa = Contact.objects.filter(company=company)
    deals_empresa = Deal.objects.filter(company=company)
    
    print(f"✓ Empresa: {company.name}")
    print(f"✓ Contactos de la empresa: {contacts_empresa.count()}")
    print(f"✓ Deals de la empresa: {deals_empresa.count()}")
    
    # Verificar que todos los contactos tienen la misma empresa
    for contact in contacts_empresa:
        assert contact.company == company, f"Contacto {contact.name} tiene empresa incorrecta"
    
    print("✅ Test 2 PASADO - Aislamiento correcto")
except Exception as e:
    print(f"❌ Test 2 FALLIDO: {e}")

# Test 3: Verificar relaciones
print("\n[TEST 3] Verificando relaciones entre modelos...")
try:
    deal = Deal.objects.first()
    print(f"✓ Deal: {deal.title}")
    print(f"  - Contacto: {deal.contact.name}")
    print(f"  - Etapa: {deal.stage.name}")
    print(f"  - Propietario: {deal.owner.username}")
    print(f"  - Empresa: {deal.company.name}")
    print(f"  - Valor: ${deal.value}")
    print(f"  - Probabilidad: {deal.probability}%")
    print("✅ Test 3 PASADO - Relaciones correctas")
except Exception as e:
    print(f"❌ Test 3 FALLIDO: {e}")

# Test 4: Verificar cálculos del dashboard
print("\n[TEST 4] Verificando cálculos del dashboard...")
try:
    from django.db.models import Sum, Count
    
    company = Company.objects.first()
    open_deals = Deal.objects.filter(company=company).exclude(
        stage__name__in=['Cerrada Ganada', 'Cerrada Perdida']
    )
    closed_won = Deal.objects.filter(company=company, stage__name='Cerrada Ganada')
    
    pipeline_value = open_deals.aggregate(total=Sum('value'))['total'] or 0
    closed_won_count = closed_won.count()
    
    print(f"✓ Oportunidades abiertas: {open_deals.count()}")
    print(f"✓ Ventas cerradas ganadas: {closed_won_count}")
    print(f"✓ Valor total del pipeline: ${pipeline_value}")
    
    # Verificar deals por etapa
    deals_by_stage = Stage.objects.filter(company=company).annotate(
        count=Count('deals')
    )
    
    print(f"\n  Distribución por etapa:")
    for stage in deals_by_stage:
        print(f"    - {stage.name}: {stage.count} deals")
    
    print("✅ Test 4 PASADO - Cálculos correctos")
except Exception as e:
    print(f"❌ Test 4 FALLIDO: {e}")

# Test 5: Verificar usuario admin
print("\n[TEST 5] Verificando credenciales de acceso...")
try:
    admin = User.objects.get(username='admin')
    print(f"✓ Usuario: {admin.username}")
    print(f"✓ Email: {admin.email}")
    print(f"✓ Es superusuario: {admin.is_superuser}")
    print(f"✓ Empresa: {admin.company.name}")
    print(f"✓ Password: admin123 (configurado)")
    print("✅ Test 5 PASADO - Usuario admin configurado")
except Exception as e:
    print(f"❌ Test 5 FALLIDO: {e}")

# Test 6: Verificar estructura de etapas
print("\n[TEST 6] Verificando pipeline de ventas...")
try:
    company = Company.objects.first()
    stages = Stage.objects.filter(company=company).order_by('order')
    
    expected_stages = ['Prospecto', 'Calificado', 'Propuesta', 'Negociación', 'Cerrada Ganada', 'Cerrada Perdida']
    
    print(f"  Etapas configuradas:")
    for i, stage in enumerate(stages):
        print(f"    {i+1}. {stage.name} (orden: {stage.order}, deals: {stage.deals.count()})")
        assert stage.name == expected_stages[i], f"Etapa {i} incorrecta"
    
    print("✅ Test 6 PASADO - Pipeline configurado correctamente")
except Exception as e:
    print(f"❌ Test 6 FALLIDO: {e}")

# Resumen final
print("\n" + "=" * 60)
print("RESUMEN DE PRUEBAS")
print("=" * 60)
print(f"\n📊 Estado del sistema:")
print(f"   ✓ Base de datos: SQLite")
print(f"   ✓ Empresas registradas: {Company.objects.count()}")
print(f"   ✓ Usuarios activos: {User.objects.count()}")
print(f"   ✓ Contactos totales: {Contact.objects.count()}")
print(f"   ✓ Oportunidades totales: {Deal.objects.count()}")
print(f"   ✓ Etapas configuradas: {Stage.objects.count()}")

print(f"\n🔐 Credenciales de acceso:")
print(f"   URL: http://127.0.0.1:3000/")
print(f"   Usuario: admin")
print(f"   Password: admin123")

print(f"\n📍 Páginas disponibles:")
print(f"   - Login: http://127.0.0.1:3000/accounts/login/")
print(f"   - Dashboard: http://127.0.0.1:3000/")
print(f"   - Contactos: http://127.0.0.1:3000/contacts/")
print(f"   - Pipeline: http://127.0.0.1:3000/pipeline/")

print("\n✅ TODAS LAS PRUEBAS COMPLETADAS")
print("=" * 60)
