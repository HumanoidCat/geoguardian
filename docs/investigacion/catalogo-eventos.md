# Catalogo de eventos historicos del canton de Tilaran

**Historia:** H4.3 · **Responsable:** Luna · **Rubrica:** OE3
**Bloquea a:** H4.4 (contrastar estimaciones contra el catalogo) y H7.3

Este catalogo reune eventos historicos de lluvia intensa, sequia e incendio
forestal en el canton de Tilaran, con la fuente que documenta cada uno. Sirve
para contrastar las estimaciones del modelo contra la realidad (OE3).

El archivo legible por maquina es `catalogo-eventos.csv`, con las columnas del
esquema `EventoHistorico` de `contratos/esquemas.py`. Este documento explica de
donde sale cada fila y que decisiones se tomaron.

Se valida ejecutando:

    python -m backend.calidad.validar_catalogo

## Resumen

| | |
|---|---|
| Filas en el CSV | 46 |
| Eventos distintos (fecha de inicio + tipo) | 29 |
| Minimo exigido por la historia | 12 |
| Periodo cubierto | 1970 - 2026 |
| Tipos de evento cubiertos | 3 de 3 |
| Distritos con al menos un evento | 7 de 8 |

Una fila es la afectacion de **un distrito** en **un evento**. Un mismo
temporal que afecta cinco distritos genera cinco filas, porque el esquema
`EventoHistorico` exige `codigo_distrito` y no admite varios por registro.

## Fuentes

**DesInventar Costa Rica** (`desinventar.net`), inventario historico de
desastres administrado por UNDRR. Es la fuente principal: 41 de las 46 filas.
Se consulto el 2026-08-18 filtrando provincia Guanacaste, canton Tilaran, y
devolvio **98 fichas** del periodo 1968-2017. Cada ficha trae distrito
explicito, que es lo que ninguna otra fuente publica ofrece de forma
sistematica.

Es ademas la base que usan Quesada-Hernandez, Hidalgo y Alfaro (2020) en la
referencia `[15]` de `referencias.md`, o sea que no es una fuente elegida por
conveniencia: es la que la literatura del tema ya emplea para Guanacaste.

**Prensa nacional y partes de la CNE**, para el evento de mayo de 2017 y para
el incendio de 2026, que estan fuera del periodo cubierto por DesInventar o no
figuran en el.

## Decisiones de mapeo, y por que importan

DesInventar clasifica con un vocabulario propio de 29 tipos. El proyecto tiene
tres. La traduccion no es mecanica y **es el punto donde este catalogo puede
introducir errores**, asi que queda escrita:

| Tipo en DesInventar | Se mapea a | Criterio |
|---|---|---|
| FLOOD, RAIN, SPATE | `lluvia_intensa` | Directo. Son inundacion, lluvias y avenida torrencial |
| DROUGHT | `sequia` | Directo |
| FORESTFIRE | `incendio` | Directo. **No aparece ninguno en Tilaran** |
| LANDSLIDE | `lluvia_intensa` **solo si la ficha atribuye el deslizamiento a lluvia** | Ver abajo |
| FIRE | **no se mapea** | Ver abajo |
| EARTHQUAKE, ERUPTION, EPIDEMIC, ACCIDENT, STRONGWIND | fuera de alcance | El proyecto no estima estos eventos |

### Por que LANDSLIDE no se mapea en bloque

Un deslizamiento es una consecuencia, no un tipo de evento climatico. En este
canton la mayoria son disparados por lluvia, y mapearlos todos a
`lluvia_intensa` habria sido comodo. **Habria sido tambien un error grave.**

La ficha `1973-85` es LANDSLIDE en Rio Chiquito y su observacion dice
"Epicentro en Rio Chiquito": es el terremoto de Tilaran del 14 de abril de
1973, no un temporal. Mapear por tipo sin leer la observacion habria metido un
sismo en el catalogo de lluvia intensa, y ese registro habria contado como
fallo del modelo en H4.4 cuando en realidad el modelo no tiene por que
estimarlo.

