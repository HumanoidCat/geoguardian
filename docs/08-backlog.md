# Backlog completo

**91 historias · 452 puntos · 654.2 horas** (incluye 20 % de revision)

Generado desde `docs/backlog.csv`, que es la fuente de verdad. Las issues de
GitHub y los archivos de `docs/tareas/` salen de ahi. Si algo no coincide,
manda el CSV.

La consistencia se comprueba con `python docs/herramientas/verificar_backlog.py`:
dependencias hacia historias inexistentes, hacia sprints posteriores,
dependencias circulares y carga por persona.

## Avance

**Este archivo no registra que historias estan terminadas, y es deliberado.** El
avance vive en `docs/tareas/<persona>.md`, donde cada quien marca su propio trabajo
con `[x]` y la fecha. Anotarlo tambien aqui crearia un cuarto lugar donde el estado
puede desfasarse, que es exactamente el problema que este proyecto ya tuvo tres
veces.

Para saber como va, sin contar a mano:

    python docs/herramientas/verificar_estado.py

Imprime historias y puntos cerrados, por persona y por sprint, calculados desde el
repositorio. Y **falla si los archivos de tareas y la matriz de trazabilidad no
dicen lo mismo**, que es la comprobacion que faltaba: la auditoria del 18 de agosto
encontro cuatro historias cerradas sin fila en la matriz y dos con el dueno
equivocado.

**El avance no se escribe aqui.** Lo imprime la herramienta, calculado desde el
repositorio en el momento en que se pregunta:

    python docs/herramientas/verificar_estado.py

Historias y puntos cerrados, por persona y por sprint. **Corre ademas en cada
cambio del CI**, asi que la cifra del dia queda en el registro de la ejecucion.

Estuvo escrita aqui del 18 al 20 de agosto y hubo que quitarla: era una cifra
derivada que cambia cada vez que alguien cierra una historia, y el verificador la
comprobaba. Rompio el CI de quien no la habia tocado **tres veces en dos dias**,
incluida una en que dos Pull Requests correctos por separado dejaban `dev` en rojo
al integrarse los dos. Generarla en vez de escribirla redujo el problema pero no
lo elimino: cualquier par de PR que cierre historias sigue chocando en esta linea.

Ver la incidencia **I-07**. Lo propuso Cesar desde el primer dia y tenia razon.

## Carga por persona y sprint

Capacidad comprometida: **18 h por semana**, o sea 36 h por sprint.

| Persona | S0 | S1 | S2 | S3 | S4 | Total | Puntos |
|---|---|---|---|---|---|---|---|
| Alejandro | 35.9 | 36.4** | 103.6** | 59.4** | 73.1** | 308.4 | 205 |
| Cesar | 18.3 | 24.9 | 0.0 | 7.8 | 34.0 | 85.0 | 69 |
| Luna | 25.9 | 34.3 | 31.0 | 40.5** | 32.0 | 163.7 | 96 |
| Avril | 2.9 | 11.5 | 21.1 | 25.0 | 36.6** | 97.1 | 82 |
| **Equipo** | 83.0 | 107.1 | 155.7 | 132.7 | 175.7 | **654.2** | **452** |

Las celdas con `**` estan por encima del compromiso.

## Sprint 0 · semanas 2-3 · 11 historias · 83.0 h

**Foco.** Contratos, infraestructura y validacion de fuentes  
**Hito.** Propuesta aprobada

| Historia | Responsable | Pts | h | Rubrica | Depende de | Bloquea a |
|---|---|---|---|---|---|---|
| **H10.8** Carpeta de evidencias organizada por materia con indice | alejandro | 5 | 4.8 | SO-4 | - | — |
| **H6.4** Seis o mas registros ADR escritos | alejandro | 3 | 7.9 | Arq | - | — |
| **H8.1** docker compose up levanta todo en maquina limpia | alejandro | 5 | 7.8 | SO-1 | - | H10.4, H8.6 |
| **H8.5** Credenciales por variables de entorno, fuera del repositorio | alejandro | 3 | 2.9 | SO-1 | - | — |
| **H8.6** Manifiestos de Kubernetes corriendo en k3d local | alejandro | 8 | 12.5 | Arq | H8.1 | — |
| **H5.1** Mapa del canton con poligonos distritales, zoom y desplazamiento | avril | 3 | 2.9 | CG-4 | contratos | H5.2, H5.3, H5.6 |
| **H1.1** Descargar 10 anios de series climaticas diarias, reejecutable e idempotente | cesar | 5 | 7.8 | BD-1 | H1.3 | H1.4, H1.5, H8.2 |
| **H1.2** Descargar historico de focos de calor filtrado al canton | cesar | 3 | 4.7 | BD-1 | H1.3 | H3.0, H9.3 |
| **H1.3** Cargar geometrias oficiales de distritos con SRID validado | cesar | 6 | 5.8 | BD-1, BD-3 | contratos | H1.1, H1.11, H1.2, H1.8 |
| **H10.1** Plan de pruebas con casos por modulo | luna | 5 | 4.8 | QA | contratos | — |
| **H10.5a** Recopilar 15 referencias IEEE con ficha de contenido | luna | 8 | 21.1 | IEEE | - | H10.5b |

