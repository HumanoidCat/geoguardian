# Estimación de riesgo climático por distrito con datos abiertos: el caso del cantón de Tilarán, Costa Rica

**Historia:** H10.5c · **Rúbrica:** IEEE · **Responsable:** Alejandro
**Depende de:** H10.5b (cerrada) · **Bloquea a:** H10.6, el cartel académico

---

> ## Estado de este documento
>
> **Borrador de trabajo, 18 de agosto de 2026.** Contiene las secciones que ya no
> van a cambiar y **declara vacías las que dependen de resultados que todavía no
> existen**.
>
> | Sección | Estado |
> |---|---|
> | I. Introducción | Redactada |
> | II. Trabajo relacionado | Redactada, sobre H10.5a y H10.5b |
> | III. Metodología | Redactada. Puede ajustarse si cambia una decisión |
> | IV. Arquitectura | Redactada |
> | V. Hallazgos sobre disponibilidad de datos | **Redactada. Es el aporte que ya existe** |
> | VI. Resultados | **Vacía. Necesita H3.6** |
> | VII. Discusión | **Vacía. Necesita la sección VI** |
> | VIII. Limitaciones | Redactada, se amplía con resultados |
> | IX. Conclusiones | **Vacía. Necesita las secciones VI y VII** |
>
> Las secciones vacías declaran **qué van a contener y qué hace falta para
> escribirlas**. Un apartado en blanco sin explicación es indistinguible de un
> olvido.
>
> **Ninguna cifra de este documento está escrita de memoria.** Todas salen de una
> herramienta del repositorio o de una fuente citada, y la sección de verificación
> al final dice de cuál.

---

## Resumen

Se presenta el diseño y la construcción de un sistema de estimación de riesgo
climático a escala distrital para el cantón de Tilarán, Guanacaste, Costa Rica,
construido exclusivamente sobre datos abiertos. El sistema estima tres eventos
—lluvia intensa, sequía e incendio forestal— para cada uno de los ocho distritos
del cantón, a un horizonte de siete días, comparando tres algoritmos de
aprendizaje supervisado contra una línea base climatológica bajo validación
temporal por ventana expansiva.

El trabajo reporta, además del sistema, **seis hallazgos medidos sobre la
disponibilidad y la aptitud de los datos abiertos globales a escala cantonal**,
obtenidos durante la construcción y verificados con herramientas que se publican
con el proyecto. Cuatro de esos hallazgos habrían producido resultados
aparentemente válidos y silenciosamente incorrectos.

*Palabras clave:* riesgo climático, datos abiertos, aprendizaje automático,
resolución espacial, SPI, Costa Rica.

---

## I. Introducción

### A. Problema

Tilarán es un cantón de 669,23 km² en la vertiente del embalse Arenal, con ocho
distritos y un régimen climático marcado por una estación seca de diciembre a
abril. Sus tres afectaciones climáticas recurrentes son la lluvia intensa, la
sequía agrícola y el incendio forestal.

Las herramientas de alerta disponibles para el cantón operan a escala nacional o
regional. La pregunta que este proyecto plantea no es si se puede estimar riesgo
climático —eso está resuelto— sino **si se puede hacerlo por distrito, para un
cantón concreto, usando únicamente datos abiertos y sin infraestructura de
observación propia**.

### B. Pregunta de investigación

> ¿Permiten los datos abiertos globales disponibles estimar el nivel de riesgo de
> lluvia intensa, sequía e incendio forestal **por distrito** en el cantón de
> Tilarán, con un desempeño superior al de una línea base climatológica?

La pregunta está formulada de modo que **las dos respuestas son informativas**. Si
los modelos superan la línea base, el resultado es un sistema utilizable. Si no la
superan, el resultado es que los datos abiertos globales no bastan a escala
cantonal, y eso responde igual de bien.

Esa simetría no es retórica: la sección V muestra que parte de la respuesta
negativa **ya está medida**, antes de entrenar ningún modelo.

### C. Aporte

1. Un sistema completo, reproducible y desplegable, construido sobre datos
   abiertos y publicado con su procedencia.
2. Seis hallazgos medidos sobre la aptitud de esos datos a escala cantonal, con
   las herramientas que los producen.
3. Una comparación de tres algoritmos contra una línea base climatológica bajo
   validación temporal estricta, para tres eventos distintos.

---

## II. Trabajo relacionado

