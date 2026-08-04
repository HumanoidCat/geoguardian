# Roadmap

Semanas 2 a 12. Sprints de dos semanas alineados a las entregas institucionales.

## 0. Modelo de esfuerzo y capacidad

El equipo trabaja asistido por Claude. Eso cambia el esfuerzo por punto, pero no
de forma uniforme: la generacion de codigo se acelera mucho, la espera por datos,
el entrenamiento de modelos y la agenda de terceros no se aceleran nada.

### Horas por punto segun acelerabilidad

| Tipo de trabajo | h/pt | Ejemplos |
|---|---|---|
| Alta | 0.8 | DDL, procedimientos, extractores, componentes de React, pruebas, redaccion |
| Parcial | 1.3 | Entrenamiento y validacion de modelos, depuracion de Docker y Kubernetes, analisis de calidad |
| Nula | 2.2 | Sesion con el CME, interpretacion de resultados, decisiones de arquitectura |

### Calculo por epica

| Epica | Pts | Horas | h/pt |
|---|---|---|---|
| E1 Datos y base de datos | 66 | 63.3 | 0.96 |
| E2 Senales y caracteristicas | 26 | 23.8 | 0.92 |
| E3 Etiquetado y modelado | 47 | 48.6 | 1.03 |
| E4 Evaluacion y explicabilidad | 26 | 34.2 | 1.32 |
| E5 Visor geoespacial | 32 | 27.6 | 0.86 |
| E6 API y arquitectura | 21 | 18.3 | 0.87 |
| E7 Tablero | 16 | 13.8 | 0.86 |
| E8 Plataforma y Kubernetes | 21 | 22.3 | 1.06 |
| E9 Validacion externa | 15 | 28.8 | 1.92 |
| E10 Documentacion | 66 | 74.8 | 1.13 |
| **TOTAL** | **336** | **356** | **1.06** |

### Impuesto de revision

El metodo de trabajo exige verificar ejecutando todo lo que se genera. Eso cuesta
tiempo y es deliberado: codigo generado sin verificar es deuda, no avance.

    Esfuerzo base                    356 h
    Impuesto de revision (20 %)       71 h
    Esfuerzo total requerido         427 h

### Capacidad necesaria

Se asume 85 por ciento de utilizacion. Nadie rinde el 100 por ciento de las horas
que declara.

| h/persona/semana | Capacidad util | Resultado |
|---|---|---|
| 13 | 442 h | Deficit de 102 h |
| 15 | 510 h | Deficit de 34 h |
| **16** | **544 h** | **Compromiso adquirido. Cabe justo, sin holgura** |

**Al incorporar lluvia intensa como tercer evento el esfuerzo paso de 506 h a
544 h.** Antes de subir las horas conviene verificar el riesgo R16: si el canton
no tiene suficientes focos de calor historicos, se elimina el evento de incendio
y el esfuerzo baja de golpe. Esa verificacion cuesta un dia.

### Lo que la asistencia de IA NO acelera

Conviene tenerlo presente para no volver a subestimar:

- La descarga de diez anios de series climaticas tarda lo que tarda.
- El entrenamiento y la validacion por ventana expansiva consumen tiempo de
  maquina, no de persona, pero bloquean igual.
- La agenda del Comite Municipal de Emergencias no depende de nosotros.
- Interpretar por que un modelo falla en ciertos distritos es criterio humano.
- Depurar Kubernetes y Docker sigue siendo lento y frustrante.
- Verificar lo generado cuesta el 20 por ciento que ya esta presupuestado.

### Regla de control

Al planificar cada semana se suman las horas asignadas por persona. Si alguien
supera 16 h, o si el total supera 64 h, el plan no se aprueba: sale trabajo o se
reasigna. Al cierre de cada sprint se compara la velocidad real contra este
modelo y se recalibran las tres tasas de h/pt.

---

## 1. Calendario

Fechas por confirmar con el profesorado.

| Sem | Fechas | Sprint | Foco | Hito |
|---|---|---|---|---|
| 2 | 27 Jul - 2 Ago | 0 | Contratos, infraestructura, validacion de fuentes | Propuesta aprobada |
| 3 | 3 - 9 Ago | 0 | ETL funcional, DDL, arranque del paper | |
| 4 | 10 - 16 Ago | 1 | Dataset consolidado, reporte de calidad | Entrega institucional |
| 5 | 17 - 23 Ago | 1 | Caracteristicas, etiquetado, linea base | |
| 6 | 24 - 30 Ago | 2 | Tres modelos entrenados y comparados | Contactar al CME |
| 7 | 31 Ago - 6 Sep | 2 | API mas visor: demo de extremo a extremo | Primer avance |
| 8 | 7 - 13 Sep | 3 | SHAP, contraste con eventos reales | |
| 9 | 14 - 20 Sep | 3 | Visor completo, tablero, Kubernetes | |
| 10 | 21 - 27 Sep | 4 | Pruebas, manuales, sesion con el CME | Segundo avance |
| 11 | 28 Sep - 4 Oct | 4 | Documento IEEE, cartel, congelamiento | |
| 12 | 5 - 11 Oct | Cierre | Ensayos y feria | Feria |

