# coach.py
"""
Análisis profundo de cada sesión, en lenguaje de entrenador.

A diferencia de feedback.py (que traduce números a frases cortas), este módulo
responde las preguntas que realmente importan después de entrenar:
  - ¿Qué tipo de estímulo fue esta sesión, en realidad?
  - ¿Qué adaptación fisiológica genera? (o sea: ¿qué mejoré con esto?)
  - ¿La ejecuté bien, o se me fue a la "zona gris"?
  - ¿Cómo viene comparada con mis sesiones parecidas de antes?
  - ¿Qué hago en las próximas 24-48 horas?

Cuando el perfil tiene datos de ergoespirometría (VT1 y VT2 medidos en
laboratorio), el análisis los usa directamente en vez de las zonas genéricas -
es bastante más preciso, porque VT1 y VT2 son los dos puntos fisiológicos que
de verdad separan los tipos de estímulo.
"""

from datetime import datetime

import config
import metrics


# ---------------------------------------------------------------------------
# Distribución por umbrales reales (modelo de 3 zonas)
# ---------------------------------------------------------------------------

def distribucion_por_umbrales(sesion, perfil):
    """
    Reparte los minutos de la sesión en los 3 dominios fisiológicos reales:
      - "baja"  : por debajo de VT1 (umbral aeróbico) -> trabajo aeróbico puro
      - "media" : entre VT1 y VT2 -> zona de tempo / umbral bajo
      - "alta"  : por encima de VT2 (umbral anaeróbico) -> trabajo intenso

    Este modelo de 3 zonas es el que se usa para evaluar si el entrenamiento
    está bien "polarizado", y es más informativo que las 5 zonas clásicas.

    Nota metodológica: Garmin entrega los minutos agrupados por zona, no
    segundo a segundo. Cuando un umbral cae en el medio de una zona, se reparte
    esa zona de forma proporcional al ancho de bpm que queda de cada lado. Es
    una aproximación, no un conteo exacto - pero para ver la forma general de
    la sesión funciona bien.

    Devuelve None si el perfil no tiene VT1/VT2 medidos.
    """
    test = perfil.get("test_fisiologico") or {}
    vt1 = test.get("vt1_fc")
    vt2 = test.get("vt2_fc")
    if not vt1 or not vt2:
        return None

    zonas = metrics.calcular_zonas_fc(perfil)
    minutos_zona = sesion.get("minutos_por_zona", {})

    resultado = {"baja": 0.0, "media": 0.0, "alta": 0.0}

    for z, minutos in minutos_zona.items():
        if not minutos:
            continue
        lo, hi = zonas.get(z, (None, None))
        if lo is None or hi <= lo:
            continue

        ancho = hi - lo
        # cuántos bpm de esta zona caen en cada dominio
        ancho_baja = max(0, min(hi, vt1) - lo)
        ancho_media = max(0, min(hi, vt2) - max(lo, vt1))
        ancho_alta = max(0, hi - max(lo, vt2))

        resultado["baja"] += minutos * (ancho_baja / ancho)
        resultado["media"] += minutos * (ancho_media / ancho)
        resultado["alta"] += minutos * (ancho_alta / ancho)

    total = sum(resultado.values())
    if total == 0:
        return None

    return {
        "minutos": {k: round(v, 1) for k, v in resultado.items()},
        "pct": {k: round(v / total * 100) for k, v in resultado.items()},
        "vt1": vt1,
        "vt2": vt2,
    }


def distribucion_3_dominios(sesion, perfil):
    """
    Igual que distribucion_por_umbrales(), pero nunca devuelve None: si no hay
    umbrales de laboratorio cargados, agrupa las 5 zonas clásicas.

    La usa la interfaz para dibujar la "cinta de umbrales" de cada sesión, que
    necesita siempre tener algo que mostrar. Devuelve además 'exacta' para poder
    aclarar en pantalla si viene de umbrales medidos o de zonas por fórmula.
    """
    d = distribucion_por_umbrales(sesion, perfil)
    if d:
        return {**d, "exacta": True}

    minutos = sesion.get("minutos_por_zona", {})
    total = sum(minutos.values())
    if not total:
        return None

    baja = minutos.get(1, 0) + minutos.get(2, 0)
    media = minutos.get(3, 0) + minutos.get(4, 0)
    alta = minutos.get(5, 0)

    return {
        "minutos": {"baja": round(baja, 1), "media": round(media, 1), "alta": round(alta, 1)},
        "pct": {
            "baja": round(baja / total * 100),
            "media": round(media / total * 100),
            "alta": round(alta / total * 100),
        },
        "vt1": None,
        "vt2": None,
        "exacta": False,
    }


# ---------------------------------------------------------------------------
# Clasificación del tipo de sesión
# ---------------------------------------------------------------------------

def clasificar_sesion(sesion, perfil):
    """
    Determina qué tipo de entrenamiento fue realmente esta sesión.

    Mira tres cosas, no una:
      1. Cuánto tiempo pasaste por encima de VT2.
      2. Cuánto de ese tiempo fue MUY por encima (la zona más alta), no apenas
         rozando el umbral.
      3. Qué pico de pulso alcanzaste respecto de tu máxima.

    --- Por qué hace falta el punto 2 ---
    La primera versión clasificaba solo por el tiempo sobre VT2, y eso metía
    casi todo en el cajón "umbral": una sesión que ronda los 163 bpm y otra que
    llega a 178 se veían idénticas, cuando fisiológicamente no tienen nada que
    ver. En una sesión de umbral el pulso oscila justo alrededor de VT2 —
    entrando y saliendo— así que acumula bastante "tiempo por encima" sin ser
    trabajo de VO2max. Lo que separa a las dos es cuán arriba llegás.
    """
    dur = sesion["duracion_min"]
    dist = distribucion_por_umbrales(sesion, perfil)
    minutos = sesion.get("minutos_por_zona", {})
    total_min = sum(minutos.values()) or 1

    if dist:
        pct_baja = dist["pct"]["baja"]
        pct_media = dist["pct"]["media"]
        pct_alta = dist["pct"]["alta"]
    else:
        # Respaldo sin umbrales de laboratorio: se agrupan las 5 zonas clásicas.
        # Z4 (umbral) cuenta como "media" y no como "alta", porque en el modelo
        # de 5 zonas el umbral anaeróbico cae dentro de Z4, no debajo.
        pct_baja = (minutos.get(1, 0) + minutos.get(2, 0)) / total_min * 100
        pct_media = (minutos.get(3, 0) + minutos.get(4, 0)) / total_min * 100
        pct_alta = minutos.get(5, 0) / total_min * 100

    # Tiempo en la zona más alta: el trabajo claramente por encima del umbral,
    # no el que apenas lo roza.
    pct_z5 = minutos.get(5, 0) / total_min * 100
    # Tiempo en la zona inmediatamente anterior, que es la parte alta de la
    # franja entre umbrales. Sirve para separar tempo de umbral: las dos cosas
    # caen entre VT1 y VT2, y lo que las distingue es en qué parte de esa franja
    # estuviste. Abajo es tempo, pegado a VT2 es umbral.
    pct_z4 = minutos.get(4, 0) / total_min * 100

    # Pico de pulso alcanzado, respecto de la máxima
    fc_max = calcular_fc_max_perfil(perfil)
    pico = sesion.get("fc_max_sesion")
    pct_pico = (pico / fc_max * 100) if (pico and fc_max) else None

    # --- VO2max: hace falta trabajo claramente arriba, no solo rozar el umbral ---
    if pct_z5 >= 12:
        return "vo2max"
    if pct_alta >= 18 and pct_pico and pct_pico >= 94:
        return "vo2max"
    if pct_alta >= 32:
        return "vo2max"

    # --- Umbral ---
    if pct_alta >= 10 or pct_z5 >= 5 or (pct_media >= 45 and pct_z4 >= 20):
        return "umbral"

    if pct_media >= 28:
        return "tempo"

    if pct_baja >= 75:
        if dur >= 150:
            return "fondo_largo"
        vt1 = (perfil.get("test_fisiologico") or {}).get("vt1_fc") or 999
        if dur <= 45 and sesion.get("fc_prom") and sesion["fc_prom"] < vt1 - 25:
            return "recuperacion"
        return "base"
    return "mixta_gris"


