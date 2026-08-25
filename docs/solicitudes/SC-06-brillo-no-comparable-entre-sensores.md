# Solicitud de cambio de contrato · `brillo_k` no es comparable entre sensores

**ID.** SC-06
**Contrato afectado.** `contratos/esquemas.py`, docstring de `FocoCalor`
**Solicitante.** César, desde H1.2
**Lo detecta.** César, al preparar la migración 005
**Módulos que lo consumen.** `backend/etl` (H1.2), `backend/modelado` (H3.0 a
H3.8), `backend/calidad`
**Fecha.** 2026-08-24
**Estado.** Propuesta. Aprueba Alejandro como dueño de `contratos/`.
**Versión de contratos.** **Ninguna.** Se mantiene en v1.4.0: no cambia el
esquema, solo lo que declara.

---

## Lo que se detectó

El contrato declara `brillo_k` así, sin una sola línea de advertencia:

```python
class FocoCalor(_Base):
    confianza: int | None = Field(default=None, ge=0, le=100)
    brillo_k: float | None = None
    satelite: str | None = None
```

César verificó el emparejamiento de bandas contra las dos fuentes oficiales, en
vez de darlo por bueno:

| | MODIS | VIIRS S-NPP |
|---|---|---|
| Infrarrojo medio | `brightness` · canal 21/22 · **3,9 a 4 µm** | `bright_ti4` · canal I-4 · **3,55 a 3,93 µm** |
| Infrarrojo largo | `bright_t31` · canal 31 · **11 µm** | `bright_ti5` · canal I-5 |

**Y declaró el límite de su verificación:** la longitud de onda del I-5 no la
encontró publicada en la documentación de FIRMS que pudo leer. Ese emparejamiento
va por nombre y por función, no comprobado.

**El emparejar la banda no vuelve comparables los valores.**

La temperatura de brillo está **integrada sobre el píxel**, y los píxeles no
miden lo mismo: **1 km en MODIS contra 375 m en VIIRS**. El mismo incendio ocupa
una fracción mucho mayor de un píxel de 375 m, así que **lee más caliente en
VIIRS aunque el fuego sea idéntico**.

Es el salto de 2,1× de **D-25** otra vez, pero en la magnitud en lugar de en la
frecuencia. D-25 declaró que la serie no es homogénea en **cuántos** focos hay.
Nadie declaró que tampoco lo es en **qué tan calientes** se reportan.

## Qué se pide

**Que el contrato lo diga.** Un modelo entrenado sobre las dos eras con `brillo_k`
como una columna continua sin advertencia **aprende el cambio de sensor** y lo
llama señal.

Se agrega al docstring de `FocoCalor`:

> `brillo_k` **no es comparable entre sensores.** Es temperatura de brillo
> integrada sobre el píxel, y el píxel mide 1 km en MODIS y 375 m en VIIRS: el
> mismo fuego lee más caliente en VIIRS. Quien use esta columna sobre la serie
> completa tiene que meter `satelite` como covariable o restringir la serie a una
> era. Ver **D-25** y **SC-06**.

Y `confianza` gana su procedencia, que César encontró publicada:

> Los cortes son los de la **Tabla 10** del *MODIS Collection 6 Active Fire
> Product User's Guide, Revision C* (Giglio, Schroeder, Hall y Justice,
> University of Maryland, diciembre de 2020): `low` por debajo de 30 %,
> `nominal` entre 30 y 80 %, `high` de 80 % en adelante. **No es criterio de
> equipo, es la clasificación del proveedor.**

## Por qué no sube la versión

No cambia ningún campo, ningún tipo, ninguna validación. **El esquema es idéntico
antes y después.** Lo que cambia es lo que el contrato declara sobre un campo que
ya existía.

Subir la versión obligaría a los cuatro módulos que la consumen a revisar un
cambio que no los rompe. La versión señala incompatibilidad, no actividad.

## Por qué NO se agrega un campo nuevo

César menciona `banda_origen`, que **no existe en el contrato**: es una columna
que planea para la migración 005 de su esquema.

No hace falta subirla al contrato, y él mismo da la razón: *"`banda_origen` no
alcanza para eso: dice de qué banda vino, no que no se puedan comparar."*

**El campo que ya carga la era es `satelite`.** Lo que faltaba no era un dato más
sino una advertencia, y una advertencia va en el docstring, no en un campo.

Si la migración 005 quiere `banda_origen` para su propia trazabilidad, es de su
esquema y no del contrato compartido.

## Lo que no se pide

**No se filtra por confianza.** César decidió guardar los 242 focos sin filtrar,
con la categoría en su columna, aunque el manual del proveedor permita descartar
los de confianza baja —serían 6 de 242, el 2,5 %—.

Es la decisión correcta y por el motivo correcto, en sus palabras: *"cambia el
conteo que ya circula en el informe de R16 [...] filtrar después es una consulta;
recargar no."*

## Cómo se comprueba

No hay comprobación automática posible: es una advertencia dirigida a quien
escriba el modelado, no una propiedad del dato.

**Donde sí se cobra es en H3.0.** El etiquetado tiene que declarar
explícitamente, en su evidencia, qué hizo con `brillo_k`: si lo usa con
`satelite` como covariable, si restringe la era, o si no lo usa. Entra como
criterio de aceptación de esa historia.

## Consecuencias

**Lo que se gana.** La tercera heterogeneidad de FIRMS queda declarada antes de
que exista un modelo que la sufra. Las dos anteriores —el salto de frecuencia en
D-25 y las eras de sensor— se descubrieron midiendo; esta se declara antes.

**Lo que se pierde.** Nada. Es documentación.

**Lo que queda pendiente.** La longitud de onda del canal I-5, que César no pudo
verificar. Va a las limitaciones del documento IEEE con el alcance declarado: el
emparejamiento con `bright_t31` se sostiene por nombre y función, no por una
fuente leída.
