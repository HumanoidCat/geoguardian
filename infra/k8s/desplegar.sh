#!/usr/bin/env bash
# Aplica los manifiestos de un entorno. Historias H11.2, H11.3 y H11.4.
#
# =============================================================================
# EL MISMO GUION EN LOS DOS SITIOS, Y ESE ES EL PUNTO
# =============================================================================
#
# Lo corre el flujo de CD contra el cluster efimero, y lo corre una persona
# contra el cluster k3d local. **No hay dos definiciones del despliegue**: si el
# CI y la maquina desplegaran por caminos distintos, el CI en verde no diria
# nada sobre lo que pasa en local, que es lo unico que alguien va a ver.
#
# Ver D-36.
#
# Uso:
#     ./infra/k8s/desplegar.sh <entorno> [etiqueta]
#
#     entorno    desarrollo | pruebas | produccion
#     etiqueta   `latest`, o el SHA del commit. Si se pasa un SHA de 40
#                caracteres se convierte a `sha-<sha>`, que es como los etiqueta
#                H11.1. Por omision, `latest`.
#
# Ejemplos:
#     ./infra/k8s/desplegar.sh desarrollo
#     ./infra/k8s/desplegar.sh produccion 3f2a9c1...

set -euo pipefail

ENTORNO="${1:?Falta el entorno: desarrollo, pruebas o produccion}"
ETIQUETA="${2:-latest}"

case "$ENTORNO" in
  desarrollo|pruebas|produccion) ;;
  *) echo "Entorno desconocido: $ENTORNO" >&2; exit 2 ;;
esac

# Un SHA de commit se convierte a la etiqueta que publica H11.1. Se acepta el
# SHA pelado porque es lo que uno tiene a mano -sale de `git rev-parse HEAD`- y
# obligar a recordar el prefijo es una fuente de despliegues fallidos que no
# dicen por que.
if [[ "$ETIQUETA" =~ ^[0-9a-f]{40}$ ]]; then
  ETIQUETA="sha-$ETIQUETA"
fi

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIRECTORIO="$RAIZ/infra/k8s/local/$ENTORNO"
NAMESPACE="geoguardian-$ENTORNO"
BASE=ghcr.io/humanoidcat/geoguardian

echo "Desplegando a $NAMESPACE con la etiqueta $ETIQUETA"

# LA ETIQUETA SE FIJA EN UNA COPIA, NO EN EL REPOSITORIO.
#
# `kustomize edit set image` reescribe el kustomization.yaml en disco. Corrido
# sobre el arbol de trabajo dejaria el repositorio sucio despues de cada
# despliegue, y tarde o temprano alguien commitea la etiqueta de una corrida.
# Se copia el arbol a un temporal y se edita ahi.
TEMPORAL="$(mktemp -d)"
trap 'rm -rf "$TEMPORAL"' EXIT
cp -r "$RAIZ/infra/k8s/." "$TEMPORAL/"

(
  cd "$TEMPORAL/local/$ENTORNO"
  kubectl kustomize edit set image \
    "$BASE/api=$BASE/api:$ETIQUETA" \
    "$BASE/visor=$BASE/visor:$ETIQUETA" 2>/dev/null \
  || {
    # kubectl no trae `kustomize edit`. Se hace con sed sobre el bloque images
    # de la base, que es donde estan declaradas.
    sed -i "s|newTag: .*|newTag: $ETIQUETA|" ../../base/kustomization.yaml
  }
)

kubectl apply -k "$TEMPORAL/local/$ENTORNO"

# `rollout status` con limite de tiempo es LO QUE CONVIERTE ESTO EN UNA
# COMPROBACION. Sin el, `kubectl apply` devuelve exito en cuanto la API acepta
# el objeto -o sea, siempre- y el despliegue diria que funciono aunque ningun
# pod arranque.
echo "Esperando a que converja..."
kubectl -n "$NAMESPACE" rollout status statefulset/postgis --timeout=240s
kubectl -n "$NAMESPACE" rollout status deployment/api --timeout=240s
kubectl -n "$NAMESPACE" rollout status deployment/visor --timeout=180s

echo
kubectl -n "$NAMESPACE" get pods -o wide
echo
echo "Listo. Para verlo desde la maquina:"
echo "  kubectl -n $NAMESPACE port-forward svc/visor 8080:80"
echo "  kubectl -n $NAMESPACE port-forward svc/api   8000:8000"
