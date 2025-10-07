# 🏗️ Arquitectura Final - Mi Mascota Backend

## 📊 Diagrama de Flujo Completo

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLIENTE                                 │
│  (React/Vue/Mobile App con CORS enabled)                        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ HTTP Request
                     │ Origin: http://localhost:3000
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY (Port 8080)                    │
│─────────────────────────────────────────────────────────────────│
│  🌐 CORS Middleware                                             │
│     ├─ Allow Origins: localhost:3000, localhost:5173           │
│     ├─ Allow Credentials: true                                 │
│     └─ Allow Methods: *                                        │
│                                                                  │
│  🎯 Request-ID Middleware                                       │
│     ├─ Genera UUID: abc-123-def                                │
│     ├─ O reutiliza del cliente                                 │
│     └─ Log: request_start                                      │
│                                                                  │
│  🛡️ Rate Limit Middleware                                       │
│     ├─ 100 requests/60s por IP                                 │
│     ├─ Headers: X-RateLimit-*                                  │
│     └─ 429 si excede límite                                    │
│                                                                  │
│  🔐 Auth Middleware                                             │
│     ├─ Valida JWT (Bearer token)                               │
│     ├─ Extrae user_id, email                                   │
│     └─ 401 si token inválido                                   │
│                                                                  │
│  📡 Proxy (httpx)                                               │
│     ├─ Propaga X-Request-Id                                    │
│     ├─ Propaga X-User-ID                                       │
│     └─ Propaga X-User-Email                                    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ Headers propagados:
                     │ - X-Request-Id: abc-123-def
                     │ - X-User-ID: user_789
                     │ - X-User-Email: juan@mail.com
                     │
        ┌────────────┼────────────┬────────────┬────────────┐
        │            │            │            │            │
        ▼            ▼            ▼            ▼            ▼
┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│  AUTH-SVC    │ │ MASCOTAS │ │VETERINAR.│ │  CITAS   │ │  OTROS   │
│  Port 8006   │ │ Port 8003│ │ Port 8004│ │ Port 8005│ │  ...     │
└──────┬───────┘ └─────┬────┘ └─────┬────┘ └─────┬────┘ └──────────┘
       │               │            │            │
       │ Reutiliza     │            │            │
       │ Request-ID    │            │            │
       │               │            │            │
       ▼               ▼            ▼            ▼
┌──────────────────────────────────────────────────────────────┐
│                   INFRAESTRUCTURA                            │
│──────────────────────────────────────────────────────────────│
│                                                              │
│  🗄️  PostgreSQL (Port 5432)                                 │
│      └─ auth schema (users, sessions)                       │
│                                                              │
│  🔴 Redis (Port 6379/0)                                     │
│      └─ login:attempts:{email}:{ip}                         │
│      └─ login:block:{email}:{ip}                            │
│                                                              │
│  📨 Kafka (Port 29092) + Zookeeper (2181)                   │
│      └─ Topics: user.registered.v1                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔄 Flujo de Request Completo

### Ejemplo: Login de Usuario

