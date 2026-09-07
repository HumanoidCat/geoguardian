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
import { fechaDeHoy } from '../datos/cliente'

const NIVELES = [
  { id: 'alto', nombre: 'Alto' },
  { id: 'medio', nombre: 'Medio' },
  { id: 'bajo', nombre: 'Bajo' },
]

// `hoyLocal` vivia aca, con la misma cuenta que hace cliente.js. Desde H5.7 se
// importa `fechaDeHoy` de cliente.js: eran dos definiciones de "hoy en hora
// local" y basta que una cambie para que el visor se contradiga a si mismo, que
// es la forma de I-07 aplicada al codigo en vez de a los documentos.
const hoyLocal = fechaDeHoy

export default function LeyendaRiesgo({ nombreEvento, riesgos, simulado, fecha }) {
  const valores = Object.values(riesgos ?? {})

  const contar = (nivel) => valores.filter((riesgo) => riesgo.nivel === nivel).length
  const sinEstimacion = valores.filter((riesgo) => !riesgo.nivel).length

  return (
    <div className="leyenda">
      <h3 className="leyenda-titulo">Riesgo de {nombreEvento?.toLowerCase()}</h3>

      {/* La fecha de la estimacion, siempre visible.
          El dato viajaba en el paquete desde H6.6 y ningun componente lo leia. Un
          mapa de riesgo sin fecha es un mapa que afirma "hoy" sin haberlo
          comprobado, y el respaldo estatico demostro que no siempre es hoy: sus
          archivos son del 16 de agosto y la pantalla no lo decia en ningun lado.
          Con la API pasa lo mismo el dia que la ingesta se atrase. */}
      {fecha && (
        <p className={fecha === hoyLocal() ? 'leyenda-fecha' : 'leyenda-fecha leyenda-fecha-vieja'}>
          Estimacion del <strong>{fecha}</strong>
          {fecha !== hoyLocal() && <span> · no es de hoy</span>}
        </p>
      )}

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
          Niveles simulados: estos valores no salen de un modelo ni de
          observaciones y no representan riesgo real.
        </p>
      )}
    </div>
  )
}