def calcular_fc_max_perfil(perfil):
    """FC máxima del perfil, medida o estimada."""
    return metrics.calcular_fc_max(perfil)


NOMBRE_TIPO = {
    "recuperacion": "Recuperación activa",
    "base": "Base aeróbica",
    "fondo_largo": "Fondo largo",
    "tempo": "Tempo",
    "umbral": "Umbral",
    "vo2max": "Alta intensidad / VO2max",
    "mixta_gris": "Mixta (sin un estímulo claro)",
}


# ---------------------------------------------------------------------------
# Qué mejoraste: adaptaciones fisiológicas por tipo de sesión
# ---------------------------------------------------------------------------

ADAPTACIONES = {
    "recuperacion": [
        "Acelerás el lavado de metabolitos y el flujo sanguíneo hacia las piernas cargadas, "
        "sin sumar fatiga nueva.",
        "Mantenés el gesto técnico del pedaleo y la movilidad, que es justamente lo que se pierde "
        "cuando uno para del todo.",
    ],
    "base": [
        "**Densidad mitocondrial**: más 'centrales energéticas' dentro de la fibra muscular, que es "
        "lo que te permite producir energía con oxígeno en vez de fermentar lactato.",
        "**Capilarización**: más capilares por fibra, o sea más superficie para entregar oxígeno y "
        "retirar desechos. Es una adaptación lenta pero muy duradera.",
        "**Oxidación de grasas**: entrenás al cuerpo a tirar más de grasa como combustible, "
        "ahorrando el glucógeno para cuando de verdad hace falta.",
        "**Volumen sistólico**: el corazón se llena más en cada latido. Esto es lo que con los meses "
        "te baja el pulso en reposo y te hace ir más rápido al mismo pulso.",
    ],
    "fondo_largo": [
        "Todo lo de una sesión de base, pero **potenciado por la duración**: las últimas horas son "
        "las que más estimulan la adaptación, porque ya entrás con glucógeno bajo.",
        "**Resistencia a la fatiga**: mejorás la capacidad de sostener potencia después de muchas "
        "horas, que es una cualidad distinta a tener buen umbral.",
        "**Economía de pedaleo**: a esta duración, el cuerpo optimiza el patrón motor y gastás menos "
        "energía para la misma velocidad.",
        "**Tolerancia digestiva y de hidratación**: se entrena, y es tan determinante como las piernas "
        "en salidas largas.",
    ],
    "tempo": [
        "**Aclaramiento de lactato**: mejorás la capacidad de reciclar el lactato como combustible en "
        "vez de acumularlo. Es el mecanismo que después te sostiene el umbral.",
        "**Resistencia muscular específica**: reclutás fibras rápidas (tipo IIa) manteniéndolas en "
        "modo aeróbico, que es como se las 'convierte' hacia un perfil más resistente.",
        "**Eficiencia al ritmo de marcha**: es el ritmo real de una salida grupal fuerte o de una "
        "subida sostenida.",
    ],
    "umbral": [
        "**Desplazamiento del umbral anaeróbico (VT2)**: la adaptación más valiosa para ir rápido en "
        "ruta. Corrés hacia arriba el punto en que empezás a acumular lactato.",
        "**Capacidad de amortiguación (buffering)**: más bicarbonato y transportadores de lactato, "
        "que te dejan tolerar más acidez sin bajar el ritmo.",
        "**Reclutamiento de fibras IIa en régimen aeróbico**: sumás músculo útil al motor aeróbico.",
        "**Potencia sostenible**: es el estímulo que más sube tu FTP, que es el número que te define "
        "el ritmo en una subida de 20-40 minutos.",
    ],
    "vo2max": [
        "**VO2max**: subís el techo de oxígeno que tu cuerpo puede consumir. Es la adaptación que más "
        "rápido responde en semanas, y también la que más rápido se pierde si dejás de estimularla.",
        "**Gasto cardíaco máximo**: el corazón mueve más sangre por minuto en el pico de esfuerzo.",
        "**Cinética del oxígeno**: llegás más rápido al régimen aeróbico cuando arranca el esfuerzo - "
        "te recuperás mejor entre repechos y ataques.",
        "**Capacidad anaeróbica (W')**: agrandás el 'tanque' de esfuerzos cortos por encima del umbral.",
    ],
    "mixta_gris": [
        "El estímulo quedó repartido sin un foco claro, así que las adaptaciones son parciales en "
        "varios frentes en lugar de fuertes en uno.",
    ],
}


ADAPTACIONES_RUNNING = {
    "recuperacion": [
        "Movés sangre y articulaciones sin agregar daño. En running esto importa más que en bici, "
        "porque el impacto no se recupera solo con estar quieto.",
    ],
    "base": [
        "**Densidad mitocondrial y capilarización**: las mismas adaptaciones aeróbicas de cualquier "
        "deporte de resistencia. Pero correr suma dos más, que son las importantes:",
        "**Rigidez tendinosa y resistencia ósea**: el tendón de Aquiles, la fascia y la tibia se "
        "adaptan al impacto repetido. Es una adaptación LENTA — de meses, no de semanas — y es la "
        "que evita las lesiones por sobrecarga.",
        "**Economía al correr** (cuánto oxígeno gastás para sostener un ritmo): mejorarla es el factor "
        "que más separa a dos corredores con el mismo VO2max.",
    ],
    "fondo_largo": [
        "**Resistencia a la fatiga muscular**: corriendo, la tirada larga entrena algo que la bici "
        "no toca — la capacidad del músculo de absorber impacto cuando ya está cansado. Es "
        "exactamente lo que se rompe en el km 32 de un maratón.",
        "**Uso de grasas y ahorro de glucógeno**, clave para cualquier distancia larga.",
        "**Tolerancia digestiva**: entrenar a comer y beber corriendo, que es bastante más difícil "
        "que sobre la bici.",
    ],
    "tempo": [
        "**Aclaramiento de lactato** y resistencia al ritmo de media maratón.",
        "**Fuerza específica de correr**: sostener la técnica cuando aparece la fatiga.",
    ],
    "umbral": [
        "**Desplazamiento del umbral**: subís el ritmo que podés sostener una hora. Es el predictor "
        "más directo del rendimiento en 10 km y media maratón.",
        "**Capacidad de amortiguación** frente a la acidez.",
    ],
    "vo2max": [
        "**VO2max y potencia aeróbica máxima**, el techo del sistema.",
        "**Reclutamiento neuromuscular y elasticidad**: mejora el rebote del tendón, y eso te hace "
        "más económico también a ritmos suaves.",
    ],
    "mixta_gris": [
        "El estímulo quedó repartido sin foco. En running esto se paga doble, porque el impacto se "
        "acumula igual aunque la adaptación sea mediocre.",
    ],
}


def _nota_running_masters(tipo, sesion, perfil):
    """Contexto de impacto y recuperación, específico de correr después de los 45."""
    if tipo in ("base", "fondo_largo"):
        return (
            "> 🧓 **Correr a los 48:** el sistema cardiovascular se adapta en semanas, pero tendones "
            "y huesos tardan meses. Esa diferencia de velocidad es la causa número uno de lesiones "
            "en corredores que vienen del ciclismo: el corazón te deja subir el volumen mucho antes "
            "de que las piernas estén listas. Subí los kilómetros semanales de a poco aunque te "
            "sobre aire."
        )
    if tipo in ("umbral", "vo2max"):
        return (
            "> 🧓 **Correr a los 48:** una sesión intensa de running deja más daño muscular que una "
            "de bici de igual intensidad, por el impacto. Dejá 48-72 h antes de otra fuerte, y si "
            "podés metelas en superficie blanda."
        )
    return ""


