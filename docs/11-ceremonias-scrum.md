# Actas de las ceremonias Scrum

**Proyecto:** GeoGuardian · Proyecto Integrador TICE · III Trimestre 2026
**Historia:** H13.1 · **Rúbrica:** Scrum · **Responsable:** Alejandro (Scrum Master)
**Periodo cubierto:** Sprint 0 (semanas 2-3) y Sprint 1 en curso (semanas 4-5)

## Integrantes

| Persona | Rol Scrum | Foco |
|---|---|---|
| Alejandro Josué Rodríguez Zamora | Product Owner y Scrum Master | Arquitectura, plataforma, modelado |
| César Andrés Ubau Calvo | Developer | Backend, ETL, base de datos |
| Luis Alejandro Luna García | Developer | Investigación, calidad y QA |
| Avril Madrigal Elizondo | Developer | Interfaz y visualización |

## Nota sobre la modalidad

Este equipo trabaja de forma **asincrónica**: cuatro estudiantes con horarios de
clase distintos, en remoto, con 18 horas semanales comprometidas que no coinciden
entre sí. Las ceremonias se celebran por escrito, no en reunión sincrónica, y cada
acta lo declara en su encabezado.

La decisión se tomó al arrancar y quedó escrita en `docs/cowork-equipo.md` el 3 de
agosto, antes de la primera historia. No es una justificación posterior.

**Cada acta de este documento corresponde a un hecho verificable en el
repositorio**: un commit, un Pull Request, un documento de consulta o su respuesta.
La columna de evidencia de cada acta indica dónde comprobarlo. No hay ninguna
sesión, hora ni participante registrado que no tenga respaldo.

---

# SPRINT 0 · Semanas 2 y 3 · del 27 de julio al 9 de agosto de 2026

---

## ACTA 01 · Sprint Planning inicial

| | |
|---|---|
| **Tipo de ceremonia** | Sprint Planning |
| **Sprint** | 0 |
| **Fecha** | 3 de agosto de 2026 |
| **Modalidad** | Asincrónica. Documento de planificación distribuido al equipo |
| **Convoca** | Alejandro, Scrum Master |
| **Participantes** | Alejandro (autor), César, Luna y Avril (receptores del reparto) |
| **Evidencia** | Commit `chore: estructura inicial, contratos congelados y backlog`; `gestion/GeoGuardian_Project_Charter.md`; `gestion/mensaje-arranque-equipo.md` |

### Asuntos tratados

1. Alcance del proyecto tras la evaluación docente de la propuesta inicial.
2. Composición y estimación del backlog.
3. Definición de la estrategia para permitir trabajo paralelo.
4. Compromiso de capacidad por persona.

### Acuerdos

**A1.1 · Reducción del alcance en un 38 %.** La evaluación docente calificó la
viabilidad en 12 semanas con 5/10 y describió el proyecto como "aproximadamente el
trabajo de una tesis de licenciatura". Se eliminan: módulo de búsqueda semántica,
sensores físicos, procesamiento en tiempo real, autenticación de usuarios,
segmentación con algoritmos propios y animación temporal. Total retirado: 118 de
310 puntos.

**A1.2 · Backlog de 83 historias**, repartido por persona con estimación en puntos
y horas, dependencias declaradas y criterio de rúbrica asignado a cada una.

**A1.3 · Contratos congelados antes de implementar.** Las interfaces entre módulos
se definen y se acuerdan primero, cada una con un simulado que las cumple, para
que nadie quede bloqueado esperando código ajeno.

**A1.4 · Compromiso de 18 horas semanales por persona.** La capacidad se calculó
contra el backlog: 427 horas requeridas contra 612 de capacidad útil, asumiendo un
85 % de utilización.

### Acciones

| # | Acción | Responsable | Estado |
|---|---|---|---|
| 1.1 | Congelar los cinco contratos y publicar sus simulados | Alejandro | Cumplida el 3 ago |
| 1.2 | Levantar PostgreSQL con PostGIS en Docker | Alejandro | Cumplida el 3 ago |
| 1.3 | Crear repositorio, ramas y tablero | Alejandro | Cumplida el 3 ago |
| 1.4 | Distribuir el archivo de tareas a cada integrante | Alejandro | Cumplida el 3 ago |

---

## ACTA 02 · Refinamiento del backlog por rúbrica sobreviniente

