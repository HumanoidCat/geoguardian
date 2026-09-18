import { useEffect, useMemo, useState } from 'react'
import { CirculoNivel, PictogramaEvento } from './Pictogramas'
import {
  NIVELES,
  SEQUIA_MEDIDA,
  TARJETAS,
  categoriaDeSequia,
  contenidoDeTarjeta,
  fechaEnPalabras,
  indiceEnPalabras,
} from '../datos/palabras'
import { obtenerIndiceDeSequia, obtenerMediciones } from '../datos/cliente'

/**
 * «Hoy en tu distrito»: la primera pantalla, para quien vive en el canton.
 *
 * Historia H14.2. Rubrica de Computacion Grafica, CG-1 y CG-4.
 *
 * QUE CAMBIA Y POR QUE
 *
 * Hasta ahora la primera pantalla era el mapa: coropleta, semaforo, leyenda y
 * selector de fecha. Eso le sirve al Comite Municipal de Emergencias y a quien
 * evalua el proyecto. No le sirve a la persona que vive en el distrito, que es
 * de quien es el producto. El mapa no desaparece: baja un nivel, entero, detras
 * de «ver el canton completo».
 *
 * LO QUE ESTA PANTALLA NO HACE, A PROPOSITO
 *
 * No trae el pronostico a siete dias, no cuenta focos de calor, no comparte por
 * WhatsApp, no imprime el cartel y no recibe reportes. Son historias aparte y
 * cada una necesita algo que hoy no existe. Prometerlas aca las volveria mentira.
 *
 * LAS DOS FECHAS, QUE NO SON LA MISMA
 *
 * `paquete.fecha` es la fecha **de la estimacion**. El ultimo dia con lluvia
 * medida es otra cosa, y con la latencia de la fuente pueden estar a mas de un
 * mes de distancia. La pantalla muestra las dos por separado y **no dice que la
 * estimacion uso datos hasta ese dia**, porque eso no se puede comprobar desde
 * aca: seria afirmar una relacion que nadie midio. Dos hechos ciertos valen mas
 * que uno comodo.
 *
 * LA TARJETA DE SEQUIA MIDE, NO ESTIMA (H14.5)
 *
 * Las otras dos tarjetas dicen un nivel estimado. La de sequia dice el indice
 * de lluvia de los ultimos seis meses, que es un hecho que ya paso, con su
 * categoria en palabras y la fecha del dato al lado. No usa el circulo de nivel
 * ni la rampa de color: usarlos diria sin palabras que es una estimacion, y
 * D-34 sigue en pie. Cuando no hay indice -respaldo estatico, dato simulado,
 * serie incompleta- dibuja la ausencia y dice por que (D-07, CA-9).
 */

const CLAVE_RECORDADO = 'geoguardian.distrito'

/** Cuantos dias hacia atras se busca el ultimo dato de lluvia. */
const DIAS_HACIA_ATRAS = 120

