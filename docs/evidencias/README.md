# Evidencias

Cada historia terminada deja aqui su evidencia, **el mismo dia**. En la semana 12
no se reconstruye evidencia: se recopila la que ya existe.

## Donde va cada cosa

La carpeta se elige por el campo "Rubrica o objetivo" de la historia.

| Rubrica | Carpeta |
|---|---|
| CG-1 a CG-6 | `computacion-grafica/` |
| BD-1 a BD-4 | `bases-de-datos/` |
| SO-1, SO-4 | `sistemas-operativos/` |
| Senales | `senales-y-sistemas/` |
| Arq, CICD, Troubleshoot, Scrum | `arquitectura-software/` |
| OE1, OE2, OE3, OE4 | `objetivos/` |
| QA | `calidad/` |
| IEEE, MVP, Documentacion | `entregables/` |

Las cinco primeras corresponden a lo que evalua cada profesor. Las tres ultimas
no son materias: `objetivos/` respalda los objetivos especificos del proyecto y
alimenta el documento IEEE, `calidad/` guarda el plan y los resultados de pruebas,
y `entregables/` reune manuales, cartel y documento final.

## Quien puede escribir aqui

**Cualquier integrante, en la carpeta que corresponda a su historia, sin pedir
autorizacion.** Es la excepcion explicita a la regla de propiedad de `docs/`.

Lo que si requiere solicitud de cambio: crear una carpeta nueva de primer nivel,
o modificar la evidencia de otra persona.

## Como se nombra

    <ID-historia>-<descripcion-corta>.md

Por ejemplo: `H8.1-despliegue.md`, `H1.5-calidad-datos.md`.

Si la evidencia incluye capturas, van en una subcarpeta con el mismo nombre:

    H5.3-coropletas.md
    H5.3-coropletas/
        mapa-riesgo-alto.png
        leyenda.png

## Que lleva

Usar `docs/plantillas/plantilla-evidencia.md`. Lo esencial:

- Que se hizo
- **Como se verifico**: el comando exacto y su salida, no "probe y funciona"
- Resultado obtenido, con numeros
- Archivos relacionados
- Observaciones y limitaciones encontradas

La seccion de verificacion es la que mas peso tiene. Un evaluador quiere poder
repetir lo que hiciste.
