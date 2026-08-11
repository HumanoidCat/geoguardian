# Cómo llenar la plantilla del Pull Request

La plantilla está en `.github/PULL_REQUEST_TEMPLATE.md` y se llena **completa**.
No es burocracia: el bloque "Cómo lo verifiqué" y la Definition of Done son
criterio evaluado en la rúbrica de Sistemas Operativos y en la de Arquitectura
de Software.

Un PR con el cuerpo en una sola línea vuelve con Changes requested, aunque el
contenido esté bien.

---

## Bloque para pegar en Claude

Pegá esto al empezar la sesión en la que vas a abrir el PR:

```
Voy a abrir un Pull Request en el repositorio geoguardian.

Reglas:
- El cuerpo del PR usa la plantilla completa de .github/PULL_REQUEST_TEMPLATE.md,
  con todas sus secciones. Leela antes de escribir nada.
- En "Historia" va "Closes #<numero>" con el numero real de la issue. No en prosa:
  "Cierra H10.1" no cierra nada, GitHub solo entiende "Closes #N".
- En "Como lo verifique" va el comando exacto que corri y su salida real, pegada.
  Si no tengo la salida, no la inventes ni la aproximes: pedimela.
- La Definition of Done se marca [x] solo en lo que efectivamente esta hecho.
  Lo que no aplica se marca y se explica por que en una linea. Lo que falta se
  deja sin marcar.
- Si la historia cierra un entregable, tiene que existir el archivo de evidencia
  en docs/evidencias/<carpeta segun la rubrica>/ y el [x] con fecha en
  docs/tareas/<mi-nombre>.md, en este mismo PR. Verifica que esten antes de
  darme el cuerpo por terminado.
- No escribas nada que no puedas sostener con la salida de un comando o con una
  linea del repositorio.

Escribi el cuerpo en un archivo .md aparte para que yo lo revise antes de subirlo.
```

---

## Qué va en cada sección

**Qué hace este PR.** Una o dos líneas, con el porqué. "Agrega X" no dice nada;
"agrega X porque sin eso Y no puede empezar" sí.

**Historia.** `H1.9 · Closes #23`. El número de issue se busca así:

```powershell
gh issue list --repo HumanoidCat/geoguardian --search "H1.9" --json number,title
```

**Cómo lo verifiqué.** Lo más importante del PR. Comando y salida, dentro del
bloque de código. No vale "probé y funciona". Un revisor tiene que poder copiar
ese comando y obtener lo mismo.

**Definition of Done.** Se marca lo que está hecho de verdad. Marcar una casilla
falsa es peor que dejarla vacía: la vacía se resuelve en un comentario, la falsa
se descubre en la semana 12.

**Rúbrica.** El criterio al que contribuye: `BD-2`, `CG-1`, `SO-1`, `OE2`, `QA`,
`IEEE`… Si no aplica a ninguno, decirlo explícitamente. Esto es lo que después
permite armar la carpeta de evidencias sin reconstruir nada.

**Bloqueaba a alguien.** Si la historia desbloquea a otra persona, nombrarla.
Es la diferencia entre que se entere hoy o dentro de una semana.

---

## Cómo se sube el cuerpo

Escribir el cuerpo en un archivo y pasarlo con `--body-file`. Así queda revisable
antes de publicarse y no se pierde si algo falla.

Al crear el PR:

```powershell
gh pr create --repo HumanoidCat/geoguardian --base dev --title "docs(investigacion): plan de pruebas H10.1" --body-file cuerpo-pr.md
```

Si el PR ya existe y hay que corregir el cuerpo:

```powershell
gh pr edit <numero> --repo HumanoidCat/geoguardian --body-file cuerpo-pr.md
```

El archivo `cuerpo-pr.md` es temporal, no se commitea.

---

## Errores reales, ya vistos

| Error | Consecuencia |
|---|---|
| Cuerpo de una sola línea | Changes requested. Falta el criterio evaluado de la rúbrica |
| "Cierra H10.1" en vez de `Closes #23` | La issue queda abierta y el tablero miente |
| Sin evidencia en `docs/evidencias/` | La DoD no se cumple. En la semana 12 no hay qué entregar |
| Sin `[x]` en `docs/tareas/<nombre>.md` | Se pierde el rastro de contribución individual, que tiene rúbrica propia |
| Marcar la DoD completa sin que lo esté | Es el único error que no se perdona: rompe la confianza en todos los demás PR |
| Salida de comando escrita a mano | Si el revisor corre el comando y da distinto, vuelve todo el PR |

---

## Ejemplo llenado

```markdown
## Qué hace este PR

Agrega el extractor de NASA POWER para las ocho estaciones del cantón. Sin esto
no hay serie histórica y H2.7 (percentiles R95p/R99p) no puede empezar.

## Historia

H2.1 · Closes #17

## Cómo lo verifiqué

```
> python -m backend.extraccion.power --distrito 50801 --desde 2020-01-01 --hasta 2020-01-31
Descargadas 31 filas para el distrito 50801.
Dias con dato completo: 29
Dias con precipitacion nula (sin dato): 2  -> fechas 2020-01-14, 2020-01-22
Guardadas en crudo.mediciones_power: 31 filas, 0 duplicados.
```

Los dos días sin dato se guardaron con `precipitacion_mm = NULL`, no con 0.
Verificado en la base:

```
> docker compose exec db psql -U geoguardian -d geoguardian -c "SELECT fecha, precipitacion_mm FROM crudo.mediciones_power WHERE precipitacion_mm IS NULL;"
   fecha    | precipitacion_mm
------------+------------------
 2020-01-14 |
 2020-01-22 |
(2 rows)
```

## Definition of Done

- [x] Solo toqué archivos de **mi carpeta**
- [x] **Verifiqué ejecutando**, no leyendo
- [x] **No inventé datos**: los dos días sin medición quedaron en NULL
- [x] CI en verde: `contratos`, `calidad` y `pruebas`
- [x] Prueba agregada: `backend/tests/test_extractor_power.py`
- [ ] **Simulado actualizado** — no aplica, no cambié ningún contrato
- [x] Evidencia guardada en `docs/evidencias/bases-de-datos/H2.1-extractor-power.md`
- [x] Matriz de trazabilidad actualizada
- [x] Marqué `[x]` con la fecha en `docs/tareas/cesar.md`

## Rúbrica

BD-1 (extracción y carga) y OE1.

## Bloqueaba a alguien

Sí. Luna puede empezar H2.7 (percentiles R95p/R99p): ya hay serie histórica en
`crudo.mediciones_power`.
```
