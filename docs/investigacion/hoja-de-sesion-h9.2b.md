# Hoja de sesión · H9.2b · Contraste con lo que la gente vivió

**30 a 40 minutos · bloques 0, 1, 5 y 6** del `guion-entrevista.md`.
Los bloques 2, 3 y 4 **no se hacen**: son H9.2a, y son otros participantes.

Esta hoja es el bloque 5 con lo que hubo que medir antes de poder correrlo.

---

## Lo que hay que saber ANTES de sentarse con alguien

### 1. Quien estima es la línea base climatológica, no un modelo entrenado

Se eligió con la regla de **D-39** y ningún algoritmo la supera fuera del ruido
(H3.6, H3.8, H3.9). En la práctica, la estimación de un día es **el almanaque de
ese distrito para ese mes**.

Entonces la pregunta de esta sesión no es «¿acertó el modelo?» sino:

> **¿Cuánto de lo que la gente vivió queda explicado por lo que es normal en ese
> distrito en ese mes, y cuánto no?**

### 2. Los dos casos de lluvia dan EXACTAMENTE la misma estimación

Medido contra la API publicada el **2026-09-14**:

| Distrito | Nate · 2017-10-05 | Rutas 925 y 927 · 2011-10-19 |
|---|---|---|
| Tilarán | medio · 0,0579 | medio · 0,0579 |
| Quebrada Grande | **alto** · 0,0968 | **alto** · 0,0968 |
| Tronadora | medio · 0,0199 | medio · 0,0199 |
| Santa Rosa | **alto** · 0,0835 | **alto** · 0,0835 |
| Líbano | **alto** · 0,1129 | **alto** · 0,1129 |
| Tierras Morenas | medio · 0,0560 | medio · 0,0560 |
| Arenal | medio · 0,0152 | medio · 0,0152 |
| Cabeceras | **alto** · 0,0939 | **alto** · 0,0939 |

**Idénticas hasta el cuarto decimal, con seis años de diferencia.** Los dos son
de octubre, y la climatológica no distingue días dentro del mes.

**Hay que saberlo de antemano y no presentarlo como si fueran dos estimaciones
distintas.** Si el participante lo nota —y el orden del bloque hace probable que
lo note— **se le da la razón y se anota literal**. Es el hallazgo, no un
tropiezo.

Es la versión local de lo que **H4.4** midió globalmente: realce 0,90x y **0,63x
pareado por mes**. La estimación publicada no distingue un día con evento de
cualquier otro día del mismo mes.

### 3. El caso de sequía NO tiene contra qué contrastarse

Medido el 2026-09-14: `?fecha=2014-09-30&tipo_evento=sequia` devuelve **ocho
filas con `nivel` nulo**. Por **D-34** la sequía no se estima.

Ese caso **no se contrasta**: se usa para preguntar qué habría esperado ver la
persona, y **la ausencia se declara tal cual**. No se sustituye por otro evento
para que la tabla quede completa.

### 4. El caso de incendio no lo puede anticipar ningún modelo climático

Según Bomberos, el fuego de Los Ángeles empezó **por extraer miel de un panal
quemando**. Es una causa humana. La pregunta 13 invita a decir que no, y **ese no
es la respuesta correcta**: es una limitación del enfoque, no un error del visor.

> **Corregido después de la primera ronda:** el sistema **no tiene ninguna
> estimación de incendio para Tilarán**, que es donde ocurrió este fuego, porque
> Tilarán no es uno de los tres distritos con señal de **D-25**. Solo Santa Rosa,
> Líbano y Tierras Morenas tienen valor, y lo escribe **regresión logística** con
> probabilidades del orden de **0,70**, no la climatológica.
>
> En la primera ronda se mostró por error una tabla marcada `[SIMULADO]` que
> nunca se sustituyó, y **el caso 4 quedó invalidado**. Ver la evidencia. **Las
> consultas se verifican contra la API el mismo día, sin excepción.**

---

## El orden, que no es negociable

**Primero lo que la persona vivió. Después lo que el sistema dijo.**

Si ve el mapa primero, lo que diga después no es su recuerdo: es su reacción al
mapa. Es la misma razón por la que el SUS va antes de los casos en H9.2a.

    1. ¿Qué pasó ese día en su distrito?
    2. (se anota, se cierra el cuaderno)
    3. Se muestra lo que el sistema estimó para esa fecha y ese distrito
    4. ¿Coincide con lo que usted vivió? ¿En qué sí y en qué no?

---

## Antes de que llegue

    [ ] /api/salud dice   modo: real
    [ ] Las cuatro consultas CORRIDAS HOY y pegadas en esta hoja
    [ ] Cargadas en pestanas aparte, SIN mostrarlas todavia
    [ ] dosier-casos.md a mano
    [ ] Anotada la hora de inicio

Las consultas, una por caso:

    2017-10-05  tipo_evento=lluvia_intensa      Nate
    2011-10-19  tipo_evento=lluvia_intensa      rutas 925 y 927
    2014-09-30  tipo_evento=sequia              devuelve NULOS
    2026-04-03  tipo_evento=incendio            Los Angeles de Tilaran

