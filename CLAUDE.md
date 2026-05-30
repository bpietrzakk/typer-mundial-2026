# Mundial Typer — CLAUDE.md

Aplikacja do typowania wyników meczów Mundialu 2026 dla znajomych.
Prywatne ligi z kodem zaproszenia, automatyczne wyniki z API, ranking, bonusy za mistrza i awanse z grup.

Projekt dwuosobowy (bartek + kolega). Backend w FastAPI, frontend w React.

---

## ŻELAZNE ZASADY (czytaj na początku każdej sesji)

1. **Funkcja punktująca jest czysta** — zero bazy, zero HTTP, zero side effects. Mieszka w `domain/scoring.py`. Każda zmiana logiki = nowe testy w `tests/test_scoring.py` PRZED zmianą implementacji.

2. **Warstwy się nie krzyżują.**
   - `domain/` nie importuje z `db/`, `routers/` ani `fastapi`
   - `db/` nie importuje z `routers/`
   - `routers/` nie piszą SQL — wywołują funkcje z `db/queries.py`

3. **Sekrety przez `.env`** — JWT secret, klucz API football-data.org, klucz Resend, hasło do bazy. NIGDY w kodzie ani w repo. `.env` jest w `.gitignore`, `.env.example` jest w repo.

4. **Migracje są wersjonowane** w `db/migrations/NNN_nazwa.sql`. Każda zmiana schematu = nowy plik. Nigdy nie edytuj wcześniejszych. Na górze każdego pliku: data i autor.

5. **Auth przez JWT w httpOnly cookie** — nigdy nie trzymaj tokenu w localStorage. Endpoint `/auth/refresh` odnawia token zanim wygaśnie.

6. **SQL tylko przez parametryzowane zapytania** — zero f-stringów z danymi użytkownika. Każdy SQL jako stała stringowa w `db/queries.py`.

7. **Małe kroki.** Jedno zadanie z MVP-checklisty naraz. Po skończeniu — odpal, przetestuj endpoint w `/docs`, dopiero potem następne.

---

## Stack

### Backend (`mundial-backend/`)
- **Język:** Python 3.11+
- **Framework:** FastAPI + uvicorn
- **Menedżer paczek:** `uv` (zależności w `pyproject.toml`, lock w `uv.lock`)
- **Baza:** PostgreSQL 16 (lokalnie w Dockerze, produkcja na Supabase)
- **Dostęp do DB:** `psycopg2-binary` + jawne SQL (bez ORM)
- **Auth:** JWT (`python-jose`) + bcrypt (`passlib[bcrypt]`)
- **Email:** Resend (`resend` SDK)
- **Dane meczów:** football-data.org API (`httpx` do zapytań)
- **Walidacja:** Pydantic (wbudowany w FastAPI)
- **Testy:** pytest + httpx (TestClient)
- **Format/lint:** ruff

### Frontend (`mundial-frontend/`)
- **Framework:** React 18 + Vite (JavaScript, bez TypeScript)
- **Stylowanie:** Tailwind CSS
- **Routing:** React Router v6
- **HTTP:** axios
- **Auth:** AuthContext (JWT token trzymany w memory + httpOnly cookie)
- **Mobile:** PWA (manifest.json + service worker)

---

## Reguły biznesowe — Punktacja

### Mecze — trzy progi, liczy się najwyższy

| Trafienie | Faza grupowa | 1/8 | Ćwierćfinał | Półfinał | Finał |
|-----------|:-----------:|:---:|:-----------:|:--------:|:-----:|
| Dokładny wynik | 5 | 7 | 9 | 11 | 15 |
| Różnica bramek | 3 | 4 | 5 | 6 | 8 |
| Tylko wynik (kto wygrał) | 2 | 3 | 4 | 5 | 6 |

Punkty są przechowywane w tabeli `scoring_rules` (osobny wiersz per faza). Funkcja `calculate_points()` dostaje je jako argument — nic nie jest hardkodowane.

**Remisy:** trafiony remis który nie jest dokładny zawsze dostaje punkty za różnicę bramek (0 = 0), nigdy za wynik. Zamierzone.

