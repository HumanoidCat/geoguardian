# Referencias con ficha de contenido

**Historia:** H10.5a · **Responsable:** Luna · **Rúbrica:** IEEE
**Depende de:** ninguna · **Bloquea a:** H10.5b (estado del arte de Costa Rica)

Este documento amplía las referencias del documento IEEE. Las ocho primeras
(`[1]`–`[8]`) ya están citadas en `Propuesta_IEEE_GeoGuardian.docx`; se listan
aquí solo por número, sin ficha nueva, para que la numeración sea continua.
Las referencias `[9]`–`[24]` son el insumo nuevo de esta historia: dieciséis
fichas de contenido, una por referencia, cada una verificada contra la fuente
primaria antes de incluirla (DOI o URL de editorial, no de agregadores).
Ninguna se cita sin haber confirmado que existe y que dice lo que aquí se
afirma.

La historia pide un mínimo de 15 referencias con ficha. Este documento aporta
16 fichas nuevas, sin contar las ocho previas que se listan solo por número.

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

**Fuente verificada:** Springer, *Machine Learning*. DOI del artículo:
`10.1023/A:1010933404324`.

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
     Processing Systems (NeurIPS), Long Beach, CA, EE. UU., 2017.
```

**Fuente verificada:** proceedings oficiales de NeurIPS 2017
(`proceedings.neurips.cc`). **Cita sin paginación a propósito:** los
proceedings oficiales de NeurIPS no publican números de página, y las
paginaciones que circulan en agregadores no coinciden entre sí (se
encontraron `4766-4777` y `4768-4777` en fuentes distintas). Como no se pudo
confirmar cuál es correcta contra el documento oficial, se omite el rango en
lugar de elegir uno. IEEE admite la referencia de actas sin paginación.

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
[16] M. Vega Araya, "El fenómeno ENOS y el análisis de la variabilidad de
     las series de tiempo de precipitación en el Área de Conservación
     Guanacaste, Costa Rica," Revista Geográfica de América Central,
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

### [17] Hosmer, Lemeshow y Sturdivant — Regresión Logística

```
[17] D. W. Hosmer, S. Lemeshow y R. X. Sturdivant, Applied Logistic
     Regression, 3rd ed. Hoboken, NJ, EE. UU.: John Wiley & Sons, 2013.
```

**Fuente verificada:** Wiley Online Library, Wiley Series in Probability
and Statistics. DOI del libro: `10.1002/9781118548387`.

**Ficha de contenido**
- *Qué dice:* es el texto de referencia sobre regresión logística: ajuste
  por máxima verosimilitud, interpretación de coeficientes como razones de
  momios, selección de variables, diagnóstico del modelo y evaluación de su
  bondad de ajuste. Cubre también la extensión multinomial y ordinal, que es
  la forma que toma el problema en este proyecto.
- *Por qué es relevante:* el documento declara tres algoritmos comparados,
  pero solo dos tenían referencia: Random Forest en `[9]` y XGBoost en
  `[5]`. Regresión Logística, que es precisamente la que el documento usa
  como "referencia lineal interpretable", no tenía ninguna. Esta ficha cierra
  ese hueco.
- *Uso previsto:* cita de respaldo en la sección V-A al describir el primero
  de los tres algoritmos (OE2), y en la interpretación de sus coeficientes
  frente al análisis SHAP de los modelos de ensamble.

### [18] Zhang et al. — Índices ETCCDI de extremos climáticos

```
[18] X. Zhang et al., "Indices for monitoring changes in extremes based on
     daily temperature and precipitation data," WIREs Climate Change,
     vol. 2, no. 6, pp. 851-870, 2011.
```

**Fuente verificada:** Wiley Online Library, *WIREs Climate Change*. DOI:
`10.1002/wcc.147`. Se cita con `et al.` porque el artículo tiene más de seis
autores; la lista completa está en el DOI.

**Ficha de contenido**
- *Qué dice:* documenta el conjunto de 27 índices definidos por el Expert
  Team on Climate Change Detection and Indices (ETCCDI) a partir de datos
  diarios de temperatura y precipitación, entre ellos R95p y R99p, que
  acumulan la precipitación de los días cuyo valor supera el percentil 95 y
  99 del periodo de referencia.
- *Por qué es relevante:* `contratos/enums.py` define el umbral de lluvia
  intensa citando explícitamente "los índices R95p y R99p del ETCCDI,
  adoptados por la OMM", pero esos índices no tenían fuente en la
  bibliografía. La referencia `[6]` es la guía de normales climáticas de la
  OMM (WMO-No. 1203), que es otro documento y no define estos índices. Sin
  esta ficha, el umbral del evento más frecuente del cantón quedaba sin
  respaldo citable.
- *Uso previsto:* cita obligada en la Tabla 1 del documento, junto a McKee
  `[4]` para el umbral de sequía. Es además la base metodológica de H2.7
  (cálculo de R95p y R99p por distrito).

### [19] Pedregosa et al. — scikit-learn

```
[19] F. Pedregosa et al., "Scikit-learn: Machine learning in Python,"
     Journal of Machine Learning Research, vol. 12, pp. 2825-2830, 2011.
