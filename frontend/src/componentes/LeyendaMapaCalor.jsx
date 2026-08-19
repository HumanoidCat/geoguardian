import { RAMPA_PROBABILIDAD, puntosDeOrigen } from '../datos/interpolacion'

/**
 * Leyenda del mapa de calor.
 *
 * Historia H5.4. Rubrica de Computacion Grafica, criterio CG-1.
 *
 * Declara tres cosas que la superficie por si sola no dice, y sin las cuales el
 * mapa se leeria como algo que no es:
 *
 *   1. Que representa PROBABILIDAD, no nivel de riesgo. La paleta es distinta
 *      justamente para que no se confundan, pero conviene decirlo con palabras.
 *   2. Sobre cuantos puntos se interpolo. Ocho es muy poco, y quien mire el mapa
 *      tiene derecho a saberlo antes de sacar conclusiones.
 *   3. Con que exponente, porque el mismo dato con otro exponente se ve distinto.
 */
export default function LeyendaMapaCalor({ centroides, riesgos, exponente }) {
  const puntos = puntosDeOrigen(centroides ?? [], riesgos)
  const total = centroides?.length ?? 0

  const gradiente = RAMPA_PROBABILIDAD.map(
    (paso) => `rgb(${paso.color.join(',')}) ${Math.round(paso.limite * 100)}%`,
  ).join(', ')

  if (puntos.length === 0) {
    return (
      <div className="leyenda">
        <h3 className="leyenda-titulo">Mapa de calor</h3>
        <p className="leyenda-aviso">
          No hay superficie que dibujar: ningun distrito tiene probabilidad
          calculada. La interpolacion necesita valores, y rellenarlos con ceros
          inventaria un dato.
        </p>
      </div>
    )
  }

  return (
    <div className="leyenda">
      <h3 className="leyenda-titulo">Probabilidad interpolada</h3>

      <div className="barra-gradiente" style={{ background: `linear-gradient(90deg, ${gradiente})` }} />
      <div className="barra-extremos">
        <span>0 %</span>
        <span>100 %</span>
      </div>

      <p className="leyenda-nota">
        Es la <strong>probabilidad</strong> de la estimacion, no el nivel de
        riesgo. Por eso usa otros colores.
      </p>

      <hr className="leyenda-separador" />

      <p className="leyenda-aviso">
        Interpolacion por distancia inversa sobre <strong>{puntos.length}</strong>
        {puntos.length === total ? '' : ` de ${total}`} puntos, exponente{' '}
        {exponente}. Los puntos de origen se marcan sobre el mapa. Con tan pocos
        puntos, la superficie es una ayuda visual, no una medicion del terreno.
      </p>

      <p className="leyenda-aviso">
        El rectangulo es el area donde la interpolacion esta definida, no el
        limite del canton. Fuera de esa caja no hay puntos que la sostengan.
      </p>
    </div>
  )
}
