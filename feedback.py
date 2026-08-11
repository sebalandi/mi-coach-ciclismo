# feedback.py
"""
Traduce los números (zonas de FC, TRIMP, CTL/ATL/TSB) a feedback en español,
en lenguaje de entrenador, no de planilla.
"""



def feedback_sesion(sesion):
    """Párrafo de feedback para UNA sesión de bici."""
    dur = sesion["duracion_min"]
    dist = sesion["distancia_km"]
    fc = sesion["fc_prom"]
    trimp = sesion["trimp"]
    minutos = sesion["minutos_por_zona"]

    partes = []
    partes.append(
        f"Sesión de {dur:.0f} min, {dist:.1f} km, FC promedio {fc if fc else '-'} bpm. "
        f"Carga de entrenamiento (TRIMP): {trimp:.0f}."
    )

    if any(minutos.values()):
        # Acá va SOLO el reparto por zona, sin veredicto sobre el tipo de sesión.
        #
        # Antes esta función tenía su propio clasificador, que miraba únicamente
        # la zona con más minutos. Eso llevó a contradicciones directas: una
        # sesión con 29% en Z2 pero con bastante Z5 y el pulso cerca del máximo
        # se anunciaba como "base aeróbica, se recupera rápido" mientras el
        # análisis del entrenador —que mira tres señales— la clasificaba
        # correctamente como VO2max. Dos veredictos distintos en la misma
        # pantalla es peor que uno solo, así que ahora la clasificación tiene un
        # único dueño: coach.clasificar_sesion().
        total_zonas = sum(minutos.values())
        reparto = " · ".join(
            f"Z{z} {minutos.get(z, 0) / total_zonas * 100:.0f}%"
            for z in range(1, 6) if minutos.get(z, 0) > 0
        ) if total_zonas else ""
        if reparto:
            partes.append(f"Reparto por zonas: {reparto}.")

    if sesion.get("zonas_estimadas"):
        partes.append(
            "(Nota: Garmin no envió el detalle de zonas para esta sesión particular, "
            "así que el reparto por zona de acá arriba es una estimación a partir de tu FC promedio.)"
        )

    # --- Contexto de recorrido: velocidad, pendiente, cadencia ---
    contexto = []
    if sesion.get("deporte") == "running":
        # En carrera el dato que importa es el ritmo, no la velocidad, y la
        # cadencia se mide en pasos por minuto con otros valores de referencia.
        if sesion.get("ritmo_texto"):
            linea_r = f"Ritmo promedio: {sesion['ritmo_texto']}"
            if sesion.get("ritmo_gap_texto"):
                linea_r += f" (equivalente a {sesion['ritmo_gap_texto']} en llano, corrigiendo el desnivel)"
            pend_r = sesion.get("elevacion_por_km")
            if pend_r is not None:
                if pend_r > 25:
                    linea_r += ", en un recorrido de montaña exigente."
                elif pend_r > 10:
                    linea_r += ", en un recorrido con desnivel."
                else:
                    linea_r += ", en terreno mayormente llano."
            else:
                linea_r += "."
            contexto.append(linea_r)

        cad_r = sesion.get("cadencia_prom")
        if cad_r:
            if cad_r < 160:
                contexto.append(
                    f"Cadencia promedio de {cad_r:.0f} pasos/min: baja. Suele indicar zancada larga y "
                    "más impacto en cada apoyo."
                )
            elif cad_r <= 185:
                contexto.append(f"Cadencia promedio de {cad_r:.0f} pasos/min: en un rango eficiente.")
            else:
                contexto.append(f"Cadencia promedio de {cad_r:.0f} pasos/min: bien ágil.")

        if contexto:
            partes.append(" ".join(contexto))
        texto = " ".join(partes)
        return texto

    vel = sesion.get("velocidad_kmh")
    pendiente = sesion.get("elevacion_por_km")
    if vel:
        frase_vel = f"Velocidad promedio: {vel:.1f} km/h"
        if pendiente is not None:
            if pendiente > 15:
                frase_vel += f", en un recorrido bien montañoso ({pendiente:.0f} m/km de desnivel)."
            elif pendiente > 5:
                frase_vel += f", en un recorrido ondulado ({pendiente:.0f} m/km de desnivel)."
            else:
                frase_vel += " en un recorrido mayormente llano."
        else:
            frase_vel += "."
        contexto.append(frase_vel)

    if pendiente and pendiente > 12 and sesion.get("elevacion_m") and sesion["duracion_min"]:
        vam_aprox = sesion["elevacion_m"] / (sesion["duracion_min"] / 60)
        contexto.append(
            f"VAM aproximado de toda la sesión: {vam_aprox:.0f} m/h (promedio de la salida completa, "
            "no solo de la subida - para un número más preciso de la subida en sí, usá el botón "
            "'Calcular VAM real' más abajo)."
        )

    cadencia = sesion.get("cadencia_prom")
    if cadencia:
        if cadencia < 75:
            contexto.append(
                f"Cadencia promedio de {cadencia:.0f} rpm: bastante baja, pedaleaste con relaciones "
                "pesadas. Está bien puntualmente, pero a diario le mete más estrés a rodillas y "
                "tendones - a tus 48 vale la pena probar subir un poco el cambio y afinar la cadencia."
            )
        elif cadencia <= 95:
            contexto.append(f"Cadencia promedio de {cadencia:.0f} rpm: en un rango eficiente y cuidado para las articulaciones.")
        else:
            contexto.append(f"Cadencia promedio de {cadencia:.0f} rpm: un estilo de pedaleo bien ligero.")

    if contexto:
        partes.append(" ".join(contexto))

    texto = " ".join(partes)

    if sesion.get("tiene_potencia"):
        texto_potencia = feedback_potencia_sesion(sesion)
        if texto_potencia:
            texto += "\n\n💪 " + texto_potencia

    return texto


def feedback_potencia_sesion(sesion):
    """Párrafo extra de feedback basado en potencia, para sesiones con medidor de vatios."""
    from metrics import NOMBRE_ZONA_POTENCIA

    pot_prom = sesion.get("potencia_prom")
    if pot_prom is None:
        return None

    pot_np = sesion.get("potencia_normalizada")
    wkg = sesion.get("watts_por_kg")
    tss = sesion.get("tss")
    if_ = sesion.get("if_")

    partes = []
    texto = f"Potencia promedio: {pot_prom:.0f} W"
    if pot_np:
        texto += f" (normalizada: {pot_np:.0f} W)"
    if wkg:
        texto += f" — {wkg:.2f} W/kg"
    texto += "."
    partes.append(texto)

    if tss is not None and if_ is not None:
        partes.append(f"TSS: {tss:.0f} · Intensity Factor: {if_:.2f}.")
        if if_ < 0.65:
            partes.append("IF bajo: en términos de potencia fue una sesión suave o de recuperación.")
        elif if_ < 0.85:
            partes.append("IF moderado: un entreno de resistencia/aeróbico sólido y sostenible.")
        elif if_ < 0.95:
            partes.append("IF alto: trabajaste cerca de tu umbral, un estímulo bastante exigente.")
        else:
            partes.append(
                "IF muy alto: fue una sesión muy intensa (umbral duro o superior). "
                "Priorizá la recuperación en las próximas 24-48 h."
            )
    else:
        partes.append(
            "Para calcular tu TSS e Intensity Factor con precisión, cargá tu FTP en la barra lateral "
            "(o configuralo en tu cuenta de Garmin para que te lo calcule directamente)."
        )

    ef = sesion.get("ef")
    if ef:
        partes.append(
            f"Factor de Eficiencia (EF): {ef:.2f} W/bpm. Seguilo en el tiempo para el mismo tipo de "
            "salida: si sube con las semanas a una intensidad similar, tu motor aeróbico está mejorando."
        )

    minutos_pot = sesion.get("minutos_por_zona_potencia")
    if minutos_pot and any(minutos_pot.values()):
        dur = sesion["duracion_min"]
        zona_dom = max(minutos_pot, key=minutos_pot.get)
        pct = minutos_pot[zona_dom] / dur * 100 if dur else 0
        partes.append(f"Zona de potencia predominante: {NOMBRE_ZONA_POTENCIA[zona_dom]} ({pct:.0f}% del tiempo).")

    if sesion.get("zona_potencia_estimada"):
        partes.append(
            "(El reparto por zona de potencia es una estimación a partir del promedio de la sesión, "
            "ya que Garmin no envió el detalle exacto.)"
        )

    return " ".join(partes)


