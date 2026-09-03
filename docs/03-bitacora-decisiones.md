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
| D-08 | Umbrales de riesgo tomados de estandares publicados | Aceptada · revisada por D-19 · umbral de incendio sustituido por D-25 | 2026-08-03 |
| D-09 | Tres algoritmos comparados, con SVM descartado | Aceptada | 2026-08-03 |
| D-10 | F1-macro como metrica principal de contraste | Aceptada | 2026-08-03 |
| D-11 | `docs/evidencias/` es de escritura libre para el equipo | Aceptada | 2026-08-05 |
| D-12 | Validacion externa con SUS, entrevista y caso retrospectivo | Aceptada | 2026-08-03 |
| D-13 | El SNIT es la fuente unica del vocabulario territorial | Aceptada | 2026-08-11 |
| D-14 | El frontend consume los simulados exportados a JSON estatico | Aceptada · revisada por D-23 | 2026-08-12 |
| D-15 | Fuente climatica hibrida: CHIRPS para precipitacion, POWER para el resto | Aceptada · revisada por D-26 | 2026-08-16 |
| D-16 | La propiedad de una carpeta sigue al trabajo asignado | Aceptada | 2026-08-16 |
| D-17 | La precipitacion no se filtra: los indices se calculan sobre la serie cruda | Aceptada | 2026-08-18 |
| D-18 | El nombre de un poblado no identifica a un distrito | Aceptada | 2026-08-18 |
| D-19 | El SPI se ajusta por mes calendario: contratos a v1.3.0 | Aceptada | 2026-08-18 |
| D-20 | La matriz de trazabilidad es un artefacto derivado, no un documento | Aceptada | 2026-08-18 |
| D-21 | `probabilidad` es P(nivel = alto), no la confianza del modelo | Aceptada | 2026-08-20 |
| D-22 | H1.4 se reduce: no hay faltantes que imputar en las series climaticas | Aceptada | 2026-08-20 |
| D-23 | El visor negocia su origen una sola vez y degrada al respaldo declarandolo | Aceptada | 2026-08-20 |
| D-24 | El modelo de estimacion es una constante: se empieza a medir antes de corregirlo | Aceptada | 2026-08-20 |
| D-25 | El incendio es binario y se acota a los tres distritos con senal | Aceptada | 2026-08-20 |
| D-26 | El sistema declara latencia por evento, no promete tiempo real | Aceptada | 2026-08-23 |
| D-27 | El alcance diferido se registra con condicion de reactivacion medible | Aceptada | 2026-08-24 |
| D-28 | Se retira el mapa de calor: interpola donde no hay medicion | **Revertida por D-30** · partia de un hecho falso | 2026-08-24 |
| D-29 | El dataset se versiona por manifiesto en el repositorio y archivo fuera | Aceptada · **revisada por D-31** | 2026-08-26 |
| D-30 | El mapa de calor vuelve, recortado contra los poligonos | Aceptada · revierte D-28 | 2026-08-27 |
| D-31 | El recibo de carga y la version del dataset son dos artefactos | Aceptada · revisa D-29 | 2026-08-27 |

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

**Estado.** Aceptada · **alcance precisado el 2026-08-20**
**Fecha.** 2026-08-03 (`1fd614b`)
**Decide.** Alejandro, con aprobacion del profesor de Arquitectura de Software

> ### Precision del 2026-08-20: esta decision es del trimestre, no del producto
>
> Al preguntar el PM como se despliega el sistema aparecio que **la palabra
> "produccion" de esta decision significa un espacio de nombres dentro de un
> cluster que corre en una laptop**. `infra/k8s/local/produccion/`. No hay dominio,
> no hay servidor y **el sistema no es accesible desde fuera del equipo**.
>
> Eso es coherente con lo decidido, esta bien registrado en la evidencia de H8.6 y
> en el encabezado de `docker-compose.yml`, y para la rubrica de CI/CD alcanza:
> lo que se evalua es que el pipeline exista y despliegue, y un pipeline que
> despliega a k3d despliega.
>
> **Pero contradice el proposito del producto, y conviene que quede escrito.**
> GeoGuardian existe para que el Comite Municipal de Emergencias y la poblacion
> del canton puedan **consultar el riesgo del dia**. Un sistema de informacion
> cuyo unico modo de consulta es que alguien lleve una computadora no cumple ese
> proposito, por bien construido que este.
>
> **El estado objetivo es un sistema publicado y actualizandose solo.** La
> restriccion es de tiempo y de presupuesto de un trimestre, no de diseno: la
> arquitectura ya lo permite. La API no guarda estado, el ETL es idempotente
> (H1.1, CA-11) y el visor habla con la API por una ruta relativa a proposito
> (D-23), de modo que funciona igual detras de cualquier servidor.
>
> **Lo que se hace este trimestre.** La historia **H11.5** publica el visor como
> sitio estatico, que es posible sin backend gracias a la degradacion de D-23, y
> declara en pantalla que los datos son simulados. Da una URL real para H9.2 y
> para la defensa sin abrir la puerta a operar infraestructura.
>
> **Lo que queda como trabajo futuro, en este orden.** Publicar la API y la base;
> automatizar la ingesta diaria para que el dato se actualice sin intervencion; y
> recien entonces retirar el aviso de datos simulados. Los tres pasos dependen de
> que exista un modelo entrenado: publicar antes seria publicar un mapa que no
> estima nada.
>
> **Si el equipo termina con holgura, esto se hace.** No es un extra: es lo que
> convierte el proyecto en la herramienta que dice ser.

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

**Estado.** Aceptada · **revisada el 2026-08-18 y el 2026-08-20**, ver las notas
**Fecha.** 2026-08-03 (`1fd614b`)
**Decide.** Alejandro, Lead PM

> **Nota de revision del 2026-08-20.** El umbral de incendio de esta decision
> **queda sustituido por D-25**, y el riesgo R16 que ella misma declaro como
> "pendiente y prioritaria" **queda cerrado con medicion**.
>
> Esta decision fijo el corte de incendio en el percentil 90 del conteo de focos
> por ventana de 7 dias, declarandolo criterio del equipo por no haber estandar
> equivalente. Cesar lo midio el 20 de agosto: **P90 = 0,0 en los ocho
> distritos**, porque entre el 97 % y el 99,9 % de las ventanas no tienen ningun
> foco. La condicion intermedia `1 <= n <= 0` esta vacia y la regla nunca produjo
> tres clases.
>
> Lo que confirma esta decision es su propio principio de fondo: los umbrales que
> vienen de un estandar publicado —SPI-3 de McKee, percentiles extremos del
> ETCCDI— aguantaron la medicion. **El unico que se cayo es el unico que puso el
> equipo**, y se cayo porque nadie comprobo que sus tres clases fueran
> alcanzables sobre el dato real.
>
> Ver **SC-05** y **D-25**.

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

**Estado.** Aceptada · **revisada por D-23 el 2026-08-20**
**Fecha.** 2026-08-12
**Decide.** Alejandro, a propuesta de Avril

> **Que cambio.** H6.6 sustituyo el origen por la API, que era lo que esta
> decision preveia. Los archivos estaticos no se borran: pasan de ser el origen a
> ser el respaldo cuando la API no responde. Y la frase *"el cambio es la URL del
> `fetch`"* resulto optimista: hubo que traducir la forma. Todo cupo en el mismo
> modulo, que es lo que esta decision existia para conseguir. Ver **D-23**.

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

**Estado.** Aceptada · **condicion cumplida y verificada** el 2026-08-18 ·
**revisada por D-26** el 2026-08-23
**Fecha.** 2026-08-16
**Decide.** Alejandro, a partir del hallazgo de Cesar en H1.1
**Revisa parcialmente.** D-01, que declaraba NASA POWER fuente primaria de clima

> **Nota de revision del 2026-08-23.** La eleccion se mantiene, y por las mismas
> razones. Lo que aparecio al medir la latencia son **dos propiedades de estas
> fuentes que esta decision no conocia**, y que no cambian la eleccion pero si lo
> que se puede prometer con ella:
>
> **CHIRPS tiene dos productos, no uno.** El final llega en la tercera semana del
> mes siguiente —de 21 a 51 dias— y el rapido es **"GTS and Mexico only"**, o sea
> que para Costa Rica se queda sin la correccion por estaciones que es justamente
> lo que esta decision valoro de CHIRPS.
>
> **POWER cambia de modelo a mitad de la serie.** El historico es MERRA-2; los
> ultimos meses son **GEOS-5.12.4 FP-IT**. Esta decision, e I-05, hablan de
> MERRA-2 como si fuera toda la serie. Cuanto difieren no esta medido.
>
> Ver **D-26** y `docs/14-latencia-de-las-fuentes.md`.

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

> **Deuda pagada el 2026-08-22.** Luna leyo las 16 paginas. **La atribucion es
> correcta y estaba en otra seccion**: la 5.1.1 describe el SPI de 1 mes como la
> comparacion del total de noviembre de un anio contra los totales de noviembre de
> todos los anios del registro, la 5.1.2 dice lo equivalente para el trimestre y la
> 5.1.5 para los doce meses. La buscabamos en la seccion 6, que es donde no esta.
>
> Se restituye **acotada**: la guia es descriptiva, no imperativa. Nunca escribe
> "ajustese por mes calendario", pero define el conjunto de comparacion como el
> mismo mes a traves de los anios, que es el fundamento de esta decision.
>
> **Y la lectura encontro algo que nadie buscaba.** El mismo archivo atribuia a
> esa guia la distribucion mixta del tratamiento de ceros, `H(x) = q + (1-q)G(x)`,
> y **es falso: la guia no contiene ninguna formula**. La atribucion correcta es
> Stagge et al. (2015), con verificacion parcial declarada.
>
> El 19 de agosto se retiro una cita a esta fuente por no poder confirmarla y **se
> dejo en pie otra a la misma fuente, en el mismo archivo, ochenta lineas mas
> abajo, sin revisarla**. Retirar una cita dudosa no sirve si no se revisan sus
> vecinas, y una revision que no declara su alcance no permite saber que quedo sin
> mirar. Es el patron de **I-08** aplicado a la bibliografia.
>
> Ver el PR #151 y la seccion VIII-C del documento IEEE.

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

## D-21 · `probabilidad` es P(nivel = alto), no la confianza del modelo

**Estado.** Aceptada
**Fecha.** 2026-08-20
**Decide.** Alejandro

### Contexto

`contratos/esquemas.py` declara `probabilidad: float | None` entre 0 y 1 y dice
cuando es `None`, pero **no dice que magnitud es**. Hay dos lecturas posibles y no
son la misma cosa:

1. **Confianza del modelo** en la clase que asigno: P(nivel asignado).
2. **Probabilidad del nivel mas severo**: P(nivel = alto).

La ambiguedad no era teorica. Avril construyo el mapa de calor de H5.4
interpolando ese campo, y su propio comentario supone la primera lectura: *"la
probabilidad de la estimacion no es el nivel estimado"*. H3.x lo va a implementar
en los proximos dias, y hasta ahora nadie habia tenido que elegir.

### Decision

**`probabilidad` es P(nivel = alto)**: la probabilidad que el modelo asigna a la
clase mas severa del evento, con independencia de cual sea el `nivel` devuelto.

1. Se documenta en el contrato, sin cambiar la firma ni la version: es una
   precision de significado, no un cambio de interfaz.
2. **No es la confianza del modelo.** Un distrito con `nivel` bajo y
   `probabilidad` 0,05 esta diciendo que el modelo lo ve tranquilo, no que este
   poco seguro.
3. La confianza en la clase asignada **no se expone**. Si alguna vez hace falta,
   entra como campo propio y no reinterpretando este.

### Justificacion

La eleccion se decide por lo que pasa al **ordenar distritos**, que es lo que hace
el visor.

Con la lectura de confianza, un distrito con nivel bajo y confianza 0,95 tendria
un valor mas alto que uno con nivel alto y confianza 0,45. **El mapa de calor
pintaria mas intenso al distrito tranquilo.** No es un defecto de la
implementacion de Avril: es lo que produce interpolar confianza y llamarlo mapa de
riesgo.

Con P(nivel = alto) el campo es **monotono en el riesgo**: mas alto significa mas
riesgo, siempre. Eso lo vuelve:

- **Interpolable con sentido.** La superficie de H5.4 pasa a ser una superficie de
  riesgo y no una de seguridad del modelo.
- **Comparable entre distritos y entre eventos**, que es lo que el semaforo de
  H7.1 necesita.
- **Utilizable como umbral continuo**, sin depender de que la clase discreta caiga
  de un lado u otro del corte.

Hay un argumento adicional, y es de uso. La confianza del modelo es informacion
util **para nosotros al diagnosticar**, y es ruido para quien tiene que decidir si
evacua. El campo que viaja a la interfaz debe responder a la pregunta del usuario,
no a la del desarrollador.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Confianza en la clase asignada | Rompe el orden: un distrito tranquilo con el modelo seguro puntua mas alto que uno en riesgo con el modelo dudando. Es lo que el mapa de calor pintaria |
| Exponer el vector completo de las tres clases | Es lo mas informativo y lo mas dificil de consumir. Obliga a cada consumidor a decidir que hace con el, y esa decision volveria a tomarse distinto en cada lugar |
| Dejarlo sin definir | Es lo que habia. Dos historias ya lo usan con supuestos distintos |
| Definirlo como P(nivel asignado) y agregar otro campo con P(alto) | Dos campos que se parecen invitan a usar el equivocado. Si mas adelante hace falta la confianza, entra con nombre propio |

### Consecuencias

**Se gana** un campo con una interpretacion unica, monotona en el riesgo y
comparable, que es lo que necesitan el mapa de calor, el semaforo y cualquier
umbral continuo.

**Se pierde** la confianza del modelo como dato expuesto. Para el analisis interno
sigue estando dentro del estimador; simplemente no viaja por el contrato.

**Afecta a H5.4, que ya esta integrada.** El mapa de calor no cambia de codigo:
cambia lo que significa. Su leyenda dice "probabilidad interpolada" y el texto de
`interpolacion.js` afirma que la probabilidad no es el nivel estimado. Con esta
decision esa afirmacion sigue siendo cierta —una probabilidad continua no es una
clase discreta— pero el matiz de "no confundir con riesgo" ya no aplica: **ahora
si es una superficie de riesgo.** Hay que ajustar ese texto.

**H3.x lo implementa asi desde el principio**, que es el motivo de decidirlo ahora
y no despues de entrenar.

### Medicion

Cuando exista un modelo entrenado, comprobar sobre los ocho distritos que el orden
por `probabilidad` **no contradice** el orden por `nivel`: ningun distrito con
nivel bajo debe tener una probabilidad mayor que uno con nivel alto del mismo
evento y fecha.

Si eso ocurriera, o el campo no es P(nivel = alto) o el etiquetado y el modelo
estan en desacuerdo, y las dos cosas hay que mirarlas.

---

## D-22 · H1.4 se reduce: no hay faltantes que imputar en las series climaticas

**Estado.** Aceptada
**Fecha.** 2026-08-20
**Decide.** Alejandro, a partir del hallazgo de Cesar en H1.1

### Contexto

H1.4 —"Documentar y aplicar criterios de imputacion de faltantes", 5 puntos y 7,8
horas— se planifico suponiendo que las series climaticas tendrian huecos.

Al cargar H1.1 se comprobo que no los tienen:

> No hay un solo faltante que imputar: cero nulos en las siete variables, en los
> ocho distritos, en 12.784 dias.

No es casualidad ni suerte: **CHIRPS y POWER son productos de malla**, generados
por interpolacion y reanalisis sobre todo el dominio. Estan completos por
construccion. La historia se planifico contra una intuicion de datos de estacion,
que si tienen huecos, y las fuentes que se eligieron no lo son.

### Decision

**H1.4 no se cierra como no aplicable, pero se reduce**: de 5 puntos y 7,8 horas a
**3 puntos y 4,7 horas**.

Deja de tener la parte de "aplicar", que no tiene sobre que aplicarse, y conserva
dos cosas que si hacen falta:

1. **Declarar la regla de imputacion antes de necesitarla**, con su prueba contra
   huecos inyectados. `MetodoImputacion` ya existe en el contrato con cuatro
   valores; lo que falta es cual se usa, cuando, y que queda registrado.
2. **Fijar la distincion entre ausencia de evento y ausencia de dato**, que es
   donde el proyecto se puede equivocar de verdad.

### Justificacion

**Cerrarla del todo seria un error, y el motivo esta en las otras dos fuentes.**

Las series climaticas no tienen huecos, pero:

- **FIRMS** (H1.2) es un producto de eventos, no de malla. Un dia sin deteccion de
  focos **no es un dato faltante: es un cero**. Confundirlos invertiria el sentido
  del riesgo de incendio, que es exactamente la clase de defecto que **D-07**
  existe para evitar y que ya produjo la incidencia I-04 con otros datos.
- **Sentinel-2** (H1.6) descarta imagenes por nubosidad mayor al 20 %. Ahi si hay
  huecos reales, y en estacion lluviosa van a ser muchos.

O sea que la historia tenia razon de existir; se equivoco de fuente. Reducirla y
reapuntarla cuesta menos que cerrarla ahora y volver a abrirla en dos semanas.

**Lo que se conserva vale por si solo.** Una regla de imputacion escrita antes de
que aparezca el primer hueco es una decision; escrita despues, es una
racionalizacion de lo que ya se hizo.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Cerrarla como no aplicable con la evidencia de H1.1 | Libera 7,8 h y deja al proyecto sin regla el dia que Sentinel-2 traiga huecos, que es seguro. El ahorro es aparente |
| Dejarla como esta | Son 7,8 h con la mitad del alcance sin objeto. Estimar contra un supuesto que ya se sabe falso es lo que la replanificacion existe para corregir |
| Fundirla con H1.5, el reporte de calidad | H1.5 **mide** lo que hay; H1.4 **decide** que hacer con lo que falta. Son cosas distintas y juntarlas haria que la decision se tome mientras se escribe un reporte |
| Moverla al Sprint 2, despues de H1.6 | Tiene sentido por dependencia, pero H1.7 la espera y quedaria bloqueada mas tiempo. Se mantiene en S1 con el alcance reducido |

### Consecuencias

**Se ganan 3,1 horas** en el Sprint 1 de Cesar, que es el que esta mas cargado de
los suyos, y una regla escrita antes de necesitarla.

**Se pierde** la aplicacion practica sobre datos reales: la regla se va a probar
contra huecos inyectados y no contra huecos observados. Es una limitacion menor y
queda declarada en la propia historia.

**La dependencia de H2.1 sobre H1.4 queda obsoleta**, porque H2.1 ya se cerro sin
ella. Se retira del backlog: mantenerla haria que el verificador de dependencias
declare satisfecha una relacion que nunca se cumplio.

**H1.7 sigue dependiendo de H1.4** y esa si se mantiene: versionar el dataset
consolidado requiere saber que se hizo con lo que falta, aunque hoy no falte nada.

### Medicion

La historia se cierra cuando exista, con prueba ejecutable:

1. La regla escrita: que metodo se aplica a cada variable y con que limite de
   huecos consecutivos.
2. Una prueba que **inyecta huecos** en una serie completa y comprueba que se
   imputan segun la regla y que **queda registro de cada imputacion**.
3. La distincion entre ausencia de evento y ausencia de dato, escrita donde la vea
   quien implemente H1.2.

Y se comprueba contra la realidad cuando H1.6 traiga sus huecos por nubosidad: si
la regla escrita hoy no sirve para ese caso, quedo corta y hay que revisarla.

---

## D-23 · El visor negocia su origen una sola vez y degrada al respaldo declarandolo

**Estado.** Aceptada
**Fecha.** 2026-08-20
**Decide.** Alejandro, desde H6.6
**Revisa.** D-14

### Contexto

D-14 dejo al visor leyendo archivos JSON estaticos y prometio que el dia que
existiera la API el cambio seria *"la URL del `fetch`, en un solo modulo"*. La API
existe desde el 19 de agosto (H6.1). Al hacer el cambio aparecieron tres cosas que
D-14 no habia previsto.

**Primera: no es una URL, es una traduccion.** La API devuelve `list[Distrito]` y
`list[Riesgo]`; el visor espera un `FeatureCollection` y un mapa indexado por
codigo. La costura de D-14 estaba bien puesta —toda la traduccion cabe en
`cliente.js` y ningun componente cambio— pero la promesa era optimista.

**Segunda: el respaldo no se puede tirar.** La Definition of Done de H6.6 exige que
el visor siga en pie si la API no responde. Los archivos de D-14 dejan de ser el
origen y pasan a ser la degradacion. Eso significa que el visor tiene **dos**
origenes posibles, no uno, y que hay que decidir cuando usa cada uno.

**Tercera: dos origenes se pueden mezclar.** `App.jsx` pide la salud y los
distritos a la vez con un `Promise.all`, y los riesgos en otro efecto. Si cada
llamada decidiera por su cuenta, una podria dar con la API arriba y la siguiente
con la API caida.

### Decision

**1. El origen se negocia una sola vez, al arrancar, y las tres llamadas usan lo
que se haya negociado.** La negociacion es la propia consulta a `/salud`,
memorizada como una promesa compartida: quien llegue primero la dispara y los
demas esperan ese mismo resultado.

**2. Si la API no responde, se lee el respaldo estatico y se declara en pantalla,
con el motivo.** El visor no se queda en blanco ni muestra un error como si no
hubiera datos.

**3. `modo` y `origen` son dos campos distintos.** `modo` dice **que** son los
datos —simulado o real— y lo decide la API segun que implementacion respondio.
`origen` dice **por donde** llegaron —`api` o `estatico`— y lo decide el cliente.

**4. El visor llega a la API por una ruta relativa, `/api`.** En desarrollo la
reenvia el proxy de `vite.config.js`; en el despliegue, el mismo servidor que
sirve el visor.

### Justificacion

**Por que un solo origen.** Hoy los dos coinciden: los dos salen del mismo
`RepositorioSimulado` con la misma semilla, asi que una mezcla seria invisible.
Cuando H6.2 traiga PostgreSQL dejaran de coincidir, y entonces el visor pintaria
los riesgos de un mundo sobre los distritos de otro **sin que nada fallara**. La
decision hay que tomarla ahora, mientras el error todavia no se puede cometer:
despues seria un defecto que solo se ve mirando el mapa con atencion.

**Por que dos campos y no uno.** Son ejes ortogonales. El caso peligroso es el que
todavia no existe: el dia que la API sirva dato real y se caiga, el respaldo
servira dato simulado viejo. Con un solo campo ese caso se veria igual que el
normal. Con dos, la pantalla puede decir a la vez "datos simulados" y "la API no
responde, esto es el respaldo del 16 de agosto".

Y ya se observo: con el respaldo sin regenerar, el visor declaraba contratos
v1.3.0 mientras la API declaraba v1.3.1. Es exactamente el riesgo que D-14 se
habia anotado a si misma —*"si los contratos cambian y nadie vuelve a correr el
exportador, el frontend trabaja contra datos viejos sin enterarse"*— y ahora es
**visible en pantalla** en vez de estar solo escrito en un ADR.

**Por que una ruta relativa y no `http://localhost:8000`.** Un origen absoluto
obliga a habilitar CORS en `backend/api/aplicacion.py`, que es archivo de Cesar y
que la excepcion de propiedad de H6.6 no autoriza. Pero aunque lo autorizara, la
ruta relativa es la solucion correcta: en el despliegue el visor y la API van
detras del mismo origen, asi que el permiso no haria falta y habria que quitarlo.
La restriccion de propiedad y la buena arquitectura apuntaron al mismo lado.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| Que cada llamada decida su origen | Permite mezclar dos mundos sin que nada falle. Es el defecto que no se ve |
| Un solo campo que diga `simulado`, `real` o `respaldo` | Confunde que son los datos con por donde llegaron. El caso "dato real caido a respaldo simulado" se volveria indistinguible |
| Borrar los archivos estaticos | Es el respaldo de la Definition of Done. Sin ellos, una API caida deja el visor en blanco |
| Origen absoluto mas CORS en la API | Toca archivo ajeno, y en produccion sobra |
| Reintentar la API en cada llamada | Un visor que cambia de origen a mitad de sesion tiene el mismo problema de mezcla, repartido en el tiempo |

### Consecuencias

Se gana un unico punto de decision y un visor que sobrevive a la API caida sin
mentir sobre lo que muestra.

Se pierde: **el origen no se renegocia**. Si la API vuelve durante la sesion, el
visor sigue en el respaldo hasta que se recargue la pagina. Es a proposito —lo
contrario permite la mezcla— y es el precio correcto para un visor que se abre y
se deja abierto unas horas.

Queda una deuda: el aviso en pantalla lo tiene que dibujar
`AvisoModoSimulado.jsx`, que es de Avril. Va por solicitud de cambio, no por diff
propio.

### Medicion

Ejecutado el 20 de agosto contra la API de H6.1, cargando el `cliente.js` real:

| Escenario | Resultado |
|---|---|
| API arriba | `origen: api`, 8 distritos, fecha de hoy, sin motivo de respaldo |
| API caida | `origen: estatico`, `motivo: fetch failed`, 8 distritos |
| API responde 502 | `origen: estatico`, `motivo: la API respondio 502` |
| API arriba, sin estimacion para hoy | `origen: api`, **8 distritos sin estimacion**, no pantalla vacia |
| Cambiar de evento y volver | Los mismos valores. Antes de SC-03, tres respuestas distintas |

31 comprobaciones en `python docs/herramientas/verificar_h66.py` al escribirse
esta decision. Son **35** desde SC-05, que agrego cuatro: la monotonia del
respaldo estatico por evento y la ausencia de nivel medio en incendio.

---

## D-24 · El modelo de estimacion es una constante: se empieza a medir antes de corregirlo

**Estado.** Aceptada
**Fecha.** 2026-08-20
**Decide.** Alejandro
**Lo detecta.** Avril, al entregar H7.1

### Contexto

Avril reporto H7.1 con tres numeros en vez de uno:

| | Horas |
|---|---|
| Backlog | 5.8 |
| Su estimacion, dicha antes de arrancar | 4.0 |
| **Real** | **2.0** |

Y planteo que el modelo del proyecto no contempla cuatro cosas que ella observo
al hacer cinco historias seguidas de frontend.

Fui a ver contra que modelo estaba discutiendo. Es este:

| Historia | Puntos | Horas | h/punto |
|---|---|---|---|
| H5.1 | 3 | 2.9 | **0.97** |
| H5.2 | 5 | 4.8 | **0.96** |
| H5.3 | 7 | 6.7 | **0.96** |
| H5.4 | 8 | 12.5 | 1.56 |
| H7.1 | 6 | 5.8 | **0.97** |

**Cuatro de cinco son puntos x 0.96.** No es una muestra: es el modelo entero.
Sobre las 82 historias, 423 puntos y 620.3 horas dan 1.47 h/punto de promedio, y
la dispersion sale de que a distintas epicas se les aplico distinta constante, no
de que se haya estimado historia por historia.

Ninguna de las cuatro variables que Avril describe esta adentro, **porque no hay
donde meterlas**: una multiplicacion por una constante no tiene parametros.

Las cuatro, en sus palabras:

1. **Si el sistema de diseno ya existe o hay que crearlo.** H5.1 lo creo y se
   paso; H5.2, H5.3 y H5.4 lo consumieron y entraron cortas. La primera historia
   visual de una epica paga una deuda que las demas no vuelven a pagar.
2. **Si la verificacion es por script o a ojo.** Lo que se comprueba con un
   comando escala; lo que hay que mirar distrito por distrito no baja con la
   practica.
3. **Si hubo ronda de revision.** H5.3 tuvo una y casi duplico el esfuerzo.
4. **Si la historia decide o solo implementa.** H5.4 tenia la estimacion mas alta
   —1.56 h/punto, la unica que se sale de la constante— y salio corta, porque el
   codigo era poco y lo caro fue decidir.

**La tercera es la que importa mas, y no es de frontend.** Las otras tres son de
su epica. La ronda de revision aplica a todas: H1.5 la tuvo el 20 de agosto,
H6.6 tuvo dos de Cesar, SC-03 y SC-04 salieron de una. Es lo mas frecuente que
hace el equipo y no esta en ninguna estimacion. Sobre 620 h planificadas, un 15 %
son 93 h que el plan no tiene.

**Un caso concreto de trabajo no registrado.** El roadmap estimaba el sistema de
diseno en 4 h como tarea de Sprint 0. Nunca se convirtio en historia y entro
dentro de H5.1, estimada en 2.9 h. Explica por que H5.1 se paso sin que nadie
supiera contra que compararla.

### Decision

**1. Se registran dos numeros al cerrar cada historia**, en
`docs/tareas/<persona>.md`, debajo de la linea de la historia:

    - horas: estimada 4.0 . real 2.0

`estimada` es lo que la persona dijo **antes de arrancar**, sin mirar el backlog.
`real` es lo que tardo. Las horas del backlog no se repiten: ya estan en la linea
de arriba y en `backlog.csv`.

**2. Se exige desde el 2026-08-20, no hacia atras.**

Cuando no hubo estimacion previa se escribe `n/d` **con el motivo entre
parentesis**, en la misma linea:

    - horas: estimada n/d (no se pidio al arrancar) . real 2.5

Escribir un numero hoy, sabiendo lo que costo, seria el anclaje que esta misma
decision descarta, con el agravante de que se veria igual que uno medido. Y un
`n/d` sin motivo no se distingue de un olvido.

> **Correccion del 2026-08-23.** La primera version aceptaba `n/d` **solo en las
> historias cerradas el 2026-08-20**, razonando que eran las unicas terminadas
> antes de que la regla existiera.
>
> **El razonamiento estaba mal, y lo encontro Luna al cerrar H9.1:** esa historia
> se cerro despues del corte y tampoco tenia estimacion previa, porque nadie se
> la pidio al arrancar.
>
> Atar la excepcion a una **fecha** suponia que la unica causa posible de no
> tener estimacion era el momento del corte. La causa real es otra —si alguien la
> pidio o no— y esa el verificador no puede conocerla. Lo unico que puede exigir
> es que quien escriba `n/d` diga por que.
>
> El diseno viejo obligaba a elegir entre inventar un numero o dejar el CI rojo.
> **Un numero inventado contamina justo la serie que esta decision quiere
> construir**, asi que era peor que el hueco que venia a tapar.
>
> Es el mismo patron que I-04 y que I-08: una regla con forma valida y contenido
> equivocado, que ninguna comprobacion automatica detecta porque la forma esta
> bien. La encontro quien la uso, no quien la escribio.

