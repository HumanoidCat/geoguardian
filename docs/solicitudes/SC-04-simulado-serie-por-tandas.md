# Solicitud de cambio de contrato · el resto de `RepositorioSimulado`

**ID.** SC-04
**Contrato afectado.** `contratos/simulados/datos.py`: `obtener_mediciones`,
`contar_focos` y `obtener_indices`
**Solicitante.** Alejandro
**Detectado por.** César, al revisar y aprobar SC-03
**Módulos que lo consumen.** `backend/api` (H6.1), `backend/senales` (H2.5 de
Luna), `backend/modelado` (H3.0), `backend/calidad`
**Fecha.** 2026-08-20
**Estado.** Pendiente de aprobación

---

## El hallazgo, y de quién es

SC-03 arregló `obtener_riesgo`. Al revisarla, César comprobó lo que yo no
comprobé: **si el mismo defecto estaba en otro lado.** Lo estaba.

> *"`obtener_riesgo` no es el único método que sortea contra `self._rnd`.
> `obtener_mediciones` también, y está expuesto hoy en
> `GET /distritos/{codigo}/mediciones`."*

Y tiene una forma peor que la del riesgo. Medido el 20 de agosto:

```
Rango A: 1 al 5 de agosto.   Rango B: 3 al 7 de agosto.
temp_max de los dias comunes:

  2026-08-03:  A = 31.2   B = 30.6   DISTINTO
  2026-08-04:  A = 27.2   B = 27.4   DISTINTO
  2026-08-05:  A = 31.1   B = 27.8   DISTINTO
```

**Un mismo día tiene dos temperaturas distintas según por dónde se lo pida. Una
serie no se puede pedir en tandas.**

## Y son cuatro métodos, no dos

Al ir a arreglarlo busqué todos los que usan el generador compartido, en vez de
arreglar el que me habían señalado. Aparecieron dos más:

| Método | Expuesto en | Efecto |
|---|---|---|
| `obtener_mediciones` | `GET /distritos/{codigo}/mediciones` | La serie cambia según el rango pedido |
| `contar_focos` | Todavía no | Cada llamada devuelve otro número |
| `obtener_indices` | Todavía no | Cada llamada devuelve otra serie |
| `obtener_riesgo` | `GET /riesgos` | **Ya corregido en SC-03** |

Es la misma lección de esta ronda, aplicada a mí: **arreglar el caso señalado no
es arreglar el defecto.** SC-03 corrigió un síntoma y declaró resuelto el
problema.

## Un segundo defecto dentro del primero, también de César

> *"los huecos salen de `i % 20 == 7`, que depende de la posición dentro del rango
> pedido, no de la fecha."*

Comprobado:

```
huecos del 1 de enero al 1 de marzo, en el tramo comun:  2026-01-28, 2026-02-17
huecos del 15 de enero al 1 de marzo:                    2026-01-22, 2026-02-11
```

**Cuatro fechas distintas para el mismo tramo de calendario.** Un día era hueco o
no según dónde cayera en la consulta.

## A quién le pega

- **H2.5, de Luna.** Trabaja sobre ventanas móviles. Dos ventanas solapadas
  habrían dado valores distintos para los mismos días, y el resultado habría
  parecido un defecto de su algoritmo.
- **H3.0, mío.** El etiquetado de incendio usa ventanas de 7 días sobre
  `contar_focos`. Dos ventanas contiguas no sumaban la ventana completa.
- **Cualquier prueba de H1.4** que compare dos consultas.

---

## Cambio propuesto

**Ninguna firma cambia. Ningún esquema cambia.** Cambian las garantías.

Una función que arma un generador determinista desde lo que identifica al dato:

```python
def _sorteo(*partes: object) -> random.Random:
    return random.Random("|".join([str(SEMILLA), *(str(p) for p in partes)]))
```

Y cada método la usa con lo que corresponde:

- **`obtener_mediciones`** siembra **por día**, con `(codigo_distrito, fecha)`. Y
  el hueco se decide desde la fecha: `fecha.toordinal() % 20 == 7`.
- **`contar_focos`** cuenta día por día y suma, en vez de sortear un número para
  el rango entero. Así **es aditivo**: dos ventanas contiguas suman la ventana
  completa, que es como se comporta una consulta sobre filas.
- **`obtener_indices`** siembra por fecha.
- **`obtener_riesgo`** pasa a usar la misma función, sin cambiar su
  comportamiento.

## Sobre `contar_focos` y el cero

Se sortea 0 o 1 por día. Un día sin detección es un **cero**, no un hueco: es la
distinción que D-22 usó para no cerrar H1.4, y ahora el simulado la respeta.

## Versión

**v1.3.2.** Cambio de comportamiento de un simulado, sin cambio de forma ni de
firma. Ningún consumidor tiene que adaptarse.

---

## Cómo se comprueba que quedó

Cuatro comprobaciones nuevas en `contratos/verificar.py`, y las cuatro fallaban
antes:

- Dos rangos que se solapan coinciden en los días comunes.
- Un día es hueco por su fecha, no por su posición en el rango.
- Contar focos en dos tramos da lo mismo que en uno.
- Los índices derivados coinciden entre instancias.

Total del verificador: **40 comprobaciones**.

## Lo que queda pendiente, y es de César

`obtener_mediciones` está expuesto en `GET /distritos/{codigo}/mediciones`. La
comprobación de que **dos llamadas iguales al endpoint devuelven lo mismo**
corresponde al verificador de la API, no al de contratos. César la incorpora en
**H6.2**, donde además pasa a ser una propiedad real del repositorio y no del
doble.
