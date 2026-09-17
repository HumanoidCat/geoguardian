import { useEffect, useMemo, useState } from 'react'
import { ORIGEN_ESTATICO, obtenerMediciones, obtenerSalud } from '../datos/cliente.js'
import { PERIODOS, compararPeriodo, obtenerNormales } from '../datos/normales.js'

/**
 * El periodo actual del distrito comparado contra la normal climatologica.
 *
 * La normal sale de `frontend/public/normales/normales.json`, que produce
 * `generar_normales.py` desde `crudo.medicion_diaria` sobre 1991-2020. El valor
 * actual sale de la serie diaria del distrito, por `obtenerMediciones`.
 *
 * H7.4. Rubrica de Computacion Grafica, CG-2.
 */

// Cuantos dias de serie se piden. El anio en curso mas un margen: en diciembre el
// periodo «anio en curso» abarca once meses cerrados.
const DIAS_PEDIDOS = 400

function restarDias(fecha, dias) {
  const [a, m, d] = fecha.split('-').map(Number)
  const t = Date.UTC(a, m - 1, d) - dias * 86400000
  return new Date(t).toISOString().slice(0, 10)
}

/** La cifra con su signo y su unidad, que es el CA-3. */
function Comparacion({ c }) {
  if (c.parcial) {
    return (
      <p className="normal-cifra">
        <strong>
          {c.actual.toFixed(1)} {c.unidad}
        </strong>{' '}
        acumulado en {c.dias} de {c.diasPosibles} dias
      </p>
    )
  }

  const signo = c.porcentaje >= 0 ? 'por encima' : 'por debajo'
  const clase = c.porcentaje >= 0 ? 'normal-arriba' : 'normal-abajo'
  return (
    <p className="normal-cifra">
      <strong className={clase}>
        {Math.abs(c.porcentaje).toFixed(0)} % {signo} de lo normal
      </strong>
      <span className="normal-crudo">
        {c.actual.toFixed(1)} contra {c.normal.toFixed(1)} {c.unidad}
      </span>
    </p>
  )
}

