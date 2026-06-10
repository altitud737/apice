"""
Script para crear un usuario de test en MercadoLibre.
Uso:
  1. Primero obtené un access_token autorizando tu app
  2. Ejecutá: python ml_create_test_user.py <ACCESS_TOKEN>

Si no tenés token, podés intentar obtener uno con el flujo de code:
  1. Abrí en el navegador:
     https://auth.mercadolibre.com.ar/authorization?response_type=code&client_id=4428398556540438&redirect_uri=https://bcfb-181-230-38-73.ngrok-free.app/integrations/mercadolibre/callback/
  2. Autorizá la app y copiá el code de la URL resultante
  3. Ejecutá: python ml_create_test_user.py --code TG-XXXX
"""
import sys
import requests

CLIENT_ID = "4428398556540438"
CLIENT_SECRET = "He3XGe4QWabg39kD51lRbVGyJIllggIc"
REDIRECT_URI = "https://bcfb-181-230-38-73.ngrok-free.app/integrations/mercadolibre/callback/"


def get_token_from_code(code):
    """Intercambia un authorization code por un access token."""
    resp = requests.post("https://api.mercadolibre.com/oauth/token", json={
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    })
    print(f"Token response status: {resp.status_code}")
    data = resp.json()
    if resp.status_code != 200:
        print(f"Error: {data}")
        return None
    print(f"Access token obtenido para user_id: {data.get('user_id')}")
    return data["access_token"]


def create_test_user(access_token):
    """Crea un usuario de test en MLA (Argentina)."""
    resp = requests.post(
        "https://api.mercadolibre.com/users/test_user",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"site_id": "MLA"},
    )
    print(f"\nCreate test user response status: {resp.status_code}")
    data = resp.json()
    if resp.status_code in (200, 201):
        print("\n========================================")
        print("  USUARIO DE TEST CREADO EXITOSAMENTE")
        print("========================================")
        print(f"  ID:       {data.get('id')}")
        print(f"  Nickname: {data.get('nickname')}")
        print(f"  Password: {data.get('password')}")
        print(f"  Status:   {data.get('site_status')}")
        print("========================================")
        print("\nGUARDA ESTOS DATOS! No se pueden recuperar despues.")
        print(f"\nPara loguearte: https://www.mercadolibre.com.ar")
        print(f"  Usuario: {data.get('nickname')}")
        print(f"  Password: {data.get('password')}")
    else:
        print(f"Error: {data}")
    return data


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "--code":
        if len(sys.argv) < 3:
            print("Falta el código. Uso: python ml_create_test_user.py --code TG-XXXX")
            sys.exit(1)
        token = get_token_from_code(sys.argv[2])
        if token:
            create_test_user(token)
    else:
        create_test_user(sys.argv[1])
