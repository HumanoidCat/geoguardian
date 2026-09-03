/**
 * Grafica interactiva de la serie climatica de un distrito. Historia H7.2.
 *
 * SOBRE LA PROPIEDAD DE ESTE ARCHIVO
 *
 * `frontend/` es de Avril. H7.2 paso a Alejandro el 2026-08-31 por **D-33**, y la
 * excepcion se movio con la historia. Esta declarada en
 * `docs/07-propiedad-archivos.md`.
 *
 * POR QUE LOS ESTILOS VIVEN AQUI DENTRO Y NO EN `index.css`
 *
 * `src/estilos/` y `src/index.css` **no** estan en la excepcion: siguen siendo de
 * Avril sin condiciones. Meter reglas ahi seria tomarme un permiso que no pedi.
 *
 * Asi que el bloque `<style>` va en este archivo, usando **las variables de
 * `tokens.css`** —no colores propios— para que la grafica se vea del proyecto y no
 * de otro. Si mas adelante conviene mover esto a la hoja comun, es decision de
 * Avril y es un corta-pega.
 *
 * LO QUE ESTA GRAFICA NO HACE, A PROPOSITO
 *
 * **No une la linea por encima de un dia sin dato.** `connectNulls` queda en
 * `false`. Un hueco dibujado como continuidad afirma una medicion que nadie tomo,
 * y el simulado trae uno de cada veinte dias justamente para que esto se pueda
 * comprobar. Ver el criterio CA-3 en `verificar_h72.mjs`.
 */

import { Suspense, lazy, useEffect, useMemo, useState } from 'react'

import { ORIGEN_ESTATICO, VARIABLES, obtenerMediciones } from '../datos/cliente.js'

/**
 * El dibujo se carga TARDE, y no es una optimizacion de adorno.
 *
 * `recharts` mas que duplica el paquete inicial del visor: 324,87 kB sin la
 * grafica, 710,33 kB con ella (gzip 101,07 y 203,13). Sin este corte, ese peso lo
 * descarga todo el que abre el mapa aunque nunca haga clic en un distrito.
 *
 * Con `lazy`, el fragmento se pide cuando se abre la ficha. El motivo largo esta
 * en la cabecera de `GraficaSerieLienzo.jsx`.
 */
const GraficaSerieLienzo = lazy(() => import('./GraficaSerieLienzo.jsx'))

/**
 * Cuantos dias se muestran al abrir.
 *
 * 90 y no los 365 que hay: un anio entero en el ancho de la ficha deja menos de
 * un pixel por dia y la serie se ve como una mancha. Noventa dias se leen, y el
 * selector esta ahi para ampliar.
 */
const DIAS_INICIALES = 90

function restarDias(fecha, dias) {
  const d = new Date(`${fecha}T00:00:00`)
  d.setDate(d.getDate() - dias)
  return d.toISOString().slice(0, 10)
}

