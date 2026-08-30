# Retroalimentación del profesor · 27 de agosto de 2026

**Sesión.** Revisión de documentación. El profesor se centró en los documentos;
al final dio dos observaciones de frontend.
**Quién tomó notas.** Luna y otro compañero, en tiempo real durante la sesión.
**Registrado por.** Alejandro, el mismo día.

---

## Por qué este documento está partido en dos mitades

Es la regla que dejó **I-14**, aplicada por primera vez:

> Cuando una decisión se apoya en lo que dijo alguien de afuera, **la cita
> textual va en el registro, no la interpretación**.

El 24 de agosto una retroalimentación se parafraseó, la paráfrasis se convirtió
en una decisión de alcance, y se retiró un entregable que el profesor no había
objetado. Costó 515 líneas y cuatro días de sitio publicado con un defecto.

Así que abajo va **primero lo anotado, sin tocar**, y después, separado y
rotulado, lo que el equipo entiende de eso. Si mañana alguien discute una
decisión que salga de aquí, puede ver exactamente dónde termina el dato y dónde
empieza la lectura.

---

## PARTE 1 · Lo anotado, textual

Transcrito de las notas del grupo, en el orden y con las palabras en que se
tomaron. **No se corrige la redacción ni se completa nada.**

| Hora | Nota |
|---|---|
| 6:23 p. m. | Definición del problema |
| 6:27 p. m. | El documento de investigación debe ser tipo científico |
| 6:28 p. m. | Plantear preguntas de investigación y se responden en el desarrollo del documento |
| 6:29 p. m. | Trabajo relacionado: revisar algo de mi nombre |
| 6:29 p. m. | Introducción de trabajo relacionado |
| 6:30 p. m. | En aportes hacer una pequeña introducción |
| 6:33 p. m. | No mostrar avances donde no hemos llegado |
| 6:38 p. m. | Poner ver figura tal cuando se necesite |
| 6:38 p. m. | Incluir gráficos de resultados |
| 6:40 p. m. | Recalcar bien que metodología usamos |
| 6:41 p. m. | En la metodología se habla de como se resuelve el problema anterior mencionado |
| 6:41 p. m. | Metodología = como vamos a resolver el problema |
| 6:46 p. m. | Conclusión sale de la investigación realizada |
| 6:49 p. m. | Tabular los datos para hacer los gráficos |
| 6:52 p. m. | **Documentación técnica no va en IEEE** |
| 6:53 p. m. | Es documentación técnica |
| 6:57 p. m. | **Mapa de calor debe quedar arriba del riesgo** |
| 7:00 p. m. | Revisar lineas de mapa de calor |

**Limitación de esta fuente, y hay que declararla.** Son notas tomadas al vuelo
por dos personas distintas, no una transcripción. Recogen la idea, no
necesariamente las palabras. Donde una nota admite más de una lectura, esta
evidencia **lo dice y no elige**.

---

## PARTE 2 · Qué entiende el equipo de cada nota

Esto es interpretación. Empieza aquí.

### A. Instrucciones claras, sin margen de lectura

| Nota | Qué implica | Estado |
|---|---|---|
| «Documentación técnica no va en IEEE» | El documento técnico se rehace **sin** formato de conferencia. Se construyó en IEEE el mismo día | **Contradice lo entregado.** Hay que rehacerlo |
| «Mapa de calor debe quedar arriba del riesgo» | Orden de capas: la superficie va **encima** de la coropleta | **Contradice el código.** Hoy va debajo, a propósito |
| «Plantear preguntas de investigación y se responden en el desarrollo» | La pregunta existe en I-B; hay que **responderla explícitamente** en el desarrollo | Parcial |
| «Incluir gráficos de resultados» · «Tabular los datos para hacer los gráficos» | Hacen falta **figuras**, no solo tablas | No existe ninguna |
| «Poner ver figura tal cuando se necesite» | Referencias cruzadas del tipo «ver Fig. 3» | No existen |
| «En aportes hacer una pequeña introducción» | La subsección I-C entra sin preámbulo | Falta |
| «Introducción de trabajo relacionado» | La sección II entra directo al primer trabajo | Falta |
| «Recalcar bien qué metodología usamos» · «Metodología = cómo vamos a resolver el problema» | La sección III describe **técnicas**; tiene que decir cómo resuelven el problema de I-A | Hay que reencuadrar |
| «Conclusión sale de la investigación realizada» | La sección IX se escribe desde lo hallado, no desde lo esperado | Vacía todavía |

### B. Dos notas que el equipo NO puede resolver sin preguntar

**«No mostrar avances donde no hemos llegado»** admite dos lecturas, y llevan a
acciones opuestas:

| Lectura | Qué haríamos | A favor |
|---|---|---|
| No presentar como logrado lo que no lo está | **Nada.** El documento ya declara cada hueco | Es la lectura literal: habla de *mostrar avances* |
| No incluir las secciones a las que no se llegó | Quitar VII y IX, y VI-E | «Donde no hemos llegado» apunta a las secciones vacías |

Hoy las secciones VII y IX **están presentes y declaran qué van a contener y qué
falta**. Eso puede leerse como honestidad o como exactamente lo que pidió no
hacer. **No se elige por cuenta propia: se pregunta.**

**«Trabajo relacionado: revisar algo de mi nombre»** no se entiende fuera de
contexto. La escribió Luna y solo él puede decir a qué se refería. **Se le
pregunta antes de tocar la sección II.**

**«Revisar líneas de mapa de calor»** admite al menos tres lecturas: el borde de
la superficie recortada, los ocho puntos de origen dibujados encima, o los
límites distritales que se ven a través de la transparencia. **Se pregunta.**

### C. Una nota que choca con una decisión escrita, y hay que decidir cuál gana

«Mapa de calor debe quedar arriba del riesgo» contradice un comentario que está
en el código desde H5.4:

> *Va primero para que quede debajo de los polígonos: la superficie es contexto,
> no el dato principal.*

El razonamiento del equipo era que la coropleta es la estimación y la superficie
interpolada es contexto; poner el contexto encima del dato lo tapa.

**El profesor pidió lo contrario, y es una instrucción, no una sugerencia.** Se
acata. Pero conviene mirar dos cosas al hacerlo:

1. Con la superficie encima, **la coropleta se ve a través de ella** o no se ve.
   La opacidad de 0,7 puede tener que bajar.
2. Los ocho puntos de origen tienen que seguir visibles: son lo que impide leer
   la superficie como una medición continua del terreno.

**No es un cambio de una línea**, y por eso se anota en vez de hacerlo de una.

---

## PARTE 3 · Lo que esto cambia de lo entregado hoy

El avance de Semana 8 se entregó con tres documentos, y **uno de ellos está en un
formato que el profesor acaba de decir que no corresponde**.

| Documento | Estado |
|---|---|
| Avance de Semana 8 | Sirve |
| Documento de investigación IEEE | **Formato correcto**, contenido con observaciones |
| Documento técnico **en IEEE** | **Formato incorrecto.** Se rehace sin plantilla de conferencia |

Que el Markdown sea la fuente y el PDF un artefacto vuelve esto barato: es
cambiar el modo de construcción, no reescribir el documento.

---

## Lo que NO dice esta evidencia

No dice que el profesor haya objetado el contenido del documento técnico. Dijo
que **no va en formato IEEE**. Son cosas distintas, y confundirlas es lo que
produjo I-14.

Tampoco dice nada sobre el resto del visor. De frontend solo hay dos notas, las
dos sobre el mapa de calor.
