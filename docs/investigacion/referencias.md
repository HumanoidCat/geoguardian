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
(`library.wmo.int`, registro 39629). **El texto completo se leyó
directamente**, las 16 páginas, el 2026-08-22, desde el PDF distribuido por
el Integrated Drought Management Programme. La lectura corrigió dos
afirmaciones previas de este proyecto; ver la advertencia al final de la
ficha.

**Ficha de contenido**
- *Qué dice:* es una guía **interpretativa y operativa**, no un documento de
  fórmulas. Cubre qué longitud mínima de serie se requiere (§6.2: al menos 30
  años de datos mensuales continuos), qué rango de escalas temporales es
  estadísticamente defendible (§5: de 1 a 24 meses, siguiendo a Guttman), qué
  significa cada escala en términos de impacto (§5.1.1 a §5.1.5), y cómo
  ejecutar el programa `SPI_SL_6.exe` del NDMC (§7 y §8).
- *Qué **no** dice:* **no contiene ninguna fórmula.** Su §6, "Computational
  methodology", son ocho viñetas en prosa que remiten explícitamente a McKee
  et al. (1993, 1995) y a Edwards y McKee (1997) para el procedimiento
  completo. En particular **no plantea la distribución mixta** para el
  tratamiento de ceros ni discute cómo se estima la probabilidad de mes seco.
- *Lo que sí sostiene sobre el ajuste por mes calendario:* el §5.1.1 describe
  el SPI de 1 mes diciendo que compara el total de noviembre de un año dado
  "with the November precipitation totals of all the years on record". El
  §5.1.2 dice lo equivalente para diciembre–enero–febrero, el §5.1.3 para
  abril–septiembre y el §5.1.5 para los 12 meses consecutivos. Es una
  descripción, no una prescripción —la guía nunca dice "ajústese por mes
  calendario"—, pero define el conjunto de comparación como el mismo mes o
  período del calendario a través de los años, que es el fundamento de **D-19**.
- *Por qué es relevante:* McKee `[4]` define el SPI y sus umbrales, pero es
  un artículo de actas de 1993 y no cubre las decisiones prácticas. Esta guía
  respalda tres de las que se tomaron en H2.3: el mínimo de 30 años, el rango
  de 1 a 24 meses, y el conjunto de comparación por mes calendario.
- *Uso previsto:* cita de respaldo en la sección de metodología para la
  longitud de serie, el rango de escalas y el ajuste por mes calendario. **No
  se usa para el tratamiento de ceros**, que se atribuye a `[27]`.

**Advertencia: dos correcciones derivadas de la lectura del texto.**

1. Una versión anterior de esta ficha afirmaba que la guía documenta "cómo se
   ajusta la distribución de probabilidad" y "cómo se manejan los ceros". Las
   dos son falsas y se retiran. El error se propagó a los comentarios de
   `backend/senales/spi.py` y a la evidencia de H2.3, y se corrigió en los
   tres lugares.
2. El §5.1.1 desaconseja calcular el SPI en escalas menores a un mes y cita
   como respaldo a "Wu and others, 2006". **La lista de referencias del propio
   documento fecha ese trabajo en 2007** (Wu, Svoboda, Hayes, Wilhite y Wen,
   *International Journal of Climatology*, 27(1):65-79). Es una errata interna
   de la guía. Si se cita ese trabajo, la fecha correcta es 2007.

### [25] IMN y SINAC — Sistema de Alerta Temprana de Incendios Forestales

```
[25] Instituto Meteorológico Nacional y Sistema Nacional de Áreas de
     Conservación, "Sistema de Alerta Temprana de Incendios Forestales
     (SATIF)," CONIFOR Costa Rica. [En línea]. Disponible:
     https://www.imn.ac.cr/alerta
```

**Fuente verificada:** sitio oficial del IMN (`imn.ac.cr/alerta`), consultado
el 2026-08-18.

**Ficha de contenido**
- *Qué dice:* documenta el sistema nacional de alerta temprana de incendios
  forestales, operativo desde 2020, gestionado por el Programa Nacional de
  Manejo del Fuego del SINAC-MINAE con el IMN y asesoría técnica del Servicio
  Forestal de Canadá. Implementa el Fire Weather Index canadiense adaptado al
  país y clasifica el peligro en cuatro categorías. Declara de forma explícita
  que se basa únicamente en temperatura, humedad relativa, velocidad del viento
  y lluvia, y que **no considera riesgo, topografía ni combustibles**. Su
  resolución espacial es la del área representativa de la estación
  meteorológica que aporta los datos.
