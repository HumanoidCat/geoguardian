-- Extensiones y esquemas base.
--
-- ATENCION: este script corre UNA SOLA VEZ, cuando el volumen de datos esta
-- vacio. Si se modifica despues, hay que borrar el volumen para que vuelva a
-- ejecutarse:
--
--     docker compose down -v      <-- BORRA TODOS LOS DATOS
--     docker compose up -d
--
-- Aqui solo van extensiones y esquemas: la infraestructura. Las tablas, roles y
-- funciones viven en basedatos/ y son responsabilidad de Cesar (H1.3, H1.8, H1.9).

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_raster;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Cuatro esquemas separados por responsabilidad. Sostienen el criterio BD-2
-- de la rubrica: seguridad con minimo privilegio.
CREATE SCHEMA IF NOT EXISTS geo;        -- referencia territorial, casi estatica
CREATE SCHEMA IF NOT EXISTS crudo;      -- datos tal como llegan, solo escribe el ETL
CREATE SCHEMA IF NOT EXISTS analitico;  -- derivados y resultados del modelo
CREATE SCHEMA IF NOT EXISTS control;    -- gobernanza, calidad y auditoria

COMMENT ON SCHEMA geo       IS 'Distritos, estaciones y fuentes. Lectura casi estatica.';
COMMENT ON SCHEMA crudo     IS 'Mediciones, focos e imagenes sin transformar.';
COMMENT ON SCHEMA analitico IS 'Indices derivados, modelos, predicciones y eventos.';
COMMENT ON SCHEMA control   IS 'Calidad de datos, bitacora de ETL y auditoria.';

-- Zona horaria del pais, para que las fechas no se corran un dia
ALTER DATABASE geoguardian SET timezone TO 'America/Costa_Rica';