> Esta sección se redacta a partir de `docs/investigacion/estado-del-arte.md`, de
> Luna, y de las 18 fichas de `docs/investigacion/referencias.md`. Lo que sigue es
> la síntesis; el insumo completo está en esos dos documentos.

### A. Existe un sistema nacional, y declara sus límites

Costa Rica opera desde 2020 el **Sistema de Alerta Temprana de Incendios
Forestales (SATIF)**, gestionado por el Programa Nacional de Manejo del Fuego del
SINAC-MINAE con apoyo del Instituto Meteorológico Nacional. Implementa el Fire
Weather Index canadiense adaptado al país, con cuatro categorías de peligro `[25]`.

Su propio operador declara el alcance: el SATIF **"se basa únicamente"** en
temperatura, humedad relativa, velocidad del viento y lluvia, y **"no toma en
cuenta el riesgo, topografía o combustibles (vegetación)"** `[25]`.

Esa declaración delimita el aporte de este trabajo con precisión y sin inflarlo.
Un índice meteorológico de peligro no es una estimación de riesgo, y al depender de
estaciones no produce un valor por distrito. Son cosas distintas.

**Y no las reemplaza.** El SATIF lleva cinco años operando con respaldo
institucional; este proyecto es un prototipo de un trimestre sin validación
externa. La comparación honesta es de naturaleza, no de calidad.

### B. La sequía en el Pacífico Norte está estudiada

El Centro de Investigaciones Geofísicas de la Universidad de Costa Rica tiene
trabajo sostenido sobre sequía en Guanacaste, y el SPI está establecido como el
índice pertinente para la región `[15]`. Este proyecto no discute esa elección: la
adopta.

### C. El vacío que este trabajo ocupa

Hasta donde la búsqueda de H10.5b pudo verificar, **no se localizó** trabajo
publicado que estime riesgo climático por distrito para un cantón costarricense
comparando algoritmos supervisados contra una línea base climatológica bajo
validación temporal, con datos exclusivamente abiertos.

La formulación es deliberada: **"no se localizó" no equivale a "no existe"**. La
búsqueda cubrió literatura indexada y no alcanzó literatura gris, tesis no
indexadas ni trabajo institucional no publicado.

---

## III. Metodología

### A. Área de estudio

Cantón de Tilarán, provincia de Guanacaste, código 508 de la División Territorial
Administrativa. Ocho distritos, códigos 50801 a 50808.

Las geometrías provienen de la capa distrital del **Sistema Nacional de
Información Territorial (SNIT)**, servicio WFS del IGN, filtradas por código de
cantón. La carga es transaccional e idempotente y deja registro de procedencia con
URL, fecha, sumas de verificación y número de entidades devueltas.

**Extensión medida del cantón:** 30,7 × 36,6 km, o 1124 km² de caja envolvente,
con 669,23 km² de superficie efectiva y una ocupación del 59,5 %.

### B. Fuentes de datos

| Variable | Fuente | Resolución | Justificación |
|---|---|---|---|
| Precipitación | CHIRPS | 0,05° ≈ 5,5 km | Es la única que distingue distritos. Sección V-A |
| Temperatura, humedad, radiación, viento | NASA POWER (MERRA-2) | 0,625° × 0,5° | No definen ningún umbral del sistema |
| Focos de calor | NASA FIRMS | 375 m | — |
| Geometrías distritales | SNIT, IGN | vectorial | Fuente oficial |

**La fuente es híbrida por una razón medida, no por conveniencia.** El motivo está
en la sección V-A y quedó registrado como decisión de arquitectura.

Ventana temporal: **1991-2025**, 35 años. No es arbitraria: la línea base
climatológica se define sobre la normal 1991-2020 y con menos registro no se puede
calcular como está declarada.

> **Las dos fuentes no son intercambiables.** Para un mismo día y punto, POWER
> reportó 0,0 mm y CHIRPS 18,72 mm. No es un error de ninguna de las dos: son
> productos distintos con procesos de asimilación distintos. Mezclarlas en una
> misma serie produciría discontinuidades que el modelo leería como señal.

### C. Procesamiento de señales

Se implementa filtrado de ruido con **Savitzky-Golay**, elegido sobre la media
móvil porque preserva los máximos: sobre un pico aislado conserva el 48,6 % de la
amplitud contra el 20,0 % de la media móvil. En un sistema cuyos umbrales se
definen sobre percentiles extremos, achatar los picos sesga los umbrales de forma
sistemática.

