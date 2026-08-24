# Manual técnico

**Proyecto:** GeoGuardian — estimación del riesgo climático por distrito en el
cantón de Tilarán, Costa Rica
**Historia:** H10.4 · **Rúbrica:** MVP · **Responsable:** Alejandro
**Estado del sistema al 23 de agosto de 2026**

Este manual está escrito para alguien que **no participó en el desarrollo**: un
evaluador, un profesor, o quien tenga que mantener el sistema el próximo
trimestre. Asume que sabe usar una terminal y nada más sobre el proyecto.

Para el manual de usuario del visor, ver H10.3. Para operar el sistema desplegado,
ver el manual de operación, H13.2. Este documento cubre **instalar, configurar,
levantar, verificar y entender** el sistema.

---

## 1. Qué es y qué no es todavía

GeoGuardian estima el nivel de riesgo de tres eventos climáticos —lluvia intensa,
sequía e incendio forestal— por cada uno de los ocho distritos del cantón de
Tilarán, a un horizonte de siete días, a partir de datos abiertos.

**Lo que funciona hoy y se puede comprobar siguiendo este manual:**

| Componente | Estado |
|---|---|
| Base de datos PostgreSQL con PostGIS, cuatro esquemas | Funciona |
| Modelo territorial en 3FN con las geometrías oficiales de los 8 distritos | Funciona |
| Sistema de migraciones versionadas, transaccional e idempotente | Funciona |
| Contratos de los seis módulos, con simulados y 47 comprobaciones automáticas | Funciona |
| Visor cartográfico con los polígonos distritales, contra datos simulados | Funciona |
| **Semáforo de riesgo** por distrito y evento, ordenado por urgencia (H7.1) | Funciona |
| **Reporte de calidad de datos**: completitud, atípicos y sesgo espacial (H1.5) | Método y pruebas, sin cifras reales |
| Tres entornos de Kubernetes en k3d | Funciona |
| Integración continua, 6 trabajos por cada cambio | Funciona |
| Publicación del visor como sitio estático en GitHub Pages (H11.5) | Escrito y verificado, **sin URL viva todavía** |
| Procesamiento de señales: filtrado, espectro, SPI, percentiles y anomalías | Funciona, con 108 pruebas |
| **Series climáticas reales**: 102.272 filas, 35 años, los 8 distritos | Funciona |
| **API REST** con OpenAPI y los esquemas del contrato | Funciona |
| Roles de base de datos con mínimo privilegio, verificando las denegaciones | Funciona |

**Lo que todavía no existe.** El extractor de focos de calor (H1.2) y el módulo
de modelado. Sus carpetas están creadas y reservadas, pero vacías.

**De H1.2 sí existe la medición.** El riesgo R16 se cerró el 20 de agosto contando
**242 focos de FIRMS en 24 años** dentro del cantón, con las geometrías del SNIT.
De ahí salió que el umbral de incendio del charter no producía tres clases sino
dos, y **SC-05** lo redefinió como binario: `alto` es «al menos un foco en la
ventana de 7 días» y `medio` no existe para ese evento. El alcance se acotó a los
tres distritos con señal. Ver **D-25**.

**El visor consume la API desde el 20 de agosto**, historia H6.6. Los datos que
sirve siguen siendo simulados, porque detrás de la API está el repositorio
simulado hasta que llegue H6.2, y el visor lo declara con una banda permanente en
pantalla.

Si la API no responde, el visor **no se cae**: lee el respaldo estático de
`frontend/public/simulados/` y declara también ese cambio de origen. Ver D-23.

El módulo de señales existe y está probado, pero **sus pruebas corren contra los
simulados**. Ahora que hay series reales cargadas, hay que volver a correrlas sobre
ellas: una serie real tiene patrones distintos de los del simulado. Es la
diferencia entre "funciona" y "produce resultados del cantón", y conviene no
confundirlas.

Este manual no promete nada que no se pueda ejecutar. Si un comando de aquí falla
en una máquina limpia, es un defecto del manual.

---

## 2. Requisitos previos

| Programa | Versión mínima | Para qué | Obligatorio |
|---|---|---|---|
| Git | cualquiera reciente | Clonar el repositorio | Sí |
| Docker + Docker Compose | Docker Desktop 4.x | Levantar la base de datos | Sí |
| Python | **3.11 exactamente** | Verificadores, migraciones, ETL | Sí |
| Node.js | 20 o superior | Compilar y levantar el visor | Solo para el visor |
| kubectl | 1.24 o superior | Desplegar en Kubernetes | Solo para k3d |
| k3d | 5.x | Clúster local de Kubernetes | Solo para k3d |

