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
 * https://vite.dev/config/
 */
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: process.env.API_URL ?? 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (ruta) => ruta.replace(/^\/api/, ''),
      },
    },
  },
})
