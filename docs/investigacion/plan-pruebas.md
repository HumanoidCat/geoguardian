# Plan de pruebas

**Historia:** H10.1 · **Responsable:** Luna · **Rúbrica:** QA
**Depende de:** contratos v1.2.0
**Estado del documento:** en redacción, sin pruebas implementadas todavía

Este documento planifica los casos de prueba que debe cubrir la suite de
`backend/tests/`. Es un plan, no una implementación: ningún caso listado aquí
se declara ejecutado hasta que exista el archivo `test_*.py` correspondiente y
se corra con `pytest`. La historia que implementa la suite es H10.2 (Sprint 3),
que a su vez depende de que exista `backend/api` (H6.2).

## 1. Objetivo y alcance

Cubrir, para cada contrato congelado en `contratos/*.py`, los casos de prueba
necesarios para verificar que una implementación (simulada o real) cumple lo
que el contrato promete, con énfasis en tres cosas que el proyecto declara
como no negociables:

1. Un dato faltante se representa como `None`, nunca como `0` ni como un valor
   plausible.
2. Una estimación sin modelo entrenado detrás es `None`, nunca un valor por
   defecto.
3. La validación temporal no debe permitir que información del futuro se
   filtre al entrenamiento.

Módulos cubiertos por este plan: `contratos/repositorio.py`,
`contratos/fuentes.py`, `contratos/senales.py`, `contratos/modelado.py`,
`contratos/esquemas.py`, y `backend/calidad` (módulo propio de Luna,
historia H1.5).

Fuera de alcance de este documento: pruebas de interfaz (`frontend`, dueño
Avril), pruebas de seguridad de base de datos y procedimientos almacenados
(`basedatos`, dueño César) — esas quedan en sus propios planes, aunque los
casos de este documento las referencian donde hay dependencia funcional.

## 2. Estrategia

- Toda prueba se escribe contra `contratos/simulados/` mientras el módulo real
  no exista. Los simulados (`RepositorioSimulado`, `ExtractorClimaSimulado`,
  `ExtractorFocosSimulado`) ya están congelados en v1.1.0 y son deterministas
  (semilla fija `SEMILLA = 20260803`), así que las pruebas contra ellos son
  reproducibles.
- Convención de archivos: `backend/tests/test_<modulo>.py`, funciones
  `test_<caso>`, según `pyproject.toml` (`testpaths = ["backend/tests"]`,
  `python_files = ["test_*.py"]`).
- Este plan no reemplaza `python -m contratos.verificar`: ese script es un
  chequeo rápido de que los simulados cumplen los protocolos, ya lo ejecuta el
  CI como trabajo separado. La suite de `backend/tests/` va más profundo: casos
  de borde, casos de error y, cuando el módulo real esté disponible, contraste
  contra datos reales.
- Cuando un módulo real reemplace a su simulado, las mismas funciones de
  prueba deben poder correr contra ambos (parametrizando el fixture), para
  detectar si la implementación real se desvía del contrato.
- Prioridad 1: casos que verifican la regla de no inventar datos y la validez
  de la comparación contra la línea base, por ser el núcleo de la pregunta de
  investigación. Prioridad 2: casos de error explícito. Prioridad 3: casos
  felices sin ambigüedad de contrato.

## 3. Casos de prueba por contrato

**Significado de la prioridad.** Prioridad 1: el caso protege una invariante
declarada en la sección 1 (representación de faltantes, ausencia de valores
por defecto, ausencia de fuga temporal); si falla, hay un resultado inválido
que nadie detecta hasta el análisis final. Prioridad 2: el caso verifica un
error o un borde declarado explícitamente en el contrato; si falla, el módulo
se comporta distinto de lo prometido. Prioridad 3: el caso verifica
comportamiento nominal sin ambigüedad de contrato; si falla, se detecta
rápido por otras vías. Se implementan en ese orden.

### 3.1 `Repositorio` (contratos/repositorio.py — dueño César, simulado: `RepositorioSimulado`)

