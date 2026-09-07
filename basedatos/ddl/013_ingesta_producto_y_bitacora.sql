-- 013 · Productos preliminares declarados y bitacora minima de corridas
--
-- Historia: H1.14 (Alejandro, por D-38) · Rubrica: BD-1 · Excepcion: docs/07
--
-- ===========================================================================
-- TRES COSAS, Y POR QUE VAN JUNTAS
-- ===========================================================================
--
-- La ingesta periodica (`backend/etl/ingestar.py`) trae cada dato en dos
-- versiones que **no son el mismo dato** (D-26), y la base tiene que poder
-- decir cual es cual. Eso son los puntos 1 y 2. El 3 es donde queda escrito
-- que corrio, con que ventana y que trajo, para que /salud deje de tener
-- `ultima_ingesta` en nulo.
--
-- ===========================================================================
-- 1. PRECIPITACION: `chirp` AL LADO DE `chirps`
-- ===========================================================================
--
-- ClimateSERV sirve el CHIRPS final (tipo 0, con estaciones; llega 21-51 dias
-- despues, medido el 2026-09-03: 33 dias) y el **CHIRP** (tipo 90): el mismo
-- algoritmo satelital **sin** la correccion por estaciones, que sale antes.
-- No sirve el "preliminar" que nombra D-26; ese lo publica CHC en GeoTIFF.
--
-- `chirp` entra como fuente propia en `crudo.fuente`, asi que
-- `fuente_precipitacion` puede decir 'chirp' sin tocar la restriccion de H1.1.
-- La regla de reemplazo vive en el SQL de la ingesta, no aca: el final
-- reemplaza al preliminar y el preliminar nunca pisa un valor del final.

INSERT INTO crudo.fuente (codigo, nombre, resolucion, descripcion)
VALUES
    ('chirp',
     'CHIRP via ClimateSERV (sin estaciones)',
     '0.05 grados',
     'La estimacion satelital de CHIRPS antes de mezclarla con estaciones. '
     'Sale dias despues del dato, no semanas. Producto preliminar declarado por '
     'H1.14: lo reemplaza el CHIRPS final cuando llega, y nunca al reves.')
ON CONFLICT (codigo) DO UPDATE SET
    nombre      = EXCLUDED.nombre,
    resolucion  = EXCLUDED.resolucion,
    descripcion = EXCLUDED.descripcion;

-- ===========================================================================
-- 2. FOCOS: LA VERSION NRT DE CADA SENSOR
-- ===========================================================================
--
-- FIRMS sirve MODIS y VIIRS en near-real-time (~3 h) y en standard processing
-- (semanas despues, con geolocalizacion y confianza reprocesadas). El archivo
-- por pais de H1.2 es SP. La API por area, que es la unica que cubre el anio
-- en curso, sirve las dos. El NRT entra con su propio codigo de producto y la
-- ingesta lo borra y lo reemplaza por el SP del mismo dia cuando este existe.
--
-- `desde_anio` es el primer anio con NRT **en este proyecto**, no en la
-- fuente: el archivo historico ya cubre hasta 2024 en SP.

INSERT INTO crudo.producto_foco (codigo, nombre, resolucion, desde_anio, descripcion)
VALUES
    ('modis-nrt',
     'MODIS Terra y Aqua, coleccion 6.1, near real time',
     '1 km',
     2025,
     'Version NRT del producto modis, por la API por area de FIRMS. Preliminar: '
     'la ingesta lo reemplaza por modis (SP) cuando el SP cubre el dia.'),
    ('viirs-snpp-nrt',
     'VIIRS Suomi-NPP, banda I, 375 m, near real time',
     '375 m',
     2025,
     'Version NRT del producto viirs-snpp, por la API por area de FIRMS. '
     'Preliminar: la ingesta lo reemplaza por viirs-snpp (SP) cuando el SP cubre el dia.')
ON CONFLICT (codigo) DO UPDATE SET
    nombre      = EXCLUDED.nombre,
    resolucion  = EXCLUDED.resolucion,
    desde_anio  = EXCLUDED.desde_anio,
    descripcion = EXCLUDED.descripcion;