El primer caso es **H6.6**, de Alejandro: 4.8 h de backlog contra **3 h reales**,
sin estimacion previa porque la regla se creo el mismo dia del cierre. Es la
primera medicion del proyecto y es incompleta a proposito.

**3. No se cambia ninguna estimacion todavia.** El backlog, el roadmap y las
tablas de capacidad se quedan como estan hasta la retrospectiva del Sprint 2.

**4. Lo comprueba `docs/herramientas/verificar_horas.py` en el CI**, que ademas
imprime la comparacion acumulada.

### Justificacion

**Por que dos numeros y no uno.** Son dos errores distintos. En H7.1 el backlog
dijo 5.8, Avril dijo 4 y el real fue 2: los dos fallaron, y no por lo mismo. Con
un solo numero no se puede separar el error del modelo del proyecto del error de
quien estima, y son dos problemas con dos soluciones.

**Por que no hacia atras.** El argumento es de Avril: estimar hoy H5.3 sabiendo
que el backlog dice 6.7 h produce un numero cerca de 6.7 h **por construccion**.
Un dato anclado no mide, confirma. Ella dio direcciones —"mucho mas larga", "mas
corta"— en lugar de inventar cifras con un decimal, y es la respuesta correcta.

**Por que medir antes de corregir.** Hay una sola historia medida. Cambiar el
coeficiente con n=1 sustituiria una constante mal fundada por otra constante mal
fundada, y ademas moveria las tablas de capacidad de las cuatro personas en mitad
del Sprint 2.

Pero la parte **estructural** no necesita mas datos: que el modelo sea una
multiplicacion se lee hoy en `backlog.csv`. Por eso esta decision separa las dos
cosas: registra lo que ya esta probado y difiere lo que todavia no.

**Por que en el archivo de tareas y no en un CSV aparte.** Es donde la persona ya
esta cuando cierra la historia. Un segundo archivo obligaria a escribir en dos
lugares y a que coincidieran, que es el defecto de I-07.

### Alternativas descartadas

**Esperar a la retrospectiva del Sprint 2 y decidirlo todo alli.** Es lo que
parecia razonable, y falla por una razon practica: hoy no existe **ningun campo**
donde escribir horas reales. Si se pide el dato sin darle lugar, vive en mensajes
sueltos y se pierde, y la retrospectiva llega sin nada que analizar. Es el mismo
problema que H1.7 tiene con la evidencia de H1.1, aplicado a la gestion.

**Reestimar el backlog completo con las cuatro variables.** 82 historias
reestimadas desde cuatro observaciones cualitativas y una medicion. Seria
sustituir una cifra sin respaldo por otra con mas aspecto de rigor y el mismo
respaldo.

**Pedir solo las horas reales, sin la estimacion previa.** Mas barato de anotar y
pierde justo lo que hace util al dato: sin la estimacion previa no se puede saber
si el error es del modelo o del criterio de quien estima.

**Reconstruir las horas de las historias ya cerradas.** Descartada por el
anclaje. Ver la justificacion.

### Consecuencias

**Lo que mejora.** A partir de la proxima historia cerrada existe una serie
comparable. La retrospectiva del Sprint 2 llega con datos en vez de con
impresiones.

**Lo que cuesta.** Dos numeros por historia y la disciplina de decir la
estimacion **antes** de arrancar, que es la parte que se olvida.

**Lo que queda abierto.** El coeficiente. Y si las cuatro variables de Avril se
vuelven parametros del modelo o solo notas para estimar mejor a mano: con los
datos de hoy no se puede decidir.

**Lo que no cambia.** Ninguna estimacion vigente, ninguna tabla de capacidad y
ningun compromiso de sprint.

### Medicion

`python docs/herramientas/verificar_horas.py` falla si una historia cerrada desde
el 2026-08-20 no declara sus horas, e imprime la tabla acumulada con el cociente
entre lo que el backlog estima y lo que costo.

**Criterio de revision.** Se vuelve sobre esta decision en la retrospectiva del
Sprint 2, con al menos **ocho historias medidas** repartidas entre las cuatro
personas. Menos que eso no distingue el modelo de la persona.

Las tres preguntas que esa revision tiene que poder contestar:

1. El cociente backlog/real, ¿es parecido entre las cuatro personas o cada una
   tiene el suyo?
2. Las historias con ronda de revision, ¿se pasan de forma sistematica?
3. La primera historia de una epica, ¿se pasa mas que las siguientes?

---

## D-25 · El incendio es binario y se acota a los tres distritos con senal

**Estado.** Aceptada
**Fecha.** 2026-08-20
**Decide.** Alejandro, desde H3.0
**Lo detecta.** Cesar, al medir R16
**Sustituye.** El umbral de incendio de **D-08**. Cierra el riesgo **R16**.

### Contexto

R16 estaba abierto desde el 3 de agosto, declarado en D-08 como *"pendiente y
prioritaria"*: si el canton no tenia suficientes focos historicos, el evento de
incendio no era modelable. Era el riesgo mas viejo del proyecto y el roadmap
condicionaba a el 60 h de esfuerzo.

Cesar lo midio. **242 focos en 24 anios**, contados con las geometrias del SNIT,
punto en poligono, sobre el archivo historico de FIRMS por pais.

Tres hechos, y cada uno decide una cosa distinta.

**Primero: el umbral no producia tres clases.** El P90 del conteo por ventana
vale **0,0 en los ocho distritos**, porque entre el 97 % y el 99,9 % de las
ventanas estan vacias. Se corrige en **SC-05** y no se repite aqui.

**Segundo: dos distritos no tienen nada que modelar.**

| Distrito | focos en 24 anios |
|---|---|
| 50804 Santa Rosa | 83 |
| 50805 Libano | 65 |
| 50806 Tierras Morenas | 65 |
| 50801 Tilaran | 15 |
| 50802 Quebrada Grande | 7 |
| 50803 Tronadora | 5 |
| **50807 Arenal** | **1** |
| **50808 Cabeceras** | **1** |

Tres distritos concentran 213 de los 242, el **88 %**. Arenal y Cabeceras tienen
**un foco en veinticuatro anios**.

**Tercero: la serie no es homogenea.**

    2001-2011, solo MODIS:    69 focos / 11 anios =  6,3 por anio
    2012-2024, MODIS+VIIRS:  173 focos / 13 anios = 13,3 por anio
                                             salto de 2,1x

VIIRS entra en 2012 con 375 m de resolucion contra los 1.000 m de MODIS. **El
salto es del sensor, no del clima.**

Y hay algo aprovechable: **cero focos entre junio y octubre**, cinco meses
seguidos, con el 86 % concentrado entre enero y abril.

    01:10  02:11  03:55  04:131  05:34  06:0  07:0  08:0  09:0  10:0  11:1  12:0

### Decision

**1. El alcance del evento incendio se limita a Santa Rosa, Libano y Tierras
Morenas.** Los otros cinco distritos se reportan como **«sin datos
suficientes»**, no con un numero.

**2. No se restringe la serie a la era VIIRS.** Se conservan los 24 anios, con
tres condiciones:

- La **era o el sensor queda como columna** en la carga de H1.2. El dato de
  heterogeneidad se guarda, no se descarta.
- **Ninguna variable de tendencia temporal entra al modelo de incendio.** Ni
  anio, ni indice de tiempo.
- **Toda afirmacion sobre tendencia se restringe a 2012-2024**, y se dice.

**3. Se declara por adelantado que la comparacion de algoritmos puede no ser
concluyente para incendio.** Con 33 a 38 ventanas positivas por distrito, H3.3 y
H3.4 miden ruido de particion antes que calidad de algoritmo. La linea base
climatologica de H3.1 puede ser el techo real del evento.

**4. El evento de incendio NO sale del alcance.** El roadmap contemplaba
retirarlo y liberar unas 60 h. No se hace: el evento es parte del charter, y con
el alcance acotado sigue siendo estimable y verificable.

### Justificacion

**Por que se acotan los distritos y no se rellenan.** Un modelo entrenado sobre
un evento en veinticuatro anios no se puede validar: cualquier particion deja
cero o un caso positivo del otro lado. Reportar «sin datos suficientes» es la
misma distincion que **D-22** —un cero no es un hueco— aplicada al otro extremo,
y aguas abajo ya funciona: el semaforo de H7.1 y las coropletas de H5.3
distinguen «sin estimacion» de «riesgo bajo».

**Por que no se restringe a VIIRS, aunque el diagnostico sea correcto.** Cuesta
la mitad de los positivos:

| Distrito | positivas 2001-2024 | positivas solo VIIRS |
|---|---|---|
| 50804 | 38 | **20** |
| 50805 | 33 | **18** |
| 50806 | 34 | **18** |

Con veinte ventanas positivas no se entrena y sobre todo **no se valida**:
partirlas deja una prueba de seis o siete casos, donde un acierto mueve la
metrica quince puntos. Pagar homogeneidad con la mitad de los positivos, estando
ya cortos, empeora el problema que pretende arreglar.

El tratamiento elegido es el de **D-17** con la precipitacion: no se tira el dato
incomodo, se declara de donde vino y se acota que se puede afirmar con el.

**Por que se declara la limitacion antes de medir.** Es lo que impide elegir
despues el modelo que salio mejor por azar y escribirle una justificacion. Mismo
criterio que los criterios de aceptacion de H3.0, escritos antes de ver el dato.

### Alternativas descartadas

**Sacar el incendio del alcance.** Es lo que D-08 previo y lo que el roadmap
tenia presupuestado, con 60 h de ahorro. Se descarta porque el evento sigue
siendo estimable en los tres distritos que concentran el 88 % de los focos, y
porque la estacionalidad da una linea base solida. Retirarlo dejaria el proyecto
con dos de los tres eventos del charter por un problema que resulto acotable.

**Ampliar la ventana a 90 dias.** Es la unica agregacion que llega al 10 % de
ventanas positivas. Se descarta porque contradice la definicion de 7 dias del
contrato y porque una alerta de incendio a 90 dias no sirve para operar.

**Agregar por canton en vez de por distrito.** Sube a 7,7 %, sigue sin llegar, y
pierde la resolucion espacial que es el objetivo del proyecto.

**Rellenar los cinco distritos sin senal con el valor del canton.** Seria inventar
una estimacion local a partir de datos que no son locales: el mismo defecto que
I-05 registro para POWER, cometido a proposito.

### Consecuencias

**Lo que mejora.** El evento incendio pasa de tener un umbral imposible de
cumplir a tener uno medido, con alcance declarado y limitaciones escritas de
antemano.

**Lo que cuesta.** Cinco de ocho distritos sin estimacion de incendio, visible en
el visor. Es informacion, no un hueco: dice que ahi no hubo con que estimar.

**Lo que queda abierto.** Si la comparacion de algoritmos de H3.3 y H3.4 resulta
concluyente para incendio. Se sabra al medirla, y esta decision deja escrito que
puede no serlo.

**H9.3 cambia de contenido.** *"Someter los umbrales de incendio"* a los actores
locales sigue en pie, pero el umbral que se somete es otro y ahora lleva una
medicion detras en lugar de un criterio del equipo sin respaldo.

### Medicion

`python -m contratos.verificar` comprueba que el simulado respete el vocabulario:
incendio nunca emite MEDIO, si alcanza BAJO y ALTO, y los otros dos eventos
conservan sus tres niveles. **47 comprobaciones**, tres nuevas.

El informe de Cesar queda como fuente en la evidencia de H1.2 y de H3.0.

**Criterio de revision.** Se vuelve sobre esta decision cuando H3.1 entregue la
linea base climatologica. Las dos preguntas que esa entrega tiene que contestar:

1. ¿Algun modelo de H3.3 supera a la linea base estacional en los tres distritos
   con senal, con una diferencia mayor que su intervalo de confianza?
2. Con la era como covariable, ¿queda algun efecto atribuible al clima y no al
   cambio de sensor?

Si la respuesta a la primera es no, el resultado del evento incendio **es la
linea base**, y se reporta como hallazgo y no como fracaso.

---

## D-26 · El sistema declara latencia por evento, no promete tiempo real

**Estado.** Aceptada
**Fecha.** 2026-08-23
**Decide.** Alejandro
**Revisa.** D-15, sobre la eleccion de CHIRPS
**Medicion.** `docs/14-latencia-de-las-fuentes.md`

### Contexto

El proyecto viene diciendo "informacion en tiempo real" desde el charter. **Nadie
habia comprobado cuando llega el dato.** Es el mismo tipo de afirmacion que
R16: escrita al principio, repetida en tres documentos, sin contrastar.

Contrastada contra la documentacion oficial de cada fuente:

| Fuente | Alimenta | Latencia |
|---|---|---|
| FIRMS | Incendio | **~3 horas** |
| POWER | Temperatura, humedad, viento, radiacion | dias, en el producto reciente |
| CHIRPS final | Precipitacion -> sequia y lluvia intensa | **21 a 51 dias** |

**Tres hechos que el proyecto no sabia.**

**Primero: CHIRPS final llega en la tercera semana del mes siguiente.** El SPI-3
mira una ventana de 90 dias que termina hoy, asi que **entre el 23 % y el 57 % de
esa ventana no es dato final** al momento de estimar.

Y el preliminar no es el mismo dato menos pulido: es **"GTS and Mexico only"**.
Para Costa Rica eso lo deja sin la correccion por estaciones, que es justamente lo
que distingue a CHIRPS de una estimacion satelital cualquiera y lo que D-15 eligio.

**Segundo: POWER cambia de modelo a mitad de la serie.** El historico sale de
**MERRA-2**; los ultimos meses, de **GEOS-5.12.4 FP-IT**. Un modelo entrenado
sobre la serie se entrena con uno y **opera con el otro**, y la frontera cae justo
en el dato que el sistema usaria en produccion.

Es la misma heterogeneidad que Cesar encontro en FIRMS al medir R16 —MODIS hasta
2011, MODIS+VIIRS despues, salto de 2,1x— pero en la fuente que dabamos por
homogenea. I-05 y D-15 hablan de MERRA-2 como si fuera toda la serie.

**Tercero: la produccion de CHIRPS v2 termina despues de diciembre de 2026.**

### Decision

**1. El sistema NO promete tiempo real. Declara una latencia por evento**, y la
muestra:

| Evento | Cadencia util | Por que |
|---|---|---|
| Incendio | diaria o mas seguido | FIRMS llega en 3 h |
| Lluvia intensa | diaria, con preliminar declarado | el final tarda hasta 51 dias |
| Sequia | **semanal como mucho** | latencia, y ademas el SPI-3 apenas se mueve |

**2. Para sequia hay una segunda razon, independiente de la latencia.** El SPI-3
mira 90 dias, de los cuales 83 ya se conocian ayer. Actualizarlo a diario moveria
la aguja poquisimo aunque el dato llegara al instante.

**3. No hay ninguna frase que retirar, y conviene decir por que.**

Al escribir esta decision di por sentado que el proyecto prometia "tiempo real"
en sus documentos, y fui a quitarlo. **No esta.** El unico lugar donde aparece es
`docs/11-ceremonias-scrum.md`, y dice lo contrario:

> *"Se eliminan: modulo de busqueda semantica, sensores fisicos, **procesamiento
> en tiempo real**, autenticacion de usuarios..."*

