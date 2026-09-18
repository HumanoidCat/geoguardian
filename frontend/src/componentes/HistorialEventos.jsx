import { useCallback, useMemo, useState } from 'react'
import { nombreDeEvento } from '../datos/eventos'
import {
  FILTROS_VACIOS,
  aCsv,
  describirFiltros,
  filtrar,
  hayFiltros,
  nombreDeArchivo,
} from '../datos/historial'

/**
 * El historial de eventos documentados del canton, filtrable y exportable.
 *
 * De donde sale el dato: `docs/investigacion/catalogo-eventos.csv`, el catalogo
 * de H4.3, escrito a mano desde fuentes documentales y validado contra los
 * contratos congelados. Llega a esta pantalla como archivo estatico, generado
 * por `frontend/herramientas/generar_historial.py`. No pasa por la API porque no
 * hay API que lo sirva: la tabla `analitico.evento` no existe.
 *
 * H7.3. Rubrica de Computacion Grafica, CG-2.
 */
export default function HistorialEventos({ historial, alVerMapa }) {
  const [filtros, setFiltros] = useState(FILTROS_VACIOS)

  const nombreDeDistrito = useCallback(
    (codigo) => historial?.distritos.find((d) => d.codigo === codigo)?.nombre ?? null,
    [historial],
  )

  const visibles = useMemo(
    () => filtrar(historial?.eventos ?? [], filtros),
    [historial, filtros],
  )

  const cambiar = useCallback((campo, valor) => {
    setFiltros((previos) => ({ ...previos, [campo]: valor }))
  }, [])

  // La descarga se arma en memoria y el objeto se libera enseguida.
  //
  // Sin `revokeObjectURL` cada exportacion deja un blob retenido mientras la
  // pestana viva. Con 46 filas no se nota, y precisamente por eso conviene que
  // este puesto: el dia que el catalogo crezca nadie va a volver a mirar esto.
  const exportar = useCallback(() => {
    const blob = new Blob([aCsv(visibles, nombreDeDistrito)], {
      type: 'text/csv;charset=utf-8',
    })
    const url = URL.createObjectURL(blob)
    const enlace = document.createElement('a')
    enlace.href = url
    enlace.download = nombreDeArchivo(filtros)
    enlace.click()
    URL.revokeObjectURL(url)
  }, [visibles, filtros, nombreDeDistrito])

  if (!historial) {
    return (
      <section className="historial" aria-label="Historial de eventos">
        <p className="historial-vacio">
          El historial no esta disponible. Se genera con{' '}
          <code>python frontend/herramientas/generar_historial.py</code>.
        </p>
      </section>
    )
  }

  const activos = describirFiltros(filtros, nombreDeDistrito, nombreDeEvento)

  return (
    <section className="historial" aria-label="Historial de eventos documentados">
      <header className="historial-cabecera">
        <div>
          <h2 className="historial-titulo">Eventos documentados</h2>
          <p className="historial-subtitulo">
            {historial.eventos.length} eventos entre {historial.rango.desde} y{' '}
            {historial.rango.hasta}, de fuentes documentales.
          </p>
        </div>
        <button type="button" className="boton-volver" onClick={alVerMapa}>
          Ver el mapa
        </button>
      </header>

      {/* El orden de tabulacion es el visual porque el orden del marcado es el
          visual: los cuatro controles van seguidos, antes de la tabla, y no hay
          ningun `tabIndex` que los reordene. Es el CA-8, y se consigue no
          haciendo nada raro en vez de arreglandolo despues. */}
      <div className="historial-filtros">
        <label className="historial-filtro">
          <span>Tipo de evento</span>
          <select value={filtros.tipo} onChange={(e) => cambiar('tipo', e.target.value)}>
            <option value="">Todos</option>
            {historial.tipos.map((tipo) => (
              <option key={tipo.id} value={tipo.id}>
                {nombreDeEvento(tipo.id) ?? tipo.id} ({tipo.eventos})
              </option>
            ))}
          </select>
        </label>

        {/* Los ocho distritos, tambien el que tiene cero.
            Cabeceras no tiene ningun evento documentado. Ofrecer solo los siete
            con datos haria que quien busca Cabeceras concluyera que el filtro
            esta roto; ofrecerlo con su cuenta dice la verdad antes del clic. */}
        <label className="historial-filtro">
          <span>Distrito</span>
          <select value={filtros.distrito} onChange={(e) => cambiar('distrito', e.target.value)}>
            <option value="">Todos</option>
            {historial.distritos.map((distrito) => (
              <option key={distrito.codigo} value={distrito.codigo}>
                {distrito.nombre} ({distrito.eventos})
              </option>
            ))}
          </select>
        </label>

        <label className="historial-filtro">
          <span>Desde</span>
          <input
            type="date"
            value={filtros.desde}
            min={historial.rango.desde}
            max={historial.rango.hasta}
            onChange={(e) => cambiar('desde', e.target.value)}
          />
        </label>

        <label className="historial-filtro">
          <span>Hasta</span>
          <input
            type="date"
            value={filtros.hasta}
            min={historial.rango.desde}
            max={historial.rango.hasta}
            onChange={(e) => cambiar('hasta', e.target.value)}
          />
        </label>

        <div className="historial-acciones">
          <button
            type="button"
            className="boton-volver"
            onClick={() => setFiltros(FILTROS_VACIOS)}
            disabled={!hayFiltros(filtros)}
          >
            Quitar filtros
          </button>
          {/* Exporta `visibles`, que es lo filtrado. Si exportara
              `historial.eventos` el filtro seria decorativo. CA-5. */}
          <button
            type="button"
            className="boton-ir-a-hoy"
            onClick={exportar}
            disabled={visibles.length === 0}
          >
            Exportar {visibles.length} a CSV
          </button>
        </div>
      </div>

      {/* CA-4. Cero resultados es una respuesta, no una pantalla en blanco, y
          viene con los filtros que la produjeron: los controles pueden haber
          quedado fuera de la pantalla en el telefono. */}
      {visibles.length === 0 ? (
        <p className="historial-vacio" role="status">
          <strong>Ningun evento documentado con esos filtros.</strong>
          {activos.length > 0 && <> Filtros activos: {activos.join(' · ')}.</>} El catalogo tiene{' '}
          {historial.eventos.length} eventos en total; que no haya ninguno aqui es un resultado del
          catalogo, no un fallo de la pantalla.
        </p>
      ) : (
        <div className="historial-desplazable">
          <table className="tabla-historial">
            <caption className="historial-caption">
              {visibles.length} de {historial.eventos.length} eventos
              {activos.length > 0 && <> · {activos.join(' · ')}</>}
            </caption>
            <thead>
              <tr>
                <th scope="col">Fecha</th>
                <th scope="col">Distrito</th>
                <th scope="col">Tipo</th>
                <th scope="col">Severidad</th>
                <th scope="col">Que paso</th>
                {/* CA-6. La procedencia es una columna, no una nota al pie: una
                    lista de eventos sin fuente no se distingue de una inventada,
                    y esa es la razon de que H4.3 valga. */}
                <th scope="col">Fuente</th>
              </tr>
            </thead>
            <tbody>
              {visibles.map((evento, indice) => (
                <tr key={`${evento.fecha_inicio}-${evento.codigo_distrito}-${indice}`}>
                  <th scope="row" className="historial-fecha">
                    {evento.fecha_inicio}
                    {evento.fecha_fin && <span className="historial-fin"> a {evento.fecha_fin}</span>}
                  </th>
                  <td>
                    <span className="nombre-distrito">
                      {nombreDeDistrito(evento.codigo_distrito) ?? evento.codigo_distrito}
                    </span>
                  </td>
                  <td>{nombreDeEvento(evento.tipo_evento) ?? evento.tipo_evento}</td>
                  {/* 42 de las 46 filas no traen severidad, y el catalogo declara
                      por que: la fuente no la reporta y los umbrales no se pueden
                      aplicar hacia atras sin la serie climatica. Escribir la
                      razon en la celda evita que un guion se lea como un dato
                      que se perdio. */}
                  <td className="historial-severidad">
                    {evento.severidad || <span className="valor-ausente">no reportada</span>}
                  </td>
                  <td className="historial-descripcion">{evento.descripcion}</td>
                  <td className="historial-fuente">{evento.fuente}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="historial-procedencia">
        Generado el {historial.generado} desde <code>{historial.fuente}</code>, validado contra los
        contratos congelados. Los eventos no se estiman: estan documentados.
      </p>
    </section>
  )
}
