# GeoGuardian

Estimación del riesgo climático por distrito en el cantón de Tilarán, Costa Rica,
mediante aprendizaje automático sobre datos climáticos y satelitales de acceso
abierto. Estima tres eventos: lluvia intensa, sequía e incendio forestal.

Proyecto Integrador · Carrera TICE · Universidad Invenio · III Trimestre 2026

## Pregunta de investigación

¿En qué medida permiten los datos climáticos y satelitales de acceso abierto
estimar el nivel de riesgo de lluvia intensa, sequía e incendio forestal por
distrito en el cantón de Tilarán, con un desempeño superior al de una línea base
climatológica?

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

**Si es tu primera vez, leé `docs/ARRANQUE.md`**: está paso a paso con los errores ya documentados.

Requisitos: Docker, Docker Compose, **Python 3.11** y **Node 20 o superior**.

> Python 3.11 no es una sugerencia: con 3.14 el `requirements.txt` no instala,
> porque `scipy` intenta compilarse desde fuente y falla.

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

| Fuente | Aporta | Resolución | Acceso |
|---|---|---|---|
| CHIRPS | Precipitación diaria desde 1981 | 0,05° (~5,5 km) | Abierto, sin registro |
| NASA POWER | Temperatura, humedad, radiación y viento, diarias desde 1981 | 0,5° × 0,625° (~68 × 55 km) | Abierto, sin registro |
| NASA FIRMS | Focos de calor desde el año 2000 | ~375 m por detección | Abierto, con clave gratuita |
| Copernicus Sentinel-2 | Imágenes multiespectrales | 10-60 m | Abierto, con cuenta gratuita |
| SNIT Costa Rica | Capas territoriales oficiales | 1:5000 | Servicios OGC públicos |

> **Por qué dos fuentes climáticas.** El cantón entero cabe dentro de una sola
> celda de NASA POWER, así que la precipitación salía idéntica en los ocho
> distritos y dos de los tres eventos —sequía y lluvia intensa, ambos definidos
> sobre precipitación— habrían dado el mismo riesgo por construcción. CHIRPS
> reparte el cantón en unas 36 celdas. Ver `docs/03-bitacora-decisiones.md`, D-15.

## Estado del proyecto

| | |
|---|---|
| Contratos | v1.4.0, congelados. 47 verificaciones en `python -m contratos.verificar` |
| Base de datos | PostgreSQL 16 + PostGIS, levanta con `docker compose up -d` |
| Despliegue | Tres entornos en k3d local, ver `infra/k8s/README.md` |
| Integración continua | Cinco trabajos: contratos, backlog y documentación, linter, pruebas y frontend |
| Backlog | 86 historias, 423 puntos. Completo en `docs/08-backlog.md`, por persona en `docs/tareas/` |
| Tablero | GitHub Projects, agrupado por sprint |

## Documentación

| Archivo | Para qué |
|---|---|
| `docs/ARRANQUE.md` | Instalar todo y dejar el entorno funcionando |
| `docs/cowork-equipo.md` | Cómo trabajar con Claude, reglas y ritmo de entrega |
| `docs/tareas/` | Historias asignadas a cada quien |
| `docs/02-contratos.md` | Interfaces congeladas entre módulos |
| `docs/03-bitacora-decisiones.md` | Decisiones técnicas con su justificación |
| `docs/04-bitacora-incidencias.md` | Qué falló, por qué y qué aprendimos |
| `docs/05-matriz-trazabilidad.md` | Requisito, módulo, prueba y evidencia |
| `docs/06-roadmap.md` | Cronograma y capacidad |
| `CONTRIBUTING.md` | Flujo de ramas, commits y Definition of Done |
