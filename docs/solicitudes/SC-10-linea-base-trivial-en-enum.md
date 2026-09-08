# SC-10 · Admitir la linea base trivial en el enum `Algoritmo`

| | |
|---|---|
| **Archivo compartido** | `contratos/enums.py` |
| **Pedida por** | Cesar, en el PR #286 (H3.7) |
| **Redactada y aprobada por** | Alejandro, 2026-09-08 |
| **Historia que la origina** | H3.7 · Versionar modelos con metricas y fecha asociadas |
| **Numeracion** | SC-08 la reservo Luna (contrato de bitacora); SC-09 se consumio en la colision de numeracion del 2026-09-02 |

## El problema, en una frase

**El enum `Algoritmo` tiene cuatro valores y ninguno nombra a la linea base
trivial, que `comparar.py` si evalua.** Por eso la tabla `analitico.metrica` que
entra con H3.7 **no puede guardar el piso contra el que se compara todo lo demas.**

## Por que importa, y por que no es cosmetico

**D-39** decide quien escribe en `analitico.riesgo` con esta regla: gana el que
supere a la linea base fuera del ruido; si ninguno, el mas simple dentro del
ruido; la trivial nunca escribe; **y nadie que este por debajo del piso trivial**.

Ese piso es parte de la decision. Sin poder guardarlo, `analitico.metrica`
almacena **las comparaciones pero no el numero contra el que se comparan**, y la
historia de versiones queda sin el unico valor que dice si un modelo esta
siquiera por encima de adivinar.

Es tambien el hallazgo de **I-34**: en incendio el bosque de fabrica venia
degenerado **por debajo del piso trivial** (0,494), y por eso escribe la regresion
logistica. Ese 0,494 es exactamente el tipo de numero que hoy no se puede
versionar.

## Que hizo H3.7 mientras tanto, y por que esta bien

La migracion **018** lo **impide con un `CHECK`** en vez de dejar que reviente al
leer, y lo deja escrito en el propio DDL:

> **LA LINEA BASE TRIVIAL NO ENTRA, Y NO ES UN OLVIDO.** [...] Admitirlo exige
> cambiar `contratos/`, que es archivo compartido y necesita solicitud aprobada.
> Queda declarado, no resuelto por la puerta de atras.

Es la decision correcta: un valor que el contrato no admite no entra en silencio,
y la consecuencia queda declarada en vez de escondida.

## El cambio pedido

Agregar un valor al enum `Algoritmo` de `contratos/enums.py` para la linea base
trivial, con el nombre que **ya usa `comparar.py`** (`REFERENCIA = "trivial"`), y
ampliar el `CHECK` de `analitico.metrica` para admitirlo.

## Quien queda afectado

`contratos/` afecta a los cuatro. **Es una adicion, no una modificacion**: ningun
valor existente cambia de nombre ni de significado, asi que nada de lo que hoy
valida deja de validar.

| Quien | Que le toca |
|---|---|
| Cesar | `basedatos/`, el `CHECK` de la 018 y `verificar_h3_7` |
| Alejandro | `contratos/enums.py`, `backend/modelado/comparar.py` |
| Luna, Avril | nada: no consumen ese enum |

## Lo que la SC **no** autoriza

- **No cambia D-39** ni quien escribe `analitico.riesgo`. Eso es H3.8.
- **No cambia el contrato de la API** ni ninguna respuesta publicada.
- **No toca `contratos/simulados/`.**

## Como se comprueba que entro bien

1. `python -m contratos.verificar` en verde.
2. `python -m basedatos.verificar_h3_7` guarda una fila con el algoritmo trivial y
   la lee de vuelta.
3. `comparar.py --guardar` persiste las lineas base **incluida la trivial**, y el
   piso de I-34 queda con fila propia.

## El riesgo, dicho

El riesgo de una adicion a un enum congelado es que alguien lo lea como permiso
para tratarlo como abierto. Se acota aqui: **este valor entra porque ya existia en
el codigo que mide** —`REFERENCIA = "trivial"` en `comparar.py`— y el enum se
habia escrito sin el. No se agrega un concepto nuevo: se corrige una omision entre
dos archivos que ya se contradecian.
