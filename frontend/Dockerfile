# Imagen del visor de GeoGuardian. Historia H6.0, issue #62.
#
# Escrito por Cesar con la excepcion concedida el 26 de agosto: `frontend/` es de
# Avril y este archivo entra por H6.0, y nada mas. **Avril revisa el Pull Request
# por esta parte.** Ver docs/07-propiedad-archivos.md.
#
# CONSTRUIR Y CORRER
#
#     docker build -f frontend/Dockerfile -t geoguardian-visor ./frontend
#     docker compose up -d visor
#
# DOS ETAPAS, Y POR QUE
#
# Node construye y nginx sirve. La imagen final no lleva ni Node ni node_modules:
# lo que se publica son los archivos estaticos que produce `npm run build` y un
# servidor de 50 MB en vez de uno de 1,5 GB.
#
# LA CONFIGURACION DE NGINX YA NO ESTA AQUI ADENTRO
#
# Estuvo embebida en un `printf` hasta el 2026-09-01, y este mismo comentario
# explicaba por que y decia que preferiria lo contrario: la excepcion de H6.0
# cubria este Dockerfile y su `.dockerignore`, no un tercer archivo en la carpeta
# de Avril, y quedaba anotado que «si mas adelante Avril prefiere el archivo
# aparte, se mueve y este bloque desaparece».
#
# Se movio a `frontend/nginx.conf.template` por **H11.1**, con la solicitud de
# cambio **SC-07**: la imagen no arrancaba fuera de `docker compose` y el arreglo
# no cabia en un `printf` sin volverlo ilegible.
#
# Este archivo sigue siendo de Cesar por la excepcion de H6.0. **Avril revisa el
# Pull Request por su parte**, y ahora hay menos que revisar aca, no mas.

# --------------------------------------------------------------------------- #
# Etapa 1: construir                                                            #
# --------------------------------------------------------------------------- #

FROM node:20-alpine AS construccion

WORKDIR /app

# package.json y su candado antes que el codigo: mientras las dependencias no
# cambien, Docker reutiliza la capa y editar un componente no reinstala nada.
#
# `npm ci` y no `npm install`: instala exactamente lo que dice el candado y falla
# si el candado no concuerda con package.json, en vez de resolver versiones nuevas
# en silencio. Una imagen que se construye con dependencias distintas cada vez no
# es reproducible.
COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

RUN npm run build

# --------------------------------------------------------------------------- #
# Etapa 2: servir                                                               #
# --------------------------------------------------------------------------- #

FROM nginx:1.27-alpine AS servidor

COPY --from=construccion /app/dist /usr/share/nginx/html

# La configuracion va como **plantilla**: la imagen oficial de nginx procesa
# `/etc/nginx/templates/*.template` con `envsubst` al arrancar y deja el
# resultado en `/etc/nginx/conf.d/`. Asi H11.2 y H11.3 pueden apuntar el visor a
# otra API cambiando una variable de entorno, sin reconstruir la imagen.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Destino por defecto: el nombre del servicio en docker-compose.yml, que Docker
# resuelve por DNS dentro de su red. Se declara con ENV y no dentro de la
# plantilla porque `envsubst` no admite valores por defecto: sin esto, un
# despliegue que olvide la variable dejaria `proxy_pass` vacio.
ENV DESTINO_API=http://api:8000

# La imagen de nginx ejecuta todo lo que haya en /docker-entrypoint.d/ antes de
# arrancar, asi que no hace falta tocar el CMD. Van dos guiones y **el sufijo de
# cada uno importa**:
#
#   *.envsh  el entrypoint le hace `source`, asi que lo que cambie del entorno
#            sobrevive hasta que corre `20-envsubst-on-templates.sh`.
#   *.sh     lo ejecuta en un subproceso: sirve para escribir archivos, no para
#            cambiar variables.
#
# Por eso el que normaliza `DESTINO_API` es `.envsh` y el que escribe
# `resolver.conf` es `.sh`. Escribir el primero como `.sh` compila, arranca y no
# hace nada. Los dos necesitan permiso de ejecucion: el entrypoint salta los que
# no lo tienen, en silencio.
COPY docker-entrypoint.d/05-destino-api.envsh /docker-entrypoint.d/05-destino-api.envsh
COPY docker-entrypoint.d/10-resolver.sh /docker-entrypoint.d/10-resolver.sh
RUN chmod +x /docker-entrypoint.d/05-destino-api.envsh /docker-entrypoint.d/10-resolver.sh

EXPOSE 80

# La imagen de nginx ya corre los procesos de trabajo como usuario `nginx`; solo
# el maestro es root, que es lo que necesita para escuchar en el puerto 80.

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --spider --quiet http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
