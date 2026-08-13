# Procedencia de las geometrias territoriales

Generado por `backend/etl/cargar_distritos.py`. Historia H1.3, issue #37.
No editar a mano: se reescribe en cada carga.

## Descarga

| Dato | Valor |
|---|---|
| Fecha y hora | 2026-08-13 00:13:21 -0600 |
| Servicio | https://geos.snitcr.go.cr/be/IGN_5_CO/wfs |
| Capa distrital | `IGN_5_CO:limitedistrital_5k` |
| Capa cantonal | `IGN_5_CO:limitecantonal_5k` |
| Filtro | `"CÓDIGO_CANTÓN"=508` |
| Sistema de coordenadas pedido | EPSG:4326 |

## Cobertura

| Dato | Valor |
|---|---|
| Entidades de la capa distrital a nivel nacional | 494 |
| Entidades traidas por el filtro | 8 |
| Entidades de la capa cantonal traidas | 1 |
| Geometrias invalidas de origen, corregidas con ST_MakeValid | 0 |

El filtro reduce 494 distritos del pais a los 8
del canton 508 (Tilaran). La reduccion ocurre en el servidor: no se
descargan las 494 para descartar despues.

## Sumas de verificacion

    distrital  sha256  853fe38d0d473c2d76d6430cff0857bed41a05faf78033f99ca5f9f76dbbf8c6
    cantonal   sha256  cfe1cc0d93dfa88a81326856f5e42ee10f8f7da1e97d6a42cdb41854a2a6be83

## Peticiones exactas

    https://geos.snitcr.go.cr/be/IGN_5_CO/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=IGN_5_CO%3Alimitedistrital_5k&outputFormat=application%2Fjson&srsName=EPSG%3A4326&CQL_FILTER=%22C%C3%93DIGO_CANT%C3%93N%22%3D508

    https://geos.snitcr.go.cr/be/IGN_5_CO/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=IGN_5_CO%3Alimitecantonal_5k&outputFormat=application%2Fjson&srsName=EPSG%3A4326&CQL_FILTER=%22C%C3%93DIGO_CANT%C3%93N%22%3D508
