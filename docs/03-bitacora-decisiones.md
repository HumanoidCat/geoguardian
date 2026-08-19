# Bitacora de decisiones de arquitectura

Toda decision tecnica se registra aqui, numerada. Sin registro, la decision no
existe y se vuelve a discutir en dos semanas.

Formato: `docs/plantillas/plantilla-adr.md`. Cada registro lleva estado, fecha,
quien decide, contexto, decision, justificacion, alternativas descartadas,
consecuencias y medicion. **Lo que se pierde tambien se escribe.**

La fecha de cada registro es la del commit en que la decision quedo
materializada en el repositorio, no la de la conversacion que la origino.

| ADR | Decision | Estado | Fecha |
|---|---|---|---|
| D-01 | Fuentes globales abiertas como base primaria | Aceptada | 2026-08-03 |
| D-02 | Aprendizaje automatico clasico, sin redes profundas | Aceptada | 2026-08-03 |
| D-03 | PostgreSQL con PostGIS | Aceptada | 2026-08-03 |
| D-04 | Validacion temporal por ventana expansiva | Aceptada | 2026-08-03 |
| D-05 | Kubernetes con manifiestos y k3d local | Aceptada | 2026-08-03 |
| D-06 | Contratos con `Protocol`, no con clases abstractas | Aceptada | 2026-08-03 |
| D-07 | La ausencia de dato se representa como `None`, nunca como `0` | Aceptada | 2026-08-03 |
| D-08 | Umbrales de riesgo tomados de estandares publicados | Aceptada · revisada por D-19 | 2026-08-03 |
| D-09 | Tres algoritmos comparados, con SVM descartado | Aceptada | 2026-08-03 |
| D-10 | F1-macro como metrica principal de contraste | Aceptada | 2026-08-03 |
| D-11 | `docs/evidencias/` es de escritura libre para el equipo | Aceptada | 2026-08-05 |
| D-12 | Validacion externa con SUS, entrevista y caso retrospectivo | Aceptada | 2026-08-03 |
| D-13 | El SNIT es la fuente unica del vocabulario territorial | Aceptada | 2026-08-11 |
| D-14 | El frontend consume los simulados exportados a JSON estatico | Aceptada | 2026-08-12 |
| D-15 | Fuente climatica hibrida: CHIRPS para precipitacion, POWER para el resto | Aceptada | 2026-08-16 |
| D-16 | La propiedad de una carpeta sigue al trabajo asignado | Aceptada | 2026-08-16 |
| D-17 | La precipitacion no se filtra: los indices se calculan sobre la serie cruda | Aceptada | 2026-08-18 |
| D-18 | El nombre de un poblado no identifica a un distrito | Aceptada | 2026-08-18 |
| D-19 | El SPI se ajusta por mes calendario: contratos a v1.3.0 | Aceptada | 2026-08-18 |
| D-20 | La matriz de trazabilidad es un artefacto derivado, no un documento | Aceptada | 2026-08-18 |

---

## D-01 · Fuentes globales abiertas como base primaria

**Estado.** Aceptada · **revisada parcialmente por D-15** el 2026-08-16
**Fecha.** 2026-08-03 (`1fd614b`)
**Decide.** Alejandro, Lead PM

> **Nota de revision.** El principio de esta decision se mantiene: fuentes
> abiertas, sin dependencia del calendario de terceros. Lo que cambio es la fuente
> de **precipitacion**, que pasa de NASA POWER a CHIRPS por resolucion espacial.
> La consecuencia que este registro ya anticipaba —"se pierde resolucion local"—
> resulto ser mas grave de lo evaluado: no era perdida de precision sino
> imposibilidad de diferenciar entre distritos. Ver **D-15** e **I-05**.

### Contexto

El Instituto Meteorologico Nacional no ofrece una API publica identificable. El
acceso a sus series por convenio institucional puede tardar semanas y el tramite
no lo controla el equipo. El proyecto dura once semanas.

### Decision

NASA POWER, NASA FIRMS y Copernicus Sentinel-2 son las fuentes primarias. Los
datos institucionales costarricenses pasan a enriquecimiento opcional, fuera de
la ruta critica.

### Justificacion

Elimina de la ruta critica una dependencia administrativa sin fecha de
respuesta. NASA POWER ofrece series diarias desde 1981 sin registro previo, y
FIRMS publica focos de calor desde el ano 2000.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Esperar la respuesta del IMN | Sin fecha comprometida. Habria puesto todo el cronograma detras de un tercero |
| Usar solo Sentinel-2 | Cadencia de cinco dias y cobertura de nubes: insuficiente para una serie diaria |

### Consecuencias

Se gana independencia total del calendario de terceros. Se pierde resolucion
local: POWER entrega una celda de reanalisis, no una estacion en Tilaran, asi
que los valores son estimaciones de area y no mediciones puntuales. Esa
limitacion tiene que quedar escrita en el documento IEEE.

### Medicion

Pendiente. Se registrara tiempo de descarga y cobertura obtenida en H2.1.

---

## D-02 · Aprendizaje automatico clasico, sin redes profundas

**Estado.** Aceptada
**Fecha.** 2026-08-03 (`1fd614b`)
**Decide.** Alejandro, Lead PM

### Contexto

Los datos son tabulares: series climaticas diarias por distrito, ocho distritos,
unas pocas decenas de variables derivadas. El equipo tiene un trimestre y no
dispone de GPU.

### Decision

Regresion Logistica, Random Forest y XGBoost sobre scikit-learn y XGBoost. Sin
redes neuronales.

### Justificacion

En datos tabulares el gradient boosting iguala o supera a las redes profundas
con una fraccion del costo de desarrollo y sin hardware especializado. Ademas
los tres modelos elegidos admiten analisis de importancia de variables, que el
objetivo especifico OE3 exige.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| TensorFlow con LSTM | Curva de aprendizaje y tiempo de entrenamiento sin ganancia esperada a este volumen |
| Modelos preentrenados de series temporales | Requieren mas historia por serie de la que hay por distrito |

### Consecuencias

Se gana velocidad de iteracion y explicabilidad directa. Se pierde la capacidad
de capturar dependencias temporales largas de forma automatica: hay que
construirlas a mano como caracteristicas (ventanas moviles, rezagos), lo que
traslada trabajo a la epica E2.

### Medicion

Pendiente hasta H3.6, la tabla comparativa de los tres algoritmos.

---

## D-03 · PostgreSQL con PostGIS

**Estado.** Aceptada
**Fecha.** 2026-08-03 (`1fd614b`)
**Decide.** Alejandro, con autorizacion expresa del profesor del curso de Bases de Datos

### Contexto

El proyecto es geoespacial: poligonos distritales, puntos de focos de calor,
consultas de interseccion punto-en-poligono y agregacion por distrito.

### Decision

PostgreSQL 16 con la extension PostGIS 3.4.

### Justificacion

Integracion nativa con GeoPandas, GDAL y QGIS. La asignacion de un foco de
calor a su distrito es una consulta espacial en la base, no codigo de
aplicacion. Los cuatro esquemas (`crudo`, `geo`, `analitico`, `control`) se
modelan sin capas de traduccion.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Un motor relacional sin extension geoespacial nativa | Obligaria a resolver la interseccion espacial en Python, mas lento y mas dificil de auditar |
| SQLite con SpatiaLite | Sin control de concurrencia ni roles de minimo privilegio, que la rubrica BD exige |

### Consecuencias

Se gana potencia espacial y cumplimiento directo de la rubrica de Bases de
Datos. Se pierde simplicidad de instalacion: el equipo necesita Docker
funcionando antes de escribir una linea de SQL, lo que se convirtio en la
primera barrera real de arranque (ver incidencias I-01 e I-02).

### Medicion

No se ha medido. La comparacion de rendimiento contra una solucion no espacial
no es relevante para el alcance.

---

## D-04 · Validacion temporal por ventana expansiva

**Estado.** Aceptada
**Fecha.** 2026-08-03 (`1fd614b`)
**Decide.** Alejandro, Lead PM

### Contexto

Los datos son series temporales con dependencia entre observaciones
consecutivas. La pregunta de investigacion es si el modelo predice mejor que
una linea base climatologica a siete dias vista.

### Decision

Validacion por ventana expansiva: se entrena con el pasado y se evalua con el
futuro inmediato, repitiendo el corte hacia adelante. Queda **prohibido**
`train_test_split` con particion aleatoria en todo el proyecto.

### Justificacion

Una particion aleatoria filtra informacion del futuro al entrenamiento y
produce metricas infladas que no se sostienen en operacion. Bergmeir y Benitez
(*Information Sciences*, vol. 191, 2012) muestran que la validacion cruzada
estandar da estimaciones sesgadas cuando existe dependencia temporal.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| `train_test_split` aleatorio | Fuga temporal. Invalida el resultado sin que se note |
| Ventana deslizante de tamano fijo | Descarta historia antigua que si aporta a la estacionalidad anual |
| Un unico corte train/test por fecha | Una sola estimacion, sin idea de su variabilidad |

### Consecuencias

Se gana un resultado defendible ante el evaluador. Se pierde tiempo de maquina:
cada pliegue reentrena el modelo completo, asi que la evaluacion de tres
algoritmos por tres eventos se multiplica por el numero de pliegues. Hay que
presupuestarlo en S3.

