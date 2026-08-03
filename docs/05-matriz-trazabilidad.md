# Matriz de trazabilidad

Liga cada requisito con el modulo que lo implementa, la prueba que lo verifica, la
metrica que lo demuestra y el criterio de rubrica al que responde.

Se actualiza cada vez que algo cambia de estado, no solo antes de una entrega.

Estados: Pendiente · En progreso · Implementado · Verificado · Con evidencia

| Historia | Requisito | Modulo | Prueba | Evidencia | Rubrica | Dueno | Estado |
|---|---|---|---|---|---|---|---|
| H1.1 | Series climaticas diarias, 10 anios | backend/etl | test_extractor_power | docs/evidencias/bases-de-datos/ | BD-1 | Cesar | Pendiente |
| H1.2 | Historico de focos de calor | backend/etl | test_extractor_firms | docs/evidencias/bases-de-datos/ | BD-1 | Cesar | Pendiente |
| H1.5 | Reporte de calidad de datos | backend/calidad | test_reporte_calidad | docs/evidencias/bases-de-datos/ | OE1 | Luna | Pendiente |
| H1.8 | Esquemas, roles, minimo privilegio | basedatos/seguridad | test_permisos_rol | docs/evidencias/bases-de-datos/ | BD-2 | Cesar | Pendiente |
| H1.9 | Control transaccional con manejo de errores | basedatos/procedimientos | test_rollback | docs/evidencias/bases-de-datos/ | BD-3 | Cesar | Pendiente |
| H1.10 | Estrategia de respaldo probada | basedatos/respaldos | restauracion manual | docs/evidencias/bases-de-datos/ | BD-4 | Cesar | Pendiente |
| H2.2 | Analisis espectral de estacionalidad | backend/senales | test_espectro | docs/evidencias/senales-y-sistemas/ | Senales | Alejandro | Pendiente |
| H2.3 | SPI por ventana movil | backend/senales | test_spi | docs/evidencias/senales-y-sistemas/ | Senales | Alejandro | Pendiente |
| H3.0 | Etiquetado de la variable objetivo | backend/modelado | test_etiquetado | docs/evidencias/ | OE2 | Alejandro | Pendiente |
| H3.1 | Linea base climatologica | backend/modelado | test_linea_base | docs/evidencias/ | OE2 | Alejandro | Pendiente |
| H3.6 | Comparativa de tres algoritmos | backend/modelado | test_comparativa | docs/evidencias/ | OE2 | Alejandro | Pendiente |
| H4.2 | Explicabilidad con SHAP | backend/modelado | test_shap | docs/evidencias/ | OE3 | Alejandro | Pendiente |
| H5.3 | Coropletas de riesgo por distrito | frontend | prueba visual | docs/evidencias/computacion-grafica/ | CG-1 | Avril | Pendiente |
| H5.6 | Transformacion de coordenadas | frontend | test_proyeccion | docs/evidencias/computacion-grafica/ | CG-1 | Avril | Pendiente |
| H6.1 | API REST documentada | backend/api | test_openapi | docs/evidencias/arquitectura-software/ | Arq | Cesar | Pendiente |
| H8.1 | Despliegue reproducible | docker-compose.yml, infra/docker/init-db | levantado en maquina limpia | docs/evidencias/sistemas-operativos/H8.1-despliegue.md | SO-1 | Alejandro | **Con evidencia** |
| H8.2 | ETL concurrente medido | backend/etl | test_concurrencia | docs/evidencias/sistemas-operativos/ | SO-1 | Alejandro | Pendiente |
| H9.2 | Validacion externa con SUS | docs | acta de sesion | docs/evidencias/ | OE4 | Luna | Pendiente |

Completar con el resto del backlog conforme entren al sprint.
