# HardLock Dashboard

React developer dashboard for the HardLock hardware-bound licensing platform.

## Quick Start

```bash
cd dashboard
npm install
npm run dev
```

The dev server runs at [http://localhost:5173](http://localhost:5173) and proxies API requests to `http://localhost:8000` via `/api`.

## Environment

Create `.env.local` to override the API URL:

```
VITE_API_URL=http://localhost:8000
```

## Pages

| Route | Description |
|-------|-------------|
| `/login` | Sign in / register |
| `/apps` | List applications, create new apps, view stats |
| `/apps/:id` | App detail — API key, licenses, devices |
| `/logs` | Launch verification audit log |

## Build

```bash
npm run build
npm run preview
```

## Tech Stack

- React 18 + Vite
- Tailwind CSS 3 (dark theme)
- React Router v6
- Axios (JWT in localStorage)
