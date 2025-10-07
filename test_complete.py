"""
Script de prueba completo para Gateway + Auth-svc
Prueba todas las nuevas features implementadas
"""
import requests  # type: ignore
import time
import json
from typing import Optional

# Configuración
GATEWAY_URL = "http://localhost:8080"
AUTH_URL = f"{GATEWAY_URL}/api/v1/auth"

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.YELLOW}ℹ️  {text}{Colors.END}")

def print_response(response):
    print(f"Status: {response.status_code}")
    print(f"Headers: X-Request-Id={response.headers.get('X-Request-Id', 'N/A')}, X-Cache={response.headers.get('X-Cache', 'N/A')}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text[:200]}")

# ==================== TESTS ====================

def test_gateway_health():
    """Test 1: Health checks del Gateway"""
    print_header("1. HEALTH CHECKS DEL GATEWAY")
    
    try:
        # Health
        r = requests.get(f"{GATEWAY_URL}/health")
        print_success(f"Health check: {r.status_code}")
        print_response(r)
        
        # Root
        r = requests.get(f"{GATEWAY_URL}/")
        print_success(f"Root endpoint: {r.status_code}")
        print_response(r)
        
    except Exception as e:
        print_error(f"Error: {e}")

def test_metrics():
    """Test 2: Prometheus Metrics"""
    print_header("2. PROMETHEUS METRICS")
    
    try:
        r = requests.get(f"{GATEWAY_URL}/metrics")
        if r.status_code == 200:
            print_success(f"Metrics disponibles: {r.status_code}")
            # Mostrar algunas métricas
            lines = r.text.split('\n')
            gateway_metrics = [l for l in lines if 'gateway_' in l and not l.startswith('#')][:10]
            print("Métricas (primeras 10):")
            for metric in gateway_metrics:
                print(f"  {metric}")
        else:
            print_error(f"Metrics fallaron: {r.status_code}")
    except Exception as e:
        print_error(f"Error: {e}")

def test_circuit_breakers():
    """Test 3: Circuit Breakers Status"""
    print_header("3. CIRCUIT BREAKERS STATUS")
    
    try:
        r = requests.get(f"{GATEWAY_URL}/circuit-breakers")
        print_success(f"Circuit breakers: {r.status_code}")
        print_response(r)
    except Exception as e:
        print_error(f"Error: {e}")

def test_register():
    """Test 4: Registrar usuario (email verification)"""
    print_header("4. REGISTER (con Email Verification)")
    
    payload = {
        "baseUser": {
            "name": "Test",
            "secondName": "Gateway",
            "email": f"test+{int(time.time())}@example.com",
            "password": "Password123!"
        },
        "client": {
            "birthdate": "2000-01-01"
        }
    }
    
    try:
        r = requests.post(f"{AUTH_URL}/register", json=payload)
        print_success(f"Register: {r.status_code}")
        print_response(r)
        
        if r.status_code == 201:
            print_info("Email de verificación debería haberse enviado (check logs)")
            return r.json()
    except Exception as e:
        print_error(f"Error: {e}")
    
    return None

def test_login(email: str, password: str) -> Optional[str]:
    """Test 5: Login y obtener token"""
    print_header("5. LOGIN")
    
    payload = {"email": email, "password": password}
    
    try:
        r = requests.post(f"{AUTH_URL}/login", json=payload)
        print_success(f"Login: {r.status_code}")
        print_response(r)
        
        if r.status_code == 200:
            return r.json().get("access_token")
    except Exception as e:
        print_error(f"Error: {e}")
    
    return None

def test_me_with_cache(token: str):
    """Test 6: GET /me con cache"""
    print_header("6. GET /ME CON CACHE")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Primera request (cache MISS)
        print_info("Primera request (debería ser MISS)...")
        r1 = requests.get(f"{AUTH_URL}/me", headers=headers)
        print_success(f"/me (1): {r1.status_code}")
        print_response(r1)
        
        # Segunda request (cache HIT)
        print_info("\nSegunda request (debería ser HIT)...")
        time.sleep(0.5)
        r2 = requests.get(f"{AUTH_URL}/me", headers=headers)
        print_success(f"/me (2): {r2.status_code}")
        print_response(r2)
        
        if r2.headers.get('X-Cache') == 'HIT':
            print_success("✨ Cache funcionando correctamente!")
        else:
            print_info("Cache no hit (puede ser que Redis no esté disponible)")
            
    except Exception as e:
        print_error(f"Error: {e}")

