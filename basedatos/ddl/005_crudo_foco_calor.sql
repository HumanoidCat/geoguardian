-- 005 · Focos de calor en el esquema crudo
--
-- Historia: H1.2 (issue #36) · Rubrica: BD-1
--
-- QUE GUARDA
--
-- Las detecciones de FIRMS que caen dentro del canton de Tilaran, 2001-2024. Son
-- 242 en veinticuatro anios: la medicion que cerro el riesgo R16. Ver
-- docs/evidencias/bases-de-datos/H1.2-focos-calor.md.
--
-- DOS PRODUCTOS QUE NO SON COMPARABLES
--
-- MODIS desde 2000 con pixel de 1 km, y VIIRS S-NPP desde 2012 con pixel de
-- 375 m. Entra VIIRS por la decision D-25: sacarlo cuesta la mitad de las
-- ventanas positivas, de 38, 33 y 34 se baja a 20, 18 y 18, y con veinte no se
-- valida nada.
--
-- Pero los dos productos no miden lo mismo:
--
--   2001-2011, solo MODIS:    69 focos / 11 anios =  6,3 por anio
--   2012-2024, MODIS + VIIRS: 173 focos / 13 anios = 13,3 por anio
--
-- El salto de 2,1 veces es del sensor, no del clima. Por eso cada fila declara de
-- que producto vino, y por eso ninguna variable de tendencia temporal entra al
-- modelo de incendio: seria la via por la que el cambio de instrumento se cuela
-- como senal climatica. D-25.
--
-- LOS NULOS SON DATOS, Y LA AUSENCIA DE FOCO NO ES UN NULO
--
-- Esta tabla guarda detecciones, no dias. Un dia sin fila es un dia sin foco
-- detectado, que es un CERO y no un hueco: FIRMS informa ausencia de focos, no
-- ausencia de dato. Es la distincion de D-22. El conteo por ventana lo calcula
-- quien lo necesite, no esta tabla.
--
-- SIN INDICES
--
-- Ni espaciales ni compuestos. Son H1.11 y H1.12, que necesitan medir el plan de
-- consulta antes y despues de crearlos.

-- --------------------------------------------------------------------------- --
-- Productos                                                                    --
-- --------------------------------------------------------------------------- --
--
-- Tabla de referencia por el mismo motivo que crudo.fuente en la migracion 004:
-- para que el nombre del producto se escriba una vez y no aparezca como
-- 'MODIS', 'modis' y 'Modis' en la misma columna.

CREATE TABLE IF NOT EXISTS crudo.producto_foco (
    codigo      text NOT NULL,
    nombre      text NOT NULL,
    resolucion  text NOT NULL,
    desde_anio  smallint NOT NULL,
    descripcion text NOT NULL,

    CONSTRAINT producto_foco_pk        PRIMARY KEY (codigo),
    CONSTRAINT producto_foco_codigo_ck CHECK (codigo ~ '^[a-z0-9_-]{2,20}$')
);

INSERT INTO crudo.producto_foco (codigo, nombre, resolucion, desde_anio, descripcion)
VALUES
    ('modis',
     'MODIS Terra y Aqua, coleccion 6.1',
     '1 km',
     2000,
     'Satelites Terra desde 2000 y Aqua desde 2002. Confianza como entero de 0 a '
     '100. Aporta 94 de los 242 focos del canton.'),
    ('viirs-snpp',
     'VIIRS Suomi-NPP, banda I, 375 m',
     '375 m',
     2012,
     'Desde el 20 de enero de 2012. Detecta fuegos mas pequenos que MODIS por su '
     'mayor resolucion, y por eso el conteo salta 2,1 veces al entrar. Confianza '
     'como categoria, no como numero. Aporta 148 de los 242.')
ON CONFLICT (codigo) DO UPDATE SET
    nombre      = EXCLUDED.nombre,
    resolucion  = EXCLUDED.resolucion,
    desde_anio  = EXCLUDED.desde_anio,
    descripcion = EXCLUDED.descripcion;

COMMENT ON TABLE crudo.producto_foco IS
    'Productos de FIRMS. Su resolucion distinta es la causa del salto de 2,1x en 2012. Ver D-25.';

-- --------------------------------------------------------------------------- --
-- Focos de calor                                                               --
-- --------------------------------------------------------------------------- --

CREATE TABLE IF NOT EXISTS crudo.foco_calor (
    -- Clave natural. Una deteccion queda identificada por donde, cuando y con que
    -- instrumento se vio. Dos satelites pueden ver el mismo fuego en el mismo
    -- momento desde orbitas distintas, y son dos detecciones, no una repetida:
    -- por eso el satelite entra en la clave.
    producto          text NOT NULL,
    satelite          text NOT NULL,
    fecha             date NOT NULL,
    hora_utc          smallint NOT NULL,
    latitud           double precision NOT NULL,
    longitud          double precision NOT NULL,

    -- Distrito al que pertenece. NULO si cae fuera de los ocho, que el contrato
    -- FocoCalor admite explicitamente. Lo asigna el cargador con ST_Contains, no
    -- el extractor: el contrato dice que el analisis espacial ocurre en la capa
    -- que conoce las geometrias.
    codigo_distrito   text,

    -- CONFIANZA
    --
    -- Categorica porque es el unico campo comparable entre los dos productos. Se
    -- convierte hacia lo grueso y nunca hacia lo fino: los 0 a 100 de MODIS se
    -- pueden colapsar a tres clases, pero las tres clases de VIIRS no se pueden
    -- expandir a un numero sin inventar precision que la fuente no da.
    --
    -- Los cortes NO son criterio del equipo. Salen de la Tabla 10 del manual
    -- oficial del producto:
    --
    --   0 %  <= C <  30 %   low
    --   30 % <= C <  80 %   nominal
    --   80 % <= C <= 100 %  high
    --
    --   Giglio, Schroeder, Hall y Justice. MODIS Collection 6 Active Fire
    --   Product User's Guide, Revision C. University of Maryland, diciembre 2020.
    confianza         text NOT NULL,

    -- El entero original de MODIS. Nulo en VIIRS, que no lo tiene. No se descarta
    -- un dato que existe solo porque el otro producto no lo tenga.
    confianza_bruta   smallint,

    -- BRILLO
    --
    -- Temperatura de brillo en kelvin. Las bandas se emparejan por region
    -- espectral, verificado en la documentacion de cada producto:
    --
    --   infrarrojo medio:  MODIS canal 21/22 (3,9 a 4 um)  <->  VIIRS I-4 (3,55 a 3,93 um)
    --   infrarrojo largo:  MODIS canal 31 (11 um)          <->  VIIRS I-5
    --
    -- ADVERTENCIA, y es la razon de que exista banda_origen: emparejar la banda
    -- NO vuelve comparables los valores. La temperatura de brillo se integra
    -- sobre el pixel, y el pixel mide 1 km en MODIS y 375 m en VIIRS. El mismo
    -- incendio ocupa una fraccion mucho mayor de un pixel de 375 m, asi que lee
    -- mas caliente en VIIRS aunque el fuego sea identico.
    --
    -- Es el salto de 2,1x otra vez, ahora en la magnitud en vez de en la
    -- frecuencia. NO usar esta columna como una sola variable continua sobre las
    -- dos eras.
    brillo_k          real,
    brillo_largo_k    real,
    banda_origen      text NOT NULL,

    -- Potencia radiativa del fuego, en megavatios. La trae la fuente y se guarda
    -- porque descartarla ahora obligaria a recargar despues.
    frp_mw            real,

    -- Tipo inferido por FIRMS. Los 242 del canton son 0, fuego de vegetacion: el
    -- volcan Arenal no contamina la serie, cosa que habia que comprobar.
    tipo              smallint,

    -- De dia o de noche. Cambia la sensibilidad del algoritmo de deteccion.
    dia_noche         char(1),

    descargado_en     timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT foco_pk PRIMARY KEY (producto, satelite, fecha, hora_utc, latitud, longitud),

    CONSTRAINT foco_producto_fk
        FOREIGN KEY (producto) REFERENCES crudo.producto_foco (codigo),
    CONSTRAINT foco_distrito_fk
        FOREIGN KEY (codigo_distrito) REFERENCES geo.distrito (codigo),

    CONSTRAINT foco_confianza_ck
        CHECK (confianza IN ('baja', 'nominal', 'alta')),
    CONSTRAINT foco_confianza_bruta_ck
        CHECK (confianza_bruta IS NULL
               OR (confianza_bruta >= 0 AND confianza_bruta <= 100)),

    -- Coherencia entre las dos confianzas, con los cortes de la Tabla 10. Si
    -- alguien recalcula la categoria con otro criterio, esto lo detiene.
    CONSTRAINT foco_confianza_coherente_ck
        CHECK (confianza_bruta IS NULL
               OR (confianza = 'baja'    AND confianza_bruta <  30)
               OR (confianza = 'nominal' AND confianza_bruta >= 30 AND confianza_bruta < 80)
               OR (confianza = 'alta'    AND confianza_bruta >= 80)),

    -- Solo MODIS trae el entero. Si apareciera en VIIRS, algo se mezclo.
    CONSTRAINT foco_bruta_solo_modis_ck
        CHECK (producto = 'modis' OR confianza_bruta IS NULL),

    CONSTRAINT foco_banda_origen_ck
        CHECK (banda_origen IN ('modis_21_22', 'viirs_i4')),
    CONSTRAINT foco_brillo_ck
        CHECK (brillo_k IS NULL OR brillo_k > 0),
    CONSTRAINT foco_frp_ck
        CHECK (frp_mw IS NULL OR frp_mw >= 0),
    CONSTRAINT foco_tipo_ck
        CHECK (tipo IS NULL OR tipo BETWEEN 0 AND 3),
    CONSTRAINT foco_dia_noche_ck
        CHECK (dia_noche IS NULL OR dia_noche IN ('D', 'N')),

    -- Coordenadas dentro del rango del canton, con holgura. Una deteccion fuera
    -- de aqui significa que el filtro por caja envolvente fallo.
    CONSTRAINT foco_latitud_ck
        CHECK (latitud BETWEEN 10.2 AND 10.8),
    CONSTRAINT foco_longitud_ck
        CHECK (longitud BETWEEN -85.2 AND -84.6),

    CONSTRAINT foco_hora_ck
        CHECK (hora_utc BETWEEN 0 AND 2359),

    -- Ventana del archivo historico por pais. FIRMS lo publica hasta 2024: para
    -- el anio en curso hace falta la clave y la API, con su tope de cinco dias
    -- por peticion. Ver la evidencia de H1.2.
    CONSTRAINT foco_fecha_ck
        CHECK (fecha >= DATE '2000-01-01' AND fecha <= CURRENT_DATE)
);

COMMENT ON TABLE crudo.foco_calor IS
    'Detecciones de FIRMS dentro del canton. Un dia sin fila es un dia sin foco, no un hueco.';
COMMENT ON COLUMN crudo.foco_calor.confianza IS
    'Cortes de la Tabla 10 del MODIS C6 User Guide rev. C: <30 baja, 30-80 nominal, >=80 alta.';
COMMENT ON COLUMN crudo.foco_calor.brillo_k IS
    'NO comparable entre productos: el pixel mide 1 km en MODIS y 375 m en VIIRS.';
COMMENT ON COLUMN crudo.foco_calor.codigo_distrito IS
    'NULO si la deteccion cae fuera de los ocho distritos. Lo asigna el cargador con ST_Contains.';
