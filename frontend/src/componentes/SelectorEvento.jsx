import { EVENTOS } from '../datos/eventos'

/**
 * Selector del tipo de evento que colorea el mapa.
 *
 * Los tres eventos y sus umbrales viven en src/datos/eventos.js, no aca: este
 * archivo solo exporta el componente.
 */
export default function SelectorEvento({ seleccionado, alCambiar }) {
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
            {evento.nombre}
          </button>
        ))}
      </div>

      {activo && <p className="selector-evento-umbral">{activo.umbral}</p>}
    </div>
  )
}
