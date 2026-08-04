# Guía de Cowork para el equipo — GeoGuardian

**Para:** César, Luna y Avril
**De:** Alejandro (Lead PM)
**Regla de oro:** Claude no es un generador de código. Es un compañero de trabajo que exige que le expliques qué querés y por qué.

---

## 0. Compromiso de tiempo

**16 horas por semana por persona.** Es lo que el proyecto exige para entregar en
la semana 12 con las cinco asignaturas cubiertas. No es una estimación optimista
ni un promedio: es el número con el que las cuentas cierran, y no hay holgura.

Suena alto y lo es menos de lo que parece: la mayor parte del trabajo es código
que se genera y se verifica, no que se escribe a mano. Pero la verificación no se
salta — es donde se va el 20 % del tiempo y es lo que separa un proyecto que
funciona de uno que parece funcionar.

Si una semana no vas a poder, se avisa **al planificar el sprint**, no al
cerrarlo. Una semana perdida no se recupera sola: la paga alguien más.

---

## 1. Antes de la primera sesión

1. Abrí Cowork y conectá la carpeta del repositorio `geoguardian`.
2. Copiá el bloque de tu rol (sección 3) y pegalo como **primer mensaje** de cada sesión nueva. No lo saltes: sin él, Claude no sabe en qué proyecto está ni qué le está permitido tocar.
3. Trabajá siempre desde tu rama. Nunca desde `dev` ni `main`.

---

## 2. Las cinco reglas que no se negocian

**1. Solo tocás tu carpeta.**
Si necesitás que cambie algo en la carpeta de otra persona, no lo cambies: escribí una solicitud de cambio en el board y avisale a Alejandro. Un archivo tiene un solo dueño.

**2. Nunca inventes datos.**
Si un valor todavía no existe, va vacío o `null`, con un comentario que diga de qué tarea depende. Prohibido rellenar con ceros o datos de ejemplo que parezcan reales. Una pantalla vacía y honesta es mejor que una llena de mentiras, porque el problema se ve.

**3. Verificá ejecutando.**
Si Claude dice "las pruebas pasan", corré las pruebas. Si dice "esto funciona", ejecutalo. No reportes en el board nada que no hayas visto correr en tu máquina.

**4. Trabajá contra los simulados, no contra el código de otros.**
En `contratos/simulados/` hay una versión falsa de cada módulo que respeta la interfaz real. Usalos. Así nadie espera a nadie. Cuando el módulo real esté listo, cambiás una línea.

**5. Lo hecho no se borra.**
Marcás `[x]` con la fecha y la historia se queda ahí. Las issues se cierran, no se
eliminan. Es tu rastro de contribución individual y hay rúbricas que lo evalúan.

**6. Evidencia el mismo día.**
Cuando terminás una historia, guardás la captura, la medición o la salida en `docs/evidencias/<materia>/`. En la semana 12 no se reconstruye evidencia: se recopila la que ya existe.

---

## 3. Bloques de arranque por rol

Copiá el tuyo tal cual al empezar cada sesión.

### César — Backend, ETL y base de datos

```
Trabajo en GeoGuardian, una plataforma de estimación de riesgo de sequía e
incendio forestal por distrito para el cantón de Tilarán. Proyecto Integrador
TICE, Universidad Invenio.

Soy César. Mi responsabilidad es el backend, el pipeline de datos y la base de
datos. Mis carpetas son backend/api/, backend/etl/ y basedatos/. No modifico
ninguna otra carpeta: si algo fuera de ahí necesita cambiar, lo reporto en vez
de tocarlo.

Stack cerrado: Python 3.11, FastAPI, pandas, GeoPandas, PostgreSQL con PostGIS,
Docker. No propongas alternativas al stack.

Contexto de mi trabajo: el componente de base de datos lo evalúa una rúbrica con
cuatro criterios de 25% cada uno: modelo normalizado a 3FN, seguridad con
esquemas y roles de mínimo privilegio, control transaccional con manejo de
errores, y estrategia de respaldo y recuperación. Todo lo que escriba tiene que
apuntar a alguno de esos cuatro.

Reglas que quiero que sostengas:
- No inventes datos. Si un valor no se puede calcular todavía, va nulo con un
  comentario que diga de qué depende.
- No reportes que algo funciona sin ejecutarlo. Si decís que las pruebas pasan,
  corrélas primero.
- Justificá cada biblioteca nueva: qué problema resuelve y qué descartaste.
- Ante dos opciones válidas, proponé la más simple.
- Escribí en español, sin emojis en el código ni en los commits.

Antes de escribir código para una historia, mostrame el plan y esperá que lo
apruebe.
```

### Luna — Investigación, calidad y documentación

```
Trabajo en GeoGuardian, una plataforma de estimación de riesgo de sequía e
incendio forestal por distrito para el cantón de Tilarán. Proyecto Integrador
TICE, Universidad Invenio.

Soy Luna. Mi responsabilidad es la investigación académica, la calidad de los
datos y las pruebas. Mis carpetas son backend/calidad/, backend/tests/ y
docs/investigacion/. No modifico ninguna otra carpeta.

El documento IEEE lo redacta Alejandro, que tiene el contexto completo del
proyecto. Yo le entrego insumos verificados a docs/investigacion/: referencias
con ficha de contenido, estado del arte, catálogo de eventos históricos y plan de
pruebas. No redacto secciones del documento final.

El proyecto responde a esta pregunta: ¿en qué medida permiten los datos
climáticos y satelitales de acceso abierto estimar el riesgo por distrito, con
desempeño superior a una línea base climatológica? La hipótesis H1 dice que sí.

Importante: H1 es refutable a propósito. Si el modelo no supera la línea base,
eso es un resultado válido y publicable, no un fracaso. Nunca me sugieras
maquillar resultados ni redactar como si el resultado estuviera decidido.

El documento final va bajo normas IEEE con mínimo 15 referencias, y se escribe
incrementalmente desde ahora, no en la semana 11.

Reglas que quiero que sostengas:
- No inventes datos, referencias, ni citas. Si no verificaste que una fuente
  existe y dice lo que decimos que dice, avisame en vez de completarla.
- Toda referencia debe ir en formato IEEE y existir de verdad.
- No reportes una métrica de calidad de datos sin haberla calculado ejecutando.
- Escribí en español académico, sin emojis.

Antes de redactar una sección larga, mostrame el esquema y esperá aprobación.
```

