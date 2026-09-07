/**
 * La marca de GeoGuardian: un escudo con el semaforo de riesgo adentro.
 *
 * Historia H5.9. Es el mismo dibujo que `public/favicon.svg`, para que la
 * pestana y la cabecera se reconozcan como una sola cosa. Los tres colores son
 * los de la rampa de `tokens.css` -alto, medio, bajo- y el fondo es
 * `--simulado-fondo`, el unico oscuro del sistema. Se escriben en duro y no como
 * variables porque el favicon no puede leer CSS y los dos archivos tienen que
 * decir lo mismo.
 *
 * Hasta el 2026-09-06 el favicon era el icono morado de la plantilla de Vite.
 *
 * Se descarto poner la silueta del canton dentro del escudo: a 16 px es una
 * mancha. Esta medido en gestion/mockups/favicons_tira.png.
 */
export default function LogoGeoGuardian({ tamano = 36 }) {
  return (
    <svg
      className="logo-geoguardian"
      width={tamano}
      height={tamano}
      viewBox="0 0 64 64"
      role="img"
      aria-label="GeoGuardian"
    >
      <path
        d="M32 3 L57 11.5 V31 C57 45.5 46.5 56.5 32 61 C17.5 56.5 7 45.5 7 31 V11.5 Z"
        fill="#263238"
      />
      <rect x="21" y="15" width="22" height="9" rx="4.5" fill="#d7301f" />
      <rect x="21" y="27.5" width="22" height="9" rx="4.5" fill="#feb24c" />
      <rect x="21" y="40" width="22" height="9" rx="4.5" fill="#ffeda0" />
    </svg>
  )
}