## Sprint 1 · semanas 4-5 · 16 historias · 107.1 h

**Foco.** Dataset consolidado, API y reporte de calidad  
**Hito.** Entrega institucional (semana 4)

| Historia | Responsable | Pts | h | Rubrica | Depende de | Bloquea a |
|---|---|---|---|---|---|---|
| **H10.4** Manual tecnico verificado por alguien ajeno al desarrollo | alejandro | 5 | 4.8 | MVP | H8.1 | — |
| **H11.1** CI: construir imagen Docker y publicar artefactos en ghcr.io | alejandro | 5 | 4.8 | CICD | H6.0, H6.1 | H11.2 |
| **H13.1** Actas de las ceremonias Scrum: planning, dailies, review y retrospectiva | alejandro | 5 | 13.2 | Scrum | - | — |
| **H1.6** Descargar imagenes Sentinel-2 de estacion seca, nubosidad menor a 20% | alejandro | 5 | 7.8 | CG-3 | - | H5.5, H8.4 |
| **H5.2** Cuatro o mas capas conmutables con control de opacidad | avril | 5 | 4.8 | CG-4 | H5.1 | — |
| **H5.3** Coropletas de riesgo por evento con rampa de color y leyenda | avril | 7 | 6.7 | CG-1 | H5.1 | H5.4, H5.7, H7.1 |
| **H1.13** Trigger de auditoria sobre predicciones, con prueba | alejandro | 3 | 2.9 | BD-2 | H1.8, H1.15 | — |
| **H1.15** Crear analitico.riesgo con sus restricciones | alejandro | 3 | 2.9 | BD-2 | H1.3, H1.8 | H1.13 |
| **H1.4** Declarar los criterios de imputacion y probarlos contra huecos inyectados | cesar | 3 | 4.7 | BD-1 | H1.1 | H1.7 |
| **H1.7** Versionar el dataset consolidado para reproducibilidad | cesar | 3 | 2.9 | OE1 | H1.4 | — |
| **H1.8** Crear esquemas, roles y usuarios con minimo privilegio | cesar | 5 | 4.8 | BD-2 | H1.3 | H1.13, H1.9, H10.7 |
| **H6.0** Dockerfile de la API y del visor con imagen construida localmente | cesar | 3 | 2.9 | CICD | H6.1 | H11.1 |
| **H6.1** API REST con OpenAPI y esquemas Pydantic en todos los endpoints | cesar | 5 | 4.8 | Arq | contratos | H11.1, H6.0, H6.2, H6.5, H7.2, H8.3 |
| **H6.2** Patron Repository con pruebas unitarias sin base de datos | cesar | 5 | 4.8 | Arq | H6.1 | H10.2, H6.3 |
| **H10.5b** Estado del arte de Costa Rica | luna | 5 | 13.2 | IEEE | H10.5a | H10.5c |
| **H4.3** Catalogo de 12 o mas eventos historicos del canton con fuente | luna | 8 | 21.1 | OE3 | - | H4.4, H7.3 |

## Sprint 2 · semanas 6-7 · 23 historias · 155.7 h

**Foco.** Modelos entrenados, despliegue continuo y demo de extremo a extremo  
**Hito.** **Primer avance (semana 7)**

