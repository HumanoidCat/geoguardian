# Tareas de Cesar

**Cesar Andres Ubau Calvo**  
**Carpetas propias:** `backend/api, backend/etl, basedatos`

> Solo modificas tus carpetas. Si necesitas un cambio fuera de ellas, se pide, no se hace.

> Marca `[x]` cuando la historia cumpla la Definition of Done, no cuando el codigo funcione.

**Total asignado:** 96 puntos · 115 horas · 11.5 h por semana en promedio

## Carga por sprint

| Sprint | Semanas | Horas | Capacidad | Estado |
|---|---|---|---|---|
| S0 | semanas 2-3 | 18.3 | 26 | holgado |
| S1 | semanas 4-5 | 25.1 | 26 | ajustado |
| S2 | semanas 6-7 | 20.3 | 26 | holgado |
| S3 | semanas 8-9 | 31.1 | 26 | SOBRECARGA +5 h |
| S4 | semanas 10-11 | 20.3 | 26 | holgado |

## Sprint 0 (semanas 2-3) — 18.3 h

- [ ] **H1.1** · Descargar 10 anios de series climaticas diarias, reejecutable e idempotente
  - `E1` · 5 pts · 7.8 h · rubrica: BD-1 · **bloquea a: H1.4, H1.5, H8.2**
- [ ] **H1.2** · Descargar historico de focos de calor filtrado al canton
  - `E1` · 3 pts · 4.7 h · rubrica: BD-1
- [ ] **H1.3** · Cargar geometrias de distritos con to_postgis y SRID validado
  - `E1` · 6 pts · 5.8 h · rubrica: BD-1 · depende de: contratos · **bloquea a: H1.8, H1.11**

## Sprint 1 (semanas 4-5) — 25.1 h

- [ ] **H1.4** · Documentar y aplicar criterios de imputacion de faltantes
  - `E1` · 5 pts · 7.8 h · rubrica: BD-1 · depende de: H1.1 · **bloquea a: H1.7, H2.1**
- [ ] **H1.7** · Versionar el dataset consolidado para reproducibilidad
  - `E1` · 3 pts · 2.9 h · rubrica: OE1 · depende de: H1.4
- [ ] **H1.8** · Crear esquemas, roles y usuarios con minimo privilegio
  - `E1` · 5 pts · 4.8 h · rubrica: BD-2 · depende de: H1.3 · **bloquea a: H1.9, H1.13**
- [ ] **H6.1** · API REST con OpenAPI y esquemas Pydantic en todos los endpoints
  - `E6` · 5 pts · 4.8 h · rubrica: Arq · depende de: contratos · **bloquea a: H6.2, H7.2, H8.3**
- [ ] **H6.2** · Patron Repository con pruebas unitarias sin base de datos
  - `E6` · 5 pts · 4.8 h · rubrica: Arq · depende de: H6.1 · **bloquea a: H6.3, H10.2**

## Sprint 2 (semanas 6-7) — 20.3 h

- [ ] **H1.11** · Particionar mediciones por anio y medir efecto en consultas
  - `E1` · 5 pts · 4.8 h · rubrica: BD-1 · depende de: H1.3 · **bloquea a: H1.12**
- [ ] **H1.9** · Funciones PL/pgSQL con EXCEPTION WHEN, RAISE y bitacora de fallos
  - `E1` · 8 pts · 7.7 h · rubrica: BD-3 · depende de: H1.8 · **bloquea a: H1.10**
- [ ] **H3.3** · Entrenar y evaluar Regresion Logistica
  - `E3` · 5 pts · 7.8 h · rubrica: OE2 · depende de: H3.2

## Sprint 3 (semanas 8-9) — 31.1 h

- [ ] **H1.10** · Estrategia de respaldo definida y restauracion probada
  - `E1` · 5 pts · 7.8 h · rubrica: BD-4 · depende de: H1.9
- [ ] **H1.12** · Indices espaciales y compuestos con planes antes y despues
  - `E1` · 5 pts · 4.8 h · rubrica: BD-1 · depende de: H1.11
- [ ] **H1.13** · Trigger de auditoria sobre predicciones, con prueba
  - `E1` · 3 pts · 2.9 h · rubrica: BD-2 · depende de: H1.8
- [ ] **H3.4** · Entrenar y evaluar Random Forest
  - `E3` · 5 pts · 7.8 h · rubrica: OE2 · depende de: H3.2
- [ ] **H8.2** · ETL concurrente con medicion secuencial contra paralelo
  - `E8` · 5 pts · 7.8 h · rubrica: SO-1 · depende de: H1.1

## Sprint 4 (semanas 10-11) — 20.3 h

- [ ] **H10.4** · Manual tecnico verificado por alguien ajeno al desarrollo
  - `E10` · 5 pts · 4.8 h · rubrica: MVP · depende de: H8.1
- [ ] **H6.3** · Strategy y Factory: agregar una fuente sin tocar el orquestador
  - `E6` · 5 pts · 4.8 h · rubrica: Arq · depende de: H6.2 · **bloquea a: H6.5**
- [ ] **H8.3** · Cache en memoria con politica de expiracion y consumo medido
  - `E8` · 5 pts · 7.8 h · rubrica: SO-1 · depende de: H6.1
- [ ] **H8.4** · Estrategia de almacenamiento de rasters con proyeccion de crecimiento
  - `E8` · 3 pts · 2.9 h · rubrica: SO-1 · depende de: H1.6

## Al terminar cada historia

1. Verificar ejecutando, no leyendo. Si dice que pasa, correlo.
2. Guardar la evidencia en `docs/evidencias/<materia>/` el mismo dia.
3. Abrir el Pull Request hacia `dev` enlazado a la issue.
4. Marcar `[x]` aqui y cerrar la issue en GitHub.
