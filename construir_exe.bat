@echo off
REM Paso 1 de 2: arma la aplicacion empaquetada de "Mi Coach de Ciclismo".
REM Se corre en tu PC con Windows y tarda varios minutos. El resultado queda en
REM dist\MiCoachDeCiclismo\ y ya se puede probar con doble clic.
REM Despues, para armar el instalador que le pasas a tus amigos: construir_instalador.bat

cd /d "%~dp0"

echo Limpiando construcciones anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist MiCoachDeCiclismo.spec del /q MiCoachDeCiclismo.spec

echo.
echo Instalando dependencias del proyecto...
python -m pip install -r requirements.txt

echo.
echo Instalando herramientas para armar el ejecutable...
python -m pip install -r requirements-exe.txt

echo.
echo Armando la aplicacion (varios minutos, no cierres esta ventana)...
REM Sobre las opciones:
REM   --add-data     copia los .py del proyecto para que Streamlit los encuentre al correr
REM   --hidden-import ademas los analiza, para que PyInstaller traiga SUS dependencias.
REM                  Sin esto faltarian librerias como plotly, que solo usa app.py y que
REM                  PyInstaller no puede descubrir solo (app.py viaja como archivo de datos,
REM                  no como codigo que el analiza).
REM   --collect-all  trae la libreria entera, incluidos sus archivos de datos
python -m PyInstaller --noconsole --name "MiCoachDeCiclismo" ^
  --add-data "app.py;." ^
  --add-data "config.py;." ^
  --add-data "metrics.py;." ^
  --add-data "feedback.py;." ^
  --add-data "coach.py;." ^
  --add-data "garmin_client.py;." ^
  --add-data "demo_data.py;." ^
  --add-data "rpe_store.py;." ^
  --add-data "ruta.py;." ^
  --add-data "importar_actividad.py;." ^
  --add-data "hrv.py;." ^
  --add-data "version.py;." ^
  --add-data "actualizador.py;." ^
  --add-data "perfil_store.py;." ^
  --add-data ".streamlit\config.toml;.streamlit" ^
  --hidden-import config ^
  --hidden-import metrics ^
  --hidden-import feedback ^
  --hidden-import coach ^
  --hidden-import garmin_client ^
  --hidden-import demo_data ^
  --hidden-import rpe_store ^
  --hidden-import ruta ^
  --hidden-import importar_actividad ^
  --hidden-import hrv ^
  --hidden-import version ^
  --hidden-import actualizador ^
  --hidden-import perfil_store ^
  --collect-all streamlit ^
  --collect-all plotly ^
  --collect-all pandas ^
  --collect-all garminconnect ^
  --collect-all gpxpy ^
  --collect-all fitparse ^
  --collect-all garth ^
  launcher.py

echo.
echo ------------------------------------------------------------
if exist "dist\MiCoachDeCiclismo\MiCoachDeCiclismo.exe" (
  echo LISTO. Probala con doble clic en:
  echo     dist\MiCoachDeCiclismo\MiCoachDeCiclismo.exe
  echo.
  echo La PRIMERA vez puede tardar entre 20 y 40 segundos en abrir.
  echo Si algo falla, el detalle queda en:
  echo     %%USERPROFILE%%\.mi_coach_ciclismo\arranque.log
  echo.
  echo Para armar el instalador que le pasas a tus amigos:
  echo     construir_instalador.bat
) else (
  echo ALGO FALLO: no se genero el ejecutable.
  echo Revisa los mensajes de error de mas arriba.
)
echo ------------------------------------------------------------
pause
