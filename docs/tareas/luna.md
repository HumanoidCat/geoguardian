# Tareas de Luis

**Luis Alejandro Luna Garcia**  
**Carpetas propias:** `backend/calidad, backend/tests, docs/investigacion`

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

- [x] **H10.5b** · Estado del arte de Costa Rica (2026-08-18)
  - `E10` · 5 pts · 13.2 h · rubrica: IEEE · depende de: H10.5a · **bloquea a: H10.5c**

- [x] **H4.3** · Catalogo de 12 o mas eventos historicos del canton con fuente (2026-08-18)
  - `E4` · 8 pts · 21.1 h · rubrica: OE3 · **bloquea a: H4.4, H7.3**


## Sprint 2 (semanas 6-7) — 31.0 h

- [x] **H1.5** · Reporte formal de calidad de datos: faltantes, atipicos, sesgos (2026-08-30)
  - `E1` · 8 pts · 12.5 h · rubrica: OE1 · depende de: H1.1
  - horas: estimada n/d (trabajo repartido entre el 20 y el 30 de agosto, no se declaro al arrancar) . real 3.0
  - El volcado se genero reejecutando la ETL de H1.1 en esta maquina, no se
    espero el de Cesar. 102272 filas, el mismo conteo que documento H1.1.
  - Hallazgo: seis de siete variables tienen 0.00 % de variacion espacial.

- [x] **H2.1** · Filtrar ruido de las series con justificacion del filtro (2026-08-18)
  - `E2` · 3 pts · 2.9 h · rubrica: Senales · depende de: H1.4 · **bloquea a: H2.2, H2.3, H2.4, H2.7**

- [x] **H2.3** · SPI de 1 y 3 meses por convolucion de ventana movil (2026-08-18)
  - `E2` · 5 pts · 7.8 h · rubrica: Senales · depende de: H2.1 · **bloquea a: H2.5, H3.0**

- [x] **H2.7** · Calcular percentiles R95p y R99p de precipitacion acumulada por distrito (2026-08-18)
  - `E2` · 5 pts · 7.8 h · rubrica: Senales · depende de: H2.1 · **bloquea a: H3.0**


## Sprint 3 (semanas 8-9) — 20.3 h

- [x] **H10.2** · Pruebas automatizadas del backend, cobertura de dominio (2026-08-30)
  - `E10` · 5 pts · 4.8 h · rubrica: QA · depende de: H6.2
  - horas: estimada 2.0 . real 1.5
  - 57 casos nuevos, 209 en la suite. Cubre 35 de los 40 del plan H10.1.
  - Hallazgo: cuatro invariantes del contrato Repositorio, tres de prioridad 1,
    que no cubre ni el simulado ni la implementacion de Postgres.

- [x] **H2.2** · Analisis espectral de la lluvia e interpretacion fisica (2026-08-30)
  - `E2` · 5 pts · 7.8 h · rubrica: Senales · depende de: H2.1
  - horas: estimada n/d (trabajo repartido entre el 20 y el 30 de agosto, no se declaro al arrancar) . real 3.5
  - Veranillo detectado en los ocho distritos, de 23 a 47 veces el modelo nulo.
    La razon varia por factor 2.10 entre distritos: la unica variable que
    discrimina espacialmente tambien cambia de estructura.

- [x] **H2.4** · Anomalias respecto a la normal climatologica 1991-2020 (2026-08-20)
  - `E2` · 3 pts · 2.9 h · rubrica: Senales · depende de: H2.1 · **bloquea a: H7.4**
  - horas: estimada n/d (la regla se creo el mismo dia del cierre) . real 2.0

- [ ] **H9.1** · Preparar SUS, guion de entrevista y dosier de 3 casos
  - `E9` · 5 pts · 4.8 h · rubrica: OE4 · **bloquea a: H9.2a**


## Sprint 4 (semanas 10-11) — 32.0 h

- [ ] **H12.4** · Diagnostico guiado a partir de la bitacora de incidencias
  - `E12` · 5 pts · 7.8 h · rubrica: Troubleshoot · depende de: H12.1 · **bloquea a: H12.5**

- [ ] **H9.2a** · Sesion de usabilidad con 3 a 5 participantes y calculo del puntaje SUS
  - `E9` · 3 pts · 7.9 h · rubrica: OE4 · depende de: H9.1 · **bloquea a: H9.2b**
  - Partida de H9.2 el 2026-08-23. Mide **usabilidad, no exactitud**, asi que se
    puede hacer HOY con datos simulados y sin esperar a H1.2. Bloques 0 a 4 y 6.
  - La banda de "modo simulado" no se oculta: se **mide**. Preguntar si el
    participante entendio que los datos no son reales responde a "comunica su
    propia incertidumbre" y es un hallazgo sobre H6.6 y D-23.
  - **No preguntar por confianza en los numeros.** Con datos simulados esa
    respuesta no significa nada, y la banda la contamina.

- [ ] **H9.2b** · Sesion de contraste: la estimacion frente a lo que la gente vivio
  - `E9` · 2 pts · 5.3 h · rubrica: OE4 · depende de: H9.2a, H3.0 · **bloquea a: H9.3, H9.4**
  - Es el bloque 5 del guion de H9.1. Contra datos simulados no mide nada: sin
    modelo, "el mapa se equivoca en Quebrada Grande" no dice nada sobre el modelo.
  - **La dependencia de H3.0 no estaba declarada.** La encontro Luna el 2026-08-23
    despues de cerrar H9.1 y dar por desbloqueada H9.2. Por H3.0 depende de H1.2.
  - Reclutamiento **distinto** al de H9.2a: aqui hacen falta personas que vivieron
    esos eventos en ese distrito. No tiene que ser la misma gente.

- [ ] **H9.3** · Someter los umbrales de incendio a criterio de los participantes
  - `E9` · 3 pts · 7.9 h · rubrica: OE4 · depende de: H9.2b, H1.2

- [ ] **H9.4** · Incorporar un cambio derivado de la retroalimentacion
  - `E9` · 2 pts · 3.1 h · rubrica: OE4 · depende de: H9.2b

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