| Historia | Responsable | Pts | h | Rubrica | Depende de | Bloquea a |
|---|---|---|---|---|---|---|
| **H6.6** El visor consume la API real en lugar de los JSON estaticos | alejandro | 5 | 4.8 | Arq | H6.1 | — |
| **H11.2** CD: despliegue automatico al entorno de desarrollo al mergear a main | alejandro | 5 | 7.8 | CICD | H11.1 | H11.3, H12.3 |
| **H11.3** CD: despliegue a staging en namespace propio, con aprobacion manual | alejandro | 3 | 4.7 | CICD | H11.2 | H11.4 |
| **H11.4** CD: despliegue a produccion con aprobacion explicita y rollback automatico | alejandro | 5 | 7.8 | CICD | H11.3 | H13.2 |
| **H3.0** Implementar el etiquetado de los tres eventos y su distribucion de clases | alejandro | 8 | 12.5 | OE2 | H2.3, H2.7, H1.2 | H3.1, H3.2 |
| **H3.1** Construir la linea base climatologica por distrito, mes y tipo de evento | alejandro | 6 | 9.4 | OE2 | H3.0 | — |
| **H3.2** Definir y documentar la validacion por ventana expansiva | alejandro | 8 | 12.5 | OE2 | H3.0 | H3.3, H3.4, H3.5 |
| **H10.3** Manual de usuario con capturas paso a paso | avril | 5 | 4.8 | MVP | H7.1 | H10.9 |
| **H10.7** Diagramas de casos de uso y entidad-relacion | alejandro | 5 | 7.8 | Arq | H1.8 | — |
| **H5.6** Transformacion WGS84 a CRTM05 verificada con puntos de control | avril | 3 | 4.7 | CG-1 | H5.1 | — |
| **H5.7** Selector de fecha que recarga el estado del mapa | avril | 3 | 2.9 | CG-4 | H5.3 | — |
| **H5.8** Encuadre del mapa en el canton y marca de seleccion accesible | avril | 3 | 2.9 | CG-1 | H5.1 | — |
| **H7.1** Semaforo de riesgo por distrito y evento con umbrales documentados | avril | 6 | 5.8 | CG-2 | H5.3 | H10.3 |
| **H7.2** Graficas interactivas de series con seleccion de rango | alejandro | 5 | 4.8 | CG-2 | H6.1 | — |
| **H1.11** Particionar mediciones por anio y medir efecto en consultas | alejandro | 5 | 4.8 | BD-1 | H1.3 | H1.12 |
| **H1.12** Indices espaciales y compuestos con planes antes y despues | alejandro | 5 | 4.8 | BD-1 | H1.11 | — |
| **H1.9** Funciones PL/pgSQL con EXCEPTION WHEN, RAISE y bitacora de fallos | alejandro | 8 | 7.7 | BD-3 | H1.8 | H1.10, H12.1 |
| **H2.5** Generar lags, acumulados y medias moviles reproducibles | alejandro | 5 | 4.8 | OE2 | H2.3 | H2.6 |
| **H3.3** Entrenar y evaluar Regresion Logistica | alejandro | 6 | 9.4 | OE2 | H3.2 | — |
| **H1.5** Reporte formal de calidad de datos: faltantes, atipicos, sesgos | luna | 8 | 12.5 | OE1 | H1.1 | — |
| **H2.1** Filtrar ruido de las series con justificacion del filtro | luna | 3 | 2.9 | Senales | H1.4 | H2.2, H2.3, H2.4, H2.7 |
| **H2.3** SPI de 1 y 3 meses por convolucion de ventana movil | luna | 5 | 7.8 | Senales | H2.1 | H2.5, H3.0 |
| **H2.7** Calcular percentiles R95p y R99p de precipitacion acumulada por distrito | luna | 5 | 7.8 | Senales | H2.1 | H3.0 |

## Sprint 3 · semanas 8-9 · 18 historias · 132.7 h

**Foco.** Explicabilidad, visor completo y pruebas  
**Hito.** —

| Historia | Responsable | Pts | h | Rubrica | Depende de | Bloquea a |
|---|---|---|---|---|---|---|
| **H3.6** Tabla comparativa de tres algoritmos contra la linea base, por evento | alejandro | 10 | 15.6 | OE2 | H3.5 | H3.7, H3.8, H4.1, H4.4 |
| **H3.8** Ajuste de hiperparametros del mejor modelo, documentado | alejandro | 3 | 4.7 | OE2 | H3.6 | — |
| **H4.1** Importancia de variables global del mejor modelo | luna | 3 | 2.9 | OE3 | H3.6 | H4.2 |
| **H4.2** Aplicar SHAP para explicar predicciones individuales | luna | 8 | 12.5 | OE3 | H4.1 | — |
| **H5.4** Mapa de calor por interpolacion IDW | avril | 8 | 12.5 | CG-1 | H5.3 | — |
| **H5.5** Indices NDVI y NDWI renderizados como capa | avril | 5 | 7.8 | CG-3 | H1.6 | — |
| **H6.5** Diagrama de componentes y de secuencia del flujo principal | avril | 3 | 4.7 | Arq | H6.1 | — |
| **H1.10** Estrategia de respaldo definida y restauracion probada | cesar | 5 | 7.8 | BD-4 | H1.9 | — |
| **H12.1** Centralizar los logs de pipeline y aplicacion en control.bitacora_etl | luna | 5 | 4.8 | Troubleshoot | H1.9 | H12.2, H12.4 |
| **H3.4** Entrenar y evaluar Random Forest | alejandro | 6 | 9.4 | OE2 | H3.2 | — |
| **H3.5** Entrenar y evaluar XGBoost | alejandro | 6 | 9.4 | OE2 | H3.2 | H3.6 |
| **H8.2** ETL concurrente con medicion secuencial contra paralelo | alejandro | 5 | 7.8 | SO-1 | H1.1 | — |
| **H10.2** Pruebas automatizadas del backend, cobertura de dominio | luna | 5 | 4.8 | QA | H6.2 | — |
| **H2.2** Analisis espectral de la lluvia e interpretacion fisica | luna | 5 | 7.8 | Senales | H2.1 | — |
| **H2.4** Anomalias respecto a la normal climatologica 1991-2020 | luna | 3 | 2.9 | Senales | H2.1 | H7.4 |
| **H9.1** Preparar SUS, guion de entrevista y dosier de 3 casos | luna | 5 | 4.8 | OE4 | - | H9.2a |
| **H11.5** Publicar el visor como sitio estatico con datos declarados simulados | alejandro | 3 | 4.7 | CICD | H5.4, H6.6 | H9.2a |

