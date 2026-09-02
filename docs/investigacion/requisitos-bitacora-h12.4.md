# Qué necesita H12.4 de `control.bitacora_etl`

**Autor.** Luna, desde H12.4 · **Para.** César, que implementa H12.1
**Fecha.** 2026-09-01

---

## Por qué este documento existe

**H12.4 consume lo que H12.1 produce.** El diagnóstico guiado lee la bitácora y
propone qué mirar; si la bitácora no guarda algo, el diagnóstico no lo puede
decir, y para entonces la tabla ya está creada y migrada.

Decirlo ahora cuesta una hora. Decirlo después cuesta una migración correctiva,
que es lo que pasó con `007_riesgo_correcciones.sql`.

**No es una lista de exigencias.** Es lo que necesito para que H12.4 sirva; si
algo no se puede o no tiene sentido, decímelo y lo ajusto de mi lado.

## Qué hace H12.4, en una frase

Dada una corrida que falló, **decir qué mirar primero** y por qué. No arregla
nada y no reintenta nada.

Tres preguntas que tiene que poder responder:

1. **Qué falló**, y si es un fallo de dato, de red o de configuración.
2. **Dónde**, con la precisión suficiente para reproducirlo.
3. **Si ya nos pasó antes**, cruzando contra las incidencias `I-XX` de
   `docs/04-bitacora-incidencias.md`.

Y una que importa tanto como las otras tres: **poder decir "no sé"**. Un
diagnóstico que siempre produce una respuesta no sirve, por la misma razón por
la que `obtener_riesgo` devuelve `None` en vez de inventar un riesgo.

## La frontera con `control.fallo`, que ya existe

H1.9 creó `control.fallo` y está bien: guarda **filas rechazadas** dentro de una
carga por lotes, con su `sqlstate`, su `detalle` y los datos de la fila.

`control.bitacora_etl` es otra granularidad: guarda **corridas**, no filas.

| | `control.fallo` | `control.bitacora_etl` |
|---|---|---|
| Unidad | Una fila rechazada | Una ejecución completa |
| Cuántas por corrida | De cero a miles | Exactamente una |
| Responde | Por qué se rechazó *esta* fila | Qué pasó con *la corrida* |
| Existe | Sí, desde H1.9 | No |

Están tan cerca que sin esta frontera escrita H12.1 puede terminar duplicando
H1.9. Con ella, se complementan.

### Y de ahí sale lo más importante que tengo que pedirte

**`control.fallo` no tiene forma de saber a qué corrida pertenece.** Sus
columnas son `id`, `origen`, `sqlstate`, `mensaje`, `detalle`, `contexto`,
`datos`, `ocurrido_en` y `reportado_por`. Ninguna identifica la ejecución.

Para diagnosticar "la carga de anoche rechazó 340 filas, todas con SQLSTATE
23514", H12.4 tendría que **correlacionar por ventana de tiempo**, y eso falla
en cuanto dos corridas se solapan o alguien reejecuta.

**Lo que pido: una columna `corrida_id` en `control.fallo`, con clave foránea a
`control.bitacora_etl`.** Es la diferencia entre un diagnóstico que afirma y uno
que adivina.

Es tu tabla y tu decisión. Si preferís resolverlo de otra forma, con que quede
alguna manera fiable de unir una fila rechazada con su corrida, me sirve igual.

## Campos que H12.4 necesita leer

Ordenados por lo que dejan de poderse responder si faltan.

### Imprescindibles

| Campo | Para qué |
|---|---|
| `id` | Identificar la corrida y unirla con `control.fallo` |
| `proceso` | Qué se ejecutó: `cargar_mediciones`, `cargar_focos`, `cargar_distritos`. Texto y no enum, por lo mismo que `control.fallo.origen` |
| `iniciado_en` | Ordenar y acotar la ventana |
| `estado` | `en_curso`, `exito`, `fallo`, `parcial`. Ver la nota de abajo sobre `en_curso` |

### Muy útiles

