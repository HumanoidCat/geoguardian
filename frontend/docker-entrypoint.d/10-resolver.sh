#!/bin/sh
# Escribe la directiva `resolver` de nginx leyendola del sistema. Historia H11.1.
#
# POR QUE NO SE ESCRIBE FIJA
#
# En Docker el DNS interno es 127.0.0.11. En Kubernetes es el del cluster, y no
# es el mismo numero. Escribir 127.0.0.11 a mano arregla hoy y **rompe en H11.3**,
# cuando el visor se despliegue en un namespace de staging.
#
# `/etc/resolv.conf` lo escribe el entorno que corre el contenedor, sea cual sea,
# asi que leerlo de ahi funciona en los tres.
#
# POR QUE ESTE DIRECTORIO
#
# La imagen oficial de nginx ejecuta todo `/docker-entrypoint.d/*.sh` antes de
# arrancar el servidor. No hay que tocar el CMD ni escribir un entrypoint propio:
# el mecanismo ya existe y esta documentado por la imagen.
#
# El numero 10 lo pone antes del 20 de la propia imagen, que es el que sustituye
# las plantillas de `/etc/nginx/templates/`. El orden no importa aca -son archivos
# distintos- pero conviene que el resolver exista antes de que nginx lea nada.
set -eu

DESTINO=/etc/nginx/conf.d/resolver.conf

# Los `nameserver` de resolv.conf, en una linea. Se toman todos, IPv4 e IPv6:
# nginx acepta las dos familias, y si el primer servidor no responde pasa al
# siguiente.
#
# **PERO UNA DIRECCION IPv6 VA ENTRE CORCHETES.** Sin ellos nginx lee los dos
# ultimos caracteres como un puerto y se niega a arrancar:
#
#     10-resolver.sh: resolver -> fd12::10
#     nginx: [emerg] invalid port in resolver "fd12::10" in
#            /etc/nginx/conf.d/resolver.conf:1
#
# Eso es de los registros de Railway del 2026-09-05, donde el DNS interno es
# **IPv6** (`fd12::10`). En Docker es 127.0.0.11 y en k3d es una IP del cluster,
# las dos IPv4, asi que este guion funciono un mes sin encontrarse nunca con el
# caso. El contenedor entraba en un ciclo de reinicio y Railway igual mostraba
# "Deployment successful" y "Online". Es la incidencia I-39.
#
# El comentario anterior decia que nginx "acepta las dos familias". Es cierto y
# no alcanzaba: acepta IPv6 **en corchetes**. Una afirmacion a medias se lee
# igual que una entera.
#
# El `printf` termina en espacio a proposito. Ver el `echo` del final.
SERVIDORES=$(awk '/^nameserver/ {
    direccion = $2
    if (index(direccion, ":") > 0 && substr(direccion, 1, 1) != "[") {
        direccion = "[" direccion "]"
    }
    printf "%s ", direccion
}' /etc/resolv.conf)

if [ -z "$SERVIDORES" ]; then
    # Sin resolver, `proxy_pass` con variable falla en cada peticion con
    # "no resolver defined to resolve api". Es mejor decirlo aca, una vez y
    # claro, que dejar que aparezca en cada respuesta 502.
    echo "10-resolver.sh: /etc/resolv.conf no declara ningun nameserver." >&2
    echo "10-resolver.sh: el visor va a servir estaticos pero /api/ no va a resolver." >&2
    # No se aborta: **el visor tiene que levantar igual**. Servir el respaldo
    # estatico sin API es un modo de operacion valido y declarado, por D-23.
    exit 0
fi

# `valid=10s` para que un cambio de IP del servicio se note en diez segundos y no
# quede cacheado hasta que el contenedor se reinicie. En Kubernetes las IP de los
# pods cambian con cada despliegue.
#
# **NO hay espacio entre `${SERVIDORES}` y `valid`, y es correcto.** El espacio lo
# pone el `printf "%s "` del `awk` de arriba, que deja uno al final de cada
# direccion. Sin el, la linea saldria `resolver 127.0.0.11valid=10s;` y nginx no
# levanta.
#
# Se dice aca porque el espacio que hace funcionar esta linea esta escrito veinte
# lineas mas arriba y es invisible. Quien "limpie" aquel `printf` rompe esto, y el
# motivo no estaria a la vista. Lo señalo la revision de SC-07.
echo "resolver ${SERVIDORES}valid=10s;" > "$DESTINO"

echo "10-resolver.sh: resolver -> ${SERVIDORES}"
