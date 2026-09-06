import { EVENTOS, nombreDeEvento } from '../datos/eventos'
import { NIVELES, enumerar, fechaEnPalabras } from '../datos/resumen'

const NOMBRE_NIVEL = { alto: 'alto', medio: 'medio', bajo: 'bajo' }

/**
 * El titular: la pagina dice en palabras cual es el riesgo de la fecha mostrada.
 *
 * Historia H5.9, criterio CA-8. Antes de esto, quien abria el visor tenia que
 * deducir el riesgo de hoy mirando colores; y si caia en un evento sin
 * estimaciones, veia un mapa en trama y nada que lo explicara.
 *
 * Todo el texto se deriva de `resumenes` (ver datos/resumen.js). Si el evento
 * mostrado no tiene estimacion, se dice, y se dice tambien cual si la tiene,
 * para que a nadie se le quede la impresion de que el sistema esta vacio.
 *
 * La fecha que se afirma es la del PAQUETE, no la pedida: contra el respaldo
 * estatico son distintas y rotular el dato con la fecha pedida seria I-04 otra
 * vez. La leyenda ya lo advierte en ambar; aca se afirma la correcta.
 */
export default function TitularRiesgo({ evento, resumenes, paquetes, fecha, nombres }) {
  if (!evento || !resumenes) return null

  const resumen = resumenes[evento]
  const fechaDelDato = paquetes?.[evento]?.fecha ?? fecha
  const nombreEvento = nombreDeEvento(evento).toLowerCase()
  const otros = EVENTOS.filter((e) => e.id !== evento)

  const ningunoConDato = EVENTOS.every((e) => resumenes[e.id]?.nivelMaximo === null)

  if (ningunoConDato) {
    return (
      <section className="titular titular-sin-dato" aria-labelledby="titular-texto">
        <p className="titular-fecha">{fechaEnPalabras(fechaDelDato)}</p>
        <h2 id="titular-texto" className="titular-texto" role="status">
          No hay estimacion para esta fecha en ningun evento.
        </h2>
        <p className="titular-detalle">
          Los ocho distritos se muestran sin nivel, con trama. Elegi otra fecha para ver
          estimaciones.
        </p>
      </section>
    )
  }

  const descripcionDeOtros = otros
    .map((e) => {
      const r = resumenes[e.id]
      if (!r || r.nivelMaximo === null) return `${e.nombre.toLowerCase()}: sin estimacion`
      const n = r.porNivel[r.nivelMaximo].length
      return `${e.nombre.toLowerCase()}: ${NOMBRE_NIVEL[r.nivelMaximo]} en ${n} de ${r.total}`
    })
    .join(' · ')

  if (resumen.nivelMaximo === null) {
    return (
      <section className="titular titular-sin-dato" aria-labelledby="titular-texto">
        <p className="titular-fecha">{fechaEnPalabras(fechaDelDato)}</p>
        <h2 id="titular-texto" className="titular-texto" role="status">
          Sin estimacion de {nombreEvento} para esta fecha.
        </h2>
        <p className="titular-detalle">
          <span className="titular-otros">{capitalizar(descripcionDeOtros)}.</span>
        </p>
      </section>
    )
  }

  const nivel = resumen.nivelMaximo
  const codigosMaximo = resumen.porNivel[nivel]
  const restantes = NIVELES.filter((n) => n !== nivel && resumen.porNivel[n].length > 0).map(
    (n) => `${NOMBRE_NIVEL[n]} en ${resumen.porNivel[n].length}`,
  )
  if (resumen.sinEstimacion.length > 0) {
    restantes.push(`sin estimacion en ${resumen.sinEstimacion.length}`)
  }

  return (
    <section className="titular" aria-labelledby="titular-texto">
      <p className="titular-fecha">
        {fechaEnPalabras(fechaDelDato)} · estimacion para los siete dias siguientes
      </p>
      <h2 id="titular-texto" className="titular-texto">
        <span className={`marca-nivel-titular marca-riesgo-${nivel}`}>Riesgo {NOMBRE_NIVEL[nivel]}</span>{' '}
        de {nombreEvento} en{' '}
        <strong>
          {codigosMaximo.length} de {resumen.total}
        </strong>{' '}
        distritos: {enumerar(codigosMaximo, nombres)}.
      </h2>
      <p className="titular-detalle">
        {restantes.length > 0 && <span>{capitalizar(restantes.join(', '))}. </span>}
        <span className="titular-otros">{capitalizar(descripcionDeOtros)}.</span>
      </p>
    </section>
  )
}

function capitalizar(texto) {
  return texto.charAt(0).toUpperCase() + texto.slice(1)
}