Es la accion **A1.1** del Sprint 0, la reduccion del 38 % que pidio la evaluacion
docente. **El procesamiento en tiempo real esta fuera de alcance desde el primer
dia**, por una decision que ya se tomo y se documento.

Lo que existe es una **aspiracion del equipo** —repetida en conversacion, no en
el repositorio— de que el sistema sirva informacion actualizada. Esta decision no
la contradice: la acota con numeros. Y deja escrito que si alguna vez esa frase
va a entrar a un documento, la latencia de arriba es lo que puede sostener.

**4. Se crea la historia de ingesta periodica.** De las 86 del backlog, ninguna
vuelve a consultar las fuentes: H1.1 es una descarga historica de una vez.

**5. Queda pendiente medir el solape MERRA-2 / FP-IT.** Es trabajo de H1.1, que
tiene el descargador, y es la misma medicion que Cesar hizo para las eras de
FIRMS.

**6. El fin de vida de CHIRPS v2 va a las limitaciones del documento IEEE.**

### Justificacion

**Por que declarar la latencia en vez de esconderla.** Un visor de riesgo
climatico que no dice cuando se midio lo que muestra invita a leer una estimacion
vieja como si fuera de hoy. Es la misma razon por la que H6.6 muestra la fecha de
la estimacion y la pone en ambar cuando no es la de hoy.

**Por que por evento y no un numero unico.** Un solo numero obligaria a usar el
peor caso, y con eso incendio —que si es casi en tiempo real— quedaria reportado
como si tardara semanas. Perderia la unica capacidad operativa real del sistema.

**Por que esto no invalida el proyecto.** El objetivo es estimar riesgo por
distrito, no operar un sistema de alerta temprana. Lo que cambia es lo que se
promete, no lo que se hace.

### Alternativas descartadas

**Usar solo el preliminar de CHIRPS y no declararlo.** Bajaria la latencia a 2
dias. Se descarta porque para Costa Rica el preliminar es satelite sin correccion
por estaciones, y presentarlo como equivalente al final seria exactamente el tipo
de afirmacion que I-05 y D-22 vinieron a evitar.

**Cambiar de fuente de precipitacion.** D-15 eligio CHIRPS por su resolucion de
0,05°, la unica que distingue distritos segun I-05. Ninguna alternativa conocida
mejora resolucion y latencia a la vez, y cambiarla a esta altura obligaria a
rehacer H2.7, D-17 y todas las mediciones de percentiles.

**No decir nada y dejar "tiempo real" en el charter.** Es lo que estaba pasando.

### Consecuencias

**Lo que mejora.** El sistema promete algo que puede cumplir, y lo que promete
esta medido.

**Lo que cuesta.** Hay que tocar el charter y el documento IEEE, y la frase
"tiempo real" era parte de como se presento el proyecto.

**Lo que queda abierto.** Cuanto difieren MERRA-2 y FP-IT en el solape. Hasta
medirlo, ninguna afirmacion sobre el comportamiento del modelo en produccion se
puede sostener del todo.

**Lo que no cambia.** Ninguna historia se cancela ni se reestima.

### Medicion

`docs/14-latencia-de-las-fuentes.md`, con las cuatro afirmaciones citadas contra
la documentacion oficial de cada proveedor.

**Alcance declarado:** las latencias son las que **declara** cada fuente. No se
midio empiricamente descargando archivos y comparando fechas. Eso confirmaria lo
declarado y es trabajo de H1.1 y H1.2.

**Criterio de revision.** Se vuelve sobre esta decision cuando H1.1 mida el
solape MERRA-2 / FP-IT. Las dos preguntas que esa medicion tiene que contestar:

1. ¿Cuanto difieren los dos productos en las variables que usa el modelo?
2. ¿Alcanza con declarar la era como covariable, como se hizo en D-25 con FIRMS,
   o hay que restringir la serie?

---

## D-27 · El alcance diferido se registra con condicion de reactivacion medible

**Estado.** Aceptada
**Fecha.** 2026-08-24
**Decide.** Alejandro, Lead PM
**Origen.** Propuesta de integrar sismos al visor, tras revisar la aplicacion del OVSICORI
**Se apoya en.** La accion **A1.1** del Sprint 0

### Contexto

El 24 de agosto surgio la propuesta de **centralizar** en GeoGuardian los eventos
climaticos y los sismicos, a partir de la aplicacion **OVSICORI-UNA Alerta
Terremotos** y de que el mundo ha tenido sismos notorios recientes. La idea es
razonable: un comite municipal preferiria una sola pantalla.

Al evaluarla aparecio que el proyecto ya tenia un conjunto de trabajo aplazado
sin registro propio. La accion **A1.1** elimino **118 de 310 puntos** el 3 de
agosto, por una evaluacion docente que califico la viabilidad en 12 semanas con
5/10:

    modulo de busqueda semantica       autenticacion de usuarios
    sensores fisicos                   segmentacion con algoritmos propios
    procesamiento en tiempo real       animacion temporal

Ese recorte esta escrito en un acta de ceremonia, que es un registro de **lo que
se acordo un dia**, no una lista viva. Nada dice bajo que condicion volveria, y
la intencion del equipo es que vuelva si sobra tiempo.

**El estado real al decidir esto:** semana 6 de 12, **24 de 87 historias
cerradas, el 29 % de los puntos**, `main` 42 commits detras de `dev`, y la cadena
de despliegue detenida detras de H1.2 y H6.0.

### Decision

**1. El alcance diferido se registra aqui, con su condicion de reactivacion.**

| Diferido | Origen | Costo | Condicion para reabrir |
|---|---|---|---|
| Los seis elementos de A1.1 | A1.1, 3 ago | 118 pts | La de abajo |
| Capa de sismos en el visor | 24 ago | sin estimar | La de abajo, y ademas hosting |

**2. La condicion es una sola, y se evalua en un momento fijado.**

Se evalua en la **retrospectiva del Sprint 3**, al cerrar la semana 9. Reabre
solo si las **tres** se cumplen:

1. **H1.2 cerrada**, y con ella la cadena de datos que hoy detiene **17 historias
   abiertas, 157,0 h**, contadas por cierre transitivo el 24 de agosto. De esas,
   **9 son de Alejandro y suman 101,8 h**: una historia de 4,7 h de Cesar
   sostiene todo el modelado y el analisis de fallos.
2. **H6.0 cerrada**, y con ella la cadena de despliegue: 6 historias, 37,7 h.
3. **Ninguna historia del Sprint 3 arrastrada** al Sprint 4.

Si las tres se cumplen, se reabre **una** linea, la que mas aporte a la rubrica,
y se estima antes de comprometerla. No se reabre el recorte entero.

**3. El sismo no se estima nunca, se muestra.**

Aunque la condicion se cumpla, la capa de sismos queda acotada a **mostrar lo que
el OVSICORI ya publica**. No entra al modelo ni al backlog de E3.

Un sismo no tiene antecedente meteorologico. Toda la arquitectura es serie
climatica diaria por distrito con horizonte de 7 dias, y el sismo no se predice a
7 dias por fisica, no por falta de datos. Agregarlo como cuarto evento del
`TipoEvento` dejaria uno que el modelo **no puede estimar en absoluto**, y eso
debilita el argumento de OE2 en lugar de reforzarlo.

**4. El OVSICORI entra al estado del arte, no al alcance.**

Es la contraparte exacta de lo que la seccion 2 de `estado-del-arte.md` ya hace
con el SATIF: un sistema nacional en operacion, para **otra** amenaza, que
declara su alcance. Y aporta el limite fisico mas claro que el documento puede
citar.

### Justificacion

**Por que no cabe este trimestre, con numeros.** El proyecto lleva el 29 % de los
puntos con la mitad del calendario consumido, y la parte detenida no se destraba
agregando trabajo: se destraba cerrando H1.2. Abrir una epica nueva mientras la
ruta critica esta parada es como se pierden los proyectos que iban bien.

**Por que hace falta una condicion y no una intencion.** "Si sobra tiempo" no es
comprobable: siempre parece que va a sobrar hasta la semana 10. Una condicion
escrita, con fecha de evaluacion, se puede contestar con si o con no mirando el
repositorio. Es el mismo aprendizaje de `docs/15-cerrar-una-historia.md`: **una
regla que ninguna maquina ni ninguna ceremonia comprueba se cumple mientras
alguien se acuerda.**

**Por que la condicion es esa y no la velocidad.** La velocidad medida en D-24 es
puntos por una constante, todavia sin corregir. Condicionar a una cifra que
sabemos que no mide bien seria darle autoridad que no tiene. H1.2 y H6.0 son
hechos binarios: estan o no estan.

**Por que el OVSICORI vale igual.** Aporta tres cosas al documento sin costar
alcance: umbrales tomados de un estandar publicado —la Escala de Mercalli
Modificada—, un canal de notificacion que cambia con la severidad, y una
**declaracion de falibilidad** en su propia ficha publica. La ultima es la mas
util: es el precedente nacional de que un sistema automatizado de riesgo diga que
puede fallar, que es lo que el aviso de datos simulados hace aqui.

### Alternativas descartadas

**Agregar sismos como cuarto `TipoEvento` ahora.** Obliga a extender los
contratos, los simulados, el semaforo y el modelo para un evento que el modelo no
puede estimar. Y `NivelRiesgo` acaba de acotarse en **SC-05** con la regla de que
un nivel existe solo si el dato lo puede producir: un nivel sismico saldria de
otra fuente y no de una estimacion propia.

**Construir la alerta temprana de sismos.** El OVSICORI ya la opera a escala
nacional, gratis, con la red sismica del pais. Duplicarla no es un aporte. Y su
margen de 3 a 30 segundos exige notificacion push y disponibilidad continua, que
es infraestructura que el proyecto no tiene: **D-26 acaba de establecer que ni
siquiera puede prometer actualizacion diaria para sequia**, y H11.5 publica un
sitio estatico.

**Dejar la idea en una conversacion.** Es lo que paso con "tiempo real", que
D-26 encontro viviendo como aspiracion repetida de palabra mientras el
repositorio decia que estaba fuera de alcance desde el primer dia. Una idea sin
registro se vuelve a discutir cada dos semanas y nadie sabe si fue rechazada o
solo aplazada.

**Reabrir el recorte de A1.1 completo si se cumple la condicion.** Son 118
puntos, mas que todo lo hecho hasta hoy. Cumplir la condicion demostraria que hay
margen para algo, no para eso.

### Consecuencias

**Lo que se gana.** La propuesta queda registrada con su fundamento, y el
proyecto puede contestar con evidencia por que no la hizo, que es distinto de no
haberla pensado. El OVSICORI entra al documento IEEE por dos vias: estado del
arte, y trabajo futuro.

**Lo que se pierde.** Si la condicion se cumple, la reapertura arranca en la
semana 9 y quedan tres semanas. Es poco, y esta asumido: se prefiere entregar
completo lo comprometido.

**Lo que se crea.** Nada en el backlog. Es deliberado: una historia en el backlog
es un compromiso, y esto no lo es todavia.

**Lo que se le encarga a alguien.** A Luna, la seccion de estado del arte, que si
es trabajo de este trimestre y ya tiene donde ir. A Alejandro, la seccion de
trabajo futuro del documento IEEE, en H10.5c.

### Medicion

La condicion es comprobable el dia de la retrospectiva del Sprint 3 con:

```bash
python docs/herramientas/verificar_estado.py
gh issue list --state all --limit 300 --json number,title,state,stateReason > issues.json
python docs/herramientas/verificar_issues.py --issues issues.json
```

H1.2 y H6.0 marcadas `[x]` en `docs/tareas/cesar.md`, y el arrastre del Sprint 3
leido de `docs/12-velocidad.md`.

**Alcance de lo verificado sobre el OVSICORI.** Lo consultado fue la ficha
publica de la aplicacion y la cobertura de prensa nacional. **No se leyo
documentacion tecnica del SATT**, que es donde estaria la parametrizacion. Antes
de que estas afirmaciones entren al documento IEEE hay que buscarla, y es parte
del encargo a Luna.

**Criterio de revision.** Se vuelve sobre este registro en la retrospectiva del
Sprint 3, con si o con no. Si la respuesta es no, se anota aqui y se cierra: un
diferido que se arrastra sin decision es peor que uno descartado.

---

## D-28 · Se retira el mapa de calor: interpola donde no hay medicion

> **REVERTIDA POR D-30 el 2026-08-27. Se deja completa y sin editar.**
>
> El registro se conserva porque el error no esta en el razonamiento sino en el
> **hecho** del que parte. Todo lo que sigue esta escrito sobre una objecion
> conceptual que el profesor **no hizo**: el reporto un defecto de recorte
> -la capa se salia del canton y habia distritos que no marcaba- y eso se
> convirtio, en la redaccion de este registro, en una objecion a interpolar.
>
> El propio contexto de aqui abajo dice que son **dos problemas de distinto
> peso**, y despues los trata como uno solo para retirar la capa. Esa costura es
> el defecto, y por eso el registro se queda visible en vez de corregirse. Ver
> **I-14** y **D-30**.

**Estado.** Revertida por D-30 el 2026-08-27, por partir de un hecho falso
**Fecha.** 2026-08-24
**Decide.** Alejandro, Lead PM
**Lo detecta.** El profesor del curso, mirando el visor publicado
**Afecta.** El entregable de **H5.4**, que queda cerrada. Ver mas abajo.

### Contexto

El visor publicado tenia una capa conmutable descrita en pantalla asi:

> *"Mapa de calor · Probabilidad interpolada entre los ocho distritos"*

El profesor la señalo al ver el sitio, el 24 de agosto. Es la primera valoracion
del sistema por alguien de afuera del equipo: **H9.2a**, la validacion externa
planificada, todavia no ocurrio. Queda en
`docs/evidencias/computacion-grafica/retroalimentacion-docente-visor-2026-08-24.md`.

Al revisarla aparecieron **dos problemas de distinto peso**.

**El visible.** La capa se pintaba sobre el **rectangulo que encierra al canton**,
con los bordes rectos a la vista, desbordando sobre cantones vecinos. Eso es un
defecto de implementacion y se arregla recortando.

**El de fondo, y es el que decide.** El riesgo se estima **por distrito**: un
valor por poligono. Interpolar por distancia inversa entre los centroides de ocho
poligonos **produce valores intermedios donde no hay ninguna medicion**, y los
pinta como un campo continuo.

Hay un paso silencioso ahi que es el error real: **tratar un agregado distrital
como si fuera una medicion puntual en el centroide**. El dato no dice que el
riesgo en el centro del distrito sea el que muestra; dice que el distrito
completo tiene ese nivel.

### Decision

**Se retira la capa del visor.** No se arregla el rectangulo.

Con ella salen `CapaMapaCalor.jsx`, `LeyendaMapaCalor.jsx`, `interpolacion.js` y
sus enganches en `App.jsx`, `MapaCanton.jsx`, `ControlCapas.jsx` y `capasBase.js`.
Es trabajo de Avril: se le pide, no se hace.

**H5.4 queda marcada `[x]`.** Lo hecho no se borra: la historia se hizo, se
evaluo y sus horas son reales. Se le agrega una nota de revision que apunta aca.
El trimestre se califica por contribucion individual, y retirar un entregable no
retira el trabajo de quien lo construyo.

### Justificacion

**Por que esto no es una cuestion de gusto.** Es el mismo principio que el
proyecto ya defendio tres veces del otro lado:

| Registro | Que se rechazo | Por que |
|---|---|---|
| **I-05**, **D-15** | NASA POWER para precipitacion | su celda no distinguia entre distritos |
| **D-21** | leer `probabilidad` como confianza | decia mas de lo que el numero sostiene |
| **D-22** | imputar faltantes que no existian | rellenar donde no hay dato |

**Rechazar una fuente por no resolver el canton y despues pintar un degradado
suave entre ocho valores no cierra.** Si el argumento contra POWER era que 68 km
de celda no permiten hablar por distrito, un mapa de calor que sugiere variacion
*dentro* del distrito afirma todavia mas.

**Por que retirar en vez de etiquetar.** La alternativa era arreglar el
rectangulo y agregar a la leyenda que la interpolacion es visual. Se descarta
porque **el problema no es que no se avise, es que se muestra**. Un degradado
continuo comunica resolucion espacial antes de que nadie lea la leyenda, y este
visor esta destinado al Comite Municipal de Emergencias.

**Por que ahora.** El sitio es publico desde el 20 de agosto y el Primer Avance
es esta semana.

### Alternativas descartadas

**Recortar la capa contra los poligonos y dejarla.** Arregla lo que se ve y deja
lo que importa. Ademas quedaria mas convincente, que es peor.

**Interpolar solo dentro de cada distrito.** Un valor constante por poligono no
tiene nada que interpolar: daria exactamente la coropleta de **H5.3**, con mas
codigo.

**Esperar a tener modelo entrenado.** No cambia nada. El problema no es que los
valores sean simulados, es que la estimacion es distrital cualquiera sea su
origen.

### Consecuencias

**Lo que se gana.** El visor deja de afirmar resolucion espacial que el dato no
tiene, antes de que lo vea el Comite Municipal.

**Lo que se pierde, y conviene decirlo con numeros.** H5.4 son **8 puntos y
12,5 horas** ya invertidas, con rubrica **CG-1**. La rubrica no queda huerfana:
**H5.3** la cubre cerrada y **H5.6** sigue abierta. Pero es trabajo hecho que
sale de pantalla.

**Lo que se conserva.** El codigo no se borra del historial. Si alguna vez el
proyecto midiera a resolucion sub-distrital —una malla CHIRPS, por ejemplo, que
reparte el canton en unas 36 celdas segun **D-15**— la interpolacion volveria a
tener sentido y el codigo esta en git.

**Lo que hay que revisar.** El documento IEEE menciona el mapa de calor entre las
capas del visor. Hay que corregirlo antes de entregarlo.

### Medicion

La captura del defecto:
`docs/evidencias/computacion-grafica/mapa-calor-rectangulo-2026-08-24.png`

Se comprueba de dos formas cuando Avril lo retire:

1. `frontend/dist/assets/*.js` **no menciona la interpolacion** tras construir
2. El control de capas del visor no ofrece la opcion

**Criterio de revision.** Se vuelve sobre esta decision **solo si el proyecto
empieza a estimar a resolucion menor que el distrito**. Mientras la unidad de
estimacion sea el distrito, no hay nada que interpolar.

---

## Como se agrega un registro

Copiar `docs/plantillas/plantilla-adr.md`, numerar con el siguiente `D-NN`,
agregar la fila al indice de arriba y abrir el Pull Request. Una decision que
deja atras a otra **no la borra**: la anterior cambia de estado y se queda donde
esta, entera.

Hay tres formas de dejar atras una decision, y no son intercambiables:

| Estado | Cuando | Ejemplo |
|---|---|---|
| **Revisada por D-NN** | El razonamiento sigue en pie; cambia una parte | D-08, cuando D-19 corrigio el ajuste del SPI |
| **Sustituida por D-NN** | El problema sigue existiendo y se resuelve de otra manera | — |
| **Revertida por D-NN** | La decision partia de un **hecho falso** y se deshace | D-28, revertida por D-30 |

La tercera se agrego el 2026-08-27. Llamarle "sustituida" a una decision tomada
sobre un hecho que no era cierto oculta justamente lo que hay que aprender. Ver
**I-14**.

---

## D-29 · El dataset se versiona por manifiesto en el repositorio y archivo fuera

**Estado.** Aceptada
**Fecha.** 2026-08-26
**Decide.** Alejandro, Lead PM
**Lo pide.** Cesar, que paro H1.7 antes de escribir porque el como no estaba anotado
**Desbloquea.** **H1.7**, 2,9 h

### Contexto

H1.7 pide versionar el dataset consolidado para reproducibilidad. El acuerdo
verbal existia desde la revision de H1.2 y **nunca se escribio**, asi que Cesar se
detuvo antes de implementarlo. Hizo bien: una decision no registrada implementada
en codigo es una decision que nadie puede auditar despues.

El dataset consolidado no es chico. Solo la serie climatica son **102 272 filas**,
mas 242 focos de calor dentro del canton y las geometrias oficiales del SNIT.

### Decision

**El manifiesto va al repositorio. El archivo, no.**

| Que | Donde | Por que |
|---|---|---|
| **Manifiesto** en texto: version, fecha, filas por tabla, ventana temporal, y la **suma SHA-256 de cada fuente** | **versionado**, en `basedatos/ddl/` | es lo que hace falta para saber que se uso, y pesa kilobytes |
| **El archivo** consolidado | **`release asset` de GitHub**, fuera del arbol | binario grande que cambiaria en cada recarga |

Reglas que lo acompanan:

1. **La suma de las geometrias del SNIT va dentro del manifiesto.** Es la fuente
   que ya nos fallo una vez -**I-03**- y la que produjo **I-10**. Si el SNIT
   republica su capa, la suma cambia y se ve.
2. **La primera version es igual al volcado que ya tiene Luna**, para que H1.5 y
   H1.7 describan el mismo dato y no dos fotos distintas.
3. **La version se declara, no se infiere.** `v1`, `v2`, con fecha. Un manifiesto
   sin numero de version obliga a comparar sumas para saber si algo cambio.
4. **Lo escribe un programa, no una persona.** Es **I-07**: una cifra derivada a
   mano se desfasa. El mismo patron de `procedencia-focos.md` y
   `procedencia-mediciones.md`, que ya se generan solos.

### Justificacion

El repositorio tiene que responder **«que dato produjo este resultado»** sin
guardar el dato. Un manifiesto con sumas lo responde: dos personas con el mismo
manifiesto pueden comprobar que tienen lo mismo, y quien lea el proyecto dentro de
un anio sabe exactamente que habia.

Meter el archivo al arbol lo haria crecer sin techo y ensuciaría cada `git diff`
con un binario que nadie puede revisar.

### Alternativas descartadas

| Alternativa | Por que se descarto |
|---|---|
| **DVC o Git LFS** | resuelven bien el problema y **agregan una herramienta mas** que las cuatro personas tendrian que instalar y aprender a dos semanas del cierre. La recarga completa toma 870 s: reproducir es viable sin ellas |
| **Versionar el CSV en el repositorio** | 102 272 filas en cada commit. El repositorio deja de ser revisable |
| **No versionar nada, basta la procedencia** | `procedencia-*.md` dice **como** se cargo, no **que** salio. Dos corridas del mismo cargador con el SNIT republicado dan procedencias identicas y datos distintos |
| **Guardarlo en la base y ya** | la base es un contenedor local que se borra con `docker compose down -v`. No es un archivo |

### Consecuencias

**H1.7 queda desbloqueada** y su alcance es exactamente: el programa que genera el
manifiesto, el manifiesto de la version 1, y la publicacion del archivo como
release asset.

**H1.5 de Luna gana un insumo**: el manifiesto le da los conteos por tabla que su
reporte de calidad tiene que explicar.

**Y queda una obligacion nueva**: cuando el dataset se recargue, el manifiesto se
regenera. Si alguien recarga y no lo regenera, el manifiesto miente. Eso hoy no lo
comprueba ninguna maquina, y **se anota como deuda**: el verificador que cruce el
manifiesto contra la base es trabajo pendiente, no parte de H1.7.

> **REVISADO POR D-31 el 2026-08-27.** Esta obligacion se escribio pensando en
> recargas ocasionales. Con H1.14 -ingesta recurrente- pasaria a incumplirse
> todos los dias, y perseguir un dataset que se mueve destruiria la propiedad que
> hace util al manifiesto: que dos personas con la misma version tengan lo mismo.
>
> **D-31 separa el recibo de carga de la version del dataset.** El manifiesto de
> esta decision es la *version*, y ya no tiene que regenerarse sola: se corta a
> mano. El registro por carga vive en la base.
>
> El generador de H1.7 no cambia. La regla 1 -que la suma del SNIT viaje dentro
> del manifiesto- sigue valiendo entera.

### Medicion

Esta decision se cumple, o no, de forma comprobable. Las cuatro condiciones:

1. **El manifiesto existe y lo genero un programa.** Se comprueba corriendo el
   generador dos veces sobre la misma base: **tiene que producir bytes identicos**.
   Si difiere, hay algo escrito a mano o una marca de tiempo que no deberia estar
   en el contenido versionado.

2. **Las sumas detectan un cambio de fuente.** Se comprueba alterando un byte de
   una fuente y regenerando: la suma correspondiente **tiene que cambiar**. Un
   manifiesto cuya suma no se mueve ante un cambio no protege de nada.

3. **Los conteos del manifiesto coinciden con la base.** La cifra de referencia de
   la version 1, medida hoy:

       geo.distrito            8 distritos
       crudo.medicion_diaria   102 272 filas, 1991-01-01 a 2025-12-31
       crudo.foco_calor        242 dentro del canton, 2001-01-01 a 2024-12-31

   Si el manifiesto declara otra cosa sin que nadie haya recargado, **el
   manifiesto esta mal**, no la base.

4. **La version 1 coincide con el volcado de Luna.** Se comprueba contra el que ya
   uso para H2.3 y H2.7: mismas filas, misma ventana. Si no coinciden, H1.5 y H1.7
   estarian describiendo dos datos distintos y el reporte de calidad no aplicaria
   al dataset publicado.

**Lo que esta decision NO mide**, y queda escrito para no confundirlo: que el dato
sea correcto. El manifiesto prueba que dos personas tienen **lo mismo**, no que
ese algo este bien. La calidad la mide H1.5.

---

## D-30 · El mapa de calor vuelve, recortado contra los poligonos

**Estado.** Aceptada · **revierte D-28**
**Fecha.** 2026-08-27
**Decide.** Alejandro, Lead PM
**Lo detecta.** Alejandro, al contrastar D-28 contra la evidencia que la origino
**Afecta.** Restituye el entregable de **H5.4**. Revierte parcialmente **H5.8**.

### Contexto

D-28 retiro la capa de mapa de calor el 24 de agosto, sobre la base de que
interpolar entre los centroides de ocho poligonos afirma una resolucion espacial
que el dato no tiene.

**Ese argumento nunca lo hizo el profesor.** Lo que dijo esta escrito, textual,
en `docs/evidencias/computacion-grafica/retroalimentacion-docente-visor-2026-08-24.md`:

> *"La capa de calor se pinta sobre el rectangulo que encierra al canton, con los
> bordes rectos a la vista, en vez de recortarse contra los poligonos
> distritales"*

Y, en la misma conversacion, que **se salia del canton y habia distritos que no
marcaba**. La transparencia le parecio bien.

Eso es un **defecto de render**, y tiene arreglo. El argumento conceptual -que
interpolar produce valores donde no hay medicion- se agrego despues, del lado del
equipo, y sobre el se decidio retirar la capa. El propio texto de D-28 dice que
son *"dos problemas de distinto peso"* y a renglon seguido los junta.

**Lo que costo.** 515 lineas, tres modulos y el entregable de una historia
cerrada, retirados por un problema que el arreglo corrige en dos lineas.

### Decision

**La capa vuelve, con el defecto arreglado.** El arreglo tiene dos mitades y
**ninguna alcanza sola**:

1. **El encuadre sale de los poligonos, no de los centroides.** Un centroide esta
   por definicion adentro de su distrito: encuadrar sobre ellos deja afuera la
   mitad exterior de los distritos del borde. El `margen = 0.03` que habia estaba
   puesto para tapar el corte recto y no compensaba eso.
2. **El lienzo se recorta contra la union de los poligonos**, con
   `destination-in` y regla par-impar, antes de colocarse. El borde de la
   superficie pasa a ser el limite del canton.

**Lo que no se toca:** la opacidad, la rampa BuPu de **D-21**, los ocho puntos de
origen dibujados encima y la leyenda que declara sobre cuantos se calculo. Nada
de eso tenia defecto.

### Justificacion

**Por que la objecion conceptual de D-28 no sostiene el retiro.** Sigue siendo
cierto que la estimacion es distrital y que un degradado continuo sugiere mas
resolucion de la que hay. Pero eso **ya estaba resuelto por diseño y esta escrito
en el codigo desde H5.4**: los ocho puntos de origen se dibujan *encima* de la
superficie justamente para que se vea de donde sale cada valor, y la leyenda
declara el conteo. La capa viene apagada por defecto.

D-28 trato ese riesgo como si no estuviera atendido. Estaba, y con el mismo
criterio que **D-07** y **D-22**: no se rellena donde no hay dato, se declara.

**Por que las dos mitades.** Medido sobre las geometrias del SNIT con
`frontend/herramientas/verificar_recorte_calor.mjs`:

| encuadre | pintado fuera del canton | canton sin pintar |
|---|---|---|
| centroides + 0,03 (lo que habia) | 23,8 % | 20,7 % |
| poligonos, sin recortar | 40,5 % | 0,0 % |
| **poligonos + recorte** | **0,0 %** | **0,0 %** |

Encuadrar sobre los poligonos y no recortar **empeora** el desborde, porque la
caja envolvente de una forma irregular es mucho mayor que la forma. Recortar sin
corregir el encuadre quita el desborde y deja los mismos huecos. La tabla es la
razon por la que el arreglo no es una linea.

**Por que un verificador y no una captura.** Es el aprendizaje de **I-06** y
**I-10** aplicado otra vez: este defecto vivio cuatro dias en el sitio publico
porque solo se veia mirando. Ahora hay una maquina que lo mira en cada Pull
Request, y que **falla si alguien vuelve a encuadrar sobre los centroides**.

### Alternativas descartadas

**Dejar la capa retirada y no volver sobre D-28.** Es la mas comoda y la peor: el
registro quedaria como precedente de que se puede retirar un entregable ajeno
sobre un hecho no verificado.

**Corregir el texto de D-28 en su lugar.** Se descarta por la misma razon por la
que D-08 y D-14 se conservan revisadas y no reescritas: una bitacora que se edita
para quedar bien deja de servir para aprender. D-28 se queda entera, con el aviso
arriba.

**Recortar con `clip-path` sobre el elemento ya colocado.** Se expresaria en
pixeles de pantalla y habria que recalcularlo en cada zoom. El recorte sobre el
lienzo se hace una vez.

**Regla `nonzero` en vez de `evenodd`.** El GeoJSON del SNIT no garantiza la
regla de la mano derecha, y con `nonzero` un anillo interior escrito al reves
quedaria relleno.

### Consecuencias

**Se restituye H5.4** con su entregable en pantalla. Sus 8 puntos y 12,5 horas
vuelven a corresponder a algo que existe.

**Se revierte parcialmente H5.8.** Ver **I-14**: el encuadre ajustado al canton
salio de la misma lectura. Se conserva de esa historia la marca de seleccion
accesible y el `zoomSnap`, que no dependian de ella.