### Medicion

Pendiente. El contraste contra la linea base es H3.6.

---

## D-05 · Kubernetes con manifiestos y k3d local

**Estado.** Aceptada
**Fecha.** 2026-08-03 (`1fd614b`)
**Decide.** Alejandro, con aprobacion del profesor de Arquitectura de Software

### Contexto

El curso de Arquitectura de Software exige orquestacion de contenedores y tres
entornos de despliegue. Operar un cluster gestionado excede la capacidad y el
presupuesto del equipo.

### Decision

Manifiestos de Kubernetes reales, ejecutados en un cluster k3d local. Los tres
entornos viven en el mismo cluster, en espacios de nombres distintos.

### Justificacion

Los manifiestos son identicos a los que se aplicarian en un cluster gestionado.
Se demuestra el diseno de despliegue sin asumir el costo de operar
infraestructura ni la deuda de aprender un proveedor de nube.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Cluster gestionado en la nube | Costo y tiempo de operacion no justificados para un MVP de un trimestre |
| Solo Docker Compose | No cumple el criterio de orquestacion de la rubrica |

### Consecuencias

Se gana cumplimiento de la rubrica a costo cero de infraestructura. Se pierde
realismo operativo: no hay balanceador real, ni almacenamiento persistente de
proveedor, ni un incidente de produccion que resolver. El manual de operacion
(H13.2) tiene que decir explicitamente que describe un entorno local.

### Medicion

No se ha medido.

---

## D-06 · Contratos con `Protocol`, no con clases abstractas

**Estado.** Aceptada
**Fecha.** 2026-08-03 (`1fd614b`)
**Decide.** Alejandro, Lead PM

### Contexto

Cuatro personas trabajan en paralelo sobre modulos que dependen entre si. Si
cada quien espera el codigo del otro, el proyecto se vuelve secuencial y no cabe
en once semanas. Hacia falta una forma de fijar las interfaces antes de que
exista una sola implementacion.

### Decision

Los cinco contratos de `contratos/` se declaran con `typing.Protocol` y
`@runtime_checkable`, no con `abc.ABC`. Cada contrato viene acompanado de un
simulado determinista en `contratos/simulados/`.

### Justificacion

`Protocol` da tipado estructural: una clase cumple el contrato por tener los
metodos, sin heredar de nada. Eso permite que cada persona escriba su modulo sin
importar codigo de las otras, y que los simulados y las implementaciones reales
sean intercambiables sin tocar el consumidor. `@runtime_checkable` habilita la
verificacion automatica con `isinstance` que corre en el CI
(`python -m contratos.verificar`).

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| `abc.ABC` con herencia | Acopla cada implementacion al modulo de contratos y obliga a un orden de importacion entre carpetas de distintos duenos |
| Solo anotaciones de tipo, sin verificacion | No falla en CI. Un contrato que nadie comprueba se rompe en silencio |
| Documentar las interfaces en un `.md` | No es ejecutable. Se desincroniza del codigo en la primera semana |

### Consecuencias

Se gana paralelismo real desde el dia uno y una red de seguridad en el CI. Se
pierde la herencia de comportamiento: no hay implementacion por defecto
compartida, asi que si dos modulos necesitan la misma logica auxiliar hay que
extraerla a una funcion aparte en vez de heredarla.

### Medicion

`python -m contratos.verificar` ejecuta 14 comprobaciones y las 14 pasan desde
`1fd614b`. Corre como trabajo independiente en el CI.

---

## D-07 · La ausencia de dato se representa como `None`, nunca como `0`

**Estado.** Aceptada
**Fecha.** 2026-08-03 (`1fd614b`)
**Decide.** Alejandro, Lead PM

### Contexto

Las series de NASA POWER tienen huecos. Un dia sin medicion y un dia con cero
milimetros de lluvia son cosas distintas, pero muchas rutinas de carga los
igualan rellenando con cero. En un proyecto de riesgo climatico esa confusion
cambia el resultado del modelo y de la linea base.

### Decision

Todo campo de medicion es `float | None`. Un dato que no se pudo obtener o
calcular se representa como `None`. Nunca `0`, nunca un valor plausible, nunca
la fecha omitida. `SerieTemporal` conserva las fechas sin dato con `valor` en
`None` en lugar de saltarlas.

### Justificacion

Cero milimetros de lluvia es una medicion; la ausencia de dato no lo es.
Rellenar con cero introduce sesgo hacia el escenario seco justo en el evento que
mas nos interesa. Omitir la fecha rompe la continuidad de la serie y hace
imposible calcular acumulados de 72 horas o el SPI, que dependen de ventanas
contiguas.

La regla se extiende a la estimacion: `Riesgo.nivel`, `.probabilidad` y
`.explicacion` son opcionales, porque un riesgo sin modelo entrenado detras es
ausencia de estimacion, no riesgo bajo.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Rellenar los huecos con `0` | Sesga hacia sequia y falsea la lluvia acumulada |
| Rellenar con la media o la normal del mes | Es imputacion, y una imputacion no declarada se vuelve invisible aguas abajo |
| Omitir las fechas sin dato | Rompe las ventanas contiguas de las que dependen SPI y acumulados |
| Un centinela numerico como `-999` | Se propaga a los calculos si alguien olvida filtrarlo |

### Consecuencias

Se gana honestidad del dato de punta a punta: una pantalla vacia es preferible a
una llena de valores inventados. Se pierde comodidad: cada calculo tiene que
manejar `None` explicitamente, y toda imputacion deliberada debe quedar marcada
con su `MetodoImputacion`, distinto de `SIN_IMPUTAR`.

### Medicion

`contratos/verificar.py` comprueba explicitamente que una medicion de `0.0` mm
no se confunda con una ausencia de dato, y que un riesgo sin modelo entrenado
salga nulo. Las dos comprobaciones pasan.

---

## D-08 · Umbrales de riesgo tomados de estandares publicados

**Estado.** Aceptada · **revisada el 2026-08-18**, ver la nota
**Fecha.** 2026-08-03 (`1fd614b`)
**Decide.** Alejandro, Lead PM

> **Nota de revision del 2026-08-18.** El principio se mantiene: los umbrales no
> los inventa el equipo. Lo que estaba mal era **el nombre de uno de ellos**.
>
> La tabla de abajo decia que el umbral de lluvia intensa son "los percentiles
> R95p y R99p" del ETCCDI. **No lo son.** R95p se define sobre precipitacion
> **diaria de dias humedos**, de 1 mm o mas; nuestro umbral se calcula sobre el
> **acumulado de 72 horas**. Luna implemento las dos cantidades en H2.7 y las
> midio sobre 30 anios:
>
>     ETCCDI, diario de dias humedos      P95: 39,90 mm    P99: 54,86 mm
>     acumulado de 72 h                   P95: 63,40 mm    P99: 87,70 mm
>
>     dias en riesgo alto con el umbral de acumulado :   110  (1,00 %)
>     dias en riesgo alto con el umbral diario       :   934  (8,53 %)
>
> **El umbral no cambia.** El acumulado de 72 h es el adecuado para riesgo de
> inundacion, porque un evento de lluvia intensa dura mas de un dia. Lo que cambia
> es como se nombra: el corte **sigue el criterio** de percentiles extremos del
> ETCCDI, que es otra cosa que **ser** uno de sus indices.
>
> Corregido en `contratos/enums.py` y en el texto que el visor muestra en
> pantalla. El R95p propiamente dicho queda implementado y disponible para el
> documento IEEE, donde si conviene reportarlo porque es lo comparable con la
> literatura.
>
> El defecto es mio: la atribucion salio de esta decision y de ahi se propago al
> contrato y al visor. Es el mismo patron de I-04 —forma valida, contenido
> falso— y esta vez sobrevivio dos semanas porque nadie tenia las dos cantidades
> calculadas para compararlas.

### Contexto

El proyecto estima tres eventos: lluvia intensa, sequia e incendio forestal.
Para etiquetar la variable objetivo hay que fijar a partir de que valor un dia
cuenta como evento. Nadie en el equipo tiene formacion en climatologia, y un
umbral inventado invalida el etiquetado y con el todo el modelo.

### Decision

Los umbrales no los define el equipo, salvo uno:

| Evento | Umbral | Fuente |
|---|---|---|
| Lluvia intensa | Percentiles 95 y 99 del acumulado de 72 h, por distrito. **No es el indice R95p**, ver la nota de revision | Criterio de percentiles extremos del ETCCDI |
| Sequia | SPI a tres meses | McKee, Doesken y Kleist (1993) |
| Incendio forestal | Percentil 90 de la distribucion historica de focos del distrito | Definido por el equipo |

El umbral de incendio, por ser el unico propio, se somete a validacion externa
en la sesion con el Comite Municipal de Emergencias.

### Justificacion

Un umbral publicado es defendible ante el evaluador y ante la Municipalidad sin
que el equipo tenga que sostener una posicion climatologica que no le
corresponde. Ademas hace el resultado comparable con literatura existente.
Quesada-Hernandez, Hidalgo y Alfaro (*Revista de Ciencias Ambientales*, 2020)
muestran que el SPI es el indice con mayor asociacion a impactos registrados en
el Pacifico Norte de Costa Rica, la region a la que pertenece Tilaran.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Fijar umbrales por criterio propio | Indefendible. Cualquier resultado quedaria condicionado a una eleccion arbitraria |
| Pedir umbrales oficiales al IMN | Misma dependencia administrativa que D-01 ya saco de la ruta critica |
| Usar alertas historicas de la CNE como etiqueta | No hay serie publica con granularidad distrital y diaria |