| | |
|---|---|
| **Tipo de ceremonia** | Refinamiento del backlog |
| **Sprint** | 0 |
| **Fecha** | 4 de agosto de 2026 |
| **Modalidad** | Asincrónica |
| **Participantes** | Alejandro |
| **Evidencia** | Commit `docs: incorporar la rubrica de Arquitectura de Software y actualizar las guias`; `gestion/Matriz_Cobertura_Rubricas.md` |

### Asuntos tratados

Recepción de la rúbrica de Arquitectura de Software, que no se tenía al planificar
el Sprint 0.

### Acuerdos

**A2.1 · El backlog crece de 506 a 616 horas de esfuerzo.** La rúbrica agrega
integración y despliegue continuos completos, herramienta de resolución de
incidencias, actas de ceremonias y manual de operación.

**A2.2 · El crecimiento se registra en lugar de absorberse en silencio.** Queda
documentado en el roadmap con su origen, para que la sobrecarga que aparezca
después tenga causa identificable.

### Acciones

| # | Acción | Responsable | Estado |
|---|---|---|---|
| 2.1 | Actualizar el modelo de capacidad del roadmap | Alejandro | Cumplida |
| 2.2 | Construir la matriz de cobertura de las cinco rúbricas | Alejandro | Cumplida |

---

## ACTA 03 · Reporte de impedimento · Luna

| | |
|---|---|
| **Tipo de ceremonia** | Daily Scrum, equivalente asincrónico |
| **Sprint** | 0 |
| **Fecha** | 5 de agosto de 2026 |
| **Modalidad** | Asincrónica. Documento de solicitud y respuesta escrita el mismo día |
| **Reporta** | Luna |
| **Responde** | Alejandro |
| **Evidencia** | `solicitud-carpeta-evidencias.md` (Luna); `gestion/respuesta-luna-evidencias.md` |

### Impedimento reportado

`docs/evidencias/` tenía subcarpetas por materia, pero ninguna correspondía a las
rúbricas QA y OE4, que son las de Luna. Sin carpeta destino no se podía cumplir el
paso de la Definition of Done que exige archivar la evidencia el mismo día.

### Acuerdos

**A3.1 · Se completa la estructura de `docs/evidencias/` por rúbrica**, incluidas
`calidad/`, `objetivos/` y `entregables/`.

**A3.2 · `docs/evidencias/` pasa a ser de escritura libre para todo el equipo.**
Cada quien sube la evidencia de sus propias historias sin solicitud previa. Es la
excepción explícita a la regla de propiedad de archivos. Registrado como decisión
**D-11**.

### Acciones

| # | Acción | Responsable | Estado |
|---|---|---|---|
| 3.1 | Crear la estructura completa de carpetas | Alejandro | Cumplida el 5 ago |
| 3.2 | Registrar D-11 y actualizar `CONTRIBUTING.md` | Alejandro | Cumplida |

**Tiempo de respuesta: mismo día.**

---

## ACTA 04 · Revisión de incremento · PR #86 y #87

| | |
|---|---|
| **Tipo de ceremonia** | Sprint Review |
| **Sprint** | 0 |
| **Fecha** | 6 de agosto de 2026 |
| **Modalidad** | Asincrónica. Revisión escrita sobre Pull Request |
| **Revisa** | Alejandro |
| **Autor del incremento** | Luna |
| **Evidencia** | `gestion/review-pr86.md`, `gestion/review-pr87.md`; historial de los PR #86 y #87 |

### Incremento presentado

| PR | Historia | Contenido |
|---|---|---|
| #86 | H10.1 | Plan de pruebas con 39 casos por contrato |
| #87 | H10.5a | Referencias IEEE con ficha de contenido |

### Resultado de la revisión

**Ambos devueltos con cambios solicitados.** Defectos encontrados:

| PR | Defecto |
|---|---|
| #86 | Faltaban los casos que verifican la ausencia de fuga temporal, declarada como invariante pero no probada |
| #86 | Ruta de evidencia incorrecta según el mapa de rúbricas |
| #87 | 8 fichas de las 15 exigidas |
| #87 | Faltaban Regresión Logística y los índices ETCCDI, ambos citados en el proyecto sin referencia |
| #87 | `Closes #N` escrito en prosa, que no cierra la issue |
| #87 | Solicitud de carpeta ya resuelta, incluida en el PR |

### Acuerdos

**A4.1 · La revisión devuelve trabajo cuando corresponde.** No se aprueba por
cortesía: un incremento que no cumple la Definition of Done vuelve.

### Acciones

