# Velocidad y capacidad

**Acción 12.3 de la retrospectiva** · Responsable: Alejandro
**Medido el 16 de agosto de 2026, al cierre del Sprint 0**

Este documento se actualiza al cierre de cada sprint. Todas las cifras salen de
`docs/backlog.csv` y del estado de `docs/tareas/` en el último commit del sprint,
no de una estimación posterior.

---

## 1. Sprint 0 · semanas 2 y 3

| | Historias | Puntos | Horas estimadas |
|---|---|---|---|
| Comprometido | 11 | 54 | 83,0 |
| Entregado | 8 | 43 | 67,6 |
| Sin terminar | 3 | 11 | 15,4 |

**Velocidad: 43 puntos en dos semanas, 21,5 puntos por semana.**

**Cumplimiento del compromiso: 80 % de los puntos, 81 % de las horas.**

No se arrastró ninguna historia de otro sprint: todo lo entregado estaba
planificado para el Sprint 0.

### Qué quedó sin cerrar

| Historia | Responsable | Puntos | Por qué |
|---|---|---|---|
| H1.1 | César | 5 | Bloqueada. La fuente climática no diferenciaba entre distritos (I-05) |
| H1.2 | César | 3 | Depende de H1.1 |
| H5.1 | Avril | 3 | Se cerró tres días después, el 16 de agosto |

Dos de las tres son la misma causa: el bloqueo de la fuente de datos. La tercera
se cerró apenas fuera del corte.

---

## 2. Lo que NO se puede calcular, y por qué

El roadmap declara un modelo de esfuerzo con tres tasas de horas por punto según
qué tan acelerable es el trabajo: 0,8 para lo que la asistencia de IA acelera
mucho, 1,3 para lo parcial y 2,2 para lo que no acelera nada.

**Ese modelo todavía no se puede recalibrar, pero ya no por falta absoluta de
datos: hay dos mediciones y hacen falta más.**

### Las dos primeras mediciones reales

César las reportó al grupo el 19 de agosto, por iniciativa propia. Son el primer
cumplimiento de la acción **12.4**.

| Historia | Pts | h estimadas | h reales | h/pt estimada | h/pt real | Desvío |
|---|---|---|---|---|---|---|
| H1.8 · Roles de mínimo privilegio | 5 | 4,8 | **4h40** | 0,96 | 0,93 | −3 % |
| H6.1 · API REST con OpenAPI | 5 | 4,8 | **2h15** | 0,96 | 0,45 | **−53 %** |

**Mismo tamaño, misma estimación, y una tardó menos de la mitad que la otra.**

### Lo que ese par sugiere, y lo que no

La lectura la puso César y es la parte que importa: la diferencia no fue el tamaño
ni el tipo de trabajo, sino que **H6.1 se apoyaba en contratos ya congelados y H1.8
tocaba infraestructura nueva**.

El modelo del roadmap clasifica por *acelerabilidad* —cuánto acelera la asistencia
de IA ese tipo de trabajo— y por esa vara las dos son "alta", 0,8 h/pt. Salieron a
0,93 y 0,45. **La variable que las separó no está en el modelo.**

Si el par se sostiene, el modelo necesita un segundo eje: **si la interfaz de la
que depende la historia ya existe y está congelada**. H6.1 encontró que
`RepositorioSimulado` ya cumplía el protocolo entero y la historia se encogió sola;
H1.8 tuvo que construir el terreno sobre el que trabajaba.

**Lo que estas dos mediciones NO permiten.** Son dos historias, las dos de 5
puntos, las dos de la misma persona, las dos estimadas a la misma tasa. No se
recalibran tres tasas con eso, y forzarlo daría un modelo que parece medido y no lo
está. Lo único que ya está descartado es la afirmación anterior de este documento
—que nadie había registrado horas— que dejó de ser cierta el 19 de agosto.

### Las cuatro historias de frontend anteriores a H7.1 no tienen horas, y es a propósito

Avril planteó el 20 de agosto si convenía estimarlas retrospectivamente. **Se
decidió que no.**

