# Przepis: Aplikacja do typowania Mundialu 2026

Aplikacja dla znajomych do typowania wyników meczów Mundialu 2026 (11 czerwca – 19 lipca).
Prywatne ligi z kodem zaproszenia, ranking, bonus za mistrza i awanse z grup.

---

## Stack technologiczny

| Warstwa | Technologia | Dlaczego |
|---------|-------------|----------|
| Frontend | React + Vite (JS) | Kolega zna React, Vite szybszy niż CRA |
| Stylowanie | Tailwind CSS | Szybkie, responsywne, dobre na mobile |
| Backend | FastAPI (Python) | Już znasz, prosta współpraca z kolegą |
| Baza danych | PostgreSQL (Supabase) | Darmowy hosting, gotowy panel DB |
| Auth | JWT + bcrypt (passlib) | Standard branżowy, bezpieczne |
| E-mail | Resend | 3000 maili/mies. za darmo, proste API |
| Wyniki meczów | football-data.org API | Darmowe, obejmuje Mundial 2026 |
| Hosting frontend | Vercel | Darmowy, automatyczny deploy z Git |
| Hosting backend | Railway | ~$5/mies., nie zasypia, PostgreSQL opcjonalnie |
| Mobile | PWA | Manifest + ikona, działa jak apka na telefonie |

---

## Hosting — koszt miesięczny

| Wariant | Koszt | Uwagi |
|---------|-------|-------|
| W pełni darmowy | $0 | Render (backend) usypia po 15 min bezczynności |
| Komfortowy | ~$5/mies. | Railway — backend nie zasypia |
| Z własną domeną | ~$10/mies. | Railway + domena (~$2/rok na Cloudflare) |

Dla 20 znajomych: **Railway $5/mies.** jest optymalny.

---

## Bezpieczeństwo (email + hasło)

- Hasła hashowane **bcrypt** z solą — nieodwracalne, bezpieczne nawet przy wycieku bazy
- Sesje jako **JWT token** (ważny 7 dni) — przechowywany w `httpOnly cookie`, nie w localStorage
- **HTTPS** wszędzie — Vercel i Railway dają certyfikat SSL automatycznie
- Rate limiting na endpoint logowania — max 5 prób/minutę, blokada na 15 min
- Email weryfikacyjny po rejestracji (przez Resend) — opcjonalnie, ale warto
- Resetowanie hasła przez email — link z tokenem ważnym 1h

---

## Schemat bazy danych

```
users               — konta graczy (id, nick, email, password_hash, email_verified)
leagues             — prawdziwe ligi (Ekstraklasa, Mundial...)
teams               — drużyny
matches             — mecze z fazą (group/round_of_16/quarter/semi/final)
predictions         — typy wyników meczów (przed startem meczu)
bonus_predictions   — typy bonusowe (mistrz turnieju, awanse z grup)
scoring_rules       — konfiguracja punktów
private_leagues     — prywatne ligi znajomych (z join_code)
private_league_members — kto należy do której ligi
```

### Rozszerzenia względem obecnego projektu

```sql
-- w tabeli matches dodajemy fazę
ALTER TABLE matches ADD COLUMN stage VARCHAR(20) DEFAULT 'group';
-- stage: 'group' | 'round_of_16' | 'quarter' | 'semi' | 'final'

-- wyższe punkty w późniejszych fazach
ALTER TABLE scoring_rules ADD COLUMN stage_multiplier NUMERIC DEFAULT 1.0;
-- np. finał: exact=10, diff=6, tend=4 (mnożnik 2x)

-- typy bonusowe (przed turniejem)
CREATE TABLE bonus_predictions (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id),
    private_league_id INTEGER REFERENCES private_leagues(id),
    champion_team_id INTEGER REFERENCES teams(id),  -- mistrz turnieju
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- awanse z grup jako osobna tabela
CREATE TABLE group_advance_predictions (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id),
    group_name      VARCHAR(2),   -- 'A', 'B', 'C'...
    team_id         INTEGER REFERENCES teams(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## System punktacji

### Mecze (konfigurowalny per faza)

| Trafienie | Faza grupowa | 1/8 | 1/4 | Półfinał | Finał |
|-----------|-------------|-----|-----|----------|-------|
| Dokładny wynik | 5 | 7 | 9 | 11 | 15 |
| Różnica bramek | 3 | 4 | 5 | 6 | 8 |
| Tylko wynik (kto wygrał) | 2 | 3 | 4 | 5 | 6 |

### Bonusy (przed turniejem)

| Trafienie | Punkty |
|-----------|--------|
| Mistrz turnieju | 20 |
| Awans z grupy (za każdą drużynę) | 3 |

---

## Struktura projektu (dwa repo)

```
mundial-frontend/          ← React + Vite, deploy na Vercel
├── src/
│   ├── components/        ← przyciski, tabele, formularze
│   ├── pages/             ← Login, Register, Matches, Ranking, League
│   ├── api/               ← funkcje fetch do backendu
│   └── context/           ← AuthContext (JWT token)
├── public/
│   ├── manifest.json      ← PWA — ikona na telefonie
│   └── sw.js              ← service worker (cache offline)
└── vite.config.js

