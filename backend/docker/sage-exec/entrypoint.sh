#!/bin/sh
set -e
if [ "$SAGE_EXEC_MODE" = "daemon" ]; then
  exec python -m sage.exec.daemon
fi
exec python -m sage.exec.daemon
