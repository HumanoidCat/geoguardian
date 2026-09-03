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
| `componentes` | UML de componentes, por capa | Declarado en el generador |
| `secuencia-consulta-riesgo` | UML de secuencia, con la degradación de D-23 | Declarado en el generador |
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

El de **casos de uso es derivado en parte**, y la división importa. Un diagrama
de casos de uso suele ser lo más dibujado a mano que tiene un proyecto, y por eso
es lo primero que miente. Pero hay una mitad que **sí** está escrita en el
código: *qué puede pedirle alguien al sistema* son las rutas de
`backend/api/rutas.py`. Esos casos declaran su ruta y el CI comprueba que las
seis aparezcan. Los actores y los casos de operación no están escritos en ningún
lado, así que el generador es su fuente.

Los otros cinco están **declarados en el generador**, porque no se pueden derivar
del código con honestidad —un diagrama de despliegue no está escrito en ningún
lado—. Ese archivo **es** su fuente. No hay copia que se desactualice porque no
hay dos lugares donde vivan.

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
| CA-6 | Cada ruta de `backend/api/rutas.py` aparece en el de casos de uso, y ese diagrama no declara ninguna ruta que la API ya no tenga |
| CA-7 | El control distingue: una ruta inventada no aparece |

**CA-6 se comprueba en las dos direcciones, y la segunda costó dos intentos.** La
primera versión buscaba una marca en el SVG versionado; al intentar romperla
renombrando una ruta, **no falló**, porque esa marca solo se escribe al
regenerar. Era un control incapaz de decir que no —la forma de I-25—. Ahora
compara la tabla declarada contra `rutas.py` directamente, sin depender de que
nadie regenere. Se descubrió por intentar romperlo, no por leerlo.

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
