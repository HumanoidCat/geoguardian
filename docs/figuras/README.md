# Figuras de resultados

```bash
python docs/herramientas/generar_figuras.py
```

Necesita `matplotlib` y **el conjunto etiquetado cargado**.

---

## Estas se versionan. Los diagramas no. No es una inconsistencia

| | `docs/diagramas/` | `docs/figuras/` |
|---|---|---|
| Qué muestran | Arquitectura: cosas que se **declaran** | Resultados: cosas que se **miden** |
| De dónde salen | Del DDL y del generador, ambos versionados | Del conjunto etiquetado, que **no** se versiona |
| ¿Se pueden regenerar en el CI? | Sí, siempre | **No.** Falta el dato |
| ¿Se versiona el PNG? | No, se regenera | **Sí**, o se pierden |

Un diagrama que se puede reconstruir en cualquier máquina no hace falta
versionarlo. Una figura que necesita la base cargada, sí: si no está en el
repositorio, quien clone el proyecto no puede ver el documento completo ni
reconstruirla.

Es la misma razón por la que las tres cifras de la sección VI del documento de
investigación están declaradas como no recalculables por la integración continua.

---

## Las tres

| Archivo | Qué muestra | Dónde se usa |
|---|---|---|
| `cobertura-datos.png` | El período que describe cada etiqueta, con la década sin datos de incendio | Fig. 1, sección VI-A |
| `lineas-base.png` | F1-macro de las dos líneas base con la dispersión entre pliegues | Fig. 2, sección VI-D |
| `contraste-catalogo.png` | Cobertura contra tasa base, y el realce resultante | Fig. 3, sección VI-F |

**Las barras de error de `lineas-base.png` son el punto de esa figura, no un
adorno.** Sin ellas, dos de los tres veredictos de la sección VI-D —«empate
técnico»— resultan incomprensibles: se ve una barra más alta que otra y no se
entiende por qué no se declara ganador. Con ellas se ve que los intervalos se
solapan.

## Una corrección que vale la pena conocer

La primera versión de `cobertura-datos.png` decía que el incendio empieza en
**2000**, y el documento dice **2001**. Las dos cifras eran ciertas y hablaban de
cosas distintas: la primera etiqueta de incendio lleva fecha 2000-12-31, y la
ventana que esa etiqueta describe arranca el 2001-01-01.

La figura ahora dibuja **el período que la etiqueta describe**, no la fecha en que
está escrita. Es lo que corresponde y además coincide con el texto.

## Convenciones

- Paleta pensada para **sobrevivir a la escala de grises**: el documento puede
  terminar impreso en blanco y negro.
- Separador decimal con **coma**, como el resto de los documentos.
- Los rótulos se escriben aparte de los identificadores del código: el enum usa
  `sequia` sin tilde porque es una clave, y la figura dice «Sequía» porque es
  para leer.
