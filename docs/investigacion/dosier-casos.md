# Dosier de casos historicos para la validacion externa

**Historia H9.1.** Material de apoyo para la sesion de H9.2b.

Este dosier reune **cuatro** eventos reales del canton de Tilaran, documentados
en el catalogo de H4.3, para que los participantes de la sesion de validacion
contrasten lo que el visor muestra contra lo que efectivamente ocurrio.

Cubren los tres tipos de evento del proyecto: dos de lluvia intensa, uno de
sequia y uno de incendio.

Todos los datos provienen de `docs/investigacion/catalogo-eventos.csv` y cada
uno conserva el numero de ficha de DesInventar que lo respalda. **No hay ningun
dato construido para esta sesion.**

## Como se usa

Cada caso se presenta en dos momentos:

1. **Antes de mostrar el visor.** Se lee al participante la descripcion del
   evento, sin decir que distritos resultaron mas afectados.
2. **Despues de mostrar el visor.** Se pregunta si lo que vio corresponde con lo
   que recuerda o con lo que sabe de la zona.

El orden importa. Si se muestra primero el mapa, el participante tiende a
confirmar lo que ya vio en pantalla, y la sesion deja de medir nada.

### Reglas para quien facilita

- **No adelantar cual distrito salio peor.** La pregunta es del participante
  hacia el visor, no al reves.
- **No defender el resultado.** Si el participante dice que el mapa se equivoca,
  eso es el dato que la sesion vino a buscar. Se anota literal, sin discutirlo.
- **No preguntar "verdad que se ve bien?".** Ver el guion de entrevista en
  `docs/investigacion/guion-entrevista.md` para la formulacion de cada pregunta.
- **Distinguir "no aparece" de "no ocurrio".** Vale para el visor y vale para el
  catalogo. Ver la advertencia del caso 1.

## Caso 1. Tormenta tropical Nate, 5 de octubre de 2017

El evento mejor documentado del catalogo: siete de los ocho distritos con ficha
propia, con perdidas en dolares y metros de via danada.

| Distrito | Codigo | Perdidas (USD) | Vias danadas (m) | Ficha |
|---|---|---|---|---|
| Quebrada Grande | 50802 | 726 148 | 123 471 | 2017-00768 |
| Tilaran | 50801 | 313 371 | 48 290 | 2017-00771 |
| Tronadora | 50803 | 166 310 | 18 580 | 2017-00772 |
| Santa Rosa | 50804 | 32 669 | sin dato | 2017-00769 |
| Tierras Morenas | 50806 | 24 681 | 17 750 | 2017-00770 |
| Arenal | 50807 | 1 808 | sin dato | 2017-00766 |
| Libano | 50805 | sin dato | 15 400 | 2017-00767 |

Total registrado: **1 264 987 USD** sobre los seis distritos que reportan cifra,
y **223,5 km** de via danada sobre los cinco que reportan longitud.

Detalle por distrito, en las palabras de las fichas: en Quebrada Grande se
afectaron 93 fincas de ganaderia de leche, 31 de platano, 3 de cafe y la escuela
La Esperanza. En Santa Rosa colapso por completo el alcantarillado y corto la
carretera. En Libano los deslizamientos obstruyeron cunetas y produjeron cortes
totales de carretera por socavacion. En Arenal hubo avenida torrencial con
socavacion de calzada y perdidas en cuatro fincas de ganado.

**Por que este caso es el mas util de los tres.** Entre Quebrada Grande y Arenal
hay una razon de **402 a 1** en perdidas registradas, el mismo dia y por el mismo
temporal. Si un participante conoce esa diferencia y el visor no la reproduce, es
un hallazgo concreto y no una impresion general sobre la interfaz.

**Advertencia que hay que leer en voz alta antes de este caso.** Cabeceras
(50808) **no tiene ficha** para Nate. Eso no significa que no le pasara nada:
DesInventar registra dano reportado, y la ausencia de reporte puede deberse a
que nadie lo levanto. Si un participante afirma que en Cabeceras si hubo dano,
**se anota como hallazgo del catalogo**, no se corrige al participante.

