# API Gateway - Mi Mascota

Gateway HTTP (FastAPI) que actúa como punto de entrada único para el frontend.

## Funcionalidades

- **Autenticación centralizada**: valida el JWT una vez y propaga los claims.
- **Enrutamiento**: hoy expone `auth-svc` y `profiles-svc` bajo `/api/v1/*`.
- **Headers de usuario**: añade `X-User-ID` y `X-User-Email` para que los microservicios conozcan al usuario.
- **CORS** y **rate limiting** global.
- **Circuit breaker** y **cache** opcional usando Redis.

## Arquitectura

```
Frontend ─┬─> Gateway (puerto 8080) ──> auth-svc (8006)
          └─> Gateway (puerto 8080) ──> profiles-svc (8082)
```

## Variables de entorno mínimas

```env
# Servicios backend
AUTH_SERVICE_URL=http://localhost:8006
PROFILE_SERVICE_URL=http://localhost:8082

# JWT (debe coincidir con auth-svc)
JWT_SECRET=change-me-in-dev
JWT_ISSUER=mimascota-auth
JWT_AUDIENCE=mimascota-api

# Redis (rate limit + cache)
REDIS_URL=redis://localhost:6379/0
```

Revisá `.env.example` para el listado completo.

## Ejecutar localmente

```bash
cd services/gateway
python -m uvicorn app.main:app --reload --port 8080
```

En Docker se levanta junto con `auth-svc` y `profiles-svc` mediante `deploy/docker-compose.yml`.

## Rutas expuestas

- `POST /api/v1/auth/*` → auth-svc (registro, login, refresh, etc.). Las rutas públicas se gestionan antes del middleware de auth.
- `GET|POST|PUT|PATCH|DELETE /api/v1/profiles/*` → profiles-svc (requieren token válido).
- `GET /health` → health del gateway.
- `GET /metrics` → métricas Prometheus.
- `GET /circuit-breakers` → estado de los circuit breakers.
