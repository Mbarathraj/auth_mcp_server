# DRF backend: users + tasks (SimpleJWT)

Each user logs in, gets a JWT, and can only ever see/change **their own** tasks.

## Setup (Windows PowerShell; on macOS/Linux use `source .venv/bin/activate`)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # then put a real DJANGO_SECRET_KEY in it
python manage.py makemigrations users tasks
python manage.py migrate
python manage.py runserver
```

Run the tests: `python manage.py test`

## Endpoints

| Method | URL | Auth | What it does |
|---|---|---|---|
| POST | `/api/users/register/` | none | Create account `{username, email, password}` |
| POST | `/api/token/` | none | Login `{username, password}` -> `{access, refresh}` |
| POST | `/api/token/refresh/` | none | `{refresh}` -> new `{access}` |
| GET | `/api/users/me/` | Bearer | Current user |
| GET/POST | `/api/tasks/` | Bearer | List my tasks / create a task |
| GET/PUT/PATCH/DELETE | `/api/tasks/<id>/` | Bearer | One of my tasks (404 if it isn't mine) |

Send the access token on every protected call: `Authorization: Bearer <access>`.

## Try it (PowerShell)

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/users/register/ -H "content-type: application/json" -d '{\"username\":\"alice\",\"email\":\"a@x.com\",\"password\":\"Str0ng-pass-123\"}'
curl.exe -X POST http://127.0.0.1:8000/api/token/ -H "content-type: application/json" -d '{\"username\":\"alice\",\"password\":\"Str0ng-pass-123\"}'
curl.exe -X POST http://127.0.0.1:8000/api/tasks/ -H "content-type: application/json" -H "Authorization: Bearer ACCESS_TOKEN" -d '{\"title\":\"Buy milk\"}'
curl.exe http://127.0.0.1:8000/api/tasks/ -H "Authorization: Bearer ACCESS_TOKEN"
```

## How the data isolation works

- `tasks/views.py`: `get_queryset` filters `Task.objects.filter(owner=request.user)`, and
  `perform_create` sets `owner=request.user`. The user comes from the verified JWT.
- `owner` is not in the serializer, so a client can't set or change it.
- Another user's task returns 404, as if it didn't exist.
- Tests in `tasks/tests.py` prove all of this.
