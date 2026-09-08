// El GeoJSON del Lago Arenal es un recurso propio del visor, no un origen de
// datos negociable entre la API y el respaldo. Aun asi la carga vive aca y no
// dentro del componente: la regla de H6.6 y D-23 es que ningun componente pida
// nada por su cuenta, y `verificar_h66.py` la comprueba archivo por archivo
// sobre `frontend/src/componentes/*.jsx`.
//
// El dia que esto tenga dos origenes -y con GitHub Pages ya tiene uno distinto
// del de desarrollo- se resuelve en un solo lugar y no en cada componente.

export const RUTA_LAGO = `${import.meta.env.BASE_URL}geo/lago-arenal.geojson`

export async function obtenerLago() {
  const respuesta = await fetch(RUTA_LAGO)
  if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`)
  return respuesta.json()
}
