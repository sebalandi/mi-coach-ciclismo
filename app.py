# app.py
"""
Mi Coach de Ciclismo - Dashboard que analiza tus entrenos de Garmin Connect
y te da feedback en lenguaje simple, pensado para entrenar con pulsómetro
(con o sin potenciómetro).

Para correrla:
    streamlit run app.py       (o doble clic en iniciar_app.bat en Windows)
"""

import os
import re

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date, timedelta

import config
import garmin_client
import metrics
import feedback
import coach
import demo_data
import hrv
import importar_actividad
import ruta
import rpe_store
import perfil_store
import version
import actualizador

st.set_page_config(page_title="Mi Coach de Ciclismo", layout="wide", page_icon="🚴")

# Los conjuntos de tipos de actividad viven en metrics.py, para que los use
# tanto la interfaz como el análisis sin duplicar la definición.



# ---------------------------------------------------------------------------
# Chequeo de consistencia entre archivos
# ---------------------------------------------------------------------------
# Al actualizar el proyecto es fácil que Windows reemplace unos archivos y otros
# no (si al descomprimir se elige "omitir" en alguno). El síntoma es un error
# críptico del tipo "el módulo X no tiene el atributo Y" en medio de la pantalla.
# Este chequeo lo detecta al arrancar y explica qué hacer.
_REQUISITOS = {
    "feedback": ["feedback_dinamicas_carrera", "feedback_carga_running",
                 "feedback_potencia_running", "feedback_vam", "feedback_recorrido"],
    "metrics": ["perfil_para_running", "calcular_rtss", "ritmo_umbral_estimado",
                "potencia_running", "calcular_mejor_vam"],
    "coach": ["analisis_profundo", "distribucion_3_dominios", "analisis_competencia"],
    "ruta": ["estimar_tiempo_running", "analizar_subidas_running"],
    "importar_actividad": ["leer_archivo", "a_actividad"],
    "hrv": ["traer_rango", "linea_de_base", "eficiencia_segun_vfc"],
    "actualizador": ["consultar", "aplicar", "revertir"],
}

_faltantes = []
for _mod, _funcs in _REQUISITOS.items():
    _obj = {"feedback": feedback, "metrics": metrics, "coach": coach,
            "ruta": ruta, "importar_actividad": importar_actividad, "hrv": hrv,
            "actualizador": actualizador}[_mod]
    for _f in _funcs:
        if not hasattr(_obj, _f):
            _faltantes.append(f"{_mod}.py")
            break

