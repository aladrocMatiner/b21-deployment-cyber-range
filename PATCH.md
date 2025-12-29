# Cambios Aplicados (PATCH)

Este documento describe los cambios realizados respecto a la version original del repositorio
`b21-deployment-cyber-range` y explica el motivo de cada cambio.

## 1) Importacion del proyecto Cyber Range Lite (CRL)

Se ha incorporado el codigo del proyecto CRL dentro del repositorio, bajo `crl/`.
Esto incluye:
- CLI `crlcli`
- Codigo Python de CRL/CRLD/PORTD
- Blueprints, stored-events, docs y utilidades
- Carpeta `challenges/` con ejemplos publicos

Motivo:
- El README del repo original solo enlazaba al proyecto CRL. Para seguir el proceso de instalacion,
  era necesario disponer del codigo localmente.

## 2) Eliminacion de repositorios Git anidados

Se eliminaron las carpetas `.git` de:
- `crl/.git`
- `crl/challenges/.git`

Motivo:
- Evitar subrepositorios dentro del repo principal, lo que dificulta el control de cambios y los commits.
- Mantener un unico historial en el repositorio `b21-deployment-cyber-range`.

## 3) Ajuste de `crl/crlcli` para evitar errores TTY/OpenRC

Archivo modificado:
- `crl/crlcli`

Cambio principal (ultima version):
- El script ahora ejecuta el CLI con:
  `docker compose run --remove-orphans --rm --entrypoint python3 crl -m crl "$@"`

Motivo:
- La imagen oficial `docker.cs.kau.se/csma/cyber-range/crl` no define un entrypoint correcto y
  termina intentando arrancar `openrc`, lo que genera errores de TTY (`/dev/ttyX`) en entornos
  sin TTY real.
- Forzar `python3 -m crl` dentro del contenedor evita que OpenRC se ejecute y permite que el CLI funcione
  de forma no interactiva.

Notas:
- Este ajuste fue necesario para poder ejecutar `init`, `create` y `start` desde el entorno actual.
- Para usar la imagen local construida, se recomienda usar `CRL_IMAGE=crl`.

## Cambios no persistidos en Git

Se construyo una imagen local (`crl:latest`) y se levantaron servicios Docker para la instalacion,
pero esos pasos no generan cambios en el repositorio y no forman parte del commit.
