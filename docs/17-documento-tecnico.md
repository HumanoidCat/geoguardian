---
author:
  - name: "Alejandro Josué Rodríguez Zamora"
  - name: "César Andrés Ubau Calvo"
  - name: "Luis Alejandro Luna García"
  - name: "Avril Madrigal Elizondo"
institute: "Universidad Invenio · Ingeniería en Tecnologías de Información · III Trimestre 2026"
date: "27 de agosto de 2026"
lang: es
---

# GeoGuardian: documento técnico. Arquitectura, tecnologías y verificación de un sistema de estimación de riesgo climático distrital

::: no-entregable

**Historia:** H10.4 y H10.5c · **Responsable:** Alejandro
**Fuente única.** Este archivo genera el PDF de entrega. El `.pdf` es artefacto.

:::

## Resumen

Se documenta la construcción técnica de **GeoGuardian**, un sistema de estimación
de riesgo climático a escala distrital para el cantón de Tilarán, Costa Rica,
edificado exclusivamente sobre datos abiertos. Se describen el conjunto de
tecnologías y la justificación de cada elección, la arquitectura en cuatro capas,
el modelo de datos geoespacial sobre PostGIS, los contratos congelados que
desacoplan los cuatro frentes de trabajo, el flujo de procesamiento desde la
fuente satelital hasta el visor, y el esquema de verificación continua.

El eje del diseño es un principio que se aplica de forma uniforme: **una sola
fuente, vistas derivadas, y una máquina que comprueba que coinciden.** Se reporta
cómo ese principio se materializa en **26 verificadores automáticos** integrados
a seis trabajos de integración continua, y se documentan las tres incidencias en
que su ausencia produjo defectos que ningún control detectó.

*Palabras clave:* arquitectura de software, PostGIS, contratos de interfaz,
verificación continua, sistemas geoespaciales, datos abiertos.

## I. Alcance y contexto

### A. Qué construye este sistema

GeoGuardian estima el riesgo de tres eventos climáticos —**lluvia intensa,
sequía e incendio forestal**— para cada uno de los ocho distritos del cantón de
Tilarán, con un horizonte de siete días. El destinatario es el Comité Municipal
de Emergencias.

El cantón mide **669,23 km²** y se extiende 30,7 × 36,6 km. Sus ocho distritos
son Tilarán, Quebrada Grande, Tronadora, Santa Rosa, Líbano, Tierras Morenas,
Arenal y Cabeceras.

### B. Qué está construido hoy

| Componente | Estado |
|---|---|
| Base de datos PostgreSQL + PostGIS | Cargada y operativa |
| ETL de series climáticas y focos de calor | Operativo |
| API REST con OpenAPI | Implementada |
| Visor web | **Publicado** en GitHub Pages |
| Etiquetado de la variable objetivo | Cerrado |
| Validación temporal y líneas base | Cerradas |
| Modelos de aprendizaje supervisado | **No implementados** |

El sistema tiene hoy el andamiaje completo y **el piso de comparación medido**;
lo que falta son los tres algoritmos que se comparan contra ese piso.

### C. Restricciones que gobiernan el diseño

1. **Solo datos abiertos.** Ninguna fuente de pago ni instrumentación propia.
2. **Cuatro personas, cuatro frentes.** El desacople entre ellos no es una
   preferencia: es la condición para avanzar en paralelo.
3. **Todo lo que se afirme tiene que poder comprobarse por una máquina.**

## II. Tecnologías

### A. Lenguajes y ejecución

| Capa | Tecnología | Versión |
|---|---|---|
| Backend, ETL, modelado | Python | 3.11 / 3.12 |
| Frontend | JavaScript (ES2022) + React | 18.3 |
| Base de datos | PostgreSQL + PostGIS | 16 / 3.4 |
| Contenedores | Docker, Docker Compose | — |
| Orquestación local | k3d (Kubernetes) | — |

### B. Bibliotecas del backend

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

### C. Bibliotecas del frontend

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

### D. Por qué PostGIS y no un archivo

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

## III. Arquitectura

### A. Estructura en cuatro capas

![Componentes del sistema](diagramas/componentes.png)

La separación es la de un diseño por capas convencional, con una particularidad:
**la capa de dominio no depende de ninguna otra**. Los contratos son estructuras
`Protocol` de Python y esquemas Pydantic sin importaciones de FastAPI, de
SQLAlchemy ni de nada de infraestructura.

### B. Los contratos congelados

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
ejecución del pipeline y es el primero de los seis trabajos de integración
continua.

### C. Flujo de datos, de la fuente a la pantalla

