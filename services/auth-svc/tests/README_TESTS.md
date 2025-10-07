# Tests Manuales - Refresh Token y Logout

## Descripción

Este conjunto de scripts te permite probar manualmente las funcionalidades de Refresh Token y Logout, similar a como lo harías con Postman.

## Requisitos Previos

1. **Servicio corriendo**: El servicio auth-svc debe estar corriendo en `http://localhost:8000`
   ```bash
   cd services/auth-svc
   python -m uvicorn app.main:app --reload --port 8000
   ```

2. **Base de datos**: PostgreSQL debe estar corriendo con las migraciones aplicadas

3. **Dependencias**: Instalar requests
   ```bash
   pip install requests
   ```

## Tests Disponibles

### 1. `manual_test_1_register.py` - Registro de Usuario
Registra un nuevo usuario en el sistema.

**Ejecutar:**
```bash
python tests/manual_test_1_register.py
```

**Qué hace:**
- Envía un POST a `/api/v1/auth/register`
- Crea un usuario con email `juan.perez@test.com`

---

### 2. `manual_test_2_login.py` - Login
Realiza login y guarda los tokens en `tokens.json`.

**Ejecutar:**
```bash
python tests/manual_test_2_login.py
```

**Qué hace:**
- Envía un POST a `/api/v1/auth/login`
- Guarda el access token y la refresh cookie en `tokens.json`
- **IMPORTANTE**: Ejecutar este test primero antes de los siguientes

---

### 3. `manual_test_3_me.py` - Acceso con Access Token
Verifica que el access token funciona correctamente.

**Ejecutar:**
```bash
python tests/manual_test_3_me.py
```

**Qué hace:**
- Lee el access token de `tokens.json`
- Envía un GET a `/api/v1/auth/me` con el token en el header
- Muestra los datos del usuario

---

### 4. `manual_test_4_refresh.py` - Refresh Token
Usa el refresh token para obtener un nuevo access token.

**Ejecutar:**
```bash
python tests/manual_test_4_refresh.py
```

**Qué hace:**
- Lee la refresh cookie de `tokens.json`
- Envía un POST a `/api/v1/auth/refresh`
- Verifica que los tokens rotan (cambian)
- Guarda los nuevos tokens en `tokens.json`

**Verificaciones:**
- ✅ El nuevo access token es diferente al anterior
- ✅ La nueva refresh cookie es diferente a la anterior

---

### 5. `manual_test_5_logout.py` - Logout
Revoca la sesión actual.

**Ejecutar:**
```bash
python tests/manual_test_5_logout.py
```

**Qué hace:**
- Lee la refresh cookie de `tokens.json`
- Envía un POST a `/api/v1/auth/logout`
- Verifica que la cookie se limpia
- Limpia `tokens.json`

---

### 6. `manual_test_6_refresh_after_logout.py` - Refresh después de Logout
Verifica que no se puede usar un refresh token después de hacer logout.

**Ejecutar:**
```bash
python tests/manual_test_6_refresh_after_logout.py
```

**Qué hace:**
- Intenta usar un refresh token de una sesión ya revocada
- Debe recibir un error 401

---

## Ejecutar Todos los Tests

Para ejecutar todos los tests en secuencia automáticamente:

```bash
python tests/run_all_manual_tests.py
```

## Flujo Recomendado

1. **Primera vez:**
   ```bash
   python tests/manual_test_1_register.py  # Registrar usuario
   python tests/manual_test_2_login.py     # Login
   python tests/manual_test_3_me.py        # Verificar token
   python tests/manual_test_4_refresh.py   # Probar refresh
   python tests/manual_test_5_logout.py    # Probar logout
   ```

2. **Para probar refresh después de logout:**
   ```bash
   python tests/manual_test_2_login.py     # Login nuevamente
   python tests/manual_test_5_logout.py    # Logout
   python tests/manual_test_6_refresh_after_logout.py  # Debe fallar
   ```

## Archivo tokens.json

Los tests 2, 3, 4 y 5 usan el archivo `tokens.json` para compartir datos entre ellos:

```json
{
  "access_token": "eyJ...",
  "refresh_cookie": "session_id.raw_token",
  "token_type": "bearer"
}
```

Este archivo simula cómo Postman guarda las variables de entorno.

## Notas

- Si el usuario ya existe (error 409 en test 1), es normal. Los otros tests funcionarán igual.
- El test 6 necesita que ejecutes el test 5 primero (para tener una sesión revocada)
- Los tokens expiran, si ves errores 401 inesperados, ejecuta `manual_test_2_login.py` nuevamente
