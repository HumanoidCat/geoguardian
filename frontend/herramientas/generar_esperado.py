"""Escribe lo que el arbol construido espera de la API, para que el visor pueda
contrastarlo contra lo que la API dice ser.

POR QUE EXISTE

**D-43** decide que el sitio publico se construye desde el repositorio y no desde
las imagenes que el CI probo, y lo escribe sin disimularlo:

    El binario que corre en el sitio publico **no es** el que el CI construyo y
    probo. Es otra construccion del mismo arbol, y nadie garantiza que salga
    identica.

La misma ADR dice como se acota esa perdida:

    `/salud` publica la version de la API y la de los contratos; comprobarlas
    contra lo que declara el repositorio detecta que se desplego otro arbol, que
    es el error que importa.

Este guion es la mitad que faltaba de esa comprobacion: deja **en el sitio
construido** lo que ese arbol esperaba, para que el visor pueda comparar sin
preguntarle a nadie mas. Historia H12.2, criterio CA-4.

POR QUE NO SE ESCRIBE LA VERSION A MANO EN EL VISOR

Porque ese es exactamente el defecto de **I-41**: un valor cierto el dia que se
copio, que nada vigila cuando deja de serlo. `rutas.py` devolvio
`base_datos_conectada=False` escrito en duro durante nueve dias despues de que
dejara de ser cierto. Una version de contratos escrita a mano en un componente
tiene la misma fecha de caducidad y no la declara.

CUANDO SE CORRE

Antes de construir el visor, y en el CI antes de `npm run build`. Si el archivo
no existe, el panel **lo dice** en vez de suponer que todo coincide.

Uso, desde la raiz del repositorio:

    python frontend/herramientas/generar_esperado.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CONTRATOS = RAIZ / "contratos" / "__init__.py"
RUTAS_API = RAIZ / "backend" / "api" / "rutas.py"
SALIDA = RAIZ / "frontend" / "public" / "estado" / "esperado.json"


def _fallar(mensaje: str) -> None:
    print(f"ERROR: {mensaje}", file=sys.stderr)
    raise SystemExit(1)


def leer_constante(archivo: Path, nombre: str) -> str | None:
    """El valor de `NOMBRE = "algo"` en un archivo de Python, sin importarlo.

    Se lee con expresion regular y no con `import` a proposito: este guion corre
    desde `frontend/`, que no tiene por que poder importar el paquete del backend
    ni arrastrar sus dependencias.
    """
    if not archivo.exists():
        return None
    texto = archivo.read_text(encoding="utf-8")
    hallazgo = re.search(rf'^{nombre}\s*=\s*["\']([^"\']+)["\']', texto, re.MULTILINE)
    return hallazgo.group(1) if hallazgo else None


def main() -> None:
    version_contratos = leer_constante(CONTRATOS, "VERSION_CONTRATOS")
    if not version_contratos:
        _fallar(
            f"no se encontro VERSION_CONTRATOS en {CONTRATOS.relative_to(RAIZ)}.\n"
            "Sin eso el visor no tiene contra que comparar, y CA-4 de H12.2 no se puede cumplir."
        )

    # La de la API es util pero no obligatoria: vive en carpeta de Cesar y puede
    # cambiar de forma sin avisar. Si no se encuentra, se declara ausente en vez
    # de inventar un valor -es D-07, y el panel la muestra como ausencia-.
    version_api = leer_constante(RUTAS_API, "VERSION_API")

    esperado = {
        "version_contratos": version_contratos,
        "version_api": version_api,
        "generado_en": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fuente": {
            "version_contratos": "contratos/__init__.py",
            "version_api": "backend/api/rutas.py" if version_api else None,
        },
    }

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(esperado, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"  contratos {version_contratos}  <- contratos/__init__.py")
    if version_api:
        print(f"  api       {version_api}  <- backend/api/rutas.py")
    else:
        print("  api       no se encontro VERSION_API: se declara ausente, no se inventa")
    print(f"  {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
