# 🐳 Guía de Docker Compose - Microservicios

## 📋 Descripción

Este proyecto usa **Docker Compose** para orquestar todos los servicios:

### **Infraestructura** (siempre en contenedores):
- 🐘 **PostgreSQL** (5432) - Base de datos principal
- 🔴 **Redis** (6379) - Cache y rate limiting
- 📨 **Kafka** (29092) + Zookeeper (2181) - Event streaming
- 🔍 **Elasticsearch** (9200) - Logs (opcional)
- 📊 **Kibana** (5601) - Visualización de logs (opcional)
- 🗄️ **Adminer** (8081) - Gestión de PostgreSQL (opcional)

### **Microservicios** (2 opciones):

#### **Opción A: Desarrollo Local** 🔥
- ✅ Hot reload automático
- ✅ Debugging fácil
- ✅ Cambios instantáneos
- ⚡ Más rápido para desarrollar

#### **Opción B: Docker Compose** 🐳
- ✅ Ambiente productivo
- ✅ Aislamiento completo
- ✅ Fácil deployment
- ✅ Consistencia entre entornos

---

## 🚀 Opción A: Desarrollo Local (Recomendado para dev)

### 1. Levantar solo infraestructura:
```bash
cd deploy
docker compose up -d postgres redis kafka zookeeper adminer
```

### 2. Verificar que estén corriendo:
```bash
docker compose ps
```

### 3. Aplicar migraciones (solo primera vez):
```bash
cd ../services/auth-svc
python -m alembic upgrade head
```

### 4. Correr Gateway localmente:
```bash
cd ../services/gateway
python -m uvicorn app.main:app --reload --port 8080
```

### 5. Correr Auth-svc localmente (en otra terminal):
```bash
cd ../services/auth-svc
python -m uvicorn app.main:app --reload --port 8006
```

### 6. Probar:
```bash
curl http://localhost:8080/health
```

### ✅ Ventajas:
- 🔥 Hot reload: cambios de código se aplican al instante
- 🐛 Debugging: breakpoints, logs directos en consola
- ⚡ Rápido: no necesita rebuilds
- 📝 Logs: todo en tu terminal

---

## 🐳 Opción B: Todo en Docker Compose

### 1. Configurar variables de entorno:
```bash
cd deploy
cp .env.example .env
# Editar .env con tus valores
```

### 2. Construir imágenes:
```bash
docker compose build
```

### 3. Levantar todo:
```bash
docker compose up -d
```

### 4. Ver logs:
```bash
# Todos los servicios
docker compose logs -f

# Solo Gateway
docker compose logs -f gateway

# Solo Auth-svc
docker compose logs -f auth-svc
```

### 5. Aplicar migraciones:
```bash
docker compose exec auth-svc python -m alembic upgrade head
```

### 6. Verificar estado:
```bash
docker compose ps
```

### 7. Probar:
```bash
curl http://localhost:8080/health
```

### ✅ Ventajas:
- 🐳 Aislamiento: cada servicio en su contenedor
- 🚀 Productivo: igual a producción
- 📦 Portátil: funciona en cualquier máquina
- 🔄 Consistente: mismo ambiente siempre

---

## 📊 Arquitectura de Contenedores

```
┌─────────────────────────────────────────────────────┐
│              DOCKER COMPOSE NETWORK                 │
│                                                     │
│  ┌──────────────┐         ┌──────────────┐        │
│  │   Gateway    │ ───────>│   Auth-svc   │        │
│  │  (Port 8080) │         │  (Port 8006) │        │
│  └──────┬───────┘         └──────┬───────┘        │
│         │                        │                 │
│         │        ┌───────────────┼─────────┐      │
│         │        │               │         │      │
│         ▼        ▼               ▼         ▼      │
│  ┌──────────┐ ┌──────┐    ┌──────────┐ ┌──────┐ │
│  │  Redis   │ │ Post │    │  Kafka   │ │ Zoo  │ │
│  │  (6379)  │ │ gres │    │ (29092)  │ │keeper│ │
│  └──────────┘ └──────┘    └──────────┘ └──────┘ │
│                                                     │
└─────────────────────────────────────────────────────┘
         │                                     │
         │ Port mapping                        │
         ▼                                     ▼
   Host: 8080 (Gateway)              Host: 8006 (Auth-svc)
   Host: 5432 (PostgreSQL)           Host: 6379 (Redis)
   Host: 29092 (Kafka)                Host: 8081 (Adminer)
```

---

## 🔧 Comandos Útiles

### **Ver estado:**
```bash
docker compose ps
```

### **Ver logs:**
```bash
# Todos
docker compose logs -f

# Solo un servicio
docker compose logs -f gateway
docker compose logs -f auth-svc
```

### **Reiniciar un servicio:**
```bash
docker compose restart gateway
docker compose restart auth-svc
```

### **Parar todo:**
```bash
docker compose down
```

### **Parar y eliminar volúmenes:**
```bash
docker compose down -v
```

### **Rebuilder imágenes:**
```bash
docker compose build --no-cache
docker compose up -d
```

### **Ejecutar comandos dentro de un contenedor:**
```bash
# Migrar DB
docker compose exec auth-svc python -m alembic upgrade head

# Entrar al contenedor
docker compose exec auth-svc bash

# Ver logs de PostgreSQL
docker compose logs -f postgres
```