def feedback_periodo(historial_pmc, dias=7):
    """Resumen en lenguaje simple de los últimos N días, usando CTL/ATL/TSB."""
    ultimos = historial_pmc[-dias:]
    if not ultimos:
        return "No hay datos suficientes para este período."

    trimp_total = sum(d["trimp"] for d in ultimos)
    dias_entrenados = sum(1 for d in ultimos if d["trimp"] > 0)
    tsb_final = ultimos[-1]["tsb"]
    ctl_final = ultimos[-1]["ctl"]
    ctl_inicial = ultimos[0]["ctl"]

    partes = [
        f"En los últimos {dias} días entrenaste {dias_entrenados} de {dias} días, "
        f"con una carga total de {trimp_total:.0f} puntos TRIMP."
    ]

    if ctl_final > ctl_inicial + 1:
        partes.append(
            "Tu fitness de base (CTL) está subiendo: la constancia está construyendo fondo aeróbico."
        )
    elif ctl_final < ctl_inicial - 1:
        partes.append(
            "Tu CTL bajó un poco respecto al período anterior: hubo menos carga acumulada, "
            "ya sea por descanso o por menos sesiones."
        )
    else:
        partes.append("Tu CTL se mantuvo bastante estable en este período.")

    if tsb_final < -15:
        partes.append(
            "Tu TSB (forma) está bastante negativo: estás acumulando fatiga. Es un buen momento "
            "para meter 1-2 días de descarga antes de encarar la próxima sesión fuerte o un gym pesado de piernas."
        )
    elif tsb_final > 10:
        partes.append(
            "Tu TSB está positivo: llegás fresco. Es un buen momento para meter la sesión más "
            "exigente de la semana, si tenés una planificada."
        )
    else:
        partes.append("Tu TSB está en un rango normal de entrenamiento: ni muy fatigado ni muy fresco.")

    return " ".join(partes)


def feedback_deriva_cardiaca(resultado, sesion=None):
    """
    Texto interpretando el resultado de metrics.calcular_deriva_cardiaca().

    Los umbrales cambian según dónde entrenaste: bajo techo (rodillo o cinta) la
    deriva SIEMPRE es mayor, porque no hay viento que te refrigere y el calor
    acumulado sube el pulso por sí solo. Juzgar una sesión de rodillo con los
    valores de la calle da un diagnóstico falso de mala forma aeróbica.
    """
    if resultado is None:
        return (
            "No hay suficientes datos en esta sesión para calcular la deriva cardíaca "
            "(sesiones muy cortas, o sin detalle segundo a segundo, no dan un resultado confiable)."
        )

    bajo_techo = bool(sesion and sesion.get("bajo_techo"))
    # Bajo techo se acepta bastante más deriva antes de considerarla una señal de algo
    corte_bueno, corte_normal = (8, 15) if bajo_techo else (5, 10)

    d = resultado["deriva_pct"]
    texto = (
        f"Deriva cardíaca: {d:.1f}% (comparando {resultado['metrica_usada']} entre la primera mitad "
        f"y la segunda de la sesión; FC promedio {resultado['fc_primera_mitad']} bpm vs "
        f"{resultado['fc_segunda_mitad']} bpm)."
    )

    if d < corte_bueno:
        texto += (
            " Muy buena estabilidad: tu corazón sostuvo el mismo esfuerzo sin perder eficiencia."
        )
        if bajo_techo:
            texto += " Y bajo techo tiene más mérito todavía, porque el calor juega en contra."
        else:
            texto += " Buena señal de base aeróbica, y de que la hidratación y la temperatura acompañaron."
    elif d < corte_normal:
        texto += " Deriva normal"
        if bajo_techo:
            texto += (
                " para una sesión bajo techo: sin viento, el calor acumulado sube el pulso aunque el "
                "esfuerzo no cambie."
            )
        elif sesion and sesion.get("deporte") == "running":
            texto += ", esperable en tiradas largas o con calor. No es preocupante."
        else:
            texto += ", esperable en salidas largas o con calor. No es preocupante."
    else:
        texto += (
            " Deriva alta: tu FC subió bastante más de lo esperado para sostener el mismo esfuerzo "
            "hacia el final."
        )
        if bajo_techo:
            texto += (
                " Bajo techo lo primero a revisar es la refrigeración: un ventilador potente de "
                "frente cambia estos números drásticamente. Después, la hidratación."
            )
        else:
            largas = "tiradas largas" if (sesion and sesion.get("deporte") == "running") else "salidas largas"
            texto += (
                " Puede ser calor, deshidratación, o que la duración o la intensidad superaron tu "
                f"base aeróbica actual. Si se repite en varias {largas}, vale la pena revisar "
                "la hidratación y la progresión de volumen antes de sumar más kilómetros."
            )

    if bajo_techo:
        texto += (
            "\n\n*Nota: los valores de referencia se ajustaron por ser bajo techo. Al aire libre, "
            "una deriva de más del 10% ya sería alta; acá el corte está en 15%.*"
        )

    return texto


def feedback_curva_potencia(curva, cp_wprime, tte, perfil):
    """Texto interpretando la curva de potencia, CP, W' y TTE."""
    if not curva:
        return "No encontré suficientes sesiones con potencia y detalle disponible para armar la curva."

    partes = []
    ftp = perfil.get("ftp_watts")
    peso = perfil.get("peso_kg")

    if cp_wprime:
        cp = cp_wprime["cp"]
        wp = cp_wprime["w_prime_kj"]
        texto_cp = f"Potencia Crítica (CP) estimada: {cp} W"
        if peso:
            texto_cp += f" ({cp/peso:.2f} W/kg)"
        texto_cp += f". Capacidad anaeróbica (W'): {wp:.1f} kJ."
        partes.append(texto_cp)

        if ftp:
            diferencia = cp - ftp
            if abs(diferencia) <= ftp * 0.03:
                partes.append("Tu CP estimada está muy en línea con tu FTP cargado - buena señal de consistencia.")
            elif diferencia > 0:
                partes.append(
                    f"Tu CP estimada ({cp} W) da algo más alta que tu FTP cargado ({ftp} W). "
                    "Puede ser que tu FTP esté un poco desactualizado, o que la muestra de datos sea limitada."
                )
            else:
                partes.append(
                    f"Tu CP estimada ({cp} W) da algo más baja que tu FTP cargado ({ftp} W). "
                    "Puede reflejar fatiga acumulada reciente, o que hace tiempo no hacés esfuerzos "
                    "sostenidos de 2-20 minutos a fondo (el rango que usa este cálculo)."
                )

        if wp < 15:
            partes.append("Tu W' es más bien bajo: tu perfil rinde mejor en esfuerzos sostenidos que en picos cortos muy intensos.")
        elif wp > 25:
            partes.append("Tu W' es alto: tenés buena capacidad de respuesta en esfuerzos cortos e intensos (ataques, sprints, repechos).")
        else:
            partes.append("Tu W' está en un rango intermedio, sin un perfil marcadamente sprinter ni marcadamente rodador.")
    else:
        partes.append(
            "No hay suficientes puntos entre 2 y 20 minutos en tu curva de potencia como para "
            "ajustar CP y W' con confianza (hacen falta esfuerzos sostenidos y bien variados en esa franja)."
        )

    if tte:
        minutos_tte = tte / 60
        partes.append(
            f"Time to Exhaustion (TTE) estimado a tu FTP: alrededor de {minutos_tte:.0f} minutos "
            "(el esfuerzo sostenido más largo que diste cerca de tu FTP, entre tus propias sesiones)."
        )
    elif ftp:
        partes.append(
            "Todavía no encontré, entre tus sesiones, un esfuerzo sostenido cercano a tu FTP como para "
            "estimar tu TTE. Un rodaje largo sosteniendo tu FTP el mayor tiempo posible te daría ese dato."
        )

    return " ".join(partes)


