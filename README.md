# Mundial Typer 2026

Aplikacja do typowania wyników meczów Mundialu 2026 dla znajomych. Prywatne ligi z kodem zaproszenia, automatyczne pobieranie wyników, ranking z podium i bonusy za mistrza turnieju.

> [English version below](#mundial-typer-2026-english)

---

## Screenshoty

<!-- Dodaj screenshoty do folderu docs/screenshots/ i odkomentuj poniższe linie -->

<!--
| Dashboard | Mecze | Ranking |
|-----------|-------|---------|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Mecze](docs/screenshots/matches.png) | ![Ranking](docs/screenshots/ranking.png) |

| Moje Typy | Bonusy | Liga |
|-----------|--------|------|
| ![Typy](docs/screenshots/predictions.png) | ![Bonusy](docs/screenshots/bonus.png) | ![Liga](docs/screenshots/league.png) |
-->

> Screenshoty pojawią się po pierwszym deploy.

---

## Funkcje

**Typowanie:**
- Typowanie wyników wszystkich 64 meczów Mundialu 2026
- Zmiana typu przed startem meczu
- Bonusy przed turniejem: mistrz i awanse z grup (deadline: 3. mecz turnieju)
- Odliczanie do końca typowania bonusowego

**Ranking i statystyki:**
- Ranking globalny z podium (złoto/srebro/brąz)
- Ranking w obrębie prywatnej ligi
- Moje typy ze statystykami (skuteczność, rozkład, forma, passa)
- Postęp turnieju na Dashboardzie

**Prywatne ligi:**
- Tworzenie ligi i dołączanie kodem zaproszenia
- Link zaproszenia (`/join/:code`) — dołącza automatycznie po kliknięciu
- Reset kodu zaproszenia przez właściciela
- Pula nagród z automatycznym podziałem 50/30/20%
- Usunięcie ligi (właściciel) / wyjście z ligi (członek)

**Konto:**
- Rejestracja email + hasło, weryfikacja emaila
- Reset hasła przez email (jednorazowy link, ważny 1h)
- Zmiana nicku i hasła w ustawieniach

**Aplikacja:**
- Interfejs responsywny — dark mode, glassmorphism
- Działa na telefonie jak natywna apka (PWA, ikona na ekranie głównym)
- Udostępnianie wyniku (native share API)
- Automatyczne pobieranie wyników z football-data.org (co 5 min)

**Panel admina:**
- Wpisywanie wyników meczów z UI
- Bootstrap danych turnieju z API
- Zarządzanie użytkownikami (weryfikacja emaila, usuwanie kont)
- Podgląd wszystkich prywatnych lig z listą członków
- Reset kodu ligi, kick z ligi

---

## Punktacja

### Mecze — liczy się najwyższy trafiony próg

| Trafienie | Faza grupowa | 1/8 | Ćwierćfinał | Półfinał | Finał |
|-----------|:-----------:|:---:|:-----------:|:--------:|:-----:|
| Dokładny wynik | 5 | 7 | 9 | 11 | 15 |
| Różnica bramek | 3 | 4 | 5 | 6 | 8 |
| Wynik meczu (kto wygrał) | 2 | 3 | 4 | 5 | 6 |

### Bonusy

| Trafienie | Punkty | Kiedy przyznawane |
|-----------|--------|------------------|
| Mistrz turnieju | 20 | Po finale |
| Awans z grupy (za każdą drużynę) | 3 | Po fazie grupowej |

---

## Stack

| Warstwa | Technologia |
|---------|-------------|
| Frontend | React 18 + Vite (JavaScript) |
| Stylowanie | Tailwind CSS, glassmorphism |
| Czcionki | Bebas Neue (display) + Inter (body) |
| Backend | Python 3.12, FastAPI, uvicorn |
| Baza danych | PostgreSQL 16 |
| Auth | JWT (httpOnly cookie) + Argon2id |
| Email | Resend |
| Dane meczów | football-data.org API |
| Hosting frontend | Azure Static Web Apps |
| Hosting backend | Azure Container Apps |
| Hosting bazy | Supabase (PostgreSQL) |
| Mobile | PWA (Progressive Web App) |

---

## Schemat bazy

```
users                     — konta graczy
leagues                   — ligi (Mundial 2026)
teams                     — drużyny z herbami
matches                   — mecze z fazą i statusem
predictions               — typy wyników meczów
bonus_predictions         — typ mistrza turnieju
group_advance_predictions — typy awansów z grup
scoring_rules             — punkty per faza (konfigurowalnie)
private_leagues           — prywatne ligi znajomych
private_league_members    — przynależność do ligi
password_reset_tokens     — tokeny resetu hasła
```

