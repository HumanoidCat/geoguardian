# Evidencia del atraso y de la reasignacion de D-33

**Fecha de corte.** 2026-08-31, semana 9 de 12
**Herramientas.** `verificar_estado.py`, `verificar_backlog.py`, `git log`

Todas las cifras de este documento se recalculan desde el repositorio. Ninguna
esta escrita a mano y cualquiera las puede reproducir con los comandos que se
citan al pie.

---

## 1. Los sprints vencidos que siguen abiertos

    python docs/herramientas/verificar_estado.py

| Sprint | Semanas | Vencio | Cerrado | Puntos |
|---|---|---|---|---|
| S0 | 2-3 | semana 3 | **11 de 11** | 54 de 54 |
| S1 | 4-5 | **semana 5** | 11 de 16 | 54 de 75 |
| S2 | 6-7 | **semana 7** | 11 de 23 | 60 de 120 |
| S3 | 8-9 | semana 9 | 6 de 18 | 29 de 93 |
| S4 | 10-11 | semana 11 | **0 de 21** | 0 de 92 |

**El Sprint 1 lleva cuatro semanas vencido.** El Sprint 2, dos.

Total del proyecto: **39 de 89 historias, 197 de 434 puntos, 45.4 %**, con el
75 % del calendario consumido.

## 2. Cierre por persona

| | Historias | % | Puntos | % |
|---|---|---|---|---|
| Luna | 12 de 17 | **71 %** | 65 de 80 | **81 %** |
| Alejandro | 11 de 23 | 48 % | 59 de 126 | 47 % |
| Avril | 7 de 21 | 33 % | 35 de 97 | 36 % |
| Cesar | 9 de 28 | **32 %** | 38 de 131 | **29 %** |

Cesar tenia la mayor asignacion del equipo -131 puntos, 28 historias- y el menor
porcentaje cerrado.

## 3. Actividad reciente

    git log origin/dev --author=<autor> --format="%ad" --date=short -1

| Persona | Ultimo commit en `dev` | Dias sin subir |
|---|---|---|
| Luna | 2026-08-30 | 1 |
| Alejandro | 2026-08-28 | 3 |
| Cesar | **2026-08-27** | **4** |
| Avril | **2026-08-26** | **5** |

## 4. Comunicaciones sin respuesta

| Fecha | Para | Asunto | Respuesta |
|---|---|---|---|
| 2026-08-28 | Avril | Las dos notas de frontend pendientes | **Ninguna** |
| 2026-08-30 | Cesar y Avril | Defecto del visor que bloquea H11.1 y 13 puntos de CD | **Ninguna** |

El segundo bloqueo es el mas caro: el visor no arranca por si solo y eso detiene
H11.1 y la entrega continua. El diagnostico y el arreglo exacto estan escritos
desde el 2026-08-30 y esperan una decision de propiedad de archivo.

## 5. Lo que se reasigna

12 historias, **58 puntos, 67.2 horas**.

| Historia | De | Sprint | Pts | h |
|---|---|---|---|---|
| H1.15 Crear `analitico.riesgo` con sus restricciones | Cesar | S1 | 3 | 2.9 |
| H1.13 Trigger de auditoria sobre predicciones | Cesar | S1 | 3 | 2.9 |
| H1.6 Imagenes Sentinel-2 de estacion seca | Avril | S1 | 5 | 7.8 |
| H1.9 Funciones PL/pgSQL con manejo de excepciones | Cesar | S2 | 8 | 7.7 |
| H1.11 Particionar mediciones por anio | Cesar | S2 | 5 | 4.8 |
| H1.12 Indices espaciales y compuestos | Cesar | S2 | 5 | 4.8 |
| H2.5 Lags, acumulados y medias moviles | Cesar | S2 | 5 | 4.8 |
| H3.3 Entrenar y evaluar Regresion Logistica | Cesar | S2 | 6 | 9.4 |
| H5.6 Transformacion WGS84 a CRTM05 | Avril | S2 | 3 | 4.7 |
| H7.2 Graficas interactivas de series | Avril | S2 | 5 | 4.8 |
| H10.3 Manual de usuario con capturas | Avril | S2 | 5 | 4.8 |
| H10.7 Diagramas de casos de uso y entidad-relacion | Avril | S2 | 5 | 7.8 |

Se traspasa el contenido **sin modificar**. No hay reduccion de alcance.

## 6. La carga resultante, que no cabe

    python docs/herramientas/verificar_backlog.py

| Sprint | PM antes | PM despues | Compromiso |
|---|---|---|---|
| S1 | 22.8 | **36.4** | 36 |
| S2 | 59.5 | **113.1** | 36 |
| S3 | 40.4 | 40.4 | 36 |
| S4 | 52.8 | 52.8 | 36 |

**Pendiente total del PM: 185.6 h. Quedan tres semanas. Son 62 h por semana.**

Se deja escrito porque **la decision se tomo con este numero a la vista**, no
por ignorarlo. La alternativa que si cabia en el calendario -repartir con Luna,
que se ofrecio por escrito el 2026-08-30 y tiene 32 h pendientes- se descarto
por preferencia del PM, no por falta de informacion.

## 7. Lo que este documento no afirma

**No dice que el trabajo de Cesar y Avril este mal hecho.** Lo que cerraron esta
en la matriz de trazabilidad con evidencia, y varias de esas historias son
dependencias de las que quedaron abiertas. H6.2, de Cesar, aporto 46 pruebas que
el CI ni siquiera estaba ejecutando (ver **I-17**).

**No dice por que se atrasaron.** Este documento registra que no hubo entregas ni
respuestas en las fechas indicadas. Las razones no se conocen, y no conocerlas es
parte del problema: **el bloqueo mas caro se pudo haber destrabado con un
mensaje**.

**Y no es una sancion.** D-33 declara como se revierte: quien retome algo suyo lo
avisa y se le devuelve, sin pedir permiso.
