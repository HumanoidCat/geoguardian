# Estado del arte en Costa Rica

**Historia:** H10.5b · **Responsable:** Luna · **Rubrica:** IEEE
**Depende de:** H10.5a · **Bloquea a:** H10.5c

Este documento reune lo que ya existe **en Costa Rica** sobre estimacion de
riesgo climatico, y sobre todo lo que **no** existe, que es lo que justifica el
proyecto. No es una revision global del tema: eso lo cubren `[22]` y `[23]` de
`referencias.md`. Es un insumo para Alejandro, no una seccion redactada del
documento final.

Las referencias entre corchetes remiten a `docs/investigacion/referencias.md`.

## 1. Indices de sequia aplicados al Pacifico Norte

El pais no carece de trabajo sobre sequia: carece de trabajo a escala
subcantonal.

Quesada-Hernandez, Hidalgo y Alfaro `[15]` construyeron una base de impactos de
sequia de 1970 a 1999 para tres cantones de Guanacaste y compararon seis
indices mediante regresion logistica. Encontraron que **el SPI a 6 y 12 meses
es el que mejor se asocia con impactos sociales y productivos reales**. Es el
antecedente mas directo del proyecto: valida empiricamente, en la misma
provincia, el indice que este trabajo usa para el umbral de sequia.

Su unidad de analisis es el **canton**. Este proyecto propone bajar al
distrito, que es un salto de escala, no una repeticion.

Vega Araya `[16]` analizo la variabilidad de la precipitacion en el Area de
Conservacion Guanacaste con datos CHIRPS y su relacion con el ENOS. Es
relevante por partida doble: por el resultado y porque **usa CHIRPS**, la misma
fuente que la decision D-15 adopto para precipitacion tras comprobar que NASA
POWER no diferencia entre distritos de Tilaran.

El grupo del CIGEFI de la Universidad de Costa Rica (Hidalgo, Alfaro, Amador)
concentra la produccion nacional sobre el Corredor Seco Centroamericano, del
que el canton de Tilaran forma parte por su vertiente pacifica.

**Lo que falta.** Ningun trabajo consultado estima riesgo de sequia por
distrito ni contrasta un modelo supervisado contra una linea base
climatologica a esa escala.

## 2. Incendios forestales: existe un sistema operativo, y declara sus limites

Costa Rica **si tiene** un sistema nacional de alerta temprana de incendios
forestales en operacion. Ignorarlo seria presentar el proyecto en el vacio.

El **SATIF** (Sistema de Alerta Temprana de Incendios Forestales) opera desde
2020, gestionado por el Programa Nacional de Manejo del Fuego del SINAC-MINAE,
con el Instituto Meteorologico Nacional y asesoria tecnica del Servicio
Forestal de Canada. Implementa el **Fire Weather Index (FWI)** canadiense
adaptado al pais, y clasifica el peligro en cuatro categorias: bajo, moderado,
alto y extremo `[25]`.

Lo relevante no es que exista, sino **lo que su propio operador declara que no
hace**. Del sitio del IMN, textualmente: el SATIF *"se basa unicamente"* en
temperatura, humedad relativa, velocidad del viento y lluvia, y **"no toma en
cuenta el riesgo, topografia o combustibles (vegetacion)"**.

Ademas, su resolucion espacial es la del **area representativa de la estacion
meteorologica que provee los datos**, no una malla ni una division
administrativa.

**Lo que falta, con precision.** Un indice meteorologico de peligro de fuego no
es una estimacion de riesgo: no incorpora combustible, ni historico de
ocurrencia, ni exposicion. Y al depender de estaciones, no produce un valor por
distrito. Este proyecto propone estimacion supervisada sobre variables
derivadas, con salida por distrito. **Son cosas distintas, y el documento debe
decirlo asi en vez de sugerir que no habia nada.**

La contraparte honesta: el SATIF esta operativo, validado y en uso
institucional desde 2020. Un prototipo de un trimestre no lo reemplaza.

## 3. Infraestructura nacional de datos abiertos

El pais tiene las cuatro piezas que el proyecto necesita:

| Institucion | Aporta | Estado |
|---|---|---|
| IMN | Series climaticas, boletines ENOS, SATIF | Publico |
| SNIT `[8]` | Capas territoriales oficiales por servicios OGC | Publico |
| CNE | Informes de emergencia con desglose por distrito, mapas de amenaza cantonales | Publico, disperso |
| DesInventar (UNDRR) | Inventario historico de desastres 1968-2019 con desagregacion distrital | Publico |

