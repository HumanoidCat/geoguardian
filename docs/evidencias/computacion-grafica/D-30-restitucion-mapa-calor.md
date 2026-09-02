# Evidencia · D-30 · Restitucion de la capa de mapa de calor, con el recorte arreglado

**Fecha.** 2026-08-27
**Quien lo ejecuta.** Alejandro, Lead PM, **con permiso escrito de Avril**
**Decision que lo ordena.** **D-30**, que revierte **D-28**
**Incidencia asociada.** **I-14**
**Historias afectadas.** **H5.4** recupera su entregable. **H5.8** se revierte en
parte.

---

## Por que este documento existe

D-28 retiro la capa de mapa de calor el 24 de agosto. Su argumento era que
interpolar entre los centroides de ocho poligonos produce valores donde no hay
medicion.

**Ese argumento no lo hizo el profesor.** Lo que dijo, textual, en
`retroalimentacion-docente-visor-2026-08-24.md`:

> *"La capa de calor se pinta sobre el rectangulo que encierra al canton, con los
> bordes rectos a la vista, en vez de recortarse contra los poligonos
> distritales"*

y que **se salia del canton y habia distritos que no marcaba**. La transparencia
le parecio bien.

Eso es un defecto de render. Este documento registra el arreglo y lo mide.

---

## El defecto, localizado

Dos lineas de `CapaMapaCalor.jsx`, tal como estaban antes de retirarse:

```js
const margen = 0.03
const limites = {
  norte: Math.max(...latitudes) + margen,
  sur: Math.min(...latitudes) - margen,
  este: Math.max(...longitudes) + margen,
  oeste: Math.min(...longitudes) - margen,
}
```

`latitudes` y `longitudes` salen de `puntosDeOrigen(centroides)`. O sea que la
superficie se encuadraba sobre la caja de los **centroides**, no de los
poligonos.

**Los dos sintomas que reporto el profesor salen de ahi:**

| Sintoma | Causa |
|---|---|
| Habia distritos que no marcaba | Un centroide esta, por definicion, adentro de su distrito. La mitad exterior de los distritos del borde caia fuera de la caja |
| Se salia del canton | Una caja es un rectangulo. Sobre una forma irregular, buena parte del rectangulo cae en los cantones vecinos y en el lago |

El `margen = 0.03` no era la causa: estaba puesto para tapar el corte recto, y
no alcanzaba a compensar lo que los centroides dejaban afuera. **La caja de
centroides mas margen sigue siendo mas chica que el canton**, 22,3 x 31,0 km
contra 30,7 x 36,6 km.

### Cobertura por distrito, con el encuadre viejo

| Distrito | cubierto |
|---|---|
| Quebrada Grande | 100,0 % |
| Libano | 99,4 % |
| Santa Rosa | 91,6 % |
| Tilaran | 91,0 % |
| Cabeceras | 87,9 % |
| Tierras Morenas | 69,7 % |
| Arenal | 68,3 % |
| **Tronadora** | **54,5 %** |

Tronadora aparecia pintada por la mitad. Eso es lo que se veia en pantalla.

---

## El arreglo, y por que son dos mitades

### 1 · El encuadre sale de los poligonos

`limitesDeColeccion()` en `frontend/src/datos/interpolacion.js`. Recorre las
coordenadas de todos los rasgos, no los centroides.

### 2 · El lienzo se recorta contra la union de los poligonos

En `dibujarSuperficie()`, despues de escribir la superficie:

```js
contexto.globalCompositeOperation = 'destination-in'
contexto.beginPath()
// ... traza todos los anillos ...
contexto.fill('evenodd')
```

`destination-in` conserva lo ya dibujado solo donde el trazo nuevo lo cubre. Es
una operacion sobre el lienzo entero: no hay que decidir celda por celda si esta
adentro.

`evenodd` y no `nonzero` porque el GeoJSON del SNIT no garantiza la regla de la
mano derecha, y con `nonzero` un anillo interior escrito al reves quedaria
relleno.

### Ninguna de las dos alcanza sola

| Encuadre | Pintado fuera del canton | Canton sin pintar |
|---|---|---|
| centroides + 0,03 — **lo que habia** | 23,8 % | 20,7 % |
| poligonos, sin recortar | 40,5 % | 0,0 % |
| **poligonos + recorte** | **0,0 %** | **0,0 %** |

Encuadrar sobre los poligonos y no recortar **empeora** el desborde: la caja
envolvente de una forma irregular es mucho mayor que la forma. Recortar sin
corregir el encuadre quita el desborde y deja los mismos huecos.

---

## Dos lienzos, no uno

La interpolacion y el recorte necesitan resoluciones distintas y no conviene
atarlas:

| | Resolucion | Por que |
|---|---|---|
| Interpolacion | 180 x 180 · celda de 203 m | Sale de ocho puntos. Mas fino no agrega informacion y encarece cada movimiento del deslizador del exponente |
| Mascara de recorte | 1024 · celda de 36 m | Su borde se ve **al lado** del borde vectorial de los distritos. A 203 m quedaria escalonado y se leeria como otro defecto de render |

Se interpola barato, se amplia con el suavizado del navegador —que es lo que da
la apariencia continua que se busca— y se recorta caro.

### Una imprecision medida que se deja como esta

Las filas del lienzo son lineales en **latitud**; `L.imageOverlay` coloca la
imagen linealmente en el plano proyectado de **Mercator**. Las dos escalas no son
la misma, asi que la mascara queda corrida respecto del borde vectorial.

Medido sobre el recuadro del canton: **4,9 m en el peor caso**, a media altura.
La celda de la propia mascara mide 36 m. **Corregirlo seria afinar por debajo de
lo que la mascara puede expresar**, asi que no se corrige y queda escrito.