-- La 005 dice «la confianza entera es solo de MODIS». Sigue siendo cierto: el
-- NRT de MODIS tambien la trae como entero. La restriccion se reescribe para
-- nombrar las dos versiones, y nada mas cambia.
ALTER TABLE crudo.foco_calor DROP CONSTRAINT IF EXISTS foco_bruta_solo_modis_ck;
ALTER TABLE crudo.foco_calor
    ADD CONSTRAINT foco_bruta_solo_modis_ck
    CHECK (producto IN ('modis', 'modis-nrt') OR confianza_bruta IS NULL);

-- ===========================================================================
-- 3. LA BITACORA DE CORRIDAS, EN SU FORMA MINIMA
-- ===========================================================================
--
-- La 012 dejo dicho que `control.bitacora_etl` la crea H12.1 (hoy de Luna,
-- por D-37). H1.14 llego primero a necesitarla, y esto es lo acordado por
-- escrito con Luna (gestion/nota-luna-h114-y-h121-2026-09-03.md): H1.14 trae
-- **la forma minima**, con `IF NOT EXISTS`, y H12.1 la extiende con
-- `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` para centralizar el resto de los
-- logs. Ninguna de las dos migraciones pisa a la otra en ningun orden.
--
-- La clave foranea desde `control.fallo.corrida_id` sigue siendo de H12.1,
-- como prometio la 012. Aca no se toca `control.fallo`.

CREATE TABLE IF NOT EXISTS control.bitacora_etl (
    id             bigint GENERATED ALWAYS AS IDENTITY,

    -- Que corrio: 'ingesta.incendio', 'ingesta.lluvia_intensa', 'ingesta.sequia',
    -- y lo que H12.1 sume ('api', 'pipeline', ...). Texto, no enum: se agregan
    -- procesos sin migrar.
    proceso        text        NOT NULL,
    iniciada_en    timestamptz NOT NULL DEFAULT now(),
    terminada_en   timestamptz,

    -- 'omitida' es una corrida que decidio no correr (cadencia no cumplida o
    -- ya al dia) y lo dejo dicho. Es distinto de 'fallida'.
    estado         text        NOT NULL,

    ventana_desde  date,
    ventana_hasta  date,
    producto       text,
    filas          integer,
    mensaje        text,

    CONSTRAINT bitacora_etl_pk        PRIMARY KEY (id),
    CONSTRAINT bitacora_etl_estado_ck
        CHECK (estado IN ('en_curso', 'exitosa', 'fallida', 'omitida')),
    CONSTRAINT bitacora_etl_ventana_ck
        CHECK (ventana_desde IS NULL OR ventana_hasta IS NULL OR ventana_desde <= ventana_hasta),
    CONSTRAINT bitacora_etl_filas_ck
        CHECK (filas IS NULL OR filas >= 0)
);

COMMENT ON TABLE control.bitacora_etl IS
    'Una fila por corrida de un proceso del ETL: que, cuando, con que ventana y producto, cuantas filas, y como termino. Forma minima de H1.14; H12.1 la extiende.';
COMMENT ON COLUMN control.bitacora_etl.estado IS
    'en_curso mientras corre; exitosa, fallida u omitida al cerrar. Una fila que queda en_curso es una corrida que murio sin cerrar.';

-- «La ultima corrida exitosa de este proceso» es la consulta que decide la
-- ventana de cada corrida y la que /salud va a hacer.
CREATE INDEX IF NOT EXISTS bitacora_etl_proceso_ix
    ON control.bitacora_etl (proceso, terminada_en DESC);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_etl') THEN
        GRANT SELECT, INSERT, UPDATE ON control.bitacora_etl TO geoguardian_etl;
        GRANT SELECT, DELETE ON crudo.foco_calor TO geoguardian_etl;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_api') THEN
        GRANT SELECT ON control.bitacora_etl TO geoguardian_api;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_lector') THEN
        GRANT SELECT ON control.bitacora_etl TO geoguardian_lector;
    END IF;
END;
$$;
