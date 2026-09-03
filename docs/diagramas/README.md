# Diagramas

**Estos archivos son artefactos. No se editan a mano: se regeneran.**

```bash
python docs/herramientas/generar_diagramas.py          # solo SVG
python docs/herramientas/generar_diagramas.py --png    # ademas PNG, para el documento
```

Hace falta **Graphviz**. En Windows: `winget install Graphviz.Graphviz`. En
Debian o Ubuntu: `sudo apt install graphviz`. El PNG necesita ademas
`pip install cairosvg`, y solo se usa para el documento de Word: el SVG alcanza
para el repositorio y para GitHub.

---

## Los siete

| Archivo | Qué muestra | Fuente |
|---|---|---|
| `entidad-relacion` | Las 8 tablas de `geo`, `crudo` y `control`, con claves y cardinalidad | **Derivado** de `basedatos/ddl/*.sql` |
| `casos-de-uso` | UML de casos de uso: quién le pide qué al sistema (H10.7) | **Derivado en parte** de `backend/api/rutas.py` |
| `flujo-datos` | De la fuente abierta a la pantalla | Declarado en el generador |
| `componentes` | UML de componentes, por capa | Declarado, **con los nombres comprobados** (CA-6, CA-7) |
| `secuencia-consulta-riesgo` | UML de secuencia, con la degradación de D-23 | Declarado, **con las rutas comprobadas** (CA-6) |
| `despliegue` | Contenedores, CI/CD y qué está publicado | Declarado en el generador |
| `flujo-modelado` | La épica E3: etiquetado, partición, estimadores, tabla | Declarado en el generador |

---

## Por qué un generador y no seis archivos dibujados

Un diagrama dibujado a mano es una **copia** del sistema, y toda copia se
desactualiza. Este proyecto ya perdió tiempo dos veces con esa forma de error
—I-04 y las cinco cifras del anexo del documento IEEE que dejaron de ser ciertas
en ocho días— y la respuesta fue siempre la misma: una sola fuente, vistas
derivadas, y una máquina que comprueba que coinciden.

El **entidad-relación es derivado**: sale de parsear el DDL. Si alguien agrega
una tabla y no regenera, `verificar_diagramas.py` lo detecta y el CI sale en
rojo.

Los otros están **declarados en el generador**. Ese archivo **es** su fuente: no
hay copia que se desactualice porque no hay dos lugares donde vivan.

**Que estén declarados no quiere decir que no se pueda comprobar nada de ellos, y
hasta H6.5 acá decía que sí.** La frase era «no se pueden derivar del código con
honestidad», y era demasiado ancha. Lo que no se deriva son **las capas, las
flechas y la degradación de D-23**: eso es criterio de quien dibuja.

Los **nombres** sí. Un componente es un archivo y una ruta de la API está escrita
en `rutas.py`. Mientras esa distinción no estuvo hecha, el diagrama de componentes
y el de secuencia decían `GET /riesgo` —en singular— contra una API que expone
`/riesgos`. Quien probara esa ruta se comía un 404, con un dibujo que se ve
autorizado.

Desde H6.5, `verificar_diagramas.py` comprueba en **CA-6** que cada ruta nombrada
en un diagrama exista en la API, y en **CA-7** que cada componente dibujado
corresponda a un archivo que existe —y que ninguno declarado falte del dibujo—.

El de **casos de uso**, agregado en H10.7, aplica esa misma distinción desde el
principio: los casos de consulta declaran su ruta, y los actores y los casos de
operación quedan declarados porque no están escritos en ningún lado.

**Y hacen falta las dos direcciones.** CA-6 va del dibujo al código: lo que un
diagrama nombra tiene que existir. **CA-8** va del código al dibujo: lo que la API
expone tiene que estar dibujado, para que un endpoint nuevo no deje el diagrama
corto en silencio. Cualquiera de las dos sola pasa en verde con el defecto que
busca la otra.

## Por qué Graphviz y no Mermaid

Mermaid renderiza en GitHub sin herramientas, que es una ventaja real. Pero
convertirlo a imagen para el documento necesita Chromium, y en el entorno de
construcción no está disponible.

