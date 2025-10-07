# Quick Start - Todo en Docker
# Levanta TODO en contenedores (infraestructura + microservicios)

Write-Host "🐳 Iniciando Backend - Mi Mascota (Docker Full)" -ForegroundColor Green
Write-Host ""

# Verificar .env
if (!(Test-Path "deploy\.env")) {
    Write-Host "⚠️  Archivo .env no encontrado" -ForegroundColor Yellow
    Write-Host "📋 Creando desde .env.example..." -ForegroundColor Cyan
    Copy-Item "deploy\.env.example" "deploy\.env"
    Write-Host ""
    Write-Host "⚠️  IMPORTANTE: Editá deploy\.env con tus valores reales" -ForegroundColor Red
    Write-Host "   - SMTP_USER y SMTP_PASSWORD (Gmail)" -ForegroundColor Yellow
    Write-Host "   - JWT_SECRET_KEY (cambiar por uno seguro)" -ForegroundColor Yellow
    Write-Host "   - POSTGRES_PASSWORD (cambiar por uno seguro)" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Presioná Enter cuando hayas configurado .env"
}

# Buildar imágenes
Write-Host "🔨 Construyendo imágenes Docker..." -ForegroundColor Cyan
Set-Location deploy
docker compose build

# Levantar todo
Write-Host ""
Write-Host "🚀 Levantando todos los servicios..." -ForegroundColor Cyan
docker compose up -d

# Esperar que estén healthy
Write-Host "⏳ Esperando que los servicios estén listos (30s)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Aplicar migraciones
Write-Host ""
Write-Host "📊 Aplicando migraciones..." -ForegroundColor Cyan
docker compose exec auth-svc python -m alembic upgrade head

# Verificar estado
Write-Host ""
Write-Host "✅ Estado de servicios:" -ForegroundColor Green
docker compose ps

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Green
Write-Host "✅ TODO LISTO" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green
Write-Host ""
Write-Host "📍 Servicios disponibles:" -ForegroundColor Cyan
Write-Host "   - Gateway:     http://localhost:8080" -ForegroundColor White
Write-Host "   - Auth-svc:    http://localhost:8006" -ForegroundColor White
Write-Host "   - PostgreSQL:  localhost:5432" -ForegroundColor White
Write-Host "   - Redis:       localhost:6379" -ForegroundColor White
Write-Host "   - Kafka:       localhost:29092" -ForegroundColor White
Write-Host "   - Adminer:     http://localhost:8081" -ForegroundColor White
Write-Host "   - Metrics:     http://localhost:8080/metrics" -ForegroundColor White
Write-Host ""
Write-Host "🧪 Para probar:" -ForegroundColor Yellow
Write-Host "   curl http://localhost:8080/health" -ForegroundColor White
Write-Host "   python test_complete.py" -ForegroundColor White
Write-Host ""
Write-Host "📊 Ver logs:" -ForegroundColor Yellow
Write-Host "   docker compose logs -f" -ForegroundColor White
Write-Host "   docker compose logs -f gateway" -ForegroundColor White
Write-Host "   docker compose logs -f auth-svc" -ForegroundColor White
Write-Host ""
Write-Host "🛑 Para detener:" -ForegroundColor Yellow
Write-Host "   docker compose down" -ForegroundColor White
Write-Host ""
