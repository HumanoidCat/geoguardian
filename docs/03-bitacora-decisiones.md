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
| D-08 | Umbrales de riesgo tomados de estandares publicados | Aceptada | 2026-08-03 |
| D-09 | Tres algoritmos comparados, con SVM descartado | Aceptada | 2026-08-03 |
| D-10 | F1-macro como metrica principal de contraste | Aceptada | 2026-08-03 |
| D-11 | `docs/evidencias/` es de escritura libre para el equipo | Aceptada | 2026-08-05 |
| D-12 | Validacion externa con SUS, entrevista y caso retrospectivo | Aceptada | 2026-08-03 |

---

## D-01 · Fuentes globales abiertas como base primaria

**Estado.** Aceptada
**Fecha.** 2026-08-03 (`1fd614b`)
**Decide.** Alejandro, Lead PM

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

**Estado.** Aceptada
**Fecha.** 2026-08-03 (`1fd614b`)
**Decide.** Alejandro, Lead PM

### Contexto

El proyecto estima tres eventos: lluvia intensa, sequia e incendio forestal.
Para etiquetar la variable objetivo hay que fijar a partir de que valor un dia
cuenta como evento. Nadie en el equipo tiene formacion en climatologia, y un
umbral inventado invalida el etiquetado y con el todo el modelo.

### Decision

Los umbrales no los define el equipo, salvo uno:

| Evento | Umbral | Fuente |
|---|---|---|
| Lluvia intensa | Percentiles R95p y R99p sobre precipitacion acumulada de 72 h | Indices ETCCDI, adoptados por la OMM |
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

## Como se agrega un registro

Copiar `docs/plantillas/plantilla-adr.md`, numerar con el siguiente `D-NN`,
agregar la fila al indice de arriba y abrir el Pull Request. Una decision que
sustituye a otra no la borra: la anterior pasa a estado
**Sustituida por D-NN** y se queda donde esta.