| # | Acción | Responsable | Estado |
|---|---|---|---|
| 4.1 | Corregir el plan de pruebas y agregar evidencia | Luna | Cumplida el 12 ago |
| 4.2 | Completar las referencias a 15 y corregir el cuerpo del PR | Luna | Cumplida el 13 ago |

---

## ACTA 05 · Reporte de impedimento · César

| | |
|---|---|
| **Tipo de ceremonia** | Daily Scrum, equivalente asincrónico |
| **Sprint** | 0 |
| **Fecha** | 11 de agosto de 2026 |
| **Modalidad** | Asincrónica. Documento de consulta y respuesta escrita el mismo día |
| **Reporta** | César |
| **Responde** | Alejandro |
| **Evidencia** | `consultas-h13.md` (César); `gestion/respuesta-cesar-h1.3.md`; incidencia I-04; decisión D-13 |

### Impedimentos reportados

Cuatro consultas al redactar los criterios de aceptación de H1.3, **antes de
escribir código**. Dos bloqueantes:

1. **Los códigos de distrito de los contratos no son los oficiales.** Los simulados
   usaban 50501-50508, que corresponde al cantón de Carrillo. Los oficiales del
   SNIT son 50801-50808: Tilarán es el cantón 08 de Guanacaste, no el 05.
2. **H1.1 depende de H1.3 y el backlog lo declaraba sin dependencias.**
   `ExtractorClima` recibe un código de distrito, pero la fuente climática consulta
   por coordenada, y esa traducción sale de las geometrías que carga H1.3.

### Acuerdos

**A5.1 · Contratos a la versión 1.2.0** con los ocho códigos corregidos.

**A5.2 · El verificador pasa a comprobar contenido y no solo estructura.** Se
agregan dos comprobaciones: que todos los códigos empiecen por `508` y que sean
exactamente 50801 a 50808. El defecto existía porque el verificador validaba que
hubiera ocho distritos, no que existieran en la realidad.

**A5.3 · El SNIT queda como fuente única del vocabulario territorial.** Registrado
como **D-13**.

**A5.4 · Se invierte el orden de ejecución:** H1.3 antes que H1.1. Se corrige la
dependencia en el backlog y en el archivo de tareas.

**A5.5 · Se registra la incidencia I-04** con causa raíz: al escribir los simulados
se inventó el prefijo de cantón en lugar de consultarlo en la fuente oficial. Es la
regla de no inventar datos, rota por quien la escribió.

### Acciones

| # | Acción | Responsable | Estado |
|---|---|---|---|
| 5.1 | Subir contratos a v1.2.0 y avisar al equipo de hacer `git pull` | Alejandro | Cumplida el 11 ago |
| 5.2 | Registrar I-04 y D-13 | Alejandro | Cumplida el 11 ago |
| 5.3 | Corregir la dependencia en backlog y tareas | Alejandro | Cumplida el 11 ago |

**Tiempo de respuesta: mismo día. Impacto evitado:** sin la detección, el error
habría aparecido en H1.2, cuando ningún foco de calor cayera dentro de ningún
distrito, con una causa raíz muy cara de diagnosticar.

---

## ACTA 06 · Revisión de incremento · PR #88 y #89

| | |
|---|---|
| **Tipo de ceremonia** | Sprint Review |
| **Sprint** | 0 |
| **Fecha** | 11 de agosto de 2026 |
| **Modalidad** | Asincrónica |
| **Revisa** | Alejandro |
| **Evidencia** | `gestion/cuerpo-pr-alejandro-s0.md`, `gestion/cuerpo-pr-alejandro-h8.6.md`; PR #88 y #89 |

### Incremento presentado

| PR | Historias | Contenido |
|---|---|---|
| #88 | H10.8, H6.4, H8.5 | Carpeta de evidencias, 14 registros ADR, credenciales fuera del repositorio |
| #89 | H8.6 | Tres entornos de Kubernetes en k3d |

### Resultado

Ambos aprobados e integrados. Se cierran tres historias del Sprint 0 con evidencia
archivada.

### Acuerdos

**A6.1 · Las issues se cierran, no se eliminan.** Una issue cerrada conserva la
discusión, los commits y el Pull Request enlazados.

**A6.2 · Se registra la incidencia I-03** sobre la conexión de kubectl al clúster
recién creado, con su aprendizaje: un error de red de kubectl no significa clúster
mal creado, y conviene mirar el kubeconfig antes de borrar y recrear.

---

## ACTA 07 · Replanificación · auditoría de dependencias

