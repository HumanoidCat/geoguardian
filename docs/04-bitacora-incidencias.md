# Bitacora de incidencias

Las incidencias no son para repartir culpas. Son para que el error no se repita y
para tener material real en la seccion de limitaciones del documento IEEE.

Formato: que paso, causa raiz, accion tomada y aprendizaje.

---

## Plantilla

## I-00 · Titulo corto de la incidencia

**Fecha.**

**Quien lo detecto.**

**Que paso.** Descripcion objetiva, sin interpretacion.

**Causa raiz.** Por que paso realmente, no el sintoma.

**Accion tomada.** Que se hizo para resolverlo.

**Aprendizaje.** Que cambia de aqui en adelante para que no se repita.

**Impacto.** Horas perdidas, tareas afectadas, personas bloqueadas.

---

## I-01 · Docker no estaba instalado en la maquina del Lead PM

**Fecha.** 2026-08-03

**Quien lo detecto.** Alejandro, al intentar levantar el entorno por primera vez.

**Que paso.** El comando `docker` no existia. Instalarlo requirio Docker Desktop,
WSL2, crear una distribucion de Ubuntu y reiniciar la maquina.

**Causa raiz.** La Definition of Done exige "funciona desde docker compose up en
maquina limpia", pero nadie verifico que Docker estuviera instalado antes de
escribir esa regla.

**Accion tomada.** Instalacion de Docker Desktop 4.85 y WSL2. Integracion de WSL
activada para poder correr scripts bash. Se redacto `docs/ARRANQUE.md` para que
el resto del equipo no repita el proceso a ciegas.

**Aprendizaje.** Los prerrequisitos de la Definition of Done se verifican en las
cuatro maquinas antes de comprometerla, no cuando alguien la necesita.

**Impacto.** Alrededor de 1 h del Lead PM. Riesgo abierto de repetirse en las
otras tres maquinas: hay que preguntarles hoy.

---

## I-02 · El contenedor de PostgreSQL entraba en bucle de reinicio

**Fecha.** 2026-08-03

**Quien lo detecto.** Alejandro, al revisar `docker compose ps` despues del primer
arranque.

**Que paso.** El contenedor mostraba `Restarting (1)` de forma indefinida y no
aceptaba conexiones.

**Causa raiz.** El `docker-compose.yml` pasaba `--locale=es_ES.UTF-8` en
`POSTGRES_INITDB_ARGS`. Esa configuracion regional no viene generada en la imagen
base de postgis, por lo que `initdb` fallaba y el proceso moria al arrancar.

**Accion tomada.** Se sustituyo por `--locale-provider=icu --icu-locale=es-CR`,
que no depende de las configuraciones regionales del sistema operativo. Como el
init nunca llego a completarse, no habia datos que perder al recrear el volumen.

**Aprendizaje.** Un contenedor que reinicia en bucle casi siempre falla en su
script de arranque. `docker compose ps` solo muestra el sintoma: la causa esta
en `docker compose logs`. Revisar los logs antes de suponer.

**Impacto.** Alrededor de 20 minutos. Sin perdida de datos.

---

## I-03 · kubectl no podia conectarse al cluster de k3d recien creado

**Fecha.** 2026-08-11

**Quien lo detecto.** Alejandro, al ejecutar `kubectl get nodes` durante H8.6.

**Que paso.** `k3d cluster create geoguardian` termino con "Cluster created
successfully" y los contenedores de los nodos quedaron corriendo, pero cualquier
comando de `kubectl` fallaba tras cinco reintentos:

    dial tcp 192.168.40.27:61052: connectex: A connection attempt failed
    because the connected party did not properly respond after a period of time

**Causa raiz.** k3d escribe la direccion del servidor de la API en el kubeconfig
como `https://host.docker.internal:<puerto>`. En una maquina con varias
interfaces de red, ese nombre resuelve a una direccion que no es la del anfitrion
donde k3d publico el puerto, y la conexion se pierde. El cluster estaba sano: el
problema era solo la direccion escrita en el kubeconfig.

**Accion tomada.** Se apunto el kubeconfig a la direccion de bucle local:

    kubectl config set-cluster k3d-geoguardian --server=https://127.0.0.1:61052

Como correccion permanente, `infra/k8s/README.md` documenta crear el cluster
fijando la direccion desde el inicio, para que no dependa de como resuelva
`host.docker.internal`:

    k3d cluster create geoguardian --agents 1 --api-port 127.0.0.1:6445

**Aprendizaje.** Un error de red de `kubectl` no significa que el cluster este
mal creado. Antes de borrar y recrear —que cuesta varios minutos de descarga de
imagenes— conviene mirar a donde apunta el kubeconfig:

    kubectl config view --minify -o jsonpath="{.clusters[0].cluster.server}"

En este caso se estuvo a punto de borrar un cluster que funcionaba
perfectamente.

**Impacto.** Alrededor de 25 minutos del Lead PM. Sin perdida de datos. Afecta a
cualquiera del equipo que levante k3d en una maquina con VPN o con varias
interfaces de red, asi que quedo documentado en el README y en la tabla de
diagnostico.

---

## I-04 · Los codigos de distrito de los contratos no eran los oficiales

**Fecha.** 2026-08-11

**Quien lo detecto.** Cesar, al redactar los criterios de aceptacion de H1.3,
antes de escribir una linea de codigo.

**Que paso.** Los simulados de `contratos/simulados/datos.py` usaban los codigos
50501 a 50508 para los ocho distritos de Tilaran. Los codigos oficiales del SNIT
son **50801 a 50808**: Tilaran es el canton 08 de Guanacaste, no el 05. El rango
505xx corresponde al canton de Carrillo. Los ocho nombres de distrito si eran
correctos; solo el prefijo de canton estaba mal.

**Causa raiz.** Al escribir los simulados se invento el prefijo de canton en
lugar de consultarlo en la fuente oficial. Es la regla de no inventar datos, rota
por quien la escribio.

Dos controles que existian y no lo detectaron:

- `contratos/verificar.py` comprobaba que hubiera ocho distritos, pero no que los
  codigos existieran en la realidad. Verificaba estructura, no contenido.
- `docs/plantillas/como-llenar-el-pr.md`, escrito la misma semana, usa `50801` en
  su ejemplo. El codigo correcto ya estaba en la documentacion y nadie cruzo los
  dos archivos.

**Accion tomada.** Contratos a **v1.2.0** con los codigos corregidos en
`simulados/datos.py`, `esquemas.py` y `verificar.py`. Se agregaron dos
comprobaciones nuevas al verificador: que todos los codigos empiecen por `508` y
que sean exactamente 50801 a 50808 sin repeticiones. Se registro la fuente
oficial de geometrias como decision de arquitectura (D-13). Se aviso al equipo de
hacer `git pull`.

**Aprendizaje.** Cuando el fallo se manifiesta tarde y lejos de su causa, hay que
verificarlo temprano y cerca. Sin la correccion, el error habria aparecido recien
en H1.2, cuando ningun foco de calor cayera dentro de ningun distrito, con una
causa raiz muy cara de diagnosticar.

Lo que hay que copiar del hallazgo: Cesar comparo el dato del repositorio contra
la fuente oficial **antes** de implementar, y al ser `contratos/` un archivo
compartido, reporto en lugar de corregir por su cuenta.

**Impacto.** Cero horas perdidas, porque se detecto antes de que nadie
implementara contra el valor equivocado. Sin la deteccion, la estimacion es de
varios dias de diagnostico en el Sprint 1.

---

## I-05 · La fuente climatica no distingue entre los distritos del canton

**Fecha.** 2026-08-16

**Quien lo detecto.** Cesar, al redactar los criterios de aceptacion de H1.1,
antes de escribir una linea del extractor.

**Que paso.** NASA POWER devuelve exactamente el mismo valor para dos puntos
distintos del canton, hasta el ultimo decimal, e incluso la misma elevacion. La
causa es la resolucion: POWER sirve MERRA-2 en una malla de 0,5° × 0,625°, unos
68 × 55 km a la latitud de Tilaran. El canton mide 669,23 km² y cabe entero
dentro de una sola celda.

Dos de los tres eventos se definen sobre precipitacion: sequia por SPI-3 y lluvia
intensa por acumulado de 72 h contra los percentiles del propio distrito. Con una
sola celda, los ocho distritos habrian dado el mismo riesgo siempre, por
construccion.

**Causa raiz.** Se eligio la fuente por cobertura temporal y facilidad de acceso
—series diarias desde 1981, sin registro— y nadie comprobo su resolucion espacial
contra el tamanio del area de estudio. La decision D-01 llego a escribir que
"POWER entrega una celda de reanalisis, no una estacion en Tilaran", pero se
trato como una limitacion aceptable de precision y no como lo que era: la
imposibilidad de cumplir el objetivo por distrito, que es el titulo del proyecto.

Nadie hizo la cuenta de cuantos distritos caben en una celda. Es una division.

**Accion tomada.** Fuente hibrida (**D-15**): CHIRPS a 0,05° para precipitacion,
que es la variable que define los dos umbrales rotos, y POWER para temperatura,
humedad, radiacion y viento, que no definen ninguno. La decision queda
condicionada a repetir el mismo test de dos puntos sobre CHIRPS antes de escribir
el extractor.

Se corrigio ademas la ventana de descarga, de 2016-2025 a 1991-2025: la linea
base de D-10 se define sobre la normal climatologica 1991-2020 y con diez anios
no se podia calcular como esta declarada. Ese segundo defecto salio de la misma
revision.

**Aprendizaje.** Una fuente de datos se evalua contra el area de estudio, no en
abstracto. La pregunta "cuantas celdas caben en el area" es una division y hay
que hacerla al elegir la fuente, no al implementar el extractor.

Lo que hay que copiar del hallazgo, otra vez: comprobar la fuente **antes** de
implementar. Es el segundo defecto grave que aparece por ese orden de trabajo
—I-04 fue el primero— y en los dos casos el costo fue cero.

Vale registrar tambien el contraejemplo: en el mismo documento la extension del
canton figuraba como 22 × 17 km, que son 374 km², cuando el area medida en H1.3
es 669 km². Un poligono no puede tener mas area que su caja envolvente. El numero
salio de medir la separacion entre los dos puntos de muestreo y no los extremos
del canton. No invalida el hallazgo, pero cambiaba el modo de fallo: si el borde
este del canton pasa de la longitud -84,6875, parte de los distritos cae en la
celda vecina y en vez de un valor uniforme habria dos, separados por una linea
recta que no corresponde a ningun accidente geografico. Eso es peor, porque
parece senial.

**Impacto.** Cero horas perdidas de implementacion: el extractor no llego a
escribirse. H1.1 queda bloqueada unos dias mientras se verifica CHIRPS. Sin la
deteccion, el defecto habria aparecido en la semana 8 o 9, con el modelo entrenado
y el visor pintando ocho poligonos identicos, y con la pregunta de investigacion
ya respondida por construccion.

## I-06 · El CI corria pytest de una forma que ninguna persona usaba

**Fecha.** 2026-08-18

**Quien lo detecto.** Alejandro, al revisar por que el trabajo de pruebas del PR
#110 salia en rojo mientras la misma suite pasaba en la maquina de Luna.

**Que paso.** El PR #110 trae la primera prueba automatizada del proyecto,
`backend/tests/test_filtros.py`. En la maquina de quien la escribio pasan los 19
casos. En el CI el trabajo fallaba al recolectar, antes de ejecutar ninguna
prueba:

    ModuleNotFoundError: No module named 'backend'

Los otros cuatro trabajos del pipeline salian en verde, asi que el fallo parecia
un defecto de la historia. No lo era: el codigo entregado estaba bien.

**Causa raiz.** El flujo de trabajo invocaba `pytest` como script de consola. Ese
script **no agrega el directorio actual al path de importacion**; `python -m
pytest` si lo hace. Como `backend/` no tiene `__init__.py` ni el proyecto se
instala como paquete, la importacion de `backend.senales.filtros` solo resuelve
si la raiz del repositorio esta en el path.

El resto de los controles del proyecto ya se invocaban con `python -m`
—`python -m contratos.verificar`, `python -m ruff check`—, asi que la unica linea
que no seguia la convencion era justamente la que nunca se habia ejecutado. El
paso estaba protegido por una condicion que lo saltaba mientras no existieran
pruebas, y por eso el trabajo llevaba dos semanas en verde sin haber corrido
nunca.

**Un control que nunca fallo no esta probado.** Es el mismo argumento con el que
se valido el verificador de documentacion inyectandole un numero falso, y aqui no
se aplico.

**Accion tomada.** Dos cambios, deliberadamente redundantes:

1. `.github/workflows/ci.yml` invoca `python -m pytest`, igual que el resto de los
   controles.
2. `pyproject.toml` declara `pythonpath = ["."]` en la configuracion de pytest, de
   modo que **las dos formas de invocar den el mismo resultado**. Sin esto, quien
   corriera `pytest` a secas en su maquina veria un fallo que el CI no muestra, o
   al reves.

El segundo es el que cierra la clase de defecto: el problema no era que el CI
estuviera mal, era que el CI y la maquina de quien escribe la prueba discrepaban.

Queda pendiente convertir en fallo el salto del paso cuando no hay pruebas. No se
hizo en el mismo cambio porque este arreglo tiene que integrarse **antes** que el
PR #110, que es el que aporta la primera prueba, y hasta entonces `dev` no tiene
ninguna.

**Aprendizaje.** Un paso de CI protegido por una condicion que lo salta no es un
control: es un control apagado que se ve igual que uno encendido. Mientras la
condicion se cumpla, el trabajo sale en verde sin haber comprobado nada, y el
primero que dependa de el se lleva el fallo.

Cuando un paso quede desactivado a la espera de algo, hay que probarlo contra un
caso de prueba de mentira el mismo dia en que se escribe, o dejar registrado que
esta apagado. Que el trabajo aparezca en verde en la interfaz de GitHub no
significa que haya corrido.

**Impacto.** Cero para el equipo, mas alla de una revision. El defecto era del
pipeline, no de la historia: `backend/senales/filtros.py` y sus 19 pruebas
estaban correctos desde el primer envio. El costo real lo habria tenido de no
haberse revisado: el autor de la primera prueba del proyecto habria pasado horas
buscando un error inexistente en su codigo, y la conclusion natural —"las pruebas
automatizadas dan problemas"— es cara de revertir en un equipo que apenas empieza
a escribirlas.

