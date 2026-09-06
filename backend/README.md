# Backend (Django + DRF)

## App layout

| App | Responsibility |
|---|---|
| `apps.accounts` | Custom email-based `User`, roles (student/instructor/admin), JWT auth (access token in body, refresh in httpOnly cookie) |
| `apps.instructors` | Public instructor marketing profile; admin approval gate before a profile is public |
| `apps.courses` | Categories, courses, lessons; admin approval gate before a course is published |
| `apps.videos` | Video upload, ffmpeg transcoding (Celery), the preview/paywall gating engine, owner-only download |
| `apps.enrollments` | Enrollment + wishlist |
| `apps.payments` | Orders, ZarinPal integration, idempotent payment callback |
| `apps.common` | Shared base models, pagination, exception handler, file-type validators |

## Local development

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements/dev.txt
cp .env.example .env   # fill in real values
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Settings are split by environment (`config/settings/{base,dev,prod,test}.py`); `manage.py` defaults to `dev`.

## Tests

```bash
pytest
```

## Code style

- `ruff check .` — lint (includes pydocstyle rules; public functions/classes need a docstring)
- `mypy .` — type checking (django-stubs enabled)
- `pip-audit` — dependency vulnerability scan

## API docs

Once the server is running: `/api/docs/` (Swagger UI), `/api/redoc/`, raw schema at `/api/schema/`.

## Video preview/paywall mechanism

See [docs/adr/0003-video-preview-gating.md](../docs/adr/0003-video-preview-gating.md) — the short version: non-purchasers are only ever handed a URL to a *physically truncated* preview file produced at upload time, never the full file behind a client-side timer.
