"""
Test 4: Usar refresh token para obtener nuevo access token
"""
import requests
import json
import os

BASE_URL = "http://localhost:8002/api/v1/auth"
TOKENS_FILE = "tokens.json"

print("="*80)
print("TEST 4: REFRESH TOKEN")
print("="*80)

try:
    # Leer tokens del archivo
    if not os.path.exists(TOKENS_FILE):
        print(f"❌ ERROR: No se encontró el archivo {TOKENS_FILE}")
        print("   Ejecuta primero manual_test_2_login.py")
        exit(1)
    
    with open(TOKENS_FILE, 'r') as f:
        tokens = json.load(f)
    
    old_access_token = tokens.get('access_token', '')
    refresh_cookie = tokens.get('refresh_cookie', '')
    
    if not refresh_cookie:
        print("❌ ERROR: No hay refresh_cookie en el archivo")
        exit(1)
    
    print(f"\nAccess Token ANTERIOR (primeros 50 chars):")
    print(old_access_token[:50] + "...")
    
    print(f"\nRefresh Cookie (primeros 50 chars):")
    print(refresh_cookie[:50] + "..." if len(refresh_cookie) > 50 else refresh_cookie)
    
    # Crear sesión con la cookie
    session = requests.Session()
    session.cookies.set('refresh_token', refresh_cookie)
    
    # Hacer request a /refresh
    print(f"\nURL: {BASE_URL}/refresh")
    response = session.post(f"{BASE_URL}/refresh")
    
    print(f"\n{'='*80}")
    print(f"Status Code: {response.status_code}")
    print(f"{'='*80}")
    
    if response.status_code == 200:
        data = response.json()
        new_access_token = data['access_token']
        
        # Obtener la última cookie refresh_token (la más reciente)
        new_refresh_cookie = ''
        for cookie in session.cookies:
            if cookie.name == 'refresh_token':
                new_refresh_cookie = cookie.value
        
        print("✅ ÉXITO: Refresh exitoso")
        
        print(f"\nNUEVO Access Token (primeros 50 chars):")
        print(new_access_token[:50] + "...")
        
        print(f"\nNUEVO Refresh Cookie (primeros 50 chars):")
        print(new_refresh_cookie[:50] + "..." if len(new_refresh_cookie) > 50 else new_refresh_cookie)
        
        # Verificar que los tokens cambiaron (rotación)
        print(f"\n{'='*80}")
        print("VERIFICACIÓN DE ROTACIÓN:")
        print(f"{'='*80}")
        
        if old_access_token != new_access_token:
            print("✅ Access token ROTÓ correctamente (es diferente)")
        else:
            print("⚠️  Access token NO cambió")
        
        if refresh_cookie != new_refresh_cookie:
            print("✅ Refresh cookie ROTÓ correctamente (es diferente)")
        else:
            print("⚠️  Refresh cookie NO cambió")
        
        # Guardar nuevos tokens
        tokens['access_token'] = new_access_token
        tokens['refresh_cookie'] = new_refresh_cookie
        
        with open(TOKENS_FILE, 'w') as f:
            json.dump(tokens, f, indent=2)
        
        print(f"\n✅ Nuevos tokens guardados en: {TOKENS_FILE}")
        
    elif response.status_code == 401:
        print("❌ ERROR: Refresh token inválido o expirado")
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
