-- 003 · Roles de minimo privilegio
--
-- Historia: H1.8 (issue #40) · Rubrica: BD-2
--
-- POR QUE EXISTE
--
-- Los cuatro esquemas los crea infra/docker/init-db/01-extensiones.sql y su
-- comentario dice que sostienen el criterio BD-2. Pero un esquema sin roles no
-- restringe nada: hasta esta migracion, cualquiera que se conectara con el
-- usuario de la aplicacion podia modificar o borrar cualquier cosa en los cuatro.
--
-- ESTE ARCHIVO NO CONTIENE NINGUNA CONTRASENA
--
-- Ni tampoco los nombres de los usuarios que inician sesion. Un
-- CREATE ROLE ... PASSWORD 'algo' aqui dejaria la contrasena en el historial de
-- git para siempre, y borrarla despues no la quita de los commits anteriores.
--
-- Los usuarios que inician sesion los crea basedatos/seguridad/crear_usuarios.py,
-- que lee sus credenciales de .env. Aqui viven solo los roles de grupo y los
-- permisos, que es la parte que el evaluador de BD-2 tiene que poder leer de un
-- vistazo. En SQL declarativo se leen; repartidos en cadenas dentro de codigo, no.
--
-- REPARTO DE PERMISOS
--
--   esquema      geoguardian_etl      geoguardian_api    geoguardian_lector
--   ---------    ------------------   ----------------   ------------------
--   geo          lectura              lectura            lectura
--   crudo        lectura y escritura  NINGUNO            lectura
--   analitico    lectura y escritura  lectura            lectura
--   control      lectura y escritura  lectura            lectura
--
-- El caso que mas importa es `crudo` para la API: ni siquiera lectura. La API
-- sirve riesgos e indices, que viven en `analitico`. No tiene por que ver los
-- datos sin transformar. Si algun dia los necesita, se discute y se concede.
--
-- Ningun rol recibe DELETE ni TRUNCATE en ningun esquema. Borrar datos historicos
-- no es una operacion de la aplicacion.
--
-- Ningun rol de aplicacion es dueno de las tablas. El dueno sigue siendo el
-- usuario administrador con el que corren las migraciones. Que un rol no pueda
-- ejecutar DROP ni ALTER sobre lo que no le pertenece no hay que prohibirlo: es
-- el comportamiento por omision de PostgreSQL cuando no se le regala la propiedad.

-- --------------------------------------------------------------------------- --
-- 1. Roles de grupo                                                            --
-- --------------------------------------------------------------------------- --
--
-- NOLOGIN a proposito: son etiquetas de permisos, no cuentas. Los permisos se
-- otorgan una vez al rol y no a cada persona o servicio. Si manana entra un
-- segundo proceso de ingesta, se le concede el rol y no hay que repetir veinte
-- GRANT. Y revocar el acceso de un usuario no toca el esquema de permisos.
--
-- DO ... IF NOT EXISTS porque CREATE ROLE no admite IF NOT EXISTS y esta
-- migracion tiene que poder correrse dos veces sin fallar.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_etl') THEN
        CREATE ROLE geoguardian_etl NOLOGIN;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_api') THEN
        CREATE ROLE geoguardian_api NOLOGIN;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geoguardian_lector') THEN
        CREATE ROLE geoguardian_lector NOLOGIN;
    END IF;
END
$$;

COMMENT ON ROLE geoguardian_etl    IS 'Ingesta: escribe crudo, analitico y control. Lee geo.';
COMMENT ON ROLE geoguardian_api    IS 'API: lee geo, analitico y control. Sin acceso a crudo.';
COMMENT ON ROLE geoguardian_lector IS 'Solo lectura, para consulta manual y revision.';

-- --------------------------------------------------------------------------- --
-- 2. Retirar lo que PostgreSQL regala por omision                              --
-- --------------------------------------------------------------------------- --
--
-- PostgreSQL concede a PUBLIC, es decir a cualquier rol, la posibilidad de
-- conectarse a la base y de crear objetos en el esquema `public`. Mientras eso
-- siga en pie, hablar de minimo privilegio es falso.
--
-- CONNECT se revoca de PUBLIC y se concede explicitamente a los tres roles: asi
-- conectarse pasa a ser un permiso otorgado y no un derecho de nacimiento.

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE geoguardian FROM PUBLIC;

GRANT CONNECT ON DATABASE geoguardian TO geoguardian_etl, geoguardian_api, geoguardian_lector;

-- --------------------------------------------------------------------------- --
-- 3. Acceso a los esquemas                                                     --
-- --------------------------------------------------------------------------- --
--
-- USAGE sobre el esquema es la puerta: sin el, los permisos sobre las tablas de
-- adentro no sirven de nada. Es lo que hace que la API reciba
-- 'permission denied for schema crudo' y no un error de tabla.

GRANT USAGE ON SCHEMA geo       TO geoguardian_etl, geoguardian_api, geoguardian_lector;
GRANT USAGE ON SCHEMA analitico TO geoguardian_etl, geoguardian_api, geoguardian_lector;
GRANT USAGE ON SCHEMA control   TO geoguardian_etl, geoguardian_api, geoguardian_lector;

-- crudo: el ETL y el lector si, la API no. Esta ausencia es deliberada.
GRANT USAGE ON SCHEMA crudo     TO geoguardian_etl, geoguardian_lector;

-- --------------------------------------------------------------------------- --
-- 4. Permisos sobre las tablas que ya existen                                  --
-- --------------------------------------------------------------------------- --

-- geo: territorio, casi estatico. Nadie de la aplicacion lo escribe.
GRANT SELECT ON ALL TABLES IN SCHEMA geo
    TO geoguardian_etl, geoguardian_api, geoguardian_lector;

-- crudo: solo el ETL escribe. Sin DELETE.
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA crudo TO geoguardian_etl;
GRANT SELECT                 ON ALL TABLES IN SCHEMA crudo TO geoguardian_lector;

-- analitico: escribe el ETL, lee la API.
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA analitico TO geoguardian_etl;
GRANT SELECT                 ON ALL TABLES IN SCHEMA analitico TO geoguardian_api, geoguardian_lector;

-- control: gobernanza y bitacora. El ETL registra, los demas consultan.
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA control TO geoguardian_etl;
GRANT SELECT                 ON ALL TABLES IN SCHEMA control TO geoguardian_api, geoguardian_lector;

-- Secuencias: sin USAGE sobre la secuencia, un INSERT en una tabla con columna
-- serial falla aunque el INSERT este concedido.
GRANT USAGE ON ALL SEQUENCES IN SCHEMA crudo     TO geoguardian_etl;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA analitico TO geoguardian_etl;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA control   TO geoguardian_etl;

-- --------------------------------------------------------------------------- --
-- 5. Permisos por omision, para las tablas que todavia no existen              --
-- --------------------------------------------------------------------------- --
--
-- Un GRANT sobre las tablas de un esquema alcanza solo a las que existen en ese
-- momento. La tabla de mediciones de H1.1 y las de riesgo de H3.x no existen
-- todavia: sin esto naceran inaccesibles, y alguien "arreglaria" el problema con
-- prisa concediendo permisos de mas.
--
-- FOR ROLE CURRENT_USER: aplica a lo que cree el usuario que corre las
-- migraciones, que es el mismo que va a crear esas tablas.

ALTER DEFAULT PRIVILEGES FOR ROLE CURRENT_USER IN SCHEMA geo
    GRANT SELECT ON TABLES TO geoguardian_etl, geoguardian_api, geoguardian_lector;

ALTER DEFAULT PRIVILEGES FOR ROLE CURRENT_USER IN SCHEMA crudo
    GRANT SELECT, INSERT, UPDATE ON TABLES TO geoguardian_etl;
ALTER DEFAULT PRIVILEGES FOR ROLE CURRENT_USER IN SCHEMA crudo
    GRANT SELECT ON TABLES TO geoguardian_lector;

ALTER DEFAULT PRIVILEGES FOR ROLE CURRENT_USER IN SCHEMA analitico
    GRANT SELECT, INSERT, UPDATE ON TABLES TO geoguardian_etl;
ALTER DEFAULT PRIVILEGES FOR ROLE CURRENT_USER IN SCHEMA analitico
    GRANT SELECT ON TABLES TO geoguardian_api, geoguardian_lector;

ALTER DEFAULT PRIVILEGES FOR ROLE CURRENT_USER IN SCHEMA control
    GRANT SELECT, INSERT, UPDATE ON TABLES TO geoguardian_etl;
ALTER DEFAULT PRIVILEGES FOR ROLE CURRENT_USER IN SCHEMA control
    GRANT SELECT ON TABLES TO geoguardian_api, geoguardian_lector;

ALTER DEFAULT PRIVILEGES FOR ROLE CURRENT_USER IN SCHEMA crudo
    GRANT USAGE ON SEQUENCES TO geoguardian_etl;
ALTER DEFAULT PRIVILEGES FOR ROLE CURRENT_USER IN SCHEMA analitico
    GRANT USAGE ON SEQUENCES TO geoguardian_etl;
ALTER DEFAULT PRIVILEGES FOR ROLE CURRENT_USER IN SCHEMA control
    GRANT USAGE ON SEQUENCES TO geoguardian_etl;