## I-07 · Una cifra derivada escrita a mano rompia el CI de quien no la toco

**Fecha.** 2026-08-19

**Quien lo detecto.** Cesar, al cerrar H1.8 y ver su Pull Request en rojo por algo
que no habia escrito.

**Que paso.** `docs/08-backlog.md` declaraba cuantas historias van cerradas:

    Al 18 de agosto de 2026: **18 historias cerradas de 84**, 84 puntos de 422.

Es una cifra que se calcula contando las marcas de `docs/tareas/*.md`, y que por
lo tanto **cambia cada vez que cualquiera cierra una historia**. El verificador de
documentacion la comprueba y es obligatorio en el CI.

El resultado: **el siguiente Pull Request de quien sea sale en rojo sin haber roto
nada.** Le toco a Cesar, y le habria tocado a los cuatro por turnos. Quedaban 65
historias por cerrar, o sea 65 ocasiones.

**La demostracion, que aparecio sola.** Cesar tenia dos Pull Requests abiertos,
#125 y #126. Los dos corrigieron la linea al mismo valor, 19, y cada uno era
correcto por separado. Al integrar los dos el valor real pasaba a 20, asi que **la
fusion de dos PR individualmente correctos dejaba `dev` en rojo**. Se comprobo
integrando ambos en una copia local antes de mergear:

    historias cerradas: 20
      - docs/08-backlog.md: dice '19' y el valor real es '20'

**Causa raiz.** La introduje yo el 18 de agosto, un dia despues de escribir la
decision **D-20**, que dice exactamente que un dato calculable no se escribe a
mano. Agregue la linea al backlog y la puse a comprobar por el verificador, sin
aplicarle el principio que acababa de registrar.

Es la tercera vez que el mismo patron aparece en el proyecto: I-04 con los codigos
de distrito, la matriz de trazabilidad con los duenos, y ahora esta linea.

**Accion tomada.** La linea la escribe `docs/herramientas/generar_matriz.py`, que
pasa a generar los dos artefactos derivados de la documentacion: la matriz y esta
cifra. **No agrega ningun paso**: quien cierra una historia ya tenia que correr esa
herramienta, porque la fila de la matriz tambien cambia.

Se fecha con el **ultimo cierre** y no con el dia de hoy. Con la fecha actual,
regenerar sin haber cerrado nada produciria un cambio en el archivo y el CI
empezaria a fallar por el paso del tiempo.

Al hacerlo aparecio un segundo defecto: la cifra de **puntos** de esa misma linea
decia 84 y el valor real era 97. Ese numero **no lo comprobaba nadie**, asi que
llevaba desfasado sin que se notara. Lo detecto Cesar tambien.

**Aprendizaje.** Un verificador convierte un dato desactualizado en un fallo
ruidoso, que es una mejora. Pero **si el dato es derivado y el verificador es
obligatorio, el fallo le cae a quien no lo causo**, y eso es peor que el problema
original: castiga al que trabaja.

La regla que sale de aqui, y que completa a D-20:

> Antes de poner una cifra bajo verificacion obligatoria, hay que preguntarse
> **quien la actualiza**. Si la respuesta es "el proximo que pase por aqui", la
> cifra tiene que generarse, no comprobarse.

**Impacto.** Un Pull Request bloqueado y el tiempo de Cesar en diagnosticarlo, que
uso bien: en vez de corregir el numero y seguir, escribio el analisis del patron y
propuso la solucion. Sin ese diagnostico, el siguiente en toparselo habria vuelto a
corregir a mano.

### Segundo punto ciego, encontrado el mismo dia

Al arreglar lo anterior aparecio un defecto peor, y lo encontro Cesar siguiendo la
instruccion que le di.

Su Pull Request #126 quedo con las **tres marcas de conflicto dentro del archivo**.
Las dos versiones del bloque eran identicas —las dos ramas escribieron la misma
cifra— asi que el conflicto era de forma y no de contenido, y no se noto al
resolverlo.

**Ningun control lo detecto.** Los ocho pasaron:

- `verificar_documentacion` encontro la linea buena entre las marcas y la dio por
  correcta.
- `generar_matriz` tenia el mismo punto ciego: sustituia la linea que coincidia y,
  como el resultado era igual a la entrada, informaba **"al dia con sus fuentes"**
  con las marcas todavia adentro.

Lo segundo es lo grave: **la instruccion que da el proyecto para resolver un
conflicto en un archivo derivado es regenerar, y regenerar no lo arreglaba.**
Cesar lo comprobo al intentarlo y tuvo que quitar las tres lineas a mano.

**Accion tomada.**

1. `generar_matriz.py` **se niega a trabajar** sobre un archivo con marcas, en vez
   de informar que esta al dia. El mensaje dice que regenerar no lo arregla.
2. Un paso nuevo en el trabajo de calidad del CI busca marcas en todo el
   repositorio. El pipeline pasa a **nueve controles**.

**El detalle del patron de busqueda, que aporto Cesar.** La version ingenua
`^=======` produce falsos positivos: las salidas de los verificadores que se pegan
en las evidencias llevan lineas de separacion de 66 y 74 signos de igual, y hay
cuatro en dos archivos. Una marca de conflicto son **exactamente siete
caracteres**, y el separador va solo en su renglon:

    ^(<{7} |={7}$|>{7} )

Comprobado contra el repositorio completo: cero falsos positivos.

**Aprendizaje.** Un control que busca un dato correcto no detecta la basura que lo
rodea. Y una herramienta que informa "al dia" cuando no pudo hacer su trabajo es
peor que una que falla: **el silencio se lee como exito.**

La regla que se agrega:

> Una herramienta que sustituye contenido tiene que comprobar que la entrada esta
> en un estado que le permita trabajar, y negarse si no. Devolver "sin cambios" es
> ambiguo entre "ya estaba bien" y "no pude".


---

## I-08 · La misma consulta a la API devolvia un valor distinto cada vez

**Fecha.** 2026-08-20

**Quien lo detecto.** Alejandro, al empezar H6.6 y llamar dos veces al mismo
endpoint para comparar la respuesta con lo que espera el visor.

**Que paso.** Tres peticiones identicas a
`GET /riesgos?fecha=2026-08-16&tipo_evento=sequia`:

| Intento | 50801 | 50802 | 50803 |
|---|---|---|---|
| 1 | bajo · 0,46 | alto · 0,53 | medio · 0,79 |
| 2 | alto · 0,70 | bajo · 0,90 | alto · 0,75 |
| 3 | medio · 0,56 | alto · 0,73 | bajo · 0,64 |

**Causa raiz.** `RepositorioSimulado.obtener_riesgo` sorteaba contra `self._rnd`,
un generador **con estado** que avanza en cada llamada. La instancia se cachea una
vez por proceso —correcto, y bien razonado en `backend/api/dependencias.py`— y el
efecto secundario es que el generador nunca vuelve al principio.

**Lo que se habria visto.** El mapa repintando los ocho distritos con colores
distintos cada vez que el usuario cambia de evento y regresa. Habria parecido un
defecto de las coropletas de H5.3, que estan bien. Es el segundo caso en el
proyecto de un sintoma que apunta a la persona equivocada.

**Por que no lo vio H6.1.** Cesar verifico que cada endpoint devolviera la forma
acordada, que es lo que la historia pedia. Llamar dos veces con los mismos
parametros y comparar no forma parte de comprobar una forma. Hizo falta un
consumidor que preguntara dos veces, y el primero es el visor.

**El detalle que lo hace peor de lo que parece.** La primera linea de
`contratos/simulados/datos.py` dice:

> *"Repositorio y extractores simulados. Datos deterministas, reproducibles y
> falsos."*

El archivo ya se comprometia a esto. Cumplia entre construcciones —dos procesos
que instancian y llaman una vez coinciden, y por eso el exportador de Avril
producia archivos estables— y dejaba de cumplir a la segunda llamada. **Una
promesa escrita en la primera linea del archivo y no comprobada por nada.**

**El segundo hallazgo, del mismo dia.** El intento 2 tiene el distrito 50802 con
nivel `bajo` y probabilidad `0,90`. Desde **D-21**, `probabilidad` es
P(nivel = alto): esa fila es imposible. El simulado sorteaba nivel y probabilidad
por separado, que era coherente mientras el contrato no decia que magnitud era
`probabilidad`, y dejo de serlo el 19 de agosto. **D-21 quedo a medias**: defini
el campo en el contrato y no arregle el unico productor de ese campo que existe.
Es mi omision.

**Accion tomada.** Solicitud de cambio **SC-03**, contratos a **v1.3.1**:

- `obtener_riesgo` siembra un generador propio con `(codigo, fecha, tipo_evento)`.
  La misma consulta devuelve siempre lo mismo, en este proceso y en el siguiente.
- El nivel se **deriva** de la probabilidad en vez de sortearse aparte, de forma
  monotona: una probabilidad mayor nunca da un nivel menor.
- Tres comprobaciones nuevas en `contratos/verificar.py`, que fallaban antes del
  arreglo: dos llamadas iguales al mismo repositorio, dos instancias distintas, y
  960 filas contrastadas contra la regla de D-21.

**Aprendizaje.** Un doble se sustituye por el original **por sus propiedades, no
por su forma**. `contratos.verificar` comprobaba con `isinstance` que el simulado
cumpliera el protocolo, que es comprobar la forma. La propiedad que hace util a un
repositorio de solo lectura —preguntar dos veces lo mismo y recibir lo mismo— no
la miraba nada.

La regla que se agrega:

> De un simulado hay que comprobar tambien lo que promete su docstring. Si dice
> "deterministas", hay una comprobacion que lo llama dos veces y compara.

---
### Actualizacion del 2026-08-20: el arreglo estaba incompleto

**Lo encontro Cesar al revisar SC-03**, comprobando lo que yo no comprobe: si el
mismo defecto estaba en otro metodo. Estaba en tres.

`obtener_mediciones`, `contar_focos` y `obtener_indices` sorteaban tambien contra
el generador compartido. Y en mediciones el defecto tenia una forma peor:

    Rango A: 1 al 5 de agosto.   Rango B: 3 al 7 de agosto.

      2026-08-03:  A = 31.2   B = 30.6   DISTINTO
      2026-08-04:  A = 27.2   B = 27.4   DISTINTO
      2026-08-05:  A = 31.1   B = 27.8   DISTINTO

**Un mismo dia con dos temperaturas segun por donde se lo pidiera.** Le habria
pegado a H2.5, que trabaja sobre ventanas moviles, y el sintoma habria apuntado al
algoritmo de Luna en vez de al simulado.

Cesar encontro ademas un segundo defecto dentro del primero: los huecos salian de
`i % 20 == 7`, la posicion dentro del rango pedido, no la fecha. Un mismo dia era
hueco o no segun donde cayera en la consulta.

Se corrige en **SC-04**, propuesta como **v1.3.2**.

### Y hubo un quinto sitio, en otra clase del mismo archivo

Al revisar SC-04, Cesar encontro que el arreglo tampoco estaba completo. Yo habia
buscado **todos los metodos de `RepositorioSimulado`**, y el archivo tiene otra
clase: **`ExtractorFocosSimulado` sorteaba tambien contra un generador con
estado.**

    dos llamadas identicas al MISMO extractor coinciden : False
      llamada 1, primer foco : 2024-03-28  10.4213  confianza 75
      llamada 2, primer foco : 2024-03-26  10.4017  confianza 91

    otra INSTANCIA coincide con la primera llamada : True

La ultima linea es la firma exacta de I-08: una instancia nueva si coincide,
porque el generador arranca de cero. **Le pega a H1.2**, que implementa
`ExtractorFocosCalor` de verdad contra ese doble.

La misma revision encontro tres cosas mas: `_es_hueco` recibia `codigo_distrito` y
no lo miraba —los ocho distritos tenian hueco los mismos dias, y no se podia
escribir la prueba de un distrito con dato y otro sin el—, `contar_focos` no podia
devolver mas de un foco por dia, y el generador compartido quedaba sin uso en
`__init__`, invitando a que alguien volviera a sortear contra el.

Todo integrado en contratos **v1.3.3**. El verificador pasa de 40 a **44**
comprobaciones.

**Y una correccion al razonamiento de esta incidencia.** Decia que el defecto
importaba porque *"un GET es idempotente por definicion"*. Es falso: la
idempotencia de HTTP restringe el efecto sobre el servidor, no la representacion
devuelta. Un `GET /hora-actual` es idempotente y responde distinto cada vez. El
simulado viejo no violaba ninguna regla de HTTP.

El argumento correcto es el de **sustituibilidad**, que ya estaba y es mas fuerte:
el repositorio de H6.2 sera determinista porque lee filas guardadas, y eso es
propiedad del repositorio, no del protocolo. Corregido en el docstring, en SC-03,
en los criterios de H6.6 y en el verificador.

**Aprendizaje, segunda parte.** El primero fue que de un simulado hay que comprobar
lo que promete su docstring. El segundo es mio y sale de esta correccion:

> **Arreglar el caso senalado no es arreglar el defecto.** Cuando aparece un
> patron —un generador con estado usado donde hacia falta reproducibilidad— hay
> que buscar todas sus apariciones antes de declarar el problema resuelto. SC-03
> corrigio un sintoma y dio por cerrado el problema.

**Y el aprendizaje se corrige a si mismo.** Escrito eso, volvi a hacerlo: busque
en una clase y declare el archivo revisado. La version que queda:

> **No alcanza con «buscar todas las apariciones del patron»: hay que decir
> DONDE se busco.** Un alcance que no se declara no se puede revisar, y quien lea
> el arreglo va a suponer que cubre lo que no cubre.


## I-09 · La mitad de los commits del Lead PM no quedaron atribuidos a su cuenta

**Fecha.** 2026-08-20

**Quien lo detecto.** Alejandro, al ver en el Pull Request de H6.6 un commit suyo
sin su foto de perfil.

**Que paso.** El repositorio tenia **dos identidades distintas para la misma
persona**:

| Nombre en Git | Correo | Commits | De donde salen |
|---|---|---|---|
| `humanoidcat` | alejo**.**rz93@gmail.com | 42 | `git commit` desde la maquina |
| `Alejandro` | alejo**rz.**93@icloud.com | 39 | Merges hechos desde la web de GitHub |

La cuenta de GitHub `HumanoidCat`, que es la dueña del repositorio, tiene
verificado **el de iCloud**. El de Gmail no le pertenece a esa cuenta.

Consecuencia: **42 de los 81 commits del Lead PM no estan vinculados a su
perfil.** GitHub los muestra con avatar generico y no los cuenta en el grafico de
contribuciones. Con la calificacion individual saliendo del historial, es una
perdida de trazabilidad, no un detalle cosmetico.

**Causa raiz.** La configuracion global de Git de la maquina quedo con el correo
de Gmail. Nadie contrasto esa configuracion contra la cuenta que es dueña del
repositorio, y el contraste es **un solo comando**:

    git log --format='%an <%ae>' | sort -u

Los dos correos se leen casi identicos —el punto cae en distinto lugar— y esa
semejanza es la que dejo pasar el error durante 42 commits.

**Accion tomada.** Identidad fijada **a nivel del repositorio**, que gana sobre la
global:

    git config --local user.name  "humanoidcat"
    git config --local user.email "alejorz.93@icloud.com"

Se elige el ambito local a proposito: arregla este repositorio sin depender de que
la configuracion global de la maquina este bien, y sobrevive a que alguien la
cambie.

**Los 42 commits anteriores se quedan como estan.** Reescribir el autor exige
reescribir los identificadores de todos los commits posteriores y forzar el
empuje, lo que romperia las copias de las otras tres personas en mitad del Sprint
2. El costo supera al beneficio. La alternativa sin reescritura seria agregar el
correo de Gmail como secundario verificado en la cuenta de GitHub, que atribuiria
los 42 de forma retroactiva; se descarta porque esa direccion no pertenece a la
cuenta y agregarla resolveria el sintoma ensuciando la identidad.

**Aprendizaje.** La identidad con la que se firma el trabajo es parte de la
trazabilidad del proyecto y nadie la estaba comprobando. Es el mismo patron de
I-04: un dato con forma valida y contenido equivocado, que ninguna validacion
automatica detecta porque la forma esta bien.

La regla que se agrega:

> Al clonar el repositorio, cada quien fija `user.name` y `user.email` **locales**
> y comprueba que su correo sea uno verificado en su cuenta de GitHub. Se verifica
> mirando que el commit propio salga con la foto de perfil en el Pull Request.

---

## I-10 · Un marcador de posicion del primer dia llego al sitio publico

**Fecha.** 2026-08-24

**Quien lo detecto.** Alejandro, abriendo el visor recien publicado.

**Que paso.** El sitio publicado mostraba el canton de Tilaran como **ocho
rectangulos identicos sobre una grilla de tres por tres**, ninguno en el lugar
del distrito que decia representar.

No eran ubicaciones aproximadas. Salian de esto, en `contratos/simulados/datos.py`:

    def _cuadro(i: int) -> dict:
        """Poligono ficticio, solo para que el visor tenga algo que dibujar."""
        lon, lat = -84.97 + (i % 3) * 0.09, 10.47 - (i // 3) * 0.07

`i % 3` e `i // 3` son **fila y columna de una grilla**. La funcion nunca intento
representar geografia, y su propio docstring lo decia.

**Causa raiz.** No fue un descuido de nadie al revisar. Fueron tres piezas
correctas por separado que nadie cruzo:

| Cuando | Que | Estaba bien? |
|---|---|---|
| 3 ago | `_cuadro()` genera cuadros para que el visor tenga que dibujar | **Si**, y lo declaraba |
| 12 ago | El exportador vuelca el simulado a archivos estaticos | **Si**, exporto lo que habia |
| 13 ago | **H1.3 carga las geometrias oficiales del SNIT en PostGIS** | **Si** |
| 20 ago | El visor publicado sirve el respaldo estatico | **Si** |

**H1.3 cerro y nada aviso de que el simulado habia quedado obsoleto.** El
marcador de posicion no tenia fecha de vencimiento ni dueno despues de cumplida
la historia que iba a reemplazarlo.

Y el dato **se declaraba falso a si mismo**, en el archivo que se publicaba:

    "geometria_simulada": true

Nadie lo leia. `verificar_h115.py` tenia veinte comprobaciones sobre el
artefacto construido y ninguna miraba **el contenido** del GeoJSON: comprobaba
que el archivo existiera y que la ruta resolviera, no que dijera la verdad.

**Accion tomada.**

1. `docs/herramientas/generar_geometrias_simulado.py`, que trae los contornos del
   SNIT reusando el descargador de H1.3 y los simplifica para mapa web. Mide
   varias tolerancias e imprime la tabla: la eleccion se toma mirando, no de
   memoria. **No reusa la tolerancia de `poligonos_simplificados.sql`**, que esta
   afinada para caber en una URL de ClimateSERV y perderia detalle sin motivo.
2. El simulado lee esa geometria de un archivo congelado. Si falta, falla con el
   comando exacto para regenerarla: **no hay camino de vuelta al cuadrado**.
3. **Dos comprobaciones nuevas en `verificar_h115.py`**, sobre el `dist` que se
   publica:
   - ningun distrito con `geometria_simulada` en `true`
   - ningun poligono de menos de diez vertices

   Son independientes a proposito. La primera atrapa el caso honesto; la segunda
   atrapa que alguien ponga la bandera en `false` sin arreglar la geometria.
   Probadas reintroduciendo los dos defectos por separado: las dos salen en rojo
   con codigo 1.

**Dos defectos mas, que aparecieron al revisar el `dist` construido en vez de
confiar en los verificadores.** Los 22 criterios salian en verde con los dos
puestos, y conviene que quede escrito por que:

**a) La ficha del distrito seguia diciendo que la forma era falsa.** Texto
visible al hacer clic en un distrito, todavia en el bundle publicado:

> *"La forma de este distrito es un marcador de posicion, no su limite real. Se
> reemplaza en la historia H1.3 con la capa del SNIT."*

Se habia corregido la banda de arriba y no se busco el resto. **Un `grep` del
identificador sobre el artefacto construido lo encontraba en un segundo**, y no
se hizo hasta despues.

**b) Las areas declaradas no eran las de la geometria.** Ocho constantes escritas
a mano en `_DISTRITOS`, contra el poligono oficial medido en EPSG:8908, que es
como lo mide `cargar_distritos.py`:

    Tronadora          declara  30,2   mide  140,0    +363 %
    Tilaran                     60,0         144,8    +141 %
    Arenal                     156,5          72,6     -54 %
    Quebrada Grande             88,4          34,4     -61 %
    -----------------------------------------------------------
    canton                     638,3         669,2      +5 %

**El total casi coincide y los individuales estan revueltos**, lo que sugiere que
los numeros estaban asignados a los codigos equivocados. Y el panel del visor
muestra esa cifra **al lado de la forma**: con la geometria falsa nadie lo
notaba; con la real, un distrito dibujado enorme decia 30,2 km2.

Se corrige igual que la geometria: **el area se calcula, no se escribe.** La
computa el generador sobre el poligono sin simplificar —la simplificacion existe
para que el mapa pese menos, no para cambiar cuanto mide un distrito— y el
simulado la lee del mismo archivo.

**Aprendizaje.** Es la cuarta vez que este proyecto encuentra lo mismo, y ya
conviene enunciarlo como regla:

> **Un dato de relleno necesita fecha de vencimiento y una maquina que la
> cobre.** Si se pone algo provisional porque todavia no existe lo real, la
> historia que va a traer lo real no alcanza como plan: hay que dejar escrito
> quien lo reemplaza y una comprobacion que falle mientras siga ahi.

Y el patron concreto, que ya se vio en **I-04** y en **I-07**: un dato con forma
valida y contenido equivocado pasa todas las validaciones de forma. Aca ademas
**venia con su propia confesion escrita** y aun asi paso, porque la confesion
estaba en un campo que nadie leia.

Lo mas incomodo: el defecto no lo encontro ningun control. Lo encontro **una
persona mirando la pantalla**, cuatro dias despues de publicar y a cuatro dias
del Primer Avance.

Y los otros dos —la frase que quedaba en la ficha, y las areas revueltas— no los
encontro ningun control **ni siquiera despues**: salieron de revisar el artefacto
construido antes de commitear, con los 22 criterios ya en verde. De ahi la
segunda regla:

> **Un verificador en verde dice que no fallo lo que se le pidio comprobar, no
> que el resultado este bien.** Antes de publicar algo que va a mirar gente de
> afuera, alguien abre el artefacto y lo mira.

**Impacto.** Ninguna hora de trabajo perdida y ninguna persona bloqueada: el
arreglo son dos programas y una tabla de tolerancias. El costo real era otro,
y no llego a ocurrir: **el sitio se le iba a mostrar al Comite Municipal de
Emergencias de Tilaran con el canton dibujado como un tablero de ajedrez.**


---

## I-11 · Diez anios sin satelite etiquetados como «no hubo incendio»

**Fecha.** 2026-08-26

**Quien lo detecto.** Alejandro, escribiendo los criterios de aceptacion de H3.2
—**no** revisando H3.0, que ya estaba en revision con sus 31 comprobaciones en
verde.

**Que paso.** El etiquetado de H3.0 producia 99 296 filas desde 1991-01-01. La
etiqueta de incendio salia de contar focos de calor en la ventana `(t, t+7]`:

    return NivelRiesgo.ALTO if focos_en_ventana >= 1 else NivelRiesgo.BAJO

**El archivo de focos empieza en 2001.** MODIS Terra/Aqua coleccion 6.1 no tiene
observacion operacional antes de finales del 2000, y los 242 focos que R16 midio
para este canton van de 2001 a 2024.

Asi que para toda fecha anterior a 2001 la cuenta daba cero —correctamente, no
hay focos cargados— y la funcion devolvia **BAJO**. No «no se sabe»: **«no hubo
incendio»**, afirmado sobre una decada que ningun satelite miro.

| | |
|---|---|
| Filas de 1991-01-01 a 2000-12-31 | 3 653 fechas x 8 distritos = **29 224** |
| Del conjunto etiquetado | **29,4 %** |
| ALTO sobre las 99 296 filas | 0,87 % |
| ALTO sobre las 70 072 **observadas** | **1,23 %** |

**Causa raiz.** La misma forma que I-04 y que I-10: cada pieza correcta por
separado, y ninguna maquina cruzandolas.

| Pieza | Estaba bien? |
|---|---|
| La serie climatica de CHIRPS arranca en 1991 | **Si**, D-15 |
| El cargador de focos trae lo que FIRMS publica, que empieza en 2001 | **Si** |
| `nivel_incendio` devuelve BAJO con cero focos | **Si**, D-25 |
| Etiquetar el rango completo de la precipitacion | **No**, y nadie lo comprobaba |

Lo agudo es que **H3.0 tenia el criterio escrito**. CA-8 dice, textualmente, que
la ausencia de dato no se convierte en una clase, y su comprobacion la aplicaba
a la precipitacion y al SPI —donde si funcionaba, 664 filas de sequia salen
`None`— **y no al incendio**. El criterio estaba, la maquina estaba, y el caso
que faltaba era justo el unico de los tres eventos que depende de una fuente con
otra fecha de inicio.

**Como se detecto.** Contando episodios de incendio por pliegue para el criterio
CA-4 de H3.2. La cuenta obligaba a preguntar de que anios sale cada episodio, y
la respuesta fue que del primer bloque de la ventana expansiva no sale ninguno,
porque en 1991-1996 no hay satelite.

**Que se cambio.**

1. `COBERTURA_FOCOS = (2001-01-01, 2024-12-31)` en `backend/modelado/etiquetado.py`,
   declarada como constante con su motivo. **No se infiere del dato cargado**:
   inferirla del minimo de las detecciones diria que un distrito sin focos nunca
   fue observado, que es la misma confusion en otra direccion.
2. `nivel_incendio` recibe `ventana_observada` y devuelve **None** si la ventana
   `(t, t+7]` no cae entera dentro de la cobertura.
3. Seis comprobaciones nuevas en `verificar_h30.py`, criterio **CA-8b**,
   incluidos los dos bordes: la ventana que asoma un dia por fuera no se
   etiqueta, y la primera que cae entera adentro si.
4. `generar_etiquetas.py` informa el porcentaje de la clase minoritaria **sobre
   las filas observadas**, ademas de sobre el total.

**Impacto.** Ninguna hora perdida, porque se detecto con el Pull Request todavia
abierto. El costo evitado si es grande: un modelo entrenado con esas filas habria
aprendido que **la decada de los noventa era segura**, sobre un evento cuya clase
minoritaria es del 1 %. Y como esas filas son el 29 % del conjunto, cualquier
metrica de exactitud habria salido mejor de lo que corresponde sin que ningun
verificador se quejara.

**La regla que deja.** Cuando dos fuentes con **fechas de inicio distintas** se
juntan en una misma tabla, la mas corta manda sobre su columna, y eso se declara
como constante y se comprueba. H3.0 ya lo habia hecho por el lado derecho de la
serie —`ULTIMO_ANIO = 2024`, porque los focos terminan antes que CHIRPS— y no
por el izquierdo. **Una cota puesta en un extremo invita a suponer que el otro no
hace falta.**

---

## I-12 · Un guardarrail correcto conectado a la condicion equivocada dejo el CI en rojo por diseno

**Fecha.** 2026-08-26

**Quien lo detecto.** Alejandro, revisando por que varios Pull Requests no
pasaban.

**Que paso.** Desde el 25 de agosto, **toda rama de trabajo salia en rojo en el
CI**, hiciera lo que hiciera. El PR #171 no podia pasar nunca.

Son dos piezas, cada una correcta, mal conectadas:

| Pieza | Que dice | Estaba bien? |
|---|---|---|
| `ci.yml` | `if: github.event_name == 'push'` | **No.** Incluye cada push a cada rama |
| `verificar_issues.py` | se planta con codigo 1 si la rama no es `dev` ni `main` | **Si**, y por buenas razones |

El comentario que acompana a esa condicion **decia lo correcto desde el primer
dia**:

> En `push` a dev y main el tablero se sigue vigilando de forma continua, el
> aviso llega igual, y llega a quien puede corregirlo.

La condicion nunca nombro las dos ramas. Decia «en cualquier push».

**Por que no se noto antes.** Mientras el verificador solo advertia, correrlo
desde una rama de trabajo daba un **verde falso** —una historia ya cerrada en
`dev` figura sin marcar en la rama vieja, asi que no reclamaba su issue abierta—
y nadie miraba un trabajo que pasaba.

El 25 de agosto se le puso el guardarrail de rama, precisamente para que ese
verde falso dejara de existir. **Desde ese momento el mismo defecto cambio de
sintoma**: de verde silencioso a rojo garantizado.

**Causa raiz.** El control estaba bien y la condicion que lo dispara estaba mal.
Es una variante de I-06 —el CI corria `pytest` de una forma que ninguna persona
usaba— pero al reves: aca el programa hace exactamente lo que debe y **se lo
invoca donde no corresponde**.

**Que se cambio.**

1. La condicion nombra las dos ramas, que es lo que su propio comentario
   declaraba:

       if: >-
         github.event_name == 'push'
         && (github.ref == 'refs/heads/dev' || github.ref == 'refs/heads/main')

2. Aprovechando el mismo cambio, **`publicar-visor` deja de depender de
   `gestion`**. Publicar el visor no puede depender de si una issue esta abierta
   en un tablero que vive fuera del repositorio. Ese acople ya habia costado una
   hora el 24 de agosto, y fallaba de la peor manera: el trabajo aparecia
   **omitido**, no rojo.

**Impacto.** Dos Pull Requests bloqueados y un rato largo de buscar la causa en
el lugar equivocado —se reviso el tablero, se cerraron issues, se creo una
duplicada que hubo que retirar— antes de mirar la condicion del CI.

**La regla que deja.** **Cuando un control cambia de «advierte» a «se planta»,
hay que revisar de nuevo donde se lo invoca.** Un guardarrail nuevo no solo
cambia lo que el programa hace: cambia el costo de cada lugar desde el que se lo
llama. Y en este repositorio hay un sitio donde eso quedo escrito y no se
releyo: **el comentario del propio paso ya decia la condicion correcta.**

---

## I-13 · El cierre de issues en `dev` exigia un ritual manual que ningun orden podia satisfacer

**Fecha.** 2026-08-26

**Quien lo detecto.** Alejandro, despues de que el mismo rojo apareciera por
tercera vez.

**Que paso.** **Cada fusion de una historia a `dev` dejaba el CI en rojo.** No
por el codigo: por el tablero.

`Closes #N` esta inerte en `dev`, porque GitHub solo cierra al fusionar a la
**rama por omision**, que aca es `main`. Asi que despues de cada merge quedaba un
`gh issue close` a mano, y hasta que alguien se acordara el trabajo `gestion`
fallaba.

**Y no habia orden que lo evitara.** Esa es la parte que convierte esto de
molestia en defecto:

| Cuando se cerraba la issue | Que discrepancia disparaba |
|---|---|
| **Antes** de fusionar | «issue cerrada y la historia no esta marcada [x]» |
| **Despues** de fusionar | «historia marcada [x] y su issue sigue abierta» |

Siempre existia una ventana en rojo. Paso con **#165**, con **#170**, y le iba a
pasar a cada persona del equipo esta semana, cuando cierren sus historias del
Sprint 2.

**Causa raiz.** El proceso escrito le pedia a una persona ejecutar una decision
que **ya estaba tomada**. `docs/15-cerrar-una-historia.md` dice, sin ambiguedad,
que `docs/tareas/` es la fuente de verdad y que el tablero se corrige contra el.
Con eso decidido, cerrar la issue de una historia marcada `[x]` no decide nada:
es la aplicacion mecanica de una regla.

Y el paso 5b del documento **describia correctamente el problema** —incluso
explicaba por que `Closes #N` no dispara en `dev`— sin notar que la solucion que
proponia era imposible de aplicar sin pasar por rojo.

**Que se cambio.**

1. `verificar_issues.py --corregir`: cierra por `gh` las issues de historias
   marcadas `[x]`, con el motivo escrito y la razon del cierre automatico.
2. El CI usa `--corregir` **solo en `dev`**. En `main` sigue reclamando, porque
   ahi `Closes #N` funciona solo y una issue abierta significa que el Pull
   Request no llevaba el enlace: eso si merece que una persona lo mire.
3. El trabajo `gestion` pasa a `issues: write`.
4. El paso 5b del proceso se reescribio: ya no le pide nada a nadie.

**Solo esa discrepancia se corrige sola.** Las otras tres siguen fallando y
esperando a una persona, porque en las tres el arreglo admite duda:

  * una issue cerrada sin historia marcada haria **mentir a la fuente de verdad**
    si se corrigiera en automatico;
  * una historia sin issue necesita que alguien le redacte el cuerpo;
  * dos issues para la misma historia necesitan que alguien elija cual sobra.

**Impacto.** Tres runs en rojo, y peor: un rato largo buscando la causa en el
tablero —se cerraron issues, se creo una duplicada que hubo que retirar— cuando
el defecto estaba en el proceso.

**Y un efecto lateral que hay que saber leer: estos runs no se pueden re-ejecutar.**

Un *Re-run* de GitHub vuelve a correr el CI **sobre el commit original**, no sobre
`dev` de hoy. Y este verificador compara dos cosas de distinta naturaleza:

    el arbol    congelado en ese commit
    el tablero  vivo, el de este momento

Asi que un run viejo **queda en rojo para siempre**, y la brecha crece con cada
historia que se cierra:

| Commit | historias `[x]` en ese arbol | le faltan respecto a hoy |
|---|---|---|
| `6c21221` merge #163 | 25 | 2 |
| `ee9b31c` merge #165 | 26 | 1 |
| `817ed59` merge #166 | 26 | 1 |
| `dev` hoy | 27 | 0 |

Corrido el verificador de hoy contra el arbol de `817ed59` sale, correctamente:

    la issue #46 de H3.0 esta cerrada y la historia no esta marcada [x]

Claro: el 25 de agosto H3.0 no existia. **Un arbol viejo no puede coincidir con un
tablero nuevo.**

**Solo tiene sentido mirar el ultimo run de `dev` y el ultimo de `main`.** Los
anteriores son fotos de un instante que ya paso. Los otros seis verificadores si
son re-ejecutables, porque comparan archivos contra archivos **dentro del mismo
commit**; este es el unico que lee estado externo mutable, y esa es la diferencia.

Se anota porque el historial de Actions se ve lleno de rojo y **no lo esta**: el
2026-08-26 se perdio un rato dandole Re-run a cuatro runs que no podian cambiar.

**La regla que deja.** **Un control que exige un ritual manual despues de cada
merge no se cumple: se desactiva mentalmente.** Y un control que la gente aprende
a ignorar es peor que no tenerlo, porque el dia que avise de algo real nadie va a
mirar. Si una regla ya esta decidida y su aplicacion es mecanica, **la ejecuta la
maquina**; lo que se le deja a una persona es lo que requiere criterio.

---

## I-14 · Una retroalimentacion de tres frases se convirtio en dos cambios que nadie pidio

**Fecha.** 2026-08-27 (los cambios: 24 y 26 de agosto)

**Quien lo detecto.** Alejandro, al ver el visor publicado despues del merge a
`main` y no reconocerlo.

**Que paso.** El 24 de agosto el profesor miro el sitio publicado y dijo, textual:

> *"en UI esta muy quedado y hay que mejorarlo"*

y sobre eso, tres observaciones concretas: que el canton se veia chico, que el
borde del distrito seleccionado parecia un defecto de dibujo, y que la capa de
calor se pintaba sobre un rectangulo, se salia del canton y dejaba distritos sin
marcar. Mando ademas una **captura** del visor.

Tres dias despues el visor tenia dos cambios que **no estaban en esa lista**:

1. **El mapa quedo encerrado en una columna angosta** con la forma del canton
   -relacion 0,83- y dos bandas vacias a los lados. Se perdio el contexto
   regional: Canas, Liberia, el lago Arenal.
2. **La capa de calor no existe.** Se retiro entera por **D-28**: 515 lineas,
   tres modulos y el entregable de H5.4.

Ninguna de las dos cosas se pidio. La primera salio de leer la captura como si
fuera una especificacion; la segunda, de convertir un defecto de recorte en una
objecion a interpolar.

**Causa raiz.** Las dos tienen la misma forma, y no es descuido de nadie en
particular: **un dato observado se elevo a intencion, y despues se razono con
rigor sobre esa intencion inventada.**

| Lo que habia | En que se convirtio | Que produjo |
|---|---|---|
| una captura recortada del visor | "el visor debe mostrar solo el canton" | el encuadre de H5.8 |
| "se sale del canton y hay distritos sin marcar" | "interpolar afirma lo que el dato no dice" | D-28 |

Lo que hace visible el defecto es que **la costura quedo escrita**. El documento
de evidencia dice, sobre las dos observaciones del mapa de calor, *"ahi hay una
segunda cuestion, distinta de la primera"*. D-28 lo repite -*"dos problemas de
distinto peso"*- y a renglon seguido los trata como uno para retirar la capa. La
separacion estaba anotada y aun asi no se respeto.

Hay un agravante que conviene nombrar sin rodeos, porque cambia como hay que
trabajar de aqui en adelante: **el equipo redacta las especificaciones con ayuda
de IA, y una premisa mal puesta no se discute, se implementa.** No hay friccion.
Una persona a la que le piden retirar un entregable ajeno pregunta por que; una
herramienta que recibe el argumento ya construido lo ejecuta bien, rapido y
completo. La calidad de la ejecucion fue la que oculto el problema: 166 lineas de
ADR, tres capturas de evidencia y un merge limpio, todo sobre un hecho falso.

**Accion tomada.**

1. **D-30 revierte D-28.** La capa vuelve, con el defecto de recorte arreglado:
   el encuadre sale de los poligonos y el lienzo se recorta contra su union.
   D-28 se conserva entera, con un aviso arriba: una bitacora que se edita para
   quedar bien deja de servir.
2. **El encuadre vuelve al mapa de ancho completo.** De H5.8 se conserva la marca
   de seleccion accesible y el `zoomSnap`, que no dependian de la lectura errada.
3. **`frontend/herramientas/verificar_recorte_calor.mjs`**, en el CI. Mide sobre
   las geometrias reales que no se pinta nada fuera del canton y que no queda
   territorio sin pintar. El defecto original **habria salido en rojo**.
4. **Se le pidio permiso a Avril por escrito** antes de tocar `frontend/`, con la
   explicacion completa. La carpeta es suya por **D-16**.

**Aprendizaje.** Tres reglas, y la tercera es la que de verdad importa.

**Uno. Una captura es una observacion, no una especificacion.** Muestra un
sintoma. Lo que hay que hacer con ella es preguntar, no deducir.

**Dos. Un defecto de implementacion no habilita una decision de alcance.** Si al
arreglar algo aparece un argumento para retirarlo, ese argumento es una decision
separada, va a su propio registro y se discute con quien escribio el codigo. No
viaja de polizon en el arreglo.

**Tres, y es la que cambia el proceso. Cuando una decision se apoya en lo que
dijo alguien de afuera, la cita textual va en el registro, no la interpretacion.**
D-28 parafraseaba al profesor; si hubiera transcrito sus palabras, la
contradiccion habria sido visible al releer el propio documento antes de
aprobarlo.

**Y lo que se sigue de trabajar con IA:** **la responsabilidad se corre hacia
arriba, a las premisas.** El razonamiento se puede delegar; el hecho del que
parte, no. Una premisa equivocada ya no produce un trabajo mediocre que se nota:
produce un trabajo impecable en la direccion equivocada, y eso es mas dificil de
detectar, no menos.

**Impacto.** Cuatro dias con el visor publicado sin una capa que funcionaba y con
un encuadre que nadie pidio, justo en la semana del Primer Avance. 515 lineas
retiradas y restituidas. El entregable de H5.4 fuera de pantalla durante ese
tiempo. Trabajo de Avril hecho dos veces por un pedido mal formulado: la primera
implementacion no tenia ningun defecto.

---

## I-15 · El zip de la entrega se armo con los PDF viejos y nada lo advirtio

**Fecha.** 2026-08-30

**Quien lo detecto.** Alejandro, al pegar la salida completa de los cinco
comandos de reconstruccion en vez de solo el ultimo.

**Que paso.** Despues de cambiar la escala del SPI por **D-32**, se corrio la
secuencia que reconstruye los entregables:

    generar_figuras.py              OK, tres figuras nuevas
    contrastar_catalogo.py          OK
    construir_entregable.py --ieee  FALLO: falta XeLaTeX
    construir_entregable.py         FALLO: falta pandoc, con traza
    armar_entrega.py                **armo el zip igual**

El paquete salio con nombre correcto, fecha de hoy y 1,9 MB. Y con **los dos
documentos anteriores al cambio de escala**: los que dicen que la sequia da 0 de
7, que el SPI-3 es la escala del proyecto y que la ventana no final es del 23 %
al 57 %.

**Causa raiz.** `armar_entrega.py` comprobaba que cada pieza **existiera**. No
comprobaba que estuviera **al dia**. Y su propio encabezado declaraba, desde que
se escribio, que existia para evitar «un zip incompleto que parece correcto»: la
intencion estaba bien y la comprobacion cubria la mitad del problema.

Hay un segundo factor, de forma: en PowerShell, pegar cinco comandos seguidos
**no detiene la secuencia cuando uno falla**. La traza de pandoc quedo sepultada
entre la salida del comando anterior y la del siguiente, que informaba exito.

**Por que es peor que un zip incompleto.** Un paquete al que le falta un archivo
se nota al abrirlo. Uno que trae el archivo equivocado, con el nombre correcto y
fecha reciente, **no se nota**: hay que leer el contenido y saber que buscar.

Es I-06 -un paso que se salta en silencio se ve igual que uno que se cumplio-
llegando hasta el artefacto que se entrega, que es el ultimo lugar donde deberia
llegar y el unico donde nadie lo revisa despues.