def feedback_lthr(resultado, perfil=None):
    """
    Texto interpretando la FC de umbral (LTHR) estimada a partir del entrenamiento.
    Si el perfil tiene datos de una ergoespirometría (perfil['test_fisiologico']),
    se compara contra el VT2 medido en laboratorio - la referencia más precisa posible.
    """
    test = (perfil or {}).get("test_fisiologico")
    vt2_fc = test.get("vt2_fc") if test else None
    vt2_fecha = test.get("fecha") if test else None

    if resultado is None:
        texto = (
            "Todavía no encontré suficientes sesiones cercanas a tu umbral como para estimar tu LTHR "
            "a partir de tus entrenamientos."
        )
        if vt2_fc:
            texto += (
                f" De todas formas, tu ergoespirometría del {vt2_fecha} ya midió esto directamente: "
                f"tu FC en el umbral anaeróbico (VT2) fue de {vt2_fc} bpm - es un dato más preciso que "
                "cualquier estimación que esta app pueda hacer con datos de entrenamiento."
            )
        return texto

    texto = (
        f"FC de umbral (LTHR) estimada a partir de tu entrenamiento: {resultado['lthr']} bpm, "
        f"calculada con {resultado['n_sesiones']} sesión(es) usando {resultado['metodo']}."
    )

    if vt2_fc:
        diferencia = resultado["lthr"] - vt2_fc
        texto += (
            f" Tu ergoespirometría del {vt2_fecha} midió tu VT2 (umbral anaeróbico real) en {vt2_fc} bpm - "
            "esa medición de laboratorio es más confiable que esta estimación basada en entrenamientos."
        )
        if abs(diferencia) <= 3:
            texto += " Están muy en línea, lo cual es una buena señal de consistencia."
        elif diferencia > 3:
            texto += (
                f" La estimación de acá te da {diferencia} bpm más alta - probablemente porque tus "
                "sesiones cercanas al umbral en Garmin no llegan exactamente a tu VT2 real."
            )
        else:
            texto += f" La estimación de acá te da {abs(diferencia)} bpm más baja que tu VT2 medido."
    else:
        texto += " Para más precisión, lo ideal es un test dedicado de 20 u 8 minutos a fondo (o una ergoespirometría)."

    return texto


def feedback_vam(resultado, perfil=None, sesion=None):
    """
    Explica el VAM: qué es, por qué no se puede comparar entre subidas distintas,
    y qué significa el número concreto para esta persona.
    """
    if resultado is None:
        return (
            "No encontré un tramo de subida sostenido lo bastante largo (mínimo 5 minutos) en esta "
            "sesión como para calcular un VAM confiable."
        )

    minutos = resultado["duracion_seg"] / 60
    vam = resultado["vam"]
    pend = resultado.get("pendiente_pct")
    w_kg = resultado.get("w_kg")
    perfil = perfil or {}

    L = []

    # --- Qué es ---
    L.append(
        f"**Mejor VAM de la sesión: {vam} m/h.** Quiere decir que, en tu mejor tramo de subida, "
        f"ganaste altura a un ritmo de **{vam} metros verticales por hora**. Si hubieras podido "
        f"sostener ese ritmo una hora entera, habrías subido {vam} metros de desnivel."
    )
    L.append(
        f"Ese tramo fueron **{minutos:.0f} minutos** en los que subiste {resultado['desnivel_m']} m"
        + (f" a lo largo de {resultado['largo_m']/1000:.1f} km, o sea una pendiente media del "
           f"**{pend}%**." if pend else ".")
    )

    # --- Todas las subidas del recorrido ---
    subidas = resultado.get("subidas") or []
    if len(subidas) > 1:
        L.append("**Las subidas que encontré en esta salida:**")
        for s in subidas:
            linea = f"- Km {s['km_inicio']} · **{s['duracion_seg']/60:.1f} min**"
            if s.get("pendiente_pct"):
                linea += f" al {s['pendiente_pct']}%"
            linea += f" · +{s['desnivel_m']} m · **VAM {s['vam']}**"
            L.append(linea)

    # --- Las dos trampas del VAM ---
    L.append(
        "⚠️ **El VAM no se compara entre subidas distintas.** Hay dos motivos, y los dos se ven en "
        "la lista de arriba:"
    )
    L.append(
        "**Por la pendiente.** En una cuesta suave vas rápido pero ganás poca altura por hora; en una "
        "empinada pasa lo contrario, con el mismo esfuerzo exacto. Un VAM de 600 al 4% puede ser un "
        "esfuerzo mayor que uno de 900 al 10%."
    )
    L.append(
        "**Por la duración.** Un repecho de 2 minutos siempre va a dar un VAM mucho más alto que una "
        "subida de 20, porque en algo tan corto podés ir muy por encima de tu umbral y aguantarlo. "
        "No significa que hayas subido \"mejor\": significa que fue más corto."
    )
    if resultado.get("mas_larga"):
        ml = resultado["mas_larga"]
        L.append(
            f"Por eso te muestro también **la subida más larga** de la salida: {ml['duracion_seg']/60:.0f} "
            f"min al {ml['pendiente_pct']}% con VAM {ml['vam']}. Ese número dice más sobre tu resistencia; "
            f"el de {vam} habla de tu punch en subidas cortas. Son dos cualidades distintas."
        )

    running = bool(sesion and sesion.get("deporte") == "running")

    # --- Referencia propia de cada deporte ---
    if running:
        # En carrera NO se usa la conversión a vatios: la fórmula de Ferrari está
        # hecha para ciclismo y no hay forma seria de derivar los vatios de un
        # corredor desde el VAM. La economía de carrera, la técnica de subida y
        # el hecho de que arriba de cierta pendiente convenga caminar hacen que
        # la relación entre potencia y VAM sea otra.
        if pend and pend >= 12:
            L.append(
                "Como referencia en subidas empinadas de trail: un corredor aficionado en buena forma "
                "suele moverse entre **600 y 900 m/h**, uno bien entrenado entre **1000 y 1300**, y los "
                "especialistas en kilómetro vertical pasan de 1600. Igual, lo más útil sigue siendo "
                "compararte con vos mismo en la misma subida."
            )
        if pend and pend >= 18:
            L.append(
                f"Con esa pendiente ({pend}%), fijate si te conviene **caminar rápido**: arriba del 15-20% "
                "la mayoría de los corredores sube más rápido y gastando menos caminando fuerte que "
                "trotando. En trail es una técnica, no una derrota — vale la pena practicarla."
            )
    elif w_kg:
        L.append(
            f"**Traducido a algo comparable: unos {w_kg} vatios por kilo.** Este número sí sirve para "
            "comparar entre subidas distintas, porque ya tiene la pendiente descontada. Sale de una "
            "fórmula estándar que relaciona VAM, pendiente y potencia, y es confiable entre el 5% y "
            "el 12% de pendiente."
        )

        ftp, peso = perfil.get("ftp_watts"), perfil.get("peso_kg")
        if ftp and peso:
            w_kg_umbral = ftp / peso
            pct = w_kg / w_kg_umbral * 100
            min_subida = resultado["duracion_seg"] / 60
            # Una subida corta permite ir muy por encima del umbral sin que eso
            # sea raro: cuanto menos dura, más se puede pasar. Sin esta aclaración,
            # un 170% en un repecho de 2 minutos parece un error o una hazaña, y
            # es simplemente lo normal.
            contexto_dur = (
                f" En un esfuerzo de {min_subida:.0f} minutos eso es esperable: cuanto más corta la "
                "subida, más se puede pasar del umbral sin explotar."
                if pct > 115 and min_subida <= 5 else ""
            )
            L.append(
                f"Tu FTP son {ftp} W, o sea **{w_kg_umbral:.2f} W/kg** en el umbral. Esta subida la "
                f"hiciste a alrededor del **{pct:.0f}% de tu umbral**"
                + (", o sea claramente por encima." + contexto_dur
                   if pct > 105 else
                   ", o sea muy cerca de tu umbral: prácticamente el máximo que podés sostener."
                   if pct > 92 else
                   ", o sea con margen: te quedaba resto para apretar más."
                   if pct > 75 else
                   ", o sea a ritmo tranquilo, bien por debajo de lo que podés dar.")
            )
    elif pend is not None and pend < 5:
        L.append(
            f"No traduzco este VAM a vatios por kilo porque la pendiente ({pend}%) es demasiado suave: "
            "por debajo del 5%, la resistencia del aire pesa más que la gravedad y la conversión deja "
            "de ser confiable."
        )
    else:
        L.append(
            "No pude calcular la pendiente de este tramo (falta el detalle de distancia), así que no "
            "puedo traducir el VAM a vatios por kilo."
        )

    # --- Para qué te sirve seguirlo ---
    L.append(
        "**Para qué sirve:** es la forma más directa de medir tu progreso en subida. Si dentro de dos "
        "meses repetís una subida parecida y tu VAM subió, mejoraste — y es un dato bastante más "
        "limpio que el ritmo o la velocidad, que dependen del viento, del terreno y del tráfico."
    )

    return "\n\n".join(L)


