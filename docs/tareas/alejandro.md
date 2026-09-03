# Tareas de Alejandro

**Alejandro Josue Rodriguez Zamora**  
**Carpetas propias:** `backend/senales, backend/modelado, infra, docs, .github/workflows`

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

**Total asignado:** 177 puntos · 272.5 horas · 27.3 h por semana en promedio

## Carga por sprint

| Sprint | Semanas | Horas | Capacidad | Estado |
|---|---|---|---|---|
| S0 | semanas 2-3 | 35.9 | 36 | ajustado |
| S1 | semanas 4-5 | 36.4 | 36 | SOBRECARGA +0 h |
| S2 | semanas 6-7 | 103.6 | 36 | SOBRECARGA +68 h |
| S3 | semanas 8-9 | 43.8 | 36 | SOBRECARGA +8 h |
| S4 | semanas 10-11 | 52.8 | 36 | SOBRECARGA +17 h |

> **Sobre los picos.** El pipeline de CI/CD, el modelado, la documentacion y la
> evaluacion se concentran aqui por decision propia. La auditoria de dependencias
> del 11 de agosto ya descargo 17.4 h a Avril (manual de usuario, diagramas y
> manual de operacion) y 17.2 h a Cesar (XGBoost y alertas), y aun asi quedan
> 202 h contra 180 de capacidad.
>
> Las dos concentraciones que quedan son estructurales, no de reparto: el Sprint
> 2 junta la cadena de despliegue continuo con el arranque del modelado, y las
> dos preceden al primer avance de la semana 7; el Sprint 4 junta el documento
> IEEE con el analisis de fallos, y ninguno se puede adelantar porque dependen de
> tener resultados.
>
> **Palanca disponible si el Sprint 4 se vuelve inviable:** H4.4 son 26.4 h en
> una sola historia, la mas grande del backlog. Se puede partir dejando el
> contraste contra el catalogo a Luna, que lo construye en H4.3.


## Sprint 0 (semanas 2-3) — 35.9 h

- [x] **H10.8** · Carpeta de evidencias organizada por materia con indice (2026-08-11)
  - `E10` · 5 pts · 4.8 h · rubrica: SO-4

- [x] **H6.4** · Seis o mas registros ADR escritos (2026-08-11)
  - `E6` · 3 pts · 7.9 h · rubrica: Arq

- [x] **H8.1** · docker compose up levanta todo en maquina limpia (2026-08-03)
  - `E8` · 5 pts · 7.8 h · rubrica: SO-1 · **bloquea a: H10.4, H8.6**

- [x] **H8.5** · Credenciales por variables de entorno, fuera del repositorio (2026-08-11)
  - `E8` · 3 pts · 2.9 h · rubrica: SO-1

- [x] **H8.6** · Manifiestos de Kubernetes corriendo en k3d local (2026-08-11)
  - `E8` · 8 pts · 12.5 h · rubrica: Arq · depende de: H8.1


## Sprint 1 (semanas 4-5) — 36.4 h


- [x] **H1.15** · Crear `analitico.riesgo` con sus restricciones (2026-09-01)
  - Evidencia: `docs/evidencias/bases-de-datos/H1.15-analitico-riesgo.md`
  - Migracion `006_analitico_riesgo.sql`, verificador `basedatos/verificar_h1_15.py`:
    **15 de 15 criterios** contra PostgreSQL 16.2. Cada restriccion se
    ejercita intentando violarla.
  - horas: estimada 2.9 . real 2.0
  - `E1` · 3 pts · 2.9 h · rubrica: BD-2 · depende de: H1.3, H1.8 · **bloquea a: H1.13**
  - **Abierta el 2026-08-27** por decision del PM, despues de que la detectaras
    al intentar H1.13. La tabla no existia y ninguna historia la creaba.
  - **No se metio dentro de H1.13** a proposito: esa historia es el disparador de
    auditoria, y juntar el esquema con el disparador hace que discutir uno
    arrastre al otro.
  - Se puede construir y probar **contra una tabla vacia**, asi que no espera al
    modelo de E3.
  - Dos cosas que el DDL tiene que cumplir, y no son negociables:
    - `probabilidad` es **P(nivel = alto)**, por **D-21**. Que el `COMMENT` de la
      columna lo diga, no solo el contrato.
    - **La ausencia es `NULL`, nunca `0`.** Un distrito sin estimacion tiene que
      poder distinguirse de uno con riesgo bajo. Es **D-07**, y es lo que el
      etiquetado y el visor ya hacen.
  - **Traspasada desde Cesar el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.