# ---------------------------------------------------------------------------
# Comparación con sesiones similares anteriores
# ---------------------------------------------------------------------------

def _parse_fecha(s):
    return datetime.strptime(s.split(" ")[0], "%Y-%m-%d").date()


def comparar_con_similares(sesion, todas_las_sesiones, perfil):
    """
    Busca sesiones anteriores del mismo tipo y compara para ver progresión.
    Es la forma más honesta de responder "¿mejoré?": compararte con vos mismo
    haciendo algo parecido, no contra una tabla genérica.

    Devuelve un dict con los datos de comparación, o None si no hay historial
    suficiente del mismo tipo.
    """
    tipo_actual = clasificar_sesion(sesion, perfil)
    fecha_actual = _parse_fecha(sesion["fecha"])

    similares = []
    for s in todas_las_sesiones:
        if s["id"] == sesion["id"]:
            continue
        if _parse_fecha(s["fecha"]) >= fecha_actual:
            continue
        if clasificar_sesion(s, perfil) != tipo_actual:
            continue
        # Solo se compara contra la misma superficie. Sin este filtro, una salida
        # de ruta se comparaba con una de MTB y el resultado era "fuiste más
        # lento" cuando lo único que cambió fue el terreno: en montaña se anda
        # más lento al mismo esfuerzo, y eso no es perder forma.
        if s.get("superficie") != sesion.get("superficie"):
            continue
        # que la duración sea comparable (+-40%)
        if not (0.6 * sesion["duracion_min"] <= s["duracion_min"] <= 1.4 * sesion["duracion_min"]):
            continue
        similares.append(s)

    if len(similares) < 2:
        return None

    similares = sorted(similares, key=lambda s: s["fecha"])[-6:]

    def promedio(campo):
        vals = [s[campo] for s in similares if s.get(campo)]
        return sum(vals) / len(vals) if vals else None

    resultado = {
        "tipo": tipo_actual,
        "superficie": sesion.get("superficie"),
        "n": len(similares),
        "vel_previa": promedio("velocidad_kmh"),
        "fc_previa": promedio("fc_prom"),
        "ef_previo": promedio("ef"),
        "pot_previa": promedio("potencia_prom"),
    }
    return resultado


# ---------------------------------------------------------------------------
# Análisis profundo (la función principal)
# ---------------------------------------------------------------------------

def analisis_profundo(sesion, perfil, todas_las_sesiones=None, historial_pmc=None):
    """
    Devuelve el análisis completo de la sesión en markdown, listo para mostrar.
    """
    bloques = []
    tipo = clasificar_sesion(sesion, perfil)
    dist = distribucion_por_umbrales(sesion, perfil)
    dur = sesion["duracion_min"]

    # ---------- 1. Qué tipo de sesión fue ----------
    bloques.append(f"### 🏷️ Qué fue esta sesión: **{NOMBRE_TIPO[tipo]}**")
    bloques.append(_descripcion_tipo(tipo, sesion, dist))

    # ---------- 2. Cómo la ejecutaste ----------
    bloques.append("### 🎯 Cómo la ejecutaste")
    bloques.append(_analisis_ejecucion(sesion, perfil, dist, tipo))

    # ---------- 3. Qué mejoraste ----------
    bloques.append("### 💪 Qué mejoraste con esto")
    es_running = sesion.get("deporte") == "running"
    tabla = ADAPTACIONES_RUNNING if es_running else ADAPTACIONES
    bloques.append("\n".join(f"- {a}" for a in tabla.get(tipo, [])))
    bloques.append(
        _nota_running_masters(tipo, sesion, perfil) if es_running
        else _nota_adaptacion_masters(tipo, dur)
    )

    # ---------- 4. Progresión ----------
    if todas_las_sesiones:
        comparacion = comparar_con_similares(sesion, todas_las_sesiones, perfil)
        texto_prog = _texto_progresion(sesion, comparacion)
        if texto_prog:
            bloques.append("### 📈 Comparado con tus sesiones parecidas")
            bloques.append(texto_prog)

    # ---------- 5. Recuperación y qué sigue ----------
    bloques.append("### 🔄 Recuperación y qué hacer ahora")
    bloques.append(_plan_recuperacion(tipo, sesion, perfil, historial_pmc))

    bloques.append(_nota_comparacion_reloj(sesion, perfil))

    return "\n\n".join(b for b in bloques if b)


def _nota_comparacion_reloj(sesion, perfil):
    """
    Explica por qué el reloj puede decir otra cosa. Aparece solo en sesiones con
    algo de intensidad, que es donde las dos lecturas se separan.
    """
    minutos = sesion.get("minutos_por_zona", {})
    total = sum(minutos.values()) or 1
    if (minutos.get(4, 0) + minutos.get(5, 0)) / total * 100 < 8:
        return ""

    return (
        "---\n\n"
        "<details><summary><b>¿Tu reloj dice otra cosa?</b></summary>\n\n"
        "**La carga no es comparable.** Garmin calcula la suya con EPOC (el oxígeno extra que tu "
        "cuerpo consume después de entrenar) mediante un modelo propio de Firstbeat. Acá se usa "
        "TRIMP, que suma los minutos en cada zona multiplicados por su intensidad. Son dos escalas "
        "distintas: que una diga 264 y la otra 308 no significa que alguna esté mal, igual que 20 °C "
        "y 68 °F son la misma temperatura. Lo que importa es que cada número sea coherente consigo "
        "mismo a lo largo del tiempo.\n\n"
        "**El tipo de sesión puede diferir.** Tu reloj usa más señales que las que hay acá: consumo "
        "de oxígeno estimado, efecto de entrenamiento aeróbico y anaeróbico por separado, y la "
        "variabilidad latido a latido. Esta app clasifica con lo que se puede leer del resumen — el "
        "tiempo en cada zona y el pico de pulso — usando tus umbrales de laboratorio, que el reloj "
        "no conoce salvo que se los cargues.\n\n"
        "Cuando no coinciden, ninguna de las dos está necesariamente equivocada: miran cosas "
        "distintas. Si querés una sola verdad, quedate con la de tu reloj para la carga —tiene más "
        "sensores— y con esta para la lectura fisiológica, que sí está calibrada con tu "
        "ergoespirometría.</details>"
    )


