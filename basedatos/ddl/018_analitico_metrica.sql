-- 018 · Metricas de cada modelo, versionadas y fechadas
--
-- Historia: H3.7 (issue #53) · Rubrica: Arq
--
-- POR QUE ESTA TABLA
--
-- `contratos/repositorio.py` declara `guardar_metricas` y `listar_metricas`
-- desde el principio, y `backend/api/repositorio_postgres.py` las tiene en su
-- registro de PENDIENTES con esta tabla como motivo. **D-39 dejo escrito que
-- crearla es DDL de Cesar y que la trae H3.7.**
--
-- Sin ella, la comparacion de estimadores de H3.6 se imprime y se pierde: los
-- numeros con los que D-39 decidio que ningun algoritmo supera a la linea base
-- fuera del ruido no estan guardados en ninguna parte.
--
-- LA VERSION NO ES UNA CONVENCION NUEVA
--
-- `analitico.riesgo` ya tiene `version_modelo` como texto libre, "porque quien
-- la asigna es el entrenamiento, no esta tabla" (006). Aca se usa la misma
-- idea y el mismo tipo. Inventar una segunda forma de nombrar la version de un
-- modelo es como se degradan los esquemas: dos columnas que significan casi lo
-- mismo y nadie sabe cual mirar.
--
-- LOS TRES ESTADOS DE `supera_linea_base`
--
-- El contrato dice que es `None` "mientras no se haya contrastado contra la
-- linea base climatologica". Son **tres** estados: no comparado, no supera,
-- supera. Por eso la columna admite NULL y **no** tiene DEFAULT false: un
-- DEFAULT convertiria "todavia no se comparo" en "no supera", que es
-- exactamente la distincion sobre la que D-39 tomo su decision.
--
-- Es la misma regla que H1.1 con la lluvia: cero milimetros es un dia sin
-- lluvia, NULL es un dia sin medicion, y confundirlos arruina el calculo.

BEGIN;

CREATE TABLE IF NOT EXISTS analitico.metrica (

    -- Los tres campos que identifican la fila. `algoritmo` incluye a las lineas
    -- base: son estimadores como cualquier otro y se miden igual, como en 006.
    algoritmo               text        NOT NULL,
    tipo_evento             text        NOT NULL,

    -- Texto libre, igual que `analitico.riesgo.version_modelo`.
    version                 text        NOT NULL,

    -- Cuando se entreno el modelo que produjo estas metricas. Admite NULL
    -- porque el contrato dice que "un modelo puede estar registrado sin
    -- haberse evaluado todavia".
    entrenado_en            timestamptz,

    -- Las tres metricas de D-10. Ninguna tiene DEFAULT: una metrica no
    -- calculada vuelve NULL, nunca cero. Un cero es un modelo que fallo del
    -- todo, y eso es un dato distinto de no haberlo medido.
    f1_macro                numeric(5, 4),
    precision_macro         numeric(5, 4),
    exhaustividad_macro     numeric(5, 4),

    -- `list[list[int]]` del contrato. jsonb y no una tabla hija por la misma
    -- razon que `explicacion` en 006: se lee entera o no se lee, y nunca se
    -- consulta por dentro.
    matriz_confusion        jsonb,

    -- Cuando se guardo esta fila, que no es lo mismo que cuando se entreno.
    registrado_en           timestamptz NOT NULL DEFAULT now(),

    supera_linea_base       boolean,

    -- Clave natural: un algoritmo, para un evento, en una version. Un `id`
    -- opaco dejaria entrar dos filas para la misma terna sin que nada se queje
    -- -el mismo defecto que 006 evita en `analitico.riesgo`-.
    CONSTRAINT metrica_pk PRIMARY KEY (algoritmo, tipo_evento, version),

    CONSTRAINT metrica_tipo_evento_ck
        CHECK (tipo_evento IN ('lluvia_intensa', 'sequia', 'incendio')),

    -- Los cuatro valores del enum `Algoritmo` del contrato, y solo esos.
    --
    -- **LA LINEA BASE TRIVIAL NO ENTRA, Y NO ES UN OLVIDO.** `comparar.py`
    -- evalua cinco estimadores -trivial, climatologica, regresion, random
    -- forest y xgboost- pero `contratos/enums.py` solo define cuatro: no hay
    -- valor para la trivial. Si esta tabla la admitiera, `listar_metricas`
    -- reventaria al construir `MetricasModelo` con un algoritmo que el enum no
    -- conoce, y el fallo aparecereria lejos de aqui.
    --
    -- La consecuencia hay que decirla: **el piso trivial que D-39 usa para
    -- decidir quien puede escribir no queda guardado en esta tabla.** Admitirlo
    -- exige cambiar `contratos/`, que es archivo compartido y necesita
    -- solicitud aprobada. Queda declarado, no resuelto por la puerta de atras.
    CONSTRAINT metrica_algoritmo_ck
        CHECK (algoritmo IN (
            'linea_base_climatologica', 'regresion_logistica', 'random_forest', 'xgboost'
        )),

    -- Los tres rangos salen del contrato, que las declara `ge=0, le=1`. Se
    -- comprueban aca tambien: el contrato protege a quien pasa por Pydantic, y
    -- esto protege a quien escribe por SQL.
    CONSTRAINT metrica_f1_ck
        CHECK (f1_macro IS NULL OR f1_macro BETWEEN 0 AND 1),
    CONSTRAINT metrica_precision_ck
        CHECK (precision_macro IS NULL OR precision_macro BETWEEN 0 AND 1),
    CONSTRAINT metrica_exhaustividad_ck
        CHECK (exhaustividad_macro IS NULL OR exhaustividad_macro BETWEEN 0 AND 1)
);

COMMENT ON TABLE analitico.metrica IS
    'Desempeno de cada estimador por evento y version. H3.7. La version usa la '
    'misma convencion de texto libre que analitico.riesgo.version_modelo.';

COMMENT ON COLUMN analitico.metrica.supera_linea_base IS
    'Tres estados: NULL = no se contrasto contra la linea base climatologica; '
    'false = no la supera; true = la supera. Sin DEFAULT a proposito.';

COMMENT ON COLUMN analitico.metrica.f1_macro IS
    'Metrica de D-10. NULL es no calculada, que no es lo mismo que cero.';

-- Para la tabla comparativa: todas las metricas de un evento, la mas reciente
-- primero. Es la unica consulta que `listar_metricas` hace hoy.
CREATE INDEX IF NOT EXISTS metrica_evento_idx
    ON analitico.metrica (tipo_evento, registrado_en DESC);

-- Sin GRANT aqui, a proposito. H1.8 dejo puesto
-- `ALTER DEFAULT PRIVILEGES ... IN SCHEMA analitico` justamente para "las de
-- riesgo de H3.x", que no existian entonces: esta tabla nace con SELECT,
-- INSERT y UPDATE para el ETL y SELECT para la API y el lector, sin que nadie
-- conceda nada a mano. Escribirlos aqui seria repetir la regla en dos lugares
-- y arriesgarse a que difieran; `006` tampoco los escribe.

COMMIT;
