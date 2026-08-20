# Reparto del backlog

**85 historias · 423 puntos · 620.3 horas** (incluye 20 % de revision)

> El detalle completo, con dependencias de cada historia, esta en
> [`docs/08-backlog.md`](../08-backlog.md). Este archivo es solo el resumen.

| Persona | S0 | S1 | S2 | S3 | S4 | Total h | Puntos | h/semana |
|---|---|---|---|---|---|---|---|---|
| Alejandro | 35.9 | 22.8 | 59.5 | 35.7 | 52.8 | 206.7 | 123 | 20.7 |
| Cesar | 18.3 | 30.9 | 31.5 | 39.2 | 34.0 | 153.9 | 125 | 15.4 |
| Luna | 25.9 | 34.3 | 31.0 | 20.3 | 32.0 | 143.5 | 80 | 14.3 |
| Avril | 2.9 | 19.3 | 30.8 | 25.0 | 36.6 | 114.6 | 94 | 11.5 |
| **Equipo** | **83.0** | **107.3** | **152.8** | **120.2** | **155.4** | **618.7** | **422** | |

## Compromiso de tiempo: 18 horas por persona por semana

    4 personas x 18 h x 10 semanas = 720 h
    Utilizacion realista al 85 %   = 612 h
    Esfuerzo requerido             = 618.7 h

No hay holgura. Una semana perdida no se recupera sola.

## Reparto revisado el 2026-08-11

La auditoria de dependencias encontro tres historias que dependian de trabajo
programado para sprints posteriores, y una cadena de seis historias de despliegue
colgando de un Dockerfile que nadie tenia asignado. Al corregirlo, el trabajo se
redistribuyo:

- **H6.0**, el Dockerfile, es historia nueva y va a Cesar en el Sprint 1.
- **H10.3**, **H10.7** y **H13.2** pasan a Avril: manual de usuario, diagramas de
  casos de uso y entidad-relacion, y manual de operacion.
- **H3.5** (XGBoost) y **H12.3** (alertas) pasan a Cesar, que ya entrena los otros
  dos algoritmos y ya centraliza los logs.
- **H3.0** y **H10.7** se mueven al Sprint 2, que es donde por fin se pueden hacer.

El detalle esta en `gestion/auditoria-dependencias-backlog.md`.

## Lo que sigue sin cuadrar, y hay que decirlo

Alejandro queda en 206.7 h contra una capacidad de 180, con el Sprint 2 en 59.5 h y
el Sprint 4 en 52.8 h. La descarga no alcanzo a cerrarlo del todo.

Las dos concentraciones que quedan son estructurales, no de reparto:

- **Sprint 2** junta toda la cadena de despliegue continuo con el arranque del
  modelado, y las dos preceden al primer avance de la semana 7.
- **Sprint 4** junta el documento IEEE, el contraste contra el catalogo y el
  analisis de fallos. Ninguna de las tres se puede adelantar: dependen de tener
  resultados.

**Palanca disponible si el Sprint 4 se vuelve inviable:** H4.4 son 26.4 h en una
sola historia, la mas grande del backlog. Se puede partir en dos, dejando el
contraste contra el catalogo a Luna, que es quien lo construye en H4.3, y el
analisis de fallos al Lead PM. No se hizo todavia porque cambia la carga de
alguien que ya esta trabajando.

## Archivos por persona

- [Alejandro](alejandro.md) · [Cesar](cesar.md) · [Luna](luna.md) · [Avril](avril.md)
