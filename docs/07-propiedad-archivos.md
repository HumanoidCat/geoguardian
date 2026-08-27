# Propiedad de archivos

Un archivo, un dueno. Nadie modifica la carpeta de otra persona. Si necesitas un
cambio fuera de tu carpeta, se pide, no se hace.

## Carpetas con dueno unico

| Carpeta | Dueno | Contenido |
|---|---|---|
| backend/api | Cesar | Endpoints, enrutamiento, dependencias de FastAPI |
| backend/etl | Cesar | Extractores, limpieza, carga |
| basedatos | Cesar | DDL, seguridad, procedimientos, respaldos, consultas |
| backend/senales | **Luna** | Filtrado, remuestreo, espectro, SPI, anomalias |
| backend/modelado | Alejandro | Etiquetado, linea base, entrenamiento, evaluacion, SHAP |
| infra | Alejandro | Docker, manifiestos de Kubernetes |
| .github/workflows | Alejandro | Pipelines de integracion y despliegue continuo |
| docs/adr | Alejandro | Registros de decisiones de arquitectura |
| backend/calidad | Luna | Reporte de calidad de datos, perfilado |
| backend/tests | Luna | Suite de pruebas |
| docs/investigacion | Luna | Referencias, estado del arte, catalogo de eventos, plan de pruebas |
| docs (resto) | Alejandro | Documento IEEE, bitacoras, matrices, roadmap, manuales |
| frontend | Avril | Visor, tablero, componentes, estilos |

## Las carpetas que faltaban en esta tabla

Lo pregunto Avril el 20 de agosto, al quedar bloqueada en H1.6: **`datos/` no
figuraba en ninguna parte**, ni antes ni despues de D-16. Tampoco `notebooks/`.
Dos carpetas de primer nivel sin dueno declarado, y una de ellas es donde
escriben tres personas.

| Carpeta | Regla | Por que |
|---|---|---|
| `datos/` | **Escritura libre**, como `docs/evidencias/` | Todo su contenido esta en `.gitignore` y nunca se versiona. Lo que se escribe ahi no puede colisionar entre ramas, asi que pedir permiso no controla nada |
| `notebooks/` | **Escritura libre**, con una regla | Cada quien crea los suyos con su prefijo: `avril-`, `cesar-`, `luna-`, `arz-`. Nadie edita el de otro |
| `contratos/` | **Archivo compartido**, no carpeta con dueno | Ya estaba en la lista de archivos compartidos de mas abajo. Se anota aca para que no haya que buscarlo en dos sitios |

**Sobre `datos/`, una advertencia que vale mas que la regla.** Que sea de escritura
libre no significa que lo que hay dentro sea compartido: **cada quien tiene su
propia copia y hoy nadie puede decir si son la misma.** Eso lo resuelve **H1.7**,
versionar el dataset consolidado, que sigue abierta. Mientras tanto, un resultado
calculado sobre `datos/` no es reproducible por otra persona.

## Excepcion: la descarga de Sentinel-2, para H1.6

`backend/etl/` es de Cesar. La historia **H1.6** —descargar imagenes Sentinel-2 de
estacion seca— es de Avril, y su script es un extractor: pertenece ahi y no en
`frontend/`.

| Quien | Donde | Para que historia |
|---|---|---|
| Avril | `backend/etl/fuentes/sentinel.py` y su prueba en `backend/tests/` | H1.6, y nada mas |

**Por que ahi y no en la carpeta de Avril.** Un extractor que vive en `frontend/`
porque lo escribio la persona del frontend es organizar el codigo por autor en vez
de por funcion. El dia que alguien busque de donde salen las imagenes, va a mirar
donde estan los otros extractores.

Es el mismo criterio de **D-16** y la misma forma que la excepcion de H6.6:
**estrecha, por historia, y escrita.** Si hiciera falta tocar otro archivo de
`backend/etl/`, se pide.

**Cesar revisa el Pull Request**, como dueno de la carpeta.

## Excepcion: backend/senales y backend/modelado

Las dos carpetas se reparten historias entre tres personas, asi que la regla de un
dueno por carpeta se relaja de forma explicita en vez de obligar a pedir permiso
seis veces.

| Quien | Donde | Para que historias |
|---|---|---|
| Cesar | `backend/senales` | H2.5, H2.6 |
| Cesar | `backend/modelado` | H3.3, H3.4, H3.5, H3.7 |
| Alejandro | `backend/senales` | lo que necesiten sus historias de modelado |