---

## 🧹 Limpiar Docker

### **Limpiar contenedores parados:**
```bash
docker container prune
```

### **Limpiar imágenes sin usar:**
```bash
docker image prune -a
```

### **Limpiar todo (cuidado!):**
```bash
docker system prune -a --volumes
```

---

## 🔄 Workflow Recomendado

### **Para Desarrollo:**
1. Levantar solo infraestructura en Docker:
   ```bash
   docker compose up -d postgres redis kafka zookeeper
   ```

2. Correr microservicios localmente:
   ```bash
   # Terminal 1
   cd services/gateway
   python -m uvicorn app.main:app --reload --port 8080
   
   # Terminal 2
   cd services/auth-svc
   python -m uvicorn app.main:app --reload --port 8006
   ```

### **Para Testing/Staging:**
1. Levantar todo en Docker:
   ```bash
   docker compose up -d
   ```

2. Aplicar migraciones:
   ```bash
   docker compose exec auth-svc python -m alembic upgrade head
   ```

3. Probar endpoints:
   ```bash
   python test_complete.py
   python services/auth-svc/tests/manual_test_2fa.py
   ```

### **Para Producción:**
1. Usar Docker Compose con profiles:
   ```bash
   docker compose --profile production up -d
   ```

2. Agregar Nginx reverse proxy
3. Configurar SSL/TLS
4. Configurar logging a sistema externo
5. Configurar backup de PostgreSQL

---

## 🔐 Seguridad

### **Variables de Entorno:**
- ❌ **NUNCA** commitear `.env` con secrets reales
- ✅ Usar `.env.example` como template
- ✅ Cambiar `JWT_SECRET_KEY` en producción
- ✅ Usar passwords fuertes para PostgreSQL

### **Network:**
- ✅ Docker Compose crea network aislada automáticamente
- ✅ Solo exponer puertos necesarios al host
- ✅ En producción, no exponer puertos de DB/Redis

### **Contenedores:**
- ✅ Usar imágenes oficiales (python:3.12-slim)
- ✅ Multi-stage builds para imágenes más pequeñas
- ✅ Ejecutar como non-root user (TODO en Dockerfile)

---

## 📈 Monitoreo

### **Healthchecks:**
Todos los servicios tienen healthchecks configurados:
- Gateway: `http://localhost:8080/health`
- Auth-svc: `http://localhost:8006/health`
- PostgreSQL: `pg_isready`
- Redis: `redis-cli ping`

### **Métricas Prometheus:**
```bash
curl http://localhost:8080/metrics
```

### **Circuit Breakers:**
```bash
curl http://localhost:8080/circuit-breakers
```

---

## 🐛 Troubleshooting

### **Problema: Puerto ya en uso**
```bash
# Ver qué está usando el puerto
netstat -ano | findstr :8080

# Matar el proceso (Windows)
taskkill /PID <PID> /F

# O cambiar el puerto en docker-compose.yml
```

### **Problema: Contenedor no arranca**
```bash
# Ver logs detallados
docker compose logs auth-svc
docker compose logs gateway

# Ver todos los logs
docker compose logs
```

### **Problema: Error de conexión a DB**
```bash
# Verificar que PostgreSQL esté healthy
docker compose ps

# Verificar logs de PostgreSQL
docker compose logs postgres

# Probar conexión manual
docker compose exec postgres psql -U mimascota_user -d mimascota_db
```

### **Problema: Redis no conecta**
```bash
# Verificar Redis
docker compose ps redis

# Probar Redis
docker compose exec redis redis-cli ping
```

### **Problema: Migraciones no aplican**
```bash
# Ver estado de migraciones
docker compose exec auth-svc python -m alembic current

# Aplicar manualmente
docker compose exec auth-svc python -m alembic upgrade head

# Ver historial
docker compose exec auth-svc python -m alembic history
```

---

## 📚 Referencias

- Docker Compose: https://docs.docker.com/compose/
- FastAPI: https://fastapi.tiangolo.com/
- PostgreSQL: https://www.postgresql.org/docs/
- Redis: https://redis.io/docs/
- Kafka: https://kafka.apache.org/documentation/

---

## ✅ Checklist de Deployment

### **Primera vez:**
- [ ] Copiar `.env.example` a `.env`
- [ ] Configurar SMTP (Gmail app password)
- [ ] Cambiar `JWT_SECRET_KEY`
- [ ] Cambiar password de PostgreSQL
- [ ] Buildar imágenes: `docker compose build`
- [ ] Levantar todo: `docker compose up -d`
- [ ] Aplicar migraciones: `docker compose exec auth-svc alembic upgrade head`
- [ ] Verificar healthchecks: `docker compose ps`
- [ ] Probar endpoints: `curl http://localhost:8080/health`

### **Actualizaciones:**
- [ ] Pull latest code: `git pull`
- [ ] Rebuild: `docker compose build`
- [ ] Down + Up: `docker compose down && docker compose up -d`
- [ ] Migrar: `docker compose exec auth-svc alembic upgrade head`
- [ ] Verificar: `docker compose logs -f`

---

**¡Listo para producción!** 🚀