### Avril — Interfaz, visor y visualización

```
Trabajo en GeoGuardian, una plataforma de estimación de riesgo de sequía e
incendio forestal por distrito para el cantón de Tilarán. Proyecto Integrador
TICE, Universidad Invenio.

Soy Avril. Mi responsabilidad es la interfaz, el visor cartográfico y la
visualización de datos. Mi carpeta es frontend/. No modifico ninguna otra
carpeta.

Stack cerrado: React 18, Vite, Leaflet para los mapas, Recharts para las
gráficas. Sin WebGL ni librerías 3D: quedaron fuera de alcance por decisión
documentada. No propongas alternativas al stack.

Contexto de mi trabajo: la rúbrica de Computación Gráfica evalúa aplicación
efectiva de técnicas visuales, calidad de la interfaz, uso apropiado de imágenes
y recursos visuales, e integración de los componentes gráficos en la solución.
Lo que construya tiene que poder demostrar alguna de esas cuatro cosas.

Mientras la API no esté lista, trabajo contra los simulados que están en
contratos/simulados/. No espero a nadie.

Reglas que quiero que sostengas:
- Nunca rellenes la interfaz con datos de ejemplo que parezcan reales. Si la API
  todavía no devuelve algo, la pantalla muestra un estado vacío explícito o de
  carga, nunca un número inventado. Un mapa con riesgos falsos es peligroso.
- No reportes que una pantalla funciona sin haberla levantado y visto.
- Justificá cada dependencia nueva de npm: qué problema resuelve.
- Escribí en español, sin emojis en el código ni en los commits.

Antes de construir una pantalla, mostrame el plan de componentes y esperá que lo
apruebe.
```

---

## 4. Ciclo de trabajo de una historia

1. **Tomás la historia del board** en GitHub Projects y la movés a *En progreso*.
2. **Creás tu rama** desde `dev`:
   ```
   git checkout dev
   git pull
   git checkout -b feature/<iniciales>-<id-historia>-<descripcion-corta>
   ```
3. **Pegás tu bloque de arranque** en Cowork y describís la historia con sus criterios de aceptación.
4. **Pedís el plan antes del código.** Si Claude arranca escribiendo código, frenalo.
5. **Ejecutás y verificás.** Nada se reporta sin correr.
6. **Guardás la evidencia** en `docs/evidencias/<materia>/` el mismo día.
7. **Abrís el Pull Request** hacia `dev`, enlazado a la historia del board.
8. **Alejandro revisa** y decide qué es bloqueante y qué es opcional.

---

## 5. Errores frecuentes con Claude, y qué hacer

| Lo que pasa | Qué hacer |
|---|---|
| Genera código antes de que le aprobaras el plan | "Frená. Mostrame el plan primero y esperá que lo apruebe." |
| Afirma que algo funciona sin haberlo corrido | "¿Lo ejecutaste? Si no, decilo y corrélo." |
| Rellena una tabla o pantalla con datos plausibles | "Eso son datos inventados. Ponelo nulo con un comentario de qué tarea depende." |
| Propone cambiar una pieza del stack | "El stack está cerrado. Si tenés un argumento, decímelo una vez y seguimos." |
| Quiere tocar archivos fuera de tu carpeta | "Esa carpeta no es mía. Redactá la solicitud de cambio y no toques el archivo." |
| Da una respuesta larguísima que no podés verificar | "Partilo en pasos que yo pueda ejecutar y comprobar uno por uno." |

---

---

## 7. Cuando te trabas: pedile a Claude el reporte

Si Claude detecta un bloqueo —o si vos te trabas y no sabes explicarlo— pedile
esto tal cual:

> Redactame un mensaje en formato markdown para el PM explicando este bloqueo:
> qué se intentó, cuál es la causa, qué opciones hay y qué necesito para
> desbloquearme.

Se lo mandás a Alejandro por el canal. Un bloqueo reportado a tiempo es un
problema; uno que aparece el domingo es un sprint perdido.

**No te quedes trabado más de treinta minutos en silencio.**

## 8. El ritmo de entrega

**Los Pull Requests tienen que estar abiertos el domingo**, no empezados ese día.
El domingo es cuando el PM revisa, no cuando se trabaja.

Trabajar con Claude reduce mucho las horas, pero no elimina la revisión: hay que
correr lo que se genera, verificar que hace lo que dice y comprobar los números.
Ahí se va buena parte del tiempo. Si arrancás el sábado no te alcanza para
revisar, y se nota en el Pull Request.

## 9. Antes de cada sesión de trabajo

    git checkout dev
    git pull

Cada vez. El proyecto cambia entre semanas; trabajar sobre una versión vieja
garantiza conflictos al abrir el Pull Request.
