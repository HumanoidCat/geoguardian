# SC-11 · Excluir `gestion/` del versionado

| | |
|---|---|
| **Archivo compartido** | `.gitignore` |
| **Pedida por** | Alejandro, al preparar el PR de H1.16 |
| **Redactada por** | Alejandro, 2026-09-14 |
| **Historia que la origina** | Ninguna. Salió de un `git status` mientras se cerraba **H1.16** |
| **Numeración** | SC-08 la reservó Luna; SC-09 se consumió en la colisión del 2026-09-02; SC-10 cerró el enum `Algoritmo` |

## El problema, en una frase

**`gestion/` aparece como `?? gestion/` en `git status`: está a un `git add -A`
de entrar al repositorio con todo adentro.**

## Por qué no alcanza con la regla que ya existe

La regla del proyecto es **nunca `git add -A`**, y es la incidencia **I-47**. Esa
regla funciona mientras nadie se equivoque **ni una vez**. Un `.gitignore`
funciona aunque alguien se equivoque.

Es exactamente el mismo razonamiento que ya está escrito dos veces en este
`.gitignore`:

> `basedatos/respaldos/` [...] estaba protegida solo por la extensión: el mismo
> antipatrón que este bloque condena.

> Mismo caso que `infra/docker/respaldos/`: aparecía como no seguido, o sea a un
> `git add .` de entrar.

`gestion/` es el tercer caso de la misma familia, y el único que sigue abierto.

## Qué hay en `gestion/`, y por qué importa que no entre

No hay credenciales. Hay algo distinto y también privado:

- borradores de mensajes al equipo, incluidos los que hablan de quién va atrasado;
- cuerpos de PR antes de pegarlos;
- notas de medición todavía sin contrastar.

Si eso entrara al repositorio, no se filtraría un secreto técnico: se publicaría
**material de gestión sobre personas** en un repositorio que el equipo entero lee.
El daño no es de seguridad, es de confianza, y no se deshace borrando el archivo
en un commit posterior porque queda en el historial.

## El cambio pedido

Agregar al final de `.gitignore`:

```
gestion/
```

con el comentario fechado que explica por qué, siguiendo el estilo del resto del
archivo.

## Por qué esto va por solicitud y no por la excepción

El propio `07-propiedad-archivos.md` dice que `.gitignore` se modifica por
solicitud **salvo cuando el cambio agrega una exclusión que protege un secreto**,
porque excluir de más «puede esconderle a alguien un archivo suyo».

**Se podría haber estirado la excepción y no se hizo.** Esto no protege un
secreto en el sentido de una credencial, así que cae del lado que «se discute». Y
la preocupación de la regla —esconderle a alguien un archivo suyo— aquí hay que
mirarla de frente: `gestion/` es carpeta de una sola persona, así que **no puede
tapar trabajo de nadie más**; pero eso lo decide quien lee la solicitud, no quien
la escribe.

## Quién queda afectado

| Quién | Qué le toca |
|---|---|
| Alejandro | Sus archivos de `gestion/` dejan de figurar en `git status`. Ninguno estaba versionado |
| Ávril, César, Luna | Nada. Ninguno tiene una carpeta con ese nombre |

Si alguien crea un `gestion/` propio más adelante, quedará ignorado también, que
es el comportamiento pedido: es una carpeta de trabajo, no de entregables.

## Lo que la SC **no** autoriza

- **No borra nada.** Los archivos siguen en disco; solo dejan de ser candidatos a
  entrar.
- **No toca ningún otro patrón** del `.gitignore`.
- **No crea un lugar donde esconder trabajo del proyecto.** Evidencias,
  decisiones y documentación siguen yendo a `docs/`, que se versiona. Si algo que
  el proyecto necesita termina en `gestion/`, es un error de ubicación y se
  arregla moviéndolo, no ampliando esta excepción.

## Cómo se comprueba que entró bien

1. `git status --short` ya no muestra `?? gestion/`.
2. `git check-ignore -v gestion/` nombra la línea del `.gitignore`.
3. `git log --all -- gestion/` sale vacío: nunca entró nada.

## El riesgo, dicho

El riesgo real de ignorar una carpeta es que se vuelva el lugar cómodo donde
guardar lo que debería estar versionado, y que dentro de un mes nadie sepa dónde
vive una decisión. Se acota con la lista de arriba y con una prueba simple: si un
archivo de `gestion/` hace falta para entender el proyecto, está en el lugar
equivocado.