**Que se cambio.** `armar_entrega.py` compara ahora la fecha de cada pieza contra
la de su fuente Markdown **y contra la de todas las figuras**, y se niega a armar
el zip si alguna quedo atras. Con la ruta del archivo que la dejo obsoleta, que
es lo que convierte el aviso en instruccion.

Se compara por fecha y no por suma porque el PDF no contiene al Markdown: no hay
suma que cruzar. Es un criterio mas debil, y **se prefiere errar hacia la
molestia**: un falso positivo cuesta reconstruir; un falso negativo cuesta
entregar el documento equivocado.

Queda una salida, `--aunque-esten-viejos`, y **el zip lo declara adentro**. Una
bandera que evita un control sin dejar rastro en el artefacto es peor que no
tener el control: da permiso y borra la evidencia de haberlo usado.

**Lo que NO se hizo, y conviene decirlo.** No se encadenaron los comandos con
`&&` ni se escribio un guion que los envuelva. Eso arregla el sintoma en una
maquina y no en la de al lado; el control vive en la herramienta, que es donde
sirve corra quien corra.

**Impacto.** Ninguno hacia afuera: el zip no se entrego. El costo real es la
confianza que el paquete tenia sin merecerla desde que la herramienta existe,
porque **este defecto no era nuevo, solo no se habia disparado antes**: hasta hoy
nunca habia fallado la construccion de los PDF con figuras recien regeneradas al
lado.

---

## I-16 · El documento decia citar 36 referencias y citaba 12, con el control en verde

**Fecha.** 2026-08-30

**Quien lo detecto.** Alejandro, al auditar cuales de las fichas nuevas de la
revision bibliografica habian entrado de verdad al cuerpo del documento. El
control no lo podia detectar: la cifra que comprobaba era cierta.

**Que paso.** El bloque de Referencias del documento IEEE decia:

> «El texto cita 36 referencias, de las cuales 28 estan verificadas...»

El cuerpo del documento citaba **12**. Las otras 24 estaban en la bibliografia y
sostenian el documento de investigacion, las fichas y las bitacoras, pero **este
texto no las citaba**.

**Causa raiz.** La afirmacion `referencias citadas` de `verificar_documentacion.py`
nunca conto citas. Cuenta los identificadores distintos de
`docs/investigacion/referencias.md`, o sea **el tamano de la bibliografia**. El
nombre decia una cosa, la funcion hacia otra, y el documento redacto la frase
creyendo el nombre.

El control comparaba **36 contra 36** y aprobaba. La cifra era correcta; la
oracion que la contenia, falsa.

**Por que este es el caso incomodo.** I-04, I-08 y I-15 son controles que no
miraban. Este miraba, y aprobo. Un numero verificado dentro de una afirmacion que
nadie verifico es peor que un numero sin control: el control le presta autoridad
a la frase entera cuando solo respalda una palabra de ella.

Y es exactamente lo que este mismo documento denuncia en su seccion de
conclusiones —«un dato con forma valida y contenido falso, que ninguna validacion
detecta porque nadie escribio la validacion»—. Estaba escrito arriba del defecto.

**Que se cambio.**

1. El documento dice ahora **«La bibliografia reune 36 referencias»** y, aparte,
   **«Este documento cita 12 de forma directa»**. Son dos hechos distintos y se
   afirman por separado.
2. Se agrego `referencias_citadas_en_el_cuerpo()`, que cuenta los `[N]` del
   documento IEEE cortando en `## Referencias`, con su propio control. Son 21
   controles, no 20.
3. La afirmacion vieja conservo su funcion y su nombre en el codigo lleva ahora
   la advertencia de que **cuenta bibliografia, no citas**.

**Lo que no se hizo.** No se forzaron citas de las 24 restantes para que el
numero subiera. Citar una referencia que el texto no usa es peor que no citarla:
convierte la bibliografia en decoracion. Cinco de las 36 -`[11]`, `[12]`, `[20]`,
`[21]` y `[35]`- no se citan en ningun documento, y eso queda declarado en vez de
disimulado; `[35]` ademas sigue sin autores transcritos y por eso no es citable.

**Impacto.** El documento no se habia entregado con esa frase a un evaluador
externo. El costo es de credibilidad interna: **la cifra mas visible del bloque
de Referencias era la unica del documento que afirmaba algo que sus propias
herramientas no comprobaban**, y llevaba semanas ahi.

---

## I-17 · El CI corre 152 de las 198 pruebas que hay en el repositorio

**Fecha.** 2026-08-30

**Quien lo detecto.** Alejandro, al medir el alcance real de H10.2 antes de
contestar las tres consultas de Luna sobre esa historia.

**Que paso.** El trabajo de pruebas del CI invoca:

    python -m pytest backend/tests -v --cov=backend --cov-report=term-missing

Dos archivos de prueba **no viven en `backend/tests`**:

    backend/api/test_repositorio_postgres.py    438 lineas
    backend/etl/test_imputacion.py              255 lineas

Son **46 pruebas, todas verdes**, que el CI nunca ha ejecutado.

| | Pruebas | Cobertura |
|---|---|---|
| Lo que corre el CI | 152 | 26 % |
| Lo que hay en el repositorio | **198** | **34 %** |

Con ellas, `repositorio_postgres.py` queda en **96 %** e `imputacion.py` en
**98 %**. Sin ellas, el reporte de cobertura del CI muestra esos dos modulos casi
vacios y las pruebas que los cubren, inexistentes.

**Causa raiz.** `pyproject.toml` declara `testpaths = ["backend"]`, que recogeria
los dos archivos. Pero `testpaths` **solo aplica cuando se invoca `pytest` sin
ruta**, y el CI pasa la ruta explicita. La ruta explicita gana y la configuracion
del proyecto queda sin efecto, sin aviso.

**Nadie rompio nada, y eso es lo que lo hace dificil de ver.** La linea del CI
existe desde el 2026-08-03, cuando `backend/tests` era el unico lugar donde
habia pruebas: era **cierta cuando se escribio**. Los dos archivos llegaron el
2026-08-27, en sus carpetas de modulo, que es donde `pytest` los recoge por
convencion y donde tiene sentido ponerlos. Ninguno de los dos cambios estaba mal.

Es una regla que fue correcta y dejo de serlo sin que ninguna de las dos partes
hiciera nada incorrecto. No hay un commit al que senalar.

**Por que el modo de fallo es el caro.** Quien corre `pytest` en su maquina
—sin ruta, tomando `testpaths`— ve las 198 pasar y concluye que estan cubiertas.
El CI reporta verde sobre 152. **Las dos observaciones son ciertas y solo una es
la que protege el repositorio.** Nadie tiene motivo para sospechar de la otra,
porque local y CI no se contradicen: dicen «verde» los dos.

Es la familia de I-06 —un control apagado que se ve igual que uno encendido— pero
con un agravante: aca el control **si corre**, y corre sobre menos de lo que
declara. `--cov=backend` mide el paquete entero ejercitando un tercio de el, asi
que el porcentaje no es una cobertura baja, **es una cobertura mal medida**.

Y es la misma forma que I-16, dos dias antes: una cifra correcta dentro de una
afirmacion que nadie comprobo.

**Que se cambio, y donde.** El arreglo es `backend/tests` → `backend` en
`.github/workflows/ci.yml`, y **no va en el cambio que registra esta
incidencia**: va en el de **H10.2**. La historia existe para encontrar
exactamente esto y el hallazgo se revisa mejor junto al resto de su trabajo.

Se redacta asi a proposito, sin «todavia» ni «pendiente», porque los dos cambios
son independientes y pueden entrar en cualquier orden. Una incidencia que
describe el estado del repositorio en el instante en que se escribio deja de ser
cierta apenas se fusiona algo; la que dice **donde vive el arreglo** sigue siendo
cierta despues.

`.github/workflows/ci.yml` es archivo de Alejandro; el permiso para esa linea
quedo dado por escrito en `gestion/respuesta-luna-h10.2.md`. No hace falta tocar
ningun archivo de Cesar: **las 46 pruebas estan bien escritas y no se toca
ninguna.**

La guarda que comprueba que `backend/tests` no este vacio se queda como esta:
comprueba otra cosa y sigue siendo cierta.

**Lo que NO se hizo.** No se quitaron los dos archivos de sus carpetas para
moverlos a `backend/tests`. Estan donde `pytest` los busca por convencion y donde
quedan al lado del codigo que prueban; el que tiene que ceder es el CI.

Tampoco se puso `--cov-fail-under`. Un umbral medido sobre la mitad de la suite
fija un piso falso, y con la otra mitad recien conectada todavia no se sabe cual
es el piso real.

**Impacto.** Ninguna prueba fallaba, asi que no se dejo pasar ningun defecto por
esta via **que se sepa**: nadie puede afirmar lo contrario, porque durante tres
dias esas 46 pruebas no se ejecutaron en ningun PR. El costo cierto es el
reporte de cobertura, que subestima en ocho puntos y llevaba tres dias siendo la
cifra con la que se decidia donde faltaban pruebas.

---

## I-18 · Un CHECK con CURRENT_DATE dejaba el respaldo en verde y la restauracion imposible

**Fecha.** 2026-09-01.

**Quien lo detecto.** Alejandro Rodriguez, escribiendo el criterio 9 del
verificador de H1.13.

**Que paso.** La migracion 006 declaraba, sobre `analitico.riesgo`:

    CHECK (fecha >= DATE '1981-01-01'
           AND fecha <= CURRENT_DATE + INTERVAL '31 days')

La restriccion se creo sin protestar y el verificador de H1.15 daba 15 de 15.
Pero `CURRENT_DATE` **no es inmutable**, y PostgreSQL reevalua el CHECK **en
cada insercion**, no solo cuando la fila entro por primera vez.

Comprobado contra PostgreSQL 16.2 el mismo dia:

    INSERT con fecha 2026-10-02 (hoy + 31)  -> ACEPTADA
    INSERT con fecha 2026-10-03 (hoy + 32)  -> RECHAZADA

Esa segunda fila era valida ayer.

**Causa raiz.** `pg_dump` emite fechas literales y **restaurar es reinsertar**.
Una fila estimada para dentro de 31 dias es valida el dia del volcado y deja de
serlo al dia siguiente. El respaldo se toma en verde y se descubre inservible
cuando hace falta, que es el unico momento en que a nadie le sirve descubrirlo.

El error de fondo no es la fecha: es haber puesto **una regla de operacion**
-«el horizonte del sistema son siete dias»- en el lugar donde viven las **reglas
de integridad**. Una regla de integridad tiene que ser cierta para siempre; esta
solo era cierta hoy.

**Donde cae.** Sobre **H1.10**, que es «estrategia de respaldo probada». Esa
prueba pasaria mientras se corra el mismo dia del volcado y empezaria a fallar
sola despues, sin que nadie tocara nada. Es la forma mas incomoda de **I-06**: un
control que hoy esta verde y **cambia de veredicto con el calendario**.

**Accion tomada.** La migracion `007_riesgo_correcciones.sql` quita el limite
superior y conserva el inferior:

    CHECK (fecha >= DATE '1981-01-01')

**No se fijo una fecha constante en su lugar.** Eso solo cambia el problema de
sitio: alguien tendria que acordarse de moverla y, el dia que se pase, la base
empieza a rechazar estimaciones legitimas.

El horizonte de siete dias pasa a hacerse cumplir **donde se escribe**, y desde
**H1.9** eso es literal: `analitico.registrar_riesgo` lo comprueba con un `RAISE`
propio de codigo `P0001` y registra el rechazo en `control.fallo`. La regla no
desaparecio: se movio al lugar donde puede cambiar sin romper un volcado.

**Aprendizaje.** **En un CHECK solo entran expresiones inmutables.** `now()`,
`CURRENT_DATE` y `CURRENT_TIMESTAMP` son correctos como `DEFAULT` -se evaluan una
vez y el valor queda congelado- y son un defecto como `CHECK` -se reevaluan
siempre-. La misma funcion, dos lugares, y en uno de ellos es una bomba de
tiempo.

PostgreSQL **no impide** crear el CHECK, asi que el compilador no ayuda: el
control tiene que ser explicito. Quedo escrito como criterio en **dos**
verificadores, el 9 de `verificar_h1_13.py` y el 14 de `verificar_h1_9.py`, que
leen `pg_get_constraintdef` y exigen que no aparezca ninguna de esas funciones.
Toda tabla nueva del esquema hereda la comprobacion.

**Impacto.** Ninguna fila perdida: la tabla estaba recien creada y vacia. El
costo real habria sido descubrirlo en H1.10 o, peor, en una restauracion de
verdad. Se detecto por escribir un verificador que muta filas en vez de leer el
DDL, que es la misma leccion de I-06 y de I-17.

---

## I-19 · Los esquemas no los crean las migraciones, y sin Docker ninguna aplica

**Fecha.** 2026-09-01.

**Quien lo detecto.** Cesar Ubau lo reporto durante la revision de H1.15.
Reproducido y confirmado por Alejandro Rodriguez al verificar H1.9.

**Que paso.** Aplicar las nueve migraciones de `basedatos/ddl/` sobre una base
vacia falla en **las nueve**:

    ERROR en 001_control_migracion.sql -> schema "control" does not exist
    ERROR en 002_geo_territorio.sql    -> schema "geo" does not exist
    ERROR en 003_seguridad_roles.sql   -> database "geoguardian" does not exist
    ...
    ERROR en 009_funciones_y_bitacora_fallos.sql -> schema "control" does not exist

**Causa raiz.** Los cuatro esquemas -`geo`, `crudo`, `analitico`, `control`- los
crea `infra/docker/init-db/01-extensiones.sql`, junto con las extensiones. Docker
ejecuta esa carpeta **una sola vez, cuando el volumen esta vacio**.

O sea que **el estado inicial de la base vive en dos sitios**: una parte en
`init-db`, que corre una vez y no esta versionada como migracion, y otra en
`ddl/`, que si. Las migraciones no son autosuficientes y **nada lo dice**.

En el flujo de todos los dias no se nota, porque `docker compose up` hace las dos
cosas en el orden correcto. Se nota al levantar PostgreSQL fuera de Docker, al
restaurar sobre una base limpia, o al querer verificar una migracion de forma
aislada -que es exactamente lo que hacia falta para H1.9-.

