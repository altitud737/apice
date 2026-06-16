@echo off
echo ========================================
echo   Iniciando servidor
echo ========================================
echo.
cd /d "%~dp0"

echo [1/2] Aplicando migraciones...
python manage.py migrate --noinput
if errorlevel 1 (
    echo ERROR: fallaron las migraciones. Revisa la conexion a PostgreSQL.
    pause
    exit /b 1
)

echo.
echo [2/2] Iniciando servidor en http://127.0.0.1:3000/
echo.
echo   SERVIDOR INICIADO
echo ========================================
echo.
echo Accede a: http://127.0.0.1:3000/
echo Admin:    http://127.0.0.1:3000/admin/
echo.
echo Presiona CTRL + C para detener el servidor
echo ========================================
echo.

python manage.py runserver 3000
