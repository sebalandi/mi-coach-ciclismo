# perfil_store.py
"""
Guarda el perfil del usuario (datos personales + ergoespirometría) en un archivo
local, para que cada persona cargue los suyos desde la app sin tocar el código.

El archivo vive en data/perfil.json y NO se comparte al distribuir la app:
cada instalación arranca vacía y cada uno carga sus propios datos.
"""

import json
import os

import config

RUTA_ARCHIVO = os.path.join(config.RUTA_DATOS, "perfil.json")


def cargar():
    """Devuelve el perfil guardado, o {} si todavía no hay ninguno."""
    if not os.path.exists(RUTA_ARCHIVO):
        return {}
    try:
        with open(RUTA_ARCHIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def guardar(perfil):
    """Guarda el perfil completo (pisa el anterior)."""
    os.makedirs(config.RUTA_DATOS, exist_ok=True)
    # No guardamos claves internas de Streamlit ni nada que no sea del perfil
    limpio = {k: v for k, v in perfil.items() if not k.startswith("_")}
    with open(RUTA_ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(limpio, f, ensure_ascii=False, indent=2)


def borrar():
    """Elimina el perfil guardado (útil antes de compartir la app con alguien)."""
    if os.path.exists(RUTA_ARCHIVO):
        os.remove(RUTA_ARCHIVO)


def perfil_efectivo():
    """
    Combina los valores por defecto de config.PERFIL con lo que el usuario haya
    guardado. Lo guardado siempre tiene prioridad.
    """
    perfil = dict(config.PERFIL)
    perfil.update(cargar())
    return perfil
