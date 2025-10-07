# Quick Start - Desarrollo Local
# Levanta infraestructura en Docker y microservicios localmente

Write-Host "🚀 Iniciando Backend - Mi Mascota" -ForegroundColor Green
Write-Host ""

# 1. Levantar infraestructura
Write-Host "📦 Levantando infraestructura (PostgreSQL, Redis, Kafka)..." -ForegroundColor Cyan
Set-Location deploy
docker compose up -d postgres redis kafka zookeeper adminer

# Esperar que los servicios estén healthy
Write-Host "⏳ Esperando que los servicios estén listos..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Verificar estado
Write-Host ""
Write-Host "✅ Estado de infraestructura:" -ForegroundColor Green
docker compose ps

# 2. Aplicar migraciones (solo si es necesario)
Write-Host ""
Write-Host "🔄 Verificando migraciones..." -ForegroundColor Cyan
Set-Location ..\services\auth-svc
$migrations = python -m alembic current 2>&1
if ($migrations -match "None") {
    Write-Host "📊 Aplicando migraciones..." -ForegroundColor Yellow
    python -m alembic upgrade head
} else {
    Write-Host "✅ Migraciones ya aplicadas" -ForegroundColor Green
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Green
Write-Host "✅ INFRAESTRUCTURA LISTA" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green
Write-Host ""
Write-Host "📍 Servicios disponibles:" -ForegroundColor Cyan
Write-Host "   - PostgreSQL:  localhost:5432" -ForegroundColor White
Write-Host "   - Redis:       localhost:6379" -ForegroundColor White
Write-Host "   - Kafka:       localhost:29092" -ForegroundColor White
Write-Host "   - Adminer:     http://localhost:8081" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Para iniciar los microservicios:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   Terminal 1 (Gateway):" -ForegroundColor Magenta
Write-Host "   cd services\gateway" -ForegroundColor White
Write-Host "   python -m uvicorn app.main:app --reload --port 8080" -ForegroundColor White
Write-Host ""
Write-Host "   Terminal 2 (Auth-svc):" -ForegroundColor Magenta
Write-Host "   cd services\auth-svc" -ForegroundColor White
Write-Host "   python -m uvicorn app.main:app --reload --port 8006" -ForegroundColor White
Write-Host ""
Write-Host "🧪 Para probar:" -ForegroundColor Yellow
Write-Host "   python test_complete.py" -ForegroundColor White
Write-Host "   python services\auth-svc\tests\manual_test_2fa.py" -ForegroundColor White
Write-Host ""