def feedback_rpe(rpe, sesion, perfil=None):
    """
    Compara tu esfuerzo percibido (RPE, 1-10) con lo que sugieren tus datos objetivos,
    usando una tabla orientativa de qué RPE "esperaríamos" según la zona dominante de la
    sesión. No es una fórmula científica exacta, es una guía aproximada para detectar
    cuándo tu sensación se aleja bastante de lo que dicen los números.
    """
    if rpe is None:
        return None

    carga_percibida = rpe * sesion["duracion_min"]
    texto = f"RPE registrado: {rpe}/10. Carga percibida (RPE x minutos): {carga_percibida:.0f}."

    minutos = sesion.get("minutos_por_zona", {})
    if not any(minutos.values()):
        return texto

    # El esfuerzo esperado sale del MISMO clasificador que usa el resto de la app,
    # no de la zona con más minutos. Mirando solo la zona dominante, una sesión
    # con mucho Z2 pero con series fuertes esperaba un RPE de 4, y entonces te
    # decía que "lo sentiste más duro de lo que fue" cuando en realidad había
    # sido una sesión dura de verdad.
    import coach
    RPE_ESPERADO = {
        "recuperacion": 2.0, "base": 4.0, "fondo_largo": 5.5,
        "tempo": 6.0, "umbral": 7.5, "vo2max": 9.0, "mixta_gris": 5.5,
    }
    tipo_sesion = coach.clasificar_sesion(sesion, perfil) if perfil else None
    rpe_esperado = RPE_ESPERADO.get(tipo_sesion, 5.5)
    diferencia = rpe - rpe_esperado

    if diferencia >= 2:
        texto += (
            " Lo sentiste bastante más duro de lo que sugieren tus datos objetivos para este tipo de "
            "sesión - puede ser una señal temprana de fatiga acumulada, poco sueño, o estrés extra de "
            "otro lado. No es para alarmarse por una sola sesión, pero si se repite, bajale la carga "
            "un par de días."
        )
    elif diferencia <= -2:
        texto += " Lo sentiste más liviano de lo que objetivamente fue - buena señal, estás respondiendo bien a la carga."
    else:
        texto += " Coincide bastante bien con lo que sugieren tus datos objetivos."

    return texto


