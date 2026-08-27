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
# POR QUE LA CONFIGURACION DE NGINX ESTA AQUI ADENTRO
#
# Normalmente iria en `frontend/nginx.conf`. La excepcion que me dieron cubre este
# Dockerfile y su `.dockerignore`, no un tercer archivo en la carpeta de Avril, asi
# que se escribe aqui para no salirse del limite exacto que se concedio.
#
# Es menos prolijo y esta declarado: si mas adelante Avril prefiere el archivo
# aparte, se mueve y este bloque desaparece.

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

# La configuracion, con dos cosas que el visor necesita:
#
# 1. `try_files ... /index.html` — el visor es una aplicacion de una sola pagina.
#    Sin esto, recargar el navegador en cualquier ruta que no sea la raiz devuelve
#    404, porque el archivo no existe: la ruta la resuelve el navegador.
#
# 2. El paso a la API por `/api/`. En desarrollo lo resuelve el bloque
#    `server.proxy` de vite.config.js, que existe desde H6.6 justamente para que el
#    visor llegue a la API por ruta relativa y no haga falta CORS. En produccion no
#    hay servidor de Vite, asi que la misma costura la tiene que sostener nginx o
#    el visor pierde sus datos al empaquetarse.
#
#    `api` es el nombre del servicio en docker-compose.yml, que Docker resuelve por
#    DNS dentro de su red.
RUN printf '%s\n' \
    'server {' \
    '    listen 80;' \
    '    server_name _;' \
    '    root /usr/share/nginx/html;' \
    '    index index.html;' \
    '' \
    '    location /api/ {' \
    '        proxy_pass http://api:8000/;' \
    '        proxy_set_header Host $host;' \
    '        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
    '        proxy_set_header X-Forwarded-Proto $scheme;' \
    '    }' \
    '' \
    '    location / {' \
    '        try_files $uri $uri/ /index.html;' \
    '    }' \
    '}' \
    > /etc/nginx/conf.d/default.conf

EXPOSE 80

# La imagen de nginx ya corre los procesos de trabajo como usuario `nginx`; solo
# el maestro es root, que es lo que necesita para escuchar en el puerto 80.

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --spider --quiet http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