> **Python 3.11 no es una sugerencia.** Con 3.14 el `requirements.txt` no instala:
> `scipy` intenta compilarse desde fuente y falla. Con 3.12 y 3.13 no se ha
> probado; el CI corre sobre 3.11.

En Windows, la instalación paso a paso de cada uno está en `docs/ARRANQUE.md`,
que además documenta los errores que ya le ocurrieron al equipo.

---

## 3. Instalación

### 3.1 Clonar y situarse

```bash
git clone https://github.com/HumanoidCat/geoguardian.git
cd geoguardian
git checkout dev
```

`main` es la rama demostrable y `dev` la de integración. El estado más reciente
está en `dev`.

### 3.2 Configurar el entorno

```bash
cp .env.example .env
```

Editar `.env` y completar **las contraseñas**, que vienen vacías a propósito. Los
nombres de usuario ya traen los valores acordados por el equipo y no hay que
cambiarlos.

| Variable | Viene con | Hay que completarla |
|---|---|---|
| `POSTGRES_DB` | `geoguardian` | No |
| `POSTGRES_USER` | vacío, resuelve a `geoguardian` | No |
| `POSTGRES_PASSWORD` | vacío | **Sí, es la única obligatoria** |
| `DB_USER_ETL` | `etl_geoguardian` | No |
| `DB_PASS_ETL` | vacío | Sí, antes de H1.8 |
| `DB_USER_API` | `api_geoguardian` | No |
| `DB_PASS_API` | vacío | Sí, antes de H1.8 |
| `FIRMS_MAP_KEY` | vacío | Solo para H1.2 |
| `COPERNICUS_USER` / `COPERNICUS_PASSWORD` | vacío | Solo para H1.6 |

Las contraseñas son locales a cada máquina: inventar cualquiera larga sirve.

Para levantar la base y correr las verificaciones de la sección 5 alcanza con
`POSTGRES_PASSWORD`. Las otras dos hacen falta cuando existan los roles de mínimo
privilegio, que es la historia H1.8.

> `POSTGRES_PASSWORD` es la única variable de conexión **sin valor por defecto**,
> tanto aquí como en `docker-compose.yml`. Si falta, el contenedor no arranca y el
> mensaje lo dice explícitamente.

> `.env` está en `.gitignore` y nunca se sube. Si aparece en `git status`, hay un
> problema: avisar antes de confirmar nada.

### 3.3 Preparar Python

```bash
python -m venv .venv
source .venv/bin/activate        # Linux y macOS
.\.venv\Scripts\Activate.ps1     # Windows PowerShell
pip install -r requirements.txt
```

---

## 4. Levantar el sistema

### 4.1 Base de datos

```bash
docker compose up -d
docker compose ps
```

Esperar a que el estado sea **healthy**. La primera vez descarga la imagen de
PostGIS (unos 600 MB) y tarda un par de minutos.

Si el estado queda en `Restarting`, el arranque falló. La causa está en los
registros, no en `ps`:

```bash
docker compose logs db
```

### 4.2 Aplicar las migraciones

Los guiones de `infra/docker/init-db/` crean extensiones y esquemas, pero corren
**una sola vez**, cuando el volumen está vacío. Todo el DDL posterior se aplica
con el aplicador de migraciones:

```bash
python -m basedatos.aplicar_migraciones --verificar   # informa sin aplicar
python -m basedatos.aplicar_migraciones               # aplica lo pendiente
```

Es **idempotente**: correrlo dos veces seguidas no reaplica nada y no falla.

Si un archivo ya aplicado fue modificado, el proceso se detiene antes de tocar
nada y explica cuál cambió. Una migración aplicada no se edita: se agrega una
nueva con el siguiente número.

### 4.3 Cargar las geometrías oficiales

```bash
python -m backend.etl.cargar_distritos --solo-descargar   # sin escribir en la base
python -m backend.etl.cargar_distritos                    # descarga y carga
```

Consulta el servicio del Sistema Nacional de Información Territorial y carga los
ocho distritos de Tilarán. Toda la carga ocurre en **una sola transacción**: o
entra todo, o no entra nada. Es idempotente: cargar dos veces deja ocho filas, no
dieciséis.

Deja el rastro de la descarga en `basedatos/ddl/procedencia-geometrias.md`, con la
URL exacta, la fecha, las sumas de verificación y cuántas entidades trajo el
filtro.

### 4.4 Visor

```bash
cd frontend
npm install
python ../frontend/herramientas/exportar_simulados.py   # genera los datos estáticos
npm run dev
```

Queda en `http://localhost:5173`.