def feedback_competencia(a):
    """Convierte el análisis de coach.analisis_competencia() en un texto accionable."""
    lineas = []

    running = a.get("deporte") == "running"
    evento = "competencia" if running else "carrera"
    lineas.append(f"### ¿Cómo llegás a {a['tipo']} en {a['dias']} días?")
    lineas.append(
        "Estar bien no es un solo número. Son cuatro cosas distintas, y podés estar bien en "
        "unas y flojo en otras:"
    )

    for etiqueta, clave in [
        ("**Motor** — ¿tengo base para la distancia?", "motor"),
        ("**Chispa** — ¿hice trabajo parecido a lo que voy a correr?", "chispa"),
        ("**Rumbo** — ¿mi forma crece o se cae?", "rumbo"),
    ]:
        icono, texto = a[clave]
        lineas.append(f"{icono} {etiqueta}  \n{texto}")

    if a["dias"] <= 0:
        lineas.append(
            f"**Frescura:** la {evento} es hoy o ya pasó, así que no hay nada que ajustar. "
            "Poné una fecha futura para ver cómo conviene descargar."
        )
        return "\n\n".join(lineas)

    lineas.append("---")

    if a["dias"] > 21:
        lineas.append(
            f"**Frescura:** faltan {a['dias']} días, así que todavía estás en tiempo de **construir** "
            f"— la descarga recién se planifica en los últimos 10 a 14 días. Las proyecciones de abajo "
            f"suponen que seguís entrenando normal hasta entrar en esa ventana final de "
            f"{a['dias_descarga']} días:"
        )
    else:
        lineas.append(
            f"**Frescura:** ya estás dentro de la ventana de descarga. Así te quedaría la Forma el día "
            f"de la {evento} según cómo encares estos {a['dias']} días:"
        )

    rango = a["rango_tsb"]
    for e in a["escenarios"]:
        marca = "  ← **recomendado**" if a["recomendado"] and e["nombre"] == a["recomendado"]["nombre"] else ""
        nota = ""
        if rango:
            if e["tsb"] >= rango["p90"]:
                nota = " (muy fresco para vos)"
            elif e["tsb"] >= rango["p75"]:
                nota = " (fresco para vos)"
            elif e["tsb"] <= rango["p25"]:
                nota = " (cargado para vos)"
        lineas.append(
            f"- **{e['nombre']}** ({e['detalle']}): Forma **{e['tsb']:+.0f}**{nota}, "
            f"Fitness {e['ctl']:.0f}{marca}"
        )

    if a["recomendado"]:
        r = a["recomendado"]
        lineas.append(
            f"El escenario marcado no sale de una fórmula: es lo que dice la investigación sobre "
            f"descarga, que es bastante consistente — recortar el volumen entre un 40% y un 60% "
            f"durante 8 a 14 días, manteniendo la intensidad. Te dejaría en Forma "
            f"**{r['tsb']:+.0f}** con Fitness {r['ctl']:.0f}."
        )
        lineas.append(
            "Las otras filas están para que veas el precio de cada opción: descansar más te deja "
            "más fresco pero te come base, y no descargar te deja con el motor grande pero cansado. "
            "No hay un número mágico que resuelva ese intercambio, así que te muestro las dos caras "
            "en vez de fingir que hay una respuesta exacta."
        )

    lineas.append(
        "**Cómo descargar bien:** bajá el *volumen*, no la intensidad. Mantené algunas series "
        "cortas y fuertes en los últimos días —eso conserva la chispa— pero recortá los minutos "
        "totales. Una descarga en la que solo rodás suave y largo te deja fresco y apagado."
    )

    consejos = {
        "MTB": "**Para MTB:** además de la forma, no descuides la técnica en los días previos. Una "
               "salida corta en el terreno de la carrera vale más que una hora extra de rodillo, y el "
               "desgaste es mínimo.",
        "Ruta": "**Para ruta:** si la carrera es en grupo, acordate de que el ritmo lo impone el "
                "pelotón, no tus zonas. Llegar fresco te da margen para aguantar los cambios de ritmo, "
                "que es donde se define casi todo.",
        "5 km": "**Para 5 km:** es casi todo intensidad. En la última semana no pierdas el contacto "
                "con el ritmo de carrera: unas pocas series cortas a ritmo objetivo alcanzan.",
        "10 km": "**Para 10 km:** se corre muy cerca del umbral de punta a punta. El error clásico es "
                 "salir demasiado rápido; los primeros mil metros deberían sentirse cómodos.",
        "21 km (media)": "**Para la media:** es la distancia donde mejor funciona ir a ritmo parejo. "
                         "Practicá el ritmo objetivo en las tiradas largas para que las piernas lo reconozcan.",
        "42 km (maratón)": "**Para el maratón:** lo que falla casi nunca es el motor, sino las piernas "
                           "y el combustible. Las tiradas largas y ensayar la alimentación valen más que "
                           "cualquier serie. Y salí más lento de lo que te pide el cuerpo: en maratón el "
                           "tiempo se pierde en la segunda mitad, no se gana en la primera.",
        "Trail / montaña": "**Para trail:** entrená las bajadas, no solo las subidas. El daño muscular "
                           "de bajar es lo que te deja las piernas destruidas, y solo se entrena bajando. "
                           "Y practicá caminar rápido en las subidas empinadas: en trail caminar bien es "
                           "una técnica, no una derrota.",
    }
    if a["tipo"] in consejos:
        lineas.append(consejos[a["tipo"]])

    lineas.append(
        "> Un recordatorio: esto sale de tus datos de entrenamiento, que son una parte de la "
        "historia. El sueño, el estrés del trabajo, cómo venís comiendo y si estás peleando algún "
        "virus pesan tanto o más, y ninguno de esos aparece acá. Si el cuerpo te dice otra cosa "
        "que los números, hacele caso al cuerpo."
    )

    return "\n\n".join(lineas)