export default function GraficaSerie({ codigo, nombre }) {
  const [variable, setVariable] = useState(VARIABLES[0])
  const [datos, setDatos] = useState(null)
  const [rango, setRango] = useState(null)
  const [error, setError] = useState(null)

  // NINGUN `setState` SINCRONO EN EL CUERPO DEL EFECTO.
  //
  // La regla `react-hooks/set-state-in-effect` del proyecto lo prohibe, y con
  // razon: dispara renders en cascada. Todo cambio de estado ocurre dentro de un
  // callback de la promesa.
  //
  // Por eso tampoco hay un estado `cargando`: se DERIVA de que no haya ni datos
  // ni error. Un tercer estado que dijera lo mismo que los otros dos es una
  // fuente mas que puede contradecirlos.
  //
  // El rango se resuelve en dos pasos: la primera consulta pide todo para que el
  // origen declare su ventana, y de ahi sale el encuadre inicial. Suponerla aqui
  // seria repetir en el componente un dato que solo el origen conoce.
  useEffect(() => {
    if (!codigo) return undefined
    let vigente = true

    const desde = rango?.desde ?? '1900-01-01'
    const hasta = rango?.hasta ?? '2100-01-01'

    obtenerMediciones(codigo, desde, hasta)
      .then((respuesta) => {
        if (!vigente) return
        setError(null)
        setDatos(respuesta)
        if (!rango) {
          setRango({
            desde: restarDias(respuesta.ventana.hasta, DIAS_INICIALES - 1),
            hasta: respuesta.ventana.hasta,
          })
        }
      })
      .catch((causa) => {
        if (vigente) setError(causa.message)
      })

    return () => {
      vigente = false
    }
  }, [codigo, rango])

  // Al cambiar de distrito NO se limpia el estado con un efecto: el componente se
  // monta de nuevo, porque `PanelDistrito` le pasa `key={codigo}`. Es mas barato
  // y no puede quedar a medias, que es lo que pasa cuando se limpian tres estados
  // en un efecto y uno se olvida.
  const cargando = !datos && !error

  const filas = useMemo(
    () =>
      (datos?.filas ?? []).map((f) => ({
        fecha: f.fecha,
        valor: f[variable.campo] ?? null,
      })),
    [datos, variable],
  )

  const huecos = useMemo(() => filas.filter((f) => f.valor === null).length, [filas])

  if (!codigo) return null

  return (
    <section className="gs">
      <style>{ESTILOS}</style>

      <h3 className="gs-titulo">Serie climatica de {nombre}</h3>

      <div className="gs-controles">
        <label className="gs-campo">
          <span>Variable</span>
          <select
            value={variable.campo}
            onChange={(e) => setVariable(VARIABLES.find((v) => v.campo === e.target.value))}
          >
            {VARIABLES.map((v) => (
              <option key={v.campo} value={v.campo}>
                {v.etiqueta} ({v.unidad})
              </option>
            ))}
          </select>
        </label>

        {/* Los `min` y `max` salen de la ventana que declaro el origen, no de una
            constante escrita aqui. Ofrecer una fecha sin datos dibujaria un
            grafico vacio, y un grafico vacio se lee como «no llovio». */}
        <label className="gs-campo">
          <span>Desde</span>
          <input
            type="date"
            value={rango?.desde ?? ''}
            min={datos?.ventana.desde}
            max={rango?.hasta}
            onChange={(e) => setRango((r) => ({ ...r, desde: e.target.value }))}
          />
        </label>

        <label className="gs-campo">
          <span>Hasta</span>
          <input
            type="date"
            value={rango?.hasta ?? ''}
            min={rango?.desde}
            max={datos?.ventana.hasta}
            onChange={(e) => setRango((r) => ({ ...r, hasta: e.target.value }))}
          />
        </label>
      </div>

      {error && <p className="gs-error">No se pudo cargar la serie. {error}</p>}

      {!error && cargando && !datos && <p className="gs-estado">Cargando la serie...</p>}

      {!error && datos && (
        <>
          <div className="gs-lienzo">
            <Suspense fallback={<p className="gs-estado">Cargando la grafica...</p>}>
              <GraficaSerieLienzo filas={filas} unidad={variable.unidad} />
            </Suspense>
          </div>

          <p className="gs-pie">
            {filas.length} dias · <strong>{huecos} sin dato</strong>, dibujados como
            cortes en la linea y no como cero.
          </p>

          <p className="gs-pie gs-ventana">
            Datos disponibles del {datos.ventana.desde} al {datos.ventana.hasta}
            {datos.origen === ORIGEN_ESTATICO && ' · respaldo estatico, sin API'}.
          </p>

          <p className="gs-simulado">
            SERIE SIMULADA. Los valores los sortea el simulado de forma determinista;
            no son observaciones reales.
          </p>
        </>
      )}
    </section>
  )
}

const ESTILOS = `
.gs { margin-top: var(--espacio-4, 1rem); }
.gs-titulo {
  font-size: var(--texto-md, 0.95rem);
  color: var(--texto);
  margin: 0 0 var(--espacio-2, 0.5rem);
}
.gs-controles { display: flex; gap: var(--espacio-2, 0.5rem); flex-wrap: wrap; }
.gs-campo { display: flex; flex-direction: column; gap: 2px; flex: 1 1 7rem; }
.gs-campo > span {
  font-size: var(--texto-xs, 0.7rem);
  color: var(--texto-suave);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.gs-campo select, .gs-campo input {
  font: inherit;
  font-size: var(--texto-sm, 0.8rem);
  color: var(--texto);
  background: var(--superficie);
  border: 1px solid var(--borde-fuerte);
  border-radius: 4px;
  padding: 3px 6px;
  min-width: 0;
}
.gs-campo select:focus-visible, .gs-campo input:focus-visible {
  outline: 2px solid var(--foco);
  outline-offset: 1px;
}
.gs-lienzo { margin-top: var(--espacio-2, 0.5rem); }
.gs-globo {
  background: var(--superficie);
  border: 1px solid var(--borde-fuerte);
  border-radius: 4px;
  padding: 4px 8px;
  font-size: var(--texto-xs, 0.72rem);
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.gs-pie {
  font-size: var(--texto-xs, 0.72rem);
  color: var(--texto-suave);
  margin: var(--espacio-1, 0.25rem) 0 0;
}
.gs-ventana { color: var(--texto-tenue); }
.gs-estado, .gs-error {
  font-size: var(--texto-sm, 0.8rem);
  color: var(--texto-suave);
  margin: var(--espacio-2, 0.5rem) 0 0;
}
.gs-simulado {
  margin: var(--espacio-2, 0.5rem) 0 0;
  padding: 4px 8px;
  background: var(--simulado-fondo);
  color: var(--simulado-texto);
  border-radius: 4px;
  font-size: var(--texto-xs, 0.7rem);
}
`