- *Por qué es relevante:* es el sistema nacional con el que el componente de
  incendio de este proyecto se va a comparar inevitablemente. Su alcance
  declarado delimita con precisión qué aporta el proyecto y qué no, y evita
  presentar la propuesta como si no existiera nada previo.
- *Uso previsto:* estado del arte (H10.5b) y discusión de resultados.

### [26] Hernández-Alpízar, Gómez-Mejía y Argüello-Vega — IA, ML y SIG en ingeniería ambiental

```
[26] L. Hernández-Alpízar, J. A. Gómez-Mejía y M. B. Argüello-Vega,
     "Inteligencia artificial, machine learning y SIG en ingeniería
     ambiental: tendencias actuales," Revista Tecnología en Marcha,
     vol. 37, no. 7, pp. 87-96, 2024.
```

**Fuente verificada:** Revista Tecnología en Marcha, Instituto Tecnológico de
Costa Rica. DOI: `10.18845/tm.v37i7.7304`.

**Ficha de contenido**
- *Qué dice:* revisa el uso de inteligencia artificial, aprendizaje automático
  y sistemas de información geográfica en ingeniería ambiental a partir de la
  base IEEE Xplore, filtrando por agua, aire, suelo, cambio climático, energía
  y residuos, y cuantifica la proporción de uso por tema para señalar las áreas
  con mayor aplicabilidad y las que merecen reforzarse.
- *Por qué es relevante:* es producción costarricense reciente sobre la
  intersección exacta de este proyecto —aprendizaje automático, SIG y ambiente—
  y permite situar el trabajo dentro de la capacidad instalada del país en vez
  de apoyarse solo en literatura extranjera.
- *Uso previsto:* estado del arte (H10.5b).

### [27] Stagge et al. — Distribuciones candidatas para índices de sequía

```
[27] J. H. Stagge, L. M. Tallaksen, L. Gudmundsson, A. F. Van Loon y
     K. Stahl, "Candidate distributions for climatological drought indices
     (SPI and SPEI)," International Journal of Climatology, vol. 35, no. 13,
     pp. 4027-4040, 2015.
```

**Fuente verificada — leer con atención el alcance de la verificación.** Los
datos bibliográficos (autores, revista, volumen, número, páginas, año, DOI
`10.1002/joc.4267`) se confirmaron en Wiley Online Library y en tres
repositorios institucionales independientes (ETH Zürich, Vrije Universiteit
Amsterdam, Wageningen).

**El texto del artículo no se leyó: está tras muro de pago.** Lo que sí se
leyó, el 2026-08-22, es la documentación de la función `fitSCI` del paquete R
`SCI`, **firmada por Lukas Gudmundsson y James H. Stagge**, dos de los cinco
autores del artículo. Esa documentación es la que atribuye a Stagge et al. el
estimador de centro de masa y da su forma explícita, y remite al DOI de
arriba en su lista de referencias.

Es una fuente secundaria escrita por los propios autores sobre su propio
trabajo: es la mejor confirmación disponible sin acceso al artículo, pero
**no equivale a haber leído el artículo** y no debe presentarse como tal. Si
alguien consigue acceso institucional, corresponde verificar contra el texto
y actualizar esta nota.

**Ficha de contenido**
- *Qué dice, según lo verificado:* evalúa qué distribución de probabilidad
  conviene para normalizar el SPI y el SPEI, y propone modificaciones a la
  metodología. Entre ellas, el tratamiento de los meses de precipitación nula
  mediante una distribución mixta *D(x) = p0 + (1 − p0)·G(x)*, con la
  probabilidad de cero estimada por un **estimador de centro de masa** basado
  en la posición de graficación de Weibull. El valor asignado en *x = 0* es
  *(n0 + 1) / (2(n + 1))*, donde *n0* es el número de meses nulos y *n* el
  tamaño de muestra.
- *Por qué es relevante:* Tilarán tiene estación seca marcada y meses de
  0,0 mm, así que el tratamiento de ceros no es un detalle. La implementación
  de H2.3 usa *q/2* en *x = 0*, que es el límite de *(n0 + 1)/(2(n + 1))*
  cuando *n* es grande: **nuestro estimador es la simplificación de muestra
  grande del de Stagge et al.**, y conviene decirlo así y no afirmar que es
  el mismo.
