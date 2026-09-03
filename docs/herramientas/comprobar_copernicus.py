"""Comprueba si la cuenta de Copernicus sirve, antes de escribir nada contra ella.

Historia H1.6.

=============================================================================
POR QUE ESTO EXISTE COMO ARCHIVO Y NO COMO UN COMANDO SUELTO
=============================================================================

H1.6 depende de una cuenta gratuita del Copernicus Data Space Ecosystem. El
`.env.example` ya avisa que **el registro tarda y no lo controlamos**, asi que el
peor escenario no es que la cuenta falle: es descubrir que falla despues de
escribir el extractor, cuando ya no hay semana para pedir otra.

Esta comprobacion separa las dos preguntas que se confunden siempre:

    la cuenta sirve?          <- esto, 3 segundos, sin escribir codigo
    el extractor funciona?    <- el extractor y su prueba

Si se mezclan, un fallo de credenciales se lee como un defecto del extractor y se
depura el archivo equivocado. Le paso al equipo con **I-23** y con **I-24**.

=============================================================================
QUE NO HACE, A PROPOSITO
=============================================================================

**No imprime la contrasena ni el usuario, ni siquiera enmascarados.** Un
verificador que ayuda a depurar filtrando el secreto en la consola es un
verificador que un dia termina pegado en un chat o en una captura del CI.

**No guarda el token.** Lo pide, mira si vino, y lo descarta. Guardarlo seria
inventar un cuarto sitio donde vive una credencial.

Uso:
    python docs/herramientas/comprobar_copernicus.py
"""

from __future__ import annotations

from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[2]
ENV = RAIZ / ".env"

# Confirmado contra la documentacion oficial el 2026-09-02:
# https://documentation.dataspace.copernicus.eu/APIs/Token.html
URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CLIENTE = "cdse-public"
TIEMPO_LIMITE = 30.0


def leer_env(ruta: Path) -> dict[str, str]:
    """Lee el .env sin dependencias. Devuelve el diccionario tal cual."""
    valores: dict[str, str] = {}
    if not ruta.exists():
        return valores
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        valores[clave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def main() -> int:
    print("\nComprobando el acceso a Copernicus Data Space Ecosystem\n")

    env = leer_env(ENV)
    usuario = env.get("COPERNICUS_USER", "")
    clave = env.get("COPERNICUS_PASSWORD", "")

    # LAS DOS VARIABLES SE COMPRUEBAN POR SEPARADO.
    #
    # «faltan las credenciales» manda a revisar las dos, y casi siempre falta
    # una. Decir cual ahorra la mitad del tiempo de quien lee esto.
    faltan = [n for n, v in (("COPERNICUS_USER", usuario), ("COPERNICUS_PASSWORD", clave)) if not v]
    if faltan:
        print(f"  SIN PROBAR  {', '.join(faltan)} esta vacio en {ENV.name}\n")
        print("  Cuenta gratuita en https://dataspace.copernicus.eu -> Register.")
        print("  El registro tarda: pedilo hoy aunque el extractor no este escrito.\n")
        return 2

    try:
        respuesta = httpx.post(
            URL,
            data={
                "client_id": CLIENTE,
                "username": usuario,
                "password": clave,
                "grant_type": "password",
            },
            timeout=TIEMPO_LIMITE,
        )
    except httpx.HTTPError as error:
        # SIN RED NO ES LO MISMO QUE CREDENCIAL MALA, Y SE DICE.
        print(f"  SIN RESPUESTA  no se pudo llegar al servidor: {type(error).__name__}\n")
        print("  Es un fallo de red o del servicio, NO dice nada sobre la cuenta.\n")
        return 3

    if respuesta.status_code == 200 and "access_token" in respuesta.json():
        vigencia = respuesta.json().get("expires_in", "?")
        print(f"  SIRVE  el servidor devolvio un token, vigente {vigencia} s\n")
        print("  La cuenta esta activa. H1.6 se puede probar contra la API real.\n")
        return 0

    # EL MOTIVO DEL RECHAZO SE TRADUCE, PORQUE EL CRUDO NO SE ENTIENDE.
    detalle = ""
    try:
        cuerpo = respuesta.json()
        detalle = cuerpo.get("error_description") or cuerpo.get("error") or ""
    except ValueError:
        detalle = respuesta.text[:120]

    print(f"  RECHAZADA  el servidor respondio {respuesta.status_code}")
    if detalle:
        print(f"             {detalle}")
    print()

    if "totp" in detalle.lower() or "account is not fully set up" in detalle.lower():
        print("  Parece que la cuenta tiene 2FA activo. Con 2FA la contrasena sola")
        print("  no alcanza: hay que mandar tambien un codigo `totp`, que cambia cada")
        print("  30 segundos y por lo tanto NO se puede guardar en el .env.")
        print("  Para un extractor desatendido conviene desactivar el 2FA de esta")
        print("  cuenta, o usar una cuenta aparte solo para descargas.\n")
    else:
        print("  Revisa usuario y contrasena en el .env. El usuario es el correo")
        print("  con el que te registraste, no un apodo.\n")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
