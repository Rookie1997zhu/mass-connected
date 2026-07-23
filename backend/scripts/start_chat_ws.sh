#!/bin/sh
set -e
if ! python -c "import daphne" 2>/dev/null; then
  pip install -q "channels>=4.1,<5" "channels-redis>=4.2,<5" "daphne>=4.1,<5"
fi
exec daphne -b 0.0.0.0 -p 8001 config.asgi:application