### Bonusy (typowane przed startem turnieju, deadline = 11 czerwca 2026 12:00 UTC)

| Typ bonusu | Punkty | Kiedy przyznawane |
|-----------|--------|------------------|
| Mistrz turnieju (dokładnie) | 20 | Po finale |
| Awans z grupy (za każdą drużynę) | 3 | Po zakończeniu fazy grupowej |

### Przykłady testów jednostkowych dla `tests/test_scoring.py`

| Typowane | Rzeczywiste | Faza | Oczekiwane |
|----------|-------------|------|-----------|
| 2:1 | 2:1 | group | 5 (dokładny) |
| 2:1 | 3:2 | group | 3 (różnica) |
| 2:1 | 4:0 | group | 2 (wynik) |
| 2:1 | 0:2 | group | 0 (pudło) |
| 1:1 | 2:2 | group | 3 (różnica, remis) |
| 2:1 | 2:1 | final | 15 (dokładny w finale) |
| 2:1 | 3:2 | final | 8 (różnica w finale) |
| 2:1 | 4:0 | final | 6 (wynik w finale) |

---

## Reguły biznesowe — Deadline typowania

- Typ meczu można dodać tylko jeśli `kickoff_at > NOW()`. Walidacja w `domain/predictions.py` (czysta funkcja). Router zwraca HTTP 409 jeśli po terminie.
- Bonusy (mistrz, awanse) można typować tylko przed startem turnieju (`2026-06-11 12:00 UTC`). Stała `TOURNAMENT_START` w `domain/bonuses.py`.
- Po wpisaniu wyniku meczu system automatycznie przelicza punkty dla wszystkich typów tego meczu. Jedyne miejsce gdzie powstaje `points_awarded` to `domain/match_results.py`.

---

## Reguły biznesowe — Auth

- Rejestracja: nick + email + hasło. Email musi być unikalny. Po rejestracji wysyłamy email weryfikacyjny (Resend).
- Logowanie: email + hasło. Zwracamy JWT w httpOnly cookie (nie w body). Token ważny 7 dni.
- Refresh: endpoint `/auth/refresh` zwraca nowy token jeśli stary jest ważny. Frontend wywołuje automatycznie.
- Reset hasła: `/auth/forgot-password` wysyła email z linkiem. Link zawiera jednorazowy token ważny 1 godzinę.
- Rate limiting: max 5 prób logowania na minutę per IP. Blokada na 15 minut.
- Hasła: bcrypt z solą, koszt factor 12. Nigdy nie przechowujemy plain text.

---

## Reguły biznesowe — Prywatne ligi

- Każda liga ma unikalny `join_code` (8 znaków, losowy). Twórca ligi może go zresetować.
- Dołączenie do ligi: POST `/leagues/join` z `join_code`. Każdy user może należeć do wielu lig.
- Ranking w lidze: te same punkty co globalnie, ale filtrowane do członków danej ligi.
- Właściciel ligi może wpisywać wyniki meczów (admin flag w `private_league_members`).

---

## Reguły biznesowe — Automatyczne wyniki

- Background job odpytuje football-data.org co 5 minut w trakcie trwania meczów (status `IN_PLAY` lub `FINISHED`).
- Gdy mecz zmienia status na `FINISHED` w API: pobieramy wynik, wywołujemy logikę domenową, zapisujemy punkty do bazy.
- Jeden mecz jest przeliczany tylko raz — gdy `matches.status` zmieni się na `finished`. Potem ignorujemy.
- W razie błędu API: logujemy błąd, nie crashujemy — spróbujemy ponownie za 5 minut.

---

## Architektura — warstwy (backend)

```
HTTP Client (przeglądarka / Swagger UI)
   ↓
REST API (FastAPI, routers/)      ← przyjmuje request, zwraca response
   ↓ wywołuje
Logika domenowa (domain/)         ← czysta, testowalna, bez I/O
   ↓ używa
Dostęp do danych (db/)            ← SQL, connection pool
   ↓
PostgreSQL (Supabase)
```