![Flujo de datos, de la fuente abierta al visor](diagramas/flujo-datos.png)

### D. Secuencia de una consulta

![Consulta de riesgo por distrito](diagramas/secuencia-consulta-riesgo.png)

La rama alterna del diagrama es **D-23** y está en producción hoy: el visor
publicado consulta `/api`, recibe 404 porque no hay servicio desplegado, y
**degrada al respaldo estático declarándolo en pantalla**.

La decisión que sostiene ese comportamiento es que el origen se negocia **una
sola vez** al arrancar, no en cada petición. Reintentar por consulta produciría
una interfaz que a veces muestra datos reales y a veces simulados sin que el
usuario pueda saber cuál está viendo.

## IV. Modelo de datos

![Modelo entidad-relación](diagramas/entidad-relacion.png)

### A. Los cuatro esquemas

| Esquema | Contiene | Por qué separado |
|---|---|---|
| `geo` | Provincia, cantón, distrito | Vocabulario territorial, cambia casi nunca |
| `crudo` | Mediciones diarias, focos de calor, catálogo de fuentes | Lo descargado, sin transformar |
| `analitico` | Riesgo estimado | Lo derivado; se puede recalcular |
| `control` | Migraciones aplicadas | Metadatos del propio esquema |

La separación permite una operación concreta: **`analitico` se puede vaciar y
reconstruir** sin tocar lo descargado. Si se mezclara con `crudo`, recalcular
exigiría volver a bajar datos de las APIs externas.

**`analitico.riesgo` no está creada.** Ninguna historia la produce y es una deuda
declarada, no un olvido.

### B. Claves e integridad

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

### C. Migraciones con suma de verificación

`control.migracion` registra número, archivo, **suma SHA-256** y fecha de
aplicación. La suma responde una pregunta que el número no puede: *¿el archivo de
migración 004 que está aplicado en esta base es el mismo que hay en el
repositorio hoy?*

Sin ella, editar una migración ya aplicada produce dos bases que se creen iguales
y no lo son.

### D. La proyección, medida y no supuesta

Las geometrías se almacenan en **EPSG:4326** porque es lo que Leaflet consume, y
se transforman a **EPSG:8908** (CR-SIRGAS / CRTM05) para todo cálculo métrico.

La transformación se verificó contra una implementación independiente de la
proyección transversa de Mercator sobre el elipsoide GRS80: la diferencia máxima
medida es de **0,005 mm**, lo que confirma que no hay desplazamiento de datum
entre los dos sistemas y que la conversión no introduce error apreciable.

## V. Procesamiento

![Flujo del modelado](diagramas/flujo-modelado.png)

### A. Fuentes y su resolución

| Variable | Fuente | Resolución | Aptitud |
|---|---|---|---|
| Precipitación | CHIRPS 2.0 vía ClimateSERV | 0,05° | Cada distrito cae en celda propia |
| Temperatura, humedad, viento, radiación | NASA POWER | 0,5 × 0,625° | **Una sola celda cubre el cantón** |
| Focos de calor | NASA FIRMS, MODIS C6.1 | 1 km, desde 2001 | Puntual |
| Geometrías | SNIT / IGN, límite distrital 5k | Vectorial | — |

La fuente es **híbrida por necesidad**, no por gusto: **D-15**. Una celda de
POWER mide 68 × 55 km y cubre el cantón entero, de modo que temperatura, humedad,
viento y radiación **tienen el mismo valor en los ocho distritos**. Se conservan
como contexto y se declara la limitación; la única variable que distingue
distritos es la precipitación.

### B. Índices y umbrales

- **Sequía:** SPI-3 ajustado **por mes calendario** (D-19), con cortes en −1,0
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

### C. Etiquetado y cobertura

El etiquetado produce **99 296 filas** con tres etiquetas cada una. La cobertura
temporal difiere por evento:

| Evento | Cobertura |
|---|---|
| Lluvia intensa, sequía | 1991–2025 |
| Incendio | **2001–2024** |

La ventana del incendio arranca en 2001 porque el archivo FIRMS de MODIS C6.1
empieza ahí. Etiquetar como «bajo» los diez años anteriores habría producido
**29 216 filas falsamente negativas, el 29,4 % del conjunto**. Las filas fuera de
cobertura devuelven ausencia, no cero.

Esa distinción —ausencia contra cero— es una regla transversal del sistema
(**D-07**) y aparece en el esquema, en el etiquetado, en las líneas base y en el
visor, que pinta con trama los distritos sin estimación en vez de usar el color
más claro de la escala.

