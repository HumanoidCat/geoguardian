# Runbook · publicar GeoGuardian en Railway

**Historia.** H11.6 · paso 1 de los tres que D-05 dejo declarados.
**Decision de arquitectura.** D-43.
**Escrito.** 2026-09-04. **Corregido con lo medido.** 2026-09-05.
**Paso 9 agregado.** 2026-09-09, por **I-48**: el sitio publicado se quedaba sin
estimaciones el 2026-09-12 y nadie lo habia medido.

**Regla que no se rompe.** Los valores de las variables los pone Alejandro en la
consola de Railway. Aca van **nombres**, nunca secretos, y nada de esto entra al
repositorio con un valor real.

Este documento existe para el **CA-10**: que alguien mas del equipo pueda
repetirlo sin mi. Por eso incluye los errores que cometi al hacerlo la primera
vez -son la parte util-, cada uno con la salida que lo delato.

---

## Que se arma

Cuatro servicios en **un solo proyecto y un solo entorno** de Railway. La red
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
                                                         ^
                                                         |
                                            +------------+---------+
                                            |       trabajos       |
                                            |  cron 09:00 UTC      |
                                            |  corre y se apaga    |
                                            +----------------------+
```

El cuarto, **`trabajos`**, no atiende nada: se enciende una vez al dia, vuelve a
estimar el riesgo y se apaga. Existe porque las estimaciones tienen fecha de
vencimiento -siete dias hacia adelante- y hasta el 2026-09-09 **nada las
renovaba**. Paso 9.

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

> **Dos avisos, del 2026-09-08.**
>
> **El host y el puerto NO son fijos.** Cada vez que se reabre el proxy, Railway
> puede dar otros: el 2026-09-06 era `altaria.proxy.rlwy.net:17362` y el 09-07
> `acela.proxy.rlwy.net:25549`. **Se leen en Settings → Networking en ese
> momento**; ningun valor anotado antes sirve.
>
> **`Test-NetConnection` NO comprueba que estes llegando a tu base.** Contra el
> host y el puerto viejos dio `TcpTestSucceeded : True` estando los dos mal: los
> proxies de Railway resuelven a un borde compartido que acepta TCP en cualquier
> puerto aunque no haya nada tuyo detras. Decia la verdad sobre lo que medía y
> mentia sobre lo que significaba. **La comprobacion honesta es intentar el
> handshake de Postgres**, con un `connect_timeout` corto para no esperar los
> noventa segundos de reintento de `conectar()`:
>
>     python -c "import os,psycopg; psycopg.connect(host=os.environ['POSTGRES_HOST_LOCAL'], port=os.environ['POSTGRES_PORT'], user=os.environ['POSTGRES_USER'], password=os.environ['POSTGRES_PASSWORD'], dbname=os.environ['POSTGRES_DB'], connect_timeout=10); print('conecta')"
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

## 9 · El servicio `trabajos`: las estimaciones no se renuevan solas

**Esto no estaba en el runbook original y es un agujero, no una mejora.** Ver
**I-48**. Medido contra la API publicada el 2026-09-09:

    2026-09-12  ->  lluvia 8/8   sequia 8/8
    2026-09-13  ->  lluvia 0/8   sequia 0/8

`estimar_riesgo` escribe hasta **hoy + 7 dias** y es un **comando manual**: la
ultima corrida fue el 2026-09-05, de ahi sale el 12. No hay `schedule:` en
`.github/workflows/`, ni CronJob en `infra/k8s/`, ni nada en Railway. Sin este
paso, **el sitio publicado se queda sin estimaciones** y por D-07 dibuja ausencia,
que es lo correcto y es justo lo que no se quiere mostrar.

> **Incendio no se arregla aca.** Sus filas terminan el 2024-12-24 porque desde
> **D-42** su escritor es la regresion logistica, que no proyecta hacia adelante.
> Correr esto no le agrega un dia. Eso es **H14.6**.

### El servicio

**New → GitHub Repo → `HumanoidCat/geoguardian`**. Renombrar a **`trabajos`**.

| Campo | Valor |
|---|---|
| Root Directory | `/` |
| Builder | Dockerfile |
| Dockerfile Path | `infra/docker/trabajos.Dockerfile` |
| Branch | `main` |
| Public Networking | **ninguno** — no generarle dominio |
| Cron Schedule (Settings) | `0 9 * * *` |

`0 9 * * *` es **09:00 UTC**, que en Costa Rica son las **3:00 de la madrugada**.
**Railway solo entiende UTC**; no hay campo de zona horaria y poner la hora local
adelanta la corrida seis horas. El horario minimo que Railway acepta es cada
cinco minutos, asi que diario entra sin problema.

> **Si se pone `*/5 * * * *` para probar, se anota en el mismo gesto cuando se
> quita.** La primera vez se puso, se dejo, y el servicio corrio cientos de
> veces fallando sin que nadie leyera una corrida: cada fallo era un correo de
> Railway, y el correo doscientos se parece al primero. Ver **I-50**. Al
> escribir `0 9 * * *` en el campo, comprobar con zoom que la casilla diga
> **At 09:00 (UTC)** y no **Daily**: Railway interpreta lo segundo como
> medianoche.

**Diario y no semanal, a proposito.** Cada corrida deja siete dias por delante.
Diario significa que **seis fallos seguidos pasan desapercibidos y el septimo se
nota**; semanal significa que un solo fallo deja el sitio en blanco.

### Variables

Las mismas de `api`, con **un cambio que importa**: el usuario. La API entra con
el rol de solo lectura; esta cadena **escribe** en `analitico.riesgo`, asi que va
con el usuario del ETL.

| Nombre | Valor |
|---|---|
| `POSTGRES_HOST_LOCAL` | `${{PostGIS.RAILWAY_PRIVATE_DOMAIN}}` |
| `POSTGRES_PORT` | `5432` |
| `POSTGRES_DB` | `geoguardian` |
| `POSTGRES_USER` | `etl_geoguardian` |
| `POSTGRES_PASSWORD` | la del rol de escritura **en la base publicada** |

> **La base publicada tiene sus propias contrasenas.** No son las del `.env` de
> nadie, y esta bien que no lo sean. Si hace falta fijar la del ETL, se hace
> **solo para ese rol** con el proxy abierto:
>
> ```powershell
> $env:NUEVA_PASS = -join ((48..57)+(65..90)+(97..122) | Get-Random -Count 32 | % {[char]$_})
> python -c "import os, psycopg; from psycopg import sql; from basedatos.conexion import conectar; c=conectar(autocommit=True); c.execute(sql.SQL('ALTER ROLE etl_geoguardian WITH LOGIN PASSWORD {}').format(sql.Literal(os.environ['NUEVA_PASS']))); print('listo')"
> Set-Clipboard $env:NUEVA_PASS      # pegar en Railway y luego: Remove-Item Env:NUEVA_PASS
> ```
>
> **No usar `crear_usuarios` para esto.** Pisa las contrasenas de **los dos**
> usuarios con las del `.env`, y la de `api_geoguardian` en produccion funciona:
> correrlo tumba el visor para arreglar el cron. Ver **I-50**.

> **`POSTGRES_HOST_LOCAL` y no `POSTGRES_HOST`**, igual que en el paso 3 y por la
> misma razon: `basedatos/conexion.py` lee esa y solo esa. Poner `POSTGRES_HOST`
> no da error, **da `localhost`**, que dentro del contenedor no es nadie. El
> propio Dockerfile lo explica en su encabezado.
>
> **`GEOGUARDIAN_REPOSITORIO` no va aca.** Esa variable la lee
> `backend/api/dependencias.py` para elegir implementacion; `estimar_riesgo`
> importa `RepositorioPostgres` directo. Ponerla no hace nada, y ponerla mal
> tampoco: por eso conviene no ponerla.
>
> **Con `api_geoguardian` la corrida falla al escribir, no al conectar.** Es un
> fallo tardio: los dos generadores corren completos y revienta al final. Si el
> registro muestra un `permission denied for table riesgo` **antes de la linea
> `escritas`**, es este error.
>
> **Si el `permission denied for table riesgo` aparece despues de `escritas`**,
> es otra cosa: la base publicada no tiene la migracion **019** y el ETL esta
> intentando el `DELETE` de `retirar_de_otros_escritores` a mano. Ver **I-51** y
> **D-48**. Se arregla aplicando la 019 con el procedimiento de mas abajo.

### Comprobar que quedo bien, en este orden

```
1. Construye. En Deployments, la etapa de instalacion tiene que listar
   exactamente siete paquetes. Si el `test` de la linea 3 del Dockerfile
   falla, la construccion se corta ahi: eso es lo que se quiere.

