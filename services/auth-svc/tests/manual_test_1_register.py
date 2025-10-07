"""
Test 1: Registrar un nuevo usuario
"""
import requests
import json

BASE_URL = "http://localhost:8002/api/v1/auth"
# BASE_URL = "http://localhost:8000/api/v1/auth"  # descomenta si usas otro puerto

# Usuario de prueba
user_data = {
    "baseUser": {
        "name": "Juan",
        "secondName": "Pérez",
        "email": "juan.perez@test.com",
        "documentType": "CI",
        "document": "12345678",
        "ubication": {
            "department": "Montevideo",
            "city": "Montevideo",
            "postalCode": "11000",
            "street": "Test Street",
            "number": "123",
            "apartment": "A"
        },
        "password": "TestPass123!"
    },
    "client": {
        "birthDate": "01/01/1990"
    }
}

print("="*80)
print("TEST 1: REGISTRO DE USUARIO")
print("="*80)
print(f"\nURL: {BASE_URL}/register")
print(f"\nDatos a enviar:")
print(json.dumps(user_data, indent=2))

try:
    response = requests.post(f"{BASE_URL}/register", json=user_data)
    
    print(f"\n{'='*80}")
    print(f"Status Code: {response.status_code}")
    print(f"{'='*80}")
    
    if response.status_code == 201:
        print("✅ ÉXITO: Usuario registrado correctamente")
        print(f"\nRespuesta:")
        print(json.dumps(response.json(), indent=2))
    elif response.status_code == 409:
        print("⚠️  ADVERTENCIA: El email ya está registrado")
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
