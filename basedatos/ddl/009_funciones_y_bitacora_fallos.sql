-- 009 · Funciones PL/pgSQL con manejo de excepciones y bitacora de fallos
--
-- Historia: H1.9 (issue #41) · Rubrica: BD-3
--
-- EL PROBLEMA REAL QUE RESUELVE
--
-- El modelado escribe estimaciones por lotes: ocho distritos por tres eventos
-- por cada dia del horizonte. Con las siete restricciones de la 006 y la 007,
-- **una sola fila mala aborta la transaccion entera** y se pierden las buenas.
--
-- Pero la salida facil -atrapar el error y seguir- es peor que el problema:
-- convierte un fallo ruidoso en uno silencioso, y el proyecto ya tiene tres
-- incidencias sobre exactamente eso.
--
-- La regla de este modulo: **se puede continuar, nunca callar.** Cada fila
-- rechazada deja un registro con su SQLSTATE, su mensaje y sus datos, y la
-- funcion devuelve cuantas entraron y cuantas no. Quien la llama **no puede
-- ignorar el resultado sin querer**.
--
-- LO QUE ESTA BITACORA NO PUEDE HACER, Y HAY QUE SABERLO
--
-- PostgreSQL **no tiene transacciones autonomas**. El registro del fallo se
-- escribe en la misma transaccion que lo detecto, asi que **si esa transaccion
-- se revierte entera, el registro se va con ella**.
--
-- Funciona para lo que esta historia necesita -continuar dentro de un lote y
-- dejar constancia de lo saltado- y **no** sirve como auditoria de seguridad
-- frente a alguien que revierta a proposito. Para eso harian falta `dblink` o
-- un proceso aparte, y eso es otra historia. Se declara aca en vez de
-- descubrirse despues.

-- --------------------------------------------------------------------------- #
-- La bitacora de fallos                                                        #
-- --------------------------------------------------------------------------- #
CREATE TABLE IF NOT EXISTS control.fallo (
    id           bigint GENERATED ALWAYS AS IDENTITY,

    -- Que funcion fallo. Texto y no un enum: las funciones se agregan sin
    -- migrar la tabla.
    origen       text        NOT NULL,

    -- EL CODIGO DE ESTADO DE SQL, QUE ES LO QUE DE VERDAD SIRVE.
    --
    -- `23514` es violacion de CHECK, `23503` de clave foranea, `23505` de
    -- unicidad. Guardar solo el mensaje obligaria a leerlo con expresiones
    -- regulares para clasificar, y el mensaje **cambia con el idioma del
    -- servidor**. El codigo no.
    sqlstate     text        NOT NULL,

    mensaje      text        NOT NULL,

    -- El detalle y la pista que PostgreSQL adjunta. Suelen traer el nombre de
    -- la restriccion y el valor que la violo, que es lo que permite reproducir.
    detalle      text,
    contexto     text,

    -- Los datos de la fila rechazada, como llegaron. `jsonb` porque cada
    -- funcion rechaza filas de forma distinta y una tabla por forma seria
    -- ingobernable.
    --
    -- **No se guarda la sentencia**: guardarla invitaria a reintentarla a ciegas.
    -- Lo que se guarda son los datos, para que quien corrija sepa que corregir.
    datos        jsonb,

    ocurrido_en  timestamptz NOT NULL DEFAULT now(),
    reportado_por text       NOT NULL DEFAULT current_user,

    CONSTRAINT fallo_pk PRIMARY KEY (id)
);

COMMENT ON TABLE control.fallo IS
    'Filas rechazadas durante una carga por lotes, con su SQLSTATE y sus datos. Se escribe en la misma transaccion que la deteccion: si esa transaccion se revierte, el registro tambien.';
COMMENT ON COLUMN control.fallo.sqlstate IS
    'Codigo SQL del error, no el mensaje. El mensaje cambia con el idioma del servidor; el codigo no.';
COMMENT ON COLUMN control.fallo.datos IS
    'La fila rechazada tal como llego. NO se guarda la sentencia: invitaria a reintentarla a ciegas.';

CREATE INDEX IF NOT EXISTS fallo_origen_fecha_ix
    ON control.fallo (origen, ocurrido_en DESC);

-- --------------------------------------------------------------------------- #
-- 1. Registrar una estimacion, sin abortar el lote                            #
-- --------------------------------------------------------------------------- #
--
-- Devuelve TRUE si entro, FALSE si se rechazo y quedo registrada.
--
-- POR QUE DEVUELVE UN BOOLEANO Y NO VOID
--
-- Una funcion `void` que atrapa excepciones es una funcion que **se puede
-- llamar en un bucle y nunca enterarse de nada**. Con un booleano, quien la
-- llama tiene que decidir explicitamente ignorarlo.
--
-- POR QUE `modo_estricto`
--
-- Continuar es lo correcto en una carga masiva y **es lo incorrecto en una
-- prueba**: si la suite de H10.2 llama a esto y el error se traga, la prueba
-- pasa sobre datos que no se escribieron. Con `modo_estricto := true` la
-- excepcion se vuelve a lanzar despues de registrarla.
CREATE OR REPLACE FUNCTION analitico.registrar_riesgo(
    p_codigo_distrito text,
    p_fecha           date,
    p_tipo_evento     text,
    p_nivel           text          DEFAULT NULL,
    p_probabilidad    numeric       DEFAULT NULL,
    p_algoritmo       text          DEFAULT NULL,
    p_version_modelo  text          DEFAULT NULL,
    modo_estricto     boolean       DEFAULT false
)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
    v_sqlstate text;
    v_mensaje  text;
    v_detalle  text;
    v_contexto text;
BEGIN
    -- UNA PRECONDICION QUE LA BASE NO PUEDE COMPROBAR SOLA.
    --
    -- El horizonte del sistema es de siete dias. La 007 quito el limite
    -- superior del CHECK -era CURRENT_DATE y rompia la restauracion, ver I-18-
    -- y dejo dicho que **la regla la hace cumplir quien escribe**.
    --
    -- Aca es donde se cumple. `RAISE` con nivel EXCEPTION y un SQLSTATE propio
    -- de la clase 'P0' -reservada por PostgreSQL para el usuario- para que se
    -- distinga de una violacion de restriccion al clasificar la bitacora.
    IF p_fecha > CURRENT_DATE + INTERVAL '31 days' THEN
        RAISE EXCEPTION
            'fecha % fuera del horizonte: mas de 31 dias hacia adelante', p_fecha
            USING ERRCODE = 'P0001',
                  HINT = 'El horizonte del sistema es de 7 dias; 31 es el margen operativo.';
    END IF;

    INSERT INTO analitico.riesgo AS r (
        codigo_distrito, fecha, tipo_evento, nivel, probabilidad,
        algoritmo, version_modelo
    )
    VALUES (
        p_codigo_distrito, p_fecha, p_tipo_evento, p_nivel, p_probabilidad,
        p_algoritmo, p_version_modelo
    )
    -- Reestimar es lo normal: el modelo vuelve a correr cada dia. El disparador
    -- de H1.13 guarda el valor anterior, asi que sobrescribir no pierde nada.
    ON CONFLICT (codigo_distrito, fecha, tipo_evento) DO UPDATE
        SET nivel          = EXCLUDED.nivel,
            probabilidad   = EXCLUDED.probabilidad,
            algoritmo      = EXCLUDED.algoritmo,
            version_modelo = EXCLUDED.version_modelo,
            estimado_en    = now();

    RETURN true;

EXCEPTION
    -- SE ATRAPAN LAS VIOLACIONES DE INTEGRIDAD Y LA PRECONDICION. NADA MAS.
    --
    -- `WHEN OTHERS` atraparia tambien un fallo de disco, una desconexion o un
    -- error de sintaxis, y los registraria como si fueran una fila mala. Un
    -- manejador demasiado ancho **convierte problemas de infraestructura en
    -- datos rechazados**, que es la peor forma de perder un incidente.
    -- `numeric_value_out_of_range` NO ES OPCIONAL, Y CASI SE QUEDA AFUERA.
    --
    -- `probabilidad` es `numeric(5,4)`. Un valor como 85 **desborda el tipo
    -- antes de que se evalue el CHECK del rango 0..1**, asi que no llega como
    -- `check_violation` sino como `22003`. Sin esta condicion, un modelo que
    -- devuelva probabilidades sin normalizar tumba el lote entero en vez de
    -- dejar constancia de una fila.
    --
    -- Aparecio corriendo el criterio 3 del verificador. Leyendo el codigo se
    -- veia bien.
    WHEN check_violation
       OR numeric_value_out_of_range
       OR string_data_right_truncation
       OR foreign_key_violation
       OR not_null_violation
       OR unique_violation
       OR invalid_text_representation
       OR datetime_field_overflow
       OR raise_exception
    THEN
        GET STACKED DIAGNOSTICS
            v_sqlstate = RETURNED_SQLSTATE,
            v_mensaje  = MESSAGE_TEXT,
            v_detalle  = PG_EXCEPTION_DETAIL,
            v_contexto = PG_EXCEPTION_CONTEXT;

        INSERT INTO control.fallo (origen, sqlstate, mensaje, detalle, contexto, datos)
        VALUES (
            'analitico.registrar_riesgo', v_sqlstate, v_mensaje, v_detalle, v_contexto,
            jsonb_build_object(
                'codigo_distrito', p_codigo_distrito,
                'fecha',           p_fecha,
                'tipo_evento',     p_tipo_evento,
                'nivel',           p_nivel,
                'probabilidad',    p_probabilidad,
                'algoritmo',       p_algoritmo,
                'version_modelo',  p_version_modelo
            )
        );

        IF modo_estricto THEN
            -- Se registro Y se relanza. El registro sobrevive porque el INSERT
            -- de arriba ya ocurrio en esta transaccion; si quien llama revierte,
            -- se pierde, y eso esta declarado en la cabecera.
            RAISE;
        END IF;

        RETURN false;
END;
$$;

COMMENT ON FUNCTION analitico.registrar_riesgo IS
    'Inserta o actualiza una estimacion. Devuelve TRUE si entro, FALSE si se rechazo y quedo en control.fallo. Con modo_estricto relanza la excepcion despues de registrarla.';

-- --------------------------------------------------------------------------- #
-- 2. El lote, que es donde el manejo de errores se paga                        #
-- --------------------------------------------------------------------------- #
--
-- Devuelve cuantas entraron, cuantas se rechazaron y en cuanto tiempo.
--
-- POR QUE ESTA FUNCION EXISTE APARTE
--
-- Porque **el bloque EXCEPTION cuesta**. Cada uno abre una subtransaccion
-- interna -un savepoint-, y en un bucle de cien mil filas eso se nota. Tenerlo
-- separado permite medirlo, que es CA-4 de esta historia.
--
-- Y porque el resumen es lo que hace que el fallo no se pueda ignorar: una
-- carga que devuelve `(8, 0)` y una que devuelve `(5, 3)` se distinguen a
-- simple vista.
CREATE OR REPLACE FUNCTION analitico.registrar_riesgo_lote(
    p_filas jsonb,
    modo_estricto boolean DEFAULT false
)
RETURNS TABLE (aceptadas integer, rechazadas integer, milisegundos numeric)
LANGUAGE plpgsql
AS $$
DECLARE
    v_fila     jsonb;
    v_ok       integer := 0;
    v_fallo    integer := 0;
    v_sqlstate text;
    v_mensaje  text;
    v_arranque timestamptz := clock_timestamp();
BEGIN
    IF jsonb_typeof(p_filas) <> 'array' THEN
        RAISE EXCEPTION 'se esperaba un arreglo JSON, llego %', jsonb_typeof(p_filas)
            USING ERRCODE = 'P0001';
    END IF;

    FOR v_fila IN SELECT * FROM jsonb_array_elements(p_filas)
    LOOP
        -- EL BLOQUE DE AFUERA ATRAPA LO QUE EL DE ADENTRO NO PUEDE.
        --
        -- Las conversiones `::date` y `::numeric` ocurren **al armar la llamada**,
        -- o sea antes de entrar a `registrar_riesgo`. Un `'fecha': 'ayer'` en el
        -- JSON explotaria aca afuera y **abortaria el lote entero**, que es
        -- exactamente lo que esta historia existe para evitar.
        --
        -- Se descubrio escribiendo el criterio 10 del verificador, no leyendo.
        BEGIN
            IF analitico.registrar_riesgo(
                v_fila ->> 'codigo_distrito',
                (v_fila ->> 'fecha')::date,
                v_fila ->> 'tipo_evento',
                v_fila ->> 'nivel',
                (v_fila ->> 'probabilidad')::numeric,
                v_fila ->> 'algoritmo',
                v_fila ->> 'version_modelo',
                modo_estricto
            ) THEN
                v_ok := v_ok + 1;
            ELSE
                v_fallo := v_fallo + 1;
            END IF;
        EXCEPTION
            -- Solo el JSON mal formado. Todo lo demas ya lo maneja -o relanza a
            -- proposito- la funcion de adentro, y volver a atraparlo aca
            -- anularia `modo_estricto`.
            -- `invalid_datetime_format` (22007) y no solo
            -- `invalid_text_representation` (22P02): un `'ayer'::date` da el
            -- primero. Los dos parecen «texto que no convierte» y son codigos
            -- distintos; el verificador lo dijo antes que la documentacion.
            WHEN invalid_text_representation
               OR invalid_datetime_format
               OR datetime_field_overflow
               OR datatype_mismatch
            THEN
                IF modo_estricto THEN
                    RAISE;
                END IF;
                GET STACKED DIAGNOSTICS
                    v_sqlstate = RETURNED_SQLSTATE,
                    v_mensaje  = MESSAGE_TEXT;
                INSERT INTO control.fallo (origen, sqlstate, mensaje, detalle, datos)
                VALUES (
                    'analitico.registrar_riesgo_lote', v_sqlstate, v_mensaje,
                    'la fila no se pudo convertir a los tipos de la tabla', v_fila
                );
                v_fallo := v_fallo + 1;
        END;
    END LOOP;

    -- UN AVISO, NO UN ERROR.
    --
    -- Que haya rechazos es un resultado legitimo del lote, asi que no se aborta.
    -- Pero **queda en el registro del servidor** ademas de en el valor devuelto,
    -- para que aparezca aunque quien llama ignore la salida.
    IF v_fallo > 0 THEN
        RAISE WARNING '% de % filas rechazadas. Ver control.fallo.',
            v_fallo, v_ok + v_fallo;
    END IF;

    RETURN QUERY SELECT
        v_ok,
        v_fallo,
        round(EXTRACT(EPOCH FROM (clock_timestamp() - v_arranque)) * 1000, 2);
END;
$$;

COMMENT ON FUNCTION analitico.registrar_riesgo_lote IS
    'Registra un arreglo JSON de estimaciones. Devuelve aceptadas, rechazadas y milisegundos. Emite WARNING si hubo rechazos, para que aparezcan aunque nadie mire el valor devuelto.';

-- --------------------------------------------------------------------------- #
-- Permisos                                                                     #
-- --------------------------------------------------------------------------- #
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_etl') THEN
        GRANT EXECUTE ON FUNCTION analitico.registrar_riesgo TO geoguardian_etl;
        GRANT EXECUTE ON FUNCTION analitico.registrar_riesgo_lote TO geoguardian_etl;
        GRANT SELECT, INSERT ON control.fallo TO geoguardian_etl;
    END IF;
    -- La API lee los fallos para poder mostrarlos, y no escribe ninguno.
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_api') THEN
        GRANT SELECT ON control.fallo TO geoguardian_api;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_lector') THEN
        GRANT SELECT ON control.fallo TO geoguardian_lector;
    END IF;
END;
$$;
