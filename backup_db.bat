@echo off
REM Script de backup automático para la base de datos de Apice
REM Ejecutar diariamente con Task Scheduler de Windows

echo ========================================
echo Backup Automatico de Base de Datos Apice
echo ========================================
echo.

REM Crear carpeta de backups si no existe
if not exist "backups" mkdir backups

REM Generar timestamp
set TIMESTAMP=%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

REM Copiar base de datos
echo Creando backup...
copy db.sqlite3 backups\db_backup_%TIMESTAMP%.sqlite3

if errorlevel 1 (
    echo ERROR: No se pudo crear el backup
    pause
    exit /b 1
)

echo.
echo ========================================
echo BACKUP COMPLETADO EXITOSAMENTE
echo ========================================
echo Archivo: backups\db_backup_%TIMESTAMP%.sqlite3
echo.

REM Eliminar backups antiguos (mantener solo los últimos 30 días)
echo Limpiando backups antiguos...
forfiles /P backups /M db_backup_*.sqlite3 /D -30 /C "cmd /c del @path" 2>nul

echo.
echo Backups mantenidos: ultimos 30 dias
echo.
