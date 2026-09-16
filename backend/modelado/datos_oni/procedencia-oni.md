# Procedencia del indice ONI

Descargado a mano. **Este archivo se versiona a proposito** (CA-2 de H3.10): hace
la corrida reproducible sin red y es la red de seguridad del CA-7, porque la
imagen `trabajos` de H11.7 corre de madrugada sin nadie mirando.

- Fuente: NOAA / NWS / **Climate Prediction Center**
- URL: `https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt`
- Momento de descarga: **2026-09-14T21:44:47-06:00**
- SHA-256: `93F8C86C7A660F46318ABE33B38C0479D184812D95A479A1FE869C0C2363A9E4`
- Tamano: 23 000 bytes · 920 lineas (1 encabezado + 919 filas)
- Cobertura: **DJF 1950 a JJA 2026**, sin un solo mes faltante
- Licencia: dominio publico (obra del gobierno de los Estados Unidos)

## Por que ESTA fuente y no la otra que se llama igual

**Hay dos tablas de NOAA que se llaman ONI y no dan los mismos numeros.** Medido
el 2026-09-14:

| | CPC (esta) | PSL (`psl.noaa.gov/data/correlation/oni.data`) |
|---|---|---|
| 1950 DJF | **-1.32** | -1.53 |
| 1950 JFM | **-1.20** | -1.34 |

La del CPC es la **primaria**: es la tabla con la que NOAA declara oficialmente
El Nino y La Nina, y usa periodos base centrados de 30 anios que se actualizan
cada cinco. La de PSL es una redistribucion con otra climatologia.

Dos archivos con el mismo nombre y distinto numero es exactamente como se cuela
un dato sin procedencia. Por eso esto esta escrito.

## Que trae y como se lee

Cuatro columnas. Se usa **ANOM**; `TOTAL` es la temperatura absoluta de la region
y no dice nada sin su climatologia.

    SEAS  YR   TOTAL   ANOM
    DJF 1950  25.01  -1.32
    ...
    JJA 2026  29.09   1.80

**El ONI no es mensual: es una media movil de tres meses.** Cada fila esta
etiquetada con las iniciales de sus tres meses y se asigna al mes **central**:
`DJF` a enero, `NDJ` a diciembre. Asi cada anio trae exactamente doce filas y el
mapeo a mes es uno a uno. Lo hace `backend/modelado/oni.py`.

## El indice se revisa hacia atras

La NOAA **recalcula meses ya publicados** cuando cambia la version de ERSST o
cuando rota el periodo base. Por eso el valor que usa el proyecto queda congelado
en este archivo con su fecha y su suma, en vez de bajarse en cada corrida: una
corrida de hoy y una de dentro de un mes tienen que dar el mismo numero.

## Como se vuelve a bajar, si hiciera falta

    $u = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
    $d = "backend/modelado/datos_oni"
    Invoke-WebRequest -Uri $u -OutFile "$d/oni.ascii.txt"
    (Get-FileHash "$d/oni.ascii.txt" -Algorithm SHA256).Hash

**Y se anota aca la fecha y la suma nuevas.** Un archivo reemplazado sin
actualizar su procedencia es peor que no tener procedencia: dice una fecha que no
es la del dato.
