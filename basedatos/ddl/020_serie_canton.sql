-- 020 · La serie larga del canton: una fila por dia, sin distrito
--
-- Historia: H1.16 · Decision: D-47 (enmendada el 2026-09-14) · Revisa D-34, D-15
--
-- ===========================================================================
-- QUE GUARDA, Y POR QUE NO TIENE `codigo_distrito`
-- ===========================================================================
--
-- La precipitacion diaria del canton entero, desde 1950, para un solo uso:
-- contar episodios de sequia sobre la serie larga (H3.11).
--
-- **La ausencia de `codigo_distrito` no es un olvido: es el criterio CA-9 de
-- H1.16 escrito en el esquema.** D-47 decidio que Open-Meteo NO entra como
-- fuente por distrito porque su malla no los distingue, y una decision que solo
-- vive en un documento se rompe el dia que alguien tiene apuro. Aca no se puede
-- romper: no hay columna donde poner el distrito.
--
-- Si algun dia hiciera falta una serie por distrito de esta fuente, la decision
-- tendria que cambiar primero y la migracion despues. Ese es el orden.
--
-- ===========================================================================
-- POR QUE `modelo` ES OBLIGATORIO Y NO TIENE VALOR POR OMISION
-- ===========================================================================
--
-- Medido el 2026-09-14 contra la API de Open-Meteo: **`era5_land` no sirve
-- precipitacion diaria en ningun punto** -se probo Tilaran, San Jose y Madrid, y
-- los tres devuelven la temperatura completa y la lluvia entera en `null`-. La
-- serie larga sale entonces de **ERA5**, que es otra malla: 0,25 grados en vez
-- de 0,1.
--
-- Y sin el parametro `models` la API elige sola: devolvio otra celda
-- (10,509666 / -85,004425 en vez de 10,5 / -85) y datos distintos. Una serie
-- cuyo origen puede cambiar sin aviso entre dos corridas no es una serie: por
-- eso el modelo se declara en cada fila y la columna es NOT NULL.
--
-- `celda_lat` y `celda_lon` son las que **devolvio** la fuente, no las que se
-- pidieron. La diferencia es la que hace auditable el dato.

BEGIN;

CREATE TABLE IF NOT EXISTS crudo.serie_canton (
    fecha             date        PRIMARY KEY,
    precipitacion_mm  numeric(8, 2),
    modelo            text        NOT NULL,
    celda_lat         numeric(9, 6) NOT NULL,
    celda_lon         numeric(9, 6) NOT NULL,
    punto_lat         numeric(9, 6) NOT NULL,
    punto_lon         numeric(9, 6) NOT NULL,
    descargado_en     timestamptz NOT NULL DEFAULT now(),

    -- `precipitacion_mm` admite NULL a proposito: es D-07. Un dia que la fuente
    -- no trae se guarda como ausencia declarada, no como cero. Contar episodios
    -- de sequia sobre ceros inventados daria un resultado y no una medicion.
    CONSTRAINT serie_canton_precipitacion_no_negativa
        CHECK (precipitacion_mm IS NULL OR precipitacion_mm >= 0),

    -- El modelo se escribe, no se supone. `best_match` queda prohibido en el
    -- esquema porque es el nombre que la API usa cuando elige ella.
    CONSTRAINT serie_canton_modelo_declarado
        CHECK (modelo <> '' AND modelo <> 'best_match')
);

COMMENT ON TABLE crudo.serie_canton IS
    'Precipitacion diaria del canton entero desde 1950, de Open-Meteo (reanalisis ERA5). Una fila por dia y SIN codigo_distrito, que es como D-47 y el CA-9 de H1.16 quedan escritos en el esquema: esta fuente no distingue distritos y no puede entrar por distrito. Uso unico: contar episodios de sequia sobre la serie larga (H3.11).';

COMMENT ON COLUMN crudo.serie_canton.modelo IS
    'Modelo de reanalisis declarado, p. ej. era5. NOT NULL y distinto de best_match: medido el 2026-09-14, sin declararlo la API elige sola y devuelve otra celda.';

COMMENT ON COLUMN crudo.serie_canton.celda_lat IS
    'Latitud de la celda que DEVOLVIO la fuente, no la que se pidio.';

COMMENT ON COLUMN crudo.serie_canton.punto_lat IS
    'Latitud del punto representativo del canton que se consulto.';

COMMENT ON COLUMN crudo.serie_canton.precipitacion_mm IS
    'Milimetros del dia. NULL es ausencia declarada (D-07), nunca cero.';

-- Los mismos permisos que el resto de `crudo`: el ETL escribe, el lector lee, y
-- la API no entra -no tiene USAGE sobre el esquema y esta migracion no se lo da,
-- igual que la 017 no se lo dio-.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_etl') THEN
        GRANT SELECT, INSERT, UPDATE ON crudo.serie_canton TO geoguardian_etl;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_lector') THEN
        GRANT SELECT ON crudo.serie_canton TO geoguardian_lector;
    END IF;
END
$$;

COMMIT;
