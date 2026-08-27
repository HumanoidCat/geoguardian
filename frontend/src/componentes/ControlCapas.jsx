import { CAPAS_BASE, CAPAS_SUPERPUESTAS } from '../datos/capasBase'

// Por debajo de este valor la rampa deja de leerse sobre la capa base. Se
// determino mirando la pantalla con relieve al 30 %: "bajo" se confundia con el
// terreno y "medio" perdia su naranja. El script de accesibilidad no lo detecta
// porque mide colores solidos.
const UMBRAL_OPACIDAD_FIABLE = 0.5

/**
 * Control de capas del visor.
 *
 * Historia H5.2. Rubrica de Computacion Grafica, criterio CG-4.
 *
 * Se escribio como panel propio y no con el control que trae Leaflet por dos
 * razones. La primera es que el control de Leaflet solo permite prender y
 * apagar: no tiene donde poner un deslizador de opacidad ni una descripcion de
 * para que sirve cada capa. La segunda es que ese control no usa el sistema de
 * diseno, asi que quedaria como un elemento ajeno encima del mapa.
 *
 * Cada capa lleva una linea que dice para que sirve. Un visor que obliga a
 * probar capas a ciegas para descubrir cual necesita esta mal explicado.
 */
export default function ControlCapas({
  capaBase,
  alCambiarCapaBase,
  superpuestas,
  alAlternarSuperpuesta,
  opacidad,
  alCambiarOpacidad,
}) {
  return (
    <section className="control-capas" aria-label="Capas del mapa">
      <div className="control-capas-bloque">
        <h3 className="control-capas-titulo">Capa base</h3>
        <div role="radiogroup" aria-label="Capa base">
          {CAPAS_BASE.map((capa) => (
            <label key={capa.id} className="control-capas-opcion">
              <input
                type="radio"
                name="capa-base"
                value={capa.id}
                checked={capaBase === capa.id}
                onChange={() => alCambiarCapaBase(capa.id)}
              />
              <span className="control-capas-texto">
                <span className="control-capas-nombre">{capa.nombre}</span>
                <span className="control-capas-descripcion">{capa.descripcion}</span>
              </span>
            </label>
          ))}
        </div>
      </div>

      <div className="control-capas-bloque">
        <h3 className="control-capas-titulo">Capas superpuestas</h3>
        {CAPAS_SUPERPUESTAS.map((capa) => (
          <div key={capa.id}>
            <label className="control-capas-opcion">
              <input
                type="checkbox"
                checked={Boolean(superpuestas[capa.id])}
                onChange={() => alAlternarSuperpuesta(capa.id)}
              />
              <span className="control-capas-texto">
                <span className="control-capas-nombre">{capa.nombre}</span>
                <span className="control-capas-descripcion">{capa.descripcion}</span>
              </span>
            </label>

            {/* El deslizador solo aparece cuando la capa que controla esta
                encendida. Un control que no afecta a nada visible confunde. */}
            {capa.conOpacidad && superpuestas[capa.id] && (
              <div className="control-opacidad">
                <label htmlFor="opacidad-riesgo" className="control-opacidad-etiqueta">
                  Opacidad
                  <span className="control-opacidad-valor">{Math.round(opacidad * 100)} %</span>
                </label>
                <input
                  id="opacidad-riesgo"
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={Math.round(opacidad * 100)}
                  onChange={(evento) => alCambiarOpacidad(Number(evento.target.value) / 100)}
                />

                {/* El deslizador deja al usuario degradar la propiedad que el
                    sistema de diseno verifica: por debajo de la mitad, los
                    colores de la rampa se mezclan con la capa base y dejan de
                    distinguirse entre si. No se le quita el control, se le
                    avisa. Ocultar el problema seria peor que declararlo. */}
                {opacidad < UMBRAL_OPACIDAD_FIABLE && (
                  <p className="control-opacidad-aviso" role="status">
                    Por debajo del {Math.round(UMBRAL_OPACIDAD_FIABLE * 100)} % los niveles se
                    mezclan con la capa base y dejan de distinguirse con fiabilidad. Util para
                    inspeccionar el terreno, no para leer el riesgo.
                  </p>
                )}
              </div>
            )}

          </div>
        ))}
      </div>
    </section>
  )
}