A esto se suman las fuentes globales: NASA POWER `[1]`, NASA FIRMS `[2]` y
Copernicus Sentinel-2 `[3]`.

**El problema no es la ausencia de datos.** Es que estan en instituciones
distintas, con formatos y granularidades distintas, y **sin ningun tratamiento
que los convierta en una estimacion localizada**. Esa es la premisa del
proyecto y este documento la confirma con las fuentes en la mano.

## 4. Aprendizaje automatico aplicado al ambiente en Costa Rica

Aqui el hallazgo es que **hay poco, y casi nada aplicado a riesgo climatico
territorial**.

Hernandez-Alpizar, Gomez-Mejia y Arguello-Vega, del Instituto Tecnologico de
Costa Rica `[26]`, revisaron el uso de inteligencia artificial, aprendizaje
automatico y SIG en ingenieria ambiental sobre IEEE Xplore, filtrando por agua,
aire, suelo, cambio climatico, energia y residuos. Su conclusion apunta a que
la aplicabilidad es amplia pero desigual, y senalan las areas que **merecen ser
reforzadas**.

En riesgo geologico si existe tradicion metodologica nacional: la metodologia
**Mora-Vahrson** de macrozonificacion de susceptibilidad a deslizamientos, de
1994, se sigue aplicando y comparando en el pais. Es un antecedente de que **la
zonificacion de amenaza por indices ponderados esta establecida en Costa
Rica**, a diferencia de la estimacion supervisada, que no lo esta.

*Nota de verificacion: la cita bibliografica completa de Mora-Vahrson (1994) no
se ha confirmado contra la publicacion original. Se menciona en el texto pero
**no se incorpora a `referencias.md`** hasta verificarla. Ver la seccion de
pendientes.*

**Lo que falta.** No se localizo ningun trabajo costarricense que compare
algoritmos supervisados para estimar riesgo climatico por unidad administrativa
subcantonal, con validacion temporal y contraste contra linea base. Es la
afirmacion mas fuerte de este documento y por eso se enuncia con cuidado: **no
se localizo** no equivale a **no existe**. La busqueda cubrio repositorios
universitarios, revistas nacionales indexadas y sitios institucionales; puede
haber literatura gris, tesis no indexadas o trabajos institucionales no
publicados que no aparecieron.

## 5. El vacio, documentado con evidencia propia

Las secciones anteriores describen lo que dice la literatura. Esta describe
tres cosas que **ninguna fuente publicada dice** y que salieron de medir en
este proyecto. Son el aporte propio de este estado del arte.

### 5.1 No hay registro historico de incendios forestales en Tilaran

La consulta a DesInventar del catalogo H4.3 devolvio **98 fichas del canton
entre 1968 y 2017**, y **ninguna es un incendio forestal**. DesInventar
distingue FIRE de FORESTFIRE; las cuatro fichas FIRE de Tilaran son incendios
estructurales: locales comerciales y una bodega.

**Consecuencia.** El componente de incendio del proyecto no se puede contrastar
contra un catalogo historico de eventos, porque ese catalogo no existe para
este canton. La validacion externa del modelo de incendio tiene que apoyarse en
otra evidencia, previsiblemente los focos de calor de FIRMS `[2]` con las
limitaciones de deteccion que documenta Giglio `[14]`. Esto afecta el diseno de
H4.4 y conviene resolverlo antes de llegar alli.

### 5.2 La sequia historica no esta desagregada por distrito

DesInventar registra sequia en Tilaran en 1972, 1973, 1976, 1977, 1982 y 1983,
varias con declaratoria de emergencia nacional. **Todas tienen el campo de
distrito vacio.** El unico episodio con desagregacion distrital es el de 2014,
y existe asi porque la declaratoria de emergencia (Decreto Ejecutivo
38642-MP-MAG) obligo a inventariar la afectacion agropecuaria finca por finca.

**Consecuencia.** La disponibilidad de datos historicos a escala distrital no
depende de la severidad del evento sino de si hubo un instrumento
administrativo que obligara a levantarlos. Es un sesgo de registro, no de
ocurrencia, y pertenece a la seccion de limitaciones.

### 5.3 Las fuentes climaticas globales no resuelven el canton

La medicion de H1.1 mostro que **los ocho distritos de Tilaran caen en una sola
celda de la malla de NASA POWER**. Temperatura, humedad, radiacion y viento son
numericamente identicas en los ocho. Solo la precipitacion, servida por CHIRPS
a 0,05 grados, varia entre distritos, con diferencias comprobadas de hasta 20 %
en acumulado semanal y, mas importante, con inversiones de orden entre dias.

