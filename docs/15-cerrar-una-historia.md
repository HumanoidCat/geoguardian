# Cómo se cierra una historia

**Qué problema resuelve este documento.** El avance del proyecto se declara en
**cuatro** lugares, y hasta el 23 de agosto solo tres tenían una máquina que los
cruzara. El cuarto —el tablero de GitHub— es justamente el que mira quien no lee
el repositorio: un profesor, un evaluador, alguien del equipo con prisa.

| Dónde | Qué dice | Quién lo comprueba |
|---|---|---|
| `docs/tareas/<persona>.md` | **La fuente de verdad.** La marca `[x]` con fecha | — |
| `docs/05-matriz-trazabilidad.md` | Vista generada | `verificar_estado.py` |
| `docs/08-backlog.md` | La línea de avance | `verificar_documentacion.py` |
| **Issues de GitHub** | El tablero | **`verificar_issues.py`**, desde hoy |

---

## Los seis pasos

Ninguno es opcional, y el orden importa.

### 1. Subir la evidencia

A `docs/evidencias/<materia>/`, con el nombre `<ID>-<algo>.md`. Es escritura
libre: no hace falta pedir permiso.

Si la historia cierra con criterios de aceptación escritos antes, la evidencia
los responde uno por uno.

### 2. Marcar `[x]` con la fecha

En **tu** archivo, `docs/tareas/<persona>.md`:

```
- [x] **H7.1** · Semaforo de riesgo por distrito y evento (2026-08-20)
```

**Solo la marca quien hizo la historia.** Es lo único que decide si está cerrada.

### 3. Declarar las horas

Debajo de la línea de la historia:

```
  - horas: estimada 4.0 . real 2.0
```

`estimada` es lo que dijiste **antes de arrancar**. Si no hubo estimación previa,
`n/d` **con el motivo entre paréntesis**. Ver **D-24**.

### 4. Traer `dev` y **después** regenerar la matriz

En ese orden, siempre:

```bash
git merge origin/dev
python docs/herramientas/generar_matriz.py
```

Al revés no funciona: el generador puede haber cambiado en `dev`, y regenerar
con la versión vieja produce un archivo que parece correcto y no lo es. Ver
`docs/07-propiedad-archivos.md`.

### 5. El Pull Request lleva `Closes #N`

**Con el número real de la issue, en el cuerpo.** No en prosa:

| Lo que se escribe | Qué pasa |
|---|---|
| `Closes #23` | GitHub cierra la issue al mergear |
| "Cierra H10.1" | **La issue queda abierta y el tablero miente** |

El número se busca así:

```bash
gh issue list --search "H1.9" --json number,title
```

### 6. Comprobar antes de pedir revisión

```bash
python docs/herramientas/verificar_estado.py
python docs/herramientas/verificar_horas.py
python docs/herramientas/verificar_documentacion.py
```

Si alguno falla, el CI también va a fallar. Sale más barato verlo antes.

---

## Si la issue quedó abierta igual

Pasa: alguien olvida el `Closes #N`, o la historia se cierra en dos PR. Se
detecta y se arregla:

```bash
gh issue list --state all --limit 300 --json number,title,state > issues.json
python docs/herramientas/verificar_issues.py --issues issues.json --comandos
```

Con `--comandos` imprime los `gh issue close` listos para pegar, con el motivo
escrito. **No se cierra a mano sin comentario**: dentro de un mes nadie va a
saber si se cerró porque se hizo o porque estorbaba.

El CI corre esa comprobación en cada cambio, así que la discrepancia aparece
sola.

---

## La regla que hay detrás

**El tablero se corrige contra el repositorio, nunca al revés.**

Si la issue dice una cosa y `docs/tareas/` otra, manda `docs/tareas/`. Marcar una
historia porque su issue estaba cerrada sería exactamente el defecto que la
auditoría del 18 de agosto encontró en la matriz: cuatro historias cerradas que
no figuraban, y dos filas con el dueño equivocado. Ese segundo defecto **le quitó
trabajo del plato a una persona durante un día**.

## Y la razón por la que esto se escribió

La convención del `Closes #N` **ya estaba documentada** en
`docs/plantillas/como-llenar-el-pr.md`, con el modo de fallo y todo. No alcanzó.

Una regla escrita que ninguna máquina comprueba se cumple mientras alguien se
acuerda. Es el mismo aprendizaje de **I-04** —un dato con forma válida y
contenido equivocado que ninguna validación detecta— y de **I-07** —una cifra
derivada escrita a mano—.

Cada vez que este proyecto encontró un desfase, la causa fue la misma: **una
fuente, varias vistas, y ninguna máquina que las cruzara.** Este documento
existe para que el tablero deje de ser la excepción.