**Donde cae.** Sobre **H1.10**, «estrategia de respaldo probada». Una
restauracion que empiece por una base vacia y aplique las migraciones **no
funciona hoy**, y esa historia existe para demostrar que si.

Es la misma familia que **I-18**, y las dos apuntan al mismo lugar: el respaldo
esta en verde y nadie ha intentado restaurarlo todavia.

**Accion tomada.** Se registra y **no se arregla en H1.9**. La correccion
-mover la creacion de esquemas a una migracion `000`, o hacer que
`aplicar_migraciones.py` la garantice- cambia el arranque de la base para todo el
equipo y merece revisarse junto con la prueba de restauracion que la justifica.
**Va con H1.10.**

Para verificar H1.9 se replico `init-db` en el entorno de pruebas, y eso quedo
anotado en el documento de evidencia: es un andamio de verificacion, no una
solucion.

**Aprendizaje.** **Si el estado inicial vive en dos sitios, uno de los dos se va
a olvidar.** El principio que el proyecto viene repitiendo -una fuente, vistas
derivadas, y una maquina que comprueba que coinciden- aplica igual al arranque de
la base que a la matriz de trazabilidad o al backlog.

Y la forma de detectarlo fue la misma de siempre: **intentar hacerlo de verdad**,
sobre una base vacia, en vez de asumir que el camino feliz es el unico camino.

**Impacto.** Ninguna hora perdida en H1.9 mas alla de reproducirlo. El costo real
esta diferido a H1.10, que ahora arranca sabiendo lo que tiene que arreglar en
vez de descubrirlo.

---

## I-20 · El arreglo de I-18 solo toco una de las tres tablas, y el control tampoco miraba las otras

**Fecha.** 2026-09-01.

**Quien lo detecto.** Alejandro Rodriguez, al leer `crudo.medicion_diaria` para
particionarla en H1.11.

**Que paso.** La migracion **007** quito `CURRENT_DATE` del `CHECK` de
`analitico.riesgo` el mismo dia en que se registro **I-18**. Nadie reviso el resto
del esquema. Dos tablas seguian con el mismo defecto:

    crudo.medicion_diaria   CHECK (fecha >= '1981-01-01' AND fecha <= CURRENT_DATE)
    crudo.foco_calor        CHECK (fecha >= '2000-01-01' AND fecha <= CURRENT_DATE)

`crudo.medicion_diaria` es **la tabla que guarda todo el dato crudo del
proyecto**: 99 296 filas, las que alimentan el etiquetado, las senales y el
modelo.

**Causa raiz.** Dos, y la segunda es peor que la primera.

**La primera:** se arreglo el sintoma donde se vio, y no se busco el patron.
I-18 se descubrio escribiendo el verificador de H1.13, que mira `analitico.riesgo`,
asi que la busqueda se detuvo en esa tabla. Nadie corrio la consulta obvia
-«dame todos los CHECK del esquema que mencionen CURRENT_DATE»- que habria
devuelto las tres de una vez.

**La segunda:** los controles que se escribieron para que no se repitiera
**nacieron con menos alcance que el defecto**. El criterio 9 de
`verificar_h1_13.py` filtra por `conrelid = 'analitico.riesgo_auditoria'::regclass`
y el criterio 14 de `verificar_h1_9.py` por `control.fallo`. Los dos pasan en
verde con las dos tablas rotas al lado.

**Un control con menos alcance que el defecto da la misma tranquilidad y ninguna
proteccion.** Es peor que no tenerlo, porque cierra la busqueda.

**Donde hacia dano, y no era donde se pensaba.** En `analitico.riesgo` el CHECK
rompia la restauracion porque el limite era `CURRENT_DATE + 31 dias` y una fila
futura dejaba de ser valida al dia siguiente. En `crudo.medicion_diaria` el limite
es `<= CURRENT_DATE` y las fechas historicas nunca dejan de cumplirlo, asi que
**la restauracion no se rompe**. El dano es otro:

    CREATE TABLE m_2027 PARTITION OF m FOR VALUES FROM ('2027-01-01') ...
      -> creada, sin una sola advertencia
    INSERT INTO m VALUES ('50801', '2027-03-10', 1.0)
      -> ERROR: new row violates check constraint

**No se puede particionar hacia adelante.** La particion existe, se ve sana en el
catalogo y no acepta una sola fila. Comprobado contra PostgreSQL 16 antes de
escribir la migracion.

Conviene anotar que **el mismo defecto tuvo dos consecuencias distintas en dos
tablas distintas**. Buscar «el sintoma de I-18» en vez de «la construccion de
I-18» fue justamente lo que hizo que no se encontrara.

**Accion tomada.** La migracion `010_particionar_medicion.sql` quita el limite
superior de las dos tablas y conserva el inferior, que es constante y atrapa el
error real -una fecha de 1900 por un parseo malo-.

Y el control se ensancho. El **criterio 14 de `verificar_h1_11.py`** ya no filtra
por tabla: recorre `pg_constraint` en los cuatro esquemas y exige que **ninguna**
restriccion `CHECK` contenga `CURRENT_DATE`, `now()`, `CURRENT_TIMESTAMP` ni
`localtime`. Toda tabla nueva hereda la comprobacion sin que nadie tenga que
acordarse de agregarla.

**Aprendizaje.** **Cuando se arregla un defecto, el control que lo atrapa se
escribe sobre la clase, no sobre el caso.** La pregunta al cerrar una incidencia
no es «¿arregle esto?» sino «¿cuantos sitios mas tienen esta forma, y como me
entero del proximo?».

La consulta que lo habria encontrado el 2026-09-01 por la manana cabe en cinco
lineas y ahora es un criterio permanente. Escribirla el dia de I-18 habria costado
diez minutos; no escribirla costo que el dato crudo del proyecto quedara tres
migraciones con una restriccion que impedia crecer.

**Impacto.** Ninguna fila perdida y ninguna carga fallida: el limite `<=
CURRENT_DATE` no rechaza dato historico. El costo cierto fue el bloqueo de H1.11
-que no podia crear particiones utilizables- y el riesgo diferido de que la carga
del proximo anio fallara en produccion sin causa visible.

---

## I-21 · El arreglo de I-17 se revirtio dos dias despues, y el CI siguio en verde

**Fecha.** 2026-09-02.

**Quien lo detecto.** Alejandro Rodriguez, comparando `ci.yml` entre `dev` y
`main` al resolver los conflictos de la fusion semanal.

**Que paso.** El PR **#208** (H10.2, de Luna) arreglo I-17 el 30 de agosto:
cambio la ruta de `pytest backend/tests` a `pytest backend`, con lo que el CI
paso a ejecutar las 198 pruebas del repositorio en vez de 152.

El PR **#212** (H11.1, mio) la devolvio a `backend/tests` el 1 de septiembre.
Junto con la linea se borro el bloque de catorce lineas de comentario que
explicaba por que tenia que ser `backend`.

**Durante dos dias el CI volvio a correr 152 de 198 pruebas, y estuvo verde todo
el tiempo.**

**Causa raiz.** Al agregar el trabajo de imagenes a `ci.yml`, la seccion de
pruebas se **reescribio** en vez de editarse, partiendo de una copia del archivo
anterior al arreglo. No fue una decision: fue un pegado.

Lo que convierte el descuido en incidencia es lo otro: **ningun control podia
detectarlo.**

  * Las 46 pruebas que dejaron de correr **pasan**. Quitarlas no pone nada en
    rojo: pone menos cosas en verde.
  * `verificar_documentacion.py` comprueba que las cifras de la prosa coincidan
    con el repositorio, pero **nadie escribio en ninguna parte «el CI corre 198
    pruebas»**. No habia cifra que contrastar.
  * El PR #212 se reviso y se fusiono con los checks en verde. La revision miro
    lo que el PR agregaba, no lo que quitaba.

**Es la forma mas dificil de I-06.** Un control que se apaga del todo se puede
detectar; **uno que se estrecha, no**: sigue corriendo, sigue pasando, y solo
cambia cuanto mira.

**Y se encontro por casualidad.** Aparecio comparando dos ramas por otro motivo
-los conflictos de la fusion a `main`- y porque `main` conservaba la version
buena. Si el arreglo hubiera llegado a `main` despues de la reversion, no habria
habido dos versiones que comparar y nadie lo habria visto.

**Accion tomada.** Se restaura `pytest backend` y el bloque de comentarios, con
una linea nueva que dice que **esto ya se revirtio una vez** y que quien toque el
trabajo edite la linea en vez de reescribir el bloque.

**Aprendizaje.** **Un control que solo puede fallar hacia menos no se vigila
solo.** Para que el proyecto se entere del proximo, la cifra tiene que existir en
algun sitio donde una maquina la pueda contrastar: si `docs/10-manual-tecnico.md`
dijera «el CI ejecuta 198 pruebas», `verificar_documentacion.py` habria puesto
rojo el mismo dia.

Es la misma leccion que I-20 desde el otro lado. Alli el control era mas angosto
que el defecto; aqui **el control se angosto solo y nada lo midio**.

**Impacto.** Ninguna prueba fallaba, asi que no se dejo pasar ningun defecto por
esta via **que se sepa** — y nadie puede afirmar lo contrario, porque durante dos
dias esas 46 pruebas no se ejecutaron en ningun PR. Se fusionaron cinco PR en esa
ventana: #216, #217, #218, #219 y #220.

---

## I-22 · La capa de mapa de calor esta encendida y no se ve, y nadie lo noto en nueve dias

**Fecha.** 2026-09-02.

**Quien lo detecto.** Avril Madrigal, abriendo el visor para verificar H5.6.

**Que paso.** Con la casilla «Mapa de calor» marcada, **en el mapa no aparece
ninguna superficie**. Lo unico visible son los ocho puntos de origen. La capa se
dibuja por debajo de la coropleta de riesgo, que va al 85 % de opacidad y la tapa
entera.

La capa es el entregable de **H5.4**, cerrada el 18 de agosto, restituida por
**D-30** el 27 de agosto. Desde entonces esta encendida y es invisible.

**Causa raiz.** El orden de dibujo de las dos capas nunca se fijo en ninguna
parte: quedo como salio del orden de montaje de los componentes. La coropleta
tiene control de opacidad y la superficie interpolada no, asi que basta con que
la primera se dibuje encima para anular a la segunda por completo.

Lo que convierte el descuido en incidencia es que **el proyecto ya tenia el aviso
por escrito y no lo leyo como tal**. El profesor lo dijo el 2026-08-27 con estas
palabras: «Mapa de calor debe quedar arriba del riesgo». Se archivo como una
preferencia de presentacion. Era el reporte de un defecto funcional.

**Y ningun control podia atraparlo.** `verificar_recorte_calor.mjs` comprueba que
la superficie se recorte contra los poligonos, y pasa: la superficie **se calcula
y se dibuja bien**. Lo que falla es que otra capa la tapa, y eso no esta en el
alcance de ningun verificador del proyecto. La capa es correcta y no se ve.

**Accion tomada.** Se documenta el defecto en `docs/18-manual-de-usuario.md`,
seccion 9, con la advertencia de que la casilla no produce nada visible. El
arreglo del orden de dibujo queda pendiente y se decidira si es defecto de H5.4,
de H5.8 o historia nueva, con la medicion de Avril a la vista.

**Aprendizaje.** **Un control que verifica el calculo no verifica el resultado.**
Las 22 comprobaciones del recorte miran la geometria que se produce; ninguna mira
la pantalla. Entre «la capa es correcta» y «la capa se ve» hay una distancia que
solo se cubre abriendo la aplicacion, y es la misma leccion que **I-10**.

Y la otra mitad: **una nota del profesor es un reporte hasta que se demuestre lo
contrario.** Esta se leyo como una opinion sobre el orden visual durante nueve
dias. La forma de no repetirlo es reproducir antes de clasificar, que es lo que
quedo escrito en **I-14** despues del caso inverso.

**Impacto.** Nueve dias con un entregable de 8 puntos invisible en la aplicacion
publicada, incluida la revision del profesor del 27 de agosto. Ninguna decision
se tomo sobre esa capa en ese periodo, asi que el dano es de presentacion y no de
dato. Aparece en las capturas de H5.6 y en el manual de usuario de H10.3.

---

## I-23 · El diagrama de secuencia nombra un endpoint que la API no expone

**Fecha.** 2026-09-02.

**Quien lo detecto.** Avril Madrigal, leyendo los diagramas contra el
repositorio antes de arrancar H6.5.

**Que paso.** `docs/diagramas/secuencia-consulta-riesgo.svg` dibuja el flujo
principal del sistema con la llamada **`GET /riesgo?evento=&fecha=`**.

Esa ruta no existe. La API expone **`/riesgos`**, en plural
(`backend/api/rutas.py`), y el visor pide `/riesgos?...` en `cliente.js`. Hay un
`/distritos/{codigo}/riesgo` en singular, pero es otra ruta y no es la del flujo
que el diagrama representa.

El diagrama esta en el documento tecnico. Quien lo lea y pruebe `/riesgo` recibe
un 404.

En el mismo repaso aparecio lo segundo: la capa de presentacion del diagrama de
componentes quedo en agosto. Muestra «Visor React» y «MapaCanton», y desde
entonces entraron el semaforo de H7.1, el selector de fecha de H5.7 y el panel de
coordenadas de H5.6.

**Causa raiz.** `verificar_diagramas.py` comprueba cinco cosas y **las cinco son
sobre el entidad-relacion**: que cada tabla del DDL aparezca, que cada clave
foranea este, que los seis archivos existan y no esten vacios, que el generador
siga produciendo lo versionado, y que el control distinga una tabla ausente.

**Ninguna mira el contenido de los otros cinco diagramas.** El README del
generador lo dice de frente: estan «declarados» porque no se pueden derivar del
codigo con honestidad.

Esa afirmacion era demasiado ancha, y es la causa raiz de verdad. Las capas, las
flechas de dependencia y la degradacion de D-23 no se pueden derivar, cierto.
**Pero los nombres si.** Los endpoints estan declarados en `rutas.py` y los
componentes son archivos. Se dio por inderivable el diagrama entero cuando lo
inderivable era una parte.

