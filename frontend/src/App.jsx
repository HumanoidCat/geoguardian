import { useCallback, useEffect, useMemo, useState } from 'react'
import AvisoModoSimulado from './componentes/AvisoModoSimulado'
import LeyendaRiesgo from './componentes/LeyendaRiesgo'
import MapaCanton from './componentes/MapaCanton'
import PanelDistrito from './componentes/PanelDistrito'
import SelectorEvento from './componentes/SelectorEvento'
import { obtenerDistritos, obtenerRiesgos, obtenerSalud } from './datos/cliente'
import { nombreDeEvento } from './datos/eventos'

const EVENTO_INICIAL = 'sequia'

export default function App() {
  const [salud, setSalud] = useState(null)
  const [coleccion, setColeccion] = useState(null)
  const [evento, setEvento] = useState(EVENTO_INICIAL)
  const [paqueteRiesgos, setPaqueteRiesgos] = useState(null)
  const [seleccionado, setSeleccionado] = useState(null)
  const [error, setError] = useState(null)
  const [cargando, setCargando] = useState(true)
  const [cargandoRiesgos, setCargandoRiesgos] = useState(true)

  // Carga inicial: lo que no cambia al cambiar de evento.
  useEffect(() => {
    let vigente = true

    async function cargar() {
      try {
        const [estado, distritos] = await Promise.all([obtenerSalud(), obtenerDistritos()])
        if (!vigente) return
        setSalud(estado)
        setColeccion(distritos)
      } catch (causa) {
        if (!vigente) return
        // El error se muestra tal cual. Una pantalla que falla en silencio y se
        // queda vacia hace creer que no hay datos, cuando lo que hubo fue un
        // fallo.
        setError(causa.message)
      } finally {
        if (vigente) setCargando(false)
      }
    }

    cargar()
    return () => {
      vigente = false
    }
  }, [])

  // Riesgos del evento seleccionado. Se recarga cada vez que cambia el evento.
  //
  // El estado de carga NO se enciende aca: se enciende en el manejador del
  // selector y arranca en true. Encenderlo dentro del efecto provoca un render
  // en cascada, y el linter lo rechaza con razon.
  useEffect(() => {
    let vigente = true

    async function cargar() {
      try {
        const paquete = await obtenerRiesgos(evento)
        if (!vigente) return
        setPaqueteRiesgos(paquete)
      } catch (causa) {
        if (!vigente) return
        // Si fallan los riesgos, el mapa sigue en pie con los distritos sin
        // estimacion. Es mejor que una pantalla en blanco: se ve el canton y se
        // ve que falta el dato.
        setPaqueteRiesgos(null)
        setError(causa.message)
      } finally {
        if (vigente) setCargandoRiesgos(false)
      }
    }

    cargar()
    return () => {
      vigente = false
    }
  }, [evento])

  const cambiarEvento = useCallback((nuevo) => {
    setCargandoRiesgos(true)
    setEvento(nuevo)
  }, [])

  const distritoSeleccionado = useMemo(() => {
    if (!coleccion || !seleccionado) return null
    return coleccion.features.find((r) => r.properties.codigo === seleccionado)?.properties ?? null
  }, [coleccion, seleccionado])

  const nombreEvento = nombreDeEvento(evento)
  const riesgos = paqueteRiesgos?.riesgos ?? null

  return (
    <div className="aplicacion">
      <header className="cabecera">
        <div>
          <h1>GeoGuardian</h1>
          <p className="subtitulo">
            Riesgo de lluvia intensa, sequia e incendio forestal por distrito ·
            Canton de Tilaran
          </p>
        </div>
      </header>

      <AvisoModoSimulado salud={salud} />

      {error && (
        <div className="error" role="alert">
          <strong>No se pudieron cargar todos los datos.</strong>
          <p>{error}</p>
        </div>
      )}

      {cargando && !error && (
        <div className="cargando-pantalla">
          <div className="pulso-cargando barra-carga" />
          <p>Cargando los distritos del canton...</p>
        </div>
      )}

      {!cargando && coleccion && (
        <main className="contenido">
          <div className="columna-mapa">
            <SelectorEvento seleccionado={evento} alCambiar={cambiarEvento} />
            <MapaCanton
              coleccion={coleccion}
              riesgos={riesgos}
              seleccionado={seleccionado}
              alSeleccionar={setSeleccionado}
            />
          </div>

          <div className="columna-panel">
            {cargandoRiesgos ? (
              <div className="leyenda">
                <div className="pulso-cargando barra-carga" />
                <p className="leyenda-aviso">Cargando los niveles de riesgo...</p>
              </div>
            ) : (
              <LeyendaRiesgo
                nombreEvento={nombreEvento}
                riesgos={riesgos}
                simulado={paqueteRiesgos?.simulado}
              />
            )}

            <PanelDistrito
              distrito={distritoSeleccionado}
              riesgo={seleccionado ? riesgos?.[seleccionado] : null}
              nombreEvento={nombreEvento}
            />
          </div>
        </main>
      )}
    </div>
  )
}
