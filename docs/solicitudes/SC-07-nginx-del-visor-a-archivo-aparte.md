# Solicitud de cambio de archivo compartido · la configuración de nginx del visor

**ID.** SC-07
**Archivos afectados.** `frontend/Dockerfile` (de César por la excepción de H6.0),
y dos archivos nuevos en `frontend/`: `nginx.conf.template` y
`docker-entrypoint.d/10-resolver.sh`
**Solicitante.** Alejandro, desde H11.1
**Lo detecta.** El verificador de H11.1, **ejecutando** la imagen construida
**Fecha.** 2026-09-01
**Estado.** Propuesta. Revisan **Avril** como dueña de `frontend/` y **César**
como autor del `Dockerfile` por la excepción de H6.0.
**Versión de contratos.** **Ninguna.** No toca `contratos/`.

> **Sobre el número.** SC-06 está usado dos veces:
> `docs/solicitudes/SC-06-brillo-no-comparable-entre-sensores.md` (César) y
> `docs/investigacion/solicitud-cambio-anomalia-mes.md` (Luna, fechada antes).
> Ese choque **no se resuelve aquí**: renumerar cualquiera de las dos rompe
> referencias en `backend/senales/`, `contratos/esquemas.py` y cuatro documentos
> de evidencia. Se toma SC-07, que está libre, y la duplicación queda pendiente
> como consulta abierta de Luna.

---

## Lo que se detectó

La imagen del visor **no arranca fuera de `docker compose`**:

```
nginx: [emerg] host not found in upstream "api"
       in /etc/nginx/conf.d/default.conf:8
```

nginx resuelve los nombres de los *upstream* **al arrancar, no al recibir la
petición**. Con `proxy_pass http://api:8000/` escrito de forma literal, si el
nombre `api` no existe en ese momento, nginx se niega a levantar y el contenedor
muere.

Dentro de `docker compose` el nombre siempre existe porque lo crea la red de
compose, y por eso nunca se notó.

**Por qué no lo vio nadie antes.** El `docker build` termina en cero. La imagen
se construye, se publica y se ve sana. El fallo solo aparece al **ejecutarla** sin
la API al lado. Es la razón por la que el verificador de H11.1 corre la imagen en
vez de leer el Dockerfile: la API pasó sus seis criterios, el visor cayó en el
tercero.

## Por qué esto bloquea cuatro historias

Ese escenario —el visor arrancando sin la API al lado— **es** el de las historias
de despliegue. En Kubernetes cada componente se despliega por separado, y el
visor puede arrancar antes que la API o con la API en otro nombre de servicio.

Sin este arreglo no cierran **H11.1**, ni **H11.2**, **H11.3** y **H11.4**, que
dependen de ella. Son 18 puntos y toda la entrega continua.

## Qué se pide

**Mover la configuración de nginx del `Dockerfile` a `frontend/nginx.conf.template`.**

Es la opción que el propio Dockerfile pedía. Su comentario decía, textualmente,
que la configuración estaba embebida porque la excepción de H6.0 cubría ese
archivo «y no un tercer archivo en la carpeta de Avril», y que **«si más adelante
Avril prefiere el archivo aparte, se mueve y este bloque desaparece»**.

Esta solicitud es ese «más adelante». El arreglo necesita tres directivas
acopladas entre sí y no cabe en un `printf` de una línea por renglón sin volverse
ilegible.

### Los tres cambios, que son una sola cosa

**1. El destino va en una variable.** Cuando `proxy_pass` lleva una variable,
nginx difiere la resolución hasta la petición. Sin API, el visor **levanta** y
`/api/` devuelve 502 — que es lo correcto: el visor ya sabe degradar a su
respaldo estático y declararlo en pantalla, por **D-23**. Hoy no llega ni a
intentarlo.

**2. El `rewrite` no es opcional.** Con `proxy_pass http://api:8000/` y barra
final, nginx quitaba el prefijo `/api/` solo. Con una variable **deja de
hacerlo**. Cambiar una cosa sin la otra da un fallo **peor que el actual**: el
contenedor arranca y todas las rutas devuelven 404, sin nada visible al iniciar.

**3. El `resolver` se lee del sistema**, en
`docker-entrypoint.d/10-resolver.sh`. En Docker es `127.0.0.11`; en Kubernetes es
el DNS del clúster. Escribirlo fijo arregla hoy y rompe en H11.3.

### Un cambio más, que no arregla el defecto

`ENV DESTINO_API=http://api:8000` y la plantilla procesada con `envsubst`, que es
el mecanismo que la imagen oficial de nginx ya trae.

**No hace falta para el defecto.** Se incluye porque H11.2 y H11.3 despliegan el
visor contra APIs distintas, y sin esto cada entorno necesitaría **reconstruir la
imagen** — lo que contradice la idea de promover el mismo artefacto entre
entornos, que es de lo que tratan esas historias.

## Lo que NO se pide

**No se toca nada más de `frontend/`.** Ni `src/`, ni `vite.config.js`, ni el
build. Los dos archivos nuevos son de despliegue y no de interfaz.

**No se retira la excepción de H6.0.** `frontend/Dockerfile` sigue siendo de
César. Este cambio le **quita** contenido: pierde el bloque `printf` y gana tres
líneas de `COPY`. Hay menos que revisar ahí, no más.

**No se cambia el comportamiento dentro de `docker compose`.** Con la API al
lado, el visor se comporta igual que hoy.

## Cómo se comprueba

Reproducción del defecto y del arreglo con nginx real, en el mismo entorno y sin
API en ninguna parte:

```
### ANTES  (config embebida, sin API en el DNS)
[emerg] host not found in upstream "api" in conf.d/default.conf:3
nginx: configuration file test failed

### DESPUES (plantilla + resolver, mismo entorno sin API)
10-resolver.sh: resolver -> 172.16.10.1
nginx: the configuration file syntax is ok
nginx: configuration file test is successful

### y arrancando de verdad, sin API en ninguna parte
  proceso nginx vivo: 2
  GET /        -> 200
  GET /api/x   -> 502
```

Y el `rewrite`, contra un servidor que devuelve la ruta que recibe:

```
  /api/distritos      -> /distritos
  /api/riesgo/50801   -> /riesgo/50801
  /api/salud?x=1      -> /salud?x=1
```

El prefijo se quita y la cadena de consulta se conserva.

## Qué pasa si se rechaza

H11.1 no cierra, y con ella no arrancan H11.2, H11.3 ni H11.4. La alternativa es
que **César haga el mismo arreglo en su archivo**, que es lo que corresponde por
propiedad y es media hora de trabajo. Esta solicitud existe porque lleva desde el
**2026-08-27** sin subir nada y no respondió al aviso del **2026-08-30**, y las
cuatro historias no pueden esperar más.

Si César prefiere hacerlo él, **esta solicitud se retira sin discusión** y el
trabajo se le devuelve.
