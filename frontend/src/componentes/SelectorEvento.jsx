import { EVENTOS } from '../datos/eventos'

function EstadoEvento({ resumen, ausencia }) {
  if (resumen.nivelMaximo === null) {
    return (
      <span className="selector-evento-estado" title={ausencia ?? undefined}>
        <span className="punto-nivel trama-sin-dato" aria-hidden="true" />
        {ausencia ? 'no se estima' : 'sin estimacion'}
      </span>
    )
  }
  const cuantos = resumen.porNivel[resumen.nivelMaximo].length
  return (
    <span className="selector-evento-estado">
      <span className={`punto-nivel punto-riesgo-${resumen.nivelMaximo}`} aria-hidden="true" />
      {resumen.nivelMaximo} en {cuantos} de {resumen.total}
    </span>
  )
}

/**
 * Selector del tipo de evento que colorea el mapa.
 *
 * Los tres eventos y sus umbrales viven en src/datos/eventos.js, no aca: este
 * archivo solo exporta el componente.
 */
export default function SelectorEvento({ seleccionado, alCambiar, resumenes = null }) {
  const activo = EVENTOS.find((evento) => evento.id === seleccionado)

  return (
    <div className="selector-evento">
      <div className="selector-evento-grupo" role="radiogroup" aria-label="Tipo de evento">
        {EVENTOS.map((evento) => (
          <button
            key={evento.id}
            type="button"
            role="radio"
            aria-checked={evento.id === seleccionado}
            className={
              evento.id === seleccionado
                ? 'selector-evento-boton selector-evento-boton-activo'
                : 'selector-evento-boton'
            }
            onClick={() => alCambiar(evento.id)}
          >
            <span className="selector-evento-nombre">{evento.nombre}</span>
            {/* Que tiene cada evento ANTES de hacer clic (H5.9, CA-1). Sequia no
                tiene estimaciones nunca por D-34; sin esta linea, elegirla era
                la unica forma de enterarse, y la pantalla vacia se leia como un
                fallo. Se deriva del resumen; si no llego, no se afirma nada. */}
            {resumenes?.[evento.id] && (
              <EstadoEvento resumen={resumenes[evento.id]} ausencia={evento.ausencia} />
            )}
          </button>
        ))}
      </div>

      {/* El umbral, siempre a la vista: es lo que permite entender que significa
          "alto". En pantalla ancha va como parrafo junto a los botones; en
          telefono (H5.9), donde ocupaba cinco lineas antes del mapa, va plegado
          bajo un resumen y se abre con un toque. Cual de los dos se ve lo
          decide el CSS; el texto es el mismo. */}
      {activo && (
        <p className="selector-evento-umbral">
          {activo.umbral}
          {activo.ausencia && <> {activo.ausencia}</>}
        </p>
      )}
      {activo && (
        <details className="selector-evento-umbral-plegable">
          <summary>Que significa «alto» en {activo.nombre.toLowerCase()}</summary>
          <p>
            {activo.umbral}
            {activo.ausencia && <> {activo.ausencia}</>}
          </p>
        </details>
      )}
    </div>
  )
}