**El documento IEEE vuelve a estar bien** en la parte que menciona el mapa de
calor entre las capas del visor. Lo que D-28 mandaba corregir ya no hay que
corregirlo.

**Queda una deuda medida, no inventada.** Los ocho poligonos simplificados **no
teselan**: su union deja 142 huecos diminutos entre distritos vecinos. No afecta
a esta capa -la tolerancia del verificador los cubre- pero esta anotado por si
alguna vez importa.

### Medicion

`node frontend/herramientas/verificar_recorte_calor.mjs`, en el CI desde este
cambio. Corre `dibujarSuperficie()` de verdad sobre un canvas simulado y compara
lo pintado contra una implementacion **independiente** de punto-en-poligono por
lanzamiento de rayos, escrita aparte. Dos algoritmos distintos que tienen que
coincidir; si compartieran codigo, un error estaria en los dos.

Comprueba, sobre 86 576 muestras:

1. El encuadre contiene **los ocho distritos enteros**
2. **0 km2** pintados fuera del canton
3. **0 km2** del canton sin pintar
4. Que el estado anterior **si falla** las dos anteriores, o sea que la medicion
   distingue. Sin esta cuarta, las tres primeras podrian estar pasando por no
   medir nada.

**Criterio de revision.** Se vuelve sobre esta decision si el visor pasara a
estimar a una resolucion distinta de la distrital, o si aparece evidencia de que
un lector interpreta la superficie como medicion continua pese a los puntos de
origen. Lo segundo se sabra en **H9.2a**, la validacion externa.

---

## D-31 · El recibo de carga y la version del dataset son dos artefactos

**Estado.** Aceptada · **revisa D-29**
**Fecha.** 2026-08-27
**Decide.** Alejandro, Lead PM
**Lo detecta.** Cesar, al revisar si H1.14 tiene sentido sin base alojada
**Afecta.** **H1.7** (cerrada), **H1.14**, y la trazabilidad de las cifras del
documento IEEE.

### Contexto

**D-29** decidio versionar el dataset por manifiesto: un documento con sumas
SHA-256 de cada fuente, sus conteos y sus rangos temporales, que responde *«¿dos
personas tienen exactamente lo mismo?»*.

Esa decision se tomo pensando en **recargas ocasionales**, y lo dejo escrito como
deuda: *si alguien recarga y no lo regenera, el manifiesto miente*.

**H1.14 convierte esa deuda de excepcion en rutina.** Si la ingesta corre a
diario, el manifiesto queda desactualizado **todos los dias**. Cesar lo planteo
como una eleccion entre dos disenos:

1. que H1.14 regenere el manifiesto al terminar cada carga, o
2. que el manifiesto pase a ser una foto fechada de una carga concreta.

### Decision

**Ninguna de las dos, porque la pregunta esta mal planteada.** El manifiesto esta
haciendo **dos trabajos que no son el mismo**, y por eso ninguna respuesta cierra:

| | Que responde | Cada cuanto | Quien lo produce | Donde vive |
|---|---|---|---|---|
| **Recibo de carga** | ¿que entro, cuando, con que sumas? | una por carga | el cargador | la base, en `control` |
| **Version del dataset** | ¿vos y yo tenemos lo mismo? | cuando alguien la corta | una persona | el repositorio |

D-29 describio el segundo, y el cargador termino produciendo el primero. De ahi
la contradiccion.

**Se separan:**

1. **El recibo de carga va a la base**, no a un archivo del repositorio. Una fila
   por carga en el esquema `control`: producto, rango de fechas, filas
   insertadas, sumas y momento. Es registro de lo que la base contiene, y la base
   es donde vive.

2. **La version del dataset se corta a mano**, con el generador de H1.7 sin
   cambios. Congela, se numera, y **es lo que citan los resultados**. Deja de
   intentar describir algo que se mueve.

3. **`basedatos/ddl/procedencia-*.md` deja de ser un archivo que el cargador
   escribe** y pasa a ser una vista generada desde los recibos, producida por
   alguien con copia de trabajo cuando hace falta.

### Justificacion

**Una version que se regenera sola no es una version.** Es la foto de ayer. La
seccion VI del documento IEEE no puede citar «la ultima carga»: tiene que citar
algo que no se mueva, o el resultado deja de ser reproducible en el sentido en
que D-29 lo prometio.

**Y un cargador que escribe dentro del arbol de git asume una persona sentada
frente al repositorio.** Lo reporto Cesar y es el mismo patron que ya aparecio
con `trazabilidad.csv`: un artefacto que el repositorio necesita, producido por
algo que no es un humano con copia de trabajo. Una ingesta programada en un
contenedor efimero escribiria esos archivos donde nadie los va a ver nunca.

**Por que el recibo va a la base y no a un archivo.** Porque describe el estado
de la base, y porque es el unico lugar al que un proceso automatico puede
escribir sin credenciales de git. Es la misma separacion que el proyecto ya hace
entre `crudo` -lo descargado- y `analitico` -lo derivado-, aplicada al registro
de la propia descarga.

**Lo que esto le devuelve a D-29.** Su regla 1 -que la suma del SNIT viaje dentro
del manifiesto, porque esa fuente ya fallo en I-03 y produjo I-10- **sigue
valiendo entera**. Lo que cambia es que el manifiesto ya no tiene que perseguir
un dataset que se mueve.

### Alternativas descartadas

**Que H1.14 regenere el manifiesto en cada carga.** Es la opcion 1 de Cesar.
Convierte el manifiesto en un archivo que cambia a diario dentro del repositorio,
y obliga al proceso automatico a hacer commit. Ademas destruye la propiedad que
lo hacia util: dos personas con la misma «version 1» dejarian de tener lo mismo.

**Que el manifiesto sea una foto fechada.** Es la opcion 2. No resuelve nada:
sigue habiendo un solo artefacto tratando de responder dos preguntas, y la
pregunta de reproducibilidad se queda sin respuesta.

**No hacer nada hasta que la base este alojada.** Tentador, porque hoy no hay
ingesta programada. Se descarta porque H1.14 se cierra antes que el alojamiento,
y cerrarla sin esta decision la obligaria a elegir una de las dos opciones malas.

**Un `control.carga` con la fila entera del manifiesto en JSON.** Guardar el
documento en vez de sus campos. Se descarta porque un JSON opaco en una columna
no se puede consultar: la pregunta «¿cuando se recargo CHIRPS por ultima vez?»
volveria a requerir leer archivos.

### Consecuencias

**H1.7 no se reabre.** Su generador sirve igual, y lo que produce pasa a llamarse
por su nombre: una version, no un estado.

**H1.14 se simplifica.** No tiene que regenerar nada; emite su recibo y termina.
Se renombra el mismo dia a **«Ingesta reejecutable con cadencia declarada por
evento y producto declarado»**, porque *periodica* no lo puede cumplir sin
alojamiento.

**Aparece trabajo nuevo, y se declara en vez de esconderse:** la tabla del recibo
y la vista generada de procedencia. Va a la historia de alojamiento, que todavia
no esta abierta.

**El documento IEEE gana una frase que hoy no puede escribir**, y la va a
necesitar: *los resultados de la seccion VI se calcularon sobre la version N del
dataset*. Hoy diria «sobre el dataset», que no identifica nada.

### Medicion

Se comprueba cuando exista la tabla del recibo:

1. **Dos cargas seguidas producen dos recibos y una sola version.** Si producen
   dos versiones, la separacion no se aplico.
2. **La version no cambia sin que una persona la corte.** Correr la ingesta no
   toca ningun archivo del repositorio.
3. **El recibo permite responder «¿cuando se recargo CHIRPS?» con una consulta**,
   sin abrir un archivo.
4. **La vista de procedencia se puede regenerar y sale identica** mientras no
   haya cargas nuevas. Es la misma propiedad que se le exige a la matriz de
   trazabilidad y a los diagramas.

**Lo que esta decision NO resuelve**, y queda escrito: dónde corre la ingesta. Esa
es la historia de alojamiento, con su propia decision.

**Criterio de revision.** Se vuelve sobre esto si el dataset dejara de recargarse
-en cuyo caso la separacion sobra y D-29 alcanza- o si apareciera una herramienta
de versionado de datos que el equipo ya use por otro motivo, que es la condicion
con la que D-29 descarto DVC.


## D-32 · La escala del SPI se decide midiendo, no por costumbre

**Estado.** Aceptada · **revisa D-19** · **medida y resuelta: SPI-6**
**Fecha.** 2026-08-30
**Decide.** Alejandro, Lead PM
**Lo detecta.** Al leer completa la referencia `[15]`, que ya se citaba
**Afecta.** **D-19**, el etiquetado de sequia de H3.0, y las conclusiones sobre
sequia del documento de investigacion.

### Contexto

**D-19 fijo SPI-3 y nadie lo midio.** Se adopto porque es la escala mas comun en
la literatura de sequia agricola. Es un argumento de costumbre.

La referencia `[15]` -Quesada-Hernandez, Hidalgo y Alfaro, 2020- se citaba desde
H10.5a como respaldo local de que el SPI es pertinente en Guanacaste. **Su ficha
se habia escrito sobre el resumen.** Leido el articulo completo el 2026-08-30,
dice tres cosas que la ficha no recogia:

1. **Evalua SPI-6 y SPI-12. No evalua SPI-3.** El SPI-12 se toma en diciembre,
   para describir el ano; el SPI-6 en octubre, para la estacion lluviosa del
   Pacifico. Concluye que esas dos son las mejor asociadas con impactos
   socio-productivos reales.
2. **Trabaja a escala cantonal, no distrital**, teniendo disponibles registros de
   distrito. Es una decision del trabajo mas cercano al nuestro, en sentido
   contrario al nuestro.
3. Integra **cuatro** fuentes de impacto -DesInventar, EM-DAT, IMN y prensa-, no
   una.

Es decir: **la referencia que citabamos como respaldo de nuestra escala no
respalda nuestra escala.** Respalda la familia del indice y otras dos escalas
concretas, en la misma provincia.

### Decision

**No se cambia a SPI-6 ni se defiende SPI-3 con argumentos. Se miden las tres y
se decide con el dato.** `backend/modelado/comparar_escalas_spi.py` rehace el
etiquetado de sequia completo para SPI-3, SPI-6 y SPI-12 -mismos cortes de
McKee, mismo ajuste gamma por mes calendario- y contrasta cada uno contra el
catalogo.

### Justificacion

Tres razones para medir en vez de adoptar la escala de la referencia:

- **La referencia no es nuestra unidad.** Trabaja por canton, con estaciones
  meteorologicas; nosotros por distrito, con CHIRPS. Adoptar su conclusion sin
  medir seria repetir el error de D-19 con otra escala: reemplazar una costumbre
  por otra.
- **Ya sabemos que la respuesta puede ser «no se puede saber».** Con siete
  registros, los siete con la misma fecha, es probable que las tres escalas
  queden empatadas. Eso tambien es un resultado, y hace falta poder decirlo con
  un numero al lado en vez de con una opinion.
- **La herramienta sirve despues.** Si aparecen mas registros -y `[15]` muestra
  el camino, integrar IMN y prensa a DesInventar-, la comparacion se vuelve a
  correr sin escribir nada nuevo.

Y una razon de forma: **la ficha de `[15]` se habia escrito sobre el resumen.**
Este registro existe porque leer el articulo completo cambio lo que sabiamos.
El criterio que se saca de ahi, y que aplica a toda la bibliografia, es que un
resumen alcanza para decidir si una referencia es pertinente y **no** alcanza
para apoyarse en ella.

### Lo que la comparacion reporta, y por que asi

**Todo con intervalo de Wilson al 95 %.** Es el segundo cambio que trae esta
decision: el documento reportaba proporciones como puntos -«64,7 % de cobertura»
sobre 34 eventos- y **sin intervalo no se puede afirmar que 64,7 % y 13,7 % son
distintos**. Se usa Wilson y no el intervalo de Wald por `[34]`: Wald es
erratico con muestras chicas y ademas colapsa a [0, 0] cuando la proporcion es
cero, que es exactamente nuestro caso en sequia.

**El realce decide, no la cobertura.** Una escala larga marca mas dias por
construccion: el SPI-12 senala rachas de un ano donde el SPI-3 senala rachas de
un trimestre. Comparar coberturas premiaria a la escala larga por la razon
equivocada.

**La ventana estricta compara; la ventana propia diagnostica.** Cada escala se
contrasta ademas con su periodo de integracion -90, 180 y 360 dias-, pero eso
**no** entra en la comparacion: una ventana mas larga detecta mas por
construccion. Se reporta al lado.

**Y se cuentan los episodios, no solo los dias.** Dos escalas pueden marcar el
mismo numero de dias repartidos en muy distinto numero de rachas. Los episodios
son el tamano de muestra efectivo para cualquier modelo que se entrene despues.

### Medicion

La herramienta corre en el CI con `--sintetico`, que comprueba el camino de
calculo y **no concluye nada** sobre las escalas: lo declara en su primera
linea. La medicion que decide se corre contra la base:

    python -m backend.modelado.comparar_escalas_spi --fallos

**Criterio de aceptacion de la decision, fijado antes de ver el resultado**,
que es la mitad del valor de fijarlo:

1. **Si los intervalos de cobertura de las tres se solapan, se mantiene SPI-3** y
   se declara en el documento que la escala no esta respaldada por medicion
   propia ni por la referencia local. No se cambia de escala por una diferencia
   puntual que la muestra no sostiene.
2. **Si una escala separa su intervalo de las otras dos y su realce excluye el
   1,0**, se adopta esa escala y se revisa D-19.
3. **Si ninguna escala excluye el 1,0 de su realce**, ninguna distingue, y eso se
   escribe tal cual: es un resultado sobre el catalogo, no sobre las escalas.

### Lo que se midio, el 2026-08-30

| Escala | Cobertura, IC 95 % | Realce, rango | Tasa base | Episodios |
|---|---|---|---|---|
| **SPI-3** | 0 % [0 %, 35,4 %] | 0,00 [0,00, **2,38**] | 15,1 % | 204 |
| **SPI-6** | 100 % [64,6 %, 100 %] | 6,50 [4,13, 6,59] | 15,4 % | 129 |
| **SPI-12** | 100 % [64,6 %, 100 %] | 5,39 [3,43, 5,46] | 18,6 % | 68 |

**El criterio no anticipo este caso, y hay que decirlo.** Se escribio pensando
en «una gana» o «empatan todas». Lo que salio es **una pierde y dos empatan**:
el intervalo del SPI-3 no toca el de las otras dos, pero SPI-6 y SPI-12 no se
separan entre si.

Eso obligo a corregir la herramienta antes de leer el resultado. `veredicto()`
buscaba la de mayor cobertura, veia el solape entre SPI-6 y SPI-12 y devolvia
«sin veredicto», **enterrando el unico hallazgo accionable**: que la escala en
uso habia quedado descartada. Ahora descarta primero y empata despues, que es el
orden correcto cuando la muestra es chica. Queda cubierto por
`test_descarta_la_escala_separada_hacia_abajo`.

**SPI-3 queda descartado**, por dos razones que apuntan al mismo lado:

- Su intervalo, 0 %-35,4 %, esta enteramente por debajo del de las otras dos.
- El **1,0 cae dentro del rango de su realce**, [0,00, 2,38]: ante el unico
  episodio que el catalogo permite probar, marcaba con la misma frecuencia que
  un dia cualquiera.

Y el fallo **no es aleatorio**: la marca mas cercana quedo a **-37 dias, el
mismo -37 en los ocho distritos**. Una coincidencia se dispersa entre distritos;
un valor identico en los ocho es la firma de algo estructural. Lo es: **el SPI-3
sale de sequia antes de que el dano se declare.** Integra tres meses, y para
fines de septiembre de 2014 las lluvias de setiembre ya lo habian recuperado
mientras la declaratoria se emitia el dia 30.

### Por que SPI-6 y no SPI-12, dicho sin disimular

**El catalogo no los separa.** Los dos dan 7 de 7 con intervalos identicos. La
eleccion se hace por otro criterio, y corresponde declarar cual:

| | SPI-6 | SPI-12 |
|---|---|---|
| Episodios | **129** | 68 |
| Tasa base | **15,4 %** | 18,6 % |
| Realce puntual | **6,50** | 5,39 |

- **Episodios: casi el doble.** Es el tamano de muestra efectivo para cualquier
  modelo que se entrene despues. Con 68 episodios repartidos en ocho distritos y
  cinco pliegues, no queda sequia suficiente en cada pliegue.
- **Menor tasa base para la misma deteccion.** SPI-12 marca 3,2 puntos mas de
  dias para detectar lo mismo: avisa mas para acertar igual.
- **`[15]` toma el SPI-6 en octubre** para describir la estacion lluviosa de la
  vertiente del Pacifico, que es el regimen de Tilaran. El SPI-12 lo toma en
  diciembre para el balance anual.

El realce puntual favorece al SPI-6, pero **sus rangos se solapan** —[4,13, 6,59]
contra [3,43, 5,46]— asi que no decide, y no se usa como si decidiera.

### La advertencia que ningun intervalo da por si solo

**Los siete registros son una fecha en siete distritos, no siete episodios.**
El intervalo de Wilson los cuenta como siete extracciones independientes y no lo
son: el *n* efectivo esta mas cerca de **uno**. La herramienta ahora lo calcula
e imprime siempre, en vez de confiar en que quien lee la tabla se acuerde.

La consecuencia es que **el resultado es asimetrico**:

- El **100 %** de SPI-6 y SPI-12 no corona a nadie. Confirmar con *n* efectivo
  de uno no establece nada general.
- El **0 %** de SPI-3 si lo descarta. Falsar es mas barato que confirmar: si una
  escala no marca el unico episodio que el catalogo permite probar, y falla de
  forma identica en los ocho distritos, ese episodio alcanza para dudar de ella.

Asi hay que escribirlo en el documento. **No** «medimos y SPI-6 es la mejor»,
sino «SPI-3 falla el unico caso comprobable de forma sistematica; entre SPI-6 y
SPI-12 el catalogo no decide y elegimos SPI-6 por numero de episodios».

### Alternativas descartadas

**Cambiar a SPI-6 sin medir, siguiendo a `[15]`.** Descartada. Es el atajo que
parece prudente -alinearse con la literatura local- y repite exactamente el
error que se esta corrigiendo: adoptar una escala por autoridad ajena en vez de
por evidencia propia. Ademas `[15]` mide sobre estaciones y por canton; sus
conclusiones no se transportan sin mas a celdas CHIRPS por distrito.

**Mantener SPI-3 y no decir nada.** Descartada, y es la alternativa que habria
sido invisible: nadie iba a notar la diferencia entre lo que dice `[15]` y lo
que hacemos, porque para notarla habia que leer el articulo completo. Callarlo
habria dejado en el documento una cita que aparenta respaldar algo que no
respalda.

**Reportar las tres escalas sin veredicto, como informacion.** Descartada. Un
documento de investigacion que enumera tres opciones y no se compromete no
decidio nada; y el criterio de aceptacion de abajo se fija **antes** de ver el
resultado justamente para no poder escurrir la decision despues.

**Ampliar primero el catalogo y medir despues.** Tentadora, porque el problema
real es el tamano de muestra. Descartada por orden: integrar IMN y prensa es
trabajo de campo de varias semanas y hay que decidir la escala para la entrega.
La herramienta queda escrita para volver a correrla cuando el catalogo crezca,
que es lo que convierte esto en un aplazamiento honesto y no en un olvido.

**Usar el intervalo de Wald por ser el conocido.** Descartada por `[34]`:
colapsa a [0, 0] con proporcion cero, que es nuestro caso en sequia, y declara
certeza absoluta donde menos informacion hay.

### Consecuencias

**A favor.**

- La escala del SPI pasa de ser una costumbre a ser una decision con criterio
  escrito y comprobable.
- El proyecto gana intervalos de confianza donde antes reportaba puntos, y eso
  se derrama sobre **todas** las proporciones del documento, no solo sobre
  sequia. La cobertura de lluvia -22 de 34- deja de ser un numero suelto.
- Queda una herramienta que se vuelve a correr sola cuando cambie el catalogo.
- El criterio sobre fichas escritas desde el resumen queda registrado y se puede
  aplicar hacia atras sobre el resto de la bibliografia.

**En contra, y se asume.**

- **Hay que reetiquetar y volver a medir todo lo que dependia de la sequia.**
  `etiquetas.csv` se regenera, las lineas base de H3.6 se vuelven a correr, y
  las cifras de sequia del documento cambian. Es el costo de haber fijado la
  escala sin medirla en D-19: se paga entero y con retraso.
- **El criterio de aceptacion no cubrio el caso que salio.** Anticipaba «una
  gana» o «empatan todas», y salio «una pierde y dos empatan». Se corrigio la
  herramienta antes de leer el resultado, no despues, pero el hecho es que el
  criterio estaba incompleto.
- Los intervalos suponen observaciones independientes y no lo son: el SPI de un
  mes es constante dentro del mes y los distritos comparten celdas de la fuente.
  Son, si acaso, **optimistas**, y hay que declararlo cada vez que se citan.
- **La eleccion entre SPI-6 y SPI-12 no la decidio el catalogo.** La decidio el
  numero de episodios. Es un criterio razonable y no es evidencia externa, y el
  documento tiene que presentarlo como lo que es.
- Aparece una segunda diferencia con `[15]` que esta medicion **no** resuelve:
  **la escala espacial.** Ellos eligieron canton teniendo el distrito
  disponible; nosotros elegimos distrito. Eso va a amenazas a la validez y no se
  arregla aqui.

**Criterio de revision.** Se vuelve sobre esto cuando el catalogo crezca. Con
siete registros de una sola fecha, cualquier veredicto es fragil, y la propia
`[15]` muestra el camino para ampliarlo: integrar IMN y prensa a DesInventar.

---

## D-33 · Las historias abiertas de Cesar y Avril en S1 y S2 pasan al PM

**Fecha.** 2026-08-31 · **Decide.** Alejandro (PM) · **Estado.** Aceptada

### Contexto

Semana 9 de 12. **El Sprint 1 vencio en la semana 5 y sigue abierto**: 11 de 16
historias. El Sprint 2 vencio en la semana 7 y va en 11 de 23. El Sprint 4, que
arranca en la semana 10, no tiene ninguna historia empezada.

Estado por persona al momento de decidir, calculado con `verificar_estado.py`:

| | Cerradas | Puntos | Ultimo commit en `dev` |
|---|---|---|---|
| Luna | 12/17 · 71 % | 65/80 · 81 % | 2026-08-30 |
| Alejandro | 11/23 · 48 % | 59/126 · 47 % | 2026-08-28 |
| Cesar | 9/28 · 32 % | 38/131 · 29 % | **2026-08-27** |
| Avril | 7/21 · 33 % | 35/97 · 36 % | **2026-08-26** |

Cesar y Avril llevan **cinco y seis dias sin subir nada**, y no respondieron a
las consultas enviadas por escrito el 2026-08-28 y el 2026-08-30.

### Decision

**Las 12 historias abiertas de Cesar y Avril en S1 y S2 quedan a nombre del PM**:
58 puntos, 67.2 horas.

    S1  H1.15  H1.13  (Cesar)     H1.6  (Avril)
    S2  H1.9  H1.11  H1.12  H2.5  H3.3  (Cesar)
        H5.6  H7.2  H10.3  H10.7  (Avril)

El contenido de cada historia se traspasa **sin modificar**. No es una
reduccion de alcance ni una correccion del trabajo previo.

### Justificacion

Esperar ya se probo. Entre el 2026-08-26 y el 2026-08-31 no hubo un solo
commit de ninguno de los dos, con dos consultas escritas sin responder. Una
quinta semana de espera es la misma apuesta que ya fallo cuatro veces, y el
Sprint 4 arranca en la semana 10.

### Consecuencias, declaradas aqui y no descubiertas despues

La carga del PM queda asi:

| Sprint | Horas | Compromiso | Exceso |
|---|---|---|---|
| S1 | 36.4 | 36 | +0.4 |
| **S2** | **113.1** | 36 | **+77.1** |
| S3 | 40.4 | 36 | +4.4 |
| S4 | 52.8 | 36 | +16.8 |

**Total pendiente del PM: 185.6 horas. Quedan unas tres semanas. Son 62 h por
semana contra un compromiso de 18.**

**Esta decision no cabe en el calendario y se toma sabiendolo.** Se registra el
numero para que quede claro que no se decidio por desconocerlo: se decidio
porque la alternativa -esperar- ya se probo durante cinco semanas y produjo un
Sprint 1 abierto en la semana 9.

Lo que sigue de aqui es una de dos, y conviene decirlo ahora:

1. **Se cierra menos de lo asignado.** El incumplimiento pasa a ser del PM
   aunque el origen sea ajeno, porque el tablero dira que las historias eran
   suyas.
2. **Se recortan alcances o se pide ayuda.** Luna se ofrecio por escrito el
   2026-08-30 y tiene 32 h pendientes, la carga mas baja del equipo.

### Alternativas descartadas

| Alternativa | Por que no se eligio |
|---|---|
| Repartir entre el PM y Luna | La preferencia del PM fue no cargar a quien si viene cumpliendo. Es la unica alternativa que cabia en el calendario |
| Reasignar solo lo que bloquea a otros | Deja el Sprint 1 abierto, que es lo que la decision busca cerrar |
| Esperar y escalar al docente | Se mantiene disponible, no excluye lo anterior |

### Lo que esta decision NO hace

**No cierra las historias de S3 y S4 de Cesar y Avril**, que siguen a su nombre:
81 h de Cesar y 61.6 h de Avril. Reasignar todo seria declarar que ya no se
espera nada de ellos, y eso no se ha decidido.

**No borra el registro.** Las historias traspasadas llevan la nota en
`docs/tareas/alejandro.md` con la fecha y el origen. El historial de git
conserva a quien estuvieron asignadas y desde cuando.

**Y no es una evaluacion del trabajo hecho.** Lo que Cesar y Avril cerraron esta
en la matriz de trazabilidad con su evidencia, y varias de esas historias son
dependencias de las que siguen abiertas.

### Medicion

Se da por buena si el **Sprint 1 queda cerrado -16 de 16- antes del cierre de
la semana 10**, que es el unico resultado que justifica haberla tomado.

Se revisa si al cierre de la semana 10 el PM cerro **menos de 40 de las 67.2
horas** traspasadas. Ese umbral no es una meta: es el punto en que insistir
cuesta mas que recortar alcance o aceptar la ayuda de Luna.

Las dos cifras salen de `verificar_estado.py`, no de una apreciacion.

### Como se revierte

Si Cesar o Avril retoman, se devuelve la historia con el mismo procedimiento y
un registro nuevo. **No hay que preguntar**: quien quiera retomar algo suyo lo
avisa y se le devuelve.

### Evidencia

`docs/evidencias/gestion/D-33-atraso-y-reasignacion.md`

---

## D-34 · Los episodios se cuentan a nivel canton, y la sequia no es modelable

**Fecha.** 2026-09-01 · **Decide.** Alejandro · **Estado.** Aceptada
**Revisa.** D-32 · **Afecta.** H3.0 (CA-6), H3.3, H3.6 y el documento IEEE

### Contexto

CA-6 de H3.0 fija, **antes de mirar el dato**, cuando un evento no se modela:

    menos de 30 ventanas positivas en total             -> no se modela
    menos de 10 en cualquier particion de entrenamiento -> no se modela

Al preparar H3.3 se fue a comprobar ese segundo umbral y aparecieron **dos
defectos en como se estaba evaluando**, no en el criterio.

### Defecto 1 · Se comparaba un promedio contra un minimo

`generar_etiquetas.py` dividia los episodios totales entre cinco pliegues
supuestos. El comentario decia por que -H3.2 no existia cuando se escribio- y
**dejo de ser cierto el dia que H3.2 se cerro, sin que nada avisara**.

CA-6 dice «en **cualquier** particion». Eso es un minimo. Con ventana expansiva
el pliegue 1 entrena con la rebanada mas chica y el 5 con casi toda la serie, asi
que promedio y minimo no son intercambiables.

### Defecto 2 · Los episodios estaban inflados por distrito

Se contaban rachas de dias ALTO **por distrito y se sumaban**. Una sequia que
pega en los ocho distritos a la vez cuenta ocho veces.

**No es un detalle: seis de las trece sequias del periodo pegan en los ocho.**

    distritos afectados     episodios del canton
      1 distrito                  2
      3 distritos                 2
      5 distritos                 1
      6 distritos                 2
      8 distritos                 6

El proyecto **ya habia aplicado este razonamiento en otro lado**:
`comparar_escalas_spi.py` declara que «los 7 registros son 1 fecha x 7 distritos,
asi que n efectivo ~ 1» al contrastar el catalogo. Lo que faltaba era aplicarlo
a CA-6.

### Decision

**Los episodios se cuentan a nivel canton.** Un episodio es una racha de dias en
que **algun** distrito esta en ALTO. Y **CA-6 se evalua contra el minimo por
pliegue de entrenamiento**, no contra el promedio.

Con eso, **la sequia no es modelable** y se declara asi.

### Medicion

    evento           por distrito   canton real   inflacion
    lluvia_intensa            496           163        3,0x
    sequia                     78            13        6,0x
    incendio                  106            67        1,6x

Episodios independientes en el **entrenamiento** de cada pliegue:

    lluvia_intensa    31 · 60 · 89 · 109 · 129    minimo 31   modelable
    sequia             2 ·  3 ·  3 ·   6 ·   9    minimo  2   NO MODELABLE
    incendio          16 · 21 · 28 ·  44 ·  55    minimo 16   modelable

**La sequia no falla por poco: falla en los cinco pliegues.** El mas rico tiene
9 y el umbral es 10.

**La inflacion tampoco es pareja** -3,0x contra 6,0x contra 1,6x-, asi que el
conteo por distrito ni siquiera sobreestimaba de forma consistente: distorsionaba
la comparacion **entre** eventos.

### Justificacion

Contar por distrito supondria que ocho filas del mismo dia son ocho
observaciones. Comparten el fenomeno meteorologico, y **los ocho distritos
comparten ademas la misma celda de NASA POWER** -(-85,0 · 10,5), medido en
H1.5-, asi que buena parte de sus variables son literalmente el mismo numero.

Un modelo que las trate como independientes cree tener ocho veces mas evidencia
de la que hay. Es el mismo error que D-32 ya habia declarado al medir el
catalogo, y sostenerlo aca y no alla seria incoherente.

