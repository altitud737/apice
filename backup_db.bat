@echo off
REM Script de backup de la base de datos PostgreSQL.
REM Requiere que pg_dump este en el PATH y las variables DB_* / DATABASE_URL en .env
REM Ejecutar diariamente con Task Scheduler de Windows.

setlocal EnableDelayedExpansion

echo ========================================
echo Backup PostgreSQL
echo ========================================
echo.

REM Crear carpeta de backups si no existe
if not exist "backups" mkdir backups

REM Generar timestamp
set TIMESTAMP=%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

REM Leer parametros de conexion via Django (toma DATABASE_URL o DB_*)
set DJANGO_SETTINGS_MODULE=core.settings
for /f "tokens=1,2,3,4,5" %%a in ('python -c "import django; django.setup(); from django.conf import settings; d=settings.DATABASES['default']; print(d['NAME'], d['USER'], d['HOST'] or 'localhost', d['PORT'] or '5432', d['PASSWORD'])" 2^>nul') do (
    set DB_NAME=%%a
    set DB_USER=%%b
    set DB_HOST=%%c
    set DB_PORT=%%d
    set PGPASSWORD=%%e
)

if "%DB_NAME%"=="" (
    echo ERROR: No se pudo leer la configuracion de la base de datos.
    echo Verifica DATABASE_URL en .env y DJANGO_SETTINGS_MODULE.
    pause
    exit /b 1
)

set BACKUP_FILE=backups\db_backup_%TIMESTAMP%.sql

echo Creando backup de %DB_NAME% (%DB_HOST%:%DB_PORT%) ...
pg_dump -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -F p -f %BACKUP_FILE%

if errorlevel 1 (
    echo ERROR: pg_dump fallo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo BACKUP COMPLETADO EXITOSAMENTE
echo ========================================
echo Archivo: %BACKUP_FILE%
echo.

REM Eliminar backups antiguos (mantener solo los ultimos 30 dias)
echo Limpiando backups antiguos...
forfiles /P backups /M db_backup_*.sql /D -30 /C "cmd /c del @path" 2>nul

echo.
echo Backups mantenidos: ultimos 30 dias
echo.

set PGPASSWORD=
endlocal
