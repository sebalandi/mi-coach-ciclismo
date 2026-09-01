# version.py
"""
Versión del proyecto. La usa el actualizador para saber si hay algo más nuevo.

Al publicar una versión hay que subir este número Y el del archivo version.json
que queda en el servidor. Si no coinciden, el actualizador no detecta el cambio.
"""

VERSION = "1.3.0"

# Dónde consultar si hay una versión más nueva. Tiene que apuntar a un archivo
# JSON con esta forma:
#   {"version": "1.3.0",
#    "zip": "https://.../garmin_coach.zip",
#    "notas": "Qué cambió",
#    "requiere_librerias": false}
#
# Lo más simple es un repositorio público de GitHub: subís el proyecto y usás la
# URL "raw" del archivo. Ver la sección de actualizaciones del README.
# Dejar vacío está bien: lo normal es configurarlo desde la propia aplicación
# (panel izquierdo, ACTUALIZACIONES), que lo guarda junto al resto del perfil.
# Editar esta línea a mano solo hace falta si querés que la app venga ya
# configurada para todos los que la instalen.
URL_VERSION = ""


def url_efectiva(perfil=None):
    """
    De dónde consultar las actualizaciones.

    Prioridad: lo que el usuario cargó en la app, y si no hay nada, lo que esté
    escrito acá arriba. Se hace así para que nadie tenga que editar código: pedir
    que alguien abra un .py y cambie una línea es una forma segura de que la
    función no se use nunca.
    """
    if perfil:
        desde_perfil = (perfil.get("url_actualizaciones") or "").strip()
        if desde_perfil:
            return desde_perfil
    return URL_VERSION.strip()


def como_tupla(texto):
    """Convierte '1.2.10' en (1, 2, 10) para poder comparar versiones."""
    try:
        return tuple(int(x) for x in str(texto).strip().split("."))
    except (ValueError, AttributeError):
        return (0,)
