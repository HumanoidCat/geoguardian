import { useCallback, useEffect, useMemo, useState } from 'react'
import AvisoModoSimulado from './componentes/AvisoModoSimulado'
import ControlCapas from './componentes/ControlCapas'
import LeyendaRiesgo from './componentes/LeyendaRiesgo'
import MapaCanton from './componentes/MapaCanton'
import PanelDistrito from './componentes/PanelDistrito'
import SelectorEvento from './componentes/SelectorEvento'
import { CAPAS_INICIALES, CAPA_BASE_INICIAL, EXPONENTE_IDW_INICIAL } from './datos/capasBase'
import {
  ORIGEN_API,
  fechaDeHoy,
  obtenerDistritos,
  obtenerIndices,
  obtenerRiesgos,
  obtenerRiesgosDeVariosEventos,
  obtenerSalud,
} from './datos/cliente'
import SelectorFecha from './componentes/SelectorFecha'
import { puntoEnSuperficie } from './datos/geometria'
import { IDS_EVENTOS, nombreDeEvento } from './datos/eventos'
import TableroSemaforo from './componentes/TableroSemaforo'
import { centroidesDeColeccion } from './datos/interpolacion'
import LeyendaMapaCalor from './componentes/LeyendaMapaCalor'
import LeyendaIndice from './componentes/LeyendaIndice'

const EVENTO_INICIAL = 'sequia'

// Mismo valor que --riesgo-opacidad en tokens.css. Se repite aca porque el
// estado de React necesita un numero inicial; el CSS sigue siendo el dueno del
// valor por defecto cuando el deslizador no se ha tocado.
// Una opacidad **por capa**, no una compartida.
//
// Hasta H5.5 habia una sola capa con deslizador y alcanzaba con un numero. Al
// entrar los indices se reuso ese mismo numero y los tres deslizadores pasaron a
// ser el mismo valor con tres dibujos: mover el del NDVI movia el del riesgo.
// Se vio probandolo en el visor, no leyendo el codigo.
const OPACIDAD_INICIAL = {
  riesgo: 0.85,
  ndvi: 0.85,
  ndwi: 0.85,
}

