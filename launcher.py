# launcher.py
"""
Punto de entrada para el ejecutable (.exe) armado con PyInstaller + pywebview.

Arranca el servidor de Streamlit y abre una ventana nativa de Windows apuntando
a esa dirección, sin barra de direcciones ni pinta de navegador.

Esto NO es para correr la app normalmente (para eso: iniciar_app.bat o
`streamlit run app.py`). Es solo el punto de entrada que usa PyInstaller.

--- Por qué está escrito así ---
La primera versión usaba `stcli.main()` y esperaba 3 segundos fijos antes de
abrir la ventana. Empaquetado eso fallaba: la ventana abría y mostraba "no se
puede acceder a esta página" porque el servidor todavía no existía. Tres
cambios lo resuelven:

  1. Se usa `bootstrap.run()` en vez de la línea de comandos de Streamlit. La
     versión de línea de comandos está pensada para una terminal y no arranca
     bien dentro de un ejecutable.
  2. En vez de esperar un tiempo fijo, se consulta el puerto hasta que responde.
     Empaquetado, Streamlit puede tardar 20 o 30 segundos la primera vez -
     bastante más que los 3 segundos que esperaba antes.
  3. Todo queda registrado en un archivo de texto. Como el ejecutable se arma
     sin consola, sin ese registro cualquier falla es invisible.
"""

import os
import socket
import sys
import threading
import time
import traceback
from pathlib import Path

# Marca de versión del lanzador. Queda registrada al arrancar para poder saber,
# mirando el log, si el ejecutable que corrió es el actual o uno viejo sin
# recompilar - que es un enredo fácil de tener: cambiar el código no actualiza
# el .exe hasta que se vuelve a correr construir_exe.bat.
VERSION_LANZADOR = "2026-08-06 · arreglo de developmentMode"

PUERTO = 8765
ESPERA_MAXIMA_SEG = 90

RUTA_LOG = Path.home() / ".mi_coach_ciclismo" / "arranque.log"


def registrar(mensaje):
    """Deja constancia en un archivo, ya que el ejecutable no tiene consola."""
    try:
        RUTA_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(RUTA_LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {mensaje}\n")
    except Exception:
        pass


def ruta_base():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS  # carpeta temporal donde PyInstaller extrae los archivos
    return os.path.dirname(os.path.abspath(__file__))


def puerto_responde(puerto):
    """True si ya hay algo escuchando en ese puerto."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", puerto)) == 0


def arrancar_streamlit():
    try:
        from streamlit.web import bootstrap

        # Streamlit instala manejadores de señales al arrancar, y Python solo lo
        # permite en el hilo principal. Como acá corre en un hilo secundario (el
        # principal lo necesita la ventana), se anula ese paso. Lo único que se
        # pierde es el apagado ordenado con Ctrl+C, que en una app con ventana no
        # se usa: se cierra cerrando la ventana.
        bootstrap._set_up_signal_handler = lambda *a, **k: None

        from streamlit import config as _config

        base = ruta_base()
        app_path = os.path.abspath(os.path.join(base, "app.py"))
        registrar(f"Arrancando Streamlit desde {app_path}")
        os.chdir(base)

        opciones = {
            # Esta primera opción es imprescindible dentro del ejecutable.
            # Streamlit se considera "en modo desarrollo" cuando su propia ruta
            # no contiene site-packages, y empaquetado sus archivos quedan en
            # _internal\streamlit\, así que se activa solo. En ese modo se niega
            # a aceptar un puerto propio y aborta con un error. Corriendo de la
            # forma normal esto no pasa, que es justo por qué el problema solo
            # aparecía en el .exe.
            "global.developmentMode": False,
            "server.port": PUERTO,
            "server.headless": True,
            "browser.gatherUsageStats": False,
            "theme.base": "light",
            "theme.primaryColor": "#2D4A7C",
            "theme.backgroundColor": "#FBFCFD",
            "theme.secondaryBackgroundColor": "#FFFFFF",
            "theme.textColor": "#131A22",
        }

        # Estos dos pasos previos son los que hace `streamlit run` por dentro.
        # Sin ellos las opciones se ignoran: la primera prueba arrancó en el
        # puerto 8501 en vez del que le pedimos, y la ventana quedaba mirando
        # un puerto vacío.
        _config._main_script_path = app_path
        bootstrap.load_config_options(flag_options=opciones)

        bootstrap.run(app_path, is_hello=False, args=[], flag_options=opciones)
    except Exception:
        registrar("FALLO el arranque de Streamlit:\n" + traceback.format_exc())


def main():
    registrar(f"=== Mi Coach de Ciclismo: iniciando (lanzador {VERSION_LANZADOR}) ===")

    hilo = threading.Thread(target=arrancar_streamlit, daemon=True)
    hilo.start()

    # Esperar a que el servidor conteste de verdad, en vez de asumir un tiempo fijo
    inicio = time.time()
    listo = False
    while time.time() - inicio < ESPERA_MAXIMA_SEG:
        if puerto_responde(PUERTO):
            registrar(f"Servidor listo en {time.time() - inicio:.1f} s")
            listo = True
            break
        time.sleep(0.5)

    if not listo:
        registrar(f"El servidor no respondio en {ESPERA_MAXIMA_SEG} s.")
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                "No pude iniciar la aplicacion.\n\n"
                f"El detalle quedo en:\n{RUTA_LOG}\n\n"
                "Pasale ese archivo a quien te compartio la app.",
                "Mi Coach de Ciclismo",
                0x10,
            )
        except Exception:
            pass
        return

    try:
        import webview
        webview.create_window(
            "Mi Coach de Ciclismo", f"http://localhost:{PUERTO}", width=1300, height=850
        )
        webview.start()
    except Exception:
        # Si la ventana nativa falla, al menos abrimos el navegador
        registrar("La ventana nativa fallo, abro el navegador:\n" + traceback.format_exc())
        import webbrowser
        webbrowser.open(f"http://localhost:{PUERTO}")
        while True:
            time.sleep(3600)


if __name__ == "__main__":
    main()
