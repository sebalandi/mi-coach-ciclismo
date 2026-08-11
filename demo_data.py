# demo_data.py
"""
Genera actividades de ejemplo con el mismo formato que devuelve Garmin Connect,
para poder probar la app sin conectarte a tu cuenta todavía. Simula un patrón
realista: 3-4 salidas de bici y 2 sesiones de gym por semana.
"""

import random
from datetime import date, timedelta

# Reparto de tiempo en zonas de potencia (Coggan, 7 zonas) según el tipo de sesión.
# Se usa solo para simular el detalle que a veces manda Garmin ('powerTimeInZone_1'.._7).
REPARTO_POTENCIA = {
    "suave":  {1: 0.15, 2: 0.55, 3: 0.20, 4: 0.07, 5: 0.02, 6: 0.01, 7: 0.00},
    "umbral": {1: 0.05, 2: 0.15, 3: 0.15, 4: 0.35, 5: 0.20, 6: 0.08, 7: 0.02},
    "fuerte": {1: 0.05, 2: 0.10, 3: 0.10, 4: 0.20, 5: 0.25, 6: 0.20, 7: 0.10},
}


def generar_actividades_demo(dias=90):
    actividades = []
    hoy = date.today()
    activity_id = 1000

    for i in range(dias, 0, -1):
        dia = hoy - timedelta(days=i)
        dow = dia.weekday()  # 0 = lunes

        es_dia_bici = dow in (1, 3, 5, 6)   # martes, jueves, sábado, domingo
        es_dia_gym = dow in (0, 4)          # lunes, viernes

        if es_dia_bici and random.random() > 0.15:
            tipo_sesion = random.choices(
                ["suave", "umbral", "fuerte"], weights=[0.6, 0.25, 0.15]
            )[0]

            if tipo_sesion == "suave":
                duracion = random.randint(50, 100) * 60
                fc_prom = random.randint(110, 128)
                reparto = {1: 0.35, 2: 0.55, 3: 0.08, 4: 0.02, 5: 0.00}
                nombre = "Salida en bici - fondo suave"
            elif tipo_sesion == "umbral":
                duracion = random.randint(45, 75) * 60
                fc_prom = random.randint(140, 155)
                reparto = {1: 0.10, 2: 0.25, 3: 0.20, 4: 0.35, 5: 0.10}
                nombre = "Salida en bici - series de umbral"
            else:
                duracion = random.randint(35, 55) * 60
                fc_prom = random.randint(150, 165)
                reparto = {1: 0.10, 2: 0.15, 3: 0.15, 4: 0.30, 5: 0.30}
                nombre = "Salida en bici - intervalos fuertes"

            actividad = {
                "activityId": activity_id,
                "activityName": nombre,
                "startTimeLocal": f"{dia} 07:30:00",
                "activityType": {"typeKey": random.choices(
                    ["road_biking", "mountain_biking", "gravel_cycling", "indoor_cycling"],
                    weights=[0.45, 0.25, 0.10, 0.20],
                )[0]},
                "duration": duracion,
                "distance": duracion / 60 * random.randint(400, 550),
                "elevationGain": random.randint(50, 600),
                "averageHR": fc_prom,
                "maxHR": fc_prom + random.randint(10, 25),
                "averageBikingCadenceInRevPerMinute": random.randint(75, 92),
                "calories": int(duracion / 60 * random.uniform(8, 11)),
            }
            for z in range(1, 6):
                actividad[f"hrTimeInZone_{z}"] = round(reparto[z] * duracion)  # segundos

            # ~70% de las salidas simulan tener medidor de potencia (ej: la bici de ruta sí,
            # la gravel no), para probar que la app funciona bien con equipo mixto.
            if random.random() < 0.7:
                rangos_potencia = {"suave": (140, 190), "umbral": (200, 240), "fuerte": (220, 270)}
                variabilidad = {"suave": 1.05, "umbral": 1.08, "fuerte": 1.18}[tipo_sesion]
                avg_power = random.randint(*rangos_potencia[tipo_sesion])
                actividad["avgPower"] = avg_power
                actividad["normPower"] = round(avg_power * variabilidad)
                actividad["maxPower"] = round(avg_power * random.uniform(1.6, 2.3))

                if random.random() < 0.5:
                    reparto_pot = REPARTO_POTENCIA[tipo_sesion]
                    for z in range(1, 8):
                        actividad[f"powerTimeInZone_{z}"] = round(reparto_pot[z] * duracion)

            actividades.append(actividad)
            activity_id += 1

        # Running: martes, jueves y domingo, alternando asfalto y montaña
        if dow in (1, 3, 6) and random.random() > 0.35:
            tipo_run = random.choices(["suave", "umbral", "largo"], weights=[0.55, 0.25, 0.2])[0]
            montana = random.random() < 0.4

            if tipo_run == "suave":
                duracion = random.randint(35, 55) * 60
                ritmo = random.uniform(6.0, 6.6)
                fc_prom = random.randint(132, 145)
                reparto = {1: 0.30, 2: 0.55, 3: 0.12, 4: 0.03, 5: 0.00}
                nombre = "Rodaje suave"
            elif tipo_run == "umbral":
                duracion = random.randint(40, 55) * 60
                ritmo = random.uniform(5.0, 5.5)
                fc_prom = random.randint(155, 166)
                reparto = {1: 0.15, 2: 0.25, 3: 0.20, 4: 0.32, 5: 0.08}
                nombre = "Series de umbral"
            else:
                duracion = random.randint(75, 110) * 60
                ritmo = random.uniform(6.2, 6.9)
                fc_prom = random.randint(138, 150)
                reparto = {1: 0.25, 2: 0.60, 3: 0.12, 4: 0.03, 5: 0.00}
                nombre = "Tirada larga"

            distancia_m = (duracion / 60) / ritmo * 1000
            act_run = {
                "activityId": activity_id,
                "activityName": nombre + (" (montaña)" if montana else ""),
                "startTimeLocal": f"{dia} 07:00:00",
                "activityType": {"typeKey": "trail_running" if montana else "running"},
                "duration": duracion,
                "distance": distancia_m,
                "elevationGain": random.randint(250, 700) if montana else random.randint(10, 80),
                "averageHR": fc_prom,
                "maxHR": fc_prom + random.randint(8, 20),
                "averageRunningCadenceInStepsPerMinute": random.randint(158, 178),
                "elevationLoss": (random.randint(240, 690) if montana else random.randint(10, 75)),
                # Dinámicas de carrera: solo si el reloj las mide, así que en el
                # ejemplo aparecen en parte de las sesiones, como en la vida real
                **({
                    "avgGroundContactTime": random.randint(230, 300),
                    "avgVerticalOscillation": round(random.uniform(8.0, 11.5), 1),
                    "avgStrideLength": random.randint(105, 130),
                    "avgGroundContactBalance": round(random.uniform(48.5, 51.5), 1),
                } if random.random() < 0.7 else {}),
                "calories": int(duracion / 60 * random.uniform(10, 13)),
            }
            for z in range(1, 6):
                act_run[f"hrTimeInZone_{z}"] = round(reparto[z] * duracion)
            actividades.append(act_run)
            activity_id += 1

        if es_dia_gym and random.random() > 0.2:
            duracion = random.randint(40, 65) * 60
            actividades.append({
                "activityId": activity_id,
                "activityName": "Gimnasio",
                "startTimeLocal": f"{dia} 19:00:00",
                "activityType": {"typeKey": "strength_training"},
                "duration": duracion,
                "distance": 0,
                "elevationGain": 0,
                "averageHR": random.randint(95, 115),
                "maxHR": random.randint(120, 140),
                "calories": int(duracion / 60 * random.uniform(5, 7)),
            })
            activity_id += 1

    return actividades