mundial-backend/           ← FastAPI, deploy na Railway
├── domain/
│   ├── scoring.py         ← czysta funkcja punktująca (z obecnego projektu!)
│   ├── match_results.py   ← przeliczanie punktów po meczu
│   └── predictions.py     ← walidacja deadline
├── db/
│   ├── connection.py      ← pool połączeń
│   ├── queries.py         ← SQL-e
│   └── migrations/        ← numerowane pliki SQL
├── routers/
│   ├── auth.py            ← POST /auth/register, /login, /refresh, /forgot-password
│   ├── matches.py         ← GET /matches, GET /matches/{id}
│   ├── predictions.py     ← POST /predictions, GET /my-predictions
│   ├── bonus.py           ← POST /bonus/champion, POST /bonus/group-advances
│   ├── ranking.py         ← GET /ranking, GET /ranking/{league_id}
│   ├── leagues.py         ← POST /leagues, POST /leagues/join, GET /leagues/{id}
│   └── admin.py           ← POST /matches/{id}/result (wpisanie wyniku)
├── schemas/
│   └── models.py          ← Pydantic modele
├── services/
│   ├── football_api.py    ← pobieranie wyników z football-data.org
│   └── email.py           ← wysyłanie maili przez Resend
└── main.py
```

---

## Kluczowe różnice vs obecny projekt

| Aspekt | Obecny projekt (zaliczenie) | Mundial app |
|--------|---------------------------|-------------|
| Auth | sha256 + localStorage | bcrypt + JWT httpOnly cookie |
| Sesje | Brak wygasania | Token ważny 7 dni, refresh token |
| Wyniki meczów | Wpisywane ręcznie przez admina | Auto-pobierane z API co 5 min |
| Email | Brak | Resend — weryfikacja, reset hasła |
| Fazy turnieju | Brak | group / knockout z mnożnikami punktów |
| Prywatne ligi | Schemat gotowy, niezaimplementowane | Pełna implementacja z kodem zaproszenia |
| Bonus typy | Brak | Mistrz turnieju, awanse z grup |
| Mobile | Brak | PWA (manifest + ikona) |
| Hosting | Lokalnie | Vercel + Railway + Supabase |
| HTTPS | Brak | Automatyczne (Vercel + Railway) |

---

## Co przenosisz z obecnego projektu 1:1

- `domain/scoring.py` — funkcja `calculate_points()` działa bez zmian
- `domain/match_results.py` — funkcja `calculate_match_points()` działa bez zmian
- `domain/predictions.py` — walidacja deadline bez zmian
- Podejście do migracji (numerowane pliki SQL)
- Wzorzec `db/queries.py` (SQL jako stałe, RealDictCursor)
- Wzorzec `get_conn()` / `release_conn()` z connection pool

---

## Pobieranie wyników z API (football-data.org)

```python
# services/football_api.py
import httpx
import os

API_KEY = os.getenv("FOOTBALL_API_KEY")
BASE_URL = "https://api.football-data.org/v4"

async def get_match_result(match_external_id: int) -> dict | None:
    # fetch live or finished match result from football-data.org
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{BASE_URL}/matches/{match_external_id}",
            headers={"X-Auth-Token": API_KEY}
        )
        if res.status_code != 200:
            return None
        data = res.json()
        score = data["score"]["fullTime"]
        return {"home": score["home"], "away": score["away"], "status": data["status"]}
