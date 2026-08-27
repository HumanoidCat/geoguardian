---
title: "GeoGuardian · Avance de Semana 8"
subtitle: "Evaluación de documentación · Revisión del MVP · Revisión de la documentación del MVP"
author: "Alejandro Josué Rodríguez Zamora · César Andrés Ubau Calvo · Luis Alejandro Luna García · Avril Madrigal Elizondo"
date: "27 de agosto de 2026"
lang: es
---

# 1 · Qué es GeoGuardian

Sistema de **estimación de riesgo climático por distrito** para el cantón de
Tilarán, Guanacaste, construido exclusivamente sobre datos abiertos.

Estima tres eventos —**lluvia intensa, sequía e incendio forestal**— para cada
uno de los ocho distritos, a un horizonte de siete días. El destinatario es el
Comité Municipal de Emergencias.

| Dato | Valor |
|---|---|
| Universidad | Invenio · III Trimestre 2026 |
| Repositorio | `github.com/HumanoidCat/geoguardian` |
| Visor publicado | GitHub Pages, desde el 20 de agosto |
| Avance | **31 de 88 historias · 160 de 431 puntos · 37,1 %** |

---

# 2 · Revisión del MVP

## 2.1 Qué funciona hoy

| Componente | Estado | Evidencia |
|---|---|---|
| **Base de datos** · PostgreSQL 16 + PostGIS 3.4 | Cargada | 8 tablas en `geo`, `crudo`, `control` |
| **Series climáticas** · 1991–2025 | Cargadas | 102 272 filas en `crudo.medicion_diaria` |
| **Focos de calor** · 2001–2024 | Cargados | 242 dentro del cantón |
| **Geometrías** · SNIT/IGN, EPSG:4326 | Cargadas | 8 distritos, 669,23 km² |
| **API REST** · FastAPI con OpenAPI | Implementada | H6.1, cerrada |
| **Visor** · React + Leaflet | **Publicado** | GitHub Pages, con respaldo estático |
| **Etiquetado** · los tres eventos | Cerrado | 99 296 filas, H3.0 |
| **Validación temporal** · ventana expansiva | Cerrada | 5 pliegues, H3.2 |
| **Líneas base** · trivial y climatológica | Cerradas | H3.1 |
| **Arnés comparativo** | Entregado | H3.6, sin cerrar |

## 2.2 Qué NO funciona, dicho sin rodeos

**No hay modelo entrenado.** Los tres algoritmos comprometidos en D-09
—Regresión Logística, Random Forest y XGBoost— son H3.3, H3.4 y H3.5, y ninguno
existe. El sistema hoy tiene un piso medido contra el que comparar, y nada que
comparar todavía.

**La base de datos no está en línea.** Corre en las máquinas del equipo. El visor
publicado consulta `/api`, recibe 404 y **cae a un respaldo estático de datos
simulados**, que declara en pantalla. Es la degradación prevista en D-23,
funcionando como se diseñó, pero significa que el sitio público no muestra datos
reales.

**`analitico.riesgo` no tiene dueño.** Ninguna historia lo crea, y H1.13 lo
necesita. Su dependencia declarada, H1.8, ya está satisfecha, así que la historia
figura desbloqueada y en realidad es imposible.

**La validación externa con personas no ha ocurrido.** H9.2a —SUS, entrevista y
caso retrospectivo, comprometidos en D-12— sigue abierta. Lo que sí se hizo es la
parte que no requiere participantes: el contraste contra el catálogo histórico,
en la sección 4.3.

## 2.3 El visor, corregido esta semana

El profesor revisó el sitio publicado el 24 de agosto. De sus tres observaciones,
dos se atendieron bien y una se sobre-interpretó, lo que produjo dos regresiones
que se revirtieron el 27. Está registrado como **I-14** y es el aprendizaje más
incómodo del sprint. Ver la sección 6.

Estado actual del visor:

- Mapa a ancho completo, con la región alrededor de Tilarán.
- Coropleta de riesgo por distrito, escala de tres niveles verificada por
  colorimetría —luminancia monótona, contraste WCAG, orden preservado bajo las
  tres dicromacias—.
- Capa de mapa de calor por interpolación IDW, **recortada contra los polígonos**.
- Selector de evento y de fecha, semáforo por distrito, panel de detalle.
- Aviso permanente de que los datos son simulados.

---

# 3 · Arquitectura