| Caso | Tipo | Verifica | Prioridad |
|---|---|---|---|
| `test_listar_distritos_devuelve_ocho` | Feliz | El vocabulario territorial está cerrado a los ocho distritos de Tilarán | 3 |
| `test_codigos_distrito_son_los_oficiales_de_tilaran` | Funcional | Los ocho códigos son 50801 a 50808, sin repetidos: Tilarán es el cantón 08 de Guanacaste. Un código con forma válida pero de otro cantón (50501–50508, Carrillo) es un dato falso que ninguna validación de tipo detecta. Ver incidencia I-04 | 1 |
| `test_obtener_distrito_codigo_inexistente_devuelve_none` | Borde | No lanza excepción ante código inexistente | 2 |
| `test_guardar_mediciones_es_idempotente` | Funcional | Guardar dos veces el mismo lote no duplica filas | 1 |
| `test_guardar_mediciones_revierte_en_fallo_parcial` | Error | Un fallo a mitad de la escritura no deja carga parcial | 1 |
| `test_obtener_mediciones_incluye_dias_sin_dato` | Funcional | Devuelve una fila por día del rango, con campos en `None` en los huecos | 1 |
| `test_guardar_focos_asigna_distrito_por_interseccion` | Feliz | La asignación espacial ocurre en el repositorio, no en el extractor | 2 |
| `test_contar_focos_ventana_sin_focos_devuelve_cero` | Borde | Ventana sin focos no lanza error ni devuelve `None` | 2 |
| `test_obtener_riesgo_sin_estimacion_devuelve_none` | Borde | No se inventa un riesgo cuando no hay estimación calculada | 1 |
| `test_obtener_riesgos_por_fecha_todos_los_distritos` | Feliz | Alimenta la coropleta con un riesgo por distrito | 3 |
| `test_listar_metricas_sin_modelos_entrenados_devuelve_vacio` | Borde | No hay métricas inventadas antes de entrenar | 1 |

### 3.2 `ExtractorClima` y `ExtractorFocosCalor` (contratos/fuentes.py — dueño César, simulados: `ExtractorClimaSimulado`, `ExtractorFocosSimulado`)

| Caso | Tipo | Verifica | Prioridad |
|---|---|---|---|
| `test_extractor_clima_disponible_antes_de_extraer` | Feliz | Se puede verificar conectividad sin descargar datos | 2 |
| `test_extractor_clima_extraer_es_idempotente` | Funcional | Dos llamadas con los mismos argumentos producen el mismo resultado | 1 |
| `test_extractor_clima_no_omite_dias_sin_dato` | Funcional | Un día sin dato se devuelve con campos en `None`, no se omite la fecha | 1 |
| `test_extractor_focos_extrae_dentro_del_rango` | Feliz | Los focos devueltos caen dentro de `desde`/`hasta` | 3 |
| `test_extractor_focos_no_asigna_distrito` | Diseño | El extractor no hace análisis espacial; `codigo_distrito` sale en `None` | 2 |

### 3.3 `ProcesadorSenales` (contratos/senales.py — dueño Alejandro, simulado: pendiente)

| Caso | Tipo | Verifica | Prioridad |
|---|---|---|---|
| `test_filtrar_ruido_preserva_huecos` | Funcional | Una posición `None` en la entrada sale `None` en la salida | 1 |
| `test_espectro_lanza_valueerror_con_huecos` | Error | Rechaza series con huecos e indica cuántos faltan | 1 |
| `test_espectro_identifica_ciclo_anual` | Funcional | La magnitud dominante corresponde al periodo anual esperado de la precipitación | 2 |
| `test_spi_primeras_posiciones_none` | Funcional | Las primeras `ventana_meses` posiciones son `None`, no se rellenan con ceros | 1 |
| `test_anomalia_mes_faltante_en_normal_devuelve_none` | Borde | Si falta el mes en `normal_por_mes`, la posición sale `None` | 2 |
| `test_remuestrear_mayoria_faltante_devuelve_none` | Funcional | Una ventana con más de la mitad de valores faltantes no promedia con los pocos datos presentes | 1 |

### 3.4 `Estimador` y `Evaluador` (contratos/modelado.py — dueño Alejandro, simulado: pendiente)

