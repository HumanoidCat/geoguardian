"""Intervalo de confianza para una proporcion. Metodo de Wilson.

===========================================================================
POR QUE EXISTE, Y POR QUE NO ES EL INTERVALO QUE UNO ESCRIBE DE MEMORIA
===========================================================================

El documento reportaba proporciones como valores puntuales: «64,7 % de
cobertura» sobre **34 eventos**, «13,7 % de tasa base». Con `n = 34` el
intervalo es ancho, y sin el **no se puede afirmar que 64,7 % y 13,7 % son
distintos**: se estan mostrando dos puntos y dejando que el lector suponga.

El intervalo que casi todo el mundo escribe de memoria es el de Wald,

    p +/- z * sqrt(p (1 - p) / n)

y Brown, Cai y DasGupta (2001) muestran que su cobertura real es erratica de
forma **mucho mas persistente** de lo que suele reconocerse, y que las reglas
de bolsillo del tipo «sirve si n p > 5» son enganosas. Recomiendan el
intervalo de **Wilson** para `n` pequeno, que es exactamente nuestro caso.

Ademas, Wald hace dos cosas inaceptables aqui:

    p = 0  ->  intervalo [0, 0]     y nosotros tenemos 0 de 7 en sequia
    p = 1  ->  intervalo [1, 1]

es decir, declara certeza absoluta justo donde menos informacion hay. Wilson
no: con 0 de 7 devuelve un limite superior cercano al 35 %, que es la lectura
honesta.

===========================================================================
LO QUE ESTE MODULO **NO** HACE
===========================================================================

No decide si dos proporciones son distintas. Devuelve intervalos; la regla de
lectura vive donde se usa, y es la misma disciplina del «empate tecnico» de
`comparar.py`: **si los intervalos se solapan, no se declara diferencia**.

Tampoco corrige por comparaciones multiples ni por dependencia entre las
observaciones. Los dias de un mismo distrito no son independientes -el SPI de
un mes es constante dentro del mes- asi que estos intervalos son, si acaso,
**optimistas**. Se declara y no se disimula.

Referencia:
    L. D. Brown, T. T. Cai y A. DasGupta, «Interval estimation for a binomial
    proportion», Statistical Science, vol. 16, no. 2, pp. 101-133, 2001.
    DOI 10.1214/ss/1009213286.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

#: Cuantil normal para el nivel de confianza. 1,959964 es el de dos colas al
#: 95 %, escrito con los decimales que hacen falta para que el resultado no
#: dependa de cuantos se escribieron.
Z_95 = 1.959963984540054


@dataclass(frozen=True)
class Intervalo:
    """Una proporcion con su intervalo. `exitos` y `total` se conservan a proposito.

    Se conservan porque un intervalo sin su `n` no se puede interpretar ni
    recalcular, y porque la pregunta «¿sobre cuantos casos?» es la primera que
    hace quien lee un porcentaje.
    """

    exitos: int
    total: int
    punto: float
    inferior: float
    superior: float

    @property
    def amplitud(self) -> float:
        return self.superior - self.inferior

    def solapa(self, otro: Intervalo) -> bool:
        """Si dos intervalos se solapan, **no se declara diferencia**.

        Es un criterio conservador y se sabe: dos intervalos pueden solaparse y
        la diferencia ser significativa en una prueba directa. Se prefiere
        equivocarse hacia no afirmar.
        """
        return self.inferior <= otro.superior and otro.inferior <= self.superior

    def __str__(self) -> str:
        return f"{self.punto:.1%} [{self.inferior:.1%}, {self.superior:.1%}] n={self.total}"


def wilson(exitos: int, total: int, z: float = Z_95) -> Intervalo:
    """Intervalo de Wilson para `exitos` de `total`.

    Args:
        exitos: numero de casos favorables. No negativo, y no mayor que `total`.
        total: tamano de la muestra.
        z: cuantil normal. Por omision el del 95 % a dos colas.

    Raises:
        ValueError: si los argumentos no describen una proporcion.

    El caso `total == 0` **no** devuelve [0, 1] en silencio: no hay muestra, y
    fingir un intervalo sobre ninguna observacion es peor que fallar.
    """
    if total <= 0:
        raise ValueError("no hay intervalo sobre cero observaciones; el llamador debe declararlo")
    if not 0 <= exitos <= total:
        raise ValueError(f"exitos={exitos} fuera de [0, {total}]")

    p = exitos / total
    z2 = z * z
    denominador = 1 + z2 / total
    centro = (p + z2 / (2 * total)) / denominador
    margen = (z / denominador) * math.sqrt(p * (1 - p) / total + z2 / (4 * total * total))

    # El acotado NO es cosmetico. En coma flotante, con p = 0 la formula
    # devuelve 2,8e-17 en vez de 0, y entonces `inferior > punto`: la
    # estimacion puntual queda **fuera de su propio intervalo**. Lo encontro
    # `test_el_punto_siempre_cae_dentro`, y el caso p = 0 es el real: la sequia
    # dio 0 de 7.
    #
    # Se acota contra `p` ademas de contra [0, 1], porque la propiedad que hay
    # que preservar es que el punto caiga dentro, y esa es la que se rompe.
    return Intervalo(
        exitos=exitos,
        total=total,
        punto=p,
        inferior=min(p, max(0.0, centro - margen)),
        superior=max(p, min(1.0, centro + margen)),
    )


def realce_con_intervalo(cobertura: Intervalo, tasa_base: Intervalo) -> tuple[float, float, float]:
    """Realce puntual y su rango, propagando los dos intervalos por los extremos.

    El realce es `cobertura / tasa_base`. Su rango se obtiene combinando los
    extremos que lo hacen mayor y menor, **no** por propagacion de errores:
    es un cociente de dos proporciones pequenas y la aproximacion lineal ahi
    no vale.

    Es un rango conservador -mas ancho que el intervalo de confianza exacto
    del cociente- y por eso sirve para lo unico que se usa: comprobar si el
    **1,0 esta dentro**. Si lo esta, el etiquetado no distingue y no se afirma
    que distinga.
    """
    if tasa_base.punto <= 0:
        raise ValueError("tasa base nula: el realce no esta definido")
    punto = cobertura.punto / tasa_base.punto
    menor = cobertura.inferior / tasa_base.superior if tasa_base.superior > 0 else 0.0
    mayor = cobertura.superior / tasa_base.inferior if tasa_base.inferior > 0 else float("inf")
    return punto, menor, mayor