Los seis diagramas se generan desde `docs/herramientas/generar_diagramas.py`. El
entidad-relación **se deriva del DDL**: si alguien agrega una tabla y no
regenera, la integración continua falla.

## 3.1 Flujo de datos

![Flujo de datos](diagramas/flujo-datos.png)

## 3.2 Componentes

![Componentes](diagramas/componentes.png)

## 3.3 Entidad-relación

![Entidad-relación](diagramas/entidad-relacion.png)

## 3.4 Secuencia · consulta de riesgo

![Secuencia](diagramas/secuencia-consulta-riesgo.png)

## 3.5 Despliegue

![Despliegue](diagramas/despliegue.png)

## 3.6 Flujo de modelado

![Flujo de modelado](diagramas/flujo-modelado.png)

---

# 4 · Resultados medidos

Ninguna cifra de esta sección proviene de los datos simulados del visor.

## 4.1 Qué informa el calendario, por evento

Contraste de las dos líneas base sobre 99 296 filas etiquetadas, con los cinco
pliegues de H3.2 y F1-macro (D-10):

| Evento | Trivial | Climatológica | Diferencia | Veredicto |
|---|---|---|---|---|
| **Lluvia intensa** | 0,309 ± 0,005 | **0,346 ± 0,010** | **+0,036** | la climatológica gana |
| **Sequía** | 0,333 ± 0,084 | 0,263 ± 0,063 | −0,070 | empate técnico |
| **Incendio** | 0,494 ± 0,003 | 0,500 ± 0,049 | +0,006 | empate técnico |

**El criterio se fijó antes de mirar los datos:** si la ventaja es menor que la
dispersión entre pliegues, no se declara ganador.

**La sequía confirma D-19.** El SPI-3 se ajusta por mes calendario para remover
la estacionalidad; que el mes no informe es la señal de que ese ajuste funciona.

**El incendio no se puede concluir.** La dispersión de la climatológica entre
pliegues (0,138) es **veintitrés veces** su ventaja. Con tres distritos, 1,23 %
de clase positiva y 24 años, la medición no tiene resolución.

**Sin prueba de significancia, deliberadamente.** Cinco pliegues de una serie
temporal no son cinco muestras independientes: la ventana es expansiva y las
métricas están correlacionadas.

## 4.2 El embargo temporal, calculado y no supuesto

Los criterios escritos antes de implementar estimaron tres valores distintos; la
medición dio uno solo:

| Evento | Estimado | Calculado |
|---|---|---|
| Incendio | 7 días | 7 días |
| Lluvia intensa | 9 días | **7 días** |
| Sequía | 38 días | **7 días** |

La corrección de la sequía es la interesante: el corte en frontera de mes
**absorbe** el alcance del SPI-3. Dos criterios escritos por separado resultaron
más baratos juntos que cada uno por su lado.

## 4.3 Validación externa contra 46 eventos reales

Contraste del etiquetado contra el catálogo de DesInventar Costa Rica construido
en H4.3. **Es la validación que no necesita participantes**, comprometida en
D-12 como caso retrospectivo.

| Evento | Registros | Contrastables | Detecta | Cobertura | Tasa base | **Realce** |
|---|---|---|---|---|---|---|
| Lluvia intensa | 38 | 34 | 22 | 64,7 % | 13,7 % | **4,74×** |
| Sequía · 7 días | 7 | 7 | 0 | 0,0 % | 15,6 % | 0,00× |
| Sequía · 90 días | 7 | 7 | 7 | 100,0 % | 15,6 % | **6,42×** |
| Incendio | 1 | 0 | — | — | 2,7 % | — |

**El número que importa es el realce**, no la cobertura: una cobertura alta se
consigue marcando siempre.

**No se reporta precisión**, y la omisión es deliberada: el catálogo registra
daños reportados, no fenómenos, y está incompleto. Una marca sin registro no es
un falso positivo.

**El cero de la sequía son dos relojes distintos.** Los siete registros llevan la
misma fecha —2014-09-30, la declaratoria administrativa— y el etiquetado marcó
sequía **de enero a agosto de 2014**. La marca más cercana está a −37 días en los
ocho distritos. Una declaratoria llega al final del episodio, no durante.

**Esto establece un piso para los modelos:** el etiquetado alcanza realce 4,74×
sobre eventos verificados por una fuente externa. Un modelo que no lo supere no
aporta sobre la verdad de terreno.

---

# 5 · Evaluación de la documentación

## 5.1 Inventario