def _descripcion_tipo(tipo, sesion, dist):
    dur = sesion["duracion_min"]
    trimp = sesion["trimp"]

    running = sesion.get("deporte") == "running"

    base = {
        "recuperacion": (
            "Una sesión corta y suave, por debajo de tu umbral aeróbico. No busca generar adaptación "
            "nueva, sino ayudar a que la generen las sesiones fuertes de alrededor."
        ),
        "base": (
            ("El rodaje de todos los días: la mayor parte del tiempo por debajo de tu umbral aeróbico. "
             "Es el kilometraje que construye el motor y, sobre todo, el que va endureciendo tendones "
             "y huesos para aguantar los entrenamientos fuertes.")
            if running else
            ("El pan de cada día del ciclismo de resistencia: la mayor parte del tiempo por debajo de "
             "tu umbral aeróbico. Poco costo de fatiga, alto retorno acumulado a lo largo de los meses.")
        ),
        "fondo_largo": (
            ("La tirada larga. Acá la duración *es* el estímulo: los últimos kilómetros valen mucho más "
             "que los primeros, porque llegás con las reservas bajas y las piernas ya castigadas — que "
             "es exactamente la situación de los últimos kilómetros de una carrera larga.")
            if running else
            ("Una salida larga de base. En este tipo de sesión, la duración *es* el estímulo: las últimas "
             "horas valen mucho más que las primeras, porque entrás con las reservas más bajas.")
        ),
        "tempo": (
            "Trabajo en la franja entre tus dos umbrales. Cansa bastante más que la base, pero desarrolla "
            "cualidades que la base sola no toca."
        ),
        "umbral": (
            "Trabajo alrededor de tu umbral anaeróbico. Este es el estímulo que más directamente sube tu "
            "capacidad de sostener ritmo fuerte por mucho tiempo."
        ),
        "vo2max": (
            "Sesión de alta intensidad, con tiempo significativo por encima de tu umbral anaeróbico. Es el "
            "estímulo más potente que existe para subir el techo aeróbico, y también el más caro en fatiga."
        ),
        "mixta_gris": (
            "El esfuerzo quedó repartido sin un foco definido, con bastante tiempo en la franja intermedia. "
            "Es el patrón clásico de 'salir a rodar sin plan': no llega a ser suficientemente suave para "
            "recuperar, ni suficientemente fuerte para generar una adaptación potente."
        ),
    }[tipo]

    detalle = f"Duración: **{dur:.0f} min** · Carga de la sesión (TRIMP): **{trimp:.0f}**."
    detalle += (
        "  \n*Si tu reloj muestra otro número de carga y a veces otro tipo de sesión, es esperable: "
        "no miden lo mismo. Ver la nota al final.*"
    )
    sup = sesion.get("superficie")
    if sup in ("MTB", "Gravel"):
        detalle += (
            f" Fue en **{sup}**: la velocidad y el VAM no son comparables con los de ruta al mismo "
            "esfuerzo, así que la app solo te compara contra otras salidas en la misma superficie."
        )

    if sesion.get("bajo_techo"):
        detalle += (
            " Fue **bajo techo** (rodillo o cinta): sin viento que te refrigere, el pulso corre "
            "unas pulsaciones más alto que afuera al mismo esfuerzo, así que la sesión pesa un "
            "poco más de lo que dicen los números."
        )
    if dist:
        p = dist["pct"]
        detalle += (
            f" Distribución real según tus umbrales de laboratorio: "
            f"**{p['baja']}%** por debajo de VT1 ({dist['vt1']} bpm), "
            f"**{p['media']}%** entre VT1 y VT2, "
            f"**{p['alta']}%** por encima de VT2 ({dist['vt2']} bpm)."
        )
    return base + "\n\n" + detalle


def _analisis_ejecucion(sesion, perfil, dist, tipo):
    notas = []

    # Calidad de la ejecución según el tipo
    if dist:
        p = dist["pct"]
        if tipo in ("base", "fondo_largo"):
            if p["media"] + p["alta"] <= 15:
                notas.append(
                    "✅ **Muy bien ejecutada.** Te mantuviste disciplinadamente por debajo de VT1, que es "
                    "exactamente lo que hay que hacer en una sesión de base. El error más común acá es ir "
                    "un poquito más fuerte de la cuenta 'porque me siento bien', y eso arruina tanto la "
                    "adaptación aeróbica como la recuperación para la sesión de calidad."
                )
            elif p["media"] + p["alta"] <= 30:
                notas.append(
                    "⚠️ Se te escapó algo de tiempo por encima de VT1. No es grave, y en terreno ondulado "
                    "es casi inevitable en los repechos. Pero si podés, en las de base tratá de dejar "
                    "cambio y bajar cadencia en las subidas cortas para no cruzar el umbral."
                )
            else:
                notas.append(
                    "⚠️ **Se fue bastante de intensidad para ser una sesión de base.** Cruzaste VT1 en un "
                    "tercio o más del tiempo. El costo: sumás fatiga como si fuera una sesión de calidad, "
                    "pero sin el estímulo concentrado que la haría valer la pena."
                )
        elif tipo in ("umbral", "vo2max"):
            if p["baja"] >= 40:
                notas.append(
                    "✅ Buena estructura: bastante tiempo suave entre los esfuerzos fuertes. Esa recuperación "
                    "entre series es la que te permite dar calidad en cada repetición en vez de arrastrarte."
                )
            else:
                notas.append(
                    "⚠️ Poco tiempo de recuperación entre los esfuerzos duros. Si el objetivo era hacer series "
                    "de calidad, con más recuperación entre repeticiones podrías sostener mejor potencia en "
                    "cada una - y el estímulo termina siendo mayor, aunque parezca contradictorio."
                )
        elif tipo == "mixta_gris":
            notas.append(
                "⚠️ **Zona gris.** Este es el patrón que a más deportistas amateur les frena el progreso: "
                "acumulás fatiga considerable a cambio de una adaptación mediocre. La alternativa que "
                "funciona mejor es el modelo polarizado: que la mayoría de tus sesiones sean claramente "
                "suaves (bajo VT1) y unas pocas claramente fuertes (sobre VT2)."
            )
    else:
        # Sin umbrales de laboratorio: análisis equivalente con las 5 zonas clásicas
        minutos = sesion.get("minutos_por_zona", {})
        total = sum(minutos.values())
        if total:
            pct_z12 = (minutos.get(1, 0) + minutos.get(2, 0)) / total * 100
            pct_z3 = minutos.get(3, 0) / total * 100
            pct_z45 = (minutos.get(4, 0) + minutos.get(5, 0)) / total * 100
            notas.append(
                f"Repartiste el tiempo así: **{pct_z12:.0f}%** en Z1-Z2 (suave), "
                f"**{pct_z3:.0f}%** en Z3 (tempo), **{pct_z45:.0f}%** en Z4-Z5 (fuerte)."
            )
            if tipo in ("base", "fondo_largo") and pct_z3 + pct_z45 > 25:
                notas.append(
                    "⚠️ Para una sesión de base, se te fue bastante tiempo por encima de Z2. Ojo con el "
                    "costo: sumás fatiga sin el beneficio concentrado de una sesión de calidad."
                )
            elif tipo == "mixta_gris":
                notas.append(
                    "⚠️ **Zona gris.** Mucho tiempo en la franja intermedia: bastante fatiga a cambio de una "
                    "adaptación difusa. Conviene que las suaves sean más suaves y las fuertes más fuertes."
                )
            notas.append(
                "*Nota: este análisis usa zonas calculadas por fórmula. Con una ergoespirometría que mida "
                "tus umbrales reales (VT1/VT2), el análisis sería bastante más preciso.*"
            )

    # Ritmo de carrera
    if sesion.get("deporte") == "running":
        if sesion.get("ritmo_texto"):
            linea = f"**Ritmo: {sesion['ritmo_texto']}**"
            if sesion.get("ritmo_gap_texto"):
                linea += (
                    f" — equivalente a **{sesion['ritmo_gap_texto']}** en llano, corrigiendo por el "
                    "desnivel. Ese segundo número es el que sirve para compararte con tus sesiones "
                    "de asfalto."
                )
            notas.append(linea)

        neg = sesion.get("desnivel_neg_m")
        if neg and neg > 300:
            notas.append(
                f"**Bajaste {neg:.0f} metros.** En trail el desnivel negativo importa tanto como el "
                "positivo, y se subestima siempre: bajar produce contracción excéntrica, que es la "
                "que rompe fibras y te deja las piernas destruidas al día siguiente. Subir cansa el "
                "motor; bajar rompe el músculo. Si vas a competir en montaña, entrená las bajadas "
                "expresamente — es la única forma de que las piernas aprendan a tolerarlas."
            )

        cad_run = sesion.get("cadencia_prom")
        if cad_run:
            if cad_run < 160:
                notas.append(
                    f"**Cadencia {cad_run:.0f} pasos/min** — baja. Una cadencia baja suele significar "
                    "zancada larga y más impacto en cada apoyo, justo lo que conviene evitar a los 48 "
                    "y viniendo del ciclismo. Probá subir 5 pasos por minuto por vez, sin cambiar el ritmo."
                )
            elif cad_run <= 185:
                notas.append(f"**Cadencia {cad_run:.0f} pasos/min** — en el rango eficiente, buen apoyo.")
            else:
                notas.append(f"**Cadencia {cad_run:.0f} pasos/min** — bien alta, zancada corta y ágil.")
        return "\n\n".join(notas) if notas else "Sin observaciones particulares sobre la ejecución."

    # Cadencia (bici)
    cad = sesion.get("cadencia_prom")
    if cad:
        if cad < 75:
            notas.append(
                f"**Cadencia {cad:.0f} rpm** - baja. A los 48, pedalear pesado le carga más las rodillas y "
                "los tendones, y recluta más fibra rápida (o sea, más fatiga muscular para el mismo trabajo). "
                "Probá subir 5-8 rpm en las sesiones suaves, cuesta un par de semanas acostumbrarse."
            )
        elif cad <= 95:
            notas.append(f"**Cadencia {cad:.0f} rpm** - en un rango eficiente y amable con las articulaciones.")
        else:
            notas.append(f"**Cadencia {cad:.0f} rpm** - bien ágil, buen reclutamiento del sistema cardiovascular por sobre el muscular.")

    # Control cardíaco vs FC máxima real
    fcmax_sesion = sesion.get("fc_max_sesion")
    test = perfil.get("test_fisiologico") or {}
    fcmax_real = test.get("fc_max_medida")
    if fcmax_sesion and fcmax_real:
        pct = fcmax_sesion / fcmax_real * 100
        notas.append(
            f"**Pico de FC: {fcmax_sesion} bpm** ({pct:.0f}% de tu máxima real medida de {fcmax_real})."
        )

    return "\n\n".join(notas) if notas else "Sin observaciones particulares sobre la ejecución."


