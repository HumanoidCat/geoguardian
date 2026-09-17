# Tareas de Luis

**Luis Alejandro Luna Garcia**  
**Carpetas propias:** `backend/calidad, backend/tests, docs/investigacion`

> Solo modificas tus carpetas. Si necesitas un cambio fuera de ellas, se pide, no se hace.

> Marca `[x]` cuando la historia cumpla la Definition of Done, no cuando el codigo funcione.
>
> **Los seis pasos para cerrar una historia estan en `docs/15-cerrar-una-historia.md`.**
> El quinto es el que mas se olvida: el Pull Request lleva `Closes #N` con el
> numero real de la issue. "Cierra H10.1" no cierra nada.

> **Compromiso de tiempo: 18 horas por semana.**

> **Al cerrar una historia, anota sus horas.** Debajo de la linea de la historia:
>
>     - horas: estimada 4.0 . real 2.0
>
> `estimada` es lo que dijiste **antes de arrancar**, sin mirar el backlog.
> `real` es lo que tardo. Las horas del backlog ya estan en la linea de arriba y
> no se repiten aqui.
>
> Si no hubo estimacion previa, se escribe `n/d` **con el motivo entre
> parentesis**: `estimada n/d (no se pidio al arrancar) . real 2.5`. Un hueco sin
> explicacion no se distingue de un olvido.
>
> Se exige desde el **2026-08-20**, no hacia atras. Lo comprueba
> `docs/herramientas/verificar_horas.py`. El porque esta en **D-24**.

**Total asignado:** 96 puntos · 163.7 horas · 16.4 h por semana en promedio

## Carga por sprint

| Sprint | Semanas | Horas | Capacidad | Estado |
|---|---|---|---|---|
| S0 | semanas 2-3 | 25.9 | 36 | holgado |
| S1 | semanas 4-5 | 34.3 | 36 | ajustado |
| S2 | semanas 6-7 | 31.0 | 36 | ajustado |
| S3 | semanas 8-9 | 40.5 | 36 | SOBRECARGA +5 h |
| S4 | semanas 10-11 | 32.0 | 36 | ajustado |

## Sprint 0 (semanas 2-3) — 25.9 h

- [x] **H10.1** · Plan de pruebas con casos por modulo (2026-08-06)
  - `E10` · 5 pts · 4.8 h · rubrica: QA · depende de: contratos

- [x] **H10.5a** · Recopilar 15 referencias IEEE con ficha de contenido (2026-08-06)
  - `E10` · 8 pts · 21.1 h · rubrica: IEEE · **bloquea a: H10.5b**


## Sprint 1 (semanas 4-5) — 34.3 h

- [x] **H10.5b** · Estado del arte de Costa Rica (2026-08-18)
  - `E10` · 5 pts · 13.2 h · rubrica: IEEE · depende de: H10.5a · **bloquea a: H10.5c**

- [x] **H4.3** · Catalogo de 12 o mas eventos historicos del canton con fuente (2026-08-18)
  - `E4` · 8 pts · 21.1 h · rubrica: OE3 · **bloquea a: H4.4, H7.3**


## Sprint 2 (semanas 6-7) — 31.0 h

- [x] **H1.5** · Reporte formal de calidad de datos: faltantes, atipicos, sesgos (2026-08-30)
  - `E1` · 8 pts · 12.5 h · rubrica: OE1 · depende de: H1.1
  - horas: estimada n/d (trabajo repartido entre el 20 y el 30 de agosto, no se declaro al arrancar) . real 3.0
  - El volcado se genero reejecutando la ETL de H1.1 en esta maquina, no se
    espero el de Cesar. 102272 filas, el mismo conteo que documento H1.1.
  - Hallazgo: seis de siete variables tienen 0.00 % de variacion espacial.

- [x] **H2.1** · Filtrar ruido de las series con justificacion del filtro (2026-08-18)
  - `E2` · 3 pts · 2.9 h · rubrica: Senales · depende de: H1.4 · **bloquea a: H2.2, H2.3, H2.4, H2.7**