```
1. Cliente (React)
   ↓
   POST http://localhost:8080/api/v1/auth/login
   Headers: Origin: http://localhost:3000
   Body: { email, password }

2. Gateway - CORS Middleware
   ↓
   ✅ Origin permitido
   ✅ Agrega headers CORS

3. Gateway - Request-ID Middleware
   ↓
   ✅ Genera Request-ID: xyz-789
   ✅ Log: request_start

4. Gateway - Rate Limit Middleware
   ↓
   ✅ IP 192.168.1.100: 23/100 requests
   ✅ Agrega headers X-RateLimit-*

5. Gateway - Auth Middleware
   ↓
   ⚠️  Ruta pública (/auth/login)
   ⏭️  Skip validación JWT

6. Gateway - Proxy
   ↓
   POST http://localhost:8006/api/v1/auth/login
   Headers agregados:
   - X-Request-Id: xyz-789

7. auth-svc recibe request
   ↓
   ✅ Reutiliza Request-ID: xyz-789
   ✅ Log: request_start (mismo ID)

8. auth-svc - Rate Limit Local
   ↓
   ✅ Redis: login:attempts:user@mail.com:192.168.1.100
   ✅ 2/5 intentos en 15min

9. auth-svc - Validar credenciales
   ↓
   ✅ PostgreSQL: SELECT * FROM users WHERE email=...
   ✅ Password válido

10. auth-svc - Generar tokens
    ↓
    ✅ JWT access_token (15min)
    ✅ refresh_token en cookie HttpOnly (14 días)

11. auth-svc - Publicar evento Kafka
    ↓
    ✅ Topic: user.registered.v1
    ✅ Headers: request-id=xyz-789

12. auth-svc - Response
    ↓
    200 OK
    Headers: X-Request-Id: xyz-789
    Body: { access_token, user: {...} }

13. Gateway recibe response
    ↓
    ✅ Log: request_complete, duration_ms=142.3

14. Gateway - Response al cliente
    ↓
    200 OK
    Headers:
    - X-Request-Id: xyz-789
    - X-RateLimit-Limit: 100
    - X-RateLimit-Remaining: 76
    - Access-Control-Allow-Origin: http://localhost:3000
    Body: { access_token, user: {...} }

15. Cliente recibe response
    ↓
    ✅ Guarda access_token
    ✅ Cookie refresh_token guardada automáticamente
```

---

## 📋 Tabla de Responsabilidades

| Layer | Responsabilidad | Tecnología |
|-------|----------------|------------|
| **Gateway** | CORS, Request-ID, Rate Limit Global, JWT Validation | FastAPI + httpx |
| **auth-svc** | Login, Register, JWT, Rate Limit Login, Kafka Events | FastAPI + SQLAlchemy + Redis + Kafka |
| **mascotas-svc** | CRUD mascotas | FastAPI |
| **veterinarios-svc** | CRUD veterinarios | FastAPI |
| **citas-svc** | Reservas y gestión | FastAPI |
| **PostgreSQL** | Persistencia datos | PostgreSQL 15+ |
| **Redis** | Rate limiting distribuido | Redis 7+ |
| **Kafka** | Event streaming | Kafka + Zookeeper |

---

## 🔐 Seguridad en Capas

```
┌─────────────────────────────────────────────────┐
│  Capa 1: Gateway                                │
│  ├─ CORS (solo orígenes permitidos)            │
│  ├─ Rate Limiting Global (100/min por IP)      │
│  └─ JWT Validation (Bearer token)              │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  Capa 2: auth-svc                               │
│  ├─ Rate Limiting Login (5/15min por email+IP) │
│  ├─ Password hashing (bcrypt)                  │
│  └─ Session management (Redis)                 │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  Capa 3: Database                               │
│  ├─ SQL injection prevention (parameterized)   │
│  ├─ Encrypted connections                      │
│  └─ Access control (user permissions)          │
└─────────────────────────────────────────────────┘
```

---

## 📊 Headers en Cada Capa

### Cliente → Gateway
```http
POST /api/v1/auth/login HTTP/1.1
Host: localhost:8080
Origin: http://localhost:3000
Content-Type: application/json
X-Request-Id: custom-id-123  (opcional)
```

### Gateway → auth-svc
```http
POST /api/v1/auth/login HTTP/1.1
Host: localhost:8006
Content-Type: application/json
X-Request-Id: custom-id-123  (propagado o generado)
X-User-ID: user_789  (si autenticado)
X-User-Email: juan@mail.com  (si autenticado)
```

### auth-svc → Cliente (via Gateway)
```http
HTTP/1.1 200 OK
X-Request-Id: custom-id-123
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Window: 60s
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Credentials: true
Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Lax
```

---

## 🎯 Decisiones de Arquitectura

