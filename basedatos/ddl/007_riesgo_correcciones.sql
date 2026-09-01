-- 007 · Dos correcciones sobre analitico.riesgo
--
-- Historia: H1.15 (issue #199) · Rubrica: BD-2
-- Las encontro Cesar revisando el PR #211, ya fusionado.
--
-- POR QUE UNA MIGRACION NUEVA Y NO EDITAR LA 006
--
-- Porque la 006 ya se aplico. La cabecera de 004 lo dice sin ambiguedad: «una
-- migracion aplicada no se renumera nunca», y editarla es peor que renumerarla:
-- una base que ya corrio 006 no volveria a ejecutarla, asi que el arreglo no
-- llegaria a ninguna instalacion existente y solo funcionaria en las nuevas.
-- Dos bases con el mismo numero de migracion y distinto esquema es exactamente
-- lo que el control de migraciones existe para impedir.

-- --------------------------------------------------------------------------- #
-- 1. El incendio no admite `medio`. SC-05.
-- --------------------------------------------------------------------------- #
--
-- `riesgo_nivel_ck` restringe a ('bajo','medio','alto') sin excepcion por
-- evento, y para incendio eso admite un valor que **el contrato ya no tiene**.
--
-- SC-05 lo redefinio como binario al medir: los 242 focos de FIRMS en 24 anios
-- no producian tres clases sino dos. `nivel_incendio()` en
-- `backend/modelado/etiquetado.py` lo dice en su primera linea -«ALTO con al
-- menos un foco, BAJO sin ninguno. **No existe MEDIO**»- y devuelve solo esos
-- dos, o None.
--
-- Con la 006 sola, `('50801','2026-09-01','incendio','medio')` entra sin ruido.
-- El codigo nunca lo escribiria; una carga manual, una restauracion parcial o un
-- guion de otro modulo, si. **Un dato imposible bajo el contrato que la base
-- acepta es peor que uno ausente, porque el ausente se nota.**
--
-- Va como restriccion aparte y no modificando `riesgo_nivel_ck` para que el
-- mensaje de error diga cual regla se violo: «nivel fuera del dominio» y
-- «incendio no tiene nivel medio» son dos diagnosticos distintos.
ALTER TABLE analitico.riesgo
    ADD CONSTRAINT riesgo_incendio_binario_ck
    CHECK (NOT (tipo_evento = 'incendio' AND nivel = 'medio'));

-- --------------------------------------------------------------------------- #
-- 2. `CURRENT_DATE` no puede vivir en un CHECK.
-- --------------------------------------------------------------------------- #
--
-- La 006 declaraba:
--
--     CHECK (fecha >= DATE '1981-01-01'
--            AND fecha <= CURRENT_DATE + INTERVAL '31 days')
--
-- **`CURRENT_DATE` no es inmutable.** PostgreSQL acepta la restriccion -por eso
-- el verificador daba 15 de 15- pero la reevalua **en cada insercion**, no solo
-- cuando la fila se escribio por primera vez.
--
-- EL DANO ESTA EN LA RESTAURACION
--
-- `pg_dump` emite fechas literales y restaurar es reinsertar. Una fila estimada
-- para dentro de 31 dias es valida el dia del volcado y **deja de serlo al dia
-- siguiente**. El respaldo se toma en verde y se descubre inservible cuando hace
-- falta, que es el unico momento en que a nadie le sirve descubrirlo.
--
-- Comprobado el 2026-09-01 contra PostgreSQL 16.2:
--
--     INSERT con fecha 2026-10-02 (hoy+31)  -> ACEPTADA
--     INSERT con fecha 2026-10-03 (hoy+32)  -> RECHAZADA: CheckViolation
--
-- Esa segunda fila era valida ayer. Un volcado de ayer no restaura hoy.
--
-- Y CAE SOBRE H1.10, QUE ES «RESTAURACION PROBADA»
--
-- La prueba de restauracion de esa historia pasaria mientras se corra el mismo
-- dia del volcado, y empezaria a fallar sola despues, sin que nadie toque nada.
-- Es la forma mas incomoda de I-06: un control que hoy esta verde y cambia de
-- veredicto con el calendario.
--
-- QUE SE HACE
--
-- **Se quita el limite superior, no se fija una constante.** Una fecha constante
-- solo cambia el problema de lugar: alguien tendria que acordarse de moverla, y
-- el dia que se pase, la base empieza a rechazar estimaciones legitimas.
--
-- El horizonte de siete dias es una regla del sistema que hace cumplir quien
-- escribe, no el esquema. Una estimacion mas lejana es un error de codigo, y ese
-- error se atrapa donde se produce.
--
-- El limite inferior se conserva: `DATE '1981-01-01'` es constante y atrapa el
-- error real -una fecha de 1900 por un desbordamiento o un parseo malo-.
ALTER TABLE analitico.riesgo
    DROP CONSTRAINT riesgo_fecha_ck;

ALTER TABLE analitico.riesgo
    ADD CONSTRAINT riesgo_fecha_ck
    CHECK (fecha >= DATE '1981-01-01');

-- --------------------------------------------------------------------------- #
-- 3. Declarar la excepcion a la primera forma normal.
-- --------------------------------------------------------------------------- #
--
-- `explicacion jsonb` guarda una lista dentro de una celda, y eso **rompe 1FN**.
-- Es la unica coleccion en una columna en todo el esquema, asi que es la primera
-- que se va a mirar al calificar BD-1.
--
-- Se mantiene, y las razones son las de la 006: se lee entera o no se lee, nunca
-- se consulta por dentro, y una tabla hija obligaria a una union en cada
-- consulta del visor para un dato que casi siempre es NULL.
--
-- Lo que cambia es que **deja de depender de que alguien se acuerde del
-- argumento**: el COMMENT lo dice, y el COMMENT viaja con la base.
--
-- La objecion contraria esta registrada y es razonable: la union se evita con un
-- LEFT JOIN que el visor solo pediria al abrir el panel de un distrito, que es
-- cuando la explicacion se muestra. Si al calificar se prefiere 1FN estricta, el
-- cambio es una tabla hija y una migracion; no hay dato que rehacer.
COMMENT ON COLUMN analitico.riesgo.explicacion IS
    'Aportes SHAP por variable. Positivo empuja hacia mayor riesgo. NULO mientras no exista modelo entrenado. EXCEPCION DELIBERADA A 1FN: es una coleccion en una columna, la unica del esquema. Se lee entera y nunca se consulta por dentro; una tabla hija obligaria a una union en cada consulta del visor para un dato que casi siempre es NULL.';
