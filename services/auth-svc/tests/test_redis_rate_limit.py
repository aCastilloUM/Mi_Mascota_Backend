"""
Test manual del Redis rate limiting en auth-svc.
Envía múltiples requests de login fallidos para verificar:
1. Contador de intentos funciona
2. Bloqueo después de MAX_ATTEMPTS
3. Respuesta 429 con retry_after
"""
import requests
import json
import time

BASE = "http://localhost:8006/api/v1/auth"

def test_redis_rate_limit():
    print("\n=== TEST: Redis Rate Limiting ===\n")
    
    # Credenciales inválidas para forzar fallos
    payload = {
        "email": "test_limiter@example.com",
        "password": "WRONG_PASSWORD"
    }
    
    max_attempts = 5  # Según LOGIN_MAX_ATTEMPTS en .env
    
    print(f"📋 Configuración: MAX_ATTEMPTS={max_attempts}")
    print(f"📧 Email de prueba: {payload['email']}\n")
    
    # Intentar login múltiples veces con password incorrecta
    for i in range(1, max_attempts + 3):
        print(f"🔄 Intento {i}...")
        
        resp = requests.post(
            f"{BASE}/login",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   Status: {resp.status_code}")
        
        if resp.status_code == 401:
            print(f"   ❌ Credenciales inválidas (esperado para intento {i})")
        elif resp.status_code == 429:
            data = resp.json()
            retry_after = data.get("detail", {}).get("retry_after", "?")
            code = data.get("detail", {}).get("code", "?")
            message = data.get("detail", {}).get("message", "")
            
            print(f"   🚫 BLOQUEADO (429)")
            print(f"      Code: {code}")
            print(f"      Retry After: {retry_after} segundos")
            print(f"      Message: {message}")
            
            if i == max_attempts + 1:
                print(f"\n✅ Rate limiting funcionando correctamente!")
                print(f"   - Bloqueó después de {max_attempts} intentos fallidos")
                print(f"   - TTL del bloqueo: {retry_after}s")
            
            break
        else:
            print(f"   ⚠️ Status inesperado: {resp.status_code}")
            print(f"      Body: {resp.text[:200]}")
        
        time.sleep(0.2)  # Pequeña pausa entre requests
    
    print("\n=== FIN TEST ===\n")

if __name__ == "__main__":
    try:
        test_redis_rate_limit()
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: No se puede conectar a auth-svc en localhost:8006")
        print("   Asegurate de que el servicio esté corriendo")
    except Exception as e:
        print(f"❌ ERROR: {e}")
