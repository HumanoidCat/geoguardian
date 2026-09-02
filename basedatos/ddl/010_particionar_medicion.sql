-- 010 · Particionar crudo.medicion_diaria por anio
--
-- Historia: H1.11 (issue #43) · Rubrica: BD-1
--
-- ===========================================================================
-- PRIMERO: I-18 SEGUIA VIVO EN DOS TABLAS MAS
-- ===========================================================================
--
-- La migracion 007 quito `CURRENT_DATE` del CHECK de `analitico.riesgo`. Nadie
-- reviso el resto del esquema. Siguen con el mismo defecto:
--
--     crudo.medicion_diaria   CHECK (fecha >= '1981-01-01' AND fecha <= CURRENT_DATE)
--     crudo.foco_calor        CHECK (fecha >= '2000-01-01' AND fecha <= CURRENT_DATE)
--
-- Y los verificadores que se escribieron para atajarlo -criterio 9 de H1.13 y
-- criterio 14 de H1.9- **miran una tabla cada uno**. Un control con el alcance
-- mas angosto que el defecto da la misma tranquilidad y ninguna proteccion.
--
-- POR QUE NO ES SOLO HIGIENE, Y POR QUE ENTRA EN ESTA HISTORIA
--
-- Con ese CHECK **no se puede particionar hacia adelante**. Comprobado contra
-- PostgreSQL 16 el 2026-09-01:
--
--     CREATE TABLE m_2027 PARTITION OF m FOR VALUES FROM ('2027-01-01') ...
--       -> creada, sin una sola advertencia
--     INSERT INTO m VALUES ('50801', '2027-03-10', 1.0)
--       -> ERROR: new row for relation "m_2027" violates check constraint
--
-- La particion existe, se ve sana en el catalogo y **no acepta una sola fila**.
-- Es peor que no tenerla: `\d+` la muestra y nadie sospecha hasta que la carga
-- del proximo anio falla en produccion.
--
-- Se arreglan las dos tablas y no solo la que esta historia necesita. Dejar una
-- corregida y la otra no es como se consigue que la incidencia vuelva en tres
-- semanas con otro numero.

ALTER TABLE crudo.medicion_diaria DROP CONSTRAINT IF EXISTS medicion_fecha_ck;
ALTER TABLE crudo.medicion_diaria
    ADD CONSTRAINT medicion_fecha_ck CHECK (fecha >= DATE '1981-01-01');

ALTER TABLE crudo.foco_calor DROP CONSTRAINT IF EXISTS foco_fecha_ck;
ALTER TABLE crudo.foco_calor
    ADD CONSTRAINT foco_fecha_ck CHECK (fecha >= DATE '2000-01-01');

-- El limite inferior se conserva: es constante y atrapa el error real -una fecha
-- de 1900 por un desbordamiento o un parseo malo-. El superior lo hace cumplir
-- quien escribe, igual que el horizonte de 7 dias en `analitico.registrar_riesgo`.

-- ===========================================================================
-- EL PARTICIONADO
-- ===========================================================================
--
-- POR QUE POR ANIO Y NO POR DISTRITO
--
-- Las consultas del sistema filtran por **rango de fechas**: la matriz de
-- caracteristicas de H3.3 pide ventanas de 30 dias, el visor pide los ultimos 7,
-- y los pliegues de H3.2 son cortes temporales. Ninguna pide «todo un distrito
-- desde 1991».
--
-- Particionar por distrito daria 8 particiones de tamano parejo y **ninguna
-- consulta podria podar**, porque casi todas tocan varios distritos a la vez.
-- La poda solo sirve si la clave de particion es la que aparece en el WHERE.
--
-- POR QUE LA CLAVE PRIMARIA NO HUBO QUE TOCARLA
--
-- PostgreSQL exige que la clave de particion este **contenida** en toda
-- restriccion unica. `medicion_pk` ya era `(codigo_distrito, fecha)` y `fecha`
-- esta ahi dentro. Fue suerte, no diseno previo: si la clave hubiera sido un
-- `id` opaco, particionar habria obligado a cambiarla y con ella la idempotencia
-- de H1.1.
--
-- LA PARTICION `DEFAULT` NO ES UN ADORNO
--
-- Sin ella, una fila con una fecha fuera de todos los rangos **falla la
-- insercion**. Con ella, entra y queda localizable. Es la misma regla de H1.9:
-- se puede continuar, nunca callar. El verificador comprueba que exista y que
-- este vacia, porque una DEFAULT con filas dentro es la senal de que falta crear
-- una particion.

-- --------------------------------------------------------------------------- #
-- 1. La tabla vieja se aparta, no se borra                                     #
-- --------------------------------------------------------------------------- #
ALTER TABLE crudo.medicion_diaria RENAME TO medicion_diaria_plana;
ALTER TABLE crudo.medicion_diaria_plana RENAME CONSTRAINT medicion_pk TO medicion_plana_pk;

-- --------------------------------------------------------------------------- #
-- 2. La tabla particionada, con las mismas restricciones                       #
-- --------------------------------------------------------------------------- #
CREATE TABLE crudo.medicion_diaria (
    codigo_distrito       text NOT NULL,
    fecha                 date NOT NULL,

    temp_max_c            real,
    temp_min_c            real,
    temp_media_c          real,
    humedad_relativa_pct  real,
    viento_ms             real,
    radiacion_mj_m2       real,
    precipitacion_mm      real,

    fuente_precipitacion  text NOT NULL,
    fuente_resto          text NOT NULL,

    imputado              boolean NOT NULL DEFAULT false,
    metodo_imputacion     text    NOT NULL DEFAULT 'sin_imputar',

    descargado_en         timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT medicion_pk PRIMARY KEY (codigo_distrito, fecha),

    CONSTRAINT medicion_distrito_fk
        FOREIGN KEY (codigo_distrito) REFERENCES geo.distrito (codigo),
    CONSTRAINT medicion_fuente_precipitacion_fk
        FOREIGN KEY (fuente_precipitacion) REFERENCES crudo.fuente (codigo),
    CONSTRAINT medicion_fuente_resto_fk
        FOREIGN KEY (fuente_resto) REFERENCES crudo.fuente (codigo),

    CONSTRAINT medicion_precipitacion_ck
        CHECK (precipitacion_mm IS NULL OR precipitacion_mm >= 0),
    CONSTRAINT medicion_humedad_ck
        CHECK (humedad_relativa_pct IS NULL
               OR (humedad_relativa_pct >= 0 AND humedad_relativa_pct <= 100)),
    CONSTRAINT medicion_viento_ck
        CHECK (viento_ms IS NULL OR viento_ms >= 0),
    CONSTRAINT medicion_radiacion_ck
        CHECK (radiacion_mj_m2 IS NULL OR radiacion_mj_m2 >= 0),
    CONSTRAINT medicion_temperaturas_ck
        CHECK (temp_min_c IS NULL OR temp_max_c IS NULL OR temp_min_c <= temp_max_c),

    -- Ya sin `CURRENT_DATE`. Ver la cabecera.
    CONSTRAINT medicion_fecha_ck CHECK (fecha >= DATE '1981-01-01'),

    CONSTRAINT medicion_imputacion_ck
        CHECK (metodo_imputacion IN ('sin_imputar', 'interpolacion_lineal',
                                     'media_movil', 'climatologia_mensual'))
) PARTITION BY RANGE (fecha);

-- --------------------------------------------------------------------------- #
-- 3. Una particion por anio con dato, mas la DEFAULT                           #
-- --------------------------------------------------------------------------- #
--
-- **No se crean 50 particiones vacias por si acaso.** Cada particion es una
-- tabla real que el planificador tiene que considerar, y una decena de tablas
-- vacias es coste de planificacion sin ningun beneficio. Se crean las que tienen
-- dato, y `crudo.asegurar_particion_anual()` crea las que hagan falta despues.
CREATE TABLE crudo.medicion_diaria_futuro
    PARTITION OF crudo.medicion_diaria DEFAULT;

COMMENT ON TABLE crudo.medicion_diaria_futuro IS
    'Particion DEFAULT. Deberia estar SIEMPRE vacia: una fila aqui significa que falta crear la particion de su anio.';

CREATE OR REPLACE FUNCTION crudo.asegurar_particion_anual(p_anio integer)
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
    v_nombre text := format('medicion_diaria_%s', p_anio);
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'crudo' AND c.relname = v_nombre
    ) THEN
        RETURN format('%s ya existia', v_nombre);
    END IF;

    -- Se crea suelta y se ADJUNTA, en vez de `PARTITION OF` directo.
    --
    -- Con una particion DEFAULT presente, `CREATE TABLE ... PARTITION OF` falla
    -- si la DEFAULT tiene filas del rango nuevo. `ATTACH` hace el mismo control
    -- pero permite mover primero las filas, que es lo que se documenta abajo.
    EXECUTE format(
        'CREATE TABLE crudo.%I (LIKE crudo.medicion_diaria INCLUDING DEFAULTS INCLUDING CONSTRAINTS)',
        v_nombre);
    EXECUTE format(
        'ALTER TABLE crudo.medicion_diaria ATTACH PARTITION crudo.%I '
        'FOR VALUES FROM (%L) TO (%L)',
        v_nombre, format('%s-01-01', p_anio), format('%s-01-01', p_anio + 1));

    RETURN format('%s creada', v_nombre);