### Consecuencias

Se gana un etiquetado defendible y trazable a fuente. Se pierde ajuste local:
un percentil calculado sobre la serie del distrito depende de la calidad de esa
serie, y si el historico es corto o tiene huecos, el umbral hereda el problema.

Consecuencia abierta y critica: el umbral de incendio solo funciona si el canton
tiene suficientes focos historicos. Es el **riesgo R16**, todavia sin verificar.
Si FIRMS muestra pocos focos entre 2001 y 2025, el modelo de incendio no tiene
casos positivos con que entrenar y el evento sale del alcance.

### Medicion

Pendiente y prioritaria: conteo de focos FIRMS para Tilaran 2001-2025. Cuesta un
dia y puede liberar unas 60 horas de esfuerzo.

---

## D-09 · Tres algoritmos comparados, con SVM descartado

**Estado.** Aceptada
**Fecha.** 2026-08-03 (`1fd614b`)
**Decide.** Alejandro, tras observacion del profesor evaluador

### Contexto

La primera version de la propuesta decia "algoritmos de aprendizaje automatico"
sin nombrarlos. El profesor pidio explicitamente especificar cuales y por que.

### Decision

Tres algoritmos, comparados sobre los mismos pliegues y las mismas
caracteristicas: Regresion Logistica, Random Forest y XGBoost. Se descarta
Maquinas de Vector Soporte.

### Justificacion

Los tres cubren un rango de complejidad creciente: un modelo lineal
interpretable como referencia, un ensamble por agregacion robusto ante ruido, y
un ensamble por refuerzo que suele ganar en datos tabulares. Los tres exponen
importancia de variables, que OE3 exige. Comparar tres y no uno permite
sostener que la eleccion final fue medida y no supuesta.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Maquinas de Vector Soporte | Costo superlineal con el numero de muestras y sin importancia de variables nativa, que OE3 necesita |
| Un solo algoritmo | No permite afirmar que la eleccion fue la mejor disponible |
| Mas de tres | Multiplica el tiempo de validacion por ventana expansiva sin aportar al argumento |

### Consecuencias

Se gana un argumento comparativo solido y trazable. Se pierde tiempo de maquina:
tres algoritmos por tres eventos por N pliegues de validacion. Es la razon por la
que H3.6 pesa 10 puntos.

### Medicion

Pendiente hasta H3.6.

---

## D-10 · F1-macro como metrica principal de contraste

**Estado.** Aceptada
**Fecha.** 2026-08-03 (`1fd614b`)
**Decide.** Alejandro, Lead PM

### Contexto

La hipotesis H1 se decide comparando el modelo contra una linea base
climatologica. Hace falta una sola metrica que decida esa comparacion, fijada de
antemano para no elegir despues la que mas convenga al resultado.

Se anticipa fuerte desbalance de clases: los dias de riesgo alto son raros por
definicion.

### Decision

F1-macro es la metrica principal de contraste, a horizonte de siete dias. Las
demas metricas se reportan, pero no deciden.

### Justificacion

El promedio macro da el mismo peso a cada clase sin importar su frecuencia, asi
que un modelo que acierta siempre "riesgo bajo" no puede ganar por mayoria.
Sokolova y Lapalme (*Information Processing & Management*, vol. 45, 2009)
analizan sistematicamente las metricas de clasificacion y documentan esa
diferencia entre promedio macro y micro.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Exactitud | Con clases desbalanceadas, predecir siempre la mayoritaria da un numero alto y un modelo inutil |
| F1-micro | Domina la clase mayoritaria, mismo problema |
| Elegir la metrica al ver los resultados | Es exactamente lo que hace irrefutable una hipotesis. H1 debe poder salir negativa |

### Consecuencias

Se gana una hipotesis genuinamente refutable: si el modelo no supera a la linea
base en F1-macro, el resultado del proyecto es que no la supera, y eso se
publica. Se pierde la posibilidad de presentar un numero mas favorable.

### Medicion

Pendiente hasta H3.6.

---

## D-11 · `docs/evidencias/` es de escritura libre para el equipo

**Estado.** Aceptada
**Fecha.** 2026-08-05 (`f26036f`)
**Decide.** Alejandro, a solicitud de Luna

### Contexto

La regla de propiedad de archivos declaraba `docs/` completo como carpeta de un
solo dueno. En la practica eso significaba que cada evidencia de cualquier
persona necesitaba una solicitud de cambio aprobada. Con 82 historias, el Lead PM
se convertia en cuello de botella de un tramite que no aporta ningun control
real.

Al revisar la solicitud se detecto ademas que **30 de las 82 historias no tenian
carpeta destino**: las carpetas existentes eran por materia, pero los objetivos
especificos, el documento IEEE, los manuales y las pruebas no son materias.

### Decision

`docs/evidencias/` es de escritura libre para todo el equipo: cada quien sube la
evidencia de sus propias historias a la carpeta que corresponda, sin solicitud
previa. Es la excepcion explicita a la regla de propiedad de `docs/`.

Se crean tres carpetas nuevas: `objetivos/` (OE1 a OE4), `calidad/` (QA) y
`entregables/` (IEEE, MVP, Documentacion).

Siguen requiriendo solicitud de cambio: crear una carpeta nueva de primer nivel,
o modificar la evidencia de otra persona.

### Justificacion

El control que se pierde es nulo: nadie iba a rechazar una evidencia por estar
mal ubicada, y el mapa de destino esta escrito en `docs/evidencias/README.md`.
El costo que se elimina es real: 82 solicitudes de cambio a lo largo del
trimestre, todas por el mismo motivo.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Crear solo `qa/`, como se pidio | Resolvia 2 historias de las 30 sin destino |
| Mantener la solicitud por cada evidencia | Convierte al Lead PM en cuello de botella sin ganancia de control |
| Una carpeta por persona | La evidencia se busca por rubrica al evaluar, no por autor |

### Consecuencias

Se gana velocidad y se elimina un cuello de botella estructural. Se pierde la
garantia automatica de que cada archivo cae en la carpeta correcta: ahora
depende de que cada quien lea el mapa. La revision de Pull Request es el unico
punto donde eso se detecta, asi que el revisor tiene que comprobarlo.

Se nombro `calidad/` en lugar de `qa/` por coherencia: el resto de las carpetas
esta en espanol.

### Medicion

30 historias sin carpeta destino antes del cambio, 0 despues. Conteo hecho sobre
`gestion/issues.csv` cruzando el campo de rubrica contra las carpetas
existentes.

---

## D-12 · Validacion externa con SUS, entrevista y caso retrospectivo

**Estado.** Aceptada
**Fecha.** 2026-08-03 (`1fd614b`)
**Decide.** Alejandro, tras observacion del profesor evaluador

### Contexto

El objetivo especifico OE4 exige validar la utilidad del sistema con usuarios
reales. El profesor pidio definir en que consiste esa validacion antes de
aprobar la propuesta. El equipo no puede evaluar su propio producto.

### Decision

Validacion externa con tres instrumentos, sobre 3 a 5 personas de la
Municipalidad de Tilaran y del Comite Municipal de Emergencias:

1. Escala SUS (Brooke, 1996), con las bandas de interpretacion de Bangor,
   Kortum y Miller (2008).
2. Entrevista semiestructurada.
3. Estudio de caso retrospectivo: contrastar las estimaciones del sistema contra
   eventos que la Municipalidad recuerde haber vivido.

### Justificacion

La escala SUS da un numero comparable con literatura; la entrevista explica ese
numero; el caso retrospectivo es lo unico que puede decir si las estimaciones
tienen sentido para quien conoce el territorio. Los tres juntos cubren
usabilidad, percepcion y validez de contenido.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Solo SUS | Da un puntaje sin explicacion. No dice por que |
| Evaluacion heuristica del propio equipo | No es validacion externa. El equipo no es usuario |
| Encuesta abierta a poblacion general | Sin criterio experto sobre el territorio ni sobre gestion de emergencias |

### Consecuencias

Se gana evidencia de utilidad que ninguna metrica interna puede dar. Se pierde
control del calendario: la sesion depende de la agenda de un tercero y tiene
holgura cero. Por eso hay que escribir al Comite en la semana 6 para una sesion
de la semana 10.

Con 3 a 5 participantes el resultado no es estadisticamente generalizable, y el
documento IEEE debe decirlo asi, sin adornarlo.

### Medicion

Pendiente hasta H9.2.

---

## D-13 · El SNIT es la fuente unica del vocabulario territorial

**Estado.** Aceptada
**Fecha.** 2026-08-11
**Decide.** Alejandro, a partir del hallazgo de Cesar en H1.3

### Contexto

Ningun documento del repositorio decia de donde salen las geometrias distritales
ni los codigos de distrito. Lo unico escrito era un comentario suelto en
`contratos/simulados/datos.py` que mencionaba el SNIT sin enlace, sin capa y sin
formato.

