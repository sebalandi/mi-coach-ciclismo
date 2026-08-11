@echo off
REM Paso 2 de 2: envuelve la app ya armada (dist\MiCoachDeCiclismo\) en un
REM instalador de verdad, usando Inno Setup. Corre primero construir_exe.bat.
REM
REM Necesita Inno Setup instalado (gratis, una sola vez en tu PC):
REM     https://jrsoftware.org/isdl.php

cd /d "%~dp0"

set "ISCC="

if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files (x86)\Inno Setup 7\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 7\ISCC.exe"
if exist "C:\Program Files\Inno Setup 7\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 7\ISCC.exe"
if exist "C:\Program Files (x86)\Inno Setup 5\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
if exist "C:\Program Files\Inno Setup 5\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 5\ISCC.exe"

REM Si no aparecio en ninguna de esas carpetas, probamos si esta en el PATH
if not defined ISCC (
  where ISCC.exe >nul 2>nul
  if not errorlevel 1 set "ISCC=ISCC.exe"
)

if not defined ISCC (
  echo No encontre Inno Setup instalado en las rutas habituales ni en el PATH.
  echo.
  echo Si sabes donde lo instalaste, busca el archivo ISCC.exe a mano
  echo ^(normalmente dentro de la carpeta de instalacion de Inno Setup^)
  echo y corre directamente:
  echo     "ruta\a\ISCC.exe" instalador.iss
  echo.
  echo O si no lo tenes instalado: https://jrsoftware.org/isdl.php
  pause
  exit /b 1
)

echo Usando Inno Setup en: %ISCC%

if not exist "dist\MiCoachDeCiclismo\MiCoachDeCiclismo.exe" (
  echo.
  echo No encontre dist\MiCoachDeCiclismo\MiCoachDeCiclismo.exe
  echo Primero tenes que correr construir_exe.bat para generar la app.
  pause
  exit /b 1
)

echo.
echo Generando el instalador...
"%ISCC%" instalador.iss

echo.
echo ------------------------------------------------------------
echo Listo. El instalador esta en:
echo     instalador_salida\Instalador_MiCoachDeCiclismo.exe
echo.
echo Ese es el UNICO archivo que le compartis a tus companeros - lo
echo corren, siguen el asistente, y les queda instalado con su icono
echo en el menu de inicio, sin necesitar Python ni nada mas.
echo ------------------------------------------------------------
pause