El estimado habría quedado **anclado a la estimación original del backlog**, que
ella conoce, y habría producido razones cercanas a 1,0 por construcción. Con dos
mediciones reales y cinco estimados de ese tipo, el promedio miente más que con las
dos mediciones solas: el 0,47 de H6.1 —el único dato que se aleja y por lo tanto el
único que enseña algo— quedaría diluido hasta parecer un caso raro.

Tres de esas cuatro historias, además, se estimaron con la misma tasa: H5.1 a 0,97,
H5.2 a 0,96 y H5.3 a 0,96 h/pt. Un estimado anclado ahí solo puede confirmar lo que
ya supuso quien armó el backlog.

**Se declara la ausencia en lugar de rellenarla.** Es D-07 aplicado a la medición
del propio proceso: un dato que no se pudo obtener no se sustituye por uno
plausible.

Lo que sí se pidió, y no es una medición: **una línea por historia diciendo si se
sintió más corta o más larga de lo estimado, y por qué.** Nombrar la variable vale
más que inventar el número, que es lo que aportó la lectura de César sobre las
interfaces congeladas.

### Qué falta

Que las otras tres personas registren, **una línea en el cuerpo del Pull Request**:

    Horas reales: 6,5 (estimadas 7,8)

Con una decena de mediciones repartidas entre las tres tasas se puede contrastar y
ajustar la planificación de los sprints 3 y 4 con datos propios. Conviene además
anotar si la historia dependía de algo ya congelado, que es la variable que este
par señaló.

Mientras tanto, la métrica que sí se sostiene es el **throughput en puntos**, que
no depende de que nadie apunte nada.

---

## 3. Proyección, con la velocidad medida

| | |
|---|---|
| Puntos pendientes al 16 de agosto | 374 |
| Velocidad medida en el Sprint 0 | 21,5 puntos por semana |
| Semanas que harían falta a esa velocidad | 17 |
| Semanas disponibles hasta la semana 12 | 5 |
| **Velocidad necesaria** | **75 puntos por semana** |
| **Multiplicador respecto del Sprint 0** | **3,5×** |

Ese es el número contra el que hay que medirse cada semana. No es una predicción:
es la meta que el plan actual exige, y sirve para saber a mitad de camino si el
ritmo alcanza, en vez de descubrirlo en la semana 11.

### Cómo leer este número sin engañarse

La velocidad del Sprint 0 está medida sobre un sprint atípico y probablemente
subestima lo que el equipo puede hacer ahora. Tres razones concretas:

1. **El Sprint 0 fue de arranque.** Instalar el entorno, aprender el flujo de
   trabajo y congelar los contratos son costos que se pagan una sola vez. La
   incidencia I-01 —Docker sin instalar— es de ese tipo.
2. **Los contratos y los simulados ya existen.** Cuando se midió esa velocidad, el
   equipo no podía trabajar en paralelo sobre módulos que aún no tenían interfaz
   acordada. Ahora sí, y los seis contratos tienen simulado desde el 16 de agosto.
3. **Dos de las tres historias sin cerrar estaban bloqueadas por un hallazgo
   externo**, no por falta de capacidad.

Aun así, 3,5× es un salto grande y conviene medirlo al cierre del Sprint 1, que es
la primera oportunidad de confirmar si la aceleración es real. Si al cerrar el
Sprint 1 la velocidad no subió al menos al doble, la proyección no se sostiene y
hay que volver a mirar el plan.

---

## 4. Sprint 1 · lectura parcial del 18 de agosto

**El Sprint 1 no esta cerrado.** Va por el **dia 5 de 14**. Esto es una lectura, no
un cierre, y se recalcula al terminar.

### Produccion del periodo, del 14 al 18 de agosto

| Origen | Historias | Puntos |
|---|---|---|
| Comprometido en el Sprint 1, entregado | 4 | 25 |
| Adelantado del Sprint 2 | 3 | 13 |
| Arrastre del Sprint 0, cerrado ahora | 1 | 3 |
| **Total del periodo** | **8** | **41** |

Comprometido en el Sprint 1: **15 historias, 74 puntos, 107,3 h**. Entregado del
compromiso: 25 puntos, un **34 %**, en el dia 5 de 14. Va en linea.

