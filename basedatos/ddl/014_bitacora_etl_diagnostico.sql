-- 014 · La bitacora de corridas, extendida para el diagnostico
--
-- Historia H12.1 · Luna, traspasada desde Cesar por D-37 · Afecta: H12.2, H12.4
--
-- ===========================================================================
-- ESTA MIGRACION EXTIENDE, NO CREA
-- ===========================================================================
--
-- La 012 dejo dicho que `control.bitacora_etl` la creaba H12.1. **H1.14 llego
-- antes a necesitarla** y la trajo en la 013 en su forma minima, con
-- `CREATE TABLE IF NOT EXISTS`, dejando el resto a esta historia. Ningun orden
-- de aplicacion rompe al otro.
--
-- Lo que sigue siendo de H12.1, y es lo que hace este archivo:
--
--   1. Las columnas que el diagnostico necesita y no estan.
--   2. El estado `parcial`.
--   3. La coherencia entre `estado` y `terminada_en`.
--   4. La clave foranea desde `control.fallo`, prometida por la 012.
--   5. El indice del detector de procesos muertos.
--
-- ===========================================================================
-- POR QUE NO SE AGREGA `filas_escritas`
-- ===========================================================================
--
-- La especificacion de H12.4 pedia `filas_leidas` y `filas_escritas`. La tabla
-- ya tiene `filas`, que `ingestar.py` llena con las escritas.
--
-- Poner `filas_escritas` al lado dejaria **dos columnas para el mismo dato**, y
-- un dia una diria una cosa y la otra otra. Es la incidencia **I-07**.
--
-- Los tres numeros que el diagnostico necesita quedan asi:
--
--   leidas     -> `filas_leidas`, que se agrega aca
--   escritas   -> `filas`, que ya existe
--   rechazadas -> se cuentan en `control.fallo` por `corrida_id`
--
-- El tercero es posible **gracias a la clave foranea de mas abajo**, que es lo
-- que enlaza las dos tablas.
--
-- ===========================================================================
-- POR QUE NO SE AGREGA UN `parametros jsonb`
-- ===========================================================================
--
-- Tambien lo pedia la especificacion. La tabla ya tiene `ventana_desde`,
-- `ventana_hasta` y `producto`: columnas tipadas, que se consultan, se
-- restringen y las valida el motor. Un `jsonb` al lado seria un segundo lugar
-- para lo mismo con menos garantias.
--
-- Se declara como desviacion en los criterios de aceptacion. El documento de
-- requisitos **no se ajusta**: se escribio el 1 de septiembre, antes de saber
-- como iba a quedar la tabla, y su valor esta justamente en eso.

BEGIN;

-- --------------------------------------------------------------------------- #
-- 1 · Las columnas del diagnostico                                             #
-- --------------------------------------------------------------------------- #
--
-- Todas anulables y sin defecto. Las corridas que ya existen quedan con NULL, y
-- eso es correcto: **inventarles un valor seria falsear el registro**. NULL aqui
-- significa «esta corrida es anterior a que se registrara esto».

ALTER TABLE control.bitacora_etl
    -- EL CODIGO DE ESTADO, NO EL MENSAJE.
    -- Misma razon que en `control.fallo.sqlstate`: el mensaje cambia con el
    -- idioma del servidor y el codigo no. Clasificar leyendo el mensaje con
    -- expresiones regulares funciona hasta que alguien cambia `lc_messages`.
    ADD COLUMN IF NOT EXISTS sqlstate       text,

    -- Cuantas filas trajo la fuente. `filas` ya guarda cuantas se escribieron.
    -- La DIFERENCIA entre las dos, cruzada con el conteo de `control.fallo`,
    -- es lo que dice si un rechazo fue masivo o puntual. Con un solo numero no
    -- se puede distinguir «la fuente trajo poco» de «se rechazo casi todo».
    ADD COLUMN IF NOT EXISTS filas_leidas   bigint,

    -- El SHA del commit. Permite decir «esto empezo a fallar con tal cambio»,
    -- que es la mitad de un diagnostico y hoy hay que reconstruirlo a mano
    -- cruzando fechas con el historial de git.
    ADD COLUMN IF NOT EXISTS version_codigo text,

    -- Igual que en `control.fallo`. Sin defecto a proposito: `current_user` como
    -- DEFAULT lo llenaria tambien en los UPDATE de cierre, y quien cierra una
    -- corrida no es necesariamente quien la abrio.
    ADD COLUMN IF NOT EXISTS reportado_por  text;

