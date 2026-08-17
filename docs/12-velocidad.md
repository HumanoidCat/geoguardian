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

**Ese modelo no se puede recalibrar todavía, porque nadie registró horas reales.**

Lo que hay en el repositorio son las horas **estimadas** de cada historia. Comparar
estimación contra estimación no dice nada: daría 1,0 siempre, por construcción.

Se declara en lugar de inventar un número. Un modelo recalibrado con datos que no
existen es peor que un modelo sin recalibrar, porque parece medido.

### Qué haría falta para poder recalibrarlo

La opción más barata, y la única que no agrega trabajo diario: **registrar las
horas reales en el cuerpo del Pull Request**, una línea, al cerrar cada historia.

    Horas reales: 6,5 (estimadas 7,8)

Con eso, al cierre del Sprint 1 se pueden contrastar las tres tasas contra la
realidad y ajustar la planificación de los sprints 3 y 4 con datos propios en vez
de con un supuesto.

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

## 4. Registro por sprint

| Sprint | Semanas | Comprometido | Entregado | Velocidad | Cumplimiento |
|---|---|---|---|---|---|
| 0 | 2-3 | 54 pts | 43 pts | 21,5 pts/sem | 80 % |
| 1 | 4-5 | 74 pts | — | — | — |
| 2 | 6-7 | — | — | — | — |
| 3 | 8-9 | — | — | — | — |
| 4 | 10-11 | — | — | — | — |

Las filas se completan al cerrar cada sprint, con el mismo método: contar sobre el
último commit del sprint en `dev`, no reconstruir después.