```

**Fuente verificada:** sitio oficial de JMLR
(`jmlr.org/papers/volume12/pedregosa11a/pedregosa11a.pdf`). Se cita con
`et al.` por tener más de seis autores.

**Ficha de contenido**
- *Qué dice:* presenta scikit-learn, biblioteca de Python que implementa
  algoritmos de aprendizaje supervisado y no supervisado bajo una interfaz
  uniforme (`fit`, `predict`, `transform`), con énfasis en facilidad de uso,
  desempeño y documentación.
- *Por qué es relevante:* el documento afirma en la sección de tecnologías
  que se usa scikit-learn para Regresión Logística y Random Forest. Una
  afirmación sobre qué implementación concreta se empleó necesita fuente, en
  particular porque los resultados reportados dependen de los valores por
  defecto de esa implementación y de su versión.
- *Uso previsto:* cita de respaldo en la sección de tecnologías y en la de
  reproducibilidad, donde se declara la versión exacta usada
  (`scikit-learn==1.6.0`, fijada en `requirements.txt`).

### [20] He y Garcia — Aprendizaje con clases desbalanceadas

```
[20] H. He y E. A. Garcia, "Learning from imbalanced data," IEEE
     Transactions on Knowledge and Data Engineering, vol. 21, no. 9,
     pp. 1263-1284, 2009.
```

**Fuente verificada:** IEEE Xplore / ACM Digital Library. DOI:
`10.1109/TKDE.2008.239`.

**Ficha de contenido**
- *Qué dice:* revisa el problema del desbalance de clases: por qué un
  clasificador entrenado sobre datos donde una clase es mucho más frecuente
  tiende a favorecerla, qué métricas engañan en ese escenario (la exactitud,
  sobre todo) y qué familias de soluciones existen: remuestreo, aprendizaje
  sensible al costo y métodos de ensamble.
- *Por qué es relevante:* el documento anticipa en la sección V-C "un fuerte
  desbalance de clases" y por eso elige F1-macro. Sokolova y Lapalme `[12]`
  respaldan la elección de la métrica; esta referencia respalda el
  diagnóstico del problema y las opciones de tratamiento. Es el escenario
  esperable aquí: los días de riesgo alto son, por definición, minoría.
- *Uso previsto:* cita de respaldo al justificar el tratamiento del
  desbalance y en la discusión de resultados, donde importa distinguir un
  modelo que aprende de uno que predice siempre la clase mayoritaria.

### [21] Harrower y Brewer — Esquemas de color para mapas

```
[21] M. Harrower y C. A. Brewer, "ColorBrewer.org: An online tool for
     selecting colour schemes for maps," The Cartographic Journal,
     vol. 40, no. 1, pp. 27-37, 2003.
```

**Fuente verificada:** Taylor & Francis, *The Cartographic Journal*. DOI:
`10.1179/000870403235002042`.

**Ficha de contenido**
- *Qué dice:* describe los criterios para elegir esquemas de color en mapas
  coropléticos según el número de clases, la naturaleza de los datos
  (secuencial, divergente o cualitativa) y el medio de visualización, e
  incluye esquemas seguros para daltonismo.
- *Por qué es relevante:* el visor representa un riesgo ordinal de tres
  niveles por distrito. Un esquema de color mal elegido puede hacer que un
  distrito en riesgo alto se lea como medio, lo que en una herramienta de
  alerta temprana no es un problema estético. Es respaldo directo para OE4 y
  para la rúbrica de Computación Gráfica.
- *Uso previsto:* cita de respaldo en la descripción del visor y en la
  justificación del esquema de color elegido para la coropleta de riesgo
  (H5.3, historia de Avril).

### [22] Mishra y Singh — Modelado de sequía

```
[22] A. K. Mishra y V. P. Singh, "Drought modeling — A review," Journal of
     Hydrology, vol. 403, no. 1-2, pp. 157-175, 2011.
