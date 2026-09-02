# Solicitud de cambio de contrato · lectura de la bitácora de corridas

**ID propuesto.** SC-08
**Contrato afectado.** `contratos/` — se **agrega** un protocolo y dos esquemas.
No se modifica ninguno existente.
**Solicitante.** Luna, desde H12.4
**Fecha.** 2026-09-01
**Estado.** Propuesta. Revisan **Alejandro** como dueño de `contratos/` y
**César** como implementador de H12.1.
**Versión de contratos.** De **1.4.0** a **1.5.0**. Es aditivo: nada de lo que
existe cambia de forma, así que ningún módulo actual se rompe.

> **Sobre dónde vive este archivo.** Está en `docs/investigacion/`, que es mi
> carpeta, y no en `docs/solicitudes/`, que no lo es. Si se aprueba, hay que
> moverlo y numerarlo formalmente. Lo digo porque **ya tenemos dos SC-06 por
> exactamente esto**: uno mío en `docs/investigacion/` y el de brillo entre
> sensores en `docs/solicitudes/`. Prefiero no repetirlo en silencio.

---

## Qué pido, en una frase

Un **protocolo de solo lectura** para consultar la bitácora de corridas, con sus
dos esquemas, para que **H12.4 se pueda escribir y probar antes de que exista la
tabla** de H12.1.

## Por qué, y por qué ahora

H12.4 depende de H12.1, que depende de H1.9. H1.9 cerró ayer. Si se espera a que
H12.1 esté implementada, migrada y fusionada, H12.4 arranca con lo que quede del
trimestre y **Troubleshoot sigue en cero**, que es uno de los ocho criterios de
rúbrica sin ninguna historia cerrada.

Con un contrato y un simulado, las dos historias se escriben en paralelo. Cuando
H12.1 entre, se comprueba que su implementación cumple el contrato y se enchufa.
Si no lo cumple, **la prueba lo dice el primer día** en vez de al integrar.

Es el patrón que el proyecto ya usa en todos lados y que funcionó: las 57 pruebas
de H10.2 se escribieron contra simulados y detectaron cuatro invariantes que
ningún doble podía demostrar.

## Lo que se agrega

### 1. Un enum cerrado para el estado de una corrida

```python
class EstadoCorrida(str, Enum):
    EN_CURSO = "en_curso"
    EXITO    = "exito"
    FALLO    = "fallo"
    PARCIAL  = "parcial"
```

**`PARCIAL` no es adorno.** Una carga que escribió seis distritos de ocho y falló
en el séptimo no es éxito ni es fallo. Marcarla como fallo hace que quien
reintente recargue los seis que ya estaban; marcarla como éxito deja dos
distritos sin dato y sin aviso.

**`EN_CURSO` tampoco.** Si la fila se escribe al empezar, una corrida que quedó
en `EN_CURSO` desde hace seis horas **es un diagnóstico en sí misma**: el proceso
murió. Si solo se escribiera al terminar, esa corrida no dejaría rastro y sería
indistinguible de una que nunca arrancó.

No es hipotético. `backend/etl/bitacora.py` existe porque una corrida de tres
minutos murió y el búfer de la tubería se perdió entero; lo cuenta su propio
docstring.

### 2. Dos esquemas en `contratos/esquemas.py`

```python
class CorridaETL(BaseModel):
    id: int
    proceso: str                          # cargar_mediciones, cargar_focos, ...
    iniciado_en: datetime
    estado: EstadoCorrida
    terminado_en: datetime | None = None
    filas_leidas: int | None = Field(default=None, ge=0)
    filas_escritas: int | None = Field(default=None, ge=0)
    sqlstate: str | None = None
    mensaje: str | None = None
    parametros: dict | None = None        # ventana de fechas, distritos
    fuente: str | None = None             # CHIRPS, POWER, FIRMS, SNIT
    version_codigo: str | None = None
    reportado_por: str | None = None


class FilaRechazada(BaseModel):
    id: int
    corrida_id: int | None = None         # ver la nota de abajo
    origen: str
    sqlstate: str
    mensaje: str
    ocurrido_en: datetime
    detalle: str | None = None
    contexto: str | None = None
    datos: dict | None = None
    reportado_por: str | None = None
```

`FilaRechazada` refleja `control.fallo`, que ya existe desde H1.9, **más una
columna**: `corrida_id`.