**El filtro no se aplica a la precipitación**, y esa decisión se tomó midiendo. El
resultado está en la sección V-B.

Índices derivados:

- **SPI** a 1 y 3 meses, por convolución de ventana móvil sobre el acumulado
  mensual, con ajuste gamma y corrección para ceros mediante distribución mixta
  `H(x) = q + (1−q)·G(x)` `[4]`.
- **Percentiles 95 y 99 del acumulado de 72 horas**, por distrito, sobre el
  período base 1991-2020.

> **Precisión terminológica.** El umbral de lluvia intensa **no es el índice R95p
> del ETCCDI**, aunque siga su criterio de percentiles extremos. R95p se define
> sobre precipitación diaria de días húmedos; este umbral, sobre acumulado de 72
> horas. La diferencia está medida en la sección V-D.

### D. Etiquetado de la variable objetivo

Tres niveles —bajo, medio, alto— por evento y distrito:

| Evento | Umbral | Origen |
|---|---|---|
| Lluvia intensa | Percentiles 95 y 99 del acumulado de 72 h, por distrito | Criterio de percentiles extremos del ETCCDI `[18]` |
| Sequía | SPI-3: alto si ≤ −1,5; medio si −1,5 < SPI ≤ −1,0 | McKee et al. `[4]`, adoptado por la OMM |
| Incendio forestal | Focos FIRMS en ventana de 7 días: **alto si hay al menos un foco**. No existe nivel medio | **Criterio del equipo**, corregido tras medir. No hay estándar equivalente |

El umbral de incendio es el único propio y se declara como tal en el sistema y en
la interfaz. Se somete a validación externa con el Comité Municipal de Emergencias.

**Y es el único de los tres que la medición obligó a rehacer.** La definición
original —bajo si 0, medio si 1 ≤ n ≤ P90, alto si n > P90— no producía tres
clases sobre estos datos sino dos: con **242 focos en 24 años** y entre el 97 % y
el 99,9 % de ventanas vacías, el percentil 90 vale 0,0 en los ocho distritos y la
condición intermedia queda vacía. Los dos umbrales tomados de estándares
publicados resistieron la verificación; el propio, no. Ver D-25 y SC-05.

El alcance del evento se acota además a **tres de los ocho distritos** —Santa
Rosa, Líbano y Tierras Morenas, que concentran el 88 % de los focos—. Los otros
cinco se reportan como «sin datos suficientes»: dos de ellos registran **un solo
foco en veinticuatro años**.

### E. Modelos y validación

Se comparan **tres algoritmos** —Regresión Logística, Random Forest y XGBoost—
contra una **línea base climatológica** construida por distrito, mes y tipo de
evento. La métrica principal es **F1-macro**, por el desbalance esperado entre
clases.

**La validación es por ventana expansiva y el corte aleatorio está prohibido.** Una
partición aleatoria sobre una serie temporal permite que el modelo vea el futuro:
produce métricas altas y sin significado. La prohibición está codificada en los
contratos del proyecto y verificada automáticamente: el evaluador rechaza una
partición fuera de orden temporal.

---

## IV. Arquitectura del sistema

### A. Estructura

Seis módulos con **interfaces congeladas antes de implementar**, cada una con un
simulado que la cumple:

```
extraccion  ->  almacenamiento  ->  senales  ->  modelado  ->  api  ->  visor
   (ETL)        (PostgreSQL/          (SPI,      (3 algoritmos   (REST)  (mapa)
                  PostGIS)         percentiles)   + linea base)
```

Cada contrato se declara como `Protocol` de PEP 544 con verificación estructural en
tiempo de ejecución. El propósito es que **nadie quede bloqueado esperando código
ajeno**: se trabaja contra el simulado y se sustituye por el módulo real en una
línea.

### B. Tres invariantes verificadas automáticamente

El proyecto declara tres reglas que ninguna implementación puede violar, y las
comprueba en integración continua:

1. **La ausencia de dato es `None`, nunca `0`.** Un cero es una medición; una
   ausencia no lo es. Confundirlos convierte una estación seca en un mes sin
   lluvia registrada.
2. **No hay estimación sin modelo entrenado detrás.** El sistema devuelve nivel
   nulo antes que un valor por defecto, y la interfaz lo distingue visualmente del
   riesgo bajo.
3. **La validación temporal no admite fuga.** Ver III-E.

### C. Verificación continua