| Documento | Qué contiene | Estado |
|---|---|---|
| `02-contratos.md` | Interfaces congeladas y sus huecos | Vigente, v1.3.0 |
| `03-bitacora-decisiones.md` | **30 decisiones** de arquitectura | Vigente |
| `04-bitacora-incidencias.md` | **14 incidencias** con causa raíz | Vigente |
| `05-matriz-trazabilidad.md` | Requisito, módulo, prueba, evidencia | **Generada**, 52 filas |
| `06-roadmap.md` | Épicas y sprints | Vigente |
| `07-propiedad-archivos.md` | Quién puede tocar qué (D-16) | Vigente |
| `08-backlog.md` | 88 historias con dependencias | Vigente |
| `09-auditoria-backlog.md` | Revisión de dependencias | Vigente |
| `10-manual-tecnico.md` | Instalación y operación | Vigente · **falta H10.4** |
| `11-ceremonias-scrum.md` | Actas de ceremonias | Vigente |
| `12-velocidad.md` | Estimado contra real | Vigente |
| `13-documento-ieee.md` | El artículo | **Parcial**, ver 5.3 |
| `14-latencia-de-las-fuentes.md` | Latencia declarada por evento | Vigente |
| `15-cerrar-una-historia.md` | Procedimiento de cierre | Vigente |
| `16-avance-semana8.md` | Este documento | — |
| `diagramas/README.md` | Los seis diagramas | Nuevo |
| `ARRANQUE.md` | Instalación en Windows | Vigente |

Más **59 documentos de evidencia** en `docs/evidencias/`, organizados por materia.

## 5.2 Lo que hace distinta a esta documentación

**Las cifras las verifica una máquina.** `verificar_documentacion.py` recalcula
**43 apariciones numéricas** desde el repositorio en cada ejecución del pipeline
y hace fallar la integración continua si alguna se desfasa.

El control se agregó el 26 de agosto porque hacía falta: entre el 18 y el 26,
**cinco cifras del documento IEEE dejaron de ser ciertas** sin que nadie lo
notara.

**Hay 26 verificadores** en el repositorio, y todos corren en la integración
continua. La regla es de I-06: *un control que se ejecuta solo cuando alguien se
acuerda no protege de nada.*

**Los artefactos derivados no se editan.** La matriz de trazabilidad, los seis
diagramas y las cifras del documento se generan. El principio es siempre el
mismo: **una sola fuente, vistas derivadas, y una máquina que comprueba que
coinciden.**

## 5.3 Estado del documento IEEE

| Sección | Estado |
|---|---|
| I. Introducción | Redactada |
| II. Trabajo relacionado | Redactada |
| III. Metodología | Redactada |
| IV. Arquitectura | Redactada |
| V. Hallazgos sobre disponibilidad de datos | Redactada · **es el aporte que ya existe** |
| **VI. Resultados** | **Parcial.** Seis subsecciones con lo medido; VI-E declara lo que falta |
| VII. Discusión | **Vacía.** Necesita los tres algoritmos |
| VIII. Limitaciones | Redactada |
| IX. Conclusiones | **Vacía.** Necesita la sección VII |

Las secciones vacías **declaran qué van a contener y qué hace falta para
escribirlas**. Un apartado en blanco sin explicación es indistinguible de un
olvido.

## 5.4 Lo que falta en la documentación

| Qué | Historia | De quién |
|---|---|---|
| Manual técnico verificado por alguien ajeno al desarrollo | H10.4 | Alejandro · necesita persona externa |
| Secciones VII y IX del documento IEEE | H10.5c | Alejandro · bloqueadas por H3.3–H3.5 |
| Validación externa con usuarios (SUS, entrevista) | H9.2a | Requiere participantes |
| Cartel académico | — | Bloqueado por H10.5c |

---

# 6 · La incidencia de la semana: I-14

Se registra aquí porque es el aprendizaje más útil del sprint y porque afecta a
cómo el equipo trabaja, no solo a un archivo.

**Qué pasó.** El profesor dio tres observaciones sobre el visor publicado. De
ellas salieron **dos cambios que no pidió**: encerrar el mapa en la forma del
cantón, y retirar por completo la capa de mapa de calor.

**Causa raíz.** Las dos tienen la misma forma: **un dato observado se elevó a
intención, y después se razonó con rigor sobre esa intención inventada.**

