-- 015 · Los roles de aplicacion necesitan USAGE sobre `public`, donde vive PostGIS
--
-- Historia H11.6 · Alejandro · Incidencia I-40 · Revisa H1.8
--
-- ===========================================================================
-- QUE PASABA
-- ===========================================================================
--
-- La 003 cierra el esquema `public` -`REVOKE ALL ... FROM PUBLIC`- para que
-- nadie cree objetos ahi ni lo use por omision. Correcto y necesario.
--
-- Pero **PostGIS se instala en `public`**: es donde `CREATE EXTENSION postgis`
-- deja sus funciones y su tipo `geometry`. Sin `USAGE` sobre ese esquema, un rol
-- lee las tablas perfectamente y **ninguna funcion de PostGIS se resuelve**.
-- Medido contra la base publicada el 2026-09-05, con `api_geoguardian`:
--
--     SELECT count(*) FROM geo.distrito              -> 8
--     SELECT postgis_version()                       -> function postgis_version() does not exist
--     SELECT ST_AsGeoJSON(geometria) FROM geo.distrito
--                                                    -> function st_asgeojson(public.geometry) does not exist
--
-- `/api/distritos` hace exactamente ese `ST_AsGeoJSON`, asi que devolvia 500 con
-- la tabla legible y la conexion sana. `/salud` decia `real`. El sintoma estaba
-- a un endpoint de distancia del indicador que lo tenia que mostrar.
--
-- ===========================================================================
-- POR QUE NO SE NOTO ANTES, Y ESTA ES LA PARTE QUE IMPORTA
-- ===========================================================================
--
-- El verificador de H1.8 comprueba con detalle **lo que la API no puede hacer**:
-- seis operaciones prohibidas, todas rechazadas. Y de lo que **si** puede, prueba
-- `SELECT count(*)` sobre una tabla.
--
-- **Nunca probo llamar a una funcion.** El minimo privilegio quedo tan ajustado
-- que dejo fuera la extension sobre la que se apoya medio sistema, y ningun
-- control lo vio porque ningun control miraba ahi.
--
-- Esta migracion arregla el permiso. La comprobacion que faltaba se agrega en
-- `basedatos/seguridad/verificar_h18.py`, en la lista de operaciones PERMITIDAS,
-- y sin ella este archivo no estaria probado.
--
-- ===========================================================================
-- QUE NO HACE
-- ===========================================================================
--
--   * **No devuelve nada a `PUBLIC`.** La 003 sigue en pie: `public` esta cerrado
--     para todos menos para los tres roles que se nombran aca.
--   * **No concede CREATE.** Solo `USAGE`: resolver nombres, no crear objetos.
--     Un rol de aplicacion que pueda crear tablas en `public` es una superficie
--     que nadie pidio.
--   * **No toca los permisos de tablas.** Lo que cada rol lee o escribe sigue
--     siendo lo que decidio H1.8.

BEGIN;

-- Con guarda: los roles los crea `crear_usuarios.py`, que puede correr despues
-- de las migraciones. Sin esto, aplicar el esquema en una base recien creada
-- fallaria por conceder a algo que todavia no existe.
DO $$
DECLARE
    rol text;
BEGIN
    FOREACH rol IN ARRAY ARRAY['geoguardian_api', 'geoguardian_etl', 'geoguardian_lector']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = rol) THEN
            EXECUTE format('GRANT USAGE ON SCHEMA public TO %I', rol);
        END IF;
    END LOOP;
END
$$;

COMMENT ON SCHEMA public IS
    'Cerrado para PUBLIC por la migracion 003. Los tres roles de aplicacion tienen USAGE por la 015, porque PostGIS vive aqui: sin eso ninguna funcion espacial se resuelve. Ver I-40.';

COMMIT;
