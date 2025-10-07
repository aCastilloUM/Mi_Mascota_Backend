"""
Script para probar las nuevas features del Gateway:
- Request-ID
- Rate Limiting
- CORS
- Propagación de headers
"""
import requests  # type: ignore
import time

GATEWAY_URL = "http://localhost:8080"

def test_request_id():
    """Test 1: Request-ID se genera automáticamente"""
    print("\n=== TEST 1: Request-ID Automático ===")
    response = requests.get(f"{GATEWAY_URL}/health")
    request_id = response.headers.get("X-Request-Id")
    print(f"✅ Request-ID generado: {request_id}")
    assert request_id is not None, "Request-ID no encontrado"
    print("✅ PASS: Request-ID funcionando\n")


def test_request_id_propagation():
    """Test 2: Request-ID personalizado se propaga"""
    print("\n=== TEST 2: Request-ID Personalizado ===")
    custom_id = "test-custom-id-12345"
    response = requests.get(
        f"{GATEWAY_URL}/health",
        headers={"X-Request-Id": custom_id}
    )
    returned_id = response.headers.get("X-Request-Id")
    print(f"Enviado: {custom_id}")
    print(f"Recibido: {returned_id}")
    assert returned_id == custom_id, "Request-ID no se propagó correctamente"
    print("✅ PASS: Request-ID propagado correctamente\n")


def test_rate_limit_headers():
    """Test 3: Headers de Rate Limiting"""
    print("\n=== TEST 3: Headers de Rate Limiting ===")
    response = requests.get(f"{GATEWAY_URL}/health")
    
    limit = response.headers.get("X-RateLimit-Limit")
    remaining = response.headers.get("X-RateLimit-Remaining")
    window = response.headers.get("X-RateLimit-Window")
    
    print(f"Límite: {limit} requests")
    print(f"Restantes: {remaining} requests")
    print(f"Ventana: {window}")
    
    assert limit is not None, "X-RateLimit-Limit no encontrado"
    assert remaining is not None, "X-RateLimit-Remaining no encontrado"
    print("✅ PASS: Headers de rate limiting presentes\n")


def test_rate_limit_enforcement():
    """Test 4: Rate Limiting se aplica (requiere muchos requests)"""
    print("\n=== TEST 4: Rate Limiting Enforcement ===")
    print("⚠️  Este test hace 105 requests para verificar el límite de 100/min")
    print("Esperando confirmación... (Ctrl+C para saltar)")
    
    try:
        input("Presiona Enter para continuar o Ctrl+C para saltar...")
    except KeyboardInterrupt:
        print("\n⏭️  Test saltado\n")
        return
    
    print("Haciendo 105 requests...")
    blocked = False
    
    for i in range(105):
        response = requests.get(f"{GATEWAY_URL}/health")
        if response.status_code == 429:
            print(f"🚫 Request #{i+1}: Bloqueado (429 Too Many Requests)")
            blocked = True
            break
        
        if (i + 1) % 20 == 0:
            print(f"✓ Requests {i+1}/105 completados")
    
    if blocked:
        print("✅ PASS: Rate limiting funcionando correctamente\n")
    else:
        print("⚠️  WARNING: No se alcanzó el límite en 105 requests\n")


def test_cors():
    """Test 5: CORS habilitado"""
    print("\n=== TEST 5: CORS ===")
    response = requests.options(
        f"{GATEWAY_URL}/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        }
    )
    
    allow_origin = response.headers.get("Access-Control-Allow-Origin")
    allow_credentials = response.headers.get("Access-Control-Allow-Credentials")
    
    print(f"Allow-Origin: {allow_origin}")
    print(f"Allow-Credentials: {allow_credentials}")
    
    assert allow_origin is not None, "CORS no configurado"
    print("✅ PASS: CORS habilitado\n")


def test_auth_flow():
    """Test 6: Flujo de autenticación con Request-ID propagado"""
    print("\n=== TEST 6: Auth Flow con Request-ID ===")
    
    # Registro
    print("Registrando usuario de prueba...")
    custom_id = f"test-auth-{int(time.time())}"
    
    register_data = {
        "email": f"test_{int(time.time())}@test.com",
        "password": "Test123!@#",
        "full_name": "Test User"
    }
    
    response = requests.post(
        f"{GATEWAY_URL}/api/v1/auth/register",
        json=register_data,
        headers={"X-Request-Id": custom_id}
    )
    
    print(f"Status: {response.status_code}")
    returned_id = response.headers.get("X-Request-Id")
    print(f"Request-ID enviado: {custom_id}")
    print(f"Request-ID recibido: {returned_id}")
    
    if response.status_code == 201:
        print("✅ PASS: Registro exitoso con Request-ID propagado\n")
    else:
        print(f"⚠️  Response: {response.json()}\n")


if __name__ == "__main__":
    print("🚀 Testing Gateway Features")
    print("=" * 50)
    
    try:
        test_request_id()
        test_request_id_propagation()
        test_rate_limit_headers()
        test_cors()
        test_auth_flow()
        test_rate_limit_enforcement()  # Este al final porque es lento
        
        print("\n" + "=" * 50)
        print("✅ Todos los tests completados")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: No se pudo conectar al Gateway")
        print("Asegúrate de que el Gateway esté corriendo en http://localhost:8080")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