### Consecuencias

**El alcance del modelado baja de tres eventos a dos.** H3.3, H3.4 y H3.5
comparan algoritmos sobre lluvia intensa e incendio. La sequia entra a la tabla
de H3.6 **declarada no modelable con su medicion al lado**, no omitida.

**Y esto es un resultado, no una perdida.** D-32 cambio la escala del SPI de 3 a
6 porque el contraste contra el catalogo daba **0 de 7**; con SPI-6 da **7 de 7**.
La misma decision que arreglo la validacion externa **redujo la muestra por debajo
del umbral de modelado**: las rachas se volvieron mas largas y menos -de 66 filas
por episodio a 100- y los episodios independientes cayeron.

**Es un compromiso medido entre detectar y modelar**, con datos propios, y va a
la seccion de resultados del documento IEEE.

### Alternativas descartadas

| Alternativa | Por que no |
|---|---|
| Bajar el umbral de CA-6 | Se fijo antes de ver el dato justamente para esto. Y ya no seria de 10 a 9: seria de 10 a 2 |
| Usar menos pliegues | Con 13 episodios totales, ni dos pliegues llegan a 10 |
| Seguir contando por distrito | Es lo que produjo el problema, y el proyecto ya lo rechazo al medir el catalogo |
| Volver a SPI-3 | Recupera muestra y **pierde la validacion externa**: 0 de 7 contra el catalogo. Cambiar un criterio para satisfacer otro, en la direccion que ya se midio como peor |
| Omitir la sequia del documento | Un evento ausente sin explicacion es indistinguible de un olvido |

### Como se revierte

Si aparece mas serie -la ETL llega hasta 2024 por el limite de los focos- o si se
amplia el cantón, se vuelve a medir y el evento puede pasar a modelable. La
decision depende del numero, no de una preferencia: **se rehace corriendo
`generar_etiquetas.py`**.

---

## D-35 · La clausula de reversion de D-33 se ejerce, y devuelve dos de las doce historias

**Fecha.** 2026-09-02 · **Decide.** Alejandro, a peticion de Avril · **Estado.** Aceptada
**Revisa.** D-33 · **Afecta.** H5.6, H10.3, H10.7, H1.6

### Contexto

**D-33** traspaso al PM las doce historias abiertas de S1 y S2 que estaban a
nombre de Cesar y Avril, y dejo escrita la salida: *«quien quiera retomar algo
suyo lo avisa y se le devuelve, sin discutir y sin pedir permiso»*.

Esa clausula no se habia usado nunca. Al pedirle al equipo respuesta por historia
antes del jueves, Avril respondio por las trece que tenia abiertas y pidio dos de
vuelta. Es la primera vez que la reversion se ejerce, asi que conviene dejar
escrito **como se resolvio**, porque el criterio va a hacer falta otra vez.

### Decision

**Se devuelven H5.6 y H10.3. Se quedan con el PM H1.6 y H10.7.**

| Historia | Vuelve a | Por que |
|---|---|---|
| **H5.6** | Avril | **Ya estaba hecha.** El trabajo existe en `feature/ame-h5.6-crtm05` con 25 controles contra `pyproj`. Empezarla de nuevo habria tirado ese trabajo y producido dos implementaciones de la misma transformacion |
| **H10.3** | Avril | Desbloquea **H10.9, que es CG-6 entera**. Quien conoce el visor saca las capturas a la primera |
| **H1.6** | se queda | Es Sprint 1, vencido hace cuatro semanas. La cuenta de Copernicus ya esta resuelta, asi que el PM la entrega **esta semana** contra el sabado 13 de la peticion. Ademas **destraba H5.5, de Avril, once dias antes** |
| **H10.7** | se queda | Avril la retiro ella misma: es Arq, y ese criterio ya lo cubre H6.5. Son 7,8 h que no sacan ningun criterio del cero |

### Medicion

Las fechas comprometidas de cada opcion, que son el dato que decidio:

| Historia | Si la hace Avril | Si la hace el PM | Diferencia |
|---|---|---|---|
| **H5.6** | viernes 4 · **ya hecha** | ~viernes 4, reescribiendola | mismo dia, y el doble de trabajo |
| **H10.3** | martes 9 | ~viernes 4 | 3 dias peor, y desbloquea CG-6 |
| **H1.6** | sabado 13 | **esta semana** | **hasta 12 dias mejor** |
| **H10.7** | jueves 11 | esta semana | 7 dias mejor, y no saca ningun criterio del cero |

Efecto en el cierre de los sprints:

| | Antes de D-35 | Despues |
|---|---|---|
| Sprint 1 cierra | sabado 13 (por H1.6) | **esta semana**, a falta de H10.4 |
| Sprint 2 depende de | solo el PM | PM + Avril, en paralelo |
| Carga del PM | 184 pts · 278,6 h | **176 pts · 269,1 h** |
| Carga de Avril | 74 pts · 87,6 h | **82 pts · 97,1 h** |

Avril estimo su plan completo en **74,3 h en tres semanas -24,8 por semana-**
contra las 18 que firmo. Con este reparto baja a **57,7 h**, sin perder ninguna de
las historias que sostienen un criterio en cero.

### Justificacion

**El criterio de desempate es la fecha, no la propiedad.** Con tiempo por delante,
que cada quien haga lo suyo produce mejor codigo y mejor aprendizaje. A tres
semanas del final y con el Sprint 1 vencido hace cuatro, lo que decide es que
opcion entrega antes — y eso se puede comprobar contra una fecha comprometida, no
discutir.

Aplicarlo asi mantiene D-33 en pie: la reversion sigue siendo un derecho, y
ejercerla obliga a poner una fecha. **Una regla que se puede invocar sin coste
tampoco informa nada.**

Y hay un motivo que no es de calendario: **H5.6 ya estaba escrita**. Ninguna
consideracion de reparto justifica producir dos veces la misma transformacion de
coordenadas.

### Por que no se aplico la regla al pie de la letra

D-33 dice «sin discutir». Aplicado literalmente, las cuatro volvian.

**Pero D-33 existia para destrabar**, y una devolucion que empuja el cierre del
Sprint 1 de esta semana al **sabado 13** trabaja contra su propio motivo. Asi que
en vez de negarse -que habria invalidado la regla para todos- o de aceptar en
silencio -que habria costado doce dias-, se devolvio una, se argumento la otra
**con la fecha como criterio**, y se dejo la decision en manos de quien la pidio.

Avril acepto el argumento y lo dijo con estas palabras: *«no la voy a discutir, y
no porque sea la regla sino porque tu argumento es mejor que el mio»*.

**El criterio que queda, y es el que hay que reusar: en una reversion no decide de
quien es la historia, decide que fecha entrega antes.** La propiedad importa
cuando hay tiempo; a tres semanas del final importa la fecha.

### Lo que salio de ejercerla, y no se esperaba

**El trabajo de H5.6 llevaba dias hecho y sin subir.** No aparecio en ningun
tablero, en ningun PR y en ninguna de las cifras de avance del proyecto: para
`verificar_estado.py` la historia estaba abierta, porque **un commit local no es
trabajo entregado**.

Se descubrio de pura suerte, porque el PM aviso que arrancaba y ella contesto a
tiempo. Un dia mas y se escriben dos veces la misma transformacion.

Es la misma forma que los cinco dias de la firma de SC-07: **trabajo terminado
detenido por un paso de comunicacion, invisible para todos los controles del
proyecto**. Los verificadores miden el repositorio, y lo que no esta en el
repositorio no existe para ellos.

### Alternativas descartadas

| Alternativa | Por que no |
|---|---|
| Devolver las cuatro | Empujaba el cierre del Sprint 1 al sabado 13, contra el motivo de D-33 |
| No devolver ninguna | La regla la escribio el PM. Aplicarla solo cuando conviene la anula para todos, y el rastro queda en el ADR |
| Decidirlo el PM sin consultar | H5.6 se habria reescrito desde cero con el trabajo hecho al lado |
| Cambiar D-33 para agregar condiciones | La regla simple funciono: forzo a argumentar en vez de imponer. Lo que faltaba era el criterio de desempate, y eso es lo que registra esta decision |

### Consecuencias

- Alejandro baja de 184 a **176 puntos** y de 278,6 a **269,1 h**.
- Avril sube de 74 a **82 puntos** y de 87,6 a **97,1 h** — con su propia
  estimacion, 57,7 h en tres semanas, mas cerca de las 18 semanales que firmo.
- El **Sprint 2 ya no depende solo del PM**: H5.6 el viernes 4 y H10.3 el martes 9
  son de Avril.
- Quedan dos compromisos del PM hacia ella, y los dos sostienen criterios en cero:
  **H10.5c a mas tardar el lunes 14** para que H10.6 salga el viernes 19, y
  **H11.4 a mas tardar el miercoles 16** para H13.2 el domingo 21.

---

## D-36 · El despliegue continuo corre contra un cluster efimero, no contra el cluster local

**Fecha.** 2026-09-02 · **Decide.** Alejandro · **Estado.** Aceptada
**Afecta.** H11.2, H11.3, H11.4, H13.2, H12.2

### Contexto

**D-05** puso los tres entornos que exige la rubrica -desarrollo, pruebas y
produccion- en **un mismo cluster k3d local**, en espacios de nombres distintos.
Esa decision sigue siendo correcta y no se toca.

H11.2 pide **despliegue automatico al entorno de desarrollo al mergear a `main`**,
y H11.3 y H11.4 encadenan pruebas y produccion detras.

Hay un hecho que no se puede negociar: **GitHub Actions corre en la nube y el
cluster k3d vive en una maquina del equipo, detras de un router domestico, sin
direccion publica ni credenciales expuestas.** Un `kubectl apply` desde el runner
no tiene contra que hablar.

No es una limitacion del proyecto: es la topologia. Cualquier solucion pasa por
elegir **que se automatiza y que queda en manos de una persona**, y el error
seria no elegirlo y escribir un flujo de trabajo que parezca desplegar.

### Decision

**El flujo de despliegue crea su propio cluster k3d dentro del runner, aplica los
manifiestos del entorno que corresponde, comprueba que converja, y lo destruye.**

**Y el cluster local persistente se actualiza con un guion de un comando**,
`infra/k8s/desplegar.py`, que aplica exactamente los mismos manifiestos.

Los dos caminos usan **el mismo kustomize y las mismas imagenes de ghcr.io**. No
hay dos definiciones del despliegue: hay una, aplicada en dos sitios.

La cadena queda asi:

| Historia | Entorno | Disparo | Aprobacion |
|---|---|---|---|
| **H11.2** | `geoguardian-desarrollo` | al fusionar a `main` | ninguna |
| **H11.3** | `geoguardian-pruebas` | despues de desarrollo | **manual**, entorno de GitHub |
| **H11.4** | `geoguardian-produccion` | despues de pruebas | **explicita**, y con reversion automatica si no converge |

### Justificacion

**Lo que el cluster efimero si demuestra**, y es la mayor parte de lo que la
rubrica evalua:

  * Que los manifiestos son validos y kustomize los construye.
  * Que las imagenes publicadas por H11.1 **arrancan dentro de Kubernetes**, que
    es distinto de arrancar en `docker run` -es lo que comprueba `verificar_h111`-.
  * Que los pods **convergen**: `kubectl rollout status` con limite de tiempo.
  * Que la reversion funciona, porque se puede provocar el fallo a proposito.
  * Que **cualquiera lo reproduce**, incluido el profesor, sin acceso a ninguna
    maquina nuestra.

**Lo que no demuestra:** que haya algo corriendo despues. Eso queda declarado
abajo y va a limitaciones del documento IEEE.

El criterio que decidio: **entre un despliegue que se puede reproducir y uno que
solo funciona si una maquina esta encendida, el primero es mas verificable.** Un
CD que depende de que alguien no haya apagado su computadora produce fallos que
no son del sistema, y una historia cerrada con un flujo que hoy no corre no vale
como evidencia.

### Alternativas descartadas

**Un runner autoalojado en la maquina del cluster.** Es la unica opcion que
despliega de verdad al namespace real, y por eso se considero primero.

Se descarta por tres motivos, en orden de peso:

  1. **El CD falla cuando la maquina esta apagada**, y eso es lo normal fuera de
     horario. Un flujo rojo por estar apagada la computadora entrena al equipo a
     ignorar el rojo, que es el peor habito que puede dejar una tuberia.
  2. **Nadie mas puede reproducirlo.** Ni el profesor al evaluar, ni un
     companero. La evidencia se vuelve una captura de pantalla.
  3. Un runner autoalojado ejecuta codigo de cualquier PR en una maquina
     personal. En un repositorio publico eso es un problema de seguridad real, y
     resolverlo bien -runner efimero, aislado- es mas trabajo que la historia.

**Exponer el cluster con un tunel.** Descartada sin medirla en detalle: mete una
dependencia de un tercero en el camino critico del despliegue y credenciales de
cluster en secretos del repositorio, a cambio de la misma fragilidad del punto 1.

**Declarar H11.2 imposible.** Es la salida que este proyecto tomo en **D-34** con
la sequia, y aca no aplica: alli faltaba el dato -9 episodios contra 30- y no
habia forma de fabricarlo. Aca **si se puede comprobar lo esencial**, y lo que no
se puede es una parte acotada que se declara.

### Consecuencias

**A favor:**

  * H11.2, H11.3 y H11.4 se pueden cerrar con evidencia ejecutable, no narrada.
  * El mismo kustomize se aplica en el CI y en local. Un manifiesto que no
    converge se descubre en el PR y no al desplegar a mano.
  * La reversion de H11.4 se puede **provocar** y por lo tanto comprobar. En un
    cluster persistente, provocar un fallo para probar la reversion significa
    romper el entorno de alguien.

**En contra, y hay que decirlo sin adornarlo:**

  * **Al terminar el flujo no queda nada corriendo.** El despliegue automatico
    demuestra que el despliegue funciona; no deja un sistema en linea.
  * **El cluster local se actualiza cuando una persona corre el guion.** No es
    entrega continua hasta el entorno persistente, y llamarlo asi seria mentir en
    la memoria.
  * **H13.2, el manual de operacion de Avril, documenta un sistema que se levanta
    localmente**, no uno con una direccion publica. Se le avisa el 2026-09-02, no
    al entregarlo.
  * **H12.2 -la pantalla de monitoreo de entornos- no puede leer estado de un
    cluster que se destruye.** Va a tener que leer del ultimo despliegue local o
    del historial de corridas, y eso cambia su diseno.

### Medicion

Lo que cada opcion demuestra, contado sobre lo que la rubrica CICD evalua:

| | Efimero | Runner autoalojado |
|---|:---:|:---:|
| Los manifiestos construyen | si | si |
| Las imagenes arrancan en Kubernetes | si | si |
| Los pods convergen | si | si |
| La reversion funciona | **si, provocable** | solo rompiendo el entorno real |
| Queda algo corriendo | **no** | si |
| Lo reproduce un tercero | **si** | no |
| Corre con la maquina apagada | **si** | no |

**Cinco de siete contra tres de siete.** Las dos que pierde el efimero son
reales, y son las que se declaran en limitaciones.

El costo se mide tambien en tiempo de tuberia: crear y destruir un k3d en el
runner agrega alrededor de un minuto por entorno. Se acepta porque corre solo
sobre `main`, no en cada PR.
