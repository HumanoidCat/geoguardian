---
author:
  - "Alejandro Josué Rodríguez Zamora"
  - "César Andrés Ubau Calvo"
  - "Luis Alejandro Luna García"
  - "Avril Madrigal Elizondo"
institute: "Universidad Invenio · Ingeniería en Tecnologías de Información · III Trimestre 2026"
date: "10 de septiembre de 2026"
lang: es
---

# GeoGuardian · Documentación técnica del MVP

::: no-entregable

**Historia:** H10.4 y H10.5c · **Responsable:** Alejandro
**Fuente única.** Este archivo genera el PDF de entrega. El `.pdf` es artefacto.
**Se construye sin plantilla de conferencia**: «documentación técnica no va en
IEEE» (retroalimentación docente del 2026-08-27).

**Qué cambió el 2026-09-10.** Se actualizó al estado real del sistema —modelos
entrenados y afinados, `analitico.riesgo` escrita, despliegue público en Railway
con datos reales— y recibió lo que salió del documento de investigación por ser
técnico: la arquitectura por contratos (5.5 y 3), la verificación continua (8) y
el anexo de procedencia de cifras (13). Se agregaron la descripción funcional
con casos de uso (1.4), la evidencia de pruebas (8.5) y la guía de
identificadores (14), que la retroalimentación del 2026-08-24 pedía y nunca se
había escrito.

:::

## Sobre este documento

**Qué es.** La documentación técnica del sistema GeoGuardian: qué hace, qué
tecnologías usa y por qué, cómo está organizado, cómo estima el riesgo, cómo se
verifica, cómo se despliega y cómo se instala.

**Para quién.** Alguien que no participó en el desarrollo y tiene que entender,
mantener o evaluar el sistema. Se asume manejo de terminal y nada más.

**Qué no es.** No es el documento de investigación —ese va aparte, en formato
IEEE, y responde tres preguntas de investigación— ni el manual de usuario del
visor ni el manual de operación, que son documentos propios (sección 11).

**Estado.** Describe el sistema al 10 de septiembre de 2026. Lo que no está
construido se dice en la sección 1.2 y se repite en la 10.

### Contenido

| | Sección |
|---|---|
| 1 | Alcance, estado y descripción funcional |
| 2 | Tecnologías |
| 3 | Arquitectura |
| 4 | Modelo de datos |
| 5 | Procesamiento y modelado |
| 6 | Interfaz de programación |
| 7 | Visor |
| 8 | Verificación y evidencia de pruebas |
| 9 | Despliegue |
| 10 | Decisiones de arquitectura y limitaciones técnicas |
| 11 | Documentación relacionada |
| 12 | Instalación y operación |
| 13 | Anexo · de dónde sale cada cifra |
| 14 | Anexo · cómo leer los identificadores |

## 1. Alcance, estado y descripción funcional

### 1.1 Qué construye este sistema

GeoGuardian estima el riesgo de tres eventos climáticos —**lluvia intensa,
sequía e incendio forestal**— para cada uno de los ocho distritos del cantón de
Tilarán, con un horizonte de siete días, exclusivamente a partir de datos
abiertos. El destinatario original es el Comité Municipal de Emergencias; el
público del visor publicado es cualquier persona del cantón que quiera saber
qué viene esta semana en su distrito.

El cantón mide **669,23 km²** y se extiende 30,7 × 36,6 km. Sus ocho distritos
son Tilarán, Quebrada Grande, Tronadora, Santa Rosa, Líbano, Tierras Morenas,
Arenal y Cabeceras.

### 1.2 Qué está construido hoy

| Componente | Estado al 10 de septiembre de 2026 |
|---|---|
| Base de datos PostgreSQL + PostGIS, cuatro esquemas | Operativa, con 35 años de series reales de los ocho distritos y el archivo de focos de calor |
| ETL de series climáticas y focos de calor | Operativo, reejecutable e idempotente, con cadencia declarada por fuente |
| Etiquetado de la variable objetivo | Cerrado: 99 296 filas, tres etiquetas por fila |
| Validación temporal, dos líneas base y arnés de comparación | Cerrados |
| Tres algoritmos supervisados, afinados | **Entrenados, afinados y medidos.** Ninguno supera a la línea base fuera del ruido |
| Tubería que escribe `analitico.riesgo` | Operativa: escribe el estimador que la tabla elige con una regla fija |
| Importancia de variables y explicaciones SHAP | Medidas y archivadas |
| API REST con OpenAPI | Implementada, en modo `postgres`, sirviendo riesgo real |
| Visor web | **Publicado con datos reales** en Railway; copia con datos simulados en GitHub Pages |
| Despliegue continuo a tres entornos de Kubernetes | Operativo sobre k3d, desde imágenes publicadas en `ghcr.io` |
| Renovación automática de las estimaciones | **Diseñada, no desplegada** (sección 9.2) |
| Validación con usuarios (SUS, sesión de contraste) | Materiales listos, **sesión pendiente** |

### 1.3 Restricciones que gobiernan el diseño

1. **Solo datos abiertos.** Ninguna fuente de pago ni instrumentación propia.
2. **Cuatro personas, cuatro frentes.** El desacople entre ellos no es una
   preferencia: es la condición para avanzar en paralelo.
3. **Todo lo que se afirme tiene que poder comprobarse por una máquina.**
4. **La ausencia de estimación se muestra como ausencia**, nunca como riesgo
   bajo. Gobierna el esquema, el etiquetado, la tubería y el visor.

### 1.4 Descripción funcional y casos de uso

![Casos de uso](diagramas/casos-de-uso.png)

El sistema tiene tres actores y un flujo principal.

**La persona que consulta** abre el visor, elige un evento y una fecha, y ve el
mapa del cantón con los ocho distritos pintados por nivel de riesgo —bajo,
medio, alto— o con trama cuando no hay estimación. Al tocar un distrito ve su
ficha: nivel, probabilidad de nivel alto, qué estimador la produjo y con qué
fecha de corrida. La pantalla «Hoy en tu distrito» dice lo mismo en palabras y
con una acción sugerida. Puede encender capas de contexto —mapa de calor
interpolado, índices de vegetación y agua, límites, el lago— y elegir otra
fecha para ver el estado de otro día.