La consecuencia aparecio de inmediato: los codigos de los simulados eran
50501-50508, del canton de Carrillo, en lugar de los oficiales 50801-50808 de
Tilaran. Nadie tenia contra que contrastarlos. Ver incidencia **I-04**.

El codigo de distrito no es un identificador interno: es la clave que une las
mediciones climaticas, los focos de calor, las geometrias del visor y las
estimaciones de riesgo. Si esa clave esta mal, no falla una consulta: falla la
union de todo el sistema, y falla en silencio.

### Decision

El **Sistema Nacional de Informacion Territorial** es la fuente unica del
vocabulario territorial del proyecto.

| Elemento | Valor |
|---|---|
| Servicio | `https://geos.snitcr.go.cr/be/IGN_5_CO/wfs` |
| Capa | `IGN_5_CO:limitedistrital_5k` |
| Entidades en la capa | 494 distritos de todo el pais, medidos al cargar |
| Ambito del proyecto | Los 8 con codigo `508xx` |
| Sistema de referencia | EPSG:4326, como exige `Distrito.geometria` |

Codigos oficiales, congelados como vocabulario cerrado:

    50801 Tilaran            50805 Libano
    50802 Quebrada Grande    50806 Tierras Morenas
    50803 Tronadora          50807 Arenal
    50804 Santa Rosa         50808 Cabeceras

El codigo se compone de provincia, canton y distrito: **5** es Guanacaste, **08**
es Tilaran. Ningun codigo del proyecto se escribe de memoria: se toma de la capa.

### Justificacion

Es el organismo oficial de informacion territorial del pais, publica por
servicios OGC estandar, y es la misma fuente que usaria la Municipalidad. Eso
hace que el resultado sea contrastable por un tercero, que es justamente lo que
pide la validacion externa (D-12).

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Escribir los codigos a mano | Es lo que ya fallo. Produjo I-04 |
| Descargar un shapefile suelto de internet | Sin trazabilidad ni version. No se puede citar en el documento IEEE |
| Usar los limites de OpenStreetMap | No son la division administrativa oficial y pueden diferir de lo que reconoce la Municipalidad |

### Consecuencias

Se gana una clave territorial verificable contra una fuente citable, y un lugar
unico donde mirar cuando haya duda. Se pierde independencia: si el servicio del
SNIT esta caido, H1.3 no avanza. Como mitigacion, las geometrias se cargan una
sola vez a la tabla `geo.distritos` y de ahi en adelante el proyecto no vuelve a
depender del servicio.

Consecuencia de proceso: **H1.1 depende de H1.3**, y el backlog lo tenia como sin
dependencias. `ExtractorClima` recibe un `codigo_distrito`, pero NASA POWER
consulta por coordenada geografica, y esa traduccion necesita las geometrias
oficiales. Queda corregido en `docs/tareas/cesar.md` y en el roadmap.

### Medicion

**Medicion realizada** (H1.3, 13 de agosto de 2026). El filtro
`"CODIGO_CANTON"=508` redujo la capa nacional a los 8 distritos de Tilaran, con
la reduccion hecha en el servidor y no descargando el pais entero. Queda
registrado en `basedatos/ddl/procedencia-geometrias.md` con la URL exacta, la
fecha y las sumas de verificacion.

**Correccion del conteo, 16 de agosto.** Este registro afirmaba **492** entidades,
tomado del listado publicado por el SNIT al redactar la decision. Al ejecutar la
carga, el servicio devolvio **494**: la division territorial cambio despues de
publicarse ese listado. El numero correcto es 494 y se consulta en cada carga en
lugar de fijarse en el codigo, de modo que una reforma territorial futura quede
registrada sola.

El error no tuvo consecuencia —el filtro por canton no depende del total
nacional— pero es un caso mas del hallazgo abierto de la retrospectiva: la
documentacion propia se desfasa y ningun verificador lo detecta.

---

## D-14 · El frontend consume los simulados exportados a JSON estatico

**Estado.** Aceptada
**Fecha.** 2026-08-12
**Decide.** Alejandro, a propuesta de Avril

### Contexto

La regla 4 del metodo de trabajo dice que cada quien trabaje contra los simulados
de `contratos/simulados/` y no espere el codigo de nadie. Para el backend
funciona: son objetos de Python que se importan directamente.

Para el frontend no. `contratos/simulados/datos.py` expone objetos de Python y el
navegador no los puede consumir. El unico puente posible seria la API, y
`backend/api/` no existe hasta H6.1. El roadmap ponia el endpoint de riesgo en la
semana 6, con Avril esperando.

En la practica, la regla que existe para que nadie se bloquee dejaba bloqueada a
una de las cuatro personas durante cuatro semanas.

### Decision

Un script en la carpeta del frontend lee `contratos/simulados/` en modo solo
lectura y escribe archivos estaticos en `frontend/public/simulados/`:

    frontend/herramientas/exportar_simulados.py
      -> frontend/public/simulados/distritos.geojson
      -> frontend/public/simulados/salud.json

El visor los consume por `fetch`, igual que consumira la API real. Cuando exista
la API, el cambio es la URL del `fetch`, en un solo modulo.

Los archivos van en `public/` y no en `src/` a proposito: asi ningun componente
los importa directamente y la migracion no se ramifica por todo el codigo.

### Justificacion

Desbloquea el frontend sin tocar ningun archivo compartido: leer `contratos/` no
es modificarlo, y todo lo generado vive en la carpeta de Avril.

El dato exportado conserva la honestidad del contrato. `poblacion` viaja como
`null` y no como `0`, que es la regla D-07 aplicada al limite de un formato que
ni siquiera tiene `None`. Los ocho codigos de distrito salen del contrato, no
escritos a mano, asi que cuando los contratos cambiaron a v1.2.0 el export
recogio los correctos sin intervencion.

Ademas el archivo se autodenuncia: lleva un campo `advertencia` y cada distrito
un `geometria_simulada: true`. Si alguien abre ese `.geojson` fuera de contexto,
la advertencia viaja con el.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Esperar a la API (H6.1) | Cuatro semanas de bloqueo para una persona, contra la regla que dice que nadie espera |
| Escribir los datos de prueba a mano en JavaScript | Es inventar datos, y se desincroniza del contrato en el primer cambio. Lo confirma I-04: los codigos cambiaron y un JSON escrito a mano no se habria enterado |
| Un servidor de simulacion aparte | Una pieza mas que instalar, arrancar y mantener, para un problema que resuelve un archivo estatico |

### Consecuencias

Se gana paralelismo real para las cuatro personas, no para tres. Se gana tambien
un punto de migracion unico y explicito.

Se pierde: hay un paso manual de regeneracion. Si los contratos cambian y nadie
vuelve a correr el exportador, el frontend trabaja contra datos viejos sin
enterarse. Mitigacion: el `salud.json` exportado lleva `version_contratos`, y el
visor puede compararla contra la que espera. Cuando exista el trabajo de frontend
en el CI, la regeneracion deberia correr ahi.

### Medicion

Ejecutado el 2026-08-12: 8 distritos exportados, codigos 50801 a 50808,
`version_contratos: 1.2.0`, `modo: simulado`. Ninguna poblacion inventada: los
ocho salen con dato ausente.

---

## D-15 · Fuente climatica hibrida: CHIRPS para precipitacion, POWER para el resto

**Estado.** Aceptada · **condicion cumplida y verificada** el 2026-08-18
**Fecha.** 2026-08-16
**Decide.** Alejandro, a partir del hallazgo de Cesar en H1.1
**Revisa parcialmente.** D-01, que declaraba NASA POWER fuente primaria de clima

> La decision se tomo condicionada a repetir sobre CHIRPS el mismo test que
> descarto a POWER. Cesar lo hizo el 18 de agosto y CHIRPS diferencia entre los
> ocho distritos. Ver la seccion de medicion, al final de este registro.

### Contexto

Antes de escribir el extractor de H1.1, Cesar comprobo que devuelve NASA POWER
para dos puntos distintos del canton. Devuelve exactamente lo mismo, hasta el
ultimo decimal, incluida la elevacion:

| Fecha | Punto suroeste | Punto noreste |
|---|---|---|
| 2024-01-01 | 24.40 C · 0.0 mm | 24.40 C · 0.0 mm |
| 2024-01-03 | 24.42 C · 0.04 mm | 24.42 C · 0.04 mm |
| 2024-01-04 | 24.31 C · 0.7 mm | 24.31 C · 0.7 mm |

La causa es la resolucion. POWER sirve MERRA-2 en una malla de 0,5° × 0,625°,
que a la latitud de Tilaran son unos 68 × 55 km. El canton mide 669,23 km²
—medidos en H1.3— y cabe entero dentro de una sola celda.

Dos de los tres eventos se definen sobre precipitacion: la sequia por SPI-3 y la
lluvia intensa por acumulado de 72 h contra los percentiles del propio distrito.
Con una sola celda, esos dos eventos dan el mismo riesgo en los ocho distritos
**por construccion y no por hallazgo**. El visor mostraria ocho poligonos del
mismo color y el modelo no tendria de donde aprender diferencias.

Eso no es una limitacion que se documenta: es responder la pregunta de
investigacion con un "no" antes de recolectar ninguna evidencia. Ver **I-05**.

El incendio no esta afectado: su etiqueta sale de los focos de FIRMS, que son
detecciones puntuales de unos 375 m.

### Decision

