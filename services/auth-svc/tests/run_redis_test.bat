@echo off
echo ============================================
echo Testing Redis Rate Limiting
echo ============================================
cd /d "c:\Users\agust\Escritorio\Mi Mascota\Backend\services\auth-svc\tests"
python test_redis_rate_limit.py
pause