## 2. Ruta critica

    Contratos congelados (S2)
      -> ETL real cargando en Postgres (S3)
        -> Dataset etiquetado con reporte de calidad (S4)
          -> Caracteristicas y linea base (S5)
            -> Tres modelos comparados (S6)
              -> API sirviendo predicciones (S7)
                -> Visor consumiendo la API  [DEMO COMPLETA]  (S7)
                  -> SHAP y eventos reales (S8)
                    -> Visor y tablero completos (S9)
                      -> Pruebas y sesion con el CME (S10)
                        -> Paper y cartel (S11)
                          -> Demo ensayada (S12)

**El eslabon mas fragil es el primero.** Sin contratos congelados en la semana 2,
nadie puede trabajar en paralelo y el proyecto se vuelve secuencial.

## 3. Tareas que bloquean a mas de una persona

Estas van primero, siempre, sin importar la semana.

| Tarea | Bloquea a | Dueno | Vence |
|---|---|---|---|
| Congelar contratos y publicar simulados | Los cuatro | Alejandro | Semana 2 |
| Levantar Postgres con PostGIS en Docker | Cesar, Alejandro, Luna | Alejandro | Semana 2 |
| DDL con esquemas y tablas | Cesar, Luna | Cesar | Semana 3 |
| Primer extractor cargando datos reales | Alejandro, Luna | Cesar | Semana 3 |
| Etiquetado de la variable objetivo | Alejandro, Luna | Alejandro | Semana 5 |
| API con endpoint de riesgo | Avril | Cesar | Semana 6 |

## 4. Que puede hacer cada quien sin esperar a nadie

Actualizar al cierre de cada semana.

**Alejandro.** Contratos, simulados, Docker Compose, manifiestos de Kubernetes,
modulo de senales sobre datos de prueba.

**Cesar.** Extractores contra las APIs publicas, DDL, procedimientos con
transacciones, scripts de seguridad y respaldo. Nada de esto espera a nadie.

**Luna.** Referencias IEEE con fichas de contenido, estado del arte, catalogo de
eventos historicos, plan de pruebas, perfilado de calidad de datos. Entrega
insumos escritos a Alejandro, que los integra al documento. Todo independiente.

**Avril.** Prototipo de Leaflet con las geometrias distritales, sistema de diseno,
wireframes, esqueleto de React. Consume los simulados, no la API real.

## 5. Sprint 0 en detalle (semanas 2 y 3)

| Dueno | Tarea | Horas | Depende de |
|---|---|---|---|
| Alejandro | Validar NASA POWER con coordenadas de Tilaran | 3 | - |
| Alejandro | Definir y congelar los cinco contratos | 6 | - |
| Alejandro | Escribir los simulados de cada contrato | 4 | Contratos |
| Alejandro | Docker Compose con Postgres y PostGIS | 4 | - |
| Alejandro | Crear repositorio, ramas y board en GitHub Projects | 3 | - |
| Alejandro | Iniciar el paper: introduccion y trabajos relacionados | 4 | Insumos de Luna |
| Cesar | Probar NASA FIRMS y filtrar al canton | 4 | - |
| Cesar | DDL: cuatro esquemas y tablas en 3FN | 6 | Docker |
| Cesar | Extractor de POWER cargando a Postgres | 6 | DDL, contratos |
| Cesar | Esqueleto de FastAPI con endpoint de salud | 3 | Contratos |
| Luna | Quince referencias academicas con fichas de contenido | 6 | - |
| Luna | Estado del arte de Costa Rica | 5 | Referencias |
| Luna | Catalogo de eventos historicos del canton | 4 | - |
| Luna | Plan de pruebas por modulo | 4 | Contratos |
| Avril | Prototipo de Leaflet con distritos de Tilaran | 5 | - |
| Avril | Sistema de diseno y escala de riesgo | 4 | - |
| Avril | Wireframes de las tres pantallas | 5 | - |
| Avril | Esqueleto de React con enrutamiento | 4 | Contratos |

    Alejandro  11 h    Cesar  18 h    Luna  21 h    Avril   3 h
    Total 53 h contra 128 h de capacidad en dos semanas (16 h x 4 x 2).

Cabe con holgura. El margen se usa para la curva de aprendizaje del stack y para
la puesta a punto del entorno, que siempre consume mas de lo previsto en la
primera semana.

**Alerta permanente.** Con la documentacion asignada a Alejandro, el reparto
tiende a desbalancearse hacia el en todos los sprints. Revisar el total por
persona al planificar cada semana, no al final.

## 6. Holguras

| Elemento | Holgura |
|---|---|
| Indices NDVI y NDWI | 2 semanas |
| Analisis espectral | 1 semana, sujeto a lo que diga el profesor de Senales |
| Manifiestos de Kubernetes | 1 semana |
| Documento IEEE y cartel | Cero. Fecha fija |
| Sesion con el CME | Cero. Depende de terceros. Escribir en la semana 6 |
