# Auditoría de dependencias del backlog

**Fecha:** 2026-08-11 · **Alcance:** las 82 historias de `gestion/issues.csv`
**Motivo:** César detectó en H1.3 una dependencia real que el backlog no
declaraba. Si pasó una, era razonable suponer que había más.

Verificación: cruce programático de cada historia contra la dependencia
declarada en su cuerpo, comparando el sprint de origen contra el de destino.

---

## Resumen

| Hallazgo | Cantidad | Gravedad |
|---|---|---|
| Dependencias hacia sprints **posteriores** | 3 | Bloqueante |
| Historias sin dueño para un artefacto que otras necesitan | 1 | Bloqueante |
| Dependencias reales no declaradas | 4 | Alta |
| Alcance duplicado entre dos historias | 1 | Media |
| Dependencias cruzadas dentro del mismo sprint | 5 | Riesgo, no error |
| Dependencias hacia historias inexistentes | 0 | — |

**Ninguna de las cinco historias del Sprint 1 de Alejandro estaba correctamente
planificada.** Tres de las cinco son imposibles o están bloqueadas: 30 de sus
47.8 horas.

---

## 1. Dependencias hacia sprints posteriores

Una historia no puede depender de otra programada más tarde. Son tres, y dos
forman una cadena.

    H10.7 (S1, Alejandro) --> H6.5 (S3, Avril) --> H6.3 (S4, Cesar)

| Historia | Sprint | Depende de | Sprint | Salto |
|---|---|---|---|---|
| H10.7 Diagramas | S1 | H6.5 | S3 | +2 |
| H6.5 Diagrama de componentes | S3 | H6.3 | S4 | +1 |
| H3.0 Etiquetado de los tres eventos | S1 | H2.3 | S2 | +1 |

**H10.7 está programada en la semana 4 y depende, en cadena, de trabajo de la
semana 11.**

## 2. Nadie escribe el Dockerfile

`H11.1 · CI: construir imagen Docker y publicar artefactos en ghcr.io` está en
el Sprint 1 y declara depender de H8.1, que ya está terminada. Pero:

- No existe ningún Dockerfile en el repositorio.
- **Ninguna de las 82 historias menciona crear uno.**

Sin Dockerfile no hay imagen que construir ni artefacto que publicar. Y H11.1
bloquea toda la cadena de despliegue continuo:

    H11.1 --> H11.2 --> H11.3 --> H11.4 --> H13.2
                    \-> H12.3

Son **seis historias, 28 puntos**, colgando de un archivo que nadie tiene
asignado. Es el hallazgo más caro de esta auditoría.

Es exactamente el mismo error que César encontró en H1.1: una historia que
necesita un artefacto producido por otra, sin que la relación esté escrita.

## 3. Dependencias reales no declaradas

| Historia | Declara | Necesita además | Por qué |
|---|---|---|---|
| **H11.1** CI con imagen Docker | H8.1 | Un Dockerfile, sin dueño, y H6.1 para que haya API que empaquetar | No se puede construir una imagen de nada |
| **H3.0** Etiquetado de los tres eventos | H2.3 | **H2.7** (percentiles R95p/R99p) y **H1.2** (focos de calor) | Son tres eventos, no uno. Sequía sale del SPI (H2.3), lluvia intensa de los percentiles (H2.7) e incendio de los focos (H1.2). Solo la primera está declarada |
| **H4.4** Contrastar contra el catálogo | H4.3 | **H3.6** | Para contrastar estimaciones hay que tenerlas: salen de la tabla comparativa |
| **H9.3** Someter los umbrales de incendio | H9.2 | **H1.2** | El umbral de incendio es el percentil 90 de la distribución de focos. Sin focos cargados no hay umbral que someter |

H3.0 es el caso más serio de los cuatro: bloquea a H3.1 y H3.2, y H3.2 bloquea a
los tres algoritmos. Está mal enganchada en la raíz de la épica de modelado.

