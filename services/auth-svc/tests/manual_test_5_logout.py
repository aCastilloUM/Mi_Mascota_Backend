"""
Test 5: Logout - revocar sesión
"""
import requests
import json
import os

BASE_URL = "http://localhost:8002/api/v1/auth"
TOKENS_FILE = "tokens.json"

print("="*80)
print("TEST 5: LOGOUT")
print("="*80)

try:
    # Leer tokens del archivo
    if not os.path.exists(TOKENS_FILE):
        print(f"❌ ERROR: No se encontró el archivo {TOKENS_FILE}")
        print("   Ejecuta primero manual_test_2_login.py")
        exit(1)
    
    with open(TOKENS_FILE, 'r') as f:
        tokens = json.load(f)
    
    refresh_cookie = tokens.get('refresh_cookie', '')
    
    if not refresh_cookie:
        print("❌ ERROR: No hay refresh_cookie en el archivo")
        exit(1)
    
    print(f"\nRefresh Cookie ANTES del logout (primeros 50 chars):")
    print(refresh_cookie[:50] + "..." if len(refresh_cookie) > 50 else refresh_cookie)
    
    # Crear sesión con la cookie
    session = requests.Session()
    session.cookies.set('refresh_token', refresh_cookie)
    
    # Hacer request a /logout
    print(f"\nURL: {BASE_URL}/logout")
    response = session.post(f"{BASE_URL}/logout")
    
    print(f"\n{'='*80}")
    print(f"Status Code: {response.status_code}")
    print(f"{'='*80}")
    
    if response.status_code == 200:
        data = response.json()
        
        print("✅ ÉXITO: Logout exitoso")
        print(f"\nRespuesta:")
        print(json.dumps(data, indent=2))
        
        # Verificar que la cookie se limpió
        new_refresh_cookie = session.cookies.get('refresh_token', '')
        print(f"\nRefresh Cookie DESPUÉS del logout:")
        print(f"'{new_refresh_cookie}' (vacía = limpiada correctamente)")
        
        if not new_refresh_cookie:
            print("\n✅ Cookie limpiada correctamente")
        else:
            print("\n⚠️  Cookie NO se limpió")
        
        # Limpiar archivo de tokens
        tokens['access_token'] = ""
        tokens['refresh_cookie'] = ""
        
        with open(TOKENS_FILE, 'w') as f:
            json.dump(tokens, f, indent=2)
        
        print(f"\n✅ Tokens limpiados en: {TOKENS_FILE}")
        
    else:
        print(f"⚠️  Código: {response.status_code}")
        print(f"\nRespuesta:")
        print(response.text)
        
except requests.exceptions.ConnectionError:
    print("❌ ERROR: No se pudo conectar al servidor")
    print("   Asegúrate de que el servicio esté corriendo en http://localhost:8000")
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