- *Uso previsto:* atribución del tratamiento de ceros y del estimador de
  centro de masa en la metodología y en la evidencia de H2.3. **Reemplaza la
  atribución a `[24]`, que era incorrecta**: la guía de la OMM no plantea la
  distribución mixta.

## Fichas nuevas de la revisión del 2026-08-30

Ocho fichas (`[28]` a `[35]`) agregadas al ampliar la revisión bibliográfica.
El criterio de las anteriores se mantiene sin cambios: se declara qué se leyó
y qué no, y ninguna entra sin haber confirmado que dice lo que aquí se afirma.

Tres de estas fichas **contradicen o matizan decisiones ya tomadas**. Están
marcadas como tales, porque el valor de encontrarlas está justamente en eso y
no en engrosar la bibliografía.

### [28] Funk et al. — CHIRPS

```
[28] C. Funk et al., "The climate hazards infrared precipitation with
     stations—a new environmental record for monitoring extremes,"
     Scientific Data, vol. 2, art. 150066, 2015.
```

**Fuente verificada:** *Scientific Data* (Nature), DOI `10.1038/sdata.2015.66`,
publicado 2015-12-08. **Texto completo leído** el 2026-08-30 (acceso abierto).

**Ficha de contenido**
- *Qué dice:* describe CHIRPS, un producto de precipitación cuasi-global
  (50°S–50°N) a resolución 0,05°, con pasos diario, pentadal y mensual desde
  1981. Combina estimaciones de lluvia derivadas de duración de nube fría
  (CCD) en infrarrojo térmico, calibradas con TMPA 3B42 v7, e incorpora datos
  de estaciones en dos fases mediante interpolación de anomalías sobre una
  climatología de alta resolución.
- *El dato decisivo para nosotros, citado del artículo:* «The basic time step
  of the CHIRP is the pentad. All other time steps are either aggregates
  (dekadal and monthly) or disaggregations (daily). Pentadal CHIRP values are
  disaggregated to daily precipitation estimates based on daily CFS fields
  rescaled to 0.05° resolution.»
- *Por qué es relevante:* **el paso básico de CHIRPS es el péntada, no el
  día.** La serie diaria no se mide: es el total del péntada repartido entre
  sus cinco días según la forma diaria que da el reanálisis CFS. Nuestra
  etiqueta de lluvia intensa se construye sobre acumulados de 72 h de esa
  serie diaria, es decir, sobre un reparto interno al péntada cuya
  distribución temporal proviene de un modelo y no de la observación.
- *Uso previsto:* cita obligada de la fuente en la metodología —hoy CHIRPS se
  usa sin referencia, que era un vacío— y **base de la amenaza a la validez
  del etiquetado de lluvia**. Explica de forma independiente el patrón medido
  en el contraste contra el catálogo: de 12 fallos de lluvia, 9 tenían marca a
  ≤14 días y en 9 la marca llegó *después*. Un error de fecha por debajo del
  péntada es exactamente lo que este diseño produce.

### [29] Rojas Morales — índices distritales de riesgo en Costa Rica

```
[29] N. Rojas Morales, "Índices distritales de riesgo de desastres por
     eventos lluviosos extremos en Costa Rica," tesis de Magister
     Scientiae, Centro Agronómico Tropical de Investigación y Enseñanza
     (CATIE), Turrialba, Costa Rica, 2018.
```

**Fuente verificada:** repositorio institucional del CATIE, handle
`11554/8725`. **Documento completo leído** el 2026-08-30.

**Ficha de contenido**
- *Qué dice:* estima índices de riesgo de desastre por lluvia extrema **para
  los 459 distritos de Costa Rica**, en dos artículos. El primero valida
  CHIRPS v2 contra ocho estaciones del IMN, una por región climática, para
  1981–2013. El segundo estima la probabilidad de desastre con un modelo
  Probit, usando como variable dependiente la ocurrencia de desastre y como
  explicativas la anomalía de precipitación —escenario de dos desviaciones
  estándar, percentil 90— junto a variables socioeconómicas, biofísicas y
  geográficas.
- *Resultados de la validación, relevantes para Tilarán:* CHIRPS v2 ajusta
  mejor en época lluviosa que en seca, y en época seca **subestima** en la
  mayoría de las estaciones. Ajusta mejor en zonas de relieve suave que en
  zonas montañosas, donde el relieve gobierna el patrón de lluvia. Tilarán es
  montañoso.
