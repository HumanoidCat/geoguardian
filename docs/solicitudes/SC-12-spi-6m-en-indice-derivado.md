# SC-12 · Agregar `spi_6m` a `IndiceDerivado`, y subir contratos a 1.5.0

| | |
|---|---|
| **Archivos compartidos** | `contratos/esquemas.py`, `contratos/__init__.py` |
| **Pedida por** | Alejandro, al preparar H14.5 |
| **Redactada por** | Alejandro, 2026-09-15 |
| **Historia que la origina** | H14.5 · La tarjeta de sequía dice el índice medido, no un nivel estimado |
| **Decisión que la respalda** | **D-53**, escrita antes que esta solicitud |
| **Numeración** | SC-11 excluye `gestion/` del versionado |

## El problema, en una frase

**El contrato tiene `spi_1m` y `spi_3m`, y no tiene `spi_6m` —que es el único que
el proyecto usa desde D-32.**

## Por qué eso es un contrato que se contradice a sí mismo

**D-32 cambió la escala del SPI de 3 a 6 meses**, y no por gusto:
`comparar_escalas_spi.py` contrastó las tres contra el catálogo de eventos y el
SPI-3 dio **0 de 7** mientras que el SPI-6 dio **7 de 7**. El etiquetado, D-34, la
tabla de resultados y el documento IEEE hablan todos de SPI-6.

El contrato se quedó en la escala anterior. Hoy, **la única escala que el proyecto
considera válida es la única que el contrato no puede expresar.**

## El cambio pedido

**1.** Agregar un campo a `IndiceDerivado` en `contratos/esquemas.py`:

```python
spi_6m: float | None = None
```

**2.** Subir `VERSION_CONTRATOS` de `1.4.0` a `1.5.0` en `contratos/__init__.py`,
con su línea en el registro de versiones del encabezado.

**Los dos campos viejos no se tocan.** `spi_1m` y `spi_3m` se quedan: no estorban,
y borrarlos sería un cambio incompatible para ganar nada.

## Sobre el salto de versión: ya estaba decidido, y ocurre una sola vez

**D-50 ya anunció «Contratos 1.4.0 → 1.5.0 (aditivo)»** para el `Pronostico` que
trae H15.0. Es el mismo salto. Esta solicitud lo ejecuta ahora porque H14.5 llega
primero; cuando H15.0 agregue `Pronostico` **no hace falta otro salto**, porque
también es aditivo y cabe dentro de 1.5.0.

Lo que **no** estaba decidido en ningún lado es `spi_6m`, y por eso existe esta
solicitud.

## Es una adición, no una modificación

Ningún campo existente cambia de nombre, de tipo ni de significado. **Nada de lo
que hoy valida deja de validar**, y un cliente que no conozca el campo nuevo sigue
funcionando: es `float | None` con omisión por defecto.

Ese es exactamente el criterio con el que SC-10 admitió un valor nuevo en el enum
`Algoritmo`.

## Quién queda afectado

`contratos/` afecta a los cuatro.

| Quién | Qué le toca |
|---|---|
| Alejandro | `contratos/esquemas.py`, `contratos/__init__.py`, y el resto de la cadena de H14.5 |
| César | Nada que hacer. `backend/api/` recibe la lectura y la ruta, escritas por el PM bajo la excepción acotada de `07-propiedad-archivos.md` y declaradas en el PR |
| Luna, Ávril | Nada: no consumen `IndiceDerivado` |

## Lo que la SC **no** autoriza

- **No crea la tabla `analitico.indice`.** D-53 decidió que el SPI-6 se calcula al
  pedirlo. `guardar_indices` sigue lanzando `TablaPendiente`.
- **No cambia la escala del SPI.** D-32 sigue vigente; esto solo le da al contrato
  la forma de expresarla.
- **No le da a la sequía nivel ni probabilidad.** D-34 sigue en pie: la tarjeta
  dice un hecho medido, no una estimación.
- **No toca `Riesgo`, `MedicionDiaria` ni ningún otro esquema.**
- **No borra `spi_1m` ni `spi_3m`.**

## Cómo se comprueba que entró bien

1. `python -m contratos.verificar` en verde. El número de comprobaciones sube y
   `verificar_documentacion` lo cuenta.
2. `verificar_documentacion.py` reporta **versión de contratos: 1.5.0**, y las
   afirmaciones de `docs/10-manual-tecnico.md` y `docs/17-documento-tecnico.md`
   coinciden. **La medición de H11.6 que dice `contratos 1.4.0` NO se toca**: es el
   registro de lo que producción respondió el 2026-09-14, no una afirmación sobre
   el presente.
3. `/salud` publicado devuelve `version_contratos: "1.5.0"` después del despliegue.
4. Un `IndiceDerivado` construido sin `spi_6m` sigue validando.

## El riesgo, dicho

El riesgo de agregar un campo a un contrato congelado es que se lea como permiso
para tratarlo como abierto. Se acota igual que en SC-10: **este campo entra porque
el proyecto ya decidió su escala hace dos semanas y el contrato se quedó atrás.**
No se agrega un concepto nuevo: se corrige una contradicción entre D-32 y
`esquemas.py`.

El otro riesgo es de secuencia: subir la versión antes de que `Pronostico` exista
deja a 1.5.0 significando dos cosas distintas según el día. Se acota declarándolo
acá y en D-50: **1.5.0 es «`IndiceDerivado` gana `spi_6m`» desde hoy, y va a
significar además «existe `Pronostico`» cuando H15.0 entre.** Las dos son
adiciones, así que ningún cliente se rompe en el medio.
