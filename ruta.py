# ruta.py
"""
Lectura y análisis de recorridos de carrera (archivos GPX o TCX).

Lo que hace, en orden de confiabilidad:

  1. GEOMETRÍA (muy confiable): distancia, desnivel, perfil de altimetría y
     detección de las subidas importantes. Esto es pura matemática sobre las
     coordenadas del archivo, no hay nada que estimar.

  2. EXIGENCIA (razonablemente confiable): cuántos vatios por kilo pide cada
     subida, y qué porcentaje de tu umbral representa. Sale de un modelo físico
     estándar (gravedad + rodadura + aire).

  3. TIEMPO ESTIMADO (poco confiable, tomalo con pinzas): cuánto tardarías. El
     modelo físico necesita suponer tu posición aerodinámica, la superficie, el
     viento y - en MTB - tu habilidad técnica bajando. Cualquiera de esos puede
     mover el resultado un 15% o más.

Los archivos GPX de recorridos vienen a veces sin altimetría o con una altimetría
muy ruidosa (los GPS son bastante malos midiendo altura). Por eso el perfil se
suaviza antes de calcular nada.
"""

import math

import gpxpy

# --- Constantes del modelo físico ---
G = 9.80665           # gravedad (m/s2)
RHO = 1.225           # densidad del aire a nivel del mar (kg/m3)

# Valores típicos por tipo de bici. Son promedios razonables, no mediciones tuyas.
PERFILES_BICI = {
    "Ruta": {
        "peso_bici": 8.5,
        "crr": 0.005,      # resistencia a la rodadura, asfalto bueno
        "cda": 0.32,       # área frontal efectiva, manos en el manillar
        "eficiencia_bajada": 0.95,
    },
    "MTB": {
        "peso_bici": 13.0,
        "crr": 0.015,      # tierra y ripio: mucho más rodadura que el asfalto
        "cda": 0.42,       # posición más erguida
        "eficiencia_bajada": 0.70,   # en MTB bajás mucho más lento que lo que dice la física
    },
}


# ---------------------------------------------------------------------------
# Lectura del archivo
# ---------------------------------------------------------------------------