function haceDias(iso, dias) {
  const d = new Date(`${iso}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() - dias)
  return d.toISOString().slice(0, 10)
}

function leerRecordado() {
  try {
    return window.localStorage.getItem(CLAVE_RECORDADO)
  } catch {
    // Navegador con el almacenamiento bloqueado. Se pide elegir de nuevo, que es
    // molesto pero honesto; tumbar la pantalla por esto seria peor.
    return null
  }
}

function guardarRecordado(codigo) {
  try {
    window.localStorage.setItem(CLAVE_RECORDADO, codigo)
  } catch {
    // Sin memoria entre visitas. No cambia nada de lo que se muestra hoy.
  }
}

/**
 * Ultimo dia con lluvia medida del distrito, o `null` si no se pudo saber.
 *
 * Sale de una segunda llamada, porque el paquete de riesgos no trae este dato.
 * Es una sola llamada y no ocho: esta pantalla muestra un distrito a la vez.
 */
function useUltimoDatoDeLluvia(codigo, hasta) {
  // `para` guarda de que distrito es la respuesta que hay. Asi «esta cargando»
  // se deduce comparando, en vez de escribirse al entrar al efecto: escribirlo
  // ahi provoca un render de mas y la regla de React lo prohibe.
  const [estado, setEstado] = useState({ para: null, fecha: null })

  useEffect(() => {
    if (!codigo || !hasta) return undefined
    let vigente = true
    obtenerMediciones(codigo, haceDias(hasta, DIAS_HACIA_ATRAS), hasta)
      .then((serie) => {
        if (!vigente) return
        // `obtenerMediciones` devuelve { filas, ventana, origen }, y las filas
        // conservan los dias sin medir con la variable en null: no se filtran,
        // porque quitarlos dibujaria una continuidad que nadie observo. Aca eso
        // importa al reves: el ultimo dia CON valor es justo lo que se busca.
        let ultima = null
        for (const fila of serie?.filas ?? []) {
          if (fila.precipitacion_mm != null && fila.fecha) ultima = fila.fecha
        }
        setEstado({ para: codigo, fecha: ultima })
      })
      .catch(() => {
        // Que no se sepa la fecha del dato no puede tumbar la pantalla. La
        // tarjeta lo dira con palabras.
        if (vigente) setEstado({ para: codigo, fecha: null })
      })
    return () => {
      vigente = false
    }
  }, [codigo, hasta])

  return { cargando: estado.para !== codigo, fecha: estado.para === codigo ? estado.fecha : null }
}

/**
 * El ultimo indice de sequia medido del distrito, o por que no lo hay.
 *
 * Misma forma que `useUltimoDatoDeLluvia`: `para` dice de que distrito es la
 * respuesta, y «cargando» se deduce comparando. Un fallo de red no tumba la
 * pantalla: la tarjeta dibuja la ausencia con el motivo `sin_dato`.
 */
function useIndiceDeSequia(codigo) {
  const [estado, setEstado] = useState({ para: null, indice: null })

  useEffect(() => {
    if (!codigo) return undefined
    let vigente = true
    obtenerIndiceDeSequia(codigo)
      .then((indice) => {
        if (vigente) setEstado({ para: codigo, indice })
      })
      .catch(() => {
        if (vigente) setEstado({ para: codigo, indice: { valor: null, fecha: null, motivo: 'sin_dato' } })
      })
    return () => {
      vigente = false
    }
  }, [codigo])

  return {
    cargando: estado.para !== codigo,
    indice: estado.para === codigo ? estado.indice : null,
  }
}

/**
 * El cuerpo de la tarjeta de sequia: un numero medido, no un nivel (H14.5).
 *
 * Sin `CirculoNivel` y sin clase `nivel-*` a proposito (CA-2): el numero va en
 * la tipografia de la tarjeta y la categoria en palabras. La linea de
 * `esMedicion` esta aca, en la tarjeta, y no en un desplegable (CA-1).
 */
function CuerpoSequia({ tarjeta, indice, cargando, nombreDistrito }) {
  if (cargando) {
    return (
      <p className="tarjeta-hoy-nivel sin-nivel" role="status">
        <strong>Buscando la lluvia de los ultimos meses...</strong>
      </p>
    )
  }

  const categoria = categoriaDeSequia(indice?.valor)
  if (!categoria) {
    const motivo = SEQUIA_MEDIDA.sinIndice[indice?.motivo] ?? tarjeta.ausencia
    return (
      <>
        <p className="tarjeta-hoy-nivel sin-nivel">
          <CirculoNivel nivel={null} />
          <strong>Sin indice por ahora</strong>
        </p>
        <p className="tarjeta-hoy-frase">{motivo}</p>
        <p className="tarjeta-hoy-nota">{tarjeta.ausencia}</p>
      </>
    )
  }

  return (
    <>
      <p className="tarjeta-hoy-medida">
        <span className="tarjeta-hoy-medida-que">{SEQUIA_MEDIDA.titulo}</span>
        <strong className="tarjeta-hoy-indice">{indiceEnPalabras(indice.valor)}</strong>
        <span className="tarjeta-hoy-categoria">{categoria.palabra}</span>
      </p>
      <p className="tarjeta-hoy-frase">{categoria.frase(nombreDistrito)}</p>
      <p className="tarjeta-hoy-medicion">
        {SEQUIA_MEDIDA.esMedicion} Lluvia medida hasta el{' '}
        <strong>{fechaEnPalabras(indice.fecha)}</strong>.
      </p>
    </>
  )
}

function Tarjeta({
  tarjeta,
  nivel,
  nombreDistrito,
  fechaEstimacion,
  fechaDato,
  cargandoDato,
  indice,
  cargandoIndice,
}) {
  const contenido = contenidoDeTarjeta(tarjeta, nivel, nombreDistrito)
  const mide = tarjeta.id === 'sequia'

  return (
    <article className="tarjeta-hoy">
      <div className="tarjeta-hoy-icono">
        <PictogramaEvento id={tarjeta.id} className="pictograma" />
      </div>

      <div className="tarjeta-hoy-cuerpo">
        <h3 className="tarjeta-hoy-evento">{tarjeta.titulo}</h3>

        {mide ? (
          <CuerpoSequia
            tarjeta={tarjeta}
            indice={indice}
            cargando={cargandoIndice}
            nombreDistrito={nombreDistrito}
          />
        ) : contenido ? (
          <>
            <p className={`tarjeta-hoy-nivel nivel-${nivel}`}>
              <CirculoNivel nivel={nivel} />
              <strong>{contenido.palabra}</strong>
              <span className="tarjeta-hoy-tecnico">{contenido.tecnico}</span>
            </p>
            <p className="tarjeta-hoy-frase">{contenido.frase}</p>
            <ul className="tarjeta-hoy-hacer">
              {contenido.hacer.map((accion) => (
                <li key={accion}>{accion}</li>
              ))}
            </ul>
          </>
        ) : (
          <>
            <p className="tarjeta-hoy-nivel sin-nivel">
              <CirculoNivel nivel={null} />
              <strong>No la estimamos</strong>
            </p>
            <p className="tarjeta-hoy-frase">{tarjeta.ausencia}</p>
          </>
        )}

        {tarjeta.nota && <p className="tarjeta-hoy-nota">{tarjeta.nota}</p>}

        {/* La sequia no tiene fecha de estimacion porque no se estima: su fecha
            es la del dato y ya esta al lado del numero (CA-3). Escribir aca
            «Estimacion del ...» contradiria la tarjeta entera. */}
        {mide ? (
          <p className="tarjeta-hoy-dato">
            La fuente entrega la lluvia de cada mes con semanas de atraso, por eso el ultimo mes
            medido no es el mes en curso.
          </p>
        ) : (
          <p className="tarjeta-hoy-dato">
            {fechaEstimacion
              ? `Estimacion del ${fechaEnPalabras(fechaEstimacion)}.`
              : 'Sin fecha de estimacion.'}{' '}
            {tarjeta.id === 'lluvia_intensa' &&
              (cargandoDato
                ? 'Buscando el ultimo dato de lluvia...'
                : fechaDato
                  ? `El ultimo dato de lluvia de ${nombreDistrito} es del ${fechaEnPalabras(fechaDato)}.`
                  : `No pudimos saber de cuando es el ultimo dato de lluvia de ${nombreDistrito}.`)}
            {tarjeta.id === 'incendio' && 'Mira los focos de los siete dias anteriores.'}
          </p>
        )}

        {/* La salida a lo oficial acompana a un nivel «cuidado» de verdad. Si la
            tarjeta esta diciendo que NO estima -la sequia, siempre-, un aviso de
            emergencia al pie contradiria justo lo que se acaba de decir. */}
        {contenido && nivel === 'alto' && (
          <div className="tarjeta-hoy-oficial">
            {/* El 9-1-1 es un boton y no un enlace dentro de una frase. En una
                tarjeta de «cuidado» es lo mas importante que hay en pantalla, y
                medido como enlace en linea daba 19 px de alto: en un telefono,
                con prisa, eso se falla. */}
            <a className="boton-emergencia" href="tel:911">
              Llamar al 9-1-1
            </a>
            <a
              className="enlace-oficial"
              href="https://www.cne.go.cr/"
              target="_blank"
              rel="noreferrer"
            >
              Alertas oficiales de la Comision Nacional de Emergencias
            </a>
          </div>
        )}
      </div>
    </article>
  )
}

export default function HoyEnTuDistrito({ distritos, paquetes, seleccionado, alSeleccionar, alVerMapa }) {
  // Se recuerda la eleccion, pero NO se adivina: sin eleccion previa la pantalla
  // pide elegir. Un aviso del distrito equivocado es peor que ninguno.
  useEffect(() => {
    if (seleccionado) return
    const recordado = leerRecordado()
    if (recordado && distritos.some((d) => d.codigo === recordado)) alSeleccionar(recordado)
  }, [seleccionado, distritos, alSeleccionar])

  const distrito = useMemo(
    () => distritos.find((d) => d.codigo === seleccionado) ?? null,
    [distritos, seleccionado],
  )

  const fechaEstimacion = paquetes?.lluvia_intensa?.fecha ?? null
  const { cargando: cargandoDato, fecha: fechaDato } = useUltimoDatoDeLluvia(
    seleccionado,
    fechaEstimacion,
  )
  const { cargando: cargandoIndice, indice } = useIndiceDeSequia(seleccionado)

  const elegir = (codigo) => {
    alSeleccionar(codigo)
    if (codigo) guardarRecordado(codigo)
  }

  return (
    <div className="hoy">
      {/* El papel va de borde a borde y el contenido va centrado adentro. Sin
          esta division el fondo calido quedaba como una franja con blanco a los
          lados, que se lee como un error de maquetado y no como un fondo. */}
      <div className="hoy-interior">
      <section className="hoy-selector">
        <label htmlFor="hoy-distrito">Tu distrito</label>
        <select
          id="hoy-distrito"
          value={seleccionado ?? ''}
          onChange={(evento) => elegir(evento.target.value)}
        >
          <option value="">Elegi tu distrito</option>
          {distritos.map((d) => (
            <option key={d.codigo} value={d.codigo}>
              {d.nombre}
            </option>
          ))}
        </select>
      </section>

      {!distrito ? (
        <p className="hoy-pide-distrito">
          Elegi tu distrito arriba para ver que viene esta semana. No lo adivinamos: un aviso del
          distrito equivocado es peor que ninguno.
        </p>
      ) : (
        <div className="hoy-tarjetas">
          {TARJETAS.map((tarjeta) => (
            <Tarjeta
              key={tarjeta.id}
              tarjeta={tarjeta}
              nivel={paquetes?.[tarjeta.id]?.riesgos?.[seleccionado]?.nivel ?? null}
              nombreDistrito={distrito.nombre}
              fechaEstimacion={paquetes?.[tarjeta.id]?.fecha ?? null}
              fechaDato={fechaDato}
              cargandoDato={cargandoDato}
              indice={indice}
              cargandoIndice={cargandoIndice}
            />
          ))}
        </div>
      )}

      <div className="hoy-acciones">
        <button type="button" className="boton-mapa" onClick={alVerMapa}>
          Ver el canton completo
        </button>
      </div>

      <section className="hoy-significado">
        <h2>Que significa cada palabra</h2>
        <dl>
          {Object.entries(NIVELES).map(([nivel, datos]) => (
            <div key={nivel}>
              <dt>
                <CirculoNivel nivel={nivel} />
                <strong>{datos.palabra}</strong> <span>{datos.tecnico}</span>
              </dt>
              <dd>{datos.significado}</dd>
            </div>
          ))}
        </dl>
      </section>

      <p className="hoy-oficial">
        GeoGuardian <strong>no emite alertas oficiales</strong>. Es una estimacion que complementa a
        la Comision Nacional de Emergencias, nunca la sustituye. Emergencias:{' '}
        <a className="enlace-oficial" href="tel:911">
          9-1-1
        </a>
        .
      </p>

      {/* Arranca cerrado: es donde viven las siglas, que no pueden estar en la
          primera pantalla. Que este a un clic no es esconderlo. */}
      <details className="hoy-de-donde">
        <summary>De donde sale esto</summary>
        <p>
          Lluvia medida por satelite (CHIRPS), clima de la NASA (POWER), focos de calor de satelite
          (FIRMS) y un modelo entrenado con treinta y cinco anos de datos de Tilaran y los eventos
          que de verdad pasaron en el canton. Cuando no sabemos, lo decimos.
        </p>
        {/* CA-6 de H14.5: por que la sequia no tiene nivel, con la cifra real
            de D-34, y que es el numero que si se muestra. */}
        <p>
          La sequia no tiene nivel porque no la estimamos: en treinta y cinco anos hubo trece
          sequias registradas en Tilaran, y para aprender de ellas el umbral que nos fijamos pide
          treinta. Lo que si mostramos es el indice de precipitacion estandarizado de seis meses
          (SPI-6), que se calcula con la lluvia que ya cayo: de -1 para abajo es seco, de -2 para
          abajo es sequia extrema. Es una medicion, no una estimacion.
        </p>
      </details>
      </div>
    </div>
  )
}
