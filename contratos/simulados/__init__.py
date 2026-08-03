"""
Implementaciones simuladas de los contratos.

Existen para que nadie quede bloqueado esperando codigo ajeno. Avril construye el
visor contra estos simulados sin esperar la API de Cesar; Cesar prueba el ETL sin
esperar el modelo de Alejandro.

Los datos que devuelven tienen la forma correcta pero NO son reales. Toda
instancia registra una advertencia al crearse y la API expone modo SIMULADO en
/salud, para que el frontend muestre un aviso visible. La regla de no inventar
datos no se rompe: se hace evidente que son simulados.

Cambiar un simulado por el modulo real es una linea en la fabrica, no una
refactorizacion.
"""

ES_SIMULADO = True