```

**Fuente verificada:** ScienceDirect, *Journal of Hydrology*. DOI:
`10.1016/j.jhydrol.2011.03.049`.

**Ficha de contenido**
- *Qué dice:* revisa los enfoques de modelado de sequía: modelos basados en
  índices, estocásticos, de probabilidad y de predicción, y discute sus
  supuestos y limitaciones al aplicarlos a distintas escalas espaciales y
  temporales.
- *Por qué es relevante:* sitúa el enfoque de este proyecto dentro del
  panorama de métodos existentes, que es lo que el estado del arte (H10.5b)
  necesita para no presentar la propuesta en el vacío. También aporta el
  vocabulario estándar para distinguir sequía meteorológica, agrícola e
  hidrológica: este proyecto estima la primera, y conviene decirlo
  explícitamente.
- *Uso previsto:* cita de respaldo en el estado del arte y en la
  delimitación del alcance, al precisar qué tipo de sequía se modela.

### [23] Xu, Li y Xu — Revisión de predicción de riesgo de incendio

```
[23] Z. Xu, J. Li y L. Xu, "Wildfire risk prediction: A review,"
     arXiv:2405.01607 [cs.LG], 2024.
```

**Fuente verificada:** arXiv, resumen y metadatos consultados
directamente (`arxiv.org/abs/2405.01607`). DOI de arXiv:
`10.48550/arXiv.2405.01607`.

**Ficha de contenido**
- *Qué dice:* revisa metodologías de predicción de riesgo de incendio
  forestal: agrupa las variables predictoras en cuatro familias (clima y
  meteorología, factores socioeconómicos, terreno e hidrología, y registro
  histórico de incendios), discute el preprocesamiento de datos de
  resoluciones espaciotemporales distintas, la evaluación de colinealidad e
  importancia de variables, y compara modelos estadísticos, de aprendizaje
  automático tradicional y profundo.
- *Por qué es relevante:* es el antecedente metodológico más cercano al
  componente de incendio de este proyecto, y su clasificación de variables
  predictoras coincide con las familias disponibles aquí, salvo la
  socioeconómica, que este proyecto no incorpora. Sirve para justificar por
  escrito qué se dejó fuera y por qué.
- *Uso previsto:* cita de respaldo en el estado del arte (H10.5b) y en la
  delimitación del alcance.
- *Advertencia sobre el tipo de fuente:* **es un preprint de arXiv, no un
  artículo con revisión por pares.** Se incluye porque su contenido se
  verificó directamente en la fuente y porque no se encontró una revisión
  equivalente de acceso abierto, pero debe citarse como preprint y no
  presentarse como literatura arbitrada. Si más adelante se confirma una
  versión publicada en revista, se reemplaza esta entrada.

### [24] OMM — Guía del usuario del SPI

```
[24] M. Svoboda, M. Hayes y D. Wood, Standardized Precipitation Index User
     Guide, WMO-No. 1090. Ginebra, Suiza: World Meteorological
     Organization, 2012.
```

**Fuente verificada:** biblioteca oficial de la OMM
(`library.wmo.int`, registro 39629).

**Ficha de contenido**
- *Qué dice:* es la guía operativa para calcular el SPI: qué longitud mínima
  de serie se requiere, cómo se ajusta la distribución de probabilidad, cómo
  se manejan los ceros en climas con estación seca marcada, y cómo se
  interpretan las escalas temporales (1, 3, 6, 12 meses) según el tipo de
  impacto que se quiere anticipar.
- *Por qué es relevante:* McKee `[4]` define el SPI y sus umbrales, pero es
  un artículo de actas de 1993 y no cubre las decisiones prácticas de
  cálculo. Esta guía sí, y es la que corresponde citar al documentar cómo se
  implementó el SPI-1 y el SPI-3 en H2.3. El detalle del manejo de ceros
  importa de forma concreta aquí: Tilarán tiene una estación seca marcada y
  meses con precipitación acumulada nula.
- *Uso previsto:* cita de respaldo en la sección de metodología al describir
  el cálculo del SPI, y en la evidencia de H2.3.

## Referencias buscadas y no incluidas

Dos revisiones de aprendizaje automático aplicado a incendio y sequía
publicadas en ScienceDirect (2025) aparecieron en la búsqueda con títulos
pertinentes, pero no se pudo acceder a su contenido para verificar qué
afirman. **No se incluyen.** En su lugar se citan `[22]` y `[23]`, cuyo
contenido sí se verificó directamente.

El criterio se mantiene: una referencia que no se pudo confirmar no entra,
aunque el título parezca adecuado y aunque haga falta para llegar a un
número.

## Resumen

| | |
|---|---|
| Fichas nuevas de esta historia | 16 (`[9]` a `[24]`) |
| Mínimo exigido por H10.5a | 15 |
| Referencias previas listadas sin ficha | 8 (`[1]` a `[8]`) |
| Total de la bibliografía | 24 |
| Referencias descartadas por no poder verificarse | 2 |