def _distancia_haversine(lat1, lon1, lat2, lon2):
    """Distancia en metros entre dos coordenadas."""
    R = 6371000
    f1, f2 = math.radians(lat1), math.radians(lat2)
    df = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(df / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def leer_recorrido(contenido):
    """
    Lee un GPX (texto o bytes) y devuelve los puntos del recorrido con su
    distancia acumulada. Sirve tanto para rutas planificadas (<rte>) como para
    tracks grabados (<trk>).
    """
    if isinstance(contenido, bytes):
        contenido = contenido.decode("utf-8", errors="ignore")
    gpx = gpxpy.parse(contenido)

    crudos = []
    for track in gpx.tracks:
        for seg in track.segments:
            crudos.extend(seg.points)
    for ruta in gpx.routes:
        crudos.extend(ruta.points)
    if not crudos and gpx.waypoints:
        crudos = gpx.waypoints

    if len(crudos) < 2:
        raise ValueError(
            "No encontré un recorrido dentro del archivo. "
            "Fijate que sea el GPX del recorrido y no una foto o un PDF."
        )

    puntos = []
    acumulada = 0.0
    anterior = None
    for p in crudos:
        if p.latitude is None or p.longitude is None:
            continue
        if anterior is not None:
            acumulada += _distancia_haversine(anterior.latitude, anterior.longitude, p.latitude, p.longitude)
        puntos.append({
            "lat": p.latitude,
            "lon": p.longitude,
            "alt": p.elevation,
            "dist": acumulada,
        })
        anterior = p

    return puntos


def suavizar_altimetria(puntos, ventana_m=250):
    """
    Suaviza la altimetría con un promedio móvil por distancia.

    Es imprescindible: el GPS mide la altura bastante mal, y sin suavizar el
    desnivel acumulado sale inflado (a veces bastante) por el ruido de la señal.
    La ventana de 250 m es amplia a propósito - filtra el ruido sin borrar las
    subidas reales, que siempre son más largas que eso.
    """
    con_alt = [p for p in puntos if p["alt"] is not None]
    if len(con_alt) < 2:
        return None

    n = len(puntos)
    # Índices de inicio y fin de la ventana, avanzando en una sola pasada
    suavizados = []
    izq = der = 0
    suma = 0.0
    cuenta = 0
    for i, p in enumerate(puntos):
        limite_izq = p["dist"] - ventana_m / 2
        limite_der = p["dist"] + ventana_m / 2
        while der < n and puntos[der]["dist"] <= limite_der:
            if puntos[der]["alt"] is not None:
                suma += puntos[der]["alt"]
                cuenta += 1
            der += 1
        while izq < n and puntos[izq]["dist"] < limite_izq:
            if puntos[izq]["alt"] is not None:
                suma -= puntos[izq]["alt"]
                cuenta -= 1
            izq += 1
        suavizados.append(suma / cuenta if cuenta > 0 else p["alt"])

    for p, a in zip(puntos, suavizados):
        p["alt_suave"] = a
    return puntos


def remuestrear(puntos, paso_m=50):
    """
    Devuelve el perfil a intervalos regulares de distancia.

    Trabajar con puntos equiespaciados hace que el cálculo de pendientes sea
    estable: en el archivo original los puntos pueden estar a 2 m o a 200 m unos
    de otros según cómo grabó el GPS, y eso distorsiona cualquier pendiente.
    """
    validos = [p for p in puntos if p.get("alt_suave") is not None]
    if len(validos) < 2:
        return []

    total = validos[-1]["dist"]
    muestras = []
    j = 0
    d = 0.0
    while d <= total:
        while j < len(validos) - 2 and validos[j + 1]["dist"] < d:
            j += 1
        a, b = validos[j], validos[j + 1]
        tramo = b["dist"] - a["dist"]
        frac = (d - a["dist"]) / tramo if tramo > 0 else 0
        frac = max(0.0, min(1.0, frac))
        muestras.append({
            "dist": d,
            "alt": a["alt_suave"] + (b["alt_suave"] - a["alt_suave"]) * frac,
        })
        d += paso_m
    return muestras


def resumen_recorrido(puntos, umbral_m=2.0):
    """
    Distancia total, desnivel positivo y negativo, altura mínima y máxima.

    El desnivel se acumula sobre el perfil remuestreado y solo cuenta los cambios
    mayores a `umbral_m`. Sin ese umbral, el ruido residual del GPS suma metros
    fantasma en cada micro-ondulación y el total termina bastante inflado - es el
    motivo por el que dos apps distintas te dan desniveles diferentes para la
    misma salida.
    """
    distancia_km = puntos[-1]["dist"] / 1000
    perfil = remuestrear(puntos)

    if len(perfil) < 2:
        return {
            "distancia_km": round(distancia_km, 1),
            "desnivel_pos": None, "desnivel_neg": None,
            "alt_min": None, "alt_max": None, "tiene_altimetria": False,
        }

    pos = neg = 0.0
    referencia = perfil[0]["alt"]
    for m in perfil[1:]:
        d = m["alt"] - referencia
        if abs(d) >= umbral_m:
            if d > 0:
                pos += d
            else:
                neg -= d
            referencia = m["alt"]

    alturas = [m["alt"] for m in perfil]
    return {
        "distancia_km": round(distancia_km, 1),
        "desnivel_pos": round(pos),
        "desnivel_neg": round(neg),
        "alt_min": round(min(alturas)),
        "alt_max": round(max(alturas)),
        "tiene_altimetria": True,
    }


def detectar_subidas(puntos, desnivel_minimo=40, pendiente_minima=2.0, hueco_max_m=400):
    """
    Encuentra las subidas relevantes del recorrido.

    Trabaja sobre el perfil remuestreado cada 50 m: marca cada tramo que sube más
    de `pendiente_minima`%, une los tramos cercanos (los puertos reales tienen
    descansos y falsos llanos en el medio) y descarta lo que no llegue a
    `desnivel_minimo` metros.

    Este enfoque reemplazó a uno anterior que iba punto por punto y arrancaba la
    subida ante cualquier repecho: con el ruido del GPS terminaba incluyendo el
    llano previo dentro de la subida y perdiéndose subidas enteras.
    """
    perfil = remuestrear(puntos, paso_m=50)
    if len(perfil) < 3:
        return []

    # 1. Marcar los tramos que suben
    tramos = []
    for a, b in zip(perfil, perfil[1:]):
        largo = b["dist"] - a["dist"]
        if largo <= 0:
            continue
        pend = (b["alt"] - a["alt"]) / largo * 100
        tramos.append({"ini": a, "fin": b, "pend": pend, "sube": pend >= pendiente_minima})

    # 2. Agrupar tramos que suben, tolerando huecos cortos
    grupos = []
    actual = None
    hueco = 0.0
    for t in tramos:
        if t["sube"]:
            if actual is None:
                actual = {"ini": t["ini"], "fin": t["fin"]}
            else:
                actual["fin"] = t["fin"]
            hueco = 0.0
        elif actual is not None:
            hueco += t["fin"]["dist"] - t["ini"]["dist"]
            if hueco > hueco_max_m:
                grupos.append(actual)
                actual = None
                hueco = 0.0
            else:
                actual["fin"] = t["fin"]
    if actual is not None:
        grupos.append(actual)

    # 3. Quedarse con las que valen la pena
    subidas = []
    for g in grupos:
        desnivel = g["fin"]["alt"] - g["ini"]["alt"]
        largo = g["fin"]["dist"] - g["ini"]["dist"]
        if largo <= 0 or desnivel < desnivel_minimo:
            continue
        pendiente = desnivel / largo * 100
        if pendiente < pendiente_minima:
            continue
        subidas.append({
            "km_inicio": round(g["ini"]["dist"] / 1000, 1),
            "km_fin": round(g["fin"]["dist"] / 1000, 1),
            "largo_m": round(largo),
            "desnivel_m": round(desnivel),
            "pendiente_pct": round(pendiente, 1),
        })

    return sorted(subidas, key=lambda s: s["desnivel_m"], reverse=True)


# ---------------------------------------------------------------------------
# Modelo físico: relación entre vatios y velocidad
# ---------------------------------------------------------------------------

def potencia_necesaria(velocidad_ms, pendiente_pct, masa_total, crr, cda):
    """
    Vatios necesarios para sostener una velocidad dada en una pendiente dada.
    Suma los tres frenos: gravedad, rodadura y aire.
    """
    theta = math.atan(pendiente_pct / 100)
    f_gravedad = masa_total * G * math.sin(theta)
    f_rodadura = masa_total * G * math.cos(theta) * crr
    f_aire = 0.5 * RHO * cda * velocidad_ms ** 2
    return (f_gravedad + f_rodadura + f_aire) * velocidad_ms


def velocidad_para_potencia(vatios, pendiente_pct, masa_total, crr, cda):
    """
    Al revés: qué velocidad alcanzás con esos vatios. No tiene solución
    algebraica simple (la ecuación es cúbica), así que se busca por bisección,
    que para este caso converge rápido y sin sorpresas.
    """
    if vatios <= 0:
        return 0.0
    lo, hi = 0.01, 30.0
    for _ in range(60):
        medio = (lo + hi) / 2
        if potencia_necesaria(medio, pendiente_pct, masa_total, crr, cda) < vatios:
            lo = medio
        else:
            hi = medio
    return (lo + hi) / 2


# ---------------------------------------------------------------------------
# Cruce entre el recorrido y tus capacidades
# ---------------------------------------------------------------------------

def analizar_exigencia(subidas, perfil, tipo_bici="Ruta", intensidad_objetivo=0.85):
    """
    Para cada subida importante, calcula qué te va a pedir y lo compara con lo
    que hoy podés sostener.

    intensidad_objetivo: a qué fracción de tu FTP pensás subir. 0.85 es un ritmo
    de carrera larga sostenible; en una subida corta cerca del final se puede ir
    a 1.0 o más.
    """
    ftp = perfil.get("ftp_watts")
    peso = perfil.get("peso_kg")
    if not ftp or not peso:
        return None

    cfg = PERFILES_BICI[tipo_bici]
    masa = peso + cfg["peso_bici"]
    vatios = ftp * intensidad_objetivo

    resultado = []
    for s in subidas:
        v_ms = velocidad_para_potencia(vatios, s["pendiente_pct"], masa, cfg["crr"], cfg["cda"])
        minutos = (s["largo_m"] / v_ms) / 60 if v_ms > 0 else None
        resultado.append({
            **s,
            "velocidad_kmh": round(v_ms * 3.6, 1),
            "minutos": round(minutos, 1) if minutos else None,
            "watts": round(vatios),
            "w_kg": round(vatios / peso, 2),
        })
    return resultado


def estimar_tiempo_total(puntos, perfil, tipo_bici="Ruta", intensidad_objetivo=0.80):
    """
    Estima el tiempo total recorriendo el perfil tramo por tramo.

    IMPORTANTE: esta es la parte menos confiable de todo el módulo. Supone
    valores promedio de aerodinámica y rodadura, no considera el viento, ni el
    ir a rueda de otros, ni tu técnica bajando. Tomalo como un orden de
    magnitud, no como una predicción.
    """
    ftp = perfil.get("ftp_watts")
    peso = perfil.get("peso_kg")
    if not ftp or not peso:
        return None

    cfg = PERFILES_BICI[tipo_bici]
    masa = peso + cfg["peso_bici"]
    vatios = ftp * intensidad_objetivo

    validos = [p for p in puntos if p.get("alt_suave") is not None]
    if len(validos) < 2:
        return None

    segundos = 0.0
    for a, b in zip(validos, validos[1:]):
        tramo = b["dist"] - a["dist"]
        if tramo <= 0:
            continue
        pendiente = (b["alt_suave"] - a["alt_suave"]) / tramo * 100
        pendiente = max(-25, min(25, pendiente))   # recortar picos absurdos del GPS

        if pendiente < -1.5:
            # Bajando no se pedalea al mismo ritmo: se deja rodar. Se calcula la
            # velocidad a la que la gravedad equilibra el rozamiento, y se le
            # aplica un factor de prudencia (mucho más fuerte en MTB).
            v = velocidad_para_potencia(50, pendiente, masa, cfg["crr"], cfg["cda"])
            v *= cfg["eficiencia_bajada"]
            v = min(v, 22 if tipo_bici == "MTB" else 30)
        else:
            v = velocidad_para_potencia(vatios, pendiente, masa, cfg["crr"], cfg["cda"])

        if v > 0.5:
            segundos += tramo / v

    return {
        "horas": segundos / 3600,
        "texto": f"{int(segundos // 3600)}h {int((segundos % 3600) // 60):02d}m",
        "vel_media_kmh": round((validos[-1]["dist"] / 1000) / (segundos / 3600), 1) if segundos else None,
    }


# ---------------------------------------------------------------------------
# Estimación para running
# ---------------------------------------------------------------------------
# En carrera no se usa el modelo físico de vatios: no hay potenciómetro y la
# aerodinámica pesa muy poco a estas velocidades. Lo que se usa es el costo
# energético de la pendiente sobre el ritmo, que está bastante bien estudiado.

def factor_pendiente_running(pendiente_pct):
    """
    Cuánto se encarece (o abarata) el ritmo según la pendiente.

    Subir cuesta alrededor de un 3% más de ritmo por cada 1% de pendiente.
    Bajar devuelve bastante menos de lo que quita subir - alrededor de un 1,5%
    por cada 1% - y a partir de un 10% de bajada deja de ayudar y empieza a
    frenar, porque hay que ir frenando para no caerse. Esa asimetría es la razón
    por la que un recorrido con 500 m de subida y 500 m de bajada es más lento
    que el mismo recorrido en llano.
    """
    p = max(-30, min(30, pendiente_pct))
    if p >= 0:
        return 1 + p * 0.030
    if p >= -10:
        return 1 + p * 0.015          # bajada suave: ayuda
    return 1 - 10 * 0.015 + (abs(p) - 10) * 0.020   # bajada fuerte: vuelve a costar


def estimar_tiempo_running(puntos, ritmo_llano_min_km, tipo_terreno="Asfalto"):
    """
    Estima el tiempo recorriendo el perfil tramo por tramo, partiendo del ritmo
    que sostenés en llano.

    En trail se aplica además una penalización general por el terreno: piedras,
    raíces y barro cuestan tiempo aunque el desnivel ya esté contemplado.
    """
    if not ritmo_llano_min_km:
        return None

    perfil = remuestrear(puntos, paso_m=50)
    if len(perfil) < 2:
        return None

    penalizacion_terreno = 1.12 if tipo_terreno == "Trail / montaña" else 1.0

    minutos = 0.0
    for a, b in zip(perfil, perfil[1:]):
        tramo_km = (b["dist"] - a["dist"]) / 1000
        if tramo_km <= 0:
            continue
        pendiente = (b["alt"] - a["alt"]) / (b["dist"] - a["dist"]) * 100
        ritmo_tramo = ritmo_llano_min_km * factor_pendiente_running(pendiente) * penalizacion_terreno
        minutos += tramo_km * ritmo_tramo

    distancia_km = perfil[-1]["dist"] / 1000
    return {
        "minutos": minutos,
        "distancia_km": distancia_km,
        "ritmo_medio": minutos / distancia_km if distancia_km else None,
    }


def analizar_subidas_running(subidas, ritmo_llano_min_km, tipo_terreno="Asfalto"):
    """Cuánto te llevaría cada subida corriendo, y a qué ritmo."""
    if not ritmo_llano_min_km:
        return None

    penalizacion = 1.12 if tipo_terreno == "Trail / montaña" else 1.0
    resultado = []
    for s in subidas:
        ritmo = ritmo_llano_min_km * factor_pendiente_running(s["pendiente_pct"]) * penalizacion
        minutos = (s["largo_m"] / 1000) * ritmo
        resultado.append({
            **s,
            "ritmo_min_km": round(ritmo, 2),
            "minutos": round(minutos, 1),
            # Por encima de cierta pendiente, casi todo el mundo camina más rápido de lo que corre
            "conviene_caminar": s["pendiente_pct"] >= 15,
        })
    return resultado
