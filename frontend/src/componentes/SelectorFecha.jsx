import { fechaDeHoy } from '../datos/cliente'

/**
 * Selector de la fecha de la estimacion.
 *
 * Historia H5.7. Rubrica de Computacion Grafica, criterio CG-4.
 *
 * ---------------------------------------------------------------------------
 * POR QUE EL TOPE SUPERIOR ES HOY
 * ---------------------------------------------------------------------------
 *
 * La estimacion de una fecha `t` describe los siete dias siguientes, `(t, t+7]`
 * (H3.0, CA-4), y se calcula con lo observado hasta `t`. Pedir hoy ya es pedir la
 * semana que viene; pedir manana exigiria observaciones que todavia no existen.
 * Dejar elegir el mes que viene ofreceria una consulta que solo puede devolver
 * vacio, y una pantalla en blanco sin explicacion se lee como un fallo del visor
 * y no como lo que es.
 *
 * Hasta el 2026-09-06 este comentario y la nota visible decian que el tope
 * existia por falta de modelo, y que se moveria cuando H3.4
 * entregara el clasificador. H3.4 cerro el 2026-09-03 y la frase sobrevivio
 * tres dias en el sitio publicado (H5.9, CA-2): era cierta el dia que se
 * escribio y nombraba la historia que la iba a invalidar, igual que I-41. Se
 * corrige la razon; la regla no cambia, porque el modelo estima desde lo
 * observado, no hacia adelante desde una fecha sin observaciones.
 *
 * ---------------------------------------------------------------------------
 * POR QUE NO HAY TOPE INFERIOR
 * ---------------------------------------------------------------------------
 *
 * Seria inventarlo. El visor **no sabe** desde cuando tiene datos la API: el
 * contrato no expone ese rango y deducirlo del inicio de alguna serie seria un
 * dato que nadie afirmo.
 *
 * La consecuencia esta cubierta y es honesta: una fecha sin estimacion devuelve
 * los ocho distritos sin nivel, y el visor los pinta con la trama de ausencia y
 * los cuenta en la leyenda. Ausencia de dato, no error.
 *
 * ---------------------------------------------------------------------------
 * POR QUE SE BLOQUEA CONTRA EL RESPALDO
 * ---------------------------------------------------------------------------
 *
 * Los archivos estaticos tienen **una sola fecha**. Ofrecer un selector que no
 * puede cambiar nada es peor que no ofrecerlo: quien lo use va a creer que
 * cambio de fecha y va a estar mirando el mismo dia.
 *
 * Es la distincion de H6.6 otra vez: lo que se puede hacer depende de **por
 * donde** llegaron los datos, no de que son.
 */
export default function SelectorFecha({ fecha, alCambiar, bloqueado, fechaDelRespaldo }) {
  const hoy = fechaDeHoy()

  if (bloqueado) {
    return (
      <div className="selector-fecha selector-fecha-bloqueado">
        <span className="selector-fecha-etiqueta">Fecha de la estimacion</span>
        <p className="selector-fecha-aviso">
          Sin conexion con la API solo existe la estimacion del{' '}
          <strong>{fechaDelRespaldo ?? 'archivo de respaldo'}</strong>. No se puede
          elegir otra fecha porque el respaldo no tiene ninguna otra.
        </p>
      </div>
    )
  }

  return (
    <div className="selector-fecha">
      <label htmlFor="fecha-estimacion" className="selector-fecha-etiqueta">
        Fecha de la estimacion
      </label>
      <div className="selector-fecha-controles">
        <input
          id="fecha-estimacion"
          type="date"
          value={fecha}
          max={hoy}
          onChange={(evento) => evento.target.value && alCambiar(evento.target.value)}
        />
        {/* Volver a hoy con un clic. Sin esto, quien se fue tres meses atras tiene
            que acordarse de la fecha de hoy para regresar, y el visor lo obliga a
            mirar el reloj para volver a su estado inicial. */}
        {fecha !== hoy && (
          <button type="button" className="selector-fecha-hoy" onClick={() => alCambiar(hoy)}>
            Volver a hoy
          </button>
        )}
      </div>
      <p className="selector-fecha-nota">
        Hasta hoy: cada fecha estima los siete dias siguientes con lo observado
        hasta ese dia.
      </p>
    </div>
  )
}
