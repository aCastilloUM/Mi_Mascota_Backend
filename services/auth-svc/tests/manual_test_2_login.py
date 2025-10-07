"""
Test 2: Login y guardar tokens
"""
import requests
import json
import os

BASE_URL = "http://localhost:8002/api/v1/auth"
TOKENS_FILE = "tokens.json"

# Credenciales
credentials = {
    "email": "juan.perez@test.com",
    "password": "TestPass123!"
}

print("="*80)
print("TEST 2: LOGIN")
print("="*80)
print(f"\nURL: {BASE_URL}/login")
print(f"\nCredenciales:")
print(json.dumps(credentials, indent=2))

try:
    # Crear sesión para mantener cookies
    session = requests.Session()
    response = session.post(f"{BASE_URL}/login", json=credentials)
    
    print(f"\n{'='*80}")
    print(f"Status Code: {response.status_code}")
    print(f"{'='*80}")
    
    if response.status_code == 200:
        data = response.json()
        
        print("✅ ÉXITO: Login exitoso")
        print(f"\nAccess Token (primeros 50 chars):")
        print(data['access_token'][:50] + "...")
        
        # Obtener refresh cookie
        refresh_cookie = session.cookies.get('refresh_token', '')
        print(f"\nRefresh Cookie (primeros 50 chars):")
        print(refresh_cookie[:50] + "..." if len(refresh_cookie) > 50 else refresh_cookie)
        
        # Guardar tokens en archivo
        tokens_data = {
            "access_token": data['access_token'],
            "refresh_cookie": refresh_cookie,
            "token_type": data.get('token_type', 'bearer')
        }
        
        with open(TOKENS_FILE, 'w') as f:
            json.dump(tokens_data, f, indent=2)
        
        print(f"\n✅ Tokens guardados en: {TOKENS_FILE}")
        
    elif response.status_code == 401:
        print("❌ ERROR: Credenciales inválidas")
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
