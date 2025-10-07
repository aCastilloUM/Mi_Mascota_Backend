"""
Script de prueba para los nuevos endpoints de auth-svc
Ejecutar después de aplicar la migración y configurar SMTP
"""
import requests  # type: ignore
import json

BASE_URL = "http://localhost:8006/api/v1/auth"

def print_response(title, response):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")

def test_register_with_verification():
    """Test 1: Registrar usuario (debería enviar email de verificación)"""
    payload = {
        "baseUser": {
            "name": "Test",
            "secondName": "User",
            "email": "test@example.com",
            "password": "Password123!"
        },
        "client": {
            "birthdate": "2000-01-01"
        }
    }
    
    response = requests.post(f"{BASE_URL}/register", json=payload)
    print_response("1. REGISTER (con email verification)", response)
    
    if response.status_code == 201:
        return response.json()
    return None

def test_resend_verification():
    """Test 2: Reenviar email de verificación"""
    payload = {
        "email": "test@example.com"
    }
    
    response = requests.post(f"{BASE_URL}/resend-verification", json=payload)
    print_response("2. RESEND VERIFICATION EMAIL", response)

def test_verify_email_invalid_token():
    """Test 3: Verificar con token inválido"""
    payload = {
        "token": "token-invalido-123"
    }
    
    response = requests.post(f"{BASE_URL}/verify-email", json=payload)
    print_response("3. VERIFY EMAIL (token inválido)", response)

def test_forgot_password():
    """Test 4: Solicitar reset de contraseña"""
    payload = {
        "email": "test@example.com"
    }
    
    response = requests.post(f"{BASE_URL}/forgot-password", json=payload)
    print_response("4. FORGOT PASSWORD", response)

def test_reset_password_invalid():
    """Test 5: Reset con token inválido"""
    payload = {
        "token": "token-invalido-reset",
        "new_password": "NewPassword123!"
    }
    
    response = requests.post(f"{BASE_URL}/reset-password", json=payload)
    print_response("5. RESET PASSWORD (token inválido)", response)

def test_change_password():
    """Test 6: Cambiar contraseña (requiere autenticación)"""
    payload = {
        "old_password": "Password123!",
        "new_password": "NewPassword456!"
    }
    
    # Nota: Este endpoint requiere X-User-ID header del Gateway
    # En producción, este header es inyectado por el Gateway después de validar JWT
    headers = {
        "X-User-ID": "some-user-id-here"  # Reemplazar con un user_id real
    }
    
    response = requests.post(f"{BASE_URL}/change-password", json=payload, headers=headers)
    print_response("6. CHANGE PASSWORD", response)

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║     TEST DE NUEVOS ENDPOINTS - AUTH-SVC                      ║
║                                                              ║
║  Asegurate de que:                                          ║
║  1. auth-svc está corriendo (puerto 8006)                   ║
║  2. La migración fue aplicada                               ║
║  3. (Opcional) SMTP configurado en .env                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Test 1: Registrar usuario
        test_register_with_verification()
        
        # Test 2: Reenviar verificación
        test_resend_verification()
        
        # Test 3: Verificar email con token inválido
        test_verify_email_invalid_token()
        
        # Test 4: Solicitar reset de contraseña
        test_forgot_password()
        
        # Test 5: Reset con token inválido
        test_reset_password_invalid()
        
        # Test 6: Cambiar contraseña
        test_change_password()
        
        print(f"\n{'='*50}")
        print("  ✅ TESTS COMPLETADOS")
        print(f"{'='*50}")
        print("\nNOTA: Para probar verify-email y reset-password con tokens reales:")
        print("1. Configura SMTP en .env (SMTP_USER y SMTP_PASSWORD)")
        print("2. Registra un usuario con tu email real")
        print("3. Copia el token del email recibido")
        print("4. Llama a /verify-email o /reset-password con ese token")
        print("\nSi no configuraste SMTP, los emails se loguean en consola (modo dev)")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: No se pudo conectar a auth-svc")
        print("Asegurate de que el servicio esté corriendo en http://localhost:8006")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    main()
