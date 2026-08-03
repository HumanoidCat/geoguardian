# GeoGuardian

Estimación del riesgo de sequía e incendio forestal por distrito en el cantón de
Tilarán, Costa Rica, mediante aprendizaje automático sobre datos climáticos y
satelitales de acceso abierto.

Proyecto Integrador · Carrera TICE · Universidad Invenio · III Trimestre 2026

## Pregunta de investigación

¿En qué medida permiten los datos climáticos y satelitales de acceso abierto
estimar el nivel de riesgo de sequía e incendio forestal por distrito en el
cantón de Tilarán, con un desempeño superior al de una línea base climatológica?

**H1.** Un modelo supervisado entrenado sobre variables derivadas de fuentes
abiertas alcanza un F1-macro superior al de una línea base construida a partir de
la normal climatológica 1991-2020, a un horizonte de siete días.

H1 es refutable por diseño. Rechazarla es un resultado válido.

## Equipo

| Persona | Rol | Carpetas propias |
|---|---|---|
| Alejandro Josué Rodríguez Zamora | PM, arquitecto, documentacion | backend/senales, backend/modelado, infra, docs |
| César Andrés Ubau Calvo | Backend y datos | backend/api, backend/etl, basedatos |
| Luis Alejandro Luna García | Análisis, calidad e investigación | backend/calidad, backend/tests, docs/investigacion |
| Avril Madrigal Elizondo | Interfaz y visualización | frontend |

## Arranque rápido

Requisitos: Docker, Docker Compose, Python 3.11, Node 20.

    cp .env.example .env
    docker compose up -d
    # La API queda en http://localhost:8000/docs
    # El visor queda en http://localhost:5173

## Estructura

    contratos/     Interfaces congeladas entre módulos y sus simulados
    backend/       API, ETL, señales, modelado, calidad y pruebas
    frontend/      Visor cartográfico y tablero
    basedatos/     DDL, seguridad, procedimientos, respaldos y consultas
    infra/         Docker y manifiestos de Kubernetes
    datos/         Datos crudos y procesados (fuera del control de versiones)
    docs/          Documentación, bitácoras, matrices y evidencias
    notebooks/     Exploración. No es código de producción.

## Fuentes de datos

| Fuente | Aporta | Acceso |
|---|---|---|
| NASA POWER | Series climáticas diarias desde 1981 | Abierto, sin registro |
| NASA FIRMS | Focos de calor desde el año 2000 | Abierto, con clave gratuita |
| Copernicus Sentinel-2 | Imágenes multiespectrales | Abierto, con cuenta gratuita |
| SNIT Costa Rica | Capas territoriales oficiales | Servicios OGC públicos |

## Documentación

Ver `docs/`. El flujo de trabajo en Git está en `CONTRIBUTING.md`.