- [x] **H2.3** · SPI de 1 y 3 meses por convolucion de ventana movil (2026-08-18)
  - `E2` · 5 pts · 7.8 h · rubrica: Senales · depende de: H2.1 · **bloquea a: H2.5, H3.0**

- [x] **H2.7** · Calcular percentiles R95p y R99p de precipitacion acumulada por distrito (2026-08-18)
  - `E2` · 5 pts · 7.8 h · rubrica: Senales · depende de: H2.1 · **bloquea a: H3.0**


## Sprint 3 (semanas 8-9) — 40.5 h

- [x] **H12.1** · Centralizar los logs de pipeline y aplicacion en control.bitacora_etl (2026-09-04)
  - `E12` · 5 pts · 4.8 h · rubrica: Troubleshoot · depende de: H1.9 · **bloquea a: H12.2, H12.4**
  - horas: estimada n/d (llego por traspaso el 2026-09-03 y nadie pidio una
    estimacion antes de arrancar) . real 2.0
  - **Traspasada desde Cesar el 2026-09-03** por **D-37**. No es un cambio de
    alcance ni una correccion del trabajo previo: la historia se movio para
    poder cerrar el Sprint 3, y su contenido queda tal como estaba escrito.
  - **El alcance paso de crear la tabla a extenderla.** H1.14 la creo primero,
    en la migracion 013, el mismo dia. Los criterios se reescribieron por eso;
    la version anterior queda en el commit `fbdf21e` para poder contrastarlas.
  - Migracion `014` mas `basedatos/verificar_h12_1.py`: 22 comprobaciones sobre
    once de los doce criterios. El criterio 10 es la corrida real del ETL de
    H1.14 despues de la extension: 8 distritos, 1968 filas, 0 fallidos.
  - Hallazgo: **la migracion no era idempotente y el aplicador lo tapaba.**
    Guarda la suma SHA-256 y nunca reaplica, asi que correrlo dos veces prueba
    que el aplicador es idempotente, no que el archivo lo sea. Al ejecutar el
    contenido dos veces de verdad aparecio un `ADD CONSTRAINT` sin su
    `DROP ... IF EXISTS`. Una herramienta que protege contra un error tambien
    puede esconderlo.
  - Hallazgo: **las tres restricciones NOT VALID no se ejercieron.** La base
    estaba vacia, asi que no encontraron violaciones porque no habia filas que
    las violaran. No es lo mismo que «los datos estan limpios».
  - Hallazgo: **el plan del criterio 8 se midio sobre 2 filas** y no es
    evidencia de rendimiento en ninguna de las dos direcciones. El verificador
    avisaba solo en el caso desfavorable; se corrigio para que avise en ambos.
  - Queda dicho para H12.4: `filas_leidas`, `sqlstate`, `version_codigo` y
    `reportado_por` existen pero **nadie las llena todavia**. Las llenaria
    `ingestar.py`, que es de H1.14 y esta historia no toca.

