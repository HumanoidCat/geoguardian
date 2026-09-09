# Imagen de los trabajos programados de GeoGuardian.
#
# Existe por un hallazgo del 2026-09-09: **las estimaciones de riesgo caducan y
# nada las renueva.** `estimar_riesgo` escribe hasta hoy + 7 dias, su ultima
# corrida fue el 2026-09-05, y a partir del 2026-09-13 el visor publicado sale
# sin estimaciones en los tres eventos. Ningun flujo de Actions lo vuelve a
# correr: los comandos son manuales. El propio guion lo dice en su encabezado,
# «para "hoy" dependeria de la ingesta con cadencia de H1.14», y esa cadencia no
# existe en produccion.
#
# CONSTRUIR Y CORRER
#
#     docker build -f infra/docker/trabajos.Dockerfile -t geoguardian-trabajos .
#     docker run --rm --env-file .env geoguardian-trabajos
#
# El contexto de construccion es la RAIZ del repositorio, igual que la API.
#
# ===========================================================================
# POR QUE UNA IMAGEN APARTE Y NO LA DE LA API
# ===========================================================================
#
# `api.Dockerfile` excluye a proposito el modelado: instala cinco paquetes y
# copia solo `backend/api/`. Meter scikit-learn y xgboost ahi para poder correr
# la estimacion le agregaria cientos de megabytes **a la imagen que se publica
# en cada push** y que sirve el trafico. Son dos cosas con vidas distintas: una
# atiende peticiones todo el dia, la otra corre unos minutos y se muere.
#
# ===========================================================================
# POR QUE SIETE PAQUETES Y NO LOS VEINTICINCO
# ===========================================================================
#
# Misma disciplina que la API, con otra lista. **La lista no se adivino: se
# recorrio el grafo de imports** desde los tres puntos de entrada, y da siete:
#
#   numpy scikit-learn xgboost   los estimadores de `comparar`
#   scipy                        `backend/senales/spi.py` usa scipy.stats
#   pydantic                     `contratos/esquemas.py`
#   psycopg python-dotenv        para hablar con la base
#
# `scipy` y `pydantic` no estaban en la primera version de este archivo. Los
# encontro el recorrido del grafo, no la lectura: scipy entra por una linea
# dentro de `senales/spi.py`, tres saltos abajo de `generar_etiquetas`, y habria
# reventado en la primera corrida programada, de madrugada y sin nadie mirando.
# `scipy` ademas llegaria igual como dependencia de scikit-learn, pero se declara
# porque **se importa directo**, y lo que se importa directo se pide directo.
#
# NO entran: pandas -la cadena no lo importa-, geopandas y rasterio -son del
# ETL-, ni shap, que es de H4.2 y solo hace falta para llenar `explicacion`, que
# estas filas dejan en NULL.
#
# El `test` de siete lineas no es adorno: si alguien renombra o quita uno de esos
# paquetes del archivo compartido, la construccion falla en vez de instalar de
# menos y reventar a media corrida, de noche, sin nadie mirando.
#
# ===========================================================================
# POR QUE EL ETL NO ENTRA EN ESTA CORRIDA
# ===========================================================================
#
# Lo que caduca es la ventana de siete dias hacia adelante, y quien la escribe
# es la climatologica, que **solo mira el calendario**: no necesita observaciones
# frescas para proyectar. Correr la ingesta ademas traeria rasterio y las
# fuentes externas -otra imagen, otras credenciales, otros modos de fallar- para
# resolver un problema distinto.
#
# La cadencia de la ingesta es H1.14 y sigue pendiente. Que esta imagen no la
# resuelva esta dicho a proposito y no por olvido.
#
# ===========================================================================
# LA VARIABLE DE LA BASE SE LLAMA MAL PARA ESTE CASO, Y HAY QUE SABERLO
# ===========================================================================
#
# `basedatos/conexion.py` arma el host con **`POSTGRES_HOST_LOCAL`**, no con
# `POSTGRES_HOST`. El nombre viene de que esos guiones se escribieron para correr
# desde la maquina anfitriona contra el puerto publicado en localhost.
#
# Aca el contenedor esta **dentro** de la red privada, asi que hay que ponerle
# `POSTGRES_HOST_LOCAL=postgis` -el nombre del servicio- y suena a contradiccion
# pero es correcto. Si se pone `POSTGRES_HOST`, se ignora y la corrida intenta
# `localhost`, que dentro del contenedor no es nadie.
#
# ===========================================================================
# TIENE QUE TERMINAR Y SALIR
# ===========================================================================
#
# Railway corre el comando de arranque del servicio segun el horario y **si la
# corrida anterior sigue viva cuando llega la siguiente, se salta la nueva**. El
# `set -e` de abajo hace que un fallo en cualquier eslabon corte la cadena con
# codigo distinto de cero, en vez de seguir y escribir sobre datos a medias.