**Por qué esa columna.** Hoy `control.fallo` no tiene forma de saber a qué
corrida pertenece. Para diagnosticar "la carga de anoche rechazó 340 filas, todas
con SQLSTATE 23514", H12.4 tendría que correlacionar por ventana de tiempo, y eso
falla en cuanto dos corridas se solapan o alguien reejecuta.

En el contrato va como `int | None` a propósito: si César decide no agregarla, el
contrato sigue siendo válido y **H12.4 declara que no puede agrupar por corrida**
en vez de adivinar. Es la misma decisión que en `Riesgo.probabilidad`: `None`
significa "no disponible", no cero.

### 3. Un protocolo de solo lectura

```python
@runtime_checkable
class LectorBitacora(Protocol):
    """Consulta de corridas y de filas rechazadas. NO escribe."""

    def listar_corridas(
        self,
        desde: datetime,
        hasta: datetime,
        proceso: str | None = None,
        estado: EstadoCorrida | None = None,
    ) -> list[CorridaETL]:
        """Corridas de la ventana, filtradas. Orden ascendente por inicio."""
        ...

    def obtener_corrida(self, id: int) -> CorridaETL | None:
        """None si no existe. La ausencia es un caso válido, no una excepción."""
        ...

    def listar_fallos(self, corrida_id: int) -> list[FilaRechazada]:
        """
        Filas rechazadas de esa corrida.

        Devuelve lista vacía si no hubo ninguna. **Vacío no es lo mismo que la
        corrida no existir**: para eso está `obtener_corrida`.
        """
        ...

    def corridas_sin_terminar(self, antiguedad_minima: timedelta) -> list[CorridaETL]:
        """
        Corridas en EN_CURSO que empezaron hace más que `antiguedad_minima`.

        Es el detector de procesos muertos, y la única consulta de este
        protocolo que existe por una razón de diagnóstico y no de consulta.
        """
        ...
```

## Lo que **no** pido

- **No pido métodos de escritura.** H12.4 diagnostica; escribir la bitácora es
  de H12.1 y del ETL. Un lector que además escribe invita a que el diagnóstico
  "corrija" algo, y eso no es su trabajo.
- **No pido que se guarde la sentencia SQL.** Por el mismo motivo por el que
  `control.fallo` no la guarda: invitaría a reintentarla a ciegas.
- **No pido cambiar `control.fallo` en este documento.** El `corrida_id` se pide
  en `docs/investigacion/requisitos-bitacora-h12.4.md`, dirigido a César, y acá
  solo se refleja como campo opcional del esquema.
- **No pido tocar ningún contrato existente.** Es aditivo.

## Qué pasa si no se aprueba

H12.4 espera a que H12.1 esté implementada y fusionada. No es un desastre: es
trabajar en serie en vez de en paralelo, con tres semanas por delante y un
criterio de rúbrica en cero.

Si se rechaza, pido que quede el ADR con el motivo, para que no se relea dentro
de un mes como un olvido.

## Cómo se comprueba que la implementación real lo cumple

Igual que con los demás contratos, y sin inventar nada nuevo:

```python
def test_el_lector_real_cumple_el_protocolo():
    assert isinstance(LectorBitacoraPostgres(), LectorBitacora)
```

Más las pruebas de forma contra el simulado, que se escriben con H12.4 y corren
contra las dos implementaciones parametrizadas, como en `test_anomalias.py`.

**El simulado tiene que poder representar los casos incómodos**, o las pruebas no
prueban nada: una corrida muerta en `EN_CURSO`, una `PARCIAL`, una con cientos de
filas rechazadas del mismo SQLSTATE, y una sin ningún fallo. Y determinista, por
**SC-04**: dos llamadas iguales devuelven lo mismo.

## Trabajo que implica

| Quién | Qué | Estimado |
|---|---|---|
| Alejandro | Revisar y aprobar o rechazar | — |
| Luna | Escribir el simulado y las pruebas del contrato | 1,5 h |
| Luna | H12.4 contra el simulado | el resto de la historia |
| César | Que su implementación cumpla el protocolo | lo que ya iba a hacer |

El protocolo y los esquemas los escribe quien Alejandro decida: son de
`contratos/` y no los toco sin autorización explícita.
