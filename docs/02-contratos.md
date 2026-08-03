# Contratos entre modulos

Las interfaces se definen ANTES de implementar y quedan congeladas. Cada modulo
tiene ademas un simulado en `contratos/simulados/` que respeta el contrato, para
que nadie quede bloqueado esperando codigo ajeno.

Cambiar un simulado por el modulo real debe ser una linea, no una refactorizacion.

## Estado

Version de contratos: **1.0.0** · Congelados el 3 de agosto de 2026.

| Contrato | Archivo | Dueno | Simulado | Estado |
|---|---|---|---|---|
| Vocabulario del dominio | contratos/enums.py | Alejandro | no aplica | CONGELADO |
| Esquemas de la API | contratos/esquemas.py | Cesar | no aplica | CONGELADO |
| Extractores | contratos/fuentes.py | Cesar | si | CONGELADO |
| Repositorio | contratos/repositorio.py | Cesar | si | CONGELADO |
| Procesador de senales | contratos/senales.py | Alejandro | pendiente | CONGELADO |
| Estimador y evaluador | contratos/modelado.py | Alejandro | pendiente | CONGELADO |

## Verificacion ejecutada

    RepositorioSimulado es Repositorio        True
    ExtractorClimaSimulado es ExtractorClima  True
    ExtractorFocosSimulado es ExtractorFocos  True
    31 dias de serie: 2 huecos (None), 11 dias con lluvia 0.0 mm, distinguibles
    listar_metricas() devuelve [] porque no hay modelos entrenados

## Decisiones de diseno

**Protocol en lugar de clases abstractas.** Los simulados no heredan de nada ni
importan el contrato: lo cumplen por estructura. Eso significa que sustituir un
simulado por el modulo real es cambiar que clase se instancia, sin tocar a los
consumidores. Con `@runtime_checkable` se conserva la verificacion por
`isinstance` en las pruebas. Se descarto ABC porque acopla por herencia y obliga
a que el simulado conozca el contrato.

**Los faltantes son representables en todas partes.** Cada variable de medicion es
`Optional[float]`. Cero milimetros de lluvia es una medicion; ausencia de dato no
lo es. Confundirlos sesga el modelo y nadie lo detecta hasta que es tarde. Por eso
`obtener_mediciones` devuelve tambien los dias sin dato, y `SerieTemporal`
conserva los huecos como `None` en vez de omitir la fecha: el grafico muestra la
discontinuidad en lugar de una recta que aparenta continuidad.

**El riesgo sin modelo es nulo, no un valor por defecto.** `Riesgo.nivel`,
`probabilidad` y `explicacion` son opcionales. Un estimador sin entrenar lanza
`RuntimeError` al predecir en lugar de devolver algo plausible.

**La linea base cumple el mismo contrato que los modelos.** `Estimador` lo
implementan tanto la linea base climatologica como los tres algoritmos. La
comparacion queda justa por construccion: mismo codigo de evaluacion, mismas
particiones temporales.

**El modo simulado es visible.** Cada simulado registra una advertencia al
instanciarse y la API expone `modo: simulado` en `/salud`. El frontend muestra un
aviso cuando lo detecta. La regla de no inventar datos no se rompe: se hace
evidente que son simulados.

## Reglas

1. Un contrato congelado no se modifica sin solicitud de cambio aprobada por
   Alejandro y por todos los duenos de modulos que lo consumen.
2. Todo contrato nuevo nace junto con su simulado. Sin simulado, no esta listo.
3. Los simulados devuelven datos con la forma correcta pero declarados como
   simulados. Nunca datos que puedan confundirse con reales.
4. El frontend consume exclusivamente los esquemas de `contratos/esquemas.py`.

## Solicitud de cambio de contrato

    ID:
    Contrato afectado:
    Solicitante:
    Modulos que lo consumen:
    Cambio propuesto:
    Por que no se puede resolver sin cambiarlo:
    Impacto en cada consumidor:
    Aprobado por:
    Fecha:
