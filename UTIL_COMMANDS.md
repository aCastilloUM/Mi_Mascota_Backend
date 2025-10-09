# 🔧 Comandos Útiles - Mi Mascota Backend

## 🐳 Docker Commands

### Start/Stop
```bash
# Iniciar todos los contenedores
cd deploy
docker compose up -d

# Ver logs en tiempo real
docker compose logs -f

# Ver logs de un servicio específico
docker compose logs -f auth-svc
docker compose logs -f gateway

# Detener todos los contenedores
docker compose down

# Detener y eliminar volúmenes (¡CUIDADO! Borra datos)
docker compose down -v
```

### Health Checks
```bash
# Gateway health
curl http://localhost:8080/health

# Auth service health
curl http://localhost:8080/api/v1/health

# Ver estado de containers
docker compose ps

# Ver recursos utilizados
docker stats
```

### Rebuild
```bash
# Rebuild un servicio específico
docker compose build auth-svc
docker compose up -d auth-svc

# Rebuild todos los servicios
docker compose build
docker compose up -d

# Rebuild sin cache
docker compose build --no-cache auth-svc
```

---

## 🔐 Testing Authentication

### Register
```bash
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!@#",
    "full_name": "Test User"
  }'
```

PowerShell:
```powershell
$body = '{"email":"test@example.com","password":"Test123!@#","full_name":"Test User"}'
Invoke-WebRequest -Uri "http://localhost:8080/api/v1/auth/register" -Method POST -ContentType "application/json" -Body $body
```

### Login
```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!@#"
  }' \
  -c cookies.txt
```

PowerShell:
```powershell
$body = '{"email":"test@example.com","password":"Test123!@#"}'
$response = Invoke-WebRequest -Uri "http://localhost:8080/api/v1/auth/login" -Method POST -ContentType "application/json" -Body $body -SessionVariable session
$token = ($response.Content | ConvertFrom-Json).access_token
```

### Get User Info (/me)
```bash
# Guardar token de login
TOKEN="eyJhbGci..."

curl http://localhost:8080/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

PowerShell:
```powershell
$headers = @{ "Authorization" = "Bearer $token" }
Invoke-WebRequest -Uri "http://localhost:8080/api/v1/auth/me" -Headers $headers
```

### Refresh Token
```bash
curl -X POST http://localhost:8080/api/v1/auth/refresh \
  -b cookies.txt \
  -c cookies.txt
```

PowerShell:
```powershell
Invoke-WebRequest -Uri "http://localhost:8080/api/v1/auth/refresh" -Method POST -WebSession $session
```

### Logout
```bash
curl -X POST http://localhost:8080/api/v1/auth/logout \
  -H "Authorization: Bearer $TOKEN" \
  -b cookies.txt
```

PowerShell:
```powershell
Invoke-WebRequest -Uri "http://localhost:8080/api/v1/auth/logout" -Method POST -Headers $headers -WebSession $session
```

---

## 🔐 2FA TOTP Commands

### Enable 2FA
```bash
curl -X POST http://localhost:8080/api/v1/auth/2fa/enable \
  -H "Authorization: Bearer $TOKEN"
```

PowerShell:
```powershell
$response = Invoke-WebRequest -Uri "http://localhost:8080/api/v1/auth/2fa/enable" -Method POST -Headers $headers
$data = $response.Content | ConvertFrom-Json
$data.qr_code  # QR code en base64
$data.secret   # Secret para TOTP
$data.backup_codes  # 10 backup codes
```

### Verify Setup
```bash
curl -X POST http://localhost:8080/api/v1/auth/2fa/verify-setup \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"code": "123456"}'
```

PowerShell:
```powershell
$body = '{"code":"123456"}'
Invoke-WebRequest -Uri "http://localhost:8080/api/v1/auth/2fa/verify-setup" -Method POST -Headers $headers -ContentType "application/json" -Body $body
```

### Login with 2FA (Step 1)
```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!@#"
  }'

# Response: { "requires_2fa": true, "temp_session_id": "uuid..." }
```

### Login with 2FA (Step 2)
```bash
TEMP_SESSION_ID="uuid-from-step-1"

curl -X POST http://localhost:8080/api/v1/auth/2fa/verify-login \
  -H "Content-Type: application/json" \
  -d '{
    "temp_session_id": "'$TEMP_SESSION_ID'",
    "code": "123456"
  }' \
  -c cookies.txt
```

PowerShell:
```powershell
$temp_id = "uuid-from-step-1"
$body = "{`"temp_session_id`":`"$temp_id`",`"code`":`"123456`"}"
Invoke-WebRequest -Uri "http://localhost:8080/api/v1/auth/2fa/verify-login" -Method POST -ContentType "application/json" -Body $body
```

### Disable 2FA
```bash
curl -X POST http://localhost:8080/api/v1/auth/2fa/disable \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "Test123!@#",
    "code": "123456"
  }'
```

---

## 🔑 Password Reset Commands

### Forgot Password (Step 1)
```bash
curl -X POST http://localhost:8080/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

PowerShell:
```powershell
$body = '{"email":"test@example.com"}'
Invoke-WebRequest -Uri "http://localhost:8080/api/v1/auth/forgot-password" -Method POST -ContentType "application/json" -Body $body
```

### Get Reset Token from Database
```bash
docker compose exec postgres psql -U app -d appdb -c \
  "SELECT password_reset_token FROM auth.users WHERE email='test@example.com';"
```

PowerShell:
```powershell
docker compose exec postgres psql -U app -d appdb -c "SELECT password_reset_token FROM auth.users WHERE email='test@example.com';"
```

### Reset Password (Step 2)
```bash
RESET_TOKEN="token-from-database"

curl -X POST http://localhost:8080/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "'$RESET_TOKEN'",
    "new_password": "NewPassword123!@#"
  }'
```

PowerShell:
```powershell
$reset_token = "token-from-database"
$body = "{`"token`":`"$reset_token`",`"new_password`":`"NewPassword123!@#`"}"
Invoke-WebRequest -Uri "http://localhost:8080/api/v1/auth/reset-password" -Method POST -ContentType "application/json" -Body $body
```

---

## 💾 Database Commands

### Connect to PostgreSQL
```bash
docker compose exec postgres psql -U app -d appdb
```

### Common Queries
```sql
-- Ver todos los usuarios
SELECT id, email, full_name, is_verified, two_factor_enabled, created_at 
FROM auth.users;

-- Ver sesiones activas
SELECT user_id, is_active, last_activity, created_at 
FROM auth.sessions 
WHERE is_active = true;

-- Ver usuario específico
SELECT * FROM auth.users WHERE email = 'test@example.com';

-- Ver si 2FA está habilitado
SELECT email, two_factor_enabled, two_factor_secret 
FROM auth.users 
WHERE email = 'test@example.com';

-- Ver tokens de reset activos
SELECT email, password_reset_token, password_reset_expires 
FROM auth.users 
WHERE password_reset_token IS NOT NULL;

-- Contar usuarios
SELECT COUNT(*) FROM auth.users;

-- Contar sesiones activas
SELECT COUNT(*) FROM auth.sessions WHERE is_active = true;
```

### Database Management
```bash
# Backup database
docker compose exec postgres pg_dump -U app appdb > backup.sql

# Restore database
docker compose exec -T postgres psql -U app -d appdb < backup.sql

# Drop and recreate database (¡CUIDADO!)
docker compose exec postgres psql -U app -c "DROP DATABASE IF EXISTS appdb;"
docker compose exec postgres psql -U app -c "CREATE DATABASE appdb;"
```

---

## 📦 Redis Commands

### Connect to Redis
```bash
docker compose exec redis redis-cli
```

### Common Commands
```redis
# Ping
PING

# Ver todas las keys
KEYS *

# Ver keys de 2FA temp sessions
KEYS 2fa:temp_session:*

# Ver valor de una key
GET key_name

# Ver TTL de una key
TTL 2fa:temp_session:uuid

# Eliminar una key
DEL key_name

# Limpiar toda la base de datos (¡CUIDADO!)
FLUSHDB

# Ver info del servidor
INFO

# Ver memoria usada
INFO memory
```

PowerShell (desde host):
```powershell
# Ver keys de 2FA
docker compose exec redis redis-cli KEYS "2fa:temp_session:*"

# Ping
docker compose exec redis redis-cli PING
```

---

## 📊 Kafka Commands

### Ver Topics
```bash
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

### Ver Mensajes de un Topic
```bash
# Ver mensajes desde el inicio
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic auth-events \
  --from-beginning

# Ver solo mensajes nuevos
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic auth-events
```

### Crear Topic Manualmente
```bash
docker compose exec kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create \
  --topic new-topic \
  --partitions 1 \
  --replication-factor 1
```

### Describir Topic
```bash
docker compose exec kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --describe \
  --topic auth-events
```

---

## 🔍 Elasticsearch & Kibana

### Check Elasticsearch
```bash
# Health check
curl http://localhost:9200/_cluster/health

# Ver índices
curl http://localhost:9200/_cat/indices?v

# Buscar en logs
curl http://localhost:9200/logs-*/_search?pretty
```

### Access Kibana
```
Open: http://localhost:5601
```

---

## 🔧 Troubleshooting

### Ver Logs Detallados
```bash
# Todos los servicios
docker compose logs -f

# Solo errores
docker compose logs -f | grep -i error

# Últimas 100 líneas
docker compose logs --tail 100

# Desde cierta fecha
docker compose logs --since "2025-10-06T17:00:00"
```

### Restart Services
```bash
# Restart un servicio
docker compose restart auth-svc

# Restart todos
docker compose restart

# Force recreate
docker compose up -d --force-recreate auth-svc
```

### Check Resource Usage
```bash
# Ver CPU/Memory usage
docker stats

# Ver espacio en disco
docker system df

# Limpiar recursos no usados
docker system prune -a
```

### Network Issues
```bash
# Ver networks
docker network ls

# Inspeccionar network
docker network inspect deploy_default

# Ver containers en la network
docker network inspect deploy_default | grep -i name
```

### Database Connection Issues
```bash
# Check PostgreSQL logs
docker compose logs postgres

# Check if port is open
netstat -ano | findstr :5432

# Test connection
docker compose exec postgres pg_isready -U app
```

---

## 🧪 Testing Scripts

### Run All Manual Tests
```bash
cd services/auth-svc/tests
python run_all_manual_tests.py
```

### Individual Tests
```bash
# Test 1: Register
python manual_test_1_register.py

# Test 2: Login
python manual_test_2_login.py

# Test 3: Me endpoint
python manual_test_3_me.py

# Test 4: Refresh token
python manual_test_4_refresh.py

# Test 5: Logout
python manual_test_5_logout.py

# Test 2FA
python manual_test_2fa.py
```

---

## 📈 Monitoring

### Check All Services Health
PowerShell script:
```powershell
Write-Host "Checking all services..." -ForegroundColor Yellow
$services = @("gateway", "auth-svc")
foreach ($service in $services) {
    $url = if ($service -eq "gateway") { "http://localhost:8080/health" } else { "http://localhost:8080/api/v1/health" }
    try {
        $response = Invoke-WebRequest -Uri $url -Method GET
        Write-Host "✅ $service : $($response.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "❌ $service : ERROR" -ForegroundColor Red
    }
}
```

### Monitor Logs in Real-Time
```bash
# Multiple terminal windows
# Terminal 1: Gateway logs
docker compose logs -f gateway

# Terminal 2: Auth service logs
docker compose logs -f auth-svc

# Terminal 3: PostgreSQL logs
docker compose logs -f postgres

# Terminal 4: Redis logs
docker compose logs -f redis
```

---

## 🚀 Quick Start (Fresh Install)

```bash
# 1. Clone repository
git clone <repo-url>
cd Backend

# 2. Start services
cd deploy
docker compose up -d

# 3. Wait for services to be ready (~30 seconds)
docker compose ps

# 4. Check health
curl http://localhost:8080/health
curl http://localhost:8080/api/v1/health

# 5. Run tests
cd ../services/auth-svc/tests
python run_all_manual_tests.py

# 6. Access services
echo "Gateway: http://localhost:8080"
echo "Auth Service: http://localhost:8000"
echo "Adminer: http://localhost:8081"
echo "Kibana: http://localhost:5601"
```

---

## 📝 Development Workflow

### Make Code Changes
```bash
# 1. Edit code in services/auth-svc/app/

# 2. Rebuild and restart
cd deploy
docker compose build auth-svc
docker compose up -d auth-svc

# 3. Check logs
docker compose logs -f auth-svc

# 4. Test changes
cd ../services/auth-svc/tests
python manual_test_X.py
```

### Database Migrations
```bash
# 1. Create migration
docker compose exec auth-svc alembic revision --autogenerate -m "Description"

# 2. Apply migration
docker compose exec auth-svc alembic upgrade head

# 3. Rollback migration
docker compose exec auth-svc alembic downgrade -1

# 4. Check current version
docker compose exec auth-svc alembic current
```

---

## 🔐 Security Notes

### Never Commit
- `.env` files with real secrets
- `cookies.txt` with session tokens
- Database backups with real data
- `tokens.json` with real JWT tokens

### Rotate Regularly
- JWT secret key
- Database passwords
- Redis password (if using)
- API keys

### Monitor
- Failed login attempts
- Unusual API access patterns
- Database connection failures
- High memory/CPU usage

---

## 📚 Documentation Links

- [Full Testing Report](./TESTING_FINAL_COMPLETE.md)
- [Executive Summary](./TESTING_SUMMARY_EXECUTIVE.md)
- [Testing Dashboard](./TESTING_DASHBOARD.md)
- [2FA TOTP Tests](./2FA_TOTP_TEST_COMPLETE.md)
- [Docker Guide](./DOCKER_GUIDE.md)

---

**Last Updated**: 6 de octubre de 2025  
**Version**: 1.0.0  
**Status**: Production Ready
