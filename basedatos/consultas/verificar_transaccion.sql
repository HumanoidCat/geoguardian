-- Verificacion del criterio CA-11 de H1.3 (issue #37) · Rubrica BD-3
--
-- QUE DEMUESTRA
--
-- Que una transaccion que falla a mitad no deja cambios parciales.
--
-- COMO
--
-- Dentro de una sola transaccion se hacen dos cambios:
--
--   1. Un UPDATE valido que duplica el area de los ocho distritos.
--   2. Un UPDATE que pone el area de un distrito en 0, lo que viola la
--      restriccion distrito_area_ck (CHECK area_km2 > 0) y aborta la transaccion.
--
-- Si el control transaccional funciona, el COMMIT no confirma nada y el primer
-- UPDATE tampoco queda. La prueba es que la SUMA de las areas al final sea
-- identica a la del principio.
--
-- Se compara la suma y no solo el conteo a proposito: un conteo igual no
-- distingue entre 'no se aplico nada' y 'se aplico el primer UPDATE'. La suma si.
--
-- NO SE INVENTAN DATOS
--
-- Este guion no inserta distritos ficticios. Opera sobre las ocho filas reales ya
-- cargadas y no persiste ningun cambio: al terminar, la tabla queda exactamente
-- como estaba.
--
-- COMO SE EJECUTA, desde la raiz del repositorio en PowerShell:
--
--   Get-Content basedatos\consultas\verificar_transaccion.sql | docker compose exec -T db psql -U geoguardian -d geoguardian
--
-- El error 'new row for relation "distrito" violates check constraint' que
-- aparece en medio de la salida NO es un fallo de la prueba: es lo que la prueba
-- provoca a proposito. El fallo seria que no apareciera.

\echo '=== 1. Estado inicial ==='

SELECT count(*)                  AS filas_antes,
       round(sum(area_km2), 4)   AS suma_area_antes
  FROM geo.distrito;

\echo ''
\echo '=== 2. Transaccion que va a abortar ==='

BEGIN;

-- Cambio valido. Si la transaccion se confirmara, dejaria las areas al doble.
UPDATE geo.distrito
   SET area_km2 = area_km2 * 2;

-- Cambio invalido: viola distrito_area_ck. Aborta la transaccion entera.
UPDATE geo.distrito
   SET area_km2 = 0
 WHERE codigo = '50808';

-- Sobre una transaccion abortada, COMMIT se comporta como ROLLBACK.
COMMIT;

\echo ''
\echo '=== 3. Estado final: debe ser identico al inicial ==='

SELECT count(*)                  AS filas_despues,
       round(sum(area_km2), 4)   AS suma_area_despues
  FROM geo.distrito;

\echo ''
\echo 'CA-11 se cumple si suma_area_despues es igual a suma_area_antes.'
