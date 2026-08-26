# Evidencia · D-28 · Retiro de la capa de mapa de calor

**Fecha.** 2026-08-26
**Responsable.** Avril Madrigal Elizondo
**Materia y criterio de rubrica.** Computacion Grafica, CG-1.
**Decision que lo ordena.** **D-28**, tomada por el Lead PM el 2026-08-24.
**Afecta al entregable de.** H5.4, que **queda cerrada**. Ver la nota al final.

---

## 1. Que se retira y por que

La capa conmutable descrita en el visor como *"Mapa de calor · Probabilidad
interpolada entre los ocho distritos"* sale del visor. No se arregla: se quita.

**El motivo no es la implementacion.** El codigo hace lo que la historia pedia. Lo
que no cierra es la premisa: **el riesgo se estima por distrito**, un valor por
poligono, y la interpolacion por distancia inversa entre los centroides de ocho
poligonos **produce valores intermedios donde no hay ninguna medicion**.

El paso silencioso que lo rompe es tratar un agregado distrital como si fuera una
medicion puntual en el centroide. El dato no dice que el riesgo en el centro del
distrito sea el que se muestra; dice que el distrito completo tiene ese nivel.

### Es coherente con lo que el proyecto ya decidio tres veces

| Registro | Que se rechazo | Por que |
|---|---|---|
| **I-05**, **D-15** | NASA POWER para precipitacion | su celda no distinguia entre distritos |
| **D-21** | leer `probabilidad` como confianza | decia mas de lo que el numero sostiene |
| **D-22** | imputar faltantes que no existian | rellenar donde no hay dato |

Rechazar una fuente porque 68 km de celda no permiten hablar por distrito, y
despues pintar un degradado suave entre ocho valores, no se sostiene: **el mapa de
calor sugiere variacion DENTRO del distrito, que afirma todavia mas.**

### Lo que ya estaba declarado, y no alcanzo

Al cerrar H5.4 esta limitacion quedo escrita como la primera de la evidencia:

> *Ocho puntos son muy pocos para una interpolacion. La superficie resultante es
> suave y parece un analisis fino, pero no lo es: es una tecnica de
> visualizacion, no una inferencia.*

La respuesta de entonces fue dibujar los ocho puntos de origen encima y declarar
en la leyenda sobre cuantos se calculo. **Avisar y mostrar no son lo mismo**: un
degradado continuo comunica resolucion espacial antes de que nadie lea la leyenda,
y este visor esta destinado al Comite Municipal de Emergencias.

Por eso la decision fue retirar y no etiquetar mejor.

---

## 2. Que se quito

**Tres archivos completos:**

- `frontend/src/componentes/CapaMapaCalor.jsx`
- `frontend/src/componentes/LeyendaMapaCalor.jsx`
- `frontend/src/datos/interpolacion.js`

**Y sus enganches** en `App.jsx`, `MapaCanton.jsx`, `ControlCapas.jsx`,
`capasBase.js` e `index.css`.

### Tres cosas que la decision no listaba y salen igual

**`centroidesDeColeccion`.** Vive en `interpolacion.js` y se comprobo que **solo
la usaba el mapa de calor**. Dejarla habria sido conservar el modulo entero por
una funcion sin consumidores.

**El estado `exponente` y su deslizador**, con las constantes
`EXPONENTE_IDW_INICIAL`, `_MINIMO` y `_MAXIMO`. Solo controlaban la
interpolacion.

**Cinco clases de CSS** —`.superficie-calor`, `.punto-origen`,
`.barra-gradiente`, `.barra-extremos` y `.leyenda-nota`— mas `.control-nota`, que
quedo sin uso porque la unica nota de control que existia era la del exponente.
Se verifico uno por uno que ningun otro componente los referenciara antes de
quitarlos.

**Por que se quitan y no se dejan.** Una constante exportada que nadie consume, o
una clase de CSS sin dueno, es una invitacion a reconstruir lo que se acaba de
decidir retirar. El razonamiento queda en un comentario de `capasBase.js`, que es
donde alguien va a mirar si se le ocurre volver a agregarla.

---

## 3. Como se verifico

### Lo que dicen las maquinas

```
npm run lint     limpio
npm run build    68 modulos transformados, 315,10 kB
```