- [x] **H1.13** · Trigger de auditoria sobre predicciones, con prueba (2026-09-01)
  - Evidencia: `docs/evidencias/bases-de-datos/H1.13-auditoria-riesgo.md`
  - Migracion `008_auditoria_riesgo.sql`, verificador `basedatos/verificar_h1_13.py`:
    **12 de 12 criterios** contra PostgreSQL real. Cada uno cambia una fila y
    mira si aparecio el registro.
  - horas: estimada 2.9 . real 1.5
  - `E1` · 3 pts · 2.9 h · rubrica: BD-2 · depende de: H1.8, H1.15
  - **Desbloqueada el 2026-08-27.** Estuvo detenida porque `analitico.riesgo` no
    existia y ninguna historia la creaba, con H1.8 -su dependencia declarada- ya
    cerrada. Ahora depende tambien de **H1.15**, que si la crea.
  - La dependencia es real y medida, no inventada para desatascar el tablero.
  - **Traspasada desde Cesar el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.

- [x] **H1.6** · Descargar imagenes Sentinel-2 de estacion seca, nubosidad menor a 20% (2026-09-03)
  - `E1` · 5 pts · 7.8 h · rubrica: CG-3 · **bloquea a: H5.5, H8.4**
  - Evidencia: `docs/evidencias/computacion-grafica/H1.6-sentinel2-estacion-seca.md`
  - **Seis escenas** en la estacion seca 2024-25 con nubosidad bajo 20 %, todas en
    el mosaico T16PGS. Comprobado contra el catalogo, no supuesto.
  - **Se bajan 4 bandas de 20 m y no el producto entero**: 49,6 MB por escena en
    vez de 555 a 929 MB. 4,4 GB no caben con comodidad en la maquina de nadie del
    equipo, asi que la diferencia es entre una historia que corre y una que no.
  - **A 20 m el infrarrojo cercano es `B8A`, no `B08`.** Encontrado listando el
    producto; copiar la formula del NDVI sin mirar habria pedido un archivo que no
    esta ahi.
  - La busqueda **no necesita credenciales** y la descarga si, asi que el
    verificador corre en el CI sin poner un secreto ahi.
  - Al correrlo aparecio un defecto propio: **dos formas de leer el `.env`**, una
    en el comprobador y otra en el extractor, y solo una funcionaba. Es I-27
    otra vez. Queda `load_dotenv()`, que es lo que el proyecto ya usaba.
  - horas: estimada 7.8 . real 4.0
  - **Traspasada desde Avril el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.
- [ ] **H10.4** · Manual tecnico verificado por alguien ajeno al desarrollo
  - `E10` · 5 pts · 4.8 h · rubrica: MVP · depende de: H8.1

- [x] **H11.1** · CI: construir imagen Docker y publicar artefactos en ghcr.io (2026-09-01)
  - `E11` · 5 pts · 4.8 h · rubrica: CICD · depende de: H6.0, H6.1 · **bloquea a: H11.2**
  - Evidencia: `docs/evidencias/sistemas-operativos/H11.1-imagenes-ghcr.md`
  - El verificador corre las imagenes y **encontro que el visor no arrancaba
    fuera de docker compose**. Arreglado por SC-07. api 6 de 6, visor 8 de 8.
  - horas: estimada 4.8 . real 5.5

- [x] **H13.1** · Actas de las ceremonias Scrum: planning, dailies, review y retrospectiva (2026-08-16)
  - `E13` · 5 pts · 13.2 h · rubrica: Scrum


## Sprint 2 (semanas 6-7) — 103.6 h