- [x] **H4.1** · Importancia de variables global del mejor modelo (2026-09-05)
  - `E4` · 3 pts · 2.9 h · rubrica: OE3 · depende de: H3.6 · **bloquea a: H4.2**
  - horas: estimada n/d (llego por traspaso el 2026-09-03 y nadie pidio una
    estimacion antes de arrancar) . real 2.5
  - **Traspasada desde Alejandro el 2026-09-03** por **D-37**. No es un cambio de
    alcance: se movio para repartir la carga del Sprint 3, y su contenido
    queda tal como estaba escrito.
  - **RESULTADO NEGATIVO, y es el resultado.** De seis combinaciones de estimador
    y evento, cinco no tienen **ninguna** columna cuya caida supere su propio
    rango entre pliegues. Los tres modelos ordenan las 27 columnas distinto entre
    si y ningun primer puesto es distinguible: **no hay una explicacion estable
    que dar**. Coherente con H3.6 y H3.8 desde un lado independiente: ninguno le
    gana a la climatologica, y ninguno se apoya en ninguna variable.
  - El titulo dice «del mejor modelo» y **no hay un mejor modelo**: en lluvia el
    primero es la climatologica, que no pondera columnas; en incendio el que mas
    puntua no es el que escribe. Se calculan los tres y se declara que ninguno
    gano el titulo, en vez de repartirlo.
  - Hallazgo: la unica columna distinguible de las 162 evaluadas es **negativa**.
    `tmax_media3` mejora el F1 de la regresion logistica al permutarla, en los
    cinco pliegues, y esa es la que **escribe** `analitico.riesgo` en incendio por
    D-42. Con 162 columnas, una cruzando su banda es lo esperable por azar: se
    reporta como pista, no como conclusion.
  - Hallazgo: **xgboost en incendio no usa ninguna columna de precipitacion.**
    Cero exacto en media y en rango, o sea que no corta por ellas en ningun
    arbol. Queda anotado para H4.2.
  - Defecto propio, encontrado en la primera corrida real y corregido el mismo
    dia: la tabla ordenaba por media descendente e imprimia diez, asi que la
    unica distinguible -por negativa- caia al fondo y **no se veia**. Lo delato
    una contradiccion en la salida. Comprobacion 12b agregada al verificador.
  - Error propio, corregido sin borrarlo: los criterios afirmaban que
    `crudo.medicion_diaria` tenia 1968 filas. **Nunca se consulto**; tenia
    104 240. Era una inferencia presentada como una medicion.
  - Hallazgo que no es de esta historia: `crudo.foco_calor` estaba en 0 filas, asi
    que incendio salia NO MODELABLE con cero episodios. El respaldo que circula
    trae mediciones y no focos, y por eso **los resultados de incendio de H3.6 y
    H3.8 no se reproducen siguiendo el README**. Se recupero con
    `cargar_focos` (494 filas, `verificar_h12` en verde).

- [x] **H4.2** · Aplicar SHAP para explicar predicciones individuales (2026-09-07)
  - `E4` · 8 pts · 12.5 h · rubrica: OE3 · depende de: H4.1
  - horas: estimada n/d (llego por traspaso el 2026-09-03 y nadie pidio una
    estimacion antes de arrancar) . real 7.0
  - **Traspasada desde Alejandro el 2026-09-03** por **D-37**. No es un cambio de
    alcance: se movio para repartir la carga del Sprint 3, y su contenido
    queda tal como estaba escrito.
  - **RESULTADO: la explicacion de un acierto y la de un error son
    indistinguibles.** Bosque aleatorio sobre lluvia intensa, distrito 50808,
    cuatro dias de diferencia: las mismas ocho columnas, en el mismo orden, con
    los mismos valores hasta el tercer decimal (`hr_media7` +0.0575 contra
    +0.0571). Se repite en los tres estimadores y en los dos eventos. Es la
    confirmacion local de lo que H4.1 midio globalmente.
  - **Solo se ve porque la regla de seleccion obligaba a incluir el error.** Las
    figuras de los aciertos, solas, se ven convincentes. La regla se fijo en los
    criterios **antes de mirar ninguna prediccion** y las dos celdas de error
    eran obligatorias; eligiendo despues de ver, esto no estaria escrito.
  - Responde CA-12, la pregunta que H4.1 dejo abierta: xgboost **si** usa la
    precipitacion en incendio (SHAP da +0.0888 a `pp_acum30`), pero no lo
    suficiente para cambiar ninguna clase, y por eso su importancia por
    permutacion era cero exacto. Se escribe como **hipotesis** consistente con
    las dos mediciones, no como hecho: comprobarla exige medir cuantas clases
    cambian al permutar, y eso no es de esta historia.
  - Los tres estimadores coinciden localmente (humedad a corto plazo en lluvia,
    30 dias en incendio) mientras H4.1 midio que ordenaban las columnas distinto.
    **No es contradiccion**: permutacion mide efecto sobre el F1, SHAP mide
    desplazamiento de la probabilidad de una fila. Se registra porque tener dos
    medidas que no coinciden es informacion sobre las dos.
  - **Cuatro defectos propios, ninguno encontrado leyendo el codigo.** El tercero
    es el que deja leccion: `modelo_interno` entregaba `_modelo` desnudo y
    `RegresionLogistica` guarda su escalador afuera, asi que se descomponia
    perfectamente un numero que no era la prediccion (`salida +0.0000` con
    `P(alto) 0.922`). **CA-4 no lo detecto y no podia**: los dos lados de la
    identidad salian del mismo camino equivocado. Lo delato poner `salida` al
    lado de `P(alto)`, un tercer numero de otra procedencia. Los otros tres:
    SHAP sin conjunto de fondo (paso a ser **CA-13**), el residuo que daba cero
    por construccion, y el orden de columnas decidido por quien llama.
  - CA-11: esta historia toco `regresion_logistica`, `random_forest` y
    `xgboost_`, que son de H3.3, H3.4 y H3.5. Sus tres verificadores siguen en
    verde (17, 20 y 21 criterios).

