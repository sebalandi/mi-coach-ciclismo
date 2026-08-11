# actualizador.py
"""
Busca y aplica actualizaciones del proyecto.

--- Cómo funciona ---
Consulta un archivo version.json publicado en internet, compara el número con el
que tiene instalado, y si hay uno más nuevo descarga el zip y reemplaza los
archivos de código. Nunca toca la carpeta de datos.

--- Los dos modos, y por qué se comportan distinto ---

Corriendo desde el código (iniciar_app.bat): la actualización es completa. Se
descargan los archivos nuevos y quedan aplicados al reiniciar.

Corriendo como .exe: solo avisa que hay una versión nueva y da el enlace. No
puede actualizarse solo porque PyInstaller descomprime la aplicación en una
carpeta temporal que Windows borra al cerrar; escribir ahí no serviría de nada.
Para actualizar un .exe hay que instalar el nuevo.

--- Seguridad al reemplazar ---
Antes de tocar nada se verifica que el zip descargado sea válido y que contenga
los archivos esperados. Los archivos actuales se guardan en una copia de
respaldo, así que si algo sale mal se puede volver atrás. Y la carpeta `data`
queda siempre fuera del proceso.
"""

import json
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import version

# Extensiones que se actualizan. Deliberadamente NO incluye .json, para que
# ninguna actualización pueda sobrescribir el perfil ni los datos del usuario.
EXTENSIONES = {".py", ".bat", ".toml", ".md", ".txt", ".iss"}

# Carpetas que nunca se tocan
INTOCABLES = {"data", "__pycache__", "build", "dist", "instalador_salida"}

TIEMPO_ESPERA = 15


def corriendo_como_exe():
    return getattr(sys, "frozen", False)


def carpeta_proyecto():
    if corriendo_como_exe():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def consultar(url=None):
    """
    Pregunta si hay una versión más nueva.

    Devuelve un dict con el resultado. Nunca lanza excepciones: si no hay red o
    la respuesta es inválida, lo informa en el propio resultado, porque una app
    no debería romperse por no poder consultar actualizaciones.
    """
    url = url or version.URL_VERSION
    if not url:
        return {"estado": "sin_configurar"}

    try:
        with urllib.request.urlopen(url, timeout=TIEMPO_ESPERA) as r:
            datos = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"estado": "error", "detalle": str(e)}

    remota = datos.get("version")
    if not remota:
        return {"estado": "respuesta_invalida"}

    hay_nueva = version.como_tupla(remota) > version.como_tupla(version.VERSION)
    return {
        "estado": "nueva" if hay_nueva else "al_dia",
        "version_local": version.VERSION,
        "version_remota": remota,
        "zip": datos.get("zip"),
        "notas": datos.get("notas", ""),
        "requiere_librerias": bool(datos.get("requiere_librerias")),
    }


def _archivos_del_zip(zf):
    """
    Los archivos del zip que corresponde actualizar, con su ruta relativa.

    Los zips generados con `zip -r garmin_coach .` traen todo dentro de una
    carpeta raíz, así que se descarta ese primer nivel.
    """
    salida = []
    for nombre in zf.namelist():
        if nombre.endswith("/"):
            continue
        partes = Path(nombre).parts
        relativa = Path(*partes[1:]) if len(partes) > 1 else Path(nombre)
        if not relativa.parts:
            continue
        if set(relativa.parts) & INTOCABLES:
            continue
        if relativa.suffix.lower() not in EXTENSIONES:
            continue
        salida.append((nombre, relativa))
    return salida


def aplicar(url_zip, destino=None):
    """
    Descarga el zip y reemplaza los archivos de código.

    Devuelve {"ok": bool, "mensaje": str, "respaldo": ruta|None, "archivos": n}
    """
    if corriendo_como_exe():
        return {
            "ok": False,
            "mensaje": (
                "Esta versión corre como aplicación instalada y no puede actualizarse sola. "
                "Descargá e instalá la versión nueva."
            ),
            "respaldo": None, "archivos": 0,
        }

    destino = Path(destino or carpeta_proyecto())

    try:
        with urllib.request.urlopen(url_zip, timeout=60) as r:
            contenido = r.read()
    except Exception as e:
        return {"ok": False, "mensaje": f"No pude descargar la actualización: {e}",
                "respaldo": None, "archivos": 0}

    tmp = Path(tempfile.mkdtemp(prefix="coach_upd_"))
    ruta_zip = tmp / "nuevo.zip"
    ruta_zip.write_bytes(contenido)

    # Verificar ANTES de tocar nada: que sea un zip válido y que traiga lo esperado
    try:
        with zipfile.ZipFile(ruta_zip) as zf:
            if zf.testzip() is not None:
                raise zipfile.BadZipFile("el archivo llegó incompleto")
            archivos = _archivos_del_zip(zf)
            nombres = {str(rel) for _, rel in archivos}
            if "app.py" not in nombres or "metrics.py" not in nombres:
                return {"ok": False, "archivos": 0, "respaldo": None,
                        "mensaje": "El zip descargado no parece ser el proyecto (no encontré app.py). "
                                   "No cambié nada."}

            # Respaldo de lo actual, para poder volver atrás
            respaldo = destino / f"_respaldo_{version.VERSION}"
            if respaldo.exists():
                shutil.rmtree(respaldo, ignore_errors=True)
            respaldo.mkdir(parents=True, exist_ok=True)
            for _, rel in archivos:
                actual = destino / rel
                if actual.exists():
                    (respaldo / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(actual, respaldo / rel)

            # Recién ahora se reemplaza
            for nombre, rel in archivos:
                salida = destino / rel
                salida.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(nombre) as origen, open(salida, "wb") as dest:
                    shutil.copyfileobj(origen, dest)

    except zipfile.BadZipFile as e:
        return {"ok": False, "mensaje": f"El archivo descargado está dañado: {e}. No cambié nada.",
                "respaldo": None, "archivos": 0}
    except Exception as e:
        return {"ok": False, "mensaje": f"Falló la actualización: {e}", "respaldo": None, "archivos": 0}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return {
        "ok": True,
        "archivos": len(archivos),
        "respaldo": str(respaldo),
        "mensaje": f"Actualicé {len(archivos)} archivos. Cerrá y volvé a abrir la app para usarla.",
    }


def revertir(respaldo, destino=None):
    """Vuelve a la versión anterior usando la copia de respaldo."""
    respaldo = Path(respaldo)
    destino = Path(destino or carpeta_proyecto())
    if not respaldo.exists():
        return {"ok": False, "mensaje": "No encontré la copia de respaldo."}
    n = 0
    for raiz, _, archivos in os.walk(respaldo):
        for a in archivos:
            origen = Path(raiz) / a
            rel = origen.relative_to(respaldo)
            (destino / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origen, destino / rel)
            n += 1
    return {"ok": True, "mensaje": f"Restauré {n} archivos de la versión anterior."}