**Quien opera el sistema** corre la ingesta (descarga y carga de las fuentes,
reejecutable), genera las características y las etiquetas, corre la tabla
comparativa y la tubería que escribe las estimaciones, y comprueba el estado del
servicio publicado. Todas son órdenes de terminal documentadas en 12 y en el
manual de operación.

**Quien evalúa o mantiene** verifica el repositorio con los verificadores de la
sección 8, reconstruye los artefactos derivados (matriz de trazabilidad,
diagramas, figuras, documentos) y sigue el manual técnico para levantar el
sistema en una máquina limpia.

| Caso de uso | Actor | Entrada | Salida | Sección |
|---|---|---|---|---|
| Consultar el riesgo de un distrito para una fecha | Persona que consulta | Evento, fecha, distrito | Nivel, probabilidad, estimador, fecha de corrida, o «sin estimación» | 6, 7 |
| Ver el estado semanal en palabras | Persona que consulta | Distrito | Nivel con palabra y término técnico, acción sugerida | 7 |
| Ingerir las fuentes | Operación | Rango de fechas, fuente | Filas en `crudo`, recibo de carga, registro en bitácora | 5.1, 12 |
| Estimar el riesgo | Operación | Conjunto etiquetado y matriz | Filas en `analitico.riesgo` con `algoritmo` y `version_modelo` | 5.5 |
| Comparar estimadores | Operación, evaluación | Etiquetas y matriz | Tabla por evento con media y rango entre pliegues, y veredicto | 5.5 |
| Verificar el repositorio | Evaluación | Repositorio limpio | Verde o rojo por control, con el motivo | 8 |

## 2. Tecnologías

### 2.1 Lenguajes y ejecución

| Capa | Tecnología | Versión |
|---|---|---|
| Backend, ETL, modelado | Python | 3.11 / 3.12 |
| Frontend | JavaScript (ES2022) + React | 18.3 |
| Base de datos | PostgreSQL + PostGIS | 16 / 3.4 |
| Contenedores | Docker, Docker Compose | — |
| Orquestación local | k3d (Kubernetes) | — |

### 2.2 Bibliotecas del backend

| Dominio | Biblioteca | Versión | Para qué |
|---|---|---|---|
| Datos | pandas · numpy · scipy | 2.2.3 · 2.1.3 · 1.14.1 | Series temporales y estadística |
| Geoespacial | geopandas · shapely · pyproj · rasterio | 1.0.1 · 2.0.6 · 3.7.0 · 1.4.3 | Geometrías, proyecciones, ráster |
| Modelado | scikit-learn · xgboost · shap | 1.6.0 · 2.1.3 · 0.46.0 | Clasificación y explicabilidad |
| API | FastAPI · uvicorn · pydantic | 0.115.6 · 0.34.0 · 2.10.4 | Servicio y validación |
| Base de datos | psycopg · SQLAlchemy · GeoAlchemy2 | 3.2.3 · 2.0.36 · 0.16.0 | Acceso y tipos geométricos |
| Calidad | pytest · pytest-cov · ruff | 8.3.4 · 6.0.0 · 0.8.4 | Pruebas y estilo |

**Las versiones están fijadas, no acotadas.** `requirements.txt` usa `==` en
todas las líneas. Una dependencia con rango convierte «funciona en mi máquina» en
una afirmación sobre una fecha, no sobre un estado del repositorio.

El archivo declara además una regla de proceso: es **compartido**, y agregar una
dependencia exige justificar qué problema resuelve y qué se descartó.

### 2.3 Bibliotecas del frontend

| Biblioteca | Versión | Para qué |
|---|---|---|
| React · React DOM | 18.3.1 | Interfaz |
| Leaflet · react-leaflet | 1.9.4 · 4.2.1 | Mapa y capas |
| Recharts | 2.15.4 | Series temporales |
| Vite | 8.2.0 | Construcción |
| ESLint | 10.8.0 | Estilo |

**Leaflet y no una biblioteca de mapas propietaria** porque el visor tiene que
poder servirse como sitio estático sin clave de API. Es la misma restricción que
gobierna las fuentes de datos, aplicada a la presentación.

### 2.4 Por qué PostGIS y no un archivo

La alternativa evaluada era mantener las geometrías como GeoJSON en disco y las
series en Parquet. Se descartó por tres capacidades que el proyecto usa de forma
efectiva:

1. **Reproyección en la consulta.** El área de cada distrito se calcula con
   `ST_Area(ST_Transform(geometria, 8908))`, es decir en **CR-SIRGAS / CRTM05**,
   la proyección oficial de Costa Rica. Calcular áreas sobre EPSG:4326 —grados—
   produce cifras sin significado métrico.
2. **Restricciones declarativas.** Las reglas de coherencia viven en el esquema y
   no en el código que inserta. Un dato inconsistente no entra.
3. **Asignación espacial de puntos.** Cada foco de calor se asocia a su distrito
   por contención geométrica, no por nombre.

El punto 3 no es menor: **D-18** registra que el nombre de un poblado no
identifica a un distrito, y la asignación por texto habría introducido errores
silenciosos.

## 3. Arquitectura

### 3.1 Estructura en cuatro capas

![Componentes del sistema](diagramas/componentes.png)

La separación es la de un diseño por capas convencional, con una particularidad:
**la capa de dominio no depende de ninguna otra**. Los contratos son estructuras
`Protocol` de Python y esquemas Pydantic sin importaciones de FastAPI, de
SQLAlchemy ni de nada de infraestructura.

### 3.2 Los contratos congelados

El 3 de agosto de 2026, antes de escribir una línea de implementación, se
congelaron las interfaces entre los cuatro frentes: `contratos/`, hoy en
**versión 1.4.0**.

