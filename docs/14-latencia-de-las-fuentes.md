# Latencia real de las tres fuentes

**Fecha.** 23 de agosto de 2026 · **Responsable.** Alejandro
**Por qué existe.** El proyecto habla de «información en tiempo real» sin haber
comprobado nunca **cuándo llega el dato**. Esto lo mide contra la documentación
oficial de cada fuente, antes de que la afirmación pase al documento IEEE.

Es el mismo procedimiento que cerró R16: la frase estaba escrita desde el
principio y nadie la había contrastado.

---

## Resumen

| Fuente | Qué alimenta | Latencia | ¿Sirve actualizar seguido? |
|---|---|---|---|
| **FIRMS** | Incendio | **~3 horas** | **Sí** |
| **POWER** | Temperatura, humedad, viento, radiación | días (producto reciente) | Poco |
| **CHIRPS final** | Precipitación → sequía y lluvia intensa | **21 a 51 días** | **No** |

**«Tiempo real» no es una propiedad del sistema: es una propiedad de cada
evento.** Para incendio es alcanzable. Para sequía y lluvia intensa, no.

---

## 1. CHIRPS · el hallazgo que cambia lo que se puede prometer

La documentación oficial (CHIRPS FAQ, sección *What is the latency of the CHIRPS
product?*):

> *"There is a rapid (GTS and Mexico only) CHIRPS available 2 days after the end
> of a pentad. Final CHIRPS (all station data) is available sometime in the third
> week of the following month."*

**El producto final llega en la tercera semana del mes siguiente.** Para un evento
del 1 de septiembre, eso son unos **51 días**; para uno del 30 de septiembre,
unos **21**.

### Por qué esto le pega directamente a la sequía

El SPI-3 mira una ventana de **90 días que termina hoy**. Con esa latencia, entre
**21 y 51 de esos 90 días** solo existen como producto preliminar en el momento
de estimar. O sea: **entre el 23 % y el 57 % de la ventana no es dato final.**

### Y el preliminar es peor de lo que su nombre sugiere

No es «el mismo dato, menos pulido». Es **«GTS and Mexico only»**: incorpora
únicamente estaciones del GTS y de México. Para Costa Rica eso significa que el
producto rápido es, en la práctica, satélite sin la corrección por estaciones
locales que es justamente lo que distingue a CHIRPS de una estimación satelital
cualquiera.

Y es la fuente que **D-15 eligió por su resolución de 0,05°**, la única capaz de
distinguir distritos según I-05.

### Un segundo hallazgo, con fecha

> *"Production of CHIRPS v2 will end after December 2026. Users are encouraged to
> transition to CHIRPS v3."*

**La fuente de precipitación del proyecto deja de producirse en cuatro meses.**
No afecta al curso —termina antes—, pero sí a cualquier afirmación sobre que el
sistema sea utilizable por la Municipalidad después.

---

## 2. POWER · el mismo defecto que R16, en otra fuente

De la documentación de la API diaria de POWER:

> *"Meteorological parameters are derived from the NASA's GMAO **MERRA-2**
> assimilation model (Jan. 1, 1981 to within a few months of real time) plus
> **GEOS-5.12.4 FP-IT** (End of MERRA-2 to within several days of real time)."*

**El dato histórico y el dato reciente no salen del mismo modelo.**

- Histórico, hasta hace unos meses: **MERRA-2**
- Los últimos meses: **GEOS-5.12.4 FP-IT**

Un modelo entrenado sobre la serie histórica se entrena con MERRA-2 y **opera
sobre FP-IT**. Es exactamente la heterogeneidad que César encontró en FIRMS
—MODIS hasta 2011, MODIS+VIIRS después, con un salto de 2,1×— pero en la fuente
que dábamos por homogénea, y en el peor lugar posible: **la frontera cae
justamente en el dato que el sistema usaría para operar.**

Nadie lo había notado. I-05 y D-15 hablan de MERRA-2 como si fuera toda la serie.

**No está medido cuánto difieren los dos productos.** Eso requiere descargar el
solape y compararlo, y es trabajo de H1.1. Queda declarado como pendiente, no
como resuelto.

---

## 3. FIRMS · la única que sí es casi en tiempo real

NASA distribuye los focos globales **dentro de las 3 horas** de la observación
satelital, a través de LANCE. Para Estados Unidos y Canadá hay un producto en
tiempo real, que no aplica acá.

Es coherente con lo que César midió en R16: el archivo histórico por país llega
hasta 2024, y para el año en curso hace falta la clave de la API.

---

## 4. Qué se puede prometer, y qué no

| Evento | Fuente | Latencia | Cadencia útil |
|---|---|---|---|
| Incendio | FIRMS | 3 h | diaria, o más seguido |
| Lluvia intensa | CHIRPS | 21-51 d final, 2 d preliminar | diaria con preliminar, declarándolo |
| Sequía | CHIRPS | 21-51 d final | **semanal como mucho** |

**Para sequía hay una razón más, y es independiente de la latencia.** El SPI-3
mira 90 días, de los cuales 83 ya se conocían ayer. Actualizarlo a diario mueve la
aguja poquísimo aunque el dato llegara al instante.

---

## 5. Lo que esto obliga a decidir

**1. El sistema no promete «tiempo real».** Promete una latencia declarada por
evento. Hay que sacar esa frase del charter y del documento IEEE, o acotarla.

**2. La ingesta necesita una historia, y no existe.** De las 86 del backlog,
ninguna vuelve a consultar las fuentes: H1.1 es una descarga histórica de una
vez. Sin ella el sistema es una foto.

**3. Hay que decidir qué hacer con el preliminar de CHIRPS.** Usarlo y declararlo,
o no usarlo y aceptar que la sequía se estima con hasta 51 días de retraso. Las
dos son defendibles; lo que no lo es, es no decidirlo.

**4. Medir el solape MERRA-2 / FP-IT.** Es de H1.1 y es la misma medición que
César hizo para las eras de FIRMS.

**5. El fin de vida de CHIRPS v2 va a las limitaciones del documento IEEE.**

---

## Fuentes

- CHIRPS FAQ, *What is the latency of the CHIRPS product?* —
  https://wiki.chc.ucsb.edu/CHIRPS_FAQ
- CHIRPS, página del producto, aviso de fin de producción de v2 —
  https://www.chc.ucsb.edu/data/chirps
- NASA POWER, documentación de la API diaria, sección de fuentes —
  https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- NASA FIRMS, latencia del producto NRT —
  https://www.earthdata.nasa.gov/data/tools/firms

**Alcance de la verificación.** Las cuatro afirmaciones salen de documentación
oficial de cada proveedor, citada arriba. **No se midió empíricamente** el retraso
real descargando archivos y comparando fechas: eso confirmaría la latencia
declarada y es trabajo de H1.1 y H1.2, que tienen los descargadores.