| Lo que había | En qué se convirtió |
|---|---|
| Una captura recortada del visor | «el visor debe mostrar solo el cantón» |
| «se sale del cantón y hay distritos sin marcar» | «interpolar afirma lo que el dato no dice» |

Lo que hace visible el defecto es que **la costura quedó escrita**: el documento
de evidencia dice que son «dos cuestiones distintas», y la decisión D-28 las
trató como una sola.

**El agravante, y hay que nombrarlo.** El equipo redacta con ayuda de IA, y una
premisa mal puesta no se discute: se implementa. Una persona a la que le piden
retirar un entregable ajeno pregunta por qué; una herramienta que recibe el
argumento ya construido lo ejecuta bien, rápido y completo. **La calidad de la
ejecución fue lo que ocultó el problema**: 166 líneas de ADR y tres capturas de
evidencia, todo sobre un hecho falso.

**Qué cambia.** Tres reglas:

1. Una captura es una observación, no una especificación.
2. Un defecto de implementación no habilita una decisión de alcance.
3. **Cuando una decisión se apoya en lo que dijo alguien de afuera, la cita
   textual va en el registro, no la interpretación.**

Y lo que se sigue de trabajar con IA: **la responsabilidad se corre hacia arriba,
a las premisas.** El razonamiento se puede delegar; el hecho del que parte, no.
Una premisa equivocada ya no produce un trabajo mediocre que se nota: produce un
trabajo impecable en la dirección equivocada.

**Corrección.** D-30 revierte D-28. D-28 se conserva entera con un aviso arriba:
una bitácora que se edita para quedar bien deja de servir para aprender. El
defecto real —el recorte— se arregló y **ahora lo vigila un verificador en la
integración continua**: 0 % pintado fuera del cantón, 0 % del cantón sin pintar,
contra 23,8 % y 20,7 % antes.

---

# 7 · Estado por persona y por sprint

| Persona | Rol | Historias | Puntos |
|---|---|---|---|
| Alejandro Josué Rodríguez Zamora | Lead PM, arquitectura, modelado | 11 de 23 | 59 |
| Luis Alejandro Luna García | Investigación y calidad | 8 de 17 | 42 |
| Avril Madrigal Elizondo | Frontend y visualización | 7 de 21 | 35 |
| César Andrés Ubau Calvo | Backend, ETL, base de datos | 5 de 27 | 24 |

**El dato de César está desactualizado en el tablero.** Tiene cuatro historias
entregadas y mergeadas —H6.0, H6.2, H1.7 y H1.4— que solo esperan la marca de
cierre. Su número real es **9 de 27**.

| Sprint | Historias | Puntos |
|---|---|---|
| S0 | 11 de 11 | 54 de 54 |
| S1 | 7 de 15 | 40 de 72 |
| S2 | 10 de 23 | 52 de 120 |
| S3 | 3 de 18 | 14 de 93 |
| S4 | 0 de 21 | 0 de 92 |

---

# 8 · Riesgos abiertos

| # | Riesgo | Impacto | Estado |
|---|---|---|---|
| 1 | **Sin modelo entrenado** | Bloquea VI-E, VII, IX del IEEE, y H3.7, H3.8, H4.1, H4.4 | H3.3–H3.5, de César |
| 2 | **Base de datos no publicada** | El sitio público muestra simulados | Sin historia asignada |
| 3 | **`analitico.riesgo` sin dueño** | H1.13 es imposible pese a figurar desbloqueada | Decisión pendiente |
| 4 | **Cadena de despliegue en serie** | 25 h de H11.1–H11.4 detrás de una marca de cierre | Esperando a César |
| 5 | **Validación con usuarios no iniciada** | D-12 comprometió SUS y entrevista | H9.2a abierta |
| 6 | **H10.4 necesita persona externa** | El manual no está verificado | Sin candidato |

---

# 9 · Cómo reproducir todo lo de este documento

```bash
# Estado del proyecto
python docs/herramientas/verificar_estado.py

# Las cifras de la documentación
python docs/herramientas/verificar_documentacion.py

# Los resultados de la sección 4
python -m backend.modelado.comparar
python -m backend.modelado.contrastar_catalogo --fallos

# Los diagramas
python docs/herramientas/generar_diagramas.py --png
python docs/herramientas/verificar_diagramas.py

# Todo lo demás
python -m pytest          # 176 pruebas
python -m ruff check .
```

Las herramientas que necesitan `datos/procesados/etiquetas.csv` requieren la base
levantada; el resto corre sobre el repositorio limpio.