## 4. Alcance duplicado

`H10.7 · Diagramas: casos de uso, componentes, secuencia y ER` (8 pts, Alejandro)
y `H6.5 · Diagrama de componentes y de secuencia del flujo principal` (3 pts,
Avril) producen **los mismos dos diagramas**. Once puntos para un trabajo que
vale ocho, y dos personas capaces de dibujar cosas distintas del mismo sistema.

Además, el diagrama entidad-relación de H10.7 no depende de H6.5 en absoluto:
depende del DDL, o sea de H1.3 y H1.8.

## 5. Dependencias cruzadas dentro del mismo sprint

No son errores, pero son los puntos donde alguien se queda esperando a otro sin
que el calendario lo advierta. Van a la planificación de cada sprint.

| Sprint | Espera | A que termine |
|---|---|---|
| S2 | H10.3 (Alejandro) | H7.1 (Avril) |
| S2 | H2.5 (César) | H2.3 (Luna) |
| S2 | H3.3 (César) | H3.2 (Alejandro) |
| S4 | H10.6 (Avril) | H10.5c (Alejandro) |
| S4 | H12.5 (Avril) | H12.4 (Luna) |

---

## Correcciones propuestas

### Crear una historia nueva

**H6.0 · Dockerfile de la API y del visor, con imagen construida localmente**
Dueño: César · Épica E6 · 3 pts · ~3 h · rúbrica: CICD · depende de: H6.1
Sprint 1.

Sin ella, seis historias de despliegue no arrancan. Es la corrección más urgente.

### Mover de sprint

| Historia | De | A | Motivo |
|---|---|---|---|
| H3.0 | S1 | **S2** | Depende de H2.3 y H2.7, ambas en S2 |
| H11.1 | S1 | **S2** | Necesita el Dockerfile (H6.0) y la API (H6.1), las dos en S1 |
| H6.5 | S3 | **fusionar en H10.7** | Alcance duplicado |

### Reformular H10.7

Dividirla, porque sus cuatro diagramas no dependen de lo mismo:

| Parte | Depende de | Sprint |
|---|---|---|
| Casos de uso | Nada. Se puede hacer hoy | **S1** |
| Entidad-relación | H1.8, el DDL con roles | **S2** |
| Componentes y secuencia | H6.1, la API real | **S2** |

Absorbe los 3 puntos de H6.5, que se elimina del backlog de Avril. A Avril se le
libera trabajo en S3, que es un sprint apretado.

### Actualizar dependencias declaradas

    H3.0   depende de: H2.3, H2.7, H1.2
    H11.1  depende de: H6.0, H6.1
    H4.4   depende de: H4.3, H3.6
    H9.3   depende de: H9.2, H1.2

---

## Efecto sobre el Sprint 1 de Alejandro

    Antes:  H10.4, H10.7, H11.1, H13.1, H3.0     47.8 h, de las cuales 30 imposibles
    Ahora:  H10.4, H10.7a (casos de uso), H13.1  22.8 h reales

H3.0 y H11.1 pasan a S2, que sube y hay que revisar contra la capacidad.

**Consecuencia que no conviene celebrar.** Esto no reduce el trabajo: lo mueve
hacia adelante. Los sprints 2 y 3 ya estaban por encima de la capacidad nominal,
y ahora reciben 25 horas más. El margen que aparece en S1 es exactamente el que
el roadmap ya advertía: *"el margen de las primeras semanas no es tiempo libre,
es el colchón de las últimas"*.

## Lo que esta auditoría dice del método

Las 82 historias se escribieron con dependencias puestas a ojo y nadie las cruzó
contra el calendario hasta hoy, en la semana 4. El cruce programático que
encontró los tres saltos de sprint tarda segundos.

Debería correr en el CI, igual que `verificar.py` y `verificar_adr.py`. Es la
misma lección de la incidencia I-04: **un control que mira estructura no
sustituye a uno que mira contenido**, y aquí ni siquiera había control.
