# 🔐 Decisión de Arquitectura: Validación de JWT

## ❓ Pregunta Original

> "¿Auth o Gateway validan el JWT? Es mejor que lo valide auth para aislar, ¿te parece bien?"

## 📊 Análisis de Opciones

### Opción A: Gateway valida JWT (IMPLEMENTACIÓN ACTUAL) ✅

```
┌─────────┐     ┌──────────────────────┐     ┌──────────┐
│ Cliente │────▶│ Gateway              │────▶│ auth-svc │
└─────────┘     │ - Valida JWT         │     │ - Confía │
  Bearer        │ - Extrae user_id     │     │   en     │
  token         │ - Agrega X-User-ID   │     │   headers│
                └──────────────────────┘     └──────────┘
```

**Ventajas:**
- ✅ **Seguridad centralizada**: Un solo punto de validación
- ✅ **Backends simplificados**: No necesitan validar JWT
- ✅ **Mejor performance**: Validas una vez, no en cada servicio
- ✅ **Menos duplicación**: Lógica de JWT en un solo lugar
- ✅ **Headers estandarizados**: Gateway inyecta X-User-ID, X-User-Email
- ✅ **Patrón estándar**: Usado por Netflix, Amazon, Google, Uber

**Desventajas:**
- ⚠️ Gateway necesita el JWT_SECRET
- ⚠️ Si Gateway se compromete, todos los servicios están expuestos

---

### Opción B: Cada servicio valida JWT (PROPUESTA)

```
┌─────────┐     ┌──────────────────────┐     ┌──────────────────┐
│ Cliente │────▶│ Gateway              │────▶│ auth-svc         │
└─────────┘     │ - Solo proxy         │     │ - Valida JWT     │
  Bearer        │ - No valida          │     │ - Extrae user_id │
  token         └──────────────────────┘     └──────────────────┘
```

**Ventajas:**
- ✅ **Mayor aislamiento**: JWT_SECRET solo en auth-svc
- ✅ **Menor riesgo**: Si Gateway se compromete, secrets están seguros

**Desventajas:**
- ❌ **Cada backend debe validar**: Duplicación de código
- ❌ **Más carga**: Todos los servicios validan el mismo token
- ❌ **Más complejo**: Cada servicio necesita JWT library
- ❌ **Inconsistencias**: Cada servicio puede implementarlo diferente
- ❌ **Más lento**: N validaciones en lugar de 1

---

## ✅ Decisión Final: OPCIÓN A (Gateway valida)

### Razones:

1. **Arquitectura de Microservicios con API Gateway**
   - El Gateway es el "Edge Service"
   - Su responsabilidad es autenticación/autorización
   - Backends son "internos" y confían en el Gateway

2. **Performance**
   ```
   Con Gateway:  1 validación JWT → N servicios
   Sin Gateway:  N validaciones JWT → N servicios
   ```

3. **Separación de Responsabilidades**
   - **Gateway**: Autenticación (¿quién eres?)
   - **auth-svc**: Autorización y gestión de usuarios (¿qué puedes hacer?)
   - **Otros servicios**: Lógica de negocio

4. **Escalabilidad**
   - Si agregas 10 servicios nuevos, no necesitas duplicar validación JWT
   - Solo agregas rutas en el Gateway

5. **Seguridad en Profundidad**
   - Aunque Gateway valida, puedes agregar validaciones adicionales en servicios críticos
   - No es "todo o nada"

---

## 🛡️ Mitigación de Riesgos

### "Pero si comprometen el Gateway..."

**Solución: Seguridad en Capas**

```
┌─────────────────────────────────────────┐
│ Capa 1: Network (VPC, Firewall)        │ ← Gateway y backends en red privada
├─────────────────────────────────────────┤
│ Capa 2: Gateway (JWT Validation)       │ ← Valida tokens
├─────────────────────────────────────────┤
│ Capa 3: Service Mesh (mTLS)            │ ← Comunicación cifrada entre servicios
├─────────────────────────────────────────┤
│ Capa 4: Backends (Authorization)       │ ← Verifican permisos específicos
└─────────────────────────────────────────┘
```