Cada cambio pasa por cinco trabajos de integración continua y **ocho controles**
que comprueban desde la coherencia de los contratos hasta que las cifras escritas
en la documentación sigan siendo ciertas.

Ese último control existe por una razón: **contar a mano falló cinco veces en dos
días** durante la construcción, y uno de esos errores infló el avance reportado en
un documento ya entregado. La corrección no fue pedir más cuidado.

---

## V. Hallazgos sobre la disponibilidad de datos a escala cantonal

**Esta sección es el aporte que el proyecto ya tiene, con independencia de cómo
salgan los modelos.** Los seis hallazgos se obtuvieron durante la construcción, se
midieron con herramientas que se publican con el proyecto, y **cuatro de ellos
habrían producido resultados aparentemente válidos y silenciosamente
incorrectos**.

### A. Las fuentes climáticas globales de reanálisis no resuelven el cantón

NASA POWER sirve MERRA-2 en una malla de 0,625° × 0,5°, unos **68 × 55 km** a la
latitud de Tilarán. El cantón mide 669,23 km² y **cabe entero dentro de una sola
celda**.

Comprobado empíricamente: dos puntos separados dentro del cantón devuelven valores
idénticos hasta el último decimal, e incluso la misma elevación.

**La consecuencia no es pérdida de precisión, es imposibilidad.** Dos de los tres
eventos se definen sobre precipitación. Con una sola celda, los ocho distritos
habrían dado el mismo riesgo siempre, **por construcción**, y el sistema habría
respondido su propia pregunta de investigación por artefacto de la fuente.

CHIRPS, a 0,05°, sí distingue: los ocho distritos caen en **ocho celdas distintas**,
con una diferencia del 20,3 % en el acumulado semanal entre los extremos. Y el
orden entre distritos **se invierte entre días**, lo que descarta que sea un sesgo
constante del método y confirma variación espacial real.

*Herramienta:* `docs/herramientas/verificar_resolucion_fuente.py`.

> **Detalle metodológico que costó una corrección.** La primera versión de la
> herramienta suponía que todas las mallas se anclan igual. No es cierto: POWER
> ancla los **centros** de celda en múltiplos del paso y CHIRPS ancla los
> **bordes**. Con el supuesto equivocado la herramienta contradecía la observación
> directa. Se corrigió y se le agregó una autoprueba contra el dato observado.

### B. Filtrar la precipitación destruye los índices que se calculan sobre ella

El filtro de ruido de la sección III-C es correcto para variables con ruido
instrumental. Aplicado a la precipitación produce series que **no son series de
lluvia**:

| Efecto sobre 35 años de serie diaria | Magnitud |
|---|---|
| Días con precipitación negativa | **12,47 %**, mínimo −13,47 mm |
| Días secos que pasan a contar como húmedos | **31,62 %** |
| Caída del P99 de días húmedos | **−53,6 %** |
| Días del 1 % más extremo que sobreviven al umbral original | **0 de 37** |

No es un defecto de implementación: los coeficientes de Savitzky-Golay para
ventana 7 y orden 2 son **negativos en los extremos**, así que un día contiguo a un
aguacero recibe contribución negativa. Es una propiedad del método.

El 31,62 % es el más grave de los dos. El umbral de día húmedo del ETCCDI es
exactamente 1 mm: filtrar **reescribe el denominador** de los índices.

Resultado que cierra la discusión: con ventana 3 y polinomio de orden 2 el filtro
**no cambia nada**, porque con tres puntos una parábola pasa exactamente por los
tres. *La única configuración que no daña la precipitación es aquella en la que el
filtro no hace nada.*

*Herramienta:* `docs/herramientas/medir_efecto_filtro.py`.

### C. Un SPI sin ajuste por mes calendario mide estacionalidad, no anomalía

El SPI ajusta una distribución gamma **por cada mes calendario**: los eneros contra
la distribución histórica de los eneros. Eso es lo que lo convierte en un índice de
anomalía `[4]`.

Con ajuste único para toda la serie, sobre 35 años de régimen del Pacífico Norte:

| | Ajuste único | Ajuste por mes |
|---|---|---|
| SPI medio en estación seca | **−0,84** | −0,00 |
| SPI medio en estación lluviosa | **+0,60** | −0,00 |