- [x] **H1.9** · Funciones PL/pgSQL con EXCEPTION WHEN, RAISE y bitacora de fallos (2026-09-01)
  - Evidencia: `docs/evidencias/bases-de-datos/H1.9-funciones-y-bitacora.md`
  - Migracion `009_funciones_y_bitacora_fallos.sql`, verificador
    `basedatos/verificar_h1_9.py`: **22 de 22 criterios** contra PostgreSQL real.
    Cada uno provoca el error y mira si la funcion siguio y si dejo registro.
  - `control.fallo` mas `analitico.registrar_riesgo` y `registrar_riesgo_lote`.
    La regla del modulo es **se puede continuar, nunca callar**.
  - Tres defectos aparecieron solo al ejecutar: `numeric(5,4)` desborda antes de
    que corra el CHECK, `'ayer'::date` da 22007 y no 22P02, y las conversiones
    del lote ocurrian **fuera** del bloque que las atrapaba.
  - De paso quedaron registradas **I-18** -que se referenciaba en cuatro sitios y
    nunca se habia escrito- e **I-19**, el hallazgo de Cesar sobre los esquemas.
  - horas: estimada 7.7 . real 3.4
  - `E1` · 8 pts · 7.7 h · rubrica: BD-3 · depende de: H1.8 · **bloquea a: H1.10, H12.1**
  - **Traspasada desde Cesar el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.

- [x] **H1.11** · Particionar mediciones por anio y medir efecto en consultas (2026-09-01)
  - Evidencia: `docs/evidencias/bases-de-datos/H1.11-particionado-medicion.md`
  - Migracion `010_particionar_medicion.sql`, verificador
    `basedatos/verificar_h1_11.py`: **14 de 14 criterios** contra PostgreSQL real.
    99 296 filas migradas en 1.54 s, 37 particiones, la DEFAULT vacia.
  - **El efecto se midio, no se supuso.** `basedatos/medir_particionado.py`
    construye las dos formas de la tabla con las mismas filas y corre las mismas
    consultas: el visor mejora **84 %**, el pliegue de H3.2 **35 %**, y el
    agregado anual empeora **4 %**. Se adopta porque lo que mejora esta en el
    camino del usuario y lo que empeora corre fuera de linea.
  - **I-20**: el arreglo de I-18 solo habia tocado una de las tres tablas, y los
    controles que se escribieron para atajarlo miraban una tabla cada uno. El
    criterio 14 ahora recorre los cuatro esquemas enteros.
  - El criterio 6 es el que mas vale: comprueba que el upsert idempotente de H1.1
    sobrevive al particionado. Si fallara, la ingesta duplicaria en silencio.
  - horas: estimada 4.8 . real 3.1
  - `E1` · 5 pts · 4.8 h · rubrica: BD-1 · depende de: H1.3 · **bloquea a: H1.12**
  - **Traspasada desde Cesar el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.

- [x] **H1.12** · Indices espaciales y compuestos con planes antes y despues (2026-09-01)
  - Evidencia: `docs/evidencias/bases-de-datos/H1.12-indices.md`
  - Migracion `011_indices.sql`, verificador `basedatos/verificar_h1_12.py`:
    **11 criterios que miran el PLAN**, no el catalogo. Un indice que existe y el
    planificador nunca elige es coste puro.
  - **Se midieron cuatro candidatos y entraron tres.** `medicion_fecha_ix` se
    descarto: la consulta iba 8 % mas rapida con el creado, pero el indice **no
    aparece en el plan**. Ese 8 % era cache. Es el motivo por el que el banco
    comprueba el plan y no solo el reloj.
  - **El criterio de aceptacion estaba mal planteado y la medicion lo dijo.**
    Empezo en «ahorra mas de 0,5 ms» y eso descartaba `riesgo_fecha_evento_ix`
    por 0,05 ms. Midiendo a cuatro tamanos, el ahorro crece de 0,49 ms a 10,09 ms
    -de 8,5x a 90,6x- mientras la consulta indexada se queda plana. La regla paso
    a ser **que tipo de escaneo reemplaza**, no cuantos milisegundos ahorra hoy.
  - El punto de partida era **un solo indice secundario en todo el proyecto**.
  - horas: estimada 4.8 . real 2.8
  - `E1` · 5 pts · 4.8 h · rubrica: BD-1 · depende de: H1.11
  - **Traspasada desde Cesar el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.