| Archivo | Qué define |
|---|---|
| `enums.py` | `TipoEvento`, `NivelRiesgo` y demás vocabulario cerrado |
| `esquemas.py` | Los objetos que viajan por la API, en Pydantic |
| `fuentes.py` | Cómo se declara una fuente de datos externa |
| `senales.py` | La interfaz de los cálculos de índices |
| `modelado.py` | La interfaz de un estimador |
| `repositorio.py` | El acceso a datos, como `Protocol` |

**Se eligió `Protocol` y no clases abstractas** —decisión **D-06**—. Un
`Protocol` verifica la forma sin exigir herencia: quien implementa no tiene que
importar el contrato, lo que evita el acoplamiento que una clase base introduce.
Además permite que un simulado y una implementación real sean intercambiables sin
ninguna relación de tipos entre ellos.

Con los contratos vinieron **simulados**: implementaciones que cumplen la
interfaz y devuelven datos construidos. Eso permitió que el frontend se
construyera **antes** de que existiera la base de datos.

`contratos/verificar.py` corre **47 comprobaciones** sobre los simulados en cada
ejecución del pipeline y es el primero de los ocho trabajos de integración
continua.

### 3.3 Flujo de datos, de la fuente a la pantalla

![Flujo de datos, de la fuente abierta al visor](diagramas/flujo-datos.png)

### 3.4 Secuencia de una consulta

![Consulta de riesgo por distrito](diagramas/secuencia-consulta-riesgo.png)

El camino principal es el que hoy corre en producción: el visor llama a `/api`
por ruta relativa, un proxy interno lo lleva a la API, y la API lee
`analitico.riesgo` en PostgreSQL. La rama alterna del diagrama es **D-23**: si
la API no responde, el visor **degrada al respaldo estático declarándolo en
pantalla**. Es lo que sirve la copia publicada en GitHub Pages, y es una
degradación exigida por diseño, no un sobrante.

La decisión que sostiene ese comportamiento es que el origen se negocia **una
sola vez** al arrancar, no en cada petición. Reintentar por consulta produciría
una interfaz que a veces muestra datos reales y a veces simulados sin que el
usuario pueda saber cuál está viendo.

### 3.5 Tres invariantes verificadas automáticamente

El proyecto declara tres reglas que ninguna implementación puede violar, y las
comprueba en integración continua:

1. **La ausencia de dato es `None`, nunca `0`** (D-07). Un cero es una medición;
   una ausencia no lo es. Confundirlos convierte una estación seca en un mes sin
   lluvia registrada, y una década sin satélite en una década sin incendios.
2. **No hay estimación sin estimador detrás.** El sistema devuelve nivel nulo
   antes que un valor por defecto, y la interfaz lo distingue visualmente del
   riesgo bajo.
3. **La validación temporal no admite fuga.** Está codificada en los contratos y
   verificada por el arnés (5.5).

## 4. Modelo de datos

![Modelo entidad-relación](diagramas/entidad-relacion.png)

### 4.1 Los cuatro esquemas

| Esquema | Contiene | Por qué separado |
|---|---|---|
| `geo` | Provincia, cantón, distrito | Vocabulario territorial, cambia casi nunca |
| `crudo` | Mediciones diarias, focos de calor, catálogo de fuentes | Lo descargado, sin transformar |
| `analitico` | Riesgo estimado, su auditoría, y las métricas de cada corrida (`analitico.metrica`) | Lo derivado; se puede recalcular |
| `control` | Migraciones aplicadas, bitácora de ETL y aplicación | Metadatos del propio sistema |

La separación permite una operación concreta: **`analitico` se puede vaciar y
reconstruir** sin tocar lo descargado. Si se mezclara con `crudo`, recalcular
exigiría volver a bajar datos de las APIs externas.

`analitico.riesgo` tiene clave natural por distrito, día y evento —una
estimación por terna—, y cada fila declara `algoritmo` y `version_modelo`
(estimador, fecha de la corrida, F1-macro y veredicto de la tabla). Un
disparador registra en `analitico.riesgo_auditoria` cada cambio real de valor;
volver a correr la tubería con el mismo resultado no genera auditoría, porque
la escritura solo actualiza cuando el valor difiere.

### 4.2 Claves e integridad

`geo.distrito` usa el **código oficial DTA del IGN**, cinco dígitos, como clave
primaria. No un identificador autoincremental: el código oficial es estable,
público y permite cruzar con cualquier otra fuente nacional. **D-13** lo fija: el
SNIT es la fuente única del vocabulario territorial.

Las restricciones no son decorativas. `crudo.foco_calor` declara **catorce
`CHECK`**, entre ellas:

- Coherencia entre `confianza` y `confianza_bruta`, con los tres rangos del
  producto MODIS.
- `confianza_bruta` solo puede existir si el producto es MODIS: VIIRS no la
  publica.
- Latitud entre 10,2 y 10,8 y longitud entre −85,2 y −84,6, la caja del cantón.

Esa última es la que impide que un error de signo en la carga meta un foco del
otro hemisferio sin que nadie lo note.

### 4.3 Migraciones con suma de verificación

`control.migracion` registra número, archivo, **suma SHA-256** y fecha de
aplicación. La suma responde una pregunta que el número no puede: *¿el archivo de
migración 004 que está aplicado en esta base es el mismo que hay en el
repositorio hoy?*

Sin ella, editar una migración ya aplicada produce dos bases que se creen iguales
y no lo son.

### 4.4 La proyección, medida y no supuesta

Las geometrías se almacenan en **EPSG:4326** porque es lo que Leaflet consume, y
se transforman a **EPSG:8908** (CR-SIRGAS / CRTM05) para todo cálculo métrico.

La transformación se verificó contra una implementación independiente de la
proyección transversa de Mercator sobre el elipsoide GRS80: la diferencia máxima
medida es de **0,005 mm**, lo que confirma que no hay desplazamiento de datum
entre los dos sistemas y que la conversión no introduce error apreciable.

## 5. Procesamiento y modelado