---

## Lo que NO se toco

- La **opacidad** de 0,7. Es lo que al profesor le gusto.
- La **rampa BuPu** de ColorBrewer, distinta de la escala de riesgo a proposito
  (**D-21**).
- Los **ocho puntos de origen** dibujados encima de la superficie, que son lo que
  impide leerla como una medicion continua del terreno.
- La **leyenda** que declara sobre cuantos puntos se calculo.
- Que la capa venga **apagada por defecto**.

Nada de eso tenia defecto, y es —precisamente— lo que ya atendia la preocupacion
que D-28 dio por desatendida.

---

## El encuadre del mapa vuelve a ancho completo

Segunda mitad de I-14, en `frontend/src/index.css`:

```css
/* antes: H5.8 */              /* ahora */
.mapa {                        .mapa {
  --mapa-aspecto: 0.83;          width: 100%;
  --mapa-alto-tope: ...;         height: 100%;
  max-width: calc(...);          min-height: 28rem;
  aspect-ratio: ...;             z-index: var(--z-mapa);
  margin-inline: auto;         }
}
```

Y en `MapaCanton.jsx` sale el calculo de `--mapa-aspecto`, con el margen de
`fitBounds` de vuelta en 32 px.

**Se conserva de H5.8:** la marca de seleccion accesible —linea clara mas halo—,
el `zoomSnap` a 0,1 y el `bringToFront` del distrito seleccionado. El borde negro
grueso si era un defecto y esa correccion fue la correcta.

---

## La maquina que lo mira

`node frontend/herramientas/verificar_recorte_calor.mjs`, en el trabajo
`frontend` del CI.

**No comprueba el codigo fuente: corre `dibujarSuperficie()` de verdad** sobre un
canvas simulado, y contrasta lo pintado contra una implementacion **independiente**
de punto-en-poligono por lanzamiento de rayos, escrita aparte en el mismo archivo.
El recorte del visor usa relleno por barrido de lineas; la referencia usa
lanzamiento de rayos. Dos algoritmos distintos que tienen que coincidir. Si
compartieran codigo, un error en el recorte estaria tambien en la referencia y la
comprobacion no probaria nada.

### Salida

```
Recorte de la capa de mapa de calor (I-14)

  OK    el simulado trae los ocho distritos
  OK    hay al menos un punto de origen con probabilidad
El encuadre sale de los poligonos, no de los centroides:
  OK    la caja de la superficie contiene el canton entero
  OK    el encuadre cubre Tilaran entero
  OK    el encuadre cubre Quebrada Grande entero
  OK    el encuadre cubre Tronadora entero
  OK    el encuadre cubre Santa Rosa entero
  OK    el encuadre cubre Libano entero
  OK    el encuadre cubre Tierras Morenas entero
  OK    el encuadre cubre Arenal entero
  OK    el encuadre cubre Cabeceras entero

Lo pintado coincide con el canton:
  OK    dibujarSuperficie devuelve un lienzo
  OK    el lienzo devuelto es el del recorte, no el de datos

                                    antes (D-28)      ahora
  pintado fuera del canton            23.8 %        0.0 %
  canton sin pintar                   20.7 %        0.0 %
  km2 fuera del canton               157.0          0.0
  km2 del canton sin pintar          130.7          0.0

  86576 muestras evaluadas, 3424 descartadas por caer a menos de una celda de
  la mascara de algun contorno, incluidas las costuras entre distritos

  OK    no se pinta nada fuera del canton
  OK    no queda territorio del canton sin pintar
  OK    el estado anterior si fallaba las dos, o sea que la medicion distingue
El recorte de la capa de calor se cumple.
```

**La cuarta comprobacion es la que sostiene a las otras tres.** Reconstruye el
estado anterior llamando a la misma funcion sin recorte y exige que **falle**. Sin
ella, las tres primeras podrian estar pasando por no estar midiendo nada, que es
exactamente el modo de fallo de **I-06**.

### Por que se descartan muestras

Las que caen a menos de una celda de la mascara de cualquier contorno, incluidas
las **costuras internas** entre distritos vecinos. Ahi el desacuerdo es de
redondeo: los dos algoritmos tienen que decidir de que lado cae un pixel que el
borde parte por la mitad, y no tienen por que decidir igual.

Que las costuras internas importaran no era obvio. La primera version descartaba
solo donde cambiaba la respuesta —o sea el contorno exterior— y quedaban **tres
muestras** en desacuerdo, a **1,8, 9,2 y 10,0 metros** de un limite entre
distritos. Adentro del canton por los dos lados, asi que el filtro no las veia.
La celda de la mascara mide 36 m.

---

## Un hallazgo lateral que queda anotado

Los ocho poligonos simplificados del SNIT **no teselan**: la union de los ocho
deja **142 huecos diminutos** entre distritos vecinos.

No afecta a esta capa —la tolerancia del verificador los cubre— y no se corrige
aqui, porque las geometrias son responsabilidad de **H1.3** y su fuente es el
SNIT. Se anota por si alguna vez importa: cualquier calculo que asuma que la
union de los distritos es el canton exacto va a encontrarlos.

---

## Como reproducirlo

```
node frontend/herramientas/verificar_recorte_calor.mjs
cd frontend && npm run lint && npm run build
python frontend/herramientas/verificar_escala.py
python docs/herramientas/verificar_h115.py --dist frontend/dist
```

Y en el visor, encendiendo la capa **Mapa de calor** en el control de capas: la
superficie tiene la forma del canton, no de un rectangulo, y ningun distrito
queda sin pintar.
