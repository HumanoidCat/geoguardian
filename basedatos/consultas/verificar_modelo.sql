-- Verificacion del criterio CA-1 de H1.3 (issue #37) · Rubrica BD-1
--
-- QUE DEMUESTRA
--
-- Que el modelo territorial esta en tercera forma normal, mostrando la
-- estructura real que quedo en la base y no la que dice el codigo fuente.
--
-- POR QUE TRES TABLAS
--
-- El codigo de distrito no es opaco. En '50801': 5 es la provincia, 08 el canton
-- y 01 el distrito. Guardar el nombre de la provincia o el del canton dentro de
-- la tabla de distritos los haria depender de una PARTE del codigo y no de la
-- clave completa. Eso es dependencia transitiva y rompe la 3FN.
--
-- Separado en tres tablas, cada nombre se guarda una sola vez.
--
-- COMO SE EJECUTA, desde la raiz del repositorio en PowerShell:
--
--   Get-Content basedatos\consultas\verificar_modelo.sql | docker compose exec -T db psql -U geoguardian -d geoguardian

\echo '=== 1. Tablas del esquema geo ==='

SELECT table_name AS tabla
  FROM information_schema.tables
 WHERE table_schema = 'geo'
 ORDER BY table_name;

\echo ''
\echo '=== 2. Columnas y nulabilidad ==='

SELECT table_name AS tabla,
       ordinal_position AS pos,
       column_name AS columna,
       data_type AS tipo,
       is_nullable AS admite_nulo
  FROM information_schema.columns
 WHERE table_schema = 'geo'
 ORDER BY table_name, ordinal_position;

\echo ''
\echo '=== 3. Claves primarias y foraneas ==='
\echo 'La cadena provincia <- canton <- distrito es lo que evita repetir nombres.'

SELECT tc.table_name        AS tabla,
       tc.constraint_type   AS tipo,
       tc.constraint_name   AS restriccion,
       kcu.column_name      AS columna,
       ccu.table_name       AS referencia_tabla,
       ccu.column_name      AS referencia_columna
  FROM information_schema.table_constraints AS tc
  JOIN information_schema.key_column_usage AS kcu
    ON kcu.constraint_name = tc.constraint_name
   AND kcu.constraint_schema = tc.constraint_schema
  LEFT JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
   AND ccu.constraint_schema = tc.constraint_schema
   AND tc.constraint_type = 'FOREIGN KEY'
 WHERE tc.table_schema = 'geo'
   AND tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE')
 ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name;

\echo ''
\echo '=== 4. Restricciones CHECK declaradas ==='
\echo 'distrito_codigo_canton_ck impide que el codigo y su clave foranea se desincronicen.'

SELECT rel.relname       AS tabla,
       con.conname       AS restriccion,
       pg_get_constraintdef(con.oid) AS definicion
  FROM pg_constraint AS con
  JOIN pg_class      AS rel ON rel.oid = con.conrelid
  JOIN pg_namespace  AS nsp ON nsp.oid = rel.relnamespace
 WHERE nsp.nspname = 'geo'
   AND con.contype = 'c'
   AND con.conname NOT LIKE '%not_null%'
 ORDER BY rel.relname, con.conname;

\echo ''
\echo '=== 5. Prueba de que la clave foranea se aplica ==='
\echo 'Un distrito de un canton inexistente debe ser rechazado.'

BEGIN;
INSERT INTO geo.distrito (codigo, codigo_canton, nombre, area_km2, geometria)
VALUES ('99901', 999, 'Distrito inexistente', 1.0,
        ST_Multi(ST_GeomFromText('POLYGON((-85 10, -84 10, -84 11, -85 10))', 4326)));
COMMIT;

\echo ''
\echo 'El error de arriba es el resultado esperado: la clave foranea rechazo el canton 999.'
\echo 'Nada quedo escrito. Se comprueba a continuacion:'

SELECT count(*) AS filas_en_distrito FROM geo.distrito;