![Flujo del modelado](diagramas/flujo-modelado.png)

### 5.1 Fuentes y su resolución

| Variable | Fuente | Resolución | Aptitud |
|---|---|---|---|
| Precipitación | CHIRPS 2.0 vía ClimateSERV | 0,05° | Cada distrito cae en celda propia |
| Temperatura, humedad, viento, radiación | NASA POWER | 0,5 × 0,625° | **Una sola celda cubre el cantón** |
| Focos de calor | NASA FIRMS | 1 km (MODIS, desde 2001) y 375 m (VIIRS, desde 2012) | Puntual |
| Geometrías | SNIT / IGN, límite distrital 5k | Vectorial | — |

La fuente es **híbrida por necesidad**, no por gusto: **D-15**. Una celda de
POWER mide 68 × 55 km y cubre el cantón entero, de modo que temperatura, humedad,
viento y radiación **tienen el mismo valor en los ocho distritos**. Se conservan
como contexto y se declara la limitación; la única variable que distingue
distritos es la precipitación.

### 5.2 Índices y umbrales

- **Sequía:** SPI-6 ajustado **por mes calendario** (D-19, escala revisada por
  D-32 tras medirla), con cortes en −1,0
  para nivel medio y −1,5 para alto, según la escala de la OMM.
- **Lluvia intensa:** percentiles 95 y 99 del **acumulado de 72 horas**.
- **Incendio:** binario, presencia de al menos un foco en la ventana de siete
  días, restringido a los tres distritos con señal (**D-25**).

El ajuste por mes calendario del SPI no es un detalle de implementación. Un SPI
ajustado sobre toda la serie mide estacionalidad, no anomalía: en el Pacífico
Norte, con una estación seca marcada, marcaría sequía todos los febreros.

**La precipitación no se filtra.** Se midió que aplicar un filtro de media móvil
reduce la amplitud de los picos en un 48,6 % y elimina los 37 eventos extremos
del período. Los índices se calculan sobre la serie cruda: **D-17**.

### 5.3 Etiquetado y cobertura

El etiquetado produce **99 296 filas** —ocho distritos por 12 412 fechas, del 1
de enero de 1991 al 24 de diciembre de 2024— con tres etiquetas cada una, que
describen la ventana de los siete días siguientes. La cobertura temporal difiere
por evento:

| Evento | Cobertura | Filas en alto (% observado) | Episodios a nivel cantón |
|---|---|---|---|
| Lluvia intensa | 1991–2024 | 3 195 (3,22 %) | 163 |
| Sequía | 1991–2024 | — | 13 |
| Incendio | **2001–2024** | 865 (1,23 %) | 67 |

La ventana del incendio arranca en 2001 porque el archivo FIRMS de MODIS C6.1
empieza ahí. Etiquetar como «bajo» los diez años anteriores habría producido
**29 216 filas falsamente negativas, el 29,4 % del conjunto**. Las filas fuera de
cobertura devuelven ausencia, no cero (**D-07**).

**Los episodios se cuentan a nivel cantón** (**D-34**): una racha de días en que
algún distrito está en alto es un episodio, aunque pegue en los ocho. Contarlos
por distrito los inflaba 3,0× en lluvia, 6,0× en sequía y 1,6× en incendio. Y
con ese conteo **la sequía no es modelable**: el criterio de aceptación del
etiquetado, fijado antes de mirar el dato, exige 30 episodios en total y 10 en
el entrenamiento de cualquier pliegue; la sequía tiene 13 y 2. Se declara en la
tabla comparativa con su medición al lado, no se omite.

### 5.4 Validación temporal

Ventana expansiva con **cinco pliegues** y cortes en frontera de mes (**D-04**).
El embargo entre entrenamiento y prueba **se calcula** a partir de hasta dónde
mira la etiqueta de la última fila de entrenamiento, en lugar de fijarse como
constante. Medido: **siete días para los tres eventos**. Para la sequía, el corte
en frontera de mes absorbe el alcance del SPI-6, lo que reduce el embargo de los
38 días estimados a 7. Cada evento se parte sobre su propio período observado.

### 5.5 Modelado y tubería de estimación

El modelado sigue la interfaz congelada en `contratos/modelado.py`: cualquier
estimador —línea base o algoritmo— expone `ajustar`, `predecir` y
`probabilidades`, y el arnés los trata por igual.

**Estimadores.** Dos líneas base —trivial (clase mayoritaria) y climatológica
(clase de mayor realce por distrito y mes)— y tres algoritmos: regresión
logística, Random Forest y XGBoost (**D-09**), sobre una matriz de **27
columnas** derivadas de cuatro variables diarias mediante rezagos de uno a tres
días y medias móviles de 3, 7 y 30 días. Los hiperparámetros se afinaron con
`python -m backend.modelado.afinar` sobre una rejilla declarada de 28
combinaciones, buscando **solo dentro de la ventana de entrenamiento del primer
pliegue**, la única anterior a todos los bloques de prueba; los afinados quedan
versionados en el módulo y un verificador comprueba que cada valor sale de la
rejilla (**D-42**).

**El arnés.** `python -m backend.modelado.comparar` corre los cinco estimadores
sobre los mismos pliegues con la misma métrica (F1-macro, **D-10**) y el mismo
trato de las predicciones ausentes, y aplica el veredicto que se fijó antes de
entrenar: no hay ganador si la ventaja es menor que el rango entre pliegues del
que va adelante.

**Quién escribe** (**D-39**). La tubería `python -m backend.modelado.estimar_riesgo`
corre la tabla completa y elige con una regla fija, sin ningún nombre de
algoritmo escrito en el guion: si el primero gana fuera del ruido, escribe; si
no, escribe el más simple de los que quedan dentro del ruido del primero, con el
orden climatológica < regresión logística < Random Forest < XGBoost; la trivial
nunca escribe y nadie escribe por debajo del piso trivial. Con las cifras
vigentes escribe la **climatológica** en lluvia intensa, la **regresión
logística** en incendio (por 0,0024 de F1-macro, registrado como borde en I-34) y
**nadie** en sequía. La regla se recalcula en cada corrida.

