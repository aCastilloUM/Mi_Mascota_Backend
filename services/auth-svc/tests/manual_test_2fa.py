# services/auth-svc/tests/manual_test_2fa.py
"""
Test manual completo del flujo 2FA TOTP.

Flujo:
1. Register usuario
2. Login (obtener tokens)
3. Enable 2FA (obtener QR code y backup codes)
4. Verify setup 2FA (confirmar con código)
5. Logout
6. Login con 2FA (requiere código)
7. Validate 2FA (completar login)
8. Verificar status 2FA
9. Regenerar backup codes
10. Login con backup code
11. Disable 2FA
"""
import requests  # type: ignore
import time
import pyotp  # type: ignore
from datetime import datetime

BASE_URL = "http://localhost:8080"

def generate_test_email():
    """Genera email único para testing"""
    timestamp = int(time.time())
    return f"test2fa_{timestamp}@example.com"

def print_step(step_num, description):
    print(f"\n{'='*60}")
    print(f"PASO {step_num}: {description}")
    print(f"{'='*60}")

def main():
    email = generate_test_email()
    password = "Test123!@#"
    
    print(f"\n🔐 Test 2FA TOTP - {datetime.now()}")
    print(f"Email: {email}")
    
    # Paso 1: Register
    print_step(1, "Register usuario nuevo")
    register_data = {
        "baseUser": {
            "name": "Test",
            "secondName": "2FA",
            "email": email,
            "documentType": "CI",
            "document": "12345678",
            "ubication": {
                "department": "Montevideo",
                "city": "Montevideo",
                "postalCode": "11200",
                "street": "Test St",
                "number": "123"
            },
            "password": password
        },
        "client": {
            "birthDate": "01/01/1990"
        }
    }
    
    resp = requests.post(f"{BASE_URL}/api/v1/auth/register", json=register_data)
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 201, f"Register falló: {resp.text}"
    user_data = resp.json()
    print(f"✅ Usuario creado: {user_data['id']}")
    
    # Paso 2: Login inicial (sin 2FA todavía)
    print_step(2, "Login inicial (sin 2FA)")
    login_data = {"email": email, "password": password}
    resp = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"Login falló: {resp.text}"
    
    # Verificar si es respuesta con 2FA o tokens directos
    data = resp.json()
    if "requires_2fa" in data:
        print(f"⚠️ 2FA ya habilitado (unexpected)")
        return
    
    access_token = data["access_token"]
    print(f"✅ Login exitoso (sin 2FA)")
    
    # Paso 3: Enable 2FA
    print_step(3, "Enable 2FA - Obtener QR code y backup codes")
    headers = {"X-User-Id": user_data["id"]}
    resp = requests.post(f"{BASE_URL}/api/v1/auth/2fa/enable", headers=headers)
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"Enable 2FA falló: {resp.text}"
    
    enable_data = resp.json()
    secret = enable_data["secret"]
    qr_code = enable_data["qr_code"]
    backup_codes = enable_data["backup_codes"]
    
    print(f"✅ 2FA iniciado")
    print(f"Secret: {secret}")
    print(f"QR Code (primeros 50 chars): {qr_code[:50]}...")
    print(f"Backup Codes (10): {backup_codes}")
    
    # Paso 4: Verify setup con código TOTP
    print_step(4, "Verify setup - Confirmar con código TOTP")
    
    # Generar código TOTP con pyotp
    totp = pyotp.TOTP(secret)
    code = totp.now()
    print(f"Código TOTP generado: {code}")
    
    verify_data = {"secret": secret, "token": code}
    resp = requests.post(f"{BASE_URL}/api/v1/auth/2fa/verify-setup", json=verify_data, headers=headers)
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"Verify setup falló: {resp.text}"
    
    verify_response = resp.json()
    print(f"✅ 2FA habilitado exitosamente")
    print(f"Backup codes finales (10): {verify_response['backup_codes']}")
    backup_codes_final = verify_response["backup_codes"]
    
    # Paso 5: Logout
    print_step(5, "Logout")
    resp = requests.post(f"{BASE_URL}/api/v1/auth/logout")
    print(f"Status: {resp.status_code}")
    print(f"✅ Logout exitoso")
    
    # Paso 6: Login con 2FA habilitado
    print_step(6, "Login con 2FA habilitado")
    resp = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"Login falló: {resp.text}"
    
    login_response = resp.json()
    if "requires_2fa" not in login_response:
        print(f"❌ ERROR: Se esperaba requires_2fa=True")
        print(f"Response: {login_response}")
        return
    
    assert login_response["requires_2fa"] == True, "Se esperaba requires_2fa=True"
    temp_session_id = login_response["temp_session_id"]
    print(f"✅ Login requiere 2FA")
    print(f"Temp Session ID: {temp_session_id}")
    
    # Paso 7: Validate 2FA con código TOTP
    print_step(7, "Validate 2FA - Completar login con código TOTP")
    
    # Generar nuevo código (puede haber cambiado en 30s)
    time.sleep(1)  # Esperar un poco
    code = totp.now()
    print(f"Código TOTP generado: {code}")
    
    validate_data = {"temp_session_id": temp_session_id, "token": code}
    resp = requests.post(f"{BASE_URL}/api/v1/auth/login/2fa", json=validate_data)
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"Validate 2FA falló: {resp.text}"
    
    validate_response = resp.json()
    access_token = validate_response["access_token"]
    print(f"✅ Login con 2FA completado")
    print(f"Access token obtenido")
    
    # Paso 8: Verificar status 2FA
    print_step(8, "Verificar status 2FA")
    resp = requests.get(f"{BASE_URL}/api/v1/auth/2fa/status", headers=headers)
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"Status falló: {resp.text}"
    
    status_data = resp.json()
    print(f"✅ Status 2FA:")
    print(f"   - Habilitado: {status_data['two_factor_enabled']}")
    print(f"   - Fecha activación: {status_data['two_factor_enabled_at']}")
    print(f"   - Backup codes restantes: {status_data['backup_codes_remaining']}")
    
    assert status_data["backup_codes_remaining"] == 10, "Deberían ser 10 códigos"
    
    # Paso 9: Regenerar backup codes
    print_step(9, "Regenerar backup codes")
    code = totp.now()
    regenerate_data = {"password": password, "token": code}
    resp = requests.post(
        f"{BASE_URL}/api/v1/auth/2fa/regenerate-backup-codes",
        json=regenerate_data,
        headers=headers
    )
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"Regenerate falló: {resp.text}"
    
    regen_data = resp.json()
    new_backup_codes = regen_data["backup_codes"]
    print(f"✅ Backup codes regenerados (10 nuevos): {new_backup_codes}")
    
    # Paso 10: Login con backup code
    print_step(10, "Login con backup code")
    
    # Logout primero
    requests.post(f"{BASE_URL}/api/v1/auth/logout")
    
    # Login
    resp = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
    login_response = resp.json()
    temp_session_id = login_response["temp_session_id"]
    
    # Usar primer backup code
    backup_code = new_backup_codes[0]
    print(f"Usando backup code: {backup_code}")
    
    validate_data = {"temp_session_id": temp_session_id, "token": backup_code}
    resp = requests.post(f"{BASE_URL}/api/v1/auth/login/2fa", json=validate_data)
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"Login con backup code falló: {resp.text}"
    
    backup_response = resp.json()
    print(f"✅ Login con backup code exitoso")
    print(f"   - backup_code_used: {backup_response.get('backup_code_used')}")
    print(f"   - backup_codes_remaining: {backup_response.get('backup_codes_remaining')}")
    
    assert backup_response["backup_code_used"] == True, "Debería indicar que se usó backup code"
    assert backup_response["backup_codes_remaining"] == 9, "Deberían quedar 9 códigos"
    
    # Paso 11: Disable 2FA
    print_step(11, "Disable 2FA")
    code = totp.now()
    disable_data = {"password": password, "token": code}
    resp = requests.post(
        f"{BASE_URL}/api/v1/auth/2fa/disable",
        json=disable_data,
        headers=headers
    )
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"Disable falló: {resp.text}"
    
    disable_response = resp.json()
    print(f"✅ 2FA deshabilitado")
    print(f"   - two_factor_enabled: {disable_response['two_factor_enabled']}")
    
    # Verificar que ya no requiere 2FA
    print_step(12, "Verificar login sin 2FA después de deshabilitar")
    requests.post(f"{BASE_URL}/api/v1/auth/logout")
    
    resp = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
    login_response = resp.json()
    
    if "requires_2fa" in login_response:
        print(f"❌ ERROR: No debería requerir 2FA después de deshabilitar")
        return
    
    assert "access_token" in login_response, "Debería retornar access_token"
    print(f"✅ Login sin 2FA exitoso")
    
    print(f"\n{'='*60}")
    print("🎉 TODOS LOS TESTS DE 2FA PASARON EXITOSAMENTE")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"\n❌ Test falló: {e}")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
