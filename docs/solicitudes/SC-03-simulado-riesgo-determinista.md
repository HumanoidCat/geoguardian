# Solicitud de cambio de contrato · `RepositorioSimulado.obtener_riesgo`

**ID.** SC-03
**Contrato afectado.** `contratos/simulados/datos.py`, método `obtener_riesgo`
**Solicitante.** Alejandro, desde H6.6
**Módulos que lo consumen.** `backend/api` (H6.1, de César, por
`dependencias.py`), `frontend` (H5.3 y H5.4, de Avril, a través de la API),
`frontend/herramientas/exportar_simulados.py`
**Fecha.** 2026-08-20
**Estado.** **Aprobada** por César el 2026-08-20. Integrada en contratos **v1.3.1**.
Ver la resolución al final.

> Aprueban: Alejandro por `contratos/`, y César como dueño del único módulo que
> hoy instancia el repositorio. Avril queda notificada porque el cambio corrige
> el dato que alimenta su mapa de calor.

---

## Cambio propuesto

Que `obtener_riesgo` sea **determinista en sus argumentos** y **coherente con
D-21**:

```python
def obtener_riesgo(
    self, codigo_distrito: str, fecha: date, tipo_evento: TipoEvento
) -> Riesgo | None:
    sorteo = random.Random(f"{SEMILLA}|{codigo_distrito}|{fecha}|{tipo_evento.value}")
    probabilidad = round(sorteo.uniform(0.05, 0.95), 2)
    return Riesgo(
        ...,
        nivel=_nivel_desde(probabilidad),
        probabilidad=probabilidad,
    )
```

La firma **no cambia**. El tipo de retorno **no cambia**. Ninguna llamada
existente se rompe. Lo que cambia es qué valores devuelve y con qué garantías.

Las dos garantías nuevas:

1. **Idempotencia.** La misma consulta devuelve siempre lo mismo, dentro de un
   proceso y entre procesos distintos.
2. **Monotonía.** `nivel` se **deriva** de `probabilidad` en vez de sortearse
   aparte. Una probabilidad mayor nunca produce un nivel menor.

---

## Defecto 1 · La misma consulta devuelve cosas distintas

Tres peticiones idénticas a `GET /riesgos?fecha=2026-08-16&tipo_evento=sequia`,
medidas el 20 de agosto contra la API de H6.1:

| Intento | 50801 | 50802 | 50803 |
|---|---|---|---|
| 1 | bajo · 0,46 | alto · 0,53 | medio · 0,79 |
| 2 | alto · 0,70 | bajo · 0,90 | alto · 0,75 |
| 3 | medio · 0,56 | alto · 0,73 | bajo · 0,64 |

La causa es que `obtener_riesgo` sortea contra `self._rnd`, un generador **con
estado** que avanza en cada llamada. La instancia se cachea una vez por proceso,
que es lo correcto y está bien razonado en `backend/api/dependencias.py`; el
efecto secundario es que el generador nunca vuelve al principio.

**Por qué hay que arreglarlo y no convivir con ello.**

El repositorio de H6.2 va a ser determinista **porque lee filas guardadas de
PostgreSQL**. Un doble que no cumple la propiedad por la que se lo puede poner en
lugar del original no es un doble: es otra cosa que se le parece en la forma.

> **Corrección del 20 de agosto, aportada por César al aprobar esta solicitud.**
> Este párrafo decía *"GET es idempotente por definición"*, y es falso. La
> idempotencia de HTTP restringe el **efecto sobre el servidor**, no la
> representación devuelta: MDN lo dice explícitamente —*"The response returned by
> each request may differ"*—. Un `GET /hora-actual` es idempotente y responde algo
> distinto cada vez, y el simulado viejo no violaba ninguna regla de HTTP.
>
> El argumento de sustituibilidad, que ya estaba, es el correcto y además el más
> fuerte: no depende del protocolo sino de qué es un repositorio. Se corrige acá
> porque este documento y el docstring del simulado son lo que va a leer quien
> toque el código dentro de dos meses.

La primera línea de `contratos/simulados/datos.py` dice:

> *"Repositorio y extractores simulados. Datos deterministas, reproducibles y
> falsos."*

El archivo ya se comprometía a esto. Lo cumple entre construcciones —dos procesos
que instancian y llaman una vez coinciden— y deja de cumplirlo a la segunda
llamada. Por eso nadie lo había notado: el exportador de Avril llama una vez por
evento y escribe. El visor, en cambio, vuelve a preguntar cada vez que el usuario
cambia de evento y regresa.

