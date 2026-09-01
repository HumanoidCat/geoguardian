-- Extension real del canton y reparto de los distritos en celdas de MERRA-2
--
-- Historia: H1.1 (issue #35). Responde a la correccion de Alejandro en el PR #97.
--
-- POR QUE EXISTE
--
-- El documento de criterios de H1.1 afirmaba que el canton mide "unos 22 x 17 km".
-- Ese numero era falso: salia de los rangos con los que contratos/simulados/datos.py
-- genera focos de calor ficticios al azar, no de las geometrias reales. La
-- comprobacion que lo delata es de una linea: 22 x 17 da 363 km2, y el area medida
-- en H1.3 es 669,23 km2. Una caja envolvente no puede tener menos area que el
-- poligono que contiene.
--
-- Este guion obtiene la extension de la base, que es la unica fuente valida, y
-- ademas calcula en que celda de MERRA-2 cae cada distrito.
--
-- SOBRE LA MALLA DE MERRA-2
--
-- CORRECCION IMPORTANTE. La primera version de este guion calculaba la celda con
-- floor((lon+180)/0.625), es decir partiendo el espacio en celdas con borde en el
-- origen. Ese modelo esta MAL para POWER y daba 3 celdas distintas, en
-- contradiccion con la comprobacion empirica, que devolvia valores identicos.
--
-- MERRA-2 no define celdas con borde: define PUNTOS DE MALLA, en longitudes
-- -180 + k*0.625 y latitudes -90 + j*0.5. Una consulta puntual a POWER devuelve
-- el punto de malla MAS CERCANO a la coordenada pedida. El calculo correcto es
-- redondear, no truncar:
--
--     lon_malla = round(lon / 0.625) * 0.625
--     lat_malla = round(lat / 0.5)   * 0.5
--
-- Con el modelo correcto los ocho distritos caen en un unico punto de malla, que
-- es lo que explica que POWER devuelva la misma serie y hasta la misma elevacion
-- para puntos separados 30 km.
--
-- CHIRPS es distinto: es un producto de celdas de 0,05 grados cuyos centros estan
-- en -179,975 + k*0,05. Ahi el indice de celda por truncamiento SI corresponde, y
-- el centro de la celda se obtiene sumando medio paso.
--
-- COMO SE EJECUTA, desde la raiz del repositorio en PowerShell:
--
--   Get-Content basedatos\consultas\extension_y_celdas.sql | docker compose exec -T db psql -U geoguardian -d geoguardian

\echo '=== 1. Extension real del canton, en grados ==='

SELECT ST_XMin(e) AS oeste,
       ST_XMax(e) AS este,
       ST_YMin(e) AS sur,
       ST_YMax(e) AS norte
  FROM (SELECT ST_Extent(geometria) AS e FROM geo.distrito) AS t;

\echo ''
\echo '=== 2. La misma extension en kilometros, y su caja envolvente ==='
\echo 'El area de la caja tiene que ser MAYOR que los 669,23 km2 del canton.'

SELECT round((ST_XMax(e) - ST_XMin(e))::numeric, 6)                        AS ancho_grados,
       round((ST_YMax(e) - ST_YMin(e))::numeric, 6)                        AS alto_grados,
       round((ST_Distance(
                ST_Transform(ST_SetSRID(ST_MakePoint(ST_XMin(e), ST_YMin(e)), 4326), 8908),
                ST_Transform(ST_SetSRID(ST_MakePoint(ST_XMax(e), ST_YMin(e)), 4326), 8908)
              ) / 1000)::numeric, 3)                                       AS ancho_km,
       round((ST_Distance(
                ST_Transform(ST_SetSRID(ST_MakePoint(ST_XMin(e), ST_YMin(e)), 4326), 8908),
                ST_Transform(ST_SetSRID(ST_MakePoint(ST_XMin(e), ST_YMax(e)), 4326), 8908)
              ) / 1000)::numeric, 3)                                       AS alto_km
  FROM (SELECT ST_Extent(geometria) AS e FROM geo.distrito) AS t;

\echo ''
\echo '=== 3. Los cuatro puntos extremos, para repetir el test sobre CHIRPS ==='

SELECT 'suroeste' AS esquina, ST_XMin(e) AS lon, ST_YMin(e) AS lat FROM (SELECT ST_Extent(geometria) AS e FROM geo.distrito) t
UNION ALL
SELECT 'sureste',            ST_XMax(e),        ST_YMin(e) FROM (SELECT ST_Extent(geometria) AS e FROM geo.distrito) t
UNION ALL
SELECT 'noroeste',           ST_XMin(e),        ST_YMax(e) FROM (SELECT ST_Extent(geometria) AS e FROM geo.distrito) t
UNION ALL
SELECT 'noreste',            ST_XMax(e),        ST_YMax(e) FROM (SELECT ST_Extent(geometria) AS e FROM geo.distrito) t;

\echo ''
\echo '=== 4. Punto de cada distrito y a que punto de malla lo lleva cada fuente ==='
\echo 'MERRA-2 redondea al punto de malla mas cercano. CHIRPS es un producto de celdas.'

SELECT codigo,
       nombre,
       round(ST_X(p)::numeric, 6)                                AS lon,
       round(ST_Y(p)::numeric, 6)                                AS lat,
       round((round((ST_X(p) / 0.625)::numeric) * 0.625), 4)     AS merra2_lon,
       round((round((ST_Y(p) / 0.5)::numeric) * 0.5), 4)         AS merra2_lat,
       round((floor((ST_X(p) + 180) / 0.05) * 0.05 - 180 + 0.025)::numeric, 4) AS chirps_lon,
       round((floor((ST_Y(p) + 90)  / 0.05) * 0.05 - 90  + 0.025)::numeric, 4) AS chirps_lat
  FROM (SELECT codigo, nombre, ST_PointOnSurface(geometria) AS p FROM geo.distrito) AS t
 ORDER BY codigo;

\echo ''
\echo '=== 5. Cuantos puntos de malla MERRA-2 distintos tocan los ocho distritos ==='
\echo 'Si da 1, POWER no puede distinguir un distrito de otro.'

SELECT count(*) AS puntos_merra2_distintos
  FROM (
    SELECT DISTINCT round((ST_X(p) / 0.625)::numeric) AS ml,
                    round((ST_Y(p) / 0.5)::numeric)   AS mb
      FROM (SELECT ST_PointOnSurface(geometria) AS p FROM geo.distrito) AS q
  ) AS c;

\echo ''
\echo '=== 6. Cuantas celdas CHIRPS distintas tocan los ocho distritos ==='
\echo 'Referencia previa. La prueba real es consultar CHIRPS y comparar la salida.'

SELECT count(*) AS celdas_chirps_distintas
  FROM (
    SELECT DISTINCT floor((ST_X(p) + 180) / 0.05) AS cl,
                    floor((ST_Y(p) + 90)  / 0.05) AS cb
      FROM (SELECT ST_PointOnSurface(geometria) AS p FROM geo.distrito) AS q
  ) AS c;

\echo ''
\echo '=== 7. Cuantas celdas CHIRPS cubren la superficie completa del canton ==='
\echo 'No solo los ocho puntos representativos, sino toda el area.'

SELECT count(*) AS celdas_chirps_sobre_el_area
  FROM (
    SELECT DISTINCT floor((ST_X((gv).geom) + 180) / 0.05) AS cl,
                    floor((ST_Y((gv).geom) + 90)  / 0.05) AS cb
      FROM (
        SELECT ST_DumpPoints(ST_Segmentize(geometria::geography, 500)::geometry) AS gv
          FROM geo.distrito
      ) AS q
  ) AS c;
