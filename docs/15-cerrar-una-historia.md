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

### 4. Traer `dev`, comprobar que tu historia tiene fila, y regenerar la matriz

> **Lo primero: ¿tu historia tiene fila en `docs/trazabilidad.csv`?**
>
> ```bash
> grep "^H1.4," docs/trazabilidad.csv
> ```
>
> Si no devuelve nada, **pedila antes de marcar `[x]`**. `trazabilidad.csv` es un
> archivo compartido y agregar una fila requiere aprobación del PM.
>
> **Por qué importa el orden.** Si marcás `[x]` sin la fila, `generar_matriz.py` y
> `verificar_estado.py` fallan con «hay historias cerradas sin fila en
> docs/trazabilidad.csv», y quedás entre dejar el CI en rojo o tocar un archivo
> compartido sin permiso. **Ninguna de las dos es aceptable.**
>
> Las filas de las historias planificadas al inicio ya existen. Las que se
> agregaron después —o que nadie cargó— no. Lo detectó César el 27 de agosto, con
> cuatro historias hechas que no podía cerrar.

> **Y regenerá la matriz aunque todavía no marques `[x]`.**
>
> ```bash
> python docs/herramientas/generar_matriz.py
> ```
>
> El procedimiento supone que quien fusiona es quien cierra la historia, y **no
> siempre coinciden**. El 27 de agosto tres Pull Requests entraron con sus
> archivos de `docs/evidencias/` mientras sus historias seguían sin marcar,
> esperando una fila de `trazabilidad.csv`. Eso solo alcanzó para desfasar la
> matriz y **dejó `dev` en rojo en los tres merges seguidos**.
>
> **Subir un archivo a `docs/evidencias/` ya cambia la matriz**, marques o no. Es
> el primero de los tres motivos que el propio `verificar_estado.py` enumera
> cuando falla.

**Y después, en este orden siempre:**

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
| `Closes #23` | GitHub la enlaza, y la cierra **al llegar a `main`** |
| "Cierra H10.1" | **GitHub no entiende nada y la issue queda huérfana** |

El número se busca así:

```bash
gh issue list --search "H1.9" --json number,title
```

### 5b. La issue se cierra sola al mergear a `dev`, y no la cerrás vos

**`Closes #N` no cierra la issue cuando el PR se fusiona a `dev`.** GitHub solo
cierra al fusionar a la **rama por omisión**, que acá es `main`.

Hasta el 26 de agosto eso se resolvía a mano, y era una trampa: **no había orden
que evitara el rojo.**

| Cuándo cerrabas la issue | Qué pasaba |
|---|---|
| **Antes** de fusionar | «issue cerrada y la historia no está marcada `[x]`» |
| **Después** de fusionar | «historia marcada `[x]` y su issue sigue abierta» |

Siempre había una ventana con el CI en rojo, y no dependía de la disciplina de
nadie. Pasó con #165 y con #170. Es **I-13**.

**Desde hoy lo hace el CI.** Al empujar a `dev`, `verificar_issues.py --corregir`
cierra las issues de las historias marcadas `[x]`, con el motivo escrito y el
enlace al Pull Request.

> **Solo esa discrepancia se corrige sola, y por una razón.** «Historia marcada,
> issue abierta» es la única de las cuatro donde el arreglo no admite duda: manda
> `docs/tareas/`, y eso ya está decidido en este mismo documento. Cerrar la issue
> no decide nada, **ejecuta una decisión ya tomada**.
>
> Las otras tres siguen fallando y esperando a una persona: una issue cerrada sin
> historia marcada haría mentir a la fuente de verdad; una historia sin issue
> necesita que alguien le redacte el cuerpo; y dos issues para la misma historia
> necesitan que alguien elija cuál sobra.

El enlace `Closes #N` **igual se pone**: deja el rastro entre la issue y el Pull
Request, que es lo que sirve dentro de un mes para saber qué la cerró. Y en
`main` sí dispara solo.

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
git checkout dev && git pull          # <- esto no es opcional, ver abajo
gh issue list --state all --limit 300 --json number,title,state,stateReason > issues.json
python docs/herramientas/verificar_issues.py --issues issues.json --comandos
```

**Se corre desde `dev` o desde `main`, nunca desde una rama de trabajo.** El
avance se lee de `docs/tareas/` del árbol de trabajo, y el tablero es uno solo
para todo el repositorio: desde una rama atrasada, una historia ya cerrada figura
sin marcar y el verificador **no reclama su issue abierta**. Da verde cuando
debería dar rojo.

Pasó el 25 de agosto, y por eso el programa ahora **se planta** si la rama no es
una de esas dos.

`issues.json` está en `.gitignore` y **no se versiona**: es una foto del tablero
en un instante. Si entrara al repositorio sería un quinto lugar declarando el
avance, que es justo lo que este verificador existe para evitar.

Con `--comandos` imprime los `gh issue close` listos para pegar, con el motivo
escrito. **No se cierra a mano sin comentario**: dentro de un mes nadie va a
saber si se cerró porque se hizo o porque estorbaba.

El CI corre esa comprobación **al empujar a `dev` y a `main`**, no en cada Pull
Request. La razón: el tablero vive fuera del repositorio y lo puede cambiar
cualquiera, así que un PR podría salir en rojo por una issue ajena que su autor
no tocó y quizá no puede arreglar. Pasó con el PR #158. Los otros seis
verificadores sí comprueban archivos que viajan dentro del PR.

### Si hay dos issues para la misma historia

Pasa cuando se carga el backlog dos veces. **La sobrante se cierra declarando que
no es trabajo hecho**, con el motivo de GitHub:

```bash
gh issue close 90 --reason "not planned" --comment "Duplicada de #92."
```

**Si la issue ya estaba cerrada**, `gh` no cambia el motivo: hay que reabrirla
primero.

```bash
gh issue reopen 90
gh issue close 90 --reason "not planned" --comment "Duplicada de #92."
```

Sin `--reason`, GitHub la marca como **completada**, y el verificador la lee como
«esta historia está hecha» — que es justo lo contrario de lo que pasó. La
distinción no es cosmética: es la diferencia entre limpiar el tablero y hacerlo
mentir en la otra dirección.

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