def _nota_adaptacion_masters(tipo, dur):
    """Contexto específico para un ciclista de 48 años."""
    if tipo == "vo2max":
        return (
            "> 🧓 **A tus 48:** este tipo de estímulo sigue siendo muy efectivo (la capacidad de mejorar "
            "el VO2max no desaparece con la edad), pero la *recuperación* sí se enlentece. Una sesión así "
            "por semana rinde más que dos mal recuperadas."
        )
    if tipo == "umbral":
        return (
            "> 🧓 **A tus 48:** el trabajo de umbral es probablemente el de mejor relación beneficio/fatiga "
            "para vos. Genera casi tanta mejora de rendimiento como el VO2max, con bastante menos costo de "
            "recuperación."
        )
    if tipo in ("base", "fondo_largo"):
        return (
            "> 🧓 **A tus 48:** este es el trabajo que más se sostiene en el tiempo y el que menos se pierde. "
            "Con 3-4 días de bici por semana, que la mayoría sean de este tipo es la estrategia correcta."
        )
    return ""


def _texto_progresion(sesion, comparacion):
    if not comparacion:
        sup_actual = sesion.get("superficie")
        aclaracion = (
            f" Ojo que solo se compara contra sesiones en **{sup_actual}**: la velocidad en MTB y en "
            "ruta no son comparables al mismo esfuerzo, así que mezclarlas daría conclusiones falsas."
            if sup_actual else ""
        )
        return (
            "Todavía no tengo suficientes sesiones parecidas anteriores como para comparar progresión. "
            "Después de 3-4 sesiones más del mismo tipo, esta sección te va a mostrar si estás mejorando."
            + aclaracion
        )

    sup = comparacion.get("superficie")
    detalle_sup = f" en **{sup}**" if sup else ""
    lineas = [
        f"Comparado con tus últimas **{comparacion['n']} sesiones de tipo "
        f"{NOMBRE_TIPO[comparacion['tipo']]}**{detalle_sup} de duración parecida:"
    ]

    # Velocidad a igual FC = el indicador más claro de mejora aeróbica
    vel_actual = sesion.get("velocidad_kmh")
    vel_previa = comparacion.get("vel_previa")
    fc_actual = sesion.get("fc_prom")
    fc_previa = comparacion.get("fc_previa")

    if vel_actual and vel_previa and fc_actual and fc_previa:
        d_vel = vel_actual - vel_previa
        d_fc = fc_actual - fc_previa
        lineas.append(
            f"- Velocidad: **{vel_actual:.1f} km/h** vs {vel_previa:.1f} km/h de promedio ({d_vel:+.1f})"
        )
        lineas.append(f"- FC promedio: **{fc_actual} bpm** vs {fc_previa:.0f} bpm de promedio ({d_fc:+.0f})")

        if d_vel > 0.4 and d_fc < 2:
            lineas.append(
                "  \n  🟢 **Buena señal:** fuiste más rápido sin que te costara más pulso. Eso es literalmente "
                "la definición de mejorar la eficiencia aeróbica."
            )
        elif d_vel < -0.4 and d_fc > 2:
            lineas.append(
                "  \n  🟠 Fuiste más lento y con más pulso. Una sesión aislada así no significa nada (viento, "
                "calor, sueño, estrés, un día pesado). Si se repite 2-3 veces seguidas, ahí sí vale la pena "
                "bajar la carga unos días."
            )
        elif abs(d_vel) <= 0.4 and abs(d_fc) <= 2:
            lineas.append("  \n  ⚪ Rendimiento estable respecto a tus sesiones parecidas.")

    ef_actual = sesion.get("ef")
    ef_previo = comparacion.get("ef_previo")
    if ef_actual and ef_previo:
        d_ef = ef_actual - ef_previo
        lineas.append(
            f"- Factor de Eficiencia: **{ef_actual:.2f}** vs {ef_previo:.2f} de promedio ({d_ef:+.2f} W/bpm)"
        )
        if d_ef > 0.05:
            lineas.append("  \n  🟢 Tu EF viene subiendo: producís más vatios por cada latido. Es el indicador más directo de mejora del motor aeróbico.")

    return "\n".join(lineas)