**El conteo de modulos es la comprobacion mas util de esta historia**: pasa de
**71 a 68**, exactamente los tres archivos borrados, y el paquete baja de 319,89 a
315,10 kB. Si un enganche hubiera quedado suelto, el build habria fallado o el
conteo no cuadraria.

Mas los doce controles del proyecto y `verificar_escala.py` con sus 22
comprobaciones.

### Lo que solo se ve abriendo el visor

Un retiro es un cambio de riesgo asimetrico: **lo que se busca no es que algo
nuevo funcione, sino que nada de lo viejo se haya roto.** Un lint limpio no dice
nada sobre eso.

| Prueba | Resultado |
|---|---|
| El panel ya no ofrece "Mapa de calor" | Quedan tres capas: riesgo, limites, nombres |
| Las tres capas superpuestas se prenden y apagan | Funcionan |
| Las tres capas base se conmutan | OpenStreetMap, Relieve y Sin capa base, las tres |
| El deslizador de opacidad sigue presente y responde | Si |
| **El aviso de opacidad baja sigue apareciendo** | **Si, por debajo del 50 %** |
| Cambio de evento | El mapa se repinta correctamente |

**La quinta fila es la que mas importaba.** El aviso de opacidad es un hallazgo de
H5.2 y vivia en el mismo bloque de `ControlCapas.jsx` que el deslizador del
exponente que se elimino. Era lo que mas riesgo tenia de irse por accidente sin
que ningun control lo notara.

Se comprobo tambien que el umbral es **estricto**: a 50 % exacto el aviso no
aparece, a 45 % si. No es un defecto, pero conviene saberlo para no leer su
ausencia como una regresion.

### Capturas

| Archivo | Que muestra |
|---|---|
| `panel-sin-mapa-de-calor.png` | Las tres capas que quedan |
| `capas-base-siguen-funcionando.png` | El fondo neutro, sin capa base |
| `aviso-de-opacidad-intacto.png` | El aviso al 45 %, intacto |

---

## 4. H5.4 queda cerrada

**Lo hecho no se borra.** La historia se hizo, se evaluo y sus horas son reales.
Se le agrega una nota de revision en `docs/tareas/avril.md` que apunta a D-28, y
su evidencia se conserva completa.

El codigo queda en el historial de git. Si el proyecto llegara a estimar riesgo a
una resolucion menor que el distrito, la interpolacion vuelve a tener sentido y se
recupera de ahi.

---

## 5. Las horas

| | Horas |
|---|---|
| Estimacion previa | **n/d — no se estimo antes de arrancar** |
| **Real** | **1,25 h** (1 h 15 min) |

**El `n/d` es un incumplimiento del procedimiento y se declara como tal.** D-24
pide la estimacion **antes** de empezar, y aca no se dio: el retiro entro como
consecuencia de una decision ajena y se arranco directo. Estimarlo ahora seria
anclarlo al tiempo real, que es exactamente lo que D-24 evita.

No aparece en `verificar_horas.py` porque **no es una historia**: es la
consecuencia de D-28 sobre el entregable de H5.4, que ya estaba cerrada con sus
propias horas. Se anota aca para que el dato no se pierda.

**Vale como dato de calibracion igual**, y en una direccion que ninguna estimacion
del proyecto contempla: **retirar algo costo 1,25 h**, casi todo en comprobar que
nada mas se rompiera. El backlog estima construir; nadie estima quitar.

## 6. Observaciones

**Quien lo detecto.** El profesor del curso, al abrir el visor publicado el 24 de
agosto. Es la **primera valoracion del sistema por alguien de afuera del equipo**:
H9.2a, la validacion externa planificada, todavia no ocurrio.

Vale registrarlo porque el defecto no era invisible: la capa estaba en el visor
desde H5.4 y la limitacion estaba escrita en su propia evidencia. Hizo falta que
alguien ajeno la mirara para que la contradiccion con I-05 y D-15 se hiciera
evidente.

**Sobre revisar el propio trabajo.** Esta evidencia la escribe quien construyo la
capa que se retira. La conclusion es que la decision es correcta, y conviene decir
por que no es deferencia: el argumento no depende de una preferencia sino de una
incoherencia con tres decisiones anteriores del proyecto, y esa incoherencia se
puede comprobar leyendo I-05, D-15 y D-21.
