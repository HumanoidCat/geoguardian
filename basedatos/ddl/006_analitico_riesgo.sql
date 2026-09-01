-- 006 · Estimaciones de riesgo en el esquema analitico
--
-- Historia: H1.15 · Rubrica: BD-2
--
-- QUE GUARDA
--
-- Una estimacion de riesgo por distrito, fecha y tipo de evento. Es la tabla que
-- el protocolo `Repositorio` necesita para `obtener_riesgo` y
-- `obtener_riesgos_por_fecha`, y la que H1.13 va a auditar con su disparador.
--
-- La abre H1.15, que existe porque NINGUNA historia del backlog la creaba: H1.13
-- declaraba depender solo de H1.8 y su dependencia real no estaba escrita. Se
-- detecto al intentar H1.13 el 2026-08-27.
--
-- POR QUE LA CLAVE ES DE TRES COLUMNAS Y NO DE CUATRO
--
-- La clave natural es (distrito, fecha, evento). El algoritmo NO entra en ella, y
-- la razon esta en la firma del protocolo:
--
--     obtener_riesgo(codigo_distrito, fecha, tipo_evento) -> Riesgo | None
--
-- Devuelve UNA estimacion y no recibe algoritmo. Si el algoritmo estuviera en la
-- clave, esa firma seria ambigua: habria varias filas candidatas y el repositorio
-- tendria que elegir una sin criterio escrito.
--
-- Esta tabla guarda **la estimacion vigente**. `algoritmo` y `version_modelo`
-- dicen cual la produjo. La comparacion entre algoritmos es H3.6, y ocurre en
-- memoria sobre los pliegues de H3.2: no se guarda una fila por algoritmo.
--
-- LA AUSENCIA ES NULA, NUNCA CERO
--
-- **D-07.** Todo lo estimado es nulable. Un distrito sin estimacion tiene que
-- poder distinguirse de uno con riesgo bajo: rellenar con `bajo` o con `0`
-- convertiria «no sabemos» en «esta tranquilo», que es el error que mas caro sale
-- en un sistema de alerta.
--
-- Por eso `nivel`, `probabilidad`, `algoritmo` y `version_modelo` admiten NULL, y
-- una fila con todo nulo es una afirmacion legitima: «esta celda existe y no hay
-- estimacion para ella».
--
-- PROBABILIDAD ES P(NIVEL = ALTO)
--
-- **D-21**, y esta en el COMMENT de la columna a proposito: quien lea el esquema
-- sin abrir los contratos tiene que enterarse igual.
--
-- NO es la confianza del modelo en la clase que asigno. Con la confianza, un
-- distrito tranquilo con el modelo seguro puntuaria mas alto que uno en riesgo
-- con el modelo dudando, y el mapa de calor pintaria mas intenso al equivocado.
--
-- EL INCENDIO NO TIENE NIVEL MEDIO
--
-- **SC-05** lo dejo binario: `alto` significa «al menos un foco en la ventana de
-- siete dias», y eso o pasa o no pasa. El umbral viejo por percentiles tampoco
-- producia tres clases: el P90 del conteo vale 0,0 en los ocho distritos, medido
-- sobre 242 focos en 24 anios.
--
-- El simulado ya lo respeta y CA-13 de H6.2 lo comprueba. Aca deja de depender de
-- que cada productor se acuerde: la base lo rechaza.
--
-- SOBRE `estimado_en`
--
-- Es metadata de escritura, no dato. Si algun dia esta tabla entra al manifiesto
-- de H1.7, va en COLUMNAS_EXCLUIDAS junto a `descargado_en`: incluirla haria que
-- dos personas con las mismas estimaciones obtuvieran sumas distintas.