def _plan_recuperacion(tipo, sesion, perfil, historial_pmc):
    running = sesion.get("deporte") == "running"
    horas = {
        "recuperacion": 0,
        "base": 12,
        "fondo_largo": 36,
        "tempo": 24,
        "umbral": 36,
        "vo2max": 48,
    }.get(tipo, 24)

    lineas = []

    suave = "un rodaje suave" if running else "bici suave"
    if horas == 0:
        lineas.append(
            "**Costo de recuperación: prácticamente nulo.** Podés entrenar normalmente mañana, incluido gym."
        )
    elif horas <= 12:
        lineas.append(
            "**Costo de recuperación: bajo.** Mañana podés hacer cualquier cosa: entrenar, gym de piernas "
            "pesado, o una sesión de calidad. Esta sesión no te condiciona."
        )
    elif horas <= 24:
        lineas.append(
            f"**Costo de recuperación: moderado (~24 h).** Mañana está bien hacer {suave} o gym de tren "
            "superior. Si querés meter una sesión fuerte o piernas pesadas, mejor pasado mañana."
        )
    else:
        aclaracion = (
            " Corriendo, además, el daño muscular del impacto tarda más en irse que la fatiga cardiovascular: "
            "podés sentirte con aire y tener las piernas todavía castigadas."
            if running else ""
        )
        lineas.append(
            f"**Costo de recuperación: alto (~{horas} h).** Las próximas dos sesiones conviene que sean "
            "suaves, o directamente descanso. Si tenías gym de piernas planeado para mañana, considerá "
            "moverlo o hacerlo liviano - el músculo ya recibió un estímulo fuerte hoy." + aclaracion
        )

    # Nutrición post-sesión, relevante según la duración/intensidad
    dur = sesion["duracion_min"]
    if dur >= 90 or tipo in ("umbral", "vo2max", "fondo_largo"):
        lineas.append(
            "**Ventana post-entreno:** en las próximas 1-2 horas, apuntá a una comida con hidratos + proteína "
            "(del orden de 20-30 g de proteína). A los 48 la síntesis proteica responde algo menos que a los 25, "
            "así que no saltear esto es más importante ahora que antes."
        )

    # Contexto del estado de forma
    if historial_pmc:
        tsb = historial_pmc[-1]["tsb"]
        if tsb < -15:
            lineas.append(
                f"⚠️ **Ojo con el contexto:** tu TSB está en {tsb:.0f}, o sea que venís acumulando bastante "
                "fatiga de los días previos. Sumado a esta sesión, sería prudente que los próximos 2 días "
                "sean claramente suaves."
            )
        elif tsb > 10:
            lineas.append(
                f"Tu TSB está en {tsb:.0f} (venías fresco), así que tenías margen para absorber bien esta sesión."
            )

    # Sugerencia de la próxima sesión
    if running:
        siguiente = {
            "recuperacion": "Un rodaje suave o la sesión de calidad de la semana, según cómo vengas.",
            "base": "Otro rodaje suave, o la sesión de calidad si te sentís fresco.",
            "fondo_largo": "Descanso o un trote muy suave. Nada de intensidad hasta que las piernas estén limpias.",
            "tempo": "Rodaje suave. Dejá al menos 48 h antes de otro trabajo intenso.",
            "umbral": "Rodaje suave o descanso. La próxima de calidad, en 48-72 h.",
            "vo2max": "Trote regenerativo o descanso. No repitas alta intensidad antes de 48-72 h.",
            "mixta_gris": "Definí el objetivo de la próxima: o claramente suave, o claramente fuerte.",
        }.get(tipo)
    else:
        siguiente = {
            "recuperacion": "Una sesión de base o de calidad, según cómo venga tu semana.",
            "base": "Podés encadenar otra de base, o meter la sesión de calidad de la semana si te sentís fresco.",
            "fondo_largo": "Descanso o recuperación activa muy suave. Después, base.",
            "tempo": "Base suave. Dejá al menos 48 h antes de otro trabajo intenso.",
            "umbral": "Base suave o descanso. La próxima de calidad, en 48-72 h.",
            "vo2max": "Recuperación activa o descanso. No repitas alta intensidad antes de 48-72 h.",
            "mixta_gris": "Definí el objetivo de la próxima: o claramente suave, o claramente fuerte.",
        }.get(tipo)
    if siguiente:
        lineas.append(f"**Próxima sesión sugerida:** {siguiente}")

    return "\n\n".join(lineas)


# ---------------------------------------------------------------------------
# Distribución de intensidad del periodo (¿estás polarizado?)
# ---------------------------------------------------------------------------

def analisis_distribucion_periodo(sesiones, perfil, dias=28):
    """
    Analiza si tu distribución de intensidad de las últimas semanas sigue un
    modelo polarizado (mucho suave + algo de fuerte, poco en el medio), que es
    el que mejor evidencia tiene para ciclistas de resistencia.
    """
    from datetime import date, timedelta

    limite = date.today() - timedelta(days=dias)
    recientes = [s for s in sesiones if _parse_fecha(s["fecha"]) >= limite]
    if not recientes:
        return None

    total = {"baja": 0.0, "media": 0.0, "alta": 0.0}
    con_umbrales = False
    for s in recientes:
        d = distribucion_por_umbrales(s, perfil)
        if d:
            con_umbrales = True
            for k in total:
                total[k] += d["minutos"][k]

    if not con_umbrales:
        return None

    suma = sum(total.values())
    if suma == 0:
        return None

    pct = {k: round(v / suma * 100) for k, v in total.items()}

    texto = (
        f"En los últimos {dias} días, tu tiempo de entrenamiento se repartió así: "
        f"**{pct['baja']}%** por debajo de VT1, **{pct['media']}%** entre VT1 y VT2, "
        f"**{pct['alta']}%** por encima de VT2."
    )

    if pct["baja"] >= 75 and pct["alta"] >= 5:
        texto += (
            "\n\n🟢 **Distribución polarizada, muy bien.** Es el patrón que mejor funciona en ciclismo de "
            "resistencia: gran base de volumen suave, con una dosis chica pero real de intensidad. Seguí así."
        )
    elif pct["baja"] >= 80 and pct["alta"] < 5:
        texto += (
            "\n\n🟡 **Base muy sólida, pero falta intensidad.** Tenés un volumen aeróbico envidiable, pero casi "
            "nada por encima de VT2. Agregar una sola sesión de calidad por semana (series de umbral o VO2max) "
            "probablemente te dé el salto de rendimiento más grande disponible ahora mismo."
        )
    elif pct["media"] >= 30:
        texto += (
            "\n\n🟠 **Demasiado tiempo en la zona intermedia.** Estás pasando mucho tiempo entre VT1 y VT2 - la "
            "famosa 'zona gris'. Es el punto donde más fatiga se acumula por unidad de adaptación. Te conviene "
            "hacer tus sesiones suaves más suaves, y concentrar la intensidad en menos sesiones pero más fuertes."
        )
    else:
        texto += (
            "\n\n⚪ Distribución razonable. Como referencia, el patrón que mejor evidencia tiene es alrededor de "
            "80% por debajo de VT1 y 15-20% por encima de VT2, con poco tiempo en el medio."
        )

    return {"pct": pct, "texto": texto}


# ---------------------------------------------------------------------------
# Lectura conjunta del estado de forma y preparación para una carrera
# ---------------------------------------------------------------------------
# Nota de calibración importante: los umbrales de TSB que circulan en la
# literatura (por ejemplo "corré con TSB entre +5 y +25") están calculados sobre
# TSS de potenciómetro. Acá la carga se mide con TRIMP de frecuencia cardíaca, que
# da números bastante más altos para la misma sesión, así que esos umbrales NO se
# pueden trasladar tal cual. Por eso todo lo que sigue se calibra contra el propio
# historial del ciclista: "alto para vos" en vez de "alto según un libro".

def rango_propio_tsb(historial_pmc, dias_minimos=30):
    """
    Calcula el rango habitual de TSB de esta persona, para poder decir si hoy está
    fresco o cargado *en relación a sí misma*.

    Ignora los primeros 30 días del historial porque el modelo arranca en cero y
    hasta que se estabiliza da valores que no representan nada real.
    """
    if len(historial_pmc) < dias_minimos + 14:
        return None

    valores = sorted(d["tsb"] for d in historial_pmc[dias_minimos:])
    if len(valores) < 14:
        return None

    def percentil(p):
        i = max(0, min(len(valores) - 1, int(round(p / 100 * (len(valores) - 1)))))
        return valores[i]

    return {
        "min": valores[0],
        "p25": percentil(25),
        "mediana": percentil(50),
        "p75": percentil(75),
        "p90": percentil(90),
        "max": valores[-1],
        "n_dias": len(valores),
    }