if _faltantes:
    st.error(
        "### Los archivos del proyecto no coinciden entre sí\n\n"
        f"Estos quedaron desactualizados: **{', '.join(sorted(set(_faltantes)))}**\n\n"
        "Pasa cuando al descomprimir el zip se reemplazan unos archivos y otros no.\n\n"
        "**Cómo arreglarlo:**\n\n"
        "1. Cerrá la aplicación.\n"
        "2. Borrá la carpeta `garmin_coach` entera (tus datos NO están ahí: viven en "
        "`C:\\Users\\TuUsuario\\.mi_coach_ciclismo`).\n"
        "3. Descomprimí el zip de nuevo, completo.\n"
        "4. Volvé a abrir con `iniciar_app.bat`."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Estilo
# ---------------------------------------------------------------------------
# Dirección visual: "informe de laboratorio", no "dashboard deportivo".
# Los datos de esta app vienen de una ergoespirometría y giran alrededor de dos
# líneas fisiológicas (VT1 y VT2), así que el diseño toma prestado el lenguaje
# del papel clínico: fondo claro, reglas finas, números en monoespaciada y mucho
# aire. El elemento distintivo es la "cinta de umbrales" que se repite en tres
# escalas y siempre significa lo mismo.
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root {
  --paper:#FBFCFD; --surface:#FFFFFF; --ink:#131A22; --ink-soft:#5A6672;
  --ink-faint:#6B7783; --rule:#E4EAF0; --rule-strong:#CBD5DF; --accent:#2D4A7C;
  --z-baja:#2F9B80; --z-media:#DFA015; --z-alta:#CB4433;
}

html, body, [data-testid="stAppViewContainer"] {
  background: var(--paper); color: var(--ink);
  font-family:'IBM Plex Sans', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"], [data-testid="stDecoration"], footer { display:none !important; }
.block-container { padding-top: 2.2rem; max-width: 1180px; }

h1,h2,h3,h4 { font-family:'Archivo', sans-serif !important; letter-spacing:-0.018em; color:var(--ink); }
h1 { font-weight:700; font-size:1.9rem; }
h2 { font-weight:600; font-size:1.25rem; }
h3 { font-weight:600; font-size:1.02rem; }
p, li { font-family:'IBM Plex Sans', sans-serif; line-height:1.62; color:var(--ink); }
[data-testid="stMetric"] { display:none; }

/* Barra superior */
.gc-topbar {
  display:flex; align-items:baseline; justify-content:space-between;
  border-bottom:1px solid var(--rule-strong); padding-bottom:.7rem; margin-bottom:1.9rem;
}
.gc-wordmark { font-family:'Archivo',sans-serif; font-weight:700; font-size:1.02rem; letter-spacing:.02em; }
.gc-wordmark span { color:var(--accent); }

/* Etiquetas de sección */
/* --- Títulos de sección ---
   Antes iban en gris claro, chicos y en mayúsculas finas: se perdían al
   hacer scroll y costaba ubicarse en una pantalla larga. Ahora van en el
   azul de la app, más grandes y con una barra vertical al costado que hace
   de ancla visual. El contraste pasó de 4,6:1 a 8,8:1. */
.gc-eyebrow {
  font-family:'Archivo',sans-serif; font-size:.82rem; font-weight:700;
  text-transform:uppercase; letter-spacing:.12em; color:var(--accent);
  display:flex; align-items:center; gap:.7rem; margin:3rem 0 1.05rem 0;
}
.gc-eyebrow::before {
  content:""; width:4px; height:1.05em; flex:none;
  background:var(--accent); border-radius:2px;
}
.gc-eyebrow::after { content:""; flex:1; height:1px; background:var(--rule-strong); }
.gc-eyebrow:first-child { margin-top:0; }

/* Hero: la última sesión */
.gc-hero { background:var(--surface); border:1px solid var(--rule); border-radius:3px; padding:1.6rem 1.8rem 1.5rem; }
.gc-hero-top { display:flex; align-items:baseline; justify-content:space-between; flex-wrap:wrap; gap:.5rem; }
.gc-hero-tipo { font-family:'Archivo',sans-serif; font-weight:700; font-size:1.75rem; letter-spacing:-.02em; }
.gc-hero-fecha { font-family:'IBM Plex Mono',monospace; font-size:.76rem; color:var(--ink-faint); }
.gc-hero-datos {
  font-family:'IBM Plex Mono',monospace; font-size:.86rem; color:var(--ink-soft);
  margin-top:.35rem; display:flex; gap:1.15rem; flex-wrap:wrap;
}
.gc-hero-datos b { color:var(--ink); font-weight:600; }

/* --- Cinta de umbrales: el elemento distintivo --- */
.gc-ribbon { display:flex; width:100%; height:13px; border-radius:2px; overflow:hidden; background:var(--rule); }
.gc-ribbon.sm { height:6px; }
.gc-ribbon i { display:block; height:100%; }
.gc-ribbon .b { background:var(--z-baja); }
.gc-ribbon .m { background:var(--z-media); }
.gc-ribbon .a { background:var(--z-alta); }
.gc-ribbon-marks {
  position:relative; height:1.15rem; margin-top:.3rem;
  font-family:'IBM Plex Mono',monospace; font-size:.66rem; color:var(--ink-faint);
}
.gc-ribbon-marks span { position:absolute; transform:translateX(-50%); white-space:nowrap; }
.gc-ribbon-legend {
  display:flex; gap:1.3rem; margin-top:.5rem;
  font-family:'IBM Plex Mono',monospace; font-size:.73rem; color:var(--ink-soft);
}
.gc-ribbon-legend em { font-style:normal; font-weight:600; color:var(--ink); }
.gc-dot { display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:.4rem; vertical-align:middle; }

/* Tarjetas de estado */
.gc-stats { display:flex; gap:0; border:1px solid var(--rule); border-radius:3px; background:var(--surface); }
.gc-stat { flex:1; padding:1.05rem 1.25rem; border-right:1px solid var(--rule); }
.gc-stat:last-child { border-right:none; }
.gc-stat-k {
  font-family:'Archivo',sans-serif; font-size:.66rem; font-weight:600;
  text-transform:uppercase; letter-spacing:.13em; color:var(--ink-faint);
}
.gc-stat-v { font-family:'IBM Plex Mono',monospace; font-size:1.85rem; font-weight:600; line-height:1.15; margin-top:.15rem; }
.gc-stat-d { font-size:.76rem; color:var(--ink-soft); line-height:1.45; margin-top:.3rem; }
.gc-stat-scale { position:relative; height:3px; background:var(--rule); border-radius:2px; margin-top:.65rem; }
.gc-stat-scale i { position:absolute; top:-3px; width:2px; height:9px; background:var(--ink); border-radius:1px; }

/* Widgets de Streamlit */
[data-testid="stSidebar"] { background:var(--surface); border-right:1px solid var(--rule); }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3 { font-size:.95rem; }
/* --- Desplegables: tienen que leerse como botones, no como texto --- */
[data-testid="stExpander"] {
  border:1px solid var(--rule-strong) !important; border-radius:3px !important;
  background:var(--surface); transition:border-color .12s, background .12s;
}
[data-testid="stExpander"] summary {
  font-family:'IBM Plex Sans',sans-serif !important;
  font-weight:600 !important; font-size:.93rem !important;
  color:var(--ink) !important; padding:.72rem .95rem !important;
}
[data-testid="stExpander"]:hover { border-color:var(--accent) !important; background:#F5F8FB; }
[data-testid="stExpander"]:hover summary { color:var(--accent) !important; }
/* La flecha es un svg dentro del summary; el otro es el icono propio que le paso */
[data-testid="stExpander"] summary svg {
  width:1.3rem !important; height:1.3rem !important; fill:var(--accent) !important;
  transition:transform .15s;
}
[data-testid="stExpanderIcon"] { color:var(--accent) !important; }
[data-testid="stExpander"] summary { cursor:pointer; }
[data-testid="stExpander"] summary:hover svg { fill:var(--ink) !important; }

/* --- Fila de sesión: todo lo importante visible sin abrir --- */
.gc-sesion {
  background:var(--surface); border:1px solid var(--rule); border-left:3px solid var(--accent);
  border-radius:3px 3px 0 0; border-bottom:none; padding:.75rem .95rem .6rem;
  margin-top:1rem;
}
.gc-sesion-top {
  display:flex; align-items:baseline; gap:.85rem; flex-wrap:wrap; margin-bottom:.6rem;
}
.gc-sesion-fecha {
  font-family:'IBM Plex Mono',monospace; font-size:.76rem; color:var(--ink-faint);
  text-transform:uppercase; letter-spacing:.04em; min-width:3.4rem;
}
.gc-sesion-tipo {
  font-family:'Archivo',sans-serif; font-weight:700; font-size:1rem;
  letter-spacing:-.01em; color:var(--ink);
}
.gc-sesion-datos {
  font-family:'IBM Plex Mono',monospace; font-size:.8rem; color:var(--ink-soft);
}
.gc-sesion-carga {
  margin-left:auto; font-family:'IBM Plex Mono',monospace; font-size:.76rem;
  color:var(--ink-faint); white-space:nowrap;
}
.gc-sesion-cinta { margin-bottom:.1rem; }

/* El desplegable se pega debajo de la fila, como una sola pieza */
[class*="st-key-sesion_"] [data-testid="stExpander"] {
  border-radius:0 0 3px 3px !important; border-top:1px solid var(--rule) !important;
  margin-top:0 !important;
}
[class*="st-key-sesion_"] { margin-top:-1rem; }

/* --- Pestañas internas ---
   Antes la pestaña activa era un bloque azul oscuro con `color:#fff`, pero
   Streamlit envuelve el texto en un <p> con su propio color, así que la letra
   quedaba oscura sobre fondo oscuro: ilegible. Además de arreglar el color en
   todos los hijos, se cambió a un diseño más liviano - subrayado en vez de
   relleno - que evita el problema de contraste de raíz. */
[data-testid="stExpanderDetails"] .stTabs [data-baseweb="tab-list"] {
  gap:1.4rem; border-bottom:1px solid var(--rule); margin-bottom:.9rem;
}
[data-testid="stExpanderDetails"] .stTabs [data-baseweb="tab"] {
  background:transparent !important; border-radius:0;
  font-size:.84rem !important; padding:.15rem 0 .5rem 0 !important;
  text-transform:none !important; letter-spacing:0 !important;
  border-bottom:2px solid transparent;
}
[data-testid="stExpanderDetails"] .stTabs [data-baseweb="tab"],
[data-testid="stExpanderDetails"] .stTabs [data-baseweb="tab"] * {
  color:var(--ink-faint) !important; font-weight:500 !important;
}
[data-testid="stExpanderDetails"] .stTabs [data-baseweb="tab"]:hover,
[data-testid="stExpanderDetails"] .stTabs [data-baseweb="tab"]:hover * {
  color:var(--ink) !important;
}
[data-testid="stExpanderDetails"] .stTabs [aria-selected="true"] {
  border-bottom:2px solid var(--accent) !important;
}
[data-testid="stExpanderDetails"] .stTabs [aria-selected="true"],
[data-testid="stExpanderDetails"] .stTabs [aria-selected="true"] * {
  color:var(--accent) !important; font-weight:600 !important;
}
/* La barra que Streamlit dibuja abajo, que duplicaría el subrayado */
[data-testid="stExpanderDetails"] .stTabs [data-baseweb="tab-highlight"] { display:none; }

/* --- Botón principal: blanco sobre azul, forzado en todos los hijos --- */
.stButton button[kind="primary"] {
  background:var(--accent) !important; border-color:var(--accent) !important;
}
.stButton button[kind="primary"], .stButton button[kind="primary"] * {
  color:#FFFFFF !important; font-weight:600 !important;
}
.stButton button[kind="primary"]:hover {
  background:#223C63 !important; border-color:#223C63 !important;
}
.stButton button[kind="primary"]:hover * { color:#FFFFFF !important; }

/* Sesiones de la lista: pista a la derecha de que hay algo adentro */
[class*="st-key-sesion_"] { margin-bottom:.45rem; }
[class*="st-key-sesion_"] [data-testid="stExpander"] summary::after {
  content:"abrir"; float:right;
  font-family:'Archivo',sans-serif; font-size:.64rem; font-weight:600;
  letter-spacing:.11em; text-transform:uppercase; color:var(--ink-faint);
  padding-top:.22rem;
}
[class*="st-key-sesion_"] [data-testid="stExpander"]:hover summary::after { color:var(--accent); }

/* Sesión destacada: es la acción principal al volver de entrenar */
[class*="st-key-analisis_destacado"] [data-testid="stExpander"] {
  border:1px solid var(--accent) !important;
  background:linear-gradient(0deg,#F3F7FC,#F8FBFE);
}
[class*="st-key-analisis_destacado"] [data-testid="stExpander"] summary {
  color:var(--accent) !important; font-size:1rem !important; padding:.9rem 1.1rem !important;
}
[class*="st-key-analisis_destacado"] [data-testid="stExpander"]:hover { background:#EDF3FA; }
.stTabs [data-baseweb="tab-list"] { gap:1.6rem; border-bottom:1px solid var(--rule); }
.stTabs [data-baseweb="tab"] {
  font-family:'Archivo',sans-serif; font-size:.78rem; font-weight:600;
  letter-spacing:.05em; text-transform:uppercase; padding:0 0 .55rem 0;
}
.stButton button {
  font-family:'IBM Plex Sans',sans-serif; font-weight:500; border-radius:2px;
  border:1px solid var(--rule-strong); font-size:.84rem;
}
.stButton button:hover { border-color:var(--accent); color:var(--accent); }
[data-testid="stDataFrame"] { border:1px solid var(--rule); border-radius:3px; }
.gc-caption { color:var(--ink-soft); font-size:.83rem; line-height:1.55; }
.gc-banner {
  display:flex; align-items:center; gap:.9rem; flex-wrap:wrap;
  background:#FFF8E8; border:1px solid #E8D9AE; border-left:3px solid var(--z-media);
  border-radius:3px; padding:.85rem 1.1rem; margin-bottom:1.6rem;
  font-size:.87rem; color:#6B5518;
}
.gc-banner b { color:#4A3A0F; }
.gc-note {
  border-left:2px solid var(--rule-strong); padding:.15rem 0 .15rem .85rem;
  color:var(--ink-soft); font-size:.82rem;
}

/* --- Pantalla chica (celular) ---
   La app se usa bastante desde el teléfono, así que en pantallas angostas se
   apilan las tarjetas, se reducen los títulos y se achican los márgenes para
   aprovechar el ancho. */
@media (max-width:760px){
  .block-container { padding-left:.9rem; padding-right:.9rem; padding-top:1.2rem; }
  .gc-stats { flex-direction:column; }
  .gc-stat { border-right:none; border-bottom:1px solid var(--rule); }
  .gc-stat:last-child { border-bottom:none; }
  .gc-stat-v { font-size:1.6rem; }
  .gc-hero { padding:1.1rem 1.1rem 1rem; }
  .gc-hero-tipo { font-size:1.3rem; }
  .gc-hero-datos { font-size:.8rem; gap:.7rem; }
  .gc-eyebrow { font-size:.74rem; margin:2.1rem 0 .8rem 0; letter-spacing:.09em; }
  .gc-sesion-top { gap:.5rem; }
  .gc-sesion-tipo { font-size:.92rem; }
  .gc-sesion-datos { font-size:.74rem; }
  .gc-sesion-carga { margin-left:0; }
  .gc-ribbon-legend { gap:.8rem; font-size:.68rem; flex-wrap:wrap; }
  h1 { font-size:1.45rem; }
  [data-testid="stExpander"] summary { font-size:.87rem !important; padding:.65rem .8rem !important; }
}
</style>
""", unsafe_allow_html=True)


def cinta_umbrales(dist, chica=False, con_marcas=True, con_leyenda=False):
    """
    Dibuja la 'cinta de umbrales': una barra proporcional al tiempo pasado por
    debajo de VT1, entre VT1 y VT2, y por encima de VT2.

    Es el elemento visual que se repite en toda la app - siempre con el mismo
    significado y los mismos colores, a tres escalas distintas (sesión destacada,
    fila de sesión, y resumen de 4 semanas).
    """
    if not dist:
        return ""
    p = dist["pct"]
    clase = "gc-ribbon sm" if chica else "gc-ribbon"

    html = (
        f'<div class="{clase}">'
        f'<i class="b" style="width:{p["baja"]}%"></i>'
        f'<i class="m" style="width:{p["media"]}%"></i>'
        f'<i class="a" style="width:{p["alta"]}%"></i>'
        f"</div>"
    )

    # Las marcas se ubican justo en el borde entre segmentos: ahí está el umbral
    if con_marcas and dist.get("vt1"):
        x1 = p["baja"]
        x2 = p["baja"] + p["media"]
        html += (
            '<div class="gc-ribbon-marks">'
            f'<span style="left:{x1}%">VT1 · {dist["vt1"]}</span>'
            f'<span style="left:{x2}%">VT2 · {dist["vt2"]}</span>'
            "</div>"
        )

    if con_leyenda:
        html += (
            '<div class="gc-ribbon-legend">'
            f'<span><i class="gc-dot" style="background:var(--z-baja)"></i>'
            f'<em>{p["baja"]}%</em> aeróbico</span>'
            f'<span><i class="gc-dot" style="background:var(--z-media)"></i>'
            f'<em>{p["media"]}%</em> intermedio</span>'
            f'<span><i class="gc-dot" style="background:var(--z-alta)"></i>'
            f'<em>{p["alta"]}%</em> intenso</span>'
            "</div>"
        )
    return html


def eyebrow(texto):
    st.markdown(f'<div class="gc-eyebrow">{texto}</div>', unsafe_allow_html=True)


# Plantilla común para que todos los gráficos hereden la tipografía y la paleta
LAYOUT_GRAFICO = dict(
    plot_bgcolor="#FFFFFF",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#131A22", family="IBM Plex Sans", size=12),
    margin=dict(l=8, r=8, t=8, b=8),
    xaxis=dict(gridcolor="#E4EAF0", linecolor="#CBD5DF", zerolinecolor="#E4EAF0"),
    yaxis=dict(gridcolor="#E4EAF0", linecolor="#CBD5DF", zerolinecolor="#E4EAF0"),
)

C_BAJA, C_MEDIA, C_ALTA, C_ACENTO = "#2F9B80", "#DFA015", "#CB4433", "#2D4A7C"


@st.cache_resource(show_spinner="Conectando con Garmin Connect...")
def obtener_cliente_garmin(email, password, recordar):
    return garmin_client.conectar(email, password, recordar)


@st.cache_resource(show_spinner="Recuperando tu sesión de Garmin...")
def obtener_cliente_con_sesion():
    return garmin_client.conectar_con_sesion_guardada()


def parse_fecha(s):
    return datetime.strptime(s.split(" ")[0], "%Y-%m-%d").date()


def html(markup):
    """
    Colapsa los saltos de línea y la indentación de un bloque HTML antes de
    mandarlo a pantalla.

    Hace falta porque Streamlit pasa el texto por Markdown antes de renderizar el
    HTML, y Markdown convierte en bloque de código cualquier línea que arranque
    con 4 espacios o más. Sin esto, un HTML escrito en varias líneas indentadas
    (que es lo natural al programar) aparece como texto crudo en la pantalla.
    """
    return re.sub(r"\s*\n\s*", " ", markup).strip()


def escribir_html(markup):
    """Muestra un bloque HTML ya normalizado."""
    st.markdown(html(markup), unsafe_allow_html=True)


def panel_analisis_sesion(s, sesiones, perfil, historial_pmc, modo_demo):
    """
    Dibuja el análisis completo de una sesión: la lectura del entrenador y las
    herramientas (deriva cardíaca, VAM y RPE).

    Está en una función porque la usan dos lugares - la sesión destacada de
    arriba y cada sesión de la lista de abajo - y tienen que ofrecer exactamente
    lo mismo. Cuando estaban duplicados, la sesión destacada se quedó sin las
    herramientas.
    """
    tab_coach, tab_datos = st.tabs(["Análisis del entrenador", "Datos y herramientas"])

    with tab_coach:
        st.markdown(coach.analisis_profundo(s, perfil, sesiones, historial_pmc))

    with tab_datos:
        escribir_html(
            '<p class="gc-caption">Los datos crudos de la sesión. La lectura de qué tipo de '
            "entrenamiento fue y qué mejoraste está en la pestaña de al lado.</p>"
        )
        st.write(feedback.feedback_sesion(s))

        if s.get("deporte") == "running":
            _din = feedback.feedback_dinamicas_carrera(s)
            if _din:
                st.markdown(_din)

            _ru = metrics.ritmo_umbral_estimado(sesiones)
            _rtss = metrics.calcular_rtss(s, _ru)
            _txt_carga = feedback.feedback_carga_running(_rtss, s, _ru)
            if _txt_carga:
                st.markdown(_txt_carga)

            _pot = metrics.potencia_running(s, perfil)
            _txt_pot = feedback.feedback_potencia_running(_pot)
            if _txt_pot:
                st.markdown(_txt_pot)

        def traer_detalle():
            """Trae el detalle segundo a segundo, del ejemplo o de Garmin."""
            if modo_demo:
                return demo_data.generar_serie_demo(s)
            client = st.session_state.get("client")
            if client is None:
                st.error("Primero cargá tus entrenamientos desde el panel de la izquierda.")
                return None
            try:
                return metrics.extraer_series(garmin_client.obtener_detalle_actividad(client, s["id"]))
            except Exception as e:
                st.error(f"No pude traer el detalle de esta sesión: {e}")
                return None

        # --- Deriva cardíaca ---
        st.markdown("**Deriva cardíaca**")
        _largas = "tiradas largas" if s.get("deporte") == "running" else "salidas largas"
        escribir_html(
            '<p class="gc-caption">Compara la primera y la segunda mitad de la sesión. '
            f"Tiene más sentido en {_largas} y estables que en series cortas.</p>"
        )
        key_deriva = f"deriva_{s['id']}"
        if st.button("Analizar deriva cardíaca", key=f"btn_der_{s['id']}"):
            with st.spinner("Analizando..."):
                serie = traer_detalle()
                st.session_state[key_deriva] = (
                    metrics.calcular_deriva_cardiaca_desde_series(serie) if serie else None
                )
        if key_deriva in st.session_state:
            st.info(feedback.feedback_deriva_cardiaca(st.session_state[key_deriva], s))

        # --- VAM ---
        # El botón se muestra siempre, aunque la salida parezca llana. Antes se
        # ocultaba cuando el desnivel era bajo, y eso confundía: desaparecía sin
        # explicar por qué. Además el desnivel promedio no dice si hubo una
        # subida sostenida — una salida "llana" puede tener un repecho de 10
        # minutos, y el análisis lo encuentra igual.
        if True:
            st.markdown("**Velocidad de ascensión (VAM)**")
            _dkm = s.get("elevacion_por_km")
            if _dkm is None:
                _aviso = "Esta sesión no trae datos de desnivel."
            elif _dkm > 15:
                _aviso = f"Recorrido montañoso ({_dkm:.0f} m/km): acá el VAM dice mucho."
            elif _dkm > 8:
                _aviso = f"Recorrido ondulado ({_dkm:.0f} m/km): puede haber alguna subida que valga la pena mirar."
            else:
                _aviso = (
                    f"Recorrido mayormente llano ({_dkm:.0f} m/km). Igual podés calcularlo: si hubo "
                    "algún repecho sostenido de al menos 5 minutos, lo va a encontrar."
                )
            escribir_html(f'<p class="gc-caption">{_aviso}</p>')

            key_vam = f"vam_{s['id']}"
            if st.button("Calcular VAM real de la subida", key=f"btn_vam_{s['id']}"):
                with st.spinner("Analizando..."):
                    serie = traer_detalle()
                    st.session_state[key_vam] = (
                        metrics.calcular_mejor_vam(
                            serie["altitud"], serie.get("distancia"),
                            serie.get("tiempo"), s["duracion_min"] * 60,
                        ) if serie else None
                    )
            if key_vam in st.session_state:
                st.info(feedback.feedback_vam(st.session_state[key_vam], perfil, s))

        # --- RPE (lo cargás vos) ---
        st.markdown("**Cómo la sentiste**")
        escribir_html('<p class="gc-caption">Del 1 (muy suave) al 10 (al máximo).</p>')
        rpe_guardado = rpe_store.obtener(s["id"])
        c_rpe1, c_rpe2 = st.columns([4, 1])
        with c_rpe1:
            rpe_valor = st.slider(
                "Esfuerzo percibido", 1, 10, rpe_guardado or 5,
                key=f"rpe_{s['id']}", label_visibility="collapsed",
            )
        with c_rpe2:
            if st.button("Guardar", key=f"rpe_btn_{s['id']}"):
                rpe_store.guardar(s["id"], rpe_valor)
                rpe_guardado = rpe_valor
        if rpe_guardado:
            st.caption(feedback.feedback_rpe(rpe_guardado, s, perfil))


def tarjeta_estado(clave, valor, descripcion, marcador_pct=None):
    """Tarjeta de una métrica de estado (Fitness / Fatiga / Forma)."""
    escala = ""
    if marcador_pct is not None:
        escala = f'<div class="gc-stat-scale"><i style="left:{marcador_pct:.1f}%"></i></div>'
    return html(f"""<div class="gc-stat">
      <div class="gc-stat-k">{clave}</div>
      <div class="gc-stat-v">{valor}</div>
      {escala}
      <div class="gc-stat-d">{descripcion}</div>
    </div>""")


# ---------------- Barra superior ----------------
st.markdown(
    '<div class="gc-topbar">'
    '<div class="gc-wordmark">MI COACH <span>/</span> CICLISMO</div>'
    "</div>",
    unsafe_allow_html=True,
)

# ---------------- Sidebar: perfil ----------------
# ---------------------------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------------------------
# Ordenada por frecuencia de uso, no por categoría: arriba y siempre a la vista
# lo que tocás cada vez que entrenás (de dónde traer los datos y el botón de
# cargar); abajo y plegado lo que se configura una vez y no se toca más.
# ---------------------------------------------------------------------------
perfil = perfil_store.perfil_efectivo()

with st.sidebar:
    # ---------- 1. Traer entrenamientos (lo de todos los días) ----------
    st.markdown(
        '<div style="font-family:Archivo,sans-serif;font-weight:700;font-size:.72rem;'
        'letter-spacing:.14em;color:#5A6672;padding:.1rem 0 .6rem 0">ENTRENAMIENTOS</div>',
        unsafe_allow_html=True,
    )

    fuente = st.radio(
        "De dónde traigo los entrenamientos",
        ["Mi cuenta de Garmin", "Archivos de mi reloj", "Datos de ejemplo"],
        index=2,
        label_visibility="collapsed",
    )
    modo_demo = fuente == "Datos de ejemplo"
    modo_archivos = fuente == "Archivos de mi reloj"

    email = password = None
    recordar = False
    usar_sesion = False
    archivos_subidos = None
    deporte_archivos = "Ciclismo"

    if modo_archivos:
        st.caption(
            "Sirve para cualquier marca: Wahoo, Coros, Polar, Suunto, Apple Watch, Strava. "
            "Exportá tus entrenamientos como **FIT**, **TCX** o **GPX** y subilos acá."
        )
        deporte_archivos = st.selectbox("Qué son estas actividades", ["Ciclismo", "Running"])
        archivos_subidos = st.file_uploader(
            "Archivos de actividad", type=["fit", "tcx", "gpx"],
            accept_multiple_files=True, label_visibility="collapsed",
        )
        with st.expander("Cómo exporto mis archivos"):
            st.markdown(
                "- **Wahoo:** app ELEMNT → la actividad → compartir → exportar FIT\n"
                "- **Coros:** web (`trainingcn.coros.com`) → la actividad → descargar FIT o GPX\n"
                "- **Apple Watch:** no exporta solo. Usá una app como *HealthFit* o *RunGap*, "
                "o sincronizá con Strava y bajá el GPX de ahí\n"
                "- **Polar / Suunto:** Polar Flow y Suunto App exportan TCX o GPX\n"
                "- **Strava:** en la actividad → los tres puntos → exportar GPX o TCX original"
            )
    elif modo_demo:
        st.caption("Entrenamientos inventados, para probar la app sin conectar nada.")
    else:
        if garmin_client.hay_sesion_guardada():
            usar_sesion = True
            st.success("Sesión guardada: no hace falta la contraseña.")
            if st.button("Olvidar esta sesión", key="btn_olvidar_sesion"):
                garmin_client.olvidar_sesion()
                st.session_state.pop("client", None)
                st.rerun()
        else:
            email = st.text_input("Email de Garmin Connect", value=perfil.get("garmin_email", ""))
            password = st.text_input("Contraseña", type="password")
            recordar = st.checkbox("Recordar mi acceso en esta computadora", value=True)
            if recordar:
                st.caption(
                    "No se guarda tu contraseña, sino los tokens de sesión que devuelve Garmin "
                    "(lo mismo que hace la app de Garmin en el celular). Quedan en tu carpeta de "
                    "usuario, fuera del proyecto, así no viajan si compartís la carpeta."
                )
            else:
                st.caption("La contraseña se usa solo para entrar y no queda guardada en ningún lado.")

    dias_historial = st.slider("Días de historial", 30, 180, 90, step=10)
    cargar = st.button("Cargar entrenamientos", type="primary", width="stretch", key="btn_cargar")

    st.divider()

    # ---------- 2. Ajustes que se cargan una vez ----------
    st.markdown(
        '<div style="font-family:Archivo,sans-serif;font-weight:700;font-size:.72rem;'
        'letter-spacing:.14em;color:#5A6672;padding:.1rem 0 .5rem 0">MIS DATOS</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Edad, peso y pulso"):
        perfil["edad"] = st.number_input("Edad", value=int(perfil["edad"]), min_value=10, max_value=100)
        perfil["peso_kg"] = st.number_input("Peso (kg)", value=float(perfil["peso_kg"]))
        perfil["fc_reposo"] = st.number_input("Pulso en reposo (bpm)", value=int(perfil["fc_reposo"]))
        st.caption("Medilo apenas te despertás, sin levantarte, promediando 3-4 días.")
        fc_max_input = st.number_input(
            "Pulso máximo (bpm) — 0 si no lo sabés", value=int(perfil.get("fc_max") or 0)
        )
        perfil["fc_max"] = fc_max_input if fc_max_input > 0 else None
        fc_max_usada = metrics.calcular_fc_max(perfil)
        origen = "el que cargaste" if perfil["fc_max"] else "estimado por fórmula según tu edad"
        st.caption(f"Se usa **{fc_max_usada} bpm** ({origen}).")

    with st.expander("Potenciómetro"):
        ftp_input = st.number_input(
            "Tu FTP en vatios — 0 si no usás potenciómetro", value=int(perfil.get("ftp_watts") or 0)
        )
        perfil["ftp_watts"] = ftp_input if ftp_input > 0 else None
        if perfil["ftp_watts"]:
            st.caption(
                f"{perfil['ftp_watts']} W ÷ {perfil['peso_kg']:.0f} kg = "
                f"**{perfil['ftp_watts'] / perfil['peso_kg']:.2f} W/kg**"
            )
        else:
            st.caption("Sin FTP no se pueden calcular el TSS ni el Intensity Factor.")

    # ---------- 3. Prueba de esfuerzo ----------
    test_guardado = perfil.get("test_fisiologico") or {}
    etiqueta_test = (
        f"Prueba de esfuerzo · cargada ({test_guardado.get('fecha', 'sin fecha')})"
        if test_guardado
        else "Prueba de esfuerzo · sin cargar"
    )

    with st.expander(etiqueta_test):
        if not test_guardado:
            st.caption(
                "¿Te hiciste una ergoespirometría? Cargando tus umbrales reales (VT1 y VT2), "
                "el análisis de cada sesión deja de usar fórmulas y pasa a usar tu fisiología."
            )

    with st.expander("✏️ Cargar / editar mi estudio"):
        st.caption(
            "Buscá estos valores en el informe de tu estudio. Los únicos imprescindibles son "
            "la FC de VT1 y la de VT2 (umbral aeróbico y anaeróbico)."
        )
        with st.form("form_ergo"):
            f_fecha = st.text_input("Fecha del estudio", value=test_guardado.get("fecha", ""), placeholder="31/07/2025")

            st.markdown("**Umbral aeróbico (VT1)**")
            c1, c2 = st.columns(2)
            f_vt1_fc = c1.number_input("FC en VT1 (bpm)", value=int(test_guardado.get("vt1_fc") or 0), key="vt1fc")
            f_vt1_w = c2.number_input("Watts en VT1", value=int(test_guardado.get("vt1_watts") or 0), key="vt1w")

            st.markdown("**Umbral anaeróbico (VT2)**")
            c3, c4 = st.columns(2)
            f_vt2_fc = c3.number_input("FC en VT2 (bpm)", value=int(test_guardado.get("vt2_fc") or 0), key="vt2fc")
            f_vt2_w = c4.number_input("Watts en VT2", value=int(test_guardado.get("vt2_watts") or 0), key="vt2w")

            st.markdown("**Máximos**")
            c5, c6 = st.columns(2)
            f_fcmax = c5.number_input("FC máxima alcanzada", value=int(test_guardado.get("fc_max_medida") or 0), key="fcmaxlab")
            f_pot_pico = c6.number_input("Potencia pico (W)", value=int(test_guardado.get("potencia_pico") or 0), key="potpico")

            f_vo2 = st.number_input(
                "VO2max (ml/kg/min)", value=float(test_guardado.get("vo2max_ml_kg_min") or 0.0), step=0.1, key="vo2",
            )

            st.divider()
            f_zonas_manual = st.checkbox(
                "Cargar la tabla de 5 zonas exacta del informe",
                value=bool(test_guardado.get("zonas_manuales")),
                help="Si no la tildás, la app deriva las zonas automáticamente de tus umbrales VT1/VT2. "
                     "La derivación suele quedar muy cerca de la tabla del laboratorio.",
            )

            zonas_form = {}
            if f_zonas_manual:
                zonas_prev = perfil.get("zonas_lab") or {}
                for z in range(1, 6):
                    prev = zonas_prev.get(str(z)) or zonas_prev.get(z) or {}
                    fc_prev = prev.get("fc") or (0, 0)
                    st.markdown(f"**Zona {z}**")
                    cz1, cz2 = st.columns(2)
                    desde = cz1.number_input(f"FC desde (Z{z})", value=int(fc_prev[0]), key=f"z{z}d")
                    hasta = cz2.number_input(f"FC hasta (Z{z})", value=int(fc_prev[1]), key=f"z{z}h")
                    zonas_form[z] = (desde, hasta)

            guardar_ergo = st.form_submit_button("💾 Guardar mi estudio")

        if guardar_ergo:
            if not f_vt1_fc or not f_vt2_fc:
                st.error("Necesito al menos la FC de VT1 y la de VT2 para poder usar el estudio.")
            elif f_vt1_fc >= f_vt2_fc:
                st.error("La FC de VT1 tiene que ser menor que la de VT2. Revisá los valores.")
            else:
                fcmax_para_zonas = f_fcmax or perfil.get("fc_max") or metrics.calcular_fc_max(perfil)

                nuevo_test = {
                    "fecha": f_fecha or "sin fecha",
                    "vt1_fc": f_vt1_fc,
                    "vt2_fc": f_vt2_fc,
                    "vt1_watts": f_vt1_w or None,
                    "vt2_watts": f_vt2_w or None,
                    "fc_max_medida": f_fcmax or None,
                    "potencia_pico": f_pot_pico or None,
                    "vo2max_ml_kg_min": f_vo2 or None,
                    "zonas_manuales": bool(f_zonas_manual),
                }

                if f_zonas_manual and all(v[1] > v[0] for v in zonas_form.values()):
                    nuevas_zonas = {
                        str(z): {"nombre": metrics.NOMBRE_ZONA[z], "fc": list(rango), "watts": None}
                        for z, rango in zonas_form.items()
                    }
                else:
                    derivadas = config.derivar_zonas_desde_umbrales(f_vt1_fc, f_vt2_fc, fcmax_para_zonas)
                    nuevas_zonas = {
                        str(z): {"nombre": d["nombre"], "fc": list(d["fc"]), "watts": None}
                        for z, d in derivadas.items()
                    }

                perfil_a_guardar = dict(perfil)
                perfil_a_guardar["test_fisiologico"] = nuevo_test
                perfil_a_guardar["zonas_lab"] = nuevas_zonas
                perfil_a_guardar["usar_zonas_fc_lab"] = True
                if f_fcmax:
                    perfil_a_guardar["fc_max"] = f_fcmax
                if f_vt2_w and not perfil_a_guardar.get("ftp_watts"):
                    perfil_a_guardar["ftp_watts"] = f_vt2_w

                perfil_store.guardar(perfil_a_guardar)
                st.success("Estudio guardado. Recargando...")
                st.rerun()



        if test_guardado:
            perfil["usar_zonas_fc_lab"] = st.checkbox(
                "Usar las zonas de mi prueba de esfuerzo",
                value=perfil.get("usar_zonas_fc_lab", True),
            )
            vt1_w = test_guardado.get("vt1_watts")
            vt2_w = test_guardado.get("vt2_watts")
            st.markdown(f"**VT1** (umbral aeróbico): {test_guardado['vt1_fc']} bpm" + (f" · {vt1_w} W" if vt1_w else ""))
            st.markdown(f"**VT2** (umbral anaeróbico): {test_guardado['vt2_fc']} bpm" + (f" · {vt2_w} W" if vt2_w else ""))
            if test_guardado.get("fc_max_medida"):
                st.markdown(f"**Pulso máximo medido:** {test_guardado['fc_max_medida']} bpm")
            if test_guardado.get("vo2max_ml_kg_min"):
                st.markdown(f"**VO2max:** {test_guardado['vo2max_ml_kg_min']} ml/kg/min")
            if test_guardado.get("potencia_pico"):
                st.markdown(f"**Potencia pico:** {test_guardado['potencia_pico']} W")
            if not test_guardado.get("zonas_manuales"):
                st.caption("Las zonas se derivaron automáticamente de tus umbrales.")
        else:
            perfil["usar_zonas_fc_lab"] = False

    # ---------- 4. Zonas (solo lectura) ----------
    with st.expander("Mis zonas de entrenamiento"):
        st.caption(
            "Según tu prueba de esfuerzo:" if perfil.get("usar_zonas_fc_lab")
            else "Calculadas por fórmula. Cargá tu prueba de esfuerzo para afinarlas."
        )
        for z, (lo, hi) in metrics.calcular_zonas_fc(perfil).items():
            escribir_html(
                f'<div style="font-size:.82rem;margin:.2rem 0">'
                f'<i class="gc-dot" style="background:{config.ZONA_COLOR[z]}"></i>'
                f'{metrics.NOMBRE_ZONA[z]} '
                f'<b style="font-family:\'IBM Plex Mono\',monospace">{lo}-{hi}</b></div>'
            )
        if perfil.get("ftp_watts"):
            st.markdown("**Zonas de potencia**")
            for z, (lo, hi) in metrics.calcular_zonas_potencia(perfil["ftp_watts"]).items():
                escribir_html(
                    f'<div style="font-size:.8rem;margin:.15rem 0;color:#5A6672">'
                    f'{metrics.NOMBRE_ZONA_POTENCIA[z]} '
                    f'<b style="font-family:\'IBM Plex Mono\',monospace;color:#131A22">{lo}-{hi} W</b></div>'
                )

    # ---------- 5. Guardar ----------
    st.divider()
    if st.button("Guardar mis datos", width="stretch", key="btn_guardar_perfil"):
        perfil_store.guardar(perfil)
        st.success("Guardado")

    with st.expander("Dónde se guardan mis datos"):
        st.caption(
            "Todo queda en esta computadora, en tu carpeta de usuario — nunca dentro del "
            "programa. Por eso, si le pasás la app a alguien, esa persona arranca en cero "
            "y no ve nada tuyo."
        )
        st.code(
            f"Perfil y RPE:\n{os.path.abspath(config.RUTA_DATOS)}\n\n"
            f"Sesión de Garmin:\n{garmin_client.RUTA_SESION}",
            language=None,
        )
        st.caption(
            "Para dejarla como la va a ver un amigo (útil para probar antes de compartirla):"
        )
        if st.button("Borrar todos mis datos", width="stretch", key="btn_borrar_todo"):
            perfil_store.borrar()
            rpe_store.borrar()
            garmin_client.olvidar_sesion()
            st.session_state.clear()
            st.warning("Listo: borré tu perfil, tus RPE y tu sesión de Garmin. Recargá la página.")

    # ---------- Actualizaciones ----------
    st.divider()
    st.markdown(
        '<div style="font-family:Archivo,sans-serif;font-weight:700;font-size:.72rem;'
        'letter-spacing:.14em;color:#5A6672;padding:.1rem 0 .5rem 0">ACTUALIZACIONES</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"Versión instalada: **{version.VERSION}**")

    if not version.URL_VERSION:
        with st.expander("Activar las actualizaciones"):
            st.markdown(
                "Todavía no está configurado desde dónde buscar versiones nuevas. Para activarlo, "
                "quien mantiene la app tiene que publicar el proyecto y poner esa dirección en "
                "`version.py` — está explicado en el README."
            )
    else:
        if st.button("Buscar actualizaciones", width="stretch", key="btn_buscar_upd"):
            st.session_state["upd"] = actualizador.consultar()

        info = st.session_state.get("upd")
        if info:
            estado = info["estado"]
            if estado == "al_dia":
                st.success("Ya tenés la última versión.")
            elif estado == "error":
                st.warning("No pude consultar. Revisá tu conexión.")
            elif estado == "nueva":
                st.info(f"Hay una versión nueva: **{info['version_remota']}**")
                if info.get("notas"):
                    st.caption(info["notas"])
                if info.get("requiere_librerias"):
                    st.caption(
                        "Necesita librerías nuevas, pero `iniciar_app.bat` las instala solo al abrir: "
                        "alcanza con reiniciar."
                    )
                if actualizador.corriendo_como_exe():
                    st.caption(
                        "Estás usando la app instalada, que no puede actualizarse sola. Pedile el "
                        "instalador nuevo a quien te compartió la app."
                    )
                elif st.button("Actualizar ahora", type="primary", width="stretch", key="btn_aplicar_upd"):
                    with st.spinner("Descargando y reemplazando archivos..."):
                        r = actualizador.aplicar(info["zip"])
                    if r["ok"]:
                        st.success(r["mensaje"])
                        st.session_state["upd"] = None
                    else:
                        st.error(r["mensaje"])


if cargar or "actividades_raw" not in st.session_state:
    if modo_demo:
        st.session_state["actividades_raw"] = demo_data.generar_actividades_demo(dias_historial)
        st.session_state["client"] = None
        st.session_state["fuente_cargada"] = "demo"
    elif modo_archivos:
        if not archivos_subidos:
            st.info(
                "Subí uno o más archivos de actividad (**FIT**, **TCX** o **GPX**) en el panel de "
                "la izquierda y tocá **Cargar entrenamientos**."
            )
            st.stop()
        zonas_actuales = metrics.calcular_zonas_fc(
            metrics.perfil_para_running(perfil) if deporte_archivos == "Running" else perfil
        )
        importadas, fallidos = [], []
        for archivo in archivos_subidos:
            try:
                muestras, _ = importar_actividad.leer_archivo(archivo.name, archivo.getvalue())
                if not muestras:
                    fallidos.append(f"{archivo.name}: no tiene datos de recorrido")
                    continue
                act = importar_actividad.a_actividad(muestras, archivo.name, perfil, zonas_actuales)
                act["activityType"] = {
                    "typeKey": "running" if deporte_archivos == "Running" else "cycling"
                }
                importadas.append(act)
            except Exception as e:
                fallidos.append(f"{archivo.name}: {e}")
        if fallidos:
            st.warning("No pude leer estos archivos:\n\n" + "\n\n".join(f"- {x}" for x in fallidos))
        if not importadas:
            st.error("Ninguno de los archivos se pudo leer. Revisá que sean FIT, TCX o GPX de actividades.")
            st.stop()
        st.session_state["actividades_raw"] = importadas
        st.session_state["client"] = None
        st.session_state["fuente_cargada"] = "archivos"
    else:
        if not usar_sesion and (not email or not password):
            st.info(
                "Completá tu email y contraseña de Garmin en el panel de la izquierda "
                "y tocá **Cargar entrenamientos**."
            )
            st.stop()
        try:
            if usar_sesion:
                client = obtener_cliente_con_sesion()
            else:
                client = obtener_cliente_garmin(email, password, recordar)
                if recordar:
                    perfil_a_guardar = dict(perfil)
                    perfil_a_guardar["garmin_email"] = email
                    perfil_store.guardar(perfil_a_guardar)
            st.session_state["client"] = client
            st.session_state["actividades_raw"] = garmin_client.obtener_actividades(client, cantidad=200)
            st.session_state["fuente_cargada"] = "garmin"
        except Exception as e:
            if usar_sesion:
                # La sesión guardada venció o dejó de servir: la borramos para que
                # la próxima vez vuelva a pedir email y contraseña en vez de fallar en loop.
                garmin_client.olvidar_sesion()
                st.error(
                    f"La sesión guardada ya no sirve ({e}). La borré: recargá la página y "
                    "volvé a poner tu email y contraseña."
                )
            else:
                st.error(
                    f"No pude entrar a Garmin: {e}\n\n"
                    "Revisá el email y la contraseña. Si tenés verificación en dos pasos activada "
                    "en tu cuenta de Garmin, ese es el motivo más probable: avisame y adapto el "
                    "inicio de sesión para que la soporte."
                )
            st.stop()

actividades_raw = st.session_state.get("actividades_raw", [])

def _tipo(a):
    return a.get("activityType", {}).get("typeKey")

bici_raw = [a for a in actividades_raw if _tipo(a) in metrics.TIPOS_BICI]
run_raw = [a for a in actividades_raw if _tipo(a) in metrics.TIPOS_RUNNING]
gym_raw = [a for a in actividades_raw if _tipo(a) in metrics.TIPOS_GYM]

if not bici_raw and not run_raw:
    st.warning(
        "No encontré actividades de ciclismo ni de running en el rango elegido. "
        "Probá ampliar los días de historial."
    )
    st.stop()

# ---------------- Elegir deporte ----------------
# Ciclismo y running se analizan por separado a propósito: mezclarlos daría una
# carga acumulada sin sentido (el impacto de correr no se compara con pedalear)
# y, sobre todo, los umbrales de pulso son distintos en cada deporte.
disponibles = []
if bici_raw:
    disponibles.append(f"Ciclismo ({len(bici_raw)})")
if run_raw:
    disponibles.append(f"Running ({len(run_raw)})")

if len(disponibles) > 1:
    eleccion = st.radio("Deporte", disponibles, horizontal=True, label_visibility="collapsed")
    deporte = "running" if eleccion.startswith("Running") else "bici"
else:
    deporte = "bici" if bici_raw else "running"

if deporte == "running":
    perfil = metrics.perfil_para_running(perfil)
    actividades_deporte = run_raw
else:
    actividades_deporte = bici_raw

# ---------------- Procesar sesiones ----------------
sesiones = [metrics.procesar_actividad(a, perfil) for a in actividades_deporte]
sesiones.sort(key=lambda s: s["fecha"])

trimp_por_dia = {}
for s in sesiones:
    f = parse_fecha(s["fecha"])
    trimp_por_dia[f] = trimp_por_dia.get(f, 0) + s["trimp"]

fecha_min = min(trimp_por_dia.keys())
historial_diario = []
f = fecha_min
while f <= date.today():
    historial_diario.append({"fecha": f, "trimp": trimp_por_dia.get(f, 0.0)})
    f += timedelta(days=1)

historial_pmc = metrics.calcular_ctl_atl_tsb(historial_diario)
ultimo = historial_pmc[-1]

# ---------------- Hero: la última sesión ----------------
# Al volver de entrenar, lo primero que querés ver es qué fue lo que acabás de
# hacer. Por eso el hero es la última sesión y no una fila de indicadores.
ultima = sesiones[-1]
tipo_ultima = coach.clasificar_sesion(ultima, perfil)
dist_ultima = coach.distribucion_3_dominios(ultima, perfil)

# El aviso se basa en los datos que están en pantalla, no en lo que esté seleccionado:
# si elegiste tu cuenta pero todavía no tocaste el botón, seguís viendo el ejemplo.
viendo_ejemplo = st.session_state.get("fuente_cargada", "demo") == "demo"

if viendo_ejemplo and not modo_demo:
    st.markdown(
        '<div class="gc-banner">'
        "<span>Elegiste tu cuenta de Garmin, pero seguís viendo el ejemplo. "
        "Completá tu email y contraseña y tocá <b>Cargar entrenamientos</b>.</span>"
        "</div>",
        unsafe_allow_html=True,
    )
elif viendo_ejemplo:
    st.markdown(
        '<div class="gc-banner">'
        "<span><b>Estos son entrenamientos de ejemplo.</b> Para ver los tuyos, abrí "
        "<b>Garmin</b> en el panel de la izquierda, elegí <b>Mi cuenta de Garmin</b> "
        "y poné tu email y contraseña.</span>"
        "</div>",
        unsafe_allow_html=True,
    )

eyebrow("Tu última sesión")

datos_hero = [
    f'<span><b>{ultima["duracion_min"]:.0f}</b> min</span>',
    f'<span><b>{ultima["distancia_km"]:.1f}</b> km</span>',
]
if ultima.get("fc_prom"):
    datos_hero.append(f'<span><b>{ultima["fc_prom"]}</b> bpm medios</span>')
if ultima.get("elevacion_m"):
    datos_hero.append(f'<span><b>{ultima["elevacion_m"]:.0f}</b> m desnivel</span>')
if ultima.get("potencia_prom"):
    datos_hero.append(f'<span><b>{ultima["potencia_prom"]:.0f}</b> W medios</span>')
datos_hero.append(f'<span>carga <b>{ultima["trimp"]:.0f}</b></span>')

st.markdown(
    '<div class="gc-hero">'
    '<div class="gc-hero-top">'
    f'<div class="gc-hero-tipo">{coach.NOMBRE_TIPO[tipo_ultima]}</div>'
    f'<div class="gc-hero-fecha">{ultima["fecha"][:10]}</div>'
    "</div>"
    f'<div class="gc-hero-datos">{"".join(datos_hero)}</div>'
    '<div style="margin-top:1.35rem">'
    + cinta_umbrales(dist_ultima, con_marcas=True, con_leyenda=True)
    + "</div></div>",
    unsafe_allow_html=True,
)

if dist_ultima and not dist_ultima.get("exacta"):
    st.markdown(
        '<p class="gc-note">La cinta usa zonas calculadas por fórmula. Cargá tu ergoespirometría '
        "en la barra lateral para que use tus umbrales reales.</p>",
        unsafe_allow_html=True,
    )

with st.expander(
    "Ver el análisis completo de esta sesión", expanded=False, key="analisis_destacado"
):
    panel_analisis_sesion(ultima, sesiones, perfil, historial_pmc, modo_demo)

# ---------------- Estado de forma ----------------
eyebrow("Estado de forma")

ctl_hace_28 = historial_pmc[-29]["ctl"] if len(historial_pmc) >= 29 else None
delta_ctl_txt = ""
if ctl_hace_28 is not None:
    delta_ctl = ultimo["ctl"] - ctl_hace_28
    delta_ctl_txt = f' Cambió {delta_ctl:+.0f} en las últimas 4 semanas.'

desc_ctl = "Carga promedio de las últimas 6 semanas. Importa la tendencia, no el número." + delta_ctl_txt
desc_atl = "Carga promedio de la última semana. Sube y baja rápido."

if ultimo["tsb"] > 5:
    estado_tsb, desc_tsb = "Fresco", "Buen momento para la sesión más exigente de la semana."
elif ultimo["tsb"] < -10:
    estado_tsb, desc_tsb = "Cargado", "Conviene meter 1-2 días suaves antes de volver a forzar."
else:
    estado_tsb, desc_tsb = "Normal", "Ni muy fatigado ni muy fresco."

pos_tsb = (max(-30, min(30, ultimo["tsb"])) + 30) / 60 * 100

st.markdown(
    '<div class="gc-stats">'
    + tarjeta_estado("Fitness", f'{ultimo["ctl"]:.0f}', desc_ctl)
    + tarjeta_estado("Fatiga", f'{ultimo["atl"]:.0f}', desc_atl)
    + tarjeta_estado(
        "Forma",
        f'{ultimo["tsb"]:+.0f} <span style="font-size:.85rem;color:var(--ink-soft);font-family:\'IBM Plex Sans\',sans-serif">{estado_tsb}</span>',
        desc_tsb,
        marcador_pct=pos_tsb,
    )
    + "</div>",
    unsafe_allow_html=True,
)

with st.expander("¿Qué significan estos tres números?", expanded=False):
    st.markdown(coach.explicar_estado_conjunto(historial_pmc))
    if deporte == "bici":
        _sups = {s.get("superficie") for s in sesiones if s.get("superficie")}
        if len(_sups) > 1:
            st.markdown(
                "**¿Y si mezclo ruta, MTB y rodillo?** Estos tres números suman todas tus "
                "salidas juntas, y así tiene que ser: tu cuerpo acumula una sola fatiga, no una "
                "por superficie. Separarlas daría dos fotos incompletas de tu forma.\n\n"
                "Donde sí se separa es al comparar tu progreso: ahí cada sesión se mide solo "
                "contra otras de la misma superficie, porque la velocidad en MTB y en ruta no "
                "son comparables al mismo esfuerzo."
            )

# ---------------- Preparación para una carrera ----------------
eyebrow("¿Llego bien a una competencia?" if deporte == "running" else "¿Llego bien a una carrera?")
opciones_carrera = (
    ["10 km", "5 km", "21 km (media)", "42 km (maratón)", "Trail / montaña"]
    if deporte == "running" else ["Ruta", "MTB"]
)
col_tipo, col_fecha = st.columns([1, 2])
with col_tipo:
    tipo_carrera = st.selectbox("Distancia" if deporte == "running" else "Tipo de carrera", opciones_carrera, label_visibility="collapsed")
with col_fecha:
    fecha_carrera = st.date_input(
        "Fecha de la carrera", value=date.today() + timedelta(days=21),
        min_value=date.today(), label_visibility="collapsed",
    )

dias_hasta = (fecha_carrera - date.today()).days
analisis_carrera = coach.analisis_competencia(
    historial_pmc, sesiones, perfil, dias_hasta, tipo_carrera, deporte
)
st.markdown(feedback.feedback_competencia(analisis_carrera))

# ---------------- Secciones propias de running ----------------
if deporte == "running":
    test_run = perfil.get("test_fisiologico") or {}
    if test_run.get("estimado_desde_bici"):
        escribir_html(
            '<p class="gc-note">Tus umbrales fueron medidos en <b>bicicleta</b>. Para el análisis de '
            f'running se corrieron <b>+{metrics.DESPLAZAMIENTO_FC_RUNNING} pulsaciones</b> '
            f'(VT1 {test_run["vt1_fc"]}, VT2 {test_run["vt2_fc"]}), porque corriendo el pulso está '
            "más alto a la misma intensidad relativa. Es una estimación razonable, no una medición: "
            "lo exacto sería una ergoespirometría en cinta.</p>"
        )

    eyebrow("Volumen semanal y riesgo de lesión")
    texto_vol = feedback.feedback_volumen_running(coach.progresion_volumen_running(sesiones))
    if texto_vol:
        st.markdown(texto_vol)
        semanas_vol = coach.progresion_volumen_running(sesiones)["semanas"]
        fig_vol = go.Figure(go.Bar(
            x=[b["desde"] for b in semanas_vol], y=[b["km"] for b in semanas_vol],
            marker_color=C_ACENTO, hovertemplate="%{y:.1f} km<extra></extra>",
        ))
        fig_vol.update_layout(**LAYOUT_GRAFICO)
        fig_vol.update_layout(height=230, bargap=.5, yaxis=dict(title="km", gridcolor="#E4EAF0"))
        st.plotly_chart(fig_vol, width="stretch")

    eyebrow("Tiempos que podrías hacer hoy")
    st.markdown(feedback.feedback_prediccion_carreras(coach.predecir_carreras(sesiones), perfil))

# ---------------- Recorrido de una carrera ----------------
eyebrow("Analizar el recorrido de una competencia" if deporte == "running" else "Analizar el recorrido de una carrera")
st.markdown(
    '<p class="gc-caption">Subí el archivo <b>GPX</b> del recorrido y te digo cómo es, dónde se '
    'define, cómo te iría con tus números de hoy y qué convendría entrenar. En Garmin Connect o '
    'Strava podés descargar el GPX del recorrido; también sirve el que te pasa la organización.</p>',
    unsafe_allow_html=True,
)

archivo_gpx = st.file_uploader("Archivo GPX del recorrido", type=["gpx"], label_visibility="collapsed")

if archivo_gpx is not None:
    ritmo_objetivo = None
    if deporte == "running":
        c_terr, c_rit = st.columns(2)
        with c_terr:
            tipo_bici = st.selectbox("Tipo de terreno", ["Asfalto", "Trail / montaña"], key="terreno_ruta")
        with c_rit:
            # Se propone su propio ritmo llano reciente como punto de partida
            candidatas = [s.get("ritmo_min_km") for s in sesiones[-25:] if s.get("ritmo_min_km")
                          and (s.get("elevacion_por_km") or 0) < 10]
            sugerido = round(sum(candidatas) / len(candidatas), 1) if candidatas else 6.0
            ritmo_objetivo = st.number_input(
                "Tu ritmo en llano (min/km)", value=float(sugerido), step=0.1, format="%.1f",
                help="El ritmo que podrías sostener en llano durante toda la carrera.",
            )
        intensidad = 0.85
    else:
        c_bici, c_int = st.columns(2)
        with c_bici:
            tipo_bici = st.selectbox("Con qué bici la corrés", ["Ruta", "MTB"], key="bici_ruta")
        with c_int:
            intensidad = st.slider(
                "A qué % de tu FTP pensás subir", 70, 100, 85, step=5,
                help="85% es un ritmo de carrera larga sostenible. Para una carrera corta podés ir más arriba.",
            ) / 100

    try:
        with st.spinner("Analizando el recorrido..."):
            puntos = ruta.suavizar_altimetria(ruta.leer_recorrido(archivo_gpx.getvalue()))
            if puntos is None:
                st.warning("El archivo no trae datos de altura, así que solo puedo medir la distancia.")
                puntos = ruta.leer_recorrido(archivo_gpx.getvalue())
                for pt in puntos:
                    pt["alt_suave"] = None
            resumen_ruta = ruta.resumen_recorrido(puntos)
            subidas = ruta.detectar_subidas(puntos) if resumen_ruta["tiene_altimetria"] else []
            if deporte == "running":
                exigencia = ruta.analizar_subidas_running(subidas, ritmo_objetivo, tipo_bici)
                t_run = (
                    ruta.estimar_tiempo_running(puntos, ritmo_objetivo, tipo_bici)
                    if resumen_ruta["tiene_altimetria"] else None
                )
                tiempo_est = {
                    "horas": t_run["minutos"] / 60,
                    "texto": metrics.formatear_duracion(t_run["minutos"]),
                    "ritmo_texto": metrics.formatear_ritmo(t_run["ritmo_medio"]),
                    "vel_media_kmh": None,
                } if t_run else None
            else:
                exigencia = ruta.analizar_exigencia(subidas, perfil, tipo_bici, intensidad)
                tiempo_est = (
                    ruta.estimar_tiempo_total(puntos, perfil, tipo_bici, max(0.5, intensidad - 0.05))
                    if resumen_ruta["tiene_altimetria"] else None
                )

        # Perfil de altimetría, con las subidas resaltadas
        if resumen_ruta["tiene_altimetria"]:
            perfil_alt = ruta.remuestrear(puntos, paso_m=50)
            fig_ruta = go.Figure()
            fig_ruta.add_trace(go.Scatter(
                x=[m["dist"] / 1000 for m in perfil_alt],
                y=[m["alt"] for m in perfil_alt],
                mode="lines", line=dict(color=C_ACENTO, width=1.6),
                fill="tozeroy", fillcolor="rgba(45,74,124,0.10)",
                hovertemplate="km %{x:.1f} · %{y:.0f} m<extra></extra>", name="Altura",
            ))
            for i, s in enumerate(subidas, 1):
                fig_ruta.add_vrect(
                    x0=s["km_inicio"], x1=s["km_fin"],
                    fillcolor=C_ALTA, opacity=0.13, line_width=0,
                    annotation_text=f"{i}", annotation_position="top left",
                )
            alturas_g = [m["alt"] for m in perfil_alt]
            fig_ruta.update_layout(**LAYOUT_GRAFICO)
            fig_ruta.update_layout(
                height=280, showlegend=False,
                xaxis=dict(title="Kilómetro", gridcolor="#E4EAF0"),
                yaxis=dict(title="Altura (m)", gridcolor="#E4EAF0",
                           range=[min(alturas_g) - 30, max(alturas_g) + 40]),
            )
            st.plotly_chart(fig_ruta, width="stretch")

        st.markdown(feedback.feedback_recorrido(
            resumen_ruta, subidas, exigencia, tiempo_est, perfil, sesiones,
            dias_hasta, tipo_bici, intensidad, deporte,
        ))
    except Exception as e:
        st.error(
            f"No pude leer el archivo: {e}\n\n"
            "Fijate que sea un GPX del recorrido. Si lo tenés en otro formato (TCX, FIT o un enlace "
            "de Strava), avisame y agrego el soporte."
        )

# ---------------- Gráfico de carga ----------------
eyebrow("Evolución de la carga")
df_pmc = pd.DataFrame(historial_pmc).set_index("fecha")[["ctl", "atl", "tsb"]]

fig_pmc = go.Figure()
fig_pmc.add_trace(go.Bar(
    x=df_pmc.index, y=df_pmc["tsb"], name="Forma",
    marker_color=["#9FB3C8" if v >= 0 else "#E0B4AE" for v in df_pmc["tsb"]],
    yaxis="y2", opacity=.75, hovertemplate="Forma %{y:.0f}<extra></extra>",
))
fig_pmc.add_trace(go.Scatter(
    x=df_pmc.index, y=df_pmc["ctl"], name="Fitness",
    line=dict(color=C_ACENTO, width=2.4), fill="tozeroy", fillcolor="rgba(45,74,124,0.07)",
    hovertemplate="Fitness %{y:.0f}<extra></extra>",
))
fig_pmc.add_trace(go.Scatter(
    x=df_pmc.index, y=df_pmc["atl"], name="Fatiga",
    line=dict(color=C_MEDIA, width=1.6, dash="dot"),
    hovertemplate="Fatiga %{y:.0f}<extra></extra>",
))
fig_pmc.update_layout(**LAYOUT_GRAFICO)
fig_pmc.update_layout(
    height=330, hovermode="x unified",
    legend=dict(orientation="h", y=1.12, x=0, bgcolor="rgba(0,0,0,0)"),
    yaxis=dict(title="Fitness / Fatiga", gridcolor="#E4EAF0"),
    yaxis2=dict(title="Forma", overlaying="y", side="right", showgrid=False, zeroline=False),
)
st.plotly_chart(fig_pmc, width='stretch')

# ---------------- Distribución semanal de zonas ----------------
eyebrow("Minutos por zona, semana a semana")
df_sesiones = pd.DataFrame(sesiones)
df_sesiones["fecha_dt"] = df_sesiones["fecha"].apply(parse_fecha)
df_sesiones["semana"] = df_sesiones["fecha_dt"].apply(lambda d: d - timedelta(days=d.weekday()))

zonas_semana = {}
for _, row in df_sesiones.iterrows():
    semana = row["semana"]
    zonas_semana.setdefault(semana, {1: 0, 2: 0, 3: 0, 4: 0, 5: 0})
    for z in range(1, 6):
        zonas_semana[semana][z] += row["minutos_por_zona"].get(z, 0)

df_zonas = pd.DataFrame(zonas_semana).T.sort_index()

# Degradado del verde aeróbico al rojo intenso, coherente con la cinta de umbrales
ESCALA_ZONAS = {1: "#6FBFA8", 2: "#2F9B80", 3: "#DFA015", 4: "#CE7328", 5: "#CB4433"}

fig_zonas = go.Figure()
for z in range(1, 6):
    fig_zonas.add_trace(go.Bar(
        x=df_zonas.index, y=df_zonas[z], name=metrics.NOMBRE_ZONA[z],
        marker_color=ESCALA_ZONAS[z],
        hovertemplate="%{y:.0f} min<extra>" + metrics.NOMBRE_ZONA[z] + "</extra>",
    ))
fig_zonas.update_layout(**LAYOUT_GRAFICO)
fig_zonas.update_layout(
    barmode="stack", height=320, bargap=.45,
    legend=dict(orientation="h", y=1.14, x=0, bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    yaxis=dict(title="Minutos", gridcolor="#E4EAF0"),
)
st.plotly_chart(fig_zonas, width='stretch')

# ---------------- Resúmenes en texto ----------------
eyebrow("Cómo viene el período")
col_sem, col_mes = st.columns(2)
with col_sem:
    st.markdown("**Últimos 7 días**")
    st.markdown(f'<p class="gc-caption">{feedback.feedback_periodo(historial_pmc, dias=7)}</p>', unsafe_allow_html=True)
with col_mes:
    st.markdown("**Últimos 30 días**")
    st.markdown(f'<p class="gc-caption">{feedback.feedback_periodo(historial_pmc, dias=30)}</p>', unsafe_allow_html=True)

# ---------------- Distribución de intensidad ----------------
dist_periodo = coach.analisis_distribucion_periodo(sesiones, perfil, dias=28)
if not dist_periodo:
    eyebrow("Distribución de intensidad · 4 semanas")
    escribir_html(
        '<p class="gc-caption">Este análisis necesita tus <b>umbrales medidos</b> (VT1 y VT2) para '
        "saber cuánto tiempo entrenaste por debajo, entre y por encima de ellos — que es la forma de "
        "ver si tu entrenamiento está bien repartido. Las zonas calculadas por fórmula no alcanzan: "
        "el reparto saldría de una estimación y no diría gran cosa.<br><br>"
        "Si te hiciste una prueba de esfuerzo, cargala en <b>Mis datos → Prueba de esfuerzo</b> "
        "(panel de la izquierda) y esta sección se activa sola.</p>"
    )

if dist_periodo:
    eyebrow("Distribución de intensidad · 4 semanas")
    st.markdown(
        '<div style="margin-bottom:1rem">'
        + cinta_umbrales(
            {"pct": dist_periodo["pct"], "vt1": perfil["test_fisiologico"]["vt1_fc"],
             "vt2": perfil["test_fisiologico"]["vt2_fc"]},
            con_marcas=True, con_leyenda=True,
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(f'<p class="gc-caption">{dist_periodo["texto"]}</p>', unsafe_allow_html=True)

# ---------------- Umbral estimado ----------------
eyebrow("Tu umbral, según tus entrenamientos")
st.markdown(
    f'<p class="gc-caption">{feedback.feedback_lthr(metrics.estimar_lthr(sesiones), perfil)}</p>',
    unsafe_allow_html=True,
)

# ---------------- Sesiones anteriores ----------------
eyebrow("Sesiones anteriores")

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

# Un color por tipo de sesión, para que el ojo distinga el tipo sin leer
COLOR_TIPO = {
    "recuperacion": C_BAJA, "base": C_BAJA, "fondo_largo": C_BAJA,
    "tempo": C_MEDIA, "umbral": C_MEDIA, "vo2max": C_ALTA, "mixta_gris": "#6B7783",
}


def _fecha_corta(s):
    f = parse_fecha(s["fecha"])
    return f"{f.day:02d} {MESES[f.month - 1]}"


def _datos_fila(s):
    """Los datos que resumen una sesión, en el orden en que se leen."""
    datos = []
    if s.get("superficie"):
        datos.append(s["superficie"])
    datos.append(f"{s['duracion_min']:.0f} min")
    if s["distancia_km"]:
        datos.append(f"{s['distancia_km']:.0f} km")
    if s.get("deporte") == "running" and s.get("ritmo_texto"):
        datos.append(s["ritmo_texto"])
    if s.get("fc_prom"):
        datos.append(f"{s['fc_prom']} bpm")
    if s.get("elevacion_m"):
        datos.append(f"{s['elevacion_m']:.0f} m+")
    if s.get("desnivel_neg_m") and s.get("deporte") == "running":
        datos.append(f"{s['desnivel_neg_m']:.0f} m-")
    return datos


anteriores = list(reversed(sesiones[-31:-1]))

if not anteriores:
    escribir_html(
        '<p class="gc-caption">Todavía no hay sesiones anteriores para comparar. '
        "A medida que sumes salidas van a aparecer acá.</p>"
    )
else:
    # Un selector en vez de la lista completa: con 15 o 30 sesiones, mostrarlas
    # todas hacía una pantalla larguísima. La etiqueta lleva los datos clave, así
    # que la lista se sigue pudiendo escanear al desplegarla.
    etiquetas = []
    for s in anteriores:
        tipo = coach.NOMBRE_TIPO[coach.clasificar_sesion(s, perfil)]
        etiquetas.append(
            f"{_fecha_corta(s)}  ·  {tipo}  ·  {' · '.join(_datos_fila(s))}  ·  carga {s['trimp']:.0f}"
        )

    elegida = st.selectbox(
        "Elegí una sesión", etiquetas, index=0, label_visibility="collapsed",
        key="selector_sesion",
    )
    s = anteriores[etiquetas.index(elegida)]

    clave_tipo = coach.clasificar_sesion(s, perfil)
    dist_s = coach.distribucion_3_dominios(s, perfil)

    escribir_html(
        f'<div class="gc-sesion gc-sesion-sola" style="border-left-color:{COLOR_TIPO.get(clave_tipo, C_ACENTO)}">'
        f'  <div class="gc-sesion-top">'
        f'    <span class="gc-sesion-fecha">{_fecha_corta(s)}</span>'
        f'    <span class="gc-sesion-tipo">{coach.NOMBRE_TIPO[clave_tipo]}</span>'
        f'    <span class="gc-sesion-datos">{" · ".join(_datos_fila(s))}</span>'
        f'    <span class="gc-sesion-carga">carga {s["trimp"]:.0f}</span>'
        f"  </div>"
        f'  <div class="gc-sesion-cinta">{cinta_umbrales(dist_s, chica=True, con_marcas=False)}</div>'
        f"</div>"
    )
    escribir_html(
        '<p class="gc-caption">La barra muestra cómo se repartió el esfuerzo: '
        '<span style="color:var(--z-baja);font-weight:600">aeróbico</span> · '
        '<span style="color:var(--z-media);font-weight:600">intermedio</span> · '
        '<span style="color:var(--z-alta);font-weight:600">intenso</span>.</p>'
    )

    panel_analisis_sesion(s, sesiones, perfil, historial_pmc, modo_demo)

# ---------------- Sesiones con potenciómetro ----------------
sesiones_con_potencia = [s for s in sesiones if s.get("tiene_potencia")] if deporte == "bici" else []

# La sección se muestra aunque no haya potencia, explicando por qué está vacía.
# Antes se ocultaba entera y no había forma de saber si faltaba un dato, si estaba
# rota, o si hacía falta configurar algo.
if deporte == "bici" and not sesiones_con_potencia:
    eyebrow("Potencia")
    cuantas = len(sesiones)
    escribir_html(
        '<p class="gc-caption">Ninguna de tus '
        f"{cuantas} salidas trae datos de vatios, así que las secciones de potencia "
        "(curva de potencia, Potencia Crítica, W&#39;, TSS e Intensity Factor) no tienen con qué "
        "trabajar. <b>No es un error</b>: hace falta un medidor de potencia en la bici — el reloj "
        "y la banda de pulso no lo miden.</p>"
    )
    with st.expander("¿Y si tengo potenciómetro y aun así no aparece?"):
        st.markdown(
            "Repasá estas tres:\n\n"
            "1. **Que esté emparejado con el ciclocomputador**, no solo con la app del celular. "
            "Los vatios tienen que quedar grabados en la actividad.\n"
            "2. **Que la actividad los tenga.** Abrila en Garmin Connect: si no ves un gráfico de "
            "potencia ahí, tampoco van a llegar acá.\n"
            "3. **Si importás archivos**, que sean **FIT**. El GPX pierde la potencia en la mayoría "
            "de los casos.\n\n"
            "Mientras tanto, todo el resto del análisis funciona igual: la carga se calcula con el "
            "pulso (TRIMP), que es justamente lo que permite que la app sirva sin potenciómetro."
        )

if sesiones_con_potencia:
    eyebrow("Curva de potencia · CP y W'")
    st.markdown(
        '<p class="gc-caption">Trae el detalle segundo a segundo de tus sesiones con potencia para armar '
        'tu curva de mejores esfuerzos (5 seg a 60 min) y estimar tu Potencia Crítica (CP), tu capacidad '
        'anaeróbica (W\') y tu Time to Exhaustion (TTE) a FTP. Es una llamada pesada (una por sesión), '
        'así que se calcula bajo demanda.</p>',
        unsafe_allow_html=True,
    )
    n_sesiones_curva = st.slider(
        "Cantidad de sesiones recientes a incluir", 5, min(30, len(sesiones_con_potencia)),
        min(15, len(sesiones_con_potencia)),
    )

    if st.button("📈 Calcular curva de potencia"):
        seleccionadas = sorted(sesiones_con_potencia, key=lambda s: s["fecha"])[-n_sesiones_curva:]
        series_potencia = []
        with st.spinner(f"Analizando {len(seleccionadas)} sesiones..."):
            if modo_demo:
                series_potencia = [demo_data.generar_serie_demo(s)["potencia"] for s in seleccionadas]
            else:
                client = st.session_state.get("client")
                if client is None:
                    st.error("Conectate a Garmin primero (desmarcá el modo demo y cargá los datos).")
                else:
                    barra = st.progress(0.0)
                    for i, s in enumerate(seleccionadas):
                        try:
                            detalle = garmin_client.obtener_detalle_actividad(client, s["id"])
                            series_potencia.append(metrics.extraer_series(detalle)["potencia"])
                        except Exception as e:
                            st.warning(f"No pude traer el detalle de la sesión del {s['fecha']}: {e}")
                        barra.progress((i + 1) / len(seleccionadas))

        curva = metrics.calcular_curva_potencia(series_potencia) if series_potencia else {}
        cp_wp = metrics.ajustar_cp_wprime(curva)
        tte = metrics.estimar_tte(curva, perfil.get("ftp_watts"))
        st.session_state["curva_potencia"] = curva
        st.session_state["curva_cp_wp"] = cp_wp
        st.session_state["curva_tte"] = tte

    if "curva_potencia" in st.session_state and st.session_state["curva_potencia"]:
        curva = st.session_state["curva_potencia"]
        fig_curva = go.Figure()
        fig_curva.add_trace(go.Scatter(
            x=list(curva.keys()), y=list(curva.values()), mode="lines+markers",
            line=dict(color=C_ACENTO, width=2.2), marker=dict(size=6),
            name="Curva de potencia",
        ))
        if perfil.get("ftp_watts"):
            fig_curva.add_hline(y=perfil["ftp_watts"], line_dash="dot", line_color=C_MEDIA,
                                 annotation_text="FTP", annotation_font_color=C_MEDIA)
        fig_curva.update_layout(**LAYOUT_GRAFICO)
        fig_curva.update_layout(
            height=320, showlegend=False,
            xaxis=dict(title="Duración (segundos, escala logarítmica)", type="log", gridcolor="#E4EAF0"),
            yaxis=dict(title="Potencia (W)", gridcolor="#E4EAF0"),
        )
        st.plotly_chart(fig_curva, width='stretch')
        st.write(feedback.feedback_curva_potencia(
            curva, st.session_state.get("curva_cp_wp"), st.session_state.get("curva_tte"), perfil
        ))

if sesiones_con_potencia:
    eyebrow("Sesiones con potenciómetro")
    st.markdown(
        '<p class="gc-caption">El gráfico de Fitness/Fatiga/Forma de más arriba usa FC (TRIMP) para poder '
        'incluir todas tus salidas por igual. Acá abajo tenés el detalle de potencia real de las sesiones '
        'que sí tienen medidor, como referencia aparte (no se mezclan las escalas).</p>',
        unsafe_allow_html=True,
    )
    df_potencia = pd.DataFrame([{
        "Fecha": parse_fecha(s["fecha"]),
        "Sesión": s["nombre"],
        "Pot. prom (W)": s["potencia_prom"],
        "Pot. normalizada (W)": s.get("potencia_normalizada"),
        "W/kg": s.get("watts_por_kg"),
        "EF (W/bpm)": s.get("ef"),
        "TSS": s.get("tss"),
        "IF": s.get("if_"),
    } for s in sesiones_con_potencia])
    st.dataframe(df_potencia.sort_values("Fecha", ascending=False), hide_index=True)

# ---------------- Sesiones de gimnasio ----------------
if gym_raw:
    eyebrow("Gimnasio")
    st.markdown(
        '<p class="gc-caption">El cálculo de carga (TRIMP) es específico para ciclismo con frecuencia '
        'cardíaca. El gym se muestra acá como referencia de días totales de entrenamiento, para tener '
        'en cuenta la recuperación.</p>',
        unsafe_allow_html=True,
    )
    df_gym = pd.DataFrame([{
        "Fecha": parse_fecha(g["startTimeLocal"]),
        "Duración (min)": round(g.get("duration", 0) / 60),
        "FC prom": g.get("averageHR"),
    } for g in gym_raw])
    st.dataframe(df_gym.sort_values("Fecha", ascending=False), hide_index=True)

# ---------------- Variabilidad de la frecuencia cardíaca ----------------
if st.session_state.get("fuente_cargada") != "garmin":
    eyebrow("Variabilidad cardíaca y recuperación")
    escribir_html(
        '<p class="gc-caption">Garmin mide la variabilidad de tu pulso mientras dormís, y sirve para '
        "saber si tu cuerpo asimiló la carga o todavía la está procesando. Este análisis necesita "
        "conectarse a tu cuenta de Garmin (no funciona con archivos importados ni con datos de "
        "ejemplo, porque el dato viene del sueño y no de la actividad).</p>"
    )

if not modo_demo and st.session_state.get("fuente_cargada") == "garmin":
    eyebrow("Variabilidad cardíaca y recuperación")
    escribir_html(
        '<p class="gc-caption">Garmin mide la variabilidad de tu pulso mientras dormís. Sirve para '
        "saber si tu cuerpo asimiló la carga o todavía la está procesando. Traerla es una consulta "
        "por día, así que se hace bajo demanda.</p>"
    )

    if st.button("Analizar mi variabilidad cardíaca", key="btn_hrv"):
        client = st.session_state.get("client")
        if client is None:
            st.error("Primero cargá tus entrenamientos desde el panel de la izquierda.")
        else:
            with st.spinner("Trayendo los últimos 45 días..."):
                try:
                    st.session_state["hrv_datos"] = hrv.traer_rango(client, dias=45)
                except Exception as e:
                    st.error(f"No pude traer los datos de variabilidad: {e}")

    if st.session_state.get("hrv_datos"):
        datos_hrv = st.session_state["hrv_datos"]
        serie_hrv = hrv.linea_de_base(datos_hrv["serie"])

        if not serie_hrv:
            st.warning(
                "Tu cuenta no devolvió datos de variabilidad que pueda interpretar. "
                "Garmin la mide durante el sueño, así que hace falta dormir con el reloj y tener un "
                "modelo que la reporte."
            )
            if datos_hrv.get("crudo_ejemplo"):
                with st.expander("Ver lo que devolvió Garmin (para poder ajustarlo)"):
                    st.json(datos_hrv["crudo_ejemplo"])
        else:
            # Gráfico: VFC diaria contra su propia línea de base
            fig_hrv = go.Figure()
            fig_hrv.add_trace(go.Scatter(
                x=[d["fecha"] for d in serie_hrv], y=[d["rmssd"] for d in serie_hrv],
                mode="lines+markers", name="VFC de cada noche",
                line=dict(color=C_ACENTO, width=1.6), marker=dict(size=5),
            ))
            con_base = [d for d in serie_hrv if d.get("base")]
            if con_base:
                fig_hrv.add_trace(go.Scatter(
                    x=[d["fecha"] for d in con_base], y=[d["base"] for d in con_base],
                    mode="lines", name="Tu promedio",
                    line=dict(color=C_MEDIA, width=2, dash="dot"),
                ))
            fig_hrv.update_layout(**LAYOUT_GRAFICO)
            fig_hrv.update_layout(
                height=280, legend=dict(orientation="h", y=1.14, x=0, bgcolor="rgba(0,0,0,0)"),
                yaxis=dict(title="ms", gridcolor="#E4EAF0"),
            )
            st.plotly_chart(fig_hrv, width="stretch")

            st.markdown(feedback.feedback_hrv(
                hrv.estado_de_hoy(serie_hrv),
                hrv.eficiencia_segun_vfc(sesiones, serie_hrv, perfil),
                hrv.vfc_contra_carga(serie_hrv, historial_pmc),
                datos_hrv.get("sin_datos", 0),
            ))

