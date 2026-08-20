-- 004 · Series climaticas diarias en el esquema crudo
--
-- Historia: H1.1 (issue #35) · Rubrica: BD-1
--
-- POR QUE EL NUMERO 004
--
-- El documento de criterios de H1.1 reservaba el 003, pero H1.8 arranco antes y
-- se lo quedo. Los numeros se asignan al subir, no al planear, y una migracion
-- aplicada no se renumera nunca.
--
-- POR QUE EN `crudo`
--
-- El comentario de infra/docker/init-db/01-extensiones.sql define ese esquema
-- como "datos tal como llegan, solo escribe el ETL", que es exactamente esto. Los
-- indices derivados y las estimaciones van en `analitico`, y los calcula otra
-- historia.
--
-- DOS FUENTES CONVIVIENDO
--
-- Por la decision D-15, la precipitacion viene de CHIRPS y el resto de POWER. Son
-- productos distintos y no son comparables entre si: el 1 de enero de 2024, POWER
-- reporta 0,0 mm en Tronadora y CHIRPS reporta 18,72 mm en el mismo lugar.
--
-- Por eso cada fila declara de que fuente vino su precipitacion. Sin esa columna,
-- dentro de un mes nadie puede auditar que dato salio de donde, y la regla de no
-- completar un hueco de CHIRPS con un valor de POWER seria imposible de verificar.
--
-- LOS NULOS SON DATOS
--
-- Todas las variables admiten nulo a proposito. El contrato MedicionDiaria las
-- declara opcionales porque las series reales tienen huecos, y la cabecera de
-- contratos/esquemas.py lo dice sin rodeos: cero milimetros de lluvia es una
-- medicion, ausencia de dato no lo es. Confundirlos arruina el modelo y nadie lo
-- detecta hasta que es tarde.
--
-- SIN INDICES
--
-- Ni espaciales ni compuestos. Son las historias H1.11 y H1.12, que necesitan
-- medir el plan de consulta antes y despues de crearlos. Crearlos aqui les
-- quitaria su evidencia.

-- --------------------------------------------------------------------------- --
-- Fuentes de datos                                                             --
-- --------------------------------------------------------------------------- --
--
-- Tabla de referencia en vez de un texto libre en cada fila: asi el nombre de la
-- fuente se escribe una sola vez y no aparece como 'CHIRPS', 'chirps' y
-- 'Chirps' en la misma columna.

CREATE TABLE IF NOT EXISTS crudo.fuente (
    codigo      text NOT NULL,
    nombre      text NOT NULL,
    resolucion  text NOT NULL,
    descripcion text NOT NULL,

    CONSTRAINT fuente_pk        PRIMARY KEY (codigo),
    CONSTRAINT fuente_codigo_ck CHECK (codigo ~ '^[a-z0-9_]{2,20}$')
);

INSERT INTO crudo.fuente (codigo, nombre, resolucion, descripcion)
VALUES
    ('power',
     'NASA POWER',
     '0.5 x 0.625 grados',
     'Reanalisis MERRA-2. Temperatura, humedad, viento y radiacion. Su celda '
     'cubre todo el canton, asi que estas variables no distinguen entre '
     'distritos. Declarado como limitacion en D-15.'),
    ('chirps',
     'CHIRPS 2.0 via ClimateSERV',
     '0.05 grados',
     'Satelite mas estaciones. Solo precipitacion. Cada distrito cae en una '
     'celda propia, que es el motivo de la decision D-15.')
ON CONFLICT (codigo) DO UPDATE SET
    nombre      = EXCLUDED.nombre,
    resolucion  = EXCLUDED.resolucion,
    descripcion = EXCLUDED.descripcion;

COMMENT ON TABLE crudo.fuente IS
    'Origenes de datos climaticos. Ver la decision D-15 sobre la fuente hibrida.';

-- --------------------------------------------------------------------------- --
-- Mediciones diarias                                                           --
-- --------------------------------------------------------------------------- --

CREATE TABLE IF NOT EXISTS crudo.medicion_diaria (
    codigo_distrito       text NOT NULL,
    fecha                 date NOT NULL,

    -- De POWER. Nulos donde la fuente no tiene dato.
    temp_max_c            real,
    temp_min_c            real,
    temp_media_c          real,
    humedad_relativa_pct  real,
    viento_ms             real,
    radiacion_mj_m2       real,

    -- De CHIRPS. Separada del resto porque viene de otro producto.
    precipitacion_mm      real,

    -- Que fuente aporto cada parte. Con dos fuentes conviviendo, sin esto no se
    -- puede auditar nada despues.
    fuente_precipitacion  text NOT NULL,
    fuente_resto          text NOT NULL,

    -- H1.1 no imputa nada: los huecos se conservan. Las columnas existen porque
    -- el contrato las declara, y H1.4 es la que las va a usar.
    imputado              boolean NOT NULL DEFAULT false,
    metodo_imputacion     text    NOT NULL DEFAULT 'sin_imputar',

    descargado_en         timestamptz NOT NULL DEFAULT now(),

    -- Clave natural. Es la que sostiene la idempotencia: cargar dos veces el
    -- mismo rango actualiza, no duplica.
    CONSTRAINT medicion_pk PRIMARY KEY (codigo_distrito, fecha),

    CONSTRAINT medicion_distrito_fk
        FOREIGN KEY (codigo_distrito) REFERENCES geo.distrito (codigo),
    CONSTRAINT medicion_fuente_precipitacion_fk
        FOREIGN KEY (fuente_precipitacion) REFERENCES crudo.fuente (codigo),
    CONSTRAINT medicion_fuente_resto_fk
        FOREIGN KEY (fuente_resto) REFERENCES crudo.fuente (codigo),

    -- Rangos fisicamente posibles. Son las mismas restricciones que el contrato
    -- declara con Field(ge=...), aplicadas tambien en la base para que un error
    -- de carga no dependa de que alguien recuerde validar en Python.
    CONSTRAINT medicion_precipitacion_ck
        CHECK (precipitacion_mm IS NULL OR precipitacion_mm >= 0),
    CONSTRAINT medicion_humedad_ck
        CHECK (humedad_relativa_pct IS NULL
               OR (humedad_relativa_pct >= 0 AND humedad_relativa_pct <= 100)),
    CONSTRAINT medicion_viento_ck
        CHECK (viento_ms IS NULL OR viento_ms >= 0),
    CONSTRAINT medicion_radiacion_ck
        CHECK (radiacion_mj_m2 IS NULL OR radiacion_mj_m2 >= 0),

    -- La minima no puede superar a la maxima. Si ambas existen y se invierten,
    -- hay un error de mapeo de parametros que conviene atajar al insertar.
    CONSTRAINT medicion_temperaturas_ck
        CHECK (temp_min_c IS NULL OR temp_max_c IS NULL OR temp_min_c <= temp_max_c),

    -- Ventana declarada en el documento de criterios. El limite inferior es el
    -- primer anio que cubren las dos fuentes; el superior evita que una fecha
    -- futura entre por un error de calculo del rango.
    CONSTRAINT medicion_fecha_ck
        CHECK (fecha >= DATE '1981-01-01' AND fecha <= CURRENT_DATE),

    CONSTRAINT medicion_imputacion_ck
        CHECK (metodo_imputacion IN ('sin_imputar', 'interpolacion_lineal',
                                     'media_movil', 'climatologia_mensual'))
);

COMMENT ON TABLE crudo.medicion_diaria IS
    'Series climaticas diarias tal como llegan. Una fila por distrito y dia, huecos incluidos.';
COMMENT ON COLUMN crudo.medicion_diaria.precipitacion_mm IS
    'De CHIRPS. NULL es ausencia de dato; 0 es un dia sin lluvia. No son lo mismo.';
COMMENT ON COLUMN crudo.medicion_diaria.fuente_precipitacion IS
    'Nunca se completa un hueco de CHIRPS con un valor de POWER: no son comparables.';
COMMENT ON COLUMN crudo.medicion_diaria.descargado_en IS
    'Momento de la descarga, para poder fechar una serie sin abrir el archivo de procedencia.';
