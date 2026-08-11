@echo off
REM Doble clic en este archivo para arrancar Mi Coach de Ciclismo.
REM Antes de abrir, revisa que esten instaladas las librerias que hacen falta.
REM Si ya estan, no hace nada y tarda un par de segundos; si falta alguna
REM (porque el proyecto se actualizo), la instala sola.

cd /d "%~dp0"

echo Revisando librerias...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo No pude instalar las librerias. Revisa tu conexion a internet.
  echo Si el problema sigue, corre a mano:  python -m pip install -r requirements.txt
  echo.
  pause
  exit /b 1
)

echo Abriendo la aplicacion...
python -m streamlit run app.py
pause