CREATE TABLE IF NOT EXISTS analitico.riesgo (
    codigo_distrito  text NOT NULL,
    fecha            date NOT NULL,

    -- Texto y no un tipo enumerado de PostgreSQL: el contrato es la fuente de
    -- verdad de los valores, y un ENUM obligaria a una migracion por cada cambio
    -- del contrato. El CHECK cumple la misma funcion y se lee igual.
    tipo_evento      text NOT NULL,

    -- Todo lo que sigue es la ESTIMACION, y toda estimacion puede faltar. D-07.
    nivel            text,
    probabilidad     real,
    algoritmo        text,
    version_modelo   text,

    estimado_en      timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT riesgo_pk PRIMARY KEY (codigo_distrito, fecha, tipo_evento),

    CONSTRAINT riesgo_distrito_fk
        FOREIGN KEY (codigo_distrito) REFERENCES geo.distrito (codigo),

    CONSTRAINT riesgo_evento_ck
        CHECK (tipo_evento IN ('lluvia_intensa', 'sequia', 'incendio')),

    CONSTRAINT riesgo_nivel_ck
        CHECK (nivel IS NULL OR nivel IN ('bajo', 'medio', 'alto')),

    CONSTRAINT riesgo_algoritmo_ck
        CHECK (algoritmo IS NULL OR algoritmo IN (
            'linea_base_climatologica', 'regresion_logistica', 'random_forest', 'xgboost')),

    -- D-21: es una probabilidad, no un puntaje.
    CONSTRAINT riesgo_probabilidad_ck
        CHECK (probabilidad IS NULL OR probabilidad BETWEEN 0 AND 1),

    -- SC-05: el incendio es binario. Emitir `medio` produciria un valor que el
    -- contrato ya no admite, y un dato imposible bajo el contrato es peor que un
    -- dato ausente.
    CONSTRAINT riesgo_incendio_binario_ck
        CHECK (NOT (tipo_evento = 'incendio' AND nivel = 'medio')),

    -- Si `probabilidad` es P(nivel = alto), una probabilidad sin nivel es una
    -- afirmacion sobre una clase que nadie asigno. Se admite el caso contrario
    -- -nivel sin probabilidad- porque las lineas base de H3.1 clasifican sin
    -- estimar probabilidad, y son parte de la comparacion de H3.6.
    CONSTRAINT riesgo_probabilidad_exige_nivel_ck
        CHECK (nivel IS NOT NULL OR probabilidad IS NULL)
);

-- El indice que hace falta NO es (codigo_distrito, fecha): ese ya existe como
-- prefijo de la clave primaria y crearlo otra vez seria mantener dos copias del
-- mismo arbol.
--
-- El que falta es este. `obtener_riesgos_por_fecha(fecha, tipo_evento)` -la
-- consulta que alimenta las coropletas del visor- filtra por fecha primero, y el
-- prefijo de la clave primaria empieza por distrito: no la sirve.
CREATE INDEX IF NOT EXISTS riesgo_fecha_evento_idx
    ON analitico.riesgo (fecha, tipo_evento);


-- Las contribuciones van en su propia tabla y no como JSON en una columna.
--
-- El contrato declara `explicacion: list[ContribucionVariable] | None`. Guardar
-- esa lista dentro de una celda es lo comodo y rompe la PRIMERA FORMA NORMAL, que
-- es justo lo que la rubrica BD-1 evalua en el resto del esquema. Una fila por
-- variable se consulta, se agrega y se restringe; un JSON no.
--
-- El borrado en cascada es deliberado: una contribucion sin su estimacion no
-- significa nada, y dejarla huerfana seria conservar una explicacion de algo que
-- ya no se afirma.
CREATE TABLE IF NOT EXISTS analitico.contribucion_riesgo (
    codigo_distrito  text NOT NULL,
    fecha            date NOT NULL,
    tipo_evento      text NOT NULL,

    variable         text NOT NULL,

    -- Valor SHAP. Positivo empuja hacia mayor riesgo. No se acota: SHAP no tiene
    -- un rango fijo y ponerle uno inventado recortaria aportes legitimos.
    aporte           real NOT NULL,

    CONSTRAINT contribucion_pk
        PRIMARY KEY (codigo_distrito, fecha, tipo_evento, variable),

    CONSTRAINT contribucion_riesgo_fk
        FOREIGN KEY (codigo_distrito, fecha, tipo_evento)
        REFERENCES analitico.riesgo (codigo_distrito, fecha, tipo_evento)
        ON DELETE CASCADE,

    CONSTRAINT contribucion_variable_ck
        CHECK (btrim(variable) <> '' AND variable = btrim(variable))
);

CREATE INDEX IF NOT EXISTS contribucion_variable_idx
    ON analitico.contribucion_riesgo (variable);


COMMENT ON TABLE analitico.riesgo IS
    'Estimacion vigente por distrito, fecha y evento. Una fila sin nivel es ausencia de estimacion, no riesgo bajo.';
COMMENT ON COLUMN analitico.riesgo.probabilidad IS
    'P(nivel = alto), por D-21. NO es la confianza del modelo en la clase que asigno.';
COMMENT ON COLUMN analitico.riesgo.nivel IS
    'NULO cuando no hay estimacion. D-07: la ausencia nunca se representa como bajo ni como cero.';
COMMENT ON COLUMN analitico.riesgo.algoritmo IS
    'Cual produjo esta fila. No entra en la clave: obtener_riesgo devuelve una sola estimacion.';
COMMENT ON COLUMN analitico.riesgo.estimado_en IS
    'Metadata de escritura, no dato. Queda fuera de cualquier suma de verificacion del dataset.';

COMMENT ON TABLE analitico.contribucion_riesgo IS
    'Aportes SHAP por variable. Tabla propia y no JSON en una columna, por 1FN.';
COMMENT ON COLUMN analitico.contribucion_riesgo.aporte IS
    'Valor SHAP: positivo empuja hacia mayor riesgo. Sin rango acotado.';
