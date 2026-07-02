# OEM Manufacturing Platform

Monorepo for OEM company website, Shop member commerce, and Vue admin panel.

## Stack

- `frontend` — Vue 3 public site (default locale: `ko`)
- `admin` — Vue 3 + Element Plus management UI
- `backend` — Django REST Framework API (no Django Admin)
- `mysql`, `redis`, `caddy`

## Quick Start

1. Copy environment file:

```bash
cp .env.example .env
```

2. Start all services:

```bash
docker compose up --build
```

3. Open:

- Website: http://localhost/
- Admin: http://localhost/admin/
- API health: http://localhost/api/health

## Default Accounts

- Admin: `admin@oem.co` / `Admin123!`
- Shop member: register via `/shop/register`

## Development

- Backend only: `cd backend && pip install -r requirements.txt`
- Frontend: `cd frontend && npm install && npm run dev`
- Admin: `cd admin && npm install && npm run dev`

## Project Spec

See [OEM Manufacturing Company Website & Platform (Multi-language).md](OEM%20Manufacturing%20Company%20Website%20&%20Platform%20(Multi-language).md)
