-- 016 · `fuente_precipitacion` declara el origen de un valor, no de una ausencia
--
-- Incidencias I-43 e I-45 · Alejandro · Revisa H1.1 (004), H1.10 (010), H1.14 (013)
--
-- ===========================================================================
-- QUE PASABA
-- ===========================================================================
--
-- Medido por Luna el 2026-09-06 (`hallazgochirps20260906.md`): las 1968 filas
-- de 2026 en `crudo.medicion_diaria` tienen `precipitacion_mm` en NULL y
-- `fuente_precipitacion = 'chirps'`. La ingesta del 2026-09-04 pidio 215 dias a
-- ClimateSERV, recibio 3, y escribio los 246 dias de la ventana con la fuente
-- puesta, porque la columna es NOT NULL desde la 004 y el ETL la llenaba con el
-- producto de la corrida, hubiera valor o no.
--
-- Quien audite la tabla lee que CHIRPS aporto esos dias. No aporto nada: la
-- respuesta venia incompleta y nadie la comparo con lo pedido (eso lo corrige
-- `comprobar_cobertura`, en `backend/etl/fuentes/chirps.py`). Esta migracion
-- corrige lo que la tabla AFIRMA.
--
-- ===========================================================================
-- QUE HACE
-- ===========================================================================
--
--   1. Quita el NOT NULL de `fuente_precipitacion`. Un dia sin precipitacion no
--      tiene fuente que declarar. Es la misma regla de D-07 (ausencia es nulo,
--      nunca cero) llevada a la columna que dice de donde vino el dato.
--   2. Pone en NULL la fuente de toda fila que no tenga precipitacion. Sobre la
--      base publicada son las 1968 filas de 2026; en una base recien cargada,
--      ninguna. Es un UPDATE sobre datos y se deja escrito aqui, en el
--      repositorio, y no en una consola.
--   3. Deja la regla como restriccion: las dos columnas son nulas a la vez o
--      ninguna lo es. Sin esto el defecto puede volver por otro camino, y la
--      restriccion lo convierte en un error del ETL en el momento de escribir,
--      que es donde se puede corregir, y no en una lectura ocho meses despues.
--
-- La restriccion va sobre la tabla particionada (010); PostgreSQL la propaga a
-- todas las particiones, presentes y futuras. Entra validada porque el UPDATE
-- del paso 2 deja la tabla coherente antes de agregarla; si en una base hubiera
-- filas con valor y sin fuente -que ningun escritor del proyecto produce- el
-- ADD CONSTRAINT falla y esa base tiene un hallazgo que mirar, no una migracion
-- que forzar.
--
-- ===========================================================================
-- QUE NO HACE
-- ===========================================================================
--
--   * **No toca `precipitacion_mm`.** Los nulos de 2026 siguen siendo nulos: la
--     serie se desatasca con una corrida del ETL (`--desde 2025-12-01`, I-43),
--     no con SQL.
--   * **No toca la FK a `crudo.fuente`.** Una fuente declarada sigue teniendo
--     que existir en el catalogo; solo se permite no declarar ninguna.
--   * **No cambia `fuente_resto`.** POWER devuelve la celda completa y no ha
--     presentado el caso; si lo presenta, es otra incidencia y otra migracion.

BEGIN;

ALTER TABLE crudo.medicion_diaria
    ALTER COLUMN fuente_precipitacion DROP NOT NULL;

UPDATE crudo.medicion_diaria
   SET fuente_precipitacion = NULL
 WHERE precipitacion_mm IS NULL
   AND fuente_precipitacion IS NOT NULL;

-- El DROP antes del ADD porque PostgreSQL no acepta ADD CONSTRAINT IF NOT EXISTS
-- (la 014 explica lo mismo). Asi la migracion se puede volver a aplicar.
ALTER TABLE crudo.medicion_diaria
    DROP CONSTRAINT IF EXISTS medicion_fuente_con_valor_ck;
ALTER TABLE crudo.medicion_diaria
    ADD CONSTRAINT medicion_fuente_con_valor_ck
    CHECK ((precipitacion_mm IS NULL) = (fuente_precipitacion IS NULL));

COMMENT ON COLUMN crudo.medicion_diaria.fuente_precipitacion IS
    'Codigo de crudo.fuente del que salio precipitacion_mm. NULL exactamente cuando precipitacion_mm es NULL (016, I-45): un dia sin dato no declara origen. chirps es el final con estaciones; chirp, el mismo algoritmo sin ellas (013, D-40).';

COMMIT;
