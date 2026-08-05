# Guía de arranque

**Para:** César, Luna y Avril
**Tiempo:** entre 40 y 60 minutos, casi todo esperando descargas.
**Sistema:** Windows 10 u 11.

Cuando termines, avisá en el canal del equipo si funcionó o dónde te trabaste.

---

## 1. Instalar Git

```powershell
winget install Git.Git
```

Cerrá PowerShell y abrilo de nuevo. Después, poné tu nombre y correo:

```powershell
git config --global user.name "tu-usuario-de-github"
git config --global user.email "tu-correo@ejemplo.com"
```

## 2. Instalar GitHub CLI

Sirve para autenticarte sin pelear con contraseñas.

```powershell
winget install GitHub.cli
```

Cerrá y volvé a abrir PowerShell. Después:

```powershell
gh auth login
```

Elegís, en orden: **GitHub.com** → **HTTPS** → **Yes** (autenticar git) → **Login with a web browser**. Copiás el código que aparece, se abre el navegador, lo pegás y listo.

## 3. Instalar Docker Desktop

```powershell
winget install Docker.DockerDesktop
```

Esto descarga unos 600 MB. No abre ninguna ventana: solo instala.

Después va a pedir **WSL2**, que es el Linux liviano donde corren los contenedores:

```powershell
wsl --install
```

Si te pide crear un usuario de Ubuntu, poné el que quieras. **Ojo: al escribir la contraseña la pantalla no muestra nada**, ni asteriscos ni puntos. Parece congelado pero está esperando. Escribí, Enter, repetí, Enter.

**Reiniciá la computadora.** Este paso no se salta.

Al volver:

1. Abrí **Docker Desktop** desde el menú Inicio
2. Aceptá los términos
3. Esperá a que abajo a la izquierda diga **Engine running**

Comprobá que funciona:

```powershell
docker version
```

Tienen que aparecer **dos** bloques: `Client` y `Server`. Si solo sale `Client`, Docker Desktop no está abierto.

### Activar la integración con WSL

Hace falta para correr scripts `.sh`:

1. Docker Desktop → engranaje de **Settings**
2. **Resources** → **WSL Integration**
3. Activá el interruptor de **Ubuntu**
4. **Apply & Restart**

## 4. Clonar el repositorio

Elegí dónde querés trabajar. Por ejemplo, en Documentos:

```powershell
cd "$env:USERPROFILE\Documents"
gh repo clone HumanoidCat/geoguardian
cd geoguardian
```

**Pasate a la rama de trabajo.** Nunca se trabaja en `main`:

```powershell
git checkout dev
```

## 5. Configurar el entorno

```powershell
Copy-Item .env.example .env
notepad .env
```

Completá estas líneas con **tus propias contraseñas** (inventalas, son solo de tu máquina):

```
POSTGRES_DB=geoguardian
POSTGRES_USER=geoguardian
POSTGRES_PASSWORD=pone-aqui-una-contrasena-larga
DB_USER_ETL=geo_etl
DB_PASS_ETL=otra-contrasena
DB_USER_API=geo_api
DB_PASS_API=otra-mas
```

Guardá y cerrá.

> `.env` nunca se sube al repositorio. Ya está en el `.gitignore`. Si alguna vez lo ves aparecer en `git status`, avisá antes de commitear.

## 6. Levantar la base de datos

```powershell
docker compose up -d
```

La primera vez descarga la imagen de PostGIS, tarda un par de minutos. Después:

```powershell
docker compose ps
```

Esperá a ver **healthy** en la columna de estado. Si dice `starting`, dale 30 segundos y repetí. Si dice **Restarting**, algo falló: mirá el error con

```powershell
docker compose logs db
```

y pegalo en el canal del equipo.

Comprobá que quedó bien:

```powershell
docker compose exec db psql -U geoguardian -d geoguardian -c "SELECT postgis_version();"
docker compose exec db psql -U geoguardian -d geoguardian -c "\dn"
```

El segundo tiene que listar cuatro esquemas: `analitico`, `control`, `crudo` y `geo`.

## 7. Preparar Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si PowerShell no deja activar el entorno virtual, corré esto una vez y volvé a intentar:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Comprobá que todo está en su lugar:

```powershell
python -m contratos.verificar
```

Tienen que pasar las 14 verificaciones y una de ellas debe decir **"tres tipos de evento"**. Si dice "dos", tu copia del repositorio está vieja: hacé `git pull` en `dev`.

Si alguna falla, avisá: significa que un contrato se rompió y hay más gente afectada.

## 8. Empezar a trabajar

Leé tu archivo de tareas:

| Vos | Tu archivo |
|---|---|
| César | `docs/tareas/cesar.md` |
| Luna | `docs/tareas/luna.md` |
| Avril | `docs/tareas/avril.md` |

Y leé también `docs/cowork-equipo.md`: ahí está el bloque que pegás como primer mensaje de cada sesión con Claude.

Para cada historia:

```powershell
git checkout dev
git pull
git checkout -b feature/tus-iniciales-H1.1-descripcion-corta
```

Trabajás, verificás ejecutando, y abrís el Pull Request hacia `dev`.

---

## Las cinco reglas

1. **Solo tocás tu carpeta.** Si necesitás un cambio fuera de ella, se pide, no se hace.
2. **Nunca inventes datos.** Si un valor no existe todavía, va vacío o nulo con un comentario de qué depende. Una pantalla vacía y honesta es mejor que una llena de mentiras.
3. **Verificá ejecutando.** Si Claude dice que las pruebas pasan, corrélas vos.
4. **Trabajá contra los simulados** de `contratos/simulados/`. No esperes el código de nadie.
5. **Lo hecho no se borra.** Marcás `[x]` con la fecha y se queda ahí. Es tu rastro de contribución individual y hay rúbricas que lo evalúan.

**El compromiso es de 18 horas por semana**, y los Pull Requests tienen que estar **abiertos el domingo** para que el PM los revise ese día.

---

## Si algo falla

| Síntoma | Qué hacer |
|---|---|
| `docker` no se reconoce | Cerrá y abrí PowerShell. Si sigue, reiniciá la máquina |
| Sale `Client` pero no `Server` | Docker Desktop no está abierto. Abrilo y esperá el **Engine running** |
| El contenedor dice `Restarting` | `docker compose logs db` y pegá el error en el canal |
| `git push` pide contraseña | `gh auth login`. GitHub ya no acepta contraseñas |
| La contraseña de Ubuntu no aparece al escribir | Es normal en Linux. Escribí a ciegas y dale Enter |
| Querés empezar la base desde cero | `docker compose down -v` y `docker compose up -d`. **Borra todos los datos** |

**No te quedes trabado más de treinta minutos en silencio.** Escribí en el canal qué intentaste, qué esperabas y qué pasó. Cuesta menos preguntar que bloquear a los demás dos días.
