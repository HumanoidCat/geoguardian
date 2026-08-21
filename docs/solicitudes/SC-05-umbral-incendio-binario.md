# Solicitud de cambio de contrato · el umbral de incendio de `NivelRiesgo`

**ID.** SC-05
**Contrato afectado.** `contratos/enums.py`, docstring de `NivelRiesgo`; y
`contratos/simulados/datos.py`, `_nivel_desde`
**Solicitante.** Alejandro, desde H3.0
**Lo detecta.** César, al medir el riesgo **R16**
**Módulos que lo consumen.** `backend/modelado` (H3.0, H3.1, H3.2, H3.3, H3.4,
H3.5), `backend/etl` (H1.2), `frontend` (H7.1, H5.3, H5.4), `backend/api`
**Fecha.** 2026-08-20
**Estado.** Propuesta. Aprueba César como dueño de `backend/etl` y autor de la
medición.

---

## Lo que se midió

R16 estaba declarado en **D-08** como *"pendiente y prioritaria"* desde el inicio
del proyecto: si el cantón no tenía suficientes focos históricos, el evento de
incendio no era modelable. Era el riesgo abierto más antiguo.

César contó los focos de FIRMS dentro de cada distrito con las geometrías del
SNIT, punto en polígono, 2001-2024. **242 focos en 24 años.**

| Distrito | focos | ventanas con foco (de 1252) | P90 |
|---|---|---|---|
| 50804 Santa Rosa | 83 | 37 · 3,0 % | **0,0** |
| 50805 Líbano | 65 | 33 · 2,6 % | **0,0** |
| 50806 Tierras Morenas | 65 | 34 · 2,7 % | **0,0** |
| 50801 Tilarán | 15 | 12 · 1,0 % | **0,0** |
| 50802 Quebrada Grande | 7 | 5 · 0,4 % | **0,0** |
| 50803 Tronadora | 5 | 4 · 0,3 % | **0,0** |
| 50807 Arenal | 1 | 1 · 0,1 % | **0,0** |
| 50808 Cabeceras | 1 | 1 · 0,1 % | **0,0** |

---

## El defecto

El contrato define hoy:

> *"focos FIRMS en ventana de 7 días por distrito: bajo si 0; medio si
> 1 ≤ n ≤ P90; alto si n > P90."*

**Con P90 = 0,0 la condición `1 ≤ n ≤ 0` está vacía.** La clase MEDIO no puede
producirse nunca, y cualquier foco único cae en ALTO.

**La regla vigente ya se comporta como binaria.** No es que vaya a fallar: falla
hoy, y lo hace en silencio, porque nada comprueba que las tres clases sean
alcanzables.

### Y es estructural, no de calibración

El percentil 90 de una serie vale cero cuando **más del 90 %** de sus valores son
cero. Aquí las ventanas vacías van del 97 % al 99,9 %. César probó todas las
agregaciones alternativas:

| Configuración | ventanas con foco | ¿llega al 10 %? |
|---|---|---|
| Distrito · 7 días · 2001-2024 | 0,1 % a 3,0 % | no |
| Distrito · 7 días · solo 2012-2024 | 2,5 % a 3,4 % | no |
| Distrito · 7 días · solo estación seca | 6,4 % a 6,9 % | no |
| Cantón · 7 días · 2001-2024 | 7,7 % | no |
| Cantón · 7 días · 2012-2024 | 9,0 % | casi, no |
| Distrito · 30 días | 0,3 % a 9,2 % | no |
| Distrito · 90 días | 1,0 % a 22,7 % | sí, en algunos |

La única que llega contradice la ventana de 7 días del contrato y no sirve para
una alerta operativa.

### La objeción obvia, y por qué no salva la regla

Las 1252 ventanas del informe son **no solapadas**. La ventana operativa es
deslizante —cada día se pregunta por los siete anteriores—, y ahí son 8766 por
distrito, con un día de foco volviendo positivas hasta siete. Alguien podría
esperar que la proporción suba lo suficiente.

Medido, como cota superior:

```
50804: 44 dias con foco -> como maximo 308 de 8766 ventanas = 3,5 %
50805: 38 dias con foco -> como maximo 266 de 8766 ventanas = 3,0 %
50806: 36 dias con foco -> como maximo 252 de 8766 ventanas = 2,9 %
```

Sigue muy por debajo del 10 % que haría falta para que P90 ≥ 1.

---

## Cambio propuesto

