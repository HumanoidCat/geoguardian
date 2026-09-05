# Runbook · publicar GeoGuardian en Railway

**Historia.** H11.6 · paso 1 de los tres que D-05 dejo declarados.
**Decision de arquitectura.** D-43.
**Escrito.** 2026-09-04. **Corregido con lo medido.** 2026-09-05.

**Regla que no se rompe.** Los valores de las variables los pone Alejandro en la
consola de Railway. Aca van **nombres**, nunca secretos, y nada de esto entra al
repositorio con un valor real.

Este documento existe para el **CA-10**: que alguien mas del equipo pueda
repetirlo sin mi. Por eso incluye los errores que cometi al hacerlo la primera
vez -son la parte util-, cada uno con la salida que lo delato.

---

## Que se arma

Tres servicios en **un solo proyecto y un solo entorno** de Railway. La red
privada de Railway solo conecta servicios del mismo proyecto y entorno.

```
   Internet
      |
      v
  +---------+   /api/*    +----------+            +-----------+
  |  visor  | ----------> |   api    | ---------> |  postgis  |
  |  nginx  |  (interno)  | uvicorn  |  (interno) |  PG 16    |
  |  :80    |             |  :8000   |            |  :5432    |
  +---------+             +----------+            +-----------+
   dominio                 sin dominio              sin dominio
   publico                  publico                  publico
```

**Un solo dominio publico, el del visor.** La API no se expone: el navegador
nunca le habla directo. Eso no es una precaucion extra, es lo que **D-23**
decidio -el visor llama a `/api` por ruta relativa- y es la razon por la que
**no hace falta CORS** y no hay que tocar `backend/api/`, que es carpeta de
Cesar. `infra/verificar_h116.py` comprueba justamente eso: que la API **no**
tenga middleware de CORS.

---

## 1 · El proyecto

**New Project → Empty Project**, nombre `geoguardian`. Un solo entorno
(`production`). Con $5 no conviene tener dos entornos encendidos.

---

## 2 · La base: PostgreSQL 16 con PostGIS 3.5

**New → Database → Add PostgreSQL** no sirve: el Postgres que Railway ofrece por
defecto **no trae PostGIS**. Hay que desplegar una imagen que lo traiga.

**New → Docker Image**, y la imagen es exactamente esta:

```
postgis/postgis:16-3.5
```

Renombra el servicio a **`postgis`**: el nombre es el hostname interno.

### Por que esa etiqueta y no `16-master` ni `17-master`

Las plantillas de Railway que aparecen buscando «PostGIS» apuntan a etiquetas
`-master`. **No las uses.** Medido el 2026-09-05: con `16-master`,
`infra/preparar_base.py` informo

    postgis 3.7.0dev

`3.7.0dev` es una construccion de la rama de desarrollo de PostGIS, sin version
publicada. Un trabajo que se defiende no se apoya en un binario que no tiene
numero de version que citar. `16-3.5` es una version publicada y fijada.

Ademas, la base local del equipo es PostgreSQL 16. Con `16-3.5` las dos puntas
son la misma version mayor, y el paso 5 -copiar los datos- deja de tener que
justificar un salto de version.

### El orden importa, y lo aprendi rompiendolo

**Si cambias la imagen de un servicio que ya tiene volumen, primero desplegas la
imagen nueva y despues purgas el volumen. Nunca al reves.**

Lo hice al reves el 2026-09-05: purgue el volumen con la imagen vieja todavia
desplegada. El servicio reinicio, corrio `initdb` **con la imagen vieja**, y
recien entonces se aplico el cambio de imagen. El directorio de datos quedo
inicializado por una version de la biblioteca del sistema y servido por otra:

    psycopg.errors.InternalError_: template database "template1" has a
    collation version mismatch
    DETAIL: The template database was created using collation version 2.41,
    but the operating system provides version 2.31.

Y detras de eso, en cadena:

    psycopg.errors.OperationalError: database "geoguardian" does not exist

### Como se sale de ahi sin volver a purgar

La pista del propio error -`REFRESH COLLATION VERSION`- **si sirve**, con una
trampa. Sobre un cluster recien inicializado no hay ningun indice de texto que
pueda quedar mal ordenado: solo estan los catalogos del sistema, que no usan la
intercalacion por omision. Refrescar ahi es seguro, y la base nueva se crea
**despues**, copiada de una `template1` ya corregida.

