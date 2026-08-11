# Tareas de Alejandro

**Alejandro Josue Rodriguez Zamora**  
**Carpetas propias:** `backend/senales, backend/modelado, infra, docs, .github/workflows`

> Solo modificas tus carpetas. Si necesitas un cambio fuera de ellas, se pide, no se hace.

> Marca `[x]` cuando la historia cumpla la Definition of Done, no cuando el codigo funcione.

> **Compromiso de tiempo: 18 horas por semana.**

**Total asignado:** 147 puntos · 241 horas · 24.1 h por semana en promedio

## Carga por sprint

| Sprint | Semanas | Horas | Capacidad | Estado |
|---|---|---|---|---|
| S0 | semanas 2-3 | 35.9 | 48 | holgado |
| S1 | semanas 4-5 | 47.8 | 48 | ajustado |
| S2 | semanas 6-7 | 47.0 | 48 | ajustado |
| S3 | semanas 8-9 | 45.1 | 48 | ajustado |
| S4 | semanas 10-11 | 65.4 | 48 | SOBRECARGA +17 h |

> **Sobre los picos.** El pipeline completo de CI/CD, el modelado, la documentacion
> y la evaluacion se concentran aqui por decision propia. S4 llega a 33 h por semana
> porque el paper, la explicabilidad y el despliegue a produccion dependen de trabajo
> previo y no se pueden adelantar. Avril esta en 9.7 h por semana: si en algun punto
> hace falta descargar, el manual de usuario y el guion de demo son lo primero que
> puede pasar a ella.


## Sprint 0 (semanas 2-3) — 35.9 h

- [x] **H10.8** · Carpeta de evidencias organizada por materia con indice (2026-08-11)
  - `E10` · 5 pts · 4.8 h · rubrica: SO-4
- [x] **H6.4** · Seis o mas registros ADR escritos (2026-08-11)
  - `E6` · 3 pts · 7.9 h · rubrica: Arq
- [x] **H8.1** · docker compose up levanta todo en maquina limpia (2026-08-03)
  - `E8` · 5 pts · 7.8 h · rubrica: SO-1 · **bloquea a: H10.4, H11.1, H8.6**
- [x] **H8.5** · Credenciales por variables de entorno, fuera del repositorio (2026-08-11)
  - `E8` · 3 pts · 2.9 h · rubrica: SO-1
- [ ] **H8.6** · Manifiestos de Kubernetes corriendo en k3d local
  - `E8` · 8 pts · 12.5 h · rubrica: Arq · depende de: H8.1

## Sprint 1 (semanas 4-5) — 47.8 h

- [ ] **H10.4** · Manual tecnico verificado por alguien ajeno al desarrollo
  - `E10` · 5 pts · 4.8 h · rubrica: MVP · depende de: H8.1
- [ ] **H10.7** · Diagramas: casos de uso, componentes, secuencia y ER
  - `E10` · 8 pts · 12.5 h · rubrica: Arq · depende de: H6.5
- [ ] **H11.1** · CI: construir imagen Docker y publicar artefactos en ghcr.io
  - `E11` · 5 pts · 4.8 h · rubrica: CICD · depende de: H8.1 · **bloquea a: H11.2**
- [ ] **H13.1** · Actas de las ceremonias Scrum: planning, dailies, review y retrospectiva
  - `E13` · 5 pts · 13.2 h · rubrica: Scrum
- [ ] **H3.0** · Implementar el etiquetado de los tres eventos y su distribucion de clases
  - `E3` · 8 pts · 12.5 h · rubrica: OE2 · depende de: H2.3 · **bloquea a: H3.1, H3.2**

## Sprint 2 (semanas 6-7) — 47.0 h

- [ ] **H10.3** · Manual de usuario con capturas paso a paso
  - `E10` · 5 pts · 4.8 h · rubrica: MVP · depende de: H7.1 · **bloquea a: H10.9**
- [ ] **H11.2** · CD: despliegue automatico al entorno de desarrollo al mergear a main
  - `E11` · 5 pts · 7.8 h · rubrica: CICD · depende de: H11.1 · **bloquea a: H11.3, H12.3**
- [ ] **H11.3** · CD: despliegue a staging en namespace propio, con aprobacion manual
  - `E11` · 3 pts · 4.7 h · rubrica: CICD · depende de: H11.2 · **bloquea a: H11.4**
- [ ] **H11.4** · CD: despliegue a produccion con aprobacion explicita y rollback automatico
  - `E11` · 5 pts · 7.8 h · rubrica: CICD · depende de: H11.3 · **bloquea a: H13.2**
- [ ] **H3.1** · Construir la linea base climatologica por distrito, mes y tipo de evento
  - `E3` · 6 pts · 9.4 h · rubrica: OE2 · depende de: H3.0
- [ ] **H3.2** · Definir y documentar la validacion por ventana expansiva
  - `E3` · 8 pts · 12.5 h · rubrica: OE2 · depende de: H3.0 · **bloquea a: H3.3, H3.4, H3.5**

## Sprint 3 (semanas 8-9) — 45.1 h

- [ ] **H3.5** · Entrenar y evaluar XGBoost
  - `E3` · 6 pts · 9.4 h · rubrica: OE2 · depende de: H3.2 · **bloquea a: H3.6**
- [ ] **H3.6** · Tabla comparativa de tres algoritmos contra la linea base, por evento
  - `E3` · 10 pts · 15.6 h · rubrica: OE2 · depende de: H3.5 · **bloquea a: H3.7, H3.8, H4.1**
- [ ] **H3.8** · Ajuste de hiperparametros del mejor modelo, documentado
  - `E3` · 3 pts · 4.7 h · rubrica: OE2 · depende de: H3.6
- [ ] **H4.1** · Importancia de variables global del mejor modelo
  - `E4` · 3 pts · 2.9 h · rubrica: OE3 · depende de: H3.6 · **bloquea a: H4.2**
- [ ] **H4.2** · Aplicar SHAP para explicar predicciones individuales
  - `E4` · 8 pts · 12.5 h · rubrica: OE3 · depende de: H4.1

## Sprint 4 (semanas 10-11) — 65.4 h

- [ ] **H10.5c** · Redactar el documento IEEE completo
  - `E10` · 8 pts · 21.1 h · rubrica: IEEE · depende de: H10.5b · **bloquea a: H10.6**
- [ ] **H12.3** · Alertas automaticas ante fallo de pipeline o despliegue
  - `E12` · 5 pts · 7.8 h · rubrica: Troubleshoot · depende de: H11.2
- [ ] **H13.2** · Manual de operacion del sistema
  - `E13` · 5 pts · 4.8 h · rubrica: Documentacion · depende de: H11.4
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
