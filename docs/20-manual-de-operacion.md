# Manual de operacion · GeoGuardian

**Historia.** H13.2 · **Autora.** Avril Madrigal Elizondo · **Fecha.** 2026-09-05

---

## Que es este manual, y que no

> **El runbook dice como montarlo. Este manual dice como atenderlo.**
> Instalar es una vez; operar es todos los dias.

| Si necesitas… | Va en |
|---|---|
| Publicar el sistema en Railway desde cero | `docs/19-runbook-railway.md` |
| Levantarlo en tu maquina para desarrollar | `docs/ARRANQUE.md` |
| Entender como esta construido | `docs/10-manual-tecnico.md` |
| **Saber si esta bien, y que hacer si no** | **este documento** |
| Usar el visor | `docs/18-manual-de-usuario.md` |

No se repite aca nada que el runbook ya explique. Cuando un procedimiento vive
alla, se enlaza en vez de copiarse: **dos copias del mismo dato se desfasan**, y
este proyecto ya perdio tiempo con eso — **I-07**, «una cifra derivada escrita a
mano rompia el CI de quien no la toco», y las cifras del anexo IEEE, que fue lo
que hizo nacer a `verificar_documentacion.py`.

---

## 1 · Los dos entornos, y cual es cual

Hay **dos** sistemas corriendo, y confundirlos es el primer error posible.

| | Railway | k3d local |
|---|---|---|
| **Que es** | El despliegue **publico**. Lo que se ve en la defensa | Tres entornos de D-05 en una maquina del equipo |
| **Historia** | H11.6 | H11.2 a H11.4 |
| **Quien llega** | Cualquiera, por el dominio del visor | Solo quien tenga la maquina |
| **Como se monta** | `docs/19-runbook-railway.md` | los manifiestos de `infra/` |
| **Respaldos** | **Ninguno automatico.** Plan Hobby | — |

**Cual de los dos importa depende de para quien.** **D-43** lo deja escrito:

> H11.2, H11.3 y H11.4 no cambian. Siguen desplegando a k3d desde `ghcr.io` por
> SHA, **que es lo que evalua la rubrica de Arquitectura**. […] El sitio publico
> es una demostracion, no la infraestructura evaluada.

O sea: **Railway es el que esta vivo y el que se ve; k3d es el que se califica.**
Un manual que tratara a k3d como secundario dejaria sin documentar justo el
despliegue que se evalua.

**Un solo dominio publico, el del visor.** La API no se expone: el navegador
nunca le habla directo, por **D-23**. Si algun dia `api` o `postgis` aparecen con
dominio publico, eso **es** el incidente, aunque nada se haya caido.

### Y una consecuencia de D-43 que hay que tener presente al operar

**El binario que corre en el sitio publico no es el que el CI construyo y probo.**
Railway reconstruye desde el arbol del repositorio; el arbol es el mismo, la
construccion no. D-43 lo acepta a proposito y lo escribe sin disimularlo.

Para quien opera, la consecuencia es concreta: **un CI en verde no dice que lo
publicado funcione.** Lo que acota esa perdida es comparar versiones —y por eso
`version_api` y `version_contratos` estan en la comprobacion diaria de la seccion
2—: si no coinciden con lo que declara el arbol, se desplego otro arbol, que es el
error que importa.

---

## 2 · La comprobacion diaria

> **Este procedimiento esta escrito, no ejecutado contra produccion.**
>
> Sale del contrato de `Salud` en `contratos/esquemas.py`, de `backend/api/rutas.py`
> y del paso 7 del runbook, que son fuentes fiables. Pero **H11.6 —la historia que
> publico el sistema— sigue abierta**: su evidencia trae los CA contra el sitio
> marcados `(pendiente)`, y el costo se mide el 2026-09-07.
>
> Se dice aca en vez de presentarlo como verificado. Un manual de operacion que
> afirma haber probado lo que no probo es el mismo defecto que este documento
> enseña a detectar: **una fuente que informa sobre si misma.**
>
> Cuando H11.6 cierre sus CA contra el sitio, esta nota se cae y en su lugar va la
> salida real.