def explicar_estado_conjunto(historial_pmc):
    """
    Explica qué dicen Fitness, Fatiga y Forma leídos EN CONJUNTO, que es la única
    forma en que significan algo. Un mismo TSB puede ser una buena o una mala
    noticia según si tu Fitness viene subiendo o cayéndose.
    """
    hoy = historial_pmc[-1]
    ctl, tsb = hoy["ctl"], hoy["tsb"]

    ctl_hace_28 = historial_pmc[-29]["ctl"] if len(historial_pmc) >= 29 else None
    tendencia = None
    if ctl_hace_28 is not None:
        delta = ctl - ctl_hace_28
        if delta > 2:
            tendencia = "subiendo"
        elif delta < -2:
            tendencia = "bajando"
        else:
            tendencia = "estable"

    rango = rango_propio_tsb(historial_pmc)

    partes = []

    # 1. Qué es cada número, en una línea
    partes.append(
        "**Fitness** es cuánto entrenaste de forma sostenida en las últimas semanas: "
        "el tamaño de tu motor. **Fatiga** es el cansancio acumulado de los últimos días. "
        "**Forma** es la resta de los dos: cuánta de esa base tenés hoy disponible para rendir."
    )

    # 2. Lectura conjunta: los cuatro cuadrantes que importan
    fresco = rango is not None and tsb >= rango["p75"]
    cargado = rango is not None and tsb <= rango["p25"]

    if tendencia == "subiendo" and cargado:
        partes.append(
            "**Estás en plena construcción.** Tu motor crece y estás pagando el precio en cansancio. "
            "Es exactamente lo que tiene que pasar en un bloque de carga: no es momento de esperar "
            "buenas sensaciones, es momento de acumular. Si además de cansado te sentís mal muchos "
            "días seguidos, ahí sí conviene bajar."
        )
    elif tendencia == "subiendo" and fresco:
        partes.append(
            "**El mejor escenario posible.** Tu motor viene creciendo y encima estás descansado. "
            "Es la ventana ideal para una sesión muy exigente, un test, o una competencia."
        )
    elif tendencia == "bajando" and fresco:
        partes.append(
            "**Estás descansado, pero perdiendo base.** Típico de una semana de descarga, unas "
            "vacaciones o una lesión. Está bien si es a propósito y por poco tiempo; si se estira "
            "varias semanas, el motor se achica y las buenas sensaciones no compensan."
        )
    elif tendencia == "bajando" and cargado:
        partes.append(
            "**La combinación a evitar:** perdés base y encima estás cansado. Suele pasar cuando el "
            "entrenamiento se vuelve irregular — pocas sesiones, pero las que hay son duras. "
            "Más constancia y menos intensidad daría vuelta las dos cosas."
        )
    elif tendencia == "estable":
        partes.append(
            "**Estás en mantenimiento.** Tu base se sostiene sin crecer. Es un buen lugar para "
            "quedarse en temporada de competencia, o si querés sostener lo logrado sin sumar carga."
        )

    # 3. Dónde cae el TSB de hoy dentro del rango propio
    if rango:
        if tsb >= rango["p90"]:
            ubicacion = "entre los días más frescos que tuviste"
        elif tsb >= rango["p75"]:
            ubicacion = "en la parte fresca de tu rango habitual"
        elif tsb >= rango["p25"]:
            ubicacion = "en tu rango normal de entrenamiento"
        else:
            ubicacion = "entre los días más cargados que tuviste"

        partes.append(
            f"Tu Forma de hoy ({tsb:+.0f}) está **{ubicacion}**. En los últimos "
            f"{rango['n_dias']} días te movés entre {rango['min']:+.0f} y {rango['max']:+.0f}, "
            f"con la mitad de los días alrededor de {rango['mediana']:+.0f}."
        )
        partes.append(
            "> Este es el punto importante: los números de Forma que se citan en libros y foros "
            "están calculados con potenciómetro (TSS), y acá la carga se mide con pulso (TRIMP), "
            "que da valores más altos. Así que no compares tu Forma contra tablas de internet — "
            "comparala contra tu propio historial, que es lo que hace esta app."
        )
    else:
        partes.append(
            "Todavía no tengo suficiente historial como para decirte si este valor de Forma es alto "
            "o bajo *para vos*. Con unas 6 semanas de datos, esta sección se vuelve mucho más útil."
        )

    return "\n\n".join(partes)


def proyectar(historial_pmc, dias, trimp_diario):
    """
    Proyecta Fitness/Fatiga/Forma hacia adelante suponiendo una carga diaria fija.
    Usa el mismo modelo que el cálculo normal, así que la proyección es coherente
    con lo que la app venía mostrando.
    """
    ctl = historial_pmc[-1]["ctl"]
    atl = historial_pmc[-1]["atl"]
    for _ in range(dias):
        ctl = ctl + (trimp_diario - ctl) / config.CTL_DIAS
        atl = atl + (trimp_diario - atl) / config.ATL_DIAS
    return {"ctl": round(ctl, 1), "atl": round(atl, 1), "tsb": round(ctl - atl, 1)}


def carga_diaria_habitual(historial_pmc, dias=28):
    """Promedio de carga diaria de las últimas semanas, incluyendo los días de descanso."""
    ultimos = historial_pmc[-dias:]
    if not ultimos:
        return 0.0
    return sum(d["trimp"] for d in ultimos) / len(ultimos)


# Cuántos minutos por encima de VT2 en 3 semanas se consideran "tener chispa",
# según la prueba. Las distancias cortas exigen mucha más intensidad reciente;
# un maratón se define por resistencia y necesita menos.
INTENSIDAD_MINIMA = {
    "Ruta": 30, "MTB": 45,
    "5 km": 60, "10 km": 45, "21 km (media)": 30, "42 km (maratón)": 20, "Trail / montaña": 40,
}


