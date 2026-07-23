#!/bin/sh
set -e
if ! python -c "import daphne" 2>/dev/null; then
  pip install -q "channels>=4.1,<5" "channels-redis>=4.2,<5" "daphne>=4.1,<5"
fi
python manage.py migrate
python manage.py create_default_admin
python manage.py seed_demo_data
python manage.py seed_quote_tables
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