Fuente hibrida, por variable y no por proveedor:

| Variable | Fuente | Resolucion | Credenciales |
|---|---|---|---|
| Precipitacion | **CHIRPS** | 0,05° (~5,5 km) | Ninguna, dominio publico |
| Temperatura, humedad, radiacion, viento | NASA POWER | 0,5° × 0,625° | Ninguna |

A 0,05° el canton se reparte en unas 36 celdas y cada distrito abarca varias, de
modo que la precipitacion deja de ser constante entre distritos.

**La decision esta condicionada a una verificacion previa.** Antes de escribir el
extractor hay que repetir sobre CHIRPS el mismo test de dos puntos con el que se
descarto POWER, usando los extremos reales del canton. Si CHIRPS tambien devuelve
valores identicos, no sirve y se vuelve a decidir. Una resolucion nominal mejor no
es prueba de diferenciacion real.

Consecuencia asociada: la ventana de descarga pasa de 2016-2025 a **1991-2025**,
porque la linea base de D-10 se define sobre la normal climatologica 1991-2020 y
con diez anios no se puede calcular como esta declarada. Ambas fuentes llegan a
1981, asi que ninguna lo impide.

### Justificacion

Se cambia solo la variable que esta rota. La precipitacion es la que define los
dos umbrales afectados; temperatura, humedad, radiacion y viento no definen
ninguno, y a escala de un canton pequenio la aproximacion de area se sostiene
mientras quede declarada.

CHIRPS es de dominio publico, no exige registro y publica desde 1981, de modo que
cubre tambien el periodo de la normal climatologica. Mantiene intacta la
independencia del calendario de terceros que motivo D-01.

Nada de esto toca los contratos: `ExtractorClima` ya contempla varias
implementaciones.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Mantener POWER y documentar la limitacion | Responde la pregunta de investigacion por construccion, sin evidencia. Obligaria a replantear OE4 y el titulo del proyecto |
| Cambiar todo a ERA5-Land | Su malla nativa de 9 km no se expone por API: el Climate Data Store entrega 0,1° (~11 km), donde varios distritos siguen compartiendo celda. Ademas exige cuenta con espera, igual que Copernicus para H1.6 |
| Usar las estaciones del IMN | Son mediciones reales y el contrato ya las nombra como segunda implementacion, pero exige averiguar cuantas estaciones hay cerca y con que continuidad en 35 anios. No se descarta como enriquecimiento; se descarta como camino critico, por la misma razon que en D-01 |

### Consecuencias

Se gana diferenciacion espacial real en las dos variables que la necesitan, sin
sumar ninguna credencial ni ninguna espera.

Se pierde homogeneidad: el conjunto de datos pasa a tener dos procedencias con
mallas distintas, y eso hay que declararlo en el documento IEEE y en el reporte de
calidad de H1.5. La temperatura sigue siendo constante entre distritos, asi que
cualquier diferencia que el modelo encuentre entre ellos vendra de la
precipitacion, de los focos de calor o de variables estaticas, nunca de la
temperatura. Esa restriccion condiciona la lectura de la importancia de variables
en H4.1 y del analisis SHAP en H4.2.

Se pierde tambien trabajo previsto: H1.1 se rehace contra otra fuente. El costo
real es cero porque el extractor no llego a escribirse, y eso es merito del orden
en que Cesar trabajo: comprobar la fuente antes de implementarla.

### Medicion

**Realizada por Cesar el 18 de agosto de 2026. La condicion se cumple y la
decision queda firme.** Evidencia completa en
`docs/evidencias/bases-de-datos/H1.1-criterios-aceptacion.md`.

**POWER no diferencia.** Los ocho distritos caen en la misma celda, `(152, 201)`,
y el servicio devuelve el mismo valor y la misma elevacion para los dos distritos
mas separados, Tronadora y Tierras Morenas, a unos 24 km.

**CHIRPS si diferencia.** Los ocho distritos caen en ocho celdas distintas. Datos
reales del 1 al 7 de setiembre de 2024, elegido por ser epoca lluviosa:

| | mm |
|---|---|
| Rango maximo en un solo dia | 13,27 |
| Acumulado semanal minimo, Tronadora | 97,25 |
| Acumulado semanal maximo, Tierras Morenas | 117,04 |
| Diferencia | 20,3 % |

Lo que mas sostiene la decision no es el rango sino que **el orden entre distritos
cambia de un dia a otro**: el dia 3 Tierras Morenas marca 0,00 mm y Arenal 11,54;
el dia 7 se invierte, 34,24 contra 28,75. Un sesgo constante del metodo daria
siempre el mismo orden. Esto es variacion espacial que cambia de signo.

### Correccion del metodo de conteo de celdas

El primer calculo de celdas dio tres para POWER, en contradiccion con la
observacion de que los valores eran identicos. El motivo importa:

- **MERRA-2, que sirve POWER, ancla los centros de celda** en multiplos del paso.
  Una consulta puntual devuelve el punto de malla mas cercano, asi que hay que
  **redondear**, no truncar. Con redondeo los ocho distritos caen en `(-85.0, 10.5)`.
- **CHIRPS ancla los bordes**, y ahi truncar si corresponde.

Aplicar el mismo anclaje a las dos mallas produce un numero que parece razonable y
es falso. `docs/herramientas/verificar_resolucion_fuente.py` incorpora una
autoprueba que compara su logica contra esta observacion y se detiene si no
coinciden.

### Limitacion abierta: el reparto por pentada de CHIRPS

En los cinco primeros dias de la muestra, seis de los ocho distritos dan valores
que son multiplos enteros exactos de una unidad base, y el patron se rompe en el
dia 6. Cinco dias es una pentada, y CHIRPS deriva sus valores diarios repartiendo
totales de pentada.

Es consistente con eso pero **una semana no alcanza para afirmarlo**. Queda
anotado, no dado por cierto.

Importa porque el umbral de lluvia intensa se define sobre acumulados de 72 horas:
si el reparto dentro de la pentada es parcialmente artificial, los percentiles de
72 h heredan ese artificio. No cambia la decision —CHIRPS es la unica fuente que
diferencia— pero hay que verificarlo sobre la serie completa y documentarlo como
limitacion en el documento IEEE antes del modelado, no durante.

### Las dos fuentes no son intercambiables

El 1 de enero de 2024, POWER reporta 0,0 mm en Tronadora y CHIRPS reporta 18,72.
No es error de ninguna: son productos distintos, uno de reanalisis y otro de
satelite combinado con estaciones.

De ahi la regla operativa: la precipitacion viene de CHIRPS **siempre**, y un hueco
de CHIRPS **nunca** se rellena con POWER.

---

## D-16 · La propiedad de una carpeta sigue al trabajo asignado

**Estado.** Aceptada
**Fecha.** 2026-08-16
**Decide.** Alejandro

### Contexto

`backend/senales` figuraba como carpeta de Alejandro desde el arranque. Al
auditar el reparto real aparecio que **las cinco historias de senales son de Luna
y dos de Cesar**: ninguno de los dos podia escribir una linea sin una solicitud de
cambio, archivo por archivo.

Lo mismo en `backend/modelado`, de Alejandro, donde Cesar tiene cuatro historias.

Nadie se habia topado con el problema todavia porque el trabajo de esas dos epicas
no ha empezado. Habria aparecido el dia que Luna abriera H2.1, y habria costado un
dia de ida y vuelta, exactamente como paso con Avril y `frontend/package.json` el
12 de agosto (ver acta 08).

### Decision

**La propiedad de una carpeta sigue al trabajo asignado, no al reves.**

- `backend/senales` pasa a **Luna**, que tiene cinco de sus siete historias.
- `backend/modelado` sigue en Alejandro, con excepcion declarada para las cuatro
  historias de Cesar: H3.3, H3.4, H3.5 y H3.7.
- Cesar escribe en `backend/senales` para H2.5 y H2.6 sin solicitud.
- Alejandro escribe en `backend/senales` para lo que necesiten sus historias de
  modelado, avisando a Luna.

### Justificacion

La regla de un dueno por carpeta existe para evitar que dos personas se pisen el
mismo archivo, no para que quien tiene la historia asignada tenga que pedir
permiso para hacerla. Cuando el reparto de trabajo y el de carpetas no coinciden,
lo que esta mal es el reparto de carpetas.

Se corrige **antes** de que bloquee a alguien y no despues, que es la diferencia
con el caso de Avril.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Dejarlo y resolver por solicitud cuando aparezca | Es garantizar el bloqueo. Ya sabemos que va a pasar y cuando |
| Devolver las historias de E2 y E3 a Alejandro | Elimina el conflicto pero le suma nueve historias sobre dos sprints que ya estan sobrecargados en +19 h y +17 h |
| Quitar la regla de propiedad | Existe por una razon y ha funcionado: nadie ha pisado el trabajo de otro en seis semanas |

### Consecuencias

Se gana que tres personas puedan arrancar E2 y E3 sin pedir permiso. Se pierde
nitidez: dos carpetas dejan de tener un unico dueno y hay que mirar la tabla de
excepciones para saber quien puede escribir donde.

La mitigacion es que la excepcion esta escrita por historia, no en general: fuera
de esas seis historias, la regla sigue valiendo.

### Medicion