| Evento | Escribe | Hasta cuándo escribe |
|---|---|---|
| Lluvia intensa | Climatológica | Hoy + 7 días: solo necesita el mes |
| Incendio | Regresión logística afinada | Último día con matriz de características: necesita las variables |
| Sequía | Nadie | — |

**Explicabilidad.** `python -m backend.modelado.importancia` mide la importancia
por permutación sobre el conjunto de prueba de cada pliegue, con los afinados;
`python -m backend.modelado.explicacion` calcula SHAP para cuatro casos por
estimador y evento elegidos por una regla previa que obliga a incluir un error.
Los dos resultados —ninguna columna estable, explicaciones indistinguibles entre
acierto y error— están en el documento de investigación.

**Reproducibilidad.** Semillas derivadas por cadena y `n_jobs = 1` no son
afinables; dos corridas dan los mismos parámetros y los mismos puntajes. Las
cifras dependen de las versiones de `requirements.txt`: una corrida con otra
versión de scikit-learn difiere en el tercer decimal.

## 6. Interfaz de programación

### 6.1 Endpoints

| Método y ruta | Devuelve |
|---|---|
| `GET /salud` | Estado del servicio y modo de datos |
| `GET /distritos` | Los ocho distritos con su geometría |
| `GET /distritos/{codigo}` | Un distrito |
| `GET /distritos/{codigo}/mediciones` | Serie climática del distrito |
| `GET /distritos/{codigo}/riesgo` | Riesgo estimado del distrito |
| `GET /riesgos` | Riesgo de los ocho, por evento y fecha, con `algoritmo` y `version_modelo` |

La especificación OpenAPI se genera desde los esquemas Pydantic, de modo que
**no puede desincronizarse de lo que el servicio realmente acepta y devuelve**.
Es el mismo principio que gobierna la matriz de trazabilidad y los diagramas.

### 6.2 El acceso a datos

Se implementa el patrón Repository sobre el `Protocol` de `contratos`. Su valor
práctico es que las pruebas del servicio corren **sin base de datos**: se
sustituye la implementación PostgreSQL por una en memoria que cumple el mismo
contrato.

## 7. Visor

### 7.1 Composición

React 18 con Leaflet. El mapa abre primero, encuadrado al cantón y usable en un
teléfono; la pantalla «Hoy en tu distrito» está a un clic, con el distrito ya
elegido, y dice el nivel en palabras junto a su término técnico. Las capas son
independientes y conmutables: coropleta de riesgo, mapa de calor interpolado,
índices de vegetación y agua (NDVI y NDWI), el Lago Arenal dibujado como agua
sobre la coropleta, límites distritales y etiquetas de nombre. Los distritos sin
estimación se pintan con trama, no con el color más claro de la escala.

### 7.2 La escala de color, verificada por colorimetría

La escala de tres niveles no se eligió por gusto. `verificar_escala.py` comprueba
en cada ejecución del pipeline que:

- la **luminancia es monótona** entre niveles;
- el **contraste cumple WCAG** sobre todos los fondos posibles;
- el **orden se conserva** bajo protanopia, deuteranopia y tritanopia;
- la marca de selección **no usa negro puro**.

Un mapa de riesgo cuyo orden se pierde para una persona con dicromacia no
comunica el riesgo: lo oculta.

### 7.3 Interpolación y su recorte

La capa de mapa de calor interpola la probabilidad por **distancia inversa**
entre los centroides distritales, con exponente ajustable y una paleta
deliberadamente distinta de la escala de riesgo, para que no se confundan dos
magnitudes que no son la misma.

Los ocho puntos de origen se dibujan **encima** de la superficie. No es
decoración: una interpolación sobre ocho puntos produce una superficie suave que
parece un análisis fino y no lo es; mostrar de dónde salió cada valor es lo que
impide leerla como una medición continua del terreno.

La superficie se recorta contra la unión de los polígonos con regla par-impar.
Antes de esa corrección, **el 23,8 % de lo pintado caía fuera del cantón y el
20,7 % del cantón quedaba sin pintar**; Tronadora aparecía cubierta al 54,5 %.
Hoy ambas cifras son cero, y un verificador lo comprueba en cada Pull Request.

## 8. Verificación y evidencia de pruebas

### 8.1 Ocho trabajos de integración continua

Cada cambio pasa por ocho trabajos: contratos y simulados (47 comprobaciones),
backlog y documentación (estado, horas, ADR, cifras, diagramas, tablero), linter
y formato, frontend (ESLint, construcción, escala de color, recorte de la
interpolación), pruebas del backend contra PostgreSQL con PostGIS como servicio,
construcción y publicación de imágenes en `ghcr.io`, publicación del visor
estático desde `main` y el despliegue continuo a los entornos de k3d.

### 8.2 Un verificador por historia

Cada historia con criterios de aceptación escritos antes de implementar tiene un
programa que los comprueba. No son pruebas unitarias: **comprueban propiedades
del resultado**, y varios incluyen una **prueba negativa** que confirma que el
control sabe fallar. Ejemplos:

- `verificar_h32.py`: 61 comprobaciones sobre la partición temporal, incluida una
  partición deliberadamente contaminada que **tiene que** salir en rojo.
- `verificar_h36.py`: contrasta dos caminos independientes hasta la misma cifra y
  exige que coincidan a menos de 1e-12; corre con etiquetas sintéticas cuando el
  artefacto real no está.
- `verificar_h38.py`: 38 comprobaciones sobre el afinado, sin base ni red; el
  segundo criterio tumbó la primera implementación (buscaba en el último pliegue
  y compartía 7 752 días con los bloques de prueba).
- `verificar_recorte_calor.mjs`: ejecuta la función de dibujo real sobre un
  canvas simulado y compara contra una implementación independiente de
  punto-en-polígono.
- `verificar_frases.py`: 18 siglas prohibidas en la pantalla de palabras, todo
  nivel con palabra y término, nadie promete «tiempo real».

