# importar_actividad.py
"""
Importa una actividad desde un archivo (FIT, TCX o GPX) y la convierte al mismo
formato que devuelve Garmin Connect, para poder analizarla con el resto de la app.

Sirve para:
  - Analizar la actividad de otra persona (con sus umbrales, ver la advertencia abajo)
  - Actividades viejas o de otra plataforma que no están en tu Garmin
  - Salidas que por lo que sea no sincronizaron

ADVERTENCIA IMPORTANTE sobre analizar actividades ajenas:
todo el análisis de esta app (zonas, TRIMP, tipo de sesión, adaptaciones) depende
de los umbrales fisiológicos de QUIEN hizo la actividad. Analizar la salida de un
amigo con tus umbrales da resultados sin sentido: si él tiene la frecuencia máxima
más alta, lo que para vos sería zona 5 para él es zona 4. Por eso la app te deja
cargar los umbrales de la otra persona antes de analizar.

Formatos:
  - FIT: el nativo de Garmin, el más completo (pulso, potencia, cadencia, altura)
  - TCX: XML de Garmin, también bastante completo
  - GPX: el más limitado; el pulso viene en una extensión que no todos los
    dispositivos escriben
"""

import io
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------------
# Lectura de cada formato -> lista de muestras {tiempo, fc, potencia, alt, dist, cadencia}
# ---------------------------------------------------------------------------

def _leer_fit(contenido):
    import fitparse

    fit = fitparse.FitFile(io.BytesIO(contenido))
    muestras = []
    for registro in fit.get_messages("record"):
        d = {campo.name: campo.value for campo in registro}
        muestras.append({
            "tiempo": d.get("timestamp"),
            "fc": d.get("heart_rate"),
            "potencia": d.get("power"),
            "alt": d.get("enhanced_altitude", d.get("altitude")),
            "dist": d.get("distance"),
            "cadencia": d.get("cadence"),
        })
    return muestras


def _sin_espacio_nombres(etiqueta):
    return etiqueta.split("}")[-1]


def _leer_tcx(contenido):
    """
    Lee un TCX. Se recorren los hijos directos de cada Trackpoint en vez de
    aplanar todo el nodo: si se aplana, la etiqueta <Value> aparece tanto dentro
    del pulso como en otros lugares y se mezclan los datos.
    """
    raiz = ET.fromstring(contenido)
    muestras = []
    for nodo in raiz.iter():
        if _sin_espacio_nombres(nodo.tag) != "Trackpoint":
            continue
        m = {"tiempo": None, "fc": None, "potencia": None, "alt": None, "dist": None, "cadencia": None}
        for hijo in nodo:
            etiqueta = _sin_espacio_nombres(hijo.tag)
            texto = (hijo.text or "").strip()
            if etiqueta == "Time" and texto:
                m["tiempo"] = texto
            elif etiqueta == "AltitudeMeters" and texto:
                m["alt"] = float(texto)
            elif etiqueta == "DistanceMeters" and texto:
                m["dist"] = float(texto)
            elif etiqueta == "Cadence" and texto:
                m["cadencia"] = int(float(texto))
            elif etiqueta == "HeartRateBpm":
                for sub in hijo:
                    if _sin_espacio_nombres(sub.tag) == "Value" and sub.text:
                        m["fc"] = int(float(sub.text))
            elif etiqueta == "Extensions":
                # La potencia y la cadencia de bici viven acá dentro
                for sub in hijo.iter():
                    et = _sin_espacio_nombres(sub.tag)
                    tx = (sub.text or "").strip()
                    if et == "Watts" and tx:
                        m["potencia"] = float(tx)
                    elif et == "Cadence" and tx and m["cadencia"] is None:
                        m["cadencia"] = int(float(tx))
        muestras.append(m)
    return muestras


def _leer_gpx(contenido):
    """
    Lee un GPX. El pulso, la cadencia y la potencia no son parte del estándar:
    van dentro de <extensions>, con etiquetas propias de cada fabricante. Se
    buscan por nombre ignorando el espacio de nombres.
    """
    raiz = ET.fromstring(contenido)
    muestras = []
    for nodo in raiz.iter():
        if _sin_espacio_nombres(nodo.tag) != "trkpt":
            continue
        m = {"tiempo": None, "fc": None, "potencia": None, "alt": None, "dist": None,
             "cadencia": None, "lat": None, "lon": None}
        try:
            m["lat"] = float(nodo.attrib.get("lat"))
            m["lon"] = float(nodo.attrib.get("lon"))
        except (TypeError, ValueError):
            pass
        for hijo in nodo.iter():
            etiqueta = _sin_espacio_nombres(hijo.tag)
            texto = (hijo.text or "").strip()
            if not texto:
                continue
            if etiqueta == "ele":
                m["alt"] = float(texto)
            elif etiqueta == "time":
                m["tiempo"] = texto
            elif etiqueta == "hr":
                m["fc"] = int(float(texto))
            elif etiqueta == "cad":
                m["cadencia"] = int(float(texto))
            elif etiqueta in ("power", "PowerInWatts"):
                m["potencia"] = float(texto)
        muestras.append(m)
    return muestras


def leer_archivo(nombre, contenido):
    """Detecta el formato por la extensión y devuelve las muestras."""
    n = nombre.lower()
    if n.endswith(".fit"):
        return _leer_fit(contenido), "FIT"
    if n.endswith(".tcx"):
        return _leer_tcx(contenido), "TCX"
    if n.endswith(".gpx"):
        return _leer_gpx(contenido), "GPX"
    raise ValueError(f"No reconozco el formato de '{nombre}'. Necesito un archivo .fit, .tcx o .gpx.")