**La trampa es `template0`.** Es la copia congelada de reserva de PostgreSQL: no
acepta conexiones y no se modifica, por diseno. Si se la incluye en la lista,
responde

    ERROR: invalid collation version change

y, si las sentencias van en una sola linea, la excepcion corta todo antes del
`CREATE DATABASE`. **`template0` no hace falta**: `CREATE DATABASE` copia de
`template1`.

Las bases a refrescar son las que el servidor nombra en sus propios avisos -en
esta imagen: `template1`, `postgres`, `railway` y `template_postgis`-:

```sql
ALTER DATABASE template1        REFRESH COLLATION VERSION;
ALTER DATABASE postgres         REFRESH COLLATION VERSION;
ALTER DATABASE railway          REFRESH COLLATION VERSION;
ALTER DATABASE template_postgis REFRESH COLLATION VERSION;
CREATE DATABASE geoguardian;
```

> **Esto vale para un cluster vacio y para nada mas.** Con datos adentro,
> refrescar la version sin reconstruir los indices de texto deja indices
> ordenados con reglas viejas: consultas que no encuentran filas que existen.
> Ahi lo correcto es `REINDEX DATABASE` despues del refresco, o volver a la
> imagen que creo el directorio.

Los avisos del servidor se leen en Railway: servicio → **Deployments** → *View
logs* → **Deploy Logs**. Ahi se ve que fallo y sobre que sentencia, que es como
se encontro lo de `template0` en vez de adivinarlo.

La secuencia correcta:

  1. Settings del servicio → Source Image → `postgis/postgis:16-3.5` → **Apply
     changes** y **Deploy**.
  2. Esperar a que el servicio quede **Online** con esa imagen. Confirmar que
     **no queda barra de cambios pendientes**.
  3. Recien ahora: pestana del volumen → Settings → **Wipe volume**. Railway
     pide escribir una frase de confirmacion; **la escribe una persona**.
  4. Esperar a que vuelva a Online.

### 2b · La base tiene que llamarse `geoguardian`

**No es preferencia, es un requisito del DDL**, comprobado el 2026-09-04 contra
una base llamada `railway`:

    Aplicando 003 003_seguridad_roles.sql ... FALLO

`basedatos/ddl/003_seguridad_roles.sql` tiene el nombre escrito literal:

    REVOKE ALL    ON DATABASE geoguardian FROM PUBLIC;
    GRANT CONNECT ON DATABASE geoguardian TO geoguardian_etl, ...;

Es correcto -un `GRANT ON DATABASE` tiene que nombrarla- y **no se arregla
editando la migracion**: una migracion aplicada no se edita nunca, y el
aplicador compara su SHA-256 justamente para detectarlo.

La imagen crea una base con el nombre de `POSTGRES_DB` (Railway pone `railway`).
Hay que crear la nuestra a mano; el paso 4 dice como.

`infra/preparar_base.py` se planta si el nombre no coincide y lo dice citando la
linea de la migracion, asi que saltarse esto no llega lejos sin enterarse.

### 2c · Exponer la base temporalmente

Para construir el esquema y cargar los datos desde tu maquina hace falta que la
base sea alcanzable desde fuera **una sola vez**:

Settings → Networking → **TCP Proxy**, puerto de destino `5432`. Railway
devuelve un host y un puerto publicos. **Se quitan en el paso 7.**

De la pestana **Variables** del servicio se anotan, para el paso 4:
`PGDATABASE`, `PGUSER`, `PGPASSWORD` (el superusuario) y el
`RAILWAY_PRIVATE_DOMAIN` (`postgis.railway.internal`), que es lo que va a leer
la API.

---

## 3 · El servicio `api`

**New → GitHub Repo → `HumanoidCat/geoguardian`**. Renombrar a **`api`**.

| Campo | Valor |
|---|---|
| Root Directory | `/` |
| Builder | Dockerfile |
| Dockerfile Path | `infra/docker/api.Dockerfile` |
| Branch | `main` |
| Public Networking | **ninguno** — no generarle dominio |

La imagen ya expone `8000` y arranca con
`uvicorn ... --host 0.0.0.0 --port 8000`; no hay que tocar el comando.

En **Variables**, con estos nombres exactos -los lee `basedatos/conexion.py`,
que es el mismo modulo que usa `repositorio_postgres.py`-:

| Nombre | Valor |
|---|---|
| `GEOGUARDIAN_REPOSITORIO` | `postgres` |
| `POSTGRES_HOST_LOCAL` | `${{PostGIS.RAILWAY_PRIVATE_DOMAIN}}` |
| `POSTGRES_PORT` | `5432` |
| `POSTGRES_DB` | `geoguardian` |
| `POSTGRES_USER` | `api_geoguardian` |
| `POSTGRES_PASSWORD` | la del rol de solo lectura |

`${{PostGIS.RAILWAY_PRIVATE_DOMAIN}}` es una **referencia de variable** de
Railway: apunta al servicio por nombre, no por un valor copiado, asi que no se
queda desactualizada si el dominio interno cambia.

> **El nombre `POSTGRES_HOST_LOCAL` es confuso aca** y no es un error de copia:
> se llama asi porque nacio para los guiones que corren fuera de la red de
> Docker. Funciona igual. Renombrarlo toca `basedatos/conexion.py`, que es
> modulo compartido de Cesar, y no es de esta historia: queda anotado.
>
> **`api_geoguardian` es el rol de solo lectura de H1.8, a proposito.** La API
> no tiene por que poder escribir. En el paso 6 se prueba intentando escribir.

**No va a desplegar bien todavia** -la base esta vacia-. Esta bien: seguir.

---

## 4 · Construir el esquema, desde tu maquina

Este paso se corre desde PowerShell contra el TCP proxy del paso 2c.

### Como se apunta a Railway: variables de sesion, no un archivo

**No sirve copiar `.env` a `.env.railway` y editarlo.** `load_dotenv()` lee
**unicamente** el archivo llamado `.env`, y ademas **no pisa** las variables que
ya existen en el entorno del proceso. Lo comprobe el 2026-09-04 despues de
mandar a hacer justamente eso: el guion siguio conectandose a `localhost`.

Lo que si funciona -y tiene la ventaja de que **no deja ningun archivo con
credenciales en el disco**- es poner las variables en la sesion de PowerShell.
`load_dotenv()` las respeta porque no pisa lo que ya esta puesto.

```powershell
cd "C:\Users\Alejo\Documents\Invenio_TI\3-2026\Proyecto integrador\geoguardian"
.\.venv\Scripts\Activate.ps1

$env:POSTGRES_HOST_LOCAL = "<host del TCP proxy>"
$env:POSTGRES_PORT       = "<puerto del TCP proxy>"
$env:POSTGRES_USER       = "postgres"
$env:POSTGRES_PASSWORD   = "<la del superusuario>"
```

Esas variables viven mientras la ventana este abierta. Si la cerras, se ponen de
nuevo; no quedan escritas en ningun lado.

### Crear la base y prepararla

```powershell
$env:POSTGRES_DB = "railway"
python -c "import os, psycopg; c = psycopg.connect(host=os.environ['POSTGRES_HOST_LOCAL'], port=os.environ['POSTGRES_PORT'], dbname=os.environ['POSTGRES_DB'], user=os.environ['POSTGRES_USER'], password=os.environ['POSTGRES_PASSWORD'], autocommit=True); c.execute('CREATE DATABASE geoguardian'); print('creada')"

$env:POSTGRES_DB = "geoguardian"
python -m infra.preparar_base --comprobar   # informa y no cambia nada
python -m infra.preparar_base               # extensiones y los cuatro esquemas
python -m basedatos.aplicar_migraciones     # las 13 migraciones
python -m basedatos.seguridad.crear_usuarios
python -m basedatos.seguridad.verificar_h18 # el minimo privilegio, probado
```

**En la salida de `preparar_base` hay que ver `postgis 3.5.x`.** Si dice
`3.7.0dev`, la imagen que corre no es la fijada, o el volumen se purgo antes de
desplegarla: volver al paso 2.

> **`preparar_base` es nuevo y sin el no corre nada de lo demas.** Las
> extensiones y los cuatro esquemas los creaba
> `infra/docker/init-db/01-extensiones.sql`, que **solo corre desde
> docker-compose**, cuando el volumen esta vacio. En cualquier base que no venga
> de compose ese guion no existe, y la primera migracion cae:
>
>     Aplicando 001 001_control_migracion.sql ... FALLO
>     schema "control" does not exist
>
> Comprobado el 2026-09-04 contra un PostgreSQL 16 recien creado.
> `preparar_base` aplica **ese mismo archivo leido del disco**, no una copia, y
> despues comprueba que las extensiones quedaron.

Toda esta cadena esta ensayada de punta a punta contra dos PostgreSQL reales:
las trece migraciones aplican limpias y **el verificador de minimo privilegio de
H1.8 pasa**, que es el CA-6 probado antes de tocar Railway.

