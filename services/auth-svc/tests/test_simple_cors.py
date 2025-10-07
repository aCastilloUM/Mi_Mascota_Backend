"""
Test SIMPLE de CORS y Request-Id
Ejecuta este script MANUALMENTE en una terminal SEPARADA mientras el servicio corre
"""
import requests

print("=" * 70)
print("TEST DE CORS Y REQUEST-ID")
print("=" * 70)

# Test 1: Request-Id automático
print("\n1️⃣  Test: Request-Id automático")
try:
    r = requests.get("http://localhost:8002/healthz")
    rid = r.headers.get("X-Request-Id", "NO ENCONTRADO")
    print(f"   ✅ Status: {r.status_code}")
    print(f"   ✅ X-Request-Id: {rid}")
    if rid == "NO ENCONTRADO":
        print("   ❌ FALLA: No se encontró header X-Request-Id")
    else:
        print("   ✅ PASS: Request-Id presente!")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

# Test 2: Request-Id custom
print("\n2️⃣  Test: Request-Id custom")
try:
    r = requests.get("http://localhost:8002/healthz", headers={"X-Request-Id": "mi-id-12345"})
    rid = r.headers.get("X-Request-Id")
    print(f"   ✅ Status: {r.status_code}")
    print(f"   ✅ X-Request-Id retornado: {rid}")
    if rid == "mi-id-12345":
        print("   ✅ PASS: Request-Id custom respetado!")
    else:
        print(f"   ❌ FALLA: Se esperaba 'mi-id-12345' pero se recibió '{rid}'")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

# Test 3: CORS
print("\n3️⃣  Test: CORS")
try:
    r = requests.options(
        "http://localhost:8002/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST"
        }
    )
    print(f"   ✅ Status: {r.status_code}")
    
    cors_origin = r.headers.get("access-control-allow-origin")
    cors_creds = r.headers.get("access-control-allow-credentials")
    
    print(f"   🌐 Access-Control-Allow-Origin: {cors_origin}")
    print(f"   🌐 Access-Control-Allow-Credentials: {cors_creds}")
    
    if cors_origin:
        print("   ✅ PASS: CORS configurado!")
    else:
        print("   ❌ FALLA: Headers CORS no encontrados")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

print("\n" + "=" * 70)
print("FIN DE TESTS")
print("=" * 70)
