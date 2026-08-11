@echo off
REM Abre la app dejandola accesible desde el celular, en la misma red WiFi.
REM
REM No es una app nativa: es la misma aplicacion, servida desde esta PC y vista
REM en el navegador del celular. Por eso la PC tiene que quedar encendida y con
REM la app abierta mientras la uses desde el telefono.

cd /d "%~dp0"

echo Revisando librerias...
python -m pip install -q -r requirements.txt

echo.
echo ============================================================
echo   ABRIR EN EL CELULAR
echo ============================================================
echo.
echo Tu direccion en la red local:
echo.
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
  for /f "tokens=1" %%b in ("%%a") do echo      http://%%b:8501
)
echo.
echo 1. Anota una de esas direcciones ^(probá la primera^).
echo 2. En el celular, conectate a la MISMA red WiFi que esta PC.
echo 3. Abri esa direccion en el navegador del celular.
echo 4. Para que quede como una app: menu del navegador ^>
echo    "Agregar a la pantalla de inicio".
echo.
echo Si no carga, es el Firewall de Windows: la primera vez pregunta
echo si permitis el acceso, hay que decir que si ^(red privada^).
echo.
echo ============================================================
echo.

python -m streamlit run app.py --server.address=0.0.0.0 --server.port=8501
pause
