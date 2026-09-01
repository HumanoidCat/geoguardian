# Tareas de Cesar

**Cesar Andres Ubau Calvo**  
**Carpetas propias:** `backend/api, backend/etl, basedatos`

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

**Total asignado:** 125 puntos · 154 horas · 15.4 h por semana en promedio

## Carga por sprint

| Sprint | Semanas | Horas | Capacidad | Estado |
|---|---|---|---|---|
| S0 | semanas 2-3 | 18.3 | 36 | holgado |
| S1 | semanas 4-5 | 30.9 | 36 | ajustado |
| S2 | semanas 6-7 | 31.5 | 36 | ajustado |
| S3 | semanas 8-9 | 39.2 | 36 | SOBRECARGA +3 h |
| S4 | semanas 10-11 | 34.0 | 36 | ajustado |

## Sprint 0 (semanas 2-3) — 18.3 h

- [x] **H1.1** · Descargar 35 anios de series climaticas diarias (1991-2025), reejecutable e idempotente (2026-08-19)
  - `E1` · 5 pts · 7.8 h · rubrica: BD-1 · depende de: H1.3 · **bloquea a: H1.4, H1.5, H8.2**
  - Fuente: CHIRPS para precipitacion, NASA POWER para el resto. Ver **D-15** e **I-05**
  - Antes de implementar: verificar que CHIRPS si diferencia entre distritos, con
    el mismo test de dos puntos que descarto a POWER
  - Evidencia: `docs/evidencias/bases-de-datos/H1.1-series-climaticas.md`

- [x] **H1.2** · Descargar historico de focos de calor filtrado al canton (2026-08-24)
  - `E1` · 3 pts · 4.7 h · rubrica: BD-1 · depende de: H1.3 · **bloquea a: H3.0, H9.3**
  - Evidencia: `docs/evidencias/bases-de-datos/H1.2-focos-calor.md`
  - horas: estimada n/d (se comprometio una fecha, no una cantidad de horas) . real 6.0
  

- [x] **H1.3** · Cargar geometrias oficiales de distritos con SRID validado (2026-08-13)
  - `E1` · 6 pts · 5.8 h · rubrica: BD-1, BD-3 · depende de: contratos · **bloquea a: H1.1, H1.11, H1.2, H1.8**
  - Evidencia: `docs/evidencias/bases-de-datos/H1.3-ddl-geometrias.md`


## Sprint 1 (semanas 4-5) — 24.9 h

- [x] **H1.4** · Declarar los criterios de imputacion y probarlos contra huecos inyectados (2026-08-27)
  - `E1` · 3 pts · 4.7 h · rubrica: BD-1 · depende de: H1.1 · **bloquea a: H1.7**
  - Reducida por **D-22** el 2026-08-20: las series de H1.1 no tienen un solo
    faltante en 12 784 dias, asi que la historia pierde *aplicar* y conserva
    *declarar la regla y probarla contra huecos inyectados*.
  - **La dependencia de H2.1 quedo obsoleta**, porque H2.1 se cerro sin ella.
  - Evidencia: `docs/evidencias/bases-de-datos/H1.4-criterios-imputacion.md`
  - horas: estimada n/d (no hubo estimacion propia previa) . real 0.5

- [x] **H1.7** · Versionar el dataset consolidado para reproducibilidad (2026-08-27)
  - `E1` · 3 pts · 2.9 h · rubrica: OE1 · depende de: H1.4
  - Evidencia: `docs/evidencias/bases-de-datos/H1.7-manifiesto-dataset.md`
  - horas: estimada n/d (no hubo estimacion propia previa) . real 0.5

- [x] **H1.8** · Crear esquemas, roles y usuarios con minimo privilegio (2026-08-19)
  - `E1` · 5 pts · 4.8 h · rubrica: BD-2 · depende de: H1.3 · **bloquea a: H1.13, H1.9, H10.7**
  - Evidencia: `docs/evidencias/bases-de-datos/H1.8-roles-minimo-privilegio.md`

- [x] **H6.0** · Dockerfile de la API y del visor con imagen construida localmente (2026-08-27)
  - `E6` · 3 pts · 2.9 h · rubrica: CICD · depende de: H6.1 · **bloquea a: H11.1**
  - Evidencia: `docs/evidencias/arquitectura-software/H6.0-imagenes-docker.md`
  - horas: estimada n/d (no hubo estimacion propia previa) . real 2.5

- [x] **H6.1** · API REST con OpenAPI y esquemas Pydantic en todos los endpoints (2026-08-19)
  - `E6` · 5 pts · 4.8 h · rubrica: Arq · depende de: contratos · **bloquea a: H11.1, H6.0, H6.2, H6.5, H7.2, H8.3**
  - Evidencia: `docs/evidencias/arquitectura-software/H6.1-api-rest-openapi.md`

