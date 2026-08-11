@echo off
REM Rehace el ejecutable Y el instalador de una sola pasada.
REM Usalo cada vez que actualices el codigo del proyecto: los cambios en los
REM archivos .py NO llegan al .exe hasta que se vuelve a compilar.

cd /d "%~dp0"

echo ============================================================
echo  PASO 1 de 2: armando la aplicacion
echo ============================================================
call construir_exe.bat

if not exist "dist\MiCoachDeCiclismo\MiCoachDeCiclismo.exe" (
  echo.
  echo No se genero el ejecutable. Revisa los errores de arriba.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo  PASO 2 de 2: armando el instalador
echo ============================================================
call construir_instalador.bat
