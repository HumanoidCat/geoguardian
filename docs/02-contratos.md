# Contratos entre modulos

Las interfaces se definen ANTES de implementar y quedan congeladas. Cada modulo
tiene ademas un simulado en `contratos/simulados/` que respeta el contrato, para
que nadie quede bloqueado esperando codigo ajeno.

Cambiar un simulado por el modulo real debe ser una linea, no una refactorizacion.

## Estado

Version de contratos: **1.3.3** · Congelados el 3 de agosto de 2026.

**Cambio v1.3.2 -> v1.3.3 (20 de agosto).** El quinto sitio:
`ExtractorFocosSimulado` sorteaba tambien contra un generador con estado, y SC-04
no lo cubrio porque la busqueda se limito a `RepositorioSimulado`. Lo encontro
Cesar. Le importa a **H1.2**, que implementa `ExtractorFocosCalor` de verdad: un
doble no reproducible hace que la prueba no pruebe nada.

En la misma revision: `_es_hueco` recibia el codigo de distrito y no lo miraba, de
modo que los ocho tenian hueco los mismos dias; `contar_focos` tenia un techo duro
de un foco por dia, que en FIRMS no existe; y quedaba un generador compartido sin
uso, que era una invitacion a repetir el defecto.

**Cambio v1.3.1 -> v1.3.2 (20 de agosto).** Los otros tres metodos de
`RepositorioSimulado` que sorteaban contra el generador compartido pasan a ser
deterministas: `obtener_mediciones`, `contar_focos` y `obtener_indices`.

El caso grave era el primero: **un mismo dia devolvia dos temperaturas segun el
rango en que se lo pidiera**, asi que una serie no se podia pedir en tandas. Los
huecos, ademas, dependian de la posicion dentro del rango y no de la fecha.

Sale de la solicitud **SC-04**. Lo detecto Cesar al revisar SC-03, comprobando si
el mismo defecto estaba en otro metodo. Estaba en tres. Ver **I-08**.

**Cambio v1.3.0 -> v1.3.1 (20 de agosto).** `RepositorioSimulado.obtener_riesgo`
pasa a ser **determinista** en sus tres argumentos, y su `nivel` se **deriva** de
la `probabilidad` en vez de sortearse aparte.

Ninguna firma cambia y ningun esquema cambia: lo que cambia son las garantias.
Antes, tres peticiones identicas a `GET /riesgos` devolvian tres respuestas
distintas, porque el simulado sorteaba contra un generador con estado que avanza
en cada llamada. Y desde D-21 producia filas imposibles, como nivel `bajo` con
probabilidad 0,90, porque `probabilidad` es P(nivel = alto).

Sale de la solicitud **SC-03**, redactada al implementar H6.6. Ver la incidencia
**I-08**. Tres comprobaciones nuevas en el verificador lo sostienen, y las tres
fallaban antes del arreglo.

**Cambio v1.2.0 -> v1.3.0 (18 de agosto).** `ProcesadorSenales.spi` recibe un
parametro nuevo, `meses: list[int] | None = None`, con el mes calendario de cada
posicion de la serie. Con el, la distribucion se ajusta por separado para cada mes
del anio, que es lo que convierte al SPI en un indice de **anomalia**.

El cambio es **aditivo**: el parametro va al final y con valor por defecto, asi
que ninguna llamada existente se rompe y el simulado lo acepta e ignora, porque no
ajusta ninguna distribucion.

Sale de la solicitud **SC-02**, que Luna redacto al implementar H2.3 en vez de
cambiar el contrato por su cuenta, y de la medicion que la sostiene: con ajuste
unico, **los 99 meses declarados en sequia caian, los 99, en estacion seca**. El
indice no detectaba sequia, detectaba que era verano. Ver la decision **D-19**.

**Cambio v1.1.0 -> v1.2.0 (11 de agosto).** Los codigos de distrito pasan de
`50501`-`50508` a los oficiales `50801`-`50808`. Tilaran es el canton **08** de
Guanacaste, no el 05; el prefijo `505` corresponde a Carrillo. El defecto lo
detecto Cesar al consultar el WFS del SNIT durante H1.3. Era un dato con forma
valida y contenido falso: ninguna validacion de tipo lo detecta. Ver incidencia
I-04. El verificador incorpora desde entonces una comprobacion explicita de los
ocho codigos.

**Cambio v1.0.0 -> v1.1.0 (3 de agosto).** `TipoEvento` incorpora
`LLUVIA_INTENSA`. Motivo: Tilaran esta en la vertiente del Arenal y la lluvia
intensa es su afectacion mas frecuente; estimar solo sequia e incendio dejaba el
sistema sin pertinencia territorial. Se hizo con cero codigo dependiendo del
enum. **Quien clono antes de esa fecha debe hacer `git pull` antes de empezar
cualquier historia.**