---

## Bloque 0 · Consentimiento · 5 min

Se lee en voz alta, **sin parafrasear**. Igual que en H9.2a:

- Es una prueba **de la herramienta, no de la persona**.
- Puede parar cuando quiera.
- **No aparece su nombre**, solo el distrito y si vivió o no el evento.
- Permiso para grabar. **Si dice que no, no se graba.**

Y una frase propia de esta sesión, que conviene decir al inicio:

> Le voy a preguntar primero qué recuerda usted, y solo después le muestro qué
> dijo el sistema. Es a propósito en ese orden.

## Bloque 1 · Contexto · 5 min

1. ¿Cuál es su rol y en qué distrito vive o trabaja?
2. ¿Cuánto tiempo lleva en ese distrito?
3. ¿Cuál de estos eventos le tocó vivir? *(se nombran los cuatro, sin dar
   detalles de qué pasó en cada uno)*
4. ¿Tiene algún registro propio de esos días? Bitácora, partes, fotos con fecha.

> **La 4 importa.** Nate fue hace **nueve años** y la sequía hace **doce**. Un
> recuerdo a esa distancia es reconstruido, y la gente recuerda mejor lo que más
> la afectó. Quien tenga registro propio pesa más que quien solo tenga memoria, y
> eso se declara en la evidencia.

---

## Bloque 5 · Los cuatro casos

Para **cada** caso, en el orden del dosier, y **sin adelantar qué distritos
resultaron más afectados**:

### Paso 1 — antes de mostrar nada

7. ¿Recuerda este evento? ¿Qué recuerda?

### Paso 2 — se muestra lo que el sistema estimó para esa fecha

8. ¿Qué le parece?
9. ¿Hay algún distrito que según usted debería verse distinto? ¿Cuál y por qué?

> **Si pregunta por qué el número es tan bajo**, la respuesta honesta es que ese
> porcentaje es la probabilidad que el sistema le da al nivel más severo, y que
> sale del historial del distrito para ese mes. **No se adelanta que lo produce
> una climatología**: eso se pregunta al final, en la 13b.

### Después de los cuatro

10. De los cuatro, ¿en cuál la herramienta se acercó más a lo que usted sabe?
11. ¿Y en cuál se alejó más?

### Preguntas propias de cada caso

**Caso 1 · Nate:**

12. En Cabeceras no tenemos ningún registro de daño para ese temporal. ¿Le consta
    algo distinto?

> **Está redactada a propósito para que sea fácil contradecirnos.** Si dice que sí
> hubo daño, **se anota como hallazgo del catálogo y no se discute**.

**Caso 4 · el incendio de abril de 2026:**

13. Según Bomberos, el fuego empezó por extraer miel de un panal quemando. ¿Una
    herramienta que solo mira clima podría haber anticipado algo ese día?

> La 13 invita a decir que no, **y ese no es una respuesta válida y valiosa**.

### La pregunta que cierra el bloque, y que es la de esta historia

**13b.** *(solo después de los cuatro casos)* Le cuento cómo funciona: el sistema
mira el historial de ese distrito para ese mes y dice qué tan normal es que llueva
fuerte en esa época. **No mira ese día en particular.**

> ¿Eso le sirve igual, o le sirve menos de lo que pensaba?

**Es la pregunta que responde qué vale la estimación para quien la usaría.** Va al
final a propósito: antes contamina todas las respuestas anteriores.

---

## Bloque 6 · Cierre · 5 min

14. ¿Usaría esto en su trabajo? ¿En qué situación concreta?
15. ¿A quién más del cantón le serviría?
16. ¿Qué le cambiaría primero?
17. **¿Hay algo que no le preguntamos y que deberíamos haber preguntado?**

> La 17 se hace siempre. En H9.2a aportó en las tres sesiones, y en H9.2b también:
> granularidad sub-distrital, la cadena aviso → respuesta, y cambiar la variable
> medida a días de cierre y población incomunicada.

---

## Al terminar

    [ ] Distrito y si vivio el evento — SIN NOMBRE
    [ ] Citas TEXTUALES entre comillas, no resumidas
    [ ] Si tenia registro propio o solo memoria
    [ ] Si noto que los dos casos de lluvia dan lo mismo, y que dijo
    [ ] Grabacion: quien autorizo, y si el archivo existe

---

## Lo que esta sesión NO puede concluir

- **No mide si el modelo acierta.** No hay modelo en lluvia: hay una climatología,
  y ningún algoritmo la supera fuera del ruido.
- **No vale como validación de la exactitud.** Cuatro casos, recordados a hasta
  doce años de distancia, por pocas personas.
- **No puede distinguir los dos casos de lluvia**, porque el sistema tampoco: son
  del mismo mes y dan idéntico. Esa imposibilidad **es** el resultado.
- **Un participante que diga que el mapa se equivoca** está juzgando al almanaque
  del distrito, no a un modelo. Se anota con esa aclaración o el dato se lee mal.
