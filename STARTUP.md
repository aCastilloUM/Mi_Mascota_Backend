# 🚀 Startup Scripts - Mi Mascota Backend

## Para arrancar todo el sistema fácilmente

### Windows PowerShell

#### 1. Arrancar Infraestructura (Docker)
```powershell
# Desde la raíz del proyecto
cd "c:\Users\agust\Escritorio\Mi Mascota\Backend\deploy"
docker-compose up -d

# Verificar que todo esté corriendo
docker-compose ps
```

Deberías ver:
- ✅ postgres (5432)
- ✅ redis (6379)
- ✅ zookeeper (2181)
- ✅ kafka (29092)

---

#### 2. Arrancar Gateway (Terminal 1)
```powershell
cd "c:\Users\agust\Escritorio\Mi Mascota\Backend\services\gateway"
python -m uvicorn app.main:app --reload --port 8080
```

Deberías ver logs JSON:
```json
{"levelname": "INFO", "name": "gateway", "message": "Application startup complete"}
```

---

#### 3. Arrancar auth-svc (Terminal 2)
```powershell
cd "c:\Users\agust\Escritorio\Mi Mascota\Backend\services\auth-svc"
python -m uvicorn app.main:app --reload --port 8006
```

Deberías ver logs JSON:
```json
{"levelname": "INFO", "name": "auth-svc", "message": "service_start"}
{"levelname": "INFO", "name": "app.infra.redis", "message": "redis_connected"}
{"levelname": "INFO", "name": "app.events.kafka", "message": "kafka_producer_started"}
```

---

#### 4. Probar el Sistema (Terminal 3)
```powershell
# Test básico
cd "c:\Users\agust\Escritorio\Mi Mascota\Backend\services\gateway"
python test_gateway_features.py
```

O con curl/Invoke-WebRequest:
```powershell
# Health check con Request-ID
$response = Invoke-WebRequest -Uri "http://localhost:8080/health" -Method GET
Write-Host "Status:" $response.StatusCode
Write-Host "Request-ID:" $response.Headers["X-Request-Id"]
Write-Host "Rate Limit:" $response.Headers["X-RateLimit-Remaining"]

# Registro de usuario
$body = @{
    email = "test@example.com"
    password = "Test123!@#"
    full_name = "Test User"
} | ConvertTo-Json

$response = Invoke-WebRequest `
    -Uri "http://localhost:8080/api/v1/auth/register" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body

Write-Host $response.Content
```

---

## Scripts Automatizados

### start-all.ps1 (TODO)
Script para arrancar todo automáticamente en terminales separadas:

```powershell
# start-all.ps1
# Arrancar Docker
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd deploy; docker-compose up"

# Esperar 5 segundos
Start-Sleep -Seconds 5

# Arrancar Gateway
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd services\gateway; python -m uvicorn app.main:app --reload --port 8080"

# Arrancar auth-svc
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd services\auth-svc; python -m uvicorn app.main:app --reload --port 8006"

Write-Host "✅ Todo arrancado!"
Write-Host "Gateway: http://localhost:8080"
Write-Host "auth-svc: http://localhost:8006"
```

### stop-all.ps1 (TODO)
```powershell
# stop-all.ps1
# Detener servicios Python
Get-Process python | Where-Object {$_.Path -like "*Mi Mascota*"} | Stop-Process -Force

# Detener Docker
cd deploy
docker-compose down

Write-Host "✅ Todo detenido"
```

---

## Verificación Rápida

### 1. ¿Está corriendo la infraestructura?
```powershell
docker ps
```
Deberías ver 4 contenedores: postgres, redis, zookeeper, kafka

### 2. ¿Está corriendo el Gateway?
```powershell
curl http://localhost:8080/health
```
Respuesta: `{"status":"healthy"}`

### 3. ¿Está corriendo auth-svc?
```powershell
curl http://localhost:8006/health
```
Respuesta: `{"status":"ok"}`

### 4. ¿Gateway puede llegar a auth-svc?
```powershell
curl http://localhost:8080/api/v1/auth/health
```
Debería redirigir correctamente

---

## Troubleshooting

### Error: "Port already in use"
```powershell
# Ver qué proceso está usando el puerto
netstat -ano | findstr :8080

# Detener el proceso (reemplaza PID)
Stop-Process -Id PID -Force
```

### Error: "Connection refused" (Docker)
```powershell
# Reiniciar Docker
cd deploy
docker-compose down
docker-compose up -d

# Esperar 10 segundos
Start-Sleep -Seconds 10
```

### Error: "Module not found"
```powershell
# Instalar dependencias
cd services/gateway
pip install -r requirements.txt

cd ../auth-svc
pip install -r requirements.txt
```

### Ver logs en tiempo real
```powershell
# Docker logs
docker-compose -f deploy/docker-compose.yml logs -f kafka

# Python logs (ya están en la terminal)
```

---

## Orden Correcto de Arranque

1. **Primero**: Docker (Postgres, Redis, Kafka, Zookeeper)
   - Esperar ~10 segundos para que Kafka inicie
2. **Segundo**: auth-svc (necesita Postgres, Redis, Kafka)
3. **Tercero**: Gateway (necesita auth-svc)
4. **Opcional**: Otros servicios 

---

## Puertos Usados

| Servicio | Puerto | URL |
|----------|--------|-----|
| Gateway | 8080 | http://localhost:8080 |
| auth-svc | 8006 | http://localhost:8006 |
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |
| Kafka | 29092 | localhost:29092 |
| Zookeeper | 2181 | localhost:2181 |

---

## URLs Útiles

### Gateway
- Health: http://localhost:8080/health
- Docs: http://localhost:8080/docs
- Root: http://localhost:8080/

### auth-svc (via Gateway)
- Register: POST http://localhost:8080/api/v1/auth/register
- Login: POST http://localhost:8080/api/v1/auth/login
- Me: GET http://localhost:8080/api/v1/auth/me
- Refresh: POST http://localhost:8080/api/v1/auth/refresh
- Logout: POST http://localhost:8080/api/v1/auth/logout

### auth-svc (directo, para debugging)
- Health: http://localhost:8006/health
- Docs: http://localhost:8006/docs

---

**¡Sistema listo para desarrollo! 🚀**