```

Dodaj w `main.py` background task który co 5 minut odpytuje API o wyniki live meczów i wywołuje `/matches/{id}/result` dla zakończonych.

---

## PWA — jak zrobić w 1 godzinę

1. Dodaj `public/manifest.json`:
```json
{
  "name": "Typer Mundialowy",
  "short_name": "Typer",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#1a1a2e",
  "theme_color": "#e94560",
  "icons": [{ "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" }]
}
```

2. W `index.html` dodaj `<link rel="manifest" href="/manifest.json" />`

3. Dodaj ikonę `public/icon-512.png` (512x512px)

Użytkownicy na telefonie zobaczą "Dodaj do ekranu głównego" — działa jak natywna apka.

---

## Porównanie z kicktipp.pl

| Funkcja | kicktipp.pl | Twoja apka |
|---------|-------------|-----------|
| Prywatne ligi | ✅ | ✅ |
| Kod zaproszenia | ✅ | ✅ |
| Auto wyniki | ✅ | ✅ (football-data.org) |
| Fazy turnieju | ✅ | ✅ |
| Typ mistrza | ✅ | ✅ |
| Awanse z grup | ✅ | ✅ |
| Mobilna apka | ✅ natywna | PWA (wystarczy) |
| Powiadomienia push | ✅ | opcjonalnie (PWA obsługuje) |
| Reklamy | ✅ (plan darmowy) | ❌ czysta apka |
| Własny branding | ❌ | ✅ |
| Cena | Darmowy (z reklamami) | ~$5/mies. |

---

## Kolejność budowania (etapy)

### Etap 1 — Fundament (tydzień 1-2)
- [ ] Repo backend + frontend, podstawowa konfiguracja
- [ ] Migracja bazy: schemat mundialowy
- [ ] Auth: rejestracja email + hasło (bcrypt + JWT)
- [ ] React: strona logowania i rejestracji
- [ ] Deploy: Vercel + Railway + Supabase

### Etap 2 — Mecze i typy (tydzień 3)
- [ ] Zasilenie bazy meczami Mundialu (wszystkie 64 mecze — seed SQL)
- [ ] GET /matches — lista meczów z podziałem na fazy
- [ ] POST /predictions — dodaj typ (z walidacją deadline)
- [ ] React: widok meczów + formularz typowania

### Etap 3 — Ranking i ligi (tydzień 4)
- [ ] GET /ranking — z filtrowaniem po prywatnej lidze
- [ ] POST /leagues — stwórz prywatną ligę
- [ ] POST /leagues/join — dołącz kodem
- [ ] React: widok rankingu, widok ligi, zaproszenia

### Etap 4 — Auto wyniki + bonusy (tydzień 5)
- [ ] Integracja football-data.org — pobieranie wyników
- [ ] Background job — co 5 min sprawdza zakończone mecze
- [ ] POST /bonus/champion, /bonus/group-advances
- [ ] Przeliczanie punktów bonusowych po zakończeniu fazy grupowej

### Etap 5 — Polish (tydzień 6, przed Mundialem)
- [ ] PWA: manifest.json + ikona
- [ ] Reset hasła przez email (Resend)
- [ ] Weryfikacja emaila
- [ ] Rate limiting na auth
- [ ] Testy i QA

---

## Podział pracy z kolegą

| Ty (znasz backend) | Kolega (zna React) |
|--------------------|-------------------|
| FastAPI — auth, endpointy, migracje | React — strony, komponenty, routing |
| Integracja football-data.org | Tailwind — responsywny design, PWA |
| Logika punktacji + bonusy | Formularze typowania, walidacja |
| Deploy Railway + Supabase | Deploy Vercel |

Wspólnie: schemat bazy (ważne żeby obaj rozumieli), API kontrakt (co endpoint zwraca).

---

## Pierwsze kroki (zacznij od tego)

```bash
# 1. załóż konta
# - github.com (dwa osobne konta albo organizacja)
# - railway.app (darmowe $5 kredytów na start)
# - vercel.com
# - supabase.com
# - football-data.org (zarejestruj się po darmowy klucz API)
# - resend.com (darmowe 3000 maili/mies.)

# 2. stwórz dwa repo
git init mundial-backend
git init mundial-frontend

# 3. backend — skopiuj z obecnego projektu
cp typer/domain/scoring.py mundial-backend/domain/
cp typer/domain/match_results.py mundial-backend/domain/
cp typer/domain/predictions.py mundial-backend/domain/
cp typer/db/connection.py mundial-backend/db/

# 4. frontend — Vite + React
npm create vite@latest mundial-frontend -- --template react
cd mundial-frontend && npm install
npm install tailwindcss axios react-router-dom
```

---

## Szacowany czas z pomocą AI

| Etap | Czas realny (z AI) |
|------|-------------------|
| Fundament + auth | 2-3 dni |
| Mecze + typy | 2-3 dni |
| Ranking + ligi | 2-3 dni |
| Auto wyniki + bonusy | 2-3 dni |
| PWA + email + bezpieczeństwo | 1-2 dni |
| **Łącznie** | **~2-3 tygodnie** |

Przy współpracy dwóch osób + Claude Code: **realnie 2 tygodnie intensywnej pracy**.
Mundial startuje 11 czerwca 2026 — masz czas.
