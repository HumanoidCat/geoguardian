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