END;
$$;

COMMENT ON FUNCTION crudo.asegurar_particion_anual IS
    'Crea la particion de un anio si no existe. Idempotente: llamarla dos veces no falla.';

-- Las particiones de los anios que la ventana del proyecto cubre.
DO $$
DECLARE
    v_anio integer;
BEGIN
    FOR v_anio IN 1991..2026 LOOP
        PERFORM crudo.asegurar_particion_anual(v_anio);
    END LOOP;
END;
$$;

-- --------------------------------------------------------------------------- #
-- 4. Los datos                                                                 #
-- --------------------------------------------------------------------------- #
--
-- `INSERT ... SELECT` y no `ATTACH` de la tabla vieja: la vieja abarca todos los
-- anios, asi que no puede ser particion de ninguno. Con ~100 000 filas la copia
-- tarda menos de un segundo.
INSERT INTO crudo.medicion_diaria
SELECT codigo_distrito, fecha, temp_max_c, temp_min_c, temp_media_c,
       humedad_relativa_pct, viento_ms, radiacion_mj_m2, precipitacion_mm,
       fuente_precipitacion, fuente_resto, imputado, metodo_imputacion,
       descargado_en
FROM crudo.medicion_diaria_plana;

-- La vieja se conserva **dentro de esta transaccion** hasta despues del conteo,
-- para que una copia incompleta aborte en vez de dejar la base a medias.
DO $$
DECLARE
    v_antes bigint;
    v_despues bigint;
