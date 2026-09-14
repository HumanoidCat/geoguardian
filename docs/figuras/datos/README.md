# Datos tabulados de las figuras de resultados

Cada figura sale de una tabla, y la tabla está aquí. Es la regla que el
documento de investigación sigue desde el 2026-09-10: **primero se tabula el
dato, después se dibuja**.

| Archivo | Qué contiene | De dónde sale |
|---|---|---|
| `comparativa-algoritmos.csv` | F1-macro y rango entre pliegues de los cinco estimadores, por evento, con los hiperparámetros afinados que corre la tubería | Corrida de `python -m backend.modelado.afinar` del 2026-09-04, transcrita de `docs/evidencias/objetivos/H3.8-afinado.md` (tablas «lluvia_intensa» e «incendio»); sequía de `H3.6-cierre-tuberia.md` |
| `episodios-por-pliegue.csv` | Episodios independientes a nivel cantón en el entrenamiento de cada pliegue, y los umbrales de CA-6 de H3.0 | D-34 (`docs/03-bitacora-decisiones.md`), reconfirmado el 2026-09-10 en `H3.11-criterios-aceptacion.md` |

**Estas dos tablas son transcripciones, no mediciones nuevas.** Las cifras
las produce el arnés de H3.6 sobre el conjunto etiquetado, que no se versiona,
y por eso no se pueden recalcular en la integración continua. Si se vuelve a
correr el arnés y una cifra cambia, se cambia aquí y se regeneran las figuras
con `python docs/herramientas/generar_figuras.py --tabuladas`.

`escribe` dice qué estimador escribe `analitico.riesgo` por la regla de D-39
con esas cifras (D-42 para incendio).