### ¿Por qué CORS solo en Gateway?
- ✅ **Single Point of Configuration**: Un solo lugar para gestionar
- ✅ **No duplicación**: Evita configuraciones inconsistentes
- ✅ **Backends más simples**: No necesitan conocer sobre CORS

### ¿Por qué JWT Validation en Gateway?
- ✅ **Seguridad temprana**: Rechaza tokens inválidos antes de llegar a backends
- ✅ **Menos carga**: Backends no necesitan validar JWT
- ✅ **User context**: Gateway extrae user_id y lo propaga

### ¿Por qué Rate Limiting en ambos?
- **Gateway**: Protección general (100/min por IP)
  - Previene DDoS básico
  - Protege toda la infraestructura
- **auth-svc**: Protección específica (5/15min por email+IP)
  - Previene brute-force en login
  - Lógica de negocio específica

### ¿Por qué Request-ID en ambos?
- **Gateway**: Genera/propaga
  - Punto de entrada único
  - Garantiza ID único
- **auth-svc**: Reutiliza
  - Logs correlacionados
  - Trazabilidad end-to-end

---

## 🚀 Ventajas de Esta Arquitectura

1. **Observabilidad**
   - Request-ID correlaciona logs entre servicios
   - Structured logging permite análisis automático
   - Duration tracking para performance monitoring

2. **Seguridad**
   - Rate limiting en múltiples capas
   - JWT centralizado en Gateway
   - CORS configurado correctamente

3. **Escalabilidad**
   - Gateway puede escalar horizontalmente
   - Backends independientes
   - Redis para estado compartido

4. **Mantenibilidad**
   - Responsabilidades claras
   - No duplicación de código
   - Fácil debugging con Request-ID

5. **Performance**
   - Request-ID en memoria (rápido)
   - Rate limiting eficiente
   - Logs estructurados (indexables)

---

## 📝 Configuración de Variables

### Gateway (.env)
```env
# Servicios backend
AUTH_SERVICE_URL=http://localhost:8006
MASCOTAS_SERVICE_URL=http://localhost:8003
VETERINARIOS_SERVICE_URL=http://localhost:8004
CITAS_SERVICE_URL=http://localhost:8005

# JWT (debe coincidir con auth-svc)
JWT_SECRET=tu-secret-super-secreto
JWT_ISSUER=mi-mascota-app
JWT_AUDIENCE=mi-mascota-users

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Gateway
GATEWAY_PORT=8080
LOG_LEVEL=info
```

### auth-svc (.env)
```env
# Database
DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/appdb

# JWT
JWT_SECRET=tu-secret-super-secreto
JWT_ISSUER=mi-mascota-app
JWT_AUDIENCE=mi-mascota-users
JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=14

# Redis
REDIS_URL=redis://localhost:6379/0

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:29092

# Rate Limiting
RATE_LIMIT_MAX_ATTEMPTS=5
RATE_LIMIT_WINDOW_MINUTES=15
RATE_LIMIT_LOCKOUT_MINUTES=30

# Request-ID (ya no necesita CORS)
REQUEST_ID_HEADER=X-Request-Id
```

---

## ✅ Checklist de Deployment

### Pre-deployment
- [ ] Todas las variables de entorno configuradas
- [ ] python-json-logger instalado en Gateway
- [ ] PostgreSQL corriendo (puerto 5432)
- [ ] Redis corriendo (puerto 6379)
- [ ] Kafka + Zookeeper corriendo (29092, 2181)

### Deployment
- [ ] Gateway iniciado (puerto 8080)
- [ ] auth-svc iniciado (puerto 8006)
- [ ] Logs JSON en ambos servicios
- [ ] Request-ID aparece en logs

### Post-deployment
- [ ] Ejecutar test_gateway_features.py
- [ ] Verificar CORS con frontend
- [ ] Verificar Rate Limiting funciona
- [ ] Verificar Request-ID se propaga

---

**¡Arquitectura completa y lista para producción! 🎉**