**El visor habla con la API**, por la ruta relativa `/api`, que el proxy de
`vite.config.js` reenvía a `localhost:8000`. Para verlo con datos hay que levantar
también la API, sección 4.5.

**Sin la API levantada el visor igual funciona:** cae al respaldo estático que
genera `exportar_simulados.py` y lo declara en pantalla. Por eso el exportador
sigue haciendo falta, aunque ya no sea el origen. Solo lee `contratos/` y escribe
dentro de `frontend/public/`.

Las decisiones son **D-14**, que puso la costura, y **D-23**, que la sustituyó por
la API dejando los archivos como degradación.

### 4.5 API

```bash
uvicorn backend.api.aplicacion:app --port 8000
```

Documentación interactiva en `http://localhost:8000/docs`.

Todavía **no hay servicio de API en `docker-compose.yml`**: falta su Dockerfile,
que es la historia H6.0. Hasta entonces se levanta a mano.

---

## 5. Verificar que la instalación quedó bien

Esta sección es la que hay que ejecutar para comprobar que el sistema funciona.
Cada comando imprime su propio veredicto.

### 5.1 PostGIS responde y los esquemas existen

```bash
docker compose exec db psql -U geoguardian -d geoguardian -c "SELECT postgis_version();"
docker compose exec db psql -U geoguardian -d geoguardian -c "\dn"
```

El segundo debe listar cuatro esquemas: `analitico`, `control`, `crudo` y `geo`.

### 5.2 Los contratos y sus simulados son coherentes

```bash
python -m contratos.verificar
```

Debe terminar en **"Todas las verificaciones pasaron"** con **47 comprobaciones**
y declarar **"Contratos version 1.4.0"**.

No comprueba solo que los métodos existan: comprueba las tres invariantes del
proyecto. Que un dato faltante se represente como nulo y nunca como cero; que una
estimación sin modelo entrenado sea nula y no un valor por defecto; y que la
validación temporal rechace una partición desordenada.

### 5.3 Los criterios de aceptación del modelo territorial

```bash
python -m basedatos.verificar_h13
```

Comprueba contra la base real: SRID 4326, validez geométrica, que estén los ocho
distritos de Tilarán y ninguno más, que los nombres conserven las tildes, que la
suma de las áreas coincida con el polígono cantonal dentro del 2 %, y que la
población quede nula y no en cero.

### 5.4 El modelo está en tercera forma normal y las restricciones se aplican

```bash
# Linux y macOS
docker compose exec -T db psql -U geoguardian -d geoguardian < basedatos/consultas/verificar_modelo.sql
docker compose exec -T db psql -U geoguardian -d geoguardian < basedatos/consultas/verificar_transaccion.sql

# Windows PowerShell
Get-Content basedatos\consultas\verificar_modelo.sql | docker compose exec -T db psql -U geoguardian -d geoguardian
Get-Content basedatos\consultas\verificar_transaccion.sql | docker compose exec -T db psql -U geoguardian -d geoguardian
```

> **Los dos guiones imprimen un `ERROR` a mitad de la salida y eso es correcto.**
> Es lo que la prueba provoca a propósito: en el primero, una clave foránea rechaza
> un cantón inexistente; en el segundo, una restricción `CHECK` aborta la
> transacción. El fallo sería que **no** apareciera. Cada guion explica al final
> qué demuestra.

### 5.5 Documentación y backlog consistentes

```bash
python docs/herramientas/verificar_backlog.py
python docs/herramientas/verificar_adr.py
python docs/herramientas/verificar_cobertura_evidencias.py docs/backlog.csv
python docs/herramientas/verificar_estado.py
python docs/herramientas/verificar_documentacion.py
```

La matriz de trazabilidad y la linea de avance del backlog **se generan, no se
editan**. Si `verificar_estado.py` o `verificar_documentacion.py` avisan que no
corresponden a sus fuentes:

```bash
python docs/herramientas/generar_matriz.py
```

Los cinco existen por errores que ya ocurrieron: tres dependencias apuntaban a
sprints posteriores, la rúbrica exige un mínimo de registros de arquitectura, 30 de
82 historias no tenían carpeta de evidencia asignada, cuatro historias cerradas no
figuraban en la matriz de trazabilidad, y cinco cifras escritas en la
documentación habían dejado de ser ciertas.

**`verificar_estado.py` imprime además el avance del proyecto** —historias y puntos
cerrados, por persona y por sprint— calculado desde el repositorio. Es la forma de
saber cómo va sin contar a mano.

### 5.6 Estilo del código

```bash
python -m ruff check .
python -m ruff format --check .
```

### 5.7 Visor

