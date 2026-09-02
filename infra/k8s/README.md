# Kubernetes en k3d local

Historia **H8.6** · rúbrica **Arq** (Arquitectura de Software) · dueño Alejandro

Los tres entornos que exige la rúbrica viven en **un mismo clúster k3d**, en
espacios de nombres distintos. La decisión está registrada en `D-05`.

| Entorno | Namespace | Almacenamiento | Despliegue |
|---|---|---|---|
| Desarrollo | `geoguardian-desarrollo` | 1 Gi | Automático al mergear a `main` (H11.2) |
| Pruebas | `geoguardian-pruebas` | 3 Gi | Con aprobación manual (H11.3) |
| Producción | `geoguardian-produccion` | 5 Gi, 2 Gi de memoria | Aprobación explícita y reversión (H11.4) |

> **Producción** aquí significa el namespace de producción del clúster local, no
> un sistema en operación real. El manual de operación (H13.2) tiene que decirlo
> así, sin adornarlo.

## Qué contiene hoy

**La base de datos, la API y el visor.** Desde H11.2 los tres:

| | Objeto | Imagen |
|---|---|---|
| PostGIS | `StatefulSet` + `Service` headless + `ConfigMap` | `postgis/postgis:16-3.4` |
| API | `Deployment` + `Service` | `ghcr.io/humanoidcat/geoguardian/api` |
| Visor | `Deployment` + `Service` | `ghcr.io/humanoidcat/geoguardian/visor` |

Las imágenes **no se construyen al desplegar**: se consumen las que H11.1
publica en ghcr.io. Reconstruirlas daría un binario distinto del que se probó.

## Requisitos

- **Docker Desktop** corriendo, con integración WSL activada. Ver `docs/ARRANQUE.md`.
- **kubectl 1.24 o superior.** Los manifiestos usan los campos `labels:` y
  `patches:` de kustomize, que necesitan la versión embebida en kubectl 1.24+.

      winget install -e --id Kubernetes.kubectl
      kubectl version --client

- **k3d.** En Windows está en winget:

      winget install -e --id k3d.k3d

  Cerrá PowerShell y volvé a abrirlo para que el `PATH` se actualice, después:

      k3d version

## 1. Crear el clúster

**Primero comprobá que Docker responde.** k3d levanta los nodos como
contenedores: si el motor no está arriba, la creación falla con
`open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`
y después `kubectl` intenta hablar con `localhost:8080` y encadena errores que
parecen otro problema.

```powershell
docker version
```

Tienen que aparecer **dos** bloques, `Client` y `Server`. Si solo sale `Client`,
abrí Docker Desktop y esperá a que diga **Engine running**.

```powershell
k3d cluster create geoguardian --agents 1 --api-port 127.0.0.1:6445
kubectl cluster-info
kubectl get nodes
```

> **Por qué `--api-port 127.0.0.1:6445`.** Sin ese parámetro, k3d escribe la
> dirección del servidor de la API como `https://host.docker.internal:<puerto>`.
> En una máquina con VPN o con varias interfaces de red, ese nombre resuelve a
> una dirección que no responde y `kubectl` falla aunque el clúster esté sano.
> Ver incidencia **I-03**. Si ya creaste el clúster sin el parámetro, no hace
> falta borrarlo:
>
>     kubectl config view --minify -o jsonpath="{.clusters[0].cluster.server}"
>     kubectl config set-cluster k3d-geoguardian --server=https://127.0.0.1:<puerto>

El clúster trae el aprovisionador `local-path`, que resuelve los `PersistentVolumeClaim`
sin configurar almacenamiento aparte.

## 2. Crear el Secret en cada entorno

**Esto no se versiona y no se automatiza.** Un `Secret` de Kubernetes está
codificado en base64, no cifrado: si el manifiesto se sube con el valor adentro,
la credencial queda en el repositorio igual que si estuviera en texto plano.

Primero los namespaces, después el Secret en cada uno:

```powershell
kubectl apply -f local\desarrollo\namespace.yaml
kubectl apply -f local\pruebas\namespace.yaml
kubectl apply -f local\produccion\namespace.yaml

foreach ($ns in "geoguardian-desarrollo","geoguardian-pruebas","geoguardian-produccion") {
    $pw = Read-Host "Contrasena para $ns" -AsSecureString
    $plano = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($pw))
    kubectl create secret generic geoguardian-db `
        --namespace $ns `
        --from-literal=POSTGRES_USER=geoguardian `
        --from-literal=POSTGRES_PASSWORD=$plano
}
Remove-Variable pw, plano
```

> `-AsSecureString` evita que la contraseña quede escrita en pantalla mientras
> la tecleás. Sin eso queda a la vista de cualquiera que mire el terminal o una
> captura.

Comprobá que existen, sin imprimir los valores. No se puede pedir un recurso por
nombre a través de todos los namespaces, hay que usar un selector de campo:

```powershell
kubectl get secret --all-namespaces --field-selector metadata.name=geoguardian-db
```

## 3. Aplicar los tres entornos

Revisar antes de aplicar. `kustomize build` no toca el clúster:

```powershell
kubectl kustomize local\desarrollo
```

Si el resultado se ve bien:

```powershell
kubectl apply -k local\desarrollo
kubectl apply -k local\pruebas
kubectl apply -k local\produccion
```

## 4. Comprobar que funciona

```powershell
kubectl get pods --all-namespaces -l app.kubernetes.io/part-of=geoguardian
kubectl get pvc --all-namespaces
```

Los tres pods tienen que llegar a `Running` con `1/1` listo. La primera arrancada
corre `initdb` y tarda: dale un par de minutos antes de preocuparte.

Que PostGIS responde y que los cuatro esquemas se crearon:

```powershell
kubectl exec -n geoguardian-desarrollo postgis-0 -- psql -U geoguardian -d geoguardian -c "SELECT postgis_version();"
kubectl exec -n geoguardian-desarrollo postgis-0 -- psql -U geoguardian -d geoguardian -c "\dn"
```

El segundo comando tiene que listar `analitico`, `control`, `crudo` y `geo`.

Para conectarse desde la máquina, por ejemplo con DBeaver o pgAdmin:

```powershell
kubectl port-forward -n geoguardian-desarrollo svc/postgis 15432:5432
```

Y apuntar a `localhost:15432`. Se usa un puerto distinto del 5432 a propósito,
para no chocar con el contenedor de `docker compose`.

## Si algo falla

| Síntoma | Qué mirar |
|---|---|
| Pod en `CrashLoopBackOff` | `kubectl logs -n <ns> postgis-0`. Si dice `invalid locale name`, es la incidencia I-02 |
| Pod en `Pending` | `kubectl describe pod -n <ns> postgis-0`. Casi siempre es el PVC sin aprovisionar |
| `CreateContainerConfigError` | Falta el Secret `geoguardian-db` en ese namespace. Volver al paso 2 |
| `initdb: directory not empty` | El PVC llegó con `lost+found`. Por eso `PGDATA` apunta a un subdirectorio; si aparece, revisar que la variable siga puesta |
| `kubectl kustomize` no reconoce `patches` | kubectl viejo. Hace falta 1.24 o superior |
| `kubectl` no conecta pero el clúster existe | El kubeconfig apunta a `host.docker.internal`. Ver I-03 y el recuadro del paso 1 |

## Borrar todo

```powershell
k3d cluster delete geoguardian
```

Borra el clúster, los tres namespaces, los volúmenes y los Secret. **Los datos
no se recuperan.**

## Diferencia con docker-compose

`docker compose` es el entorno de trabajo diario: más rápido de levantar y con
la carpeta de respaldos montada desde el disco. Kubernetes es el entorno de
despliegue que evalúa la rúbrica, y el destino del CD de las historias H11.2 a
H11.4.

Los dos describen la misma base de datos y **tienen que mantenerse
consistentes**. Hay una duplicación conocida: el SQL de extensiones y esquemas
vive en `infra/docker/init-db/01-extensiones.sql` y también, copiado, en
`base/postgis-configmap-init.yaml`. Si se cambia uno, hay que cambiar el otro.
Está anotado en la cabecera del ConfigMap.

## 5. Desplegar la aplicación

Todo lo de arriba deja la infraestructura en pie. Para poner una versión
concreta a correr:

```powershell
bash infra/k8s/desplegar.sh desarrollo
bash infra/k8s/desplegar.sh desarrollo (git rev-parse HEAD)
```

Sin segundo argumento usa `latest`. Con un SHA de 40 caracteres lo convierte a
`sha-<sha>`, que es como los etiqueta H11.1 — se acepta el SHA pelado porque es
lo que sale de `git rev-parse HEAD`.

**Es el mismo guion que corre el flujo de CD**, y eso es deliberado: si el CI y
tu máquina desplegaran por caminos distintos, un CI en verde no diría nada sobre
lo que pasa acá. Ver **D-36**.

El guion espera a que los tres objetos converjan con `kubectl rollout status`.
Sin esa espera, `kubectl apply` devuelve éxito en cuanto la API acepta el objeto
—o sea siempre— y el despliegue diría que funcionó aunque ningún pod arranque.

Después comprobalo:

```powershell
python infra/verificar_cd.py --entorno desarrollo --sha (git rev-parse HEAD)
kubectl -n geoguardian-desarrollo port-forward svc/visor 8080:80
```

### Lo que el CD no hace, y hay que saberlo

**GitHub Actions no despliega a este clúster.** No puede alcanzarlo: corre en la
nube y esto vive detrás de un router doméstico.

El flujo `cd.yml` crea su propio k3d dentro del runner, aplica estos mismos
manifiestos, comprueba que converjan y lo destruye. Demuestra que el despliegue
funciona; **no deja nada corriendo**.

Este clúster se actualiza cuando una persona corre el guion de arriba. La
decisión, con sus alternativas descartadas y lo que se pierde, está en **D-36**.
