# 🎉 Kafka Implementado - Evento user_registered

## ✅ Implementación Completa

### Archivos Creados/Modificados:

**Nuevos:**
- ✅ `app/events/kafka.py` - Productor Kafka async con AIOKafka
- ✅ `tests/test_kafka_event.py` - Test de evento user_registered

**Modificados:**
- ✅ `app/main.py` - Lifecycle hooks para start/stop de Kafka producer
- ✅ `app/api/v1/auth.py` - Emite evento al registrar usuario
- ✅ `app/core/config.py` - Variables de configuración Kafka
- ✅ `.env` - Variables KAFKA_BOOTSTRAP_SERVERS y USER_REGISTERED_TOPIC
- ✅ `requirements.txt` - Agregado `aiokafka>=0.10.0`
- ✅ `deploy/docker-compose.yml` - Kafka con listeners para host y docker

---

## 🔧 Configuración

### Variables de Entorno (.env):
```env
# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:29092
USER_REGISTERED_TOPIC=user.registered.v1
```

### Docker Compose:
Kafka expone DOS listeners:
- **`kafka:9092`** - Para contenedores dentro de Docker
- **`localhost:29092`** - Para tu host (uvicorn corriendo fuera de Docker)

---

## 📨 Evento user_registered

### Estructura del Evento:
```json
{
  "event": "user_registered",
  "id": "uuid-del-evento",
  "ts": 1696599999999,
  "v": 1,
  "payload": {
    "user_id": "uuid-del-usuario",
    "email": "usuario@example.com",
    "full_name": "Nombre Completo"
  },
  "source": "auth-svc"
}
```

### Headers del Mensaje:
- `event-type`: `user_registered`
- `event-id`: UUID único del evento
- `content-type`: `application/json`
- `request-id`: El mismo request-id del middleware (trazabilidad)

### Topic:
- **Nombre**: `user.registered.v1`
- **Key**: `user_id` (para particionamiento por usuario)

---

## 🔄 Flujo Completo

```
1. POST /api/v1/auth/register
   ↓
2. AuthService.register() crea usuario en DB
   ↓
3. Commit exitoso
   ↓
4. Se emite evento a Kafka (bus.publish)
   ↓
5. Kafka persiste el evento en topic user.registered.v1
   ↓
6. Response 201 al cliente
```

---

## 🧪 Testing

### Opción 1: Test Automático
```bash
cd services/auth-svc/tests
python test_kafka_event.py
```

### Opción 2: Test Manual con curl
```bash
# Registrar usuario
curl -X POST http://localhost:8006/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "baseUser": {
      "email": "test@example.com",
      "password": "Test1234!",
      "name": "Test",
      "secondName": "User"
    },
    "client": {
      "birthdate": "1990-01-01"
    }
  }'
```

### Opción 3: Consumir eventos desde Kafka

**Desde Docker (dentro del contenedor Kafka):**
```bash
docker exec -it backend-kafka bash
kafka-console-consumer --bootstrap-server localhost:9092 \
    --topic user.registered.v1 --from-beginning
```

**Desde tu host (si tenés Kafka CLI instalado):**
```bash
kafka-console-consumer --bootstrap-server localhost:29092 \
    --topic user.registered.v1 --from-beginning
```

**Con kafkacat:**
```bash
kafkacat -b localhost:29092 -t user.registered.v1 -C
```

---

## 🎯 Logs Estructurados

Al iniciar el servicio verás:
```json
{
  "levelname": "INFO",
  "name": "auth-svc",
  "message": "service_start",
  "db": "postgresql+asyncpg://..."
}

{
  "levelname": "INFO",
  "name": "app.events.kafka",
  "message": "kafka_producer_started",
  "bootstrap": "localhost:29092"
}
```

Al registrar un usuario:
```json
{
  "levelname": "INFO",
  "name": "auth-svc",
  "message": "access",
  "method": "POST",
  "path": "/api/v1/auth/register",
  "status": 201,
  "duration_ms": 234,
  "request_id": "uuid...",
  "client_ip": "127.0.0.1"
}
```

---

## 🚀 Arquitectura Event-Driven

```
                  ┌─────────────┐
                  │  Frontend   │
                  └──────┬──────┘
                         │
                         ↓
                  ┌──────────────┐
                  │  API Gateway │ (puerto 8080)
                  └──────┬───────┘
                         │
                         ↓
                  ┌──────────────┐
                  │  Auth Service│ (puerto 8006)
                  │              │
                  │ - Register   │
                  │ - Login      │
                  │ - Refresh    │
                  └──┬───────┬───┘
                     │       │
         ┌───────────┘       └───────────┐
         ↓                                ↓
  ┌──────────────┐              ┌────────────────┐
  │  PostgreSQL  │              │     Kafka      │
  │              │              │                │
  │  - Users     │              │ Topic:         │
  │  - Sessions  │              │ user.          │
  └──────────────┘              │ registered.v1  │
                                └────────┬───────┘
                                         │
                                         ↓
                                ┌─────────────────┐
                                │ Profile Service │ (futuro)
                                │                 │
                                │ Consume evento  │
                                │ Crea perfil     │
                                └─────────────────┘
```

---

## 📊 Estado Actual del Proyecto

### ✅ Completado:
- [x] Base de datos con migraciones
- [x] Modelos y repositorios
- [x] Endpoints de auth (register, login, refresh, logout, me)
- [x] Refresh tokens con rotación
- [x] CORS configurado
- [x] Request-Id middleware
- [x] Logging estructurado (JSON)
- [x] Rate limiting / Anti-fuerza-bruta
- [x] **Kafka integrado - Evento user_registered** ✨ NUEVO
- [x] API Gateway (en `services/gateway/`)

### 🔜 Próximos Pasos:
- [ ] Redis para rate limiting (cluster-safe)
- [ ] Profile Service con consumer de user_registered
- [ ] Dead Letter Queue para eventos fallidos
- [ ] Tests unitarios
- [ ] CI/CD pipeline

---

## 💡 Notas Importantes

### Kafka Producer:
- **Async**: Usa `aiokafka` con asyncio
- **Lifecycle**: Se inicia en startup y se detiene en shutdown
- **Singleton**: Instancia global `bus` compartida
- **Serialización**: JSON automática para values

### Manejo de Errores:
- Si Kafka no está disponible al startup, el servicio loguea el error pero **NO falla**
- Esto permite desarrollo sin Kafka si es necesario
- En producción, quizás quieras que falle si Kafka no está disponible

### Trazabilidad:
- El `request-id` del middleware se propaga al evento
- Esto permite correlacionar:
  - Request del usuario
  - Log en auth-svc
  - Evento en Kafka
  - Procesamiento en profile-svc (futuro)

---

## 🎉 Resumen

**Ahora tu auth-svc:**
1. ✅ Registra usuarios en PostgreSQL
2. ✅ Emite evento `user_registered` a Kafka
3. ✅ Logs estructurados con trazabilidad completa
4. ✅ Rate limiting anti-fuerza-bruta
5. ✅ Refresh tokens seguros con rotación
6. ✅ CORS y Request-Id configurados

**¡Sistema listo para arquitectura de microservicios event-driven!** 🚀