- *Por qué es relevante:* es el antecedente directo más cercano que existe al
  problema de GeoGuardian —mismo país, misma unidad administrativa, misma
  fuente de precipitación, mismo evento— y hasta ahora el documento no lo
  citaba. Define el trabajo relacionado nacional y fija qué aporta GeoGuardian
  que este trabajo no hace: operación continua, tres eventos en vez de uno, y
  un visor.
- *Uso previsto:* trabajo relacionado (sección II), justificación de la escala
  distrital, y respaldo de la limitación por relieve en amenazas a la validez.

### [30] Openshaw — el problema de la unidad de área modificable

```
[30] S. Openshaw, The Modifiable Areal Unit Problem, Concepts and
     Techniques in Modern Geography (CATMOG) 38. Norwich, Reino Unido:
     Geo Books, 1984.
```

**Fuente verificada:** monografía CATMOG 38, ISBN 0-86094-134-5, ISSN
0306-6142. **Texto completo leído** el 2026-08-30.

**Ficha de contenido**
- *Qué dice:* nombra y descompone el problema. Cita textual de la definición:
  «the areal units (zonal objects) used in many geographical studies are
  arbitrary, modifiable, and subject to the whims and fancies of whoever is
  doing, or did, the aggregating». Distingue dos subproblemas: el **problema
  de escala** —la variación de resultados al agregar progresivamente a
  unidades menos numerosas y más grandes— y el **problema de agregación** —la
  variación por combinaciones alternativas de unidades manteniendo constante
  el número de zonas—. Y lo vincula con la **falacia ecológica**: inferir
  sobre los individuos que forman una zona a partir del dato agregado de la
  zona, cuya gravedad depende de cuán heterogénea sea internamente.
- *Por qué es relevante:* **le pone nombre al hallazgo central del proyecto.**
  Que cuatro de cinco variables no distingan distritos de Tilarán no es una
  anomalía nuestra: es un efecto de escala documentado desde 1984, medido aquí
  en un caso concreto. Citarlo convierte una observación en una medición de un
  fenómeno conocido, que es la diferencia entre un informe y una
  investigación.
- *Uso previsto:* marco conceptual de la sección I y de las conclusiones.

### [31] Gotway y Young — combinación de datos espaciales incompatibles

```
[31] C. A. Gotway y L. J. Young, "Combining incompatible spatial data,"
     Journal of the American Statistical Association, vol. 97, no. 458,
     pp. 632-648, 2002.
```

**Fuente verificada — alcance declarado.** Datos bibliográficos confirmados en
Taylor & Francis (JASA), DOI `10.1198/016214502760047140`, y en dos índices
independientes. **El texto completo no se leyó: está tras muro de pago.** Lo
que se leyó es el resumen del editor y las descripciones concordantes de tres
fuentes secundarias. Si alguien consigue acceso institucional, corresponde
verificar y actualizar esta nota.

**Ficha de contenido**
- *Qué dice, según lo verificado:* revisa el **problema de cambio de soporte**
  (*change of support problem*), esto es, inferir un proceso espacial a una
  resolución a partir de datos en otra. Distingue tres casos: *upscaling*
  (agregar puntos a un área), ***downscaling* (desagregar el dato de un área a
  unidades menores)** y *side-scaling* (dos particiones que se solapan sin
  anidar). Clasifica el MAUP como un caso del problema de cambio de soporte.
- *Por qué es relevante:* es el nombre técnico exacto de lo que hace
  GeoGuardian. Asignar el valor de una celda CHIRPS de 0,05° —unos 5,5 km— a
  distritos de Tilarán es *downscaling*, y hacerlo por asignación directa,
  sin modelo, es la forma que la literatura identifica como problemática. El
  documento describe hoy esta operación sin nombrarla.
- *Uso previsto:* metodología, al declarar la operación de asignación
  celda→distrito, y amenazas a la validez.

### [32] Roberts et al. — validación cruzada con estructura espacial y temporal

```
[32] D. R. Roberts et al., "Cross-validation strategies for data with
     temporal, spatial, hierarchical, or phylogenetic structure,"
     Ecography, vol. 40, no. 8, pp. 913-929, 2017.
```

**Fuente verificada:** *Ecography* (Wiley / Nordic Society Oikos), DOI
`10.1111/ecog.02881`. Datos bibliográficos y resumen confirmados en la
editorial y en dos repositorios institucionales. **Se leyó el resumen
completo, no el artículo entero.**