Ninguna solicitud de cambio sobre `backend/senales` o `backend/modelado` cuando
arranquen E2 y E3. Si aparece una, la excepcion quedo corta y hay que ampliarla.

---

## D-17 · La precipitacion no se filtra: los indices se calculan sobre la serie cruda

**Estado.** Aceptada
**Fecha.** 2026-08-18
**Decide.** Alejandro, a peticion de Luna en H2.1

### Contexto

La historia H2.1 entrego un filtro de ruido, Savitzky-Golay, que cumple el
contrato y esta bien construido. Al entregarlo, Luna planteo una pregunta que la
historia no resolvia y que no le correspondia resolver:

> Filtrar ruido tiene sentido cuando el ruido es instrumental: temperatura,
> humedad, radiacion, viento. En precipitacion el caso es distinto: un pico de
> lluvia no es ruido, es el evento que el proyecto quiere detectar.

La pregunta pesa porque **dos de los tres eventos del sistema se definen sobre
precipitacion**: sequia por SPI-3 y lluvia intensa por el acumulado de 72 h contra
los percentiles P95 y P99 del propio distrito. Si la serie se suaviza antes de
calcular esos indices, se altera justamente lo que los indices miden.

Y porque, sin decision escrita, la respuesta quedaba determinada por el orden en
que alguien llamara a las funciones. Eso no es una arquitectura: es una
casualidad que despues nadie puede explicar.

Las tres opciones planteadas fueron: no filtrar precipitacion; filtrarla solo
para visualizacion y calcular los indices sobre la serie cruda; o filtrar tambien
para el calculo documentando el efecto.

### Decision

**La precipitacion no se filtra, en ningun punto de la cadena.**

1. El filtro de H2.1 se aplica a **temperatura, humedad relativa, radiacion y
   viento**, que son las variables con ruido instrumental.
2. **SPI (H2.3), percentiles R95p y R99p (H2.7) y el acumulado de 72 h se
   calculan sobre la serie cruda de CHIRPS**, sin paso previo de suavizado.
3. Tampoco se filtra para visualizacion. Si en algun momento hace falta mostrar
   una tendencia suavizada, se hara con un metodo que no produzca valores
   negativos, se etiquetara como serie suavizada en la propia pantalla y no
   alimentara ningun calculo.
4. `filtrar_ruido` no lleva una lista de variables prohibidas por dentro. La
   restriccion vive en quien lo llama, y esta escrita aqui y en la evidencia de
   H2.1: un filtro que decide por su cuenta a que serie se aplica es peor de
   depurar que una regla explicita.

### Justificacion

Se midio en vez de argumentar, porque los dos argumentos suenan razonables y
leyendolos no se puede elegir. La herramienta es
`docs/herramientas/medir_efecto_filtro.py` y los resultados estan abajo, en
Medicion.

Lo que decide no es el corrimiento de los percentiles, aunque sea grande. Es que
**el filtro produce series que no son series de lluvia**:

- **El 12,5 % de los dias sale con precipitacion negativa**, hasta −13,5 mm. No
  es un defecto de la implementacion: los coeficientes de Savitzky-Golay para
  ventana 7 y orden 2 son negativos en los extremos, −0,0952 a cada lado, asi que
  un dia contiguo a un aguacero recibe una contribucion negativa. Es una
  propiedad del metodo, no un error.
- **El 31,6 % de los dias secos, de 0,0 mm, sale con 1 mm o mas.** El ETCCDI
  define R95p y R99p sobre los dias humedos, y el umbral de dia humedo es
  exactamente 1 mm. Filtrar reescribe cual es el denominador del indice.

Un corrimiento de percentil se puede documentar y compensar. Una serie con lluvia
negativa no se puede compensar: rompe el ajuste gamma del que sale el SPI, que
esta definido sobre valores no negativos, y hace que la mitad de la estacion seca
cuente como dias con lluvia.

El corrimiento, ademas, es severo: el P99 de los dias humedos cae un 53,6 %, y de
los 37 dias que la serie cruda clasifica como el 1 % mas extremo, **ninguno
sobrevive** si se conserva el umbral original. Aun comparando cada serie contra su
propio umbral, solo coinciden 16 de 37: el 43 %.

Sobre el acumulado de 72 h el efecto es menor —el P99 baja un 11,7 % y coincide el
78 % de los dias— y tiene explicacion: acumular ya es suavizar. Esa observacion no
cambia la decision, la refuerza. El indice del proyecto **ya incorpora el
promediado que se necesita**; agregar un filtro antes es aplicarlo dos veces.

Hay un ultimo resultado que conviene dejar escrito porque cierra la discusion sin
apelar a preferencias: con ventana 3 y polinomio de orden 2 el filtro **no cambia
nada**, porque con tres puntos una parabola pasa exactamente por los tres. La
unica configuracion que no dana la precipitacion es aquella en la que el filtro no
hace nada.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Filtrar tambien para el calculo, documentando el efecto | Es la opcion 3 de Luna. Documentar que el P99 baja un 53,6 % no lo arregla: los umbrales del proyecto quedan definidos sobre una serie que contiene lluvia negativa. Se estaria publicando un indice estandar, R99p del ETCCDI, calculado sobre una entrada que el estandar no admite |
| Filtrar solo para visualizacion | Es la opcion 2, la que Luna prefiere y la que yo prefería antes de medir. Se cae por lo mismo: la serie que se mostraria en pantalla tiene 12,5 % de dias negativos. Habria que recortarlos a cero, y ese recorte es una segunda transformacion no declarada que ademas rompe la conservacion de masa. Un grafico que dibuja lluvia que no cayo es peor que uno con ruido |
| Usar una media movil en lugar de Savitzky-Golay para precipitacion | La media movil no produce negativos, pero aplasta los maximos aun mas: es exactamente lo que H2.1 midio y descarto, con el pico conservando un 20 % de su amplitud contra el 48,6 % de Savitzky-Golay. Cambia un defecto por otro peor |
| Filtrar solo la parte de la serie sin eventos extremos | Requiere decidir que es extremo antes de calcular los umbrales que definen lo extremo. Es circular |
| Dejarlo sin decidir y que cada historia elija | Es lo que habia. La decision quedaria implicita en el orden de las llamadas y cambiaria sola cuando alguien reordenara el codigo |

### Consecuencias

**Se gana** que los tres indices de precipitacion se calculen sobre el dato tal
como lo entrega la fuente, y que el resultado sea comparable con la literatura que
usa las mismas definiciones. Es lo que permite citar el ETCCDI sin asterisco.

**Se pierde** el suavizado en las variables donde quiza si habria ayudado y ahora
no se aplica por precaucion. No se pierde mucho: ninguno de los tres eventos se
define sobre temperatura, humedad, radiacion o viento; entran al modelo como
variables predictoras, donde el ruido lo absorbe el propio algoritmo.

**Queda una asimetria que hay que declarar en el documento IEEE:** el proyecto
implementa un filtro de senales, lo justifica y lo prueba, y luego lo aplica a
cuatro variables y no a la que define dos de los tres eventos. Es la conclusion
correcta, pero se ve rara si no se explica. La explicacion es que la rubrica de
Senales y Sistemas evalua el tratamiento de la senal, y **decidir con medicion no
aplicar una tecnica es tratamiento de la senal**, no ausencia de el.

**H2.1 no se reabre.** El filtro esta bien construido y su justificacion se
sostiene para las variables a las que aplica. Lo que cambia es su alcance, y eso
se anota en la matriz de trazabilidad, no en la historia.

**H2.3 y H2.7 quedan desbloqueadas** con la regla explicita: entrada cruda.

### Medicion

Se comprueba con dos cosas, y las dos tienen que dar.

**Primero, la medicion misma, repetida sobre datos reales.** Lo de arriba se midio
sobre una serie sintetica de 35 anios con el regimen de Guanacaste, porque H1.1
sigue abierta y no hay series descargadas. **Cuando CHIRPS entregue las series de
Tilaran hay que volver a correr `medir_efecto_filtro.py` sobre ellas.** La
decision se sostiene si el signo y el orden de magnitud se conservan; si sobre
datos reales el filtro no produjera negativos ni mojara dias secos, hay que
reabrir este registro.

El resultado sobre la serie sintetica, con la ventana por defecto de 7 muestras:

    P99 de los dias humedos      crudo 54,91 mm    filtrado 25,50 mm    -53,6 %
    P95 de los dias humedos      crudo 32,30 mm    filtrado 17,93 mm    -44,5 %
    P99 del acumulado de 72 h    crudo 64,82 mm    filtrado 57,21 mm    -11,7 %

    dias con valor negativo               1594 de 12784   12,47 %   minimo -13,47 mm
    dias secos que pasan a humedos        2610 de  8255   31,62 %
    masa total                            sin cambio, -0,00 %

Verificado con tres semillas y cuatro ventanas: el signo y el orden de magnitud se
conservan en las doce combinaciones.

**Segundo, que la regla se cumpla en el codigo.** Cuando H2.3 y H2.7 esten
implementadas, ninguna debe llamar a `filtrar_ruido` sobre la serie de
precipitacion. Si aparece esa llamada, o la regla no se comunico o hace falta un
verificador que la compruebe, como el de documentacion desfasada.

La masa total conservada sirve de control de la propia herramienta: Savitzky-Golay
preserva la suma en el interior de la serie, y que la medicion lo reproduzca
indica que el script no esta introduciendo su propio error.

