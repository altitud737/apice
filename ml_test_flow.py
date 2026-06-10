"""
Script para probar el flujo completo de MercadoLibre con usuarios de test.

Pasos:
1. Crear segundo usuario de test (comprador)
2. Publicar producto con el vendedor (TESTUSER6675764094163994699)
3. Hacer pregunta con el comprador
4. Hacer compra con el comprador

Requiere: access_token del vendedor
"""
import requests
import sys

# Credenciales del vendedor (ya conectado en el CRM)
SELLER_USER = "TESTUSER6675764094163994699"
SELLER_PASSWORD = "8lCLnMYjBb"

def create_buyer_test_user(seller_access_token):
    """Crea un segundo usuario de test que actuará como comprador."""
    resp = requests.post(
        "https://api.mercadolibre.com/users/test_user",
        headers={"Authorization": f"Bearer {seller_access_token}"},
        json={"site_id": "MLA"},
    )
    print(f"\n[CREATE BUYER] Status: {resp.status_code}")
    data = resp.json()
    if resp.status_code in (200, 201):
        print("========================================")
        print("  COMPRADOR TEST CREADO")
        print("========================================")
        print(f"  ID:       {data.get('id')}")
        print(f"  Nickname: {data.get('nickname')}")
        print(f"  Password: {data.get('password')}")
        print("========================================")
        return data
    else:
        print(f"Error: {data}")
        return None


def create_test_listing(access_token):
    """Crea una publicación de prueba."""
    listing_data = {
        "title": "Item de Prueba - Por favor, NO OFERTAR",
        "category_id": "MLA5726",  # Otros (categoría genérica)
        "price": 100,
        "currency_id": "ARS",
        "available_quantity": 10,
        "buying_mode": "buy_it_now",
        "listing_type_id": "free",
        "condition": "new",
        "description": {"plain_text": "Producto de prueba para testing de webhooks"},
        "pictures": [],
    }
    
    resp = requests.post(
        "https://api.mercadolibre.com/items",
        headers={"Authorization": f"Bearer {access_token}"},
        json=listing_data,
    )
    print(f"\n[CREATE LISTING] Status: {resp.status_code}")
    data = resp.json()
    if resp.status_code in (200, 201):
        print(f"✅ Producto creado: {data.get('id')}")
        print(f"   Título: {data.get('title')}")
        print(f"   Permalink: {data.get('permalink')}")
        return data
    else:
        print(f"❌ Error: {data}")
        return None


def post_question(item_id, buyer_access_token):
    """Publica una pregunta como comprador."""
    question_data = {
        "item_id": item_id,
        "text": "¿Está disponible? Pregunta de prueba",
    }
    
    resp = requests.post(
        "https://api.mercadolibre.com/questions",
        headers={"Authorization": f"Bearer {buyer_access_token}"},
        json=question_data,
    )
    print(f"\n[POST QUESTION] Status: {resp.status_code}")
    data = resp.json()
    if resp.status_code in (200, 201):
        print(f"✅ Pregunta creada: {data.get('id')}")
        print(f"   Texto: {data.get('text')}")
        return data
    else:
        print(f"❌ Error: {data}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python ml_test_flow.py <SELLER_ACCESS_TOKEN>")
        print("\nPara obtener el access_token del vendedor:")
        print("1. Andá a Django admin: http://localhost:8000/admin/")
        print("2. Buscá 'MercadoLibre integrations'")
        print("3. Copiá el access_token del usuario TESTUSER6675764094163994699")
        sys.exit(1)
    
    seller_token = sys.argv[1]
    
    print("=" * 50)
    print("  FLUJO DE PRUEBA MERCADOLIBRE")
    print("=" * 50)
    
    # Paso 1: Crear comprador
    print("\n📝 PASO 1: Crear usuario comprador...")
    buyer = create_buyer_test_user(seller_token)
    if not buyer:
        print("❌ No se pudo crear el comprador. Abortando.")
        sys.exit(1)
    
    buyer_id = buyer['id']
    buyer_nick = buyer['nickname']
    buyer_pass = buyer['password']
    
    # Paso 2: Crear publicación
    print("\n📦 PASO 2: Crear publicación de prueba...")
    listing = create_test_listing(seller_token)
    if not listing:
        print("❌ No se pudo crear la publicación. Abortando.")
        sys.exit(1)
    
    item_id = listing['id']
    
    # Paso 3: Obtener token del comprador (necesario para preguntar/comprar)
    print(f"\n🔑 PASO 3: Obtener token del comprador...")
    print(f"   ⚠️  MANUAL: Necesitás autenticar al comprador via OAuth")
    print(f"   Usuario: {buyer_nick}")
    print(f"   Password: {buyer_pass}")
    print(f"\n   Para hacer la pregunta, necesitás el access_token del comprador.")
    print(f"   Podés obtenerlo conectando otra integración en tu CRM con este usuario,")
    print(f"   o usando el flujo OAuth manual.")
    
    print("\n" + "=" * 50)
    print("  RESUMEN")
    print("=" * 50)
    print(f"✅ Vendedor: {SELLER_USER}")
    print(f"✅ Comprador: {buyer_nick} / {buyer_pass}")
    print(f"✅ Producto: {item_id}")
    print(f"   Link: {listing.get('permalink')}")
    print("\n📋 PRÓXIMOS PASOS MANUALES:")
    print(f"1. Abrí el link del producto en incógnito")
    print(f"2. Logueate como {buyer_nick}")
    print(f"3. Hacé una pregunta")
    print(f"4. Comprá el producto (usá tarjeta de prueba)")
    print(f"\n👀 Verificá en tu CRM:")
    print(f"   - /integrations/mercadolibre/status/")
    print(f"   - Deberías ver webhooks recibidos")
    print(f"   - Contact, Lead, Deal creados")
    print("=" * 50)