**Accion tomada.** El arreglo de los dos diagramas y su comprobacion entran como
alcance de **H6.5**, con autorizacion escrita para que Avril toque
`generar_diagramas.py` y `verificar_diagramas.py`, que estan fuera de su carpeta.

Las comprobaciones nuevas: que cada ruta nombrada en el SVG exista en
`rutas.py`, y que cada componente dibujado corresponda a un modulo real -que
atrapa el caso inverso, dibujar algo que ya no existe-.

**Aprendizaje.** **«Esto no se puede verificar» es una afirmacion, y se sostiene
o se acota.** Escrita sin acotar, exime de comprobar la parte que si se podia. La
pregunta correcta no es si el artefacto entero se deriva del codigo, sino **que
porcion se deriva**, porque esa porcion vigilada es mejor que ninguna.

Y vale citarse a si mismo: el propio README del generador dice que «un diagrama
desactualizado es peor que ninguno: se ve autorizado y dice algo falso». La
frase estaba escrita al lado del diagrama que lo hacia.

**Impacto.** Un diagrama del documento tecnico afirmando una ruta inexistente
desde que se genero, el 2026-08-27. No bloqueo a nadie porque nadie implemento
contra el diagrama; el costo es de credibilidad del entregable, que es la
moneda de la rubrica de Arquitectura.

---

## I-24 · Cuatro controles del proyecto no corren en Windows, donde trabaja todo el equipo

**Fecha.** 2026-09-02.

**Quien lo detecto.** Avril Madrigal, al reunir en una lista los cuatro casos
sueltos que habia ido arreglando.

**Que paso.** Cuatro controles pasan en verde en el CI y **fallan al ejecutarlos
en la maquina de cualquiera del equipo**:

  * `verificar_proyeccion.py` — el cargador ESM de Node rechaza las rutas `C:\...`
    y exige `file:///C:/...`.
  * `verificar_recorte_calor.mjs` — el mismo defecto, en el import dinamico.
  * El mismo `verificar_proyeccion.py`, por otra via: pasar la geometria de los
    ocho distritos como argumento de `node -e` supera el limite de longitud de
    linea de comandos de Windows y muere con `WinError 206`, que no menciona el
    tamano en ningun lado.
  * `verificar_issues.py` — lee con `encoding="utf-8"`, y el volcado de `gh`
    redirigido en PowerShell trae marca BOM, asi que revienta con
    `Unexpected UTF-8 BOM`.

**El CI corre en Linux y los cuatro pasan. Ninguno de los cuatro corre donde se
trabaja.**

**Causa raiz.** El CI es el unico entorno donde se comprueba que los controles
funcionan, y ese entorno no es el de nadie. Cada uno de los cuatro casos se
escribio, se probo en el CI, salio verde y se dio por bueno.

No es que se olvidara probar en Windows: es que **el proyecto nunca declaro que
sus controles tuvieran que correr en Windows**, asi que no habia nada que
incumplir. La ausencia del requisito es la causa, no el descuido.

**Accion tomada.** Los cuatro arreglados: `pathToFileURL` y `Path.as_uri()` para
las rutas, archivo temporal en vez de argumento para la entrada larga, y
`utf-8-sig` para el BOM -que ademas lee bien los dos casos, porque sin BOM se
comporta igual que `utf-8`-.

**Pendiente, y es lo que de verdad cierra la incidencia:** una comprobacion de
que los controles corren en el entorno del equipo. Propuesta por Avril; queda
como trabajo con nombre y no como intencion.

**Aprendizaje.** **Un control que solo corre en un entorno que nadie usa protege
a nadie.** Su valor no esta en pasar: esta en que alguien lo ejecute antes de
abrir el PR, y eso solo pasa si corre en su maquina. Los cuatro casos estaban en
verde todo el tiempo, que es exactamente por lo que nadie los miro.

Es **I-06** en serie, y la serie es el hallazgo. Uno solo es un defecto; cuatro
con la misma forma es que falta un requisito.

**Impacto.** Cuatro controles inutiles en la practica durante el tiempo que
llevan escritos, sin forma de saber cuantas veces alguien renuncio a correr uno y
mando el PR a ciegas. Las horas de diagnostico las absorbio Avril, que ademas
identifico el patron.

**Actualizacion del mismo dia: apareció el quinto, y lo produjo esta incidencia.**

El guion de despliegue de H11.2 se escribio en bash y **no corria en ninguna
maquina del equipo**. El motivo es nuevo y vale anotarlo: winget instala
`kubectl` como **alias de linea de comandos**, uno de los reparse points de
`WindowsApps`. PowerShell lo ejecuta, Python lo ejecuta, **Git Bash no**, ni
siquiera lo encuentra con `command -v`.

El sintoma fue el peor posible: el guion decia «falta kubectl» mientras el
verificador de al lado, en Python, hablaba con el cluster sin problema.

Dos cosas se aprendieron que no estaban arriba:

  * **`command -v` pregunta si existe un archivo. La pregunta era si se puede
    ejecutar.** Las dos respuestas difieren justo en el caso que importaba.
  * Se podia arreglar pidiendole a cada uno que bajara el binario real. Eso es
    **resolver el sintoma en cuatro maquinas en vez de la causa en un archivo**,
    y deja la trampa puesta para el proximo que clone el repositorio.

El guion se reescribio en Python, que ya es requisito del proyecto y resuelve
los ejecutables como los resuelve el sistema operativo. `verificar_cd.py`
comprueba que no vuelva a bash, con el motivo escrito al lado.

---

## I-25 · Dos verificaciones del CI corrian sin impedir ninguna fusion

**Fecha.** 2026-09-02.

**Quien lo detecto.** Alejandro Rodriguez, revisando la proteccion de la rama
`dev` por un motivo distinto: el costo de actualizar cada rama antes de mergear.

**Que paso.** La regla de proteccion de `dev` exigia **tres** verificaciones para
poder fusionar: «Contratos y simulados», «Linter y formato» y «Pruebas contra
PostgreSQL».

El flujo de trabajo define **cinco**. Las dos que faltaban en la lista:

  * **Frontend** — el que corre `verificar_recorte_calor.mjs` y, desde hoy, las
    40 comprobaciones de `verificar_proyeccion.py`.
  * **Backlog y documentacion** — el que contrasta el tablero de issues contra el
    repositorio. **El mismo que salio en rojo esta manana por la issue #17.**

Las dos se ejecutaban en cada PR y salian en rojo cuando algo se rompia. Ninguna
de las dos impedia fusionar.

**Causa raiz.** La lista de verificaciones obligatorias se llena a mano, una por
una, y no se deriva del flujo de trabajo. Los dos trabajos se agregaron a
`ci.yml` despues de que la regla se configurara, y agregar un trabajo no lo
inscribe en ninguna parte.

Es un desfase silencioso por construccion: **el sitio donde se declara un control
y el sitio donde se le da poder son dos, y nada los compara.**

**Accion tomada.** Las dos agregadas a la lista de verificaciones obligatorias.
La proteccion de `dev` pasa de tres a cinco.

**Aprendizaje.** **Un control tiene dos mitades: que corra y que bloquee.** Solo
la primera se ve al mirar el CI, y es la que todo el mundo mira. Agregar un paso
al flujo de trabajo se siente como haber puesto una barrera; hasta que esta en la
lista de obligatorias, es un aviso.

Tiene consecuencia inmediata sobre trabajo de hoy: la observacion (c) del PR #229
pedia meter `verificar_proyeccion.py` al CI **para que no quedara sin
vigilancia**. Entro a un trabajo que no bloqueaba nada, asi que quedo a medias
sin que ninguno de los dos lo notara. La observacion se dio por cerrada y no lo
estaba.

Es la misma familia de I-17 y de I-21: un control que corre y no protege se ve
identico a uno que protege.

**Impacto.** Todos los PR fusionados en `dev` desde que existen esos dos trabajos
pudieron entrar con ellos en rojo. No se sabe si alguno lo hizo, y esa es
justamente la parte que no se puede reconstruir hacia atras.

---

## I-26 · El CD salio a buscar una imagen que el CI todavia no habia publicado

**Fecha.** 2026-09-02.

**Quien lo detecto.** La primera corrida del flujo, sobre `main`, sin que nadie
lo buscara.

**Que paso.** El despliegue a desarrollo murio a los 28 segundos con
`Error response from daemon: manifest unknown` al bajar
`ghcr.io/humanoidcat/geoguardian/api:sha-4bffbd6`.

Esa imagen no existia. Y no tenia por que existir todavia.

**Causa raiz.** `cd.yml` se disparaba con `on: push: branches: [main]`. **El CI
se dispara con el mismo evento**, y es el CI el que publica las imagenes en
ghcr.io, en su trabajo de H11.1.

Los dos flujos arrancan a la vez y son independientes: **nada define un orden
entre ellos.** El CD salio a buscar la imagen del commit mientras el CI todavia
estaba instalando Python.

Lo que hace que esto sea incidencia y no un descuido: **la dependencia estaba
escrita en el codigo y no en el disparador.** El propio `cd.yml` decia, en su
encabezado, «se consumen las que H11.1 publico en ghcr.io». La frase describia
una dependencia real que ningun mecanismo garantizaba.

Es la misma forma que **I-12**: un control correcto conectado con la condicion
equivocada. Alli la condicion era demasiado ancha; aca directamente no expresaba
la dependencia que el flujo necesitaba.

**Accion tomada.** El disparador pasa a `on: workflow_run` sobre el CI, con
`types: [completed]` y la condicion `conclusion == 'success'`. Ahora el CD
empieza cuando el CI termino, y solo si termino bien.

Eso obligo a un segundo cambio que no era obvio: **con `workflow_run`,
`github.sha` no es el commit que disparo el CI**, apunta a la cabeza de la rama
por omision. El commit real esta en `workflow_run.head_sha`, y es el que etiqueta
las imagenes. Confundirlos habria desplegado una version distinta de la probada
**sin que nada lo delatara** — un defecto peor que el que se estaba arreglando.

Y el paso que baja las imagenes ahora **dice su causa al fallar**: `manifest
unknown` no menciona a H11.1 en ningun lado, asi que el mensaje lo nombra.

**Aprendizaje.** **Una dependencia entre dos flujos no existe porque este escrita
en un comentario: existe si el disparador la expresa.** Dos flujos con el mismo
evento no tienen orden, y el que ese orden salga bien en las pruebas no lo
convierte en garantia.

La pregunta que faltaba al escribir `cd.yml` es la que queda: **«que tiene que
haber terminado antes de que esto empiece, y quien lo garantiza?»**.

**Impacto.** Ninguno mas alla del tiempo de diagnostico: el flujo fallo en su
primera corrida, en el paso de preparacion, sin llegar a desplegar nada. Es el
mejor momento posible para encontrarlo, y es el argumento de por que las
historias H11.2 a H11.4 **no se marcaron `[x]` al escribirlas**.

---

## I-27 · Dos caminos en el guion de despliegue, y solo uno se recorria

**Fecha.** 2026-09-02.

**Quien lo detecto.** La segunda corrida del CD sobre `main`.

**Que paso.** El despliegue murio con
`Error: Missing kustomization file 'kustomization.yaml'`.

`fijar_etiqueta()` llamaba a `kustomize edit set image` **sin situarse en el
directorio del overlay**. En la version en bash el comando iba dentro de un
`( cd "$TEMPORAL/local/$ENTORNO" && ... )`; al portar el guion a Python por I-24,
ese `cd` se perdio, y `subprocess` hereda el directorio actual —la raiz del
repositorio, donde no hay ningun `kustomization.yaml`—.

**Causa raiz.** El descuido del `cd` es la mitad. La otra es la que importa:

**el guion tenia dos caminos y solo uno se ejecutaba nunca.** Usaba `kustomize`
si el binario existia, y una sustitucion de texto si no. **En las maquinas del
equipo no hay `kustomize` instalado**, asi que todas las pruebas locales tomaban
el segundo camino. El runner si lo tiene, y tomo el primero, que no se habia
ejecutado ni una vez.

Es I-24 vista desde el otro lado. Alli el control corria en un entorno que no era
el nuestro; aca **el codigo que se probaba no era el que iba a correr**.

**Y el verificador no podia atraparlo.** `verificar_cd.py --manifiestos`
comprobaba que la cadena `newTag` **apareciera en el archivo del guion**. Eso
pasa en verde mientras la funcion revienta: buscar un texto no dice si el codigo
corre. Es la forma de **I-10** aplicada a un verificador estatico.

**Accion tomada.** Tres cambios, en orden de importancia:

  1. **Queda un solo camino.** Se elimina el de `kustomize`. La sustitucion de
     texto es la que se ejecuta en las dos partes y esta comprobada.
  2. **El verificador ejecuta la funcion** en vez de buscar una cadena: copia el
     arbol a un temporal, llama a `fijar_etiqueta()` y comprueba el resultado.
     Se introdujo el defecto a proposito y **el criterio lo detecta**.
  3. Ese criterio nuevo, en su primera version, **tampoco distinguia**: atrapaba
     `Exception` y `fijar_etiqueta` se planta con `SystemExit`, que hereda de
     `BaseException`. El verificador moria a mitad y se saltaba los trece
     criterios restantes. Corregido a `except (Exception, SystemExit)`.

**Aprendizaje.** **Una rama condicional que depende de que una herramienta este
instalada crea dos programas, y se prueba uno.** Si las dos ramas no se ejercitan
en el mismo sitio, la que no se ejercita es codigo sin escribir.

Y la de los controles, que ya va tercera esta semana: **un verificador que busca
texto comprueba la forma del codigo, no su comportamiento.** Ejecutar la funcion
cuesta cinco lineas mas y es la diferencia entre un control y un adorno.

**Impacto.** Dos corridas fallidas del CD, ninguna con consecuencia: las dos
murieron antes de desplegar. Las historias H11.2 a H11.4 siguen sin marcarse, que
es exactamente para lo que se dejo esa condicion.

## I-28 · El control de produccion contaba el pod que se estaba apagando

**Fecha.** 2026-09-03.

**Quien lo detecto.** La corrida `CD #5` sobre `main` (33727543241), la primera
que llego a produccion con una aprobacion real de por medio. Salio en rojo
despues de esperar la aprobacion desde la 1:19 hasta las 14:12.

