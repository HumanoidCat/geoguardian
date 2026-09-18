import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  FILTROS_VACIOS,
  describirCorte,
  describirFiltros,
  filtrar,
  hayFiltros,
  soloFecha,
  trozos,
} from '../datos/incidentes'

/**
 * Muestra el texto como fue escrito: el documento usa markdown y los signos de
 * marcado no son contenido. Ver `trozos`.
 */
function Texto({ children }) {
  return (
    <>
      {trozos(children).map((trozo, indice) =>
        trozo.tipo === 'fuerte' ? (
          <strong key={indice}>{trozo.texto}</strong>
        ) : trozo.tipo === 'codigo' ? (
          <code key={indice}>{trozo.texto}</code>
        ) : (
          <span key={indice}>{trozo.texto}</span>
        ),
      )}
    </>
  )
}

/**
 * El historico de incidencias del proyecto, consultable desde la aplicacion.
 *
 * Historia H12.5. Rubrica Troubleshoot.
 *
 * DE DONDE SALE EL DATO
 *
 * De `docs/04-bitacora-incidencias.md`, el documento que el equipo escribe a mano
 * y revisa en Pull Request. Llega como archivo estatico generado por
 * `frontend/herramientas/generar_incidentes.py`.
 *
 * **No pasa por la API porque no hay API que lo sirva**, igual que el historial de
 * eventos de H7.3. Servirlo desde el propio origen respeta **D-23** sin pedirle
 * nada a nadie.
 *
 * LO QUE NO HACE
 *
 * No resume y no reescribe. Cada incidencia se muestra con **todas** sus secciones
 * y con el rotulo que el documento les puso, incluso cuando ese rotulo no esta en
 * la plantilla —y en 61 incidencias hay 151 rotulos distintos, asi que pasa
 * seguido—. Una bitacora vale porque nadie la suavizo.
 */