Serwisy zewnętrzne (`services/`) są wywoływane z routerów, nie z domeny:
- `services/football_api.py` → wywołuje router admin przy auto-update wyników
- `services/email.py` → wywołują routery auth

---

## Model danych

```sql
users
    id, nick, email, password_hash, email_verified, created_at

leagues                         -- prawdziwe ligi piłkarskie
    id, name, country, season

teams
    id, name, short_name, league_id

matches
    id, league_id, home_team_id, away_team_id,
    kickoff_at, home_goals, away_goals,
    status,                     -- 'scheduled' | 'live' | 'finished'
    stage,                      -- 'group' | 'round_of_16' | 'quarter' | 'semi' | 'final'
    external_id                 -- id meczu w football-data.org API

scoring_rules
    id, stage, exact_pts, diff_pts, tendency_pts
    -- osobny wiersz per faza: group=5/3/2, round_of_16=7/4/3, ..., final=15/8/6

predictions
    id, user_id, match_id, pred_home, pred_away, points_awarded, created_at
    UNIQUE (user_id, match_id)

bonus_predictions
    id, user_id, private_league_id, champion_team_id, points_awarded, created_at
    UNIQUE (user_id, private_league_id)

group_advance_predictions
    id, user_id, private_league_id, group_name, team_id, points_awarded, created_at
    UNIQUE (user_id, private_league_id, group_name, team_id)

private_leagues
    id, name, owner_user_id, join_code, created_at

private_league_members
    private_league_id, user_id, is_admin, joined_at
    PRIMARY KEY (private_league_id, user_id)

password_reset_tokens
    id, user_id, token_hash, expires_at, used_at
```

**Ranking** to zapytanie, nie tabela:
```sql
SELECT u.id, u.nick,
       COALESCE(SUM(p.points_awarded), 0)
       + COALESCE(SUM(bp.points_awarded), 0)
       + COALESCE(SUM(gap.points_awarded), 0) AS total_points
FROM users u
LEFT JOIN predictions p         ON p.user_id = u.id
LEFT JOIN matches m             ON p.match_id = m.id AND m.status = 'finished'
LEFT JOIN bonus_predictions bp  ON bp.user_id = u.id
LEFT JOIN group_advance_predictions gap ON gap.user_id = u.id
-- opcjonalny filtr: JOIN private_league_members plm ON plm.user_id = u.id AND plm.private_league_id = ?
GROUP BY u.id, u.nick
ORDER BY total_points DESC
```

---

## Układ katalogów — widok z góry

```
mundial_typer_2026/              ← jeden git repo
├── .gitignore
├── CLAUDE.md
├── README.md
├── mundial-backend/
└── mundial-frontend/
```

---

## Układ katalogów (backend)

```
mundial-backend/
├── .env.example
├── pyproject.toml
├── uv.lock
├── docker-compose.yml
├── main.py                         # tworzy app FastAPI, rejestruje routery, background jobs
├── domain/
│   ├── __init__.py
│   ├── scoring.py                  # CZYSTA funkcja calculate_points(pred_h, pred_a, real_h, real_a, rules) -> int
│   ├── match_results.py            # calculate_match_points(predictions, real_h, real_a, rules) -> list
│   ├── predictions.py              # is_prediction_allowed(kickoff_at) -> bool
│   └── bonuses.py                  # is_bonus_allowed(now) -> bool, calculate_advance_points(pred, real) -> int
├── db/
│   ├── __init__.py
│   ├── connection.py               # get_conn() / release_conn() — SimpleConnectionPool
│   ├── queries.py                  # SQL jako stałe stringi, funkcje opakowujące
│   └── migrations/
│       ├── 001_init.sql            # schemat wszystkich tabel
│       └── 002_seed_mundial_2026.sql # drużyny, mecze, scoring_rules per faza
├── routers/
│   ├── __init__.py
│   ├── auth.py                     # /auth/register, /login, /logout, /refresh, /forgot-password, /reset-password
│   ├── matches.py                  # GET /matches, GET /matches/{id}
│   ├── predictions.py              # POST /predictions, GET /predictions/mine
│   ├── bonus.py                    # POST /bonus/champion, POST /bonus/group-advances
│   ├── ranking.py                  # GET /ranking, GET /ranking/{league_id}
│   ├── leagues.py                  # POST /leagues, POST /leagues/join, GET /leagues/{id}
│   └── admin.py                    # POST /matches/{id}/result (wpisanie wyniku)
├── services/
│   ├── __init__.py
│   ├── football_api.py             # pobieranie wyników z football-data.org
│   └── email.py                    # wysyłanie maili przez Resend
├── schemas/
│   ├── __init__.py
│   └── models.py                   # Pydantic modele request/response
└── tests/
    ├── test_scoring.py             # unit testy calculate_points() — wszystkie 8+ przypadków
    ├── test_predictions.py         # unit testy walidacji deadline
    ├── test_bonuses.py             # unit testy logiki bonusów
    └── test_api.py                 # testy endpointów przez httpx TestClient
```

---

## Układ katalogów (frontend)

```
mundial-frontend/
├── .env.example                    # VITE_API_URL=http://localhost:8000
├── vite.config.js
├── package.json
├── tailwind.config.js
├── public/
│   ├── manifest.json               # PWA — name, icons, display: standalone
│   ├── sw.js                       # service worker (cache offline)
│   └── icon-512.png                # ikona apki
└── src/
    ├── main.jsx
    ├── App.jsx                     # router, AuthProvider
    ├── api/
    │   ├── auth.js                 # login(), register(), logout(), refresh()
    │   ├── matches.js              # getMatches(), getMatch(id)
    │   ├── predictions.js          # addPrediction(), getMyPredictions()
    │   ├── ranking.js              # getRanking(), getLeagueRanking(id)
    │   └── leagues.js              # createLeague(), joinLeague(code)
    ├── context/
    │   └── AuthContext.jsx         # currentUser, login(), logout(), isLoggedIn
    ├── components/
    │   ├── Navbar.jsx
    │   ├── MatchCard.jsx
    │   ├── PredictionForm.jsx
    │   ├── RankingTable.jsx
    │   └── LeagueCard.jsx
    └── pages/
        ├── Login.jsx
        ├── Register.jsx
        ├── Matches.jsx             # lista meczów z podziałem na fazy
        ├── MyPredictions.jsx       # moje typy i punkty
        ├── Ranking.jsx             # ranking globalny / ligi
        ├── League.jsx              # widok prywatnej ligi
        └── BonusPicks.jsx          # typowanie mistrza i awansów
```

---

## Konwencje

- **Komentarze w kodzie:** po angielsku, krótkie zdania bez zbędnej interpunkcji, styl junior/mid. Opisują CO i PO CO, nie JAK.
  - dobrze: `# check if match hasn't started yet`
  - źle: `# Initialize the prediction validation process by comparing timestamps`
- `snake_case` w Pythonie i SQL, `camelCase` w JavaScript/React.
- Funkcje w `domain/` — pure, bez I/O. Cały I/O robi `db/` i `routers/`.
- SQL trzymany w `db/queries.py` jako stałe stringi, parametryzowany przez `%s`.
- Pydantic schema dla każdego request body i response w `schemas/models.py`.
- Importy: `domain` nie importuje z `db` ani `routers`. `db` nie importuje z `routers`.
- Komunikaty błędów API po polsku (HTTP responses), kod po angielsku.
- React komponenty — jeden plik = jeden komponent. Props przez destrukturyzację.
- Axios interceptor w `src/api/` automatycznie dołącza token i obsługuje 401 (redirect do /login).

---

## Jak odpalić lokalnie

### Backend

```bash
cd mundial-backend

# zmienne środowiskowe
cp .env.example .env
# uzupełnij .env: FOOTBALL_API_KEY, RESEND_API_KEY, JWT_SECRET

# baza danych
docker compose up -d

# zależności Python
uv sync

# migracje (ręcznie w kolejności)
psql -h localhost -U mundial -d mundial -f db/migrations/001_init.sql
psql -h localhost -U mundial -d mundial -f db/migrations/002_seed_mundial_2026.sql

# serwer (--reload = restart przy zmianie pliku)
uv run uvicorn main:app --reload

# testy
uv run pytest
```

