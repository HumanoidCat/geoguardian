-- 011 · Indices espaciales y compuestos
--
-- Historia: H1.12 (issue #44) · Rubrica: BD-1
--
-- ===========================================================================
-- CADA INDICE DE AQUI SE MIDIO ANTES DE ESCRIBIRSE
-- ===========================================================================
--
-- `basedatos/medir_indices.py` corre cada candidato contra la base real: mide
-- la consulta sin el, lo crea, vuelve a medir, y **mira si el planificador lo
-- eligio**. Todo dentro de una transaccion que se revierte, asi que la
-- herramienta no decide nada: decide esta migracion, con sus numeros a la vista.
--
--   indice                        sin       con     cambio   lo usa
--   riesgo_fecha_evento_ix     13.08 ms   0.14 ms   -98.9 %    si     ACEPTA
--   foco_distrito_fecha_ix      2.61 ms   0.19 ms   -92.8 %    si     ACEPTA
--   distrito_geometria_gix          -         -         -       -     ver abajo
--   medicion_fecha_ix           0.29 ms   0.27 ms    -8.3 %    NO     DESCARTA
--
-- UN INDICE QUE NO SE USA ES PEOR QUE NO TENERLO: cuesta espacio, cuesta en
-- cada escritura del ETL, y no devuelve nada. Por eso el cuarto candidato no
-- esta en esta migracion.
--
-- EL PUNTO DE PARTIDA
--
-- Antes de esta historia el esquema tenia **un solo indice secundario** en todo
-- el proyecto. Todo lo demas se apoyaba en los indices que PostgreSQL crea para
-- las claves primarias, y las tres consultas de abajo no empiezan por la primera
-- columna de la suya.

-- --------------------------------------------------------------------------- #
-- 1. El riesgo por fecha y evento — lo que pide el visor                       #
-- --------------------------------------------------------------------------- #
--
-- `obtener_riesgos_por_fecha(fecha, tipo_evento)` alimenta las coropletas. La
-- clave primaria es `(codigo_distrito, fecha, tipo_evento)` y la consulta **no
-- filtra por la primera columna**, asi que el indice de la clave no puede
-- usarse: le falta la columna guia. El plan era un `Seq Scan` sobre la tabla
-- entera.
--
-- POR QUE `INCLUDE` Y NO CUATRO COLUMNAS EN LA CLAVE
--
-- `codigo_distrito` y `nivel` no se filtran, se devuelven. Ponerlos en el cuerpo
-- del indice los haria parte del orden y del arbol -mas grande, mas caro de
-- mantener- sin que ninguna consulta los aproveche para buscar. Con `INCLUDE`
-- viajan como carga y permiten un **Index Only Scan**: la consulta se responde
-- sin tocar la tabla.
--
-- POR QUE SE ACEPTA AUNQUE HOY AHORRE POCO
--
-- Se midio a cuatro tamanos, y el ahorro crece linealmente mientras la consulta
-- indexada se queda plana:
--
--     17 544 filas    0,56 -> 0,07 ms     8,5x
--     52 584 filas    2,56 -> 0,11 ms    23,0x
--    122 664 filas    6,03 -> 0,10 ms    57,4x
--    262 824 filas   10,20 -> 0,11 ms    90,6x
--
-- `analitico.riesgo` suma 24 filas por dia -8 distritos por 3 eventos- para
-- siempre. **El numero de hoy es el mas pequeno que va a tener nunca.**
CREATE INDEX IF NOT EXISTS riesgo_fecha_evento_ix
    ON analitico.riesgo (fecha, tipo_evento)
    INCLUDE (codigo_distrito, nivel);

COMMENT ON INDEX analitico.riesgo_fecha_evento_ix IS
    'Para obtener_riesgos_por_fecha. La clave primaria empieza por codigo_distrito y esa consulta no lo filtra. INCLUDE permite Index Only Scan.';

-- --------------------------------------------------------------------------- #
-- 2. Los focos por distrito y rango — lo que cuenta el etiquetado              #
-- --------------------------------------------------------------------------- #
--
-- `SQL_CONTAR_FOCOS` filtra por `(codigo_distrito, fecha BETWEEN ...)`. La clave
-- primaria de `crudo.foco_calor` es
-- `(producto, satelite, fecha, hora_utc, latitud, longitud)`: **`codigo_distrito`
-- no aparece en ella**, asi que no habia forma de que ayudara.
--
-- El orden de las columnas importa: `codigo_distrito` va primero porque se
-- compara por igualdad y `fecha` por rango. Al reves, el indice tendria que
-- recorrer todo el rango de fechas de los ocho distritos.
CREATE INDEX IF NOT EXISTS foco_distrito_fecha_ix
    ON crudo.foco_calor (codigo_distrito, fecha);

COMMENT ON INDEX crudo.foco_distrito_fecha_ix IS
    'Para contar focos por distrito y rango. codigo_distrito primero: se compara por igualdad, y fecha por rango.';

-- --------------------------------------------------------------------------- #
-- 3. El indice espacial                                                        #
-- --------------------------------------------------------------------------- #
--
-- `cargar_focos.py` y `guardar_focos` asignan distrito con
-- `ST_Contains(d.geometria, punto)`. Sin GIST, PostgreSQL evalua la geometria
-- **exacta** de los ocho distritos por cada punto. Con el, la caja envolvente
-- descarta siete antes de llegar a la prueba cara.
--
-- SU NUMERO NO ESTA EN LA TABLA DE ARRIBA, Y HAY QUE DECIR POR QUE
--
-- El entorno donde se midieron los otros tres no tiene PostGIS, asi que
-- `ST_MakePoint` no existe y el candidato **quedo sin medir**. El banco lo
-- reporta como «SIN MEDIR», no como descartado: son cosas distintas y
-- confundirlas haria que un entorno incompleto se leyera como un veredicto.
--
-- Se crea igual, y el criterio 5 del verificador comprueba **contra la base con
-- PostGIS** que el planificador lo elige. Si alli no lo eligiera, este indice
-- sale de la migracion: la regla no cambia por ser el que da nombre a la
-- historia.
CREATE INDEX IF NOT EXISTS distrito_geometria_gix
    ON geo.distrito USING GIST (geometria);

COMMENT ON INDEX geo.distrito_geometria_gix IS
    'Para ST_Contains al asignar distrito a cada foco. Sin el, se evalua la geometria exacta de los ocho distritos por punto.';

-- --------------------------------------------------------------------------- #
-- LO QUE NO SE CREA, Y POR QUE                                                  #
-- --------------------------------------------------------------------------- #
--
-- `medicion_fecha_ix` -un btree sobre `crudo.medicion_diaria (fecha)`- **se
-- midio y se descarto**. El planificador no lo elige: desde H1.11 la tabla esta
-- particionada por anio y la poda ya reduce la busqueda antes de tocar dato.
--
-- Se predijo antes de medir que iba a ser asi, y quedo escrito en el banco como
-- `esperado="sin efecto"`. Se midio igual, porque una prediccion sin comprobar
-- es una opinion.
--
-- Lo interesante es que la consulta **si** fue un 8 % mas rapida con el indice
-- creado. Sin mirar el plan, ese 8 % habria bastado para justificarlo. Mirando
-- el plan, el indice no aparece: el 8 % es ruido y cache. **Es el motivo por el
-- que el banco comprueba el plan y no solo el reloj.**

-- --------------------------------------------------------------------------- #
-- Estadisticas                                                                 #
-- --------------------------------------------------------------------------- #
--
-- Un indice recien creado sin `ANALYZE` puede no usarse: el planificador decide
-- con estadisticas, y las de la tabla no saben todavia que el indice existe.
ANALYZE analitico.riesgo;
ANALYZE crudo.foco_calor;
ANALYZE geo.distrito;
