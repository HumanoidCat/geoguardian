-- 017 · La API lee la serie climatica por una vista en `analitico`; `crudo` sigue cerrado
--
-- Decision D-45 · Incidencia I-44 · Alejandro · Revisa H1.1 (contrato), H1.8 (003)
--
-- ===========================================================================
-- QUE PASABA
-- ===========================================================================
--
-- `GET /api/distritos/{codigo}/mediciones` existe desde H1.1 y lee
-- `crudo.medicion_diaria`. La 003 le niega a `geoguardian_api` hasta el USAGE
-- sobre `crudo`, y lo dice a proposito: «Esta ausencia es deliberada». Con ese
-- rol la consulta solo puede fallar con `permission denied for schema crudo`,
-- y en Railway la ruta respondia 500 (comprobado el 2026-09-06, I-44).
--
-- Dos historias decidieron bien por separado y nadie las junto. Esta migracion
-- las junta sin desdecir a ninguna.
--
-- ===========================================================================
-- QUE HACE
-- ===========================================================================
--
-- Crea `analitico.serie_climatica`, una vista sobre `crudo.medicion_diaria` con
-- las columnas que la ruta ya devuelve, y le da SELECT a la API (y al lector).
--
-- Lo que lo hace posible sin tocar la 003: en PostgreSQL una vista se ejecuta con
-- los privilegios de **quien la creo**, no de quien la consulta
-- (`security_invoker` apagado, que es lo que trae por omision). Quien aplica
-- las migraciones puede leer `crudo`; la API solo puede leer la vista.
--
-- La vista lleva `security_invoker = false` escrito aunque sea el valor por
-- omision, porque es la propiedad de la que depende todo esto y una propiedad
-- de la que se depende se declara, no se supone.
--
-- ===========================================================================
-- QUE NO HACE
-- ===========================================================================
--
--   * **No concede nada sobre `crudo`.** La 003 sigue cierta letra por letra;
--     `verificar_h18.py` lo comprueba con un SELECT sobre `crudo.medicion_diaria`
--     que tiene que ser rechazado.
--   * **No expone `fuente_resto`, `descargado_en` ni `imputado_en`.** La ruta no
--     los devuelve; el dia que haga falta, se agregan aqui y la 003 sigue igual.
--   * **No cambia el contrato.** La ruta, sus parametros y su forma son los de
--     la 1.4.0.

BEGIN;

CREATE OR REPLACE VIEW analitico.serie_climatica
    WITH (security_invoker = false)
AS
    SELECT codigo_distrito,
           fecha,
           temp_max_c,
           temp_min_c,
           temp_media_c,
           humedad_relativa_pct,
           viento_ms,
           radiacion_mj_m2,
           precipitacion_mm,
           fuente_precipitacion,
           imputado,
           metodo_imputacion
      FROM crudo.medicion_diaria;

COMMENT ON VIEW analitico.serie_climatica IS
    'La serie climatica diaria tal como la sirve la API (D-45, I-44). Vista sobre crudo.medicion_diaria que corre con los privilegios de su duenio: la API la lee sin tener acceso a crudo, que sigue cerrado por la 003.';

-- Con guarda: los roles los crea `crear_usuarios.py`, que puede correr despues
-- de las migraciones (misma razon que la 015).
DO $$
DECLARE
    rol text;
BEGIN
    FOREACH rol IN ARRAY ARRAY['geoguardian_api', 'geoguardian_lector']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = rol) THEN
            EXECUTE format('GRANT SELECT ON analitico.serie_climatica TO %I', rol);
        END IF;
    END LOOP;
END
$$;

COMMIT;
