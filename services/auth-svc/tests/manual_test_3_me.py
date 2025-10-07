"""
Test 3: Acceder a /me con access token
"""
import requests
import json
import os

BASE_URL = "http://localhost:8002/api/v1/auth"
TOKENS_FILE = "tokens.json"

print("="*80)
print("TEST 3: ACCESO A /ME CON ACCESS TOKEN")
print("="*80)

try:
    # Leer tokens del archivo
    if not os.path.exists(TOKENS_FILE):
        print(f"❌ ERROR: No se encontró el archivo {TOKENS_FILE}")
        print("   Ejecuta primero manual_test_2_login.py")
        exit(1)
    
    with open(TOKENS_FILE, 'r') as f:
        tokens = json.load(f)
    
    access_token = tokens.get('access_token')
    if not access_token:
        print("❌ ERROR: No hay access_token en el archivo")
        exit(1)
    
    print(f"\nUsando Access Token (primeros 50 chars):")
    print(access_token[:50] + "...")
    
    # Hacer request a /me
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    print(f"\nURL: {BASE_URL}/me")
    response = requests.get(f"{BASE_URL}/me", headers=headers)
    
    print(f"\n{'='*80}")
    print(f"Status Code: {response.status_code}")
    print(f"{'='*80}")
    
    if response.status_code == 200:
        user_data = response.json()
        print("✅ ÉXITO: Access token válido")
        print(f"\nDatos del usuario:")
        print(json.dumps(user_data, indent=2))
    elif response.status_code == 401:
        print("❌ ERROR: Token inválido o expirado")
        print(f"\nRespuesta:")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"❌ ERROR: Código {response.status_code}")
        print(f"\nRespuesta:")
        print(response.text)
        
except requests.exceptions.ConnectionError:
    print("❌ ERROR: No se pudo conectar al servidor")
    print("   Asegúrate de que el servicio esté corriendo en http://localhost:8000")
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
