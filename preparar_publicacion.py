# preparar_publicacion.py
"""
Arma el zip para publicar en GitHub, SIN datos personales.

Genera "garmin_coach.zip" en esta misma carpeta, listo para subir, y verifica que
no lleve nada de la carpeta `data` — donde viven el perfil y la ergoespirometría.
Si esa carpeta llegara a un repositorio público, los datos de salud quedarían a
la vista de cualquiera.

Está escrito en Python y no en el .bat a propósito: la primera versión metía
comandos de PowerShell dentro del .bat y fallaba en silencio, cerrando la ventana
sin decir por qué. En Python se puede probar de verdad y los errores se ven.

Se usa con doble clic en preparar_publicacion.bat, o directamente:
    python preparar_publicacion.py
"""

import json
import os
import sys
import zipfile
from pathlib import Path

# Lo que NO se publica
CARPETAS_EXCLUIDAS = {
    "data",                 # perfil, ergoespirometría y RPE: datos personales
    "__pycache__", ".git", ".idea", ".vscode",
    "build", "dist", "instalador_salida",
}
ARCHIVOS_EXCLUIDOS = {"garmin_coach.zip"}
SUFIJOS_EXCLUIDOS = {".pyc", ".spec"}

NOMBRE_ZIP = "garmin_coach.zip"
RAIZ_EN_ZIP = "garmin_coach"   # el actualizador espera una carpeta raíz


def se_excluye(ruta_relativa):
    partes = ruta_relativa.parts
    if set(partes) & CARPETAS_EXCLUIDAS:
        return True
    if any(p.startswith("_respaldo_") for p in partes):
        return True
    if ruta_relativa.name in ARCHIVOS_EXCLUIDOS:
        return True
    if ruta_relativa.suffix.lower() in SUFIJOS_EXCLUIDOS:
        return True
    return False


def verificar_versiones(base):
    """Avisa si version.py y version.json no coinciden, que es el error más común."""
    try:
        texto = (base / "version.py").read_text(encoding="utf-8")
        v_py = texto.split('VERSION = "')[1].split('"')[0]
    except Exception:
        v_py = None
    try:
        v_json = json.loads((base / "version.json").read_text(encoding="utf-8")).get("version")
    except Exception:
        v_json = None

    print(f"  version.py   dice: {v_py or 'no pude leerlo'}")
    print(f"  version.json dice: {v_json or 'no pude leerlo'}")
    if v_py and v_json and v_py != v_json:
        print()
        print("  ATENCION: los numeros NO coinciden.")
        print("  El actualizador no va a detectar el cambio hasta que sean iguales.")
        return False
    if v_py and v_json:
        print("  Coinciden, bien.")
    return True


def armar(base):
    salida = base / NOMBRE_ZIP
    if salida.exists():
        salida.unlink()

    incluidos = []
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        for raiz, carpetas, archivos in os.walk(base):
            raiz_p = Path(raiz)
            rel_carpeta = raiz_p.relative_to(base)
            # Podar carpetas excluidas para no recorrerlas
            carpetas[:] = [
                c for c in carpetas
                if c not in CARPETAS_EXCLUIDAS and not c.startswith("_respaldo_")
            ]
            if rel_carpeta != Path(".") and se_excluye(rel_carpeta):
                continue
            for a in archivos:
                rel = (rel_carpeta / a) if rel_carpeta != Path(".") else Path(a)
                if se_excluye(rel):
                    continue
                z.write(raiz_p / a, str(Path(RAIZ_EN_ZIP) / rel))
                incluidos.append(str(rel))
    return salida, incluidos


def verificar_zip(ruta):
    """Confirma que el zip no lleve datos personales y que sirva para actualizar."""
    with zipfile.ZipFile(ruta) as z:
        nombres = z.namelist()

    personales = [
        n for n in nombres
        if "/data/" in n.replace("\\", "/") or n.endswith("perfil.json")
        or n.endswith("rpe_guardados.json")
    ]
    esenciales = ["app.py", "metrics.py", "version.py", "version.json"]
    faltantes = [e for e in esenciales if not any(n.endswith("/" + e) for n in nombres)]

    return {"personales": personales, "faltantes": faltantes, "total": len(nombres)}


def main():
    base = Path(__file__).resolve().parent
    print("Verificando la version...")
    verificar_versiones(base)

    print()
    print("Armando el zip sin datos personales...")
    ruta, incluidos = armar(base)

    r = verificar_zip(ruta)
    print()
    print("-" * 60)
    if r["personales"]:
        # Se borra el zip: si queda en la carpeta, tarde o temprano alguien lo sube.
        # Es mejor no tener archivo que tener uno con datos de salud adentro.
        ruta.unlink(missing_ok=True)
        print("ATENCION: el zip iba a contener datos personales.")
        for p in r["personales"]:
            print("   ", p)
        print()
        print("BORRE el zip para que no puedas subirlo por error.")
        print("Avisale a quien te dio la app antes de publicar nada.")
        return 1

    if r["faltantes"]:
        ruta.unlink(missing_ok=True)
        print("El zip quedo incompleto, faltan archivos esenciales:")
        for f in r["faltantes"]:
            print("   ", f)
        print()
        print("Borre el zip. Fijate que no falten archivos en la carpeta del proyecto.")
        return 1

    print(f"LISTO: {NOMBRE_ZIP}  ({r['total']} archivos)")
    print()
    print("  OK: no contiene la carpeta data, ni el perfil, ni los RPE.")
    print("  OK: incluye el codigo completo y la informacion de version.")
    print()
    print("Ahora subilo a GitHub, reemplazando el anterior si ya habia uno.")
    print("-" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
