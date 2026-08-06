# Referencias con ficha de contenido

**Historia:** H10.5a · **Responsable:** Luna · **Rúbrica:** IEEE
**Depende de:** ninguna · **Bloquea a:** H10.5b (estado del arte de Costa Rica)

Este documento amplía las referencias del documento IEEE. Las ocho primeras
(`[1]`–`[8]`) ya están citadas en `Propuesta_IEEE_GeoGuardian.docx`; se listan
aquí solo por número, sin ficha nueva, para que la numeración sea continua.
Las referencias `[9]`–`[16]` son el insumo nuevo de esta historia: ocho
referencias adicionales, cada una verificada contra la fuente primaria antes
de incluirla (DOI o URL de editorial, no de agregadores). Ninguna se cita sin
haber confirmado que existe y que dice lo que aquí se afirma.

## Referencias ya citadas en el documento (sin cambio)

```
[1] NASA Langley Research Center, "POWER Data Access Viewer and API
    Documentation," Prediction of Worldwide Energy Resources Project.
[2] NASA LANCE, "Fire Information for Resource Management System (FIRMS):
    API and Archive Download," NASA Earthdata.
[3] European Space Agency, "Copernicus Data Space Ecosystem: Sentinel-2
    Data Access," 2023.
[4] T. B. McKee, N. J. Doesken y J. Kleist, "The relationship of drought
    frequency and duration to time scales," in Proc. 8th Conf. Applied
    Climatology, Anaheim, CA, EE. UU., 1993, pp. 179-184.
[5] T. Chen y C. Guestrin, "XGBoost: A scalable tree boosting system," in
    Proc. 22nd ACM SIGKDD Int. Conf. Knowledge Discovery and Data Mining,
    San Francisco, CA, EE. UU., 2016, pp. 785-794.
[6] World Meteorological Organization, WMO Guidelines on the Calculation
    of Climate Normals, WMO-No. 1203. Ginebra, Suiza: WMO, 2017.
[7] J. Brooke, "SUS: A quick and dirty usability scale," in Usability
    Evaluation in Industry, P. W. Jordan et al., Eds. Londres, Reino
    Unido: Taylor & Francis, 1996, pp. 189-194.
[8] Sistema Nacional de Información Territorial, "Servicios OGC del
    Instituto Meteorológico Nacional," SNIT, Costa Rica.
```

## Referencias nuevas de esta historia

### [9] Breiman — Random Forests

```
[9] L. Breiman, "Random forests," Machine Learning, vol. 45, no. 1,
    pp. 5-32, 2001.
```

**Fuente verificada:** Springer, *Machine Learning*, DOI de la revista
(`10.1023/A:1010933404324`).

**Ficha de contenido**
- *Qué dice:* define el algoritmo de Random Forest como un conjunto de
  árboles de decisión entrenados sobre muestras bootstrap con submuestreo
  aleatorio de variables en cada nodo, y demuestra que el error de
  generalización converge cuando crece el número de árboles, en función de
  la fuerza de los árboles individuales y su correlación mutua.
- *Por qué es relevante:* es la referencia original del algoritmo que el
  proyecto declara en la sección V-A del documento como "ensamble por
  agregación robusto ante ruido y con pocos hiperparámetros".
- *Uso previsto:* cita de respaldo al elegir Random Forest como uno de los
  tres algoritmos comparados (OE2).

### [10] Lundberg y Lee — SHAP

```
[10] S. M. Lundberg y S.-I. Lee, "A unified approach to interpreting
     model predictions," in Proc. 31st Int. Conf. Neural Information
     Processing Systems (NeurIPS), Long Beach, CA, EE. UU., 2017,
     pp. 4766-4777.
```

**Fuente verificada:** proceedings oficiales de NeurIPS 2017
(`proceedings.neurips.cc`).

**Ficha de contenido**
- *Qué dice:* presenta SHAP (SHapley Additive exPlanations), un marco que
  unifica seis métodos previos de explicabilidad bajo una única familia de
  medidas aditivas de importancia de variables, con base en los valores de
  Shapley de teoría de juegos, y demuestra que esa familia tiene una
  solución única con un conjunto de propiedades deseables.
