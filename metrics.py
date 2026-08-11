# metrics.py
"""
Cálculos deportivos: zonas de frecuencia cardíaca, carga de entrenamiento (TRIMP)
y el balance Fitness/Fatiga/Forma (CTL/ATL/TSB), adaptado para entrenar solo con
pulsómetro (sin potenciómetro).
"""

import config

# ---------------------------------------------------------------------------
# Deportes
# ---------------------------------------------------------------------------

TIPOS_BICI_AIRE = {"cycling", "road_biking", "mountain_biking", "gravel_cycling"}
TIPOS_BICI_RODILLO = {"indoor_cycling", "virtual_ride"}
TIPOS_BICI = TIPOS_BICI_AIRE | TIPOS_BICI_RODILLO

TIPOS_RUN_ASFALTO = {"running", "street_running", "track_running"}
TIPOS_RUN_MONTANA = {"trail_running"}
TIPOS_RUN_CINTA = {"treadmill_running", "indoor_running", "virtual_run"}
TIPOS_RUNNING = TIPOS_RUN_ASFALTO | TIPOS_RUN_MONTANA | TIPOS_RUN_CINTA

TIPOS_GYM = {"strength_training", "fitness_equipment", "indoor_cardio"}


def es_bajo_techo(tipo):
    """True si la actividad fue en rodillo o cinta (sin viento que te refrigere)."""
    return tipo in TIPOS_BICI_RODILLO or tipo in TIPOS_RUN_CINTA


def es_montana(tipo):
    return tipo in TIPOS_RUN_MONTANA


SUPERFICIE = {
    "road_biking": "Ruta",
    "mountain_biking": "MTB",
    "gravel_cycling": "Gravel",
    "indoor_cycling": "Rodillo",
    "virtual_ride": "Rodillo",
    "cycling": None,            # Garmin usa este tipo genérico: no se sabe la superficie
    "trail_running": "Montaña",
    "running": "Asfalto",
    "street_running": "Asfalto",
    "track_running": "Pista",
    "treadmill_running": "Cinta",
    "indoor_running": "Cinta",
    "virtual_run": "Cinta",
}


def superficie_de(tipo):
    """
    Superficie o modalidad de la actividad, según lo que informa el dispositivo.

    Importa para comparar sesiones entre sí: la velocidad y el VAM de una salida
    de MTB no son comparables con los de una de ruta al mismo esfuerzo. Lo que sí
    es comparable es la carga: un TRIMP de 200 cuesta lo mismo en cualquier
    superficie, y por eso el cálculo de forma NO se separa por terreno.
    """
    return SUPERFICIE.get(tipo)


def deporte_de(tipo):
    """Devuelve 'bici', 'running', 'gym' o None."""
    if tipo in TIPOS_BICI:
        return "bici"
    if tipo in TIPOS_RUNNING:
        return "running"
    if tipo in TIPOS_GYM:
        return "gym"
    return None


# ---------------------------------------------------------------------------
# Umbrales de running
# ---------------------------------------------------------------------------
# Un punto importante: los umbrales medidos en una ergoespirometría sobre
# bicicleta NO se trasladan tal cual al running. Corriendo, la frecuencia
# cardíaca suele estar entre 5 y 10 pulsaciones más alta a la misma intensidad
# relativa, porque se mueve más masa muscular, hay impacto y la postura es
# distinta. Usar las zonas de la bici para correr clasifica mal las sesiones.

DESPLAZAMIENTO_FC_RUNNING = 7   # bpm, el punto medio del rango habitual de 5 a 10


def perfil_para_running(perfil):
    """
    Devuelve una copia del perfil con los umbrales corridos hacia arriba para
    running, si es que los umbrales cargados vienen de una prueba en bicicleta.

    Es una estimación, no una medición: lo ideal sería una ergoespirometría en
    cinta. La app lo aclara en pantalla cada vez que la usa.
    """
    p = dict(perfil)
    test = perfil.get("test_fisiologico") or {}
    if not test.get("vt1_fc") or not test.get("vt2_fc"):
        return p

    if test.get("deporte_del_test") == "running":
        return p   # ya son de correr, no hay nada que ajustar

    d = DESPLAZAMIENTO_FC_RUNNING
    p["test_fisiologico"] = {
        **test,
        "vt1_fc": test["vt1_fc"] + d,
        "vt2_fc": test["vt2_fc"] + d,
        "estimado_desde_bici": True,
    }
    if perfil.get("fc_max"):
        p["fc_max"] = perfil["fc_max"] + 3   # la máxima corriendo también suele ser algo mayor

    zonas = perfil.get("zonas_lab")
    if zonas:
        p["zonas_lab"] = {
            str(z): {**datos, "fc": [datos["fc"][0] + d, datos["fc"][1] + d]}
            for z, datos in zonas.items()
        }
    return p


# ---------------------------------------------------------------------------
# Métricas de running
# ---------------------------------------------------------------------------

def ritmo_min_km(distancia_km, duracion_min):
    """Ritmo en minutos por kilómetro."""
    if not distancia_km or distancia_km <= 0:
        return None
    return duracion_min / distancia_km


def formatear_ritmo(min_km):
    """Convierte 5.5 en '5:30 /km'."""
    if not min_km or min_km <= 0:
        return None
    minutos = int(min_km)
    segundos = round((min_km - minutos) * 60)
    if segundos == 60:
        minutos, segundos = minutos + 1, 0
    return f"{minutos}:{segundos:02d} /km"