COMMENT ON COLUMN control.bitacora_etl.sqlstate IS
    'Codigo SQL del error si la corrida fallo. El mensaje cambia con el idioma del servidor; el codigo no.';
COMMENT ON COLUMN control.bitacora_etl.filas_leidas IS
    'Filas que trajo la fuente. `filas` son las escritas. La diferencia, cruzada con el conteo de control.fallo por corrida_id, distingue un rechazo masivo de uno puntual.';
COMMENT ON COLUMN control.bitacora_etl.version_codigo IS
    'SHA del commit con el que corrio. NULL en las corridas anteriores a esta migracion.';

-- El DROP va antes del ADD porque **PostgreSQL no acepta `ADD CONSTRAINT IF NOT
-- EXISTS`**. Sin el, aplicar este archivo dos veces falla con «la restriccion ya
-- existe», y el criterio 3 pide justamente lo contrario.
--
-- Es el mismo par que se usa mas abajo para las otras tres restricciones. Aca
-- faltaba, y no se noto porque el aplicador guarda la suma SHA-256 de cada
-- archivo y **nunca reaplica uno ya aplicado**: la idempotencia del aplicador
-- estaba tapando la no idempotencia del archivo.
ALTER TABLE control.bitacora_etl
    DROP CONSTRAINT IF EXISTS bitacora_etl_leidas_ck;

ALTER TABLE control.bitacora_etl
    ADD CONSTRAINT bitacora_etl_leidas_ck
    CHECK (filas_leidas IS NULL OR filas_leidas >= 0);

-- --------------------------------------------------------------------------- #
-- 2 · El estado `parcial`                                                      #
-- --------------------------------------------------------------------------- #
--
-- Una carga que escribio seis distritos de ocho y fallo en el septimo **no es
-- exitosa ni es fallida**:
--
--   Marcada FALLIDA  -> quien reintente recarga los seis que ya estaban.
--   Marcada EXITOSA  -> dos distritos quedan sin dato y nadie se entera.
--
-- Es la misma distincion que D-07 hace entre un cero y un hueco: forzar dos
-- cosas distintas al mismo valor pierde justo lo que hace falta saber.
--
-- `omitida` se conserva tal cual: la puso H1.14 para una corrida que decidio no
-- correr porque la cadencia no se cumplia, y eso tambien es informacion.
--
-- Se reemplaza la restriccion en vez de agregar otra: dos CHECK sobre la misma
-- columna se contradicen en silencio, y el mensaje de error no dice cual fallo.

ALTER TABLE control.bitacora_etl
    DROP CONSTRAINT IF EXISTS bitacora_etl_estado_ck;

ALTER TABLE control.bitacora_etl
    ADD CONSTRAINT bitacora_etl_estado_ck
    CHECK (estado IN ('en_curso', 'exitosa', 'fallida', 'omitida', 'parcial'));

COMMENT ON COLUMN control.bitacora_etl.estado IS
    'en_curso mientras corre. Al cerrar: exitosa, fallida, parcial u omitida. parcial es una corrida que escribio parte y fallo en el resto; forzarla a exitosa o a fallida pierde la informacion. omitida es una que decidio no correr y dijo por que. Una fila que queda en en_curso es una corrida que murio sin cerrar.';

-- --------------------------------------------------------------------------- #
-- 3 · Coherencia entre el estado y la fecha de fin                             #
-- --------------------------------------------------------------------------- #
--
-- Hoy nada impide que una corrida quede en `exitosa` con `terminada_en` en NULL.
-- Eso rompe el diagnostico de dos maneras a la vez: la duracion se pierde -y una
-- corrida que tarda el triple de lo normal es un sintoma antes de ser un fallo-
-- y el detector de procesos muertos no la ve, porque no esta en `en_curso`.
--
-- **Se agrega como NOT VALID a proposito.**
--
-- Si alguna corrida existente ya lo viola, un CHECK normal haria fallar la
-- migracion entera y el hallazgo quedaria escondido detras de un error de
-- despliegue. Con NOT VALID la restriccion se aplica **desde ahora** y las filas
-- viejas se revisan aparte, con la consulta que esta en el verificador.
--
-- Si la validacion posterior falla, eso es un HALLAZGO sobre los datos y va a la
-- evidencia antes de corregirse. No se arregla en silencio.