2. Corre y SALE. En el registro de la corrida tiene que verse el codigo de
   salida 0 y el contenedor apagado. Un servicio de cron que se queda vivo
   hace que Railway SE SALTE la corrida siguiente, sin avisar.

3. Escribio de verdad. Contra el visor, no contra la base:

   https://<dominio del visor>/api/riesgos?fecha=<hoy+7>&tipo_evento=lluvia_intensa

   Tiene que devolver ocho filas. Con la fecha de ayer + 8 devuelve cero, y
   esa es la prueba de que la ventana se movio.

4. Cuanto costo. Anotar la duracion de la corrida y mirar el consumo del
   proyecto al dia siguiente. Son tres servicios encendidos con $5; este es
   el cuarto y hay que saber cuanto suma antes de darlo por gratis.
```

### Dos cosas que hay que mirar en la consola, no suponer

  * **Si al desplegar corre una vez de inmediato o espera al horario.** Cambia
    como se prueba el punto 3: si espera, hay que disparar la corrida a mano
    desde Deployments para verla. **No lo confirme; se ve en el registro.**
  * **Si el servicio se reconstruye en cada push a `main`.** Al ser un servicio
    de repositorio, en principio si, y esta imagen es la mas pesada de las
    cuatro. Railway tiene **Watch Paths** en Settings para acotarlo a
    `infra/docker/trabajos.Dockerfile`, `backend/modelado/**`, `backend/senales/**`
    y `requirements.txt`. Vale la pena si las construcciones pesan en el consumo.

### La red de seguridad, que no es opcional

El horizonte se mueve solo mientras el cron corra. **Antes de la Invenio Fest
hay que mirarlo con los ojos**, el lunes 22 y otra vez la manana del 24:

    https://<dominio del visor>/api/riesgos?fecha=2026-09-24&tipo_evento=lluvia_intensa

Ocho filas. Si salen cero, el arreglo manual es el mismo de siempre -abrir el TCP
proxy del paso 2c, poner las variables de sesion del paso 4 con el usuario del
ETL y correr la cadena- y toma minutos, **si se descubre a tiempo**.

### Si no se quiere el servicio

**Hay una salida sin servicio nuevo:** correr la cadena a mano el lunes 22, con
el proxy abierto y las variables de sesion del paso 4:

```powershell
python -m backend.modelado.generar_etiquetas
python -m backend.modelado.generar_caracteristicas
python -m backend.modelado.estimar_riesgo --sin-escribir   # dice que escritor elige D-39
python -m backend.modelado.estimar_riesgo
```

Eso cubre hasta el **29 de septiembre** y la feria es el 24. Es menos trabajo hoy
y **es un recordatorio en la cabeza de una persona**, que es exactamente el tipo
de control que fallo para llegar a I-48. La imagen existe igual y no caduca:
sirve para esta feria y para la siguiente.

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

**Al 2026-09-06, 22:00:** la base publicada tenia dieciseis migraciones (la
014, la 015 y la 016 se aplicaron esa noche; el rodeo de I-43 se corrio y no
tenia nada que rellenar: ver la correccion de I-43). La 017 (D-45,
`analitico.serie_climatica`) se aplico despues y
`GET /api/distritos/50801/mediciones?desde=2026-08-01&hasta=2026-08-10` responde
200. **Al 2026-09-11:** dieciocho aplicadas; la **019** (D-48) entra con este
cambio y hay que aplicarla con el procedimiento de arriba **antes** de la
siguiente corrida de `trabajos`.

> **`--verificar` primero, y sobre la base correcta.** El servidor de Railway
> tiene **tres** bases: `geoguardian`, que es la buena, `postgres`, y `railway`,
> que Railway crea sola y esta vacia. Con `POSTGRES_DB=railway` el verificador
> dice «0 de 18 aplicadas» y la tentacion es aplicar. **No.** Ver I-50.

Si alguna vez una serie de precipitacion queda atascada -el ultimo dia con dato
no avanza aunque la fuente publique-, el rodeo de I-43 es, con el proxy abierto
y las mismas variables:

```powershell
python -m backend.etl.ingestar --evento lluvia_intensa --desde 2025-12-01
```

Pide desde el dia 1 de un mes, que es lo que ClimateSERV devuelve completo. Queda
escrito en la bitacora (`mensaje`: «ventana fijada con --desde»). Las corridas
siguientes vuelven a calcular su ventana solas.

**Las variables de Railway se ponen en una terminal aparte, o se limpian al
terminar.** `docker-compose.yml` lee `POSTGRES_PORT`, `POSTGRES_USER` y
`POSTGRES_PASSWORD` del entorno. La noche del 2026-09-06, un `docker compose up
-d db` corrido en la misma terminal donde seguian las variables del proxy
recreo la base **local** escuchando en el puerto del proxy y con el healthcheck
preguntando por el rol `postgres`, que ahi no existe: el aplicador fue a 5432 y
no encontro a nadie, y los registros del contenedor se llenaron de `FATAL: role
"postgres" does not exist` cada diez segundos. Los datos no se tocaron (el
volumen es el mismo), pero costo tres vueltas entenderlo. Al terminar con
Railway:

```powershell
Remove-Item Env:POSTGRES_HOST_LOCAL, Env:POSTGRES_PORT, Env:POSTGRES_USER, Env:POSTGRES_PASSWORD, Env:POSTGRES_DB
docker compose up -d db      # recrea el contenedor con los valores del .env
```

Esto es trabajo manual y se nota. Es una de las razones por las que el paso 3 de
D-05 -la automatizacion- existe como historia.

---

## PostGIS vive en `public`, y los roles necesitan USAGE ahi

La migracion **015** lo concede. Se dice aca porque el sintoma no se parece a un
problema de permisos: la API lee las tablas perfectamente, `/salud` responde
`real`, y **cualquier endpoint que llame a una funcion espacial devuelve 500**:

    function st_asgeojson(public.geometry) does not exist

El 2026-09-05 se aplico a mano sobre la base publicada, porque el sitio estaba
roto. **Esa deriva se cierra al aplicar la 015**, que registra el cambio en
`control.migracion` como corresponde. Si alguna vez se levanta la base de cero
siguiendo este runbook, la 015 entra con las demas y nada de esto hace falta.

Ver **I-40**.

---

## Lo que hay que medir, no suponer

**El plan Hobby son $5/mes que incluyen $5 de consumo**; pasarse se cobra
aparte. **Tres servicios encendidos las 24 horas con $5 es ajustado**, y no se
puede decir cuanto da sin medirlo.

**`trabajos` es el cuarto pero no esta encendido las 24 horas**: corre unos
minutos al dia y se apaga. Lo que si puede pesar son sus **construcciones**, que
son las mas grandes de las cuatro imagenes -scikit-learn y xgboost-, y por eso el
paso 9 dice que hay que mirar si se reconstruye en cada push.

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
- **No poner `POSTGRES_HOST` en `trabajos` creyendo que es el host.** Se ignora
  y la corrida va a `localhost`. La que se lee es `POSTGRES_HOST_LOCAL`.
- **No darle a `trabajos` el usuario de la API.** `api_geoguardian` es de solo
  lectura: la corrida llega hasta el final y falla al escribir.
- **No dejar que `trabajos` quede vivo.** Railway se salta la corrida siguiente
  si la anterior sigue corriendo, y no avisa.
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
| No preguntar hasta cuando alcanzaban los datos publicados | Las estimaciones se acababan el 2026-09-12 y se descubrio por casualidad | Paso 9, y la comprobacion de la ventana en el paso 7 |
| Dejar el cron de prueba `*/5` y no leer el registro | Cientos de corridas fallidas y cientos de correos, cero estimaciones renovadas | Paso 9: el horario de prueba se anota con su fecha de retiro; la primera corrida se lee entera |
| Probar el rol del ETL solo con operaciones prohibidas | La cadena completa nunca habia corrido como `etl_geoguardian`; le faltaba un permiso | CA-9 de H11.7: la aplicacion se corre con su rol |

---

**Fuentes consultadas**

- [Private Networking — como funciona (Railway Docs)](https://docs.railway.com/networking/private-networking/how-it-works)
- [Variables y referencias entre servicios (Railway Docs)](https://docs.railway.com/guides/variables)
- [Volumenes (Railway Docs)](https://docs.railway.com/guides/volumes)
- [Planes y precios (Railway Docs)](https://docs.railway.com/reference/pricing/plans)
- [Etiquetas de la imagen postgis/postgis (Docker Hub)](https://hub.docker.com/r/postgis/postgis/tags)