**Por que se corrigio.** `backend/senales` figuraba como carpeta de Alejandro, pero
las cinco historias de senales son de Luna y dos de Cesar: ninguno de los dos podia
escribir una linea sin una solicitud de cambio por archivo. Es el mismo bloqueo que
tuvo Avril con `frontend/package.json` el 12 de agosto, y se corrigio antes de que
volviera a ocurrir en lugar de despues.

La regla que se aplica es la misma que salio de aquel caso: **la propiedad sigue al
trabajo asignado, no al reves.**

## Excepcion: frontend/src/datos/cliente.js, para H6.6

`frontend/` es de Avril. La historia **H6.6** —cambiar el origen de datos del visor
de los JSON estaticos a la API real— es de Alejandro, y toca ese archivo.

| Quien | Donde | Para que historia |
|---|---|---|
| Alejandro | `frontend/src/datos/cliente.js` y la configuracion de entorno del visor | H6.6, y nada mas |

**Que resulto ser "la configuracion de entorno del visor".** Al ejecutar H6.6 el
20 de agosto fue exactamente **un archivo mas**: el bloque `server.proxy` de
`frontend/vite.config.js`, para que el visor llegue a la API por una ruta relativa
y no haga falta CORS. El resto de ese archivo no se toco. Se anota aca con nombre
propio para que la excepcion no quede abierta a interpretacion.

`frontend/public/simulados/*.json` se **regeneraron** corriendo
`exportar_simulados.py`, que es de Avril y no se modifico. Son artefactos
derivados: sin regenerar, el respaldo declaraba contratos v1.3.0 mientras la API
declaraba v1.3.1.

**Por que no se le asigna a Avril.** El cambio no es de presentacion: es de
arquitectura, sustituye la costura que D-14 dejo puesta a proposito y depende de
conocer los esquemas de la API. Avril diseño el archivo justamente para que esto
fuera un cambio de una constante y ningun componente se enterara; el trabajo esta
del lado de la API, no del visor.

**Por que la excepcion es tan estrecha.** Solo ese archivo y la configuracion. Los
componentes, los estilos y el exportador siguen siendo de Avril sin excepcion. Si
hiciera falta tocar un componente, se pide.

Es el mismo criterio de **D-16**: la propiedad de un archivo sigue al trabajo
asignado, y se declara por historia y no en general.

## Excepcion: el arreglo de la geometria publicada, por I-10

`frontend/` es de Avril. El **24 de agosto** el sitio publicado mostraba el
canton como ocho rectangulos sobre una grilla, y el arreglo cruza tres carpetas.

| Quien | Donde | Para que |
|---|---|---|
| Alejandro | `frontend/herramientas/exportar_simulados.py`, la bandera y los textos de geometria | I-10, y nada mas |
| Alejandro | `frontend/src/componentes/AvisoModoSimulado.jsx`, solo los textos y cuando se muestra cada banda | I-10, y nada mas |
| Alejandro | `frontend/src/componentes/PanelDistrito.jsx`, **solo el texto de la nota de geometria** | I-10, y nada mas |
| Alejandro | `frontend/src/componentes/MapaCanton.jsx`, **solo un comentario** | I-10, y nada mas |

**Por que no se le pide a Avril y ya.** Porque **el origen del defecto es mio**:
la funcion `_cuadro()` de `contratos/simulados/datos.py`, en los contratos
congelados del 3 de agosto. Avril exporto correctamente lo que el simulado le
daba. Pedirle que arregle la consecuencia de un archivo mio, a cuatro dias del
Primer Avance, seria pasarle un trabajo que no origino.

**Por que son cuatro y no dos.** Las dos ultimas aparecieron al revisar el
`dist` construido en vez de confiar en los verificadores: **la frase que decia
que la geometria era un marcador de posicion seguia en el bundle publicado**, en
la ficha que se abre al hacer clic en un distrito. Se habia corregido la banda de
arriba y no se busco el resto.

**Por que es tan estrecha.** No se toca ningun componente del mapa, ni los
estilos, ni la logica de datos, ni el calculo de nada. Solo cadenas de texto y
una condicion:

- en el exportador, la bandera `geometria_simulada` y los textos de geometria
- en el aviso, el texto y cuando aparece cada banda —**no** se quita el aviso de
  datos simulados, que lo exigen los contratos y el criterio CA-7 de H11.5—
- en la ficha del distrito, el texto de una nota
- en el mapa, un comentario