- [x] **H6.2** · Patron Repository con pruebas unitarias sin base de datos (2026-08-27)
  - `E6` · 5 pts · 4.8 h · rubrica: Arq · depende de: H6.1 · **bloquea a: H10.2, H6.3**
  - Evidencia: `docs/evidencias/arquitectura-software/H6.2-repositorio-postgres.md`
  - horas: estimada n/d (no hubo estimacion propia previa) . real 3.0


## Sprint 2 (semanas 6-7) — 0.0 h

## Sprint 3 (semanas 8-9) — 47.0 h

- [ ] **H1.14** · Ingesta reejecutable con cadencia declarada por evento y producto declarado
  - `E1` · 5 pts · 7.8 h · rubrica: BD-1 · depende de: H1.1, H1.2
  - Agregada el 2026-08-23 por **D-26**. Hueco del backlog: de las 86 historias,
    **ninguna volvia a consultar las fuentes**. H1.1 es una descarga historica de
    una vez, asi que el sistema era una foto y no un servicio.
  - **La cadencia no es una sola.** Incendio a diario, porque FIRMS llega en 3 h.
    Sequia semanal como mucho: el final de CHIRPS tarda de 21 a 51 dias, y ademas
    el SPI-3 mira 90 dias de los que 83 ya se conocian ayer.
  - Tiene que **declarar que producto cargo**: el preliminar de CHIRPS es "GTS and
    Mexico only" y no es el mismo dato que el final. Mismo criterio que D-17 con
    la precipitacion y que D-25 con la era de FIRMS.
  - Idempotente: correrla dos veces el mismo dia no duplica filas. Es el defecto
    que Luna encontro en H1.5, donde una fila repetida escondia un dia ausente.
  - **No resuelve donde se ejecuta.** No hay entorno alojado: los overlays de
    Kubernetes son locales. La programacion queda declarada y sin destino.
  - **RENOMBRADA el 2026-08-27**, de «Ingesta periodica de las tres fuentes». Lo
    planteo Cesar y el PM lo acepto: *una ingesta programada contra una base que
    solo existe cuando alguien levanta `docker compose` no es periodica, es un
    guion con un `cron` escrito al lado.* La historia se cierra con lo que si
    demuestra -cadencia, producto declarado, idempotencia- y **donde corre sale a
    la historia de alojamiento**, todavia sin abrir.
  - **Y por D-31, esta historia NO regenera el manifiesto de H1.7.** Emite su
    recibo de carga en la base y termina. El manifiesto es una version que se
    corta a mano; perseguir con el a un dataset que se mueve destruiria la
    propiedad que lo hace util.


- [ ] **H1.10** · Estrategia de respaldo definida y restauracion probada
  - `E1` · 5 pts · 7.8 h · rubrica: BD-4 · depende de: H1.9

- [ ] **H12.1** · Centralizar los logs de pipeline y aplicacion en control.bitacora_etl
  - `E12` · 5 pts · 4.8 h · rubrica: Troubleshoot · depende de: H1.9 · **bloquea a: H12.2, H12.4**

- [ ] **H3.4** · Entrenar y evaluar Random Forest
  - `E3` · 6 pts · 9.4 h · rubrica: OE2 · depende de: H3.2

- [ ] **H3.5** · Entrenar y evaluar XGBoost
  - `E3` · 6 pts · 9.4 h · rubrica: OE2 · depende de: H3.2 · **bloquea a: H3.6**

- [ ] **H8.2** · ETL concurrente con medicion secuencial contra paralelo
  - `E8` · 5 pts · 7.8 h · rubrica: SO-1 · depende de: H1.1


## Sprint 4 (semanas 10-11) — 34.0 h

- [ ] **H12.3** · Alertas automaticas ante fallo de pipeline o despliegue
  - `E12` · 5 pts · 7.8 h · rubrica: Troubleshoot · depende de: H11.2

- [ ] **H2.6** · Documentar seleccion de variables y descartar redundantes
  - `E2` · 5 pts · 7.8 h · rubrica: OE2 · depende de: H2.5

- [ ] **H3.7** · Versionar modelos con metricas y fecha asociadas
  - `E3` · 3 pts · 2.9 h · rubrica: Arq · depende de: H3.6

- [ ] **H6.3** · Strategy y Factory: agregar una fuente sin tocar el orquestador
  - `E6` · 5 pts · 4.8 h · rubrica: Arq · depende de: H6.2

- [ ] **H8.3** · Cache en memoria con politica de expiracion y consumo medido
  - `E8` · 5 pts · 7.8 h · rubrica: SO-1 · depende de: H6.1

- [ ] **H8.4** · Estrategia de almacenamiento de rasters con proyeccion de crecimiento
  - `E8` · 3 pts · 2.9 h · rubrica: SO-1 · depende de: H1.6

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
