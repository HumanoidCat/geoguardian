# Solicitud de cambio de contrato · `ProcesadorSenales.anomalia`

**ID.** SC-06
**Contrato afectado.** `contratos/senales.py`, metodo `anomalia`
**Solicitante.** Luna, desde H2.4
**Modulos que lo consumen.** `backend/senales` (H2.4, mio), `backend/modelado`
(H7.4 depende de H2.4), `contratos/simulados/senales.py`
**Fecha.** 2026-08-20
**Estado.** Pendiente de aprobacion

*Se toma SC-06 y no SC-05 porque esa quedo asignada al umbral de incendio.*

---

## Cambio propuesto

Es el **mismo cambio que D-19 hizo para `spi`**, aplicado al metodo vecino:

```python
def anomalia(
    self,
    serie: list[float | None],
    normal_por_mes: dict[int, float],
    meses: list[int] | None = None,
) -> list[float | None]:
    ...
```

`meses[i]` es el mes calendario de la posicion `i`, de 1 a 12. Con ese dato, la
normal se elige por el mes real. Sin el, se mantiene el comportamiento actual
—suponer que la serie arranca en enero— y la implementacion **debe advertirlo
por registro**, exactamente como ya hace `spi`.

El parametro va al final y con valor por defecto: **ninguna llamada existente se
rompe**, y el simulado puede aceptarlo e ignorarlo.

---

## Por que no se puede resolver sin cambiar el contrato

El hueco **ya estaba registrado antes de esta historia**, en
`docs/02-contratos.md`:

> *"`ProcesadorSenales.anomalia` no recibe fechas. La firma toma la serie y las
> normales indexadas por mes, pero nada indica a que mes corresponde cada
> posicion. El simulado supone que la serie es mensual y arranca en enero. Si
> esa suposicion no se cumple, el resultado es silenciosamente incorrecto: no
> falla, devuelve numeros equivocados. Corregirlo es agregar las fechas a la
> firma, en la proxima version."*

Lo que aporta H2.4 no es el hallazgo: es **la medicion de cuanto cuesta**.

Y hay un contraste que hace evidente el problema. En el mismo modulo,
`normales_por_mes` **si recibe fechas**, porque no es un metodo del contrato, y
por eso calcula la normal correctamente sin ninguna suposicion. Elegir la normal
correcta es trivial cuando se conoce la fecha. Es exactamente lo que a
`anomalia` le falta.

---

## La medicion

Herramienta: `docs/herramientas/medir_anomalia_desfase.py`. Serie mensual
sintetica de 30 anios con el regimen del Pacifico Norte. Se desfasa el mes de
inicio y se compara la version del contrato contra la que usa el mes real.

    Normal climatologica por mes, en mm:
       1:   7.9   2:   4.9   3:   6.4   4:  27.2   5: 195.8   6: 232.2
       7: 147.5   8: 220.4   9: 305.2  10: 274.3  11: 107.9  12:  26.5

    Error que introduce suponer que la serie arranca en enero

     desfase   err. medio   err. maximo   peor mes
           0          0.0           0.0          1   <- sin desfase
           1         64.2         168.5          5
           2        104.7         247.8         12
           3        130.1         278.7         12
           4        150.3         297.3          1
           5        184.5         300.3          2
           6        199.1         298.8          3
           7        184.5         300.3          9
           8        150.3         297.3          9
           9        130.1         278.7          9
          10        104.7         247.8         10
          11         64.2         168.5          4

    Magnitud tipica de una anomalia real: 48.8 mm

### Lectura

**El dato decisivo esta en la primera fila con desfase.**

Con **un solo mes** de corrimiento, el error medio es **64,2 mm**. La magnitud
tipica de una anomalia real en esta serie es **48,8 mm**.

**El error supera a la señal.** No es que el resultado sea menos preciso: es que
deja de medir lo que dice medir. Con seis meses de desfase el error medio es de
199,1 mm, **cuatro veces** la magnitud de la anomalia que pretende reportar.

El error maximo llega a **300,3 mm**, que es del orden de la normal de octubre
entera. Un octubre normal comparado contra la normal de febrero da una anomalia
de casi +300 mm: el sistema reportaria una anomalia humeda extraordinaria todos
los octubres, y una seca todos los febreros, con datos perfectamente normales.

### Por que es mas grave que el caso de SC-02

En SC-02, el SPI sin `meses` producia un indice **sesgado pero consistente**:
todos los valores estaban mal en la misma direccion y por eso el error era
detectable comparando estaciones.

Aqui no. El error **depende del desfase**, que es un dato externo a la funcion y
que nadie declara. Dos ejecuciones sobre la misma serie cargada desde meses
distintos producen anomalias distintas, y **ninguna de las dos avisa**.

---

## Impacto en cada consumidor

| Consumidor | Impacto |
|---|---|
| `backend/senales` (H2.4, mio) | Ninguno para llamadas existentes. Con `meses` se elige la normal correcta |
| **H7.4** (depende de H2.4) | Es el mas afectado: consumiria anomalias calculadas contra el mes equivocado si la serie no arranca en enero |
| `contratos/simulados/senales.py` | Hay que aceptar el parametro. Puede ignorarlo, pero debe aceptarlo para seguir cumpliendo el protocolo |
| `backend/api`, `frontend` | Ninguno. No llaman a `anomalia` directamente |

---

## Lo que ya esta hecho, y no depende de esta solicitud

H2.4 esta implementada y probada contra la firma actual, con **24 pruebas en
verde**. El calculo de la normal, el tratamiento de huecos y el criterio de que
un mes ausente en `normal_por_mes` produce `None` **no cambian** si se aprueba:
lo unico que cambia es de donde sale el mes de cada posicion.

`anomalia_con_fechas` ya tiene la logica correcta escrita, porque hizo falta
para medir. **Si SC-06 se aprueba, esa funcion desaparece y su cuerpo pasa a
`anomalia`.** El trabajo adicional es de menos de media hora.

---

## Alternativa considerada y descartada

**Dejar la suposicion documentada y no cambiar el contrato**, confiando en que
la carga siempre empiece en enero.

Se descarta por el mismo motivo que en SC-02: la suposicion no se puede
verificar desde dentro de la funcion y su incumplimiento **no produce ningun
sintoma**. Una serie que empiece en otro mes devuelve numeros de aspecto
razonable, del orden de magnitud correcto, y completamente equivocados.

Es la misma familia de la incidencia **I-04**: un dato con forma valida y
contenido falso.

---

## Aprobado por

Pendiente.

## Fecha de aprobacion

Pendiente.
