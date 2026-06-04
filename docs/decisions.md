# Decyzje architektoniczne

Plik append-only: nowe decyzje na dół, stare zostają. Każdy wpis ma kontekst,
wybór, alternatywy które rozważaliśmy i krótkie "dlaczego".

Format inspirowany [ADR](https://adr.github.io/) ale lżejszy — to projekt
2-osobowy, nie potrzebujemy ceremonii.

Jak edytować: dodaj nowy nagłówek `## NNN — Tytuł (data)` na końcu. Nigdy nie
zmieniaj starych wpisów — zamiast tego dopisz nową decyzję "supersedes NNN".

---

## 001 — Pure functions zamiast klasycznej warstwy service (2026-06-02)

**Kontekst.** Standard w Spring/Java to `Controller → Service → Repository`.
W FastAPI łatwo zrobić to samo, ale router-y mają już typing + Pydantic +
Depends — większość tego co w Javie robiłby cienki controller.

**Decyzja.** Brak osobnej warstwy `service/`. Logika rozłożona na:
- `domain/` — **czyste funkcje** bez I/O (`scoring.calculate_points`, `predictions.is_prediction_allowed`)
- `routers/` — orkiestracja (woła `domain/` + `db/queries.py`, zwraca HTTP)
- `db/queries.py` — SQL jako stałe + funkcje opakowujące
- `services/` (folder) — **klienci ZEWNĘTRZNYCH** API (football-data, Resend),
  nie logika biznesowa. Uwaga na pułapkę nazewniczą: to nie spring-service.

**Alternatywy.** Klasyczna trójwarstwa Spring-style. Odrzucone bo dodaje
pliki/abstrakcje bez korzyści przy ~10 endpointach. Iron rule z CLAUDE.md
(warstwy się nie krzyżują: domain→nic, db→nic poza domain) daje tę samą
dyscyplinę bez ceremonii.

**Kiedy zrewidować.** Jeśli logika `submit_prediction`-style zaczyna się
powtarzać w >1 routerze albo w background-job-ach, ekstraktować do funkcji
w `services/predictions.py`. Wciąż funkcja, nie klasa.

---

## 002 — `pwdlib[argon2]` zamiast `passlib[bcrypt]` (2026-06-02)

**Kontekst.** CLAUDE.md pierwotnie zakładał `passlib[bcrypt]` (powszechny
wybór sprzed kilku lat). `passlib` jest jednak praktycznie nieutrzymywany
(ostatnie wydanie 2020) i rzuca AttributeError z `bcrypt >= 4.1`.

**Decyzja.** `pwdlib[argon2]` + `PasswordHash.recommended()` (Argon2id z
sensownymi parametrami pamięci/czasu).

**Alternatywy.**
- `bcrypt` bezpośrednio — działa, ale `bcrypt` cost 12 jest gorszy od
  Argon2id na nowoczesnym sprzęcie GPU.
- `passlib[bcrypt]` — stary konsensus, dziś dług techniczny.
- `argon2-cffi` bezpośrednio — pwdlib jest cienkim wrapperem, zapina się
  ładniej z FastAPI tutorial-em.

**Dlaczego.** FastAPI w aktualnej dokumentacji oficjalnie rekomenduje pwdlib
+ Argon2id. Argon2id wygrał Password Hashing Competition 2015, jest odporny
na ASIC/GPU dzięki dużemu zużyciu RAM (~64 MB per hash).

---

## 003 — JWT w `HttpOnly` cookie, nie w localStorage (2026-06-02)

**Kontekst.** Frontend musi gdzieś przechowywać token sesji. Dwa style:
localStorage + ręczne dorzucanie do `Authorization: Bearer`, albo cookie
ustawiane przez backend.

**Decyzja.** JWT w cookie z flagami `HttpOnly + SameSite=Lax + Secure (prod)`.
`Max-Age` = 7 dni (zgodnie z `JWT_EXPIRE_DAYS`). CORS z
`allow_credentials=True`, axios z `withCredentials: true`.

**Alternatywy.**
- localStorage. Odrzucone — XSS daje atakującemu pełen dostęp do tokenu
  (`document.cookie` go nie widzi przy `HttpOnly`).
- Cookie bez `SameSite`. Odrzucone — CSRF na POST z evil.com przeszłoby.
- `SameSite=Strict`. Odrzucone — psuje przypadki "user klika link z emaila"
  (browser nie wyśle cookie). `Lax` to złoty środek.

**Konsekwencje.** Frontend nigdy nie dotyka tokenu ręcznie — przeglądarka
zarządza sama. `/auth/refresh` przedłuża sesję. `/auth/logout` czyści cookie.

---

## 004 — Upsert na `POST /predictions` zamiast osobny PUT (2026-06-02)

**Kontekst.** User może zmienić typ aż do gwizdka. Dwie ścieżki: osobny
`PUT /predictions/{id}` na update + `POST /predictions` na create, albo
jeden endpoint upsert-owy.

**Decyzja.** Jeden `POST /predictions` z `INSERT ... ON CONFLICT (user_id,
match_id) DO UPDATE`. Zawsze 200 OK z aktualnym typem. Frontend nie musi
sprawdzać "czy już typowałem".

**Alternatywy.** Pełen REST (POST + PUT + GET). Odrzucone — więcej routes,
więcej kodu frontu, ten sam efekt biznesowy. UNIQUE constraint w DB zapewnia
"jeden typ per user per match" niezależnie od ścieżki HTTP.

**Konsekwencje.** Brak race condition na "sprawdź czy istnieje, potem
wstaw" — jeden round-trip do DB. Walidacja deadline-u (`kickoff_at > NOW()`)
w routerze przez `domain.predictions.is_prediction_allowed`.

---

## 005 — Admin gating: `ADMIN_EMAILS` w `.env`, nie kolumna `users.is_admin` (2026-06-02)

**Kontekst.** Endpoint `POST /matches/{id}/result` musi być chroniony przed
losowym userem. CLAUDE.md mówi "admin" ale nie precyzuje mechanizmu.
W schemacie nie ma `users.is_admin`.

**Decyzja.** Lista emaili przez przecinek w `.env`:
```env
ADMIN_EMAILS=bartek@example.com,kolega@example.com
```
Dependency `get_admin_user` (w `routers/deps.py`) sprawdza
`current_user.email` przeciw liście → 403 jeśli nie pasuje.

**Alternatywy.**
- `users.is_admin BOOLEAN` (migracja 004) + dependency czyta z DB. Odrzucone
  bo: 2-osobowy zespół, stała lista, admin to backup (główna ścieżka =
  auto-update z football-data.org), więcej kodu na feature który pewnie nie
  będzie potrzebny po MVP.
- Brak auth (dev only). Odrzucone — niebezpieczne, ktoś mógłby wpisać
  fałszywe wyniki.

**Konsekwencje.** Promowanie nowego admina = edycja `.env` + restart
backendu. Tożsamość jest emailem — jeśli kiedyś dodamy zmianę emaila przez
UI, admin status pęknie (acceptable risk, email nie jest zmienialny przez
UI w MVP).

**Kiedy zrewidować.** Jeśli adminów będzie >5 lub często się zmieniają.
Migracja do kolumny `is_admin` zajmie ~30 minut.

---

## 006 — Migracje SQL append-only, bez tabeli śledzącej (2026-06-02)

**Kontekst.** Trzymamy migracje jako `db/migrations/NNN_nazwa.sql`. Trzeba
zdecydować jak je aplikować.

**Decyzja.** Bash script `scripts/migrate.sh` aplikuje wszystkie pliki w
kolejności leksykograficznej przez `psql -v ON_ERROR_STOP=1`. **Brak tabeli
`schema_migrations`** śledzącej co zaaplikowane.

**Alternatywy.**
- Alembic / yoake / manual `schema_migrations` table. Odrzucone na teraz —
  overhead dla 3-osobowego zespołu migracji.
- Re-runnable migrations (`IF NOT EXISTS` wszędzie). Odrzucone — utrudnia
  pisanie i ukrywa pomyłki.

**Konsekwencje.** Ponowne uruchomienie skryptu na zapełnionej bazie sypnie
się fail-fast (UNIQUE/relation exists). To zamierzona ochrona przed
podwójną aplikacją. Flaga `--reset` daje czysty start w dev.

**Kiedy zrewidować.** Przed pierwszym deploy-em na Supabase / przy >10
migracjach. Wtedy doda się `schema_migrations` + lekki migrator.

---

## 007 — Login rate limiting in-memory, nie Redis (2026-06-04)

**Kontekst.** CLAUDE.md wymaga rate limitingu na `/auth/login`: 5 prób/min
per IP, blokada 15 min. Trzeba gdzieś trzymać stan licznika prób per IP.

**Decyzja.** Stan **in-memory** — zwykły `dict[str, RateLimitState]` w
`routers/auth.py`. Czysta logika (`is_locked`, `record_failure`) w
`domain/rate_limit.py` dostaje `now` jako argument → testowalna bez zegara.
Liczymy tylko **nieudane** próby; udane logowanie czyści licznik dla IP.
IP czytane z `X-Forwarded-For` (za proxy Railway), fallback `client.host`.

**Alternatywy.**
- Redis — poprawne dla multi-instance, ale dodatkowa infra + zależność dla
  feature który na single-instance działa trywialnie. Odrzucone na teraz.
- Postgres (tabela z próbami) — przesada, dokłada zapis do DB na każdy login.
- Biblioteka `slowapi` — działa, ale to kolejna zależność; nasza logika to
  ~30 linii i jest w pełni pod kontrolą + przetestowana.

**Konsekwencje.** Stan **nie przeżywa restartu** procesu (restart = reset
liczników) i **nie jest współdzielony** między workerami/instancjami. Dla
MVP na jednym kontenerze Railway to akceptowalne — restart i tak rozłącza
sesje, a brute-force i tak musiałby zmieścić się w oknie między restartami.

**Kiedy zrewidować.** Gdy uruchomimy >1 worker uvicorna (`--workers N`) lub
>1 instancję na Railway — wtedy każdy proces ma własny licznik i limit się
rozjeżdża. Przejście na Redis (np. `redis-py` + ten sam `domain/rate_limit`).