Un índice de anomalía cuya media es −0,84 en una estación y +0,60 en la otra no
está midiendo anomalía. Y el dato que lo remata: **de los 99 meses que el ajuste
único declara en sequía, los 99 caen en estación seca.** El índice no detecta
sequía, detecta que es verano.

La correlación entre ambos métodos es **0,425**, lo que impide tratarlos como dos
versiones de lo mismo con distinta precisión.

**Dónde se paga.** Una etiqueta de sequía correlacionada con el mes calendario
haría que un modelo entrenado sobre ella aprendiera el calendario en lugar del
clima, **y en la evaluación se vería bien**, porque la estación seca es predecible.
Es la misma familia de resultado engañoso que la fuga temporal.

*Herramienta:* `docs/herramientas/medir_spi_por_mes.py`.

### D. El percentil del acumulado de 72 h no es el índice R95p

Dos cantidades que el proyecto llegó a nombrar igual, medidas sobre el mismo
período base de 30 años:

| | P95 | P99 |
|---|---|---|
| ETCCDI, diario sobre días húmedos | 39,90 mm | 54,86 mm |
| Acumulado de 72 h | 63,40 mm | 87,70 mm |

Aplicar el umbral equivocado **multiplica por 8,5** los días declarados en riesgo
alto: de 110 a 934 sobre 10 956 ventanas.

El umbral del proyecto no cambia —el acumulado de 72 h es el adecuado para riesgo
de inundación, porque un evento de lluvia intensa dura más de un día—. Lo que
cambió fue el nombre. **Un umbral atribuido a una fuente equivocada es peor que un
umbral sin citar.**

*Herramienta:* `docs/herramientas/medir_percentiles.py`.

### E. No hay registro histórico de incendios forestales en el cantón

DesInventar Costa Rica devuelve 98 fichas para Tilarán entre 1968 y 2017, cada una
con distrito explícito. **Ninguna es un incendio forestal.** Las cuatro fichas de
tipo FIRE son incendios estructurales.

Consecuencia directa: el contraste del componente de incendio contra eventos
históricos **no se puede hacer con registro documental**. Queda como limitación
declarada y obliga a apoyarse en los focos FIRMS.

### F. La sequía histórica no está desagregada por distrito

Las sequías de 1972, 1973, 1976, 1977, 1982 y 1983 existen en el registro **con el
campo de distrito vacío**. La de 2014 sí está desagregada, y solo porque una
declaratoria de emergencia obligó a inventariar la afectación finca por finca.

De ahí sale la observación más general de esta sección:

> **La disponibilidad de datos históricos a escala distrital no depende de la
> severidad del evento, sino de si existió un instrumento administrativo que
> obligara a levantarlos.** Es un sesgo de registro, no de ocurrencia.

*Fuente de E y F:* `docs/investigacion/catalogo-eventos.md`, 46 registros de 29
eventos distintos entre 1970 y 2026.

---

## VI. Resultados

> **VACÍA. No hay resultados porque no hay modelo entrenado.**
>
> **Qué va a contener:**
>
> 1. Tabla comparativa de los tres algoritmos contra la línea base climatológica,
>    por evento, con F1-macro, precisión y exhaustividad.
> 2. Matrices de confusión por evento y distribución de clases.
> 3. Curvas de desempeño bajo validación por ventana expansiva.
> 4. Importancia de variables del mejor modelo y explicaciones locales con SHAP.
>
> **Qué hace falta para escribirla:** las series climáticas reales (H1.1), el
> histórico de focos (H1.2), el etiquetado (H3.0), la línea base (H3.1), la
> validación (H3.2), los tres entrenamientos (H3.3 a H3.5) y la comparativa
> (H3.6).
>
> **Advertencia metodológica que ya está fijada.** Ninguna cifra de esta sección
> puede provenir de los simulados. El sistema opera hoy contra datos simulados y lo
> declara en pantalla; esos valores existen para construir y verificar la
> representación visual, y **no pueden aparecer en este documento bajo ninguna
> circunstancia**.

## VII. Discusión

> **VACÍA. Depende de la sección VI.**
>
> **Qué va a contener:**
>
> 1. Respuesta a la pregunta de investigación, en la dirección que resulte.
> 2. Interpretación física de las variables que resulten importantes, contrastada
>    contra lo que la literatura de la sección II establece para el Pacífico Norte.
> 3. Comparación de naturaleza —no de calidad— con el SATIF.
> 4. Contraste de las estimaciones contra el catálogo de eventos históricos, con la
>    salvedad de V-E: el contraste será sólido para lluvia intensa, débil para
>    sequía e inexistente para incendio.
>
> **Ya está decidido cómo se redacta el caso negativo.** Si los modelos no superan
> la línea base, la sección lo reporta como respuesta a la pregunta y no como
> fracaso del sistema, apoyándose en los hallazgos de la sección V, que apuntan en
> esa dirección desde antes de entrenar.

