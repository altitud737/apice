@echo off
echo ========================================
echo Test API de Captura de Leads
echo ========================================
echo.

REM Reemplaza con una API Key real de tu base de datos
REM Puedes obtenerla desde el admin: /admin/accounts/company/
if "%API_KEY%"=="" set API_KEY=REEMPLAZAR_CON_API_KEY_REAL

echo Enviando lead de prueba...
echo.

curl -X POST http://localhost:8000/api/leads/ ^
  -H "Content-Type: application/json" ^
  -H "x-api-key: %API_KEY%" ^
  -d "{\"name\": \"Juan Perez Test\", \"email\": \"juan.test@example.com\", \"phone\": \"1133334444\", \"message\": \"Lead de prueba desde cURL\", \"source\": \"facebook\", \"metadata\": {\"page\": \"/contacto\", \"campaign\": \"test_campaign\", \"utm_source\": \"facebook\", \"utm_medium\": \"cpc\"}}"

echo.
echo.
echo ========================================
echo Test completado
echo ========================================
pause
