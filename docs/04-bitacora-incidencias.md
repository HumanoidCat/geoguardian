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

**Fecha.** 2026-08-28

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