Toma un minuto y responde la unica pregunta que importa: **¿esta sirviendo?**

```
1.  Abrir  https://<dominio del visor>/api/salud
2.  Leer:  modo   y   version_contratos
           -NO base_datos_conectada ni ultima_ingesta: ver abajo por que-
3.  Abrir el visor y hacer clic en un distrito
```

### Que aspecto tiene «normal»

`Salud` tiene **cinco** campos (`contratos/esquemas.py`), y desde el 2026-09-05
**los cinco informan**:

| Campo | Normal | Que significa si no |
|---|---|---|
| `modo` | `real` | `simulado` = la API **no llego a PostgreSQL** y esta sirviendo el repositorio de relleno |
| `version_contratos` | la de `contratos/__init__.py` (**hoy `1.4.0`**) | una version vieja = lo publicado no es lo que esta en `dev` |
| `version_api` | acompaña a la anterior | idem |
| `base_datos_conectada` | `true` | `false` con `modo: real` es **contradictorio**: ver el triaje |
| `ultima_ingesta` | una fecha reciente | `null` = nunca se ejecuto la ingesta |
| El visor | pinta los ocho distritos | ver el triaje |

**Ninguno de los tres primeros se escribe a mano: los tres se le preguntan a la
implementacion que contesto.** Si `modo` dice `simulado`, no hay variable que
forzar: hay una conexion que arreglar.

> **Esto cambio el 2026-09-05, y conviene saber por que.**
>
> Hasta ese dia `rutas.py` devolvia `base_datos_conectada=False` y
> `ultima_ingesta=None` **escritos en duro**. Eran ciertos el 2026-08-13, cuando
> H6.1 no abria conexion; H6.2 la trajo y las constantes sobrevivieron nueve dias,
> porque ningun criterio preguntaba por ellas con el repositorio real.
>
> Es **I-41**, y esta corregida: los tres campos se derivan, y CA-7 de
> `verificar_h61.py` ahora si pregunta.
>
> Se cuenta aca porque **la version anterior de este manual decia que esos dos
> campos «no informan»**, y era cierto cuando se escribio. Un manual tambien
> caduca.

### Por que se pide y no se mira una consola

**Es la leccion de I-39, y es la regla central de este manual.**

Durante dos horas Railway mostro `Online` y `Deployment successful` mientras el
contenedor del visor arrancaba, moria y reiniciaba **una vez por segundo**. La
consola decia la verdad sobre si misma —el contenedor existia— y nada sobre el
sistema.

> **La unica comprobacion de que un servicio publicado funciona es pedirle algo y
> mirar lo que contesta.**

---

## 3 · Triaje · sintoma, causa, accion

Esta tabla sale de incidencias reales del proyecto, no de casos imaginados. Cada
fila enlaza la suya.

### El visor no carga o devuelve 502

| Que ver | Causa probable | Que hacer |
|---|---|---|
| `{"status":"error","code":502,"message":"Application failed to respond"}` **y** la consola dice `Online` | El contenedor esta en ciclo de reinicio. **I-39** | Mirar los **registros de despliegue**, no el estado. Un error repetido una vez por segundo es el ciclo |
| En los registros: `nginx: [emerg] invalid port in resolver` | Una direccion IPv6 sin corchetes. **I-39**, arreglado | Confirmar que `10-resolver.sh` esta al dia |
| nginx dice `start worker process` y aun asi 502 | nginx escucha solo IPv4 y la red es IPv6. **I-39**, segunda parte | Confirmar que `nginx.conf.template` tiene `listen [::]:80` |

### El visor carga pero los datos estan mal

