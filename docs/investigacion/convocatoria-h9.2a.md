# Convocatoria · H9.2a · Sesion de usabilidad y puntaje SUS

**Fecha de emision.** 2026-09-13
**Responsable.** Luis Alejandro Luna Garcia (Luna)
**Instrumentos.** `sus-cuestionario.md`, `guion-entrevista.md` (bloques 0-4 y 6)
**Duracion por sesion.** 45 minutos

Este archivo **es parte del registro del estudio**, no un borrador. Una sesion
con participantes se documenta desde el reclutamiento: a quien se busco, con que
criterio, que se le dijo y que no. Sin eso, lo que queda es una conversacion.

---

## Que mide esta sesion, y que NO mide

**Mide usabilidad: si la persona puede usar la herramienta y entender lo que
dice.** No mide si la estimacion acierta. Eso es H9.2b, es otra sesion y son
otros participantes.

La distincion importa al reclutar: **aqui no hace falta que la persona haya
vivido ningun evento.** Hace falta que sea alguien que usaria la herramienta.

## A quien se busca

**Entre 3 y 5 participantes.** El numero no es por comodidad: con 5 usuarios se
detecta la mayor parte de los problemas de usabilidad de una interfaz, y es el
tamano habitual de una prueba formativa.

Perfiles buscados, en orden de preferencia:

| Perfil | Por que |
|---|---|
| Comite municipal o comunal de emergencias | Es el usuario previsto |
| Cruz Roja, Bomberos, fuerza publica local | Toman decisiones con informacion de riesgo |
| Municipalidad de Tilaran, gestion de riesgo o acueductos | Usuario institucional |
| ASADAS, asociaciones de productores, ganaderos | Usuario afectado, con interes directo |
| Docentes o estudiantes de la zona | Ultimo recurso, y se declara si se usa |

**No se recluta a nadie del equipo del proyecto, ni a sus familiares directos.**
Un participante que sabe como quiere uno que responda no esta evaluando nada.

## Que se le dice a la persona, textual

> Buenas. Soy Luis Alejandro Luna, estudiante de la Universidad Invenio. Estamos
> construyendo **GeoGuardian**, una herramienta que estima riesgo de lluvia
> intensa, sequia e incendio **por distrito** en el canton de Tilaran, con datos
> abiertos de satelite.
>
> Necesito que alguien la use y me diga que no se entiende. **No es una
> demostracion: es una prueba de la herramienta, no suya.** Todo lo que no
> funcione o no se entienda es exactamente lo que ando buscando.
>
> Son **45 minutos**, en linea o presencial, cuando a usted le sirva. No hay
> pago. Los resultados son parte de un trabajo academico y se publican **sin su
> nombre**: solo se registra su rol, por ejemplo «miembro de comite de
> emergencias». Si prefiere que no se grabe audio, no se graba.
>
> ¿Le sirve algun dia entre el **martes 15 y el viernes 18**?

## Lo que NO se dice antes de la sesion

- **No se explica como funciona el sistema por dentro.** Si se le cuenta antes
  que la estimacion la produce una linea base climatologica, ya no se puede
  medir si la interfaz lo comunica sola.
- **No se adelanta que hay un resultado negativo.** Predispone la respuesta.
- **No se le pide que "pruebe si funciona bien".** Esa frase invita a decir que
  si. Se le pide que diga que no se entiende.

## Disponible antes de la sesion

- Sitio: `https://visor-production-40b5.up.railway.app/`
- Estado al 2026-09-13: `/api/salud` responde `modo: real`, base conectada.
  **Se vuelve a comprobar el mismo dia de cada sesion**, y si estuviera caido se
  declara en la evidencia en vez de reprogramar en silencio.

## Ajuste del guion, declarado antes de la primera sesion

`guion-entrevista.md` se escribio el 2026-08-22, cuando el visor servia **datos
simulados**, y dice que la banda de «modo simulado» no se oculta sino que se
mide. **Desde el 2026-09-11 el visor sirve estimaciones reales** (H11.7), asi que
esa pregunta ya no interroga lo mismo.

El ajuste va escrito en los criterios de aceptacion de H9.2a **antes de correr
ninguna sesion**, no sobre la marcha. Lo que se conserva es la pregunta de fondo
—si la herramienta comunica su propia incertidumbre— reformulada sobre lo que el
visor declara hoy.

## Registro que hay que llevar

Por cada persona contactada, aunque diga que no:

    fecha de contacto · perfil · canal · respuesta · fecha de sesion

**Los rechazos tambien se anotan.** Si de quince contactos aceptan tres, eso dice
algo sobre la disponibilidad del perfil y pertenece al estudio.
