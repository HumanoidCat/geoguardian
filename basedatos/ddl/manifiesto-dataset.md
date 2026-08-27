# Manifiesto del dataset consolidado

**Version.** v1
**Fecha de la version.** 2026-08-27
**Historia.** H1.7 - **Decide el como.** D-29

Generado por `basedatos/generar_manifiesto.py`. **No editar a mano.**

Este documento **no contiene el dataset**: lo describe. El archivo
consolidado se publica como *release asset*, fuera del arbol. Lo decide
D-29, y la razon es que 102 272 filas en cada commit dejan el repositorio
sin poder revisarse.

**No lleva marca de tiempo de generacion, a proposito.** Dos corridas con
los mismos argumentos tienen que producir bytes identicos: es la condicion 1
de la seccion Medicion de D-29, y una hora de generacion la rompe.

## Contenido

**Las dos ventanas no son la misma y las dos son ciertas.** *Pedida* es el
rango que se solicito al descargar, declarado en el `procedencia-*.md`
correspondiente. *Observada* es el primer y el ultimo dato que hay en la
base. Difieren cuando la fuente no tuvo nada que entregar en los extremos
del rango, que es el caso de los focos de calor: se pidieron doce meses de
2001 y el primero detectado es de marzo.

| Tabla | Filas | Ventana pedida | Ventana observada |
|---|---|---|---|
| `geo.distrito` | 8 | no aplica | sin columna de fecha |
| `crudo.medicion_diaria` | 102272 | 1991-01-01 a 2025-12-31 | 1991-01-01 a 2025-12-31 |
| `crudo.foco_calor` | 494 | 2001-01-01 a 2024-12-31 | 2001-03-02 a 2024-05-25 |

De los 494 focos de calor, **242 caen dentro del canton** y el
resto fuera, con `codigo_distrito` nulo: la caja de descarga es un rectangulo
y el canton no lo es. Las dos cifras son ciertas y D-29 cita la de adentro.

## Que se hizo con lo que falta

D-22 redujo H1.4 al comprobar que las series climaticas no tienen un solo
faltante en 12 784 dias -CHIRPS y POWER son productos de malla, completos
por construccion- pero **mantuvo la dependencia de H1.7 sobre H1.4**:
versionar el dataset requiere saber que se hizo con lo que falta, aunque hoy
no falte nada. Esta seccion es esa respuesta.

| metodo_imputacion | imputado | Filas |
|---|---|---|
| `sin_imputar` | false | 102272 |

**Ninguna fila fue imputada.** No es que no se haya aplicado la regla: es
que no hubo sobre que aplicarla. Decirlo explicitamente es distinto de
callarlo, y el dia que Sentinel-2 traiga huecos reales -H1.6- la
diferencia entre dos versiones de este manifiesto se va a poder leer.

## Sumas del contenido cargado

Responden si dos copias del dataset son la misma. Dos personas con el mismo
dataset llegan al mismo numero; si difieren, sus copias no son iguales.

| Tabla | sha256 |
|---|---|
| `geo.distrito` | `1ded16b8e78c3954bcb01ed361dd9670e20abc677fa711dca5a1aea420d28eff` |
| `crudo.medicion_diaria` | `7ea356daa115c3087845c7b6546290b64abae8916451c3a7f63eea6fdd645e84` |
| `crudo.foco_calor` | `6c8917625981316261e5ccd22fa91f52bc4bebfe1b78fdb7eebcfe533d496b21` |

### Como se calcula, para que se pueda recalcular

**Se excluye la metadata de carga.** `crudo.medicion_diaria` y
`crudo.foco_calor` declaran `descargado_en timestamptz NOT NULL DEFAULT
now()`. Incluirla haria que dos personas con datos identicos obtuvieran
sumas distintas, porque cada una cargo en otro momento.

Columnas descartadas: descargado_en.

**`geo.distrito`**, 6 columnas:

    codigo, codigo_canton, nombre, area_km2, poblacion, geometria

```sql
SELECT encode(sha256(coalesce(string_agg(h, '' ORDER BY h), '')::bytea), 'hex')
  FROM (SELECT md5(ROW(codigo, codigo_canton, nombre, area_km2, poblacion, geometria)::text) AS h FROM geo.distrito) s
```

**`crudo.medicion_diaria`**, 13 columnas:

    codigo_distrito, fecha, temp_max_c, temp_min_c, temp_media_c, humedad_relativa_pct, viento_ms, radiacion_mj_m2, precipitacion_mm, fuente_precipitacion, fuente_resto, imputado, metodo_imputacion

```sql
SELECT encode(sha256(coalesce(string_agg(h, '' ORDER BY h), '')::bytea), 'hex')
  FROM (SELECT md5(ROW(codigo_distrito, fecha, temp_max_c, temp_min_c, temp_media_c, humedad_relativa_pct, viento_ms, radiacion_mj_m2, precipitacion_mm, fuente_precipitacion, fuente_resto, imputado, metodo_imputacion)::text) AS h FROM crudo.medicion_diaria) s
```

**`crudo.foco_calor`**, 15 columnas:

    producto, satelite, fecha, hora_utc, latitud, longitud, codigo_distrito, confianza, confianza_bruta, brillo_k, brillo_largo_k, banda_origen, frp_mw, tipo, dia_noche

```sql
SELECT encode(sha256(coalesce(string_agg(h, '' ORDER BY h), '')::bytea), 'hex')
  FROM (SELECT md5(ROW(producto, satelite, fecha, hora_utc, latitud, longitud, codigo_distrito, confianza, confianza_bruta, brillo_k, brillo_largo_k, banda_origen, frp_mw, tipo, dia_noche)::text) AS h FROM crudo.foco_calor) s
```

## Suma de la fuente descargada

Responde de donde vino el dato. Es la regla 1 de D-29: el SNIT es la fuente
que ya fallo una vez -I-03- y la que produjo I-10. Si republica su capa,
esta suma cambia y se ve.

Se toma de `basedatos/ddl/procedencia-geometrias.md`, que la calculo sobre
los bytes crudos en el momento de la descarga. **No se recalcula**: pedirle
la capa al SNIT hoy daria la suma de hoy, que es justo lo que se quiere
poder comparar contra esta.

| Capa | sha256 |
|---|---|
| distrital | `853fe38d0d473c2d76d6430cff0857bed41a05faf78033f99ca5f9f76dbbf8c6` |
| cantonal | `cfe1cc0d93dfa88a81326856f5e42ee10f8f7da1e97d6a42cdb41854a2a6be83` |

## Lo que este manifiesto NO afirma

**Que el dato sea correcto.** Prueba que dos personas tienen lo mismo, no
que ese algo este bien. La calidad la mide H1.5.

**Que la base siga en este estado.** El manifiesto es una foto. Cuando el
dataset se recargue hay que regenerarlo, y si alguien recarga y no lo
regenera, **el manifiesto miente**. Hoy no lo comprueba ninguna maquina:
D-29 lo deja anotado como deuda y no es parte de H1.7.