**Que queda de Avril, sin excepcion.** La interfaz. El apilamiento de bandas, la
tipografia, el espaciado y todo lo demas que haya que mejorar para el avance se
pide, no se hace.

Es el mismo criterio de **D-16**: la propiedad sigue al trabajo asignado, y la
excepcion se declara por caso y con fecha, no en general.

## Excepcion: la publicacion del visor, para H11.5

`frontend/` es de Avril. La historia **H11.5** —publicar el visor como sitio
estatico— es de Alejandro y toca dos archivos suyos.

| Quien | Donde | Para que historia |
|---|---|---|
| Alejandro | `frontend/vite.config.js`, solo la clave `base` | H11.5, y nada mas |
| Alejandro | `frontend/src/datos/cliente.js`, solo las rutas de `RESPALDO` | H11.5, y nada mas |

**Por que hacen falta las dos.** GitHub Pages sirve en un **subdirectorio**,
`/geoguardian/`, y ahi toda ruta absoluta de raiz se rompe. Son dos problemas
distintos y ninguno se arregla solo:

- `vite.config.js` resuelve lo que Vite reescribe: el `index.html` y los
  `import`. Sin `base`, los `assets/` se piden desde la raiz del dominio.
- `cliente.js` resuelve lo que Vite **no** reescribe: `RESPALDO` son cadenas que
  se arman en tiempo de ejecucion. Medido antes de arreglarlo, servido desde un
  subdirectorio, el respaldo daba **404** y el visor se quedaba sin ningun
  origen. En el sitio publicado el respaldo es el unico origen que existe,
  porque no hay API.

**Por que no se le asigna a Avril.** No es un cambio de presentacion: es donde
vive el artefacto construido, y depende de conocer la negociacion de origen de
D-23 y el comportamiento de `base` en Vite. Ningun componente cambia.

**Por que `base: './'` y no `'/geoguardian/'`.** Un valor fijo obligaria a Avril
a entrar a `localhost:5173/geoguardian/` para trabajar. `'./'` deja el servidor de
desarrollo sirviendo en la raiz, funciona en cualquier subdirectorio, y no
necesita variables de entorno —que ademas fallarian con `no-undef` en su
`eslint.config.js`, como ya paso en H6.6—.

**Por que la excepcion es tan estrecha.** Dos claves, no dos archivos. Los
componentes, los estilos, el exportador y el resto de la configuracion siguen
siendo de Avril sin excepcion.

Es el mismo criterio de **D-16** y la misma forma que las excepciones de H1.6 y
H6.6: **estrecha, por historia, y escrita.**

**Avril revisa el Pull Request**, como dueña de la carpeta.

## Excepcion: docs/evidencias/

`docs/` pertenece a Alejandro, pero **`docs/evidencias/` es de escritura libre**
para todo el equipo. Cada integrante sube la evidencia de sus propias historias
sin pedir autorizacion.

La razon es practica: son 84 historias, cada una con su evidencia. Exigir una
solicitud de cambio por cada una convertiria al Lead PM en cuello de botella de
algo que no aporta ningun control real.

Sigue requiriendo solicitud: crear una carpeta nueva de primer nivel dentro de
`docs/evidencias/`, o modificar la evidencia de otra persona.

## Lo que se genera no se edita

Dos cosas son **artefactos derivados**. Nadie las abre para escribir en ellas, ni
siquiera Alejandro:

- `docs/05-matriz-trazabilidad.md`, la tabla completa.
- La **linea de avance** de `docs/08-backlog.md`, la que dice cuantas historias
  van cerradas. El resto de ese archivo si se edita a mano.

Se produce con:

    python docs/herramientas/generar_matriz.py

Para cambiar una fila se cambia su fuente:

| Que queres cambiar | Donde se cambia | Quien puede |
|---|---|---|
| Que la historia figure como terminada | `docs/tareas/<persona>.md`, marcando `[x]` | Su dueno |
| El archivo de evidencia que aparece | Subirlo a `docs/evidencias/`, con el nombre `<ID>-<algo>.md` | Su dueno |
| El dueno o la rubrica | `docs/backlog.csv` | Alejandro |
| El requisito, el modulo o la prueba | `docs/trazabilidad.csv` | Alejandro |

**Por que.** Era el archivo mas conflictivo del repositorio: lo tocaban las cuatro
personas, casi siempre en el mismo bloque de filas, y nada lo comprobaba. En dos
dias produjo tres conflictos de fusion, tres duenos desfasados y cuatro historias
cerradas sin fila. Uno de esos defectos le quito trabajo del plato a una persona
durante un dia.

