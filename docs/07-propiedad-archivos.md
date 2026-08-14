# Propiedad de archivos

Un archivo, un dueno. Nadie modifica la carpeta de otra persona. Si necesitas un
cambio fuera de tu carpeta, se pide, no se hace.

## Carpetas con dueno unico

| Carpeta | Dueno | Contenido |
|---|---|---|
| backend/api | Cesar | Endpoints, enrutamiento, dependencias de FastAPI |
| backend/etl | Cesar | Extractores, limpieza, carga |
| basedatos | Cesar | DDL, seguridad, procedimientos, respaldos, consultas |
| backend/senales | Alejandro | Filtrado, remuestreo, espectro, SPI, anomalias |
| backend/modelado | Alejandro | Etiquetado, linea base, entrenamiento, evaluacion, SHAP |
| infra | Alejandro | Docker, manifiestos de Kubernetes |
| .github/workflows | Alejandro | Pipelines de integracion y despliegue continuo |
| docs/adr | Alejandro | Registros de decisiones de arquitectura |
| backend/calidad | Luna | Reporte de calidad de datos, perfilado |
| backend/tests | Luna | Suite de pruebas |
| docs/investigacion | Luna | Referencias, estado del arte, catalogo de eventos, plan de pruebas |
| docs (resto) | Alejandro | Documento IEEE, bitacoras, matrices, roadmap, manuales |
| frontend | Avril | Visor, tablero, componentes, estilos |

## Excepcion: docs/evidencias/

`docs/` pertenece a Alejandro, pero **`docs/evidencias/` es de escritura libre**
para todo el equipo. Cada integrante sube la evidencia de sus propias historias
sin pedir autorizacion.

La razon es practica: son 82 historias, cada una con su evidencia. Exigir una
solicitud de cambio por cada una convertiria al Lead PM en cuello de botella de
algo que no aporta ningun control real.

Sigue requiriendo solicitud: crear una carpeta nueva de primer nivel dentro de
`docs/evidencias/`, o modificar la evidencia de otra persona.

## Archivos compartidos

**Se MODIFICAN solo por solicitud de cambio** aprobada por Alejandro y por el
dueno del modulo afectado:

- contratos/ (todo el contenido)
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

Luna es duena de `docs/investigacion/`, que alimenta al documento IEEE con
insumos que no requieren contexto arquitectonico: referencias, estado del arte,
catalogo de eventos historicos y plan de pruebas.

La division existe para que el documento tenga una sola voz sin convertir a
Alejandro en cuello de botella para todo lo escrito.
