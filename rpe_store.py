# rpe_store.py
"""
Guarda tu percepción de esfuerzo (RPE, escala 1-10) por sesión en un archivo
local, ya que Garmin no expone esto por API - es un dato que solo vos podés
cargar. Persiste entre corridas de la app (queda guardado en data/rpe_guardados.json).
"""

import json
import os

import config

RUTA_ARCHIVO = os.path.join(config.RUTA_DATOS, "rpe_guardados.json")


def _asegurar_carpeta():
    os.makedirs(config.RUTA_DATOS, exist_ok=True)


def cargar_todos():
    if not os.path.exists(RUTA_ARCHIVO):
        return {}
    try:
        with open(RUTA_ARCHIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def obtener(activity_id):
    return cargar_todos().get(str(activity_id))


def guardar(activity_id, valor):
    _asegurar_carpeta()
    datos = cargar_todos()
    datos[str(activity_id)] = valor
    with open(RUTA_ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(datos, f)


def borrar():
    """Elimina todos los RPE guardados."""
    if os.path.exists(RUTA_ARCHIVO):
        os.remove(RUTA_ARCHIVO)
