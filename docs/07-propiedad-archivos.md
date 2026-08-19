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

## Excepcion: docs/evidencias/

`docs/` pertenece a Alejandro, pero **`docs/evidencias/` es de escritura libre**
para todo el equipo. Cada integrante sube la evidencia de sus propias historias
sin pedir autorizacion.

La razon es practica: son 84 historias, cada una con su evidencia. Exigir una
solicitud de cambio por cada una convertiria al Lead PM en cuello de botella de
algo que no aporta ningun control real.

Sigue requiriendo solicitud: crear una carpeta nueva de primer nivel dentro de
`docs/evidencias/`, o modificar la evidencia de otra persona.

## La matriz de trazabilidad no se edita: se genera

`docs/05-matriz-trazabilidad.md` **es un archivo derivado**. Nadie lo abre para
escribir en el, ni siquiera Alejandro.

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

**Si aparece un conflicto de fusion en la matriz, no se fusiona a mano:**

    git checkout --ours docs/05-matriz-trazabilidad.md
    python docs/herramientas/generar_matriz.py

Es la misma idea que `ruff format`: un archivo derivado no se discute, se vuelve a
producir. `verificar_estado.py` comprueba en el CI que corresponda a sus fuentes.

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
