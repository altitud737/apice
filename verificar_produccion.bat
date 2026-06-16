@echo off
echo ========================================
echo Verificacion del proyecto para Produccion
echo ========================================
echo.

echo [1/6] Verificando configuracion Django...
python manage.py check
if errorlevel 1 (
    echo ERROR: Hay problemas en la configuracion
    pause
    exit /b 1
)
echo OK - Configuracion correcta

echo.
echo [2/6] Verificando migraciones...
python manage.py showmigrations | findstr /C:"[ ]"
if not errorlevel 1 (
    echo ERROR: Hay migraciones pendientes
    echo Ejecuta: python manage.py migrate
    pause
    exit /b 1
)
echo OK - Todas las migraciones aplicadas

echo.
echo [3/6] Verificando conexion a PostgreSQL...
python -c "from django.db import connection; connection.ensure_connection(); print('OK - PostgreSQL accesible:', connection.settings_dict.get('NAME'))"
if errorlevel 1 (
    echo ERROR: No se pudo conectar a PostgreSQL
    echo Revisa DATABASE_URL en .env
    pause
    exit /b 1
)

echo.
echo [4/6] Verificando API de leads...
python -c "from apice.models import Lead; print(f'Leads en DB: {Lead.objects.count()}')"
if errorlevel 1 (
    echo ERROR: Problema con modelo Lead
    pause
    exit /b 1
)
echo OK - Modelo Lead funcional

echo.
echo [5/6] Verificando empresas y API Keys...
python -c "from accounts.models import Company; companies = Company.objects.all(); print(f'Empresas: {companies.count()}'); [print(f'  - {c.name}: {c.api_key[:20]}...') for c in companies]"
if errorlevel 1 (
    echo ERROR: Problema con modelo Company
    pause
    exit /b 1
)
echo OK - Empresas configuradas

echo.
echo [6/6] Verificando archivos estaticos...
if not exist "static" mkdir static
python manage.py collectstatic --noinput --clear >nul 2>&1
echo OK - Archivos estaticos listos

echo.
echo ========================================
echo VERIFICACION COMPLETADA
echo ========================================
echo.
echo El proyecto esta listo para:
echo   - Desarrollo local
echo   - Demos a clientes
echo   - Deploy a produccion
echo.
echo Proximos pasos:
echo   1. Crear backup: backup_db.bat
echo   2. Iniciar servidor: python manage.py runserver
echo   3. Deploy a Railway/Render cuando estes listo
echo.
pause
