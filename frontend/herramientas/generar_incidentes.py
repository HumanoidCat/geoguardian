"""Convierte la bitacora de incidencias en un JSON que el visor pueda consultar.

Historia H12.5. Rubrica Troubleshoot.

POR QUE UN ARCHIVO ESTATICO Y NO LA API

Porque no hay API que lo sirva, y es la misma figura de **H7.3**, que lo escribio
asi en la cabecera de su componente: «no pasa por la API porque no hay API que lo
sirva». Las incidencias viven en `docs/04-bitacora-incidencias.md`, un documento
del repositorio que se escribe a mano y se revisa en Pull Request.

Servirlo como archivo del propio origen respeta **D-23** —el navegador no habla con
ningun otro dominio— sin pedirle nada a nadie.

LO QUE ESTE GUION NO HACE, Y ES LO MAS IMPORTANTE

**No resume, no reescribe y no interpreta.** Copia el texto tal como esta. Una
incidencia que dice «costo cinco dias» tiene que seguir diciendo eso: el valor de
esta bitacora esta en que nadie la suavizo, y un conversor que «mejora» la
redaccion la vuelve inutil. Es CA-4.

Y **declara lo que falta en vez de rellenarlo**: si una incidencia no tiene
«Causa raiz», el campo va `null` y la pantalla lo dice. Es **D-07**.

LA TRAMPA DE LA PLANTILLA

El archivo abre con un bloque `## I-00 · Titulo corto de la incidencia`, con el
mismo formato que las reales. **No es una incidencia**: es el ejemplo del formato.
Un guion que cuente encabezados `## I-NN` la incluiria y el total saldria mal por
uno. Se excluye explicitamente y se avisa por pantalla cuando se hace, para que la
exclusion sea visible y no un silencio. Es CA-2.

Uso, desde la raiz del repositorio:

    python frontend/herramientas/generar_incidentes.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
FUENTE = RAIZ / "docs" / "04-bitacora-incidencias.md"
SALIDA = RAIZ / "frontend" / "public" / "incidentes" / "incidentes.json"

# El identificador reservado para el bloque de ejemplo. Ver la cabecera.
PLANTILLA = "I-00"

# Las dos que se usan para la cabecera de la ficha y para filtrar. El resto NO se
# enumera aca a proposito: ver `extraer_secciones`.
ETIQUETA_FECHA = "Fecha"
ETIQUETA_DETECTO = "Quien lo detecto"

ENCABEZADO = re.compile(r"^## (I-\d+)\s*·\s*(.+?)\s*$", re.MULTILINE)

# Cualquier bloque `**Etiqueta.**` al principio de una linea. El bloque llega hasta
# el siguiente rotulo igual, o hasta el final de la incidencia.
#
# POR QUE NO UNA LISTA FIJA DE SIETE CAMPOS
#
# La primera version buscaba exactamente los siete de la plantilla -Fecha, Quien lo
# detecto, Que paso, Causa raiz, Accion tomada, Aprendizaje, Impacto- y reportaba
# `null` cuando no los encontraba. Al correrlo, **26 de 61 incidencias salian con
# campos ausentes**, y no era cierto: I-58 tiene `**El barrido.**`, y otras tienen
# rotulos propios que la plantilla no previo.
#
# O sea que el guion **declaraba ausente lo que existia con otro nombre**. Una
# ausencia falsa es peor que un hueco: el hueco se ve, la ausencia falsa se cree.
# Y en una pantalla que existe para no repetir I-25, I-39 e I-41, informar sobre
# las limitaciones del propio conversor en vez de sobre el documento habria sido
# el mismo defecto una cuarta vez.
#
# Ahora se toman **todas** las secciones que haya, en el orden en que estan. Nada
# se pierde y nada se inventa.
# Un rotulo de seccion. El documento usa dos formas y las dos son lo mismo:
#
#     **Causa raiz.**              la de la plantilla
#     ### Los que no pueden fallar  subtitulo, en las incidencias largas
#
# Tratarlas distinto dejaria los `###` a la vista como texto, que es lo que pasaba
# antes de esta linea.
ROTULO = re.compile(
    r"^(?:\*\*([^*\n]+?)\.\*\*[ \t]*|#{3,}[ \t]+(.+?)[ \t]*$)",
    re.MULTILINE,
)

# Un bloque de codigo cercado. El lenguaje despues de las comillas es opcional y
# se descarta: no se usa para nada y no vale la pena arrastrarlo.
CERCA = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)


def _fallar(mensaje: str) -> None:
    print(f"ERROR: {mensaje}", file=sys.stderr)
    raise SystemExit(1)


def limpiar(texto: str) -> str | None:
    """Junta el parrafo en una linea, sin tocar las palabras.

    Se quitan los saltos de linea porque el original esta ajustado a 80 columnas y
    eso es del archivo, no del contenido. **No se quita nada mas**: ni el enfasis,
    ni las comillas, ni los numeros.

    **Solo se aplica a prosa.** A un bloque de codigo lo destruiria: ver
    `partir_en_bloques`.
    """
    texto = re.sub(r"\s*\n\s*", " ", texto).strip()
    return texto or None


def partir_en_bloques(texto: str) -> list[dict[str, str]]:
    """Separa la prosa de los bloques de codigo, porque no se tratan igual.

    POR QUE HACE FALTA

    La primera version pasaba todo por `limpiar` y juntaba cada seccion en una
    linea. En la prosa esta bien -el ajuste a 80 columnas es del archivo-, pero en
    un bloque de codigo borra lo unico que lo hace legible. I-41 tiene una salida
    de `EXPLAIN` con tres filas alineadas; aplastada era una oracion sin sentido.

    Y el proyecto tiene incidencias que son **casi solo** bloques de codigo: el
    valor de I-41 o de I-58 esta en la salida que se pego, no en el parrafo que la
    presenta.

    Los saltos de linea de dentro del bloque **se conservan tal cual**.
    """
    bloques: list[dict[str, str]] = []
    ultimo = 0

    for cerca in CERCA.finditer(texto):
        prosa = limpiar(texto[ultimo : cerca.start()])
        if prosa:
            bloques.append({"tipo": "texto", "texto": prosa})
        codigo = cerca.group(1).rstrip("\n")
        if codigo.strip():
            bloques.append({"tipo": "codigo", "texto": codigo})
        ultimo = cerca.end()

    resto = limpiar(texto[ultimo:])
    if resto:
        bloques.append({"tipo": "texto", "texto": resto})

    return bloques


def extraer_secciones(cuerpo: str) -> list[dict[str, str]]:
    """Todas las secciones rotuladas de una incidencia, en su orden original.

    No hay lista de campos esperados: se toma lo que el documento traiga. Si una
    incidencia inventa un rotulo -y varias lo hacen-, se conserva con su nombre.
    """
    rotulos = list(ROTULO.finditer(cuerpo))
    secciones = []

    for indice, rotulo in enumerate(rotulos):
        desde = rotulo.end()
        hasta = rotulos[indice + 1].start() if indice + 1 < len(rotulos) else len(cuerpo)
        bloques = partir_en_bloques(cuerpo[desde:hasta])
        if bloques:
            # group(1) es la forma `**Rotulo.**`; group(2), la forma `### Rotulo`.
            etiqueta = (rotulo.group(1) or rotulo.group(2)).strip()
            secciones.append({"etiqueta": etiqueta, "bloques": bloques})

    return secciones


def buscar(secciones: list[dict[str, str]], etiqueta: str) -> str | None:
    """Una seccion por su rotulo, o `None` si esa incidencia no la trae.

    Aca `None` **si** significa ausente de verdad, porque se busca sobre lo que se
    encontro y no sobre una lista de lo que deberia haber. D-07.
    """
    for seccion in secciones:
        if seccion["etiqueta"].lower() == etiqueta.lower():
            prosa = [b["texto"] for b in seccion["bloques"] if b["tipo"] == "texto"]
            return " ".join(prosa) if prosa else None
    return None


def main() -> None:
    if not FUENTE.exists():
        _fallar(f"no existe {FUENTE.relative_to(RAIZ)}")

    texto = FUENTE.read_text(encoding="utf-8")
    encabezados = list(ENCABEZADO.finditer(texto))

    if not encabezados:
        _fallar(
            "no se encontro ningun encabezado '## I-NN · titulo'.\n"
            "Si el formato del documento cambio, este guion tiene que cambiar con el: "
            "sacar un JSON vacio de un archivo lleno seria peor que fallar."
        )

    incidentes = []
    omitidas = []

    for indice, encabezado in enumerate(encabezados):
        identificador, titulo = encabezado.group(1), encabezado.group(2)

        # El cuerpo va hasta el siguiente encabezado, o hasta el final.
        desde = encabezado.end()
        hasta = encabezados[indice + 1].start() if indice + 1 < len(encabezados) else len(texto)
        cuerpo = texto[desde:hasta]

        if identificador == PLANTILLA:
            omitidas.append(identificador)
            continue

        secciones = extraer_secciones(cuerpo)
        incidentes.append(
            {
                "id": identificador,
                "titulo": titulo,
                "fecha": buscar(secciones, ETIQUETA_FECHA),
                "detecto": buscar(secciones, ETIQUETA_DETECTO),
                "secciones": secciones,
            }
        )

    # El orden: de la mas reciente a la mas vieja, que es como se consulta un
    # historico. El numero crece con el tiempo, asi que se ordena por el numero y
    # no por la fecha -que puede faltar, y ordenar por un campo que puede ser nulo
    # pone las incompletas en un extremo por una razon que no es su fecha-.
    incidentes.sort(key=lambda i: int(i["id"].split("-")[1]), reverse=True)

    paquete = {
        "fuente": "docs/04-bitacora-incidencias.md",
        "generado_en": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": len(incidentes),
        "incidentes": incidentes,
    }

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(paquete, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"  incidencias: {len(incidentes)}")
    if omitidas:
        # Se dice. Una exclusion silenciosa es indistinguible de un defecto.
        print(f"  omitida la plantilla: {', '.join(omitidas)}  (CA-2)")

    # Cuantas secciones se extrajeron en total, y cuantos rotulos distintos hay.
    # El segundo numero es el que importa: si fueran siete, la plantilla se
    # respetaria al pie de la letra; que sean mas es el dato que hizo cambiar este
    # guion.
    total_secciones = sum(len(i["secciones"]) for i in incidentes)
    rotulos = sorted({s["etiqueta"] for i in incidentes for s in i["secciones"]})
    print(f"  secciones extraidas: {total_secciones}, con {len(rotulos)} rotulos distintos")

    sin_fecha = [i["id"] for i in incidentes if i["fecha"] is None]
    if sin_fecha:
        print(f"  sin fecha: {', '.join(sin_fecha)}")

    print(f"  {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
