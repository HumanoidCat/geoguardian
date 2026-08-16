import { useEffect, useMemo, useState } from 'react'
import AvisoModoSimulado from './componentes/AvisoModoSimulado'
import MapaCanton from './componentes/MapaCanton'
import PanelDistrito from './componentes/PanelDistrito'
import { obtenerDistritos, obtenerSalud } from './datos/cliente'

export default function App() {
  const [salud, setSalud] = useState(null)
  const [coleccion, setColeccion] = useState(null)
  const [seleccionado, setSeleccionado] = useState(null)
  const [error, setError] = useState(null)
  const [cargando, setCargando] = useState(true)

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

  const distritoSeleccionado = useMemo(() => {
    if (!coleccion || !seleccionado) return null
    return coleccion.features.find((r) => r.properties.codigo === seleccionado)?.properties ?? null
  }, [coleccion, seleccionado])

  return (
    <div className="aplicacion">
      <header className="cabecera">
        <div>
          <h1>GeoGuardian</h1>
          <p className="subtitulo">
            Riesgo de sequia e incendio forestal por distrito · Canton de Tilaran
          </p>
        </div>
      </header>

      <AvisoModoSimulado salud={salud} />

      {error && (
        <div className="error" role="alert">
          <strong>No se pudieron cargar los datos.</strong>
          <p>{error}</p>
        </div>
      )}

      {cargando && !error && (
        <div className="cargando-pantalla">
          <div className="pulso-cargando barra-carga" />
          <p>Cargando los distritos del canton...</p>
        </div>
      )}

      {!cargando && !error && (
        <main className="contenido">
          <MapaCanton
            coleccion={coleccion}
            seleccionado={seleccionado}
            alSeleccionar={setSeleccionado}
          />
          <PanelDistrito distrito={distritoSeleccionado} />
        </main>
      )}
    </div>
  )
}