**Ficha de contenido**
- *Qué dice, según lo verificado:* cuando los datos tienen estructura
  temporal, espacial o jerárquica, ignorarla al validar produce una
  **subestimación seria del error predictivo**. Propone validación cruzada por
  bloques —partir los datos de forma estratégica y no aleatoria— y recomienda
  usarla siempre que exista estructura de dependencia, **aunque los residuos
  del modelo ajustado no muestren correlación visible** y aunque el modelo
  incorpore estructuras de correlación.
- *Por qué es relevante, y en qué nos corrige:* la validación de ventana
  expansiva ya bloquea la dimensión **temporal**, con cortes en frontera de
  mes y embargo de 7 días. **No bloquea la dimensión espacial.** Los ocho
  distritos de Tilarán comparten celdas de las fuentes gruesas, de modo que
  dos filas del mismo día en distritos vecinos no son observaciones
  independientes. Según este trabajo, eso subestima el error, y la
  subestimación no se detecta mirando residuos.
- *Uso previsto:* amenazas a la validez, y trabajo futuro. Complementa a
  `[11]`, que cubre solo la dependencia temporal.

### [33] Northcutt, Athalye y Mueller — errores de etiqueta

```
[33] C. G. Northcutt, A. Athalye y J. Mueller, "Pervasive label errors in
     test sets destabilize machine learning benchmarks," in Proc. 35th
     Conf. Neural Information Processing Systems (NeurIPS) Datasets and
     Benchmarks Track, 2021.
```

**Fuente verificada:** actas de NeurIPS 2021, *Datasets and Benchmarks Track*;
preprint arXiv `2103.14749`. **Se leyó el resumen y la ficha de las actas, no
el artículo entero.**

**Ficha de contenido**
- *Qué dice, según lo verificado:* identifica errores de etiqueta en los
  conjuntos de prueba de diez de los repositorios más usados en visión,
  lenguaje y audio, con un promedio del **3,4 %** de error; en el conjunto de
  validación de ImageNet, 2916 errores, un 6 %. La consecuencia que interesa:
  con suficiente proporción de etiquetas mal puestas, **un modelo de menor
  capacidad puede ser más útil en la práctica que uno de mayor capacidad**, y
  el orden del *ranking* se invierte.
- *Por qué es relevante:* es el respaldo externo de la tesis del proyecto.
  Sostiene que la calidad del etiquetado condiciona la comparación de modelos
  y que un error en la variable objetivo no produce un fallo visible sino
  métricas plausibles sobre un objetivo mal construido —exactamente lo que
  dicen nuestras conclusiones sobre cuatro de los seis hallazgos—.
- *Uso previsto:* introducción y conclusiones; convierte «decidimos validar el
  etiquetado antes de modelar» en una decisión con respaldo en la literatura.

### [34] Brown, Cai y DasGupta — intervalos para una proporción binomial

```
[34] L. D. Brown, T. T. Cai y A. DasGupta, "Interval estimation for a
     binomial proportion," Statistical Science, vol. 16, no. 2,
     pp. 101-133, 2001.
```

**Fuente verificada:** *Statistical Science* (Institute of Mathematical
Statistics), DOI `10.1214/ss/1009213286`, acceso abierto en Project Euclid;
copia del autor en la Wharton School. **Se leyó el resumen y las
recomendaciones, no la demostración completa.**

**Ficha de contenido**
- *Qué dice, según lo verificado:* la cobertura del intervalo de Wald para una
  proporción es errática de forma mucho más persistente de lo que se suele
  reconocer, y las recetas habituales de los libros de texto sobre cuándo es
  seguro usarlo son engañosas. Recomienda el **intervalo de Wilson** o el de
  Jeffreys de colas iguales para *n* pequeño, y el de Agresti-Coull para *n*
  mayor.
- *Por qué es relevante, y en qué nos corrige:* el documento reporta hoy
  proporciones como valores puntuales —64,7 % de cobertura sobre 34 eventos de
  lluvia, 13,7 % de tasa base— sin intervalo. Con *n* = 34 el intervalo es
  ancho, y **sin él no se puede afirmar que 64,7 % y 13,7 % son distintos**:
  solo se está mostrando la diferencia entre dos puntos. Es la carencia más
  concreta frente a un documento de investigación bien hecho.
- *Uso previsto:* recalcular las proporciones de la Fig. 3 y del contraste
  contra el catálogo con intervalo de Wilson al 95 %, y apoyar las
  conclusiones en la separación entre intervalos y no en los valores puntuales.

### [35] Ben Bouallègue et al. — verificación de pronósticos de eventos raros

