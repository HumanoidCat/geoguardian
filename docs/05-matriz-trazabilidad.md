# Matriz de trazabilidad

Liga cada requisito con el modulo que lo implementa, la prueba que lo verifica, la
metrica que lo demuestra y el criterio de rubrica al que responde.

> **Este archivo se genera. No se edita a mano.**
>
>     python docs/herramientas/generar_matriz.py
>
> Sale de `docs/backlog.csv` (dueno y rubrica), de `docs/tareas/<persona>.md` (si
> la historia esta cerrada), de `docs/trazabilidad.csv` (requisito, modulo y
> prueba) y de los archivos que existan en `docs/evidencias/`.
>
> Para cambiar una fila se cambia la fuente, no la tabla. Si aparece un conflicto
> de fusion aqui, se resuelve regenerando:
>
>     git checkout --ours docs/05-matriz-trazabilidad.md
>     python docs/herramientas/generar_matriz.py
>
> `docs/herramientas/verificar_estado.py` comprueba en el CI que la tabla
> corresponda a sus fuentes.

Estados: Pendiente · En progreso · Implementado · Verificado · Con evidencia

| Historia | Requisito | Modulo | Prueba | Evidencia | Rubrica | Dueno | Estado |
|---|---|---|---|---|---|---|---|
| H1.1 | Series climaticas diarias, 10 anios | backend/etl | test_extractor_power | docs/evidencias/bases-de-datos/H1.1-series-climaticas.md | BD-1 | Cesar | **Con evidencia** |
| H1.2 | Historico de focos de calor | backend/etl | test_extractor_firms | docs/evidencias/bases-de-datos/H1.2-focos-calor.md | BD-1 | Cesar | **Con evidencia** |
| H1.3 | Geometrias de distritos en 3FN con SRID validado | basedatos/ddl, backend/etl | basedatos/verificar_h13.py, consultas/verificar_modelo.sql, consultas/verificar_transaccion.sql | docs/evidencias/bases-de-datos/H1.3-ddl-geometrias.md | BD-1, BD-3 | Cesar | **Con evidencia** |
| H1.5 | Reporte de calidad de datos | backend/calidad | test_reporte_calidad | docs/evidencias/objetivos/H1.5-calidad-datos.md | OE1 | Luna | Pendiente |
| H1.8 | Esquemas, roles, minimo privilegio | basedatos/seguridad | test_permisos_rol | docs/evidencias/bases-de-datos/H1.8-roles-minimo-privilegio.md | BD-2 | Cesar | **Con evidencia** |
| H1.9 | Control transaccional con manejo de errores | basedatos/procedimientos | test_rollback | docs/evidencias/bases-de-datos/ | BD-3 | Cesar | Pendiente |
| H1.10 | Estrategia de respaldo probada | basedatos/respaldos | restauracion manual | docs/evidencias/bases-de-datos/ | BD-4 | Cesar | Pendiente |
| H2.1 | Filtrado de ruido con justificacion del filtro. Alcance acotado por D-17: no aplica a precipitacion | backend/senales | test_filtros, 19 casos | docs/evidencias/senales-y-sistemas/H2.1-filtro-ruido.md | Senales | Luna | **Con evidencia** · pendiente reejecutar contra las series reales de H1.1 |
| H2.2 | Analisis espectral de estacionalidad, sobre la serie cruda (D-17) | backend/senales | test_espectro | docs/evidencias/senales-y-sistemas/ | Senales | Luna | Pendiente |
| H2.3 | SPI por ventana movil, sobre la serie cruda (D-17) | backend/senales | test_spi, 21 casos | docs/evidencias/senales-y-sistemas/H2.3-spi.md | Senales | Luna | **Con evidencia** · SC-02 resuelta por D-19 e implementada: spi() recibe el parametro `meses`. Atribuciones cerradas el 2026-08-22 tras leer WMO-No. 1090 completo |
| H2.4 | Anomalias respecto a la normal climatologica 1991-2020, sobre la serie cruda (D-17) | backend/senales | test_anomalias, 24 casos | docs/evidencias/senales-y-sistemas/H2.4-anomalias.md | Senales | Luna | **Con evidencia** · SC-06 pendiente: el contrato no recibe fechas y se supone que la serie arranca en enero |
| H2.7 | Percentiles de lluvia intensa por distrito: R95p/R99p del ETCCDI y percentil de acumulado de 72 h, que no son lo mismo | backend/senales | test_percentiles, 17 casos | docs/evidencias/senales-y-sistemas/H2.7-percentiles.md | Senales | Luna | **Con evidencia** |
| H3.0 | Etiquetado de la variable objetivo | backend/modelado | test_etiquetado | docs/evidencias/ | OE2 | Alejandro | **Con evidencia** |
| H3.1 | Linea base climatologica | backend/modelado | test_linea_base | docs/evidencias/ | OE2 | Alejandro | Pendiente |
| H3.6 | Comparativa de tres algoritmos | backend/modelado | test_comparativa | docs/evidencias/ | OE2 | Alejandro | Pendiente |
| H4.2 | Explicabilidad con SHAP | backend/modelado | test_shap | docs/evidencias/ | OE3 | Alejandro | Pendiente |
| H5.1 | Mapa del canton con poligonos distritales, zoom y desplazamiento | frontend | frontend/herramientas/verificar_escala.py, npm run lint, npm run build, verificacion visual documentada | docs/evidencias/computacion-grafica/H5.1-encuadre-y-seleccion.md<br>docs/evidencias/computacion-grafica/H5.1-mapa-distritos.md<br>docs/evidencias/computacion-grafica/H5.1-sistema-diseno.md | CG-4 | Avril | **Con evidencia** |
| H5.3 | Coropletas de riesgo por evento con rampa de color y leyenda | frontend | frontend/herramientas/exportar_simulados.py, npm run lint, npm run build, verificacion visual documentada | docs/evidencias/computacion-grafica/H5.3-coropletas.md | CG-1 | Avril | **Con evidencia** |
| H5.6 | Transformacion de coordenadas | frontend | test_proyeccion | docs/evidencias/computacion-grafica/ | CG-1 | Avril | Pendiente |
| H6.1 | API REST documentada | backend/api | test_openapi | docs/evidencias/arquitectura-software/H6.1-api-rest-openapi.md | Arq | Cesar | **Con evidencia** |
| H8.1 | Despliegue reproducible | docker-compose.yml, infra/docker/init-db | levantado en maquina limpia | docs/evidencias/sistemas-operativos/H8.1-despliegue.md | SO-1 | Alejandro | **Con evidencia** |
| H8.2 | ETL concurrente medido | backend/etl | test_concurrencia | docs/evidencias/sistemas-operativos/ | SO-1 | Cesar | Pendiente |
| H1.14 | Ingesta periodica con cadencia por evento | backend/etl | test_ingesta_idempotente | docs/evidencias/bases-de-datos/ | BD-1 | Cesar | Pendiente |
| H9.2a | Validacion externa de usabilidad con SUS | docs | acta de sesion | docs/evidencias/objetivos/ | OE4 | Luna | Pendiente |
| H9.2b | Contraste de la estimacion contra eventos vividos | docs | acta de sesion | docs/evidencias/objetivos/ | OE4 | Luna | Pendiente |
| H10.1 | Plan de pruebas con casos por modulo | docs/investigacion | no aplica: es el plan, no la suite | docs/evidencias/calidad/H10.1-plan-pruebas.md | QA | Luna | **Con evidencia** |
| H10.4 | Manual tecnico verificado por alguien ajeno al desarrollo | docs | los comandos de su seccion 5, ejecutados | docs/evidencias/entregables/H10.4-manual-tecnico.md | MVP | Alejandro | En progreso: falta la verificacion externa |
| H13.1 | Actas de las ceremonias Scrum | docs | contraste de cada cifra contra git log y el backlog | docs/evidencias/arquitectura-software/H13.1-ceremonias-scrum.md | Scrum | Alejandro | **Con evidencia** |
| H10.2 | Suite de pruebas del backend | backend/tests | los 39 casos del plan H10.1 | docs/evidencias/calidad/ | QA | Luna | Pendiente |
| H10.5a | 15 referencias IEEE con ficha de contenido | docs/investigacion | verificacion de cada DOI contra la editorial | docs/evidencias/entregables/H10.5a-referencias-ieee.md | IEEE | Luna | **Con evidencia** |
| H10.5b | Estado del arte de Costa Rica | docs/investigacion | verificacion de las fuentes nuevas contra el sitio del editor | docs/evidencias/entregables/H10.5b-estado-del-arte.md | IEEE | Luna | **Con evidencia** |
| H4.3 | Catalogo de 12 o mas eventos historicos con fuente | docs/investigacion, backend/calidad | python -m backend.calidad.validar_catalogo | docs/evidencias/objetivos/H4.3-catalogo-eventos.md | OE3 | Luna | **Con evidencia** |
| H4.4 | Contrastar estimaciones contra el catalogo | backend/modelado | test_contraste_catalogo | docs/evidencias/objetivos/ | OE3 | Alejandro | Pendiente: sin eventos de incendio catalogables, ver H4.3 |
| H6.4 | Seis o mas registros ADR escritos | docs | docs/herramientas/verificar_adr.py, 18 de 18 completos | docs/evidencias/arquitectura-software/H6.4-registros-adr.md | Arq | Alejandro | **Con evidencia** |
| H8.5 | Credenciales por variables de entorno, fuera del repositorio | .env.example, docker-compose.yml | rastreo del historial de git buscando .env | docs/evidencias/sistemas-operativos/H8.5-credenciales-por-entorno.md | SO-1 | Alejandro | **Con evidencia** |
| H8.6 | Manifiestos de Kubernetes corriendo en k3d local | infra/k8s | kubectl apply sobre un cluster k3d recien creado | docs/evidencias/arquitectura-software/H8.6-kubernetes-k3d.md | Arq | Alejandro | **Con evidencia** |
| H10.8 | Carpeta de evidencias organizada por materia con indice | docs/evidencias | docs/herramientas/verificar_cobertura_evidencias.py | docs/evidencias/sistemas-operativos/H10.8-carpeta-evidencias.md | SO-4 | Alejandro | **Con evidencia** |
| H6.6 | El visor consume la API real en lugar de los JSON estaticos | frontend/src/datos/cliente.js, backend/api | verificacion de punta a punta con la API levantada | docs/evidencias/arquitectura-software/H6.6-aviso-de-origen.md<br>docs/evidencias/arquitectura-software/H6.6-visor-contra-api.md | Arq | Alejandro | **Con evidencia** |
| H5.2 | Cuatro o mas capas conmutables con control de opacidad | frontend | npm run lint, npm run build, verificacion visual documentada | docs/evidencias/computacion-grafica/H5.2-capas-conmutables.md | CG-4 | Avril | **Con evidencia** |
| H5.4 | Mapa de calor por interpolacion IDW sobre la probabilidad | frontend | npm run lint, npm run build, verificacion visual documentada | docs/evidencias/computacion-grafica/H5.4-mapa-calor.md | CG-1 | Avril | **Con evidencia** |
| H7.1 | Semaforo de riesgo por distrito y evento con umbrales documentados | frontend | npm run lint, npm run build, verificacion visual documentada | docs/evidencias/computacion-grafica/H7.1-semaforo.md | CG-2 | Avril | **Con evidencia** |
| H11.5 | Publicar el visor como sitio estatico con datos declarados simulados | .github/workflows/ci.yml, frontend/vite.config.js, frontend/src/datos/cliente.js | docs/herramientas/verificar_h115.py, 22 comprobaciones sobre el dist construido | docs/evidencias/arquitectura-software/H11.5-visor-publicado.md | CICD | Alejandro | **Con evidencia** |
| H3.0 | Implementar el etiquetado de los tres eventos y su distribucion de clases | backend/modelado/etiquetado.py, backend/modelado/generar_etiquetas.py | backend/modelado/verificar_h30.py, 24 comprobaciones sin base de datos | docs/evidencias/objetivos/H3.0-etiquetado.md | OE2 | Alejandro | **Con evidencia** |
| H5.7 | Selector de fecha que recarga el estado del mapa | frontend | npm run lint, npm run build, verificacion visual con la API arriba y abajo | docs/evidencias/computacion-grafica/H5.7-selector-fecha.md | CG-4 | Avril | **Con evidencia** |

Completar con el resto del backlog conforme entren al sprint: se agrega la fila a
`docs/trazabilidad.csv` y se regenera.