## Sprint 4 · semanas 10-11 · 23 historias · 175.7 h

**Foco.** Documento IEEE, validacion externa y cierre  
**Hito.** Segundo avance (semana 10) y feria (semana 12)

| Historia | Responsable | Pts | h | Rubrica | Depende de | Bloquea a |
|---|---|---|---|---|---|---|
| **H10.5c** Redactar el documento IEEE completo | alejandro | 8 | 21.1 | IEEE | H10.5b | H10.6 |
| **H4.4** Contrastar estimaciones contra el catalogo y analizar fallos | alejandro | 10 | 26.4 | OE3 | H4.3, H3.6 | H4.5 |
| **H4.5** Redactar la respuesta a la pregunta de investigacion | alejandro | 2 | 5.3 | OE3 | H4.4 | — |
| **H11.6** Publicar la API y la base en la nube y que el visor sirva dato real | alejandro | 5 | 7.8 | CICD | H11.1, H11.5, H6.2, H3.6, H3.8 | — |
| **H5.9** Rediseno del visor: la primera pantalla no engana y la pagina se puede usar en un telefono | alejandro | 13 | 12.5 | CG-1 | H5.3, H5.7, H5.8, H7.1, H3.4 | — |
| **H10.6** Cartel academico IEEE legible a 1.5 m | avril | 8 | 7.7 | IEEE | H10.5c | — |
| **H10.9** Guion de demo y tres ensayos completos | avril | 4 | 10.6 | CG-6 | H10.3 | — |
| **H12.2** Pantalla de monitoreo de pipelines y entornos dentro del visor | avril | 5 | 4.8 | Troubleshoot | H12.1 | — |
| **H12.5** Historico de incidentes consultable desde la aplicacion | avril | 3 | 2.9 | Troubleshoot | H12.4 | — |
| **H13.2** Manual de operacion del sistema | avril | 5 | 4.8 | Documentacion | H11.4 | — |
| **H7.3** Historial de eventos filtrable y exportable | avril | 3 | 2.9 | CG-2 | H4.3 | — |
| **H7.4** Panel de estadisticas comparado contra la normal historica | avril | 3 | 2.9 | CG-2 | H2.4 | — |
| **H12.3** Alertas automaticas ante fallo de pipeline o despliegue | cesar | 5 | 7.8 | Troubleshoot | H11.2 | — |
| **H2.6** Documentar seleccion de variables y descartar redundantes | cesar | 5 | 7.8 | OE2 | H2.5 | — |
| **H3.7** Versionar modelos con metricas y fecha asociadas | cesar | 3 | 2.9 | Arq | H3.6 | — |
| **H6.3** Strategy y Factory: agregar una fuente sin tocar el orquestador | cesar | 5 | 4.8 | Arq | H6.2 | — |
| **H8.3** Cache en memoria con politica de expiracion y consumo medido | cesar | 5 | 7.8 | SO-1 | H6.1 | — |
| **H8.4** Estrategia de almacenamiento de rasters con proyeccion de crecimiento | cesar | 3 | 2.9 | SO-1 | H1.6 | — |
| **H12.4** Diagnostico guiado a partir de la bitacora de incidencias | luna | 5 | 7.8 | Troubleshoot | H12.1 | H12.5 |
| **H9.2a** Sesion de usabilidad con 3 a 5 participantes y calculo del puntaje SUS | luna | 3 | 7.9 | OE4 | H9.1 | H9.2b |
| **H9.2b** Sesion de contraste: la estimacion frente a lo que la gente vivio | luna | 2 | 5.3 | OE4 | H9.2a, H3.0 | H9.3, H9.4 |
| **H9.3** Someter los umbrales de incendio a criterio de los participantes | luna | 3 | 7.9 | OE4 | H9.2b, H1.2 | — |
| **H9.4** Incorporar un cambio derivado de la retroalimentacion | luna | 2 | 3.1 | OE4 | H9.2b | — |