### El detalle, por dia

| Fecha | Historia | Quien | Puntos |
|---|---|---|---|
| 15 ago | H5.1 · Mapa del canton (S0) | Avril | 3 |
| 16 ago | H13.1 · Actas de ceremonias | Alejandro | 5 |
| 17 ago | H5.3 · Coropletas de riesgo | Avril | 7 |
| 18 ago | H4.3 · Catalogo de eventos historicos | Luna | 8 |
| 18 ago | H10.5b · Estado del arte de Costa Rica | Luna | 5 |
| 18 ago | H2.1 · Filtrado de ruido (S2) | Luna | 3 |
| 18 ago | H2.3 · SPI (S2) | Luna | 5 |
| 18 ago | H2.7 · Percentiles (S2) | Luna | 5 |

### Velocidad

**41 puntos en cinco dias.** El Sprint 0 entrego 43 puntos en catorce dias.

| | Sprint 0 | Periodo actual |
|---|---|---|
| Puntos | 43 | 41 |
| Dias | 14 | 5 |
| Puntos por dia | 3,07 | 8,20 |
| Puntos por semana | 21,5 | 57,4 |

La aceleracion es de **2,7 veces**. La seccion 3 de este documento proyectaba que
hacian falta 3,5 veces la velocidad del Sprint 0 para llegar a tiempo. **No se
alcanza esa cifra todavia, pero el orden de magnitud ya no es imposible.**

### Tres razones para no proyectar sobre esta cifra

**1. El 63 % de los puntos son de una sola persona.** Luna cerro cinco historias y
26 de los 41 puntos. Alejandro suma 5, Avril 10, Cesar cero. Una velocidad de
equipo sostenida por una persona no es una velocidad de equipo.

**2. Buena parte del periodo es documentacion e investigacion**, que se mueve mas
rapido que el modelado, el despliegue continuo y la API que vienen despues. Las
historias de E3 son de 12,5 h cada una y dependen unas de otras en cadena.

**3. Hay deuda que no aparece en los puntos.** H1.1 y H1.2 siguen abiertas desde el
Sprint 0. Son 12,5 horas que **destraban a las cuatro personas**, y mientras no
entren, tres de los cuatro trabajan contra simulados. Los puntos entregados no
reflejan ese bloqueo porque el trabajo bloqueado ni siquiera empezo.

### Lo que si se puede afirmar

El metodo de trabajo empezo a rendir. En este periodo entraron **la primera suite
de pruebas automatizadas** del proyecto, **dos decisiones de arquitectura tomadas
midiendo** en vez de discutiendo, y **dos defectos de fondo detectados en revision**
antes de llegar al modelo.

Ninguna de esas cuatro cosas aparece en el conteo de puntos, y las cuatro cambian
el resultado final mas que un punto de mas o de menos.

### Lo que sigue sin poder calcularse

**Las horas reales.** La accion 12.4 dejo de estar en cero el 19 de agosto: Cesar
reporto las de H1.8 y H6.1 por iniciativa propia, y de ahi sale la seccion 2 de
este documento. Con dos mediciones de la misma persona y del mismo tamano todavia
no se recalibra nada, pero la afirmacion anterior de este apartado —que nadie las
registraba— ya no es cierta y se corrige.

**Lo que sigue faltando** son las mediciones de las otras tres personas, y que se
anote si la historia dependia de una interfaz ya congelada, que es la variable que
el primer par de datos senalo y que el modelo del roadmap no tiene.

---

## 5. Registro por sprint

| Sprint | Semanas | Comprometido | Entregado | Velocidad | Cumplimiento |
|---|---|---|---|---|---|
| 0 | 2-3 | 54 pts | 43 pts | 21,5 pts/sem | 80 % |
| 1 | en curso | 74 pts | 25 pts al dia 5 de 14 | 57,4 pts/sem en el periodo | — |
| 2 | 6-7 | — | — | — | — |
| 3 | 8-9 | — | — | — | — |
| 4 | 10-11 | — | — | — | — |

Las filas se completan al cerrar cada sprint, con el mismo método: contar sobre el
último commit del sprint en `dev`, no reconstruir después.