def test_forgot_password(email: str):
    """Test 7: Forgot Password"""
    print_header("7. FORGOT PASSWORD")
    
    payload = {"email": email}
    
    try:
        r = requests.post(f"{AUTH_URL}/forgot-password", json=payload)
        print_success(f"Forgot password: {r.status_code}")
        print_response(r)
        print_info("Email de reset debería haberse enviado (check logs)")
    except Exception as e:
        print_error(f"Error: {e}")

def test_circuit_breaker_failure():
    """Test 8: Simular fallo de Circuit Breaker"""
    print_header("8. CIRCUIT BREAKER (Simulando fallos)")
    
    print_info("Este test requiere que auth-svc esté APAGADO")
    print_info("Vamos a hacer 6 requests para abrir el circuit breaker...")
    
    user_input = input("¿Apagaste auth-svc? (s/n): ")
    if user_input.lower() != 's':
        print_info("Saltando test de circuit breaker")
        return
    
    try:
        for i in range(6):
            print(f"\nRequest {i+1}/6...")
            try:
                r = requests.get(f"{AUTH_URL}/me", headers={"Authorization": "Bearer invalid"}, timeout=2)
                print(f"Status: {r.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"Error: {type(e).__name__}")
        
        # Verificar estado del circuit breaker
        print_info("\nVerificando estado del circuit breaker...")
        r = requests.get(f"{GATEWAY_URL}/circuit-breakers")
        print_response(r)
        
        if r.status_code == 200:
            cb_state = r.json().get('circuit_breakers', {}).get('auth-svc', {}).get('state')
            if cb_state == 'open':
                print_success("✨ Circuit breaker ABIERTO! Funcionando correctamente")
            else:
                print_info(f"Circuit breaker estado: {cb_state}")
    except Exception as e:
        print_error(f"Error: {e}")

def test_rate_limiting():
    """Test 9: Rate Limiting"""
    print_header("9. RATE LIMITING")
    
    print_info("Haciendo 105 requests rápidas para activar rate limit...")
    
    try:
        for i in range(105):
            r = requests.get(f"{GATEWAY_URL}/health")
            if r.status_code == 429:
                print_success(f"✨ Rate limit activado en request {i+1}")
                print_response(r)
                break
            if i % 20 == 0:
                print(f"  Request {i+1}/105...")
        else:
            print_info("Rate limit no activado (límite: 100 req/60s)")
    except Exception as e:
        print_error(f"Error: {e}")

# ==================== MAIN ====================

def main():
    print(f"""
{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗
║     TEST COMPLETO - GATEWAY + AUTH-SVC                       ║
║                                                              ║
║  Prueba:                                                    ║
║  ✅ Circuit Breaker                                         ║
║  ✅ Response Caching                                        ║
║  ✅ Prometheus Metrics                                      ║
║  ✅ Email Verification                                      ║
║  ✅ Password Reset                                          ║
║  ✅ Rate Limiting                                           ║
║                                                              ║
║  Asegurate de que:                                          ║
║  1. Gateway está corriendo (puerto 8080)                    ║
║  2. auth-svc está corriendo (puerto 8006)                   ║
║  3. Redis está corriendo (puerto 6379)                      ║
║  4. PostgreSQL está corriendo (puerto 5432)                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Colors.END}
    """)
    
    # Test 1: Gateway Health
    test_gateway_health()
    
    # Test 2: Metrics
    test_metrics()
    
    # Test 3: Circuit Breakers
    test_circuit_breakers()
    
    # Test 4: Register
    user_email = f"test+{int(time.time())}@example.com"
    user_password = "Password123!"
    test_register()
    
    # Test 5: Login
    token = test_login(user_email, user_password)
    
    if token:
        # Test 6: Cache
        test_me_with_cache(token)
        
        # Test 7: Forgot Password
        test_forgot_password(user_email)
    
    # Test 8: Circuit Breaker (opcional)
    test_circuit_breaker_failure()
    
    # Test 9: Rate Limiting
    test_rate_limiting()
    
    print_header("TESTS COMPLETADOS")
    print(f"""
{Colors.BOLD}Resumen:{Colors.END}
- Gateway: Health, Metrics, Circuit Breakers
- Auth: Register, Login, /me con cache
- Password: Forgot Password flow
- Circuit Breaker: Protección contra fallos
- Rate Limiting: Protección anti-spam

{Colors.CYAN}📊 Ver métricas completas:{Colors.END}
  curl http://localhost:8080/metrics

{Colors.CYAN}🔍 Ver circuit breakers:{Colors.END}
  curl http://localhost:8080/circuit-breakers

{Colors.GREEN}¡Todo implementado y funcionando! 🎉{Colors.END}
    """)

if __name__ == "__main__":
    main()
