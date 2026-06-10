@echo off
echo ========================================
echo   Iniciando Apice CRM
echo ========================================
echo.
cd /d "%~dp0"

echo [1/2] Verificando base de datos...
python manage.py migrate --noinput

echo.
echo [2/2] Iniciando servidor en http://127.0.0.1:3000/
echo.
echo   Apice INICIADO CORRECTAMENTE
echo ========================================
echo.
echo Accede a: http://127.0.0.1:3000/
echo Usuario: admin
echo Password: admin123
echo.
echo Presiona CTRL + C para detener el servidor
echo ========================================
echo.

python manage.py runserver 3000
