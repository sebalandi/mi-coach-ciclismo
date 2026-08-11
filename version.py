# version.py
"""
Versión del proyecto. La usa el actualizador para saber si hay algo más nuevo.

Al publicar una versión hay que subir este número Y el del archivo version.json
que queda en el servidor. Si no coinciden, el actualizador no detecta el cambio.
"""

VERSION = "1.0.0"

# Dónde consultar si hay una versión más nueva. Tiene que apuntar a un archivo
# JSON con esta forma:
#   {"version": "1.1.0",
#    "zip": "https://.../garmin_coach.zip",
#    "notas": "Qué cambió",
#    "requiere_librerias": false}
#
# Lo más simple es un repositorio público de GitHub: subís el proyecto y usás la
# URL "raw" del archivo. Ver la sección de actualizaciones del README.
URL_VERSION = "https://raw.githubusercontent.com/sebalandi/mi-coach-ciclismo/main/version.json"


def como_tupla(texto):
    """Convierte '1.2.10' en (1, 2, 10) para poder comparar versiones."""
    try:
        return tuple(int(x) for x in str(texto).strip().split("."))
    except (ValueError, AttributeError):
        return (0,)