Es el mismo principio que ya esta documentado en H1.5 para los productos
grillados: la ausencia de un dato no es evidencia de la ausencia del fenomeno.

## Caso 2. Inundaciones de rutas, 19 de octubre de 2011

Tres distritos, sin cifras de perdida, con dano concentrado en la red vial.

| Distrito | Codigo | Que ocurrio | Ficha |
|---|---|---|---|
| Tilaran | 50801 | Ruta 925, del rio Higueron hacia San Jose. Paso cerrado por inundacion | 2011-00917 |
| Libano | 50805 | Ruta 925. Paso cerrado por inundaciones. Superficie de ruedo danada | 2011-00915 |
| Tierras Morenas | 50806 | Ruta 927, entrada principal hacia Tilaran y Canas. Paso regulado. Dano en superficie de ruedo | 2011-00916 |

**Por que esta un evento menor en el dosier.** Si los tres casos fueran
catastrofes, la sesion no podria distinguir si el participante reconoce
**niveles de riesgo** o simplemente reconoce **desastres**. Este caso existe
para probar esa diferencia: un sistema que pinta 2011 igual que Nate no esta
estimando riesgo, esta detectando que llovio.

Tambien es util porque el dano es vial y no agricola, mientras que en Nate y en
la sequia de 2014 el dano agricola domina. Permite preguntar si el visor le
sirve a alguien que decide sobre carreteras y no sobre cultivos.

## Caso 3. Sequia de 2014

Siete de los ocho distritos, con declaratoria de emergencia nacional.

**Decreto Ejecutivo 38642-MP-MAG.** Cinco de las siete fichas lo mencionan
expresamente: las de Tilaran, Quebrada Grande, Tronadora, Santa Rosa y Tierras
Morenas.

| Distrito | Codigo | Afectacion registrada | Ficha |
|---|---|---|---|
| Tilaran | 50801 | Chile picante y lechuga. Caudal disminuido en los acueductos de las ASADA de Monsenor Morera, San Luis y El Silencio | 2014-00193 |
| Quebrada Grande | 50802 | Cafe, en San Ramon y Las Nubes | 2014-00194 |
| Tronadora | 50803 | Tomate, chile dulce y lechuga | 2014-00195 |
| Santa Rosa | 50804 | Maiz, pasto y pasto de corte para ganaderia | 2014-00196 |
| Libano | 50805 | Cafe, maiz, aguacate, tomate, chile dulce, lechuga, pasto y pasto de corte | 2014-00197 |
| Tierras Morenas | 50806 | Tomate y chile dulce, pasto y pasto de corte | 2014-00198 |
| Arenal | 50807 | Disminucion **permanente** del caudal del acueducto de la ASADA de Arenal | 2014-00199 |

**Por que la sequia necesita su propio caso.** Los dos anteriores se ven: una
carretera cortada se fotografia. Una sequia no. Se manifiesta en el caudal de un
acueducto y en el rendimiento de un cultivo, meses despues de que dejo de
llover. Es el tipo de evento donde un visor de riesgo aporta mas, justamente
porque no hay nada que mirar por la ventana.

La ficha de Arenal merece atencion aparte: es la unica del catalogo que califica
un efecto como **permanente**. Vale la pena preguntar si alguien del canton lo
recuerda asi.

## Caso 4. Incendio en Los Angeles de Tilaran, 3 al 5 de abril de 2026

Un solo distrito, el evento mas reciente del catalogo y uno de los tres unicos
con severidad asignada.

| Campo | Valor |
|---|---|
| Distrito | Santa Rosa (50804) |
| Fechas | 3 al 5 de abril de 2026 |
| Severidad | **Alto** |
| Fuente | La Nacion, seccion Foros, 27 de abril de 2026, con testimonio de funcionarios del Cuerpo de Bomberos |

