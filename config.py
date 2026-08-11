# config.py
"""
Valores por defecto de la aplicación.

IMPORTANTE: acá NO van tus datos personales. Todo lo tuyo (edad, peso, FTP y los
resultados de tu ergoespirometría) se carga desde la propia app, en la barra
lateral, y se guarda en data/perfil.json - un archivo que es solo tuyo y que no
se comparte cuando le pasás la app a otra persona.
"""

# Valores de arranque, genéricos. Se pisan con lo que cargues desde la app.
PERFIL = {
    "nombre": "Ciclista",
    "edad": 40,
    "peso_kg": 75.0,
    "altura_m": 1.75,
    "fc_reposo": 60,   # FC en reposo (bpm). Medila apenas te despertás, en la cama,
                       # promediando 3-4 días. Es el dato que más afecta la precisión
                       # de tus zonas si las calculás por fórmula.
    "fc_max": None,    # Si la conocés de un test real, cargala desde la app.
                       # Si no, se estima con la fórmula de Tanaka.
    "ftp_watts": None, # Tu FTP en vatios, si entrenás con potenciómetro.
    "usar_zonas_fc_lab": False,   # Se activa solo cuando cargás una ergoespirometría.
    "test_fisiologico": None,      # Los datos de tu ergoespirometría (se cargan desde la app).
    "zonas_lab": None,             # Tabla de 5 zonas del estudio (o derivada de tus umbrales).
}


def estimar_fc_max(edad):
    """
    Fórmula de Tanaka (2001): 208 - 0.7 x edad.
    Es más precisa que la clásica '220 - edad' para adultos de más de 40 años.
    De todas formas, nada le gana a un test real de FC máxima.
    """
    return round(208 - 0.7 * edad)


def derivar_zonas_desde_umbrales(vt1_fc, vt2_fc, fc_max):
    """
    Arma una tabla de 5 zonas de FC a partir de tus umbrales ventilatorios reales.

    Se usa cuando cargaste tu ergoespirometría pero no querés tipear a mano las
    20 cifras de la tabla de zonas del informe. Es bastante fiel a cómo las arman
    los laboratorios, porque parte de los mismos dos puntos fisiológicos (VT1 y VT2):

      Z1  arranca en ~53% de la FC máxima (piso típico de calentamiento)
      Z2  termina justo en VT1  (todo el trabajo aeróbico de base)
      Z3  de VT1 al punto medio entre umbrales (tempo)
      Z4  de ese punto medio hasta VT2 (umbral)
      Z5  de VT2 hasta la FC máxima (VO2max / anaeróbico)

    Si tenés la tabla exacta del informe, siempre es preferible cargarla a mano.
    """
    if not (vt1_fc and vt2_fc and fc_max):
        return None

    piso = round(0.53 * fc_max)
    z2_inicio = max(piso + 1, vt1_fc - 15)
    medio = round((vt1_fc + vt2_fc) / 2)

    return {
        1: {"nombre": "Recuperación / calentamiento", "fc": (piso, z2_inicio), "watts": None},
        2: {"nombre": "Aeróbico de base", "fc": (z2_inicio, vt1_fc), "watts": None},
        3: {"nombre": "Tempo", "fc": (vt1_fc, medio), "watts": None},
        4: {"nombre": "Umbral", "fc": (medio, vt2_fc), "watts": None},
        5: {"nombre": "VO2max / anaeróbico", "fc": (vt2_fc, fc_max), "watts": None},
    }


# Pesos de zona para el cálculo de carga de entrenamiento (TRIMP, método Edwards).
# Cuanto más intensa la zona, más "cara" sale un minuto en ella.
PESO_ZONA = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}

# Constantes de tiempo (en días) para el cálculo de Fitness (CTL) y Fatiga (ATL).
# Son los valores estándar que usa todo el mundo del ciclismo (Coggan / TrainingPeaks).
CTL_DIAS = 42
ATL_DIAS = 7

def _carpeta_datos():
    """
    Dónde se guardan tu perfil y tus RPE.

    Corriendo normalmente: la carpeta `data` del proyecto.

    Corriendo como .exe: la carpeta del usuario. Es imprescindible que sea así,
    porque PyInstaller descomprime la aplicación en una carpeta temporal que
    Windows borra al cerrar - si los datos se guardaran ahí, cada persona
    perdería su perfil cada vez que cierra la app.
    """
    import sys
    from pathlib import Path

    if getattr(sys, "frozen", False):
        carpeta = Path.home() / ".mi_coach_ciclismo" / "datos"
        carpeta.mkdir(parents=True, exist_ok=True)
        return str(carpeta)
    return "data"


RUTA_DATOS = _carpeta_datos()

# Colores por zona - se usan tanto en los gráficos como en las etiquetas de feedback,
# para que el mismo color siempre signifique la misma intensidad en toda la app.
# Es la misma convención "semáforo de esfuerzo" que usan los ciclocomputadores.
ZONA_COLOR = {
    1: "#6FBFA8",  # recuperación
    2: "#2F9B80",  # aeróbico
    3: "#DFA015",  # tempo
    4: "#CE7328",  # umbral
    5: "#CB4433",  # VO2max / anaeróbico
}

ZONA_COLOR_POTENCIA = {
    1: "#4C9BE8",
    2: "#4CC9A0",
    3: "#E8C94C",
    4: "#E8934C",
    5: "#E85C4C",
    6: "#C24CE8",  # capacidad anaeróbica - magenta
    7: "#7A4CE8",  # neuromuscular - violeta
}
