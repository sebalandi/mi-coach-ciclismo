# verificar_secciones.py
"""
Comprueba que ninguna sección de la app desaparezca sin explicación.

Existe porque el mismo error apareció tres veces: el botón del VAM se ocultaba
en recorridos llanos, la sección de potencia desaparecía sin potenciómetro, y la
distribución de intensidad no se mostraba sin ergoespirometría. En los tres casos
el usuario no tenía forma de saber si faltaba un dato, si algo estaba roto, o si
había que configurar algo.

La regla: si una sección puede no mostrarse, tiene que existir una rama que
explique por qué. Este script busca los `eyebrow(...)` gobernados por una
condición y verifica que haya una rama alternativa.

Correr con:  python verificar_secciones.py
"""

import re
import sys

# Secciones cuya ausencia es legítima y no necesita explicación: reflejan
# actividades o deportes que directamente no están en juego. Anunciar "no hiciste
# gimnasio" o "esto es de running y estás en ciclismo" sería ruido.
EXENTAS = {
    "Gimnasio",
    "Volumen semanal y riesgo de lesión",   # solo aplica a running
    "Tiempos que podrías hacer hoy",        # solo aplica a running
}

# Secciones cuya ausencia YA está explicada por otra sección que sí se muestra.
# Sin este mapeo el chequeo daría falsos positivos, y un chequeo ruidoso se ignora.
CUBIERTAS_POR = {
    "Curva de potencia · CP y W'": "Potencia",
    "Sesiones con potenciómetro": "Potencia",
}


def main():
    lineas = open("app.py", encoding="utf-8").read().split("\n")
    titulos_con_condicion = {}

    for i, l in enumerate(lineas):
        if not l.strip().startswith("eyebrow("):
            continue
        indent = len(l) - len(l.lstrip())
        condicion = None
        for j in range(i - 1, max(0, i - 12), -1):
            lj = lineas[j]
            if lj.strip().startswith(("if ", "elif ")) and (len(lj) - len(lj.lstrip())) < indent:
                condicion = lj.strip()
                break
        m = re.search(r'eyebrow\(\s*"([^"]+)"', l)
        titulo = m.group(1) if m else l.strip()[:40]
        if condicion:
            titulos_con_condicion.setdefault(titulo, []).append(condicion)

    # Un título que aparece dos veces con condiciones opuestas está cubierto:
    # una rama muestra la sección y la otra explica por qué está vacía.
    texto = "\n".join(lineas)
    sin_cubrir = []
    for titulo, condiciones in titulos_con_condicion.items():
        if titulo in EXENTAS:
            continue
        if titulo in CUBIERTAS_POR:
            # Válido solo si la sección que la cubre realmente existe en el código
            if f'eyebrow("{CUBIERTAS_POR[titulo]}")' in texto:
                continue
        apariciones = texto.count(f'eyebrow("{titulo}")')
        tiene_rama_negativa = any(" not " in c for c in condiciones)
        if apariciones < 2 and not tiene_rama_negativa:
            sin_cubrir.append((titulo, condiciones[0]))

    print(f"{'sección':50} estado")
    print("-" * 78)
    for titulo, condiciones in sorted(titulos_con_condicion.items()):
        if titulo in EXENTAS:
            estado = "exenta — no aplica al contexto"
        elif titulo in CUBIERTAS_POR:
            estado = f'cubierta por "{CUBIERTAS_POR[titulo]}"'   
        elif any(t == titulo for t, _ in sin_cubrir):
            estado = "SE OCULTA SIN EXPLICAR"
        else:
            estado = "OK — tiene rama que explica"
        print(f"{titulo[:50]:50} {estado}")

    print()
    print("Secciones que desaparecen sin explicación:", len(sin_cubrir))
    for titulo, cond in sin_cubrir:
        print(f"  - {titulo}   (gobernada por: {cond[:60]})")
    return 1 if sin_cubrir else 0


def verificar_duplicados():
    """
    Detecta bloques repetidos en app.py.

    Existe porque una edición mal hecha llegó a duplicar 300 líneas enteras: dos
    copias de las secciones de running, recorrido, gráficos y sesiones. La app
    seguía compilando y la mitad funcionaba, así que el síntoma visible fue un
    error lateral sobre identificadores repetidos, no la duplicación en sí.
    """
    lineas = open("app.py", encoding="utf-8").read().split("\n")
    encabezados = [l.strip() for l in lineas if l.startswith("# ---------------- ")]
    repetidos = {e for e in encabezados if encabezados.count(e) > 1}

    # Los widgets sin clave propia también se duplican en silencio
    import re
    sin_clave = []
    for tipo in ("file_uploader", "selectbox", "radio", "slider"):
        llamadas = re.findall(rf"st\.{tipo}\((.*?)\)", "\n".join(lineas), re.S)
        etiquetas = [c.split(",")[0].strip() for c in llamadas]
        for e in set(etiquetas):
            if etiquetas.count(e) > 1 and "key=" not in " ".join(llamadas):
                sin_clave.append(f"{tipo}: {e[:40]}")

    print()
    print("Secciones duplicadas:", sorted(repetidos) or "ninguna")
    print("Widgets repetidos sin clave propia:", sorted(set(sin_clave)) or "ninguno")
    return 1 if (repetidos or sin_clave) else 0


if __name__ == "__main__":
    sys.exit(main() + verificar_duplicados())