# --------------------------------------------------------------------------- #
# Etapa 1: dependencias                                                         #
# --------------------------------------------------------------------------- #

FROM python:3.11-slim AS dependencias

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt /tmp/requirements.txt

RUN set -eux; \
    grep -E '^(numpy|scipy|scikit-learn|xgboost|pydantic|psycopg|python-dotenv)' /tmp/requirements.txt > /tmp/trabajos.txt; \
    test "$(wc -l < /tmp/trabajos.txt)" -eq 7; \
    cat /tmp/trabajos.txt; \
    python -m venv /opt/venv; \
    /opt/venv/bin/pip install --no-cache-dir -r /tmp/trabajos.txt

# --------------------------------------------------------------------------- #
# Etapa 2: ejecucion                                                            #
# --------------------------------------------------------------------------- #

FROM python:3.11-slim AS ejecucion

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY --from=dependencias /opt/venv /opt/venv

# Lo que la cadena importa de verdad, rastreado modulo por modulo:
#
#   backend/modelado/    los tres guiones y lo que arrastra `comparar`
#   backend/senales/     `etiquetado` y `generar_caracteristicas` lo usan; solo
#                        biblioteca estandar, ni un paquete de terceros
#   backend/api/         `estimar_riesgo` escribe por `repositorio_postgres`
#   basedatos/conexion   la cadena de conexion y el reintento
#   contratos/           los enums y los esquemas
#
# `backend/` y `backend/senales/` son paquetes de espacio de nombres y no tienen
# __init__.py; `backend/api/` si lo tiene y por eso se copia explicito.
COPY contratos/ ./contratos/
COPY basedatos/__init__.py basedatos/conexion.py ./basedatos/
COPY backend/senales/ ./backend/senales/
COPY backend/api/__init__.py backend/api/repositorio_postgres.py ./backend/api/
COPY backend/modelado/ ./backend/modelado/

# Los dos generadores escriben aca y `estimar_riesgo` los lee. Es efimero: cada
# corrida los vuelve a producir desde la base, que es la fuente.
RUN mkdir -p /app/datos/procesados

RUN useradd --create-home --uid 10001 geoguardian && chown -R geoguardian:geoguardian /app
USER geoguardian

# El orden importa y no es intercambiable: las etiquetas salen de la base, la
# matriz de caracteristicas sale de la base y de las etiquetas, y la estimacion
# lee las dos. `--sin-escribir` va primero para dejar en el registro que escritor
# elige D-39 en esta corrida **antes** de tocar ninguna fila: si el veredicto
# cambia de un dia para otro, queda escrito quien y cuando.
CMD ["sh", "-c", "set -e; \
python -m backend.modelado.generar_etiquetas; \
python -m backend.modelado.generar_caracteristicas; \
python -m backend.modelado.estimar_riesgo --sin-escribir; \
python -m backend.modelado.estimar_riesgo"]
