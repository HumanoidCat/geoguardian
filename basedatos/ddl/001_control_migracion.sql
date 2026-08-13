-- 001 · Registro de migraciones
--
-- Historia: H1.3 (issue #37) · Rubrica: BD-1, BD-3
--
-- Los scripts de infra/docker/init-db/ corren una sola vez, cuando el volumen de
-- datos esta vacio. Todo DDL posterior necesita otra via de aplicacion. Esta
-- tabla es el registro de esa via: guarda que migraciones se aplicaron, cuando y
-- con que contenido.
--
-- REGLA: un archivo de migracion ya aplicado NO SE EDITA NUNCA. Todo cambio
-- posterior es un archivo nuevo con el siguiente numero. Editar uno aplicado
-- deja dos bases distintas con el mismo numero de migracion y sin forma de
-- distinguirlas. La columna `suma_sha256` existe para que el aplicador detecte
-- esa situacion y se detenga en vez de continuar.

CREATE TABLE IF NOT EXISTS control.migracion (
    -- Numero de la migracion, tomado del prefijo del nombre de archivo.
    numero        integer     NOT NULL,

    -- Nombre completo del archivo, para poder rastrearlo sin adivinar.
    archivo       text        NOT NULL,

    -- SHA-256 del contenido del archivo en el momento de aplicarlo. Si el
    -- archivo cambia despues, el aplicador lo compara contra este valor y falla.
    suma_sha256   char(64)    NOT NULL,

    -- Momento de aplicacion. Sirve para reconstruir el orden real, que puede
    -- diferir del orden numerico si alguien aplica migraciones a destiempo.
    aplicada_en   timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT migracion_pk           PRIMARY KEY (numero),
    CONSTRAINT migracion_archivo_unq  UNIQUE (archivo),
    CONSTRAINT migracion_numero_ck    CHECK (numero > 0),
    CONSTRAINT migracion_suma_ck      CHECK (suma_sha256 ~ '^[0-9a-f]{64}$')
);

COMMENT ON TABLE  control.migracion IS
    'Migraciones de DDL aplicadas. Un archivo aplicado no se edita: se agrega uno nuevo.';
COMMENT ON COLUMN control.migracion.suma_sha256 IS
    'SHA-256 del archivo al aplicarlo. Si difiere del actual, el aplicador se detiene.';
COMMENT ON COLUMN control.migracion.aplicada_en IS
    'Orden real de aplicacion, que puede no coincidir con el orden numerico.';
