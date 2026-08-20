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

Se corrige en **SC-04**, contratos **v1.3.2**, con cuatro comprobaciones nuevas.

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

