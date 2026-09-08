# Procedencia del Lago Arenal

Generado por `frontend/herramientas/generar_lago.py` a partir de la descarga
cruda del SNIT. Historia H14.3. **Artefacto derivado: no editar a mano.**

## Descarga

| Dato | Valor |
|---|---|
| Fecha | 2026-09-08 |
| Servicio | https://geos.snitcr.go.cr/be/IGN_25/wfs |
| Capa | `IGN_25:cuerposdeagua_25k` ("Cuerpos de Agua 1:25mil") |
| Filtro | `nombre='Embalse de Arenal'` |
| Sistema de coordenadas pedido | EPSG:4326 |
| Entidades devueltas | 1 (`numberMatched: 1`) |

Es el **mismo servicio del SNIT** que H1.3 uso para los limites distritales, en su
espacio de trabajo de 1:25.000. Se descarto `IGN_5:hidrografia_5000` (1:5.000):
mas detalle del que la vista cantonal puede mostrar, y mas peso.

    https://geos.snitcr.go.cr/be/IGN_25/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=IGN_25:cuerposdeagua_25k&outputFormat=application/json&srsName=EPSG:4326&CQL_FILTER=nombre%3D%27Embalse%20de%20Arenal%27

**El servicio devuelve EPSG:5367 (CRTM05) si no se le pide otra cosa.** Sin
`srsName=EPSG:4326` las coordenadas salen en metros proyectados y Leaflet las
coloca en el Golfo de Guinea. Queda escrito porque no es evidente.

## Lo que dice la fuente

| Campo | Valor |
|---|---|
| `nombre` | Embalse de Arenal |
| `nom_objeto` | EMBALSE |
| `codigo` | 150203 |
| `area` | 88,236,197 m2 (88.2 km2) |
| `perimetro` | 209,524 m |
| `origen` | PRCR05 |

El nombre oficial es **Embalse de Arenal**. En el visor se muestra como **Lago
Arenal**, que es como lo nombra la gente del canton; el oficial queda en
`nombre_oficial` para que la fuente se pueda rastrear.

## Simplificacion

Douglas-Peucker con tolerancia **0.0002** grados, unos **22 m**
a esta latitud.

| | Anillos | Vertices | Bytes |
|---|---|---|---|
| Original | 21 | 18,103 | 485,385 |
| Publicado | 19 | 1,878 | 39,324 |

Reduccion del 89.6 % de los vertices. La tolerancia se eligio
**midiendo, no a ojo**: a la escala a la que el visor muestra el canton -unos
50 m por pixel en escritorio y 106 en telefono- 22 m es menos de
medio pixel, y a ocho veces ese acercamiento la linea simplificada sigue pegada
a la original. Con 55 m, en cambio, las ensenadas se cortan en linea recta y se
nota. La tabla completa la imprime este mismo guion con `--medir`, y la
comparacion visual esta en la evidencia de la historia.

Los 2 anillos que se pierden son islas de menos de cuatro
vertices tras simplificar: a esta escala no ocupan ni un pixel.

## Sumas de verificacion

    crudo      sha256  96c9c6efca5904d6aff0ecc30ac9abb78840cf6c23875cfe9a13afce970867df
    publicado  sha256  bffe6e57e3dcecad5083e07a717fe6a55060636b11725c0bc17f709f5b7b4f76

## Licencia y uso

Datos del Sistema Nacional de Informacion Territorial (SNIT), Instituto
Geografico Nacional de Costa Rica. Uso academico. **El SNIT prohibe el uso
comercial**; si el proyecto cambiara de licencia, esta capa se sustituye por la
de OpenStreetMap (ODbL, con atribucion).