---

## 5 · Cargar los datos

`infra/cargar_datos.py` copia las tablas de la base local a la de la nube con
`COPY` binario, en orden topologico de llaves foraneas.

**Este es el unico paso que si necesita un archivo**, porque hay dos bases a la
vez y las variables de sesion solo describen una. El archivo del **destino** se
escribe a mano y se borra al terminar:

```powershell
# .env.destino  (NO se versiona: .gitignore ignora .env.* salvo .env.example)
POSTGRES_HOST_LOCAL=<host del TCP proxy>
POSTGRES_PORT=<puerto del TCP proxy>
POSTGRES_DB=geoguardian
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<la del superusuario>
```

```powershell
python -m infra.cargar_datos --destino .env.destino --reemplazar
Remove-Item .env.destino
```

Lo que el guion hace y **por que**, que es lo que hay que entender antes de
correrlo:

  * **No copia `control.migracion`.** Ese registro dice que migraciones se
    aplicaron **en esta base**; copiarlo hace que el destino afirme un estado que
    nadie le aplico.
  * **Comprueba que las columnas de origen y destino coincidan** antes de copiar.
    Una copia binaria con una columna de diferencia corre a ciegas.
  * **Iguala las secuencias** despues de copiar. Sin eso, la proxima insercion
    del ETL choca contra una clave que ya existe.
  * **Comprueba los disparadores de historial.** Un disparador que se dispare en
    `INSERT` fabricaria filas de auditoria durante la copia y las cuentas no
    cuadrarian. Medido: `riesgo_auditoria_tg` es `AFTER DELETE OR UPDATE`, asi
    que una copia -que solo inserta- no lo activa. **Esa premisa se comprobo con
    `pg_get_triggerdef`, no se supuso.**

Despues, el **CA-4**: contar las filas de las dos bases y que den lo mismo.

---

## 6 · El servicio `visor`

**New → GitHub Repo → `HumanoidCat/geoguardian`**. Renombrar a **`visor`**.

| Campo | Valor |
|---|---|
| Root Directory | `/frontend` |
| Builder | Dockerfile |
| Dockerfile Path | `Dockerfile` |
| Public Networking | **Generate Domain**, target port **80** |

En **Variables**, una sola:

| Nombre | Valor |
|---|---|
| `DESTINO_API` | `http://${{api.RAILWAY_PRIVATE_DOMAIN}}:8000` |

> **Sin barra final.** `proxy_pass` concatena el valor tal cual: con barra
> produce `//distritos`, que falla en silencio y no aparece en ningun registro.
> Esta documentado en `visor-deployment.yaml` y en `05-destino-api.envsh`, y en
> la evidencia de esta historia se **provoca** para ver que falla de verdad.
>
> **`http://` y no `https://`.** Dentro de la red privada de Railway el trafico
> ya va por el tunel; forzar TLS ahi solo rompe.

---

## 7 · Comprobar, en este orden

```
1. La API NO se alcanza desde fuera: confirmar en Settings que Public
   Networking esta vacio. No hay URL que pedir, y esa es la prueba.

2. La API responde por dentro, a traves del visor:
   https://<dominio del visor>/api/salud   ->   modo = "real"

   Si dice "simulado", la API no llego a PostgreSQL. NO forzarlo con una
   variable: `modo` se deduce de que implementacion respondio, y esa es la
   gracia.

3. Todas las peticiones del navegador al mismo origen: abrir el visor,
   F12 -> Red. Ni una peticion a otro dominio, ni una cabecera CORS.

4. El rol de solo lectura no puede escribir: con las credenciales de
   api_geoguardian, un INSERT en analitico.riesgo tiene que ser RECHAZADO.
   Un rol de lectura que nadie probo escribiendo no esta probado.
```

---

## 8 · Cerrar la puerta

Una vez cargados los datos:

  * **Quitar el TCP proxy de `postgis`** (Settings → Networking). Deja de haber
    una base expuesta a Internet.
  * Confirmar que no quedo ningun `.env.*` con valores reales:
    `git status --short` no tiene que mostrarlo, y `.gitignore` lo ignora, pero
    **borrarlo es mejor que ignorarlo**.

---

## Cuando entra una migracion nueva al repositorio

La base publicada **no se actualiza sola**. Cada vez que se fusiona una historia
que agrega un archivo a `basedatos/ddl/`, hay que aplicarla a la nube:

```powershell
$env:POSTGRES_HOST_LOCAL = "<host del TCP proxy>"   # hay que reabrirlo
$env:POSTGRES_PORT       = "<puerto del TCP proxy>"
$env:POSTGRES_USER       = "postgres"
$env:POSTGRES_PASSWORD   = "<la del superusuario>"
$env:POSTGRES_DB         = "geoguardian"
python -m basedatos.aplicar_migraciones
```

**Pendiente al 2026-09-05:** el PR #262 (H12.1, Luna) agrega
`014_bitacora_etl_diagnostico.sql`, que extiende `control.bitacora_etl`. La base
publicada tiene trece migraciones. Cuando ese PR se fusione, hay que correr lo de
arriba; si no, la API publicada corre contra un esquema mas viejo que su codigo y
el sintoma va a aparecer lejos de la causa.

Esto es trabajo manual y se nota. Es una de las razones por las que el paso 3 de
D-05 -la automatizacion- existe como historia.

---

## Lo que hay que medir, no suponer

**El plan Hobby son $5/mes que incluyen $5 de consumo**; pasarse se cobra
aparte. **Tres servicios encendidos las 24 horas con $5 es ajustado**, y no se
puede decir cuanto da sin medirlo.

Por eso el **CA-9** lo mide **a las 48 horas**, no el dia de la entrega. Y por
eso **el visor de GitHub Pages no se toca**: si Railway se apaga, la defensa
sigue teniendo un sitio en pie que declara sus datos como simulados.

**El plan Hobby no tiene respaldos automaticos** -son de Pro-. El respaldo real
es que el esquema se reconstruye con `aplicar_migraciones` y los datos se
vuelven a copiar con `cargar_datos`: este runbook **es** el procedimiento de
restauracion, y por eso esta versionado.

Si a las 48 h el consumo no cierra, hay dos salidas: apagar servicios fuera de
horario, o dejar solo base + API y que el visor siga en GitHub Pages -lo que si
obligaria a CORS y a tocar archivo de Cesar, con solicitud de cambio-.

---

## Lo que NO hay que hacer

- **No generarle dominio publico a `api` ni a `postgis`.** Rompe el modelo de un
  solo origen de D-23 y expone la base.
- **No usar una etiqueta `-master` de PostGIS.** Ver el paso 2.
- **No purgar un volumen antes de desplegar el cambio de imagen.** Ver el paso 2.
- **No poner `GEOGUARDIAN_REPOSITORIO=postgres` en el visor.** No lo lee.
- **No copiar ningun secreto a un archivo del repositorio.** Ni a `.env.example`,
  ni a un manifiesto, ni a un comentario.
- **No borrar `frontend/public/simulados/*.json`.** Son la degradacion que exige
  la Definition of Done de H6.6, y el respaldo si Railway cae.

---

## Errores cometidos la primera vez, para que no se repitan

| Que pase por alto | Como se manifesto | Que lo evita |
|---|---|---|
| Purgar el volumen antes de desplegar la imagen nueva | `template1 has a collation version mismatch (2.41 vs 2.31)` | Paso 2: imagen, desplegar, **despues** purgar |
| Usar una etiqueta `-master` | `postgis 3.7.0dev`, sin version publicada | Paso 2: `16-3.5` fijada |
| Creer que `load_dotenv()` lee `.env.railway` | El guion siguio yendo a `localhost` sin decir nada | Paso 4: variables de sesion de PowerShell |
| `.gitignore` con `.env` exacto y no `.env.*` | Un archivo con contrasenas reales **no** estaba ignorado | Corregido en esta historia, con el motivo escrito en el propio `.gitignore` |
| Incluir `template0` al refrescar la intercalacion | `ERROR: invalid collation version change`, y la excepcion corto el `CREATE DATABASE` | Paso 2: `template0` no se toca ni hace falta |
| Afirmar que hacia falta CORS | D-23 y `cliente.js` ya resolvian eso con ruta relativa | Leer la decision antes de proponer |

---

**Fuentes consultadas**

- [Private Networking — como funciona (Railway Docs)](https://docs.railway.com/networking/private-networking/how-it-works)
- [Variables y referencias entre servicios (Railway Docs)](https://docs.railway.com/guides/variables)
- [Volumenes (Railway Docs)](https://docs.railway.com/guides/volumes)
- [Planes y precios (Railway Docs)](https://docs.railway.com/reference/pricing/plans)
- [Etiquetas de la imagen postgis/postgis (Docker Hub)](https://hub.docker.com/r/postgis/postgis/tags)
