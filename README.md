# 🚴 Mi Coach de Ciclismo

Dashboard que trae tus entrenamientos de **Garmin Connect** y te da feedback en
español, en lenguaje de entrenador, pensado para vos: 48 años, entrenás con
**pulsómetro (sin potenciómetro)**, 3-4 salidas de bici y 2 de gym por semana.

---

## 1. Qué hace

- Trae tus últimas actividades de Garmin Connect (bici y gimnasio).
- Calcula tus **zonas de frecuencia cardíaca** personalizadas (método Karvonen).
- Calcula la **carga de entrenamiento** de cada sesión (TRIMP, el equivalente
  al TSS de potencia pero basado en pulso).
- Calcula tu **Fitness (CTL) / Fatiga (ATL) / Forma (TSB)** a lo largo del
  tiempo — el mismo modelo que usa TrainingPeaks, adaptado a pulsómetro.
- Si alguna sesión tiene **potenciómetro**, suma vatios, W/kg, **TSS** e
  **Intensity Factor**, y tu zona de potencia predominante (7 zonas de Coggan).
- Calcula el **Factor de Eficiencia (EF)** de cada sesión con potencia, para
  ver si tu motor aeróbico mejora con el tiempo.
- Bajo demanda, podés pedirle que calcule la **deriva cardíaca** de una sesión
  puntual (ver la sección de deriva cardíaca).
- Te da **feedback en texto plano**: por sesión, por semana y por mes, incluyendo
  velocidad, desnivel y cadencia.
- Tiene un **modo demo** con datos de ejemplo para que puedas probar todo
  antes de conectar tu cuenta real.

## 2. ⚠️ Cómo actualizar el proyecto

Cuando te pase una versión nueva, **descomprimí el zip reemplazando todos los
archivos**. Si Windows pregunta qué hacer con los repetidos, elegí *"Reemplazar
los archivos en el destino"* — nunca *"Omitir"*.

Si se reemplazan solo algunos, la app queda con piezas de dos versiones distintas
y falla. Para que eso no te agarre desprevenido, al arrancar verifica que los
archivos coincidan entre sí; si no, te dice exactamente cuál quedó viejo y qué
hacer, en vez de tirar un error técnico.

**Lo más seguro es borrar la carpeta entera y descomprimir de nuevo.** Tus datos
no están ahí: viven en `C:\Users\TuUsuario\.mi_coach_ciclismo`, así que no se
pierde nada.

## 3. Instalación

Necesitás Python 3.9 o superior instalado.

```bash
# 1. Entrá a la carpeta del proyecto
cd garmin_coach

# 2. (Recomendado) creá un entorno virtual
python3 -m venv venv
source venv/bin/activate        # en Windows: venv\Scripts\activate

# 3. Instalá las dependencias
pip install -r requirements.txt
```

## 4. Cómo correrla

**Windows - la forma más fácil:** hacé doble clic en `iniciar_app.bat`. Se va a
abrir una ventana negra (la terminal) y después el navegador con la app. Podés
minimizar la ventana negra, pero no cerrarla - si la cerrás, se apaga la app.

**Desde la terminal (cualquier sistema operativo):**

```bash
streamlit run app.py
```

`iniciar_app.bat` revisa e instala solo las librerías que falten antes de
arrancar, así que cuando el proyecto se actualiza no tenés que acordarte de
correr nada a mano.

Se te va a abrir automáticamente en el navegador (normalmente en
`http://localhost:8501`).

Por defecto arranca en **modo demo** (con datos de ejemplo generados), así
podés ver cómo funciona todo sin tocar tu cuenta de Garmin. Cuando quieras
usar tus datos reales:

1. Arriba de todo en el panel de la izquierda, elegí **Mi cuenta de Garmin**
   (viene seleccionado *Datos de ejemplo*).
2. Poné tu email y contraseña de Garmin Connect.
3. Dejá tildado **Recordar mi acceso en esta computadora** si no querés volver
   a escribir la contraseña cada vez.
4. Tocá **Cargar entrenamientos**.

### Cómo funciona "recordar mi acceso"

**No se guarda tu contraseña.** Lo que se guarda son los *tokens de sesión* que
Garmin devuelve al entrar — el mismo mecanismo que usa la app de Garmin en tu
celular para no pedirte la clave todos los días.