# Tope de pendiente media para el ajuste. Por encima de este valor, la corrección
# deja de tener sentido: en un recorrido cuya pendiente MEDIA supera el 8%, gran
# parte del tiempo se sube caminando y la relación entre ritmo y esfuerzo cambia
# por completo. Sin tope, un trail muy vertical devolvía ritmos equivalentes de
# nivel élite que no significaban nada.
PENDIENTE_MAX_AJUSTE = 8.0

# Cuánto encarece el ritmo cada 1% de pendiente media del recorrido.
# Ojo: NO es el 3% por 1% que se usa para la pendiente instantánea. Acá la
# pendiente se calcula como desnivel total sobre distancia total, y eso supone
# que se sube todo el recorrido, cuando en realidad buena parte se baja. Usar el
# 3% con este promedio sobreestima bastante; 2% es una corrección más honesta
# para un valor de sesión completa.
FACTOR_POR_PUNTO_PENDIENTE = 0.02


def ritmo_ajustado_por_pendiente(min_km, desnivel_m, distancia_km):
    """
    Ritmo equivalente en llano (GAP, Grade Adjusted Pace).

    Correr en subida cuesta más que en llano, así que un ritmo de 6:00 en un
    recorrido con mucho desnivel vale bastante más que el mismo 6:00 en pista.

    Es una aproximación de sesión completa: se parte del desnivel total sobre la
    distancia total. Ese promedio mezcla las subidas con las bajadas, así que la
    corrección se aplica con prudencia (ver las dos constantes de arriba). Para
    un número exacto habría que integrar tramo por tramo con el detalle del
    archivo, que es lo que hace el análisis de recorridos.
    """
    if not min_km or not distancia_km or desnivel_m is None:
        return None
    pendiente_media = (desnivel_m / (distancia_km * 1000)) * 100
    pendiente_media = min(pendiente_media, PENDIENTE_MAX_AJUSTE)
    factor = 1 + (pendiente_media * FACTOR_POR_PUNTO_PENDIENTE)
    return min_km / factor if factor > 0 else min_km


def predecir_tiempo_carrera(dist_conocida_km, tiempo_conocido_min, dist_objetivo_km):
    """
    Fórmula de Riegel: T2 = T1 x (D2/D1)^1.06

    Es la predicción de rendimiento más usada y funciona razonablemente entre
    5 km y maratón. Dos advertencias que la app repite en pantalla:
      - Supone que entrenaste lo suficiente para la distancia objetivo. Predecir
        un maratón desde un 5 km sin haber hecho tiradas largas da un número
        optimista que no se cumple.
      - Cuanto más lejos estén las dos distancias, menos confiable es.
    """
    if not dist_conocida_km or not tiempo_conocido_min or not dist_objetivo_km:
        return None
    return tiempo_conocido_min * (dist_objetivo_km / dist_conocida_km) ** 1.06