| Contrato | Archivo | Dueno | Simulado | Estado |
|---|---|---|---|---|
| Vocabulario del dominio | contratos/enums.py | Alejandro | no aplica | CONGELADO |
| Esquemas de la API | contratos/esquemas.py | Cesar | no aplica | CONGELADO |
| Extractores | contratos/fuentes.py | Cesar | si | CONGELADO |
| Repositorio | contratos/repositorio.py | Cesar | si | CONGELADO |
| Procesador de senales | contratos/senales.py | Alejandro | si | CONGELADO |
| Estimador y evaluador | contratos/modelado.py | Alejandro | si | CONGELADO |

Los seis contratos tienen simulado. Los dos ultimos se agregaron el 16 de agosto:
hasta entonces figuraban como pendientes y tenian detenidos 16 de los 39 casos del
plan de pruebas H10.1, el 41 por ciento.

## Verificacion ejecutada

`python -m contratos.verificar` ejecuta **44 comprobaciones** agrupadas en once
bloques. No comprueba solo que los simulados tengan los metodos: comprueba que
respeten las invariantes del proyecto.

    Los simulados cumplen los protocolos             6 comprobaciones
    Los datos faltantes son representables            4
    Lo que aun no existe se reporta vacio             4
    El procesamiento de senales no rellena huecos     6
    No hay estimacion sin modelo detras               4
    La validacion temporal no admite fuga             3
    El modo simulado es visible                       1
    El vocabulario del dominio esta cerrado           5
    El riesgo es reproducible y coherente con D-21    3
    La serie no cambia segun como se la pida          4
    Los extractores simulados son reproducibles       4
                                                     --
                                                     44

Los dos ultimos bloques se agregaron el 20 de agosto con SC-03 y SC-04, y las
siete comprobaciones fallaban antes de sus arreglos. Comprueban una propiedad que
ninguna de las anteriores miraba: **que preguntar dos veces lo mismo devuelva lo
mismo.** Los `isinstance` de arriba comprueban la forma; estas comprueban el
comportamiento por el que un doble puede ponerse en lugar del original.

Las tres comprobaciones de fuga temporal son las que menos se notan y mas valen:
una particion aleatoria sobre series temporales no rompe ninguna prueba por si
sola, infla las metricas y no se descubre hasta el analisis final, cuando ya
invalido el contraste de H1.

## Huecos conocidos del contrato

Se registran aqui, sin corregirlos: modificar un contrato congelado exige
solicitud de cambio aprobada.

**`ProcesadorSenales.anomalia` no recibe fechas.** La firma toma la serie y las
normales indexadas por mes, pero nada indica a que mes corresponde cada posicion.
El simulado supone que la serie es mensual y arranca en enero. Si esa suposicion
no se cumple, el resultado es silenciosamente incorrecto: no falla, devuelve
numeros equivocados. Corregirlo es agregar las fechas a la firma, en la proxima
version.

## Decisiones de diseno

**Protocol en lugar de clases abstractas.** Los simulados no heredan de nada ni
importan el contrato: lo cumplen por estructura. Eso significa que sustituir un
simulado por el modulo real es cambiar que clase se instancia, sin tocar a los
consumidores. Con `@runtime_checkable` se conserva la verificacion por
`isinstance` en las pruebas. Se descarto ABC porque acopla por herencia y obliga
a que el simulado conozca el contrato.

**Los faltantes son representables en todas partes.** Cada variable de medicion es
`Optional[float]`. Cero milimetros de lluvia es una medicion; ausencia de dato no
lo es. Confundirlos sesga el modelo y nadie lo detecta hasta que es tarde. Por eso
`obtener_mediciones` devuelve tambien los dias sin dato, y `SerieTemporal`
conserva los huecos como `None` en vez de omitir la fecha: el grafico muestra la
discontinuidad en lugar de una recta que aparenta continuidad.

**El riesgo sin modelo es nulo, no un valor por defecto.** `Riesgo.nivel`,
`probabilidad` y `explicacion` son opcionales. Un estimador sin entrenar lanza
`RuntimeError` al predecir en lugar de devolver algo plausible.

**La linea base cumple el mismo contrato que los modelos.** `Estimador` lo
implementan tanto la linea base climatologica como los tres algoritmos. La
comparacion queda justa por construccion: mismo codigo de evaluacion, mismas
particiones temporales.

**El modo simulado es visible.** Cada simulado registra una advertencia al
instanciarse y la API expone `modo: simulado` en `/salud`. El frontend muestra un
aviso cuando lo detecta. La regla de no inventar datos no se rompe: se hace
evidente que son simulados.

## Reglas

1. Un contrato congelado no se modifica sin solicitud de cambio aprobada por
   Alejandro y por todos los duenos de modulos que lo consumen.
2. Todo contrato nuevo nace junto con su simulado. Sin simulado, no esta listo.
3. Los simulados devuelven datos con la forma correcta pero declarados como
   simulados. Nunca datos que puedan confundirse con reales.
4. El frontend consume exclusivamente los esquemas de `contratos/esquemas.py`.

## Solicitud de cambio de contrato

    ID:
    Contrato afectado:
    Solicitante:
    Modulos que lo consumen:
    Cambio propuesto:
    Por que no se puede resolver sin cambiarlo:
    Impacto en cada consumidor:
    Aprobado por:
    Fecha:
