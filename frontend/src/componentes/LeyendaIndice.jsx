/**
 * Leyenda de una capa de indice. Historia H5.5.
 *
 * ---------------------------------------------------------------------------
 * POR QUE ESTA LEYENDA DICE TRES COSAS Y NO SOLO LOS COLORES
 * ---------------------------------------------------------------------------
 *
 * La capa muestra **detalle de 20 metros** al lado de una coropleta que es **por
 * distrito**. Eso puede sugerir una precision que las estimaciones de riesgo no
 * tienen, y el riesgo de que alguien lea el indice como si fuera una prediccion
 * es real.
 *
 * La decision fue mostrar el detalle -promediarlo por distrito seria tirar dato
 * medido- y pagar la contrapartida aca. Asi que la leyenda declara:
 *
 *   1. **Que es y de cuando.** Un indice por pixel de una fecha concreta, la de
 *      la escena de satelite. **No es la fecha del selector**, y por eso se
 *      escribe: si el visor muestra el riesgo del 3 de septiembre y el indice es
 *      del 27 de enero, quien mire tiene que poder saberlo.
 *   2. **Cuanto falta.** El porcentaje del canton sin dato por nubes, con el
 *      hueco dibujado igual que en la escala de riesgo. Es D-07: la ausencia se
 *      declara, no se rellena.
 *   3. **Que no es una estimacion de riesgo.** Dicho con esas palabras.
 *
 * Los extremos de la escala van con su cifra. Un color sin numero al lado se lee
 * como impresion; con numero se lee como medicion.
 */

const DEFINICIONES = {
  ndvi: {
    titulo: 'Vegetacion · NDVI',
    formula: '(B8A - B04) / (B8A + B04)',
    bajo: 'suelo desnudo, agua',
    alto: 'vegetacion densa',
    // Los mismos extremos de la rampa de `generar_indices.py`. Se repiten aca
    // porque el visor no lee ese archivo; el JSON trae los numeros y estos
    // colores tienen que coincidir con los que el guion pinto.
    desde: '#aa6e3c',
    hasta: '#28c86e',
  },
  ndwi: {
    titulo: 'Humedad y agua · NDWI',
    formula: '(B03 - B8A) / (B03 + B8A)',
    bajo: 'seco',
    alto: 'agua libre',
    desde: '#c8be8c',
    hasta: '#14dcf0',
  },
}

function comoFecha(iso) {
  if (!iso) return null
  const [anio, mes, dia] = iso.split('-')
  const meses = [
    'enero',
    'febrero',
    'marzo',
    'abril',
    'mayo',
    'junio',
    'julio',
    'agosto',
    'setiembre',
    'octubre',
    'noviembre',
    'diciembre',
  ]
  return `${Number(dia)} de ${meses[Number(mes) - 1]} de ${anio}`
}

export default function LeyendaIndice({ id, paquete }) {
  const definicion = DEFINICIONES[id]
  const indice = paquete?.indices?.[id]
  if (!definicion || !indice) return null

  const fecha = comoFecha(paquete.fecha)

  return (
    <div className="leyenda">
      <h2 className="leyenda-titulo">{definicion.titulo}</h2>

      <p className="leyenda-aviso">
        Lo que el satelite vio el <strong>{fecha}</strong>. No es una estimacion de
        riesgo, y no cambia con la fecha del selector.
      </p>

      <div
        className="indice-rampa"
        style={{
          background: `linear-gradient(to right, ${definicion.desde}, ${definicion.hasta})`,
        }}
      />
      <div className="indice-extremos">
        <span>
          {indice.minimo} · {definicion.bajo}
        </span>
        <span>
          {definicion.alto} · {indice.maximo}
        </span>
      </div>

      <dl className="indice-datos">
        <div>
          <dt>Sin dato por nubes</dt>
          <dd>{indice.sin_dato_canton} % del canton</dd>
        </div>
        <div>
          <dt>Resolucion</dt>
          <dd>20 m por pixel</dd>
        </div>
        <div>
          <dt>Formula</dt>
          <dd className="indice-formula">{definicion.formula}</dd>
        </div>
      </dl>

      <p className="leyenda-nota">
        La coropleta de riesgo es <strong>por distrito</strong>; esta capa es por
        pixel. Son dos cosas distintas sobre el mismo mapa.
      </p>
    </div>
  )
}