BEGIN
    SELECT count(*) INTO v_antes FROM crudo.medicion_diaria_plana;
    SELECT count(*) INTO v_despues FROM crudo.medicion_diaria;
    IF v_antes <> v_despues THEN
        RAISE EXCEPTION
            'la copia perdio filas: % en la plana, % en la particionada', v_antes, v_despues;
    END IF;
    RAISE NOTICE '% filas migradas a la tabla particionada', v_despues;
END;
$$;

DROP TABLE crudo.medicion_diaria_plana;

-- --------------------------------------------------------------------------- #
-- 5. Comentarios y permisos, que no sobreviven al CREATE nuevo                  #
-- --------------------------------------------------------------------------- #
COMMENT ON TABLE crudo.medicion_diaria IS
    'Series climaticas diarias tal como llegan. Una fila por distrito y dia, huecos incluidos. Particionada por anio desde H1.11.';
COMMENT ON COLUMN crudo.medicion_diaria.precipitacion_mm IS
    'De CHIRPS. NULL es ausencia de dato; 0 es un dia sin lluvia. No son lo mismo.';
COMMENT ON COLUMN crudo.medicion_diaria.fuente_precipitacion IS
    'Nunca se completa un hueco de CHIRPS con un valor de POWER: no son comparables.';
COMMENT ON COLUMN crudo.medicion_diaria.descargado_en IS
    'Momento de la descarga, para poder fechar una serie sin abrir el archivo de procedencia.';

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_etl') THEN
        GRANT SELECT, INSERT, UPDATE ON crudo.medicion_diaria TO geoguardian_etl;
        GRANT EXECUTE ON FUNCTION crudo.asegurar_particion_anual TO geoguardian_etl;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_api') THEN
        GRANT SELECT ON crudo.medicion_diaria TO geoguardian_api;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_lector') THEN
        GRANT SELECT ON crudo.medicion_diaria TO geoguardian_lector;
    END IF;
END;
$$;
