# Reparto del backlog

**82 historias · 417 puntos · 616 horas** (incluye 20 % de revision)

| Persona | S0 | S1 | S2 | S3 | S4 | Total h | Puntos | h/semana |
|---|---|---|---|---|---|---|---|---|
| Alejandro | 35.9 | 47.8 | 47.0 | 45.1 | 65.4 | 241 | 147 | 24.1 |
| Cesar | 18.3 | 28.0 | 31.5 | 37.6 | 18.4 | 134 | 111 | 13.4 |
| Luna | 25.9 | 34.3 | 31.0 | 20.3 | 32.0 | 144 | 80 | 14.3 |
| Avril | 2.9 | 11.5 | 26.0 | 25.0 | 31.8 | 97 | 79 | 9.7 |
| **Equipo** | **83** | **122** | **136** | **128** | **148** | **616** | **417** | |

> El Lead PM asume el pipeline de CI/CD completo, el nucleo de modelado y toda
> la documentacion. Concentra el 39 % del esfuerzo por decision propia.

## Compromiso de tiempo: 18 horas por persona por semana

La rubrica de Arquitectura de Software incorporo CI/CD completo, una herramienta
de resolucion de incidencias, evidencia de ceremonias Scrum y manual de operacion:
51 puntos y 72 horas mas. El esfuerzo paso de 544 h a 616 h.

    4 personas x 18 h x 10 semanas = 720 h
    Utilizacion realista al 85 %   = 612 h
    Esfuerzo requerido             = 616 h

No hay holgura. Una semana perdida no se recupera sola.

**Verificacion pendiente que puede bajar este numero.** El riesgo R16: si el canton
no tiene suficientes focos de calor historicos, sale el evento de incendio y el
esfuerzo baja alrededor de 60 h. Cuesta un dia y va antes que cualquier otra tarea.

## El crunch final es estructural

Los sprints 3 y 4 estan por encima de la capacidad nominal y los sprints 0 y 1
por debajo. No es un error de calculo: es la forma que imponen las dependencias.

- El documento IEEE no se escribe antes de que existan resultados.
- La sesion con el Comite Municipal de Emergencias necesita algo que mostrar.
- Los manuales describen un producto que todavia no esta terminado.
- SHAP y el contraste con eventos reales dependen de los modelos entrenados.

**Mitigaciones:**

1. Adelantar todo lo adelantable en S0 y S1, que estan flojos: referencias,
   estado del arte, catalogo de eventos, plantillas de manuales, guion de demo.
2. Escribir el paper de forma incremental desde la semana 3.
3. Escribir al CME en la semana 6 para agendar la sesion de la semana 10.
4. Congelar funcionalidades al inicio de la semana 11.

**Riesgo declarado:** si S0 y S1 se desaprovechan, el crunch de S3 y S4 se vuelve
inviable. El margen de las primeras semanas no es tiempo libre: es el colchon de
las ultimas.

## Archivos por persona

- [Alejandro](alejandro.md) · [Cesar](cesar.md) · [Luna](luna.md) · [Avril](avril.md)
