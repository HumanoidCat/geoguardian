-- 019 · El retiro de escritores anteriores, sin darle DELETE al ETL
--
-- Historia: H11.7 · Decision: D-48 · Incidencia: I-51
--
-- LO QUE PASO
--
-- La noche del 2026-09-11 la cadena de estimacion corrio por primera vez bajo
-- el rol del ETL, en el servicio `trabajos` de Railway. Etiqueto, genero la
-- matriz, escribio 104.360 filas de lluvia intensa y **murio en la ultima
-- instruccion**:
--
--     psycopg.errors.InsufficientPrivilege: permission denied for table riesgo
--
-- La instruccion era el DELETE de `retirar_de_otros_escritores`, el arreglo de
-- I-37: un evento, un escritor. Y la 003 dice, textual: «Ningun rol recibe
-- DELETE ni TRUNCATE en ningun esquema.»
--
-- Las dos decisiones son correctas y nunca se habian encontrado, porque en
-- local la cadena corre con el usuario dueno, que puede todo.
--
-- LO QUE SE DECIDE (D-48)
--
-- La regla de la 003 **no se toca**. El ETL sigue sin poder borrar una fila de
-- `analitico.riesgo` con un DELETE. Lo que se le da es una funcion:
--
--     analitico.retirar_otros_escritores(tipo_evento, algoritmo_que_se_queda)
--
-- que hace ese unico borrado, con el WHERE cocido adentro, y corre con los
-- permisos de quien la definio (SECURITY DEFINER). El ETL puede pedir que se
-- retire lo que D-39 ya no elige, y nada mas.
--
-- Es la misma idea con la que la 009 le dio al ETL `registrar_riesgo` en vez
-- de dejarlo hacer INSERT a mano contra siete restricciones: el permiso se
-- concede sobre la operacion que la aplicacion necesita, no sobre la tabla.
--
-- LA SALVAGUARDA QUE EL DELETE CRUDO NO TENIA
--
-- `DELETE ... WHERE algoritmo <> 'x'` con una `x` que nunca escribio borra el
-- evento entero. Desde Python eso no puede pasar -el valor sale del enum-, pero
-- una funcion que el ETL puede llamar no debe fiarse de quien la llama. Por
-- eso la funcion **se niega** si el escritor que se queda no tiene ni una fila
-- del evento: retirar a todos en favor de nadie es exactamente lo que
-- `estimar_riesgo` dice que no se hace solo («no se borran solas: decidilo a
-- mano»).
--
-- SECURITY DEFINER, CON LAS TRES PRECAUCIONES DE COSTUMBRE
--
--   1. `search_path` fijado en la definicion, para que nadie resuelva
--      `analitico.riesgo` hacia otro objeto.
--   2. Los nombres van calificados con esquema aunque el search_path ya lo
--      cubra: dos candados.
--   3. Se revoca EXECUTE de PUBLIC antes de conceder al rol. Por omision toda
--      funcion nueva es ejecutable por cualquiera, y una que borra no.
--
-- El disparador `riesgo_auditoria_tg` de la 008 es AFTER DELETE y se dispara
-- igual: la historia de H1.13 guarda que estas filas existieron y cuando se
-- retiraron. Eso se quiere y por eso no se apaga.

BEGIN;

CREATE OR REPLACE FUNCTION analitico.retirar_otros_escritores(
    p_tipo_evento text,
    p_algoritmo   text
)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, analitico
AS $$
DECLARE
    v_retiradas integer;
BEGIN
    IF p_tipo_evento IS NULL OR p_algoritmo IS NULL THEN
        RAISE EXCEPTION 'retirar_otros_escritores: evento y algoritmo son obligatorios'
            USING ERRCODE = 'null_value_not_allowed';
    END IF;

    -- El escritor que se queda tiene que existir. Sin esta linea, un algoritmo
    -- mal escrito borra el evento completo. Con ella, borra cero y avisa.
    IF NOT EXISTS (
        SELECT 1
          FROM analitico.riesgo
         WHERE tipo_evento = p_tipo_evento
           AND algoritmo   = p_algoritmo
    ) THEN
        RAISE EXCEPTION
            'retirar_otros_escritores: % no tiene filas de % y no se retira a nadie en favor de nadie',
            p_algoritmo, p_tipo_evento
            USING ERRCODE = 'no_data_found';
    END IF;

    -- `<>` y no `IS DISTINCT FROM`, a proposito: es el mismo predicado que
    -- tenia el DELETE de Python. Una fila con `algoritmo` nulo es una ausencia
    -- declarada (006) y no pertenece a ningun escritor: no se retira.
    DELETE FROM analitico.riesgo
     WHERE tipo_evento = p_tipo_evento
       AND algoritmo <> p_algoritmo;

    GET DIAGNOSTICS v_retiradas = ROW_COUNT;
    RETURN v_retiradas;
END;
$$;

COMMENT ON FUNCTION analitico.retirar_otros_escritores(text, text) IS
    'Borra las filas del evento escritas por cualquier algoritmo distinto del indicado. Es el unico borrado que la aplicacion hace sobre analitico.riesgo (I-37) y el ETL lo ejecuta sin tener DELETE (D-48). Se niega si el algoritmo indicado no tiene filas del evento.';

-- Por omision, PUBLIC puede ejecutar cualquier funcion nueva. Esta no.
REVOKE ALL ON FUNCTION analitico.retirar_otros_escritores(text, text) FROM PUBLIC;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_etl') THEN
        GRANT EXECUTE ON FUNCTION analitico.retirar_otros_escritores(text, text)
            TO geoguardian_etl;
    END IF;
END;
$$;

COMMIT;
