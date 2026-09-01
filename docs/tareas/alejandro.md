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

**Total asignado:** 123 puntos · 206.8 horas · 20.7 h por semana en promedio

## Carga por sprint

| Sprint | Semanas | Horas | Capacidad | Estado |
|---|---|---|---|---|
| S0 | semanas 2-3 | 35.9 | 36 | ajustado |
| S1 | semanas 4-5 | 22.8 | 36 | holgado |
| S2 | semanas 6-7 | 59.5 | 36 | SOBRECARGA +23.5 h |
| S3 | semanas 8-9 | 35.7 | 36 | ajustado |
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

- [ ] **H1.13** · Trigger de auditoria sobre predicciones, con prueba
  - `E1` · 3 pts · 2.9 h · rubrica: BD-2 · depende de: H1.8, H1.15
  - **Desbloqueada el 2026-08-27.** Estuvo detenida porque `analitico.riesgo` no
    existia y ninguna historia la creaba, con H1.8 -su dependencia declarada- ya
    cerrada. Ahora depende tambien de **H1.15**, que si la crea.
  - La dependencia es real y medida, no inventada para desatascar el tablero.
  - **Traspasada desde Cesar el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.

- [ ] **H1.6** · Descargar imagenes Sentinel-2 de estacion seca, nubosidad menor a 20%
  - `E1` · 5 pts · 7.8 h · rubrica: CG-3 · **bloquea a: H5.5, H8.4**
  - **Traspasada desde Avril el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.
- [ ] **H10.4** · Manual tecnico verificado por alguien ajeno al desarrollo
  - `E10` · 5 pts · 4.8 h · rubrica: MVP · depende de: H8.1

- [ ] **H11.1** · CI: construir imagen Docker y publicar artefactos en ghcr.io
  - `E11` · 5 pts · 4.8 h · rubrica: CICD · depende de: H6.0, H6.1 · **bloquea a: H11.2**

- [x] **H13.1** · Actas de las ceremonias Scrum: planning, dailies, review y retrospectiva (2026-08-16)
  - `E13` · 5 pts · 13.2 h · rubrica: Scrum


## Sprint 2 (semanas 6-7) — 113.1 h


- [ ] **H1.9** · Funciones PL/pgSQL con EXCEPTION WHEN, RAISE y bitacora de fallos
  - `E1` · 8 pts · 7.7 h · rubrica: BD-3 · depende de: H1.8 · **bloquea a: H1.10, H12.1**
  - **Traspasada desde Cesar el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.

- [ ] **H1.11** · Particionar mediciones por anio y medir efecto en consultas
  - `E1` · 5 pts · 4.8 h · rubrica: BD-1 · depende de: H1.3 · **bloquea a: H1.12**
  - **Traspasada desde Cesar el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.

- [ ] **H1.12** · Indices espaciales y compuestos con planes antes y despues
  - `E1` · 5 pts · 4.8 h · rubrica: BD-1 · depende de: H1.11
  - **Traspasada desde Cesar el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.

- [ ] **H2.5** · Generar lags, acumulados y medias moviles reproducibles
  - `E2` · 5 pts · 4.8 h · rubrica: OE2 · depende de: H2.3 · **bloquea a: H2.6**
  - **Traspasada desde Cesar el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.

- [ ] **H3.3** · Entrenar y evaluar Regresion Logistica
  - `E3` · 6 pts · 9.4 h · rubrica: OE2 · depende de: H3.2
  - **Traspasada desde Cesar el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.

- [ ] **H5.6** · Transformacion WGS84 a CRTM05 verificada con puntos de control
  - `E5` · 3 pts · 4.7 h · rubrica: CG-1 · depende de: H5.1
  - **Traspasada desde Avril el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.

- [ ] **H7.2** · Graficas interactivas de series con seleccion de rango
  - `E7` · 5 pts · 4.8 h · rubrica: CG-2 · depende de: H6.1
  - **Traspasada desde Avril el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.

- [ ] **H10.3** · Manual de usuario con capturas paso a paso
  - `E10` · 5 pts · 4.8 h · rubrica: MVP · depende de: H7.1 · **bloquea a: H10.9**
  - **Traspasada desde Avril el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.

- [ ] **H10.7** · Diagramas de casos de uso y entidad-relacion
  - `E10` · 5 pts · 7.8 h · rubrica: Arq · depende de: H1.8
  - **Traspasada desde Avril el 2026-08-31** por **D-33**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el sprint, y su contenido queda tal como estaba escrito.
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

- [ ] **H11.2** · CD: despliegue automatico al entorno de desarrollo al mergear a main
  - `E11` · 5 pts · 7.8 h · rubrica: CICD · depende de: H11.1 · **bloquea a: H11.3, H12.3**

- [ ] **H11.3** · CD: despliegue a staging en namespace propio, con aprobacion manual
  - `E11` · 3 pts · 4.7 h · rubrica: CICD · depende de: H11.2 · **bloquea a: H11.4**

- [ ] **H11.4** · CD: despliegue a produccion con aprobacion explicita y rollback automatico
  - `E11` · 5 pts · 7.8 h · rubrica: CICD · depende de: H11.3 · **bloquea a: H13.2**

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


## Sprint 3 (semanas 8-9) — 40.4 h

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

- [ ] **H4.1** · Importancia de variables global del mejor modelo
  - `E4` · 3 pts · 2.9 h · rubrica: OE3 · depende de: H3.6 · **bloquea a: H4.2**

- [ ] **H4.2** · Aplicar SHAP para explicar predicciones individuales
  - `E4` · 8 pts · 12.5 h · rubrica: OE3 · depende de: H4.1

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