| | |
|---|---|
| **Tipo de ceremonia** | Refinamiento y replanificación |
| **Sprint** | 0, con efecto sobre 1 y 2 |
| **Fecha** | 12 de agosto de 2026 |
| **Modalidad** | Asincrónica |
| **Participantes** | Alejandro |
| **Evidencia** | PR #91; `docs/09-auditoria-backlog.md`; `docs/herramientas/verificar_backlog.py` |

### Asuntos tratados

Auditoría de las dependencias declaradas en las 83 historias del backlog.

### Hallazgos

**Tres dependencias apuntaban a sprints posteriores**: historias que dependían de
trabajo planificado para después de ellas mismas. Con esa configuración, el sprint
no podía cerrarse.

### Acuerdos

**A7.1 · Se reprograman las tres historias afectadas.**

**A7.2 · Se agrega `verificar_backlog.py` al pipeline de integración continua**,
para que una dependencia inconsistente falle en el momento y no en la semana en que
bloquea a alguien.

**A7.3 · El backlog se versiona en el repositorio** como `docs/backlog.csv`, en
lugar de vivir solo en el tablero.

### Acciones

| # | Acción | Responsable | Estado |
|---|---|---|---|
| 7.1 | Corregir las tres dependencias | Alejandro | Cumplida el 12 ago |
| 7.2 | Integrar el verificador al CI | Alejandro | Cumplida el 12 ago |

---

## ACTA 08 · Reporte de impedimento · Avril

| | |
|---|---|
| **Tipo de ceremonia** | Daily Scrum, equivalente asincrónico |
| **Sprint** | 0 |
| **Fecha** | 12 de agosto de 2026 |
| **Modalidad** | Asincrónica. Documento de bloqueo y respuesta escrita el mismo día |
| **Reporta** | Avril |
| **Responde** | Alejandro |
| **Evidencia** | `bloqueo-frontend.md` (Avril); `gestion/respuesta-avril-bloqueo-frontend.md`; decisión D-14; PR #93 |

### Impedimentos reportados

1. **No podía crear `frontend/package.json`.** Figuraba como archivo compartido, lo
   que exigía solicitud aprobada, pero la carpeta `frontend/` estaba vacía: no se
   podía crear el andamiaje sin generarlo, ni generarlo sin aprobación.
2. **El navegador no puede leer los simulados**, que son objetos de Python. Entre
   el simulado y el visor no había puente hasta que existiera la API, prevista para
   la semana 6.

Además reportó **cinco defectos en archivos del Scrum Master**, los cinco reales:
la guía de arranque no instalaba Node, declaraba un número de verificaciones
desactualizado, el README citaba una versión de contratos vieja y no aclaraba que
Node 20 era el mínimo, y el pipeline de CI no tenía ningún trabajo de frontend.

### Acuerdos

**A8.1 · Se corrige la regla de propiedad de archivos.** Ahora distingue entre
modificar un archivo compartido, que requiere solicitud, y crearlo por primera vez
dentro de la carpeta propia, que no. Se agrega además que **leer** un archivo
compartido nunca requiere solicitud.

**A8.2 · El frontend consume los simulados exportados a JSON estático.** Avril
escribió un exportador que lee `contratos/simulados/` en solo lectura y escribe en
`frontend/public/`. Registrado como **D-14**.

**A8.3 · Se aceptan los cinco defectos reportados** y se corrigen en los archivos
del Scrum Master.

**A8.4 · Se rechaza un sexto hallazgo.** Avril reportó que el documento IEEE
mencionaba dos eventos y faltaba lluvia intensa; se comprobó el documento y ya
menciona los tres. Se le respondió con la aclaración en lugar de asumir que tenía
razón.

**A8.5 · H1.6 se adelanta del Sprint 2 al Sprint 1.** No depende de nada, bloquea a
dos historias de otras personas y requiere una cuenta de Copernicus cuyo trámite no
controla el equipo. El argumento lo propuso Avril y se adopta.

### Acciones

| # | Acción | Responsable | Estado |
|---|---|---|---|
| 8.1 | Corregir la regla de propiedad de archivos | Alejandro | Cumplida el 12 ago |
| 8.2 | Registrar D-14 | Alejandro | Cumplida el 12 ago |
| 8.3 | Corregir los cinco defectos y agregar el trabajo de frontend al CI | Alejandro | Cumplida el 12 ago |
| 8.4 | Adelantar H1.6 y recalcular capacidad | Alejandro | Cumplida el 12 ago |