- [x] **H2.5** · Generar lags, acumulados y medias moviles reproducibles (2026-09-01)
  - Evidencia: `docs/evidencias/senales-y-sistemas/H2.5-caracteristicas.md`
  - `backend/senales/caracteristicas.py`, 16 pruebas. La que importa es la de
    fuga al futuro, **comprobada contra una fuga real de un solo dia**.
  - horas: estimada 4.8 . real 3.0
  - `E2` · 5 pts · 4.8 h · rubrica: OE2 · depende de: H2.3 · **bloquea a: H2.6**
  - **Traspasada desde Cesar el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.

- [x] **H3.3** · Entrenar y evaluar Regresion Logistica (2026-09-01)
  - Evidencia: `docs/evidencias/objetivos/H3.3-regresion-logistica.md`
  - `generar_caracteristicas.py` arma la matriz desde `crudo.medicion_diaria` con
    las transformaciones de H2.5; `comparar()` la consume y el estimador entra en
    la tabla de H3.6. **17 criterios** en `verificar_h33.py` y **11 pruebas** en
    `test_generar_caracteristicas.py`.
  - Tres defectos aparecieron midiendo la matriz: un umbral absoluto que la
    ventana de 3 dias no puede cumplir nunca -0 % de rendimiento-, acumulados
    colineales con sus medias en las variables que no se suman, y columnas
    constantes que `StandardScaler` no denuncia. De 44 columnas a 27.
  - **D-34 pasa del ADR al codigo**: la sequia queda declarada no modelable, con
    sus 9 episodios contra los 30 que pide CA-6 de H3.0.
  - El estimador ya estaba escrito y probado desde el PR #217; esta entrega es la
    matriz y el cableado.
  - horas: estimada 9.4 . real 4.2
  - `E3` · 6 pts · 9.4 h · rubrica: OE2 · depende de: H3.2 · **bloquea a: H3.4, H3.5**
  - **Traspasada desde Cesar el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.

> **H5.6 volvio a Avril el 2026-09-02**, por la clausula de devolucion de D-33:
> «quien retome algo suyo lo avisa y se le devuelve, sin pedir permiso». Estaba
> terminada y verificada antes del traspaso y se cierra el mismo dia. La entrada
> vive ahora en `docs/tareas/avril.md`.

- [x] **H7.2** · Graficas interactivas de series con seleccion de rango (2026-09-03)
  - `E7` · 5 pts · 4.8 h · rubrica: CG-2 · depende de: H6.1
  - **Traspasada desde Avril el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.
  - Evidencia: `docs/evidencias/computacion-grafica/H7.2-graficas-de-serie.md`
  - Excepcion de propiedad declarada **antes** de tocar `frontend/`, en
    `docs/07-propiedad-archivos.md`.
  - **Los huecos cortan la linea.** El simulado trae un dia sin dato de cada
    veinte y viajan como `null` hasta el dibujo: unir la linea por encima
    afirmaria una medicion que nadie tomo. El exportador se planta si la serie
    sale sin ningun hueco, porque entonces el criterio no podria fallar.
  - **El respaldo estatico tambien tiene serie** (`mediciones.json`, 239 KB): sin
    eso la grafica no existiria en el visor publicado por H11.5, que es el unico
    que alguien puede abrir sin levantar nada.
  - **Medido, no supuesto:** `recharts` llevaba el paquete inicial de 325 a
    710 kB. Con carga perezosa queda en 332 kB y los 379 kB del dibujo se piden
    al abrir una ficha. Salio de construir las dos versiones.
  - horas: estimada 4.8 . real 3.5

- [x] **H10.7** · Diagramas de casos de uso y entidad-relacion (2026-09-02)
  - `E10` · 5 pts · 7.8 h · rubrica: Arq · depende de: H1.8
  - **Traspasada desde Avril el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.
  - Evidencia: `docs/evidencias/arquitectura-software/H10.7-diagramas-casos-de-uso.md`
  - **El entidad-relacion ya existia desde H6.5** y nadie lo habia anotado: la
    historia figuraba entera cuando le faltaba una mitad. Solo se entrego el de
    casos de uso.
  - Se derivo de `backend/api/rutas.py` en vez de dibujarlo. **CA-6** comprueba
    que las 6 rutas aparezcan y que el diagrama no declare ninguna que ya no
    exista. Su primera version **no distinguia** -leia el SVG generado, que solo
    cambia al regenerar-; se descubrio intentando romperla.
  - horas: estimada 7.8 . real 2.5