def analisis_competencia(historial_pmc, sesiones, perfil, dias_hasta_carrera,
                         tipo_carrera="Ruta", deporte="bici"):
    """
    Responde la pregunta que los tres números sueltos no responden: ¿llego bien a
    la carrera? Lo hace mirando cuatro cosas distintas, porque "estar bien" no es
    un solo número:

      1. Motor  - ¿tengo base suficiente para la distancia?
      2. Frescura - ¿voy a llegar descansado?
      3. Chispa - ¿hice trabajo parecido a lo que me va a exigir la carrera?
      4. Rumbo  - ¿mi forma viene creciendo o cayéndose?

    Devuelve un dict con los cuatro puntos y las proyecciones de descarga.
    """
    from datetime import date, timedelta

    hoy = historial_pmc[-1]
    habitual = carga_diaria_habitual(historial_pmc)
    rango = rango_propio_tsb(historial_pmc)

    # --- 1. Motor (CTL) comparado con el propio máximo reciente ---
    ctl_historico = [d["ctl"] for d in historial_pmc[30:]] or [hoy["ctl"]]
    ctl_pico = max(ctl_historico)
    pct_del_pico = hoy["ctl"] / ctl_pico * 100 if ctl_pico else 100

    if pct_del_pico >= 97:
        motor = ("✅", "Tu motor está en su mejor momento del período que tengo registrado.")
    elif pct_del_pico >= 90:
        motor = ("✅", f"Tu motor está al {pct_del_pico:.0f}% de tu mejor momento reciente. Bien.")
    elif pct_del_pico >= 80:
        motor = ("⚠️", f"Tu motor está al {pct_del_pico:.0f}% de tu pico reciente. Vas a poder terminar, "
                       "pero probablemente no rendir como en tu mejor forma.")
    else:
        motor = ("⚠️", f"Tu motor está al {pct_del_pico:.0f}% de tu pico reciente. Te falta base: "
                       "conviene apuntar a terminar cómodo antes que a competir.")

    # --- 2. Chispa: exposición a intensidad en las últimas 3 semanas ---
    limite = date.today() - timedelta(days=21)
    recientes = [s for s in sesiones if _parse_fecha(s["fecha"]) >= limite]
    minutos_intensos = 0.0
    for s in recientes:
        d = distribucion_3_dominios(s, perfil)
        if d:
            minutos_intensos += d["minutos"]["alta"]

    minimo_intenso = INTENSIDAD_MINIMA.get(tipo_carrera, 30)
    if minutos_intensos >= minimo_intenso:
        chispa = ("✅", f"Hiciste {minutos_intensos:.0f} min por encima de tu umbral en las últimas 3 "
                        "semanas. Tenés chispa: tu cuerpo se acuerda de lo que es ir fuerte.")
    elif minutos_intensos >= minimo_intenso * 0.5:
        chispa = ("⚠️", f"Solo {minutos_intensos:.0f} min por encima del umbral en 3 semanas. Te falta "
                        "algo de chispa. Una sesión de series fuertes esta semana te la devuelve "
                        "sin comprometer la recuperación.")
    else:
        detalle_chispa = "."
        if tipo_carrera == "MTB":
            detalle_chispa = " — y en MTB eso pesa mucho, porque se corre a golpes de intensidad."
        elif tipo_carrera in ("5 km", "10 km"):
            detalle_chispa = (
                f" — y en {tipo_carrera} eso es determinante: son pruebas que se corren cerca del "
                "umbral de punta a punta."
            )
        elif tipo_carrera == "Trail / montaña":
            detalle_chispa = " — en trail las subidas te van a exigir picos de intensidad seguido."
        chispa = ("⚠️", f"Casi no hiciste trabajo intenso ({minutos_intensos:.0f} min en 3 semanas). "
                        "Vas a tener base pero te va a faltar respuesta en los momentos duros" + detalle_chispa)

    # --- 3. Rumbo (tendencia del CTL) ---
    ctl_hace_28 = historial_pmc[-29]["ctl"] if len(historial_pmc) >= 29 else None
    if ctl_hace_28 is None:
        rumbo = ("⚪", "Todavía no tengo suficiente historial para ver la tendencia.")
    else:
        delta = hoy["ctl"] - ctl_hace_28
        if delta > 2:
            rumbo = ("✅", f"Tu base viene creciendo ({delta:+.0f} en 4 semanas). Vas en la dirección correcta.")
        elif delta > -2:
            rumbo = ("✅", "Tu base se mantiene estable. Bien para un período de competencia.")
        else:
            rumbo = ("⚠️", f"Tu base viene cayendo ({delta:+.0f} en 4 semanas). Si la carrera es importante, "
                           "convendría recuperar constancia antes de la descarga.")

    # --- 4. Frescura proyectada según cómo encares los días que faltan ---
    # Una descarga real dura 7 a 14 días, no más. Si falta más tiempo que eso, se
    # proyecta entrenamiento normal hasta entrar en la ventana de descarga, y la
    # descarga solo en los últimos días. Proyectar 60 días de descarga no tendría
    # ningún sentido y daría consejos absurdos.
    DIAS_DESCARGA_MAX = 14
    escenarios = []
    recomendado = None

    if dias_hasta_carrera > 0:
        dias_descarga = min(dias_hasta_carrera, DIAS_DESCARGA_MAX)
        dias_normales = dias_hasta_carrera - dias_descarga

        for nombre, factor, detalle in [
            ("Sigo igual, sin descargar", 1.0, "sin bajar nada"),
            ("Descarga suave", 0.6, "40% menos de volumen"),
            ("Descarga marcada", 0.35, "65% menos de volumen"),
            ("Descanso casi total", 0.1, "apenas movilidad"),
        ]:
            base = historial_pmc
            if dias_normales:
                # Primero los días de entrenamiento normal
                previo = proyectar(base, dias_normales, habitual)
                base = [{"ctl": previo["ctl"], "atl": previo["atl"], "tsb": previo["tsb"], "trimp": habitual}]
            proy = proyectar(base, dias_descarga, habitual * factor)
            escenarios.append({"nombre": nombre, "detalle": detalle, **proy})

        # Cuál recomendar: acá NO se optimiza ninguna fórmula. Se sigue lo que dice
        # la literatura de tapering, que es bastante consistente: recortar el volumen
        # entre un 40% y un 60% a lo largo de 8 a 14 días, manteniendo la intensidad.
        # "Descarga suave" es justo el medio de ese rango.
        #
        # Intentar en cambio elegir el escenario que maximice alguna combinación de
        # Fitness y Forma sonaba más sofisticado, pero requiere inventar cuánto pesa
        # cada uno - y según cómo se elijan esos pesos, la misma cuenta recomienda no
        # descargar nunca o descansar dos semanas enteras. Las proyecciones de acá
        # abajo sirven para que veas qué esperar, no para decidir por vos.
        recomendado = next(e for e in escenarios if e["nombre"] == "Descarga suave")

    return {
        "motor": motor,
        "chispa": chispa,
        "rumbo": rumbo,
        "escenarios": escenarios,
        "recomendado": recomendado,
        "rango_tsb": rango,
        "tsb_hoy": hoy["tsb"],
        "dias": dias_hasta_carrera,
        "tipo": tipo_carrera,
        "deporte": deporte,
        "dias_descarga": min(dias_hasta_carrera, 14) if dias_hasta_carrera > 0 else 0,
    }


# ---------------------------------------------------------------------------
# Análisis propios del running
# ---------------------------------------------------------------------------

def progresion_volumen_running(sesiones, semanas=6):
    """
    Revisa cómo viene subiendo el volumen semanal de carrera.

    Es el análisis más útil para prevenir lesiones, y mucho más importante en
    running que en bici: los saltos bruscos de kilometraje son la causa más
    frecuente de lesiones por sobrecarga. La referencia clásica es no subir más
    de un 10% por semana; no es una ley exacta, pero sirve para detectar los
    saltos grandes, que son los que hacen daño.
    """
    from datetime import date, timedelta

    corridas = [s for s in sesiones if s.get("deporte") == "running"]
    if not corridas:
        return None

    hoy = date.today()
    lunes_actual = hoy - timedelta(days=hoy.weekday())

    bloques = []
    for i in range(semanas):
        ini = lunes_actual - timedelta(weeks=semanas - 1 - i)
        fin = ini + timedelta(days=7)
        de_la_semana = [s for s in corridas if ini <= _parse_fecha(s["fecha"]) < fin]
        bloques.append({
            "desde": ini,
            "km": round(sum(s["distancia_km"] for s in de_la_semana), 1),
            "minutos": round(sum(s["duracion_min"] for s in de_la_semana)),
            "sesiones": len(de_la_semana),
        })

    # Buscar saltos grandes entre semanas consecutivas con actividad
    saltos = []
    for previa, actual in zip(bloques, bloques[1:]):
        if previa["km"] >= 5 and actual["km"] > previa["km"]:
            subida = (actual["km"] - previa["km"]) / previa["km"] * 100
            if subida > 20:
                saltos.append({"desde": actual["desde"], "pct": round(subida)})

    return {"semanas": bloques, "saltos": saltos}


def mejor_esfuerzo_running(sesiones, dias=120):
    """
    Busca la carrera continua más rápida de los últimos meses, para usarla como
    base de la predicción de tiempos.

    Se queda con la de mejor ritmo entre las de al menos 5 km, porque una sesión
    de series muy corta no representa un rendimiento sostenido.
    """
    from datetime import date, timedelta

    limite = date.today() - timedelta(days=dias)
    candidatas = [
        s for s in sesiones
        if s.get("deporte") == "running"
        and s.get("ritmo_min_km")
        and s["distancia_km"] >= 5
        and _parse_fecha(s["fecha"]) >= limite
    ]
    if not candidatas:
        return None
    return min(candidatas, key=lambda s: s["ritmo_min_km"])


DISTANCIAS_OBJETIVO = [
    ("5 km", 5.0),
    ("10 km", 10.0),
    ("21 km (media)", 21.0975),
    ("42 km (maratón)", 42.195),
]


def predecir_carreras(sesiones):
    """Proyecta tiempos para las distancias clásicas a partir de tu mejor esfuerzo reciente."""
    base = mejor_esfuerzo_running(sesiones)
    if not base:
        return None

    predicciones = []
    for nombre, dist in DISTANCIAS_OBJETIVO:
        minutos = metrics.predecir_tiempo_carrera(base["distancia_km"], base["duracion_min"], dist)
        if minutos:
            predicciones.append({
                "nombre": nombre,
                "distancia_km": dist,
                "minutos": minutos,
                "texto": metrics.formatear_duracion(minutos),
                "ritmo": metrics.formatear_ritmo(minutos / dist),
                # La predicción pierde confianza cuanto más lejos está de la base
                "confianza": "alta" if 0.5 <= dist / base["distancia_km"] <= 2
                             else ("media" if dist / base["distancia_km"] <= 4 else "baja"),
            })
    return {"base": base, "predicciones": predicciones}
