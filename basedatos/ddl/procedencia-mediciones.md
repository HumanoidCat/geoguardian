# Procedencia de las series climaticas

Generado por `backend/etl/cargar_mediciones.py`. No editar a mano.

- Fuente: CHIRPS + NASA POWER (hibrida, D-15)
- Ventana: 1991-01-01 a 2025-12-31
- Momento: 2026-08-19T23:30:00-06:00

| Distrito | Nombre | Filas | Sin lluvia | Sin temperatura | Segundos |
|---|---|---|---|---|---|
| 50801 | Tilarán | 12784 | 0 | 0 | 103.0 |
| 50802 | Quebrada Grande | 12784 | 0 | 0 | 81.3 |
| 50803 | Tronadora | 12784 | 0 | 0 | 85.9 |
| 50804 | Santa Rosa | 12784 | 0 | 0 | 91.3 |
| 50805 | Líbano | 12784 | 0 | 0 | 84.6 |
| 50806 | Tierras Morenas | 12784 | 0 | 0 | 84.4 |
| 50807 | Arenal | 12784 | 0 | 0 | 87.2 |
| 50808 | Cabeceras | 12784 | 0 | 0 | 92.2 |

Total de filas escritas: 102272 en 712.3 segundos

Los dias sin dato quedan con sus columnas en NULL. No se imputa
nada aqui: eso es H1.4, y necesita los huecos intactos para poder
medir cuantos habia.
