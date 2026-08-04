# Reparto del backlog

**71 historias · 366 puntos · 544 horas** (incluye 20 % de revision)

| Persona | S0 | S1 | S2 | S3 | S4 | Total h | Puntos | h/semana |
|---|---|---|---|---|---|---|---|---|
| Alejandro | 10.7 | 37.7 | 44.0 | 48.0 | 52.8 | 193 | 117 | 19.3 |
| Cesar | 18.3 | 25.1 | 24.8 | 29.8 | 15.5 | 114 | 93 | 11.3 |
| Luna | 25.9 | 34.3 | 31.0 | 25.1 | 32.0 | 148 | 85 | 14.8 |
| Avril | 2.9 | 11.5 | 26.0 | 25.0 | 24.1 | 90 | 71 | 8.9 |
| **Equipo** | **58** | **109** | **126** | **128** | **124** | **544** | **366** | |

> El Lead PM asume la documentacion completa y el nucleo de modelado, por eso
> concentra un tercio del esfuerzo. Es una decision, no un desbalance accidental.

## Compromiso de tiempo: 16 horas por persona por semana

Al incorporar lluvia intensa como tercer evento, el esfuerzo paso de 506 h a
544 h. Con 85 por ciento de utilizacion realista, **el proyecto exige 16 horas
por persona por semana**. Es el numero con el que se entrega en la semana 12 sin
recortar alcance ni bajar la calidad de los entregables.

    4 personas x 16 h x 10 semanas = 640 h
    Utilizacion realista al 85 %    = 544 h
    Esfuerzo requerido              = 544 h

No hay holgura. Eso significa que una semana perdida no se recupera sola: se
recupera trabajando de mas o recortando alcance, y el alcance ya esta comprometido
con cinco asignaturas.

**Verificacion pendiente que puede cambiar este numero.** El riesgo R16 dice que
el canton podria no tener suficientes focos de calor historicos para entrenar el
modelo de incendio. Si se confirma, ese evento sale y el esfuerzo baja alrededor
de 60 h. La verificacion cuesta un dia y va antes que cualquier otra tarea.

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
