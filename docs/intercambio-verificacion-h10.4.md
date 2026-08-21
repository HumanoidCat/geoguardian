# Intercambio de verificación de manuales técnicos

**Propuesta de GeoGuardian · Universidad Invenio · III Trimestre 2026**
**Contacto:** Alejandro Rodríguez, Lead PM — `HumanoidCat/geoguardian`
**Origen:** propuesta de César Ubau, 19 de agosto de 2026
**Cierra:** historia H10.4

---

## Qué proponemos

**Una hora cada uno.** Ustedes siguen nuestro manual técnico desde cero y anotan
dónde se traba. Nosotros hacemos lo mismo con el suyo.

No es una revisión de código ni una opinión sobre el diseño. Es una sola pregunta:
**¿alguien que no escribió esto puede levantar el sistema siguiendo el documento, y
nada más que el documento?**

## Por qué se lo pedimos a otro equipo

La historia H10.4 exige que el manual lo verifique *"alguien ajeno al desarrollo,
en una máquina donde el proyecto no esté instalado"*.

Uno de los nuestros ya lo intentó y él mismo declaró que no calificaba: conocía el
proyecto y su máquina lo tenía instalado. Quien escribió el manual ya sabe lo que
el manual omite, y por eso no detecta las omisiones. Hace falta alguien de afuera,
literalmente.

## Qué necesita quien lo haga

- Windows con Docker Desktop, Git, Python 3.11 y Node 20. El manual explica cómo
  instalarlos; si ya los tiene, mejor.
- Una carpeta donde el proyecto **no** esté clonado.
- Una hora sin interrupciones.
- **No** hace falta saber nada del dominio, ni de clima, ni de mapas.

## Cómo se hace

1. Abrir `docs/10-manual-tecnico.md` del repositorio.
2. Empezar en la **sección 2** y seguir en orden hasta la **sección 5**.
3. Mientras avanza, ir llenando la tabla de la **sección 10**.
4. Cada vez que algo no funcione, o haya que averiguarlo por fuera del manual,
   **anotarlo y seguir**. No hace falta arreglarlo.

## La regla que hace útil el ejercicio

> **No preguntarnos nada durante la hora.**

Si la persona pregunta y nosotros contestamos, el manual queda igual de incompleto
y nadie se entera. Cada pregunta que quiso hacer y no hizo es un defecto que
encontramos.

Si se traba de forma definitiva, anota el paso, **salta al siguiente** y sigue.

## Qué nos devuelve

La tabla de la sección 10 llena, con estos campos:

- Quién verificó, fecha y tiempo total.
- Por cada paso: si funcionó y qué observó.
- **Y el campo que más nos importa:** qué pasos tuvo que resolver buscando por
  fuera del manual.

Ese último campo es todo el valor del ejercicio. Un paso que la persona resolvió
por su cuenta es un defecto del manual, aunque el sistema haya terminado
funcionando.

## Qué damos a cambio

Lo mismo, con el mismo protocolo, sobre el manual de ustedes. Nos dicen cuándo y
quién.

Si su manual todavía no existe, la oferta sigue en pie para cuando lo tengan. Y si
prefieren otro entregable —el README, la guía de instalación, lo que sea que
alguien de afuera deba poder seguir— también sirve.

## Lo que hacemos antes de convocarlos

Corregir los **4 defectos** que ya detectamos internamente. Sería un desperdicio
que gasten su hora tropezando con problemas que ya conocíamos.

Les avisamos cuando el manual esté limpio.

---

## Datos del proyecto, por si ayudan a decidir

| | |
|---|---|
| Repositorio | `github.com/HumanoidCat/geoguardian` |
| Qué es | Estimación de riesgo climático por distrito, cantón de Tilarán |
| Estado | 22 de 84 historias cerradas · Sprint 2 |
| Pila | Python 3.11, FastAPI, PostgreSQL 16 con PostGIS, React con Leaflet, Docker |
| Manual | `docs/10-manual-tecnico.md`, 11 secciones |
| Lo que se levanta en la hora | Base de datos con geometrías reales del SNIT, API con su documentación OpenAPI, y el visor del cantón |

---

## Para el registro interno

Cuando el intercambio ocurra, hay que dejar en el repositorio:

1. La sección 10 del manual **llena**, en `docs/10-manual-tecnico.md`.
2. Los defectos encontrados y **cómo se corrigieron**, en la evidencia
   `docs/evidencias/entregables/H10.4-manual-tecnico.md`.
3. El acta de la sesión en `docs/11-ceremonias-scrum.md`.
4. Recién entonces, marcar H10.4 en `docs/tareas/alejandro.md` y regenerar la
   matriz.

Y la verificación que hicimos nosotros sobre el manual del otro equipo, si ellos la
quieren para su propia evidencia, se las pasamos en el formato que usen.
