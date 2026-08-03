# Bitacora de decisiones

Toda decision tecnica se registra aqui, numerada. Sin registro, la decision no
existe y se vuelve a discutir en dos semanas.

Formato: contexto, decision, justificacion, alternativa descartada y, cuando
exista, la medicion que la respalda.

---

## D-01 · Fuentes globales abiertas como base primaria

**Contexto.** El IMN no ofrece API publica identificable y el acceso por convenio
puede tardar semanas, que no controlamos.

**Decision.** NASA POWER, NASA FIRMS y Copernicus son las fuentes primarias. Los
datos institucionales costarricenses pasan a enriquecimiento opcional.

**Justificacion.** Elimina la dependencia de un tramite administrativo que estaba
en la ruta critica. POWER ofrece series diarias desde 1981 sin registro.

**Alternativa descartada.** Esperar respuesta del IMN. Habria puesto en riesgo
todo el cronograma por una dependencia externa sin fecha.

**Medicion.** Pendiente: registrar tiempo de descarga y cobertura obtenida.

---

## D-02 · scikit-learn y XGBoost en lugar de aprendizaje profundo

**Contexto.** Los datos son tabulares: series climaticas diarias por distrito.

**Decision.** Regresion Logistica, Random Forest y XGBoost. Sin redes neuronales.

**Justificacion.** En datos tabulares el gradient boosting iguala o supera a las
redes profundas con una fraccion del costo de desarrollo y sin GPU.

**Alternativa descartada.** TensorFlow con LSTM. Mayor curva de aprendizaje y
tiempo de entrenamiento sin ganancia esperada para este volumen de datos.

---

## D-03 · PostgreSQL con PostGIS

**Contexto.** El proyecto es geoespacial: polígonos distritales, puntos de focos
de calor e imágenes satelitales. La eleccion de motor condiciona todo el modulo
de datos.

**Decision.** PostgreSQL con PostGIS, autorizado por el profesor del curso.

**Justificacion.** Integracion nativa con GeoPandas, GDAL y QGIS. Los cuatro
criterios de la rubrica se cumplen: esquemas y roles para seguridad, bloques
EXCEPTION en PL/pgSQL para manejo de errores, y pg_dump con archivado de WAL para
respaldo y recuperacion a un punto en el tiempo.

**Alternativa descartada.** Un motor relacional sin extension geoespacial nativa.
Habria obligado a convertir geometrias a mano desde Python, sin tipo raster y sin
compatibilidad directa con GeoPandas ni QGIS.

---

## D-04 · Validacion temporal por ventana expansiva

**Contexto.** Los datos son series temporales.

**Decision.** Validacion por ventana expansiva. Prohibido `train_test_split`
aleatorio.

**Justificacion.** Una particion aleatoria filtra informacion del futuro al
conjunto de entrenamiento y produce metricas infladas que no se sostienen en
operacion real.

---

## D-05 · Kubernetes con manifiestos y k3d local

**Contexto.** El curso de Arquitectura de Software exige orquestacion de
contenedores. Operar un cluster gestionado excede la capacidad del equipo.

**Decision.** Manifiestos reales ejecutados en k3d local. Aprobado por el
profesor.

**Justificacion.** Los manifiestos son identicos a los de un cluster gestionado.
Se demuestra el diseno sin asumir el costo de operar infraestructura.

**Alternativa descartada.** Cluster gestionado en la nube. Costo y tiempo de
operacion no justificados para un MVP de un trimestre.

---

## D-06 · [Siguiente decision]

**Contexto.**

**Decision.**

**Justificacion.**

**Alternativa descartada.**

**Medicion.**
