"""
Script de prueba para verificar el registro de usuarios
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import User, Company
from django.contrib.auth import authenticate

def test_registro():
    """Prueba el flujo completo de registro"""
    
    # Limpiar usuario de prueba si existe
    User.objects.filter(email='test@apice.com').delete()
    
    print("=" * 60)
    print("PRUEBA DE REGISTRO - Apice con django-allauth")
    print("=" * 60)
    
    # 1. Crear empresa
    print("\n[1/5] Creando empresa...")
    company = Company.objects.create(name="Empresa de Prueba")
    print(f"✅ Empresa creada: {company.name}")
    print(f"   API Key: {company.api_key}")
    
    # 2. Crear usuario
    print("\n[2/5] Creando usuario...")
    user = User.objects.create_user(
        username='testuser',
        email='test@apice.com',
        password='TestPass123',
        company=company
    )
    print(f"✅ Usuario creado: {user.email}")
    print(f"   Username: {user.username}")
    print(f"   Empresa: {user.company.name}")
    
    # 3. Verificar autenticación
    print("\n[3/5] Verificando autenticación...")
    auth_user = authenticate(username='test@apice.com', password='TestPass123!')
    if auth_user:
        print(f"✅ Autenticación exitosa")
    else:
        print(f"❌ Error en autenticación")
        return False
    
    # 4. Verificar relación User-Company
    print("\n[4/5] Verificando relación User-Company...")
    user_from_db = User.objects.get(email='test@apice.com')
    if user_from_db.company:
        print(f"✅ Usuario tiene empresa asignada")
        print(f"   Empresa: {user_from_db.company.name}")
        print(f"   API Key: {user_from_db.company.api_key}")
    else:
        print(f"❌ Usuario NO tiene empresa asignada")
        return False
    
    # 5. Verificar que la empresa tiene el usuario
    print("\n[5/5] Verificando usuarios de la empresa...")
    company_users = company.users.all()
    print(f"✅ Empresa tiene {company_users.count()} usuario(s)")
    for u in company_users:
        print(f"   - {u.email}")
    
    print("\n" + "=" * 60)
    print("✅ TODAS LAS PRUEBAS PASARON CORRECTAMENTE")
    print("=" * 60)
    print("\nResumen:")
    print(f"  Email: {user.email}")
    print(f"  Password: TestPass123!")
    print(f"  Empresa: {company.name}")
    print(f"  API Key: {company.api_key}")
    print("\nPuedes usar estas credenciales para hacer login en:")
    print("  http://127.0.0.1:8000/accounts/login/")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    try:
        test_registro()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