### D. Validación temporal

Ventana expansiva con **cinco pliegues** y cortes en frontera de mes (**D-04**).
El embargo entre entrenamiento y prueba **se calcula** a partir de hasta dónde
mira la etiqueta de la última fila de entrenamiento, en lugar de fijarse como
constante.

Medido: **siete días para los tres eventos**. Para la sequía, el corte en
frontera de mes absorbe el alcance del SPI-3, lo que reduce el embargo de los 38
días estimados a 7.

## VI. Interfaz de programación

### A. Endpoints

| Método y ruta | Devuelve |
|---|---|
| `GET /salud` | Estado del servicio y modo de datos |
| `GET /distritos` | Los ocho distritos con su geometría |
| `GET /distritos/{codigo}` | Un distrito |
| `GET /distritos/{codigo}/mediciones` | Serie climática del distrito |
| `GET /distritos/{codigo}/riesgo` | Riesgo estimado del distrito |
| `GET /riesgos` | Riesgo de los ocho, por evento y fecha |

La especificación OpenAPI se genera desde los esquemas Pydantic, de modo que
**no puede desincronizarse de lo que el servicio realmente acepta y devuelve**.
Es el mismo principio que gobierna la matriz de trazabilidad y los diagramas.

### B. El acceso a datos

Se implementa el patrón Repository sobre el `Protocol` de `contratos`. Su valor
práctico es que las pruebas del servicio corren **sin base de datos**: se
sustituye la implementación PostgreSQL por una en memoria que cumple el mismo
contrato.

## VII. Visor

### A. Composición

React 18 con Leaflet. Las capas son independientes y conmutables: coropleta de
riesgo, mapa de calor interpolado, límites distritales y etiquetas de nombre.

### B. La escala de color, verificada por colorimetría

La escala de tres niveles no se eligió por gusto. `verificar_escala.py` comprueba
en cada ejecución del pipeline que:

- la **luminancia es monótona** entre niveles;
- el **contraste cumple WCAG** sobre todos los fondos posibles;
- el **orden se conserva** bajo protanopia, deuteranopia y tritanopia;
- la marca de selección **no usa negro puro**.

Un mapa de riesgo cuyo orden se pierde para una persona con dicromacia no
comunica el riesgo: lo oculta.

### C. Interpolación y su recorte

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

## VIII. Verificación

### A. Seis trabajos de integración continua

| Trabajo | Qué comprueba |
|---|---|
| Contratos y simulados | 47 comprobaciones sobre las interfaces congeladas |
| Backlog y documentación | Estado, horas, ADR, cifras, diagramas, tablero |
| Linter y formato | `ruff` sobre todo el código Python |
| Frontend | ESLint, construcción, escala de color, recorte |
| Pruebas contra PostgreSQL | 176 pruebas, con PostGIS como servicio |
| Publicar el visor | Solo desde `main` |

### B. Veintiséis verificadores

Cada historia con criterios de aceptación escritos antes de implementar tiene un
programa que los comprueba. No son pruebas unitarias: **comprueban propiedades
del resultado**, y varios incluyen una **prueba negativa** que confirma que el
control sabe fallar.

Ejemplos:

- `verificar_h32.py`: 61 comprobaciones sobre la partición temporal, incluida una
  partición deliberadamente contaminada que **tiene que** salir en rojo.
- `verificar_h36.py`: contrasta dos caminos independientes hasta la misma cifra y
  exige que coincidan a menos de 1e-12.
- `verificar_recorte_calor.mjs`: ejecuta la función de dibujo real sobre un
  canvas simulado y compara contra una implementación independiente de
  punto-en-polígono.

### C. Los artefactos derivados no se editan

| Artefacto | Se deriva de |
|---|---|
| Matriz de trazabilidad | `docs/trazabilidad.csv` y los archivos de tareas |
| Los seis diagramas | El DDL y el generador |
| Cifras de la documentación | El repositorio, recalculadas en cada ejecución |
| Especificación OpenAPI | Los esquemas Pydantic |

**43 apariciones numéricas** de la documentación se recalculan automáticamente y
hacen fallar la integración continua si se desfasan. El control se agregó porque
hacía falta: en ocho días, cinco cifras del documento de investigación habían
dejado de ser ciertas sin que nadie lo notara.

### D. Tres lecciones que costaron

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

## IX. Despliegue

![Arquitectura de despliegue](diagramas/despliegue.png)

### A. Lo que está desplegado

