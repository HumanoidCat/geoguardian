-- 002 · Tablas territoriales del esquema geo
--
-- Historia: H1.3 (issue #37) · Rubrica: BD-1 (modelo normalizado a 3FN)
--
-- Los esquemas ya existen: los crea infra/docker/init-db/01-extensiones.sql.
-- Aqui van solo las tablas.
--
--
-- POR QUE TRES TABLAS Y NO UNA
--
-- El codigo de distrito no es un identificador opaco. En '50801':
--
--     5    provincia (Guanacaste)
--     08   canton    (Tilaran)
--     01   distrito
--
-- Si el nombre de la provincia y el del canton vivieran dentro de la tabla de
-- distritos, dependerian de una PARTE del codigo, no de la clave completa. Eso
-- es una dependencia transitiva y rompe la tercera forma normal. Ademas
-- permitiria que el mismo canton apareciera escrito de ocho formas distintas,
-- una por distrito.
--
-- Separadas en tres tablas, cada nombre se guarda una sola vez y depende de la
-- clave completa de su propia tabla.
--
--
-- SOBRE geo.distrito.codigo_canton
--
-- Es derivable de los tres primeros caracteres de `codigo`, asi que a primera
-- vista parece redundante. No lo es en el sentido de la normalizacion: es un
-- atributo que depende de la clave completa de la tabla, que es justamente lo
-- que la tercera forma normal exige. Existe como columna propia porque una clave
-- foranea necesita una columna real sobre la que declararse.
--
-- Lo que si haria falta vigilar es que ambos valores no se desincronicen. De eso
-- se encarga la restriccion distrito_codigo_canton_ck, mas abajo.
--
--
-- SOBRE LOS SISTEMAS DE COORDENADAS
--
-- Las geometrias se almacenan en EPSG:4326 porque el contrato Distrito.geometria
-- lo exige literalmente: 'Poligono GeoJSON en EPSG:4326, listo para Leaflet'.
--
-- Las areas NO se calculan sobre 4326: sus unidades son grados y un area en
-- grados no es una superficie. Se calculan reproyectando a EPSG:8908
-- (CR-SIRGAS / CRTM05), que es el sistema nativo de la capa del SNIT de donde
-- salen estos datos, y esta en metros.
--
--
-- LO QUE NO VA AQUI
--
-- Indices espaciales y compuestos: son la historia H1.12, que tiene que poder
-- medir el plan de consulta antes y despues de agregarlos. Crearlos aqui le
-- quitaria a esa historia su propia evidencia.
--
-- Roles y permisos de minimo privilegio: historia H1.8.

-- --------------------------------------------------------------------------- --
-- Provincia                                                                     --
-- --------------------------------------------------------------------------- --

CREATE TABLE IF NOT EXISTS geo.provincia (
    codigo  smallint NOT NULL,
    nombre  text     NOT NULL,

    CONSTRAINT provincia_pk         PRIMARY KEY (codigo),
    CONSTRAINT provincia_nombre_unq UNIQUE (nombre),
    CONSTRAINT provincia_codigo_ck  CHECK (codigo BETWEEN 1 AND 7),
    CONSTRAINT provincia_nombre_ck  CHECK (btrim(nombre) <> '' AND nombre = btrim(nombre))
);

COMMENT ON TABLE geo.provincia IS
    'Provincias de Costa Rica. Fuente: SNIT, capa IGN_5_CO:limitedistrital_5k.';

-- --------------------------------------------------------------------------- --
-- Canton                                                                        --
-- --------------------------------------------------------------------------- --

CREATE TABLE IF NOT EXISTS geo.canton (
    codigo           smallint NOT NULL,
    codigo_provincia smallint NOT NULL,
    nombre           text     NOT NULL,

    -- La geometria del canton no la pide el contrato. Se guarda porque el
    -- criterio de aceptacion CA-7 contrasta la suma de las areas de los ocho
    -- distritos contra el area del canton: teniendola aqui, esa comprobacion es
    -- una consulta SQL que cualquier revisor puede repetir, en vez de depender
    -- de una peticion a un servicio externo en el momento de verificar.
    geometria        geometry(MultiPolygon, 4326),

    CONSTRAINT canton_pk            PRIMARY KEY (codigo),
    CONSTRAINT canton_provincia_fk  FOREIGN KEY (codigo_provincia)
                                    REFERENCES geo.provincia (codigo),
    CONSTRAINT canton_nombre_unq    UNIQUE (codigo_provincia, nombre),
    CONSTRAINT canton_codigo_ck     CHECK (codigo BETWEEN 101 AND 799),
    CONSTRAINT canton_nombre_ck     CHECK (btrim(nombre) <> '' AND nombre = btrim(nombre)),

    -- Los tres digitos del codigo de canton empiezan por el codigo de provincia.
    CONSTRAINT canton_codigo_provincia_ck
        CHECK (codigo / 100 = codigo_provincia)
);

COMMENT ON TABLE geo.canton IS
    'Cantones. La geometria sostiene el contraste de areas del criterio CA-7 de H1.3.';

-- --------------------------------------------------------------------------- --
-- Distrito                                                                      --
-- --------------------------------------------------------------------------- --

CREATE TABLE IF NOT EXISTS geo.distrito (
    -- Texto y no entero: el contrato declara `codigo: str`, y un entero perderia
    -- un eventual cero a la izquierda si alguna vez se usa otra codificacion.
    codigo        text     NOT NULL,

    codigo_canton smallint NOT NULL,

    -- Se guarda tal como llega de la fuente oficial: sin pasar a mayusculas y
    -- sin quitar tildes. 'Libano' y 'Tilaran' se escriben 'Libano' y 'Tilaran'
    -- con tilde, y asi se muestran en el visor.
    nombre        text     NOT NULL,

    -- Calculada desde la geometria reproyectada a EPSG:8908. No viene de la
    -- fuente: la capa del SNIT no publica un atributo de area utilizable.
    area_km2      numeric(12, 4) NOT NULL,

    -- Nulo mientras no haya fuente censal cargada. El contrato lo declara
    -- `int | None` con la nota 'None si no hay dato censal'. Rellenarlo con cero
    -- lo haria indistinguible de un distrito deshabitado.
    poblacion     integer,

    geometria     geometry(MultiPolygon, 4326) NOT NULL,

    CONSTRAINT distrito_pk         PRIMARY KEY (codigo),
    CONSTRAINT distrito_canton_fk  FOREIGN KEY (codigo_canton)
                                   REFERENCES geo.canton (codigo),
    CONSTRAINT distrito_nombre_unq UNIQUE (codigo_canton, nombre),

    CONSTRAINT distrito_codigo_ck    CHECK (codigo ~ '^[0-9]{5}$'),
    CONSTRAINT distrito_nombre_ck    CHECK (btrim(nombre) <> '' AND nombre = btrim(nombre)),
    CONSTRAINT distrito_area_ck      CHECK (area_km2 > 0),
    CONSTRAINT distrito_poblacion_ck CHECK (poblacion IS NULL OR poblacion >= 0),

    -- Impide que el codigo del distrito y su clave foranea se desincronicen:
    -- '50801' solo puede pertenecer al canton 508.
    CONSTRAINT distrito_codigo_canton_ck
        CHECK (substr(codigo, 1, 3)::smallint = codigo_canton)
);

COMMENT ON TABLE geo.distrito IS
    'Distritos. Clave: codigo oficial DTA del IGN. Geometria en EPSG:4326 para Leaflet.';
COMMENT ON COLUMN geo.distrito.area_km2 IS
    'Calculada con ST_Area(ST_Transform(geometria, 8908)) / 1000000. No viene de la fuente.';
COMMENT ON COLUMN geo.distrito.poblacion IS
    'NULL mientras no exista fuente censal cargada. Nunca 0 como relleno.';