Backend: http://localhost:8000 | Swagger UI: http://localhost:8000/docs

### Frontend

```bash
cd mundial-frontend

cp .env.example .env
# ustaw VITE_API_URL=http://localhost:8000

npm install
npm run dev
```

Frontend: http://localhost:5173

---

## Zmienne środowiskowe (backend)

```env
# baza danych
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=mundial
POSTGRES_PASSWORD=mundial
POSTGRES_DB=mundial

# auth
JWT_SECRET=min-32-znakowy-losowy-string
JWT_EXPIRE_DAYS=7

# zewnętrzne API
FOOTBALL_API_KEY=twoj-klucz-z-football-data.org
RESEND_API_KEY=twoj-klucz-z-resend.com

# frontend URL (do linków w emailach)
FRONTEND_URL=http://localhost:5173
```

---

## MVP — definicja "gotowe"

### Backend
- [ ] Migracja 001: pełny schemat (wszystkie tabele)
- [ ] Migracja 002: seed — drużyny Mundialu 2026, wszystkie 64 mecze, scoring_rules per faza
- [ ] `domain/scoring.py` — `calculate_points()` z testami dla wszystkich faz
- [ ] `POST /auth/register` + `POST /auth/login` — JWT w httpOnly cookie
- [ ] `GET /matches` — lista meczów z podziałem na fazy
- [ ] `POST /predictions` — dodaj typ (HTTP 409 po starcie meczu)
- [ ] `GET /ranking` — globalny ranking
- [ ] `POST /leagues` + `POST /leagues/join` — prywatne ligi
- [ ] `GET /ranking/{league_id}` — ranking w lidze
- [ ] `POST /matches/{id}/result` — wpisz wynik → punkty
- [ ] Auto-pobieranie wyników z football-data.org (background job)

### Frontend
- [ ] Strona logowania i rejestracji
- [ ] Lista meczów (grupowa / play-off)
- [ ] Formularz typowania (tylko scheduled mecze)
- [ ] Ranking globalny
- [ ] Widok prywatnej ligi + dołączanie kodem
- [ ] Typowanie mistrza turnieju i awansów z grup
- [ ] PWA: manifest.json + ikona (instalacja na telefonie)

### Bezpieczeństwo (przed deploy)
- [ ] Rate limiting na `/auth/login`
- [ ] Email weryfikacyjny po rejestracji
- [ ] Reset hasła przez email
- [ ] HTTPS na produkcji (automatyczne przez Vercel + Railway)

---

## Deploy (produkcja)

| Co | Gdzie | Jak |
|----|-------|-----|
| Frontend | Vercel | Połącz repo `mundial-frontend`, auto-deploy z `main` |
| Backend | Railway | Połącz repo `mundial-backend`, ustaw env vars |
| Baza | Supabase | Stwórz projekt, uruchom migracje przez SQL editor |

Koszt: ~$5/mies. (Railway) + $0 (Vercel + Supabase)

---

## Workflow z Claude Code

- **Plan mode** (`Shift+Tab` dwa razy) dla każdego zadania które dotyka > 1 pliku.
- Jedno zadanie z MVP-checklisty naraz. Po każdym — przetestuj w `/docs` lub w przeglądarce.
- Zmiana logiki punktacji = **najpierw test, potem implementacja**.
- Backend i frontend rozwijane równolegle — ustalcie kontrakt API (co endpoint zwraca) zanim zaczniecie kodować.
- Komentarze w kodzie po angielsku, proste, styl junior/mid.
- `/clear` między zupełnie różnymi zadaniami.

---

## Co NIE wchodzi w MVP

- Powiadomienia push (PWA to obsługuje — na później)
- Statystyki historyczne i wykresy
- Społecznościowe funkcje (komentarze, reakcje)
- Apka natywna (React Native) — PWA wystarczy na start
- Wiele turniejów (na razie tylko Mundial 2026)
- Płatne plany / monetyzacja
