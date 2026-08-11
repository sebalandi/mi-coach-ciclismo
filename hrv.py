# hrv.py
"""
Variabilidad de la frecuencia cardíaca (VFC) y su relación con el entrenamiento.

--- Qué se compara acá, y por qué no lo obvio ---

La idea intuitiva es cruzar la curva de potencia con la VFC: "cuando estoy mejor
recuperado, ¿rindo más?". El problema es que la curva de potencia es la
envolvente de tus mejores esfuerzos de todo el período: es casi estática, solo se
mueve cuando hacés un récord. Cruzarla contra un dato que cambia día a día no
dice nada.

La variante aparentemente sensata -comparar la mejor potencia de cada día contra
la VFC de esa mañana- tiene un sesgo que la invalida: SOLO producís potencia alta
cuando hacés una sesión dura. En un día de rodaje suave tu mejor potencia de 5
minutos es baja porque no lo intentaste, no porque estuvieras cansado. Esa
correlación terminaría midiendo qué sesión planificaste, no tu recuperación.

Por eso acá se hacen tres análisis que sí controlan ese sesgo:

  1. VFC contra tu propia línea de base. Lo que importa no es el valor absoluto
     (es enormemente individual) sino cuánto te apartás de tu promedio reciente.

  2. Eficiencia en sesiones comparables. Se agrupan solo las sesiones del MISMO
     tipo y se compara el factor de eficiencia según la VFC de ese día. Al
     comparar peras con peras, el sesgo desaparece.

  3. VFC contra la carga acumulada. Si tu VFC cae cuando el TSB se hunde, el
     modelo de carga describe bien tu fisiología. Si no se mueven juntos, alguno
     de los dos no te representa.

--- Advertencia sobre los datos ---

Garmin devuelve la VFC con estructuras que varían según el modelo de reloj y la
versión de la app. La lectura de acá abajo es defensiva: prueba varios nombres de
campo y, si no reconoce nada, devuelve el dato crudo para poder ajustarlo, en vez
de fallar en silencio.
"""

from datetime import date, timedelta
import statistics


def _buscar(dic, *nombres):
    """Busca la primera clave que exista, sin distinguir mayúsculas."""
    if not isinstance(dic, dict):
        return None
    bajos = {k.lower(): v for k, v in dic.items()}
    for n in nombres:
        v = bajos.get(n.lower())
        if v is not None:
            return v
    return None


def interpretar_dia(crudo):
    """
    Convierte la respuesta de Garmin para un día en algo manejable.
    Devuelve None si no reconoce el formato, sin lanzar excepciones.
    """
    if not crudo or not isinstance(crudo, dict):
        return None

    resumen = _buscar(crudo, "hrvSummary") or crudo
    rmssd = _buscar(resumen, "lastNightAvg", "weeklyAvg", "avgHrv", "hrvValue")

    if rmssd is None:
        lecturas = _buscar(crudo, "hrvReadings", "readings") or []
        valores = [_buscar(r, "hrvValue", "value") for r in lecturas if isinstance(r, dict)]
        valores = [v for v in valores if isinstance(v, (int, float))]
        if valores:
            rmssd = sum(valores) / len(valores)

    if not isinstance(rmssd, (int, float)):
        return None

    base = _buscar(resumen, "baseline") or {}
    return {
        "rmssd": round(float(rmssd), 1),
        "estado": _buscar(resumen, "status"),
        "base_min": _buscar(base, "balancedLow", "lowUpper"),
        "base_max": _buscar(base, "balancedUpper", "upperLimit"),
    }


def traer_rango(client, dias=45):
    """
    Trae la VFC de los últimos días. Cada día es una llamada aparte, así que
    conviene pedir unas pocas semanas y no más.
    """
    import garmin_client

    serie, sin_datos, ejemplo = [], 0, None
    hoy = date.today()
    for i in range(dias):
        d = hoy - timedelta(days=i)
        crudo = garmin_client.obtener_hrv(client, d)
        interpretado = interpretar_dia(crudo)
        if interpretado:
            serie.append({"fecha": d, **interpretado})
        else:
            sin_datos += 1
            if crudo and ejemplo is None:
                ejemplo = crudo   # para diagnosticar un formato desconocido
    serie.sort(key=lambda x: x["fecha"])
    return {"serie": serie, "sin_datos": sin_datos, "crudo_ejemplo": ejemplo}


# ---------------------------------------------------------------------------
# 1. Línea de base y desviación
# ---------------------------------------------------------------------------

def linea_de_base(serie, ventana=7):
    """
    Agrega a cada día su línea de base (promedio de los días previos) y cuánto se
    aparta, en desviaciones estándar.

    El valor absoluto de la VFC no dice casi nada: depende de la edad, la
    genética y hasta de cómo te pusiste la banda. Lo que informa es el desvío
    respecto de TU propio promedio.
    """
    resultado = []
    for i, d in enumerate(serie):
        previos = [x["rmssd"] for x in serie[max(0, i - ventana):i]]
        base = sum(previos) / len(previos) if len(previos) >= 3 else None
        desvio = statistics.pstdev(previos) if len(previos) >= 3 else None
        z = ((d["rmssd"] - base) / desvio) if (base and desvio and desvio > 0.5) else None
        resultado.append({**d, "base": round(base, 1) if base else None,
                          "z": round(z, 2) if z is not None else None})
    return resultado


