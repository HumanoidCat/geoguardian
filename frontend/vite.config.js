import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * Configuracion del visor.
 *
 * El proxy de /api lo agrego la historia H6.6, bajo la excepcion de propiedad de
 * docs/07-propiedad-archivos.md: "cliente.js y la configuracion de entorno del
 * visor". El resto del archivo es de Avril y no se toco.
 *
 * POR QUE UN PROXY Y NO UN ORIGEN ABSOLUTO
 *
 * El visor podria llamar a http://localhost:8000 directo, pero entonces el
 * navegador haria una peticion de otro origen y la API tendria que permitirlo con
 * CORS. Eso significaria tocar backend/api/aplicacion.py, que es de Cesar y que
 * esta historia no autoriza.
 *
 * Es ademas la solucion correcta por si sola: en el despliegue el visor y la API
 * van detras del mismo origen, asi que el permiso no haria falta. Un origen
 * absoluto escrito aca habria que quitarlo despues; una ruta relativa funciona en
 * los dos lados sin cambiar nada.
 *
 * Si la API no esta levantada, el proxy responde con error y cliente.js cae al
 * respaldo estatico declarandolo. Eso es lo que pide el criterio CA-3 de H6.6.
 *
 * El destino va escrito y no leido de `process.env`: el `eslint.config.js` de
 * Avril aplica los globales del NAVEGADOR a todos los `.js`, asi que `process`
 * es `no-undef` y el trabajo de frontend del CI sale en rojo. Arreglarlo del
 * lado del linter significaria tocar su archivo, que esta fuera de la excepcion
 * de H6.6. Y no hace falta: para apuntar a otra maquina esta `VITE_API_URL`,
 * que Vite si expone al visor.
 *
 * https://vite.dev/config/
 */
export default defineConfig({
  // H11.5. GitHub Pages sirve en /geoguardian/, no en la raiz del dominio, y ahi
  // toda ruta absoluta de raiz se rompe. Con `base` relativo, Vite emite rutas
  // relativas en index.html y en los assets, asi que el mismo `dist` funciona en
  // la raiz y en cualquier subdirectorio.
  //
  // Se elige './' y no '/geoguardian/' para NO cambiarle el flujo a Avril: en
  // desarrollo Vite ignora el base relativo y sigue sirviendo en localhost:5173/.
  // Un valor fijo la obligaria a entrar a /geoguardian/ para trabajar.
  //
  // Tampoco se lee de una variable de entorno: `process` es `no-undef` en su
  // eslint.config.js, que aplica los globales del navegador a todos los .js. Es
  // el mismo tropiezo que documenta el comentario de `server.proxy`.
  //
  // Ver docs/07-propiedad-archivos.md, excepcion de H11.5.
  base: './',
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (ruta) => ruta.replace(/^\/api/, ''),
      },
    },
  },
})
