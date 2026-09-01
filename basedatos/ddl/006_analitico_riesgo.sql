-- 006 · Estimaciones de riesgo en el esquema analitico
--
-- Historia: H1.15 (issue #199) · Rubrica: BD-2
--
-- POR QUE ESTA HISTORIA EXISTE
--
-- `analitico.riesgo` es la tabla que el visor consulta y sobre la que H1.13
-- monta su disparador de auditoria. **No la creaba ninguna historia.** H1.13
-- declaraba depender de H1.8 -esquemas y roles-, que ya estaba cerrada, asi que
-- figuraba desbloqueada y no lo estaba: la tabla no existia.
--
-- Se abrio aparte el 2026-08-27 en vez de meterla dentro de H1.13, a proposito.
-- El esquema y el disparador son dos cosas: juntarlos hace que discutir una
-- arrastre a la otra, y esta se puede construir y probar **contra una tabla
-- vacia**, sin esperar al modelo de E3.
--
-- POR QUE EN `analitico`
--
-- `01-extensiones.sql` define `crudo` como "datos tal como llegan, solo escribe
-- el ETL". Esto no llega: se calcula. Y los permisos de H1.8 ya reparten en esa
-- direccion -`geoguardian_api` lee `analitico` y **no** tiene acceso a `crudo`-,
-- asi que poner la tabla en otro esquema obligaria a abrirle a la API un
-- permiso que se le nego a proposito.
--
-- LAS DOS REGLAS QUE NO SON NEGOCIABLES
--
-- 1. **`probabilidad` es P(nivel = alto)**, por D-21. No es la confianza del
--    modelo en la clase que asigno. Con la confianza, un distrito tranquilo y
--    un modelo seguro puntuarian mas alto que un distrito en riesgo con el
--    modelo dudando, y el mapa de calor pintaria mas intenso al equivocado.
--    Va en un COMMENT de columna y no solo en el contrato, porque quien abre la
--    base con un cliente SQL no lee `contratos/esquemas.py`.
--
-- 2. **La ausencia es NULL, nunca 0**, por D-07. Un distrito sin estimacion
--    tiene que poder distinguirse de uno con riesgo bajo. Es lo que el
--    etiquetado y el visor ya hacen, y es la razon de que casi todas las
--    columnas de abajo admitan nulo.
--
-- SIN INDICES, IGUAL QUE 004
--
-- Ni espaciales ni compuestos. Son H1.11 y H1.12, que necesitan medir el plan
-- de consulta antes y despues de crearlos. Crearlos aqui les quitaria su
-- evidencia.

CREATE TABLE IF NOT EXISTS analitico.riesgo (
    -- Texto y no entero, por lo mismo que `geo.distrito.codigo`: el contrato lo
    -- declara `str` y un entero perderia un cero a la izquierda.
    codigo_distrito text NOT NULL,

    fecha           date NOT NULL,

    -- Los tres del enum `TipoEvento`. Se restringen con CHECK y no con un tipo
    -- ENUM de PostgreSQL: agregar un valor a un ENUM es una migracion con
    -- bloqueo, y el catalogo de eventos todavia puede crecer.
    tipo_evento     text NOT NULL,

    -- NULO mientras no exista estimacion para ese distrito, fecha y evento.
    -- Un riesgo sin modelo detras no se rellena con un valor plausible.
    nivel           text,

    -- P(nivel = alto). Ver la cabecera y el COMMENT de mas abajo.
    probabilidad    numeric(5, 4),

    -- Cual de los cuatro estimadores produjo la fila. La linea base
    -- climatologica cuenta como algoritmo: es el piso contra el que se compara
    -- todo lo demas, y sus estimaciones se guardan igual que las otras.
    algoritmo       text,

    -- Version del modelo, para poder reproducir una fila vieja. Texto libre
    -- porque quien la asigna es el entrenamiento, no esta tabla.
    version_modelo  text,

    -- Aportes SHAP por variable, tal como los define `ContribucionVariable`.
    -- `jsonb` y no una tabla aparte: se lee entera o no se lee, nunca se
    -- consulta por dentro, y una tabla hija obligaria a una union en cada
    -- consulta del visor para un dato que casi siempre es NULL.
    explicacion     jsonb,

    -- Momento del calculo. Permite fechar una estimacion sin cruzarla contra el
    -- registro de la corrida, igual que `descargado_en` en 004.
    estimado_en     timestamptz NOT NULL DEFAULT now(),

    -- La clave es natural y no un identificador opaco: una estimacion queda
    -- determinada por distrito, dia y evento. Un `id serial` permitiria dos
    -- filas para la misma terna sin que nada se queje, que es justo el defecto
    -- que esta restriccion evita.
    CONSTRAINT riesgo_pk PRIMARY KEY (codigo_distrito, fecha, tipo_evento),

    CONSTRAINT riesgo_distrito_fk
        FOREIGN KEY (codigo_distrito) REFERENCES geo.distrito (codigo)
        ON DELETE RESTRICT,

    CONSTRAINT riesgo_tipo_evento_ck
        CHECK (tipo_evento IN ('lluvia_intensa', 'sequia', 'incendio')),

    CONSTRAINT riesgo_nivel_ck
        CHECK (nivel IS NULL OR nivel IN ('bajo', 'medio', 'alto')),

    CONSTRAINT riesgo_algoritmo_ck
        CHECK (algoritmo IS NULL OR algoritmo IN ('linea_base_climatologica',
                                                  'regresion_logistica',
                                                  'random_forest',
                                                  'xgboost')),

    -- El contrato declara `ge=0, le=1`. Sin esta restriccion, un error de escala
    -- -guardar 85 en vez de 0,85- entraria sin ruido y el visor pintaria el mapa
    -- con un valor imposible.
    CONSTRAINT riesgo_probabilidad_ck
        CHECK (probabilidad IS NULL OR (probabilidad >= 0 AND probabilidad <= 1)),

    -- UNA PROBABILIDAD SIN MODELO DETRAS NO ES AUDITABLE.
    --
    -- Si hay `probabilidad`, tiene que constar quien la produjo y con que
    -- version. Sin esto, una fila con 0,93 y `algoritmo` nulo es indistinguible
    -- de un valor escrito a mano, y no hay forma de reproducirla ni de
    -- retirarla cuando el modelo que la genero se descarte.
    --
    -- Es la misma regla que el proyecto ya aplica en otros lados: un dato con
    -- forma valida y procedencia desconocida es peor que un dato ausente,
    -- porque el ausente se nota.
    CONSTRAINT riesgo_probabilidad_trazable_ck
        CHECK (probabilidad IS NULL
               OR (algoritmo IS NOT NULL AND version_modelo IS NOT NULL)),

    -- La explicacion es sobre una estimacion. Sin `nivel` no hay nada que
    -- explicar, y una fila asi solo puede venir de un error de carga.
    CONSTRAINT riesgo_explicacion_ck
        CHECK (explicacion IS NULL OR nivel IS NOT NULL),

    -- Misma ventana que 004 por el limite inferior. El superior **no** es
    -- CURRENT_DATE: a diferencia de una medicion, una estimacion de riesgo mira
    -- hacia adelante. El horizonte del sistema es de siete dias y se deja un
    -- margen hasta 31 para no tener que migrar si el horizonte se amplia.
    CONSTRAINT riesgo_fecha_ck
        CHECK (fecha >= DATE '1981-01-01'
               AND fecha <= CURRENT_DATE + INTERVAL '31 days')
);

COMMENT ON TABLE analitico.riesgo IS
    'Estimacion de riesgo por distrito, dia y tipo de evento. Una fila por terna. Sin estimacion, no hay fila o el nivel es NULL.';
COMMENT ON COLUMN analitico.riesgo.probabilidad IS
    'P(nivel = alto), por D-21. NO es la confianza del modelo en la clase asignada: nivel bajo con probabilidad 0,05 significa que el modelo lo ve tranquilo.';
COMMENT ON COLUMN analitico.riesgo.nivel IS
    'NULO cuando no hay estimacion. Por D-07, la ausencia nunca se representa como riesgo bajo.';
COMMENT ON COLUMN analitico.riesgo.algoritmo IS
    'Obligatorio si hay probabilidad: una probabilidad sin modelo detras no se puede reproducir ni retirar.';
COMMENT ON COLUMN analitico.riesgo.explicacion IS
    'Aportes SHAP por variable. Positivo empuja hacia mayor riesgo. NULO mientras no exista modelo entrenado.';
COMMENT ON COLUMN analitico.riesgo.estimado_en IS
    'Momento del calculo, para fechar una estimacion sin abrir el registro de la corrida.';