export default function HistorialIncidentes({ alVerMapa }) {
  const [filtros, setFiltros] = useState(FILTROS_VACIOS)
  const [abierta, setAbierta] = useState(null)
  // `undefined` mientras se pide, `null` si no esta. Son estados distintos y se
  // muestran distinto: «cargando» no es lo mismo que «no hay archivo».
  const [paquete, setPaquete] = useState(undefined)

  useEffect(() => {
    let vigente = true
    fetch(`${import.meta.env.BASE_URL}incidentes/incidentes.json`)
      .then((respuesta) => (respuesta.ok ? respuesta.json() : null))
      .then((datos) => {
        if (vigente) setPaquete(datos)
      })
      .catch(() => {
        if (vigente) setPaquete(null)
      })
    return () => {
      vigente = false
    }
  }, [])

  // Con `useMemo` y no suelto: `?? []` crea un arreglo nuevo en cada render, y eso
  // invalidaria el `useMemo` de abajo siempre, que es justo lo que evita.
  const incidentes = useMemo(() => paquete?.incidentes ?? [], [paquete])
  const visibles = useMemo(() => filtrar(incidentes, filtros), [incidentes, filtros])
  const corte = useMemo(() => describirCorte(paquete), [paquete])

  const cambiar = useCallback((campo, valor) => {
    setFiltros((previos) => ({ ...previos, [campo]: valor }))
  }, [])

  const limpiar = useCallback(() => setFiltros(FILTROS_VACIOS), [])

  if (paquete === undefined) {
    return (
      <section className="incidentes" aria-label="Historico de incidencias">
        <p className="incidentes-vacio" aria-live="polite">
          Cargando el historico...
        </p>
      </section>
    )
  }

  // CA-5 · si el archivo no esta, se dice. No se muestra una pantalla vacia, que
  // haria creer que no hay incidencias cuando lo que falta es el archivo.
  if (!paquete) {
    return (
      <section className="incidentes" aria-label="Historico de incidencias">
        <div className="incidentes-encabezado">
          <h2 className="incidentes-titulo">Historico de incidencias</h2>
          <button type="button" className="boton-ir-a-hoy" onClick={alVerMapa}>
            Volver al mapa
          </button>
        </div>
        <p className="incidentes-vacio">
          No se encontro <code>incidentes/incidentes.json</code>, asi que no hay historico que
          mostrar. <strong>No quiere decir que no haya incidencias:</strong> quiere decir que
          falta el archivo. Se genera con{' '}
          <code>python frontend/herramientas/generar_incidentes.py</code>.
        </p>
      </section>
    )
  }

  const activos = describirFiltros(filtros)

  return (
    <section className="incidentes" aria-label="Historico de incidencias">
      <div className="incidentes-encabezado">
        <div>
          <h2 className="incidentes-titulo">Historico de incidencias</h2>
          <p className="incidentes-subtitulo">
            Los errores que el equipo cometio, con su causa y lo que se aprendio. Salen de{' '}
            <code>{paquete.fuente}</code> y se muestran tal como estan escritos: no se resumen
            ni se reescriben.
          </p>
        </div>
        <button type="button" className="boton-ir-a-hoy" onClick={alVerMapa}>
          Volver al mapa
        </button>
      </div>

      {/* CA-5 · de cuando es este historico */}
      <p className="incidentes-corte">
        {corte ? (
          <>
            {paquete.total} incidencias · corte del <strong>{corte.iso}</strong> ({corte.cuando})
          </>
        ) : (
          <>
            {paquete.total} incidencias ·{' '}
            <span className="incidentes-ausente">sin fecha de corte en el archivo</span>
          </>
        )}
      </p>

      {/* CA-3 · los dos filtros */}
      <div className="incidentes-filtros">
        <label>
          <span>Buscar en todo el texto</span>
          <input
            type="search"
            value={filtros.texto}
            onChange={(evento) => cambiar('texto', evento.target.value)}
            placeholder="verificador, trama, IPv6..."
          />
        </label>
        <label>
          <span>Quien la detecto</span>
          <input
            type="search"
            value={filtros.detecto}
            onChange={(evento) => cambiar('detecto', evento.target.value)}
            placeholder="Cesar, el CI, el profesor..."
          />
        </label>
        {hayFiltros(filtros) && (
          <button type="button" className="incidentes-limpiar" onClick={limpiar}>
            Quitar filtros
          </button>
        )}
      </div>

      {/* El contador dice cuantas de cuantas, y por que bajo */}
      <p className="incidentes-conteo" aria-live="polite">
        <strong>
          {visibles.length} de {incidentes.length}
        </strong>
        {activos.length > 0 && <> · filtrando por {activos.join(' y ')}</>}
      </p>

      {visibles.length === 0 ? (
        <p className="incidentes-sin-resultados">
          Ninguna incidencia coincide con {activos.join(' y ')}. El historico tiene{' '}
          {incidentes.length}; lo que no hay es una que cumpla eso.
        </p>
      ) : (
        <ol className="incidentes-lista">
          {visibles.map((incidente) => {
            const desplegada = abierta === incidente.id
            return (
              <li key={incidente.id} className="incidentes-ficha">
                <button
                  type="button"
                  className="incidentes-ficha-cabecera"
                  aria-expanded={desplegada}
                  onClick={() => setAbierta(desplegada ? null : incidente.id)}
                >
                  <span className="incidentes-id">{incidente.id}</span>
                  <span className="incidentes-ficha-titulo">
                    <Texto>{incidente.titulo}</Texto>
                  </span>
                  <span className="incidentes-fecha">
                    {/* Solo la fecha; la oracion completa vive en sus secciones */}
                    {soloFecha(incidente.fecha) ?? (
                      <span className="incidentes-ausente">sin fecha</span>
                    )}
                  </span>
                </button>

                {desplegada && (
                  <div className="incidentes-cuerpo">
                    {/* Todas las secciones, con el rotulo que el documento les dio */}
                    <dl className="incidentes-secciones">
                      {incidente.secciones.map((seccion, indice) => (
                        <div key={`${incidente.id}-${indice}`}>
                          <dt>{seccion.etiqueta}</dt>
                          <dd>
                            {seccion.bloques.map((bloque, i) =>
                              bloque.tipo === 'codigo' ? (
                                // Los saltos de linea son el contenido: una salida
                                // de EXPLAIN aplastada en un parrafo no dice nada.
                                <pre key={i} className="incidentes-codigo">
                                  {bloque.texto}
                                </pre>
                              ) : (
                                <p key={i} className="incidentes-parrafo">
                                  <Texto>{bloque.texto}</Texto>
                                </p>
                              ),
                            )}
                          </dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                )}
              </li>
            )
          })}
        </ol>
      )}
    </section>
  )
}
