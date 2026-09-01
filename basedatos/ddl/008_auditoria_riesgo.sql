-- 008 · Disparador de auditoria sobre analitico.riesgo
--
-- Historia: H1.13 (issue #45) · Rubrica: BD-2
--
-- QUE PROBLEMA RESUELVE
--
-- `analitico.riesgo` guarda **una fila por distrito, dia y evento**, y esa fila
-- se sobrescribe cada vez que el modelo vuelve a estimar. Sin auditoria, una
-- estimacion que hoy dice ALTO y manana dice BAJO **no deja rastro de que
-- cambio**: la tabla solo conserva el ultimo valor.
--
-- Eso importa aca mas que en una tabla cualquiera. El sistema publica riesgo
-- climatico: si alguien pregunta «¿que decia el sistema el martes?», la
-- respuesta tiene que existir. Y si un modelo nuevo empeora las estimaciones, la
-- unica forma de demostrarlo es tener las viejas.
--
-- QUE SE GUARDA, Y QUE NO
--
-- Se guarda **el estado ANTERIOR** de la fila, no el nuevo. El nuevo ya esta en
-- `analitico.riesgo`; duplicarlo seria guardar dos veces lo mismo y hacer que la
-- auditoria crezca al doble sin agregar informacion.
--
-- En un INSERT no hay estado anterior, asi que **no se audita**. Una fila nueva
-- no cambio nada: aparecio. Auditar el INSERT llenaria la tabla de filas cuyo
-- «antes» es todo NULL.
--
-- POR QUE UN DISPARADOR Y NO CODIGO DE APLICACION
--
-- Porque la aplicacion no es el unico que escribe. Una carga manual, un guion de
-- otro modulo o una restauracion parcial tambien tocan la tabla, y todos ellos
-- se saltarian una auditoria escrita en Python.
--
-- Es la misma razon por la que las restricciones de la 006 y la 007 viven en el
-- esquema: **lo que tiene que cumplirse siempre se pone donde no se puede
-- evitar.**

-- --------------------------------------------------------------------------- #
-- La bitacora                                                                  #
-- --------------------------------------------------------------------------- #
CREATE TABLE IF NOT EXISTS analitico.riesgo_auditoria (
    -- Aca SI va un identificador opaco, al reves que en `analitico.riesgo`.
    --
    -- La terna (distrito, fecha, evento) **no es unica** en esta tabla: la
    -- gracia es justamente guardar varias versiones de la misma estimacion. Una
    -- clave natural haria imposible el segundo cambio.
    id              bigint GENERATED ALWAYS AS IDENTITY,

    -- La terna de la fila auditada. No lleva clave foranea a `analitico.riesgo`
    -- **a proposito**: si la fila original se borra, su historia tiene que
    -- sobrevivir. Una FK con ON DELETE CASCADE borraria justo lo que se quiere
    -- conservar, y con RESTRICT impediria borrar nada.
    codigo_distrito text        NOT NULL,
    fecha           date        NOT NULL,
    tipo_evento     text        NOT NULL,

    operacion       text        NOT NULL,

    -- El estado ANTERIOR. Se guardan las columnas que pueden cambiar; la terna
    -- de la clave primaria no puede -un UPDATE que la cambie es un borrado mas
    -- una insercion- y por eso no se duplica aca.
    nivel_anterior         text,
    probabilidad_anterior  numeric(5, 4),
    algoritmo_anterior     text,
    version_anterior       text,

    -- Cuando y quien. `current_user` es el rol de PostgreSQL, que por H1.8 es
    -- `geoguardian_etl` o `geoguardian_api`: distingue una estimacion del
    -- pipeline de una escritura manual.
    --
    -- NOTA SOBRE now(): aca SI es correcto y no contradice la 007.
    --
    -- Alla `CURRENT_DATE` estaba en un CHECK, que **se reevalua en cada
    -- insercion** y por eso rompia la restauracion. Aca es un DEFAULT: se evalua
    -- UNA VEZ, al escribir la fila, y el valor queda congelado. Un DEFAULT
    -- volatil es lo normal; un CHECK volatil es el defecto.
    registrado_en   timestamptz NOT NULL DEFAULT now(),
    registrado_por  text        NOT NULL DEFAULT current_user,

    CONSTRAINT riesgo_auditoria_pk PRIMARY KEY (id),

    CONSTRAINT riesgo_auditoria_operacion_ck
        CHECK (operacion IN ('UPDATE', 'DELETE'))
);

COMMENT ON TABLE analitico.riesgo_auditoria IS
    'Historia de analitico.riesgo. Guarda el estado ANTERIOR de cada UPDATE y DELETE. Los INSERT no se auditan: una fila nueva no cambio nada.';
COMMENT ON COLUMN analitico.riesgo_auditoria.registrado_por IS
    'Rol de PostgreSQL que hizo el cambio. Distingue el pipeline (geoguardian_etl) de una escritura manual.';
COMMENT ON COLUMN analitico.riesgo_auditoria.nivel_anterior IS
    'Lo que decia la fila ANTES del cambio. El valor nuevo ya esta en analitico.riesgo; duplicarlo no agregaria informacion.';

-- --------------------------------------------------------------------------- #
-- La funcion                                                                   #
-- --------------------------------------------------------------------------- #
--
-- `SECURITY DEFINER` a proposito: la auditoria tiene que escribirse aunque el
-- rol que dispara el cambio **no tenga permiso de escritura** sobre la bitacora.
-- Si dependiera del permiso de quien escribe, bastaria con revocarselo para
-- dejar de auditar, y una auditoria que se puede apagar desde afuera no es una
-- auditoria.
--
-- `search_path` fijo porque `SECURITY DEFINER` sin el es la receta clasica de
-- escalada de privilegios: quien invoca podria anteponer un esquema con una
-- tabla `riesgo_auditoria` propia.
CREATE OR REPLACE FUNCTION analitico.auditar_riesgo()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analitico, pg_temp
AS $$
BEGIN
    INSERT INTO analitico.riesgo_auditoria (
        codigo_distrito, fecha, tipo_evento, operacion,
        nivel_anterior, probabilidad_anterior, algoritmo_anterior, version_anterior
    )
    VALUES (
        OLD.codigo_distrito, OLD.fecha, OLD.tipo_evento, TG_OP,
        OLD.nivel, OLD.probabilidad, OLD.algoritmo, OLD.version_modelo
    );

    -- En un disparador AFTER el valor de retorno se ignora, pero PL/pgSQL exige
    -- devolver algo. Se devuelve OLD y no NULL para que, si alguien lo cambia a
    -- BEFORE por error, el DELETE siga ocurriendo en vez de cancelarse en
    -- silencio -que es lo que hace un BEFORE que devuelve NULL-.
    RETURN OLD;
END;
$$;

COMMENT ON FUNCTION analitico.auditar_riesgo() IS
    'Escribe en riesgo_auditoria el estado anterior de la fila. SECURITY DEFINER para que la auditoria no dependa del permiso de quien dispara el cambio.';

-- --------------------------------------------------------------------------- #
-- El disparador                                                                #
-- --------------------------------------------------------------------------- #
--
-- AFTER y no BEFORE: si el cambio falla por una restriccion -las siete de la 006
-- y la 007-, no tiene que quedar rastro de un cambio que no ocurrio. Un BEFORE
-- auditaria intentos, no hechos.
--
-- FOR EACH ROW: la unidad de la auditoria es la fila. Con FOR EACH STATEMENT un
-- UPDATE que toca 800 filas dejaria un solo registro y no se sabria cuales.
DROP TRIGGER IF EXISTS riesgo_auditoria_tg ON analitico.riesgo;

CREATE TRIGGER riesgo_auditoria_tg
    AFTER UPDATE OR DELETE ON analitico.riesgo
    FOR EACH ROW
    EXECUTE FUNCTION analitico.auditar_riesgo();

-- --------------------------------------------------------------------------- #
-- Permisos                                                                     #
-- --------------------------------------------------------------------------- #
--
-- Nadie escribe en la bitacora directamente: la escribe la funcion, que corre
-- con los privilegios de su dueno. Los roles solo leen.
--
-- Es lo que hace que la auditoria sea confiable: **el ETL puede cambiar una
-- estimacion pero no puede borrar el registro de que la cambio.**
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_api') THEN
        GRANT SELECT ON analitico.riesgo_auditoria TO geoguardian_api;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_lector') THEN
        GRANT SELECT ON analitico.riesgo_auditoria TO geoguardian_lector;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_etl') THEN
        GRANT SELECT ON analitico.riesgo_auditoria TO geoguardian_etl;
    END IF;
END;
$$;
