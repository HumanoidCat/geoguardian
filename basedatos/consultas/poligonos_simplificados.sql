-- Simplificacion de los poligonos distritales para consultar CHIRPS
--
-- Historia: H1.1 (issue #35)
--
-- POR QUE HACE FALTA
--
-- ClimateSERV recibe la geometria como parametro de la URL. Los distritos vienen
-- del SNIT a escala 1:5000: Tilaran tiene 24.515 vertices y su GeoJSON pesa
-- 656.448 caracteres. Ni de lejos cabe en una URL.
--
-- Al ir en una cadena de consulta, los corchetes, comas y comillas se codifican,
-- asi que el peso real es alrededor del doble del que se mide aqui. Con un limite
-- habitual de 8 KB, el objetivo es quedar por debajo de unos 3.000 caracteres.
--
-- DOS PALANCAS
--
--   tolerancia   cuanto se puede mover el contorno, en grados
--   decimales    cuantos decimales lleva cada coordenada en el GeoJSON
--
-- La segunda es gratis: a 4 decimales la precision es de unos 11 metros, y la
-- malla de CHIRPS mide 5,5 km. Guardar 6 decimales solo alarga la URL.
--
-- QUE DECIDE LA ELECCION
--
-- No el area perdida, sino **si el conjunto de celdas CHIRPS que toca el poligono
-- sigue siendo el mismo**. Si cambia, el dato saldria de celdas distintas y la
-- serie ya no seria la del distrito. Eso es lo que mide la consulta 2.
--
-- Se usa ST_SimplifyPreserveTopology y no ST_Simplify porque el segundo puede
-- producir poligonos invalidos, y uno roto haria que ClimateSERV devolviera un
-- error dificil de leer.
--
-- COMO SE EJECUTA, desde la raiz del repositorio en PowerShell:
--
--   Get-Content basedatos\consultas\poligonos_simplificados.sql | docker compose exec -T db psql -U geoguardian -d geoguardian

\echo '=== 1. Peso del GeoJSON segun tolerancia y decimales ==='
\echo 'Objetivo: el maximo por debajo de unos 3.000 caracteres.'

WITH opciones AS (
    SELECT * FROM (VALUES (0.001), (0.002), (0.005), (0.010)) AS t(tolerancia)
),
medidas AS (
    SELECT o.tolerancia,
           d.codigo,
           length(ST_AsGeoJSON(ST_SimplifyPreserveTopology(d.geometria, o.tolerancia), 6)) AS c6,
           length(ST_AsGeoJSON(ST_SimplifyPreserveTopology(d.geometria, o.tolerancia), 4)) AS c4,
           ST_NPoints(ST_SimplifyPreserveTopology(d.geometria, o.tolerancia))              AS vertices
      FROM geo.distrito d CROSS JOIN opciones o
)
SELECT tolerancia,
       round((tolerancia * 111000)::numeric, 0) AS metros_aprox,
       max(vertices)                            AS peor_vertices,
       max(c6)                                  AS peor_6_decimales,
       max(c4)                                  AS peor_4_decimales
  FROM medidas
 GROUP BY tolerancia
 ORDER BY tolerancia;

\echo ''
\echo '=== 2. Celdas CHIRPS tocadas, por tolerancia ==='
\echo 'La columna original y cada tolerancia tienen que dar el MISMO numero en los ocho.'

WITH puntos AS (
    SELECT d.codigo, 0.0 AS tolerancia,
           (ST_DumpPoints(ST_Segmentize(d.geometria::geography, 400)::geometry)).geom AS p
      FROM geo.distrito d
    UNION ALL
    SELECT d.codigo, o.tolerancia,
           (ST_DumpPoints(
               ST_Segmentize(
                   ST_SimplifyPreserveTopology(d.geometria, o.tolerancia)::geography, 400
               )::geometry)).geom
      FROM geo.distrito d
      CROSS JOIN (SELECT * FROM (VALUES (0.001), (0.002), (0.005), (0.010)) AS t(tolerancia)) o
),
celdas AS (
    SELECT DISTINCT codigo, tolerancia,
           floor((ST_X(p) + 180) / 0.05) AS cl,
           floor((ST_Y(p) + 90) / 0.05)  AS cb
      FROM puntos
)
SELECT codigo,
       count(*) FILTER (WHERE tolerancia = 0.0)   AS original,
       count(*) FILTER (WHERE tolerancia = 0.001) AS t_0_001,
       count(*) FILTER (WHERE tolerancia = 0.002) AS t_0_002,
       count(*) FILTER (WHERE tolerancia = 0.005) AS t_0_005,
       count(*) FILTER (WHERE tolerancia = 0.010) AS t_0_010
  FROM celdas
 GROUP BY codigo
 ORDER BY codigo;

\echo ''
\echo '=== 3. Validez geometrica en cada tolerancia ==='

SELECT o.tolerancia,
       count(*) FILTER (WHERE NOT ST_IsValid(ST_SimplifyPreserveTopology(d.geometria, o.tolerancia)))
           AS invalidos
  FROM geo.distrito d
  CROSS JOIN (SELECT * FROM (VALUES (0.001), (0.002), (0.005), (0.010)) AS t(tolerancia)) o
 GROUP BY o.tolerancia
 ORDER BY o.tolerancia;

\echo ''
\echo '=== 4. Area perdida en cada tolerancia ==='
\echo 'Referencia. Lo que decide es el conteo de celdas de la consulta 2.'

SELECT o.tolerancia,
       round(max(abs(ST_Area(ST_Transform(d.geometria, 8908))
                     - ST_Area(ST_Transform(ST_SimplifyPreserveTopology(d.geometria, o.tolerancia), 8908)))
                 / ST_Area(ST_Transform(d.geometria, 8908)) * 100)::numeric, 4) AS peor_diferencia_pct
  FROM geo.distrito d
  CROSS JOIN (SELECT * FROM (VALUES (0.001), (0.002), (0.005), (0.010)) AS t(tolerancia)) o
 GROUP BY o.tolerancia
 ORDER BY o.tolerancia;