export default function PanelNormales({ codigo, nombre }) {
  const [normales, setNormales] = useState(null)
  const [salud, setSalud] = useState(null)
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)
  const [periodo, setPeriodo] = useState(PERIODOS[1].id)
  const [variable, setVariable] = useState('precipitacion_mm')

  useEffect(() => {
    let vigente = true
    obtenerNormales().then((p) => {
      if (vigente) setNormales(p)
    })
    // `salud` decide si la comparacion se puede dibujar. Ver el bloque de abajo.
    obtenerSalud()
      .then((s) => {
        if (vigente) setSalud(s)
      })
      .catch(() => {})
    return () => {
      vigente = false
    }
  }, [])

  useEffect(() => {
    if (!codigo) return undefined
    let vigente = true
    const hasta = new Date().toISOString().slice(0, 10)
    obtenerMediciones(codigo, restarDias(hasta, DIAS_PEDIDOS), hasta)
      .then((r) => {
        if (vigente) {
          setError(null)
          setDatos(r)
        }
      })
      .catch((causa) => {
        if (vigente) setError(causa.message)
      })
    return () => {
      vigente = false
    }
  }, [codigo])

  const comparacion = useMemo(() => {
    if (!normales || !datos) return null
    return compararPeriodo({
      filas: datos.filas,
      normales,
      variable,
      periodo,
      hoy: new Date(),
      minimoAnios: normales.minimo_anios_omm,
      codigoDistrito: codigo,
    })
  }, [normales, datos, variable, periodo, codigo])

  if (error) {
    return (
      <section className="normales" aria-label="Comparacion contra la normal historica">
        <p className="normal-ausencia">No se pudo leer la serie de {nombre}: {error}</p>
      </section>
    )
  }

  if (!normales) {
    return (
      <section className="normales" aria-label="Comparacion contra la normal historica">
        <p className="normal-ausencia">
          La normal historica no esta disponible. Se genera con{' '}
          <code>python frontend/herramientas/generar_normales.py</code>.
        </p>
      </section>
    )
  }

  const info = normales.variables[variable]

  return (
    <section className="normales" aria-label="Comparacion contra la normal historica">
      <h3 className="normal-titulo">Contra lo normal</h3>

      <div className="normal-controles">
        <label className="normal-control">
          <span>Variable</span>
          <select value={variable} onChange={(e) => setVariable(e.target.value)}>
            {Object.entries(normales.variables).map(([id, v]) => (
              <option key={id} value={id}>
                {v.etiqueta}
              </option>
            ))}
          </select>
        </label>
        <label className="normal-control">
          <span>Periodo</span>
          <select value={periodo} onChange={(e) => setPeriodo(e.target.value)}>
            {PERIODOS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nombre}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* LA COMPARACION SOLO SE DIBUJA CON DATO REAL, Y LA SENAL ES `modo`, NO EL ORIGEN.
          La primera version miraba solo `origen === 'estatico'`. **Estaba mal, y se
          vio levantando la API de verdad**: respondio 200 con
          `modo: "simulado", base_datos_conectada: false`, porque
          `GEOGUARDIAN_REPOSITORIO` vale `simulado` por omision en
          `docker-compose.yml` -decision declarada ahi: al repositorio contra
          PostgreSQL le faltan tablas para diez de sus dieciseis metodos-.
          O sea que el origen era `api` y el dato seguia siendo inventado: el panel
          habria puesto un porcentaje entre un numero simulado y treinta anios
          medidos, con toda la cara de una medicion.
          Las dos condiciones son distintas y la pantalla las dice distinto, igual
          que hace `AvisoModoSimulado` con su tabla de modo por origen. */}
      {datos?.origen === ORIGEN_ESTATICO ? (
        <p className="normal-ausencia" role="status">
          <strong>No hay con que comparar ahora mismo.</strong> La API no responde y la serie del
          distrito viene del respaldo estatico, que son datos simulados. La normal de abajo si es
          real, pero contrastar un dato simulado contra treinta anios medidos daria un porcentaje
          que no significa nada.
        </p>
      ) : salud?.modo === 'simulado' ? (
        <p className="normal-ausencia" role="status">
          <strong>No hay con que comparar: la API sirve datos de demostracion.</strong> Responde,
          pero declara <code>modo: simulado</code>, asi que su serie no es una observacion. La
          normal de abajo si sale de treinta anios medidos; comparar una contra la otra daria una
          cifra con apariencia de medicion.
        </p>
      ) : !comparacion ? (
        <p className="normal-ausencia">Cargando la serie de {nombre}...</p>
      ) : comparacion.motivo ? (
        <p className="normal-ausencia" role="status">
          <strong>Sin comparacion para este periodo.</strong> {comparacion.detalle}. No se dibuja un
          cero: un cero se leeria como «estuvo en lo normal», que es lo contrario de «no se sabe».
        </p>
      ) : (
        <>
          <Comparacion c={comparacion} />
          {/* CA-2. Una normal de pocos anios se marca, no se esconde. */}
          {comparacion.normalDebil && (
            <p className="normal-aviso">
              La normal de alguno de estos meses sale de {comparacion.anios} anios, menos de los{' '}
              {normales.minimo_anios_omm} que recomienda la OMM. El numero de arriba vale menos de
              lo que aparenta.
            </p>
          )}
        </>
      )}

      {/* CA-1. El periodo y la cobertura, en pantalla y no en una nota al pie:
          son lo que hace interpretable la cifra de arriba. */}
      <p className="normal-procedencia">
        Normal {normales.periodo.desde.slice(0, 4)}–{normales.periodo.hasta.slice(0, 4)} de{' '}
        {info.etiqueta.toLowerCase()}, {comparacion?.anios ?? '—'} anios con dato en los meses
        comparados.{' '}
        {info.resolucion === 'canton' ? (
          <>
            <strong>Es un valor del canton, no de {nombre}</strong>: la fuente tiene una sola celda
            sobre Tilaran para esta variable y los ocho distritos comparten el mismo numero.
          </>
        ) : (
          <>Calculada para {nombre}.</>
        )}
      </p>
    </section>
  )
}
