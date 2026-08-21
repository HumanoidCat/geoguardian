import { useMemo } from 'react'
import { EVENTOS, UMBRAL_CORTO } from '../datos/eventos'

/**
 * Semaforo de riesgo por distrito y evento.
 *
 * Historia H7.1. Rubrica de Computacion Grafica, criterio CG-2.
 *
 * ---------------------------------------------------------------------------
 * QUE MUESTRA, Y POR QUE NO ES UNA REPETICION DEL MAPA
 * ---------------------------------------------------------------------------
 *
 * El mapa muestra un evento a la vez y responde "donde". El semaforo muestra los
 * tres eventos juntos y responde otra pregunta: **que hay que atender primero**.
 * Son ocho distritos por tres eventos, veinticuatro celdas, y en un mapa eso no
 * cabe sin cambiar de capa tres veces.
 *
 * ---------------------------------------------------------------------------
 * TRES DECISIONES
 * ---------------------------------------------------------------------------
 *
 * 1. Ordenado por riesgo, no alfabeticamente.
 *
 *    Si alguien del Comite Municipal de Emergencias abre esto durante un evento,
 *    lo primero que ve tiene que ser lo mas urgente. El orden alfabetico es comodo
 *    para buscar un distrito conocido y malo para decidir cual mirar. Se ordena
 *    por la probabilidad mas alta que tenga el distrito en cualquiera de los tres
 *    eventos, de mayor a menor.
 *
 * 2. Cada celda muestra el nivel Y la probabilidad.
 *
 *    El nivel es la clase; la probabilidad es lo que distingue dos "altos" que no
 *    son igual de altos. Desde D-21, `probabilidad` es P(nivel = alto), asi que
 *    es comparable entre distritos y entre eventos. Sin ella, ocho distritos en
 *    rojo se ven todos iguales.
 *
 * 3. Los umbrales van en la cabecera de cada columna, no en un pie de pagina.
 *
 *    Quien lee la tabla tiene que poder saber que significa "alto" sin buscar en
 *    otro lado. Es el mismo criterio del selector de eventos del mapa.
 */

const NOMBRE_POR_NIVEL = { bajo: 'Bajo', medio: 'Medio', alto: 'Alto' }

/** Para ordenar: un distrito sin ninguna probabilidad va al final, no al principio. */
function riesgoMaximo(codigo, paquetes) {
  const valores = EVENTOS.map((evento) => paquetes?.[evento.id]?.riesgos?.[codigo]?.probabilidad)
    .filter((valor) => valor !== null && valor !== undefined)

  return valores.length === 0 ? -1 : Math.max(...valores)
}

function Celda({ riesgo, nombreDistrito, nombreEvento, alSeleccionar }) {
  const nivel = riesgo?.nivel ?? null
  const probabilidad = riesgo?.probabilidad

  if (!nivel) {
    return (
      <td className="celda-semaforo">
        <span
          className="marca-semaforo trama-sin-dato"
          title={`${nombreDistrito}, ${nombreEvento}: sin estimacion`}
        >
          <span className="valor-ausente">sin dato</span>
        </span>
      </td>
    )
  }

  const porcentaje =
    probabilidad === null || probabilidad === undefined ? null : Math.round(probabilidad * 100)

  return (
    <td className="celda-semaforo">
      <button
        type="button"
        className={`marca-semaforo marca-riesgo-${nivel}`}
        onClick={alSeleccionar}
        title={`${nombreDistrito}, ${nombreEvento}: riesgo ${nivel}`}
      >
        <span className="marca-nivel">{NOMBRE_POR_NIVEL[nivel]}</span>
        {/* La probabilidad distingue dos "altos" que no son igual de altos. Si no
            se pudo calcular, se declara en vez de omitirse: una celda con nivel y
            sin numero se leeria como un error de dibujo. */}
        <span className="marca-probabilidad">
          {porcentaje === null ? 'sin calcular' : `${porcentaje} %`}
        </span>
      </button>
    </td>
  )
}

export default function TableroSemaforo({ distritos, paquetes, alSeleccionar, seleccionado }) {
  const filas = useMemo(() => {
    if (!distritos?.length) return []
    return [...distritos].sort(
      (uno, otro) => riesgoMaximo(otro.codigo, paquetes) - riesgoMaximo(uno.codigo, paquetes),
    )
  }, [distritos, paquetes])

  if (filas.length === 0) return null

  const simulado = EVENTOS.some((evento) => paquetes?.[evento.id]?.simulado)
  const fecha = paquetes?.[EVENTOS[0].id]?.fecha

  return (
    <section className="tablero" aria-label="Semaforo de riesgo por distrito y evento">
      <header className="tablero-cabecera">
        <h2 className="tablero-titulo">Semaforo de riesgo</h2>
        <p className="tablero-subtitulo">
          Los ocho distritos y los tres eventos, ordenados por riesgo.
          {fecha ? ` Estimacion del ${fecha}.` : ''}
        </p>
      </header>

      <div className="tablero-desplazable">
        <table className="tabla-semaforo">
          <thead>
            <tr>
              <th scope="col" className="columna-distrito">
                Distrito
              </th>
              {EVENTOS.map((evento) => (
                <th key={evento.id} scope="col">
                  <span className="columna-evento">{evento.nombre}</span>
                  {/* El umbral abreviado, con el texto completo al pasar el
                      cursor. Abreviar no es esconder: el corte tiene que estar a
                      la vista para poder entender que significa "alto". */}
                  <span className="columna-umbral" title={evento.umbral}>
                    {UMBRAL_CORTO[evento.id]}
                  </span>
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {filas.map((distrito) => (
              <tr
                key={distrito.codigo}
                className={distrito.codigo === seleccionado ? 'fila-seleccionada' : undefined}
              >
                <th scope="row" className="columna-distrito">
                  <span className="nombre-distrito">{distrito.nombre}</span>
                  <span className="codigo-distrito">{distrito.codigo}</span>
                </th>

                {EVENTOS.map((evento) => (
                  <Celda
                    key={evento.id}
                    riesgo={paquetes?.[evento.id]?.riesgos?.[distrito.codigo]}
                    nombreDistrito={distrito.nombre}
                    nombreEvento={evento.nombre}
                    alSeleccionar={() => alSeleccionar(distrito.codigo, evento.id)}
                  />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {simulado && (
        <p className="tablero-aviso">
          Niveles simulados. No hay modelo entrenado: estos valores no representan
          riesgo real.
        </p>
      )}
    </section>
  )
}