**Ninguna firma cambia. Ningún esquema cambia.** Cambia lo que un valor
significa.

> **Para incendio, `alto` se define como «al menos un foco de calor en la ventana
> de 7 días», y `bajo` como «ninguno». MEDIO no existe para este evento.**

### Por qué esta formulación y no «predecir P(al menos un foco)» a secas

La propuesta original de César era predecir `p = P(al menos un foco)` y derivar
el nivel de esa probabilidad. El fondo es correcto y es lo que se hace. Pero
enunciada así **rompe D-21** en lugar de alinearse con él:

- D-21 fija que `probabilidad` es **P(nivel = alto)**, un solo significado para
  el campo, en los tres eventos.
- Si el nivel se derivara de `p` con cortes propios, `probabilidad` significaría
  *P(≥1 foco)* para incendio y *P(nivel = alto)* para los otros dos. Dos
  magnitudes bajo el mismo nombre, que es exactamente lo que D-21 vino a cerrar.

Al **definir** ALTO como «al menos un foco», P(≥1 foco) **es** P(nivel = alto).
El objetivo binario deja de ser una traducción y pasa a ser la definición de la
clase. D-21 se cumple literalmente y sin excepción por evento.

### Que MEDIO no exista se declara, no se deja implícito

`NivelRiesgo` sigue siendo el vocabulario común de los tres eventos. Que uno use
dos de sus tres valores es **propiedad del evento, no defecto del enum**. Escrito
en el docstring, comprobado por el verificador, y visible en el visor.

---

## Lo que cambia en el simulado

`_nivel_desde` recibe el `tipo_evento` y, para incendio, corta en la mitad en vez
de en tercios:

```python
if tipo_evento is TipoEvento.INCENDIO:
    return NivelRiesgo.ALTO if probabilidad >= 1 / 2 else NivelRiesgo.BAJO
```

El corte en la mitad es **tan arbitrario como los tercios de SC-03** y se declara
igual. Lo único que el simulado garantiza sigue siendo la monotonía.

Un doble que emitiera MEDIO para incendio produciría un valor que el contrato ya
no admite, y dejaría de servir para sustituir al original. Es el argumento de
SC-03 aplicado al vocabulario en vez de al determinismo.

---

## Versión

**v1.4.0.** Menor, no parche. Ningún esquema ni firma se toca, pero **lo que
significa un valor cambia** y los consumidores tienen que enterarse: el semáforo
de H7.1 muestra el umbral en pantalla y hoy cita el viejo.

---

## A quién le pega

| Quién | Qué | Qué hay que hacer |
|---|---|---|
| **Avril**, H7.1 | `frontend/src/datos/eventos.js` declara *"alto por encima del percentil 90 histórico"* en el tooltip de la columna | Cambiar el texto al umbral nuevo. Va en su PR #147 o en uno posterior |
| **César**, H1.2 | Ninguna. Los focos se guardan crudos igual | Nada |
| **Alejandro**, H3.0 | El etiquetado se vuelve binario para incendio | Rehacer los criterios de aceptación de ese evento |
| **H9.3** | *"Someter los umbrales de incendio"* a los actores locales | El umbral que se somete es otro, y ahora tiene una medición detrás |

**Nadie queda bloqueado por esto.** El cambio es de significado y de texto, no de
forma.

---

## Cómo se comprueba que quedó

Tres comprobaciones nuevas en `contratos/verificar.py`, y las tres fallaban antes:

- Incendio nunca sale con nivel medio.
- Incendio sí alcanza los dos niveles que le quedan, bajo y alto. Sin esta, un
  simulado que devolviera siempre `bajo` pasaría la anterior.
- Sequía y lluvia intensa conservan sus tres niveles, para que el cambio no se
  desborde a los otros dos eventos.

El verificador pasa de **44 a 47** comprobaciones.

---

## Lo que esta solicitud NO decide

**Si el evento de incendio se puede modelar de verdad.** Con 33 a 38 ventanas
positivas por distrito en los tres distritos con señal, la comparación de cuatro
algoritmos de H3.3 y H3.4 mide ruido de partición y no calidad de algoritmo. Eso
se decide en **D-25**, que además fija el alcance a esos tres distritos y declara
por adelantado que la línea base climatológica de H3.1 puede ser el techo real.

Se separa a propósito: esta solicitud arregla un contrato que hoy es imposible de
cumplir. La otra decide qué se puede prometer con estos datos.