```
[35] Methodological and conceptual challenges in rare and severe event
     forecast verification, Natural Hazards and Earth System Sciences,
     vol. 22, no. 2, pp. 539-557, 2022.
```

**Fuente verificada — alcance declarado.** Artículo en acceso abierto en
NHESS (Copernicus), volumen 22, número 2, páginas 539-557, 2022. **Se leyó el
planteamiento y las secciones sobre exactitud y sobre los índices de destreza;
no el artículo completo.** *La lista de autores no se transcribió de la fuente
y debe completarse antes de citar.*

**Ficha de contenido**
- *Qué dice, según lo verificado:* en pronóstico de eventos raros, centrarse
  en la exactitud «recompensa desempeños sin destreza e incentiva predicciones
  de no-ocurrencia», lo que es especialmente grave cuando fallar una
  ocurrencia cuesta mucho más que una falsa alarma. Discute índices pensados
  para tasas base bajas —Peirce, Heidke, índice de éxito crítico— y su
  relación con precisión y exhaustividad.
- *Por qué es relevante:* respalda desde la meteorología operativa la elección
  de F1-macro sobre exactitud, que hoy se justifica solo con `[12]` y `[20]`,
  ambas de aprendizaje automático general. Y aporta el vocabulario propio del
  dominio, que es el que va a leer un evaluador de riesgo climático.
- *Uso previsto:* metodología, al justificar la métrica; y discusión.

## Corrección de la ficha `[15]`

**La ficha original se escribió sobre el resumen. Leído el artículo completo
el 2026-08-30, dice algo que la ficha no recoge y que afecta a una decisión
nuestra.**

Lo que la ficha decía —que el SPI es el índice con asociación más fuerte con
los impactos socio-productivos registrados en Guanacaste— es correcto. Falta
lo siguiente:

- *Las escalas evaluadas son SPI-6 y SPI-12, no SPI-3.* El SPI-12 se toma en
  diciembre, para describir el año; el SPI-6 en octubre, para describir la
  estación lluviosa del Pacífico. **SPI-3 no se evalúa en ese trabajo.**
  GeoGuardian usa SPI-3 por D-19. La conclusión de la referencia no respalda
  esa escala: respalda el SPI como familia y otras dos escalas concretas.
- *La escala espacial elegida es cantonal, no distrital.* Los autores filtran
  los impactos «a una escala cantonal (municipal, gobierno local)», teniendo
  disponibles registros a escala de distrito. Es una decisión del trabajo más
  cercano al nuestro, en sentido contrario al nuestro.
- *Las fuentes de impacto son cuatro, no tres:* DesInventar, EM-DAT, IMN **y
  prensa nacional en papel y digital**, integradas en una base única. Nosotros
  contrastamos contra DesInventar sola.
- *Declaran una limitación que también es nuestra:* «en las bases de datos
  consultadas no siempre aparecía el sector que fue afectado o el tipo de
  impacto», lo que les obligó a un análisis más general que el planeado.
- *Contexto que el documento no usa y debería:* Tilarán está en Guanacaste, y
  Guanacaste es el extremo sur del **Corredor Seco Centroamericano**, que va
  desde Chiapas hasta ahí. Es el marco geográfico natural de la parte de
  sequía.

**Consecuencia pendiente de decisión:** o se justifica SPI-3 con otro
respaldo, o se cambia la escala, o se declara como amenaza a la validez.
Ver la anotación en la bitácora de decisiones.

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
| Fichas de H10.5a | 16 (`[9]` a `[24]`) |
| Mínimo exigido por H10.5a | 15 |
| Fichas agregadas por H10.5b | 2 (`[25]` y `[26]`) |
| Fichas agregadas por la corrección de atribución de H2.3 | 1 (`[27]`) |
| Fichas agregadas por la revisión del 2026-08-30 | 8 (`[28]` a `[35]`) |
| Referencias previas listadas sin ficha | 8 (`[1]` a `[8]`) |
| Total de la bibliografía | 35 |
| Referencias descartadas por no poder verificarse | 2 |
| Fichas corregidas tras leer la fuente completa | 2 (`[24]`, `[15]`) |
| Pendientes de verificar antes de citar | 2 (Mora-Vahrson 1994, ver `estado-del-arte.md`; autores de `[35]`) |
| Citadas con verificación parcial declarada | 4 (`[27]`, `[31]`, `[32]`, `[35]`) |
| Fichas que contradicen o matizan una decisión tomada | 3 (`[15]`, `[32]`, `[34]`) |