**Que paso.** Produccion desplego bien -las dos revisiones, `latest` y luego el
SHA `e930d60`- y el paso «Comprobar lo que el despliegue promete» fallo en una
sola comprobacion de nueve:

    ok    api-64fd9f9cdb-kc248 esta Ready
    ok    postgis-0 esta Ready
    FALLA visor-7d5d85594d-zl54c esta Ready
    ok    visor-7f7994f8d5-cs59q esta Ready
    ok    visor corre el SHA exacto, no `latest`  ...:sha-e930d60...
    ok    la API responde 200 en /salud desde el cluster

Dos pods de `visor` con dos ReplicaSet distintos: `7f7994f8d5` es la revision
nueva, Ready; `7d5d85594d` es **la revision anterior, en proceso de apagarse**.
`kubectl rollout status` -que es lo que espera `desplegar.py`- vuelve cuando la
revision nueva esta disponible, no cuando la anterior termino de morir. La
comprobacion corrio cuatro segundos despues y el pod viejo todavia estaba en la
lista, con `deletionTimestamp` puesto y `Ready=False`.

**Causa raiz.** `comprobar_entorno()` exigia `Ready` a **todos los pods del
namespace**, cuando lo que el despliegue promete es que **la revision
desplegada** este Ready. Son dos afirmaciones distintas, y la primera depende
del reloj: es verdadera unos segundos despues de que la segunda ya lo era.

Y en produccion el hueco existe **siempre**, porque el flujo despliega dos veces
a proposito -para tener a que revertir, ver la cabecera de `cd.yml`-. Que las
dos corridas anteriores pasaran fue suerte: el pod de nginx suele morir en
menos de cuatro segundos, esta vez no. En desarrollo y pruebas no hay revision
anterior, y por eso alli nunca fallo.

**Es la familia de I-17, I-21 y I-25 con una variante nueva: un control que
pasa o falla segun el reloj.** Un control asi es peor que uno que siempre falla,
porque las corridas en verde lo acreditan.

**Accion tomada.**

  1. `separar_pods()`: los pods con `deletionTimestamp` se apartan y se
     imprimen como «se esta apagando: revision anterior, no cuenta». Solo los
     vivos tienen que estar Ready, y tiene que quedar al menos uno.
  2. **El control se prueba sin cluster, en cada PR**: `--manifiestos` ahora le
     da a `separar_pods()` los tres casos -pod nuevo Ready, pod viejo apagandose,
     pod vivo y roto- y comprueba que aparta el segundo y **conserva el
     tercero**. Se saboteo dos veces: con el comportamiento viejo caen tres
     comprobaciones; con el arreglo tramposo -apartar todo lo que no esta Ready-
     cae la que dice que un pod vivo y roto sigue haciendo fallar el criterio.
     Es la advertencia de I-21: el arreglo tiene que vigilar al menos lo mismo
     que antes, y aca se comprueba que vigila.
  3. No se toca `cd.yml` ni se agrega una espera: esperar a que el pod viejo
     muera habria escondido la misma pregunta mal hecha detras de un `sleep`.

**Aprendizaje.** Un control tiene que comprobar **lo que se prometio**, no el
estado del mundo en un instante. «Todos los pods Ready» era mas facil de
escribir que «la revision desplegada esta Ready», y por eso se escribio; la
diferencia solo aparecio cuando el reloj cayo del lado malo.

**Impacto.** Una corrida del CD en rojo sobre `main` con el despliegue
correcto. Ningun entorno quedo afectado: el cluster es efimero y se destruye al
final de cada corrida (D-36). H11.4 sigue cerrada: la aprobacion, el despliegue
al SHA exacto y la respuesta de `/salud` se cumplieron; lo que fallo fue una
pregunta mal hecha del verificador. Se corrige en `dev` y se promueve a `main`
para que la siguiente corrida lo demuestre.
## I-29 · El registro de migraciones es local a cada maquina, y una fusion puede cambiar una migracion aplicada sin que nadie la edite

**Fecha.** 2026-09-03.

**Quien lo detecto.** Cesar, al correr `aplicar_migraciones` despues de traer
`dev` para H1.10. Lo reporto por escrito en su respuesta a D-37 y lo dejo
contado en la evidencia de H1.10.

**Que paso.** El control dijo:

    006 006_analitico_riesgo.sql: el contenido cambio despues de aplicarse
    Una migracion aplicada no se edita. Reverti el cambio y crea un archivo nuevo.

Nadie habia editado nada. **H1.15 se hizo dos veces**: la de Cesar quedo en un
PR cerrado y la del PM -que la tomo por D-33- fue la que se fusiono. Cesar
tenia aplicada en su base la migracion 006 de su propia rama; al traer `dev`,
el archivo 006 paso a ser el de la rama que gano, con otro contenido, y el
registro local -que guarda el contenido aplicado- lo vio como una edicion.

**Causa raiz.** El registro de migraciones vive en la base de cada maquina, y
compara **contenido aplicado contra contenido en disco**. Esa comparacion es
correcta para lo que se diseño -que nadie edite una migracion ya aplicada-,
pero **no distingue «alguien edito» de «gano otra rama»**, y el mensaje manda a
revertir un cambio que no existe. Cualquiera que tenga aplicada una migracion
de una rama que no gano se va a topar con lo mismo, y va a recibir una
instruccion equivocada.

Es la familia de I-28 vista desde otro lado: **un control que dice la verdad
sobre lo que mide y miente sobre lo que significa.** La diferencia de
contenido es real; la causa que el mensaje afirma, no.

**Accion tomada.** Por ahora, registrarlo: el archivo es
`basedatos/aplicar_migraciones.py`, de Cesar, y la correccion es suya. Lo que
se le pide, por historia y sin urgencia porque no bloquea a nadie:

  1. Que el mensaje **distinga los dos casos**, o al menos nombre los dos: «el
     contenido cambio despues de aplicarse: o alguien lo edito, o tenes aplicada
     la version de otra rama». Un control que no puede saber cual de las dos
     paso no debe afirmar una.
  2. Que la evidencia de H1.10 -donde ya esta contado como se realineo sin
     perder datos- sea la referencia del procedimiento, hasta que haya uno
     escrito en `docs/10-manual-tecnico.md`.

**Aprendizaje.** Cuando dos personas hacen la misma historia en dos ramas, el
costo no termina al cerrar el PR perdedor: **todo lo que esa rama dejo
aplicado en una maquina sigue ahi**, y los controles que comparan estado local
contra repositorio lo van a encontrar. D-33 movio doce historias entre
personas; conviene esperar mas de estos.

**Impacto.** Ninguno en datos: Cesar realineo su base sin perder nada. Un
mensaje de error que manda a hacer lo incorrecto, pendiente de corregir en
`basedatos/`.

## I-30 · `/salud` dice que la base no esta conectada mientras sirve 143 407 filas de ella

**Fecha.** 2026-09-03.

**Quien lo detecto.** La primera consulta a la API en modo `postgres`, al
cerrar H3.6: `GET /salud` respondio `"modo":"real","base_datos_conectada":false`
un segundo despues de que `GET /riesgos` devolviera filas leidas de
`analitico.riesgo`.

**Que paso.** En `backend/api/rutas.py`, `base_datos_conectada=False` esta
escrito a mano desde H6.1, con este comentario: «Esta historia no abre conexion
a PostgreSQL: eso es H6.2. Declararlo falso es la respuesta honesta». Era
honesto el 2026-08-13. H6.2 trajo la conexion y no toco la linea; H3.6 activo el
modo `postgres` y la linea siguio diciendo lo de agosto.

**Causa raiz.** Un valor que era verdadero cuando se escribio y que **nada
vigila cuando deja de serlo**. `verificar_h61` comprueba que el campo sea
`False` en modo simulado (CA-8), que es correcto, y no comprueba nada en modo
real, porque cuando se escribio no habia modo real. Es la familia de I-21 y de
verificar_h66: un control que solo conoce la entrada con la que nacio.

`modo`, en cambio, no miente: `modo_de()` pregunta por la implementacion. La
diferencia entre los dos campos es exactamente la diferencia entre un valor
derivado y uno escrito a mano.

**Accion tomada.** Registrar y pedir la correccion a Cesar, dueno de
`backend/api/rutas.py` y `dependencias.py`. Lo que se le pide:

  1. Que el campo se **derive**: `True` si el repositorio activo es el de
     PostgreSQL y la conexion responde; `False` en cualquier otro caso. La forma
     natural es una funcion en `dependencias.py` al lado de `modo_de()`, que ya
     resuelve el mismo problema para `modo` sin que las rutas conozcan la clase.
  2. Que `verificar_h61` compruebe el campo **en los dos modos**, no solo en el
     que existia cuando nacio.
  3. Y que `verificar_h61` **fije el modo que necesita en vez de heredarlo**:
     al cerrar H3.6 se corrio en una terminal que tenia
     `GEOGUARDIAN_REPOSITORIO=postgres` puesta desde la prueba anterior, y CA-8
     salio en rojo -y con el, CA-7 de `verificar_h62`, que lo invoca- sin que
     nada hubiera cambiado en el codigo. `verificar_h62` ya limpia esa variable
     antes de probar; `verificar_h61` no. Es el mismo defecto visto desde el
     verificador: un control cuyo resultado depende del entorno de quien lo
     corre no distingue un defecto de una terminal.

**Impacto.** Ninguno en el visor: la franja de «datos simulados» depende de
`modo`, que es correcto. Un campo de `/salud` falso para quien lo consulte a
mano o para H12.2, la pantalla de monitoreo, que lo va a leer.

**Aprendizaje.** Un campo de estado escrito a mano tiene fecha de caducidad y
no la declara. Si un valor puede cambiar por una historia futura, o se deriva
o se vigila; escribirlo con un comentario que explica por que hoy es cierto
es dejarle una trampa a quien cierre esa historia.


---

## I-31 · Los verificadores que corremos antes de cerrar no son los que corre el CI

**Fecha.** 2026-09-03.

**Quien lo detecto.** El Pull Request #258 de H1.14, que fallo en el trabajo
*Backlog y documentacion* despues de haber pasado en verde los siete
verificadores de la lista de cierre, `pytest` completo y `ruff` en la maquina
del PM.

**Que paso.** La migracion 013 agrego `control.bitacora_etl` con diez columnas.
`verificar_diagramas.py` exige que **cada tabla y cada columna del DDL**
aparezcan en `docs/diagramas/entidad-relacion.svg`, y el diagrama versionado no
las tenia. El CI lo vio; la lista de cierre, no.

**Causa raiz.** `docs/15-cerrar-una-historia.md` manda correr tres
verificadores antes de pedir revision -`verificar_estado`, `verificar_horas`,
`verificar_documentacion`- y dice, textual: «si alguno falla, el CI tambien va
a fallar». La frase es cierta al reves y **falsa en la direccion que importa**:
que esos pasen no dice nada del CI, porque el trabajo *Backlog y documentacion*
corre ademas `verificar_diagramas.py`, `verificar_cobertura_evidencias.py` y
`verificar_issues.py`. La lista se escribio cuando esos tres no existian y
nadie la actualizo al agregarlos.

Es la forma de I-06 otra vez -el CI corriendo algo que ninguna persona corre-
pero al reves: la persona corriendo **menos** de lo que corre el CI.

**Y hay una segunda mitad.** `verificar_diagramas.py` **no se puede correr
entero en la maquina del PM**: necesita Graphviz para regenerar y comparar
(CA-4), y ahi no esta instalado. O sea que aunque la lista lo hubiera incluido,
habria fallado por falta de herramienta y no por un defecto. Un verificador que
no corre donde se hace el trabajo solo avisa cuando ya es tarde.

**Accion tomada.**

  1. `docs/15` corregido: la seccion «comprobar antes de pedir revision» lista
     ahora **los seis** verificadores del trabajo de documentacion del CI, y
     dice cual necesita Graphviz y como se instala.
  2. El diagrama se regenero y entro en el mismo PR.
  3. Queda pendiente, y se declara: **nadie ha medido** cuanto tarda correr los
     seis en local. Si resultara caro, la respuesta no es sacarlos de la lista
     sino separarlos en «los que corro siempre» y «los que corro cuando toque
     el DDL o el backlog», con esa regla escrita.

---

## I-32 · El diagrama entidad-relacion no muestra las columnas que agrega un `ALTER TABLE`

**Fecha.** 2026-09-03.

**Quien lo detecto.** Alejandro, mirando el `entidad-relacion.png` regenerado
para arreglar I-31: `control.fallo` sale con ocho columnas y en la base tiene
nueve.

**Que paso.** La migracion 012 agrego `control.fallo.corrida_id` con
`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. `leer_ddl()` de
`generar_diagramas.py` extrae las columnas del texto de los `CREATE TABLE`, asi
que esa columna no existe para el generador. El dibujo la omite desde el
2026-09-02 y **nadie lo noto durante un dia**.

**Causa raiz.** El verificador y el generador leen el DDL **de la misma
manera**. `verificar_diagramas.py` compara el diagrama contra lo que
`leer_ddl()` sabe leer, no contra lo que la base tiene: una columna invisible
para el lector es invisible para el control. Un control que comparte el punto
ciego de lo que vigila da verde sobre el defecto que existe para vigilar.

Es la misma familia que I-21 y que el CA-8 de I-30: el control conoce solo el
caso con el que nacio.

**Accion tomada.** Registrar. **No se arregla en H8.2**: tocar `leer_ddl()` es
cambiar el generador de diagramas, que es de H6.5, y hacerlo dentro de una
historia de concurrencia seria exactamente lo que `docs/07` existe para
impedir. Lo que corresponde, y queda propuesto para quien tome esa historia:

  1. Que `leer_ddl()` aplique tambien los `ALTER TABLE ... ADD COLUMN` del DDL,
     que es donde el proyecto agrega columnas desde la 007.
  2. O, mejor, que el control compare contra **la base levantada**
     (`information_schema.columns`) en vez de contra el texto del DDL: ahi no
     hay punto ciego posible. Cuesta que el trabajo del CI necesite PostgreSQL,
     que ya lo tiene el trabajo de pruebas.
  3. Mientras tanto, el diagrama dice de menos y esta declarado aca. Decir de
     menos es menos grave que decir de mas, pero no es correcto.