| Campo | Para qué |
|---|---|
| `terminado_en` | Duración. Una corrida que tarda el triple de lo normal es un síntoma antes de ser un fallo |
| `filas_leidas` y `filas_escritas` | La diferencia entre las dos, contra `control.fallo`, dice si el rechazo fue masivo o puntual |
| `sqlstate` | Si terminó en fallo. Por la misma razón que en `control.fallo`: **el mensaje cambia con el idioma del servidor y el código no** |
| `parametros` (`jsonb`) | Ventana de fechas, distritos pedidos. Sin esto no se puede reproducir |
| `fuente` | CHIRPS, POWER, FIRMS, SNIT. Un fallo de red se agrupa por fuente, no por proceso |

### Si no cuestan mucho

| Campo | Para qué |
|---|---|
| `version_codigo` | El SHA del commit. Permite decir "esto empezó a fallar con tal cambio", que es la mitad de un diagnóstico |
| `reportado_por` | Igual que en `control.fallo` |

## Dos cosas de diseño que pido, y el motivo

### 1. Escribir la fila al **empezar**, no al terminar

Si la fila se escribe solo al final, **una corrida que muere a la mitad no deja
rastro**, y se vuelve indistinguible de una que nunca arrancó.

Eso no es hipotético en este proyecto. El propio `backend/etl/bitacora.py`
existe porque una corrida de tres minutos murió y el búfer de la tubería se
perdió entero, sin dejar por qué. Su docstring lo cuenta.

Lo que propongo: insertar con `estado = 'en_curso'` al arrancar y actualizar al
terminar. Una corrida que quedó en `en_curso` con `iniciado_en` de hace seis
horas **es un diagnóstico en sí misma**: el proceso murió.

Es la misma distinción que atraviesa el proyecto entero: **ausencia de registro
no es ausencia de evento.**

### 2. `parcial` tiene que existir como estado

Una carga que escribió seis distritos de ocho y falló en el séptimo no es
`exito` ni es `fallo`. Si se la marca como fallo, quien vaya a reintentar va a
recargar los seis que ya estaban; si se la marca como éxito, dos distritos
quedan sin dato y nadie se entera.

## Lo que H12.4 **no** va a hacer

Lo escribo para que no se espere de la bitácora algo que no tiene que dar.

- **No reintenta nada.** Propone qué mirar; ejecutar es de una persona.
- **No guarda la sentencia SQL.** Por el mismo motivo que `control.fallo` no la
  guarda: invitaría a reintentarla a ciegas.
- **No inventa un diagnóstico.** Si la corrida no coincide con ningún patrón
  conocido, dice eso y muestra los datos crudos.
- **No clasifica por el mensaje de error.** Solo por `sqlstate` y por la forma
  de la corrida. El mensaje se muestra, no se interpreta.

## Preguntas abiertas para vos

1. **¿`corrida_id` en `control.fallo` te complica?** Es lo único que pido que
   toque algo ya hecho.
2. **¿La aplicación escribe en la misma tabla que el pipeline?** El título de
   H12.1 dice "logs de pipeline **y aplicación**". Si van juntos, `proceso`
   necesita distinguirlos; si van en tablas distintas, H12.4 lee las dos.
3. **¿Quién escribe la fila, Python o una función PL/pgSQL?** Si es PL/pgSQL,
   igual que `registrar_riesgo`, hereda la garantía de que se escribe en la
   misma transacción. Si es Python, una caída del proceso deja la fila en
   `en_curso`, que es justo lo que queremos.

## Una propuesta para trabajar en paralelo

**Si te parece, defino el contrato de lectura y construyo H12.4 contra un
simulado**, igual que hicimos con `Repositorio` y `ProcesadorSenales`.

Eso significa que H12.4 se escribe y se prueba **sin esperar a que exista la
tabla**, y cuando H12.1 entre se enchufa. Si la implementación real cumple el
contrato, no hay ajuste; si no lo cumple, la prueba del contrato lo dice el
primer día en vez de al integrar.

Es el patrón que el proyecto usa en todos lados y funcionó: las 57 pruebas de
H10.2 se escribieron contra simulados y detectaron cuatro invariantes que ningún
doble podía demostrar.

**Requiere agregar un `Protocol` a `contratos/`**, que no es mi carpeta, así que
va como solicitud de cambio y no lo hago por mi cuenta. Lo redacto si vos y
Alejandro están de acuerdo.

Y si preferís que espere a que la tabla exista, también está bien. Lo digo
porque a esta altura del trimestre trabajar en paralelo vale más que trabajar en
orden.
