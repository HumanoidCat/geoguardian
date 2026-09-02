-- 012 · A que corrida pertenece cada fila rechazada
--
-- Pedido por Luna en el PR #223, para H12.4 · Afecta: H1.9, H12.1, H12.4
--
-- ===========================================================================
-- EL HALLAZGO ES CORRECTO Y ES SOBRE ESTA TABLA
-- ===========================================================================
--
-- `control.fallo` la creo H1.9 ayer, y guarda origen, sqlstate, mensaje,
-- detalle, contexto, datos, ocurrido_en y reportado_por. **Ninguna de esas
-- columnas dice a que corrida del ETL pertenece la fila.**
--
-- Para responder «la carga de anoche rechazo 340 filas con SQLSTATE 23514» hay
-- que correlacionar por ventana de tiempo. Eso funciona hasta que **dos corridas
-- se solapan** o **alguien reejecuta**, y entonces mezcla filas de dos cargas
-- distintas sin avisar.
--
-- Es la misma forma que I-18 e I-20: algo que anda bien mientras el caso facil
-- sea el unico caso.
--
-- ===========================================================================
-- POR QUE NO SE PASA COMO PARAMETRO, QUE ERA LO PEDIDO
-- ===========================================================================
--
-- La propuesta original era agregar la columna y pasarla en cada llamada. Eso
-- obliga a cambiar la firma de `analitico.registrar_riesgo` y de
-- `registrar_riesgo_lote`, y a que **cada sitio que las llame arrastre el id**.
-- Un dia alguien lo olvida, la fila entra con NULL, y el hueco no se distingue
-- de una escritura hecha fuera de una corrida.
--
-- Aca se usa un **parametro de sesion** y un DEFAULT:
--
--     SET LOCAL geoguardian.corrida_id = 42;   -- el ETL lo declara UNA vez
--
-- y la columna se llena sola. Ventajas medibles:
--
--   * **Cero cambios en las funciones de H1.9.** No se tocan sus 150 lineas ni
--     sus 22 criterios de aceptacion.
--   * Sirve para **cualquiera** que escriba en `control.fallo`, no solo para
--     esas dos funciones. Una carga manual tambien queda atribuida.
--   * `SET LOCAL` muere con la transaccion, asi que **no se puede filtrar** a la
--     siguiente corrida de la misma conexion.
--
-- ===========================================================================
-- SIN CLAVE FORANEA TODAVIA, Y ESO ES DELIBERADO
-- ===========================================================================
--
-- `control.bitacora_etl` no existe: la crea **H12.1**, que es de Cesar. Poner la
-- FK ahora significaria crear la tabla desde aca, y eso seria decidir su diseno
-- por el.
--
-- La columna entra sin FK y **H12.1 la agrega** con una linea:
--
--     ALTER TABLE control.fallo
--         ADD CONSTRAINT fallo_corrida_fk
--         FOREIGN KEY (corrida_id) REFERENCES control.bitacora_etl (id);
--
-- Hasta entonces el dato se guarda igual. **Perder la atribucion de las cargas
-- de estas tres semanas para esperar una tabla que no existe seria cambiar
-- informacion real por prolijidad.**

-- --------------------------------------------------------------------------- #
-- 1. De donde sale el identificador de corrida                                 #
-- --------------------------------------------------------------------------- #
CREATE OR REPLACE FUNCTION control.corrida_actual()
RETURNS bigint
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    -- `true` es `missing_ok`: si nadie declaro la corrida devuelve NULL en vez
    -- de fallar. Escribir en `control.fallo` fuera de una corrida es legitimo
    -- -una prueba, una carga a mano- y no tiene por que romperse.
    --
    -- El NULLIF cubre el caso de la cadena vacia, que `current_setting`
    -- devuelve en algunas rutas y que reventaria el cast.
    RETURN NULLIF(current_setting('geoguardian.corrida_id', true), '')::bigint;
EXCEPTION
    -- Si alguien pone ahi algo que no es un numero, **la carga no se cae**: la
    -- fila entra sin corrida. Es la regla de H1.9 llevada a su propio registro:
    -- se puede continuar, nunca callar. Y el NULL es visible.
    WHEN invalid_text_representation THEN
        RETURN NULL;
END;
$$;

COMMENT ON FUNCTION control.corrida_actual() IS
    'Lee geoguardian.corrida_id de la sesion. NULL si no se declaro, que es legitimo: escribir fuera de una corrida no es un error.';

-- --------------------------------------------------------------------------- #
-- 2. La columna                                                                #
-- --------------------------------------------------------------------------- #
ALTER TABLE control.fallo
    ADD COLUMN IF NOT EXISTS corrida_id bigint DEFAULT control.corrida_actual();

COMMENT ON COLUMN control.fallo.corrida_id IS
    'Corrida del ETL a la que pertenece la fila rechazada. Se llena sola desde el parametro de sesion geoguardian.corrida_id. NULL significa escritura fuera de una corrida, no un olvido. La clave foranea a control.bitacora_etl la agrega H12.1.';

-- El indice que H12.4 va a usar: «dame todo lo que rechazo la corrida 42».
-- Sin el, esa consulta recorre la tabla entera, que es justo lo que H1.12
-- acaba de medir para otras dos.
CREATE INDEX IF NOT EXISTS fallo_corrida_ix
    ON control.fallo (corrida_id, sqlstate)
    WHERE corrida_id IS NOT NULL;

COMMENT ON INDEX control.fallo_corrida_ix IS
    'Parcial a proposito: las filas sin corrida no se agrupan por corrida, asi que no hace falta indexarlas.';

-- --------------------------------------------------------------------------- #
-- 3. Como se usa, desde el ETL                                                 #
-- --------------------------------------------------------------------------- #
--
--     BEGIN;
--     SET LOCAL geoguardian.corrida_id = 42;
--     SELECT analitico.registrar_riesgo_lote('[...]'::jsonb);
--     COMMIT;
--
-- Todo lo que se rechace dentro de esa transaccion queda atribuido a la corrida
-- 42, **sin que ninguna funcion lo sepa**.
--
-- Y una consulta que antes no se podia responder:
--
--     SELECT sqlstate, count(*)
--     FROM control.fallo
--     WHERE corrida_id = 42
--     GROUP BY sqlstate ORDER BY 2 DESC;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_etl') THEN
        GRANT EXECUTE ON FUNCTION control.corrida_actual() TO geoguardian_etl;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_api') THEN
        GRANT EXECUTE ON FUNCTION control.corrida_actual() TO geoguardian_api;
    END IF;
END;
$$;
