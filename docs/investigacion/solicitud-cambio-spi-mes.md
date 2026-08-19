# Solicitud de cambio de contrato · `ProcesadorSenales.spi`

**ID.** SC-02
**Contrato afectado.** `contratos/senales.py`, metodo `spi`
**Solicitante.** Luna, desde H2.3
**Modulos que lo consumen.** `backend/senales` (H2.3, mio), `backend/modelado`
(H3.0, etiquetado de la variable objetivo, de Alejandro),
`contratos/simulados/senales.py`
**Fecha.** 2026-08-18
**Estado.** Pendiente de aprobacion

---

## Cambio propuesto

Que `spi` reciba el mes calendario de cada posicion de la serie:

```python
def spi(
    self,
    precipitacion: list[float | None],
    ventana_meses: int,
    meses: list[int] | None = None,
) -> list[float | None]:
    ...
```

`meses[i]` es el mes calendario, de 1 a 12, de la posicion `i`. Si se pasa
`None`, el comportamiento es el actual —un unico ajuste para toda la serie— y
la implementacion **debe advertirlo por registro**, porque el resultado no es
un SPI.

El parametro va al final y con valor por defecto, de modo que **ninguna llamada
existente se rompe**.

---

## Por que no se puede resolver sin cambiar el contrato

El SPI de McKee, Doesken y Kleist (1993), referencia `[4]`, y la guia operativa
de la OMM WMO-No. 1090, referencia `[24]`, **ajustan una distribucion gamma por
cada mes calendario**: los eneros contra la distribucion historica de los
eneros, los febreros contra los febreros. Eso es lo que convierte al SPI en un
indice de **anomalia**.

La firma actual recibe `list[float | None]` y nada mas. **No hay forma de saber
a que mes corresponde cada posicion**, asi que la implementacion solo puede
ajustar una distribucion unica para toda la serie.

No es un detalle de precision. Con ajuste unico, en un clima con estacion seca
marcada, los meses secos caen siempre en la cola baja de la distribucion
conjunta y los lluviosos siempre en la alta. El indice deja de medir anomalia
y pasa a medir **en que epoca del anio estamos**, que es justamente lo que un
indice estandarizado existe para descontar.

---

## La medicion

Herramienta: `docs/herramientas/medir_spi_por_mes.py`. Serie sintetica de 35
anios con el regimen del Pacifico Norte, estacion seca de diciembre a abril y
maximos en setiembre y octubre. SPI-3, que es el que usa el umbral de sequia de
`contratos/enums.py`.

    Serie sintetica: 35 anios, 420 meses, SPI-3
    Posiciones con SPI calculado en ambos metodos: 417

    SPI medio por estacion (deberia rondar 0 en las dos)
                             ajuste unico   ajuste por mes
      estacion seca                 -0.84            -0.00
      estacion lluviosa              0.60            -0.00

    Meses declarados en sequia (SPI <= -1.0)
      ajuste unico   :   99
      ajuste por mes :   73
      coinciden      :   21

      De los 99 meses que el ajuste unico declara en sequia,
      99 caen en estacion seca (100.0 %).
      De los 73 del ajuste por mes,
      29 caen en estacion seca (39.7 %).

    Correlacion entre ambos metodos: 0.425

### Lectura

**El dato decisivo es el 100 %.** Los 99 meses que el ajuste unico declara en
sequia caen, los 99, en estacion seca. El indice no esta detectando sequia:
esta detectando que es verano. Un sistema de alerta construido sobre eso
declararia sequia todos los anios, en los mismos meses, llueva lo que llueva.

El ajuste por mes da media **-0,00 en las dos estaciones**, que es exactamente
lo que debe dar un indice de anomalia, y reparte sus declaraciones de sequia
entre ambas: 39,7 % en seca y el resto en lluviosa.

De los 73 episodios reales que detecta el ajuste por mes, el ajuste unico solo
coincide en **21**. Se pierden 52 sequias reales y se inventan 78 que no lo son.

La correlacion de **0,425** entre ambos metodos confirma que no son dos
versiones de lo mismo con distinta precision: **miden cosas distintas**.

---

## Impacto en cada consumidor

| Consumidor | Impacto |
|---|---|
| `backend/senales` (H2.3, Luna) | Ninguno para llamadas existentes. Con `meses` se activa el ajuste correcto |
| `backend/modelado` (H3.0, Alejandro) | Es el mas afectado: el etiquetado de sequia usa el umbral SPI-3 <= -1,0 de `contratos/enums.py`. Con ajuste unico, la etiqueta "sequia alta" quedaria correlacionada con el mes calendario y el modelo aprenderia el calendario, no el clima |
| `contratos/simulados/senales.py` (Alejandro) | Hay que aceptar el parametro. El simulado calcula una puntuacion z y no un SPI, asi que puede ignorarlo, pero debe aceptarlo para seguir cumpliendo el protocolo |
| `backend/api`, `frontend` | Ninguno. No llaman a `spi` directamente |

---

## Lo que ya esta hecho, y no depende de esta solicitud

H2.3 esta implementada y probada contra la firma actual, con 21 pruebas en
verde. El ajuste gamma, la correccion de la OMM para los ceros, la
transformacion a normal estandar y el tratamiento de huecos **no cambian** si
se aprueba el cambio: lo unico que cambia es que el ajuste se hace una vez por
mes en lugar de una vez para toda la serie.

Si el cambio se aprueba, el trabajo adicional es de aproximadamente una hora.

---

## Alternativa considerada y descartada

**Inferir el mes a partir de la posicion**, asumiendo que la serie empieza en
enero y no tiene meses ausentes. Se descarto: la suposicion no esta en ninguna
parte del contrato, no se puede verificar desde dentro de la funcion, y si
alguna vez entra una serie que empieza en otro mes el indice quedaria mal
calculado **sin ningun sintoma visible**. Es la misma clase de error silencioso
que la incidencia I-04.

---

## Aprobado por

Pendiente.

## Fecha de aprobacion

Pendiente.
