# Tareas de Avril

**Avril Madrigal Elizondo**  
**Carpetas propias:** `frontend`

> Solo modificas tus carpetas. Si necesitas un cambio fuera de ellas, se pide, no se hace.

> Marca `[x]` cuando la historia cumpla la Definition of Done, no cuando el codigo funcione.

> **Compromiso de tiempo: 18 horas por semana.**

**Total asignado:** 94 puntos · 115 horas · 11.5 h por semana en promedio

## Carga por sprint

| Sprint | Semanas | Horas | Capacidad | Estado |
|---|---|---|---|---|
| S0 | semanas 2-3 | 2.9 | 36 | holgado |
| S1 | semanas 4-5 | 19.3 | 36 | holgado |
| S2 | semanas 6-7 | 30.8 | 36 | ajustado |
| S3 | semanas 8-9 | 25.0 | 36 | holgado |
| S4 | semanas 10-11 | 36.6 | 36 | SOBRECARGA +1 h |

## Sprint 0 (semanas 2-3) — 2.9 h

- [x] **H5.1** · Mapa del canton con poligonos distritales, zoom y desplazamiento (2026-08-15)
  - `E5` · 3 pts · 2.9 h · rubrica: CG-4 · depende de: contratos · **bloquea a: H5.2, H5.3, H5.6**


## Sprint 1 (semanas 4-5) — 19.3 h

- [ ] **H1.6** · Descargar imagenes Sentinel-2 de estacion seca, nubosidad menor a 20%
  - `E1` · 5 pts · 7.8 h · rubrica: CG-3 · **bloquea a: H5.5, H8.4**

- [x] **H5.2** · Cuatro o mas capas conmutables con control de opacidad (2026-08-17)
  - `E5` · 5 pts · 4.8 h · rubrica: CG-4 · depende de: H5.1

- [x] **H5.3** · Coropletas de riesgo por evento con rampa de color y leyenda (2026-08-17)
  - `E5` · 7 pts · 6.7 h · rubrica: CG-1 · depende de: H5.1 · **bloquea a: H5.4, H5.7, H7.1**


## Sprint 2 (semanas 6-7) — 30.8 h

- [ ] **H10.3** · Manual de usuario con capturas paso a paso
  - `E10` · 5 pts · 4.8 h · rubrica: MVP · depende de: H7.1 · **bloquea a: H10.9**

- [ ] **H10.7** · Diagramas de casos de uso y entidad-relacion
  - `E10` · 5 pts · 7.8 h · rubrica: Arq · depende de: H1.8

- [ ] **H5.6** · Transformacion WGS84 a CRTM05 verificada con puntos de control
  - `E5` · 3 pts · 4.7 h · rubrica: CG-1 · depende de: H5.1

- [ ] **H5.7** · Selector de fecha que recarga el estado del mapa
  - `E5` · 3 pts · 2.9 h · rubrica: CG-4 · depende de: H5.3

- [ ] **H7.1** · Semaforo de riesgo por distrito y evento con umbrales documentados
  - `E7` · 6 pts · 5.8 h · rubrica: CG-2 · depende de: H5.3 · **bloquea a: H10.3**

- [ ] **H7.2** · Graficas interactivas de series con seleccion de rango
  - `E7` · 5 pts · 4.8 h · rubrica: CG-2 · depende de: H6.1


## Sprint 3 (semanas 8-9) — 25.0 h

- [x] **H5.4** · Mapa de calor por interpolacion IDW (2026-08-18)
  - `E5` · 8 pts · 12.5 h · rubrica: CG-1 · depende de: H5.3

- [ ] **H5.5** · Indices NDVI y NDWI renderizados como capa
  - `E5` · 5 pts · 7.8 h · rubrica: CG-3 · depende de: H1.6

- [ ] **H6.5** · Diagrama de componentes y de secuencia del flujo principal
  - `E6` · 3 pts · 4.7 h · rubrica: Arq · depende de: H6.1


## Sprint 4 (semanas 10-11) — 36.6 h

- [ ] **H10.6** · Cartel academico IEEE legible a 1.5 m
  - `E10` · 8 pts · 7.7 h · rubrica: IEEE · depende de: H10.5c

- [ ] **H10.9** · Guion de demo y tres ensayos completos
  - `E10` · 4 pts · 10.6 h · rubrica: CG-6 · depende de: H10.3

- [ ] **H12.2** · Pantalla de monitoreo de pipelines y entornos dentro del visor
  - `E12` · 5 pts · 4.8 h · rubrica: Troubleshoot · depende de: H12.1

- [ ] **H12.5** · Historico de incidentes consultable desde la aplicacion
  - `E12` · 3 pts · 2.9 h · rubrica: Troubleshoot · depende de: H12.4

- [ ] **H13.2** · Manual de operacion del sistema
  - `E13` · 5 pts · 4.8 h · rubrica: Documentacion · depende de: H11.4

- [ ] **H7.3** · Historial de eventos filtrable y exportable
  - `E7` · 3 pts · 2.9 h · rubrica: CG-2 · depende de: H4.3

- [ ] **H7.4** · Panel de estadisticas comparado contra la normal historica
  - `E7` · 3 pts · 2.9 h · rubrica: CG-2 · depende de: H2.4

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