ALTER TABLE control.bitacora_etl
    DROP CONSTRAINT IF EXISTS bitacora_etl_fin_coherente_ck;

ALTER TABLE control.bitacora_etl
    ADD CONSTRAINT bitacora_etl_fin_coherente_ck
    CHECK (
        (estado =  'en_curso' AND terminada_en IS NULL)
        OR
        (estado <> 'en_curso' AND terminada_en IS NOT NULL)
    ) NOT VALID;

-- El fin no puede ser anterior al inicio. Una duracion negativa en un reporte de
-- diagnostico es peor que no tener duracion: parece un dato.
ALTER TABLE control.bitacora_etl
    DROP CONSTRAINT IF EXISTS bitacora_etl_orden_temporal_ck;

ALTER TABLE control.bitacora_etl
    ADD CONSTRAINT bitacora_etl_orden_temporal_ck
    CHECK (terminada_en IS NULL OR terminada_en >= iniciada_en) NOT VALID;

-- --------------------------------------------------------------------------- #
-- 4 · La clave foranea que la 012 dejo escrita y no puso                       #
-- --------------------------------------------------------------------------- #
--
-- La 012 la dejo en un comentario porque `control.bitacora_etl` no existia
-- todavia, y ponerla habria sido crear la tabla de otra historia desde aquella
-- migracion.
--
-- **VA SIN `NOT NULL`, A PROPOSITO.** Escribir en `control.fallo` fuera de una
-- corrida es legitimo: una carga manual tambien rechaza filas, y perder ese
-- registro seria peor que no atribuirlo. NULL significa «fuera de una corrida»,
-- no «se olvidaron de anotarlo».
--
-- Que ese NULL se pueda confundir con un olvido es real, y se resuelve donde
-- corresponde: **H12.4 cuenta las filas sin atribuir ANTES de agrupar**, en vez
-- de suponer que todas la tienen. Es el criterio 12 de aceptacion.
--
-- ON DELETE RESTRICT: borrar una corrida que tiene filas rechazadas dejaria esas
-- filas hablando de algo que ya no existe. Si alguna vez hay que borrar
-- historial, se borra en orden y a proposito.
--
-- Tambien NOT VALID: si hay `corrida_id` apuntando a corridas inexistentes, es
-- un hallazgo sobre los datos y no un obstaculo para desplegar.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fallo_corrida_fk'
    ) THEN
        ALTER TABLE control.fallo
            ADD CONSTRAINT fallo_corrida_fk
            FOREIGN KEY (corrida_id)
            REFERENCES control.bitacora_etl (id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;
END
$$;

-- --------------------------------------------------------------------------- #
-- 5 · El indice del detector de procesos muertos                               #
-- --------------------------------------------------------------------------- #
--
-- H1.14 dejo `(proceso, terminada_en DESC)`, que sirve para «la ultima corrida
-- exitosa de este proceso». Para el diagnostico hace falta la contraria: **las
-- corridas que nunca terminaron**, y en esas `terminada_en` es NULL, que es
-- justo la columna por la que ese indice ordena.
--
-- Parcial porque las terminadas no interesan para esta pregunta y son la
-- mayoria: el indice queda pequeno y solo crece cuando hay algo roto.

CREATE INDEX IF NOT EXISTS bitacora_etl_en_curso_ix
    ON control.bitacora_etl (iniciada_en)
    WHERE estado = 'en_curso';

-- --------------------------------------------------------------------------- #
-- Permisos                                                                     #
-- --------------------------------------------------------------------------- #
--
-- El rol de la API pasa a poder escribir, porque el titulo de H12.1 dice
-- «pipeline **y aplicacion**» y la aplicacion registra con `proceso = 'api'`.
-- H1.14 ya anticipo ese valor en el comentario de su migracion.
--
-- Sigue sin poder borrar: minimo privilegio, igual que en H1.8. Un diagnostico
-- que puede borrar corridas puede borrar la evidencia de lo que diagnostica.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_api') THEN
        GRANT INSERT, UPDATE ON control.bitacora_etl TO geoguardian_api;
    END IF;
END
$$;

COMMIT;