export default function App() {
  const [salud, setSalud] = useState(null)
  const [coleccion, setColeccion] = useState(null)
  const [evento, setEvento] = useState(EVENTO_INICIAL)
  const [paqueteRiesgos, setPaqueteRiesgos] = useState(null)
  const [seleccionado, setSeleccionado] = useState(null)
  const [error, setError] = useState(null)
  const [cargando, setCargando] = useState(true)
  const [cargandoRiesgos, setCargandoRiesgos] = useState(true)

  const [capaBase, setCapaBase] = useState(CAPA_BASE_INICIAL)
  const [superpuestas, setSuperpuestas] = useState(CAPAS_INICIALES)
  const [opacidad, setOpacidad] = useState(OPACIDAD_INICIAL)

  const cambiarOpacidad = useCallback((id, valor) => {
    setOpacidad((previas) => ({ ...previas, [id]: valor }))
  }, [])
  const [exponente, setExponente] = useState(EXPONENTE_IDW_INICIAL)
  const [paquetesTodos, setPaquetesTodos] = useState(null)

  // La fecha que se PIDE. No es la misma que la que trae el paquete: contra el
  // respaldo estatico solo existe una, y ese origen ignora lo que se le pida.
  // Confundir las dos seria rotular un dato con una fecha que no es la suya.
  const [fecha, setFecha] = useState(fechaDeHoy)

  // El punto exacto donde se hizo clic, **junto al distrito al que pertenece**.
  //
  // El codigo viaja con el punto a proposito. La primera version guardaba solo
  // las coordenadas y se rompio en cuanto la seleccion cambio por otra via: al
  // elegir un distrito desde el semaforo, la ficha seguia mostrando el clic
  // anterior, que estaba en OTRO distrito. La pantalla afirmaba "donde hiciste
  // clic" señalando un lugar donde nadie hizo clic.
  //
  // Se podria limpiar el punto en cada manejador que cambia la seleccion, pero
  // eso depende de que alguien se acuerde cada vez que se agregue un camino
  // nuevo. Con el codigo adentro, la comprobacion es una sola y no se puede
  // olvidar: si no corresponde al distrito de la ficha, no se muestra.
  const [puntoClic, setPuntoClic] = useState(null)

  // Los indices de H5.5. Se cargan una sola vez: no dependen del evento ni de la
  // fecha del selector, porque son de la fecha de la escena de satelite.
  const [indices, setIndices] = useState(null)

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

  // Los indices, aparte. Si no estan, la capa no se ofrece y ya: no es un error
  // y no tiene que ensuciar el estado general con un mensaje rojo.
  useEffect(() => {
    let vigente = true
    obtenerIndices().then((paquete) => {
      if (vigente) setIndices(paquete)
    })
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
        const paquete = await obtenerRiesgos(evento, fecha)
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
  }, [evento, fecha])

  // Los tres eventos a la vez, para el semaforo de H7.1. Es una carga aparte
  // porque responde otra pregunta: el mapa muestra donde esta el riesgo de un
  // evento, y el semaforo cual de los tres hay que atender primero.
  //
  // Si falla, el semaforo simplemente no se dibuja. No se propaga al error
  // general: el mapa sigue siendo util sin la tabla, y una pantalla en rojo por
  // una parte accesoria seria peor que la ausencia de esa parte.
  useEffect(() => {
    let vigente = true

    obtenerRiesgosDeVariosEventos(IDS_EVENTOS, fecha)
      .then((paquetes) => {
        if (vigente) setPaquetesTodos(paquetes)
      })
      .catch(() => {
        if (vigente) setPaquetesTodos(null)
      })

    return () => {
      vigente = false
    }
  }, [fecha])

  const cambiarEvento = useCallback((nuevo) => {
    setCargandoRiesgos(true)
    setEvento(nuevo)
  }, [])

  // El estado de carga se enciende aca y no dentro del efecto, por lo mismo que
  // en `cambiarEvento`: encenderlo en el efecto provoca un render en cascada y el
  // linter lo rechaza con razon.
  const cambiarFecha = useCallback((nueva) => {
    setCargandoRiesgos(true)
    setFecha(nueva)
  }, [])

  // Desde el semaforo: seleccionar un distrito lleva el mapa a ese evento y a ese
  // distrito. Sin eso la tabla seria un tablero muerto, y la relacion entre las
  // dos vistas quedaria a cargo de la memoria de quien mira.
  const seleccionarDesdeTablero = useCallback(
    (codigo, eventoDeLaCelda) => {
      setSeleccionado(codigo)
      if (eventoDeLaCelda !== evento) cambiarEvento(eventoDeLaCelda)
    },
    [evento, cambiarEvento],
  )

  const alternarSuperpuesta = useCallback((id) => {
    setSuperpuestas((previas) => ({ ...previas, [id]: !previas[id] }))
  }, [])

  // Desde el mapa llega el codigo y el punto exacto del clic. Con el teclado el
  // punto es null: quien navega con Enter no senalo ningun lugar del distrito, y
  // poner el centro seria inventar un dato que nadie indico.
  const seleccionarDesdeMapa = useCallback((codigo, punto) => {
    setSeleccionado(codigo)
    setPuntoClic(punto ? { codigo, longitud: punto.lng, latitud: punto.lat } : null)
  }, [])

  const rasgoSeleccionado = useMemo(() => {
    if (!coleccion || !seleccionado) return null
    return coleccion.features.find((r) => r.properties.codigo === seleccionado) ?? null
  }, [coleccion, seleccionado])

  const ubicacionDelDistrito = useMemo(
    () => puntoEnSuperficie(rasgoSeleccionado?.geometry),
    [rasgoSeleccionado],
  )

  const distritoSeleccionado = rasgoSeleccionado?.properties ?? null

  const centroides = useMemo(() => centroidesDeColeccion(coleccion), [coleccion])

  const distritos = useMemo(
    () => coleccion?.features.map((rasgo) => rasgo.properties) ?? [],
    [coleccion],
  )

  const nombreEvento = nombreDeEvento(evento)
  const riesgos = paqueteRiesgos?.riesgos ?? null

  // El selector se bloquea cuando los datos NO vienen de la API, porque el
  // respaldo estatico tiene una sola fecha y no puede servir otra.
  //
  // Se decide por `origen` y no por `modo`: `modo` dice que son los datos
  // -simulados o reales- y `origen` por donde llegaron. Lo que limita aca es el
  // camino, no el contenido. Es la misma separacion de H6.6.
  const sinEleccionDeFecha = salud !== null && salud.origen !== ORIGEN_API

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
            <SelectorFecha
              fecha={fecha}
              alCambiar={cambiarFecha}
              bloqueado={sinEleccionDeFecha}
              fechaDelRespaldo={paqueteRiesgos?.fecha}
            />
            <MapaCanton
              coleccion={coleccion}
              riesgos={riesgos}
              seleccionado={seleccionado}
              alSeleccionar={seleccionarDesdeMapa}
              capaBase={capaBase}
              superpuestas={superpuestas}
              opacidad={opacidad}
              exponente={exponente}
              centroides={centroides}
              indices={indices}
            />
          </div>

          <div className="columna-panel">
            <ControlCapas
              capaBase={capaBase}
              alCambiarCapaBase={setCapaBase}
              superpuestas={superpuestas}
              alAlternarSuperpuesta={alternarSuperpuesta}
              opacidad={opacidad}
              alCambiarOpacidad={cambiarOpacidad}
              exponente={exponente}
              alCambiarExponente={setExponente}
            />

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
                fecha={paqueteRiesgos?.fecha}
              />
            )}

            {superpuestas.mapaCalor && !cargandoRiesgos && (
              <LeyendaMapaCalor centroides={centroides} riesgos={riesgos} exponente={exponente} />
            )}

            {superpuestas.ndvi && <LeyendaIndice id="ndvi" paquete={indices} />}
            {superpuestas.ndwi && <LeyendaIndice id="ndwi" paquete={indices} />}

            <PanelDistrito
              distrito={distritoSeleccionado}
              ubicacion={ubicacionDelDistrito}
              puntoClic={puntoClic?.codigo === seleccionado ? puntoClic : null}
              riesgo={seleccionado ? riesgos?.[seleccionado] : null}
              nombreEvento={nombreEvento}
            />
          </div>
        </main>
      )}

      {!cargando && coleccion && paquetesTodos && (
        <TableroSemaforo
          distritos={distritos}
          paquetes={paquetesTodos}
          seleccionado={seleccionado}
          alSeleccionar={seleccionarDesdeTablero}
        />
      )}
    </div>
  )
}
