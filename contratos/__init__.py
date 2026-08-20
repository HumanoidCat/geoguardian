"""
Contratos congelados de GeoGuardian.

Estas interfaces se definen antes de implementar y no se modifican sin solicitud
de cambio aprobada por el Lead PM y por los duenos de los modulos que las
consumen. Ver docs/02-contratos.md.

Cada contrato tiene un simulado en contratos/simulados/ que lo respeta, para que
nadie quede bloqueado esperando codigo ajeno.
"""

# 1.3.2 · 2026-08-20 · El resto de `RepositorioSimulado` se vuelve determinista:
#         `obtener_mediciones`, `contar_focos` y `obtener_indices`. Lo encontro
#         Cesar revisando SC-03: el arreglo de 1.3.1 cubria solo el riesgo. En
#         mediciones el defecto era peor, porque un mismo dia devolvia dos
#         temperaturas segun el rango pedido. Solicitud SC-04, incidencia I-08.
# 1.3.1 · 2026-08-20 · `RepositorioSimulado.obtener_riesgo` deja de sortear
#         contra un generador con estado y su `nivel` se deriva de la
#         `probabilidad`, coherente con D-21. Solicitud SC-03, incidencia I-08.
# 1.3.0 · 2026-08-18 · `ProcesadorSenales.spi` recibe `meses`, opcional, para
#         ajustar la distribucion por mes calendario. Cambio aditivo: ninguna
#         llamada existente se rompe. Sale de la solicitud SC-02 de Luna y de la
#         medicion que la sostiene. Ver decision D-19.
# 1.2.0 · 2026-08-11 · Codigos de distrito corregidos de 50501-50508 a los
#         oficiales 50801-50808. Tilaran es el canton 08 de Guanacaste, no el 05.
#         Defecto detectado por Cesar contra el WFS del SNIT. Ver incidencia I-04.
# 1.1.0 · Tercer tipo de evento: lluvia intensa.
# 1.0.0 · Contratos iniciales.
VERSION_CONTRATOS = "1.3.2"