- [x] **H10.2** · Pruebas automatizadas del backend, cobertura de dominio (2026-08-30)
  - `E10` · 5 pts · 4.8 h · rubrica: QA · depende de: H6.2
  - horas: estimada 2.0 . real 1.5
  - 57 casos nuevos, 209 en la suite. Cubre 35 de los 40 del plan H10.1.
  - Hallazgo: cuatro invariantes del contrato Repositorio, tres de prioridad 1,
    que no cubre ni el simulado ni la implementacion de Postgres.

- [x] **H2.2** · Analisis espectral de la lluvia e interpretacion fisica (2026-08-30)
  - `E2` · 5 pts · 7.8 h · rubrica: Senales · depende de: H2.1
  - horas: estimada n/d (trabajo repartido entre el 20 y el 30 de agosto, no se declaro al arrancar) . real 3.5
  - Veranillo detectado en los ocho distritos, de 23 a 47 veces el modelo nulo.
    La razon varia por factor 2.10 entre distritos: la unica variable que
    discrimina espacialmente tambien cambia de estructura.

- [x] **H2.4** · Anomalias respecto a la normal climatologica 1991-2020 (2026-08-20)
  - `E2` · 3 pts · 2.9 h · rubrica: Senales · depende de: H2.1 · **bloquea a: H7.4**
  - horas: estimada n/d (la regla se creo el mismo dia del cierre) . real 2.0

- [x] **H9.1** · Preparar SUS, guion de entrevista y dosier de 3 casos (2026-08-22)
  - `E9` · 5 pts · 4.8 h · rubrica: OE4 · **bloquea a: H9.2a**
  - horas: estimada 2.5 . real 2.5
  - El guion indica que bloques van a H9.2a y cuales a H9.2b, segun la particion
    del 2026-08-23. Se entregan cuatro casos y no tres: el cuarto es el unico
    evento de incendio del catalogo.


## Sprint 4 (semanas 10-11) — 32.0 h