---

## VIII. Limitaciones

### A. El riesgo por distrito descansa hoy sobre una sola variable

De las cinco variables climáticas, **solo la precipitación tiene resolución
suficiente para distinguir distritos** (sección V-A). Temperatura, humedad,
radiación y viento son, para este cantón, constantes en el eje espacial.

La afirmación "riesgo por distrito" se sostiene sobre esa única variable. Es la
limitación más importante del trabajo y está medida, no supuesta.

### B. El componente de incendio es el más débil de los tres

Concentra tres debilidades a la vez: **no tiene estándar internacional** para su
umbral, **no tiene registro histórico** contra el cual validarse (V-E), y su
volumen de datos de entrenamiento es el más escaso de los tres.

**Ya no está supuesto: está medido.** El riesgo R16 se cerró el 20 de agosto con
**242 focos de FIRMS en 24 años** dentro del cantón. De ahí salieron tres hechos:

- El umbral por percentiles del conteo **no producía tres clases sino dos**. El
  P90 vale 0,0 en los ocho distritos, porque entre el 97 % y el 99,9 % de las
  ventanas de 7 días están vacías. Se corrigió a un objetivo binario, D-25.
- **Cinco de los ocho distritos no tienen datos suficientes**, y dos de ellos
  registran **un solo foco en veinticuatro años**. El alcance del evento se acotó
  a Santa Rosa, Líbano y Tierras Morenas, que concentran el 88 %.
- Con 33 a 38 ventanas positivas por distrito, **la comparación de algoritmos
  puede no ser concluyente para este evento**. Se declaró antes de medir ningún
  AUC, para que la elección de modelo no se justifique a posteriori.

De los tres umbrales del trabajo, los dos tomados de estándares publicados
resistieron la verificación. **El único que fijó el equipo, no.**

### C. Las dos deudas de verificación bibliográfica, saldadas

Se declararon el 19 de agosto en lugar de resolverse por conveniencia, y se
pagaron el 22 leyendo WMO-No. 1090 completo. El resultado no fue el esperado en
ninguno de los dos casos.

**1. El ajuste por mes calendario sí tiene respaldo, y está en otra sección.** La
5.1.1 describe el SPI de 1 mes como la comparación del total de noviembre de un
año contra los totales de noviembre de todos los años del registro; la 5.1.2 dice
lo equivalente para el trimestre y la 5.1.5 para los doce meses. Es
**descriptivo, no imperativo** —la guía nunca escribe «ajústese por mes
calendario»— pero define el conjunto de comparación como el mismo mes a través de
los años, que es el fundamento de D-19. La cita se restituye acotada a eso.

Lo buscábamos en la sección 6, que es donde no está.

**2. La fuente del tratamiento de ceros no era la que se creía, y había una
atribución falsa que nadie había detectado.** El código atribuía a WMO-No. 1090
la distribución mixta `H(x) = q + (1−q)·G(x)`. **La guía no contiene ninguna
fórmula**: su sección 6 remite a McKee et al. (1993, 1995) y a Edwards y McKee
(1997) para el procedimiento de cálculo.

La atribución correcta es Stagge et al. (2015). Y la verificación se declara
parcial: **el artículo está tras muro de pago y no se leyó**; lo que se leyó es la
documentación de `fitSCI` del paquete R `SCI`, firmada por dos de sus cinco
autores. Además, el `q/2` que usa esta implementación **no es la fórmula de
Stagge sino su límite** cuando el tamaño de muestra crece: la forma exacta es
`(n0 + 1) / (2(n + 1))`. Con 35 años la diferencia es despreciable, y se documenta
como simplificación y no como equivalencia.

**Lo que esto deja como aprendizaje metodológico.** El 19 de agosto se retiró una
atribución a esa fuente por no poder confirmarla, y **se dejó en pie otra a la
misma fuente, en el mismo archivo, ochenta líneas más abajo, sin revisarla**.
Retirar una cita dudosa no sirve si no se revisan sus vecinas, y una revisión que
no declara su alcance no permite saber qué quedó sin mirar.

