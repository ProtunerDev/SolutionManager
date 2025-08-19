@echo off
echo =========================================================
echo   EJECUTAR COMANDOS SQL EN LA BASE DE DATOS
echo =========================================================
echo.

echo Ejecutando script SQL en la base de datos PostgreSQL...
echo.

set DB_HOST=shuttle.proxy.rlwy.net
set DB_PORT=50835
set DB_NAME=railway
set DB_USER=postgresql
set PGPASSWORD=jDslkFSncfcGsAFkfQnlpHLAnBNFwvkY

echo Conectando a: %DB_HOST%:%DB_PORT%/%DB_NAME%
echo Usuario: %DB_USER%
echo.

psql -h %DB_HOST% -p %DB_PORT% -d %DB_NAME% -U %DB_USER% -f app\database\schema.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Tablas creadas exitosamente!
    echo.
    echo Las siguientes tablas fueron creadas:
    echo   - users
    echo   - vehicle_info  
    echo   - field_dependencies
    echo   - field_values
    echo   - solutions
    echo   - solution_types
    echo   - file_metadata
    echo   - differences_metadata
    echo.
    echo 🎉 La base de datos está lista para usar!
) else (
    echo.
    echo ❌ Error ejecutando el script SQL
    echo.
    echo 💡 Alternativas:
    echo   1. Usa pgAdmin o DBeaver para conectarte manualmente
    echo   2. Ejecuta: python generate_tables.py 
    echo   3. Copia y pega el SQL manualmente
)

echo.
pause
