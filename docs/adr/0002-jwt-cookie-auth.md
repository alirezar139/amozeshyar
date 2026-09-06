# ADR 0002: JWT access token in-memory + httpOnly refresh cookie

## Status
Accepted

## Context
Frontend (Nuxt) and backend (Django) are separately deployed processes/origins. We need an auth scheme that works for both server-side (SSR) and client-side API calls without the CSRF complexity of pure session-cookie auth across origins, while limiting the damage an XSS bug could do.

## Decision
- Access token: short-lived (15 min), returned in the JSON login response body, held only in the Pinia store (memory) on the frontend — never `localStorage`.
- Refresh token: longer-lived (14 days), set as an httpOnly, `SameSite=Lax`, path-scoped cookie by the backend (`apps.accounts.views.LoginView`); rotated and blacklisted on every use (`djangorestframework-simplejwt` + `token_blacklist`).
- `useApi()` on the frontend retries once through `POST /auth/refresh/` on a 401 before surfacing the error.

## Consequences
- An XSS bug can at worst steal a 15-minute access token, not the long-lived refresh token.
- Refresh requires `credentials: 'include'` on every relevant fetch and correct `CORS_ALLOW_CREDENTIALS`/`CORS_ALLOWED_ORIGINS` configuration — misconfiguring either silently breaks refresh.
