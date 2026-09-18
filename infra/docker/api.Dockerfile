# Imagen de la API de GeoGuardian. Historia H6.0, issue #62.
#
# Escrito por Cesar con la excepcion concedida el 26 de agosto: `infra/` es de
# Alejandro y este archivo entra por H6.0, y nada mas. Ver
# docs/07-propiedad-archivos.md.
#
# CONSTRUIR Y CORRER
#
#     docker build -f infra/docker/api.Dockerfile -t geoguardian-api .
#     docker compose up -d api
#
# El contexto de construccion es la RAIZ del repositorio, no esta carpeta: la API
# importa `contratos/` y `basedatos/`, que viven arriba.
#
# POR QUE SE INSTALAN SIETE PAQUETES Y NO LOS VEINTICINCO
#
# `requirements.txt` es un archivo compartido y trae las dependencias de todo el
# proyecto: pandas, geopandas, rasterio, scikit-learn, xgboost y shap, que son
# del ETL y del modelado. **La API no importa ninguno de ellos.**
#
# Se rastreo la cadena de imports desde `backend/api/aplicacion.py` y solo llega a
# `fastapi` y `pydantic`. A eso se suman `uvicorn` para servir, y `psycopg` con
# `python-dotenv`, que entran cuando se fusione H6.2 y su repositorio contra
# PostgreSQL.
#
# **Desde H14.5 (2026-09-17) entran tambien `numpy` y `scipy`.** D-53 decidio que
# el SPI-6 de la tarjeta de sequia se calcula al pedirlo, con el mismo codigo que
# uso el etiquetado -`backend/senales/spi.py`-, y ese codigo ajusta la gamma con
# `scipy.stats.gamma.fit`. La alternativa era reescribir el ajuste sin scipy, y
# se descarto porque un segundo ajuste da un segundo numero. Lo que cuesta -la
# imagen crece- esta medido en la evidencia de H14.5. Ver la enmienda de D-53.
#
# Instalar los veinticinco agregaria un par de gigas y varios minutos **a cada
# construccion**, y H11.1 va a publicar esta imagen en ghcr.io en cada push. El
# costo no lo paga esta historia: lo paga la cadena de despliegue.
#
# No se parte `requirements.txt` en dos archivos porque es compartido y eso
# necesitaria otra solicitud de cambio. En su lugar se filtra, de modo que **las
# versiones siguen viniendo de un solo lugar** y no pueden desfasarse.
#
# El `test` de cinco lineas no es adorno: si alguien renombra o quita uno de esos
# paquetes del archivo compartido, la construccion **falla** en vez de instalar de
# menos y dejar que la imagen reviente al arrancar.

# --------------------------------------------------------------------------- #
# Etapa 1: dependencias                                                         #
# --------------------------------------------------------------------------- #
#
# POR QUE DOS ETAPAS
#
# Lo pide el criterio CA-1. Y se sostiene solo: en la imagen final no queda ni
# `pip`, ni su cache, ni `requirements.txt`, que es el archivo compartido con los
# veinticinco paquetes del proyecto entero. Publicar la lista de dependencias del
# ETL dentro de la imagen de la API no aporta nada.
#
# Con honestidad sobre el tamano: los siete paquetes traen rueda precompilada
# (`psycopg[binary]` justamente por eso), asi que aqui no se compila nada y el
# ahorro es modesto, del orden de decenas de megabytes. La separacion vale por lo
# que NO viaja, no por un salto grande de peso.

FROM python:3.11-slim AS dependencias

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Se copia solo requirements.txt antes que el codigo. Asi Docker reutiliza esta
# capa mientras ese archivo no cambie, y editar un endpoint no reinstala nada.
COPY requirements.txt /tmp/requirements.txt

# El entorno virtual es el paquete que cruza a la etapa siguiente: una sola carpeta
# que se copia entera, sin arrastrar el resto del sistema de archivos.
RUN set -eux; \
    grep -E '^(fastapi|uvicorn|pydantic|psycopg|python-dotenv|numpy|scipy)' /tmp/requirements.txt > /tmp/api.txt; \
    test "$(wc -l < /tmp/api.txt)" -eq 7; \
    cat /tmp/api.txt; \
    python -m venv /opt/venv; \
    /opt/venv/bin/pip install --no-cache-dir -r /tmp/api.txt

# --------------------------------------------------------------------------- #
# Etapa 2: ejecucion                                                            #
# --------------------------------------------------------------------------- #

FROM python:3.11-slim AS ejecucion

# La misma version menor que fija el CI en .github/workflows, y la misma que la
# etapa de arriba. Si divergen, algo puede pasar las pruebas y fallar en la imagen,
# que es el peor orden posible.

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY --from=dependencias /opt/venv /opt/venv

# --------------------------------------------------------------------------- #
# Codigo                                                                        #
# --------------------------------------------------------------------------- #
#
# Solo lo que la API necesita para arrancar. `backend/etl` y `basedatos/ddl` no
# entran: el ETL corre fuera de este contenedor.

# `backend/` no tiene __init__.py: es un paquete de espacio de nombres, y copiar
# uno que no existe romperia la construccion. `backend/api/` si lo tiene.
COPY contratos/ ./contratos/
COPY basedatos/__init__.py basedatos/conexion.py ./basedatos/
COPY backend/api/ ./backend/api/

# H14.5 (D-53): el SPI-6 se calcula en la API con el codigo del proyecto.
# `backend/senales/` entera -son seis modulos chicos; `etiquetado.py` importa
# `spi.py` y `percentiles.py`- y de `backend/modelado/` SOLO `etiquetado.py`,
# que es donde vive `acumulado_mensual`. El resto de modelado -scikit-learn,
# xgboost, shap- sigue afuera, y el `.dockerignore` de al lado es quien lo
# garantiza.
COPY backend/senales/ ./backend/senales/
COPY backend/modelado/__init__.py backend/modelado/etiquetado.py ./backend/modelado/

# --------------------------------------------------------------------------- #
# Usuario sin privilegios                                                       #
# --------------------------------------------------------------------------- #
#
# El proceso no necesita ser root y correr como root en un contenedor publicado
# es una diferencia gratuita entre lo que se despliega y lo que hace falta.

RUN useradd --create-home --uid 10001 geoguardian && chown -R geoguardian:geoguardian /app
USER geoguardian

EXPOSE 8000

# `/salud` existe desde H6.1 y declara version de contratos y modo de operacion,
# asi que sirve de sonda: si responde, la aplicacion cargo sus esquemas.
#
# start-period generoso porque la API espera a que PostgreSQL acepte conexiones.
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/salud', timeout=4).status == 200 else 1)"

# Sin --reload: eso es para desarrollo y vigila el sistema de archivos.
CMD ["uvicorn", "backend.api.aplicacion:app", "--host", "0.0.0.0", "--port", "8000"]
