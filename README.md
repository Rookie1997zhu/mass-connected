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

See [MASS CONNECTED 平台文档.md](MASS%20CONNECTED%20%E5%B9%B3%E5%8F%B0%E6%96%87%E6%A1%A3.md) and the requirement docs under `project/`.
