# Tareas de Alejandro

**Alejandro Josue Rodriguez Zamora**  
**Carpetas propias:** `backend/senales, backend/modelado, infra, docs`

> Solo modificas tus carpetas. Si necesitas un cambio fuera de ellas, se pide, no se hace.

> Marca `[x]` cuando la historia cumpla la Definition of Done, no cuando el codigo funcione.

> **Compromiso de tiempo: 16 horas por semana.** Es lo que el proyecto exige para
> entregar en la semana 12 sin recortar alcance. Si una semana no se puede, se avisa
> al planificar el sprint, no al cerrarlo.

**Total asignado:** 117 puntos · 193 horas · 19.3 h por semana en promedio

## Carga por sprint

| Sprint | Semanas | Horas | Capacidad | Estado |
|---|---|---|---|---|
| S0 | semanas 2-3 | 10.7 | 44 | holgado |
| S1 | semanas 4-5 | 37.7 | 44 | ajustado |
| S2 | semanas 6-7 | 44.0 | 44 | ajustado |
| S3 | semanas 8-9 | 48.0 | 44 | SOBRECARGA +4 h |
| S4 | semanas 10-11 | 52.8 | 44 | SOBRECARGA +9 h |

> **Sobre los picos de S3 y S4.** Suman cerca de 25 h por semana en las semanas 8
> a 11, por encima de las 16 comprometidas. No es reparto desigual: el paper, la
> explicabilidad y el contraste contra eventos reales dependen de que los modelos
> ya esten entrenados, y no se pueden adelantar. Como Lead PM se asume esa carga.
> La unica salida real es no desperdiciar S0 y S1, que estan al 25 % de capacidad:
> cada hora aprovechada ahi es una hora menos de crunch en octubre.


## Sprint 0 (semanas 2-3) — 10.7 h

- [x] **H8.1** · docker compose up levanta todo en maquina limpia (2026-08-03)
  - `E8` · 5 pts · 7.8 h · rubrica: SO-1 · **bloquea a: H10.4, H8.6**
- [ ] **H8.5** · Credenciales por variables de entorno, fuera del repositorio
  - `E8` · 3 pts · 2.9 h · rubrica: SO-1

## Sprint 1 (semanas 4-5) — 37.7 h

- [ ] **H10.7** · Diagramas: casos de uso, componentes, secuencia y ER
  - `E10` · 8 pts · 12.5 h · rubrica: Arq · depende de: H6.5
- [ ] **H10.8** · Carpeta de evidencias organizada por materia con indice
  - `E10` · 5 pts · 4.8 h · rubrica: SO-4
- [ ] **H3.0** · Implementar el etiquetado de los tres eventos y su distribucion de clases
  - `E3` · 8 pts · 12.5 h · rubrica: OE2 · depende de: H2.3 · **bloquea a: H3.1, H3.2**
- [ ] **H6.4** · Seis o mas registros ADR escritos
  - `E6` · 3 pts · 7.9 h · rubrica: Arq

## Sprint 2 (semanas 6-7) — 44.0 h

- [ ] **H10.3** · Manual de usuario con capturas paso a paso
  - `E10` · 5 pts · 4.8 h · rubrica: MVP · depende de: H7.1 · **bloquea a: H10.9**
- [ ] **H10.4** · Manual tecnico verificado por alguien ajeno al desarrollo
  - `E10` · 5 pts · 4.8 h · rubrica: MVP · depende de: H8.1
- [ ] **H3.1** · Construir la linea base climatologica por distrito, mes y tipo de evento
  - `E3` · 6 pts · 9.4 h · rubrica: OE2 · depende de: H3.0
- [ ] **H3.2** · Definir y documentar la validacion por ventana expansiva
  - `E3` · 8 pts · 12.5 h · rubrica: OE2 · depende de: H3.0 · **bloquea a: H3.3, H3.4, H3.5**
- [ ] **H8.6** · Manifiestos de Kubernetes corriendo en k3d local
  - `E8` · 8 pts · 12.5 h · rubrica: Arq · depende de: H8.1

## Sprint 3 (semanas 8-9) — 48.0 h

- [ ] **H3.5** · Entrenar y evaluar XGBoost
  - `E3` · 6 pts · 9.4 h · rubrica: OE2 · depende de: H3.2 · **bloquea a: H3.6**
- [ ] **H3.6** · Tabla comparativa de tres algoritmos contra la linea base, por evento
  - `E3` · 10 pts · 15.6 h · rubrica: OE2 · depende de: H3.5 · **bloquea a: H3.7, H3.8, H4.1**
- [ ] **H3.7** · Versionar modelos con metricas y fecha asociadas
  - `E3` · 3 pts · 2.9 h · rubrica: Arq · depende de: H3.6
- [ ] **H3.8** · Ajuste de hiperparametros del mejor modelo, documentado
  - `E3` · 3 pts · 4.7 h · rubrica: OE2 · depende de: H3.6
- [ ] **H4.1** · Importancia de variables global del mejor modelo
  - `E4` · 3 pts · 2.9 h · rubrica: OE3 · depende de: H3.6 · **bloquea a: H4.2**
- [ ] **H4.2** · Aplicar SHAP para explicar predicciones individuales
  - `E4` · 8 pts · 12.5 h · rubrica: OE3 · depende de: H4.1

## Sprint 4 (semanas 10-11) — 52.8 h

- [ ] **H10.5c** · Redactar el documento IEEE completo
  - `E10` · 8 pts · 21.1 h · rubrica: IEEE · depende de: H10.5b · **bloquea a: H10.6**
- [ ] **H4.4** · Contrastar estimaciones contra el catalogo y analizar fallos
  - `E4` · 10 pts · 26.4 h · rubrica: OE3 · depende de: H4.3 · **bloquea a: H4.5**
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