Segun la fuente: el fuego empezo alrededor de las 5 p.m. del Viernes Santo en
una finca ganadera de Los Angeles de Tilaran, avanzo por dos flancos y amenazo
un caserio vecino, otra finca colindante y el pueblo. Una lluvia fuerte lo
contuvo parcialmente esa misma tarde, y siguieron dos dias mas apagando focos
aislados. Participaron al menos 20 personas. La causa probable, segun Bomberos,
fue la extraccion de miel de un panal usando fuego.

**Por que este caso funciona bien en una sesion con personas.** Ocurrio hace
pocos meses, en Semana Santa, y movilizo a veinte vecinos. Es el evento del
dosier que mas probablemente los participantes vivieron de primera mano, y no
recuerdan de oidas.

**Por que no sirve para lo mismo que los otros tres.** Es un unico evento en un
unico distrito: no permite contrastar entre distritos como Nate, ni comparar
severidades como el par 2011-2017. Sirve para preguntar si el visor habria dicho
algo util **ese dia**, no para evaluar su discriminacion espacial.

**Tres advertencias que hay que tener presentes al usarlo:**

1. **La fuente es prensa, no un registro institucional.** Los otros tres casos
   vienen de fichas de DesInventar. Este viene de un reportaje con testimonio de
   Bomberos. Es verificable y esta citado, pero no es el mismo tipo de respaldo.
2. **La causa fue humana**, no climatica: fuego usado para extraer miel. Un
   modelo que estima riesgo a partir de variables climaticas **no puede
   anticipar eso**. Si un participante lo senala, tiene razon, y conviene
   anotarlo tal cual: es una limitacion real del enfoque, no un error del visor.
3. **Una lluvia fuerte lo contuvo el mismo dia.** Las condiciones de ese
   viernes no eran de sequia extrema. Vale preguntar que habria mostrado el
   visor y si eso habria servido de algo.

Este caso alimenta directamente a **H9.3**, que somete los umbrales de incendio
a criterio de los participantes.

## Lo que este dosier no incluye, y por que

**No hay ningun incendio forestal historico**, porque no existe ninguno
registrado.

En H4.3 quedo documentado que DesInventar distingue FIRE de FORESTFIRE, y que
en 56 anios de registro **las cuatro fichas FIRE de Tilaran son incendios
estructurales** —locales comerciales, una bodega—, ninguna forestal. El caso 4
es el unico evento de tipo incendio del catalogo, y entro por prensa.

Esto tiene consecuencia sobre **H4.4**: el contraste del modelo de incendio
contra eventos historicos no se puede hacer con este catalogo y habra que
resolverlo por otra via, por ejemplo los focos FIRMS de H1.2.

**Para la sesion de H9.2b la limitacion es distinta y menor.** Un solo evento no
alcanza para validar un modelo estadisticamente, pero si alcanza para preguntarle
a una persona si el visor le habria servido ese dia. Son dos usos distintos del
mismo dato.

**No se construyo ningun caso hipotetico.** Si hubiera hecho falta un segundo
incendio para "equilibrar" el dosier, no se habria inventado: los participantes
estarian opinando sobre un escenario que no ocurrio y no habria forma de separar
esa opinion de las demas.

Si en la sesion algun participante aporta un evento de incendio con fecha y
localidad, eso es material nuevo para el catalogo y se registra como tal, pero
no se improvisa un caso para la sesion en curso.

## Trazabilidad

Cada cifra de este documento sale de `docs/investigacion/catalogo-eventos.csv`,
validado por `python -m backend.calidad.validar_catalogo`. Los totales de Nate
se calcularon sobre esas filas y no se transcribieron de otra fuente.

Los codigos de distrito son los ocho de Tilaran, de 50801 a 50808, segun la
lista de `backend/calidad/validar_catalogo.py`. La comprobacion existe por la
incidencia **I-04**, en que un codigo con forma valida resulto ser de otro
canton.