**Requiere haber hecho `npm install`**, sección 4.4. Sin eso los dos comandos
fallan con *"eslint no se reconoce"* y *"vite no se reconoce"*, y el mensaje no da
ninguna pista de qué falta. Node estar instalado no alcanza: las herramientas
viven en `node_modules`.

```bash
cd frontend
npm install      # si no se corrió antes, sección 4.4
npm run lint
npm run build
```

> Lo encontró César al verificar el manual el 19 de agosto. La sección 5 se
> presenta como *"la que hay que ejecutar para comprobar que el sistema
> funciona"*, lo que invita a correrla por su cuenta, y quien lo haga se topaba
> con dos fallos sin explicación.

---

## 6. Tecnologías y por qué se eligieron

Cada decisión está registrada con su alternativa descartada en
`docs/03-bitacora-decisiones.md`. Aquí el resumen.

| Capa | Tecnología | Motivo principal | ADR |
|---|---|---|---|
| Base de datos | PostgreSQL 16 + PostGIS 3.4 | Integración nativa con las bibliotecas geoespaciales de Python; cubre los cuatro criterios evaluados de bases de datos | D-03 |
| Migraciones | Aplicador propio sobre `psycopg` | Alembic resolvía lo mismo agregando una dependencia a un archivo compartido | — |
| Contratos | Protocolos estructurales de Python (PEP 544) | Un simulado cumple el contrato sin heredar de él; sustituirlo por el módulo real no toca a quien lo consume | D-06 |
| Modelado | scikit-learn, XGBoost, SHAP | Regresión Logística, Random Forest y XGBoost tienen importancia de variables nativa, que el objetivo de explicabilidad exige | D-02, D-09 |
| API | FastAPI + Pydantic | Validación en el borde y documentación OpenAPI automática, consistente con los contratos ya escritos en Pydantic | — |
| Visor | React + Leaflet | Cubre coropletas y capas conmutables sin un motor de render propio | D-14 |
| Datos climáticos | CHIRPS (precipitación) + NASA POWER (resto) | El cantón entero cabe en una celda de POWER: la precipitación salía idéntica en los ocho distritos | D-15 |
| Territorio | SNIT, servicio WFS | Fuente oficial, citable y contrastable por un tercero | D-13 |
| Plataforma | Docker Compose y k3d | Entorno reproducible en máquina limpia y tres entornos aislados | D-05 |

---

## 7. Estructura del repositorio

```
contratos/      Interfaces congeladas entre módulos y sus simulados
  simulados/    Implementaciones falsas que cumplen los mismos contratos
backend/
  etl/          Extractores y cargadores      (César)
  api/          API REST                      (César)
  senales/      Filtrado, espectro, SPI,
                anomalías                     (**Luna**)
  modelado/     Estimadores y evaluación      (Alejandro) — vacío
  calidad/      Reporte de calidad de datos   (Luna)
  tests/        Suite de pruebas              (Luna)    — 130 pruebas
basedatos/
  ddl/          Migraciones numeradas, nunca se editan una vez aplicadas
  consultas/    Guiones de verificación
  seguridad/    Roles y permisos              — vacío
frontend/       Visor cartográfico            (Avril)
infra/
  docker/       Guiones de inicialización de la base
  k8s/          Manifiestos de Kubernetes y overlays por entorno
docs/           Documentación, bitácoras, matrices y evidencias
  evidencias/   Una por historia terminada, organizada por rúbrica
```

Cada carpeta tiene un dueño y nadie modifica la de otro sin solicitud aprobada.
El mapa completo está en `docs/07-propiedad-archivos.md`.

---

## 8. Operaciones frecuentes

| Necesito | Comando |
|---|---|
| Ver el estado de la base | `docker compose ps` |
| Ver por qué falló el contenedor | `docker compose logs db` |
| Entrar a la base | `docker compose exec db psql -U geoguardian -d geoguardian` |
| Saber qué migraciones faltan | `python -m basedatos.aplicar_migraciones --verificar` |
| Empezar la base desde cero | `docker compose down -v && docker compose up -d` ← **borra todos los datos** |
| Regenerar los datos del visor | `python frontend/herramientas/exportar_simulados.py` |
| Detener todo sin perder datos | `docker compose down` |

---

## 9. Resolución de problemas

Todos los casos de esta tabla ocurrieron de verdad y están documentados con su
causa raíz en `docs/04-bitacora-incidencias.md`.