Se descartó tener **dos** fuentes —Mermaid para leer, otra cosa para el
documento— porque dos fuentes del mismo diagrama es exactamente el problema que
el generador existe para evitar.

El SVG es texto, así que se revisa en un Pull Request como cualquier código.

## El diagrama de secuencia va aparte

Se emite como SVG escrito a mano, sin Graphviz. Una línea de vida de UML no es
una arista de un grafo dirigido, y forzarla produce algo que se parece a un
diagrama de secuencia sin respetar su semántica.

---

## Qué comprueba el CI

`python docs/herramientas/verificar_diagramas.py`, en el trabajo `gestion`.

| CA | Qué exige |
|---|---|
| CA-1 | Cada tabla y cada una de las 55 columnas del DDL aparecen en el entidad-relación |
| CA-2 | Cada clave foránea del DDL aparece como relación, con su columna |
| CA-3 | Los siete diagramas existen y no están vacíos |
| CA-4 | Lo que el generador produce hoy está en el SVG versionado |
| CA-5 | El control distingue: una tabla que no está, se detecta |
| CA-6 | Cada ruta **nombrada** en un diagrama existe en la API (H6.5) |
| CA-7 | Cada componente dibujado corresponde a un archivo que existe, y ninguno declarado falta del dibujo (H6.5) |
| CA-7b | El control distingue: un componente inventado ni existe ni aparece |
| CA-8 | Cada ruta que la API **expone** aparece en el de casos de uso, y ese diagrama no declara ninguna que ya no exista (H10.7) |
| CA-9 | El control distingue: una ruta inventada no aparece |

**CA-6 y CA-8 miran el mismo archivo en direcciones opuestas, y las dos hacen
falta.** CA-6 va del dibujo al código —lo que un diagrama nombra tiene que
existir— y nació de que `componentes` decía `GET /riesgo` contra una API que
expone `/riesgos`. CA-8 va del código al dibujo —lo que la API expone tiene que
estar dibujado— y evita que un endpoint nuevo deje el diagrama corto. Cualquiera
de las dos sola pasa en verde con el defecto que busca la otra.

**La mitad inversa de CA-8 costó dos intentos.** La primera versión buscaba una
marca en el SVG versionado; al intentar romperla renombrando una ruta, **no
falló**, porque esa marca solo se escribe al regenerar. Era un control incapaz de
decir que no —la forma de I-25—. Ahora compara la tabla declarada contra
`rutas.py` directamente. Se descubrió por intentar romperlo, no por leerlo.

> **Sobre la numeración.** CA-6/CA-7 y CA-8/CA-9 se escribieron el mismo día en
> dos ramas distintas, y las dos parejas eligieron los mismos números. Se detectó
> al integrar. La de H6.5 es anterior y conservó los suyos.
>
> No es anecdótico: pasó porque quien escribió los segundos **no miró los Pull
> Requests abiertos** antes de numerar. Es la misma forma de I-20 —concluir desde
> la mitad del estado— y el remedio es igual de barato: `gh pr list` antes de
> tocar un archivo compartido.

**No compara bytes.** Graphviz no garantiza la misma salida entre versiones, y
como el desarrollo es en Windows y el CI en Ubuntu, un cambio de versión del
motor habría puesto todo en rojo sin que ningún diagrama estuviera mal. Ese modo
de fallo ya se conoce —es el de I-13— y un control que la gente aprende a ignorar
es peor que no tenerlo.

Se compara el **contenido**: que cada nombre que el DDL declara esté presente en
el SVG. Sobrevive a cualquier versión de Graphviz y detecta lo único que importa.

---

## Convenciones de lectura

- **Línea discontinua** = todavía no existe. `analitico.riesgo` sin dueño, los
  tres algoritmos de H3.3 a H3.5, la API y la base en línea sin desplegar.
- **`*`** junto a una columna = `NOT NULL`.
- **Pata de gallo** del lado que referencia —muchos—; **barra** del lado
  referenciado —uno—.
- La paleta se eligió para que **sobreviva a la escala de grises**: el documento
  puede terminar impreso en blanco y negro, y un color que ahí no se distingue
  comunica menos que ninguno.