**Tiempo de respuesta: mismo día. Resultado medible:** la carga de Avril pasa de
11,5 h en S1 y 38,6 h en S2 —por encima del compromiso— a 19,3 h y 30,8 h.

---

## ACTA 09 · Revisión de incremento y cierre del Sprint 0

| | |
|---|---|
| **Tipo de ceremonia** | Sprint Review |
| **Sprint** | 0 |
| **Fecha** | 13 de agosto de 2026 |
| **Modalidad** | Asincrónica |
| **Revisa** | Alejandro |
| **Autores del incremento** | Luna, César |
| **Evidencia** | PR #86, #87, #94 |

### Incremento presentado

| PR | Historia | Autor | Resultado |
|---|---|---|---|
| #86 | H10.1 plan de pruebas | Luna | Aprobado tras corrección |
| #87 | H10.5a referencias IEEE | Luna | Aprobado tras corrección |
| #94 | H1.3 geometrías de distritos | César | Aprobado |

### Observaciones de la revisión

**Sobre #87.** Luna descartó dos referencias que no pudo verificar contra la fuente
primaria, aun cuando eso la dejaba corta para el mínimo exigido, y lo declaró en la
evidencia. También omitió la paginación de una cita en lugar de elegir entre dos
versiones contradictorias sin poder confirmarla. Ambas decisiones se señalaron como
criterio correcto.

**Sobre #94.** El área del cantón calculada, 669,23 km², no coincide con la cifra
divulgativa de 638 que suele citarse. No es un error de cálculo: los ocho distritos
recubren el polígono cantonal oficial con 0,0001 km² de diferencia sobre la misma
fuente. Queda explicado en la evidencia.

### Estado al cierre del Sprint 0

Contado sobre el último commit del 13 de agosto en `dev`, con dos métodos
independientes que coinciden:

| Persona | Historias cerradas con evidencia | Cuáles |
|---|---|---|
| Alejandro | 5 | H10.8, H6.4, H8.1, H8.5, H8.6 |
| César | 1 | H1.3 |
| Luna | 2 | H10.1, H10.5a |
| Avril | 0 | — |
| **Total** | **8 de 83** | |

El reparto desigual es esperado y estaba anotado como alerta en el roadmap: con la
documentación asignada al Scrum Master, la carga tiende a concentrarse en él. Avril
arrancó con 2,9 h asignadas en el Sprint 0 por diseño, no por retraso, y cerró H5.1
tres días después.

**Ocho historias de 83 al cerrar el primer sprint de cinco.** El dato no se maquilla:
de esas ocho, seis son de infraestructura y documentación y solo H1.3 es código que
va a correr en el sistema final. La velocidad de producto todavía no se puede medir.

### Acciones abiertas al cierre

| # | Acción | Responsable |
|---|---|---|
| 9.1 | Los simulados de señales y modelado no existen y bloquean 16 de los 39 casos de prueba de Luna | Alejandro |
| 9.2 | Calcular la velocidad real del sprint y contrastarla contra el modelo de horas por punto | Alejandro |

---

# SPRINT 1 · Semanas 4 y 5 · del 10 al 23 de agosto de 2026

---

## ACTA 10 · Reporte de impedimento · César

| | |
|---|---|
| **Tipo de ceremonia** | Daily Scrum, equivalente asincrónico |
| **Sprint** | 1 |
| **Fecha** | 16 de agosto de 2026 |
| **Modalidad** | Asincrónica. Documento de consulta y respuesta escrita el mismo día |
| **Reporta** | César |
| **Responde** | Alejandro |
| **Evidencia** | `MENSAJ_1.MD` (César); `gestion/respuesta-cesar-h1.1-h1.8.md`; decisión D-15; incidencia I-05; PR #97 y #98 |

### Impedimento reportado

**Bloqueante, y toca la hipótesis del proyecto.** Antes de escribir el extractor de
H1.1, César comprobó qué devuelve NASA POWER para dos puntos distintos del cantón:
devuelve exactamente lo mismo, hasta el último decimal, incluida la elevación.

La causa es la resolución. POWER sirve MERRA-2 en celdas de unos 68 × 55 km a la
latitud de Tilarán, y el cantón entero cabe en una sola. Dos de los tres eventos
—sequía por SPI-3 y lluvia intensa por acumulado de 72 h— se definen sobre
precipitación, así que darían el mismo riesgo en los ocho distritos por
construcción y no por hallazgo.

Reportó además tres consultas de diseño sobre H1.8, ninguna bloqueante.