**Medidas adicionales:**
1. **Secrets Management**: Usar Vault, AWS Secrets Manager
2. **mTLS**: Certificados entre Gateway y backends
3. **Network Isolation**: Backends no expuestos a internet
4. **Authorization en backends**: Aunque Gateway valida identidad, backends validan permisos

---

## 🏗️ Arquitectura Recomendada (Actual)

```
┌──────────────────────────────────────────────────────┐
│                     CLIENTE                          │
│  (React/Vue/Mobile App)                              │
└───────────────────┬──────────────────────────────────┘
                    │
                    │ Authorization: Bearer <JWT>
                    │
                    ▼
┌──────────────────────────────────────────────────────┐
│                  API GATEWAY (Port 8080)             │
│──────────────────────────────────────────────────────│
│  1. CORS Middleware                                  │
│  2. Request-ID Middleware                            │
│  3. Rate Limiting Global (100/min por IP)            │
│  4. ✅ JWT VALIDATION ← AQUÍ                         │
│     - Valida signature                               │
│     - Verifica expiration                            │
│     - Extrae user_id, email                          │
│  5. Proxy Request                                    │
│     - Inyecta X-User-ID                              │
│     - Inyecta X-User-Email                           │
│     - Inyecta X-Request-Id                           │
└───────────────────┬──────────────────────────────────┘
                    │
                    │ Headers:
                    │ - X-User-ID: user_123
                    │ - X-User-Email: juan@mail.com
                    │ - X-Request-Id: abc-456
                    │
                    ▼
┌──────────────────────────────────────────────────────┐
│                auth-svc (Port 8006)                  │
│──────────────────────────────────────────────────────│
│  ✅ Confía en X-User-ID del Gateway                  │
│  - No necesita validar JWT                           │
│  - Usa X-User-ID directamente                        │
│  - Lógica de negocio de autenticación                │
│  - Rate limiting específico (login)                  │
└──────────────────────────────────────────────────────┘
```

---

## 📝 Configuración Actual

### Gateway (.env)
```env
# JWT (necesario para validación)
JWT_SECRET=change-me-in-dev
JWT_ISSUER=mimascota.auth
JWT_AUDIENCE=mimascota.front
```

### auth-svc (.env)
```env
# JWT (necesario para GENERACIÓN)
JWT_SECRET=change-me-in-dev  # ← Mismo secret
JWT_ISSUER=mimascota.auth
JWT_AUDIENCE=mimascota.front
JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=14
```

**⚠️ IMPORTANTE**: JWT_SECRET debe ser el MISMO en ambos.

---

## 🔄 Flujo Completo de Autenticación

### 1. Login
```
Cliente → Gateway → auth-svc
                    ↓
                    Valida credenciales
                    Genera JWT
                    ←
Gateway ← JWT ← auth-svc
↓
Cliente ← JWT
```

### 2. Request Autenticado
```
Cliente → Gateway (valida JWT) → auth-svc (confía en headers)
          ↓
          Extrae user_id
          Inyecta X-User-ID
                    ↓
                    Usa X-User-ID
```

---

## 🎯 Conclusión

**Mantén la validación de JWT en el Gateway.**

Es el patrón correcto para una arquitectura de microservicios con API Gateway.

Si quieres más seguridad, agrega:
1. **mTLS** entre Gateway y backends
2. **Network isolation** (VPC)
3. **Authorization checks** en backends críticos

Pero NO muevas la validación JWT a cada servicio.

---

## 📚 Referencias

- [Netflix API Gateway](https://netflixtechblog.com/optimizing-the-netflix-api-5c9ac715cf19)
- [AWS API Gateway Authorization](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-control-access-to-api.html)
- [Kong Gateway Authentication](https://docs.konghq.com/gateway/latest/get-started/authentication/)
- [Nginx API Gateway](https://www.nginx.com/blog/building-microservices-using-an-api-gateway/)

---

**Decisión tomada**: ✅ Gateway valida JWT (Opción A)
**Fecha**: 6 de octubre de 2025
**Razón**: Arquitectura estándar, mejor performance, menos duplicación