def estado_de_hoy(serie_con_base):
    """Resume cómo viene la VFC hoy respecto de la línea de base."""
    if not serie_con_base:
        return None
    hoy = serie_con_base[-1]
    if hoy.get("z") is None:
        return {**hoy, "lectura": "sin_base"}
    z = hoy["z"]
    if z <= -1.5:
        lectura = "muy_baja"
    elif z <= -0.75:
        lectura = "baja"
    elif z >= 1.0:
        lectura = "alta"
    else:
        lectura = "normal"
    return {**hoy, "lectura": lectura}


# ---------------------------------------------------------------------------
# 2. Eficiencia en sesiones comparables
# ---------------------------------------------------------------------------

def eficiencia_segun_vfc(sesiones, serie_con_base, perfil, minimo_por_grupo=3):
    """
    Compara el factor de eficiencia entre los días de VFC alta y los de VFC baja,
    DENTRO del mismo tipo de sesión.

    Ese "dentro del mismo tipo" es lo que hace válida la comparación: sin él, el
    resultado mediría qué sesión hiciste ese día en vez de cómo estabas.
    """
    import coach
    from datetime import datetime

    por_fecha = {d["fecha"]: d for d in serie_con_base if d.get("z") is not None}
    if not por_fecha:
        return None

    grupos = {}
    for s in sesiones:
        f = datetime.strptime(s["fecha"].split(" ")[0], "%Y-%m-%d").date()
        vfc = por_fecha.get(f)
        if not vfc:
            continue

        if s.get("ef"):
            ef, unidad = s["ef"], "W por latido"
        elif s.get("velocidad_kmh") and s.get("fc_prom"):
            ef, unidad = s["velocidad_kmh"] / s["fc_prom"] * 100, "km/h por 100 latidos"
        else:
            continue

        tipo = coach.clasificar_sesion(s, perfil)
        grupos.setdefault(tipo, {"alta": [], "baja": [], "unidad": unidad})
        if vfc["z"] >= 0.25:
            grupos[tipo]["alta"].append(ef)
        elif vfc["z"] <= -0.25:
            grupos[tipo]["baja"].append(ef)

    salida = []
    for tipo, g in grupos.items():
        if len(g["alta"]) < minimo_por_grupo or len(g["baja"]) < minimo_por_grupo:
            continue
        media_alta = sum(g["alta"]) / len(g["alta"])
        media_baja = sum(g["baja"]) / len(g["baja"])
        salida.append({
            "tipo": tipo,
            "n_alta": len(g["alta"]), "n_baja": len(g["baja"]),
            "ef_alta": round(media_alta, 2), "ef_baja": round(media_baja, 2),
            "diferencia_pct": round((media_alta - media_baja) / media_baja * 100, 1) if media_baja else None,
            "unidad": g["unidad"],
        })
    return salida or None


# ---------------------------------------------------------------------------
# 3. VFC contra la carga acumulada
# ---------------------------------------------------------------------------

def vfc_contra_carga(serie_con_base, historial_pmc):
    """
    Cruza la VFC con el TSB (frescura) del mismo día.

    Si tu VFC baja cuando el TSB se hunde, el modelo de carga describe bien tu
    fisiología. Si no se mueven juntos, alguno de los dos no te representa - y
    suele ser el modelo, que es genérico, no tu cuerpo.

    Nota técnica: acá se usa el valor absoluto de la VFC, no el desvío respecto de
    la línea de base. El desvío está pensado para detectar CAMBIOS, y se recalibra
    solo: en un bloque de carga largo, la línea de base baja junto con la VFC y el
    desvío vuelve a cero, justo cuando más deprimida está. Para cruzar contra el
    TSB -que sí es un nivel sostenido- hay que comparar niveles con niveles.
    """
    tsb_por_fecha = {d["fecha"]: d["tsb"] for d in historial_pmc}
    pares = [
        (d["rmssd"], tsb_por_fecha[d["fecha"]])
        for d in serie_con_base
        if d.get("rmssd") is not None and d["fecha"] in tsb_por_fecha
    ]
    if len(pares) < 10:
        return None

    zs = [p[0] for p in pares]
    tsbs = [p[1] for p in pares]
    mz, mt = sum(zs) / len(zs), sum(tsbs) / len(tsbs)
    num = sum((v - mz) * (t - mt) for v, t in pares)
    dz = sum((v - mz) ** 2 for v in zs) ** 0.5
    dt = sum((t - mt) ** 2 for t in tsbs) ** 0.5
    if dz == 0 or dt == 0:
        return None
    return {"correlacion": round(num / (dz * dt), 2), "n": len(pares)}