---

## D-18 · El nombre de un poblado no identifica a un distrito

**Estado.** Aceptada
**Fecha.** 2026-08-18
**Decide.** Alejandro, a partir del hallazgo de Luna en H4.3

### Contexto

Al construir el catalogo de eventos historicos, Luna encontro que **en Tilaran hay
dos lugares llamados Rio Chiquito y no pertenecen al mismo distrito**: el poblado
principal es del distrito central, 50801, y Rio Chiquito Abajo se asocia a
Tronadora, 50803.

Las fuentes historicas —fichas de DesInventar, partes de la CNE, prensa— describen
donde ocurrio un evento **por el nombre del lugar**, no por el codigo del
distrito. Cualquier proceso que traduzca ese nombre a un distrito tiene que
resolver la ambiguedad, y si la resuelve tomando la primera coincidencia produce
un error que no se ve: la fila queda completa, con un codigo valido, asignada al
distrito equivocado.

Es la misma familia que la incidencia **I-04**, donde los codigos de distrito de
los contratos no eran los oficiales. En los dos casos el dato tiene la forma
correcta y el contenido falso, y en los dos el sistema no puede detectarlo solo.

Sin registro, esto se olvida. Luna lo resolvio a mano en H4.3 mirando ficha por
ficha; el proximo que cargue eventos historicos, o que geocodifique un reporte
ciudadano, no va a saber que el problema existe.

### Decision

**El nombre de un poblado no es clave para asignar distrito. Nunca.**

1. La unica clave territorial valida es el **codigo de distrito de cinco digitos**
   de la division territorial administrativa, con el SNIT como fuente unica
   (**D-13**).
2. Cuando una fuente historica da un nombre de lugar y tambien un distrito, **manda
   el distrito que declara la fuente**, aunque el nombre sugiera otro. Es lo que
   Luna hizo en H4.3.
3. Cuando una fuente da solo un nombre y ese nombre es ambiguo dentro del canton,
   la fila **no se asigna**: el distrito queda en `None` y se documenta el motivo.
   No se elige la coincidencia mas probable.
4. Ningun proceso automatico asigna distrito por nombre sin registrar la
   ambiguedad. Si se implementa una traduccion de nombre a codigo, tiene que
   devolver la lista de candidatos, no uno solo.

### Justificacion

La regla se deriva de **D-07**: la ausencia de dato se representa como `None`,
nunca como un valor por defecto. Un distrito adivinado a partir de un nombre
ambiguo es exactamente un valor por defecto, con el agravante de que parece un
dato medido.

El costo de equivocarse no es simetrico. Dejar la fila sin distrito cuesta una
fila menos en el catalogo, y el validador ya lo reporta como aviso. Asignarla mal
cuesta que en H4.4 el contraste cuente un fallo del modelo donde el modelo acerto,
o al reves. Ese error contamina la respuesta a la pregunta de investigacion y no
deja rastro.

El caso concreto lo demuestra: la ficha `1973-85` de DesInventar es un
deslizamiento cuya observacion dice "Epicentro en Rio Chiquito". Mapeada por
nombre habria entrado al catalogo de lluvia intensa. Es el terremoto de Tilaran
del 14 de abril de 1973. Un sismo contado como evento de lluvia, en el distrito
que el nombre sugiere y no en el que la ficha declara: dos errores de la misma
linea.

Los toponimos no son identificadores. Se repiten dentro de un mismo canton, se
escriben de varias formas, cambian con el tiempo y no respetan los limites
administrativos, que es justamente lo que los hace utiles para hablar y malos para
indexar.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Resolver por el candidato mas poblado o mas conocido | Es una heuristica plausible que acierta la mayoria de las veces, y por eso es peligrosa: los errores que produce son pocos y no se distinguen de los aciertos |
| Construir un diccionario de toponimos a distritos | Util, y probablemente haga falta. Pero no resuelve el caso ambiguo, que es este: los dos Rio Chiquito son entradas legitimas del diccionario. Un diccionario sin marca de ambiguedad esconde el problema mejor que la ausencia de diccionario |
| Asignar el evento a los dos distritos candidatos | Duplica el evento. En H4.4 contaria dos veces y sesgaria el contraste hacia el evento que resulto ambiguo |
| Tratarlo como incidencia y no como decision | Ya existe el hallazgo en la evidencia de H4.3. Lo que faltaba es la regla, que es lo que se aplica a las historias que todavia no se escribieron: H4.4, H7.3 y cualquier ingreso de reportes ciudadanos |

### Consecuencias

**Se gana** que el catalogo y todo lo que se construya sobre el tengan una regla
unica y verificable, y que las filas sin distrito sean visibles en lugar de estar
disueltas entre las asignadas.

**Se pierde** cobertura. Habra eventos historicos reales que no entren al catalogo
porque su fuente solo da un nombre ambiguo. Es una perdida aceptable y ya
declarada: el catalogo de H4.3 documenta su sesgo, y este es un sesgo mas del
mismo tipo, de registro y no de ocurrencia.

**Impacto en H4.4.** El contraste tiene que separar tres cosas y no dos: el modelo
acerto, el modelo fallo, y no habia con que comparar. La tercera no es un fallo
del modelo y no puede contarse como tal.

**Impacto en el visor.** Si en algun momento se busca un distrito por nombre de
lugar, la interfaz tiene que mostrar los candidatos y dejar elegir, no resolver
sola.

### Medicion

Ninguna fila del catalogo de eventos con distrito asignado a partir del nombre del
poblado cuando la ficha declara otro. Se comprueba sobre
`docs/investigacion/catalogo-eventos.csv`, que ya trae la procedencia de cada fila
en `catalogo-eventos.md`.

En H4.3 la regla se aplico y el resultado esta: la ficha `1973-85` no entro al
catalogo de lluvia intensa, y las fichas con toponimo ambiguo conservan el
distrito de la ficha y no el que sugiere el nombre.

Si aparece un proceso automatico de asignacion por nombre, debe traer su propia
prueba con el caso de Rio Chiquito: dos candidatos, ninguno elegido en solitario.

---

## D-19 · El SPI se ajusta por mes calendario: contratos a v1.3.0

**Estado.** Aceptada
**Fecha.** 2026-08-18
**Decide.** Alejandro, a partir de la solicitud SC-02 de Luna

### Contexto

Al implementar H2.3, Luna encontro que **el contrato no permite calcular el SPI
correctamente** y lo reporto en vez de rodearlo.

El SPI de McKee, Doesken y Kleist (1993) ajusta una distribucion gamma **por cada
mes calendario**: los eneros contra la distribucion historica de los eneros, los
febreros contra los febreros. Eso es lo que lo convierte en un indice de
**anomalia** y no en una descripcion de la estacionalidad.

La firma congelada, `spi(precipitacion, ventana_meses)`, no recibe fechas. Sin
saber a que mes pertenece cada posicion, la implementacion solo puede ajustar una
distribucion unica para toda la serie.

En un clima con estacion seca marcada eso no es una perdida de precision: cambia
lo que el indice mide.

### Decision

**`ProcesadorSenales.spi` recibe `meses: list[int] | None = None`.** Contratos
suben a **v1.3.0**.

1. El parametro va **al final y con valor por defecto**, asi que el cambio es
   aditivo y ninguna llamada existente se rompe.
2. Cuando llega, la distribucion se ajusta por separado para cada mes del anio.
3. Cuando llega en `None`, quien implementa **debe documentar que el resultado no
   es un SPI de anomalia**. No es un modo equivalente: es un modo degradado y
   tiene que decirlo.
4. El simulado lo acepta y lo ignora, porque calcula una puntuacion z y no ajusta
   ninguna distribucion. Valida el largo igual, para que un error de
   correspondencia salga en el simulado y no tres historias despues.
5. **H3.0 no usa el SPI para etiquetar hasta que la implementacion acepte el
   parametro.**

### Justificacion

Se decidio con la medicion de `docs/herramientas/medir_spi_por_mes.py`, sobre 35
anios de serie sintetica con el regimen del Pacifico Norte, SPI-3. La reproduje en
una copia limpia del repositorio y da lo mismo:

    SPI medio por estacion (deberia rondar 0 en las dos)
                             ajuste unico   ajuste por mes
      estacion seca                 -0,84            -0,00
      estacion lluviosa              0,60            -0,00

**Un indice de anomalia cuya media es -0,84 en una estacion y +0,60 en la otra no
esta midiendo anomalia.** Eso se lee sin recurrir a ninguna autoridad.

El dato que cierra la discusion es otro: de los **99 meses que el ajuste unico
declara en sequia, los 99 caen en estacion seca**. El indice no detecta sequia,
detecta que es verano. Un sistema de alerta construido sobre eso declararia sequia
todos los anios, en los mismos meses, lloviera lo que lloviera.

La correlacion entre ambos metodos es **0,425**, que impide el argumento facil de
"es lo mismo con menos precision". De los 73 episodios que detecta el ajuste por
mes, el unico coincide en 21: se pierden 52 sequias reales y se declaran 78 que no
lo son.