**Consecuencia.** La afirmacion "riesgo por distrito" descansa, en la practica,
sobre la precipitacion. Es el hallazgo que mas acota lo que la hipotesis H1
puede sostener y debe declararse de forma explicita en el documento.

**Y es tambien un aporte al estado del arte:** que las fuentes abiertas de
cobertura global tengan o no resolucion suficiente a escala cantonal es
exactamente la pregunta que el proyecto se planteo. Para las variables
distintas de la precipitacion, en este canton, **la respuesta medida es que
no**. Ese resultado es publicable con independencia de como salga el modelo.

## 6. Como se posiciona el proyecto

Con lo anterior, el aporte queda acotado sin exagerar:

1. **No es el primer sistema de alerta del pais.** El SATIF existe, opera desde
   2020 y esta validado institucionalmente.
2. **No es el primer trabajo sobre sequia en Guanacaste.** El CIGEFI lleva anios
   y `[15]` ya establecio que el SPI es el indice pertinente.
3. **Si es, hasta donde se pudo verificar, el primero que** estima riesgo por
   distrito para un canton costarricense, comparando algoritmos supervisados
   contra una linea base climatologica bajo validacion temporal estricta, con
   datos exclusivamente abiertos.
4. **Su resultado es informativo en las dos direcciones.** Si el modelo no
   supera la linea base, el hallazgo es que los datos abiertos globales no
   bastan a escala cantonal, y eso responde la pregunta de investigacion igual
   de bien. La medicion de POWER de la seccion 5.3 ya apunta parcialmente en
   esa direccion, antes de entrenar nada.

## Referencias nuevas que aporta este documento

Se incorporan a `referencias.md` como `[25]` y `[26]`.

```
[25] Instituto Meteorologico Nacional y Sistema Nacional de Areas de
     Conservacion, "Sistema de Alerta Temprana de Incendios Forestales
     (SATIF)," CONIFOR Costa Rica. [En linea]. Disponible:
     https://www.imn.ac.cr/alerta

[26] L. Hernandez-Alpizar, J. A. Gomez-Mejia y M. B. Arguello-Vega,
     "Inteligencia artificial, machine learning y SIG en ingenieria
     ambiental: tendencias actuales," Revista Tecnologia en Marcha,
     vol. 37, no. 7, pp. 87-96, 2024.
```

**Fichas de contenido**

`[25]` **SATIF.** *Que dice:* documenta el sistema nacional de alerta temprana
de incendios forestales, operativo desde 2020, basado en el Fire Weather Index
canadiense adaptado al pais, con cuatro categorias de peligro. Declara
explicitamente que se basa unicamente en temperatura, humedad relativa,
velocidad del viento y lluvia, y que no considera riesgo, topografia ni
combustibles. *Por que es relevante:* es el sistema con el que el componente de
incendio de este proyecto va a compararse inevitablemente, y su alcance
declarado delimita con precision que aporta el proyecto y que no. *Uso
previsto:* estado del arte y discusion.

`[26]` **Hernandez-Alpizar et al.** *Que dice:* revision del uso de IA,
aprendizaje automatico y SIG en ingenieria ambiental sobre IEEE Xplore,
cuantificando la proporcion de uso por tema e identificando areas que merecen
reforzarse. *Por que es relevante:* es produccion costarricense reciente sobre
la interseccion exacta de este proyecto, y sirve para situar el trabajo dentro
de la capacidad instalada del pais en vez de citar solo literatura extranjera.
*Uso previsto:* estado del arte.

## Pendientes

1. **Verificar Mora-Vahrson (1994)** contra la publicacion original antes de
   incorporarla a `referencias.md`. Se menciona en el texto pero no se cita
   formalmente.
2. **Revisar tesis de grado y posgrado** de la UCR, la UNA y el TEC sobre
   riesgo climatico en Guanacaste. Los repositorios institucionales no
   aparecieron bien indexados en las busquedas y pueden contener trabajo
   relevante no publicado en revista.
3. **Consultar al IMN** si el SATIF tiene documentacion tecnica publicada con
   la parametrizacion del FWI para Costa Rica. Seria la comparacion mas util
   para la discusion de resultados.
4. **Contrastar con el Comite Municipal de Emergencias de Tilaran** si existe
   algun instrumento local de estimacion de riesgo que no este publicado en
   linea.