- [x] **H12.4** · Diagnostico guiado a partir de la bitacora de incidencias (2026-09-13)
  - `E12` · 5 pts · 7.8 h · rubrica: Troubleshoot · depende de: H12.1 · **bloquea a: H12.5**
  - horas: estimada n/d (no se registro una estimacion propia antes de
    arrancar; las 7.8 h de arriba las deriva el backlog de los puntos) . real 8.3
  - **Que bitacora**: el titulo del backlog dice «de incidencias», que es el
    nombre de `04-bitacora-incidencias.md`, escrito a mano. **No es esa.** Es
    `control.bitacora_etl`, la de H12.1, confirmado por el PM el 2026-09-13.
  - **RESULTADO: en su primera corrida diagnostico hacia atras la causa de
    I-52.** La senal `[ausente] estimacion.riesgo · sin corrida` dice por que
    `analitico.riesgo` estaba vacia en la base local el 08: la cadena de
    estimacion nunca habia corrido ahi. Averiguarlo a mano costo cinco dias.
  - **SEGUNDO RESULTADO, y es el util: la tabla real desmintio el modelo con el
    que se escribio la herramienta.** Comparaba `filas_leidas` contra `filas`
    como si una contuviera a la otra, y son etapas distintas —lo que trajo la
    fuente contra lo que se escribio—. La corrida 63 da 1944 y 1712: una razon
    de **1,135**, que bajo esa suposicion era imposible. Lo pedido esta en
    `ventana_desde` y `ventana_hasta`, dos columnas que la primera version ni
    consultaba.
  - **El verificador no podia detectarlo**, porque el sabotaje se construyo con
    la misma suposicion que el detector: 17 comprobaciones en verde sobre una
    premisa falsa. Es la leccion de H4.2 aparecida en otro sitio. Lo delato
    consultar la tabla completa **por otro motivo**, no ninguna comprobacion.
  - Tercera: la corrida 39, la del propio I-43, tiene `filas_leidas` nulo y la
    primera version **la dejaba pasar en silencio**. De ahi salen CA-14 y la
    senal `cobertura no declarada`: una corrida que no se puede juzgar no es una
    corrida sana, es una corrida sin medir.
  - Cuarta, en pequeno: se etiqueto como «corrida 63 real» una ventana
    reconstruida que daba 1944 de 1944, un 100 % demasiado limpio. La medida
    llega al 2026-09-05 y da **87,1 %**. Corregida y anotada, no borrada.
  - El umbral de 0,5 **tiene argumento medido y no hipotetico**: a la corrida 63,
    que esta sana, le faltan 288 series que son 36 dias por 8 distritos, la
    latencia de D-40. Con 0,9 una corrida buena real se marcaria.
  - Por decision del PM del 2026-09-13, **opcion (b)**: diagnostica con lo que
    hay y declara donde esta ciega. `sqlstate`, `version_codigo` y
    `reportado_por` siguen en 0 de 3; las llena `ingestar.py` (H1.14) y entra
    despues del 24 por solicitud de cambio.
  - **No necesito excepcion de propiedad**: todo vive en `backend/calidad/` y
    `backend/tests/`, las dos mias.
  - Hallazgo para el CI, que no es de esta historia: **`ci.yml` no invoca
    `verificar_h41`, `h42`, `h12_1`, `h3_7`, `h12_3` ni `h12_4`.** Esos
    verificadores solo corren cuando alguien se acuerda, que es la misma forma
    de I-52. Por eso H12.4 deja ademas **16 pruebas en `backend/tests/`**, que el
    CI si ejecuta. Reportado al PM: `ci.yml` es suyo.
  - Hallazgo abierto: la corrida **62** lleva 168 h `en_curso` sin `filas`, sin
    `mensaje` y sin fin, con la misma ventana que la 63, que arranco tres
    minutos despues y cerro bien. Apunta a **interrupcion** y no a cierre
    olvidado, y la causa queda por confirmar en vez de cerrarse con la
    explicacion que suena mejor.

- [x] **H9.2a** · Sesion de usabilidad con 3 a 5 participantes y calculo del puntaje SUS (2026-09-14)
  - `E9` · 3 pts · 7.9 h · rubrica: OE4 · depende de: H9.1 · **bloquea a: H9.2b**
  - horas: estimada n/d (no se registro una estimacion propia antes de arrancar;
    las 7.9 h de arriba las deriva el backlog de los puntos) . real 12.0
  - **Las 12 h no son de analisis: son de conseguir gente y de moverse.** Tres
    sesiones de 41 a 47 minutos suman poco mas de dos horas; el resto fue
    reclutamiento y desplazamiento. Es la primera historia del proyecto donde el
    costo dominante no es tecnico, y conviene que la estimacion de H9.2b y H9.3
    lo tenga en cuenta.
  - Partida de H9.2 el 2026-08-23. Mide **usabilidad, no exactitud**.
  - **El visor ya NO sirve datos simulados**, asi que las dos notas de abajo
    quedaron vencidas antes de correr la historia. Se dejan porque lo hecho no se
    borra, y el ajuste esta declarado con fecha en `hoja-de-sesion-h9.2a.md`.
  - La banda de "modo simulado" no se oculta: se **mide**. Preguntar si el
    participante entendio que los datos no son reales responde a "comunica su
    propia incertidumbre" y es un hallazgo sobre H6.6 y D-23.
  - **No preguntar por confianza en los numeros.** Con datos simulados esa
    respuesta no significa nada, y la banda la contamina.
  - **TRES COINCIDENCIAS entre tres perfiles que no se conocen entre si:**
  - **1. Ninguno encontro declaracion de incertidumbre.** Los tres la buscaron en
    la tarea 3 y no existe. «Si no tengo esas tres —de donde salio, a que hora se
    actualizo, quien firma— para mi es una opinion bonita» (gestion de riesgo).
  - **2. Ninguno encontro el sello de no-oficialidad, y la consecuencia es
    distinta en cada uno**: el de gestion de riesgo NO actua, el agricultor
    ACTUA de inmediato («yo bajo el ganado y ya»), y el del lodge PROPAGA a un
    grupo de unas 20 personas citando el visor. El que menos riesgo presenta es
    el que lo llamo **«grave»** y pidio un letrero, «porque lo otro es comodidad
    y esto es responsabilidad».
  - **3. Dos de tres leyeron bien la casilla rayada de sequia, pero NINGUNO
    gracias al visor**: uno por los boletines del IMN y otro por analogia con
    Windy. **La interfaz no enseño nada en ninguno de los tres casos**, y el que
    fallo es el que mas depende de la sequia para vivir.
  - La lectura peligrosa que D-34 anticipa **ocurrio**: «que no hay, que ahorita
    no hay sequia», sostenida 40 s. Y el arreglo lo propuso el mismo
    participante: «pongale "no medido" con letras».
  - SUS **60,0 · 42,5 · 72,5**. El promedio (58,3) es el numero menos informativo
    del estudio: 30 puntos de rango. **La herramienta funciona para quien maneja
    aplicaciones y falla para quien mas la necesita.** No se aplica banda de
    aceptabilidad mientras siga abierta la deuda de verificacion de `[13]`.
  - El 72,5 dijo en la pregunta 14 que **lo abandonaria en una semana**. Un
    puntaje alto leido solo habria dicho lo contrario.
  - Limitaciones declaradas: n=3; **el facilitador trabajo en el proyecto**, asi
    que las criticas son un piso y no un techo; **el instrumento vario entre
    sesiones** y la formulacion previa de las sesiones 01 y 02 no se conservo; el
    registro de reclutamiento se lleno despues y no permite saber cuanto costo
    conseguir a los tres; la traduccion del SUS mostro un piso de lectura en el
    perfil agropecuario; y ningun participante es de los tres distritos con señal
    de incendio (D-25).