### Acuerdos

**A10.1 · Fuente climática híbrida.** CHIRPS a 0,05° para precipitación, que es la
variable que define los dos umbrales rotos; NASA POWER se mantiene para
temperatura, humedad, radiación y viento, que no definen ninguno. Registrado como
**D-15**.

**A10.2 · La decisión queda condicionada a verificación previa.** Antes de escribir
el extractor hay que repetir sobre CHIRPS el mismo test de dos puntos que descartó
a POWER. Una resolución nominal mejor no es prueba de diferenciación real.

**A10.3 · Se descarta ERA5-Land**, cuya malla nativa de 9 km no se expone por API
—el Climate Data Store entrega 0,1°— y que además exige una cuenta con espera.

**A10.4 · La ventana de descarga pasa de 2016-2025 a 1991-2025.** La línea base se
define sobre la normal climatológica 1991-2020: con diez años no se podía calcular
como está declarada y el contraste de la hipótesis se caía. Lo levantó César como
tercera consulta y en realidad era el segundo asunto bloqueante.

**A10.5 · Se corrige un dato del reporte.** La extensión del cantón declarada,
22 × 17 km, son 374 km², menor que los 669 km² medidos en H1.3. Un polígono no
puede tener más área que su caja envolvente: el número salió de medir la separación
entre los dos puntos de muestreo. No invalida el hallazgo, pero cambia el modo de
fallo, y por eso el PR #97 se devuelve con cambios.

**A10.6 · Se resuelven las tres consultas de H1.8:** se mantiene el rol de solo
lectura, se acuerdan los nombres `etl_geoguardian` y `api_geoguardian`, y se
confirma que la API no lee el esquema de datos crudos.

**A10.7 · Se registra la incidencia I-05** con causa raíz: la fuente se eligió por
cobertura temporal y facilidad de acceso, y nadie comprobó su resolución espacial
contra el tamaño del área de estudio.

### Acciones

| # | Acción | Responsable | Estado |
|---|---|---|---|
| 10.1 | Registrar D-15 e I-05 | Alejandro | Cumplida el 16 ago |
| 10.2 | Actualizar backlog, roadmap y README con la fuente y la ventana | Alejandro | Cumplida el 16 ago |
| 10.3 | Completar `.env.example` con los nombres acordados | Alejandro | Cumplida el 16 ago |
| 10.4 | Verificar CHIRPS con el test de dos puntos antes de implementar | César | Cumplida el 18 ago |
| 10.5 | Corregir la extensión del cantón en los criterios de H1.1 | César | Cumplida el 18 ago |

### Resultado de las acciones 10.4 y 10.5

**10.4 · CHIRPS diferencia.** Los ocho distritos caen en ocho celdas distintas, y
sobre datos reales del 1 al 7 de setiembre de 2024 el acumulado semanal va de 97,25
mm en Tronadora a 117,04 en Tierras Morenas, un 20,3 % de diferencia. Lo que más
sostiene la decisión es que **el orden entre distritos cambia de un día a otro**,
que es variación espacial y no un sesgo constante del método. **D-15 queda firme**
y H1.1 se desbloquea.

**10.5 · La extensión real es 30,7 × 36,6 km**, con una caja envolvente de 1.124
km² que contiene los 669,23 km² del cantón. El cantón es más alto que ancho, al
revés de lo que decía la versión anterior.

César rastreó de dónde salía el número falso, que es lo que evita que se repita:
los 22 × 17 km no venían de ninguna medición sino de las líneas 251 y 252 de
`contratos/simulados/datos.py`, los rangos con los que el generador inventa focos
**simulados** al azar. Comprobado: 10,40–10,55 de latitud son 16,6 km y −85,05 a
−84,85 de longitud son 21,9 km. Exactamente 22 × 17.

Es la misma clase de defecto que I-04: un dato del simulado que se cuela a un
documento con etiqueta de medido.

**Un hallazgo nuevo, anotado sin darlo por cierto.** En los cinco primeros días de
la muestra, seis de los ocho distritos dan valores que son múltiplos enteros
exactos de una unidad base, y el patrón se rompe en el día 6. Cinco días son una
péntada, y CHIRPS reparte totales de péntada entre sus días. Es consistente, pero
una semana no alcanza para afirmarlo. Importa porque el umbral de lluvia intensa se
define sobre acumulados de 72 h. Queda para verificar sobre la serie completa y
documentar como limitación antes del modelado.