### 8.3 Los artefactos derivados no se editan

| Artefacto | Se deriva de |
|---|---|
| Matriz de trazabilidad | `docs/trazabilidad.csv` y los archivos de tareas |
| Los siete diagramas | El DDL, las rutas de la API y el generador |
| Las figuras de resultados | El conjunto etiquetado, o las tablas de `docs/figuras/datos/` |
| Cifras de la documentación | El repositorio, recalculadas en cada ejecución (anexo 13) |
| Especificación OpenAPI | Los esquemas Pydantic |
| Los PDF de entrega | Los `.md`, con `construir_entregable.py` |

### 8.4 Tres lecciones que costaron

**I-06 · un control que se salta se ve igual que uno que pasa.** Un verificador
condicionado a la existencia de un archivo que nunca está en el entorno de
integración queda verde sin ejecutar nada.

**I-10 · una regla que ninguna máquina comprueba se cumple mientras alguien se
acuerda.** El sitio publicado mostró ocho rectángulos en vez de los distritos
reales durante días. El propio archivo declaraba `"geometria_simulada": true`, y
nadie leía esa bandera.

**I-14 · la responsabilidad se corre hacia arriba, a las premisas.** El equipo
redacta con ayuda de herramientas de IA, y una premisa mal puesta no se discute:
se implementa, con rigor, en la dirección equivocada. La calidad de la ejecución
es lo que oculta el problema.

### 8.5 Evidencia de pruebas

La evidencia de pruebas del MVP está en cinco capas. Cada una deja rastro en el
repositorio, y aquí se trae lo que ese rastro dice, no solo dónde está.

**Pruebas automatizadas.** La suite de `backend/tests/` corre en el CI contra
PostgreSQL con PostGIS como servicio. Al cerrar la historia de cobertura de
dominio (30 de agosto) pasó de **148 a 209 pruebas** con 57 casos nuevos en
cuatro archivos —19 sobre el contrato del repositorio, 19 sobre el de modelado,
10 sobre el de fuentes y 9 sobre los esquemas— y cubre **35 de los 40 casos del
plan de pruebas**. Los cinco que faltan no faltan por tiempo: cuatro no se
pueden escribir contra el simulado porque este no implementa la invariante que
el caso protege (por ejemplo, el simulado «siempre devuelve un `Riesgo`: no
puede representar la ausencia de estimación, que es justo lo que el caso
protege»), y quedan declarados como hallazgo. La evidencia también reconcilió el
plan con la suite: nueve casos ya estaban cubiertos con otro nombre y 139
pruebas existían sin que el plan las nombrara, porque el plan es una lista a
nivel de contrato y la suite creció a nivel de implementación.

**Verificadores de criterios.** Cada historia con criterios escritos antes de
implementar tiene un programa que los comprueba (8.2), y su salida se pega en la
evidencia de la historia, en `docs/evidencias/<materia>/`. Los de modelado
suman, entre otros: 61 comprobaciones sobre la partición temporal, 31 sobre el
arnés, 21 sobre la tubería que escribe, 38 sobre el afinado.

**Sabotajes: el control se prueba rompiéndolo.** Para los verificadores del
modelado se escribió un guion que rompe una cosa, corre el verificador,
comprueba qué criterio cae y restaura. En el afinado fueron **doce sabotajes y
ninguno pasó en verde**; dos de ellos —«un valor afinado que no sale de la
rejilla» y «el verificador no restaura los parámetros»— son controles que no
existían hasta que se pegó el resultado real. En la tubería se saboteó la regla
de escritura rama por rama (el de mayor media siempre escribe; la trivial entra
al orden de simplicidad; …) y en cada caso cayeron los criterios esperados.

**Verificación externa del manual técnico.** El 2 de septiembre, una persona
ajena al equipo recorrió las secciones 2 a 5 del manual de instalación en una
máquina Windows 11 sin Python 3.11, durante una hora y diez minutos, y llenó la
hoja de verificación paso por paso. De **16 pasos, 11 funcionaron y 5 «a
medias»**; ninguno falló. Las observaciones textuales que obligaron a corregir
el manual el mismo día: «`python -m venv` toma la 3.13; hay que saber
`py -3.11`»; «el manual decía 36 comprobaciones y versión 1.2.0; la salida real
da 47 y 1.4.0»; «`npm run dev` bloquea la terminal». La hoja se archivó tal
como llegó, sin editar.

**Contraste contra la realidad.** El etiquetado se contrastó contra 46
registros históricos con daños documentados; los números están en el documento
de investigación (sección V-G) y no se repiten aquí.

Lo que **no** hay todavía es evidencia con usuarios: la sesión de usabilidad y
el SUS tienen instrumento, guion y dosier de casos preparados, y no se han
realizado.

## 9. Despliegue

![Arquitectura de despliegue](diagramas/despliegue.png)

### 9.1 Lo que está desplegado

Hay **tres** cosas corriendo, y conviene no confundirlas:

| | Qué es | Datos | Quién llega |
|---|---|---|---|
| **Railway** | El despliegue público: visor (nginx) → API (uvicorn) → PostgreSQL con PostGIS, en un solo proyecto y una red privada; un solo dominio público, el del visor | **Reales** | Cualquiera |
| **k3d local** | Tres entornos —desarrollo, staging, producción— desplegados por el pipeline desde las imágenes de `ghcr.io` por SHA, con aprobación manual y reversión automática | Reales | Quien tenga la máquina |
| **GitHub Pages** | El visor como sitio estático, publicado desde `main` por el pipeline | **Simulados**, y lo declara en pantalla | Cualquiera |

La rúbrica evalúa el despliegue continuo a k3d; el sitio público es una
demostración (**D-43**). El binario de Railway se construye desde el árbol del
repositorio y no desde las imágenes que el CI probó: es una pérdida aceptada por
escrito, y la comprobación diaria del manual de operación compara `version_api`
y `version_contratos` para acotarla.