- [x] **H9.2b** · Sesion de contraste: la estimacion frente a lo que la gente vivio (2026-09-14)
  - `E9` · 2 pts · 5.3 h · rubrica: OE4 · depende de: H9.2a, H3.0 · **bloquea a: H9.3, H9.4**
  - horas: estimada n/d (no se registro una estimacion propia antes de arrancar;
    las 5.3 h de arriba las deriva el backlog de los puntos) . real 9.0
  - Es el bloque 5 del guion de H9.1. Contra datos simulados no mide nada: sin
    modelo, "el mapa se equivoca en Quebrada Grande" no dice nada sobre el modelo.
  - **La dependencia de H3.0 no estaba declarada.** La encontro Luna el 2026-08-23
    despues de cerrar H9.1 y dar por desbloqueada H9.2. Por H3.0 depende de H1.2.
  - Reclutamiento **distinto** al de H9.2a: aqui hacen falta personas que vivieron
    esos eventos en ese distrito. No tiene que ser la misma gente.
  - **RESULTADO: el sistema da la MISMA estimacion, hasta el cuarto decimal, para
    dos temporales separados por seis anios.** Nate (2017-10-05) y las
    inundaciones de las rutas 925 y 927 (2011-10-19) son los dos de octubre, y
    quien estima es la linea base climatologica: el almanaque del distrito por
    mes. **Dos de los tres participantes lo descubrieron solos.**
  - El de mantenimiento vial verifico las ocho filas en menos de cinco segundos y
    lo desmonto con sus propios partes de trabajo: «en el 2011 cerramos nueve
    dias la 927; con Nate no cerramos ni dos. Y su sistema me esta dando el mismo
    numero para los dos. Entonces ese numero no esta hablando del evento.»
  - Es la version local de lo que **H4.4** midio globalmente (0,63x pareado por
    mes), con dos casos concretos y contra registros fechados.
  - **CONTRADICCION DOCUMENTADA CONTRA EL CATALOGO DE H4.3.** El ganadero de
    Cabeceras contradijo el vacio de dano de Nate con bitacora manuscrita y un
    recibo fechado el 2017-10-11. Su explicacion: «no hay registro no porque no
    pasara, sino porque no lo apunto nadie mas que yo». **Consecuencia: la
    ausencia de dano se debe leer como ausencia de REPORTE**, y cualquier analisis
    que use un distrito sin dano registrado como caso negativo esta contaminado
    por subregistro. **Eso incluye al contraste de H4.4.**
  - El subregistro lo formularon los tres, desde tres roles. El mas preciso es el
    sesgo por densidad: «en Tierras Morenas hay cuatro casas, pues hay cuatro
    reportes. Pero el camino se cae igual.»
  - **Los tres leyeron la casilla vacia de sequia como una posible averia** —«¿se
    cayo?»— y dos pidieron literalmente texto en vez del simbolo. Sumado a H9.2a,
    **seis participantes entre las dos historias y ninguno entendio el vacio
    gracias a la interfaz.**
  - **El evento que D-34 excluye es el de mayor impacto declarado** por dos de
    tres: «la lluvia le tumba a uno un alambre, la seca le quita a uno la finca».
    Se registra como brecha de cobertura, no como error.
  - La 13b responde la pregunta de la historia: **cuanto vale una climatologia
    depende del horizonte de decision.** Dos dijeron «me sirve menos» y uno «me
    sirve casi igual», y los tres separaron mes de dia. «No es el dato, es donde
    lo pusieron: un almanaque en una pantalla que parece de emergencia confunde.»
  - **EL CASO 4 SE DECLARA INVALIDO.** A los tres se les mostro una tabla de
    incendio marcada `[SIMULADO]` que nunca se sustituyo: no coincide **ningun**
    valor con lo que el sistema produce. Tres citas fuertes se descartan, no se
    matizan. Se conservan las respuestas a la pregunta 13, que no dependen de la
    tabla. Es falta del procedimiento y esta declarada.
  - Hallazgo que la tabla falsa tapaba, medido despues y **no atribuido a los
    participantes**: el sistema **no tiene ninguna estimacion de incendio para
    Tilaran**, que es donde ocurrio el fuego del catalogo, porque Tilaran no es
    uno de los tres distritos de D-25.
  - La pregunta 17 aporto en las tres. La mas util para el proyecto: **cambiar la
    variable medida**, de intensidad del fenomeno a dias de cierre y poblacion
    incomunicada. «Eso si distingue el 2011 del 2017, que es justo lo que su
    sistema no puede hacer», y ya existe fechado en los partes de trabajo.

- [ ] **H9.3** · Someter los umbrales de incendio a criterio de los participantes
  - `E9` · 3 pts · 7.9 h · rubrica: OE4 · depende de: H9.2b, H1.2

- [ ] **H9.4** · Incorporar un cambio derivado de la retroalimentacion
  - `E9` · 2 pts · 3.1 h · rubrica: OE4 · depende de: H9.2b

## Regla: lo hecho no se borra

Una historia terminada se marca `[x]` y **se queda donde esta**. Nunca se borra
ni se mueve a otro archivo.

Este archivo es el registro de lo que hiciste durante el trimestre. En la semana
12 hay que demostrar contribucion individual: la rubrica de Computacion Grafica
lo evalua explicitamente. Si vas borrando lo terminado para "ver mejor lo que
falta", en noviembre no vas a tener con que respaldar tu aporte.

Al marcar una historia, agregale la fecha entre parentesis:

    - [x] **H1.1** · Descargar 10 anios de series climaticas diarias (2026-08-14)

Lo mismo aplica a las issues de GitHub: se cierran, no se eliminan. Una issue
cerrada conserva la discusion, los commits enlazados y el Pull Request. Una issue
borrada no deja nada.

## Al terminar cada historia

1. Verificar ejecutando, no leyendo. Si dice que pasa, correlo.
2. Guardar la evidencia en `docs/evidencias/<materia>/` el mismo dia.
3. Abrir el Pull Request hacia `dev` enlazado a la issue.
4. Marcar `[x]` aqui con la fecha, y **cerrar** la issue en GitHub. No borrar ninguna de las dos.