- *Por qué es relevante:* es la referencia original de la técnica que el
  proyecto usa para explicabilidad (OE3) y que el contrato
  `Estimador.explicar` de `contratos/modelado.py` implementa.
- *Uso previsto:* cita de respaldo en la sección de metodología al
  describir el análisis SHAP.

### [11] Bergmeir y Benítez — validación de series temporales

```
[11] C. Bergmeir y J. M. Benítez, "On the use of cross-validation for
     time series predictor evaluation," Information Sciences, vol. 191,
     pp. 192-213, 2012.
```

**Fuente verificada:** ScienceDirect / Information Sciences,
DOI `10.1016/j.ins.2011.12.028`.

**Ficha de contenido**
- *Qué dice:* muestra que la validación cruzada aleatoria estándar
  (k-fold) produce estimaciones de error sesgadas cuando hay dependencia
  temporal entre observaciones, porque permite que el modelo se entrene
  con datos posteriores a los que usa para evaluar.
- *Por qué es relevante:* es el fundamento metodológico de por qué el
  contrato `Evaluador.validar_ventana_expansiva` prohíbe explícitamente la
  partición aleatoria y exige ventana expansiva (entrenar con el pasado,
  probar con el futuro).
- *Uso previsto:* cita de respaldo en la sección de diseño metodológico
  (V) al justificar la validación temporal estricta.

### [12] Sokolova y Lapalme — métricas de clasificación

```
[12] M. Sokolova y G. Lapalme, "A systematic analysis of performance
     measures for classification tasks," Information Processing &
     Management, vol. 45, no. 4, pp. 427-437, 2009.
```

**Fuente verificada:** ScienceDirect / Information Processing &
Management, DOI `10.1016/j.ipm.2009.03.002`.

**Ficha de contenido**
- *Qué dice:* analiza sistemáticamente veinticuatro métricas de desempeño
  para clasificación binaria, multiclase, multietiqueta y jerárquica, y
  muestra que los promedios macro dan el mismo peso a cada clase sin
  importar su frecuencia, a diferencia de los promedios micro.
- *Por qué es relevante:* fundamenta por qué el documento fija F1-macro
  como métrica principal (sección V-C) ante el fuerte desbalance de clases
  que se anticipa entre los niveles bajo/medio/alto de riesgo.
- *Uso previsto:* cita de respaldo al justificar la elección de la métrica
  de contraste de H1.

### [13] Bangor, Kortum y Miller — interpretación del puntaje SUS

```
[13] A. Bangor, P. Kortum y J. Miller, "The System Usability Scale: An
     empirical evaluation," International Journal of Human-Computer
     Interaction, vol. 24, no. 6, pp. 574-594, 2008.
```

**Fuente verificada:** Taylor & Francis / International Journal of
Human-Computer Interaction, DOI `10.1080/10447310802205776`.

**Ficha de contenido**
- *Qué dice:* reporta casi diez años de datos SUS recolectados sobre
  cientos de productos en distintas fases de desarrollo, y propone bandas
  de interpretación del puntaje (por ejemplo, "aceptable" frente a
  "marginal" o "no aceptable").
- *Por qué es relevante:* complementa a Brooke `[7]`, que define la
  escala SUS pero no cómo interpretar el puntaje resultante. Esta
  referencia es la que se necesita para poder decir algo sobre los
  resultados de la validación externa (V-D), no solo calcularlos.
- *Uso previsto:* cita de respaldo al reportar e interpretar el puntaje
  SUS obtenido en H9.2.

### [14] Giglio, Schroeder y Justice — algoritmo de detección de focos de calor

```
[14] L. Giglio, W. Schroeder y C. O. Justice, "The collection 6 MODIS
     active fire detection algorithm and fire products," Remote Sensing
     of Environment, vol. 178, pp. 31-41, 2016.
```

**Fuente verificada:** ScienceDirect / Remote Sensing of Environment,
DOI `10.1016/j.rse.2016.02.054`.