| Que ver | Causa probable | Que hacer |
|---|---|---|
| El aviso de **datos de demostracion** en pantalla | `modo = simulado`: la API no alcanzo la base | Pedir `/api/salud`. Con `base_datos_conectada: false`, revisar las variables del servicio `api` en Railway |
| Todos los distritos con trama de «sin estimacion» | No hay filas en `analitico.riesgo` para esa fecha | `python docs/herramientas/contar_riesgo.py` |
| `modo: real` pero `base_datos_conectada: false` | **Contradiccion real.** Desde I-41 los dos se derivan, asi que ya no puede ser un valor viejo | Es un incidente: dos preguntas al mismo proceso dan respuestas incompatibles. Registrarlo antes de tocar nada |

### Se fusiono algo y no llego

| Que ver | Causa probable | Que hacer |
|---|---|---|
| El codigo esta en `dev` y el sitio no cambia | **La base publicada no se actualiza sola** | Ver «Cuando entra una migracion nueva» en el runbook |
| El CI paso pero el defecto llego igual | **I-25**: habia verificaciones que corrian **y salian en rojo** sin impedir la fusion | Comprobar que la proteccion de `dev` siga exigiendo **cinco** verificaciones obligatorias, no tres. **Agregar un trabajo a `ci.yml` no lo inscribe en esa lista** |

### La regla que atraviesa las tres

**I-25, I-41 e I-39 son el mismo defecto tres veces:** un indicador que informa
**sobre si mismo** en vez de sobre el sistema.

- Una verificacion que corre y no bloquea informa de que corrio.
- Un campo escrito a mano informa de lo que alguien creyo en agosto.
- Un `Online` informa de que el contenedor existe.

Las tres estan corregidas. **El patron no**, porque no es un error de nadie: es lo
que pasa cuando el sitio donde se declara algo y el sitio donde se comprueba son
dos, y nada los compara. Por eso la regla se queda aunque las incidencias cierren.

**Ante cualquier duda, la pregunta no es «que dice el panel» sino «que contesta si
le pido algo».**

---

## 4 · Tareas de rutina

### Cuando entra una migracion nueva

No se hace desde aca: el procedimiento vive en el runbook, seccion «Cuando entra
una migracion nueva al repositorio». **La base publicada no se actualiza sola.**

### Recargar los datos

`infra/cargar_datos.py`, con las variables de sesion que el runbook explica. Es
tambien el procedimiento de restauracion; ver mas abajo.

### Cerrar la puerta despues de cargar

**Quitar el TCP proxy de `postgis`.** Mientras esta puesto, hay una base expuesta
a Internet. Es el paso 8 del runbook y el que mas facil se olvida, porque el
sistema funciona igual con la puerta abierta.

---

## 5 · Restauracion

**El plan Hobby no tiene respaldos automaticos.** Eso no es un descuido: esta
declarado y tiene una respuesta.

> El respaldo real es que el esquema se reconstruye con `aplicar_migraciones` y
> los datos se vuelven a copiar con `cargar_datos`. **El runbook es el
> procedimiento de restauracion, y por eso esta versionado.**

En claro: **lo que se restaura no es una copia, es el procedimiento.** Si la base
publicada se pierde, no se busca un respaldo —no existe—: se vuelve a ejecutar el
runbook desde el paso 2.

### Y los datos crudos, ¿de donde salen?

`datos/` esta en `.gitignore` y cada quien tiene lo suyo, asi que **no sale del
arbol del repositorio**. Sale de otro lado, y esto ya esta resuelto: **H1.7,
cerrada el 2026-08-27**.

  * El dataset consolidado **se publica como *release asset***, fuera del arbol.
    Lo decide **D-29**, y la razon es que 102 272 filas por commit dejan el
    repositorio sin poder revisarse.
  * `basedatos/ddl/manifiesto-dataset.md` **no contiene el dataset: lo describe**,
    con el conteo por tabla y un **sha256 por tabla**.

Para quien opera, la consecuencia practica:

> **Despues de recargar, comparar contra el manifiesto.** Si el sha256 no coincide,
> la copia que se cargo no es la misma que la del manifiesto — y eso se sabe antes
> de que alguien lo note en un mapa, no despues.