**Ninguna de las dos afectaba a los resultados**: la decisión de V-C se sostiene
sobre la medición, no sobre la cita. Lo que sí habría llegado al documento es una
atribución falsa.

### D. Las mediciones de V-B y V-C son sobre series sintéticas

Ambas se hicieron sobre series generadas con el régimen del Pacífico Norte, porque
las series reales no estaban descargadas al medirlas. **Miden una propiedad del
método**, que no depende de los valores exactos del cantón, y las herramientas
quedan publicadas para repetirlas sobre los datos reales.

### E. Sin validación externa todavía

La validación con el Comité Municipal de Emergencias y el cálculo del puntaje SUS
no se han realizado.

### F. El sistema no está publicado, y esa es la limitación más grande

GeoGuardian se desplegó sobre Kubernetes local con k3d, según la decisión D-05: el
curso exige orquestación de contenedores y tres entornos, y operar un clúster
gestionado excedía el presupuesto del equipo. La decisión se cumple —los tres
entornos existen y funcionan— pero **"producción" es un espacio de nombres dentro
de un clúster que corre en una computadora del equipo.** No hay dominio ni acceso
externo.

La consecuencia es de fondo y no de infraestructura. Un sistema cuyo propósito es
que un comité de emergencias consulte el riesgo del día **no cumple ese propósito
si la única forma de consultarlo es que alguien lleve una computadora.** La
arquitectura no es el obstáculo: la API no guarda estado, la ingesta es idempotente
y el visor llega a la API por una ruta relativa justamente para funcionar detrás de
cualquier servidor (D-23). El obstáculo es el tiempo y el costo de operación dentro
de un trimestre.

Dentro del alcance se publica el visor como sitio estático con los datos declarados
como simulados, que es posible sin backend por la degradación que introdujo D-23.
Queda como trabajo futuro, en este orden: publicar la API y la base, automatizar la
ingesta diaria, y solo entonces retirar el aviso de simulación. Los tres pasos
dependen de que exista un modelo entrenado; publicar antes sería publicar un mapa
que no estima nada.

---

## IX. Conclusiones

> **VACÍA. Depende de las secciones VI y VII.**
>
> **Lo único que ya se puede afirmar**, y que se conservará con independencia del
> resultado de los modelos: los datos abiertos globales de reanálisis **no tienen
> resolución suficiente** para diferenciar distritos dentro de un cantón
> costarricense en cuatro de las cinco variables climáticas relevantes. Esa parte
> de la pregunta de investigación ya está respondida y medida.

---

## Referencias

> Las 18 fichas verificadas están en `docs/investigacion/referencias.md`, cada una
> con su DOI comprobado contra la editorial y una ficha de contenido que declara
> qué dice, por qué es relevante y dónde se usa.
>
> El listado formal en formato IEEE se traslada aquí al cerrar el documento, para
> no mantener dos copias que puedan desincronizarse. Es la misma regla que el
> proyecto aplica a la matriz de trazabilidad y a las cifras de la documentación.

---

## Anexo · De dónde sale cada cifra de este documento

Ninguna está escrita de memoria.

| Cifra | Origen |
|---|---|
| 669,23 km²; 30,7 × 36,6 km; 59,5 % | Medición sobre la carga del SNIT, H1.3 |
| 68 × 55 km, celda POWER | `verificar_resolucion_fuente.py` |
| 8 celdas CHIRPS, 20,3 % | Medición de César sobre ClimateSERV, incidencia I-05 |
| 0,0 mm contra 18,72 mm | La misma medición |
| 48,6 % contra 20,0 % de amplitud | `medir_efecto_filtro.py`, y comprobado contra el coeficiente teórico 17/35 |
| 12,47 %; 31,62 %; −53,6 %; 0 de 37 | `medir_efecto_filtro.py` |
| −0,84; +0,60; 99 de 99; 0,425 | `medir_spi_por_mes.py` |
| 39,90 / 54,86 / 63,40 / 87,70 mm; 8,5× | `medir_percentiles.py` |
| 98 fichas, 46 registros, 29 eventos | `docs/investigacion/catalogo-eventos.md` |
| 18 referencias | `docs/investigacion/referencias.md` |
| 33 comprobaciones, 5 trabajos de CI, 8 controles | `verificar_documentacion.py` |
| Cita textual del SATIF | Sitio del IMN, verificada palabra por palabra `[25]` |