**La linea de avance** se agrego el 19 de agosto por la incidencia **I-07**: era
una cifra derivada escrita a mano, y rompia el CI de quien cerrara la siguiente
historia sin haber roto nada.

**Si aparece un conflicto de fusion en la matriz, no se fusiona a mano:**

    git checkout --ours docs/05-matriz-trazabilidad.md
    python docs/herramientas/generar_matriz.py

Es la misma idea que `ruff format`: un archivo derivado no se discute, se vuelve a
producir. `verificar_estado.py` comprueba en el CI que corresponda a sus fuentes.

### Antes de regenerar hay que estar al dia con `dev`

Un artefacto derivado no se genera desde el disco solamente: se genera desde **el
disco que tenga esa rama**. Regenerarlo en una rama vieja produce un archivo
correcto para el pasado y equivocado para el presente, y el CI lo rechaza igual.

**El orden es este, y no el otro:**

    git checkout <mi-rama>
    git merge origin/dev                            # 1. traer dev PRIMERO
    python docs/herramientas/generar_matriz.py      # 2. regenerar DESPUES
    git add -A && git commit -m "merge: traer dev y regenerar la matriz"

**Por que.** El 20 de agosto, `feature/lal-h1.5-calidad-datos` estaba **18 commits
detras de dev**. En esos 18 commits habian cambiado dos clases de cosas, y las dos
entran en la matriz:

| Que cambio en dev | Efecto sobre la matriz regenerada en la rama vieja |
|---|---|
| `docs/herramientas/generar_matriz.py` | La genera el **generador viejo**, que listaba una sola evidencia por historia en vez de todas |
| Tres archivos nuevos en `docs/evidencias/` | Sus filas apuntan a la carpeta y no al archivo, porque en esa rama el archivo no existe |

Regenerar primero y traer `dev` despues no arregla nada: el `git merge` posterior
abre conflicto en la matriz, y quien lo resuelva a mano vuelve a caer en lo que
esta seccion prohibe.

**Como se reconoce.** Si el CI sigue rojo despues de regenerar, casi siempre es
esto. Se comprueba con:

    git log --oneline HEAD..origin/dev | wc -l

Si no da cero, la rama esta atrasada y hay que fusionar antes de volver a generar.

## Archivos compartidos

**Se MODIFICAN solo por solicitud de cambio** aprobada por Alejandro y por el
dueno del modulo afectado:

- contratos/ (todo el contenido)
- docs/trazabilidad.csv
- docker-compose.yml
- .env.example
- requirements.txt
- frontend/package.json
- .github/workflows/

### La regla aplica a modificar, no a crear

**Crear por primera vez uno de estos archivos, dentro de la propia carpeta, no
requiere solicitud.** El dueno de la carpeta lo declara en el Pull Request y
listo.

La distincion sale de un bloqueo real: `frontend/package.json` estaba en esta
lista y `frontend/` no tenia ningun archivo de proyecto. Avril no podia crear el
andamiaje de Vite sin generar `package.json`, y no podia generar `package.json`
sin aprobacion. La regla se habia escrito pensando en proteger un archivo
existente de cambios ajenos, no en impedir que una carpeta vacia arrancara.

Lo que sigue exigiendo solicitud:

- Modificar cualquiera de estos archivos una vez que existe.
- Agregar una dependencia que no este en el stack cerrado del proyecto.
- Crear o modificar un archivo compartido que este fuera de tu carpeta. El caso
  claro es `contratos/`, que no es de nadie y afecta a los cuatro.

**Leer un archivo compartido nunca requiere solicitud.** Leer `contratos/` para
generar algo dentro de la propia carpeta es uso normal, no modificacion.

## Por que esta regla

Con cuatro personas trabajando en paralelo sobre el mismo repositorio, los
conflictos de fusion son el mayor consumidor silencioso de tiempo. Un dueno por
carpeta los reduce casi a cero y hace que las revisiones sean rapidas, porque
cada quien revisa territorio que conoce.


## Nota sobre la documentacion

Alejandro es el dueno de `docs/` porque tiene el contexto completo del proyecto y
es quien puede sostener la coherencia entre arquitectura, resultados y redaccion.

Luna es dueno de `docs/investigacion/`, que alimenta al documento IEEE con
insumos que no requieren contexto arquitectonico: referencias, estado del arte,
catalogo de eventos historicos y plan de pruebas.

