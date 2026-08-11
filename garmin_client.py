# garmin_client.py
"""
Conexión con Garmin Connect.

Usa la librería no oficial `garminconnect` (github.com/cyberjunky/python-garminconnect),
que es la que usan la mayoría de las apps de terceros para leer tus propios datos.
IMPORTANTE - esto NO es una API oficial de Garmin:
  - Funciona iniciando sesión con tu usuario y contraseña, igual que en la app o la web.
  - Garmin puede cambiar su backend en cualquier momento y romper la librería.
    Si un día deja de funcionar, probá actualizarla: pip install -U garminconnect

Alternativa 100% oficial y sin depender de esto: exportar manualmente los archivos
.FIT de cada actividad desde Garmin Connect y analizarlos con la librería `fitparse`.
Es más manual (tenés que descargar cada actividad a mano) pero no depende de una
librería no oficial.

--- Sobre recordar la sesión ---
Cuando pedís que la app recuerde tu acceso, NO se guarda tu contraseña en ningún
lado. Lo que se guarda son los tokens de sesión que devuelve Garmin al entrar
(el mismo mecanismo que usa la app de Garmin en tu celular para no pedirte la
clave cada vez).

Esos tokens se guardan en tu carpeta de usuario, FUERA de la carpeta del
proyecto: así, si comprimís el proyecto para compartirlo con alguien, tu acceso
a Garmin no viaja adentro. Los tokens dan acceso a tu cuenta, así que tratalos
como si fueran la contraseña: no los copies ni los compartas.
"""

from pathlib import Path
import shutil

import garminconnect

# Fuera de la carpeta del proyecto, a propósito (ver nota de arriba)
RUTA_SESION = Path.home() / ".mi_coach_ciclismo" / "garmin"


def hay_sesion_guardada():
    """True si ya hay una sesión guardada de un ingreso anterior."""
    return RUTA_SESION.exists() and any(RUTA_SESION.iterdir())


def olvidar_sesion():
    """Borra la sesión guardada. La próxima vez va a pedir email y contraseña."""
    if RUTA_SESION.exists():
        shutil.rmtree(RUTA_SESION, ignore_errors=True)


def conectar_con_sesion_guardada():
    """
    Entra usando los tokens guardados, sin necesidad de la contraseña.
    Lanza una excepción si no hay sesión guardada o si ya venció.
    """
    if not hay_sesion_guardada():
        raise RuntimeError("No hay una sesión guardada.")
    client = garminconnect.Garmin()
    client.login(str(RUTA_SESION))
    return client


def conectar(email, password, recordar=False):
    """
    Inicia sesión con email y contraseña.

    Si recordar=True, guarda los tokens de la sesión para que la próxima vez no
    haga falta la contraseña. La librería se encarga de escribirlos cuando se le
    pasa la ruta al hacer login.
    """
    client = garminconnect.Garmin(email, password)
    if recordar:
        RUTA_SESION.mkdir(parents=True, exist_ok=True)
        client.login(str(RUTA_SESION))
    else:
        client.login()
    return client


def obtener_actividades(client, cantidad=200):
    """Trae las últimas `cantidad` actividades (de cualquier tipo)."""
    return client.get_activities(0, cantidad)


def obtener_detalle_actividad(client, activity_id):
    """
    Trae el detalle segundo a segundo de UNA actividad puntual (FC, potencia,
    velocidad a lo largo del tiempo). Se usa bajo demanda, solo cuando el
    usuario pide analizar la deriva cardíaca o la curva de potencia - no se
    trae para todas las actividades porque es una llamada pesada.
    """
    return client.get_activity_details(activity_id)


def obtener_hrv(client, fecha):
    """
    Intenta traer el resumen de HRV (Heart Rate Variability) de un día puntual.
    Esto depende de que tu reloj lo reporte (no todos los modelos lo hacen) y
    de la versión exacta de la librería garminconnect - por eso está envuelto
    en un try/except: si falla, devuelve None en vez de romper la app.
    """
    try:
        return client.get_hrv_data(fecha.isoformat())
    except Exception:
        return None


def obtener_body_battery(client, fecha_inicio, fecha_fin):
    """Igual que obtener_hrv: intenta traer Body Battery, devuelve None si falla."""
    try:
        return client.get_body_battery(fecha_inicio.isoformat(), fecha_fin.isoformat())
    except Exception:
        return None
