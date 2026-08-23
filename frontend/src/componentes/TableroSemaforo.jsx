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
 *    por el NIVEL mas alto que tenga el distrito en cualquiera de los tres
 *    eventos, y la probabilidad desempata.
 *
 *    La primera version ordenaba solo por probabilidad y era un defecto: ver la
 *    nota de `claveDeOrden`.
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

/**
 * Peso ordinal de los niveles, para poder compararlos.
 *
 * No es una escala numerica del riesgo: entre "bajo" y "medio" no hay ninguna
 * distancia establecida. Solo sirve para ordenar, que es lo unico que una
 * variable ordinal permite hacer.
 */
const PESO_NIVEL = { bajo: 1, medio: 2, alto: 3 }

/** Distrito sin ninguna estimacion. Va al final, no al principio. */
const SIN_ESTIMACION = [-1, -1]

/**
 * Clave de orden de un distrito: el peor nivel, y la peor probabilidad como
 * desempate.
 *
 * ---------------------------------------------------------------------------
 * POR QUE NO ALCANZA CON LA PROBABILIDAD, QUE ES COMO ESTABA
 * ---------------------------------------------------------------------------
 *
 * `nivel` y `probabilidad` son dos opcionales INDEPENDIENTES en el contrato,
 * y el docstring de `Riesgo` en contratos/esquemas.py lo dice: `probabilidad`
 * es None mientras no exista un modelo entrenado.
 *
 * La version anterior ordenaba solo por probabilidad y mandaba al final a los
 * distritos que no la tenian. Un distrito con `nivel: alto` y `probabilidad:
 * null` quedaba DEBAJO de uno en bajo. Hoy no se ve, porque el simulado rellena
 * los dos campos siempre; se va a ver el dia que H3.4 entregue el clasificador,
 * que es justo cuando esta pantalla deja de ser una demostracion.
 *
 * Es la decision 3 del componente aplicada en un solo lugar: la celda ya
 * distingue "sin dato" de "con nivel y sin numero", y el orden los metia en la
 * misma bolsa. Defecto encontrado por el Lead PM al revisar el PR #147.
 *
 * ---------------------------------------------------------------------------
 * POR QUE EL FILTRO ES POR `nivel` Y NO POR `probabilidad`
 * ---------------------------------------------------------------------------
 *
 * Un riesgo con probabilidad y sin nivel se pinta como "sin dato" en la celda:
 * `Celda` devuelve la trama en cuanto falta el nivel, sin mirar el numero. Si el
 * orden lo tuviera en cuenta, un distrito subiria en la tabla por un valor que
 * la tabla no muestra en ningun lado. **El orden tiene que corresponder a lo
 * visible**, si no es imposible de auditar mirando la pantalla.
 *
 * Los dos maximos se toman por separado, cada uno sobre los tres eventos: es el
 * peor caso en cada eje. Desde D-21 `probabilidad` es P(nivel = alto), la misma
 * magnitud para los tres, asi que el maximo entre eventos significa algo.
 */
function claveDeOrden(codigo, paquetes) {
  const riesgos = EVENTOS.map((evento) => paquetes?.[evento.id]?.riesgos?.[codigo]).filter(
    (riesgo) => riesgo?.nivel,
  )

  if (riesgos.length === 0) return SIN_ESTIMACION

  return [
    Math.max(...riesgos.map((riesgo) => PESO_NIVEL[riesgo.nivel] ?? 0)),
    Math.max(...riesgos.map((riesgo) => riesgo.probabilidad ?? 0)),
  ]
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

    // La clave se calcula una vez por distrito y no dentro del comparador, que
    // corre del orden de n log n veces.
    const claves = new Map(
      distritos.map((distrito) => [distrito.codigo, claveDeOrden(distrito.codigo, paquetes)]),
    )

    return [...distritos].sort((uno, otro) => {
      const [nivelUno, probabilidadUno] = claves.get(uno.codigo)
      const [nivelOtro, probabilidadOtro] = claves.get(otro.codigo)

      // Alfabetico como ultimo desempate: entre distritos con la misma
      // informacion de riesgo, o entre los que no tienen ninguna, el orden util
      // es el de buscar un nombre. Ademas hace la tabla reproducible.
      return (
        nivelOtro - nivelUno ||
        probabilidadOtro - probabilidadUno ||
        uno.nombre.localeCompare(otro.nombre)
      )
    })
  }, [distritos, paquetes])

  if (filas.length === 0) return null

  const simulado = EVENTOS.some((evento) => paquetes?.[evento.id]?.simulado)

  // La fecha se toma de los tres eventos y no del primero. Contra la API los
  // tres piden el mismo dia, pero contra el respaldo cada riesgos-*.json trae la
  // suya: si alguien regenera uno solo, afirmar una sola fecha seria afirmar algo
  // falso sobre dos tercios de la tabla.
  const fechas = [
    ...new Set(EVENTOS.map((evento) => paquetes?.[evento.id]?.fecha).filter(Boolean)),
  ].sort()

  return (
    <section className="tablero" aria-label="Semaforo de riesgo por distrito y evento">
      <header className="tablero-cabecera">
        <h2 className="tablero-titulo">Semaforo de riesgo</h2>
        <p className="tablero-subtitulo">
          Los ocho distritos y los tres eventos, ordenados por riesgo.
          {fechas.length === 1 && ` Estimacion del ${fechas[0]}.`}
          {fechas.length > 1 && (
            <span className="tablero-fechas-dispares">
              {' '}
              Las columnas no son de la misma fecha: {fechas.join(', ')}.
            </span>
          )}
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
                      la vista para poder entender que significa "alto".

                      Con datos simulados el texto agrega de donde NO salieron los
                      numeros. El aviso del pie ya dice que son simulados, pero
                      esta al pie: se puede leer "alto: acumulado 72 h > P99" en la
                      cabecera y "alto 91 %" en la celda sin haber llegado abajo, y
                      concluir que ese 91 % salio de un percentil sobre treinta
                      anios de precipitacion. No salio de ahi. */}
                  <span
                    className="columna-umbral"
                    title={
                      simulado
                        ? `${evento.umbral} Es el corte del modelo real: los valores de esta tabla no salieron de el.`
                        : evento.umbral
                    }
                  >
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
