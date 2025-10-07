"""
Test completo: Login -> Logout -> Intentar Refresh (debe fallar)
"""
import requests
import json

BASE_URL = "http://localhost:8002/api/v1/auth"

credentials = {
    "email": "juan.perez@test.com",
    "password": "TestPass123!"
}

print("="*80)
print("TEST COMPLETO: LOGOUT Y REFRESH DESPUÉS DE LOGOUT")
print("="*80)

try:
    # Paso 1: Login
    print("\n[PASO 1] Login...")
    session = requests.Session()
    login_response = session.post(f"{BASE_URL}/login", json=credentials)
    
    if login_response.status_code != 200:
        print(f"❌ Login falló: {login_response.status_code}")
        exit(1)
    
    # Guardar la cookie
    refresh_cookie_before_logout = ''
    for cookie in session.cookies:
        if cookie.name == 'refresh_token':
            refresh_cookie_before_logout = cookie.value
            break
    
    print(f"✅ Login exitoso")
    print(f"   Cookie obtenida (primeros 50 chars): {refresh_cookie_before_logout[:50]}...")
    
    # Paso 2: Logout
    print("\n[PASO 2] Logout...")
    logout_response = session.post(f"{BASE_URL}/logout")
    
    if logout_response.status_code != 200:
        print(f"❌ Logout falló: {logout_response.status_code}")
        exit(1)
    
    print(f"✅ Logout exitoso")
    
    # Paso 3: Intentar refresh con la cookie vieja
    print("\n[PASO 3] Intentar refresh con cookie revocada...")
    
    # Crear nueva sesión con la cookie vieja
    new_session = requests.Session()
    new_session.cookies.set('refresh_token', refresh_cookie_before_logout)
    
    refresh_response = new_session.post(f"{BASE_URL}/refresh")
    
    print(f"\nStatus Code: {refresh_response.status_code}")
    
    if refresh_response.status_code == 401:
        error_detail = refresh_response.json().get("detail", {})
        error_code = error_detail.get("code", "")
        error_message = error_detail.get("message", "")
        
        print(f"✅ ÉXITO: Refresh rechazado correctamente")
        print(f"   Código: {error_code}")
        print(f"   Mensaje: {error_message}")
        
        if error_code == "INVALID_REFRESH":
            print("\n🎉 ¡PERFECTO! La sesión revocada no permite refresh")
        else:
            print(f"\n⚠️  Error inesperado: se esperaba INVALID_REFRESH")
            
    else:
        print(f"❌ ERROR: Refresh NO debería haber funcionado")
        print(f"   La sesión fue revocada, debería retornar 401")
        print(f"   Respuesta: {refresh_response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ ERROR: No se pudo conectar al servidor")
    print("   Asegúrate de que el servicio esté corriendo en http://localhost:8001")
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
