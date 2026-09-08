/**
 * Un dibujo por evento y uno por nivel, de trazo, para la pantalla «Hoy en tu
 * distrito». Historia H14.2.
 *
 * POR QUE DE TRAZO Y NO RELLENOS
 *
 * Los mismos dibujos tienen que funcionar en cuatro sitios: la pantalla, el
 * mensaje que se reenvia, el cartel A3 del aula y una fotocopia en blanco y
 * negro. Un trazo grueso sobrevive a los cuatro; un degradado no sobrevive a
 * ninguno salvo la pantalla.
 *
 * POR QUE ESTAS FORMAS Y NO OTRAS
 *
 *  - Lluvia: una gota. Es universal y a 24 px sigue siendo una gota.
 *  - Incendio: una llama con el nucleo lleno. El nucleo la distingue de una gota
 *    invertida cuando el dibujo es chico, que es donde se confunden.
 *  - Sequia: un sol sobre tierra agrietada. El sol solo dice «buen tiempo»; la
 *    grieta es lo que dice sequia.
 *
 * Se descartaron la nube con rayo -se confunde con tormenta electrica, que no es
 * un evento del proyecto-, el termometro -calor no es sequia- y el arbol quemado
 * -demasiado detalle a 24 px-.
 *
 * `currentColor` en todos los trazos: el color lo decide el CSS, asi que el
 * mismo dibujo sirve sobre papel claro y sobre fondo oscuro sin duplicarlo.
 */

const COMUN = {
  viewBox: '0 0 48 48',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2.5,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
  focusable: false,
}

function Gota(props) {
  return (
    <svg {...COMUN} {...props}>
      <path d="M24 5c6.5 8.5 12 15 12 21a12 12 0 0 1-24 0c0-6 5.5-12.5 12-21z" />
      <path d="M18.5 27a5.5 5.5 0 0 0 5.5 5.5" strokeWidth="2" />
    </svg>
  )
}

function Llama(props) {
  return (
    <svg {...COMUN} {...props}>
      <path d="M27 4c1 6-2.5 8.5-5.5 11.5S15 22 15 27a9 9 0 0 0 18 0c0-3-1.5-5.5-3-7.5 3.5 1 6 4.5 6 9a12 12 0 0 1-24 0c0-8 6-11 9.5-15C24 10.5 26.5 8 27 4z" />
      <path d="M24 26c2 1.5 3 3.5 3 5.5a3 3 0 0 1-6 0c0-1.5.8-3 3-5.5z" fill="currentColor" />
    </svg>
  )
}

function SolAgrietado(props) {
  return (
    <svg {...COMUN} {...props}>
      <circle cx="24" cy="15" r="7" />
      <path d="M24 3v3M24 24v0M12 15H9M39 15h-3M15.5 6.5l-2-2M32.5 6.5l2-2" />
      <path d="M6 32h36" />
      <path d="M14 32v9M27 32v6M36 32v9M20 38h8" strokeWidth="2" />
    </svg>
  )
}

/**
 * El dibujo del evento que se le pida.
 *
 * Es un componente y no un objeto con los tres, porque la recarga en caliente de
 * Vite exige que un archivo de componentes exporte solo componentes. Es la misma
 * regla por la que los eventos viven en su propio archivo de datos.
 */
export function PictogramaEvento({ id, ...props }) {
  if (id === 'lluvia_intensa') return <Gota {...props} />
  if (id === 'incendio') return <Llama {...props} />
  if (id === 'sequia') return <SolAgrietado {...props} />
  return null
}

/**
 * El circulo de nivel.
 *
 * Lleva borde oscuro siempre. Sin el, el amarillo palido del nivel «tranquilo»
 * da 1,1:1 contra el papel y a 16 px desaparece: el borde es lo que lo hace
 * legible, y esta medido en la escala.
 *
 * Cuando no hay nivel no se pinta un color: se pinta la trama de ausencia de
 * D-07, que es la misma que ya usa el mapa. La ausencia se dibuja, nunca se
 * rellena con algo plausible.
 */
export function CirculoNivel({ nivel }) {
  const clase = nivel ? `circulo-nivel nivel-${nivel}` : 'circulo-nivel sin-nivel'
  return <i className={clase} aria-hidden="true" />
}
