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

**Total asignado:** 69 puntos · 85.0 horas · 8.5 h por semana en promedio

## Carga por sprint

| Sprint | Semanas | Horas | Capacidad | Estado |
|---|---|---|---|---|
| S0 | semanas 2-3 | 18.3 | 36 | holgado |
| S1 | semanas 4-5 | 24.9 | 36 | holgado |
| S2 | semanas 6-7 | 0.0 | 36 | holgado |
| S3 | semanas 8-9 | 7.8 | 36 | holgado |
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

## Sprint 3 (semanas 8-9) — 7.8 h

> **Actualizado el 2026-09-03 por D-37 y D-38.** H3.4, H3.5 y H12.1 salieron de
> esta lista por D-37 (las dos primeras a Alejandro, la tercera a Luna). H1.14 y
> H8.2 salieron por D-38: Cesar las declino por escrito y el PM las tomo. Queda
> H1.10, entregada en el PR #250.

- [x] **H1.10** · Estrategia de respaldo definida y restauracion probada (2026-09-03)
  - `E1` · 5 pts · 7.8 h · rubrica: BD-4 · depende de: H1.9
  - horas: estimada 7.8 . real 8.0
  - Evidencia: `docs/evidencias/bases-de-datos/H1.10-criterios-aceptacion.md`, `docs/evidencias/bases-de-datos/H1.10-respaldo-restauracion.md`. PR #250.

## Sprint 4 (semanas 10-11) — 34.0 h

> **Compromiso escrito de Cesar, 2026-09-03 (D-38):** H12.3, H6.3 y H8.4 en la
> semana 10 (15,5 h, 13 pts). H3.7 si H3.6 cierra a tiempo. **H2.6 y H8.3
> quedan diferidas** por D-38.

- [ ] **H12.3** · Alertas automaticas ante fallo de pipeline o despliegue
  - `E12` · 5 pts · 7.8 h · rubrica: Troubleshoot · depende de: H11.2

- [ ] **H2.6** · Documentar seleccion de variables y descartar redundantes
  - `E2` · 5 pts · 7.8 h · rubrica: OE2 · depende de: H2.5
  - **Diferida el 2026-09-03 por D-38.**

- [ ] **H3.7** · Versionar modelos con metricas y fecha asociadas
  - `E3` · 3 pts · 2.9 h · rubrica: Arq · depende de: H3.6

- [ ] **H6.3** · Strategy y Factory: agregar una fuente sin tocar el orquestador
  - `E6` · 5 pts · 4.8 h · rubrica: Arq · depende de: H6.2
  - Entregada el 2026-09-03 y esperando fila en `docs/trazabilidad.csv`, que es de
    Alejandro. Se marca `[x]` cuando la fila exista: `generar_matriz.py` falla si una
    historia cerrada no la tiene, y `verificar_horas.py` rechaza declarar horas de
    algo que sigue abierto. Al marcarla va la linea `estimada 4.8 . real 5.0`.
  - Evidencia: `docs/evidencias/arquitectura-software/H6.3-strategy-y-factory.md`
  - Construye la Factory, **no** el orquestador: no existe. Los criterios daban por
    hecho cuatro implementaciones y son dos: `ExtractorChirps` y `ExtractorPower` no
    cumplen `ExtractorClima` -no tienen `extraer()`-. Correccion anotada en los criterios.

- [ ] **H8.3** · Cache en memoria con politica de expiracion y consumo medido
  - `E8` · 5 pts · 7.8 h · rubrica: SO-1 · depende de: H6.1
  - **Diferida el 2026-09-03 por D-38.**

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
