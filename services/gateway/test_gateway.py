"""
Test del Gateway - Flujo completo
Prueba todos los endpoints de auth a través del Gateway
"""
import requests
import json

# URLs
GATEWAY_URL = "http://localhost:8080"
AUTH_DIRECT_URL = "http://localhost:8003"

def print_separator(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_result(label, data):
    print(f"\n{label}:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

# ============================================================
# TEST 1: Health Check del Gateway
# ============================================================
print_separator("TEST 1: Health Check del Gateway")
try:
    response = requests.get(f"{GATEWAY_URL}/health")
    print(f"Status: {response.status_code}")
    print_result("Response", response.json())
    assert response.status_code == 200
    print("✅ Gateway está funcionando")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# ============================================================
# TEST 2: Register a través del Gateway
# ============================================================
print_separator("TEST 2: Register a través del Gateway")
register_data = {
    "email": f"gateway_test_{__import__('time').time()}@test.com",
    "password": "Test1234!",
    "nombre": "Gateway",
    "apellido": "Test"
}

try:
    response = requests.post(
        f"{GATEWAY_URL}/api/v1/auth/register",
        json=register_data
    )
    print(f"Status: {response.status_code}")
    print_result("Response", response.json())
    assert response.status_code == 201
    user_data = response.json()
    print("✅ Registro exitoso a través del Gateway")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# ============================================================
# TEST 3: Login a través del Gateway
# ============================================================
print_separator("TEST 3: Login a través del Gateway")
login_data = {
    "email": register_data["email"],
    "password": register_data["password"]
}

try:
    response = requests.post(
        f"{GATEWAY_URL}/api/v1/auth/login",
        json=login_data
    )
    print(f"Status: {response.status_code}")
    
    # Guardar access token
    login_result = response.json()
    print_result("Response", login_result)
    access_token = login_result["access_token"]
    
    # Verificar refresh token en cookies
    cookies = response.cookies
    print(f"\n🍪 Cookies recibidas: {dict(cookies)}")
    assert "refresh_token" in cookies
    
    print("✅ Login exitoso a través del Gateway")
    print(f"🔑 Access Token: {access_token[:50]}...")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# ============================================================
# TEST 4: /me a través del Gateway (con validación JWT)
# ============================================================
print_separator("TEST 4: GET /me a través del Gateway")
print("🔐 El Gateway validará el JWT antes de llamar a auth-svc")

try:
    response = requests.get(
        f"{GATEWAY_URL}/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    print(f"Status: {response.status_code}")
    print_result("Response", response.json())
    assert response.status_code == 200
    me_data = response.json()
    assert me_data["email"] == register_data["email"]
    print("✅ /me exitoso - Gateway validó JWT correctamente")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# ============================================================
# TEST 5: /me sin token (debe fallar en Gateway)
# ============================================================
print_separator("TEST 5: GET /me sin token (debe fallar)")
print("❌ El Gateway debe rechazar el request antes de llamar a auth-svc")

try:
    response = requests.get(f"{GATEWAY_URL}/api/v1/auth/me")
    print(f"Status: {response.status_code}")
    print_result("Response", response.json())
    assert response.status_code == 401
    error = response.json()
    assert error["detail"]["code"] == "MISSING_TOKEN"
    print("✅ Gateway rechazó correctamente el request sin token")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# ============================================================
# TEST 6: /me con token inválido (debe fallar en Gateway)
# ============================================================
print_separator("TEST 6: GET /me con token inválido")
print("❌ El Gateway debe rechazar el token inválido")

try:
    response = requests.get(
        f"{GATEWAY_URL}/api/v1/auth/me",
        headers={"Authorization": "Bearer token_invalido_123"}
    )
    print(f"Status: {response.status_code}")
    print_result("Response", response.json())
    assert response.status_code == 401
    error = response.json()
    assert error["detail"]["code"] == "INVALID_TOKEN"
    print("✅ Gateway rechazó correctamente el token inválido")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# ============================================================
# TEST 7: Refresh Token a través del Gateway
# ============================================================
print_separator("TEST 7: Refresh Token a través del Gateway")
print("🔄 Este endpoint es PÚBLICO (no requiere validación)")

try:
    response = requests.post(
        f"{GATEWAY_URL}/api/v1/auth/refresh",
        cookies=cookies
    )
    print(f"Status: {response.status_code}")
    refresh_result = response.json()
    print_result("Response", refresh_result)
    assert response.status_code == 200
    
    # Obtener nuevo access token
    new_access_token = refresh_result["access_token"]
    print(f"\n🔑 Nuevo Access Token: {new_access_token[:50]}...")
    
    # Verificar que el token cambió
    assert new_access_token != access_token
    print("✅ Refresh exitoso - Token rotado correctamente")
    
    # Actualizar cookies y token
    cookies = response.cookies
    access_token = new_access_token
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# ============================================================
# TEST 8: Verificar nuevo token funciona
# ============================================================
print_separator("TEST 8: Verificar nuevo token en /me")

try:
    response = requests.get(
        f"{GATEWAY_URL}/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    print(f"Status: {response.status_code}")
    print_result("Response", response.json())
    assert response.status_code == 200
    print("✅ Nuevo token funciona correctamente")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# ============================================================
# TEST 9: Logout a través del Gateway
# ============================================================
print_separator("TEST 9: Logout a través del Gateway")

try:
    response = requests.post(
        f"{GATEWAY_URL}/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        cookies=cookies
    )
    print(f"Status: {response.status_code}")
    print_result("Response", response.json())
    assert response.status_code == 200
    print("✅ Logout exitoso a través del Gateway")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# ============================================================
# TEST 10: Verificar que refresh ya no funciona después de logout
# ============================================================
print_separator("TEST 10: Refresh después de logout (debe fallar)")

try:
    response = requests.post(
        f"{GATEWAY_URL}/api/v1/auth/refresh",
        cookies=cookies
    )
    print(f"Status: {response.status_code}")
    print_result("Response", response.json())
    assert response.status_code == 401
    error = response.json()
    assert error["detail"]["code"] == "INVALID_REFRESH"
    print("✅ Refresh correctamente rechazado después del logout")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# ============================================================
# RESUMEN
# ============================================================
print_separator("🎉 TODOS LOS TESTS PASARON")
print("""
✅ Gateway funcionando correctamente:
  - Health check OK
  - Register a través del gateway
  - Login a través del gateway
  - /me con validación JWT en gateway
  - Rechaza requests sin token
  - Rechaza tokens inválidos
  - Refresh token (endpoint público)
  - Logout con validación
  - Refresh después de logout correctamente rechazado

🔥 El Gateway está validando JWT correctamente antes de llamar a los servicios!
""")