| Caso | Tipo | Verifica | Prioridad |
|---|---|---|---|
| `test_estimador_entrenado_false_antes_de_entrenar` | Feliz | El estado inicial es explícito | 3 |
| `test_predecir_sin_entrenar_lanza_runtimeerror` | Error | No hay predicción por defecto de un estimador sin entrenar | 1 |
| `test_linea_base_ignora_caracteristicas` | Funcional | La línea base climatológica usa solo distrito y mes calendario, no las variables del modelo | 1 |
| `test_linea_base_explicar_devuelve_none` | Borde | La línea base no soporta SHAP; devuelve `None` explícito, no lanza excepción | 2 |
| `test_validar_ventana_expansiva_respeta_orden_temporal` | Funcional | En cada corte, la fecha máxima del pliegue de entrenamiento es anterior a la fecha mínima de su pliegue de prueba. Ninguna observación de entrenamiento es posterior al inicio de la prueba | 1 |
| `test_validar_ventana_expansiva_la_ventana_se_expande_no_se_desliza` | Funcional | Cada pliegue de entrenamiento contiene íntegramente al pliegue anterior. Una ventana deslizante descartaría historia que sí estaba disponible en operación | 1 |
| `test_validar_ventana_expansiva_rechaza_particion_aleatoria` | Error | Una partición construida al azar sobre las mismas fechas es rechazada explícitamente, no aceptada en silencio | 1 |
| `test_validar_ventana_expansiva_n_cortes_produce_n_evaluaciones` | Funcional | El número de particiones evaluadas coincide con `n_cortes`; ningún corte se omite por quedar sin datos suficientes sin que se reporte | 2 |
| `test_comparar_con_linea_base_devuelve_supera_y_valor_p` | Feliz | El contraste de H1 produce ambos valores | 2 |
| `test_comparar_con_linea_base_resultado_negativo_no_lanza_error` | Funcional | Un modelo que no supera la línea base es un resultado válido, no una excepción ni un caso descartado | 1 |

### 3.5 `esquemas.py` — validación de datos (dueño César, sin Protocol, validación Pydantic)

| Caso | Tipo | Verifica | Prioridad |
|---|---|---|---|
| `test_medicion_precipitacion_negativa_rechazada` | Error | `precipitacion_mm` no admite valores negativos (`ge=0`) | 2 |
| `test_riesgo_probabilidad_fuera_de_rango_rechazada` | Error | `probabilidad` se restringe a `[0, 1]` | 2 |
| `test_serie_temporal_conserva_huecos_como_none` | Funcional | `SerieTemporal.puntos` no omite fechas con `valor` en `None` | 1 |
| `test_foco_calor_confianza_fuera_de_rango_rechazada` | Error | `confianza` se restringe a `[0, 100]` | 3 |

### 3.6 `backend/calidad` (módulo propio de Luna — sin contrato Protocol, historia H1.5)

| Caso | Tipo | Verifica | Prioridad |
|---|---|---|---|
| `test_reporte_calidad_pct_faltantes_se_calcula_no_se_declara` | Funcional | El porcentaje de faltantes se obtiene ejecutando sobre una serie conocida, no se asigna a mano | 1 |
| `test_reporte_calidad_detecta_atipicos` | Funcional | Un valor fuera de rango físico razonable se marca, no se descarta en silencio | 1 |
| `test_reporte_calidad_registra_metodo_imputacion` | Funcional | Toda imputación queda con su `MetodoImputacion` distinto de `SIN_IMPUTAR` | 2 |

## 4. Referencia cruzada con la matriz de trazabilidad

`docs/05-matriz-trazabilidad.md` ya anticipa nombres de prueba para historias
de otros dueños (`test_extractor_power`, `test_espectro`, `test_spi`,
`test_linea_base`, `test_comparativa`, `test_shap`, `test_openapi`,
`test_concurrencia`, `test_permisos_rol`, `test_rollback`, `test_proyeccion`).
Este plan los conserva y añade los casos de borde y error que la matriz no
detalla. Cuando se implemente cada prueba, su fila en la matriz pasa de
"Pendiente" a "Implementado" y luego a "Verificado" cuando corre en CI, y a
"Con evidencia" cuando la evidencia queda archivada en la carpeta que
corresponda según `docs/evidencias/README.md`. Para las historias de rúbrica
QA de este plan (H10.1, H10.2) esa carpeta es `docs/evidencias/calidad/`.

## 5. Estado de implementación

Ningún caso de este plan está implementado todavía. Esta tabla se actualiza a
medida que se agregan archivos a `backend/tests/`.

| Sección | Casos planificados | Casos implementados |
|---|---|---|
| Repositorio | 11 | 0 |
| Extractores | 5 | 0 |
| Procesador de señales | 6 | 0 |
| Estimador y evaluador | 10 | 0 |
| Esquemas | 4 | 0 |
| Calidad | 3 | 0 |
| **Total** | **39** | **0** |
