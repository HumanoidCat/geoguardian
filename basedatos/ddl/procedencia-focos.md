# Procedencia de los focos de calor

Generado por `backend/etl/cargar_focos.py`. No editar a mano.

- Fuente: NASA FIRMS: MODIS C6.1 y VIIRS S-NPP 375 m
- Archivo historico por pais, sin autenticacion
- Ventana: 2001-01-01 a 2024-12-31
- Momento: 2026-08-24T19:27:10-06:00
- Caja: -85.04680, 10.32079, -84.76609, 10.65175

Focos en la caja: 494. Dentro del canton: 242. Fuera: 252.

| Distrito | Nombre | Focos |
|---|---|---|
| 50804 | Santa Rosa | 83 |
| 50806 | Tierras Morenas | 65 |
| 50805 | Líbano | 65 |
| 50801 | Tilarán | 15 |
| 50802 | Quebrada Grande | 7 |
| 50803 | Tronadora | 5 |
| 50807 | Arenal | 1 |
| 50808 | Cabeceras | 1 |

Los focos fuera del canton se guardan con `codigo_distrito` nulo. La caja
es un rectangulo y el canton no, asi que la diferencia es el borde.

Cortes de confianza: Tabla 10 de Giglio, Schroeder, Hall y Justice,
MODIS Collection 6 Active Fire Product User's Guide, Revision C,
University of Maryland, diciembre de 2020.
