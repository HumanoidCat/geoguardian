# SC-13 · Excepción acotada sobre `TableroSemaforo.jsx` para el texto de la casilla vacía

| | |
|---|---|
| **Archivo ajeno** | `frontend/src/componentes/TableroSemaforo.jsx` · carpeta de **Avril** |
| **Pedida por** | Luna, 2026-09-17 |
| **Responde** | Alejandro, como PM · y Avril, como dueña de la carpeta |
| **Historia que la origina** | **H9.4** · Incorporar un cambio derivado de la retroalimentación |
| **Estado** | **Propuesta. Nada tocado hasta que esté respondida.** |
| **Numeración** | Se escribió como SC-11 el 2026-09-17 y **se renumeró el mismo día**: SC-11 y SC-12 ya estaban tomadas en `dev`, de un `git pull` posterior a haberla escrito. Es la segunda colisión de numeración del proyecto —la primera fue la del 2026-09-02, que consumió SC-09— y se detectó antes del PR, no después |

## El problema, en una frase

**Seis participantes externos leyeron la casilla vacía del semáforo, y ninguno
entendió qué significaba gracias a la interfaz.**

## De dónde sale, medido y no supuesto

H9.2a y H9.2b, entre el 2026-09-08 y el 2026-09-14, tres participantes cada una:

| | Cómo la leyeron |
|---|---|
| H9.2a | uno la leyó como **«no hay sequía»** |
| H9.2b | los tres la leyeron como **«se cayó el sistema»** — *«¿se cayó?»* |
| Los dos que acertaron | por los boletines del IMN y por analogía con Windy |

**Los dos aciertos llegaron con conocimiento traído de afuera.** La interfaz no
enseñó nada en ninguno de los seis casos.

Y es el único hallazgo en el que coinciden los seis, entre perfiles que no se
conocen entre sí: gestión de riesgo municipal, agricultura, turismo, ganadería,
brigada de emergencias y mantenimiento vial.

**El arreglo lo propusieron dos participantes, sin conocerse:**

> «Póngale "no medido" con letras. Si me deja el espacio vacío yo pienso que está
> bueno.» *(el que había leído «no hay sequía»)*
>
> «Póngale un letrero: "Sequía: no disponible". Dos palabras y se acabó el
> problema.» *(22 años viendo sistemas institucionales: «cuando algo sale en
> blanco **siempre** es que se cayó»)*

## Por qué no es cosmético

El caso de la sequía es **D-34**: no se estima porque hubo 13 episodios en 34
años, muy pocos para entrenar o validar. **Es una decisión declarada del
proyecto.** Que se lea como «no hay sequía» invierte su significado, y le pasó
justo al participante cuya actividad más depende de la sequía —el año anterior se
le secó la naciente del ganado y perdió dos terneras.

Y hay una **inconsistencia interna** que nadie había notado:

    LeyendaRiesgo.jsx      «Sin estimacion»
    PanelDistrito.jsx      «Sin estimacion de riesgo»
    MapaCanton.jsx         «sin estimacion»
    TableroSemaforo.jsx    title: «sin estimacion»
    TableroSemaforo.jsx    TEXTO VISIBLE: «sin dato»   <-- el unico

El propio `title` de esa celda ya dice «sin estimación». **Solo el texto que la
gente lee dice otra cosa.**

## Qué se pide exactamente

**Una excepción acotada al componente `TableroSemaforo.jsx`, y solo a la función
`Celda` y al texto que emite.** No al resto del archivo, no al resto de
`frontend/`.

Declarada antes de tocar nada, con el mismo criterio con que **D-37** dio a Luna
`backend/modelado` para H4.1 y H4.2, y con el que H12.1 tocó
`basedatos/seguridad/verificar_h18.py`.

### Dos alcances, y la elección es del PM

**A · El mínimo honesto** — unas diez líneas. Una función que mapee el evento al
texto: la sequía dice que **no se mide**, el resto dice **sin estimación**.

**B · El mínimo literal** — una línea. `sin dato` → `sin estimación`.

**Se propone A.** El motivo está en los criterios de H9.4:

> **B cierra la inconsistencia pero deja sin resolver justo la lectura que causó
> el fallo.** El participante no se confundió porque el texto fuera inconsistente:
> se confundió porque nada le decía que la ausencia era deliberada.

**Si a siete días de la feria preferís acotar el riesgo, se hace B** y se anota en
la evidencia que el hallazgo queda parcialmente sin atender, con la parte que
falta descrita. Eso es preferible a hacer A sin permiso.

### Y una tercera opción, que también sirve

**Que lo implemente Avril y Luna documente el ciclo.** H9.4 dice «incorporar un
cambio», no «escribir el código». Si es más limpio así, no hay objeción: lo que la
historia tiene que demostrar es que el ciclo hallazgo → decisión → cambio se
cerró, y quién teclea es secundario si está declarado.

## Qué NO se pide

- **No se pide tocar el mapa, la leyenda ni el panel de distrito.** Ya dicen «sin
  estimación».
- **No se pide quitar ni agregar la columna de sequía.** Dos participantes lo
  pidieron; eso cambia qué muestra el visor y no es un cambio de texto.
- **No se pide distinguir los tres casos de ausencia** —no se mide (D-34), no se
  estima (D-25), el ETL no trajo— que hoy se ven iguales. **Eso es más grande que
  H9.4 y queda anotado como historia propia.**
- **No se pide cambiar ningún token de color ni la trama.** El contraste ya está
  verificado por `verificar_escala.py` y no se toca.

## Verificación comprometida

```powershell
python frontend/herramientas/verificar_frases.py
python frontend/herramientas/verificar_escala.py
cd frontend ; npm run build
```

Más una **medición en el DOM a 390 px** de que el texto cabe en la celda sin
recortarse, y una captura. Los criterios completos están en
`docs/evidencias/objetivos/H9.4-criterios-aceptacion.md`.

**Comprobado antes de pedir la excepción:** ninguna prueba ni verificador busca la
cadena `sin dato` dentro de este componente. Las apariciones en `frontend/` son
clases CSS (`trama-sin-dato`, `valor-ausente`), tokens, y otros componentes.
`verificar_escala.py` comprueba el contraste de la trama, no el texto.

## Si se rechaza

H9.4 se cierra con **otro** de los tres candidatos medidos, o se difiere con
**D-27**. Los otros dos, en el orden que la evidencia de H9.2a dejó fijado:

1. **El sello de no-oficialidad.** El de mayor consecuencia: ninguno de los tres
   de H9.2a lo encontró, y el de gestión de riesgo lo llamó **«grave»** —«porque
   lo otro es comodidad y esto es responsabilidad»—. Pero es más grande que un
   texto: hay que decidir dónde va y cómo se ve, y también es `frontend/`.
2. **La fecha y hora del dato**, pedida por dos participantes.

**No se toca nada de `frontend/` hasta que esta solicitud esté respondida.**