- [x] **H6.6** · El visor consume la API real en lugar de los JSON estaticos (2026-08-20)
  - `E6` · 5 pts · 4.8 h · rubrica: Arq · depende de: H6.1
  - horas: estimada n/d (la regla se creo el mismo dia del cierre) . real 3.0
  - Hueco del backlog detectado el 2026-08-18: ninguna de las 83 historias cubria
    el cambio de origen de datos del visor, y esta en la ruta critica del
    prototipo. Al cerrarla hay que anotar **D-14** como revisada.
  - Excepcion de propiedad: autoriza a tocar `frontend/src/datos/cliente.js` y la
    configuracion de entorno del visor, nada mas. Ver `docs/07-propiedad-archivos.md`.
  - **D-14 anotada como revisada por D-23.** Ningun componente cambio, que era la
    prueba de que la costura estaba bien puesta. Produjo ademas **SC-03**,
    contratos a v1.3.1, e **I-08**: la API devolvia un valor distinto en cada
    lectura y, desde D-21, filas imposibles.
  - Queda fuera de esta historia, por bloqueo de **H6.0**: el servicio de API en
    `docker-compose.yml`. La verificacion se hizo con `uvicorn` a mano.
  - Queda pendiente de Avril, por solicitud: pintar `origen` y `motivo_respaldo`
    en `AvisoModoSimulado.jsx`. El cliente ya los devuelve.

- [x] **H11.2** · CD: despliegue automatico al entorno de desarrollo al mergear a main (2026-09-03)
  - `E11` · 5 pts · 7.8 h · rubrica: CICD · depende de: H11.1 · **bloquea a: H11.3, H12.3**
  - Evidencia: `docs/evidencias/sistemas-operativos/H11.2-H11.4-entrega-continua.md`
  - Corrida `CD #4`, commit `8bb6849`. **8 de 8 comprobaciones** contra el cluster
    efimero, incluido un `GET /salud` desde dentro.
  - Encadenado al CI con `workflow_run`: en `push` simple corria a la vez que la
    construccion de la imagen y moria con `manifest unknown`. Es **I-26**.
  - horas: estimada 7.8 . real 9.0

- [x] **H11.3** · CD: despliegue a staging en namespace propio, con aprobacion manual (2026-09-03)
  - `E11` · 3 pts · 4.7 h · rubrica: CICD · depende de: H11.2 · **bloquea a: H11.4**
  - Evidencia: `docs/evidencias/sistemas-operativos/H11.2-H11.4-entrega-continua.md`
  - **8 de 8** contra el cluster y **2 de 2** de aprobacion. La aprobacion quedo
    registrada en la corrida a las 03:27.
  - `--comprobar-aprobacion` consulta la API de GitHub: un flujo puede declarar
    `environment: pruebas` y salir verde aunque ese entorno no tenga revisores.
  - horas: estimada 4.7 . real 3.0

- [x] **H11.4** · CD: despliegue a produccion con aprobacion explicita y rollback automatico (2026-09-03)
  - `E11` · 5 pts · 7.8 h · rubrica: CICD · depende de: H11.3 · **bloquea a: H13.2**
  - Evidencia: `docs/evidencias/sistemas-operativos/H11.2-H11.4-entrega-continua.md`
  - **La reversion se provoco, no se declaro.** Disparo manual con
    `probar_reversion=true`: se desplego una etiqueta inexistente, el rollout no
    convergio en cuatro minutos, entro `rollout undo` y `--tras-reversion` dio
    **8 de 8**, con `api volvio a la revision anterior` y `200 en /salud`.
  - Mirando los nombres de los pods se vio que **la corrida demuestra dos cosas
    distintas**: con `Recreate` la API estuvo caida de verdad y la reversion la
    devolvio; con `RollingUpdate` el pod del visor nunca se fue, asi que su
    reversion fue preventiva. Anotado en la evidencia, no previsto.
  - horas: estimada 7.8 . real 11.0