El manifiesto es v1, del 2026-08-27, y declara `crudo.medicion_diaria` con
**102 272** filas y `crudo.foco_calor` con **494**, de las cuales **242 caen dentro
del canton**. Si la base publicada da otra cosa, la carga quedo a medias.

---

## 6 · Consumo, y que hacer cuando no cierre

El plan Hobby son **$5/mes** que incluyen $5 de consumo; pasarse se cobra aparte.
**Tres servicios encendidos las 24 horas con $5 es ajustado**, y el CA-9 de H11.6
lo mide **a las 48 horas**, no el dia de la entrega.

Si no cierra, hay dos salidas declaradas:

1. **Apagar servicios fuera de horario.**
2. **Dejar solo base y API**, y que el visor siga en GitHub Pages. Eso obligaria a
   CORS y a tocar `backend/api/`, que es carpeta de Cesar, con solicitud de cambio.

**Y hay una tercera que no es salida sino red de seguridad:** el visor de GitHub
Pages **no se toca**. Si Railway se apaga, la defensa sigue teniendo un sitio en
pie que declara sus datos como simulados.

---

## 7 · Lo que no hay que hacer

Esta lista vive en el runbook y no se copia. Se repiten aca solo las dos que un
operador puede romper **sin estar instalando nada**:

- **No generarle dominio publico a `api` ni a `postgis`.** Rompe el modelo de un
  solo origen de D-23 y expone la base.
- **No borrar `frontend/public/simulados/`.** Son la degradacion que exige la
  Definition of Done de H6.6, y el respaldo si Railway cae. El runbook lo escribe
  como `simulados/*.json`; **la carpeta tiene ademas `distritos.geojson`**, que
  ese patron no toma y sin el cual el visor de respaldo no dibuja nada.

Y una que es de operacion pura:

- **No forzar `modo` con una variable de entorno.** Si dice `simulado`, es que la
  API no llego a la base. Cambiar la etiqueta no conecta nada y convierte un
  sintoma visible en uno invisible.

---

## 8 · A quien avisar

| Que pasa | Quien |
|---|---|
| El visor no carga o devuelve 502 | Alejandro — `infra/`, Railway, y las variables |
| Los datos estan mal o faltan filas | Cesar — `backend/etl`, `basedatos` |
| El visor carga pero se ve mal | Avril — `frontend/` |
| El CI falla y no se sabe por que | quien sea dueño del verificador que fallo |

**Los valores de las variables de Railway los pone Alejandro en la consola.** En
el repositorio van **nombres**, nunca secretos — es la regla del runbook y no
tiene excepcion.

---

## Lo que este manual no comprueba, y hay que decirlo

Hay que decirlo con precision, porque la mitad ya se resolvio.

**Lo que si se vigila solo, desde el 2026-09-07:** los pipelines. **H12.3** cerro,
y `.github/workflows/alerta.yml` escucha con `workflow_run` cuando CI o CD
terminan; si fallan, `backend/alertas/alertar.py` abre una issue etiquetada
`alerta`, y si vuelven a pasar, la cierra.

**Lo que NO vigila nadie: el sitio publicado.** Esa alerta mira **corridas de
GitHub Actions**, no el dominio. Un CI en verde con el visor caido no dispara
nada — y eso es exactamente I-39, donde el despliegue decia `Deployment
successful` mientras el contenedor moria una vez por segundo.

Asi que la comprobacion de la seccion 2 sigue siendo manual y sigue dependiendo de
que alguien se acuerde. I-39 lo detecto Alejandro *«pidiendo `/api/salud` por
curiosidad»*, dos horas despues de que empezara. **Un procedimiento que depende de
la memoria de una persona es lo que I-10 dejo dicho que no funciona.**

Lo que falta es **H12.2**, la pantalla de monitoreo dentro del visor, abierta.
Mientras no exista, para el sitio publicado esta seccion es toda la vigilancia que
hay.
