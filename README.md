# ⚽ Mundial Typer

Aplikacja do typowania wyników meczów Mundialu 2026 dla znajomych.
Prywatne ligi z kodem zaproszenia, automatyczne pobieranie wyników, ranking i bonusy za mistrza turnieju.

> 🇬🇧 [English version below](#-mundial-typer-english)

---

## Funkcje

- Konto użytkownika (email + hasło, bezpieczne bcrypt + JWT)
- Prywatna liga dla znajomych z unikalnym kodem zaproszenia
- Typowanie wyników wszystkich 64 meczów Mundialu 2026
- Bonus przed turniejem: mistrz turnieju i awanse z grup
- Automatyczne pobieranie wyników z football-data.org (co 5 minut)
- Ranking globalny i w obrębie prywatnej ligi
- Wyższe punkty w fazach pucharowych (mnożniki)
- Interfejs responsywny — działa na telefonie jak apka (PWA)
- Reset hasła przez email

---

## System punktacji

### Mecze

Liczy się najwyższy trafiony próg — punkty się nie sumują.

| Trafienie | Faza grupowa | 1/8 finału | Ćwierćfinał | Półfinał | Finał |
|-----------|:-----------:|:----------:|:-----------:|:--------:|:-----:|
| Dokładny wynik | 5 | 7 | 9 | 11 | 15 |
| Różnica bramek | 3 | 4 | 5 | 6 | 8 |
| Tylko wynik (kto wygrał) | 2 | 3 | 4 | 5 | 6 |

### Bonusy (typowane przed startem turnieju)

| Trafienie | Punkty |
|-----------|--------|
| Mistrz turnieju | 20 |
| Awans z grupy (za każdą drużynę) | 3 |

---

## Stack technologiczny

| Warstwa | Technologia |
|---------|-------------|
| Frontend | React + Vite (JavaScript) |
| Stylowanie | Tailwind CSS |
| Backend | Python 3.11+, FastAPI, uvicorn |
| Baza danych | PostgreSQL 16 |
| Auth | JWT + bcrypt (passlib) |
| E-mail | Resend (3000 maili/mies. za darmo) |
| Dane meczów | football-data.org API (darmowy tier) |
| Hosting frontend | Vercel (darmowy) |
| Hosting backend | Railway (~$5/mies.) |
| Hosting bazy | Supabase (darmowy, 500 MB) |
| Migracje bazy | Raw SQL pliki (`db/migrations/NNN_nazwa.sql`) |
| Mobile | PWA (Progressive Web App) |

---

## Schemat bazy danych

```
users                    — konta graczy
leagues                  — ligi (Mundial, Ekstraklasa...)
teams                    — drużyny
matches                  — mecze z fazą (group/round_of_16/quarter/semi/final)
predictions              — typy wyników meczów
bonus_predictions        — typ mistrza turnieju
group_advance_predictions— typy awansów z grup
scoring_rules            — konfiguracja punktów per faza
private_leagues          — prywatne ligi znajomych (z join_code)
private_league_members   — przynależność do prywatnej ligi
```

---

## Struktura projektu

Projekt składa się z dwóch osobnych repozytoriów:

```
mundial-backend/           ← FastAPI, deploy na Railway
├── domain/
│   ├── scoring.py         ← czysta funkcja punktująca
│   ├── match_results.py   ← przeliczanie punktów po meczu
│   └── predictions.py     ← walidacja deadline
├── db/
│   ├── connection.py      ← connection pool (psycopg2)
│   ├── queries.py         ← SQL-e jako stałe stringi
│   └── migrations/        ← numerowane pliki .sql
├── routers/
│   ├── auth.py            ← /auth/register, /auth/login, /auth/forgot-password
│   ├── matches.py         ← GET /matches, GET /matches/{id}
│   ├── predictions.py     ← POST /predictions
│   ├── bonus.py           ← POST /bonus/champion, /bonus/group-advances
│   ├── ranking.py         ← GET /ranking, GET /ranking/{league_id}
│   ├── leagues.py         ← POST /leagues, POST /leagues/join
│   └── admin.py           ← POST /matches/{id}/result
├── services/
│   ├── football_api.py    ← pobieranie wyników z football-data.org
│   └── email.py           ← wysyłanie maili przez Resend
├── schemas/
│   └── models.py          ← Pydantic modele request/response
├── .env.example
└── main.py

mundial-frontend/          ← React + Vite, deploy na Vercel
├── public/
│   ├── manifest.json      ← PWA
│   └── icon-512.png
├── src/
│   ├── api/               ← funkcje fetch do backendu
│   ├── components/        ← przyciski, tabele, formularze
│   ├── pages/
│   │   ├── Login.jsx
│   │   ├── Register.jsx
│   │   ├── Matches.jsx
│   │   ├── Ranking.jsx
│   │   └── League.jsx
│   └── context/
│       └── AuthContext.jsx ← JWT token, zalogowany user
└── vite.config.js
```

---

## Endpointy API

| Metoda | Ścieżka | Opis | Auth |
|--------|---------|------|------|
| POST | `/auth/register` | Rejestracja | — |
| POST | `/auth/login` | Logowanie, zwraca JWT | — |
| POST | `/auth/forgot-password` | Wyślij link do resetu hasła | — |
| POST | `/auth/reset-password` | Ustaw nowe hasło przez token | — |
| GET | `/matches` | Lista wszystkich meczów | ✅ |
| GET | `/matches/{id}` | Szczegóły meczu | ✅ |
| POST | `/predictions` | Dodaj typ (tylko przed startem) | ✅ |
| GET | `/predictions/mine` | Moje typy | ✅ |
| POST | `/bonus/champion` | Typuj mistrza turnieju | ✅ |
| POST | `/bonus/group-advances` | Typuj awanse z grup | ✅ |
| GET | `/ranking` | Ranking globalny | ✅ |
| GET | `/ranking/{league_id}` | Ranking prywatnej ligi | ✅ |
| POST | `/leagues` | Stwórz prywatną ligę | ✅ |
| POST | `/leagues/join` | Dołącz do ligi kodem | ✅ |
| GET | `/leagues/{id}` | Szczegóły ligi | ✅ |
| POST | `/matches/{id}/result` | Wpisz wynik (admin) | ✅ admin |

Pełna dokumentacja auto-generowana przez FastAPI: `http://localhost:8000/docs`

---

## Jak uruchomić lokalnie

### Wymagania

- Python 3.11+
- Node.js 18+
- Docker (PostgreSQL)
- [uv](https://github.com/astral-sh/uv) — menedżer paczek Python

### Backend

```bash
cd mundial-backend

# utwórz .env
cp .env.example .env
# uzupełnij: klucz football-data.org, klucz Resend, sekret JWT

# uruchom bazę danych
docker compose up -d

# zainstaluj zależności
uv sync

# uruchom migracje (ręcznie w kolejności — każda nowa zmiana schematu to nowy plik)
psql -h localhost -U mundial -d mundial -f db/migrations/001_init.sql
psql -h localhost -U mundial -d mundial -f db/migrations/002_seed_mundial_2026.sql

# uruchom serwer
uv run uvicorn main:app --reload
```

Backend dostępny pod: http://localhost:8000
Swagger UI: http://localhost:8000/docs

### Frontend

```bash
cd mundial-frontend

npm install
npm run dev
```

Frontend dostępny pod: http://localhost:5173

---

## Zmienne środowiskowe (backend)

Plik `.env` — **nigdy nie wrzucaj do repozytorium**.

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=mundial
POSTGRES_PASSWORD=mundial
POSTGRES_DB=mundial

JWT_SECRET=twoj-tajny-klucz-min-32-znaki
JWT_EXPIRE_DAYS=7

FOOTBALL_API_KEY=twoj-klucz-z-football-data.org
RESEND_API_KEY=twoj-klucz-z-resend.com
FRONTEND_URL=http://localhost:5173
```

---

## Bezpieczeństwo

- Hasła hashowane **bcrypt** z solą — nieodwracalne
- Sesje jako **JWT token** w httpOnly cookie (nie localStorage)
- **HTTPS** na produkcji (automatyczne certyfikaty Vercel + Railway)
- Rate limiting: max 5 prób logowania/minutę
- SQL wyłącznie przez parametryzowane zapytania (zero f-stringów)
- Weryfikacja emaila po rejestracji
- Reset hasła przez jednorazowy token ważny 1 godzinę

---

## Deploy na produkcję

### Baza danych (Supabase)

1. Załóż konto na [supabase.com](https://supabase.com)
2. Stwórz nowy projekt → skopiuj connection string
3. Uruchom migracje przez Supabase SQL editor

### Backend (Railway)

1. Załóż konto na [railway.app](https://railway.app)
2. Połącz z repozytorium GitHub `mundial-backend`
3. Ustaw zmienne środowiskowe w panelu Railway
4. Railway automatycznie deployuje przy każdym push na `main`

### Frontend (Vercel)

1. Załóż konto na [vercel.com](https://vercel.com)
2. Połącz z repozytorium GitHub `mundial-frontend`
3. Ustaw zmienną `VITE_API_URL=https://twoj-backend.railway.app`
4. Vercel automatycznie deployuje przy każdym push na `main`

### Koszt

| Serwis | Plan | Koszt |
|--------|------|-------|
| Vercel | Hobby (darmowy) | $0 |
| Railway | Starter | ~$5/mies. |
| Supabase | Free | $0 |
| football-data.org | Free | $0 |
| Resend | Free (3000 maili/mies.) | $0 |
| **Razem** | | **~$5/mies.** |

---

## Plan budowania (6 tygodni)

| Tydzień | Co budujemy |
|---------|-------------|
| 1-2 | Auth (rejestracja, logowanie, JWT), podstawowy deploy |
| 3 | Mecze + typowanie wyników |
| 4 | Ranking + prywatne ligi z kodem zaproszenia |
| 5 | Auto wyniki z API + bonusy (mistrz, awanse) |
| 6 | PWA, reset hasła, testy, finalne szlify |

Mundial 2026 startuje **11 czerwca** — deadline na gotową apkę.

---

## Uruchomienie testów

```bash
# backend
cd mundial-backend
uv run pytest

# frontend
cd mundial-frontend
npm run test
```

---

---

# ⚽ Mundial Typer (English)

A football World Cup 2026 prediction app for friends.
Private leagues with invite codes, automatic results, leaderboard and tournament bonuses.

> 🇵🇱 [Wersja polska powyżej](#-mundial-typer)

---

## Features

- User accounts (email + password, secure bcrypt + JWT)
- Private leagues for friends with unique invite codes
- Predict results for all 64 World Cup 2026 matches
- Tournament bonuses: champion pick and group stage advances
- Automatic result fetching from football-data.org (every 5 minutes)
- Global and per-league leaderboard
- Higher points in knockout stages (multipliers)
- Responsive UI — installable on phone as PWA
- Password reset via email

---

## Scoring System

### Matches

Only the highest matching tier is awarded — points do not stack.

| Match | Group stage | Round of 16 | Quarter | Semi | Final |
|-------|:-----------:|:-----------:|:-------:|:----:|:-----:|
| Exact score | 5 | 7 | 9 | 11 | 15 |
| Goal difference | 3 | 4 | 5 | 6 | 8 |
| Correct result (who won) | 2 | 3 | 4 | 5 | 6 |

### Bonuses (picked before the tournament starts)

| Pick | Points |
|------|--------|
| Tournament champion | 20 |
| Group stage advance (per team) | 3 |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React + Vite (JavaScript) |
| Styling | Tailwind CSS |
| Backend | Python 3.11+, FastAPI, uvicorn |
| Database | PostgreSQL 16 |
| Auth | JWT + bcrypt (passlib) |
| Email | Resend (3,000 emails/month free) |
| Match data | football-data.org API (free tier) |
| Frontend hosting | Vercel (free) |
| Backend hosting | Railway (~$5/month) |
| DB hosting | Supabase (free, 500 MB) |
| Mobile | PWA (Progressive Web App) |

---

## API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/auth/register` | Create account | — |
| POST | `/auth/login` | Log in, returns JWT | — |
| POST | `/auth/forgot-password` | Send password reset link | — |
| POST | `/auth/reset-password` | Set new password via token | — |
| GET | `/matches` | All matches | ✅ |
| GET | `/matches/{id}` | Match details | ✅ |
| POST | `/predictions` | Add prediction (before kickoff only) | ✅ |
| GET | `/predictions/mine` | My predictions | ✅ |
| POST | `/bonus/champion` | Pick tournament champion | ✅ |
| POST | `/bonus/group-advances` | Pick group stage advances | ✅ |
| GET | `/ranking` | Global leaderboard | ✅ |
| GET | `/ranking/{league_id}` | Private league leaderboard | ✅ |
| POST | `/leagues` | Create private league | ✅ |
| POST | `/leagues/join` | Join league with code | ✅ |
| GET | `/leagues/{id}` | League details | ✅ |
| POST | `/matches/{id}/result` | Set match result (admin) | ✅ admin |

Full auto-generated docs at: `http://localhost:8000/docs`

---

## How to Run Locally

### Requirements

- Python 3.11+
- Node.js 18+
- Docker (PostgreSQL)
- [uv](https://github.com/astral-sh/uv) — Python package manager

### Backend

```bash
cd mundial-backend

cp .env.example .env
# fill in: football-data.org key, Resend key, JWT secret

docker compose up -d

uv sync

psql -h localhost -U mundial -d mundial -f db/migrations/001_init.sql
psql -h localhost -U mundial -d mundial -f db/migrations/002_seed_mundial_2026.sql

uv run uvicorn main:app --reload
```

Backend: http://localhost:8000
Swagger UI: http://localhost:8000/docs

### Frontend

```bash
cd mundial-frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

---

## Environment Variables (backend)

`.env` file — **never commit to repository**.

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=mundial
POSTGRES_PASSWORD=mundial
POSTGRES_DB=mundial

JWT_SECRET=your-secret-key-min-32-chars
JWT_EXPIRE_DAYS=7

FOOTBALL_API_KEY=your-key-from-football-data.org
RESEND_API_KEY=your-key-from-resend.com
FRONTEND_URL=http://localhost:5173
```

---

## Security

- Passwords hashed with **bcrypt** + salt — irreversible
- Sessions as **JWT token** in httpOnly cookie (not localStorage)
- **HTTPS** in production (automatic certs on Vercel + Railway)
- Rate limiting: max 5 login attempts/minute
- SQL exclusively via parameterised queries (no f-strings with user data)
- Email verification on registration
- Password reset via single-use token valid for 1 hour

---

## Production Deploy

### Database (Supabase)

1. Sign up at [supabase.com](https://supabase.com)
2. Create a new project → copy connection string
3. Run migrations via Supabase SQL editor

### Backend (Railway)

1. Sign up at [railway.app](https://railway.app)
2. Connect to GitHub repo `mundial-backend`
3. Set environment variables in Railway dashboard
4. Railway auto-deploys on every push to `main`

### Frontend (Vercel)

1. Sign up at [vercel.com](https://vercel.com)
2. Connect to GitHub repo `mundial-frontend`
3. Set `VITE_API_URL=https://your-backend.railway.app`
4. Vercel auto-deploys on every push to `main`

### Monthly Cost

| Service | Plan | Cost |
|---------|------|------|
| Vercel | Hobby (free) | $0 |
| Railway | Starter | ~$5/mo |
| Supabase | Free | $0 |
| football-data.org | Free | $0 |
| Resend | Free (3k emails/mo) | $0 |
| **Total** | | **~$5/mo** |

---

## Build Timeline (6 weeks)

| Week | What we build |
|------|---------------|
| 1–2 | Auth (register, login, JWT), basic deploy |
| 3 | Matches + predictions |
| 4 | Leaderboard + private leagues with invite codes |
| 5 | Auto results from API + bonuses (champion, advances) |
| 6 | PWA, password reset, tests, final polish |

World Cup 2026 kicks off **June 11** — ship before that.

---

## Running Tests

```bash
# backend
cd mundial-backend
uv run pytest

# frontend
cd mundial-frontend
npm run test
```
