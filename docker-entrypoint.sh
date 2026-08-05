#!/bin/sh
set -e

# The image bakes /app/data as appuser-owned, but docker-compose.yml bind-
# mounts a host directory over that same path at runtime - which replaces it
# with whatever ownership the host side has (root, on Docker Desktop's
# Windows/Mac file-sharing layer). Can't fix this at build time since the
# mount only exists after the image is built and the container starts, so
# fix it here, then drop from root to appuser before exec'ing the real command.
chown -R appuser:appuser /app/data

exec gosu appuser "$@"