**Tiempo de respuesta: mismo día. Impacto evitado:** sin la detección, el defecto
habría aparecido en la semana 8 o 9, con el modelo entrenado y el visor pintando
ocho polígonos idénticos, y con la pregunta de investigación ya respondida por
construcción.

---

## ACTA 11 · Revisión de incremento

| | |
|---|---|
| **Tipo de ceremonia** | Sprint Review |
| **Sprint** | 1 |
| **Fecha** | 16 de agosto de 2026 |
| **Modalidad** | Asincrónica |
| **Revisa** | Alejandro; César revisa los incrementos del Scrum Master |
| **Evidencia** | PR #96 a #101 |

### Incremento presentado

| PR | Historia | Autor | Resultado |
|---|---|---|---|
| #96 | H5.1 visor con los ocho distritos | Avril | Aprobado |
| #97 | H1.1 criterios de aceptación | César | **Cambios solicitados** |
| #98 | H1.8 criterios de aceptación | César | Aprobado |
| #99 | Simulados de señales y modelado | Alejandro | Aprobado por César |
| #100 | D-15, I-05 y desbloqueo de H1.8 | Alejandro | Aprobado por César |
| #101 | H10.4 manual técnico | Alejandro | Aprobado por César |

### Observaciones de la revisión

**Sobre #96.** El encuadre del mapa se calcula a partir de la geometría recibida en
lugar de fijar coordenadas: cuando lleguen las geometrías reales el mapa seguirá
funcionando. Los ocho distritos se pintan con la trama de ausencia de dato y no con
un color de la escala de riesgo, porque no hay modelo entrenado y pintarlos
afirmaría un riesgo que nadie calculó.

**Sobre #98.** El criterio CA-5 verifica las **denegaciones** de permiso y no solo
las concesiones. Una lista de permisos concedidos no demuestra mínimo privilegio;
lo demuestra que las operaciones prohibidas fallen.

**Sobre #99.** Desbloquea los 16 casos de prueba que Luna tenía detenidos desde el
6 de agosto, el 41 % de su plan. La acción 9.1 del Sprint 0 queda cumplida.

**Sobre #101.** La verificación del manual encontró tres defectos en la
documentación propia del Scrum Master: el número de comprobaciones estaba mal en
cuatro archivos, la guía de arranque daba nombres de usuario anteriores al acuerdo
con César, y el manual pedía completar una variable que tiene valor por defecto.

### Acuerdos

**A11.1 · H10.4 no se cierra.** Su título exige verificación por alguien ajeno al
desarrollo y esa verificación no ha ocurrido. Queda en progreso en la matriz de
trazabilidad y sin marcar en el archivo de tareas.

---

## ACTA 12 · Retrospectiva

| | |
|---|---|
| **Tipo de ceremonia** | Retrospectiva |
| **Sprint** | 0, con revisión del avance del 1 |
| **Fecha** | 16 de agosto de 2026 |
| **Modalidad** | Asincrónica. Consolidación de la bitácora de incidencias |
| **Participantes** | Alejandro, sobre incidencias reportadas por todo el equipo |
| **Evidencia** | `docs/04-bitacora-incidencias.md`, incidencias I-01 a I-05 |

### Método

La retrospectiva de este equipo se construye sobre la bitácora de incidencias. Cada
registro lleva qué pasó, causa raíz, acción tomada, aprendizaje e impacto, y el
aprendizaje **cambia una regla del proyecto**, no queda como intención.

### Qué salió bien y se conserva

**Comprobar la fuente de datos antes de implementar.** Produjo los dos defectos más
graves detectados hasta hoy —I-04 con los códigos de distrito, I-05 con la
resolución climática— y en ambos casos el costo fue **cero horas**, porque no había
código escrito. Es el hábito más valioso del equipo y no se toca.

**Reportar en lugar de corregir por cuenta propia** cuando el archivo es compartido.
Los tres integrantes lo hicieron.

**La revisión devuelve trabajo.** Tres Pull Requests volvieron con cambios
solicitados. Una revisión que aprueba todo no es una revisión.

### Qué salió mal y qué cambió a raíz de eso