**Lo que se vería sin el arreglo.** El mapa repinta los ocho distritos con colores
distintos al ir y volver entre eventos. Parecería un defecto de las coropletas de
H5.3, que están bien.

---

## Defecto 2 · Desde D-21, el simulado se contradice

En la tabla de arriba, intento 2: **50802 sale con nivel `bajo` y probabilidad
0,90**.

D-21 fijó que `probabilidad` es **P(nivel = alto)**. Un distrito no puede tener
90 % de probabilidad de ser alto y ser bajo. La fila es imposible bajo el
contrato vigente.

El simulado sortea las dos cosas por separado. Era coherente mientras el contrato
no decía qué magnitud era `probabilidad` —esa ambigüedad es justamente la que D-21
vino a cerrar— y dejó de serlo el 19 de agosto.

**A quién le pega.** Al mapa de calor de H5.4, que interpola `probabilidad`. Sobre
datos incoherentes la superficie no admite ninguna lectura, y su desacuerdo con
las coropletas de al lado parecería un error de interpolación de Avril.

**Qué dice esto de D-21.** Que quedó a medias. Definir el significado de un campo
en el contrato sin arreglar el único productor de ese campo que existe hoy deja
escrita una regla que nada cumple. Es mi omisión, del 19 de agosto.

---

## La derivación propuesta

```python
def _nivel_desde(probabilidad: float) -> NivelRiesgo:
    if probabilidad >= 2 / 3:
        return NivelRiesgo.ALTO
    if probabilidad >= 1 / 3:
        return NivelRiesgo.MEDIO
    return NivelRiesgo.BAJO
```

Los cortes en tercios son **arbitrarios y se declaran como tales**. No pretenden
ser el umbral del modelo real: cuando H3.4 entrene un clasificador, será él quien
decida su nivel y su probabilidad de forma conjunta, y esta función desaparece.

Lo que no es arbitrario es la **monotonía**, y es lo único que el simulado tiene
que garantizar: es la propiedad de la que dependen el mapa de calor de H5.4 y el
semáforo continuo de H7.1.

El rango pasa de `uniform(0.3, 0.95)` a `uniform(0.05, 0.95)` para que los tres
niveles sean alcanzables. Con el rango viejo, `probabilidad ≥ 1/3` casi siempre, y
el nivel `bajo` no aparecería nunca.

---

## Qué no cambia

- La firma, el tipo de retorno y el protocolo `Repositorio`.
- `obtener_riesgos_por_fecha`, que sigue delegando en `obtener_riesgo`.
- Los demás simulados. Solo se toca el riesgo.
- Los datos que salen: siguen siendo **falsos** y siguen declarándose así en
  `/salud`, en la leyenda y en cada archivo exportado.

## Qué sí hay que rehacer

`frontend/public/simulados/riesgos-*.json` se regeneran, porque los valores
cambian. Los produce `exportar_simulados.py`, que es de Avril y no se toca: solo
se vuelve a correr.

## Versión

**v1.3.1.** Es un cambio de comportamiento de un simulado, no de la forma de
ningún esquema ni de ninguna firma. Ningún consumidor tiene que adaptarse.

---

## Cómo se comprueba que quedó

Dos comprobaciones nuevas en `contratos/verificar.py`:

- Llamar `obtener_riesgo` con los mismos argumentos, desde **dos instancias
  distintas**, devuelve el mismo `nivel` y la misma `probabilidad`.
- Para los ocho distritos, los tres eventos y varias fechas: el nivel es
  coherente con la probabilidad según los cortes declarados, y no hay ningún caso
  de nivel bajo con probabilidad alta.

La primera falla hoy. La segunda también.


---

## Resolución

**Aprobada por César el 20 de agosto**, con revisión completa en el PR #133.
Integrada en **contratos v1.3.1**.

Su revisión aportó tres cosas más que la aprobación:

1. **Midió lo que no estaba medido.** Sobre 8 distritos × 3 eventos × 40 fechas,
   **642 de 960 filas eran incoherentes con D-21, el 66,9 %**. No era un caso raro:
   con el nivel sorteado uniforme entre tres valores, acertar el que corresponde a
   la probabilidad tiene probabilidad de un tercio. El peor caso, 50808 con nivel
   bajo y probabilidad 0,95.
2. **Verificó el arreglo ejecutándolo** sobre una copia parcheada, incluido el caso
   entre procesos distintos, lanzando un subproceso.
3. **Corrigió el argumento del GET**, arriba.

Y encontró que **el arreglo estaba incompleto**: `obtener_riesgo` no era el único
método que sorteaba contra el generador compartido. De ahí sale **SC-04**.