def formatear_duracion(minutos):
    """Convierte 215.5 en '3h 35m'."""
    if not minutos:
        return None
    h = int(minutos // 60)
    m = int(round(minutos % 60))
    if m == 60:
        h, m = h + 1, 0
    return f"{h}h {m:02d}m" if h else f"{m} min"


NOMBRE_ZONA = {
    1: "Z1 - Recuperación",
    2: "Z2 - Aeróbico / Resistencia",
    3: "Z3 - Tempo",
    4: "Z4 - Umbral",
    5: "Z5 - VO2max / Anaeróbico",
}


def calcular_fc_max(perfil):
    return perfil["fc_max"] or config.estimar_fc_max(perfil["edad"])


def calcular_zonas_fc(perfil):
    """
    Devuelve los límites de bpm de cada zona.

    Si el perfil tiene una tabla de zonas de laboratorio cargada y activada,
    usa esos rangos reales. Si no, los calcula con el método Karvonen
    (reserva de frecuencia cardíaca = FCmax - FCreposo).
    """
    zonas_lab = perfil.get("zonas_lab")
    if perfil.get("usar_zonas_fc_lab") and zonas_lab:
        # Las claves pueden venir como texto si se leyeron de un JSON
        return {int(z): tuple(datos["fc"]) for z, datos in zonas_lab.items()}

    fc_max = calcular_fc_max(perfil)
    fc_reposo = perfil["fc_reposo"]
    reserva = fc_max - fc_reposo

    limites_pct = {
        1: (0.50, 0.60),
        2: (0.60, 0.70),
        3: (0.70, 0.80),
        4: (0.80, 0.90),
        5: (0.90, 1.00),
    }

    zonas = {}
    for z, (lo, hi) in limites_pct.items():
        zonas[z] = (
            round(fc_reposo + lo * reserva),
            round(fc_reposo + hi * reserva),
        )
    return zonas


def tiempo_en_zonas_desde_actividad(actividad):
    """
    Garmin suele entregar 'hrTimeInZone_1' .. 'hrTimeInZone_5' (en segundos) en el
    resumen de cada actividad, calculado con las zonas configuradas en tu cuenta.
    Si estos campos no vienen (algunas actividades no los tienen), devolvemos None
    para que se use una estimación de respaldo.
    """
    minutos = {}
    encontrado = False
    for z in range(1, 6):
        segundos = actividad.get(f"hrTimeInZone_{z}")
        if segundos is not None:
            minutos[z] = segundos / 60
            encontrado = True
        else:
            minutos[z] = 0.0
    return minutos if encontrado else None


def estimar_tiempo_en_zonas(actividad, perfil):
    """
    Respaldo cuando Garmin no manda el detalle por zona: le asigna toda la duración
    de la sesión a la zona de la FC promedio. Es una aproximación (menos precisa
    que el detalle real), pero mejor que no tener nada.
    """
    duracion_min = actividad.get("duration", 0) / 60
    fc_prom = actividad.get("averageHR")
    zonas = calcular_zonas_fc(perfil)
    minutos = {z: 0.0 for z in range(1, 6)}

    if fc_prom is None or duracion_min == 0:
        return minutos

    zona_asignada = 1
    for z, (lo, hi) in zonas.items():
        if fc_prom >= lo:
            zona_asignada = z
    minutos[zona_asignada] = duracion_min
    return minutos


def trimp_edwards(minutos_por_zona):
    """TRIMP método Edwards: minutos en cada zona x peso de esa zona, sumados."""
    return sum(minutos_por_zona.get(z, 0) * config.PESO_ZONA[z] for z in range(1, 6))


NOMBRE_ZONA_POTENCIA = {
    1: "Z1 - Recuperación activa",
    2: "Z2 - Resistencia (Endurance)",
    3: "Z3 - Tempo",
    4: "Z4 - Umbral (Threshold)",
    5: "Z5 - VO2max",
    6: "Z6 - Capacidad anaeróbica",
    7: "Z7 - Neuromuscular (sprints)",
}


def calcular_zonas_potencia(ftp):
    """
    Zonas clásicas de Andrew Coggan basadas en % de tu FTP. Devuelve None si no
    hay FTP cargado (no se pueden calcular zonas de potencia sin ese dato).
    """
    if not ftp:
        return None
    limites_pct = {
        1: (0.00, 0.55),
        2: (0.56, 0.75),
        3: (0.76, 0.90),
        4: (0.91, 1.05),
        5: (1.06, 1.20),
        6: (1.21, 1.50),
        7: (1.51, 3.00),  # techo arbitrario alto, para sprints
    }
    return {z: (round(lo * ftp), round(hi * ftp)) for z, (lo, hi) in limites_pct.items()}


def tiempo_en_zonas_potencia_desde_actividad(actividad):
    """
    Garmin puede entregar 'powerTimeInZone_1' .. '_7' (en segundos) si tenés zonas de
    potencia configuradas en tu cuenta. Si no vienen, devuelve None para usar el fallback.
    """
    minutos = {}
    encontrado = False
    for z in range(1, 8):
        segundos = actividad.get(f"powerTimeInZone_{z}")
        if segundos is not None:
            minutos[z] = segundos / 60
            encontrado = True
        else:
            minutos[z] = 0.0
    return minutos if encontrado else None


def estimar_tiempo_en_zonas_potencia(actividad, ftp):
    """Fallback: asigna toda la duración a la zona de la potencia promedio de la sesión."""
    duracion_min = actividad.get("duration", 0) / 60
    potencia_prom = actividad.get("avgPower")
    zonas = calcular_zonas_potencia(ftp)
    minutos = {z: 0.0 for z in range(1, 8)}

    if not zonas or potencia_prom is None or duracion_min == 0:
        return minutos

    zona_asignada = 1
    for z, (lo, hi) in zonas.items():
        if potencia_prom >= lo:
            zona_asignada = z
    minutos[zona_asignada] = duracion_min
    return minutos


def calcular_tss(actividad, ftp):
    """
    TSS (Training Stress Score). Prioridad:
    1) Si Garmin ya lo calculó (porque configuraste tu FTP en Garmin Connect), se usa ese.
    2) Si no, se calcula a mano con la Potencia Normalizada (o el promedio si no hay NP) y tu FTP.
    Devuelve None si no hay FTP cargado ni TSS provisto por Garmin.
    """
    tss_garmin = actividad.get("trainingStressScore")
    if tss_garmin is not None:
        return round(tss_garmin, 1)
    if not ftp:
        return None
    np_ = actividad.get("normPower") or actividad.get("avgPower")
    duracion_seg = actividad.get("duration", 0)
    if np_ is None or duracion_seg == 0:
        return None
    intensity_factor = np_ / ftp
    tss = (duracion_seg * np_ * intensity_factor) / (ftp * 3600) * 100
    return round(tss, 1)


def calcular_intensity_factor(actividad, ftp):
    """IF = Potencia Normalizada / FTP. Mide qué tan dura fue la sesión en relación a tu umbral."""
    if_garmin = actividad.get("intensityFactor")
    if if_garmin is not None:
        return round(if_garmin, 2)
    if not ftp:
        return None
    np_ = actividad.get("normPower") or actividad.get("avgPower")
    if np_ is None:
        return None
    return round(np_ / ftp, 2)


def procesar_actividad(actividad, perfil):
    """Convierte una actividad cruda de Garmin en un resumen limpio con TRIMP incluido,
    y con métricas de potencia si la sesión tiene medidor de vatios."""
    minutos = tiempo_en_zonas_desde_actividad(actividad)
    estimado = False
    if minutos is None:
        minutos = estimar_tiempo_en_zonas(actividad, perfil)
        estimado = True

    trimp = trimp_edwards(minutos)

    duracion_min = round(actividad.get("duration", 0) / 60, 1)
    distancia_km = round((actividad.get("distance") or 0) / 1000, 1)
    elevacion_m = actividad.get("elevationGain")

    resultado = {
        "id": actividad.get("activityId"),
        "nombre": actividad.get("activityName") or "Salida en bici",
        "fecha": actividad.get("startTimeLocal"),
        "tipo": actividad.get("activityType", {}).get("typeKey", "desconocido"),
        "duracion_min": duracion_min,
        "distancia_km": distancia_km,
        "elevacion_m": elevacion_m,
        "velocidad_kmh": round(distancia_km / (duracion_min / 60), 1) if duracion_min else None,
        "elevacion_por_km": round(elevacion_m / distancia_km, 1) if elevacion_m and distancia_km else None,
        "fc_prom": actividad.get("averageHR"),
        "fc_max_sesion": actividad.get("maxHR"),
        "cadencia_prom": (
            actividad.get("averageBikingCadenceInRevPerMinute")
            or actividad.get("averageRunningCadenceInStepsPerMinute")
        ),
        "calorias": actividad.get("calories"),
        "minutos_por_zona": minutos,
        "zonas_estimadas": estimado,
        "trimp": round(trimp, 1),
    }

    tipo = resultado["tipo"]
    resultado["deporte"] = deporte_de(tipo)
    resultado["superficie"] = superficie_de(tipo)
    resultado["bajo_techo"] = es_bajo_techo(tipo)
    resultado["montana"] = es_montana(tipo)

    # Desnivel negativo: en trail es tan importante como el positivo. Bajar
    # produce contracción excéntrica, que es la que rompe las fibras y deja las
    # piernas destruidas al día siguiente - más que subir.
    resultado["desnivel_neg_m"] = actividad.get("elevationLoss")

    if resultado["deporte"] == "running":
        # --- Dinámicas de carrera ---
        # Las reporta el reloj solo si tenés un sensor compatible (banda HRM-Pro,
        # Running Dynamics Pod, o relojes recientes con sensor en la muñeca).
        resultado["contacto_suelo_ms"] = actividad.get("avgGroundContactTime")
        resultado["oscilacion_vertical_cm"] = actividad.get("avgVerticalOscillation")
        resultado["ratio_vertical_pct"] = actividad.get("avgVerticalRatio")
        resultado["balance_contacto"] = actividad.get("avgGroundContactBalance")

        zancada = actividad.get("avgStrideLength")
        if zancada:
            # Garmin la manda en centímetros; si viene chica ya está en metros
            resultado["zancada_m"] = round(zancada / 100, 2) if zancada > 10 else round(zancada, 2)

        # Si el reloj no da el ratio vertical, se calcula: es la oscilación
        # dividida por la zancada. Mide cuánta energía se va en subir y bajar el
        # cuerpo en vez de empujarlo hacia adelante.
        if not resultado.get("ratio_vertical_pct") and resultado.get("oscilacion_vertical_cm") and resultado.get("zancada_m"):
            resultado["ratio_vertical_pct"] = round(
                resultado["oscilacion_vertical_cm"] / (resultado["zancada_m"] * 100) * 100, 1
            )

        ritmo = ritmo_min_km(distancia_km, duracion_min)
        resultado["ritmo_min_km"] = round(ritmo, 2) if ritmo else None
        resultado["ritmo_texto"] = formatear_ritmo(ritmo)
        gap = ritmo_ajustado_por_pendiente(ritmo, elevacion_m, distancia_km)
        # El ritmo ajustado solo aporta algo si hubo desnivel de verdad
        if gap and elevacion_m and distancia_km and (elevacion_m / distancia_km) > 8:
            resultado["ritmo_gap"] = round(gap, 2)
            resultado["ritmo_gap_texto"] = formatear_ritmo(gap)

    potencia_prom = actividad.get("avgPower")
    resultado["tiene_potencia"] = potencia_prom is not None

    if resultado["tiene_potencia"]:
        ftp = perfil.get("ftp_watts")
        minutos_pot = tiempo_en_zonas_potencia_desde_actividad(actividad)
        zona_pot_estimada = False
        if minutos_pot is None and ftp:
            minutos_pot = estimar_tiempo_en_zonas_potencia(actividad, ftp)
            zona_pot_estimada = True

        peso = perfil.get("peso_kg")
        potencia_para_ef = actividad.get("normPower") or potencia_prom
        resultado.update({
            "potencia_prom": potencia_prom,
            "potencia_max": actividad.get("maxPower"),
            "potencia_normalizada": actividad.get("normPower"),
            "watts_por_kg": round(potencia_prom / peso, 2) if peso else None,
            "tss": calcular_tss(actividad, ftp),
            "if_": calcular_intensity_factor(actividad, ftp),
            "minutos_por_zona_potencia": minutos_pot,
            "zona_potencia_estimada": zona_pot_estimada,
            "ef": round(potencia_para_ef / resultado["fc_prom"], 2) if resultado.get("fc_prom") else None,
        })

    return resultado


def calcular_ctl_atl_tsb(historial_diario):
    """
    historial_diario: lista de dicts {"fecha": date, "trimp": float}, UN registro por
    día calendario (incluyendo días de descanso con trimp=0), ordenada cronológicamente.

    Devuelve la misma lista agregando 'ctl' (fitness, media móvil de 42 días),
    'atl' (fatiga, media móvil de 7 días) y 'tsb' (forma = ctl - atl del mismo día).

    Sobre el TSB: la convención clásica de TrainingPeaks usa los valores del día
    ANTERIOR, porque el gráfico está pensado para planificar a la mañana, antes de
    entrenar. Acá se usa el mismo día a propósito: esta app se mira sobre todo al
    volver de entrenar, y con la convención clásica la pantalla mostraba cosas como
    "Fitness 83 · Fatiga 119 · Forma -1", donde la resta no cerraba y una sesión
    muy dura recién hecha no se reflejaba en la forma. Con el mismo día, los tres
    números son coherentes entre sí y la lectura es honesta.
    """
    ctl = 0.0
    atl = 0.0
    resultado = []
    for dia in historial_diario:
        trimp_hoy = dia["trimp"]
        ctl = ctl + (trimp_hoy - ctl) / config.CTL_DIAS
        atl = atl + (trimp_hoy - atl) / config.ATL_DIAS
        tsb = ctl - atl
        resultado.append({**dia, "ctl": round(ctl, 1), "atl": round(atl, 1), "tsb": round(tsb, 1)})
    return resultado


# ---------------------------------------------------------------------------
# Deriva cardíaca (aerobic decoupling)
# ---------------------------------------------------------------------------
# Compara la relación potencia/FC (o velocidad/FC si no hay potencia) entre la
# primera y la segunda mitad de una sesión. Si tu FC sube pero tu potencia/velocidad
# se mantiene, tu corazón está trabajando más para sostener el mismo esfuerzo -
# típicamente por calor, deshidratación, o porque la duración/intensidad superó tu
# base aeróbica actual. Solo tiene sentido en salidas largas y estables (no en series).
# Requiere el detalle segundo a segundo de la actividad, no solo el resumen.

def extraer_series(detalle_actividad):
    """
    Convierte la respuesta de Garmin `get_activity_details` en listas planas de
    FC, potencia y velocidad. El formato exacto puede variar según la versión de
    la librería; si algo no calza, devuelve listas vacías en vez de romper.
    """
    try:
        descriptores = detalle_actividad.get("metricDescriptors", [])
        indices = {d["key"]: d["metricsIndex"] for d in descriptores if "key" in d and "metricsIndex" in d}
        muestras = detalle_actividad.get("activityDetailMetrics", [])
    except (AttributeError, KeyError, TypeError):
        return {"fc": [], "potencia": [], "velocidad": [], "altitud": [],
                "distancia": [], "tiempo": []}

    def valor(fila, clave):
        idx = indices.get(clave)
        if idx is None or idx >= len(fila):
            return None
        return fila[idx]

    fc, potencia, velocidad, altitud, distancia, tiempo = [], [], [], [], [], []
    for m in muestras:
        fila = m.get("metrics", [])
        fc.append(valor(fila, "directHeartRate"))
        potencia.append(valor(fila, "directPower"))
        velocidad.append(valor(fila, "directSpeed"))
        altitud.append(valor(fila, "directElevation"))
        # La distancia acumulada permite calcular la pendiente de cada tramo,
        # que es imprescindible para interpretar el VAM: el mismo esfuerzo da
        # VAM muy distintos según lo empinada que sea la subida.
        distancia.append(valor(fila, "sumDistance"))
        # El tiempo transcurrido es imprescindible: Garmin NO devuelve una
        # muestra por segundo (submuestrea a ~1000-2000 puntos por actividad),
        # así que contar muestras para medir el tiempo da resultados muy errados.
        tiempo.append(valor(fila, "sumElapsedDuration") or valor(fila, "sumDuration"))

    return {"fc": fc, "potencia": potencia, "velocidad": velocidad,
            "altitud": altitud, "distancia": distancia, "tiempo": tiempo}


def calcular_deriva_cardiaca_desde_series(series):
    fc, potencia, velocidad = series["fc"], series["potencia"], series["velocidad"]

    n = len(fc)
    if n < 60:  # muy pocos puntos como para que el cálculo tenga sentido
        return None

    mitad = n // 2

    def promedio(lista, ini, fin):
        vals = [v for v in lista[ini:fin] if v is not None]
        return sum(vals) / len(vals) if vals else None

    fc1, fc2 = promedio(fc, 0, mitad), promedio(fc, mitad, n)
    if not fc1 or not fc2:
        return None

    if any(v is not None for v in potencia):
        m1, m2 = promedio(potencia, 0, mitad), promedio(potencia, mitad, n)
        etiqueta = "potencia/FC"
    else:
        m1, m2 = promedio(velocidad, 0, mitad), promedio(velocidad, mitad, n)
        etiqueta = "velocidad/FC"

    if not m1 or not m2:
        return None

    ratio1, ratio2 = m1 / fc1, m2 / fc2
    deriva_pct = (ratio1 - ratio2) / ratio1 * 100

    return {
        "deriva_pct": round(deriva_pct, 1),
        "fc_primera_mitad": round(fc1),
        "fc_segunda_mitad": round(fc2),
        "metrica_usada": etiqueta,
    }


def calcular_deriva_cardiaca(detalle_actividad):
    """Atajo: recibe directamente la respuesta cruda de get_activity_details."""
    return calcular_deriva_cardiaca_desde_series(extraer_series(detalle_actividad))


# ---------------------------------------------------------------------------
# Curva de potencia, Potencia Crítica (CP), W' y Time to Exhaustion (TTE)
# ---------------------------------------------------------------------------
# La "curva de potencia" (o mean maximal power curve) es el mejor promedio de
# potencia que sostuviste para cada duración (5 seg, 1 min, 5 min, 20 min...),
# tomando el mejor resultado entre TODAS tus sesiones. De ahí se derivan:
#   - CP (Potencia Crítica): muy cercana conceptualmente a tu FTP.
#   - W' (o FRC): tu "tanque" de trabajo anaeróbico por encima de la CP, en kJ.
#   - TTE: cuánto tiempo sostenés algo cercano a tu FTP en la práctica.

DURACIONES_CURVA = [5, 15, 30, 60, 120, 180, 300, 600, 720, 1200, 1800, 3600]


def mejor_potencia_promedio(potencia_serie, ventana_seg):
    """
    Mejor promedio móvil de potencia para una ventana de duración dada.
    Asume ~1 muestra por segundo (lo habitual en el detalle de Garmin).
    """
    valores = [v for v in potencia_serie if v is not None]
    n = len(valores)
    if ventana_seg <= 0 or n < ventana_seg:
        return None

    acumulado = [0]
    for v in valores:
        acumulado.append(acumulado[-1] + v)

    mejor = 0
    for i in range(n - ventana_seg + 1):
        promedio = (acumulado[i + ventana_seg] - acumulado[i]) / ventana_seg
        if promedio > mejor:
            mejor = promedio
    return mejor


def calcular_curva_potencia(series_multiples):
    """
    series_multiples: lista de listas de potencia (una lista por actividad).
    Devuelve {duracion_seg: mejor_potencia_watts}, combinando el mejor
    resultado de TODAS las actividades para cada duración.
    """
    curva = {}
    for duracion in DURACIONES_CURVA:
        mejor_global = 0
        for serie in series_multiples:
            mejor = mejor_potencia_promedio(serie, duracion)
            if mejor and mejor > mejor_global:
                mejor_global = mejor
        if mejor_global > 0:
            curva[duracion] = round(mejor_global)

    # La curva tiene que ser no creciente: lo que sostenés 5 minutos no puede
    # superar lo que sostenés 3. Tomar el máximo por duración de forma
    # independiente no lo garantiza — si la potencia va alta, baja y alta otra
    # vez, toda ventana corta cae en el hueco mientras que una larga alcanza los
    # dos picos, y el resultado sube al alargar la duración. Es matemáticamente
    # válido pero fisiológicamente absurdo, así que se recorta con el valor de la
    # duración anterior, que es lo que hace que la curva signifique "lo mejor que
    # podés sostener DURANTE AL MENOS ese tiempo".
    tope = None
    for duracion in sorted(curva):
        if tope is not None and curva[duracion] > tope:
            curva[duracion] = tope
        tope = curva[duracion]
    return curva


def ajustar_cp_wprime(curva):
    """
    Ajusta el modelo clásico de Potencia Crítica de 2 parámetros (Monod-Scherrer):
        trabajo total = CP x t + W'
    con una regresión lineal sobre los puntos de la curva entre 2 y 20 minutos
    (el rango donde este modelo es más confiable). Devuelve
    {"cp": watts, "w_prime_kj": kilojulios} o None si no hay suficientes puntos.
    """
    puntos = [(t, p) for t, p in curva.items() if 120 <= t <= 1200]
    if len(puntos) < 2:
        return None

    xs = [t for t, _ in puntos]
    ys = [p * t for t, p in puntos]  # trabajo total en joules

    n = len(xs)
    media_x = sum(xs) / n
    media_y = sum(ys) / n
    num = sum((x - media_x) * (y - media_y) for x, y in zip(xs, ys))
    den = sum((x - media_x) ** 2 for x in xs)
    if den == 0:
        return None

    cp = num / den
    w_prime = media_y - cp * media_x

    if cp <= 0 or w_prime <= 0:
        return None

    return {"cp": round(cp), "w_prime_kj": round(w_prime / 1000, 1)}


def estimar_tte(curva, ftp):
    """
    Estima el Time to Exhaustion (TTE) a FTP de forma EMPÍRICA: busca, dentro
    de tu curva de potencia real, la mayor duración en la que sostuviste una
    potencia cercana a tu FTP (dentro de un 3%).

    No se usa la fórmula teórica W'/(FTP-CP) a propósito: en el modelo de 2
    parámetros, FTP y CP son casi el mismo valor, y esa fórmula se vuelve
    inestable justo ahí (tiende a infinito) - es una limitación conocida del
    modelo simple. Un valor tomado de tus propios mejores esfuerzos reales es
    más honesto que un número inventado por una fórmula que no aplica bien acá.
    """
    if not ftp:
        return None
    candidatos = [t for t, p in curva.items() if p >= ftp * 0.97]
    if not candidatos:
        return None
    return max(candidatos)


# ---------------------------------------------------------------------------
# FC de Umbral (LTHR)
# ---------------------------------------------------------------------------

def estimar_lthr(sesiones):
    """
    Estima tu FC de umbral (LTHR) a partir de tus propias sesiones:
    - Si tenés potencia: promedia la FC de sesiones largas (>=20 min) con
      Intensity Factor cercano a 1 (esfuerzo cercano al umbral real).
    - Si no tenés potencia: promedia la FC de sesiones donde la zona
      dominante fue Z4 (umbral), como aproximación más rústica.
    Devuelve {"lthr": bpm, "metodo": str, "n_sesiones": int} o None si no hay
    datos suficientes.
    """
    candidatas_potencia = [
        s for s in sesiones
        if s.get("tiene_potencia") and s.get("if_") is not None
        and 0.93 <= s["if_"] <= 1.03 and s["duracion_min"] >= 20 and s.get("fc_prom")
    ]
    if candidatas_potencia:
        fcs = [s["fc_prom"] for s in candidatas_potencia]
        return {
            "lthr": round(sum(fcs) / len(fcs)),
            "metodo": "esfuerzos con Intensity Factor cercano a 1 (más preciso)",
            "n_sesiones": len(fcs),
        }

    candidatas_hr = []
    for s in sesiones:
        minutos = s.get("minutos_por_zona", {})
        if not any(minutos.values()) or not s.get("fc_prom"):
            continue
        if max(minutos, key=minutos.get) == 4 and s["duracion_min"] >= 15:
            candidatas_hr.append(s["fc_prom"])

    if candidatas_hr:
        return {
            "lthr": round(sum(candidatas_hr) / len(candidatas_hr)),
            "metodo": "FC en tus sesiones de zona de umbral (estimación más rústica)",
            "n_sesiones": len(candidatas_hr),
        }

    return None


# ---------------------------------------------------------------------------
# VAM (Velocidad de Ascensión Media)
# ---------------------------------------------------------------------------

VENTANAS_VAM_SEG = (300, 600, 1200)  # 5, 10 y 20 minutos


def vatios_kg_desde_vam(vam, pendiente_pct):
    """
    Estima los vatios por kilo a partir del VAM y la pendiente (fórmula de Ferrari):

        VAM = W/kg x (2 + pendiente%/10) x 100

    Es útil porque el VAM por sí solo NO se puede comparar entre subidas de
    distinta pendiente, y los W/kg sí. En una subida suave vas rápido pero ganás
    poca altura por hora; en una empinada pasa lo contrario, con el mismo esfuerzo.

    La fórmula es confiable entre un 5% y un 15% de pendiente. Por debajo del 5%
    la resistencia del aire empieza a pesar más que la gravedad y la estimación
    se va para arriba; por encima del 15% empiezan a pesar la técnica y el hecho
    de que muchos se paran sobre los pedales. Fuera de ese rango no se muestra,
    para no dar un número con apariencia de precisión que no la tiene.
    """
    if not vam or pendiente_pct is None or not (5 <= pendiente_pct <= 15):
        return None
    factor = (2 + pendiente_pct / 10) * 100
    return round(vam / factor, 2) if factor else None


def calcular_mejor_vam(altitud_serie, distancia_serie=None, tiempo_serie=None,
                       duracion_total_seg=None, minimo_seg=120):
    """
    Encuentra la mejor subida sostenida de la sesión y calcula su VAM.

    Cómo funciona: en vez de mirar ventanas de tamaño fijo, detecta los tramos
    que realmente suben (usando altura y distancia), los une tolerando descansos
    cortos, y se queda con el que da mayor ganancia de altura por hora.

    Devuelve la mejor subida y, además, una lista con las principales del
    recorrido. Hace falta mostrar varias porque un circuito ondulado suele tener
    dos cosas distintas: repechos cortos y empinados, y alguna subida larga y
    suave. Con una sola no se ve el circuito real - antes, con un mínimo de 5
    minutos, los repechos de 2 o 3 minutos al 15% quedaban excluidos y la app
    terminaba reportando la subida más suave, que es justo la menos interesante.

    --- Por qué está escrito así ---
    La primera versión recorría ventanas de 300, 600 y 1200 muestras suponiendo
    que cada muestra era un segundo. Eso es falso: Garmin submuestrea el detalle
    a unos 1000-2000 puntos por actividad, así que en una salida de dos horas
    cada muestra son 7 segundos. El resultado era que una "ventana de 5 minutos"
    abarcaba en realidad 36 minutos y kilómetros de llano, y el VAM salía
    disparatado (más del doble que el de un ciclista profesional).

    Por eso ahora el tiempo se toma del propio archivo, y si no viene, se deduce
    de la duración total de la sesión.
    """
    n = len(altitud_serie)
    if n < 10:
        return None

    # --- Reconstruir el tiempo real de cada muestra ---
    tiempos = None
    if tiempo_serie and len(tiempo_serie) == n and any(t is not None for t in tiempo_serie):
        tiempos = list(tiempo_serie)
    elif duracion_total_seg:
        paso = duracion_total_seg / max(n - 1, 1)
        tiempos = [i * paso for i in range(n)]
    else:
        return None   # sin referencia de tiempo no se puede calcular un VAM honesto

    # Quedarse con las muestras que tienen los tres datos
    puntos = [
        {"alt": a, "dist": d, "t": t}
        for a, d, t in zip(altitud_serie, distancia_serie or [None] * n, tiempos)
        if a is not None and t is not None
    ]
    if len(puntos) < 10:
        return None
    hay_distancia = all(p["dist"] is not None for p in puntos)

    # --- Detectar tramos que suben, uniendo los que están cerca ---
    HUECO_MAX_SEG = 60          # descansos cortos dentro de una misma subida
    CAIDA_MAX_M = 12            # cuánto puede bajar sin cortar la subida

    subidas = []
    ini_i = None
    techo_i = None
    for i in range(1, len(puntos)):
        subiendo = puntos[i]["alt"] > puntos[i - 1]["alt"]
        if subiendo:
            if ini_i is None:
                ini_i, techo_i = i - 1, i
            elif puntos[i]["alt"] > puntos[techo_i]["alt"]:
                techo_i = i
        elif ini_i is not None:
            cayo = puntos[techo_i]["alt"] - puntos[i]["alt"]
            hueco = puntos[i]["t"] - puntos[techo_i]["t"]
            if cayo > CAIDA_MAX_M or hueco > HUECO_MAX_SEG:
                subidas.append((ini_i, techo_i))
                ini_i, techo_i = None, None
    if ini_i is not None and techo_i is not None:
        subidas.append((ini_i, techo_i))

    # --- Armar la lista de subidas válidas ---
    validas = []
    for a_i, b_i in subidas:
        desnivel = puntos[b_i]["alt"] - puntos[a_i]["alt"]
        segundos = puntos[b_i]["t"] - puntos[a_i]["t"]
        if segundos < minimo_seg or desnivel < 15:
            continue
        largo = (puntos[b_i]["dist"] - puntos[a_i]["dist"]) if hay_distancia else None
        pendiente = round(desnivel / largo * 100, 1) if largo and largo > 0 else None
        vam = desnivel / (segundos / 3600)
        item = {
            "vam": round(vam),
            "duracion_seg": round(segundos),
            "desnivel_m": round(desnivel),
            "largo_m": round(largo) if largo else None,
            "pendiente_pct": pendiente,
            "km_inicio": round(puntos[a_i]["dist"] / 1000, 1) if hay_distancia else None,
        }
        if pendiente:
            item["w_kg"] = vatios_kg_desde_vam(vam, pendiente)
        validas.append(item)

    if not validas:
        return None

    validas.sort(key=lambda x: x["vam"], reverse=True)
    mejor = dict(validas[0])
    mejor["subidas"] = validas[:5]
    # La subida más larga suele ser otra distinta de la de mayor VAM, y también
    # interesa: es la que pone a prueba la resistencia, no la potencia.
    mas_larga = max(validas, key=lambda x: x["duracion_seg"])
    if mas_larga is not validas[0]:
        mejor["mas_larga"] = mas_larga
    return mejor


# ---------------------------------------------------------------------------
# Carga de entrenamiento en running (rTSS)
# ---------------------------------------------------------------------------
# El TRIMP mide la carga por el pulso y sirve para cualquier deporte, pero tiene
# un límite conocido: el pulso tarda en subir, así que en series cortas subestima
# el esfuerzo real. El rTSS lo mide por el ritmo, igual que el TSS de ciclismo
# lo mide por los vatios, y capta mejor esas sesiones. Los dos conviven: la app
# sigue usando TRIMP para el gráfico de forma (porque funciona siempre) y muestra
# el rTSS como referencia adicional cuando puede calcularlo.

def ritmo_umbral_estimado(sesiones):
    """
    Estima tu ritmo de umbral: el que podrías sostener alrededor de una hora.

    Se deduce de tu mejor esfuerzo reciente proyectado a una hora con la fórmula
    de Riegel. No reemplaza a un test, pero permite calcular el rTSS sin pedirte
    que midas nada nuevo.
    """
    candidatas = [
        s for s in sesiones
        if s.get("deporte") == "running" and s.get("ritmo_min_km") and s["distancia_km"] >= 5
    ]
    if not candidatas:
        return None

    mejor = min(candidatas, key=lambda s: s["ritmo_min_km"])
    # Distancia que recorrería en una hora a ese ritmo, y su ritmo proyectado
    dist_una_hora = 60 / mejor["ritmo_min_km"]
    tiempo = predecir_tiempo_carrera(mejor["distancia_km"], mejor["duracion_min"], dist_una_hora)
    if not tiempo or dist_una_hora <= 0:
        return None
    return round(tiempo / dist_una_hora, 2)


def calcular_rtss(sesion, ritmo_umbral):
    """
    Running Stress Score: 100 equivale a una hora exacta a ritmo de umbral.

    Se calcula con la relación de velocidades (no de ritmos), elevada al
    cuadrado, igual que el TSS de ciclismo:  rTSS = horas x IF^2 x 100

    En recorridos con desnivel se usa el ritmo ajustado por pendiente (GAP), que
    para esto es más justo: una hora subiendo cuesta mucho más que una hora en
    llano al mismo ritmo de reloj.
    """
    if not ritmo_umbral or not sesion.get("ritmo_min_km"):
        return None

    ritmo = sesion.get("ritmo_gap") or sesion["ritmo_min_km"]
    if ritmo <= 0:
        return None

    intensidad = ritmo_umbral / ritmo          # relación de velocidades
    # Un tope de seguridad: sostener más del 115% del umbral por una sesión
    # entera no es fisiológicamente posible, así que si sale eso es que el ritmo
    # de umbral estimado quedó lento, no que la sesión fue sobrehumana.
    intensidad = min(intensidad, 1.15)
    horas = sesion["duracion_min"] / 60
    return {
        "rtss": round(horas * intensidad ** 2 * 100, 1),
        "intensidad": round(intensidad, 2),
        "uso_gap": bool(sesion.get("ritmo_gap")),
    }


def potencia_running(sesion, perfil):
    """
    Potencia de carrera, si el reloj o el sensor la reportan.

    ADVERTENCIA importante: la potencia en carrera NO está estandarizada. Garmin,
    Stryd, Coros y Polar la calculan con modelos distintos y sus números no son
    comparables entre sí. Tampoco es comparable con la potencia de ciclismo, que
    sí mide trabajo mecánico real sobre los pedales. Sirve para compararte con
    vos mismo usando siempre el mismo dispositivo, y para nada más.
    """
    pot = sesion.get("potencia_prom")
    if not pot:
        return None
    peso = perfil.get("peso_kg")
    return {
        "watts": round(pot),
        "w_kg": round(pot / peso, 2) if peso else None,
        "normalizada": sesion.get("potencia_normalizada"),
    }