def feedback_recorrido(resumen, subidas, exigencia, tiempo, perfil, sesiones,
                       dias_hasta, tipo_bici, intensidad, deporte="bici"):
    """
    Análisis completo de un recorrido de carrera: cómo es, qué te va a pedir,
    cómo te iría con lo que tenés hoy, y qué conviene entrenar en el tiempo
    que queda.
    """
    L = []
    running = deporte == "running"
    ftp = perfil.get("ftp_watts")
    peso = perfil.get("peso_kg")
    test = perfil.get("test_fisiologico") or {}

    # ---------- 1. Cómo es el recorrido ----------
    L.append("### El recorrido")
    if resumen["tiene_altimetria"]:
        dp = resumen["desnivel_pos"]
        m_por_km = dp / resumen["distancia_km"] if resumen["distancia_km"] else 0
        if m_por_km < 8:
            caracter = "prácticamente llano: se va a decidir por ritmo sostenido y, si es en grupo, por saber ir a rueda"
        elif m_por_km < 15:
            caracter = "ondulado: sube y baja constantemente, lo que castiga más de lo que parece en el papel"
        elif m_por_km < 25:
            caracter = "exigente: el desnivel es un factor central de la carrera"
        else:
            caracter = "muy montañoso: acá manda la relación peso-potencia por sobre cualquier otra cosa"
        L.append(
            f"**{resumen['distancia_km']} km** con **{dp} m** de desnivel positivo "
            f"({m_por_km:.0f} m por km). Es un recorrido {caracter}."
        )
        L.append(
            f"Altura entre {resumen['alt_min']} y {resumen['alt_max']} m."
            + (" A esa altura el aire ya rinde un poco menos, aunque el efecto todavía es chico."
               if resumen["alt_max"] > 2000 else "")
        )
    else:
        L.append(
            f"**{resumen['distancia_km']} km**. El archivo no trae datos de altura, así que no puedo "
            "analizar las subidas ni estimar tiempos. Si podés conseguir el GPX con altimetría, "
            "el análisis mejora muchísimo."
        )
        return "\n\n".join(L)

    # ---------- 2. Los momentos decisivos ----------
    if subidas:
        L.append("### Dónde se define")
        L.append(f"Encontré **{len(subidas)} subidas** que importan:")
        for i, s in enumerate(exigencia or subidas, 1):
            linea = (
                f"{i}. **Km {s['km_inicio']} a {s['km_fin']}** — {s['largo_m']} m al "
                f"{s['pendiente_pct']}%, +{s['desnivel_m']} m"
            )
            if s.get("minutos"):
                if running:
                    from metrics import formatear_ritmo
                    linea += f" · te llevaría **~{s['minutos']:.0f} min** a {formatear_ritmo(s['ritmo_min_km'])}"
                    if s.get("conviene_caminar"):
                        linea += (
                            "  \n   ⚠️ Con esa pendiente, casi todo el mundo camina rápido más "
                            "eficientemente de lo que trota. Practicalo: en trail, caminar bien es una técnica."
                        )
                else:
                    linea += f" · te llevaría **~{s['minutos']:.0f} min** a {s['velocidad_kmh']} km/h"
            L.append(linea)

        mas_larga = max(exigencia or subidas, key=lambda s: s.get("minutos") or 0)
        if mas_larga.get("minutos"):
            L.append(
                f"La decisiva es la del km {mas_larga['km_inicio']}: **{mas_larga['minutos']:.0f} minutos** "
                f"de esfuerzo continuo. Ese es el esfuerzo que tenés que poder sostener sin explotar."
            )

    # ---------- 3. Cómo te iría hoy ----------
    L.append("### Cómo te iría con lo que tenés hoy")
    if running:
        if tiempo:
            L.append(
                f"Tiempo estimado: **{tiempo['texto']}**, a un ritmo medio de "
                f"**{tiempo.get('ritmo_texto', '?')}** contando el desnivel."
            )
            L.append(
                "> El cálculo parte del ritmo en llano que indicaste y encarece cada tramo según su "
                "pendiente: subir cuesta alrededor de un 3% de ritmo por cada 1% de cuesta, y bajar "
                "devuelve bastante menos de lo que quita subir. Por eso un recorrido con 500 m de "
                "subida y 500 m de bajada es más lento que el mismo en llano."
                + (" En trail se suma además un recargo por el terreno: piedras, raíces y barro "
                   "cuestan tiempo aunque el desnivel ya esté contemplado." if tipo_bici != "Asfalto" else "")
            )
    elif not ftp:
        L.append(
            "Para estimar tiempos necesito tu FTP. Cargalo en el panel de la izquierda "
            "(o cargá tu prueba de esfuerzo, que lo deduce del VT2)."
        )
    elif tiempo:
        L.append(
            f"Tiempo estimado: **{tiempo['texto']}** ({tiempo['vel_media_kmh']} km/h de media), "
            f"yendo al {intensidad*100:.0f}% de tu FTP en las subidas ({ftp*intensidad:.0f} W, "
            f"{ftp*intensidad/peso:.2f} W/kg)."
        )
        L.append(
            "> **Ojo con este número.** El tiempo es la parte menos confiable de todo esto: el modelo "
            "supone una aerodinámica y una rodadura promedio, y no sabe nada del viento, de si vas a "
            "rueda de alguien, ni de tu técnica bajando"
            + (" — que en MTB es determinante y puede cambiar el resultado más que las piernas."
               if tipo_bici == "MTB" else ".")
            + " Tomalo como un orden de magnitud, con un margen de error tranquilamente del 15%."
        )

    # ---------- 4. Qué te falta: el cruce con tus datos ----------
    L.append("### Qué deberías mejorar")
    faltantes = []

    # a) ¿Aguanto la duración total?
    if tiempo and sesiones:
        mas_larga_reciente = max((s["duracion_min"] for s in sesiones[-40:]), default=0) / 60
        horas = tiempo["horas"]
        if mas_larga_reciente < horas * 0.75:
            faltantes.append(
                f"**Resistencia para la distancia.** La carrera te llevaría unas {horas:.1f} h y tu "
                f"salida más larga reciente fue de {mas_larga_reciente:.1f} h. Antes de la carrera "
                f"convendría que hagas al menos dos salidas de {horas*0.8:.1f} h o más, aunque sean "
                "suaves: lo que se entrena ahí es tolerar el tiempo arriba de la bici, la alimentación "
                "y que no se te acalambre nada."
            )
        else:
            faltantes.append(
                f"**Resistencia: bien.** Tu salida más larga reciente ({mas_larga_reciente:.1f} h) está "
                f"en línea con la duración estimada de la carrera ({horas:.1f} h)."
            )

    # b) ¿Aguanto la subida más larga a esa intensidad?
    if exigencia:
        mas_larga = max(exigencia, key=lambda s: s.get("minutos") or 0)
        minutos_clave = mas_larga.get("minutos") or 0
        # El tipo de serie tiene que coincidir con la intensidad real que pide la
        # subida: al 85% del FTP eso es sweet spot, no umbral, y entrenar umbral
        # para una demanda de sweet spot es innecesariamente caro en fatiga.
        if intensidad >= 0.95:
            nombre_zona, receta = "umbral", "2x15 o 2x20 min"
        elif intensidad >= 0.83:
            nombre_zona, receta = "sweet spot (justo debajo del umbral)", "2x20 o 3x15 min"
        else:
            nombre_zona, receta = "tempo", "2x25 o 3x20 min"

        if minutos_clave >= 20:
            faltantes.append(
                f"**Sostener {minutos_clave:.0f} minutos a {nombre_zona}.** Eso es lo que pide la "
                f"subida clave a la intensidad que elegiste ({intensidad*100:.0f}% del FTP). "
                f"Entrenalo con series de {receta}, y andá alargando hasta poder hacer una sola de "
                f"{minutos_clave:.0f} min seguidos. Si podés, hacelas en una subida parecida."
            )
        elif minutos_clave >= 8:
            faltantes.append(
                f"**Esfuerzos de {minutos_clave:.0f} minutos a {nombre_zona}.** Series de 4x8 o "
                "3x10 min reproducen bien lo que te va a pedir la subida principal."
            )

    # c) Subidas repetidas: capacidad de repetir esfuerzos
    largas = [s for s in (exigencia or []) if (s.get("minutos") or 0) >= 8]
    if len(largas) >= 3:
        faltantes.append(
            f"**Repetir sin caerte.** Hay {len(largas)} subidas largas: lo difícil no es la primera "
            "sino llegar entero a la última. Entrenalo haciendo tus series de umbral **al final** de "
            "una salida larga, no descansado."
        )

    # d) En recorridos muy montañosos, lo que define es la relación potencia/peso.
    #    El texto encabeza por el lado que el entrenamiento sí puede cambiar - la
    #    potencia - en vez de sugerir bajar de peso, que no es algo que esta app
    #    tenga con qué aconsejar ni sepa si corresponde en cada persona.
    if peso and resumen["desnivel_pos"] / resumen["distancia_km"] > 15:
        faltantes.append(
            "**Acá manda la relación potencia/peso.** En un recorrido con este desnivel, los W/kg "
            "pesan más que cualquier otra cualidad. Lo que podés trabajar con el entrenamiento es el "
            "numerador: subir los vatios que sostenés en subidas largas, con series de umbral hechas "
            "en cuesta. Es lo mismo que ya te recomienda el punto anterior, pero acá rinde el doble."
        )

    for f in faltantes:
        L.append(f"- {f}")

    # ---------- 5. El plan hasta la carrera ----------
    if dias_hasta > 0:
        L.append(f"### Plan hasta la carrera ({dias_hasta} días)")
        semanas = dias_hasta / 7
        if semanas >= 5:
            L.append(
                f"Tenés **{semanas:.0f} semanas**, que alcanza para un bloque de trabajo real:"
            )
            L.append(
                f"- **Semanas 1 a {int(semanas)-2}:** construcción. Una sesión de umbral por semana con "
                "series parecidas a la subida clave, una tirada o salida larga progresiva, y el resto suave."
            )
            L.append(
                "- **Penúltima semana:** la más exigente, y si podés hacé un reconocimiento del "
                "recorrido o de una subida parecida."
            )
            L.append(
                "- **Última semana:** descarga. Bajás el volumen un 40-60% pero mantenés algunas "
                "series cortas y fuertes para no perder la chispa."
            )
        elif semanas >= 2:
            L.append(
                f"Quedan **{semanas:.1f} semanas**: ya no hay tiempo de construir base nueva, así que "
                "el foco es afinar. Una o dos sesiones de calidad parecidas a la subida clave, una "
                "sesión larga, y la última semana de descarga."
            )
        else:
            L.append(
                f"Quedan **{dias_hasta} días**: nada de lo que hagas ahora te va a hacer más fuerte "
                "para la carrera, pero sí te puede dejar cansado. Prioridad absoluta: llegar descansado. "
                "Salidas cortas, alguna aceleración para mantenerte despierto, y dormir bien."
            )

    # ---------- 6. El día de la carrera ----------
    L.append("### El día de la competencia" if running else "### El día de la carrera")
    if exigencia and tiempo:
        primera = min(exigencia, key=lambda s: s["km_inicio"])
        referencia = (
            "Andá a tu pulso y a sensaciones"
            if running else
            f"Andá a tus vatios ({ftp*intensidad:.0f} W si tenés potenciómetro) o a tu pulso"
        )
        L.append(
            f"**Ritmo:** la primera subida importante llega en el km {primera['km_inicio']}, "
            "temprano. El error clásico es irse con los que arrancan fuerte y pagarlo después. "
            + referencia
            + (f" —por debajo de {test['vt2_fc']} bpm, tu VT2— " if test.get("vt2_fc") else " ")
            + "en las primeras subidas, y guardate para la última."
        )
    if tiempo:
        horas = tiempo["horas"]
        if horas >= 1.5:
            L.append(
                f"**Alimentación:** con ~{horas:.1f} h de carrera, apuntá a **60-90 g de hidratos por "
                f"hora** desde el arranque (no cuando ya tenés hambre, ahí es tarde) y entre 500 y "
                f"750 ml de líquido por hora, más si hace calor. Son unos {horas*70:.0f} g de hidratos "
                f"y {horas*0.6:.1f} litros en total. Probá en los entrenamientos largos exactamente lo "
                "que vas a usar en carrera: el estómago también se entrena."
            )

    L.append(
        "> Todo esto sale de la geometría del recorrido y de tus números de entrenamiento. No sabe "
        "del viento, del calor, de cómo dormiste, ni de cómo esté el piso ese día. Usalo para "
        "planificar, no como un pronóstico."
    )

    return "\n\n".join(L)


def feedback_volumen_running(datos):
    """Texto sobre la progresión del volumen semanal de carrera."""
    if not datos:
        return None

    semanas = datos["semanas"]
    kms = [b["km"] for b in semanas]
    L = [
        "**Kilómetros por semana (últimas 6):** "
        + " → ".join(f"{k:.0f}" for k in kms)
    ]

    if datos["saltos"]:
        peor = max(datos["saltos"], key=lambda s: s["pct"])
        L.append(
            f"⚠️ Detecté un salto de **{peor['pct']}%** en el volumen semanal. La referencia habitual "
            "es no subir más de un 10-15% por semana. No es una ley exacta, pero los saltos grandes "
            "son la causa más común de lesiones por sobrecarga: tendones y huesos se adaptan mucho "
            "más lento que el corazón, así que vas a poder aguantar de aire bastante antes de que "
            "las piernas estén listas."
        )
        L.append(
            "Si esta semana venís bien, no hace falta que retrocedas — pero conviene sostener este "
            "volumen un par de semanas antes de volver a subir, en vez de encadenar otro salto."
        )
    elif kms[-1] > 0:
        L.append("✅ La progresión viene ordenada, sin saltos bruscos. Así es como se construye sin lesionarse.")

    if len([k for k in kms if k > 0]) >= 4 and kms[-1] > 0:
        promedio = sum(kms[-4:]) / 4
        if kms[-1] > promedio * 1.5:
            L.append("Esta semana está bastante por encima de tu promedio reciente: buen momento para una semana más suave.")

    return "\n\n".join(L)


def feedback_prediccion_carreras(datos, perfil):
    """Texto con los tiempos proyectados para las distancias clásicas."""
    if not datos:
        return (
            "Todavía no tengo una carrera continua de 5 km o más en los últimos meses como para "
            "proyectar tiempos. Con una salida a ritmo sostenido alcanza."
        )

    base = datos["base"]
    L = [
        f"Tomando como referencia tu mejor esfuerzo reciente — **{base['distancia_km']:.1f} km "
        f"a {base.get('ritmo_texto', '?')}** ({base['fecha'][:10]}):"
    ]

    for p in datos["predicciones"]:
        marca = {"alta": "", "media": " ·  confianza media", "baja": " ·  ⚠️ confianza baja"}[p["confianza"]]
        L.append(f"- **{p['nombre']}:** {p['texto']} ({p['ritmo']}){marca}")

    L.append(
        "Esto sale de la fórmula de Riegel, que es la predicción más usada y funciona razonablemente "
        "entre 5 km y maratón. **Pero tiene un supuesto grande:** asume que entrenaste lo suficiente "
        "para la distancia objetivo. Proyectar un maratón desde un 10 km sin haber hecho tiradas "
        "largas da un número lindo que después no se cumple — en maratón lo que falla no suele ser "
        "el motor sino las piernas y el combustible."
    )
    L.append(
        "Por eso las distancias más lejanas a tu referencia aparecen marcadas con menos confianza."
    )
    return "\n\n".join(L)


def feedback_dinamicas_carrera(sesion):
    """
    Interpreta las dinámicas de la zancada: tiempo de contacto con el suelo,
    oscilación vertical, ratio vertical y longitud de zancada.

    Solo aparecen si tu reloj las mide (hace falta banda HRM-Pro, Running
    Dynamics Pod, o un reloj reciente con el sensor incorporado).
    """
    gct = sesion.get("contacto_suelo_ms")
    osc = sesion.get("oscilacion_vertical_cm")
    ratio = sesion.get("ratio_vertical_pct")
    zancada = sesion.get("zancada_m")
    balance = sesion.get("balance_contacto")

    if not any((gct, osc, ratio, zancada)):
        return None

    L = ["**Dinámicas de la zancada**"]

    if gct:
        if gct < 210:
            t = "muy bajo, propio de corredores rápidos y elásticos"
        elif gct < 260:
            t = "en un buen rango"
        elif gct < 300:
            t = "en el rango habitual de corredores aficionados"
        else:
            t = "alto: pasás bastante tiempo apoyado en cada paso"
        L.append(f"- **Contacto con el suelo: {gct:.0f} ms** — {t}.")

    if osc:
        if osc < 7.5:
            t = "muy contenida, poca energía perdida en subir y bajar"
        elif osc < 9.5:
            t = "en un buen rango"
        elif osc < 11:
            t = "algo alta: rebotás un poco más de lo ideal"
        else:
            t = "alta: bastante energía se va en subir el cuerpo en vez de empujarlo hacia adelante"
        L.append(f"- **Oscilación vertical: {osc:.1f} cm** — {t}.")

    if ratio:
        if ratio < 6.5:
            t = "excelente"
        elif ratio < 8:
            t = "bueno"
        elif ratio < 10:
            t = "en el rango habitual"
        else:
            t = "mejorable"
        L.append(
            f"- **Ratio vertical: {ratio:.1f}%** — {t}. Es la oscilación dividida por la zancada, "
            "y de las tres es la más útil: mide cuánto de tu movimiento va hacia arriba en vez de "
            "hacia adelante."
        )

    if zancada:
        L.append(f"- **Longitud de zancada: {zancada:.2f} m.**")

    if balance:
        desvio = abs(balance - 50)
        if desvio < 1.5:
            L.append(f"- **Balance de apoyo: {balance:.1f}%** — parejo entre las dos piernas.")
        else:
            L.append(
                f"- **Balance de apoyo: {balance:.1f}%** — hay una asimetría de {desvio:.1f} puntos "
                "entre una pierna y la otra. Un desvío chico es normal; si se mantiene sesión tras "
                "sesión y encima te molesta algo, vale la pena que lo mire un kinesiólogo."
            )

    L.append(
        "> Un matiz importante: estos números son sobre todo **una consecuencia** de tu forma física "
        "y de la velocidad a la que vas, no una causa. Mejoran solos cuando mejorás como corredor. "
        "Forzar la técnica para bajarlos (acortar el contacto a propósito, por ejemplo) suele terminar "
        "en lesiones. Lo único que sí conviene trabajar de forma directa es la cadencia."
    )
    return "\n".join(L)


