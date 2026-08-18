/**
 * Leyenda de la escala de riesgo.
 *
 * Historia H5.3. Rubrica de Computacion Grafica, criterio CG-1.
 *
 * La decision de diseno mas importante esta en la separacion: los tres niveles
 * van juntos y la ausencia de estimacion va debajo de una linea divisoria, no
 * como un cuarto escalon de la rampa. Un distrito sin estimar no es un distrito
 * de riesgo bajo: es un distrito que nadie midio, y confundirlos hace que el
 * mapa afirme algo que nadie calculo.
 *
 * La leyenda muestra ademas cuantos distritos hay en cada nivel. Sin ese conteo,
 * quien mira el mapa tiene que contar cuadros a ojo.
 */

const NIVELES = [
  { id: 'alto', nombre: 'Alto' },
  { id: 'medio', nombre: 'Medio' },
  { id: 'bajo', nombre: 'Bajo' },
]

export default function LeyendaRiesgo({ nombreEvento, riesgos, simulado }) {
  const valores = Object.values(riesgos ?? {})

  const contar = (nivel) => valores.filter((riesgo) => riesgo.nivel === nivel).length
  const sinEstimacion = valores.filter((riesgo) => !riesgo.nivel).length

  return (
    <div className="leyenda">
      <h3 className="leyenda-titulo">Riesgo de {nombreEvento?.toLowerCase()}</h3>

      <ul className="leyenda-lista">
        {NIVELES.map((nivel) => (
          <li key={nivel.id} className="leyenda-fila">
            <span className={`cuadro-leyenda cuadro-riesgo-${nivel.id}`} aria-hidden="true" />
            <span className="leyenda-nombre">{nivel.nombre}</span>
            <span className="leyenda-conteo">{contar(nivel.id)}</span>
          </li>
        ))}
      </ul>

      <hr className="leyenda-separador" />

      <ul className="leyenda-lista">
        <li className="leyenda-fila">
          <span className="cuadro-leyenda trama-sin-dato cuadro-sin-dato" aria-hidden="true" />
          <span className="leyenda-nombre">Sin estimacion</span>
          <span className="leyenda-conteo">{sinEstimacion}</span>
        </li>
      </ul>

      {simulado && (
        <p className="leyenda-aviso">
          Niveles simulados. No hay modelo entrenado: estos valores no
          representan riesgo real.
        </p>
      )}
    </div>
  )
}
