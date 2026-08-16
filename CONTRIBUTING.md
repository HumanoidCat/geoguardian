# Flujo de trabajo

## Ramas

    main    Siempre demostrable. Es lo que se enseña si un profesor pide ver el proyecto.
    dev     Rama de integracion. Todo el trabajo llega aqui primero.
    feature/<iniciales>-<id-historia>-<descripcion>

Ejemplo: `feature/cu-h1.1-descarga-series-power`

## Ciclo

1. Tomar la historia del board y moverla a En progreso.
2. Crear la rama desde `dev`:

       git checkout dev
       git pull
       git checkout -b feature/cu-h1.1-descarga-series-power

3. Trabajar solo dentro de la carpeta propia.
4. Ejecutar y verificar. Nada se reporta sin haberlo corrido.
5. Guardar la evidencia en docs/evidencias/<materia>/ el mismo dia.
6. Abrir Pull Request hacia `dev`, enlazado a la historia del board.
7. Alejandro revisa y separa lo bloqueante de lo opcional.

`dev` se integra a `main` los viernes, solo si la suite pasa y el sistema levanta
con `docker compose up` en una maquina limpia.

## Regla de main

No hay proteccion tecnica sobre `main`. Se sostiene por acuerdo del equipo:

- Nadie hace push directo a `main`. Nadie, incluido Alejandro.
- `main` solo recibe merges de Pull Request desde `dev`.
- Solo Alejandro aprueba y ejecuta el merge semanal.
- Romper esta regla se registra como incidencia en docs/04-bitacora-incidencias.md.

`main` es lo que se enseña si un profesor pide ver el proyecto en cualquier
momento. Por eso tiene que estar siempre demostrable.

Si alguien hace push a `main` por error:

    git checkout main
    git reset --hard origin/main~1   # solo si nadie mas tiro todavia
    git push --force-with-lease

Avisar en el canal del equipo antes de forzar nada.

## Propiedad de archivos

Un archivo, un dueno. Nadie modifica la carpeta de otra persona.

| Carpeta | Dueno |
|---|---|
| backend/api, backend/etl, basedatos | Cesar |
| backend/senales, backend/modelado, infra, docs, .github/workflows | Alejandro |
| backend/calidad, backend/tests, docs/investigacion | Luna |
| frontend | Avril |

Excepciones acordadas:

- Cesar trabaja en `backend/modelado` para las historias H2.5, H2.6 y H3.7,
  coordinando con Alejandro.
- **`docs/evidencias/` es de escritura libre para todo el equipo.** Cada quien
  sube la evidencia de sus propias historias a la carpeta que corresponda, sin
  solicitud previa. Ver `docs/evidencias/README.md`. Solo requiere solicitud
  crear una carpeta nueva de primer nivel o tocar evidencia ajena.

Archivos compartidos: `contratos/`, `docker-compose.yml`, `.env.example`,
`requirements.txt`, `package.json`, `.github/workflows/`. Se **modifican** solo
por solicitud de cambio aprobada por Alejandro y por el dueno del modulo
afectado.

**Crearlos por primera vez dentro de tu propia carpeta no requiere solicitud**:
lo declaras en el Pull Request. Leer un archivo compartido tampoco: leer
`contratos/` para generar algo tuyo es uso normal. Ver `docs/07-propiedad-archivos.md`.

## Commits

Conventional Commits, en espanol, explicando el porque y no solo el que.

    feat(etl): descargar series diarias de POWER con reintentos

    La API corta conexiones intermitentes en descargas largas. Se agrega
    reintento con espera exponencial para que el proceso sea reejecutable
    sin intervencion manual.

Tipos: feat, fix, docs, refactor, test, chore, perf.

Sin emojis en el codigo ni en los mensajes de commit.

## Definition of Ready

- [ ] Criterios de aceptacion escritos y verificables
- [ ] Estimada por el equipo
- [ ] Dependencias resueltas o planificadas antes
- [ ] Datos o insumos disponibles
- [ ] Identificado a que criterio de que rubrica contribuye
- [ ] Responsable asignado

## Registro de lo hecho

Las historias terminadas se marcan `[x]` con la fecha en `docs/tareas/<persona>.md`
y **no se borran nunca**. Las issues se cierran, no se eliminan.

Es el rastro de contribucion individual de cada quien, y hay rubricas que lo
evaluan de forma explicita en la semana 12. Ademas, una issue cerrada conserva la
discusion y los commits enlazados; una borrada no deja nada.

## Definition of Done

- [ ] En `dev`, con revision de al menos una persona
- [ ] Criterios de aceptacion verificados por alguien distinto al autor
- [ ] Pruebas donde aplica
- [ ] Documentada
- [ ] Evidencia archivada el mismo dia en docs/evidencias/<materia>/
- [ ] No rompe funcionalidad existente
- [ ] Funciona desde `docker compose up` en maquina limpia