Esos tokens quedan en tu carpeta de usuario (`~/.mi_coach_ciclismo/garmin/` o
`C:\Users\TuUsuario\.mi_coach_ciclismo\garmin\`), **a propósito fuera de la
carpeta del proyecto**: así, si comprimís el proyecto para compartirlo con un
amigo, tu acceso a Garmin no viaja adentro.

Aun así, tratá esos tokens como si fueran la contraseña: le dan acceso a tu
cuenta de Garmin a quien los tenga. No los copies ni los compartas.

Los tokens vencen cada tanto. Cuando pase, la app te lo dice, borra la sesión
vieja y te pide el email y la contraseña de nuevo — no queda colgada. También
podés cerrarla a mano con **Olvidar esta sesión**, o con **Borrar datos** (que
borra el perfil y la sesión juntos).

Mientras estés viendo datos de ejemplo, un aviso amarillo arriba de todo te lo
recuerda, así no confundís esos entrenamientos con los tuyos.

Tu contraseña se usa únicamente para iniciar sesión en Garmin desde tu
propia computadora (vía la librería que se explica abajo) — la app no la
guarda en ningún archivo ni la envía a ningún otro lado.

## 5. La conexión con Garmin

Esta app usa la librería **`garminconnect`** (no oficial, de código abierto:
github.com/cyberjunky/python-garminconnect), que es la que usan la mayoría
de las apps de terceros para leer datos de Garmin. Algunas cosas a saber:

- **No es una API oficial de Garmin.** Funciona iniciando sesión igual que
  lo harías en la app o la web.
- Garmin puede cambiar su backend y romper la librería en cualquier momento.
  Si un día deja de conectar, probá primero: `pip install -U garminconnect`.
- Después del primer login guarda un token localmente (carpeta `~/.garth`)
  para no pedirte usuario y contraseña todo el tiempo.
- Si en algún momento preferís no depender de esto, la alternativa 100%
  manual es exportar cada actividad como archivo `.FIT` desde Garmin Connect
  y analizarla con la librería `fitparse` — más trabajoso, pero sin
  intermediarios.

## 6. Sobre el diseño de la interfaz

La app está pensada como **un informe de laboratorio**, no como un dashboard
deportivo. La razón: tus datos vienen de una ergoespirometría y todo el
análisis gira alrededor de dos líneas fisiológicas (VT1 y VT2), así que la
interfaz toma prestado el lenguaje del papel clínico — fondo claro, reglas
finas, números en tipografía monoespaciada y mucho aire.

**Los títulos de sección** van en el azul de la app, con una barra vertical al
costado que hace de ancla visual. Antes iban en gris claro y chicos: se perdían
al hacer scroll y costaba ubicarse en una pantalla larga. El contraste pasó de
4,6:1 a 8,6:1.

**Sobre el contraste.** Hay un script, `verificar_contraste.py`, que calcula la
relación de luminancia de cada par texto/fondo de la interfaz y avisa si alguno
baja de 4.5:1 (el mínimo recomendado para texto normal). Existe porque ya pasó:
la pestaña activa quedó con fondo azul oscuro y letra oscura encima, ilegible.
Ese error es invisible leyendo el código — hay que calcular los números.

Tres decisiones que vale la pena explicar:

**El primer bloque es tu última sesión**, no una fila de indicadores. Cuando
abrís la app al volver de entrenar, lo que querés saber es qué fue lo que
acabás de hacer.

**La cinta de umbrales** es el elemento que se repite en toda la app. Muestra
cómo se repartió tu esfuerzo entre los tres dominios (por debajo de VT1, entre
VT1 y VT2, por encima de VT2) y aparece en tres escalas: grande en tu última
sesión, chica al lado de cada sesión anterior, y como resumen de las últimas 4
semanas. Siempre significa lo mismo y usa siempre los mismos colores, así que
se lee de un vistazo sin tener que interpretar nada. Las marcas de VT1 y VT2
caen justo en el borde entre segmentos, porque ahí es exactamente donde está
el umbral.

**Las sesiones anteriores están en un selector.** Con 30 sesiones, mostrarlas
todas hacía una pantalla interminable. Ahora ocupan una sola línea; al
desplegarla se ve la lista completa, y cada entrada lleva los datos clave
(fecha, tipo, superficie, duración, distancia, pulso, desnivel y carga) para
poder escanearla sin abrir nada.

**Cuando abrís una sesión, se lee sin más clics.** Cada fila muestra la fecha, el
tipo de sesión, la duración, la distancia, el pulso medio, el desnivel y la
carga — más la cinta de umbrales. Un borde de color a la izquierda indica el
tipo de estímulo (verde aeróbico, ámbar intermedio, rojo intenso), para
distinguirlo sin leer. Recién si querés el detalle abrís el análisis.

**El panel de la izquierda está ordenado por frecuencia de uso**, no por
categoría. Arriba y siempre a la vista, lo único que tocás cada vez que
entrenás: de dónde traer los datos y el botón de cargar. Abajo y plegado, lo
que se configura una vez y no se toca más (tu edad y peso, tu prueba de
esfuerzo). Las secciones plegadas muestran su estado en el título — por
ejemplo *"Prueba de esfuerzo · cargada (31/07/2025)"* — así sabés qué hay
adentro sin abrirlas.

## 7. Otras marcas: Wahoo, Coros, Apple Watch, Polar, Suunto

La app tiene conexión directa **solo con Garmin**. Vale la pena explicar por qué,
porque no es un capricho:

- **Wahoo y Coros** tienen API oficial, pero exige registrarse como desarrollador
  y que aprueben la aplicación. Y no existe una librería no oficial mantenida
  como la de Garmin.
- **Apple Watch** directamente **no tiene API en la nube**. Los datos viven en el
  iPhone (HealthKit) y no hay de dónde bajarlos desde una app de escritorio.
- **Polar y Suunto** también piden registro y aprobación.

**La solución que sí funciona con todas: importar archivos.** Absolutamente
todos estos dispositivos exportan **FIT**, **TCX** o **GPX**, y la app lee los
tres. Una vez importada, la actividad se analiza igual que una de Garmin: mismas
zonas, mismo TRIMP, mismo análisis del entrenador, misma deriva cardíaca.

En el panel de la izquierda, elegí **"Archivos de mi reloj"**, indicá si son de
ciclismo o de running, y subí uno o varios archivos.

### Cómo exportar de cada marca

| Marca | Cómo |
|---|---|
| **Wahoo** | App ELEMNT → la actividad → compartir → exportar FIT |
| **Coros** | Web `trainingcn.coros.com` → la actividad → descargar FIT o GPX |
| **Apple Watch** | No exporta solo. Usá *HealthFit* o *RunGap*, o sincronizá con Strava y bajá el GPX |
| **Polar** | Polar Flow → la sesión → exportar TCX o GPX |
| **Suunto** | Suunto App → la actividad → exportar |
| **Strava** | La actividad → tres puntos → exportar GPX o "exportar original" |

### Qué formato conviene

**FIT es el mejor** de los tres: trae todo (pulso, potencia, cadencia, altura,
distancia) con una muestra por segundo. TCX viene después. **GPX es el más
pobre**: el pulso y la potencia van en extensiones que no todos los dispositivos
escriben, y la distancia no viene incluida — la app la calcula desde las
coordenadas. Si tenés la opción, exportá FIT.

## 8. Cómo personalizar tu perfil

Todo se carga desde la **barra lateral de la app** — no hace falta editar
código. Lo que cargues se guarda en `data/perfil.json` y persiste entre usos
(hay un botón **"💾 Guardar perfil"** al final de la barra lateral).

Podés ajustar:

- **Edad, peso**
- **FC en reposo**: medila apenas te despertás, en la cama, promediando 3-4
  días. Es el dato que más impacto tiene en la precisión de tus zonas.
- **FC máxima real**: si alguna vez la mediste en un test de esfuerzo o en
  una sesión muy exigente, cargala. Si no, la app la estima con la fórmula
  de Tanaka (`208 - 0.7 × edad`), que es más precisa que la clásica
  `220 - edad` para gente de más de 40 años — pero ningún cálculo le gana
  a un dato real.

## 8.1 Cargar tu ergoespirometría (prueba de esfuerzo)

Si te hiciste una prueba de esfuerzo con medición de gases, cargá los datos
desde la app: en la barra lateral, sección **🩺 Ergoespirometría** →
**"✏️ Cargar / editar mi estudio"**.

Los datos quedan guardados en `data/perfil.json`, así que se cargan una sola
vez y persisten entre usos. **No hace falta tocar el código.**

### Qué valores cargar

De todo el informe, los dos únicos **imprescindibles** son:

- **FC en VT1** (umbral aeróbico / primer umbral ventilatorio)
- **FC en VT2** (umbral anaeróbico / segundo umbral ventilatorio)

Esos dos números son los que transforman el análisis: son los puntos
fisiológicos reales que separan un tipo de estímulo de otro, y valen mucho
más que cualquier zona calculada por fórmula.

Opcionales pero recomendados: watts en VT1 y VT2, FC máxima alcanzada,
potencia pico, VO2max y la fecha del estudio.

### La tabla de 5 zonas

Por defecto la app **deriva las zonas automáticamente** a partir de VT1, VT2 y
tu FC máxima, así no tenés que tipear 10 números más. La derivación queda muy
cerca de lo que arman los laboratorios — comparando con un informe real:

| Zona | Derivada por la app | Tabla del laboratorio |
|------|--------------------|-----------------------|
| Z1   | 98-132             | 97-133                |
| Z2   | 132-147            | 133-149               |
| Z3   | 147-154            | 149-153               |
| Z4   | 154-161            | 153-164               |
| Z5   | 161-184            | 164-184               |

Si preferís cargar la tabla exacta de tu informe, tildá **"Cargar la tabla de
5 zonas exacta del informe"** dentro del formulario y completá los rangos.

### Si no tenés ergoespirometría

La app funciona igual: cae automáticamente en zonas calculadas por fórmula
(método Karvonen) y te avisa en los análisis que serían más precisos con
umbrales medidos. No hay que configurar nada.

### FTP y VT2: una aclaración honesta

Cuando cargás los watts de VT2, la app los propone como FTP si no tenías uno
cargado. Pero **no son exactamente lo mismo**: el FTP se define como lo que
sostenés ~60 minutos, mientras que el VT2 es un umbral fisiológico medido en
una prueba incremental más corta. Suelen estar bastante cerca, pero si hacés
un test de FTP de campo (20 min a fondo) y te da distinto, es totalmente
válido preferir ese número — podés cambiarlo en la barra lateral.

Para las zonas de **potencia**, la app usa el esquema de 7 zonas de Coggan
(basado en % de tu FTP) para el TSS/IF, no la tabla de 5 zonas del estudio.
Son dos sistemas con distinta cantidad de zonas, y unificarlos bien merece
hacerse con cuidado; si querés que lo integre, avisame.

## 8.2 ⚠️ Privacidad al compartir la app

Tus datos de salud (ergoespirometría, peso, FC) quedan en `data/perfil.json`,
**solo en tu computadora**. Nunca se suben a ningún lado.

Ahora bien, si le pasás a alguien el **zip del proyecto**, esa carpeta va
adentro. Antes de compartirlo, borrá el archivo `data/perfil.json` (o usá el
botón **Borrar datos** de la barra lateral).

Tu sesión de Garmin es el único dato que **nunca** viaja con el proyecto:
se guarda a propósito en tu carpeta de usuario, fuera del proyecto, justamente
para que compartir la carpeta no comparta tu acceso a Garmin.

Si en cambio compartís el **instalador** generado con `construir_exe.bat` +
`construir_instalador.bat` (ver sección 13), no hay problema: la carpeta
`data/` no se incluye en el empaquetado, así que cada persona arranca con la
app vacía y carga sus propios datos.

### Por qué la app te arranca con tus datos (y a tus amigos no)

Tus datos viven en **tu carpeta de usuario**, nunca dentro del programa:

```
C:\Users\TuUsuario\.mi_coach_ciclismo\datos\    (perfil y RPE)
C:\Users\TuUsuario\.mi_coach_ciclismo\garmin\   (sesión de Garmin)
```

Por eso, cuando instalás la app en tu PC te aparece todo lo tuyo: no viene con
el programa, ya estaba en tu carpeta. En la computadora de un amigo esa carpeta
no existe, así que la app arranca en cero y él carga lo suyo.

Podés confirmarlo desde la app: en el panel de la izquierda, abajo de todo,
**"Dónde se guardan mis datos"** te muestra las rutas exactas. Y si querés ver
la app tal como la va a ver un amigo, ahí mismo tenés **"Borrar todos mis
datos"**, que limpia el perfil, los RPE y la sesión de Garmin de una vez.

Corriendo como `.exe`, los datos de cada persona se guardan en
`C:\Users\SuUsuario\.mi_coach_ciclismo\datos\`. Tiene que ser fuera de la
aplicación: PyInstaller la descomprime en una carpeta temporal que Windows
borra al cerrar, así que si los datos vivieran ahí cada uno perdería su perfil
en cada cierre.


## 9. El análisis del entrenador

Cada sesión tiene dos pestañas. La de **Análisis del entrenador** es la
principal, y responde cinco preguntas en orden:

1. ### ¿Conviene separar ruta de MTB?

Garmin distingue las dos y la app lo lee, pero la respuesta es: **depende de para
qué**.

**Para la carga, NO se separan.** Fitness, Fatiga y Forma suman todas tus salidas
juntas, y así tiene que ser: tu cuerpo acumula una sola fatiga, no una por
superficie. Un TRIMP de 200 cuesta lo mismo en ripio que en asfalto. Separarlas
daría dos fotos incompletas de tu forma, y ninguna sería cierta.

**Para comparar tu progreso, SÍ.** Acá había un error real: la sección "Comparado
con tus sesiones parecidas" comparaba una salida de ruta contra una de MTB y
concluía *"fuiste más lento"*, cuando lo único que cambió era el terreno. En
montaña se anda más lento al mismo esfuerzo, y eso no es perder forma. Ahora cada
sesión se compara **solo contra otras de la misma superficie**.

La superficie aparece en cada fila de la lista (Ruta, MTB, Gravel, Rodillo; y en
running: Asfalto, Montaña, Pista, Cinta), así que se ve de un vistazo.

### Una sola clasificación, un solo dueño

La app clasifica cada sesión en **un solo lugar**: `coach.clasificar_sesion()`.
Todo lo demás la consulta, nadie la reimplementa.

Suena obvio, pero no lo era: había dos clasificadores en paralelo. El de la
pestaña de datos miraba solo la zona con más minutos, y eso producía
contradicciones directas en la misma pantalla — una sesión con 29% en Z2 pero con
23% en Z4 y 15% en Z5 se anunciaba como *"base aeróbica, se recupera rápido,
podés hacer gym mañana"*, mientras el análisis del entrenador la clasificaba
correctamente como VO2max. El mismo defecto afectaba al esfuerzo percibido: te
decía que "lo sentiste más duro de lo que fue" en sesiones que habían sido
genuinamente duras.

Ahora la pestaña **Datos y herramientas** muestra solo hechos —incluido el
reparto completo por zonas, que es más informativo que "predominó Z2"— y la
interpretación vive únicamente en **Análisis del entrenador**.

### Si tu reloj dice otra cosa

Es esperable, y no significa que alguna esté mal.

**La carga no es comparable.** Garmin calcula la suya con EPOC (el oxígeno extra
que consumís después de entrenar) mediante un modelo propio de Firstbeat. Esta
app usa TRIMP, que suma los minutos en cada zona por su intensidad. Son escalas
distintas — que una diga 264 y la otra 308 es como comparar 20 °C con 68 °F. Lo
que importa es que cada número sea coherente consigo mismo en el tiempo.

**El tipo de sesión también puede diferir.** El reloj usa más señales: consumo de
oxígeno estimado, efecto aeróbico y anaeróbico por separado, variabilidad latido
a latido. La app clasifica con lo que se lee del resumen (tiempo en cada zona y
pico de pulso), pero usando **tus umbrales de laboratorio**, que el reloj no
conoce a menos que se los cargues.

La clasificación mira tres cosas, no una: cuánto tiempo pasaste sobre VT2, cuánto
de ese tiempo fue *muy* por encima, y qué pico de pulso alcanzaste. La primera
versión miraba solo el tiempo sobre VT2 y metía casi todo en "umbral": una sesión
rondando los 163 y otra llegando a 178 se veían idénticas, cuando no tienen nada
que ver. Hay una prueba automática con ocho sesiones tipo (recuperación, base,
fondo largo, tempo, umbral clásico, umbral duro y dos de VO2max) que verifica que
cada una caiga donde corresponde.

**🏷️ Qué fue esta sesión.** La app la clasifica sola (recuperación, base,
   fondo largo, tempo, umbral, VO2max, o "mixta") mirando la distribución
   completa del esfuerzo, no solo la zona dominante.
2. **🎯 Cómo la ejecutaste.** Si era de base, ¿te mantuviste realmente suave o
   se te escapó? Si era de series, ¿recuperaste bien entre esfuerzos? Acá es
   donde aparece la advertencia de "zona gris" cuando corresponde.
3. **💪 Qué mejoraste.** Las adaptaciones fisiológicas concretas de ese tipo de
   estímulo: densidad mitocondrial, capilarización, desplazamiento del umbral,
   capacidad de amortiguación, VO2max, etc. — explicadas en criollo.
4. **📈 Comparado con tus sesiones parecidas.** Busca tus sesiones anteriores
   del mismo tipo y duración similar, y compara velocidad, FC y Factor de
   Eficiencia. Ir más rápido al mismo pulso es la señal más limpia de mejora.
5. **🔄 Recuperación y qué hacer ahora.** Cuántas horas de recuperación pide
   esa sesión, si conviene mover el gym de piernas, la ventana de nutrición
   post-entreno, y qué tipo de sesión hacer después.

El análisis incluye notas específicas para un ciclista de 48 años (marcadas
con 🧓), porque la recuperación y la respuesta al estímulo no son iguales que
a los 25.

**El modelo de 3 dominios.** Cuando hay una ergoespirometría cargada, el
análisis no usa las 5 zonas clásicas sino los dos umbrales reales: tiempo por
**debajo de VT1**, **entre VT1 y VT2**, y **por encima de VT2**. Son los dos
puntos fisiológicos que de verdad separan los tipos de estímulo, así que la
lectura es bastante más precisa.

Un detalle metodológico honesto: Garmin entrega los minutos agrupados por
zona, no segundo a segundo. Cuando un umbral cae en el medio de una zona, la
app reparte esa zona en forma proporcional al ancho de bpm de cada lado. Es
una aproximación, no un conteo exacto — para ver la forma general de la sesión
funciona bien, pero no lo tomes como un número al milímetro.

**Sin ergoespirometría también funciona** (importante si compartís la app):
cae automáticamente en el modelo de 5 zonas por fórmula, y avisa en el texto
que el análisis sería más preciso con umbrales medidos.

## 9.1 Distribución de intensidad (¿estás polarizado?)

En el dashboard hay una sección que analiza las **últimas 4 semanas** y te
dice qué porcentaje del tiempo pasaste en cada dominio. El patrón con mejor
evidencia en ciclismo de resistencia es el **polarizado**: alrededor de 80%
del tiempo por debajo de VT1, 15-20% por encima de VT2, y poco en el medio.

La app te dice en cuál de estos casos estás:
- **Polarizado** — seguí así.
- **Mucha base pero sin intensidad** — agregar una sola sesión de calidad por
  semana suele ser el salto de rendimiento más grande disponible.
- **Demasiado tiempo en la franja intermedia** — la "zona gris", donde más
  fatiga se acumula por unidad de adaptación.

## 9.2 ¿Llego bien a una carrera?

Los tres números de Fitness, Fatiga y Forma por separado no responden la pregunta
que importa antes de competir. Esta sección sí: elegís **Ruta** o **MTB**, ponés
la fecha, y la app evalúa cuatro cosas distintas — porque "estar bien" no es un
solo número:

1. **Motor** — ¿tengo base para la distancia? (tu Fitness comparado con tu propio
   mejor momento reciente)
2. **Chispa** — ¿hice trabajo parecido al de la carrera? (minutos por encima de
   VT2 en las últimas 3 semanas; para MTB se pide más, porque se corre a golpes
   de intensidad)
3. **Rumbo** — ¿mi forma crece o se cae?
4. **Frescura** — proyección de cómo quedaría tu Forma el día de la carrera
   según cómo entrenes hasta ahí

### Dos aclaraciones honestas sobre esta sección

**Los umbrales de Forma que circulan por internet no aplican acá.** Cosas como
"corré con TSB entre +5 y +25" están calculadas con TSS de potenciómetro. Esta
app mide la carga con TRIMP de pulso, que da números bastante más altos para la
misma sesión (una salida de 175 min puede dar 373 de TRIMP y ~170 de TSS). Por
eso la app calibra todo **contra tu propio historial**: te dice si hoy estás
fresco o cargado *para vos*, comparando con el rango en el que te movés
habitualmente. No compares tu Forma con tablas de otra escala.

**La recomendación de descarga no sale de una fórmula.** Sale de la
investigación sobre tapering, que es bastante consistente: recortar el volumen
entre un 40% y un 60% durante 8 a 14 días, manteniendo la intensidad. Probé
primero un enfoque que "optimizaba" alguna combinación de Fitness y Forma, y el
resultado dependía enteramente de cuánto peso le diera a cada uno — según cómo
eligiera esos pesos, la misma cuenta recomendaba no descargar nunca o descansar
dos semanas enteras. Así que la app te muestra las proyecciones de los cuatro
escenarios para que veas el precio de cada uno, y marca el que respalda la
evidencia. Las proyecciones informan; no deciden por vos.

Si faltan más de 21 días, la app te lo aclara: todavía estás en tiempo de
construir, y la descarga se planifica recién en los últimos 10-14 días.

## 9.3 Analizar el recorrido de una carrera

Subís el **GPX** del recorrido y la app te dice cómo es, dónde se define, cómo
te iría con tus números de hoy y qué convendría entrenar en el tiempo que
queda. Lo podés bajar de Garmin Connect, de Strava, o usar el que pasa la
organización.

Lo que hace, ordenado **de más a menos confiable** — y es importante que sepas
cuál es cuál:

**1. Geometría (muy confiable).** Distancia, desnivel, perfil de altura y
detección de las subidas importantes. Es matemática pura sobre las coordenadas,
no hay nada estimado.

Un detalle técnico que sí importa: los GPS miden la altura bastante mal, así que
el perfil se suaviza con una ventana de 250 m y el desnivel solo acumula cambios
mayores a 2 m. Sin eso el desnivel sale inflado por el ruido de la señal — es el
motivo por el que dos apps te dan desniveles distintos para la misma salida.

**2. Exigencia (razonablemente confiable).** Cuántos vatios y W/kg pide cada
subida, y cuántos minutos te llevaría. Sale de un modelo físico estándar
(gravedad + rodadura + resistencia del aire) usando tu FTP y tu peso reales.

**3. Tiempo total (poco confiable — tomalo con pinzas).** El modelo tiene que
suponer tu posición aerodinámica, la superficie, y no sabe nada del viento ni de
si vas a rueda de otros. En MTB además tu técnica bajando puede pesar más que
las piernas. Contá con un margen de error del 15% tranquilamente.

**4. Qué entrenar (lo más útil).** Acá se cruzan las exigencias del recorrido con
tus datos: si la subida clave pide 30 minutos continuos y tu salida más larga
reciente fue de una hora, te lo dice y te propone las series concretas. El tipo
de serie se ajusta a la intensidad real que pide la subida — al 85% del FTP eso
es *sweet spot* y no umbral, y entrenar umbral para una demanda de sweet spot
sale innecesariamente caro en fatiga.

También te arma un plan por semanas hasta la carrera, la estrategia de ritmo
para el día, y cuántos hidratos y líquido vas a necesitar por hora según la
duración estimada.

## 10. Running y entrenamiento bajo techo

### Sobre la palabra "carrera"

En español, *carrera* significa tanto el deporte como la competencia, y eso se
presta a confusión. La app lo resuelve así:

- El deporte se llama siempre **Running** (o "corriendo" cuando va en una frase).
- En modo running, una prueba se llama **competencia** — nunca "carrera".
- En ciclismo sí se usa "carrera" para la prueba, porque ahí no hay ambigüedad
  posible.

Así, en modo running la palabra "carrera" no aparece en ningún lado. Hay una
verificación automática que lo comprueba.

### El selector de deporte

Si tenés actividades de ciclismo y de running, arriba de todo aparece un
selector. **Los dos deportes se analizan por separado a propósito:** mezclar la
carga de correr con la de pedalear daría un número sin sentido (el impacto de
correr no se compara con pedalear) y, sobre todo, los umbrales de pulso no son
los mismos en cada deporte.

### ⚠️ Tus umbrales de bici no sirven tal cual para correr

Esto es importante y la app te lo recuerda en pantalla. Una ergoespirometría
hecha sobre bicicleta mide tus umbrales **en bicicleta**. Corriendo, la
frecuencia cardíaca suele estar entre 5 y 10 pulsaciones más alta a la misma
intensidad relativa: se mueve más masa muscular, hay impacto y la postura es
distinta.

Si se usaran las zonas de la bici para correr, pasaría exactamente lo mismo que
pasaba con el ciclocomputador mal configurado: sesiones suaves clasificadas como
duras. Por eso, en modo running la app corre los umbrales **+7 pulsaciones**
(el punto medio del rango habitual) y te lo aclara cada vez. Es una estimación
razonable, no una medición — lo exacto sería una ergoespirometría en cinta.

### Todo el análisis cambia, no solo los números

Al pasar a running no cambian únicamente las zonas: cambia **el texto completo
del entrenador**. Las adaptaciones que se explican, el consejo de recuperación,
la clasificación de la sesión, la sección de preparación para una carrera y el
análisis de recorridos son distintos en cada deporte.

Nada de bicicleta aparece en modo running: ni vatios, ni FTP, ni cadencia en
rpm, ni "salida suave". Y al revés. Hay una verificación automática que recorre
la pantalla en modo running buscando términos de ciclismo, para que esto no se
degrade al agregar cosas nuevas.

Un ejemplo concreto: la sección "¿Llego bien a una carrera?" ofrece **Ruta o
MTB** en ciclismo, y **5 km, 10 km, media, maratón o trail** en running — con
consejos propios de cada distancia y una exigencia de intensidad distinta (un
5 km necesita mucha más intensidad reciente que un maratón).

### Qué analiza en running

- **Ritmo y ritmo ajustado por pendiente (GAP).** En montaña, el ritmo crudo
  engaña: 6:00 min/km con 500 m de desnivel vale mucho más que 6:00 en asfalto.
  La app calcula el equivalente en llano para que puedas compararte con tus
  sesiones de asfalto.
- **Cadencia en pasos por minuto**, con la referencia de 170-180. Una cadencia
  baja implica zancada larga y más impacto por apoyo.
- **Adaptaciones propias de correr**: además de las cardiovasculares, la
  rigidez tendinosa y la resistencia ósea — que tardan **meses**, no semanas.
  Esa diferencia de velocidad entre el corazón y los tendones es la causa
  número uno de lesiones en quienes vienen del ciclismo: vas a poder aguantar
  de aire mucho antes de que las piernas estén listas.
- **Progresión del volumen semanal**, con aviso cuando hay un salto grande de
  kilometraje. Es el análisis más útil para no lesionarse.
- **Análisis de recorridos con modelo propio**: en carrera no se usa el modelo
  de vatios sino el costo de la pendiente sobre el ritmo. Subir cuesta ~3% de
  ritmo por cada 1% de cuesta, y bajar devuelve bastante menos de lo que quita
  subir — por eso un recorrido con 500 m de subida y 500 m de bajada es más
  lento que el mismo en llano. En trail se suma un recargo por el terreno, y si
  una subida pasa del 15% te avisa que conviene caminarla.
- **Dinámicas de la zancada**: tiempo de contacto con el suelo, oscilación
  vertical, ratio vertical, longitud de zancada y balance entre piernas. Solo
  aparecen si tu reloj las mide (banda HRM-Pro, Running Dynamics Pod o relojes
  recientes). Con una advertencia que importa: **son sobre todo una consecuencia
  de tu forma física y de la velocidad, no una causa.** Mejoran solas cuando
  mejorás como corredor, y forzar la técnica para bajarlas suele terminar en
  lesiones. Lo único que conviene trabajar directo es la cadencia.
- **Carga por ritmo (rTSS)**, además del TRIMP por pulso. Los dos miden lo mismo
  por caminos distintos: el TRIMP sirve siempre pero en series cortas se queda
  corto (el corazón tarda en subir), y el rTSS capta mejor esas sesiones pero
  necesita tu ritmo de umbral — que la app estima de tu mejor esfuerzo reciente.
  El gráfico de forma sigue usando TRIMP, porque funciona en todas las sesiones.
- **Desnivel negativo (m-)**, no solo el positivo. En trail es tan importante o
  más: subir cansa el motor, **bajar rompe el músculo** (contracción excéntrica).
  Si una sesión pasa de 500 m de bajada, la app te avisa que la recuperación la
  va a mandar ese daño, no el cardiovascular.
- **Potencia de carrera** si tu dispositivo la reporta, con la advertencia de que
  **no está estandarizada**: Garmin, Stryd, Coros y Polar usan modelos distintos
  y sus números no se comparan entre sí, ni con la potencia de ciclismo.
- **Predicción de tiempos** para 5 km, 10 km, media y maratón, con la fórmula
  de Riegel. Las distancias más lejanas a tu referencia aparecen marcadas con
  menos confianza, porque la fórmula asume que entrenaste para esa distancia:
  proyectar un maratón desde un 10 km sin tiradas largas da un número que
  después no se cumple.

### Rodillo y cinta

Las sesiones bajo techo se detectan solas y cambian dos cosas:

- **La deriva cardíaca se juzga con otra vara.** Sin viento que te refrigere, el
  calor acumulado sube el pulso por sí solo. Al aire libre una deriva mayor al
  10% ya es alta; bajo techo el corte está en 15%. Con los valores de la calle,
  una sesión de rodillo normal daría un diagnóstico falso de mala forma
  aeróbica.
- **El análisis lo menciona**: al mismo esfuerzo, una sesión bajo techo pesa un
  poco más de lo que dicen los números.

Si tu deriva en rodillo da alta, lo primero a revisar no es tu estado de forma
sino el ventilador.

## 11. Cómo leer las métricas (para vos, no para un fisiólogo)

**Zonas de FC (Z1 a Z5):** de más suave a más fuerte. La mayoría de tus
salidas deberían estar en Z1-Z2 (base aeróbica); Z4-Z5 son las sesiones
puntuales de calidad; Z3 es la "zona gris" — cansa sin aportar tanto,
conviene que no sea la protagonista.

**TRIMP:** un número que resume cuánto "costó" una sesión, combinando
duración e intensidad. Sirve para comparar entrenos entre sí, no tiene una
escala universal — lo importante es la tendencia.

**CTL (Fitness):** tu carga de entrenamiento promedio de las últimas ~6
semanas. Si sube de forma sostenida, estás construyendo forma física de base.

**ATL (Fatiga):** tu carga promedio de la última semana. Sube rápido después
de unos días exigentes y baja rápido si descansás.

**TSB (Forma):** la diferencia entre Fitness y Fatiga. Negativo = estás
cargado/fatigado (bajarle el ritmo). Positivo = estás fresco (buen momento
para una sesión fuerte o, en tu caso, para el gym pesado).

Una nota sobre el TSB: la convención clásica de TrainingPeaks lo calcula con
los valores del día *anterior*, porque su gráfico está pensado para planificar
a la mañana. Acá se usa el mismo día a propósito — esta app se mira sobre todo
al volver de entrenar, y con la convención clásica la pantalla mostraba cosas
como "Fitness 83 · Fatiga 119 · Forma −1": la resta no cerraba, y una sesión
muy dura recién terminada no se veía reflejada en la forma. Si comparás con
TrainingPeaks y ves una diferencia de un día, este es el motivo.

## 11.1 Deriva cardíaca (aerobic decoupling)

**Qué es:** en una salida larga y de esfuerzo estable, es normal que tu FC suba
un poco con el correr de los minutos aunque mantengas el mismo ritmo o la misma
potencia (por el calor acumulado, la deshidratación progresiva, y la fatiga
natural). A eso se le llama **deriva cardíaca** o *decoupling*. El indicador
clásico para medirla:

1. Se divide la sesión en dos mitades.
2. Se calcula la relación **potencia ÷ FC** (o **velocidad ÷ FC** si no tenés
   potenciómetro) en cada mitad.
3. Se compara cuánto cayó esa relación entre la primera y la segunda mitad.

**Cómo interpretarla:**
- **Menor a 5%:** excelente. Tu corazón sostuvo el esfuerzo sin perder eficiencia.
- **5-10%:** normal, sobre todo en salidas largas o con calor.
- **Mayor a 10%:** tu FC subió bastante más de lo esperable para el mismo
  esfuerzo. Puede ser calor, deshidratación, o que la duración/intensidad
  superó tu base aeróbica actual. Si se repite seguido en tus salidas largas,
  vale la pena mirar la hidratación y no acelerar tanto el aumento de volumen.

**Cómo usarla en la app:** abrí cualquier sesión (la destacada de arriba o
cualquiera de la lista), andá a la pestaña **Datos y herramientas** y tocá
**Analizar deriva cardíaca**. Al tocarlo, la app trae el detalle segundo a segundo de esa
actividad puntual y hace el cálculo. Es información que solo se pide bajo
demanda (no para las 15 sesiones a la vez) porque requiere una llamada extra
a Garmin por cada sesión.

Tiene más sentido en salidas de **fondo largas y estables** (45+ min en Z2)
que en sesiones de series o intervalos, donde el esfuerzo cambia todo el
tiempo y el número no significa lo mismo.

## 12. Si entrenás con potenciómetro

La app detecta automáticamente qué sesiones tienen datos de potencia (por ejemplo,
si tenés medidor en la bici de ruta pero no en la gravel, funciona igual con
las dos). Para las sesiones con potencia vas a ver, además del análisis por FC:

- **Vatios promedio, normalizados y W/kg.**
- **TSS (Training Stress Score)** e **Intensity Factor (IF)**, si cargaste tu
  **FTP** en la barra lateral (o si vos ya lo tenés configurado en tu cuenta de
  Garmin, en cuyo caso la app usa directamente el TSS que calcula Garmin).
- **Zona de potencia predominante**, con las 7 zonas clásicas de Coggan (de
  Z1 recuperación a Z7 sprints).

**¿Por qué el gráfico de Fitness/Fatiga/Forma sigue basado en FC (TRIMP) y no
en TSS?** Porque TSS y TRIMP están en escalas distintas, y mezclarlos en una
misma línea de tendencia daría una falsa sensación de precisión. Al usar FC
para el gráfico principal, se puede incluir el 100% de tus salidas (con o sin
potenciómetro) en una sola línea consistente. El detalle de potencia real
(TSS, IF, W/kg) se muestra aparte, en su propia tabla, sin mezclarse.

Cómo conseguir tu FTP:
- Si ya lo sabés (test de 20 min, test de 8 min, o el que te dio Garmin/tu
  entrenador), cargalo directamente en la barra lateral.
- Si no lo sabés, un valor aproximado y accesible: tu promedio de potencia en
  un esfuerzo máximo sostenido de 20 minutos, multiplicado por 0.95.

## 12.1 Curva de potencia, CP, W' y TTE

**Nota sobre la monotonía de la curva.** Lo que sostenés 5 minutos no puede
superar lo que sostenés 3, así que la curva se recorta para que nunca suba al
alargar la duración. No es una obviedad: tomar el máximo de cada duración por
separado *no* lo garantiza. Si la potencia va alta, baja y alta otra vez, toda
ventana corta cae en el hueco mientras que una larga alcanza los dos picos, y el
resultado sube. Es matemáticamente válido pero fisiológicamente absurdo. Con el
recorte, la curva significa lo que tiene que significar: **lo mejor que podés
sostener durante al menos ese tiempo**.

Con el botón **"📈 Calcular curva de potencia"** (dentro de la sección de
potencia del dashboard), la app trae el detalle de tus últimas sesiones con
medidor y arma tu **curva de potencia**: el mejor promedio que sostuviste
para cada duración, de 5 segundos a 60 minutos, tomando el mejor resultado
entre todas esas sesiones.

De esa curva se derivan:

- **CP (Potencia Crítica):** conceptualmente muy cercana a tu FTP - la
  potencia que, en teoría, podrías sostener por tiempo prolongado sin fatiga
  acumulativa. Se calcula ajustando el modelo clásico de 2 parámetros
  (Monod-Scherrer) sobre los puntos de tu curva entre 2 y 20 minutos.
- **W' (o FRC, capacidad de trabajo anaeróbico):** tu "tanque" de energía por
  encima de la CP, en kilojulios. Un W' alto = mejor para ataques, sprints y
  repechos cortos. Un W' bajo = perfil más "rodador", mejor en esfuerzos
  sostenidos.
- **TTE (Time to Exhaustion) a FTP:** acá tomé una decisión a propósito -
  en vez de calcularlo con la fórmula teórica `W' / (FTP - CP)`, lo estimo de
  forma **empírica**: busco en tu propia curva el esfuerzo sostenido más
  largo que dieras cerca de tu FTP (dentro de un 3%). La razón: en el modelo
  de 2 parámetros, FTP y CP terminan siendo casi el mismo número, y esa resta
  en el denominador se vuelve inestable justo ahí (tiende a infinito). Un
  valor tomado de tus propios mejores esfuerzos reales es más honesto que un
  número que la fórmula no puede sostener bien en ese punto exacto.

Esto pide traer el detalle de varias sesiones (una llamada por sesión a
Garmin), así que se calcula bajo demanda con un botón, no automáticamente -
podés elegir cuántas sesiones recientes incluir (más sesiones = curva más
completa, pero tarda más).

## 12.2 FC de umbral (LTHR)

Se calcula automáticamente, sin botón, a partir de tus propias sesiones:
- Si tenés potencia: promedia la FC de tus sesiones largas (20+ min) con
  Intensity Factor cercano a 1 - esos son, en la práctica, tus esfuerzos más
  parecidos a un test de umbral real.
- Si no tenés potencia: promedia la FC de las sesiones donde la zona
  dominante fue Z4 (umbral), como aproximación más rústica.
- Si no hay datos suficientes de ningún tipo, te lo dice directamente en vez
  de inventar un número.

Para más precisión que cualquiera de estas dos estimaciones, lo ideal sigue
siendo un test dedicado de 20 u 8 minutos a fondo.

## 12.3 Variabilidad de la frecuencia cardíaca (VFC)

Garmin la mide mientras dormís. La app la trae bajo demanda (es una consulta por
día) y hace **tres análisis**.

### Por qué NO se cruza con la curva de potencia

La pregunta natural es "cuando estoy mejor recuperado, ¿rindo más?", y lo obvio
sería cruzar la curva de potencia con la VFC. Pero eso no funciona por dos
motivos:

La curva de potencia es la envolvente de tus mejores esfuerzos de todo el
período: es casi estática, solo se mueve cuando hacés un récord. Cruzarla contra
un dato que cambia todos los días no dice nada.

Y la variante aparentemente sensata —comparar tu mejor potencia de cada día
contra la VFC de esa mañana— tiene un sesgo que la invalida: **solo producís
potencia alta cuando hacés una sesión dura**. En un rodaje suave tu potencia de 5
minutos es baja porque no lo intentaste, no porque estuvieras cansado. Esa
correlación mediría qué sesión planificaste, no tu recuperación.

### Lo que sí hace

**1. VFC contra tu propia línea de base.** El valor absoluto no dice casi nada
—depende de la edad, la genética y hasta de cómo dormiste con el reloj—, así que
lo que se mide es cuánto te apartás de tu promedio de los últimos días. Si estás
muy por debajo, hoy no es día para la sesión más dura.

**2. Eficiencia en sesiones comparables.** Acá está la respuesta honesta a tu
pregunta: compara tus vatios por latido en los días de VFC alta contra los de VFC
baja, **pero solo dentro del mismo tipo de sesión**. Ese agrupamiento es lo que
elimina el sesgo de arriba. También te dice con cuántas sesiones se hizo la
cuenta, porque con pocas una diferencia chica puede ser azar.

**3. VFC contra la carga acumulada.** Si tu VFC baja cuando el TSB se hunde, el
modelo de carga está describiendo bien tu fisiología y podés confiar en él. Si no
se mueven juntos, la VFC te sirve igual como señal de recuperación general, pero
no para juzgar si el entrenamiento fue mucho o poco.

Un detalle técnico de este tercer punto: usa el valor absoluto de la VFC, no el
desvío respecto de la base. El desvío detecta *cambios* y se recalibra solo — en
un bloque de carga largo la base baja junto con la VFC y el desvío vuelve a cero,
justo cuando más deprimida está. Para cruzar contra el TSB, que es un nivel
sostenido, hay que comparar niveles con niveles.

### Si no aparecen datos

Hace falta dormir con el reloj puesto y tener un modelo que la reporte. Si tu
cuenta devuelve algo que la app no reconoce, te muestra el dato crudo para poder
ajustarlo en vez de fallar en silencio.

## 12.3.1 Body Battery (experimental)

Garmin sí reporta HRV (variabilidad de la frecuencia cardíaca) y Body
Battery, pero de una forma que varía bastante según el modelo exacto de
reloj y la versión de la librería `garminconnect` instalada - así que, a
diferencia del resto de la app, todavía no lo integré al feedback
automático para no arriesgarme a mostrarte un número mal interpretado.

En cambio, dejé un botón de diagnóstico (dentro de un panel plegable
"🧬 HRV / Body Battery") que trae el dato crudo de tu cuenta tal cual lo
devuelve Garmin. Si te funciona y me compartís qué te muestra, lo integro
bien la próxima vez con la interpretación correspondiente.

## 12.4 VAM (Velocidad de Ascensión Media)

El botón aparece en **todas** las sesiones, no solo en las montañosas. Antes se
ocultaba cuando el desnivel promedio era bajo, y eso solo generaba confusión:
desaparecía sin explicar por qué. Además el desnivel promedio de una salida no
dice si hubo una subida sostenida — un recorrido "llano" puede tener un repecho
de 10 minutos que vale la pena mirar.

Ahora, junto al botón, una línea te dice qué esperar según el terreno de esa
sesión (montañoso, ondulado o llano). Y si no hay ninguna subida sostenida de al
menos 5 minutos, el resultado te lo dice claramente en vez de dar un número sin
sentido.

En sesiones con desnivel vas a ver:

- Un **VAM aproximado** directo en el feedback de la sesión, calculado con el
  desnivel total y la duración total de la salida - es un promedio de toda
  la sesión, así que mezcla la subida con los llanos y descansos.
- Un botón **"Calcular VAM real de la subida"** que trae el detalle de la
  actividad, **detecta las subidas de verdad** (uniendo los tramos que suben y
  tolerando descansos cortos) y calcula el VAM de la mejor — no el promedio de
  toda la sesión.

### Muestra varias subidas, no una

Un circuito ondulado suele tener dos cosas distintas: repechos cortos y
empinados, y alguna subida larga y suave. Por eso la app lista **todas** las
subidas relevantes de la salida, con su duración, pendiente y VAM.

Antes exigía un mínimo de 5 minutos por subida, y eso dejaba afuera los repechos
de 2-3 minutos al 15% — terminaba reportando la subida más suave del circuito,
que es justo la menos interesante. Ahora el mínimo son 2 minutos.

**El VAM tampoco se compara entre duraciones.** Un repecho de 2 minutos siempre
va a dar un VAM mucho más alto que una subida de 20, porque en algo tan corto se
puede ir muy por encima del umbral. En el ejemplo de arriba, dos repechos al 15%
dieron VAM 1728 y 1620, y una subida de 15 min al 4% dio 792 — no significa que
los repechos se subieran "mejor". Por eso la app muestra también la subida más
larga: ese número habla de tu resistencia, el otro de tu punch en subidas cortas.

### Una nota sobre cómo se mide el tiempo

Esto parece un detalle pero arruinaba el cálculo. **Garmin no devuelve una
muestra por segundo**: submuestrea el detalle a unos 1000-2000 puntos por
actividad. En una salida de dos horas, eso significa una muestra cada 7
segundos.

La primera versión contaba muestras como si fueran segundos, así que una
"ventana de 5 minutos" abarcaba en realidad 36 minutos y kilómetros de llano.
El síntoma era claro cuando uno lo miraba: decía *"5 minutos... a lo largo de
19,5 km"*, o sea 234 km/h. Y el VAM salía por encima de 4000 m/h, más del doble
que un ciclista profesional.

Ahora el tiempo se toma del propio archivo de la actividad, y si no viene, se
deduce de la duración total de la sesión. Nunca se cuentan muestras.

### Cómo leer el número

El VAM son los **metros de altura que ganás por hora**. Un VAM de 900 significa
que, a ese ritmo, subirías 900 metros de desnivel en una hora.

**La trampa: el VAM solo se compara entre subidas de pendiente parecida.** Es el
error más común. En una cuesta suave vas rápido pero ganás poca altura por hora;
en una empinada pasa lo contrario — con el mismo esfuerzo exacto. Un VAM de 600
al 4% puede ser un esfuerzo mayor que uno de 900 al 10%.

Por eso la app hace dos cosas más:

**Lo traduce a vatios por kilo** (solo en ciclismo). Ese número sí es comparable entre subidas
distintas, porque ya tiene la pendiente descontada. Usa la fórmula de Ferrari
(`VAM = W/kg × (2 + pendiente%/10) × 100`), que es confiable entre el 5% y el
12% de pendiente. Por debajo del 5% la resistencia del aire empieza a pesar más
que la gravedad y la conversión deja de valer, así que en esos casos la app te
dice que no la puede hacer en vez de mostrarte un número inventado.

**En running no se hace esa conversión.** La fórmula de Ferrari está hecha para
ciclismo, y no hay forma seria de derivar los vatios de un corredor desde el
VAM: la economía de carrera, la técnica de subida y el hecho de que arriba de
cierta pendiente convenga caminar hacen que la relación sea otra. En su lugar,
la app da referencias propias de trail (un aficionado en buena forma anda entre
600 y 900 m/h en subidas empinadas; los especialistas en kilómetro vertical
pasan de 1600) y, si la pendiente supera el 18%, te sugiere evaluar caminar
rápido — que arriba del 15-20% suele ser más rápido y más económico que trotar.

**Lo compara con tu propio umbral** (en ciclismo). Sabiendo tu FTP y tu peso, te dice a qué
porcentaje de tu umbral hiciste esa subida: si te sobraba resto, si estabas
justo en el límite, o si te fuiste por encima de lo sostenible. Eso es bastante
más útil que compararte con profesionales — que, para referencia, andan por los
1700-1800 m/h en puertos del 8%, lo que equivale a unos 6 W/kg.

## 12.5 RPE (Esfuerzo Percibido)

Garmin no expone esto por API porque es un dato subjetivo - por eso, dentro
del feedback de cada sesión, hay un control para que cargues vos mismo cómo
sentiste el esfuerzo (escala 1 a 10) y un botón "Guardar". Queda guardado en
`data/rpe_guardados.json`, así que persiste entre usos de la app.

Con eso, la app compara tu sensación contra lo que sugieren tus datos
objetivos (zona de FC dominante de esa sesión) y te avisa cuando hay una
diferencia grande: sentir una sesión mucho más dura de lo que objetivamente
fue puede ser una señal temprana de fatiga acumulada, falta de sueño, o
estrés de otro lado - algo valioso de trackear, sobre todo combinando
entrenamiento y trabajo como en tu caso.

## 13. Compartirla con tus compañeros (instalador)

Una aclaración importante primero: Streamlit **siempre** funciona mostrando su
interfaz en un navegador — así está construido, levanta un mini-servidor local
y renderiza ahí. Eso no cambia por más que la empaquetemos. Lo que sí
podemos hacer es que **no se vea como un navegador**: con `pywebview` se abre
una ventana nativa (sin barra de direcciones), y con un instalador de verdad,
tus compañeros la instalan con un asistente normal, les queda un ícono en el
menú de inicio, y la pueden desinstalar como cualquier programa - sin
necesitar Python ni saber que por dentro es una app de Streamlit.

### ⚠️ Cada vez que actualices el código, hay que recompilar

Los cambios en los archivos `.py` **no llegan solos al `.exe`**. El ejecutable
es una foto congelada del código al momento de compilarlo. Si actualizás el
proyecto y volvés a abrir el `.exe` sin recompilar, seguís corriendo la versión
vieja.

Para no equivocarte, podés usar el atajo que hace los dos pasos de una:

```powershell
reconstruir_todo.bat
```

Para saber con certeza qué versión está corriendo, mirá la primera línea del
registro (`%USERPROFILE%\.mi_coach_ciclismo\arranque.log`): incluye la fecha
del lanzador con el que se compiló.

**El proceso son dos pasos, los dos en tu propia PC con Windows:**

```powershell
construir_exe.bat
```
Arma la app empaquetada (tarda varios minutos). Queda en `dist\MiCoachDeCiclismo\`.

```powershell
construir_instalador.bat
```
Envuelve esa carpeta en un instalador de verdad usando **Inno Setup** (una
herramienta gratuita - si no la tenés instalada, el script te avisa y te
pasa el link de descarga). El resultado es un único archivo:
`instalador_salida\Instalador_MiCoachDeCiclismo.exe`.

**Ese archivo es el que le compartís a tus compañeros** — por mail si el
tamaño lo permite, o por Google Drive / OneDrive si pesa mucho (empaquetar
Python + Streamlit + Pandas + Plotly puede dar un instalador de bastantes
decenas de MB, es normal). Ellos lo corren, siguen el asistente (parecido a
instalar cualquier programa), y les queda instalado con su propio ícono.

**Cosas importantes para vos y para ellos, antes de compartirla:**

- **Cada persona usa su propia cuenta de Garmin.** La app no comparte datos
  entre instalaciones - cada compañero carga su propio email/contraseña de
  Garmin, su propio perfil (edad, peso, FTP), y sus propios RPE quedan
  guardados solo en su computadora. Es exactamente como debe ser para una
  herramienta de entrenamiento personal.
- **Windows probablemente va a mostrar una advertencia de SmartScreen** ("Windows
  protegió su PC") la primera vez que alguien lo instale o lo abra, porque el
  instalador no está firmado digitalmente (firmar código cuesta dinero y
  requiere un certificado de una entidad certificadora). Hay que tocar "Más
  información" → "Ejecutar de todas formas". Vale la pena avisarles esto de
  antemano para que no piensen que es un virus.
- Si tu empresa tiene políticas de IT restrictivas (bloqueo de instalación de
  software no aprobado), esto podría no funcionar en computadoras de trabajo
  sin permiso de un administrador - en ese caso, la alternativa más simple
  es que cada uno instale Python y use `iniciar_app.bat` (sección 4).

**Si algo falla al abrir el .exe:** el detalle queda registrado en
`C:\Users\TuUsuario\.mi_coach_ciclismo\arranque.log`. Ese archivo es lo que
hay que mirar, porque el ejecutable se arma sin consola y de otro modo las
fallas son invisibles.

Tené paciencia la primera vez: empaquetado, Streamlit puede tardar entre 20 y
40 segundos en levantar. La ventana espera hasta 90 segundos antes de darse
por vencida, y si se rinde te muestra un cartel diciendo dónde está el registro.

**Una honestidad importante:** el empaquetado no lo puedo compilar ni probar yo
(PyInstaller genera el resultado en el mismo sistema donde corre, y yo trabajo
en Linux). Lo que sí probé es la lógica del lanzador, y ahí aparecieron dos
errores que valen la pena mencionar porque explican por qué la primera versión
no funcionaba:

- Arrancaba Streamlit con la interfaz de línea de comandos, que no funciona
  dentro de un ejecutable. Ahora usa `bootstrap.run()`, que es la vía prevista
  para embeberlo.
- Esperaba 3 segundos fijos y abría la ventana. Como empaquetado tarda mucho
  más, la ventana aparecía apuntando a un servidor que todavía no existía: de
  ahí el mensaje *"localhost rechazó la conexión"*. Ahora consulta el puerto
  hasta que responde de verdad.
- Streamlit se considera "en modo desarrollo" cuando su propia ruta no contiene
  `site-packages`, y dentro del ejecutable sus archivos quedan en
  `_internal\streamlit\`, así que se activaba solo. En ese modo se niega a
  aceptar un puerto propio y aborta. Ahora se lo desactiva explícitamente. Este
  error es un buen ejemplo de por qué el registro vale la pena: corriendo de la
  forma normal no aparece nunca, así que solo se podía diagnosticar leyendo el
  log del ejecutable.

Si preferís no lidiar con nada de esto para un primer uso interno, `iniciar_app.bat`
(doble clic, sección 4) ya funciona bien para que un par de compañeros la
prueben, siempre que tengan Python instalado.

## 14. Limitaciones a tener en cuenta

- El cálculo de carga (TRIMP/CTL/ATL/TSB) está pensado **solo para ciclismo
  con pulsómetro**. Las sesiones de gimnasio se muestran aparte, como
  referencia de días totales de entrenamiento, pero no están integradas al
  mismo cálculo de fatiga (el pulso en el gym no refleja bien la fatiga
  muscular real).
- Cuando Garmin no manda el detalle de tiempo por zona de una actividad
  puntual, la app hace una estimación simple a partir de la FC promedio de
  esa sesión (queda aclarado en el feedback de esa sesión con una nota).
- Esto es una herramienta de apoyo para entender tus propios datos, no un
  reemplazo de un entrenador o de un chequeo médico — a los 48 años, si
  notás fatiga persistente, pulso en reposo elevado varios días seguidos, o
  cualquier síntoma raro, consultá con un profesional antes de seguir
  exigiendo el cuerpo.

## 15. Estructura del proyecto

```
garmin_coach/
├── app.py               # Dashboard de Streamlit (lo que corrés)
├── iniciar_app.bat       # Doble clic para arrancar en Windows
├── construir_exe.bat      # Paso 1: arma la app empaquetada (dist\MiCoachDeCiclismo\)
├── construir_instalador.bat # Paso 2: envuelve todo en un instalador real (Inno Setup)
├── reconstruir_todo.bat      # Atajo: hace los pasos 1 y 2 de una sola vez
├── instalador.iss           # Script de Inno Setup usado por construir_instalador.bat
├── launcher.py                # Punto de entrada usado solo para armar el .exe
├── config.py                # Tu perfil (edad, peso, FC reposo/máxima, FTP) y colores de zona
├── garmin_client.py           # Conexión con Garmin Connect
├── metrics.py                  # Zonas de FC/potencia, TRIMP, CTL/ATL/TSB, TSS, deriva cardíaca
├── feedback.py                  # Traducción de números a texto en español
├── coach.py                      # Análisis profundo: tipo de sesión, adaptaciones, recuperación
├── ruta.py                        # Lectura y análisis de recorridos GPX de carreras
├── hrv.py                          # Variabilidad cardíaca: base, eficiencia y carga
├── importar_actividad.py           # Importa actividades FIT/TCX/GPX de cualquier marca
├── rpe_store.py                  # Guarda tus valores de RPE por sesión (data/rpe_guardados.json)
├── perfil_store.py                # Guarda tu perfil y ergoespirometría (data/perfil.json)
├── .streamlit/config.toml          # Tema visual (colores base de la interfaz)
├── verificar_contraste.py           # Chequea que todos los textos se lean bien
├── verificar_secciones.py            # Chequea que nada desaparezca sin explicación
├── version.py                         # Versión del proyecto y dónde buscar actualizaciones
├── actualizador.py                     # Descarga y aplica versiones nuevas
├── abrir_en_celular.bat                 # Arranca la app accesible desde el teléfono
├── version.json                          # Lo que se publica para avisar de versiones nuevas
├── preparar_publicacion.bat               # Doble clic: arma el zip para GitHub
├── preparar_publicacion.py                 # El que hace el trabajo, y verifica que no lleve datos
└── .gitignore                              # Impide que los datos personales se publiquen
├── demo_data.py                   # Generador de datos de ejemplo (modo demo)
├── requirements.txt                # Dependencias para uso normal
└── requirements-exe.txt              # Dependencias extra, solo para armar el .exe
```

## 17. Actualizaciones sin reinstalar

La app puede buscar versiones nuevas y aplicarlas sola, sin que cada persona
tenga que volver a descargar e instalar. Está en el panel de la izquierda, abajo
de todo, en **ACTUALIZACIONES**.

### Cómo publicarlo en GitHub, paso a paso

Se hace una sola vez y no hace falta instalar nada ni saber usar git: todo por
la página web de GitHub.

> ⚠️ **Antes que nada:** el repositorio va a ser **público**, así que nunca subas
> la carpeta `data`. Ahí están tu perfil y tu ergoespirometría. El proyecto ya
> trae un `.gitignore` que la excluye, y el script `preparar_publicacion.bat`
> arma el zip sin ella y te lo verifica.

**1. Creá una cuenta** en [github.com](https://github.com) si no tenés. Es
gratis y no pide tarjeta.

**2. Creá el repositorio.** Arriba a la derecha, el botón **+** → *New
repository*.
- *Repository name*: `mi-coach-ciclismo`
- Elegí **Public**
- No tildes nada más
- **Create repository**

**3. Armá el zip limpio.** En tu PC, entrá a la carpeta del proyecto (la misma
donde está `iniciar_app.bat`) y hacé doble clic en **`preparar_publicacion.bat`**.

Genera `garmin_coach.zip` en esa carpeta y te confirma en pantalla que no lleva
nada personal. Si por algún motivo detectara datos personales adentro, **borra el
zip** para que no puedas subirlo por error, y te lo dice.

También podés correrlo desde PowerShell si preferís ver todo:

```powershell
python preparar_publicacion.py
```

**4. Subí los archivos.** En la página del repositorio vacío, hacé clic en
*uploading an existing file*. Arrastrá ahí:
- todos los archivos `.py`, `.bat`, `.txt`, `.md`, `.iss`
- la carpeta `.streamlit`
- `version.json`
- `garmin_coach.zip`

**NO** arrastres la carpeta `data`. Abajo, escribí cualquier descripción y tocá
**Commit changes**.

**5. Averiguá tu dirección.** En el repositorio, hacé clic en `version.json` y
después en el botón **Raw**. La dirección que aparece en el navegador es la que
necesitás. Tiene esta forma:

```
https://raw.githubusercontent.com/TU-USUARIO/mi-coach-ciclismo/main/version.json
```

**6. Pegala en `version.py`.** Abrí el archivo en tu PC con el Bloc de notas y
completá:

```python
URL_VERSION = "https://raw.githubusercontent.com/TU-USUARIO/mi-coach-ciclismo/main/version.json"
```

**7. Corregí la dirección del zip.** Abrí `version.json` y reemplazá
`USUARIO/REPO` por lo tuyo:

```json
"zip": "https://github.com/TU-USUARIO/mi-coach-ciclismo/raw/main/garmin_coach.zip"
```

**8. Volvé a subir** esos dos archivos corregidos a GitHub (misma operación del
paso 4, reemplazando los anteriores). Y listo: en la app, **Buscar
actualizaciones** ya funciona.

### Cada vez que quieras publicar una versión nueva

Son cuatro pasos y siempre los mismos:

1. Subí el número en **`version.py`** (`VERSION = "1.1.0"`)
2. Subí el mismo número en **`version.json`**, y escribí en `notas` qué cambió
3. Doble clic en **`preparar_publicacion.bat`**
4. Subí a GitHub los archivos que cambiaron + el `garmin_coach.zip` nuevo

Si los dos números no coinciden, el actualizador no detecta el cambio. Es el
error más fácil de cometer, y por eso `preparar_publicacion.bat` te los muestra
juntos antes de armar el zip.

Poné `"requiere_librerias": true` cuando la versión necesite alguna librería
nueva. Nadie tiene que correr nada: `iniciar_app.bat` las instala al abrir.

### Qué hace y qué no toca

- Reemplaza únicamente archivos de código (`.py`, `.bat`, `.toml`, `.md`, `.txt`,
  `.iss`).
- **Nunca toca la carpeta `data`.** Los perfiles y los RPE quedan intactos —
  está verificado con una prueba automática.
- Antes de reemplazar nada, comprueba que el zip sea válido y que realmente
  contenga el proyecto. Si el archivo llegó dañado o es otro zip cualquiera, no
  cambia nada y te lo dice.
- Guarda una copia de respaldo de los archivos anteriores en `_respaldo_X.Y.Z`,
  así una actualización problemática se puede revertir.

### ⚠️ El `.exe` no puede actualizarse solo

Esto es una limitación real, no un olvido. PyInstaller descomprime la aplicación
en una carpeta temporal que Windows borra al cerrar: escribir ahí no serviría de
nada. Así que la app instalada **detecta** que hay una versión nueva y lo avisa,
pero para aplicarla hay que instalar el nuevo instalador.

**Conclusión práctica:** si te importa poder actualizar seguido, es mejor que tus
compañeros usen `iniciar_app.bat` (necesita Python instalado, pero se actualiza
solo). El instalador conviene para quien no quiere saber nada de Python y va a
usar la misma versión por meses.

## 18. En el celular (Android y iPhone)

Sí se puede usar desde el celular, pero con una aclaración importante: **no es
una app nativa**. Es la misma aplicación, servida desde tu PC y vista en el
navegador del teléfono.

### Cómo

Doble clic en **`abrir_en_celular.bat`**. Te muestra la dirección de tu PC en la
red y arranca la app abierta a la red local. En el celular, conectate a la misma
WiFi y abrí esa dirección.

Para que quede como una app de verdad: en el navegador del celular, menú →
**"Agregar a la pantalla de inicio"**. Queda con su ícono y se abre a pantalla
completa, sin barra de direcciones. Funciona igual en Android y en iPhone.

La interfaz se adapta a pantalla angosta: las tarjetas se apilan, los títulos se
reducen y los márgenes se achican.

### Los límites, sin vueltas

- **La PC tiene que estar encendida** y con la app abierta. El celular no procesa
  nada, solo muestra.
- **Solo funciona en la misma red WiFi.** Fuera de casa no.
- La primera vez, el Firewall de Windows va a preguntar si permitís el acceso:
  hay que decir que sí, en red privada.

### ¿Y una app nativa de verdad?

Sería otro proyecto. Esta app está hecha con Streamlit, que funciona como sitio
web; una app nativa para las tiendas de Android e iPhone implica reescribirla
completa en otra tecnología, más las cuentas de desarrollador de Google y Apple
(la de Apple es paga y anual).

La alternativa intermedia sería publicarla en internet para poder entrar desde
cualquier lado, pero ahí aparece un problema serio: cada persona tendría que
poner sus credenciales de Garmin en un servidor compartido, y los datos de salud
dejarían de estar solo en su computadora. No lo recomiendo para esto.

## 19. Verificaciones automáticas

El proyecto trae varias comprobaciones que conviene correr después de cualquier
cambio, porque cubren errores que son invisibles leyendo el código:

| Qué revisa | Cómo |
|---|---|
| Contraste de todos los textos | `python verificar_contraste.py` |
| Código muerto, imports rotos | `python -m pyflakes *.py` |
| Que ninguna sección se oculte sin explicación | `python verificar_secciones.py` |
| Que la app arranque sin errores | `python -m streamlit run app.py` |

Y dentro del desarrollo se usan otras que vale la pena conocer: que la
clasificación acierte en ocho tipos de sesión conocidos, que en modo running no
aparezca ni un término de ciclismo, que ningún bloque HTML quede indentado (eso
lo muestra como texto crudo en pantalla), y que las llamadas entre módulos
coincidan con las firmas de las funciones.

## 20. Próximos pasos posibles

- Guardar el historial en una base de datos local para no depender de traer
  siempre las últimas 200 actividades.
- Sumar HRV / Body Battery si tu reloj los reporta, como indicador extra de
  si conviene forzar la sesión del día o bajarle el ritmo.
- Conectar la generación de feedback a la API de Claude para que los textos
  sean más variados y conversacionales (hoy son reglas fijas, 100% locales
  y sin costo de API).