La API **no se expone**: el visor le habla por `/api` en ruta relativa y un
proxy interno la lleva a la red privada. Por eso no hace falta CORS, y un
verificador comprueba que la API no lo tenga.

### 9.2 Lo que no está desplegado

**La renovación automática de las estimaciones.** La tubería escribe hasta siete
días después de su corrida, y hoy es un comando manual: nada la vuelve a correr.
Está diseñado un cuarto servicio, `trabajos`, que se enciende una vez al día,
corre la cadena y se apaga; su imagen y su verificador de dependencias existen
y el paso del runbook está escrito. No está desplegado al cierre de este
documento.

### 9.3 Reproducibilidad del dataset

El dataset consolidado se versiona **por manifiesto**, no por archivo: un
documento con sumas SHA-256 de cada fuente, sus conteos y sus rangos temporales.
Se descartaron DVC y Git LFS por costo de infraestructura frente al tamaño real
del dato.

El manifiesto responde una pregunta concreta: *¿dos personas tienen exactamente
el mismo dato?* No responde si ese dato es correcto —eso lo mide el reporte de
calidad— y la distinción está escrita para no confundirlas.

## 10. Decisiones de arquitectura y limitaciones técnicas

### 10.1 Decisiones

51 decisiones registradas, cada una con contexto, justificación, alternativas
descartadas, consecuencias y medición. Las que más gobiernan el código:

| ADR | Decisión |
|---|---|
| D-04 | Validación temporal por ventana expansiva |
| D-06 | Contratos con `Protocol`, no clases abstractas |
| D-07 | La ausencia se representa como nulo, nunca como cero |
| D-09 | Tres algoritmos: regresión logística, Random Forest, XGBoost |
| D-10 | F1-macro como métrica principal |
| D-13 | El SNIT es la fuente única del vocabulario territorial |
| D-15 | Fuente climática híbrida: CHIRPS y POWER |
| D-17 | La precipitación no se filtra |
| D-19 | El SPI se ajusta por mes calendario |
| D-21 | `probabilidad` es P(nivel = alto) |
| D-23 | El visor negocia su origen una vez y degrada declarándolo |
| D-25 | El incendio es binario y se acota a tres distritos |
| D-29 | El dataset se versiona por manifiesto |
| D-32 | La escala del SPI es 6 meses, elegida contra el catálogo |
| D-34 | Los episodios se cuentan a nivel cantón; la sequía no es modelable |
| D-39 | Qué estimador escribe cuando ninguno gana fuera del ruido |
| D-42 | Los afinados se aplican aunque cambien quién escribe |
| D-43 | El despliegue público se construye desde el repositorio |
| D-46 | Público meta y palabras de los niveles en la pantalla |

Una decisión que se deja atrás **no se borra**: cambia de estado y se conserva
entera. El registro distingue tres formas de hacerlo —*revisada*, *sustituida* y
*revertida*—, y la tercera se agregó al comprobar que una decisión partía de un
hecho falso. Llamarle «sustituida» habría ocultado justamente lo que había que
aprender.

### 10.2 Limitaciones técnicas

1. **Una sola variable resuelve el cantón.** De las cinco variables climáticas,
   solo la precipitación distingue distritos.
2. **Ningún modelo supera a la línea base fuera del ruido.** Lo publicado para
   lluvia intensa es la climatológica, y cada fila lo declara.
3. **La sequía no se modela** con 34 años de datos. Se puede mostrar el índice
   medido; no un nivel estimado.
4. **Las estimaciones caducan a los siete días** y hoy se renuevan a mano.
5. **La precipitación llega con 21 a 51 días de atraso** (CHIRPS final), así que
   el último día con lluvia medida queda semanas detrás de la fecha de
   estimación, y la pantalla lo declara por separado.
6. **El componente de incendio es el más débil.** Sin estándar para el umbral,
   sin registro histórico y con clase positiva del 1,23 %.
7. **Los polígonos simplificados no teselan:** su unión deja 142 huecos diminutos
   entre distritos vecinos. No afecta a los cálculos actuales y queda anotado.

## 11. Documentación relacionada

La entrega consta de cinco documentos. Este es el segundo.

| # | Documento | Para qué |
|---|---|---|
| 1 | Documento de investigación (formato IEEE) | Las preguntas de investigación, los resultados y las conclusiones |
| 2 | **Documentación técnica del MVP** (este documento) | Qué hace el sistema, cómo está hecho, cómo se verifica y despliega |
| 3 | Manual de usuario del visor | Cómo se usa el visor, pantalla por pantalla |
| 4 | Manual técnico de instalación | Levantar el sistema paso a paso en una máquina limpia, verificado por una persona ajena |
| 5 | Manual de operación | Cómo se atiende el sistema publicado: comprobación diaria, triaje, restauración |

En el repositorio, además: el runbook del despliegue público, las dos bitácoras
(decisiones e incidencias), la matriz de trazabilidad y las evidencias de cada
historia. Todo lo que este documento toma de ellos está transcrito aquí; las
rutas se dan para poder verificarlo, no para completar la lectura.

## 12. Instalación y operación

### 12.1 Requisitos

Python 3.11 o superior, Node 20 o superior, Docker con Docker Compose, y
PostgreSQL 16 con PostGIS 3.4 —que Compose levanta.

### 12.2 Puesta en marcha

```bash
git clone https://github.com/HumanoidCat/geoguardian
cd geoguardian

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

docker compose up -d
python -m basedatos.aplicar_migraciones

cd frontend && npm ci && npm run dev
```

### 12.3 Comprobar que la instalación quedó bien

```bash
python -m contratos.verificar          # 47 comprobaciones
python -m pytest                       # la suite del backend, contra PostgreSQL
python -m ruff check . && python -m ruff format --check .
python -m backend.api.verificar_h61
python docs/herramientas/verificar_h66.py
python docs/herramientas/verificar_estado.py
python docs/herramientas/verificar_documentacion.py
python docs/herramientas/verificar_backlog.py
python docs/herramientas/verificar_adr.py
python docs/herramientas/verificar_diagramas.py
```

