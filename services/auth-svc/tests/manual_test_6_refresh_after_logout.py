"""
Test 6: Intentar refresh después de logout (debe fallar)
"""
import requests
import json
import os

BASE_URL = "http://localhost:8001/api/v1/auth"
TOKENS_FILE = "tokens.json"
TOKENS_BACKUP_FILE = "tokens_backup.json"

print("="*80)
print("TEST 6: REFRESH DESPUÉS DE LOGOUT (debe fallar)")
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
    
    # Si no hay cookie, intentar leer del backup (de antes del logout)
    if not refresh_cookie and os.path.exists(TOKENS_BACKUP_FILE):
        print("⚠️  No hay refresh_cookie en tokens.json, usando backup...")
        with open(TOKENS_BACKUP_FILE, 'r') as f:
            tokens_backup = json.load(f)
        refresh_cookie = tokens_backup.get('refresh_cookie_before_logout', '')
    
    if not refresh_cookie:
        print("❌ ERROR: No hay refresh_cookie")
        print("   Este test necesita una cookie de una sesión ya cerrada")
        print("   Ejecuta manual_test_2_login.py, luego manual_test_5_logout.py")
        print("   y luego este test")
        exit(1)
    
    print(f"\nIntentando usar Refresh Cookie revocada (primeros 50 chars):")
    print(refresh_cookie[:50] + "..." if len(refresh_cookie) > 50 else refresh_cookie)
    
    # Crear sesión con la cookie revocada
    session = requests.Session()
    session.cookies.set('refresh_token', refresh_cookie)
    
    # Hacer request a /refresh (debe fallar)
    print(f"\nURL: {BASE_URL}/refresh")
    response = session.post(f"{BASE_URL}/refresh")
    
    print(f"\n{'='*80}")
    print(f"Status Code: {response.status_code}")
    print(f"{'='*80}")
    
    if response.status_code == 401:
        print("✅ ÉXITO: Refresh rechazado correctamente (sesión revocada)")
        print(f"\nRespuesta:")
        print(json.dumps(response.json(), indent=2))
    elif response.status_code == 200:
        print("❌ ERROR: Refresh NO debería haber funcionado")
        print("   La sesión fue revocada con logout, no debería aceptar el refresh")
    else:
        print(f"⚠️  Código inesperado: {response.status_code}")
        print(f"\nRespuesta:")
        print(response.text)
        
except requests.exceptions.ConnectionError:
    print("❌ ERROR: No se pudo conectar al servidor")
    print("   Asegúrate de que el servicio esté corriendo en http://localhost:8000")
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
