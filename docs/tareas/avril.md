# Tareas de Avril

**Avril Madrigal Elizondo**  
**Carpetas propias:** `frontend`

> Solo modificas tus carpetas. Si necesitas un cambio fuera de ellas, se pide, no se hace.

> Marca `[x]` cuando la historia cumpla la Definition of Done, no cuando el codigo funcione.
>
> **Los seis pasos para cerrar una historia estan en `docs/15-cerrar-una-historia.md`.**
> El quinto es el que mas se olvida: el Pull Request lleva `Closes #N` con el
> numero real de la issue. "Cierra H10.1" no cierra nada.

> **Compromiso de tiempo: 18 horas por semana.**

> **Al cerrar una historia, anota sus horas.** Debajo de la linea de la historia:
>
>     - horas: estimada 4.0 . real 2.0
>
> `estimada` es lo que dijiste **antes de arrancar**, sin mirar el backlog.
> `real` es lo que tardo. Las horas del backlog ya estan en la linea de arriba y
> no se repiten aqui.
>
> Si no hubo estimacion previa, se escribe `n/d` **con el motivo entre
> parentesis**: `estimada n/d (no se pidio al arrancar) . real 2.5`. Un hueco sin
> explicacion no se distingue de un olvido.
>
> Se exige desde el **2026-08-20**, no hacia atras. Lo comprueba
> `docs/herramientas/verificar_horas.py`. El porque esta en **D-24**.

**Total asignado:** 82 puntos · 97.1 horas · 8.8 h por semana en promedio

## Carga por sprint

| Sprint | Semanas | Horas | Capacidad | Estado |
|---|---|---|---|---|
| S0 | semanas 2-3 | 2.9 | 36 | holgado |
| S1 | semanas 4-5 | 11.5 | 36 | holgado |
| S2 | semanas 6-7 | 21.1 | 36 | holgado |
| S3 | semanas 8-9 | 25.0 | 36 | holgado |
| S4 | semanas 10-11 | 36.6 | 36 | SOBRECARGA +1 h |

## Sprint 0 (semanas 2-3) — 2.9 h

- [x] **H5.1** · Mapa del canton con poligonos distritales, zoom y desplazamiento (2026-08-15)
  - `E5` · 3 pts · 2.9 h · rubrica: CG-4 · depende de: contratos · **bloquea a: H5.2, H5.3, H5.6**


## Sprint 1 (semanas 4-5) — 11.5 h

- [x] **H5.2** · Cuatro o mas capas conmutables con control de opacidad (2026-08-17)
  - `E5` · 5 pts · 4.8 h · rubrica: CG-4 · depende de: H5.1

- [x] **H5.3** · Coropletas de riesgo por evento con rampa de color y leyenda (2026-08-17)
  - `E5` · 7 pts · 6.7 h · rubrica: CG-1 · depende de: H5.1 · **bloquea a: H5.4, H5.7, H7.1**


## Sprint 2 (semanas 6-7) — 21.1 h

- [ ] **H5.6** · Transformacion WGS84 a CRTM05 verificada con puntos de control
  - `E5` · 3 pts · 4.7 h · rubrica: CG-1 · depende de: H5.1
  - **Devuelta el 2026-09-02** por la clausula de reversion de **D-33**. La tomo
    Alejandro el 31 de agosto y Avril la pidio de vuelta con motivo: **ya estaba
    hecha** en `feature/ame-h5.6-crtm05`, con 25 controles contra `pyproj` como
    implementacion independiente. Empezarla de nuevo habria tirado ese trabajo.
  - Compromiso: **PR el viernes 4 de septiembre**.

- [ ] **H10.3** · Manual de usuario con capturas paso a paso
  - `E10` · 5 pts · 4.8 h · rubrica: MVP · depende de: H7.1 · **bloquea a: H10.9**
  - **Devuelta el 2026-09-02** por la clausula de reversion de **D-33**. Se
    devuelve porque **desbloquea H10.9, que es CG-6 entera** -el unico criterio
    que sostiene esa historia- y porque quien conoce el visor saca las capturas a
    la primera.
  - Compromiso: **martes 9 de septiembre**.

- [x] **H5.7** · Selector de fecha que recarga el estado del mapa (2026-08-26)
  - `E5` · 3 pts · 2.9 h · rubrica: CG-4 · depende de: H5.3
  - horas: estimada 2.5 . real 1.25

- [x] **H5.8** · Encuadre del mapa en el canton y marca de seleccion accesible (2026-08-26)
  - `E5` · 3 pts · 2.9 h · rubrica: CG-1 · depende de: H5.1
  - horas: estimada 2.0 . real 2.4
  - Sale de la retroalimentacion del profesor sobre el visor publicado, el
    2026-08-24. Ver `docs/evidencias/computacion-grafica/`.
  - **No reabre H5.1 ni H5.3**, que estan cerradas y con evidencia. Es trabajo
    nuevo con criterios escritos antes de empezar.
  - **Revertida en parte el 2026-08-27, por I-14.** La mitad del encuadre -darle
    al contenedor la forma del canton- salio de leer una **captura** del profesor
    como si fuera una especificacion. El nunca pidio que el mapa mostrara solo el
    canton, y sin la region alrededor se pierde la referencia que ubica a
    Tilaran. **El pedido estaba mal, no el trabajo.**
  - **Lo que se conserva, y es la mayor parte:** la marca de seleccion accesible
    -linea clara mas halo, que era el defecto que el profesor si señalo-, el
    `zoomSnap` a 0,1 y el `bringToFront` del distrito seleccionado. La historia
    sigue cerrada con sus 3 puntos y sus 2,4 horas.

- [x] **H7.1** · Semaforo de riesgo por distrito y evento con umbrales documentados (2026-08-20)
  - `E7` · 6 pts · 5.8 h · rubrica: CG-2 · depende de: H5.3 · **bloquea a: H10.3**
  - horas: estimada 4.0 . real 2.0

## Sprint 3 (semanas 8-9) — 25.0 h

- [x] **H5.4** · Mapa de calor por interpolacion IDW (2026-08-18)
  - `E5` · 8 pts · 12.5 h · rubrica: CG-1 · depende de: H5.3
  - **Su entregable se restituye por D-30**, el 2026-08-27. La historia sigue
    cerrada y ahora vuelve a tener algo en pantalla.
  - Lo que paso, en orden: **D-28** retiro la capa el 24 de agosto sobre un
    argumento que el profesor **nunca hizo**. El reporto un defecto de recorte
    -la capa se salia del canton y dejaba distritos sin marcar-, y eso se
    convirtio, al redactar la decision, en una objecion a interpolar. **La
    implementacion de esta historia no tenia el defecto conceptual que se le
    atribuyo.** Ver **I-14**.
  - El defecto real eran dos lineas: el encuadre salia de los **centroides** y
    la superficie no se recortaba. Medido: 23,8 % de lo pintado caia fuera del
    canton y el 20,7 % del canton quedaba sin pintar. Corregido a 0 % y 0 %.
  - Lo que arreglo Alejandro con permiso escrito de Avril: encuadre desde los
    poligonos y recorte contra su union. **La opacidad, la rampa y los puntos de
    origen quedaron intactos** — eso no tenia nada malo.
  - Ahora lo vigila una maquina:
    `node frontend/herramientas/verificar_recorte_calor.mjs`, en el CI.
  - Evidencia del retiro, que se conserva:
    `docs/evidencias/computacion-grafica/D-28-retiro-mapa-calor.md`.
    De la restitucion:
    `docs/evidencias/computacion-grafica/D-30-restitucion-mapa-calor.md`.

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