# ---------------------------------------------------------------------------
# Conversión al formato de actividad de Garmin
# ---------------------------------------------------------------------------

def _segundos_entre(muestras):
    """Duración total en segundos, contando desde la primera a la última muestra."""
    tiempos = [m["tiempo"] for m in muestras if m.get("tiempo")]
    if len(tiempos) < 2:
        return None

    from datetime import datetime

    def parsear(t):
        if isinstance(t, datetime):
            return t
        texto = str(t).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(texto)
        except ValueError:
            return None

    ini, fin = parsear(tiempos[0]), parsear(tiempos[-1])
    if ini and fin:
        return (fin - ini).total_seconds()
    return None


def a_actividad(muestras, nombre_archivo, perfil, zonas_fc):
    """
    Convierte las muestras en el mismo diccionario que devuelve Garmin Connect,
    calculando el tiempo en cada zona a partir del pulso segundo a segundo.

    Calcular las zonas desde las muestras (en vez de estimarlas del promedio, que
    es lo que hace la app cuando Garmin no las manda) es en realidad MÁS preciso:
    acá tenemos el detalle real de toda la sesión.
    """
    from datetime import datetime

    fcs = [m["fc"] for m in muestras if m.get("fc")]
    potencias = [m["potencia"] for m in muestras if m.get("potencia")]
    cadencias = [m["cadencia"] for m in muestras if m.get("cadencia")]
    distancias = [m["dist"] for m in muestras if m.get("dist") is not None]
    alturas = [m["alt"] for m in muestras if m.get("alt") is not None]

    duracion = _segundos_entre(muestras) or len(muestras)

    # Distancia: los FIT y TCX la traen acumulada; los GPX no, así que hay que
    # calcularla sumando la distancia entre coordenadas consecutivas.
    if distancias:
        distancia_m = max(distancias)
    else:
        import ruta
        distancia_m = 0.0
        anterior = None
        for m in muestras:
            if m.get("lat") is None or m.get("lon") is None:
                continue
            if anterior is not None:
                distancia_m += ruta._distancia_haversine(
                    anterior["lat"], anterior["lon"], m["lat"], m["lon"]
                )
            anterior = m

    # Desnivel positivo, con un umbral para no acumular ruido del GPS
    desnivel = 0.0
    if len(alturas) > 1:
        referencia = alturas[0]
        for a in alturas[1:]:
            if a - referencia >= 2:
                desnivel += a - referencia
                referencia = a
            elif a < referencia:
                referencia = a

    # Tiempo en cada zona, contando muestra por muestra
    segundos_por_muestra = duracion / len(muestras) if muestras else 1
    tiempo_zona = {z: 0.0 for z in range(1, 6)}
    for m in muestras:
        fc = m.get("fc")
        if not fc:
            continue
        for z, (lo, hi) in zonas_fc.items():
            if lo <= fc < hi or (z == 5 and fc >= lo):
                tiempo_zona[z] += segundos_por_muestra
                break

    fecha = None
    for m in muestras:
        if m.get("tiempo"):
            t = m["tiempo"]
            fecha = t.strftime("%Y-%m-%d %H:%M:%S") if isinstance(t, datetime) else str(t)[:19].replace("T", " ")
            break
    if not fecha:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    actividad = {
        "activityId": f"import_{abs(hash(nombre_archivo)) % 10**8}",
        "activityName": nombre_archivo.rsplit(".", 1)[0],
        "startTimeLocal": fecha,
        "activityType": {"typeKey": "cycling"},
        "duration": duracion,
        "distance": distancia_m,
        "elevationGain": round(desnivel) if desnivel else None,
        "averageHR": round(sum(fcs) / len(fcs)) if fcs else None,
        "maxHR": max(fcs) if fcs else None,
        "averageBikingCadenceInRevPerMinute": round(sum(cadencias) / len(cadencias)) if cadencias else None,
        "calories": None,
    }

    for z in range(1, 6):
        actividad[f"hrTimeInZone_{z}"] = tiempo_zona[z]

    if potencias:
        actividad["avgPower"] = round(sum(potencias) / len(potencias))
        actividad["maxPower"] = round(max(potencias))
        actividad["normPower"] = _potencia_normalizada(potencias, segundos_por_muestra)

    return actividad


def _potencia_normalizada(potencias, segundos_por_muestra):
    """
    Potencia Normalizada: media móvil de 30 segundos, elevada a la cuarta,
    promediada, y raíz cuarta. Es la fórmula estándar de Coggan, y castiga la
    variabilidad: 200 W constantes y 200 W a los saltos no cuestan lo mismo.
    """
    if not potencias:
        return None
    ventana = max(1, int(30 / max(segundos_por_muestra, 0.1)))
    if len(potencias) < ventana:
        return round(sum(potencias) / len(potencias))

    acumulado = [0.0]
    for p in potencias:
        acumulado.append(acumulado[-1] + p)

    cuartas = []
    for i in range(len(potencias) - ventana + 1):
        media = (acumulado[i + ventana] - acumulado[i]) / ventana
        cuartas.append(media ** 4)

    return round((sum(cuartas) / len(cuartas)) ** 0.25)


def series_desde_muestras(muestras):
    """Devuelve las series segundo a segundo, para la deriva cardíaca y el VAM."""
    return {
        "fc": [m.get("fc") for m in muestras],
        "potencia": [m.get("potencia") for m in muestras],
        "velocidad": [None] * len(muestras),
        "altitud": [m.get("alt") for m in muestras],
    }