Por eso solo entran los LANDSLIDE cuya ficha menciona lluvia de forma
explicita: `2017-00015` ("Fuertes lluvias provocaron varios deslizamientos"),
`1976-77` ("Llueve desde hace 24 horas"), `2017-00767` (parte del temporal del
5 de octubre de 2017), `2008-1006`, `2014-00073` y `1976-78`.

### Por que FIRE no es incendio forestal

DesInventar distingue FIRE de FORESTFIRE. Las cuatro fichas FIRE de Tilaran
son incendios estructurales: `2008-1286` ("incendio estructural con perdidas
totales"), `1987-103` (tres locales comerciales), `1987-37` (una bodega),
`1985-44` (dos locales comerciales). **Ninguno es un incendio forestal** y
ninguno entra al catalogo.

El resultado es que **DesInventar no registra ni un solo incendio forestal en
Tilaran entre 1968 y 2017**. El unico incendio del catalogo es el de abril de
2026, documentado por prensa. Esto se discute abajo.

## Severidad: por que 42 de 46 filas van vacias

`EventoHistorico.severidad` admite `None`, y aqui se usa a proposito.

Los umbrales de severidad del proyecto estan definidos en `contratos/enums.py`
sobre magnitudes fisicas: SPI-6 para sequia (D-32), percentiles P95/P99 de
precipitacion acumulada para lluvia intensa, conteo de focos FIRMS para
incendio. **Ninguna ficha de DesInventar reporta esas magnitudes.** Reportan
danos: viviendas, metros de via, perdidas en colones.

Asignar `bajo`, `medio` o `alto` a partir de los danos seria construir una
escala paralela que no es la del proyecto, y luego compararla contra las
predicciones del modelo como si fueran la misma cosa. Eso invalidaria H4.4.

Las cuatro filas que si llevan severidad son las que provienen de prensa y la
CNE, donde la asignacion es cualitativa por danos declarados; queda marcado en
este documento y en la descripcion de cada fila.

**Camino correcto para completarla**, cuando exista la serie climatica de H1.1:
recalcular la severidad de cada fecha aplicando los umbrales reales sobre la
precipitacion observada. Es trabajo de H4.4, no de esta historia.

## Sesgo del catalogo, declarado

Los tres tipos de evento **no se documentan igual**, y el catalogo lo refleja:

| Tipo | Filas | Por que |
|---|---|---|
| `lluvia_intensa` | 38 | La lluvia deja danos puntuales, fechados y localizables: una vivienda, un puente, una ruta. Se registra bien |
| `sequia` | 7 | Solo el episodio de 2014, y existe desagregado por distrito unicamente porque hubo declaratoria de emergencia (Decreto 38642-MP-MAG) que obligo a inventariar afectacion agropecuaria finca por finca |
| `incendio` | 1 | Ninguno en DesInventar. El unico proviene de prensa |

**Las sequias anteriores existen pero no son catalogables.** DesInventar tiene
fichas DROUGHT de Tilaran en 1972, 1973, 1976, 1977, 1982 y 1983, varias con
declaratoria de emergencia nacional. **Todas tienen el campo de distrito
vacio**: se registraron a nivel de canton. No se les asigna distrito y por
tanto no entran al CSV.

**Consecuencia para H4.4, que conviene anticipar.** El contraste del modelo
contra eventos reales sera solido para lluvia intensa, debil para sequia y
practicamente inexistente para incendio. Eso **no es un defecto de este
trabajo**: es un hallazgo sobre la disponibilidad de datos historicos a escala
distrital, y es material directo para la seccion de limitaciones del documento
IEEE. Un modelo de incendio que no se puede contrastar contra un catalogo es
un modelo cuya validacion externa hay que resolver por otra via, por ejemplo
los focos FIRMS.

## Cabeceras (50808) no tiene ningun evento

Es el unico distrito sin registros. No significa que no hayan ocurrido eventos
alli. Cabeceras es el distrito de creacion mas reciente del canton y las
fichas antiguas de DesInventar usan la division territorial vigente al momento
del registro. **No se inventa ninguna fila para rellenar el hueco.** El
validador lo reporta como aviso en cada ejecucion.

## Ambiguedad de toponimos: un problema que va a reaparecer

En Tilaran existen dos lugares llamados **Rio Chiquito**, y no pertenecen al
mismo distrito:

| Lugar | Distrito | Codigo |
|---|---|---|
| Rio Chiquito, poblado principal | Tilaran (central) | 50801 |
| Rio Chiquito Abajo | Tronadora | 50803 |

Senalado por Luna el 2026-08-17 por conocimiento local del canton.

Esto afecta a varias fichas de DesInventar que mencionan "Rio Chiquito" en el
campo Lugar. En esos casos se respeta **el distrito que asigna la propia
ficha**, no el que sugiere el nombre del lugar, porque la ficha la levanto
quien conocia el caso.

**Por que importa mas alla de este catalogo.** Los toponimos no son claves
unicas dentro del canton. Cualquier proceso que asigne distrito a partir del
nombre del poblado va a producir errores silenciosos, de la misma familia que
la incidencia I-04 (codigos de distrito de otro canton, con forma valida y
contenido falso). Debe considerarse al disenar H4.4 y quedar en la seccion de
limitaciones.

## Eventos que merecen mencion aparte

### Temporal del 5 de octubre de 2017 (Nate)

El evento mejor documentado del catalogo: siete fichas de DesInventar, una por
distrito, con perdidas cuantificadas en dolares y metros de via danada. Suma
mas de 1,2 millones de dolares en perdidas registradas en el canton. Es el
mejor caso disponible para el estudio retrospectivo de la historia H9.1.

### Sequia del 30 de septiembre de 2014

Siete distritos, con detalle de cultivos afectados por distrito y afectacion a
acueductos de ASADA. Es el unico episodio de sequia catalogable a escala
distrital en 56 anios de registro.

### Incendio del 3 de abril de 2026

Unico evento de tipo `incendio` del catalogo. Tres salvedades, todas
declaradas:

1. **La fuente es una columna de opinion**, no una nota informativa. Aporta
   testimonio de primera mano y cita a funcionarios de Bomberos, pero conviene
   respaldarla con el reporte oficial.
2. **El distrito lo aporto Luna** por conocimiento local (Los Angeles
   pertenece a Santa Rosa), no la fuente. Es la unica fila del catalogo cuyo
   distrito no proviene de la fuente citada.
3. **La fecha se derivo**, no se leyo. La fuente dice "el pasado Viernes
   Santo". La derivacion es reproducible: el mismo articulo fecha un dato
   independiente ("el lunes 6 de abril"), y el 6 de abril de 2026 fue lunes;
   el Domingo de Pascua de 2026 fue el 5 de abril, luego el Viernes Santo fue
   el **3 de abril de 2026**. Una busqueda web devolvio "10 de abril", que es
   incorrecto porque ese viernes cae despues de Pascua: se documenta el error
   para dejar claro por que la fecha se calculo en vez de aceptarse.

## Como se verifica

    python -m backend.calidad.validar_catalogo

El script carga cada fila del CSV contra el modelo Pydantic `EventoHistorico`,
comprueba que el codigo de distrito este entre 50801 y 50808 (incidencia
I-04), que `fecha_fin` no sea anterior a `fecha_inicio`, que ninguna fecha este
en el futuro y que toda fila declare fuente. Despues reporta la distribucion
por tipo, distrito y severidad, y cuenta los eventos distintos.

No corrige ni completa nada: reporta y devuelve codigo de salida distinto de
cero si algo falla, para que el CI pueda usarlo.

## Pendientes

1. Recalcular severidad con los umbrales reales cuando exista la serie
   climatica de H1.1. Es trabajo de H4.4.
2. Respaldar el incendio de 2026 con el reporte del Cuerpo de Bomberos.
3. Revisar si el Comite Municipal de Emergencias de Tilaran conserva registros
   posteriores a 2017 que DesInventar aun no incorpora.
4. Confirmar contra el INEC la pertenencia distrital de Los Angeles y de los
   dos Rio Chiquito.