Todas corren sobre el repositorio limpio. Las que necesitan datos procesados
—el contraste contra el catálogo, la tabla comparativa, el afinado, la
importancia de variables— requieren la base cargada y se describen en 5.5.

### 12.4 Reconstruir los artefactos

```bash
python docs/herramientas/generar_matriz.py
python docs/herramientas/generar_diagramas.py --png
python docs/herramientas/generar_figuras.py --tabuladas
python docs/herramientas/construir_entregable.py docs/13-documento-ieee.md --ieee
python docs/herramientas/construir_entregable.py docs/17-documento-tecnico.md
python docs/herramientas/construir_entregable.py docs/18-manual-de-usuario.md
python docs/herramientas/armar_entrega.py
```

El documento de investigación es el único que se construye con la plantilla de
conferencia (`--ieee`). Este documento, el manual de usuario y el de operación
se construyen sin ella.

## 13. Anexo · De dónde sale cada cifra de la documentación

Ninguna cifra de esta documentación ni del documento de investigación está
escrita de memoria. Las que la integración continua puede recalcular las
recalcula `verificar_documentacion.py` en cada ejecución del pipeline, y hace
fallar el CI si alguna se desfasa. El control se agregó porque hacía falta:
entre el 18 y el 26 de agosto, cinco cifras del documento de investigación
dejaron de ser ciertas sin que nadie lo notara, y al ampliar la bibliografía el
30 de agosto la herramienta señaló el desfase en el acto.

| Cifra | Origen |
|---|---|
| 669,23 km²; 30,7 × 36,6 km; 59,5 % | Medición sobre la carga de las geometrías del SNIT |
| 68 × 55 km, celda POWER; 8 celdas CHIRPS; 20,3 % | `verificar_resolucion_fuente.py` y medición sobre ClimateSERV |
| 48,6 % contra 20,0 %; 12,47 %; 31,62 %; −53,6 %; 0 de 37 | `medir_efecto_filtro.py` |
| −0,84; +0,60; 99 de 99; 0,425 | `medir_spi_por_mes.py` |
| 39,90 / 54,86 / 63,40 / 87,70 mm; 8,5× | `medir_percentiles.py` |
| 98 fichas, 46 registros, 29 eventos | Catálogo de eventos históricos |
| 38 referencias, 29 con ficha | Fichero bibliográfico del proyecto |
| 47 comprobaciones, 8 trabajos de CI, 22 controles | `verificar_documentacion.py` |
| 51 decisiones, 54 incidencias | Las dos bitácoras |
| 5 pliegues; embargo de 7 días en los tres eventos | `verificar_h32.py`, 61 comprobaciones |
| 99 296 filas; 29 216 filas, 29,4 % | `generar_etiquetas.py` sobre la base cargada |
| 163 / 13 / 67 episodios; 2, 3, 3, 6, 9 por pliegue | `generar_etiquetas.py`; D-34 |
| F1-macro de los cinco estimadores, por evento | `afinar.py` y `comparar.py`; transcritos en `docs/figuras/datos/comparativa-algoritmos.csv` |
| Cobertura, tasa base y realce (4,74×; 6,31× con tasa base 15,9 %); los −37 días | `contrastar_catalogo.py`; figura `contraste-catalogo.png` |
| Las tres escalas del SPI (6,50 con tasa base 15,4 %; 5,39; 0,00) | `comparar_escalas_spi.py`, registrado en la decisión de la escala |
| 0 columnas estables de 27; explicaciones indistinguibles | `importancia.py` y `explicacion.py` |

**Las cifras que salen del conjunto etiquetado no las puede recalcular la
integración continua**, porque ese conjunto es un artefacto derivado de la base
y no se versiona. Lo que sí comprueba la máquina en cada ejecución es que el
arnés que las produce sigue siendo correcto —`verificar_h36.py` corre con
etiquetas sintéticas deterministas— y que las tablas de `docs/figuras/datos/`
existen y generan las figuras. La trazabilidad completa la da el manifiesto del
conjunto de datos, que registra con SHA-256 las fuentes de las que se deriva.

## 14. Anexo · Cómo leer los identificadores

La documentación usa identificadores cortos para poder cruzar historias,
decisiones, incidencias y evidencias sin repetir títulos. Se leen así:

| Identificador | Qué es | Cómo se lee |
|---|---|---|
| **H1.6**, **H10.4** | Historia de usuario | `H` de historia; el primer número es la **épica** (E1 datos, E3 modelado, E10 documentación…); el segundo es el **orden dentro de la épica**. H10.4 es la cuarta historia de la épica 10. Una letra al final (H10.5a, H10.5b) parte una historia en piezas que se cierran por separado |
| **E3** | Épica | Un grupo de historias con un objetivo común. Las épicas van de E1 a E14 |
| **D-34** | Decisión de arquitectura (ADR) | Numeradas en orden de registro en `docs/03-bitacora-decisiones.md`. Tienen contexto, decisión, justificación, alternativas descartadas, consecuencias y medición |
| **I-14** | Incidencia | Numeradas en orden de registro en `docs/04-bitacora-incidencias.md`. Qué pasó, causa raíz, acción tomada, aprendizaje |
| **SC-05** | Solicitud de cambio | Cambio a un archivo compartido (contratos, compose, workflows), aprobado por el PM y el dueño del módulo |
| **CA-6** | Criterio de aceptación | El sexto criterio de la historia en cuestión, escrito antes de implementarla |
| **S3** | Sprint | S0 a S4 en el trimestre |
| **R16** | Riesgo del registro de riesgos | Del charter del proyecto |
| **OE2**, **CG-1**, **BD-1** | Criterio de rúbrica | La materia y el criterio que la historia cubre; la matriz de trazabilidad cruza cada historia con ellos |

Los números **no indican prioridad ni orden de ejecución**: H1.6 no se hizo
antes que H1.5 por llamarse así. El orden real está en el backlog y en los
archivos de tareas por persona.