La division existe para que el documento tenga una sola voz sin convertir a
Alejandro en cuello de botella para todo lo escrito.

## Excepción: las imágenes de contenedor, para H6.0

**Concedida el 2026-08-26.** Pedida por César, que **paró H6.0 antes de escribir**
al ver que la historia era suya y las tres carpetas donde vive eran de otros.

| Quién | Dónde | Para qué historia |
|---|---|---|
| César | `infra/docker/api.Dockerfile` y su `.dockerignore` | **H6.0, y nada más** |
| César | `frontend/Dockerfile` y su `.dockerignore` | **H6.0, y nada más** |
| César | `docker-compose.yml`, **solo los dos servicios nuevos** | **H6.0, y nada más** |

**Avril revisa el Pull Request por la parte del visor**, igual que César revisa el
de Sentinel-2 por ser dueño de `backend/etl`.

**Por qué la excepción es tan estrecha.** Nada de `infra/k8s`, ningún componente ni
estilo del visor, y del compose **solo se agregan bloques**: el servicio `db` no se
toca. Fuera de eso, `infra` sigue siendo de Alejandro y `frontend` de Avril.

**Por qué no se partió la historia en dos.** Era la alternativa que César mismo
propuso —él la imagen de la API, Avril la del visor— y la descartó su propio
argumento: H6.0 son **2,9 h**, y partirla deja dos pedazos de hora y media más la
coordinación entre ellos. Avril tiene 25 h del Sprint 2 abiertas y H1.6 del
Sprint 1.

**Y dónde va el Dockerfile de la API: en `infra/docker/`.** César preguntó si no
sería mejor `backend/api/`, junto al código que empaqueta, que además caería en su
carpeta y evitaría el permiso. Se descartó por una razón concreta: `init-db` ya
vive en `infra/docker/` y esta tabla dice que `infra` es «Docker, manifiestos de
Kubernetes». **Mover un archivo para no necesitar permiso sería dejar que la
propiedad de archivos decida la arquitectura**, y los permisos existen para evitar
que dos personas se pisen, no para determinar dónde vive una cosa.

> **Por qué esto está escrito acá y no solo en el mensaje que se le respondió.**
> Un mensaje fuera del repositorio es un lugar más declarando estado, y ninguna
> máquina lo cruza. César llegó a este pedido leyendo un backlog de cinco días
> atrás; el permiso que se le concede no puede vivir en un archivo con el mismo
> problema. Si el mensaje y esta tabla llegaran a decir cosas distintas, **manda
> esta tabla**.

## `pyproject.toml` · compartido, y hasta hoy sin declarar

**Agregado el 2026-08-27.** Lo señaló César, y es el mismo hueco que Avril había
encontrado con `datos/` y `notebooks/`: un archivo que todo el mundo puede
necesitar y que no estaba ni en la tabla de carpetas ni en la lista de
compartidos.

| Sección | Quién la toca | Cómo |
|---|---|---|
| `[tool.ruff]` | Alejandro | directo |
| `[tool.pytest.ini_options]` | **cualquiera**, con solicitud | afecta a las pruebas de los cuatro |
| dependencias | **cualquiera**, con solicitud | el stack está cerrado |

**Por qué importa que `testpaths` sea compartido y no de una persona.** Apuntaba a
`backend/tests`, que es la carpeta de Luna, así que las pruebas que cada quien
escribe junto a su módulo **no las ejecutaba nadie**. El 27 de agosto eran 46 de
César, invisibles mientras el CI reportaba 130 en verde. Desde hoy apunta a
`backend/` y se recogen 176.

Es I-06: el CI corriendo pytest de una forma que ninguna persona usa.

## Ampliación de la excepción de H6.0 · `frontend/nginx.conf`

**Agregada el 2026-08-27.** La excepción original cubría el `Dockerfile` del visor
y su `.dockerignore`, y César respetó ese límite escribiendo la configuración de
nginx **dentro** del Dockerfile con `printf`, declarándolo:

> Normalmente iría en `frontend/nginx.conf`. La excepción que me dieron cubre este
> archivo.

Respetó el límite correctamente. **El límite estaba mal puesto por mí**: veinte
líneas de `printf` escapado son más difíciles de leer y de corregir que un archivo
de configuración.

Queda autorizado **`frontend/nginx.conf`, para H6.0 y para su mantenimiento
posterior**, con Avril revisando el Pull Request igual que en el resto de la
excepción. No hace falta rehacer lo ya fusionado: se mueve la próxima vez que
alguien lo toque.
