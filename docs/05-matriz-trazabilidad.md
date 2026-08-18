# Matriz de trazabilidad

Liga cada requisito con el modulo que lo implementa, la prueba que lo verifica, la
metrica que lo demuestra y el criterio de rubrica al que responde.

Se actualiza cada vez que algo cambia de estado, no solo antes de una entrega.

Estados: Pendiente · En progreso · Implementado · Verificado · Con evidencia

| Historia | Requisito | Modulo | Prueba | Evidencia | Rubrica | Dueno | Estado |
|---|---|---|---|---|---|---|---|
| H1.1 | Series climaticas diarias, 10 anios | backend/etl | test_extractor_power | docs/evidencias/bases-de-datos/ | BD-1 | Cesar | Pendiente |
| H1.2 | Historico de focos de calor | backend/etl | test_extractor_firms | docs/evidencias/bases-de-datos/ | BD-1 | Cesar | Pendiente |
| H1.3 | Geometrias de distritos en 3FN con SRID validado | basedatos/ddl, backend/etl | basedatos/verificar_h13.py, consultas/verificar_modelo.sql, consultas/verificar_transaccion.sql | docs/evidencias/bases-de-datos/H1.3-ddl-geometrias.md | BD-1, BD-3 | Cesar | **Con evidencia** |
| H1.5 | Reporte de calidad de datos | backend/calidad | test_reporte_calidad | docs/evidencias/objetivos/ | OE1 | Luna | Pendiente |
| H1.8 | Esquemas, roles, minimo privilegio | basedatos/seguridad | test_permisos_rol | docs/evidencias/bases-de-datos/ | BD-2 | Cesar | Pendiente |
| H1.9 | Control transaccional con manejo de errores | basedatos/procedimientos | test_rollback | docs/evidencias/bases-de-datos/ | BD-3 | Cesar | Pendiente |
| H1.10 | Estrategia de respaldo probada | basedatos/respaldos | restauracion manual | docs/evidencias/bases-de-datos/ | BD-4 | Cesar | Pendiente |
| H2.1 | Filtrado de ruido con justificacion del filtro | backend/senales | test_filtros, 19 casos | docs/evidencias/senales-y-sistemas/H2.1-filtro-ruido.md | Senales | Luna | **Con evidencia** |
| H2.2 | Analisis espectral de estacionalidad | backend/senales | test_espectro | docs/evidencias/senales-y-sistemas/ | Senales | Alejandro | Pendiente |
| H2.3 | SPI por ventana movil | backend/senales | test_spi, 21 casos | docs/evidencias/senales-y-sistemas/H2.3-spi.md | Senales | Luna | **Con evidencia**, con la salvedad de SC-02: el ajuste no es por mes calendario |
| H3.0 | Etiquetado de la variable objetivo | backend/modelado | test_etiquetado | docs/evidencias/ | OE2 | Alejandro | Pendiente |
| H3.1 | Linea base climatologica | backend/modelado | test_linea_base | docs/evidencias/ | OE2 | Alejandro | Pendiente |
| H3.6 | Comparativa de tres algoritmos | backend/modelado | test_comparativa | docs/evidencias/ | OE2 | Alejandro | Pendiente |
| H4.2 | Explicabilidad con SHAP | backend/modelado | test_shap | docs/evidencias/ | OE3 | Alejandro | Pendiente |
| H5.1 | Mapa del canton con poligonos distritales, zoom y desplazamiento | frontend | frontend/herramientas/verificar_escala.py, npm run lint, npm run build, verificacion visual documentada | docs/evidencias/computacion-grafica/H5.1-mapa-distritos.md | CG-4 | Avril | **Con evidencia** |
| H5.3 | Coropletas de riesgo por evento con rampa de color y leyenda | frontend | frontend/herramientas/exportar_simulados.py, npm run lint, npm run build, verificacion visual documentada | docs/evidencias/computacion-grafica/H5.3-coropletas.md | CG-1 | Avril | **Con evidencia** |
| H5.6 | Transformacion de coordenadas | frontend | test_proyeccion | docs/evidencias/computacion-grafica/ | CG-1 | Avril | Pendiente |
| H6.1 | API REST documentada | backend/api | test_openapi | docs/evidencias/arquitectura-software/ | Arq | Cesar | Pendiente |
| H8.1 | Despliegue reproducible | docker-compose.yml, infra/docker/init-db | levantado en maquina limpia | docs/evidencias/sistemas-operativos/H8.1-despliegue.md | SO-1 | Alejandro | **Con evidencia** |
| H8.2 | ETL concurrente medido | backend/etl | test_concurrencia | docs/evidencias/sistemas-operativos/ | SO-1 | Alejandro | Pendiente |
| H9.2 | Validacion externa con SUS | docs | acta de sesion | docs/evidencias/objetivos/ | OE4 | Luna | Pendiente |
| H10.1 | Plan de pruebas con casos por modulo | docs/investigacion | no aplica: es el plan, no la suite | docs/evidencias/calidad/H10.1-plan-pruebas.md | QA | Luna | **Con evidencia** |
| H10.4 | Manual tecnico verificado por alguien ajeno al desarrollo | docs | los comandos de su seccion 5, ejecutados | docs/evidencias/entregables/H10.4-manual-tecnico.md | MVP | Alejandro | En progreso: falta la verificacion externa |
| H13.1 | Actas de las ceremonias Scrum | docs | contraste de cada cifra contra git log y el backlog | docs/evidencias/arquitectura-software/H13.1-ceremonias-scrum.md | Scrum | Alejandro | **Con evidencia** |
| H10.2 | Suite de pruebas del backend | backend/tests | los 39 casos del plan H10.1 | docs/evidencias/calidad/ | QA | Luna | Pendiente |
| H10.5a | 15 referencias IEEE con ficha de contenido | docs/investigacion | verificacion de cada DOI contra la editorial | docs/evidencias/entregables/H10.5a-referencias-ieee.md | IEEE | Luna | **Con evidencia** |
| H10.5b | Estado del arte de Costa Rica | docs/investigacion | verificacion de las fuentes nuevas contra el sitio del editor | docs/evidencias/entregables/H10.5b-estado-del-arte.md | IEEE | Luna | **Con evidencia** |
| H4.3 | Catalogo de 12 o mas eventos historicos con fuente | docs/investigacion, backend/calidad | python -m backend.calidad.validar_catalogo | docs/evidencias/objetivos/H4.3-catalogo-eventos.md | OE3 | Luna | **Con evidencia** |
| H4.4 | Contrastar estimaciones contra el catalogo | backend/modelado | test_contraste_catalogo | docs/evidencias/objetivos/ | OE3 | Alejandro | Pendiente: sin eventos de incendio catalogables, ver H4.3 |

Completar con el resto del backlog conforme entren al sprint.
