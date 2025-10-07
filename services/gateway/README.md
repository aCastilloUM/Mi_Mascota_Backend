# API Gateway - Mi Mascota

Este servicio actúa como punto de entrada único para todas las peticiones del frontend.

## Funcionalidades

- **Autenticación centralizada**: Valida tokens JWT una sola vez
- **Enrutamiento**: Distribuye requests a los microservicios correspondientes
- **Headers de usuario**: Agrega información del usuario autenticado para los servicios internos
- **CORS**: Maneja CORS para el frontend
- **Rate limiting**: Protege contra abuso (opcional)

## Arquitectura

```
Frontend → Gateway (puerto 8080) → Microservicios
                ↓
         Valida JWT
                ↓
     Agrega X-User-ID, X-User-Email
                ↓
         Enruta al servicio
```

## Servicios Backend

- `auth-svc`: http://localhost:8002 - Autenticación
- `mascotas-svc`: http://localhost:8003 - Gestión de mascotas
- `veterinarios-svc`: http://localhost:8004 - Veterinarios
- `citas-svc`: http://localhost:8005 - Citas

## Ejecutar

```bash
cd services/gateway
python -m uvicorn app.main:app --reload --port 8080
```

## Variables de Entorno

Crear archivo `.env`:

```env
# Auth Service
AUTH_SERVICE_URL=http://localhost:8002
JWT_SECRET=change-me-in-dev
JWT_ISSUER=mimascota.auth
JWT_AUDIENCE=mimascota.front

# Otros servicios
MASCOTAS_SERVICE_URL=http://localhost:8003
VETERINARIOS_SERVICE_URL=http://localhost:8004
CITAS_SERVICE_URL=http://localhost:8005

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## Endpoints

### Públicos (sin autenticación)
- `POST /api/v1/auth/register` → auth-svc
- `POST /api/v1/auth/login` → auth-svc
- `POST /api/v1/auth/refresh` → auth-svc
- `GET /health` → Gateway health check

### Protegidos (requieren token)
- `GET /api/v1/auth/me` → auth-svc (con validación)
- `POST /api/v1/auth/logout` → auth-svc (con validación)
- `GET /api/v1/mascotas/*` → mascotas-svc
- `GET /api/v1/veterinarios/*` → veterinarios-svc
- `GET /api/v1/citas/*` → citas-svc