**Por que importa para el modelado, que es donde se paga.** Con ajuste unico la
etiqueta de sequia queda correlacionada con el mes calendario. Un modelo entrenado
sobre ella aprenderia el calendario en lugar del clima **y en la evaluacion se
veria bien**, porque la estacion seca es predecible. Es la misma familia de
resultado enganoso que la fuga temporal que **D-04** prohibe, y por el mismo
motivo: la metrica sale alta y no significa lo que parece.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Inferir el mes desde la posicion, suponiendo que la serie empieza en enero | La suposicion no esta en el contrato, no se puede verificar desde dentro de la funcion, y una serie que empezara en otro mes quedaria mal calculada **sin ningun sintoma visible**. Es exactamente el modo de fallo de I-04 |
| Recibir fechas completas en vez del mes | Mas informacion de la que el calculo necesita. El SPI solo distingue por mes del anio; pasar fechas invita a que alguien las use para otra cosa dentro de la funcion |
| Dejarlo como esta y documentar la limitacion | Es lo que hizo H2.3 provisionalmente, y estuvo bien como medida temporal. Como decision permanente significa publicar un indice que lleva el nombre de un estandar y no cumple su definicion |
| Cambiar de indice, a percentiles de precipitacion mensual | Resuelve la estacionalidad pero pierde comparabilidad con la literatura, que es la razon por la que se eligio el SPI en D-08 |
| Un parametro obligatorio en vez de opcional | Rompe las llamadas existentes y obligaria a tocar el simulado y las pruebas de otras historias en el mismo cambio. Se prefiere aditivo |

### Consecuencias

**Se gana** un SPI que significa lo que su nombre dice, comparable con la
literatura, y una etiqueta de sequia que no arrastra el calendario al modelo.

**Se pierde** la congelacion del contrato, que era una regla del proyecto y ya se
habia roto una vez, en v1.2.0 por I-04. Dos cambios en quince dias sobre algo
declarado congelado es un patron que hay que mirar: en los dos casos el defecto
estaba en el contrato original y lo encontro quien fue a implementarlo.

**La leccion no es "congelar mejor", es que un contrato escrito antes de
implementar nada se equivoca.** Lo que funciono las dos veces fue que quien lo
encontro lo reporto en vez de rodearlo, y que el cambio fue aditivo.

**Cuesta una hora de trabajo** a Luna, segun su propia estimacion: el ajuste
gamma, la correccion de ceros y el tratamiento de huecos no cambian; solo se hace
el ajuste una vez por mes en lugar de una para toda la serie.

**H2.3 no se reabre.** El codigo esta bien construido y probado. Lo que cambia es
el alcance de lo que puede calcular, y eso queda anotado en la matriz.

**Deuda de verificacion declarada.** La atribucion del ajuste por mes calendario a
la guia operativa WMO-No. 1090 **no se pudo confirmar textualmente**, ni por mi ni
por Luna, y se retiro de la solicitud. La decision no depende de ella: se sostiene
sobre la medicion. Antes de que la afirmacion pase al documento IEEE hay que
verificarla contra el texto original, que son 16 paginas.

### Medicion

Se comprueba con tres cosas.

**Primero, que el contrato lo exija.** `contratos/verificar.py` incorpora dos
comprobaciones nuevas: que `spi` acepte el mes calendario de cada posicion, y que
rechace una lista de meses de otro largo. Son las comprobaciones 32 y 33.

**Segundo, que la implementacion lo use.** Cuando H2.3 se actualice, repetir
`medir_spi_por_mes.py` contra la implementacion real: la media por estacion tiene
que rondar cero en las dos, y la proporcion de sequias en estacion seca tiene que
bajar del 100 % a algo cercano al reparto natural del calendario.

**Tercero, sobre datos reales.** La medicion es sobre serie sintetica, porque H1.1
sigue abierta. Cuando existan las series de CHIRPS hay que repetirla. Si sobre
datos reales el ajuste unico no separara las estaciones, este registro se reabre.

---

## D-20 · La matriz de trazabilidad es un artefacto derivado, no un documento

**Estado.** Aceptada
**Fecha.** 2026-08-18
**Decide.** Alejandro, por el acuerdo A16.1 del acta de revision

### Contexto

`docs/05-matriz-trazabilidad.md` era el archivo mas conflictivo del repositorio.
Lo tocaban las cuatro personas, casi siempre sobre el mismo bloque de filas, y
**ninguna herramienta lo comprobaba**.

En dos dias produjo tres conflictos de fusion, tres duenos desfasados —H2.2, H2.3 y
H8.2— y cuatro historias cerradas sin fila —H6.4, H8.5, H8.6 y H10.8—.

El defecto de los duenos no fue cosmetico. Luna leyo la matriz, vio dos historias
suyas a nombre de otro y las dio por ajenas: reporto que se quedaba sin trabajo
disponible cuando tenia tres historias libres. **Un dia perdido por un documento
que mentia.**

Ninguno de los diez se detecto leyendo. Aparecieron al auditar, cuatro dias
despues del primero.

### Decision

**La matriz deja de escribirse a mano.** Se genera con
`docs/herramientas/generar_matriz.py` desde cuatro fuentes, y **ninguna de las
cuatro es compartida entre dos personas**:

| Fuente | Que aporta | Quien la edita |
|---|---|---|
| `docs/backlog.csv` | Dueno y rubrica | Alejandro |
| `docs/tareas/<persona>.md` | Si la historia esta cerrada | Su dueno, solo su archivo |
| `docs/trazabilidad.csv` | Requisito, modulo y prueba | Alejandro |
| `docs/evidencias/` | El archivo de evidencia, buscado en disco | Su dueno |

Quien cierra una historia marca `[x]` en su propio archivo y sube su evidencia. La
fila aparece sola.

`verificar_estado.py` comprueba en el CI que el archivo corresponda a sus fuentes,
igual que `ruff format --check`. Editarlo a mano pasa a ser un defecto detectable.

**Un conflicto de fusion sobre la matriz ya no se fusiona**, se regenera:

    git checkout --ours docs/05-matriz-trazabilidad.md
    python docs/herramientas/generar_matriz.py

### Justificacion

El problema no era falta de cuidado, y por eso pedir mas cuidado no lo resolvia.
Era estructural: **un archivo que cuatro personas editan a mano, sobre las mismas
lineas, sin ninguna comprobacion.** Con esas tres condiciones el desfase es cuestion
de tiempo, y las tres se cumplian.

Se elimina una de las tres. Las otras dos siguen —sigue siendo un archivo unico y
confirmado— pero ya no hay edicion manual que se desincronice ni cambio que pase
sin comprobar.

Es el mismo patron que el proyecto ya aplico tres veces con resultado: **una sola
fuente, vistas derivadas, y una maquina que comprueba que coincidan.** Se uso para
las cifras de la documentacion, para el conteo de historias cerradas y para la
version de contratos, que hasta esta semana estaba escrita a mano en
`salud_simulada()`.

La migracion se verifico comparando la tabla generada contra la escrita a mano:
**las 35 filas salen identicas**, incluidas las notas de estado con matiz.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Pedir mas cuidado al editarla | Es lo que se venia haciendo. Fallo diez veces en dos dias, y ninguna se detecto leyendo |
| Partirla en un archivo por epica | Reduce los choques pero no los elimina, y multiplica por trece los archivos que el evaluador tiene que abrir para ver la trazabilidad |
| Dejar de confirmarla y generarla solo en el CI | Elimina los conflictos por completo. Se descarto porque la rubrica la evalua **como documento**: tiene que poder leerse en el repositorio sin ejecutar nada |
| Agregar una columna de estado al backlog | Crearia un cuarto lugar que declara lo mismo, sobre el archivo que mas personas tocan. Es el problema, no la solucion |
| Un controlador de fusion de git para ese archivo | Resuelve el sintoma sin resolver el desfase de contenido, que es lo que causo el dano real |

### Consecuencias

**Se gana** que la matriz no pueda contradecir a sus fuentes, que cerrar una
historia sea marcar `[x]` en el propio archivo, y que los conflictos que queden se
resuelvan con un comando en lugar de comparando filas.

**Se pierde** la posibilidad de escribir en la matriz algo que no este en ninguna
fuente. Es deliberado: cada columna tiene ahora un lugar declarado de donde sale.

**Aparece un archivo compartido nuevo**, `docs/trazabilidad.csv`, con requisito,
modulo y prueba. Entra a la lista de archivos que se modifican por solicitud de
cambio. Es un archivo mas que gobernar, y a cambio saca a tres personas de la
matriz.

**El pipeline pasa de siete a ocho controles.**

### Medicion

Ningun conflicto de fusion sobre la matriz que haya que resolver comparando filas.
Si aparece uno, se resuelve regenerando; si alguien lo fusiona a mano y el
resultado no corresponde a las fuentes, el CI lo detecta.

Ningun dueno ni estado desfasado en la matriz, porque ya no puede haberlo: salen
del backlog y de los archivos de tareas.

Se revisa al cierre del Sprint 2. Si en ese periodo aparece un desfase de la matriz
que el verificador no haya detectado, la comprobacion quedo corta.

---

## Como se agrega un registro

Copiar `docs/plantillas/plantilla-adr.md`, numerar con el siguiente `D-NN`,
agregar la fila al indice de arriba y abrir el Pull Request. Una decision que
sustituye a otra no la borra: la anterior pasa a estado
**Sustituida por D-NN** y se queda donde esta.