**Ficha de contenido**
- *Qué dice:* describe el algoritmo contextual de la Colección 6 de MODIS
  para detectar focos de calor por anomalía térmica, comparando la
  temperatura de un píxel candidato con la de su entorno, y documenta sus
  limitaciones: cobertura de nubes, tamaño mínimo detectable del incendio
  y resolución espacial.
- *Por qué es relevante:* NASA FIRMS `[2]`, la fuente de focos de calor
  del proyecto, distribuye datos derivados de este tipo de algoritmo
  (MODIS y VIIRS). Conocer sus limitaciones es necesario para interpretar
  correctamente los focos que alimentan el etiquetado de riesgo de
  incendio.
- *Uso previsto:* cita de respaldo al describir las limitaciones de la
  fuente de datos de incendio, y en la discusión de limitaciones del
  proyecto (el riesgo R16 mencionado en `contratos/enums.py` sobre si hay
  suficientes focos históricos para entrenar).

### [15] Quesada-Hernández, Hidalgo y Alfaro — índices de sequía en Guanacaste

```
[15] L. E. Quesada-Hernández, H. G. Hidalgo y E. J. Alfaro, "Asociación
     entre algunos índices de sequía e impactos socio-productivos en el
     Pacífico Norte de Costa Rica," Revista de Ciencias Ambientales,
     vol. 54, no. 1, pp. 16-32, 2020.
```

**Fuente verificada:** Revista de Ciencias Ambientales (Universidad
Nacional, Costa Rica), DOI `10.15359/rca.54-1.2`.

**Ficha de contenido**
- *Qué dice:* construye una base de impactos de sequía (1970-1999) para
  tres cantones de Guanacaste a partir de Desinventar, EM-DAT y el IMN, y
  compara seis índices de sequía (incluido el SPI a 6 y 12 meses) mediante
  regresión logística. Encuentra que el SPI es el índice con la asociación
  más fuerte con los impactos sociales y productivos registrados.
- *Por qué es relevante:* es evidencia empírica, en la misma región
  (Guanacaste, provincia a la que pertenece Tilarán) de que el SPI —el
  índice que el documento usa para el umbral de sequía en la Tabla 1— es
  pertinente para esta zona del país, y no solo un estándar internacional
  adoptado sin verificación local.
- *Uso previsto:* cita de respaldo en la introducción y en el estado del
  arte de Costa Rica (H10.5b), y como antecedente directo para la validez
  de la Tabla 1 del documento.

### [16] Vega Araya — ENOS y precipitación en el Área de Conservación Guanacaste

```
[16] M. Vega Araya, "El fenomeno ENOS y el analisis de la variabilidad de
     las series de tiempo de precipitacion en el Area de Conservacion
     Guanacaste, Costa Rica," Revista Geografica de America Central,
     no. 72, pp. 491-513, 2024.
```

**Fuente verificada:** SciELO Costa Rica / Revista Geográfica de América
Central, DOI `10.15359/rgac.72-1.18`.

**Ficha de contenido**
- *Qué dice:* analiza series de tiempo de precipitación del producto
  CHIRPS en cinco ecorregiones del Área de Conservación Guanacaste y su
  relación con el fenómeno El Niño-Oscilación del Sur (ENOS).
- *Por qué es relevante:* aporta contexto reciente (2024) sobre la
  variabilidad climática interanual de la región donde está Tilarán,
  relevante para explicar por qué un solo horizonte de siete días puede no
  capturar toda la variabilidad relevante, y para la sección de
  limitaciones.
- *Uso previsto:* cita de respaldo en la discusión de limitaciones y en el
  estado del arte de Costa Rica (H10.5b).

## Pendiente

Se buscaron además dos revisiones de aprendizaje automático aplicado a
predicción de incendio y de sequía (ScienceDirect), pero no fue posible
verificar su contenido completo por una restricción de acceso al fetch. No
se incluyen como referencia hasta poder confirmarlas contra la fuente
primaria. Quedan como candidatas para una futura ronda si el estado del
arte (H10.5b) las necesita.