- [x] **H3.0** · Implementar el etiquetado de los tres eventos y su distribucion de clases (2026-08-25)
  - `E3` · 8 pts · 12.5 h · rubrica: OE2 · depende de: H2.3, H2.7, H1.2 · **bloquea a: H3.1, H3.2**
  - horas: estimada 3.0 . real 4.5
  - Evidencia: `docs/evidencias/objetivos/H3.0-etiquetado.md`
  - **Los tres eventos son modelables.** 99 296 filas, 8 distritos x 12 412
    fechas. Incendio 106 episodios, sequia 110, lluvia intensa 496, contra un
    umbral de 30 escrito antes de mirar el dato.
  - El reparto del incendio **reproduce D-25 sin estar programado**: Santa Rosa,
    Libano y Tierras Morenas concentran el 88 %, y Arenal y Cabeceras tienen
    7 filas de 12 412 cada uno.
  - **Deja dos requisitos para H3.2:** la particion corta por episodio y no por
    fila, y la sequia arrastra bloques de 66 filas, mas de dos meses.

- [x] **H3.1** · Construir la linea base climatologica por distrito, mes y tipo de evento (2026-08-26)
  - `E3` · 6 pts · 9.4 h · rubrica: OE2 · depende de: H3.0
  - horas: estimada 5.0 . real 3.5
  - Criterios escritos antes en `docs/evidencias/objetivos/H3.1-criterios-aceptacion.md`;
    evidencia en `H3.1-linea-base.md`.
  - **La primera version degeneraba en la trivial.** Predecir la clase modal por
    distrito-mes da BAJO en las 96 celdas, porque la minoritaria es del 1-7 %. Se
    cambio a realce sobre la tasa base.
  - De la prediccion escrita antes acerte dos de tres: la lluvia arriba (+0,036) y
    la sequia cerca (-0,070, que **confirma D-19**). El incendio da +0,006, por
    debajo del margen, y el margen **no se movio**.


- [x] **H3.2** · Definir y documentar la validacion por ventana expansiva (2026-08-26)
  - `E3` · 8 pts · 12.5 h · rubrica: OE2 · depende de: H3.0 · **bloquea a: H3.3, H3.4, H3.5**
  - horas: estimada 6.0 . real 4.0
  - Criterios escritos antes en `docs/evidencias/objetivos/H3.2-criterios-aceptacion.md`;
    evidencia en `H3.2-ventana-expansiva.md`.
  - **El codigo corrigio dos de mis tres estimaciones del embargo.** CA-2 estimo
    9 dias para la lluvia y 38 para la sequia; salen 7 en los tres eventos. La
    sequia porque **CA-3 la absorbe**: con el corte en frontera de mes, exigir que
    la etiqueta no mire dentro de la prueba equivale a siete dias.
  - Desbloquea H3.3 de Cesar, que la tiene en su Sprint 2.


## Sprint 3 (semanas 8-9) — 43.8 h

- [ ] **H3.4** · Entrenar y evaluar Random Forest
  - `E3` · 6 pts · 9.4 h · rubrica: OE2 · depende de: H3.2
  - **Traspasada desde Cesar el 2026-09-03** por **D-37**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el Sprint 3, y su contenido queda tal como estaba escrito.

- [ ] **H3.5** · Entrenar y evaluar XGBoost
  - `E3` · 6 pts · 9.4 h · rubrica: OE2 · depende de: H3.2 · **bloquea a: H3.6**
  - **Traspasada desde Cesar el 2026-09-03** por **D-37**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el Sprint 3, y su contenido queda tal como estaba escrito.