| Incidencia | Regla que cambió |
|---|---|
| I-01 · Docker no instalado | Los prerrequisitos de la Definition of Done se verifican en las cuatro máquinas antes de comprometerla. Se escribió la guía de arranque |
| I-02 · PostgreSQL en bucle de reinicio | Un contenedor que reinicia falla en su arranque: se miran los registros antes de suponer |
| I-03 · kubectl no conectaba | Un error de red no significa clúster mal creado. Se documentó fijar la dirección al crearlo |
| I-04 · Códigos de distrito falsos | El verificador comprueba **contenido** y no solo estructura. Se registró la fuente única del vocabulario territorial |
| I-05 · La fuente no distingue distritos | Una fuente se evalúa contra el área de estudio. La pregunta "cuántas celdas caben en el área" es una división y se hace al elegir la fuente |

### Hallazgo abierto

**La documentación propia se desfasa y ningún verificador lo detecta.** El 16 de
agosto aparecieron cinco casos: el conteo de verificaciones equivocado en tres
archivos, los nombres de usuario desactualizados en la guía de arranque, y el
registro D-13 afirmando 492 entidades cuando el servicio devuelve 494.

Los cinco se corrigieron, pero el patrón es el mismo que produjo I-04: un número
escrito una vez y nunca vuelto a comprobar.

### Acciones

| # | Acción | Responsable | Estado |
|---|---|---|---|
| 12.1 | Corregir los cinco documentos desfasados | Alejandro | Cumplida el 16 ago |
| 12.2 | Agregar un verificador de documentación desfasada al CI | Alejandro | Cumplida el 16 ago |
| 12.3 | Calcular la velocidad real del Sprint 0 | Alejandro | Cumplida el 16 ago |
| 12.4 | Registrar horas reales en el cuerpo del PR, para poder recalibrar el modelo de esfuerzo | Todo el equipo | **Abierta** |

### Resultado de las acciones 12.2 y 12.3

**12.2.** `docs/herramientas/verificar_documentacion.py` corre en el trabajo de
gestión del CI. Calcula desde el repositorio cada cifra que la documentación
afirma —comprobaciones de contratos, versión, historias del backlog, trabajos del
pipeline— y falla si alguna no coincide. Se probó inyectando un número falso: lo
detecta y sale con código 1.

Trae además una función de conteo de historias cerradas que excluye el ejemplo del
bloque de instrucciones, que fue el origen de dos de los cinco errores.

**12.3.** El Sprint 0 entregó **43 de 54 puntos comprometidos, un 80 %**: 21,5
puntos por semana. El detalle está en `docs/12-velocidad.md`.

Ese documento declara también lo que **no** se pudo calcular: el modelo de horas
por punto del roadmap no se puede recalibrar porque nadie registró horas reales, y
comparar estimación contra estimación daría 1,0 por construcción. De ahí sale la
acción 12.4, que cuesta una línea por Pull Request.

---

# Anexo · Cobertura de la rúbrica de Scrum

| Elemento evaluado | Dónde se demuestra |
|---|---|
| Sprints de duración fija | Cinco sprints de dos semanas alineados a las entregas institucionales, `docs/06-roadmap.md` |
| Backlog priorizado y estimado | 83 historias con puntos, horas, dependencias y responsable, verificado en cada cambio por el CI |
| Capacidad medida, no supuesta | Modelo de horas por punto según acelerabilidad, con impuesto de revisión del 20 %. Acta 01 |
| Sprint Planning | Actas 01 y 02 |
| Replanificación justificada | Actas 02 y 07 |
| Daily Scrum | Actas 03, 05, 08 y 10. Cuatro impedimentos, los cuatro con respuesta el mismo día |
| Sprint Review | Actas 04, 06, 09 y 11. Doce Pull Requests revisados, tres devueltos |
| Retrospectiva | Acta 12, sobre cinco incidencias con aprendizaje aplicado |
| Refinamiento | Acta 02 y los criterios de aceptación previos a implementar de H1.3, H1.8 y H1.1 |
| Definition of Ready y of Done | `CONTRIBUTING.md`, aplicadas en cada revisión |
| Roles Scrum asignados | Tabla de integrantes, con Product Owner y Scrum Master identificados |

## Lo que este registro no puede demostrar

**Actas de reuniones sincrónicas**, porque el equipo no las celebra: la modalidad
asincrónica está declarada en cada acta y se decidió al arrancar, no después.

**El modelo de horas por punto recalibrado**, porque nadie registró horas reales y
comparar estimación contra estimación daría 1,0 por construcción. La velocidad en
puntos sí está medida —43 de 54 comprometidos en el Sprint 0— y vive en
`docs/12-velocidad.md`.

Ambas ausencias se declaran en lugar de rellenarse. Es la misma regla que el
proyecto aplica a sus datos: lo que no existe se reporta vacío, no se inventa.