def generar_serie_demo(sesion):
    """
    Genera una serie sintética segundo a segundo (FC, potencia y velocidad) para poder
    probar el análisis de deriva cardíaca y la curva de potencia en modo demo, ya que no
    tenemos el time-series real de Garmin acá. Simula una deriva leve/moderada al azar,
    y picos de potencia si la sesión parece intervalica (NP bastante más alta que el promedio).
    """
    duracion_seg = max(int(sesion["duracion_min"] * 60), 60)
    fc_base = sesion.get("fc_prom") or 130
    potencia_base = sesion.get("potencia_prom") if sesion.get("tiene_potencia") else None
    potencia_np = sesion.get("potencia_normalizada")
    velocidad_base = sesion.get("velocidad_kmh") or 25
    es_intervalica = bool(potencia_base and potencia_np and potencia_np > potencia_base * 1.1)

    deriva_simulada = random.uniform(2, 12)  # % de deriva a lo largo de la sesión
    ciclo_intervalo = random.randint(180, 420)
    largo_intervalo = random.randint(40, 150)

    elevacion_total = sesion.get("elevacion_m") or 0
    incremento_medio = elevacion_total / duracion_seg if duracion_seg else 0

    fc, potencia, velocidad, altitud, distancia, tiempo = [], [], [], [], [], []
    alt_acum = 100.0   # altitud de partida arbitraria
    dist_acum = 0.0
    for i in range(duracion_seg):
        progreso = i / duracion_seg
        ruido = random.uniform(-3, 3)
        ajuste = deriva_simulada / 100 * fc_base * (progreso - 0.5)
        fc_val = fc_base + ajuste + ruido

        pot_val = None
        if potencia_base:
            pot_val = potencia_base + random.uniform(-15, 15)
            # Los intervalos se generan con duración y separación variables. Con un
            # patrón fijo (siempre 30 s cada 240 s) los datos quedan tan regulares
            # que producen curvas de potencia imposibles en la vida real.
            if es_intervalica and (i % ciclo_intervalo) < largo_intervalo:
                pot_val = potencia_base * random.uniform(1.6, 2.1)
                fc_val += 8
            potencia.append(round(pot_val))
        else:
            potencia.append(None)

        fc.append(round(fc_val))
        velocidad.append(round(velocidad_base + random.uniform(-2, 2), 1))

        alt_acum += incremento_medio + random.uniform(-0.4, 0.4)
        altitud.append(round(alt_acum, 1))
        dist_acum += velocidad[-1] / 3.6          # km/h a metros por segundo
        distancia.append(round(dist_acum, 1))
        tiempo.append(i)

    return {"fc": fc, "potencia": potencia, "velocidad": velocidad,
            "altitud": altitud, "distancia": distancia, "tiempo": tiempo}

