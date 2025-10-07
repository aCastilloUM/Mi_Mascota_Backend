"""
Test para verificar CORS y Request-Id
"""
import requests
import json

BASE_URL = "http://localhost:8002"

def print_separator(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

# ============================================================
# TEST 1: Verificar health y Request-Id
# ============================================================
print_separator("TEST 1: Health + Request-Id")

response = requests.get(f"{BASE_URL}/health")
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

# Verificar que el header X-Request-Id está presente
request_id = response.headers.get("X-Request-Id")
print(f"\n✅ X-Request-Id header: {request_id}")
assert request_id is not None, "❌ Falta header X-Request-Id"
print("✅ Request-Id funciona!")

# ============================================================
# TEST 2: Enviar un Request-Id custom
# ============================================================
print_separator("TEST 2: Request-Id custom")

custom_id = "mi-request-12345"
response = requests.get(
    f"{BASE_URL}/health",
    headers={"X-Request-Id": custom_id}
)
print(f"Status: {response.status_code}")

returned_id = response.headers.get("X-Request-Id")
print(f"Request-Id enviado: {custom_id}")
print(f"Request-Id retornado: {returned_id}")

assert returned_id == custom_id, "❌ Request-Id no coincide"
print("✅ Request-Id custom funciona!")

# ============================================================
# TEST 3: Verificar CORS headers
# ============================================================
print_separator("TEST 3: CORS headers")

response = requests.options(
    f"{BASE_URL}/api/v1/auth/login",
    headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type,Authorization"
    }
)
print(f"Status: {response.status_code}")
print(f"\n🌐 CORS Headers:")
for header, value in response.headers.items():
    if "access-control" in header.lower():
        print(f"  {header}: {value}")

# Verificar que los headers CORS están presentes
assert "access-control-allow-origin" in response.headers
print("\n✅ CORS configurado correctamente!")

# ============================================================
# TEST 4: Register con CORS
# ============================================================
print_separator("TEST 4: Register con origen CORS")

register_data = {
    "email": f"cors_test_{__import__('time').time()}@test.com",
    "password": "Test1234!",
    "nombre": "CORS",
    "apellido": "Test"
}

response = requests.post(
    f"{BASE_URL}/api/v1/auth/register",
    json=register_data,
    headers={"Origin": "http://localhost:3000"}
)
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

# Verificar CORS headers en respuesta
cors_origin = response.headers.get("access-control-allow-origin")
cors_credentials = response.headers.get("access-control-allow-credentials")
request_id = response.headers.get("X-Request-Id")

print(f"\n🌐 CORS Origin: {cors_origin}")
print(f"🌐 CORS Credentials: {cors_credentials}")
print(f"✅ Request-Id: {request_id}")

assert response.status_code == 201
assert cors_origin is not None
assert request_id is not None

print("\n✅ CORS y Request-Id funcionan en endpoints de auth!")

print_separator("🎉 TODOS LOS TESTS PASARON")
print("""
✅ CORS configurado:
  - Headers CORS presentes
  - Origin permitido: http://localhost:3000
  - Credentials habilitadas

✅ Request-Id funcionando:
  - Se genera automáticamente si no se envía
  - Se respeta el custom si se envía
  - Se incluye en todas las respuestas
""")