**Solo el visor**, como sitio estático en GitHub Pages, publicado desde `main`
por un trabajo del propio pipeline. No hay servicio externo de despliegue: la
configuración vive en el repositorio y se revisa como cualquier otro código.

El visor se sirve desde un **subdirectorio**, lo que rompe toda ruta absoluta de
raíz, y lo hace **en silencio**: el archivo se pide, devuelve 404, y el visor se
queda sin datos sin mostrar error. Un verificador comprueba sobre el artefacto
construido —no sobre el código fuente— que ninguna ruta absoluta sobreviva.

### B. Lo que no está desplegado

**Ni la API ni la base de datos.** Ambas corren en las máquinas del equipo. La
consecuencia es que el sitio público muestra datos simulados y lo declara.

Es la limitación técnica más visible del sistema y no tiene todavía una historia
asignada que la resuelva.

### C. Reproducibilidad del dataset

El dataset consolidado se versiona **por manifiesto**, no por archivo: un
documento con sumas SHA-256 de cada fuente, sus conteos y sus rangos temporales.
Se descartaron DVC y Git LFS por costo de infraestructura frente al tamaño real
del dato.

El manifiesto responde una pregunta concreta: *¿dos personas tienen exactamente
el mismo dato?* No responde si ese dato es correcto —eso lo mide el reporte de
calidad— y la distinción está escrita para no confundirlas.

## X. Decisiones de arquitectura

Treinta decisiones registradas, cada una con contexto, alternativas descartadas,
consecuencias y criterio de revisión. Las que más gobiernan el código:

| ADR | Decisión |
|---|---|
| D-04 | Validación temporal por ventana expansiva |
| D-06 | Contratos con `Protocol`, no clases abstractas |
| D-07 | La ausencia se representa como nulo, nunca como cero |
| D-10 | F1-macro como métrica principal |
| D-13 | El SNIT es la fuente única del vocabulario territorial |
| D-15 | Fuente climática híbrida: CHIRPS y POWER |
| D-16 | La propiedad de una carpeta sigue al trabajo asignado |
| D-17 | La precipitación no se filtra |
| D-19 | El SPI se ajusta por mes calendario |
| D-21 | `probabilidad` es P(nivel = alto) |
| D-23 | El visor negocia su origen una vez y degrada declarándolo |
| D-25 | El incendio es binario y se acota a tres distritos |
| D-29 | El dataset se versiona por manifiesto |

Una decisión que se deja atrás **no se borra**: cambia de estado y se conserva
entera. El registro distingue tres formas de hacerlo —*revisada*, *sustituida* y
*revertida*—, y la tercera se agregó al comprobar que **D-28 partía de un hecho
falso**. Llamarle «sustituida» habría ocultado justamente lo que había que
aprender.

## XI. Limitaciones técnicas

1. **Una sola variable resuelve el cantón.** De las cinco variables climáticas,
   solo la precipitación distingue distritos.
2. **Sin modelo entrenado.** Existe el arnés de comparación y el piso medido; no
   los tres algoritmos.
3. **Sin servicio en línea.** La API y la base corren solo en local.
4. **`analitico.riesgo` sin implementar.**
5. **El componente de incendio es el más débil.** Un solo evento en el catálogo
   histórico, posterior a la serie etiquetada, y clase positiva del 1,23 %.
6. **Los polígonos simplificados no teselan:** su unión deja 142 huecos diminutos
   entre distritos vecinos. No afecta a los cálculos actuales y queda anotado.

## XII. Instalación y operación

### A. Requisitos

Python 3.11 o superior, Node 20 o superior, Docker con Docker Compose, y
PostgreSQL 16 con PostGIS 3.4 —que Compose levanta.

### B. Puesta en marcha

```bash
git clone https://github.com/HumanoidCat/geoguardian
cd geoguardian

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

docker compose up -d
python -m basedatos.aplicar_migraciones

cd frontend && npm ci && npm run dev
```

### C. Comprobar que la instalación quedó bien

```bash
python -m contratos.verificar          # 47 comprobaciones
python -m pytest                       # 176 pruebas
python -m ruff check .
python docs/herramientas/verificar_estado.py
python docs/herramientas/verificar_documentacion.py
python docs/herramientas/verificar_diagramas.py
```

Las seis órdenes corren sobre el repositorio limpio. Las que necesitan datos
procesados —el contraste contra el catálogo y la tabla comparativa— requieren la
base cargada.

### D. Reconstruir los artefactos

```bash
python docs/herramientas/generar_matriz.py
python docs/herramientas/generar_diagramas.py --png
python docs/herramientas/construir_entregable.py docs/17-documento-tecnico.md --ieee
```