- [ ] **H3.6** · Tabla comparativa de tres algoritmos contra la linea base, por evento
  - `E3` · 10 pts · 15.6 h · rubrica: OE2 · depende de: H3.5 · **bloquea a: H3.7, H3.8, H4.1, H4.4**
  - **Entregado el arnes y el contrato, el 2026-08-27. NO se marca `[x]`**: la
    historia dice «tres algoritmos» y los tres -H3.3, H3.4 y H3.5, de Cesar- no
    existen. Cerrarla con dos lineas base seria declarar hecho el contraste de
    **D-09**, que es lo que esta historia tiene que probar.
  - Lo que si esta: `backend/modelado/comparar.py` fija la particion, la metrica,
    el trato de los `None` y el contrato `Estimador` que los tres tienen que
    cumplir. Agregar un algoritmo a la tabla es agregar una entrada a
    `DISPONIBLES`.
  - Medido hoy con las dos lineas base: la climatologica **gana en lluvia**
    (+0,036), y en **sequia e incendio hay empate tecnico** porque la dispersion
    entre pliegues supera la ventaja. En incendio la dispersion es **23 veces**
    la ventaja: explica por que H3.1 no pudo concluir.
  - Verificador `backend/modelado/verificar_h36.py`, 31 comprobaciones, en el CI.
    Evidencia en `docs/evidencias/objetivos/H3.6-tabla-comparativa.md`.
  - **Desbloquea parcialmente el documento IEEE:** la seccion VI deja de estar
    vacia y reporta lo que si esta medido.

- **Diagramas del proyecto** — 2026-08-27, sin historia propia todavia
  - `docs/herramientas/generar_diagramas.py` produce seis: entidad-relacion,
    flujo de datos, componentes, secuencia, despliegue y flujo de modelado.
  - El **entidad-relacion es derivado**: sale de parsear `basedatos/ddl/*.sql`.
    Los otros cinco se declaran en el generador, que es su unica fuente.
  - `verificar_diagramas.py` en el CI: 25 comprobaciones. Falla si alguien
    agrega una tabla al DDL y no regenera.
  - **DECISION PENDIENTE DE ALEJANDRO.** Dos de los seis -componentes y
    secuencia- son el entregable de **H6.5**, que esta asignada a Avril. Hay que
    elegir, y no lo decide quien escribio el codigo:
    - reasignar H6.5 a Alejandro, o
    - dejarla de Avril para que la cierre usando estos, o
    - dejar estos como material del documento IEEE y que H6.5 siga aparte.
    Hasta que se decida, **H6.5 no se toca**: sigue abierta y de Avril.

- [ ] **H3.8** · Ajuste de hiperparametros del mejor modelo, documentado
  - `E3` · 3 pts · 4.7 h · rubrica: OE2 · depende de: H3.6

- [x] **H11.5** · Publicar el visor como sitio estatico con datos declarados simulados (2026-08-24)
  - `E11` · 3 pts · 4.7 h · rubrica: CICD · depende de: H5.4, H6.6 · **bloquea a: H9.2a**
  - horas: estimada n/d (salio de una pregunta del PM, no se estimo al arrancar) . real 4.0
  - **https://humanoidcat.github.io/geoguardian/** · evidencia en
    `docs/evidencias/arquitectura-software/H11.5-visor-publicado.md`
  - El tiempo de **I-10** no cuenta aca: es un defecto aparte, no alcance de esta
    historia.
  - Agregada el 2026-08-20. Sale de una pregunta del PM: **el sistema no se
    publica en ningun lado.** D-05 eligio k3d local, asi que "produccion" es un
    espacio de nombres en una laptop y no hay URL. Para la sesion con el Comite
    Municipal de H9.2a eso obliga a llevar la maquina.
  - Es barata porque **H6.6 la dejo posible sin querer**: la degradacion al
    respaldo estatico hace que `npm run build` produzca algo que funciona solo,
    sin API ni base. Ver D-23.
  - No publica la API ni la base. Eso sigue fuera de alcance por D-05.


## Sprint 4 (semanas 10-11) — 52.8 h

- [ ] **H10.5c** · Redactar el documento IEEE completo
  - `E10` · 8 pts · 21.1 h · rubrica: IEEE · depende de: H10.5b · **bloquea a: H10.6**

- [ ] **H4.4** · Contrastar estimaciones contra el catalogo y analizar fallos
  - `E4` · 10 pts · 26.4 h · rubrica: OE3 · depende de: H4.3, H3.6 · **bloquea a: H4.5**

- [ ] **H4.5** · Redactar la respuesta a la pregunta de investigacion
  - `E4` · 2 pts · 5.3 h · rubrica: OE3 · depende de: H4.4

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
