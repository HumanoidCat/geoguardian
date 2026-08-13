# Tareas de Luis

**Luis Alejandro Luna Garcia**  
**Carpetas propias:** `backend/calidad, backend/tests, docs/investigacion`

> Solo modificas tus carpetas. Si necesitas un cambio fuera de ellas, se pide, no se hace.

> Marca `[x]` cuando la historia cumpla la Definition of Done, no cuando el codigo funcione.

> **Compromiso de tiempo: 18 horas por semana.**

**Total asignado:** 80 puntos · 144 horas · 14.3 h por semana en promedio

## Carga por sprint

| Sprint | Semanas | Horas | Capacidad | Estado |
|---|---|---|---|---|
| S0 | semanas 2-3 | 25.9 | 36 | holgado |
| S1 | semanas 4-5 | 34.3 | 36 | ajustado |
| S2 | semanas 6-7 | 31.0 | 36 | ajustado |
| S3 | semanas 8-9 | 20.3 | 36 | holgado |
| S4 | semanas 10-11 | 32.0 | 36 | ajustado |

## Sprint 0 (semanas 2-3) — 25.9 h

- [x] **H10.1** · Plan de pruebas con casos por modulo (2026-08-06)
  - `E10` · 5 pts · 4.8 h · rubrica: QA · depende de: contratos

- [x] **H10.5a** · Recopilar 15 referencias IEEE con ficha de contenido (2026-08-06)
  - `E10` · 8 pts · 21.1 h · rubrica: IEEE · **bloquea a: H10.5b**


## Sprint 1 (semanas 4-5) — 34.3 h

- [ ] **H10.5b** · Estado del arte de Costa Rica
  - `E10` · 5 pts · 13.2 h · rubrica: IEEE · depende de: H10.5a · **bloquea a: H10.5c**

- [ ] **H4.3** · Catalogo de 12 o mas eventos historicos del canton con fuente
  - `E4` · 8 pts · 21.1 h · rubrica: OE3 · **bloquea a: H4.4, H7.3**


## Sprint 2 (semanas 6-7) — 31.0 h

- [ ] **H1.5** · Reporte formal de calidad de datos: faltantes, atipicos, sesgos
  - `E1` · 8 pts · 12.5 h · rubrica: OE1 · depende de: H1.1

- [ ] **H2.1** · Filtrar ruido de las series con justificacion del filtro
  - `E2` · 3 pts · 2.9 h · rubrica: Senales · depende de: H1.4 · **bloquea a: H2.2, H2.3, H2.4, H2.7**

- [ ] **H2.3** · SPI de 1 y 3 meses por convolucion de ventana movil
  - `E2` · 5 pts · 7.8 h · rubrica: Senales · depende de: H2.1 · **bloquea a: H2.5, H3.0**

- [ ] **H2.7** · Calcular percentiles R95p y R99p de precipitacion acumulada por distrito
  - `E2` · 5 pts · 7.8 h · rubrica: Senales · depende de: H2.1 · **bloquea a: H3.0**


## Sprint 3 (semanas 8-9) — 20.3 h

- [ ] **H10.2** · Pruebas automatizadas del backend, cobertura de dominio
  - `E10` · 5 pts · 4.8 h · rubrica: QA · depende de: H6.2

- [ ] **H2.2** · Analisis espectral de la lluvia e interpretacion fisica
  - `E2` · 5 pts · 7.8 h · rubrica: Senales · depende de: H2.1

- [ ] **H2.4** · Anomalias respecto a la normal climatologica 1991-2020
  - `E2` · 3 pts · 2.9 h · rubrica: Senales · depende de: H2.1 · **bloquea a: H7.4**

- [ ] **H9.1** · Preparar SUS, guion de entrevista y dosier de 3 casos
  - `E9` · 5 pts · 4.8 h · rubrica: OE4 · **bloquea a: H9.2**


## Sprint 4 (semanas 10-11) — 32.0 h

- [ ] **H12.4** · Diagnostico guiado a partir de la bitacora de incidencias
  - `E12` · 5 pts · 7.8 h · rubrica: Troubleshoot · depende de: H12.1 · **bloquea a: H12.5**

- [ ] **H9.2** · Sesion con 3 a 5 participantes y calculo del puntaje SUS
  - `E9` · 5 pts · 13.2 h · rubrica: OE4 · depende de: H9.1 · **bloquea a: H9.3, H9.4**

- [ ] **H9.3** · Someter los umbrales de incendio a criterio de los participantes
  - `E9` · 3 pts · 7.9 h · rubrica: OE4 · depende de: H9.2, H1.2

- [ ] **H9.4** · Incorporar un cambio derivado de la retroalimentacion
  - `E9` · 2 pts · 3.1 h · rubrica: OE4 · depende de: H9.2

## Regla: lo hecho no se borra

Una historia terminada se marca `[x]` y **se queda donde esta**. Nunca se borra
ni se mueve a otro archivo.

Este archivo es el registro de lo que hiciste durante el trimestre. En la semana
12 hay que demostrar contribucion individual: la rubrica de Computacion Grafica
lo evalua explicitamente. Si vas borrando lo terminado para "ver mejor lo que
falta", en noviembre no vas a tener con que respaldar tu aporte.

Al marcar una historia, agregale la fecha entre parentesis:

    - [x] **H1.1** · Descargar 10 anios de series climaticas diarias (2026-08-14)

Lo mismo aplica a las issues de GitHub: se cierran, no se eliminan. Una issue
cerrada conserva la discusion, los commits enlazados y el Pull Request. Una issue
borrada no deja nada.

## Al terminar cada historia

1. Verificar ejecutando, no leyendo. Si dice que pasa, correlo.
2. Guardar la evidencia en `docs/evidencias/<materia>/` el mismo dia.
3. Abrir el Pull Request hacia `dev` enlazado a la issue.
4. Marcar `[x]` aqui con la fecha, y **cerrar** la issue en GitHub. No borrar ninguna de las dos.