def feedback_carga_running(datos_rtss, sesion, ritmo_umbral):
    """Explica el rTSS y por qué convive con el TRIMP en vez de reemplazarlo."""
    if not datos_rtss:
        return None
    from metrics import formatear_ritmo

    L = [
        f"**Carga por ritmo (rTSS): {datos_rtss['rtss']:.0f}** · intensidad "
        f"{datos_rtss['intensidad']:.2f} respecto de tu ritmo de umbral "
        f"({formatear_ritmo(ritmo_umbral)})."
    ]
    if datos_rtss["uso_gap"]:
        L.append(
            "Se calculó con el ritmo ajustado por pendiente, que para esto es más justo: una hora "
            "subiendo cuesta mucho más que una hora en llano al mismo ritmo de reloj."
        )
    L.append(
        f"Un rTSS de 100 equivale a una hora exacta a ritmo de umbral. Esta sesión te costó "
        f"{datos_rtss['rtss']:.0f}, y la carga por pulso (TRIMP) dio {sesion['trimp']:.0f}."
    )
    L.append(
        "> Los dos números miden lo mismo por caminos distintos y no son intercambiables. El TRIMP "
        "mide por el pulso: sirve siempre, pero en series cortas se queda corto porque el corazón "
        "tarda en subir. El rTSS mide por el ritmo y capta mejor esas sesiones, pero necesita saber "
        "tu ritmo de umbral. La app usa el TRIMP para el gráfico de forma —porque funciona en todas "
        "las sesiones— y te muestra el rTSS al lado como segunda opinión."
    )
    return "\n\n".join(L)


def feedback_potencia_running(datos):
    """Potencia de carrera, con la advertencia que corresponde."""
    if not datos:
        return None
    L = [f"**Potencia de carrera: {datos['watts']} W**"
         + (f" · {datos['w_kg']} W/kg" if datos.get("w_kg") else "")]
    if datos.get("normalizada"):
        L.append(f"Potencia normalizada: {datos['normalizada']} W.")
    L.append(
        "> ⚠️ La potencia en carrera **no está estandarizada**. Garmin, Stryd, Coros y Polar la "
        "calculan con modelos distintos y sus números no se pueden comparar entre sí. Tampoco es "
        "comparable con la potencia de ciclismo, que mide trabajo mecánico real sobre los pedales. "
        "Sirve para compararte con vos mismo usando siempre el mismo dispositivo, y para nada más."
    )
    return "\n\n".join(L)


def feedback_hrv(estado, comparacion_ef, correlacion, sin_datos=0):
    """Interpreta los tres análisis de variabilidad de la frecuencia cardíaca."""
    L = []

    # --- Estado de hoy ---
    if not estado:
        return (
            "No encontré datos de variabilidad cardíaca en tu cuenta. Garmin la mide durante el "
            "sueño, así que hace falta dormir con el reloj puesto y tener un modelo que la reporte."
        )

    if estado.get("lectura") == "sin_base":
        L.append(
            f"**VFC de anoche: {estado['rmssd']} ms.** Todavía no tengo suficientes noches como para "
            "saber si eso es alto o bajo *para vos*. Con una semana más de datos, esta sección "
            "empieza a servir."
        )
    else:
        textos = {
            "muy_baja": ("🔴", "bastante por debajo de tu promedio reciente. Suele significar que el cuerpo "
                              "todavía está procesando algo: carga acumulada, poco sueño, estrés, alcohol o "
                              "el arranque de una infección. Hoy no es día para la sesión más dura de la semana."),
            "baja": ("🟠", "algo por debajo de tu promedio. Una sola noche no dice mucho; si se repite dos o "
                          "tres días seguidos, conviene bajar la intensidad."),
            "normal": ("⚪", "dentro de tu rango habitual. Podés entrenar según lo planificado."),
            "alta": ("🟢", "por encima de tu promedio: buena señal de recuperación. Es un buen día para la "
                          "sesión exigente si la tenías prevista."),
        }
        icono, texto = textos[estado["lectura"]]
        L.append(
            f"{icono} **VFC de anoche: {estado['rmssd']} ms** — {texto}"
        )
        L.append(
            f"Tu promedio de los últimos días viene en {estado['base']} ms. Lo que importa no es el "
            "número absoluto —depende muchísimo de cada persona, y compararlo con el de otro no "
            "significa nada— sino cuánto te apartás de tu propio promedio."
        )

    # --- Eficiencia según VFC ---
    if comparacion_ef:
        L.append("### ¿Rendís mejor los días de VFC alta?")
        L.append(
            "Comparando **solo sesiones del mismo tipo** (para que la comparación sea justa), esto es "
            "lo que dan tus datos:"
        )
        import coach
        for g in comparacion_ef:
            signo = "mejor" if (g["diferencia_pct"] or 0) > 0 else "peor"
            L.append(
                f"- **{coach.NOMBRE_TIPO[g['tipo']]}**: {g['ef_alta']} con VFC alta vs {g['ef_baja']} "
                f"con VFC baja ({g['unidad']}) — **{abs(g['diferencia_pct']):.0f}% {signo}** los días "
                f"de buena VFC. Basado en {g['n_alta']} y {g['n_baja']} sesiones."
            )
        L.append(
            "> Esa comparación se hace dentro de cada tipo de sesión a propósito. Cruzar la VFC contra "
            "tu mejor potencia del día daría un resultado engañoso: la potencia alta aparece cuando "
            "hacés una sesión dura, no cuando estás recuperado. Agrupando por tipo, ese sesgo se va."
        )
        L.append(
            "> Y ojo con la cantidad de sesiones: con menos de una decena por grupo, una diferencia "
            "chica puede ser simplemente azar."
        )

    # --- VFC contra la carga ---
    if correlacion:
        r = correlacion["correlacion"]
        L.append("### ¿El modelo de carga describe bien tu fisiología?")
        if r >= 0.3:
            veredicto = (
                f"**Sí (correlación {r:+.2f} en {correlacion['n']} días).** Tu VFC baja cuando el TSB se "
                "hunde y se recupera cuando descansás. Eso significa que el cálculo de carga de la app "
                "está describiendo bien cómo responde tu cuerpo — podés confiar en él para planificar."
            )
        elif r <= -0.3:
            veredicto = (
                f"**Al revés de lo esperable (correlación {r:+.2f}).** Tu VFC sube cuando el TSB se hunde. "
                "Es raro y vale la pena mirarlo con cuidado: a veces pasa cuando la VFC se mide en "
                "condiciones muy distintas de una noche a otra."
            )
        else:
            veredicto = (
                f"**No demasiado (correlación {r:+.2f} en {correlacion['n']} días).** Tu VFC y el modelo de "
                "carga se mueven bastante independientes. Puede ser que la fatiga te afecte por otro lado, "
                "o que tu VFC responda más al sueño y al estrés del trabajo que al entrenamiento. En ese "
                "caso, la VFC te sirve igual como señal de recuperación general, pero no la uses para "
                "juzgar si el entrenamiento fue mucho o poco."
            )
        L.append(veredicto)

    if sin_datos:
        L.append(f"*Nota: {sin_datos} de los días consultados no tenían datos de VFC (noches sin el reloj puesto).*")

    return "\n\n".join(L)