---

## Struktura projektu

```
mundial_typer_2026/
├── mundial-backend/      ← FastAPI (Python)
└── mundial-frontend/     ← React + Vite
```

---

## Endpointy API

| Metoda | Ścieżka | Opis | Auth |
|--------|---------|------|------|
| POST | `/auth/register` | Rejestracja | — |
| POST | `/auth/login` | Logowanie | — |
| POST | `/auth/logout` | Wylogowanie | ✅ |
| GET | `/auth/me` | Dane zalogowanego | ✅ |
| POST | `/auth/forgot-password` | Link do resetu hasła | — |
| POST | `/auth/reset-password` | Ustaw nowe hasło | — |
| GET | `/matches` | Lista meczów | ✅ |
| POST | `/predictions` | Dodaj/zmień typ | ✅ |
| GET | `/predictions/mine` | Moje typy | ✅ |
| POST | `/bonus/champion` | Typuj mistrza | ✅ |
| POST | `/bonus/group-advances` | Typuj awanse | ✅ |
| GET | `/ranking` | Ranking globalny | ✅ |
| GET | `/ranking/{league_id}` | Ranking ligi | ✅ |
| POST | `/leagues` | Utwórz ligę | ✅ |
| POST | `/leagues/join` | Dołącz kodem | ✅ |
| GET | `/leagues/{id}` | Szczegóły ligi | ✅ |
| POST | `/leagues/{id}/leave` | Opuść ligę | ✅ |
| DELETE | `/leagues/{id}` | Usuń ligę (właściciel) | ✅ |
| POST | `/leagues/{id}/reset-code` | Reset kodu | ✅ |
| POST | `/matches/bootstrap` | Pobierz dane z API | ✅ admin |
| POST | `/matches/{id}/result` | Wpisz wynik | ✅ admin |

Pełna dokumentacja: `http://localhost:8000/docs`

---

## Uruchomienie lokalnie

### Docker (najszybciej)

```bash
git clone <repo>
cd mundial_typer_2026

cp mundial-backend/.env.example mundial-backend/.env
# uzupełnij .env: JWT_SECRET, ADMIN_EMAILS

docker compose up --build
```

- Aplikacja: http://localhost:8080
- Swagger: http://localhost:8000/docs

### Dewelopka z hot-reload

**Backend:**
```bash
cd mundial-backend
cp .env.example .env        # uzupełnij JWT_SECRET, FOOTBALL_API_KEY, ADMIN_EMAILS
docker compose up -d        # tylko baza
uv sync
./scripts/migrate.sh
uv run uvicorn main:app --reload
```

**Frontend:**
```bash
cd mundial-frontend
npm install
npm run dev
```

> Wygeneruj `JWT_SECRET`: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`

---

## Zmienne środowiskowe

```env
# baza danych
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=mundial
POSTGRES_PASSWORD=mundial
POSTGRES_DB=mundial

# auth
JWT_SECRET=          # min 32 losowe znaki
JWT_EXPIRE_DAYS=7

# maile
RESEND_API_KEY=      # resend.com
EMAIL_FROM=Mundial Typer <noreply@twojadomena.pl>
REQUIRE_VERIFIED_EMAIL=true   # false na dev

# dane meczów
FOOTBALL_API_KEY=    # football-data.org (wymaga weryfikacji konta)

# dostęp admina
ADMIN_EMAILS=        # przecinek = wielu adminów

# CORS
FRONTEND_URL=http://localhost:5173
```

---

## Deploy (produkcja)

**Azure Static Web Apps + Azure Container Apps + Supabase ≈ $0/mies.**

### 1. Supabase (baza)
- Nowy projekt na [supabase.com](https://supabase.com)
- Uruchom migracje przez SQL editor: `001_init.sql` → `002_seed_mundial_2026.sql`
- Skopiuj connection string

### 2. Azure Container Apps (backend)
```bash
az group create --name mundial-rg --location westeurope
az acr create --name mundialtyper --resource-group mundial-rg --sku Basic
az acr build --registry mundialtyper --image backend:latest ./mundial-backend
az containerapp env create --name mundial-env --resource-group mundial-rg --location westeurope
az containerapp create \
  --name mundial-backend \
  --resource-group mundial-rg \
  --environment mundial-env \
  --image mundialtyper.azurecr.io/backend:latest \
  --min-replicas 0 --max-replicas 3 \
  --target-port 8000 --ingress external \
  --env-vars POSTGRES_HOST=... JWT_SECRET=... FOOTBALL_API_KEY=... \
             RESEND_API_KEY=... REQUIRE_VERIFIED_EMAIL=true \
             ADMIN_EMAILS=twoj@email.com DEV_SEED=false \
             FRONTEND_URL=https://<app>.azurestaticapps.net