| Síntoma | Causa | Solución |
|---|---|---|
| `docker version` muestra `Client` pero no `Server` | Docker Desktop no está corriendo | Abrirlo y esperar a que diga **Engine running** |
| El contenedor de la base queda en `Restarting` | Suele ser un fallo del guion de arranque, no del contenedor | `docker compose logs db`. Si es la configuración regional, ver I-02 |
| `connection failed: server closed the connection unexpectedly` | La base publica el puerto antes de terminar de inicializarse | No es un error: `basedatos/conexion.py` reintenta hasta 90 segundos. Si persiste, revisar `docker compose ps` |
| `scipy` falla al instalar | Versión de Python distinta de 3.11 | Crear el entorno virtual con Python 3.11 |
| `kubectl` no conecta con el clúster recién creado | El kubeconfig apunta a un nombre que resuelve mal con varias interfaces de red | Crear el clúster fijando la dirección: `k3d cluster create geoguardian --api-port 127.0.0.1:6445`. Ver I-03 |
| Un `ERROR` en medio de los guiones de verificación | Es intencional: la prueba provoca el rechazo | Leer la línea siguiente del guion, que explica qué demuestra |
| `git push` pide contraseña | GitHub ya no acepta contraseñas | `gh auth login` |

---

### Una migración registrada en la base que no está en disco

    003 003_seguridad_roles.sql: registrada en la base pero no esta en disco

**No es un defecto: es la protección funcionando.** Pasa cuando la base tiene
aplicada una migración que vive en una rama sin fusionar y el repositorio está
parado en otra. El aplicador se niega antes de tocar nada, para que nadie trabaje
contra una base que no corresponde a su código.

La salida es fusionar la rama que trae esa migración, o recrear el volumen:

```bash
docker compose down -v && docker compose up -d
python -m basedatos.aplicar_migraciones
```

Lo señaló César al verificar el manual el 19 de agosto, y le va a pasar a
cualquiera que lo verifique mientras haya migraciones en ramas sin fusionar.

---

## 10. Hoja de verificación para quien revisa

Esta sección la completa **una persona ajena al desarrollo**, siguiendo el manual
desde el punto 2 en una máquina donde el proyecto no esté instalado. Es el
requisito de la historia H10.4: un manual que solo funciona para quien lo escribió
no es un manual.

| # | Paso | Comando de referencia | ¿Funcionó? | Observación |
|---|---|---|---|---|
| 1 | Instalar los requisitos previos | sección 2 | | |
| 2 | Clonar y cambiar a `dev` | 3.1 | | |
| 3 | Configurar `.env` | 3.2 | | |
| 4 | Crear el entorno de Python | 3.3 | | |
| 5 | Levantar la base | 4.1 | | |
| 6 | Aplicar migraciones | 4.2 | | |
| 7 | Aplicar migraciones **por segunda vez** | 4.2 | | Debe decir que no hay nada que aplicar |
| 8 | Cargar geometrías | 4.3 | | |
| 9 | Cargar geometrías **por segunda vez** | 4.3 | | Debe seguir habiendo 8 filas |
| 10 | PostGIS y esquemas | 5.1 | | Cuatro esquemas |
| 11 | Contratos | 5.2 | | 47 comprobaciones |
| 12 | Criterios del modelo territorial | 5.3 | | |
| 13 | Modelo y transacciones | 5.4 | | Los `ERROR` son esperados |
| 14 | Documentación y backlog | 5.5 | | |
| 15 | Estilo | 5.6 | | |
| 16 | Visor | 4.4 y 5.7 | | |

**Quién verificó:** ______________________
**Fecha:** ______________________
**Tiempo total:** ______________________
**Pasos que no funcionaron o que hubo que averiguar por fuera del manual:**

_El valor de esta hoja está en esta última línea._ Un paso que la persona tuvo que
resolver buscando por su cuenta es un defecto del manual, y se corrige antes de dar
la historia por terminada.

---

## 11. Documentación relacionada

| Archivo | Para qué |
|---|---|
| `docs/ARRANQUE.md` | Instalación paso a paso en Windows, para el equipo |
| `docs/02-contratos.md` | Las interfaces congeladas y sus huecos conocidos |
| `docs/03-bitacora-decisiones.md` | Las 27 decisiones de arquitectura con su justificación |
| `docs/04-bitacora-incidencias.md` | Qué falló, por qué y qué se cambió para que no se repita |
| `docs/05-matriz-trazabilidad.md` | Requisito, módulo, prueba y evidencia |
| `docs/06-roadmap.md` | Cronograma, capacidad y ruta crítica |
| `docs/07-propiedad-archivos.md` | Quién es dueño de qué carpeta |
| `infra/k8s/README.md` | Levantar los tres entornos en k3d |
| `CONTRIBUTING.md` | Flujo de ramas, commits y Definition of Done |
