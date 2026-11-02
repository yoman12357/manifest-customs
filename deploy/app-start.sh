#!/bin/sh
set -eu
# A freshly attached persistent disk may be root-owned. The app itself runs unprivileged.
if [ "$(id -u)" = "0" ]; then
  chown manifest:manifest /app/data /app/samples
  exec runuser -u manifest -- "$@"
fi
exec "$@"