```

### 3. Azure Static Web Apps (frontend)
- Azure Portal → Create → Static Web App → połącz z GitHub
- App location: `/mundial-frontend`, Output: `dist`
- Dodaj env: `VITE_API_URL=https://<backend>.azurecontainerapps.io`

### 4. Po deploy — obowiązkowe
- Wejdź na `/admin` → **"Pobierz dane z API"** (bootstrap drużyn i meczów)

### Resend — własna domena (wymagane)

Bez własnej domeny maile trafiają do spamu lub nie dochodzą.

1. Kup domenę (np. Cloudflare Registrar)
2. resend.com → Domains → Add Domain
3. Dodaj rekordy DNS (SPF, DKIM, DMARC) wskazane przez Resend
4. Ustaw `EMAIL_FROM=Mundial Typer <noreply@twojadomena.pl>`

### Koszt

| Serwis | Plan | Koszt |
|--------|------|-------|
| Azure Static Web Apps | Free | $0 |
| Azure Container Apps | Free tier (180k vCPU-sec/mies.) | ~$0 |
| Supabase | Free (500MB) | $0 |
| football-data.org | Free | $0 |
| Resend | Free (3000 maili/mies.) | $0 |
| **Razem** | | **~$0/mies.** |

---

## Bezpieczeństwo

- Hasła: **Argon2id** (pwdlib) — nieodwracalne
- Sesja: **JWT w httpOnly cookie** — nie localStorage
- SQL: wyłącznie **parametryzowane zapytania** — zero f-stringów z danymi usera
- Rate limiting: max 5 prób logowania/minutę
- Email weryfikacyjny przy rejestracji
- Reset hasła przez jednorazowy token ważny 1h
- HTTPS automatycznie na Azure + Cloudflare

---

## Testy

```bash
cd mundial-backend
uv run pytest
```

---

---

# Mundial Typer 2026 (English)

A World Cup 2026 prediction app for friends. Private leagues with invite codes, automatic results, leaderboard with podium and tournament bonuses.

> [Wersja polska powyżej](#mundial-typer-2026)

---

## Screenshots

<!-- Add screenshots to docs/screenshots/ and uncomment below -->

> Screenshots will appear after the first deploy.

---

## Features

- Predict all 64 World Cup 2026 matches, change picks before kickoff
- Pre-tournament bonuses: champion pick and group stage advances
- Global leaderboard with gold/silver/bronze podium
- Private leagues — invite by code or shareable link (`/join/:code`)
- Dashboard with tournament progress, league position and streak tracker
- Automatic result fetching from football-data.org every 5 minutes
- PWA — installable on mobile home screen
- Share your ranking position (native share API)
- Admin panel: bootstrap data, set results, manage users and leagues

---

## Scoring

### Matches — highest matching tier wins

| Tier | Group | R16 | QF | SF | Final |
|------|:-----:|:---:|:--:|:--:|:-----:|
| Exact score | 5 | 7 | 9 | 11 | 15 |
| Goal difference | 3 | 4 | 5 | 6 | 8 |
| Correct winner | 2 | 3 | 4 | 5 | 6 |

### Bonuses

| Pick | Points | Awarded |
|------|--------|---------|
| Tournament champion | 20 | After final |
| Group advance (per team) | 3 | After group stage |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 + Vite |
| Styling | Tailwind CSS |
| Fonts | Bebas Neue + Inter |
| Backend | Python 3.12, FastAPI |
| Database | PostgreSQL 16 |
| Auth | JWT (httpOnly cookie) + Argon2id |
| Email | Resend |
| Match data | football-data.org API |
| Hosting | Azure Static Web Apps + Container Apps |
| Database hosting | Supabase |
| Mobile | PWA |

---

## Run Locally

```bash
git clone <repo>
cd mundial_typer_2026

cp mundial-backend/.env.example mundial-backend/.env
# set JWT_SECRET and ADMIN_EMAILS

docker compose up --build
# App: http://localhost:8080
# Swagger: http://localhost:8000/docs
```

---

## Deploy

**Azure Static Web Apps + Azure Container Apps + Supabase ≈ $0/month**

See the Polish section above for full step-by-step instructions.

Key environment variables for production:
```
REQUIRE_VERIFIED_EMAIL=true
ADMIN_EMAILS=your@email.com
FOOTBALL_API_KEY=...
RESEND_API_KEY=...
FRONTEND_URL=https://your-app.azurestaticapps.net
```

After deploy: go to `/admin` → **"Pobierz dane z API"** to bootstrap teams and fixtures.
