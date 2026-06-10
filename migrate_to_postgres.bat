@echo off
echo ========================================
echo Migracion de SQLite a PostgreSQL
echo ========================================
echo.

echo [1/5] Verificando PostgreSQL...
psql --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: PostgreSQL no esta instalado
    echo Descarga desde: https://www.postgresql.org/download/windows/
    pause
    exit /b 1
)
echo OK - PostgreSQL instalado

echo.
echo [2/5] Creando base de datos apice_crm...
psql -U postgres -c "DROP DATABASE IF EXISTS apice_crm;"
psql -U postgres -c "CREATE DATABASE apice_crm;"
if errorlevel 1 (
    echo ERROR: No se pudo crear la base de datos
    echo Verifica que PostgreSQL este corriendo y que la password sea 'postgres'
    pause
    exit /b 1
)
echo OK - Base de datos creada

echo.
echo [3/5] Aplicando migraciones...
python manage.py migrate
if errorlevel 1 (
    echo ERROR: Fallo al aplicar migraciones
    pause
    exit /b 1
)
echo OK - Migraciones aplicadas

echo.
echo [4/5] Creando datos de prueba...
python setup_data.py
if errorlevel 1 (
    echo ADVERTENCIA: No se pudieron crear datos de prueba
    echo Puedes crearlos manualmente despues
)

echo.
echo [5/5] Verificando instalacion...
python manage.py check
if errorlevel 1 (
    echo ERROR: Hay problemas en la configuracion
    pause
    exit /b 1
)

echo.
echo ========================================
echo MIGRACION COMPLETADA EXITOSAMENTE
echo ========================================
echo.
echo Proximos pasos:
echo 1. Crear superusuario: python manage.py createsuperuser
echo 2. Iniciar servidor: python manage.py runserver
echo.
pause
